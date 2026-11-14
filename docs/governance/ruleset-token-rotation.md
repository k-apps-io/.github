# Ruleset automation token rotation

Owner: @imnotakopp. Repository: `k-apps-io/.github`.
Secret: `ORG_RULESET_SYNC_TOKEN` (repository Actions secret).

## Schedule

The owner provisioned the current fine-grained personal access token on November 14, 2026 with a one-year expiration. Verify the exact expiration in GitHub token settings; it cannot be inferred from the Actions secret metadata.

Rotate by **September 1, 2027**, tracked in [issue #27](https://github.com/k-apps-io/.github/issues/27) and its dated milestone. This provides a buffer before expected November 2027 expiration. A milestone records a due date; it does not create an automated reminder or rotate the token.

## Required access

Create a dedicated fine-grained personal access token with:

- Resource owner: `k-apps-io`.
- Organization permissions: **Administration — Read and write**.
- Repository permissions: no additional permissions beyond GitHub's mandatory defaults.
- Repository access: the minimum selection; private repository access is unnecessary for the organization ruleset endpoints used by this reconciler.
- Expiration: explicitly set and record the date; follow the owner's approved lifetime.

Repository selection does not restrict the organization-level rulesets this permission can administer. The version-controlled configuration determines the pilot targeting. Workflow checkout uses its separate built-in `GITHUB_TOKEN`.

See [GitHub organization rules API permissions](https://docs.github.com/en/rest/orgs/rules) and [managing personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

## Rotate

1. Open GitHub Settings, Developer settings, Personal access tokens, Fine-grained tokens. Identify the current dedicated token and confirm its exact expiration.
2. Create a replacement with the permissions above. Complete organization approval if required. Keep the old token valid until verification succeeds, unless it has been compromised.
3. Copy the replacement value directly into the existing `ORG_RULESET_SYNC_TOKEN` secret at [repository Actions secrets](https://github.com/k-apps-io/.github/settings/secrets/actions). Use **Update**, keeping the same secret name. Do not put token values in issues, PRs, shell arguments, logs, or this document.
4. Alternatively, use the CLI's interactive secret prompt; paste the value only into the prompt:

   ```bash
   gh secret set ORG_RULESET_SYNC_TOKEN --repo k-apps-io/.github
   ```

5. Verify the token through the workflow as described below.
6. After successful verification, revoke the previous token in GitHub token settings. Changing an Actions secret does not revoke the old token.
7. Record the rotation date, replacement expiration, successful workflow run URL, and old-token revocation in the tracking issue. Do not record the token value.
8. Create the next rotation issue with a dated milestone before the new expiration, preserving a similar buffer. Close the current rotation issue only after validation and revocation are complete.

## Verify without modifying protections

The `Ruleset Sync` workflow must already be merged into `main`. Confirm repository variable `ORG_PR_BASELINE_RULESET_ID` remains `27263218`.

```bash
gh workflow run ruleset-sync.yml --repo k-apps-io/.github --ref main -f apply=false
gh run list --repo k-apps-io/.github --workflow ruleset-sync.yml --event workflow_dispatch --limit 5
```

Select the run triggered by your dispatch and inspect it:

```bash
gh run watch RUN_ID --repo k-apps-io/.github --exit-status
gh run view RUN_ID --repo k-apps-io/.github
```

Require a successful run with no authentication, authorization, approval, or expiration errors. Read the summary and artifact: normally it reports `No drift; no writes performed.` If drift is reported, review it separately; do not turn on apply just to validate a token. This test must remain report-only.

Local `gh auth status` does not validate the Actions secret. A secret-name listing confirms only that the secret exists, not that its value works.

## Failure and recovery

If verification fails, inspect the failure report and confirm resource owner, organization approval, Administration write permission, and expiration. Do not revoke the old token until the replacement succeeds.

GitHub cannot show the stored Actions secret value. Restore the previous value only if it is still available through an approved secure store; otherwise create a corrected replacement. Do not regenerate or invalidate the old token first if uninterrupted operation is required.

If the token expires, scheduled reporting and manual reconciliation fail, but the already active GitHub ruleset continues enforcing its policy. Replace the token and rerun report-only verification; no ruleset rollback is needed for credential rotation.
