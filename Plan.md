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

## Fixes made after `agent-review-cloud`

Round 1 caught one real, blocking gap and several smaller ones, all
applied:
- **`AGENTS.md` was never updated.** This whole branch's point is making
  the review loop actually happen instead of staying pure convention, and
  the one doc that tells a contributor what `git config core.hooksPath
  .githooks` does was left describing only the old main-push-only
  behavior. Fixed: "Branching" now documents both hooks, their overrides,
  and the changed semantics below.
- `pre-commit`'s comment overclaimed why it unsets `GIT_DIR`/etc.: `make
  lint` never runs pytest, so it was never actually exposed to the
  corruption reproduced in `pre-push`'s verification section. Fixed the
  comment to say so plainly and frame the unset there as consistency/
  defense-in-depth, not an active fix for a reachable bug.
- `ALLOW_PUSH_TO_MAIN=1` silently changed meaning: it used to short-circuit
  the entire old hook, now it only bypasses the main-push block specifically
  -- the lint/test/review gate still applies unless `SKIP_PUSH_VERIFICATION=1`
  is also set. Called this out explicitly in both `AGENTS.md` and the
  hook's own header comment, for anyone with muscle memory for the old flag.
- The verification gate doesn't distinguish branches from tags (anything
  with a non-zero local SHA triggers it) -- noted explicitly as intentional-
  by-default rather than an unconsidered gap, since this repo doesn't
  currently tag releases.

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
5. `pre-push` was exercised for real, against the actual GitHub remote (this
   branch's own push), not just read through. That real run surfaced two
   genuine bugs neither `bash -n` nor reasoning about the script would have
   caught:
   - **`make test` failed with a missing `DATABASE_URL`.** `git push`
     doesn't run inside direnv's normal shell-hook flow, so `.envrc`'s
     exports aren't present for a bare `make test` call even though they
     are for a human running the same target in an already-direnv-loaded
     terminal -- the exact class of bug `make dev`/`make smoke` already hit
     and fixed by routing through `direnv exec .`. Fixed the same way.
   - **Worse: `make test` (before that fix) silently corrupted this
     worktree's own git index.** In a git *worktree* specifically (verified
     this doesn't happen in a plain, non-worktree repo), git sets `GIT_DIR`
     in a hook's environment, and it leaks into any subprocess the hook
     spawns -- including `tests/test_check_file_sizes.py`'s own supposedly-
     isolated `git init`/`git add` calls in a pytest `tmp_path`, which then
     silently mutated the real worktree's index instead of an isolated one.
     Reproduced this directly (with `GIT_DIR` set: corrupts; unset: clean)
     to confirm causation before fixing, and recovered the one real
     corruption incident cleanly with `git reset` (working tree content was
     never touched, only the index -- confirmed via `git show HEAD:<path>`
     matching disk before resetting). Fixed by unsetting
     `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE`/`GIT_COMMON_DIR` at the top
     of both hooks.
   - Also found: `make agent-review-local`'s own `make smoke` step needs
     `DB_PORT`/`PROMETHEUS_PORT` for its `docker-compose up -d` call too --
     `scripts/smoke_test.sh` only routes its *uvicorn* invocation through
     `direnv exec .` internally, not `docker-compose`. Without this, that
     call fell back to default ports and collided with another worktree's
     already-running containers. Fixed by routing all three `make` calls in
     `pre-push` (`lint`, `test`, `agent-review-local`) through `direnv exec
     .` uniformly, rather than cherry-picking which ones "need" it.
   - After all three fixes, a real `git push` of this branch ran `make
     lint` / `make test` / `make agent-review-local` (lint + `make smoke` +
     the Plan.md-coverage check) cleanly end-to-end and succeeded.

Not yet exercised end-to-end: the pure-branch-deletion skip path (`git push
origin --delete <branch>`) -- read through carefully against the same
`while read`/`ZERO_SHA` pattern already proven correct for the main-push
block, but not executed against a real remote as part of building this.
