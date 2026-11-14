import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("sync", ROOT / ".github/scripts/ruleset-sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


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
                return ([{"id": 42, "name": sync.NAME}] if self.state else []) + [{"id": 7, "name": "unrelated"}]
            return copy.deepcopy(self.state)
        self.state = dict(copy.deepcopy(payload), id=42, source="k-apps-io", source_type="Organization")
        return copy.deepcopy(self.state)

    def run_sync(self, **kwargs):
        return sync.reconcile(self.config, self.output, request=self.api, **kwargs)

    def test_missing_dry_run_never_writes(self):
        self.assertIn("would create", self.run_sync())
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_create_then_reapply_is_noop(self):
        self.run_sync(apply=True)
        self.calls.clear()
        self.assertIn("No drift", self.run_sync(apply=True, ruleset_id=42))
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_update_preserves_unrelated_rulesets(self):
        self.state = dict(copy.deepcopy(self.config), id=42)
        self.state["enforcement"] = "disabled"
        self.assertIn("would update", self.run_sync(ruleset_id=42))
        self.run_sync(apply=True, ruleset_id=42)
        self.assertEqual([endpoint for method, endpoint in self.calls if method != "GET"], ["orgs/k-apps-io/rulesets/42"])
        self.assertEqual(json.loads((self.output / "before.json").read_text())["enforcement"], "disabled")

    def test_requires_explicit_ownership(self):
        self.state = dict(self.config, id=42)
        with self.assertRaisesRegex(ValueError, "ownership"):
            self.run_sync(apply=True)

    def test_missing_pin_does_not_recreate(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            self.run_sync(apply=True, ruleset_id=42)

    def test_invalid_scope_fails_before_api(self):
        self.config["conditions"]["repository_name"]["include"] = ["~ALL"]
        with self.assertRaises(ValueError):
            self.run_sync(apply=True)
        self.assertEqual(self.calls, [])

    def test_permissions_failure_does_not_mutate(self):
        def fail(*args, **kwargs):
            raise RuntimeError("403 insufficient permissions")
        with self.assertRaisesRegex(RuntimeError, "403"):
            sync.reconcile(self.config, self.output, apply=True, request=fail)

    def test_duplicate_name_fails(self):
        def duplicate(*args, **kwargs):
            return [{"id": i, "name": sync.NAME} for i in (1, 2)]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            sync.reconcile(self.config, self.output, request=duplicate)

    def test_concurrent_change_fails_without_write(self):
        self.state = dict(copy.deepcopy(self.config), id=42, enforcement="disabled")
        reads = 0
        def changing(method, endpoint, **kwargs):
            nonlocal reads
            result = self.api(method, endpoint, **kwargs)
            if endpoint.endswith("/42"):
                reads += 1
                if reads == 2:
                    result["bypass_actors"] = [{"actor_type": "OrganizationAdmin", "bypass_mode": "always"}]
            return result
        with self.assertRaisesRegex(RuntimeError, "changed during planning"):
            sync.reconcile(self.config, self.output, apply=True, ruleset_id=42, request=changing)
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_failed_write_is_not_reported_successful(self):
        def fail_write(method, endpoint, **kwargs):
            if method == "POST":
                raise RuntimeError("422 unsupported feature")
            return self.api(method, endpoint, **kwargs)
        with self.assertRaisesRegex(RuntimeError, "422"):
            sync.reconcile(self.config, self.output, apply=True, request=fail_write)
        self.assertIsNone(self.state)
        self.assertFalse((self.output / "applied.json").exists())

    def test_cli_failure_writes_failure_report(self):
        with patch("sys.argv", ["ruleset-sync", "--output", str(self.output)]), patch.object(
            sync, "reconcile", side_effect=RuntimeError("403 insufficient permissions")
        ):
            self.assertEqual(sync.main(), 1)
        self.assertIn("FAILED", (self.output / "report.md").read_text())

    def test_order_and_metadata_are_not_drift(self):
        self.state = dict(copy.deepcopy(self.config), id=42, updated_at="today")
        self.state["rules"].reverse()
        self.assertIn("No drift", self.run_sync(ruleset_id=42))


if __name__ == "__main__":
    unittest.main()
