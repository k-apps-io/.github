# PR Ruleset MVP

Phase one of [issue #24](https://github.com/k-apps-io/.github/issues/24).
Owner: @imnotakopp. The owner approved this MVP in the implementation conversation on November 14, 2026.

## Approved policy

- Target only `ok-agent-ts` and `ok-agent-openai-ts`, matching their default branches dynamically.
- Require pull requests with zero required approvals. The author may merge their own PR.
- Block force pushes and protected branch deletion, including for administrators.
- No bypass actors, CODEOWNERS approvals, stale-approval dismissal, latest-push approval, or required conversation resolution.
- No required CI checks in this phase. Existing CI continues independently.
- Squash merging remains preferred. All existing merge methods remain allowed; repository merge settings are untouched.
- No release-branch targeting, branch-name enforcement, issue-link enforcement, or organization-wide rollout.

The name-based selector covers only the two exact names. Renaming a repository out of the selector removes coverage; repository renames are not blocked by this MVP. Newly created repositories with other names are not covered. Broader targeting and a disposable matching-repository test remain later phases of #24.

Approvals can be added later through a reviewed configuration and validator change. No bypass is needed to merge an author's own PR when the required approval count is zero.

## Discovery evidence

Read-only API inspection on November 14, 2026 found:

| Item | Observation |
| --- | --- |
| Organization | `k-apps-io`, Team plan reported by organization API |
| Local CLI identity | `imnotakopp`; admin permission on both pilot repositories |
| Default branches | `main` on both repositories |
| Repository ruleset listings | Empty for both repositories |
| Classic branch protections | Both `main` endpoints returned `Branch not protected` |
| Merge methods | Squash, merge commit, and rebase enabled on both |
| `ok-agent-ts` workflows | CI, Dependabot Auto Merge, Dependabot Updates |
| `ok-agent-openai-ts` workflows | CodeQL, Quality, Test |
| Organization inventory | After scope refresh, organization ruleset listing was empty before activation |

Empty repository listings do not establish a complete organization-wide audit. Organization rulesets and classic branch protection can layer; inspect all applicable protections before activation. Reviewer capacity and check contexts need no enforcement decisions in this MVP because neither is required.

## Authentication

Local operation uses the authenticated `gh` CLI. The organization ruleset API requires organization Administration write permission even for listing rulesets. The current classic OAuth credential needs `admin:org`, obtained interactively with:

```bash
gh auth refresh -h github.com -s admin:org
```

For Actions, configure a dedicated `ORG_RULESET_SYNC_TOKEN` secret with organization Administration write permission and access to this organization. Prefer an appropriately scoped fine-grained credential. Do not reuse the label-sync token or fall back to `github.token`. No token values belong in configuration, logs, or reports.

Reference: [GitHub organization rules API](https://docs.github.com/en/rest/orgs/rules).

## Reconciliation

Configuration: `.github/rulesets/pr-baseline.json`.
The script is deliberately limited to this MVP. Expanding targeting or review policy requires a corresponding reviewed validator change.

```bash
python3 .github/scripts/ruleset-sync.py --validate-only
python3 -m unittest discover -s .github/scripts/tests -v
python3 .github/scripts/ruleset-sync.py
```

Dry-run is the default and performs only GET requests. Artifacts contain the previous ruleset, desired policy, unified diff, and summary. A missing managed ruleset is reported as a proposed create. API failures exit nonzero and produce a failure summary; they are never interpreted as an empty ruleset list.

After reviewing the dry-run and completing the protection audit:

```bash
python3 .github/scripts/ruleset-sync.py --apply
```

Record the returned ruleset ID. Set repository Actions variable `ORG_PR_BASELINE_RULESET_ID` to that ID. Every subsequent run must supply it locally:

```bash
python3 .github/scripts/ruleset-sync.py --ruleset-id RULESET_ID
python3 .github/scripts/ruleset-sync.py --ruleset-id RULESET_ID --apply
```

An existing same-name ruleset without the matching explicit ID causes a failure instead of automatic adoption. A missing or renamed pinned ruleset also fails. Duplicate names are rejected. Only this managed ruleset is created or updated; the script never deletes rulesets or changes classic protections or repository settings.

An unchanged policy produces no write. A changed policy is reread before update and verified after apply. GitHub does not provide an atomic compare-and-swap through this script: avoid simultaneous local/UI changes. The workflow serializes its own runs. Retain each run's artifacts separately; local output defaults to a reusable directory, so use `--output artifacts/ruleset-sync-RUN` for audit retention.

## Workflow

`Ruleset Sync` runs weekly in report-only mode and supports manual dispatch with `apply` defaulting to false. Apply is restricted to the default `main` ref. Scheduled drift is reported in the summary and `drift.diff`; operational failures fail the job. Artifacts upload even on failure. Someone must review drift reports; this workflow does not remediate automatically.

Before enabling scheduled operation, configure the dedicated secret and pinned ruleset ID. Until authentication is configured, runs fail explicitly rather than silently skipping protection management. `Ruleset Tests` validates the configuration and exercises reconciliation on PRs without organization credentials.

## Pilot verification and completion record

Do not mark enforcement verified based only on a successful API write.

- [x] Audit existing organization rulesets and effective rules for both pilot default branches.
- [x] Save pre-change snapshots and the approved dry-run diff.
- [x] Activate the ruleset and record its ID and apply artifact.
- [x] Verify effective rules include PR, deletion, and non-fast-forward protections on both branches.
- [ ] Verify an ordinary contributor's direct push is rejected.
- [ ] Verify force push and branch deletion are rejected using an approved disposable test setup. Do not test potentially destructive operations against live `main` without a recovery plan.
- [ ] Verify a legitimate PR authored by @imnotakopp merges with zero approvals.
- [x] Run apply again and confirm zero updates.
- [ ] Verify rollback and restoration in the approved test setup.
- [ ] Record evidence and remaining limitations in the implementation PR.

Bypass-path testing is not applicable: no bypass actors exist. Automation must use PRs; existing auto-merge behavior should be checked during the pilot. Destructive tests and new test repositories require an explicitly selected disposable setup. Until the checklist is complete, this is prepared enforcement, not a completed rollout.

## Rollback

Preserve `before.json` and the applied ID before further changes. For an existing managed ruleset, extract only writable fields from the saved snapshot and PUT them back to the same ID with `gh api --method PUT --input FILE`. Inspect and verify the restored ruleset; do not restore unrelated rulesets.

For first installation (`before.json` is null), create a copy of the canonical configuration with `enforcement` set to `disabled`, then run the reconciler with that config, the pinned ID, and `--apply`. This disables only the new managed ruleset without deleting it. Run the default configuration to restore active enforcement after resolving the problem.

Rollback changes protection and must be directed by the owner. Confirm the intended ID and snapshot before execution. Scheduled runs only report drift and will not undo a rollback.

## Activation evidence

On November 14, 2026, ruleset `27263218` was activated and its API read-back verified. Both pilot `main` effective-rules endpoints returned deletion, non-fast-forward, and zero-approval pull-request requirements from that organization ruleset. A repeated apply reported `No drift; no writes performed.` Repository variable `ORG_PR_BASELINE_RULESET_ID` is set to `27263218`.

GitHub initially added `required_reviewers: []` and `require_extra_approval_for_unattributed_changes: true` to the response. Verification correctly detected the mismatch. The canonical configuration now explicitly specifies no required reviewers and disables the extra approval option; the subsequent apply and read-back matched exactly.

Local artifacts are under `artifacts/ruleset-mvp-preflight`, `artifacts/ruleset-mvp-activation`, `artifacts/ruleset-mvp-explicit-defaults`, and `artifacts/ruleset-mvp-idempotence` (git-ignored). The initial snapshot was null because no managed ruleset existed. These local artifacts are not uploaded by this operation.

Live push rejection, author-PR merge, and rollback exercises remain unperformed. The dedicated Actions secret must still be provisioned; local CLI authorization does not provision an Actions credential. The workflow must be merged before scheduled drift reporting is operational.
