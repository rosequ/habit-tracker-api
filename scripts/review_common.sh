#!/usr/bin/env bash
# Shared helpers for the agent-review-local / agent-review-cloud Makefile targets.

# This script is invoked from inside a Claude Code session (the implementer's),
# which sets these in its own environment. Strip them so every nested `claude
# -p` call this loop makes is forced to start a brand-new, isolated session --
# it must never be able to attach to or continue the calling session.
unset CLAUDE_CODE_SESSION_ID CLAUDE_CODE_CHILD_SESSION

BASE_REF="${BASE_REF:-main}"

# The commit this branch forked from. Falls back to the repo root commit if
# BASE_REF isn't reachable (e.g. running this on main itself, or a shallow
# clone). Assumes a single root commit; a repo with multiple root commits
# (e.g. a history graft) would need a different fallback.
review_merge_base() {
    git merge-base HEAD "$BASE_REF" 2>/dev/null || git rev-list --max-parents=0 HEAD | tail -n1
}

# Committed + staged + unstaged changes on this branch, relative to where it
# forked from. `git diff <merge-base>` (no second ref) compares against the
# working tree, so uncommitted work is included without extra plumbing.
review_full_diff() {
    git diff "$(review_merge_base)" -- .
}

require_plan() {
    if [[ ! -f Plan.md ]]; then
        echo "Plan.md not found at repo root. Commit a Plan.md describing this branch's intended changes before running review." >&2
        exit 1
    fi
}

# Resolve the GitHub issue this branch/PR is meant to close: explicit ISSUE
# env var, else a "Closes #N" / "Fixes #N" / "Resolves #N" keyword in the open
# PR body. Deliberately does NOT grep Plan.md prose for a bare "#N" -- a plan
# can reference an issue in passing (e.g. an "out of scope" note) without that
# issue being the one this branch closes, which would silently mismatch the
# review against the wrong acceptance criteria.
# Prints nothing (not an error) if none can be found.
current_issue_number() {
    if [[ -n "${ISSUE:-}" ]]; then
        printf '%s\n' "$ISSUE"
        return 0
    fi

    if command -v gh >/dev/null 2>&1; then
        gh pr view --json body -q '.body' 2>/dev/null \
            | grep -Eio '(close[sd]?|fix(e[sd])?|resolve[sd]?)[[:space:]]+#[0-9]+' \
            | grep -Eo '[0-9]+' \
            | head -n1 || true
    fi
}
