# k-apps-io/.github

This repository defines organization-level GitHub governance defaults for `@k-apps-io`.

## Purpose

- Centralize baseline governance files and contribution standards.
- Provide default issue and pull request templates for repositories in the organization.
- Host lightweight quality checks for governance documentation and templates.

## Ownership Model

- Primary maintainers: platform/governance maintainers listed in `CODEOWNERS`.
- Governance changes require review from code owners.
- Security-sensitive updates follow `SECURITY.md`.

## Contribution Flow

1. Open or reference a tracking issue describing scope and acceptance criteria.
2. Create a focused branch and submit a pull request.
3. Ensure CI checks pass before merge.
4. Merge only after required reviews are complete.

## Repository Layout

- `CODEOWNERS`: review ownership for governance artifacts.
- `CONTRIBUTING.md`: standards for contributing changes.
- `SECURITY.md`: process for reporting and handling vulnerabilities.
- `docs/governance/`: canonical governance policies, including issue label lifecycle rules.
- `.github/labels/`: machine-readable label catalog and default target repository list.
- `.github/scripts/label-sync.sh`: label drift detection and sync runner.
- `.github/workflows/repo-governance-bootstrap.yml`: scheduled org repo auto-discovery and governance label bootstrap.
- `.github/scripts/status-guardrails.sh`: status transition and conflict enforcement.
- `docs/governance/org-rollout-plan.md`: rollout waves, owners, metrics, and timelines.
- `docs/governance/template-adoption-and-overrides.md`: template precedence and override rules.
- `.github/ISSUE_TEMPLATE/`: baseline issue templates.
- `.github/pull_request_template.md`: default PR checklist.
- `.github/workflows/`: CI workflows for markdown and link validation.
