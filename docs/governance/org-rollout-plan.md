# Org Governance Rollout Plan

Issue reference: `#6`

Last updated: 2026-02-22 (UTC)

## Objective

Adopt `.github` governance artifacts and issue lifecycle standards across
`@k-apps-io` repositories with measurable rollout quality and explicit ownership.

## Inputs and Dependencies

- Policy baseline: `docs/governance/issue-label-policy.md`
- Label sync automation: `.github/workflows/label-sync.yml`
- Status guardrails automation: `.github/workflows/status-guardrails.yml`
- Inventory source: `docs/governance/repo-inventory.csv`

## Repository Inventory Snapshot

- Total repositories inventoried: 49
- Wave 1 candidates (`active repo`): 18
- Wave 2 candidates (`moderate activity`): 12
- Wave 3 candidates (`legacy or low activity`): 16
- Wave 3 blocked (`missing default branch`): 3

Readiness classification is derived from last update date and default branch
presence in `docs/governance/repo-inventory.csv`.

## Rollout Waves

| Wave | Window (UTC) | Owner | Scope | Follow-up Issue |
| --- | --- | --- | --- | --- |
| Wave 1 | 2026-02-23 to 2026-03-01 | `@imnotakopp` | Active repositories with recent delivery activity | #10 |
| Wave 2 | 2026-03-02 to 2026-03-12 | `@imnotakopp` | Moderate-activity repositories | #11 |
| Wave 3 | 2026-03-13 to 2026-03-25 | `@imnotakopp` | Legacy/blocked repositories and disposition decisions | #12 |
| Alignment | 2026-02-23 to 2026-03-07 | `@imnotakopp` | `agent-skills` issue-guidance alignment | #13 |

## Execution Checklist Per Wave

1. Confirm repository owner and adoption readiness.
2. Run label sync in dry-run mode and review drift report.
3. Apply label sync in scoped mode (`repos=<owner/name>`).
4. Verify issue status guardrails behavior on test issue transitions.
5. Log completion evidence and exceptions in the wave issue.

## Success Metrics

- Adoption coverage:
  - Wave 1: at least 90% of candidate repos migrated by 2026-03-01.
  - Wave 2: at least 85% of candidate repos migrated by 2026-03-12.
  - Wave 3: 100% of repos dispositioned (migrated, deferred, or archived) by
    2026-03-25.
- Drift control:
  - Post-migration repos should show 0 critical label drift items in dry-run
    reports for two consecutive weekly runs.
- Guardrail reliability:
  - 0 unresolved multi-status conflicts in migrated repositories after rollout.

## Monitoring and Reporting

- Weekly dry-run artifact from `.github/workflows/label-sync.yml` is the primary
  drift-monitoring signal.
- Wave owners post summary updates on #10, #11, #12, and #13 at least every
  3 business days.
- Issue #6 remains the executive roll-up with links to all wave updates.

## Risks and Mitigations

- Missing default branches:
  - Mitigation: treat as Wave 3 blocked; assign unblock task before migration.
- Repo ownership ambiguity:
  - Mitigation: require owner confirmation in wave issue before apply mode.
- Automation permission gaps:
  - Mitigation: validate token scopes before each wave start.
- Unexpected label churn:
  - Mitigation: dry-run first, then pilot apply on one repo per wave.

## Exit Criteria for #6

- Wave follow-up issues #10, #11, #12, and #13 are all closed.
- Final inventory disposition is recorded in `docs/governance/repo-inventory.csv`.
- A closing summary comment on #6 includes adoption percentages, exception list,
  and links to the final wave reports.
