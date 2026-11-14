#!/usr/bin/env python3
"""Reconcile the single MVP organization ruleset through gh; dry-run by default."""
import argparse
import difflib
import json
from pathlib import Path
import subprocess
import sys

ORG = "k-apps-io"
NAME = "kapps-managed-pr-baseline"
FIELDS = ("name", "target", "enforcement", "bypass_actors", "conditions", "rules")


def canonical(value):
    """Ignore response metadata, but retain unknown policy fields to expose drift."""
    def normalize(item):
        if isinstance(item, dict):
            return {k: normalize(v) for k, v in item.items()}
        if isinstance(item, list):
            return sorted((normalize(v) for v in item), key=lambda v: json.dumps(v, sort_keys=True))
        return item
    return normalize({k: value[k] for k in FIELDS if k in value})


def validate(config):
    if set(config) != set(FIELDS) or config["name"] != NAME:
        raise ValueError("Expected the named managed ruleset and exactly the supported top-level fields")
    if config["target"] != "branch" or config["enforcement"] not in ("active", "disabled"):
        raise ValueError("Only active/disabled branch rulesets are supported")
    if config["bypass_actors"] != []:
        raise ValueError("MVP does not authorize bypass actors")
    expected_conditions = {
        "repository_name": {"include": ["ok-agent-ts", "ok-agent-openai-ts"], "exclude": [], "protected": False},
        "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []},
    }
    if canonical({"conditions": config["conditions"]}) != canonical({"conditions": expected_conditions}):
        raise ValueError("Targeting must be exactly the two approved pilot repositories' default branches")
    expected_rules = [
        {"type": "deletion"}, {"type": "non_fast_forward"},
        {"type": "pull_request", "parameters": {
            "allowed_merge_methods": ["merge", "squash", "rebase"],
            "dismiss_stale_reviews_on_push": False, "require_code_owner_review": False,
            "require_last_push_approval": False, "required_approving_review_count": 0,
            "required_review_thread_resolution": False,
            "required_reviewers": [], "require_extra_approval_for_unattributed_changes": False,
        }},
    ]
    if json.dumps(canonical({"rules": config["rules"]}), sort_keys=True) != json.dumps(canonical({"rules": expected_rules}), sort_keys=True):
        raise ValueError("Rules must match the approved zero-approval MVP; policy expansion requires code review")


def api(method, endpoint, payload=None, paginate=False):
    command = ["gh", "api", "--method", method, "-H", "Accept: application/vnd.github+json", endpoint]
    if paginate:
        command += ["--paginate", "--slurp"]
    if payload is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{method} {endpoint} failed: {result.stderr.strip()} "
                           "Verify organization Administration write permission (classic OAuth: admin:org) and plan support.")
    value = json.loads(result.stdout)
    return [item for page in value for item in page] if paginate else value


def reconcile(config, output, apply=False, ruleset_id=None, request=api):
    validate(config)
    endpoint = f"orgs/{ORG}/rulesets"
    existing = request("GET", endpoint + "?per_page=100", paginate=True)
    matches = [item for item in existing if item["name"] == NAME]
    if len(matches) > 1:
        raise ValueError("Duplicate managed names; resolve ambiguity manually")
    if matches and ruleset_id != matches[0]["id"]:
        raise ValueError(f"Existing ruleset requires --ruleset-id {matches[0]['id']} to explicitly confirm ownership")
    if not matches and ruleset_id is not None:
        raise ValueError("Pinned ruleset is missing or renamed; refusing to create a replacement")
    current = request("GET", f"{endpoint}/{ruleset_id}") if matches else None
    output.mkdir(parents=True, exist_ok=True)
    (output / "before.json").write_text(json.dumps(current, indent=2) + "\n")
    (output / "desired.json").write_text(json.dumps(config, indent=2) + "\n")
    before = json.dumps(canonical(current) if current else {}, indent=2, sort_keys=True).splitlines(True)
    after = json.dumps(canonical(config), indent=2, sort_keys=True).splitlines(True)
    diff = "".join(difflib.unified_diff(before, after, fromfile="current", tofile="desired"))
    (output / "drift.diff").write_text(diff)
    if not diff:
        return "No drift; no writes performed."
    if not apply:
        return "Drift detected; would " + ("update" if current else "create") + ". No writes performed. See drift.diff."
    # Re-read immediately before a write to detect concurrent changes.
    if current:
        latest = request("GET", f"{endpoint}/{ruleset_id}")
        if canonical(latest) != canonical(current):
            raise RuntimeError("Ruleset changed during planning; rerun dry-run")
        result = request("PUT", f"{endpoint}/{ruleset_id}", payload=config)
    else:
        latest = request("GET", endpoint + "?per_page=100", paginate=True)
        if any(item["name"] == NAME for item in latest):
            raise RuntimeError("Managed name appeared during planning; rerun dry-run")
        result = request("POST", endpoint, payload=config)
    (output / "applied.json").write_text(json.dumps(result, indent=2) + "\n")
    actual = request("GET", f"{endpoint}/{result['id']}")
    if canonical(actual) != canonical(config):
        raise RuntimeError("Read-back differs from desired policy; inspect applied.json and restore before.json if needed")
    return f"Applied and verified ruleset {result['id']}. Pin this ID for subsequent runs."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(".github/rulesets/pr-baseline.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/ruleset-sync"))
    parser.add_argument("--ruleset-id", type=int)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        config = json.loads(args.config.read_text())
        validate(config)
        message = "Configuration valid." if args.validate_only else reconcile(config, args.output, args.apply, args.ruleset_id)
        status = 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        message = f"FAILED: {error}"
        status = 1
    (args.output / "report.md").write_text("# Ruleset sync\n\n" + message + "\n")
    print(message)
    return status


if __name__ == "__main__":
    sys.exit(main())
