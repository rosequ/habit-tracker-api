# 0002. Mechanical Plan.md-before-implementation pre-commit gate

## Status

Accepted

## Context

`make agent-review-local` / `make agent-review-cloud` both compare a
branch's diff against a `Plan.md` at the repo root to check that the
change actually matches what was planned, and to flag scope that the plan
never mentioned. That check is only useful if `Plan.md` describes *this*
branch's change and was written before the implementation, not backfilled
afterward to rubber-stamp whatever was already done — a plan written after
the fact can always be made to match the diff, so it can't actually catch
unplanned scope.

Headless agent workflows (`agent-ticket.yml` in particular) and
interactive sessions alike had no mechanical enforcement of that
ordering — nothing stopped committing implementation first and writing
(or never writing) `Plan.md` afterward. Relying on the agent, human or
not, to remember to plan first is exactly the kind of rule this repo
prefers to enforce structurally rather than trust to memory.

## Decision

`.githooks/pre-commit` calls `require_plan_staged` (in
`scripts/review_common.sh`) on every commit. It refuses the commit if the
index changes any tracked file other than `Plan.md` while `Plan.md` itself
still reads identically to `main` — i.e. some non-`Plan.md` file changed
on this branch, ever, without `Plan.md` ever having changed too. Because
it compares the index against the merge-base rather than diffing this one
commit in isolation, a first commit that adds `Plan.md` followed by later
commits implementing it passes every one of those later commits as well;
only a branch that never touched `Plan.md` at all gets blocked.

This cannot enforce true edit *order* within a single commit — git has no
such notion — only that `Plan.md` was touched somewhere on the branch
before other files can be. It also cannot check the plan's *content* is
accurate; that's `agent-review-local`'s job, at push time. Override once
with `SKIP_COMMIT_PLAN_CHECK=1 git commit ...` for a genuine false
positive (e.g. a merge commit dragging in unrelated `main` history).

## Consequences

A stale `Plan.md` left over from a previous feature/worktree can no longer
silently rubber-stamp unrelated work as "planned" — the gate forces a real
edit to `Plan.md` on this branch first. The tradeoff is friction on every
single commit (not just at push time), including small WIP ones, and a
sharp edge on merge commits (documented in `scripts/review_common.sh`)
where pulling in unrelated `main` history can trip the check for files the
branch author never touched, requiring the `SKIP_COMMIT_PLAN_CHECK`
override.
