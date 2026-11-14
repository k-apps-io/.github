import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from githubkit import GitHub

from kapps_governance import cli
from kapps_governance.ruleset_sync import NAME

ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self):
        self.calls = []
        self.policy = json.loads((ROOT / ".github/rulesets/pr-baseline.json").read_text())
        self.current = dict(copy.deepcopy(self.policy), id=42, enforcement="disabled")

    def __call__(self, method, endpoint, payload=None, paginate=False):
        self.calls.append(method)
        if method == "GET":
            return [{"name": NAME, "id": 42}] if paginate else copy.deepcopy(self.current)
        self.current = dict(copy.deepcopy(payload), id=42)
        return self.current

    def close(self):
        pass


class CliTests(unittest.TestCase):
    def setUp(self):
        patch("sys.stdout", new_callable=io.StringIO).start()
        patch("sys.stderr", new_callable=io.StringIO).start()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.client = FakeClient()
        self.base = ["rulesets", "sync", "--output", str(self.output), "--ruleset-id", "42"]

        def transport(request):
            result = self.client(
                request.method,
                request.url.path,
                payload=json.loads(request.content) if request.content else None,
                paginate=request.method == "GET" and request.url.path.endswith("/rulesets"),
            )
            return httpx.Response(200, json=result)

        self.factory = patch.object(
            cli,
            "make_client",
            side_effect=lambda: GitHub(
                "fake-token",
                transport=httpx.MockTransport(transport),
                http_cache=False,
                auto_retry=False,
            ),
        ).start()
        self.addCleanup(patch.stopall)

    def run_cli(self, *args, tty=False, answer="n"):
        with (
            patch("sys.stdin.isatty", return_value=tty),
            patch("builtins.input", return_value=answer) as prompt,
        ):
            result = cli.main(self.base + list(args))
        return result, prompt

    def test_default_dry_run_and_yes_never_write(self):
        for args in [(), ("--yes",), ("--dry-run", "true", "--yes")]:
            status, prompt = self.run_cli(*args)
            self.assertEqual(status, 0)
            prompt.assert_not_called()
        self.assertTrue(all(call == "GET" for call in self.client.calls))
        self.assertEqual(len(list(self.output.glob("*/before.json"))), 3)

    def test_explicit_unattended_apply(self):
        status, prompt = self.run_cli("--dry-run", "false", "--yes")
        self.assertEqual(status, 0)
        self.assertEqual(self.client.calls.count("PUT"), 1)
        prompt.assert_not_called()

    def test_noninteractive_apply_requires_yes_before_api(self):
        status, _ = self.run_cli("--dry-run", "false")
        self.assertEqual(status, 1)
        self.factory.assert_not_called()
        self.assertIn("Noninteractive", next(self.output.glob("*/report.md")).read_text())

    def test_interactive_confirmation_and_decline(self):
        for answer, expected_status in [("n", 1), ("y", 0)]:
            status, prompt = self.run_cli("--dry-run", "false", tty=True, answer=answer)
            self.assertEqual(status, expected_status)
            prompt.assert_called_once()
        self.assertEqual(self.client.calls.count("PUT"), 1)

    def test_invalid_boolean_and_old_apply_rejected(self):
        for args in [("--dry-run", "no"), ("--dry-run",), ("--apply",)]:
            with self.assertRaises(SystemExit) as result:
                self.run_cli(*args)
            self.assertEqual(result.exception.code, 2)
        self.factory.assert_not_called()

    def test_validation_needs_no_authentication(self):
        self.assertEqual(self.run_cli("--validate-only")[0], 0)
        self.factory.assert_not_called()

    def test_failure_produces_report(self):
        self.factory.side_effect = ValueError("Missing token")
        self.assertEqual(self.run_cli()[0], 1)
        self.assertIn("FAILED", next(self.output.glob("*/report.md")).read_text())
