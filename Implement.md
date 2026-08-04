# Implementation log: Issue #27 — Archive Plan.md/Implement.md per branch

Following Plan.md. Logging steps and issues as they happen.

## Steps taken

1. `docs/plans/README.md` — new archive folder + documents the naming
   convention and points at `scripts/archive_plan.sh` / `make archive-plan`.
2. `scripts/archive_plan.sh` — new script. Resolves issue number (`ISSUE`
   env, `issue-N` in branch name, else `current_issue_number()` from
   `scripts/review_common.sh`) and a slug (arg, descriptive branch-name
   part, `Plan.md`'s own `# Plan: ...` heading, else `plan`), then writes
   `docs/plans/<issue-or-date>-<slug>.md` (Plan.md + Implement.md content,
   with a small header noting source branch/timestamp).
3. `Makefile` — added `archive-plan` target (`make archive-plan
   [SLUG=...]`).
4. `AGENTS.md` — added an "Archiving plans" section documenting the manual
   convention and why it isn't automated via `ci.yml`/a git hook (see
   Plan.md's "Decision" section for the full reasoning).
5. `tests/test_archive_plan.py` — 6 unit tests against a throwaway `git
   init` tmp repo (same pattern as `tests/test_check_file_sizes.py`):
   issue+slug from branch name, date+branch-name fallback with no issue
   number, Plan.md-heading fallback when the branch name has no
   descriptive part, explicit slug argument override, `Implement.md`
   inclusion, and failure when `Plan.md` is missing.

## Issues hit

- **Manual dry-run of the script** against a scratch tmp repo (outside this
  worktree, in the scratchpad dir) surfaced one edge case before I wrote
  the automated tests: a bare `agent/issue-27`-style branch (no descriptive
  suffix) strips down to an empty slug after removing the `issue-N`
  component, which would otherwise produce a redundant/ugly
  `27-issue-27.md` filename. Fixed by falling further back to slugifying
  `Plan.md`'s own `# Plan: ...` heading in that case, before finally
  falling back to a plain `plan` string.
- **First `make test` run failed** across the whole suite (not just my new
  tests) with `relation "habits" does not exist` — this worktree's
  docker-compose Postgres was up but had never had Alembic migrations
  applied. Ran `uv run alembic upgrade head` (pre-existing project setup
  step, not something this issue's change needed) and all 18 tests passed,
  including the 6 new ones.
- No production/runtime code touched (`app/`), so `make smoke` isn't
  expected to reveal anything new, but ran it anyway per the loop in
  AGENTS.md.

## Verification so far

- `make lint` — ruff + import-linter + file-size check, all clean.
- `make test` — 18 passed (5 pre-existing + 6 new + 2 + 5 file-size/
  completions/habits — see full list above), 0 failed.
- Manually dry-ran `scripts/archive_plan.sh` against a scratch tmp repo
  covering all four slug/issue resolution paths (branch-name slug + issue
  number, date fallback with no issue number, explicit `SLUG=` override,
  `Plan.md`-heading fallback) before writing `tests/test_archive_plan.py`
  to cover the same paths automatically.

## Status: implementation done, pending agent-review-local/cloud + push
