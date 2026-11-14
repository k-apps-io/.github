# PR Ruleset MVP

Phase one of [issue #24](https://github.com/k-apps-io/.github/issues/24).
Owner: @imnotakopp.

## Policy and targeting

The canonical configuration is `.github/rulesets/pr-baseline.json`. Its `conditions.repository_name.include` list is the source of truth for repository targets in `k-apps-io`, dynamically protecting their default branches. Add or remove explicit repository names there, then review a dry-run before applying.

- Require pull requests with zero approvals. Authors may merge their own PRs.
- Block force pushes and branch deletion. No bypass actors, including administrators.
- No CODEOWNERS, latest-push, extra, or stale-review approval requirements.
- No required CI or conversation resolution in this phase.
- Squash is preferred; merge and rebase remain allowed. Repository merge settings are unchanged.

Renaming a repository out of the selector removes coverage. Other repository names and release branches are not targeted. Broader rollout, branch-name enforcement, issue linkage, and label migration are separate changes. The validator accepts a nonempty, case-insensitively unique list of explicit repository names; owners, wildcards, exclusions, and non-default branch targeting are rejected. Adding a repository requires only a configuration change, not a Python change. The zero-approval rule policy remains validated separately.

## Python project

The `kapps_governance` package lives in `src/`, with tests in `tests/`. `pyproject.toml` declares Python 3.11+, dependencies, the `governance` command, Ruff, and mypy configuration. `.python-version` selects Python 3.11 for development and CI. `uv.lock` locks the SDK, generated schemas, and development dependencies. A separate hand-maintained requirements file is unnecessary.

On macOS, install uv once with `brew install uv`. Then run these commands from the repository root:

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked python -m unittest discover -s tests -v
uv run --locked governance rulesets sync --validate-only
```

GitHubKit 0.17.1 uses the explicit REST API version `2026-03-10`. Reconciliation disables HTTP caching and automatic retries to avoid stale verification or duplicated writes. Raw JSON preserves unknown policy fields for drift detection. Credentials and API error bodies are not printed. A small factory returns the supported GitHubKit `GitHub` instance; reconciliation calls its typed methods directly. There are no custom client classes, endpoint routers, or parallel backends.

## Authentication

GitHubKit requires `GH_TOKEN` supplied securely in the environment. The organization ruleset API requires organization **Administration: write**, including for reads. The Actions workflow uses dedicated secret `ORG_RULESET_SYNC_TOKEN` and never falls back to the label token or `github.token`.

Local development also uses GitHubKit with `GH_TOKEN` supplied securely in the environment. There are no current SDK gaps requiring subprocess calls; a narrowly scoped helper can be added later only if a concrete gap appears.

See [GitHub ruleset API permissions](https://docs.github.com/en/rest/orgs/rules) and the [token rotation runbook](ruleset-token-rotation.md). Rotation is tracked in [issue #27](https://github.com/k-apps-io/.github/issues/27), due September 1, 2027.

## Command behavior

Default operation is report-only. Only the literal `--dry-run false` permits a write; `--yes` alone cannot enable writes.

```bash
# Default: read and report, using GH_TOKEN.
uv run governance rulesets sync --ruleset-id 27263218

# Explicit report-only mode using GH_TOKEN and GitHubKit.
uv run governance rulesets sync --ruleset-id 27263218 --dry-run true

# Show the planned diff and request confirmation on an interactive terminal.
uv run governance rulesets sync --ruleset-id 27263218 --dry-run false

# Explicit unattended reconciliation.
uv run governance rulesets sync --ruleset-id 27263218 --dry-run false --yes
```

Noninteractive writes without `--yes` fail before API access. Confirmation happens after the plan is prepared and before any mutation. A no-drift run writes nothing. `--validate-only` requires neither credentials nor API requests. Invalid boolean strings and the old `--apply` flag are rejected.

The existing ruleset ID must match `--ruleset-id`; missing/renamed IDs, duplicate names, and unconfirmed ownership fail. To create a genuinely new managed ruleset, omit the ID and explicitly authorize writes. Scheduled operation requires the ID variable to prevent accidental creation after a configuration mistake.

Each invocation saves a unique timestamped directory under `artifacts/ruleset-sync/` (override the parent with `--output`). Reports include mode/client, previous state, desired configuration, diff, and applied response when available. API failures exit nonzero. No unrelated rulesets, classic protections, labels, or repository settings are modified.

Before update the script rereads the managed policy, then verifies the result after writing. This detects intervening changes but cannot provide an atomic compare-and-swap; avoid simultaneous UI/local edits. Workflow concurrency serializes scheduled/manual workflow runs only.

## Monthly automation

`.github/workflows/ruleset-sync.yml` schedules reconciliation at **13:30 UTC on the first of each month** (`30 13 1 * *`): 07:30 Chicago standard time or 08:30 daylight time.

Scheduled runs explicitly use `--dry-run false --yes` and reconcile the committed policy without prompting. Manual dispatch has `dry_run` defaulting to true; select false explicitly to apply. Both run only from `main`, with locked dependencies and the pinned ruleset ID. Validation and safety checks are identical to local execution.

Configure these repository Actions settings:

- Secret `ORG_RULESET_SYNC_TOKEN`: dedicated token; confirmed present in November 2026.
- Variable `ORG_PR_BASELINE_RULESET_ID`: `27263218`.

Run summaries and timestamped snapshots are uploaded even on failure; setup failures produce a fallback report. Failures fail the job. Operators should enable GitHub Actions failure notifications. There is no automatic issue creation or additional messaging integration.

Existing rulesets enforce continuously, independent of this schedule. Configuration changes wait until the next monthly run unless manually dispatched. **Monthly reconciliation restores the committed policy after UI drift, including reactivating a ruleset disabled outside configuration.** For a sustained emergency pause, disable the Ruleset Sync workflow before rollback, or merge an explicitly approved disabled configuration; re-enable scheduling only when the intended configuration is ready.

The existing label weekly reporting and six-hour bootstrap remain unchanged until their separate migration. They do not use this Python command yet.

## Rollback

Preserve the timestamped run artifacts and verify the ruleset ID. First disable the Ruleset Sync workflow if automatic reconciliation must not undo the rollback. This does not disable the GitHub ruleset itself.

For a first installation, copy the canonical JSON, change only `enforcement` to `disabled`, and run:

```bash
uv run governance rulesets sync --config /path/to/disabled-policy.json \
  --ruleset-id 27263218 --dry-run false
```

For restoration of the approved MVP, pass the saved writable policy or canonical configuration through the same CLI. A historical configuration outside the MVP validator requires a separately reviewed exact-ID API restore. Never submit response metadata or overwrite unrelated protections. Verify read-back and effective rules before resuming the workflow. Rollback is an owner-directed operation.

## Evidence and current rollout status

The organization reported Team plan support. Pre-activation organization/repository ruleset listings were empty; both pilot `main` branches lacked classic protection. All merge methods were enabled. The original pilot activated organization ruleset `27263218`; effective rules and repeated no-op apply were verified.

Disposable tests using administrator identity `imnotakopp` without bypass verified rejected direct updates, forced rewinds, and protected-branch deletion; a self-authored PR squash-merged with no approvals. Disabling the test ruleset allowed ref restoration; restoring it blocked direct updates again. See [sanitized evidence](pr-ruleset-mvp-evidence.json). These tests verified the original policy, not the new GitHubKit client. A separate ordinary-contributor identity was not tested.

The temporary ruleset was removed. Deletion of temporary repository `k-apps-io/ruleset-mvp-test-24` was blocked by missing `delete_repo`; cleanup remains an owner task unless subsequently completed.

PR #26 was reverted by PR #28. The live ruleset was not reverted. This replacement implementation requires review and an explicitly approved merge before monthly automation becomes active on `main`. No new live mutation is implied by local validation. After merge, validate the dedicated Actions token and SDK using a manual report-only run before relying on the monthly schedule.

The owner subsequently added `ok-github` to the configured targets, applied the change locally, and reported a successful no-drift verification. This is owner-reported evidence; the original disposable tests covered the initial pilot policy.
