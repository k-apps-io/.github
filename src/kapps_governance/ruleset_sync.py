#!/usr/bin/env python3
"""Reconcile the single MVP organization ruleset through GitHubKit; dry-run by default."""

import difflib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

from githubkit import GitHub
from githubkit_schemas.v2026_03_10.types import (
    OrgsOrgRulesetsPostBodyType,
    OrgsOrgRulesetsRulesetIdPutBodyType,
)

from .github_client import API_VERSION

ORG = "k-apps-io"
NAME = "kapps-managed-pr-baseline"
FIELDS = ("name", "target", "enforcement", "bypass_actors", "conditions", "rules")


def canonical(value: Mapping[str, Any]) -> dict[str, Any]:
    """Ignore response metadata, but retain unknown policy fields to expose drift."""

    def normalize(item: Any) -> Any:
        if isinstance(item, dict):
            return {k: normalize(v) for k, v in item.items()}
        if isinstance(item, list):
            return sorted((normalize(v) for v in item), key=lambda v: json.dumps(v, sort_keys=True))
        return item

    return normalize({k: value[k] for k in FIELDS if k in value})


def validate(config: dict[str, Any]) -> None:
    if set(config) != set(FIELDS) or config["name"] != NAME:
        raise ValueError(
            "Expected the named managed ruleset and exactly the supported top-level fields"
        )
    if config["target"] != "branch" or config["enforcement"] not in ("active", "disabled"):
        raise ValueError("Only active/disabled branch rulesets are supported")
    if config["bypass_actors"] != []:
        raise ValueError("MVP does not authorize bypass actors")
    conditions = config["conditions"]
    if not isinstance(conditions, dict) or set(conditions) != {"repository_name", "ref_name"}:
        raise ValueError("Targeting requires repository_name and ref_name conditions")
    repositories = conditions["repository_name"]
    if not isinstance(repositories, dict) or set(repositories) != {
        "include",
        "exclude",
        "protected",
    }:
        raise ValueError("Repository targeting requires include, exclude, and protected fields")
    names = repositories["include"]
    if (
        not isinstance(names, list)
        or not names
        or any(
            not isinstance(name, str)
            or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name) is None
            or name in {".", ".."}
            for name in names
        )
    ):
        raise ValueError(
            "Repository include must be a nonempty list of explicit repository names (no owners or wildcards)"
        )
    if len({name.lower() for name in names}) != len(names):
        raise ValueError("Repository include contains duplicate names")
    if repositories["exclude"] != [] or repositories["protected"] is not False:
        raise ValueError(
            "Repository exclusions and rename protection are not supported by this policy"
        )
    if conditions["ref_name"] != {"include": ["~DEFAULT_BRANCH"], "exclude": []}:
        raise ValueError("Branch targeting must select only each repository's default branch")
    expected_rules = [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "allowed_merge_methods": ["merge", "squash", "rebase"],
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_approving_review_count": 0,
                "required_review_thread_resolution": False,
                "required_reviewers": [],
                "require_extra_approval_for_unattributed_changes": False,
            },
        },
    ]
    if json.dumps(canonical({"rules": config["rules"]}), sort_keys=True) != json.dumps(
        canonical({"rules": expected_rules}), sort_keys=True
    ):
        raise ValueError(
            "Rules must match the approved zero-approval MVP; policy expansion requires code review"
        )


def reconcile(
    config: dict[str, Any],
    output: Path,
    *,
    github: GitHub,
    dry_run: bool = True,
    ruleset_id: int | None = None,
    confirm: Callable[[str], bool] | None = None,
) -> str:
    validate(config)
    repos = github.rest(API_VERSION).repos
    existing = list(
        github.rest.paginate(
            repos.get_org_rulesets,
            map_func=lambda response: response.json(),
            org=ORG,
            per_page=100,
            headers={"X-GitHub-Api-Version": API_VERSION},
        )
    )
    matches = [item for item in existing if item["name"] == NAME]
    if len(matches) > 1:
        raise ValueError("Duplicate managed names; resolve ambiguity manually")
    if matches and ruleset_id != matches[0]["id"]:
        raise ValueError(
            f"Existing ruleset requires --ruleset-id {matches[0]['id']} to explicitly confirm ownership"
        )
    if not matches and ruleset_id is not None:
        raise ValueError("Pinned ruleset is missing or renamed; refusing to create a replacement")
    current = repos.get_org_ruleset(ORG, ruleset_id).json() if ruleset_id is not None else None
    output.mkdir(parents=True, exist_ok=True)
    (output / "before.json").write_text(json.dumps(current, indent=2) + "\n")
    (output / "desired.json").write_text(json.dumps(config, indent=2) + "\n")
    before = (
        json.dumps(canonical(current) if current else {}, indent=2, sort_keys=True) + "\n"
    ).splitlines(True)
    after = (json.dumps(canonical(config), indent=2, sort_keys=True) + "\n").splitlines(True)
    diff = "".join(difflib.unified_diff(before, after, fromfile="current", tofile="desired"))
    (output / "drift.diff").write_text(diff)
    if not diff:
        return "No drift; no writes performed."
    if dry_run:
        return (
            "Drift detected; would "
            + ("update" if current else "create")
            + ". No writes performed. See drift.diff."
        )
    if confirm is None or not confirm(diff):
        raise RuntimeError("Apply cancelled; no writes performed")
    # Re-read immediately before a write to detect concurrent changes.
    if current:
        assert ruleset_id is not None
        latest = repos.get_org_ruleset(ORG, ruleset_id).json()
        if canonical(latest) != canonical(current):
            raise RuntimeError("Ruleset changed during planning; rerun dry-run")
        result = repos.update_org_ruleset(
            ORG, ruleset_id, data=cast(OrgsOrgRulesetsRulesetIdPutBodyType, config)
        ).json()
    else:
        latest_rulesets = list(
            github.rest.paginate(
                repos.get_org_rulesets,
                map_func=lambda response: response.json(),
                org=ORG,
                per_page=100,
                headers={"X-GitHub-Api-Version": API_VERSION},
            )
        )
        if any(item["name"] == NAME for item in latest_rulesets):
            raise RuntimeError("Managed name appeared during planning; rerun dry-run")
        result = repos.create_org_ruleset(
            ORG, data=cast(OrgsOrgRulesetsPostBodyType, config)
        ).json()
    (output / "applied.json").write_text(json.dumps(result, indent=2) + "\n")
    actual = repos.get_org_ruleset(ORG, result["id"]).json()
    if canonical(actual) != canonical(config):
        raise RuntimeError(
            "Read-back differs from desired policy; inspect applied.json and restore before.json if needed"
        )
    return f"Applied and verified ruleset {result['id']}. Pin this ID for subsequent runs."
