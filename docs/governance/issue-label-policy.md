# Issue Label Taxonomy and Lifecycle Policy

This policy defines the canonical issue label system for repositories in `@k-apps-io`.

## Goals

- Provide a consistent planning and execution signal across repositories.
- Keep label semantics machine-friendly for automation and reporting.
- Minimize ambiguity in issue state transitions.

## Canonical Label Groups

### `status/*` (single-select, required)

Exactly one `status/*` label must be present on every active issue.

| Label | Color | Description |
| --- | --- | --- |
| `status/backlog` | `C5DEF5` | Planned work not started. |
| `status/in-progress` | `FBCA04` | Actively being executed. |
| `status/review` | `0E8A16` | Implementation complete and under review. |
| `status/blocked` | `B60205` | Cannot proceed due to an external dependency. |
| `status/done` | `1D76DB` | Completed and accepted. |

### `priority/*` (single-select, required)

Exactly one `priority/*` label must be present.

| Label | Color | Description |
| --- | --- | --- |
| `priority/p0` | `7A0000` | Critical work requiring immediate attention. |
| `priority/p1` | `B60205` | High priority for current milestone. |
| `priority/p2` | `D93F0B` | Medium priority after prerequisites. |
| `priority/p3` | `FBCA04` | Lower priority and deferrable. |

### `type/*` (single-select, required)

Exactly one `type/*` label must be present.

| Label | Color | Description |
| --- | --- | --- |
| `type/bug` | `D73A4A` | Defect affecting expected behavior. |
| `type/feature` | `A2EEEF` | New product or platform capability. |
| `type/ops` | `0E8A16` | Operational, governance, or maintenance work. |
| `type/initiative` | `1D76DB` | Multi-repo or program-level work. |

### `work/*` (multi-select, optional)

`work/*` labels are thematic slices and may be combined.

| Label | Color | Description |
| --- | --- | --- |
| `work/governance` | `5319E7` | Governance standards and controls. |
| `work/automation` | `0052CC` | Workflows and repository automation. |
| `work/docs` | `0075CA` | Documentation deliverables and maintenance. |

### Integration labels (optional)

These labels support platform tooling that expects exact names.

| Label | Color | Description |
| --- | --- | --- |
| `dependabot` | `1F6FEB` | Automated dependency update pull requests from Dependabot. |
| `dependencies` | `0366D6` | Changes to project dependencies or dependency tooling. |

## Selection Rules

- `status/*`: single-select, required.
- `priority/*`: single-select, required.
- `type/*`: single-select, required.
- `work/*`: multi-select, optional.
- A label outside this policy may exist only when approved through governance change control.

## Lifecycle and Transition Model

Primary flow:

1. `status/backlog`
2. `status/in-progress`
3. `status/review`
4. `status/done`

Blocked path:

- `status/in-progress` or `status/review` -> `status/blocked`
- `status/blocked` -> `status/in-progress` when blocker is resolved

Invalid transitions:

- `status/backlog` -> `status/done` (must pass through implementation/review)
- `status/review` -> `status/backlog` (use `status/in-progress` if rework is needed)
- Multiple `status/*` labels at once

Automation behavior expectations:

- On invalid combinations, automation should remove conflicting status labels and keep one authoritative value.
- On invalid transitions, automation should comment with corrective guidance and link to this policy.

## Naming, Color, and Description Standards

- Format labels as lowercase `group/value`.
- Keep values concise, stable, and automation-friendly (no spaces).
- Colors are six-character uppercase hex codes.
- Descriptions must define intent, not implementation details.
- Do not overload one label with multiple meanings.

## Governance Process for Label Changes

1. Open a policy-change issue in `k-apps-io/.github` with rationale, impact, and migration plan.
2. Submit a PR updating this policy (and related automation config if applicable).
3. Require CODEOWNERS approval before merge.
4. Run a dry-run sync across target repos before applying changes broadly.
5. Announce change window and migration result in linked issues.

## Migration and Backfill Guidance

Use GitHub CLI for deterministic rollout.

### 1) Ensure canonical labels exist in one repository

```bash
gh label create status/backlog --repo k-apps-io/<repo> --color C5DEF5 --description "Planned work not started."
gh label create status/in-progress --repo k-apps-io/<repo> --color FBCA04 --description "Actively being executed."
gh label create status/review --repo k-apps-io/<repo> --color 0E8A16 --description "Implementation complete and under review."
gh label create status/blocked --repo k-apps-io/<repo> --color B60205 --description "Cannot proceed due to an external dependency."
gh label create status/done --repo k-apps-io/<repo> --color 1D76DB --description "Completed and accepted."
```

### 2) Normalize legacy labels

```bash
gh label edit "in progress" --repo k-apps-io/<repo> --name status/in-progress --color FBCA04 --description "Actively being executed."
gh label edit "todo" --repo k-apps-io/<repo> --name status/backlog --color C5DEF5 --description "Planned work not started."
```

### 3) Backfill issue status labels

```bash
gh issue list --repo k-apps-io/<repo> --state open --limit 500 --json number,labels \
| jq -r '.[] | select(([.labels[].name] | map(startswith("status/")) | any) | not) | .number' \
| xargs -I{} gh issue edit {} --repo k-apps-io/<repo> --add-label status/backlog
```

### 4) Remove conflicting status labels (manual fallback)

```bash
gh issue edit <issue-number> --repo k-apps-io/<repo> \
  --remove-label status/backlog \
  --remove-label status/in-progress \
  --remove-label status/review \
  --remove-label status/blocked \
  --remove-label status/done \
  --add-label status/in-progress
```
