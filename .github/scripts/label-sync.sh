#!/usr/bin/env bash
set -euo pipefail

CATALOG_PATH="${CATALOG_PATH:-.github/labels/catalog.json}"
REPO_LIST_PATH="${REPO_LIST_PATH:-.github/labels/target-repos.txt}"
REPOS_OVERRIDE="${REPOS_OVERRIDE:-}"
AUTO_DISCOVER_REPOS="${AUTO_DISCOVER_REPOS:-false}"
ORG_NAME="${ORG_NAME:-}"
ORG_REPO_LIMIT="${ORG_REPO_LIMIT:-200}"
DRY_RUN="${DRY_RUN:-true}"
REPORT_PATH="${REPORT_PATH:-artifacts/label-sync-report.md}"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

bool_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

require_cmd gh
require_cmd jq

if [[ ! -f "$CATALOG_PATH" ]]; then
  echo "Catalog file not found: $CATALOG_PATH" >&2
  exit 1
fi

if [[ "$(bool_lower "$AUTO_DISCOVER_REPOS")" != "true" && ! -f "$REPO_LIST_PATH" && -z "$REPOS_OVERRIDE" ]]; then
  echo "Repo list file not found: $REPO_LIST_PATH" >&2
  exit 1
fi

if ! jq -e '.labels and (.labels | type == "array")' "$CATALOG_PATH" >/dev/null; then
  echo "Invalid catalog schema in $CATALOG_PATH (expected .labels array)." >&2
  exit 1
fi

mkdir -p "$(dirname "$REPORT_PATH")"
timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mode="$(bool_lower "$DRY_RUN")"

declare -a repos=()
if [[ -n "$REPOS_OVERRIDE" ]]; then
  IFS=',' read -r -a raw_repos <<<"$REPOS_OVERRIDE"
  for repo in "${raw_repos[@]}"; do
    repo="$(trim "$repo")"
    [[ -n "$repo" ]] && repos+=("$repo")
  done
elif [[ "$(bool_lower "$AUTO_DISCOVER_REPOS")" == "true" ]]; then
  if [[ -z "$ORG_NAME" ]]; then
    echo "ORG_NAME is required when AUTO_DISCOVER_REPOS=true." >&2
    exit 1
  fi

  while IFS= read -r repo || [[ -n "$repo" ]]; do
    repo="$(trim "$repo")"
    [[ -n "$repo" ]] && repos+=("$repo")
  done < <(
    gh repo list "$ORG_NAME" --limit "$ORG_REPO_LIMIT" --json nameWithOwner,defaultBranchRef,isArchived \
      --jq '.[] | select(.isArchived | not) | select(.defaultBranchRef and .defaultBranchRef.name != "") | .nameWithOwner'
  )
else
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="$(trim "$line")"
    [[ -z "$line" || "$line" == \#* ]] && continue
    repos+=("$line")
  done <"$REPO_LIST_PATH"
fi

if [[ "${#repos[@]}" -eq 0 ]]; then
  echo "No target repositories were resolved." >&2
  exit 1
fi

total_created=0
total_updated=0
total_unchanged=0
total_failed=0

{
  echo "# Label Sync Report"
  echo
  echo "- Timestamp (UTC): $timestamp"
  echo "- Mode: $([[ "$mode" == "true" ]] && echo "dry-run" || echo "apply")"
  echo "- Catalog: \`$CATALOG_PATH\`"
  echo "- Target repos: ${#repos[@]}"
  echo
} >"$REPORT_PATH"

for repo in "${repos[@]}"; do
  repo_created=0
  repo_updated=0
  repo_unchanged=0
  repo_failed=0

  echo "## $repo" >>"$REPORT_PATH"
  echo >>"$REPORT_PATH"
  echo "| Label | Action | Details |" >>"$REPORT_PATH"
  echo "| --- | --- | --- |" >>"$REPORT_PATH"

  if ! existing_labels="$(gh api --paginate "repos/${repo}/labels?per_page=100" 2>/dev/null | jq -s 'add // []')"; then
    echo "| n/a | failed | Could not read labels for repository. |" >>"$REPORT_PATH"
    echo >>"$REPORT_PATH"
    total_failed=$((total_failed + 1))
    continue
  fi

  while IFS= read -r label; do
    name="$(jq -r '.name' <<<"$label")"
    color="$(jq -r '.color' <<<"$label")"
    description="$(jq -r '.description // ""' <<<"$label")"

    existing="$(jq -c --arg n "$name" '.[] | select(.name == $n)' <<<"$existing_labels" | head -n 1 || true)"

    if [[ -z "$existing" ]]; then
      if [[ "$mode" == "true" ]]; then
        echo "| \`$name\` | create | Missing label; would create. |" >>"$REPORT_PATH"
      else
        if gh label create "$name" --repo "$repo" --color "$color" --description "$description" >/dev/null 2>&1; then
          echo "| \`$name\` | create | Created successfully. |" >>"$REPORT_PATH"
        else
          echo "| \`$name\` | failed | Create failed. |" >>"$REPORT_PATH"
          repo_failed=$((repo_failed + 1))
          total_failed=$((total_failed + 1))
          continue
        fi
      fi
      repo_created=$((repo_created + 1))
      total_created=$((total_created + 1))
      continue
    fi

    current_color="$(jq -r '.color // ""' <<<"$existing" | tr '[:lower:]' '[:upper:]')"
    current_description="$(jq -r '.description // ""' <<<"$existing")"

    if [[ "$current_color" == "$color" && "$current_description" == "$description" ]]; then
      echo "| \`$name\` | unchanged | Already matches catalog. |" >>"$REPORT_PATH"
      repo_unchanged=$((repo_unchanged + 1))
      total_unchanged=$((total_unchanged + 1))
      continue
    fi

    if [[ "$mode" == "true" ]]; then
      echo "| \`$name\` | update | Drift found; would update color/description. |" >>"$REPORT_PATH"
    else
      if gh label edit "$name" --repo "$repo" --color "$color" --description "$description" >/dev/null 2>&1; then
        echo "| \`$name\` | update | Updated to catalog values. |" >>"$REPORT_PATH"
      else
        echo "| \`$name\` | failed | Update failed. |" >>"$REPORT_PATH"
        repo_failed=$((repo_failed + 1))
        total_failed=$((total_failed + 1))
        continue
      fi
    fi
    repo_updated=$((repo_updated + 1))
    total_updated=$((total_updated + 1))
  done < <(jq -c '.labels[]' "$CATALOG_PATH")

  echo >>"$REPORT_PATH"
  echo "- Summary: created=$repo_created updated=$repo_updated unchanged=$repo_unchanged failed=$repo_failed" >>"$REPORT_PATH"
  echo >>"$REPORT_PATH"
done

{
  echo "## Overall Summary"
  echo
  echo "- Created: $total_created"
  echo "- Updated: $total_updated"
  echo "- Unchanged: $total_unchanged"
  echo "- Failed: $total_failed"
} >>"$REPORT_PATH"

echo "Report written to $REPORT_PATH"
