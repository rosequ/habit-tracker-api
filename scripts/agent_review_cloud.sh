#!/usr/bin/env bash
# make agent-review-cloud: deeper gate.
# Spawns a fresh, isolated Claude Code subagent (no access to the implementer's
# conversation, read-only tools only) as an independent reviewer. Gives it the
# full diff, Plan.md, and the linked GitHub issue's acceptance criteria, and
# asks for an explicit verdict.
# Exits non-zero if the reviewer requests changes.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/review_common.sh

CLOUD_MODEL="${CLOUD_MODEL:-claude-sonnet-5}"
REVIEW_DIR=".agent-review"
mkdir -p "$REVIEW_DIR"

require_plan

diff_content="$(review_full_diff)"
if [[ -z "$diff_content" ]]; then
    echo "==> No changes vs $BASE_REF; nothing to review."
    echo "agent-review-cloud: PASS"
    exit 0
fi

plan_content="$(cat Plan.md)"

issue_number="$(current_issue_number)"
issue_section="No linked GitHub issue was found for this branch/PR."
if [[ -n "$issue_number" ]] && command -v gh >/dev/null 2>&1; then
    issue_json="$(gh issue view "$issue_number" --json title,body 2>/dev/null || true)"
    if [[ -n "$issue_json" ]]; then
        issue_title="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["title"])' <<< "$issue_json")"
        issue_body="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["body"])' <<< "$issue_json")"
        issue_section="Issue #$issue_number: $issue_title

$issue_body"
    fi
fi

system_prompt="You are an independent code reviewer with no memory of how this code was written. You have read-only access to the repository (Read/Glob/Grep only) -- you must not edit or write any files. Your only output is a review verdict and comments. Judge the diff on correctness, whether it satisfies the linked issue's acceptance criteria, whether it stays within the scope of Plan.md, and general code quality. Be concrete: cite file paths and line numbers."

# Delimiter is deliberately unique (not "EOF") -- $issue_section embeds raw
# GitHub issue body text, unlike the diff, which can't contain a bare "EOF"
# line since every diff line is prefixed with +/-/space.
prompt="$(cat <<REVIEW_PROMPT_EOF_9f3a
=== Plan.md (committed) ===
$plan_content

=== Linked GitHub issue ===
$issue_section

=== Full diff (vs $BASE_REF) ===
$diff_content

Review this change. You may use Read/Glob/Grep to inspect the repository
directly for context beyond the diff. Respond with:
1. If there are blocking issues: a concrete, numbered list of required
   changes (file/line references where possible).
2. If there are non-blocking suggestions: a separate short list.
3. A final line, exactly one of:
VERDICT: APPROVE
VERDICT: REQUEST_CHANGES
REVIEW_PROMPT_EOF_9f3a
)"

echo "==> Running isolated read-only reviewer subagent with $CLOUD_MODEL"
timestamp="$(date +%Y%m%d-%H%M%S)"
out_file="$REVIEW_DIR/cloud-review-$timestamp.md"

claude -p \
    --model "$CLOUD_MODEL" \
    --tools "Read,Glob,Grep" \
    --permission-mode bypassPermissions \
    --system-prompt "$system_prompt" \
    <<< "$prompt" | tee "$out_file"

output="$(cat "$out_file")"

echo
echo "Full review saved to $out_file"

if echo "$output" | grep -q '^VERDICT: REQUEST_CHANGES'; then
    echo "agent-review-cloud: FAIL (blocking issues found)" >&2
    exit 1
fi

if ! echo "$output" | grep -q '^VERDICT: APPROVE'; then
    echo "agent-review-cloud: FAIL (no clear verdict from reviewer)" >&2
    exit 1
fi

echo "agent-review-cloud: PASS"
