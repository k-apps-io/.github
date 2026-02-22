# Label Sync Automation

This document defines how label synchronization is executed and safely operated.

## Purpose

- Keep canonical labels consistent across target repositories.
- Detect drift in label name, color, and description.
- Support low-risk rollout with dry-run reporting before apply mode.

## Source of Truth

- Label catalog: `.github/labels/catalog.json`
- Default target repositories: `.github/labels/target-repos.txt`
- Workflow: `.github/workflows/label-sync.yml`
- Sync script: `.github/scripts/label-sync.sh`

## Execution Modes

- Scheduled run (weekly): always dry-run.
- Manual run (`workflow_dispatch`):
  - `dry_run=true` for audit-only reporting
  - `dry_run=false` to apply create/update changes
- Optional repo override:
  - Use comma-separated `owner/name` values in dispatch input `repos`
  - Leave empty to use `target-repos.txt`

## Required Token and Permissions

Set secret `ORG_LABEL_SYNC_TOKEN` in this repository.

Recommended scopes:

- `repo` for private repositories
- `public_repo` for public-only repositories
- `read:org` if needed for organization visibility checks

If `ORG_LABEL_SYNC_TOKEN` is absent, the workflow falls back to `GITHUB_TOKEN`,
which is generally insufficient for cross-repo synchronization.

## Drift Report and Audit Trail

Each run writes a markdown report at `artifacts/label-sync-report.md` and uploads
it as a workflow artifact.

The report includes:

- execution mode (dry-run/apply)
- repository-by-repository actions
- per-label action (`create`, `update`, `unchanged`, `failed`)
- overall totals

## Safe Change and Rollback Guidance

1. Always run a dry-run first against the full target repo list.
2. Review the report for unexpected updates.
3. Apply to one low-risk repository first using dispatch `repos=<single repo>`.
4. Apply to full set only after pilot success.
5. If incorrect changes are applied:
   - Revert the catalog change in a PR.
   - Re-run in apply mode to restore prior color/description values.
   - If needed, patch a specific repo label manually with `gh label edit`.

## Non-Goals

- Deleting unmanaged labels from target repositories.
- Enforcing issue transition rules (handled by guardrail automation in issue #5).
