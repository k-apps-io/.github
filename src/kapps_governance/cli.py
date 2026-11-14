"""Command interface shared by local development and scheduled automation."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from githubkit.exception import GitHubException

from .github_client import make_client
from .ruleset_sync import reconcile, validate


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="governance")
    resources = root.add_subparsers(dest="resource", required=True)
    actions = resources.add_parser("rulesets").add_subparsers(dest="action", required=True)
    sync = actions.add_parser("sync")
    sync.add_argument("--config", type=Path, default=Path(".github/rulesets/pr-baseline.json"))
    sync.add_argument("--output", type=Path, default=Path("artifacts/ruleset-sync"))
    sync.add_argument("--ruleset-id", type=int)
    sync.add_argument("--dry-run", choices=("true", "false"), default="true")
    sync.add_argument(
        "--yes", action="store_true", help="Skip confirmation; does not enable writes"
    )
    sync.add_argument("--validate-only", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    dry_run = args.dry_run == "true"
    # Isolate each invocation so rollback snapshots cannot be overwritten by later runs.
    output = args.output / datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True, exist_ok=False)
    try:
        config = json.loads(args.config.read_text())
        validate(config)
        if args.validate_only:
            message = "Configuration valid; no API requests performed."
        else:
            if not dry_run and not args.yes and not sys.stdin.isatty():
                raise ValueError("Noninteractive writes require --dry-run false --yes")

            def confirm(diff: str) -> bool:
                print(diff)
                return args.yes or input("Apply this ruleset plan? [y/N] ").strip().lower() == "y"

            with make_client() as github:
                message = reconcile(
                    config,
                    output,
                    github=github,
                    dry_run=dry_run,
                    ruleset_id=args.ruleset_id,
                    confirm=confirm,
                )
        status = 0
    except GitHubException as error:
        response = getattr(error, "response", None)
        http_status = getattr(response, "status_code", "unknown")
        message = (
            f"FAILED: GitHub request failed (HTTP {http_status}); check permissions, "
            "token approval/expiry, and API availability. No automatic retry was attempted."
        )
        status = 1
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        RuntimeError,
        EOFError,
    ) as error:
        message = f"FAILED: {error}"
        status = 1
    report = f"# Ruleset sync\n\n- Mode: {'dry-run' if dry_run else 'apply'}\n- Client: GitHubKit\n\n{message}\n"
    (output / "report.md").write_text(report)
    print(message)
    print(f"Report: {output / 'report.md'}")
    return status
