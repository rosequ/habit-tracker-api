#!/usr/bin/env bash
# make agent-review-local: fast, cheap gate.
#   1. make lint (ruff + import-linter + file-size check)
#   2. a cheap model checks the diff against the committed Plan.md and flags
#      anything changed that the plan doesn't account for
# Exits non-zero if lint fails or the diff has unplanned scope.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/review_common.sh

LOCAL_MODEL="${LOCAL_MODEL:-claude-haiku-4-5-20251001}"

echo "==> make lint"
if ! make lint; then
    echo "agent-review-local: FAIL (lint)" >&2
    exit 1
fi

require_plan

diff_content="$(review_full_diff)"
if [[ -z "$diff_content" ]]; then
    echo "==> No changes vs $BASE_REF; nothing to review."
    echo "agent-review-local: PASS"
    exit 0
fi

plan_content="$(cat Plan.md)"

prompt="$(cat <<EOF
You are a fast, cheap pre-review gate in an automated review loop. Do not
review code quality or correctness in depth -- only check plan coverage.

Task: compare the diff below against the committed Plan.md. Flag any changed
file or behavior that is NOT reasonably accounted for by Plan.md. Mechanical
changes clearly implied by the plan (e.g. tests for planned code, imports,
renames) do not need explicit mention. Be strict about genuinely unplanned
scope: new files, endpoints, or behavior the plan never mentions.

=== Plan.md ===
$plan_content

=== Diff (vs $BASE_REF) ===
$diff_content

Respond with:
1. A short bullet list of unplanned changes found (or "None").
2. A final line, exactly one of:
RESULT: PASS
RESULT: FAIL
EOF
)"

echo "==> Checking diff against Plan.md with $LOCAL_MODEL"
output="$(claude -p \
    --model "$LOCAL_MODEL" \
    --tools "" \
    --permission-mode bypassPermissions \
    <<< "$prompt")"

echo "$output"

if echo "$output" | grep -q '^RESULT: FAIL'; then
    echo "agent-review-local: FAIL (unplanned diff)" >&2
    exit 1
fi

if ! echo "$output" | grep -q '^RESULT: PASS'; then
    echo "agent-review-local: FAIL (no clear result from model)" >&2
    exit 1
fi

echo "agent-review-local: PASS"
