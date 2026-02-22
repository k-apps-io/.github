#!/usr/bin/env bash
set -euo pipefail

EVENT_PATH="${GITHUB_EVENT_PATH:-}"
REPO="${GITHUB_REPOSITORY:-}"
ACTOR="${GITHUB_ACTOR:-}"
MAINTAINER_BYPASS="${MAINTAINER_BYPASS:-true}"
POLICY_URL="${POLICY_URL:-https://github.com/${REPO}/blob/main/docs/governance/issue-label-policy.md}"
STATUS_BACKLOG="status/backlog"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

contains() {
  local needle="$1"
  shift
  for value in "$@"; do
    if [[ "$value" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

rank_status() {
  case "$1" in
    status/done) echo 5 ;;
    status/blocked) echo 4 ;;
    status/review) echo 3 ;;
    status/in-progress) echo 2 ;;
    status/backlog) echo 1 ;;
    *) echo 0 ;;
  esac
}

is_transition_allowed() {
  local from="$1"
  local to="$2"
  case "$from:$to" in
    status/backlog:status/in-progress) return 0 ;;
    status/in-progress:status/review) return 0 ;;
    status/in-progress:status/blocked) return 0 ;;
    status/review:status/done) return 0 ;;
    status/review:status/in-progress) return 0 ;;
    status/review:status/blocked) return 0 ;;
    status/blocked:status/in-progress) return 0 ;;
    *) return 1 ;;
  esac
}

post_comment() {
  local issue_number="$1"
  local body="$2"
  gh issue comment "$issue_number" --repo "$REPO" --body "$body" >/dev/null
}

require_cmd gh
require_cmd jq

if [[ -z "$EVENT_PATH" || -z "$REPO" || -z "$ACTOR" ]]; then
  echo "Required GitHub context is missing." >&2
  exit 1
fi

if [[ ! -f "$EVENT_PATH" ]]; then
  echo "Event payload file not found: $EVENT_PATH" >&2
  exit 1
fi

action="$(jq -r '.action // ""' "$EVENT_PATH")"
issue_number="$(jq -r '.issue.number // 0' "$EVENT_PATH")"
issue_state="$(jq -r '.issue.state // ""' "$EVENT_PATH")"
event_label="$(jq -r '.label.name // ""' "$EVENT_PATH")"

if [[ "$issue_number" == "0" ]]; then
  echo "No issue number in event payload; nothing to do."
  exit 0
fi

if [[ "$issue_state" != "open" ]]; then
  echo "Issue #$issue_number is not open; skipping."
  exit 0
fi

if [[ "$action" == "labeled" && "$event_label" == "status/done" ]]; then
  gh issue close "$issue_number" --repo "$REPO" >/dev/null || true
fi

permission="$(gh api "repos/${REPO}/collaborators/${ACTOR}/permission" --jq '.permission' 2>/dev/null || echo "none")"
if [[ "${MAINTAINER_BYPASS,,}" == "true" && ( "$permission" == "admin" || "$permission" == "maintain" ) ]]; then
  echo "Bypassing strict guardrails for maintainer actor '${ACTOR}' (${permission})."
  exit 0
fi

mapfile -t labels < <(gh issue view "$issue_number" --repo "$REPO" --json labels --jq '.labels[].name')
mapfile -t status_labels < <(printf '%s\n' "${labels[@]}" | grep '^status/' || true)

if [[ "${#status_labels[@]}" -eq 0 ]]; then
  gh issue edit "$issue_number" --repo "$REPO" --add-label "$STATUS_BACKLOG" >/dev/null
  post_comment "$issue_number" "Applied \`$STATUS_BACKLOG\` because every active issue must have exactly one \`status/*\` label. Policy: $POLICY_URL"
  echo "Added default status/backlog to issue #$issue_number."
  exit 0
fi

# Infer last two labeled status transitions from issue events.
mapfile -t recent_status_events < <(
  gh api "repos/${REPO}/issues/${issue_number}/events?per_page=100" \
    --jq '[.[] | select(.event == "labeled" and (.label.name | startswith("status/"))) | .label.name][-2:][]'
)
previous_status=""
if [[ "${#recent_status_events[@]}" -ge 2 ]]; then
  previous_status="${recent_status_events[0]}"
fi

authoritative_status=""
if [[ "$action" == "labeled" && "$event_label" =~ ^status/ ]]; then
  authoritative_status="$event_label"
else
  top_rank=0
  for status in "${status_labels[@]}"; do
    rank="$(rank_status "$status")"
    if (( rank > top_rank )); then
      top_rank="$rank"
      authoritative_status="$status"
    fi
  done
fi

if [[ -n "$previous_status" && -n "$authoritative_status" && "$previous_status" != "$authoritative_status" ]]; then
  if ! is_transition_allowed "$previous_status" "$authoritative_status"; then
    if [[ "$action" == "labeled" && "$event_label" =~ ^status/ ]]; then
      gh issue edit "$issue_number" --repo "$REPO" --remove-label "$authoritative_status" >/dev/null || true
      gh issue edit "$issue_number" --repo "$REPO" --add-label "$previous_status" >/dev/null || true
    fi
    post_comment "$issue_number" "Invalid status transition blocked: \`$previous_status -> $authoritative_status\`. Allowed transitions are defined in policy: $POLICY_URL"
    authoritative_status="$previous_status"
  fi
fi

if [[ -z "$authoritative_status" ]]; then
  authoritative_status="${status_labels[0]}"
fi

for status in "${status_labels[@]}"; do
  if [[ "$status" != "$authoritative_status" ]]; then
    gh issue edit "$issue_number" --repo "$REPO" --remove-label "$status" >/dev/null || true
  fi
done

if ! contains "$authoritative_status" "${status_labels[@]}"; then
  gh issue edit "$issue_number" --repo "$REPO" --add-label "$authoritative_status" >/dev/null || true
fi

if [[ "${#status_labels[@]}" -gt 1 ]]; then
  post_comment "$issue_number" "Resolved conflicting status labels and kept \`$authoritative_status\` as the active status. Policy: $POLICY_URL"
fi

echo "Guardrails completed for issue #$issue_number with active status '$authoritative_status'."
