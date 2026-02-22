# Status Guardrails Automation

This automation enforces `status/*` label integrity on GitHub issues.

## Scope

- Enforce exactly one active `status/*` label on open issues.
- Apply `status/backlog` automatically when status labels are missing.
- Resolve multi-status conflicts by keeping one authoritative status.
- Validate status transitions against the canonical lifecycle policy.
- Comment with guidance when corrections are applied.

Workflow file:

- `.github/workflows/status-guardrails.yml`

Script:

- `.github/scripts/status-guardrails.sh`

## Triggering Events

The workflow runs on issue events:

- `opened`
- `reopened`
- `labeled`
- `unlabeled`

## Transition Rules

Allowed transitions:

- `status/backlog -> status/in-progress`
- `status/in-progress -> status/review`
- `status/in-progress -> status/blocked`
- `status/review -> status/done`
- `status/review -> status/in-progress`
- `status/review -> status/blocked`
- `status/blocked -> status/in-progress`

Disallowed transitions are reverted when deterministically detectable.

## Conflict Resolution

When multiple status labels are present:

1. If the current event added a `status/*` label, that label is treated as the candidate.
2. If transition validation fails, candidate is reverted to the previous status.
3. Any extra `status/*` labels are removed.
4. The workflow comments with the correction outcome.

## Exception Handling

Maintainer/admin bypass is enabled by default:

- If actor permission is `admin` or `maintain`, strict enforcement is skipped.
- This supports emergency/manual intervention scenarios.

Bypass can be disabled by setting `MAINTAINER_BYPASS` to `false` in the workflow.

## Edge Cases

- Closed issues are ignored.
- If status history cannot be inferred, the workflow still enforces one active status
  and comments guidance when corrections are made.
- Adding `status/done` closes the issue.

## Related Policy

Canonical policy source:

- `docs/governance/issue-label-policy.md`
