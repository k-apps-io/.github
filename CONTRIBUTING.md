# Contributing

Thank you for contributing to projects maintained by `@k-apps-io`.

This document defines the organization-wide standards for planning, implementing, reviewing, and merging changes.

These standards apply to both human contributors and autonomous development agents.

Repository-specific documentation may establish additional requirements, provided they do not conflict with organization-wide governance policies.

## 1. Development Workflow

All changes must follow an issue-driven, pull-request-based workflow.

The standard development lifecycle is:

Issue → Triage → Branch → Implementation → Pull Request → Review → Merge

### Requirements

- All planned changes must be associated with a GitHub issue.
- Issues must define clear scope and acceptance criteria before implementation begins.
- Changes must be implemented on a dedicated branch.
- Direct commits to protected branches, including `main`, are prohibited.
- All changes must be integrated through pull requests.
- Pull requests must pass required validation and satisfy applicable review requirements before merging.
- Work should remain focused on the associated issue and its acceptance criteria.

Exceptions for emergency changes must follow an explicitly authorized procedure and should preserve the PR and review process whenever feasible.

## 2. Issues and Work Classification

GitHub issues are the authoritative source for tracking planned work.

### Issue Templates

Use the appropriate issue template when creating new work:

- **Bug Report:** Defects or incorrect existing behavior.
- **Feature Request:** New capabilities or extensions to existing functionality.
- **Governance Task:** Organization policies, standards, and governance automation.

Repository-specific issue templates may be used when additional information is required.

Issues must document sufficient context for another contributor or development agent to independently understand and execute the work.

### Issue Requirements

Before implementation begins, confirm:

- The problem or objective is clearly described.
- Scope and non-goals are identified where applicable.
- Acceptance criteria are concrete and verifiable.
- Relevant dependencies and constraints are documented.
- Appropriate classification, priority, and status labels are assigned.

For defects, include reproduction steps, expected behavior, and actual behavior when applicable.

### Label Standards

Follow the canonical [Issue Label Taxonomy and Lifecycle Policy](https://github.com/k-apps-io/.github/blob/main/docs/governance/issue-label-policy.md).

Every active issue must have exactly one label from each required group:

- `type/*` — Classification of the work.
- `priority/*` — Relative urgency.
- `status/*` — Current lifecycle state.

Optional `work/*` labels identify additional areas of responsibility.

Do not create new label conventions or modify canonical label definitions without following the organization's governance change process.

## 3. Git Branching Workflow

The organization follows a lightweight, trunk-based development strategy.

The repository's default branch, normally `main`, is the primary integration branch.

All development must occur on short-lived branches.

### Branch Naming

Branches must use the following naming convention:

`<type>/<issue-number>-<short-description>`

Supported branch types:

| Prefix      | Purpose                                                    |
| ----------- | ---------------------------------------------------------- |
| `feat/`     | New functionality or capabilities                          |
| `fix/`      | Defect corrections                                         |
| `refactor/` | Internal restructuring without intended behavioral changes |
| `chore/`    | Maintenance and operational updates                        |
| `docs/`     | Documentation changes                                      |
| `test/`     | Test coverage and testing infrastructure                   |
| `ci/`       | Continuous integration and delivery changes                |

Examples:

- `feat/123-add-shell-tool`
- `fix/124-handle-session-timeout`
- `refactor/125-simplify-agent-dispatch`
- `chore/126-update-dependencies`
- `docs/127-update-contribution-guide`
- `test/128-add-coordinator-coverage`
- `ci/129-improve-build-validation`

Branch names must:

- Use lowercase letters, numbers, and hyphens.
- Include the originating issue number.
- Use a concise, descriptive identifier.
- Avoid spaces and unnecessarily long descriptions.

The branch prefix describes the primary nature of the implementation and does not replace the issue's canonical `type/*` classification.

### Branch Lifecycle

1. Create a branch from the latest target integration branch.
2. Implement changes addressing the linked issue.
3. Keep commits and modifications relevant to the issue.
4. Incorporate upstream changes when necessary.
5. Open a pull request targeting the integration branch.
6. Merge only after required validations and reviews are satisfied.
7. Delete the development branch after a successful merge unless there is a documented reason to retain it.

Long-lived feature branches are discouraged.

Do not force-push shared or protected branches.

## 4. Implementation Standards

Contributions should prioritize correctness, maintainability, compatibility, and appropriately scoped changes.

### Scope

- Implement only changes necessary to satisfy the associated issue.
- Avoid unrelated refactoring and formatting-only changes.
- Prefer incremental changes over unnecessarily large modifications.
- Document newly discovered work separately when it falls outside the issue's scope.

### Code Organization

- Follow the existing repository architecture and directory conventions.
- Place functionality within the appropriate existing module or abstraction.
- Prefer existing shared utilities over introducing duplicated implementations.
- Avoid adding generic abstractions without a demonstrated need.
- Respect established boundaries between modules and components.

Repository-specific implementation guidance belongs in the repository's documentation.

### Compatibility

Preserve backward compatibility where reasonably possible.

Changes to public interfaces, shared contracts, configuration formats, or established behavior must identify potential compatibility impacts.

Breaking changes must be explicitly documented and reviewed.

### Dependencies

New or updated dependencies must have a clear justification.

Avoid introducing dependencies when existing project capabilities adequately address the requirement.

## 5. Testing and Validation

All changes must be validated before they are considered complete.

Contributors must:

- Execute applicable tests covering modified functionality.
- Add or update tests when introducing behavior or correcting defects.
- Run required linting, formatting, and type-checking checks.
- Verify that existing functionality remains operational.
- Report validation failures or limitations in the pull request.

A bug fix should include regression coverage when practical.

Validation requirements and commands may differ between repositories and should be documented locally.

Do not bypass tests, suppress errors, or disable quality checks solely to obtain passing CI results.

## 6. Pull Requests

Pull requests are the required mechanism for integrating changes into protected branches.

### Creating a Pull Request

Every pull request must:

- Reference its originating GitHub issue.
- Use the organization's default pull request template or an approved repository-specific template.
- Explain what changed and why.
- Identify relevant scope and exclusions.
- Describe validation performed.
- Document potential risks and rollback considerations.
- Include documentation updates when applicable.

Keep pull requests focused on one logically scoped change.

Large initiatives should be divided into independently reviewable work whenever practical.

### Draft Pull Requests

Draft pull requests may be opened before implementation is complete.

They may be used to share progress, obtain early feedback, or enable preliminary CI validation.

A draft pull request does not indicate that implementation is ready for final review.

### Review Requirements

Before merging:

- Required CI checks must pass.
- Required reviewers must approve the change.
- CODEOWNERS requirements must be satisfied where configured.
- Blocking review feedback must be addressed.
- Required review conversations must be resolved.
- The pull request must be mergeable into its target branch.

Contributors must not approve their own changes as a substitute for independent review.

### Merge Requirements

All changes to protected branches must be merged through GitHub pull requests.

Direct pushes and direct commits to protected branches are prohibited.

**Squash merging is the preferred merge strategy** for ordinary development work.

A different merge strategy may be used when explicitly required by the repository's release or version-management process.

After merging:

1. Confirm the change was successfully integrated.
2. Confirm the originating issue's acceptance criteria are satisfied.
3. Transition the issue to `status/done`.
4. Close the issue when the work is accepted.
5. Remove the merged development branch when appropriate.

## 7. Issue Lifecycle

Follow the [Issue Label Taxonomy and Lifecycle Policy](https://github.com/k-apps-io/.github/blob/main/docs/governance/issue-label-policy.md).

The standard lifecycle is:

`status/backlog → status/in-progress → status/review → status/done`

### Status Definitions

- `status/backlog`: Work is planned but implementation has not started.
- `status/in-progress`: Implementation or requested rework is underway.
- `status/review`: Implementation is complete and awaiting review or acceptance.
- `status/blocked`: Progress is prevented by an external dependency.
- `status/done`: Work is completed and accepted.

Status changes must reflect actual progress.

- When implementation starts, transition the issue to `status/in-progress`.
- When implementation and applicable validation are complete and the pull request is ready for review, transition the issue to `status/review`.
- Opening a draft pull request alone does not move the issue to `status/review`.
- If an external dependency blocks implementation or review, transition to `status/blocked`; return to `status/in-progress` when the blocker is resolved.

Do not mark an issue complete merely because a pull request was opened or implementation was reported finished.

If review identifies required changes, return the issue to `status/in-progress`.

Do not assign multiple `status/*` labels to the same issue.

## 8. Documentation

Documentation must remain consistent with implemented behavior and established organizational policies.

Contributors should:

- Update relevant documentation when functionality or contracts change.
- Keep examples executable or otherwise verifiable where practical.
- Prefer clear and deterministic language.
- Avoid duplicating authoritative policies across repositories.
- Link to canonical organization-wide standards when appropriate.

Repository-specific architecture and implementation details should remain within the relevant project.

Changes affecting organization-wide governance must be made through the established governance process.

## 9. Autonomous Development Agents

Autonomous development agents are subject to the same contribution requirements as human developers.

Agents must:

- Read applicable repository instructions before making changes.
- Respect issue scope and acceptance criteria.
- Follow established branch naming and PR requirements.
- Validate changes before reporting implementation complete.
- Accurately report completed work and validation results.
- Avoid unrelated changes or unauthorized modifications.
- Respect repository review and merge permissions.

Repository-specific `AGENTS.md` files may define additional operating instructions.

Agent instructions do not override organization-wide contribution policies, security requirements, or protected-branch rules.

## 10. Governance and Exceptions

The `k-apps-io/.github` repository maintains the organization's shared contribution standards, issue templates, labels, and governance automation.

Changes to these standards must follow the established governance review process.

### Ownership and Escalation

- **Owner:** @imnotakopp is the designated owner of the organization's contribution and governance standards.
- **Questions and escalations:** Mention @imnotakopp in the relevant issue or pull request when a problem, clarification, a policy decision, an exception, or escalation requires direction.
- Do not make unilateral decisions on unresolved governance questions; document the concern and mention @imnotakopp for direction.

For security-sensitive concerns, follow the private reporting process in [SECURITY.md](https://github.com/k-apps-io/.github/blob/main/SECURITY.md).

### Policy Changes and Exceptions

Organization-wide policy changes should consider:

- Compatibility with existing repositories.
- Effects on automated workflows and development agents.
- Required migration or adoption steps.
- Rollback procedures.

Emergency security disclosures must follow [SECURITY.md](https://github.com/k-apps-io/.github/blob/main/SECURITY.md), rather than public issue reporting.

Repository-specific requirements may strengthen these standards but must not silently weaken mandatory organizational protections.

Exceptions require explicit authorization from the responsible maintainers.

---

## Related Documentation

- [Issue Label Taxonomy and Lifecycle Policy](https://github.com/k-apps-io/.github/blob/main/docs/governance/issue-label-policy.md)
- [Template Adoption and Override Rules](https://github.com/k-apps-io/.github/blob/main/docs/governance/template-adoption-and-overrides.md)
- [Pull Request Template](https://github.com/k-apps-io/.github/blob/main/.github/pull_request_template.md)
- [Security Policy](https://github.com/k-apps-io/.github/blob/main/SECURITY.md)
