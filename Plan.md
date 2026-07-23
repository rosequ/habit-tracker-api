# Plan: Enforce lint/tests/review at commit and push time, not just at merge

## Context

AGENTS.md documents a review loop (`agent-review-local` -> fix -> repeat ->
`agent-review-cloud` -> address comments -> repeat) and requires a
committed `Plan.md` describing the branch. Nothing actually enforces that
loop happens before code leaves the machine — it's currently pure
convention, and it was just skipped in practice (a prior branch was
committed and pushed without running either review step). Separately, the
existing `.githooks/pre-push` hook only blocks direct pushes to `main` — it
does nothing for pushes of feature branches, which is where routine work
actually leaves the machine.

This branch closes both gaps at the one point that's actually enforceable
client-side (server-side branch protection 403s on this repo -- private,
Free plan, issue #7 -- so nothing here can be made truly unbypassable; see
`.githooks/pre-push`'s existing comment for the same root cause):

**1. `.githooks/pre-commit`** (new) — runs `make lint` (ruff + import-linter
+ file-size guard; all static, no DB/network needed) before allowing any
commit. Fast enough to run on every commit without friction. Override once
with `SKIP_COMMIT_LINT=1 git commit ...`.

**2. `.githooks/pre-push`** (edited) — keeps the existing main-push block
unchanged, and adds a second, independent gate that applies to pushing ANY
branch, not just main: refuses the push unless `make lint`, `make test`,
and `make agent-review-local` (lint + `make smoke` + a check that the diff
is covered by `Plan.md`, via `scripts/review_common.sh`'s `require_plan` and
a cheap Haiku-powered scope check) all pass. A pure branch deletion (`git
push origin --delete <branch>` -- every ref's local SHA is the all-zero
SHA) skips verification entirely, since there's nothing to check. Override
once with `SKIP_PUSH_VERIFICATION=1 git push ...`.

**Deliberately NOT run in either hook: `make agent-review-cloud`.** That's
the deep, slow, costly reviewer-subagent pass (spins up a full Sonnet/Opus
session with repo read access) — AGENTS.md's own loop already describes it
as a once-before-asking-for-human-review step, not a repeat-every-push one.
Gating every routine WIP push behind it would make pushing prohibitively
slow/expensive for iterative work and doesn't match how the loop is meant
to be used. `agent-review-local` (cheap, ~seconds, no external model calls
beyond a single small Haiku prompt) is the right gate for "does every push
meet a baseline," not `agent-review-cloud`.

## Out of scope

- Any change to `agent-review-local`/`agent-review-cloud` themselves
  (`scripts/agent_review_local.sh` / `scripts/agent_review_cloud.sh`) --
  reused as-is via `make agent-review-local`.
- True (unbypassable) enforcement -- not achievable without upgrading this
  repo off the Free plan or making it public to unlock branch protection.
  Out of scope for this branch; these hooks are the same class of
  client-side stopgap `.githooks/pre-push` already is for the main-push
  block, just widened to cover pushing any branch.

## Verification

1. Tested directly in an isolated `git worktree` off `main`
   (`habit-tracker-api-hooks`), so as not to touch the primary working
   directory or interfere with an in-flight review of unrelated work there.
2. Confirmed `git rev-parse --show-toplevel` (which both hooks `cd` into)
   resolves to the worktree's own path when run from within it, not the
   main working directory's -- each git worktree has its own independent
   checkout of tracked files including `.githooks/`, so hooks in one
   worktree can't affect another.
3. `pre-commit`: committed a trivial change and confirmed `make lint`
   actually runs and the commit succeeds when it passes; then staged a file
   with a deliberate unused-import lint violation and confirmed the commit
   is refused with the lint error shown; then confirmed
   `SKIP_COMMIT_LINT=1 git commit` overrides it. All three matched expected
   behavior.
4. `bash -n` on both hook scripts.

Not yet exercised end-to-end: the `pre-push` hook's `make test`/
`make agent-review-local` path (needs a real push to a remote to trigger,
which wasn't done as part of building this) and the pure-branch-deletion
skip path. Both are small, direct extensions of the same `while read`
loop/override pattern already validated for `pre-commit` and the existing
`ALLOW_PUSH_TO_MAIN` block, and were read through carefully rather than
executed against a real remote.
