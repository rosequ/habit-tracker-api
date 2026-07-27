#!/usr/bin/env bash
# Archives the current branch's Plan.md (and Implement.md, if present)
# into docs/plans/<issue-or-date>-<slug>.md before the next branch/worktree
# overwrites them. Manual convention, not CI-enforced -- see AGENTS.md's
# "Archiving plans" section and the Plan.md history for issue #27 for why
# this isn't wired into ci.yml or a git hook instead.
#
# Usage: scripts/archive_plan.sh [slug]
#   Run this right before merging a PR (after the last Plan.md/Implement.md
#   update, before `gh pr merge`), then commit the resulting docs/plans/*.md
#   file as part of that same PR. Also available as `make archive-plan`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(git rev-parse --show-toplevel)"

if [[ ! -f Plan.md ]]; then
    echo "archive_plan: no Plan.md at repo root -- nothing to archive." >&2
    exit 1
fi

# For current_issue_number() -- the "Closes #N" fallback below.
source "$SCRIPT_DIR/review_common.sh"

branch="$(git branch --show-current)"

slugify() {
    printf '%s' "$1" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' \
        | cut -c1-50
}

# Issue number: explicit ISSUE env var, else "issue-N" parsed out of the
# branch name (matches agent-ticket.yml's `agent/issue-N` convention), else
# an open PR's "Closes #N" body via current_issue_number (review_common.sh).
issue="${ISSUE:-}"
if [[ -z "$issue" && "$branch" =~ issue-([0-9]+) ]]; then
    issue="${BASH_REMATCH[1]}"
fi
if [[ -z "$issue" ]]; then
    issue="$(current_issue_number)"
fi

# Slug: explicit $1, else the descriptive part of the branch name (with any
# leading "agent/" and any "issue-N" component stripped -- a bare
# `agent/issue-27` branch has no descriptive part left after this), else
# the "# Plan: ..." heading in Plan.md, else a plain fallback. Never fails
# the whole script just because a good slug couldn't be inferred.
slug="${1:-}"
if [[ -z "$slug" ]]; then
    branch_slug="$(printf '%s' "$branch" | sed -E 's#^agent/##; s/(^|-)issue-[0-9]+(-|$)/\1/g')"
    slug="$(slugify "$branch_slug")"
fi
if [[ -z "$slug" ]]; then
    plan_title="$(grep -m1 -E '^# Plan:' Plan.md | sed -E 's/^# Plan:[[:space:]]*//')"
    slug="$(slugify "$plan_title")"
fi
if [[ -z "$slug" ]]; then
    slug="plan"
fi

prefix="${issue:-$(date +%Y-%m-%d)}"

mkdir -p docs/plans
out="docs/plans/${prefix}-${slug}.md"

{
    echo "<!-- Archived from branch \`$branch\` on $(date -u +%Y-%m-%dT%H:%M:%SZ) by scripts/archive_plan.sh -->"
    echo
    cat Plan.md
    if [[ -f Implement.md ]]; then
        echo
        echo "---"
        echo
        cat Implement.md
    fi
} > "$out"

echo "archive_plan: wrote $out"
echo "archive_plan: remember to 'git add $out' and commit it as part of this PR."
