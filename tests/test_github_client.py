import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import httpx
from githubkit import GitHub

from kapps_governance import cli
from kapps_governance.github_client import make_client
from kapps_governance.ruleset_sync import reconcile

ROOT = Path(__file__).resolve().parents[1]


class GitHubKitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / ".github/rulesets/pr-baseline.json").read_text())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)

    def test_factory_returns_supported_client_with_safe_settings(self):
        with patch.dict("os.environ", {"GH_TOKEN": "test-token"}), make_client() as github:
            self.assertIsInstance(github, GitHub)
            self.assertFalse(github.config.http_cache)
            self.assertIsNone(github.config.auto_retry)
            self.assertEqual(github.config.timeout.read, 30)

    def test_missing_token_does_not_invoke_cli(self):
        with patch.dict("os.environ", {}, clear=True), patch("subprocess.run") as run:
            with self.assertRaisesRegex(ValueError, "GH_TOKEN"):
                make_client()
            run.assert_not_called()

    def test_reconciliation_paginates_and_preserves_unknown_fields(self):
        seen = []

        def handler(request):
            seen.append(request)
            if request.url.path.endswith("/42"):
                policy = {**self.config, "id": 42}
                policy["conditions"] = {**self.config["conditions"], "future_condition": True}
                return httpx.Response(200, json=policy)
            if request.url.params.get("page") == "2":
                return httpx.Response(200, json=[{"id": 42, "name": self.config["name"]}])
            return httpx.Response(
                200,
                json=[{"id": 7, "name": "unrelated"}],
                headers={
                    "Link": '<https://api.github.com/orgs/k-apps-io/rulesets?page=2>; rel="next"'
                },
            )

        with GitHub(
            "fake", transport=httpx.MockTransport(handler), http_cache=False, auto_retry=False
        ) as github:
            result = reconcile(self.config, self.output, github=github, ruleset_id=42)
        self.assertIn("would update", result)
        self.assertIn("future_condition", (self.output / "drift.diff").read_text())
        self.assertTrue(all(r.method == "GET" for r in seen))
        self.assertTrue(all(r.headers["X-GitHub-Api-Version"] == "2026-03-10" for r in seen))

    def test_sdk_write_payload_is_exact_and_create_not_retried(self):
        calls = []

        def handler(request):
            calls.append(request)
            if request.method == "POST":
                self.assertEqual(json.loads(request.content), self.config)
                return httpx.Response(503, json={"message": "secret-sentinel"})
            return httpx.Response(200, json=[])

        with (
            patch.object(
                cli,
                "make_client",
                side_effect=lambda: GitHub(
                    "fake",
                    transport=httpx.MockTransport(handler),
                    http_cache=False,
                    auto_retry=False,
                ),
            ),
            redirect_stdout(io.StringIO()),
        ):
            status = cli.main(
                ["rulesets", "sync", "--output", str(self.output), "--dry-run", "false", "--yes"]
            )
        self.assertEqual(status, 1)
        self.assertEqual(sum(r.method == "POST" for r in calls), 1)
        report = next(self.output.glob("*/report.md")).read_text()
        self.assertIn("HTTP 503", report)
        self.assertNotIn("secret-sentinel", report)

    def test_transport_failure_produces_sanitized_report(self):
        def handler(request):
            raise httpx.ConnectError("secret-sentinel", request=request)

        with (
            patch.object(
                cli,
                "make_client",
                side_effect=lambda: GitHub(
                    "fake",
                    transport=httpx.MockTransport(handler),
                    http_cache=False,
                    auto_retry=False,
                ),
            ),
            redirect_stdout(io.StringIO()),
        ):
            status = cli.main(["rulesets", "sync", "--output", str(self.output)])
        self.assertEqual(status, 1)
        report = next(self.output.glob("*/report.md")).read_text()
        self.assertIn("FAILED", report)
        self.assertNotIn("secret-sentinel", report)
