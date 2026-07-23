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
    if git merge-base HEAD "$BASE_REF" 2>/dev/null; then
        return 0
    fi
    echo "warning: could not resolve BASE_REF '$BASE_REF' as an ancestor of HEAD -- falling back to this repo's first commit, so the diff below is the *entire* history, not just this branch. Set BASE_REF to the correct base branch if that's wrong." >&2
    git rev-list --max-parents=0 HEAD | tail -n1
}

# Committed + staged + unstaged changes on this branch, relative to where it
# forked from. `git diff <merge-base>` (no second ref) compares the merge
# base against the working tree, so modifications to already-tracked files
# are included without extra plumbing -- but it never shows brand-new files
# that haven't been `git add`ed at all, since git diff only walks paths that
# are tracked in the tree or index. Union in untracked (non-ignored) files as
# synthetic "new file" diffs so a forgotten `git add` can't hide unplanned
# scope from either review target.
review_full_diff() {
    local merge_base
    merge_base="$(review_merge_base)"
    git diff "$merge_base"
    git ls-files --others --exclude-standard -z | while IFS= read -r -d '' f; do
        git diff --no-index -- /dev/null "$f" || true
    done
}

require_plan() {
    if [[ ! -f Plan.md ]]; then
        echo "Plan.md not found at repo root. Commit a Plan.md describing this branch's intended changes before running review." >&2
        exit 1
    fi

    # A Plan.md that exists but predates this branch's actual changes (e.g.
    # left over from a previous worktree/feature) is worse than no plan at
    # all: the diff-vs-plan check below would silently "pass" this branch's
    # real changes as unplanned-scope-free just because *some* Plan.md is
    # sitting at the repo root. Fail loudly if other tracked or untracked
    # files changed on this branch but Plan.md itself didn't.
    local merge_base
    merge_base="$(review_merge_base)"

    local other_tracked_changed=1
    git diff --quiet "$merge_base" -- . ':(exclude)Plan.md' || other_tracked_changed=0

    local other_untracked
    other_untracked="$(git ls-files --others --exclude-standard -- . ':(exclude)Plan.md')"

    if { [[ "$other_tracked_changed" -eq 0 ]] || [[ -n "$other_untracked" ]]; } \
        && git diff --quiet "$merge_base" -- Plan.md; then
        echo "Plan.md hasn't changed since $BASE_REF, but other files on this branch have. A stale/unrelated Plan.md (e.g. left over from a previous feature) would let review silently pass this branch's actual changes as 'planned' -- update Plan.md to describe what this branch does before running review." >&2
        exit 1
    fi
}

# Commit-time counterpart to require_plan(), meant to be called from
# .githooks/pre-commit rather than from the push-time review scripts.
# Compares the INDEX (what's about to become the new commit's tree) against
# the merge-base, not the working tree -- untracked/unstaged files aren't
# part of the commit being made, so (unlike require_plan()) those are
# irrelevant here and deliberately not unioned in. Because the index already
# reflects every earlier commit on this branch since the merge-base (not
# just what's staged right now), this refuses a commit only if Plan.md has
# never been touched on this branch at all, not merely in this one commit --
# so a first commit that adds Plan.md, followed by later commits that
# implement it, passes every one of those later commits too.
#
# Same pre-existing sharp edge as require_plan() (not introduced here, but
# hit more often now that this runs on every commit instead of just at
# push): a merge commit pulling unrelated main history into a long-lived
# branch can make this see diffs in files the branch author never touched,
# and refuse the merge unless Plan.md changed too.
require_plan_staged() {
    if [[ ! -f Plan.md ]]; then
        echo "Plan.md not found at repo root. Add a Plan.md describing this branch's intended changes before committing anything else -- override once with SKIP_COMMIT_PLAN_CHECK=1 git commit ..." >&2
        exit 1
    fi

    local merge_base
    merge_base="$(review_merge_base)"

    # `git diff --quiet` exits 0 (true) when there's NO difference -- so
    # other_changed=1 here means "nothing outside Plan.md changed" and only
    # flips to 0 once the `||` fires on a real diff. Same inverted-boolean
    # convention require_plan() above already uses; kept consistent rather
    # than diverging for this one function.
    local other_changed=1
    git diff --cached --quiet "$merge_base" -- . ':(exclude)Plan.md' || other_changed=0

    if [[ "$other_changed" -eq 0 ]] && git diff --cached --quiet "$merge_base" -- Plan.md; then
        echo "This commit (or an earlier one on this branch) changes files other than Plan.md, but Plan.md itself still reads identically to $BASE_REF. Write/update Plan.md to describe the change BEFORE committing it, not after -- override once with SKIP_COMMIT_PLAN_CHECK=1 git commit ..." >&2
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
