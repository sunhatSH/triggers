#!/usr/bin/env bash
# Apply GitHub branch protection for sunhatSH/triggers (rulesets API).
#
# Requires gh auth with repo Administration permission. Fine-grained PATs need:
#   Repository permissions → Administration: Read and write
# Classic token: gh auth login -h github.com -s repo
#
# Usage:
#   bash scripts/admin/apply-branch-protection.sh
set -euo pipefail

OWNER="${OWNER:-sunhatSH}"
REPO="${REPO:-triggers}"
PUSH_USER="${PUSH_USERS:-$OWNER}"
RULESET_NAME="${RULESET_NAME:-PR-only all branches}"
# Legacy name from earlier main/dev-only ruleset (updated in place when re-run).
LEGACY_RULESET_NAME="PR-only main and dev"

if ! command -v gh >/dev/null 2>&1; then
  echo "!! gh CLI not found" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "!! Run: gh auth login" >&2
  exit 1
fi

USER_ID=$(gh api "users/${PUSH_USER}" -q .id)
echo "==> ${OWNER}/${REPO}  bypass user: ${PUSH_USER} (id=${USER_ID})"

PAYLOAD=$(cat <<EOF
{
  "name": "${RULESET_NAME}",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["~ALL"],
      "exclude": []
    }
  },
  "bypass_actors": [
    {
      "actor_id": ${USER_ID},
      "actor_type": "User",
      "bypass_mode": "always"
    }
  ],
  "rules": [
    {
      "type": "update",
      "parameters": {"update_allows_fetch_and_merge": true}
    },
    {
      "type": "pull_request",
      "parameters": {
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": false,
        "required_approving_review_count": 1,
        "required_review_thread_resolution": false
      }
    },
    {"type": "deletion"},
    {"type": "non_fast_forward"}
  ]
}
EOF
)

RULESET_ID=$(
  gh api "repos/${OWNER}/${REPO}/rulesets" --jq \
    ".[] | select(.name==\"${RULESET_NAME}\" or .name==\"${LEGACY_RULESET_NAME}\") | .id" \
    | head -1
)

if [[ -n "${RULESET_ID}" ]]; then
  echo "==> Updating existing ruleset id=${RULESET_ID}"
  gh api "repos/${OWNER}/${REPO}/rulesets/${RULESET_ID}" -X PUT --input - <<<"${PAYLOAD}"
else
  echo "==> Creating ruleset"
  gh api "repos/${OWNER}/${REPO}/rulesets" -X POST --input - <<<"${PAYLOAD}"
fi

echo "==> Done"
echo "Verify: https://github.com/${OWNER}/${REPO}/settings/rules"
echo "Branches: all (~ALL); direct push bypass: @${PUSH_USER}"
echo "Others: fork → PR; you review (CODEOWNERS: @${PUSH_USER})"
