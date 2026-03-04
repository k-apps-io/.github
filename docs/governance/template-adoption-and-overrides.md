# Template Adoption and Override Rules

This document explains how repositories in `@k-apps-io` adopt or override
organization defaults from `k-apps-io/.github`.

## Org Default Templates

Default templates provided by this repository:

- `.github/ISSUE_TEMPLATE/bug.yml`
- `.github/ISSUE_TEMPLATE/feature.yml`
- `.github/ISSUE_TEMPLATE/governance-task.yml`
- `.github/pull_request_template.md`

## Resolution and Precedence

GitHub resolves templates with this precedence:

1. Repository-local templates in `<target-repo>/.github/`
2. Organization-level defaults in `k-apps-io/.github`

Practical result:

- If a target repository defines its own issue forms or PR template, the repo
  local files take precedence.
- If a target repository has no local template for a type, org defaults apply.

## Adoption (Recommended Default Path)

For repositories that should inherit org defaults:

1. Do not add local duplicates of these files:
   - `<target-repo>/.github/ISSUE_TEMPLATE/bug.yml`
   - `<target-repo>/.github/ISSUE_TEMPLATE/feature.yml`
   - `<target-repo>/.github/pull_request_template.md`
2. Keep org-level templates current in `k-apps-io/.github`.
3. Verify template availability in the target repository issue/PR UI.

## Override (When Repo-Specific Customization Is Needed)

Allowed override pattern:

1. Copy the org default file into the target repo:
   - `k-apps-io/.github/.github/ISSUE_TEMPLATE/bug.yml` ->
     `<target-repo>/.github/ISSUE_TEMPLATE/bug.yml`
2. Keep the canonical labels in defaults:
   - `type/*`, `status/backlog`, and `priority/*`
3. Add only repo-specific fields required by that repository.
4. Document why the override exists in target repo `README` or `CONTRIBUTING`.

## Validation Checklist

- New issues created from `bug` and `feature` forms apply default labels.
- PR template appears when opening pull requests.
- Required metadata fields are present in created issues.
- Overrides remain compatible with org label taxonomy.
