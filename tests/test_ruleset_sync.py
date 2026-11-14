import copy
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from githubkit import GitHub
from githubkit.exception import GitHubException

from kapps_governance import ruleset_sync as sync

ROOT = Path(__file__).resolve().parents[1]


class RulesetTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / ".github/rulesets/pr-baseline.json").read_text())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.state = None
        self.calls = []

    def api(self, method, endpoint, payload=None, paginate=False):
        self.calls.append((method, endpoint))
        if method == "GET":
            if paginate:
                return ([{"id": 42, "name": sync.NAME}] if self.state else []) + [
                    {"id": 7, "name": "unrelated"}
                ]
            return copy.deepcopy(self.state)
        self.state = dict(
            copy.deepcopy(payload), id=42, source="k-apps-io", source_type="Organization"
        )
        return copy.deepcopy(self.state)

    def client(self, handler):
        def transport(request):
            listing = request.method == "GET" and request.url.path.endswith("/rulesets")
            result = handler(
                request.method,
                request.url.path.lstrip("/"),
                payload=json.loads(request.content) if request.content else None,
                paginate=listing,
            )
            return (
                result if isinstance(result, httpx.Response) else httpx.Response(200, json=result)
            )

        return self.enterContext(
            GitHub(
                "test-token",
                transport=httpx.MockTransport(transport),
                http_cache=False,
                auto_retry=False,
            )
        )

    def run_sync(self, **kwargs):
        return sync.reconcile(self.config, self.output, github=self.client(self.api), **kwargs)

    def test_missing_dry_run_never_writes(self):
        self.assertIn("would create", self.run_sync())
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_create_then_reapply_is_noop(self):
        self.run_sync(dry_run=False, confirm=lambda diff: True)
        self.calls.clear()
        self.assertIn(
            "No drift", self.run_sync(dry_run=False, confirm=lambda diff: True, ruleset_id=42)
        )
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_update_preserves_unrelated_rulesets(self):
        self.state = dict(copy.deepcopy(self.config), id=42)
        self.state["enforcement"] = "disabled"
        self.assertIn("would update", self.run_sync(ruleset_id=42))
        self.run_sync(dry_run=False, confirm=lambda diff: True, ruleset_id=42)
        self.assertEqual(
            [endpoint for method, endpoint in self.calls if method != "GET"],
            ["orgs/k-apps-io/rulesets/42"],
        )
        self.assertEqual(
            json.loads((self.output / "before.json").read_text())["enforcement"], "disabled"
        )

    def test_requires_explicit_ownership(self):
        self.state = dict(self.config, id=42)
        with self.assertRaisesRegex(ValueError, "ownership"):
            self.run_sync(dry_run=False, confirm=lambda diff: True)

    def test_missing_pin_does_not_recreate(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            self.run_sync(dry_run=False, confirm=lambda diff: True, ruleset_id=42)

    def test_invalid_scope_fails_before_api(self):
        self.config["conditions"]["repository_name"]["include"] = ["~ALL"]
        with self.assertRaises(ValueError):
            self.run_sync(dry_run=False, confirm=lambda diff: True)
        self.assertEqual(self.calls, [])

    def test_repository_list_is_configuration_driven(self):
        self.config["conditions"]["repository_name"]["include"] = ["another-repo", ".github"]
        self.assertIn("would create", self.run_sync())
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_invalid_repository_lists_rejected(self):
        for names in [
            [],
            "repo",
            [None],
            ["org/repo"],
            ["repo*"],
            ["~ALL"],
            ["a", "A"],
            [" repo"],
            [".."],
        ]:
            with self.subTest(names=names):
                self.config["conditions"]["repository_name"]["include"] = names
                with self.assertRaises(ValueError):
                    self.run_sync()
        self.assertEqual(self.calls, [])

    def test_branch_scope_stays_default_only(self):
        self.config["conditions"]["ref_name"]["include"] = ["~ALL"]
        with self.assertRaisesRegex(ValueError, "default branch"):
            self.run_sync()
        self.assertEqual(self.calls, [])

    def test_permissions_failure_does_not_mutate(self):
        def fail(*args, **kwargs):
            return httpx.Response(403, json={"message": "insufficient permissions"})

        with self.assertRaises(GitHubException):
            sync.reconcile(
                self.config,
                self.output,
                dry_run=False,
                confirm=lambda diff: True,
                github=self.client(fail),
            )

    def test_duplicate_name_fails(self):
        def duplicate(*args, **kwargs):
            return [{"id": i, "name": sync.NAME} for i in (1, 2)]

        with self.assertRaisesRegex(ValueError, "Duplicate"):
            sync.reconcile(self.config, self.output, github=self.client(duplicate))

    def test_concurrent_change_fails_without_write(self):
        self.state = dict(copy.deepcopy(self.config), id=42, enforcement="disabled")
        reads = 0

        def changing(method, endpoint, **kwargs):
            nonlocal reads
            result = self.api(method, endpoint, **kwargs)
            if endpoint.endswith("/42"):
                reads += 1
                if reads == 2:
                    result["bypass_actors"] = [
                        {"actor_type": "OrganizationAdmin", "bypass_mode": "always"}
                    ]
            return result

        with self.assertRaisesRegex(RuntimeError, "changed during planning"):
            sync.reconcile(
                self.config,
                self.output,
                dry_run=False,
                confirm=lambda diff: True,
                ruleset_id=42,
                github=self.client(changing),
            )
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_failed_write_is_not_reported_successful(self):
        def fail_write(method, endpoint, **kwargs):
            if method == "POST":
                return httpx.Response(422, json={"message": "unsupported feature"})
            return self.api(method, endpoint, **kwargs)

        with self.assertRaises(GitHubException):
            sync.reconcile(
                self.config,
                self.output,
                dry_run=False,
                confirm=lambda diff: True,
                github=self.client(fail_write),
            )
        self.assertIsNone(self.state)
        self.assertFalse((self.output / "applied.json").exists())

    def test_order_and_metadata_are_not_drift(self):
        self.state = dict(copy.deepcopy(self.config), id=42, updated_at="today")
        self.state["rules"].reverse()
        self.assertIn("No drift", self.run_sync(ruleset_id=42))


if __name__ == "__main__":
    unittest.main()
