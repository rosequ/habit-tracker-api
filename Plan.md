# Plan: Mechanically gate "Plan.md before implementation," not just "at push"

## Context

Feedback from this session: in both prior branches (`recover-continuous-
maintenance-fixes`, `north-mini-code-provider-toggle`), `Plan.md` was
written or corrected *after* the actual code/workflow changes were already
made — backfilled to describe what had already happened, sometimes more
than once, rather than written first and implemented against. The existing
`require_plan()` check (`scripts/review_common.sh`, used by both
`agent-review-local`/`agent-review-cloud`) only runs at **push** time and
only checks the *final* state of the diff vs `Plan.md` — it can't catch
"implemented first, planned after," because by push time everything lines
up regardless of the order things actually happened in.

This branch moves a cheap, mechanical (no LLM call, no network — consistent
with `.githooks/pre-commit`'s existing "fast enough for every commit"
design) version of that check earlier, to **commit** time: you cannot
commit a change to any tracked file unless `Plan.md` has *already* been
touched, in this commit or an earlier one on the same branch, relative to
where the branch forked from `main`. This can't fully enforce "the plan was
written before you started thinking about the code" (git has no notion of
edit order within a single commit), but it does mechanically block the
exact failure mode from this session: committing implementation changes
while `Plan.md` still reads identically to `main`.

## What this branch adds

**1. `scripts/review_common.sh`** — new function `require_plan_staged()`,
alongside the existing `require_plan()`. Same spirit (Plan.md must cover
what's changed since the merge-base) but different diff source: `git diff
--cached "$merge_base"` (index vs merge-base — i.e. what the *new* commit's
tree will look like, which already includes every earlier commit on this
branch since `merge_base`) instead of `require_plan()`'s working-tree-based
diff. Refuses if any tracked path other than `Plan.md` differs from the
merge-base in that comparison, but `Plan.md` itself does not. Existing
`require_plan()` is untouched — it keeps gating pushes with its own
(working-tree-inclusive, untracked-file-inclusive) semantics; this is a
second, distinct, cheaper check for a different point in the lifecycle.

**2. `.githooks/pre-commit`** — sources `scripts/review_common.sh` and
calls `require_plan_staged` after `make lint`, skippable via a new
`SKIP_COMMIT_PLAN_CHECK=1` env var (mirrors the existing
`SKIP_COMMIT_LINT=1` pattern) for the legitimate case of an early WIP commit
before `Plan.md` is ready (e.g. `git init`-style scaffolding), not intended
for routine use.

**3. `AGENTS.md`** — documents the new check and its override alongside the
existing `pre-commit`/`pre-push` description.

## Out of scope

- Changing `require_plan()`'s own semantics or its push-time LLM-based
  coverage check (`agent-review-local`'s Plan.md-vs-diff comparison) — this
  branch only adds an earlier, cheaper, purely mechanical checkpoint.
  Semantic "does Plan.md actually *describe* the diff well" is still only
  checkable by the existing Haiku pass at push time; this new gate only
  checks "was Plan.md touched at all."
- Enforcing true edit-order (plan content written before code content) —
  not observable from git state at all; out of reach for any hook.

## Verification

1. Exercised directly in an isolated scratch git repo (a throwaway repo
   outside this working tree, not a worktree of this repo, since the check
   under test is generic git-diff logic with no dependency on this repo's
   actual files):
   - A first commit that only adds `Plan.md` — allowed.
   - A subsequent commit changing a tracked file, `Plan.md` untouched since
     the merge-base — refused, with a clear message.
   - A commit changing a tracked file where `Plan.md` was already modified
     in an *earlier* commit on the same branch (not this one) — allowed,
     confirming the check is cumulative-since-merge-base, not
     this-commit-only.
   - `SKIP_COMMIT_PLAN_CHECK=1` overrides the refusal.
2. `bash -n` on the edited hook and `make lint` passes in this repo itself.
3. Re-ran this exact check against this branch's own commits as they're
   made, dogfooding it live while implementing.
>>>>>>> a784392 (Add Plan.md for a mechanical plan-before-implementation gate)
