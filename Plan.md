# Plan: Archive each branch's Plan.md/Implement.md (issue #27)

## Context

`Plan.md` (and often `Implement.md`) is mechanically required per-branch by
`require_plan_staged` in `.githooks/pre-commit`, but every new
branch/worktree just overwrites these files. `git log --oneline -- Plan.md`
confirms it's been rewritten on essentially every feature branch, so
whatever isn't captured in a squashed PR description is effectively lost.

## Decision: standalone script + documented manual convention, NOT a `ci.yml` step

The issue itself suggests wiring this into `ci.yml`'s merge path, but
editing `.github/workflows/*` is explicitly off-limits for this issue in
this batch (unlike issue #28, which has a separately-approved exception).
Given that constraint, I'm implementing this as:

- `scripts/archive_plan.sh` — a standalone script that copies the current
  branch's `Plan.md` (and `Implement.md`, if present) into
  `docs/plans/<issue-or-date>-<slug>.md`.
- A documented manual convention in `AGENTS.md` ("Archiving plans" section):
  run `make archive-plan` right before merging a PR (after the last
  `Plan.md`/`Implement.md` update, before `gh pr merge`), then commit the
  resulting `docs/plans/*.md` file as part of that same PR.

I considered instead adding a new git hook (e.g. `post-commit`) to automate
this further, but rejected it:
- The two hooks I'm allowed to touch are explicitly limited to
  `pre-commit`/`pre-push`, and neither of those is a natural place to
  detect "this branch is about to merge" — that's a merge-time decision,
  not a commit/push-time one, and guessing wrong (e.g. archiving on every
  commit) would spam `docs/plans/` with half-finished plans instead of
  final ones.
- Doing it well would require knowing which commit is the *last* one before
  merge, which isn't knowable from inside a single hook invocation without
  either false-triggering early or missing the final update — a human/agent
  judgment call ("I'm about to merge this PR now") is simpler and more
  reliable than trying to infer that mechanically here.
- The issue text itself frames "a small script + documented manual
  convention" as an acceptable alternative to CI automation if "automating
  it isn't worth the complexity" — that's the case here, given the
  restriction on editing workflows/hooks for this issue.

## What this branch changes

- **`docs/plans/README.md`** — new archive folder, documents the naming
  convention (`<issue-or-date>-<slug>.md`) and points at
  `scripts/archive_plan.sh` / `make archive-plan`.
- **`scripts/archive_plan.sh`** — new script:
  - Resolves an issue number: `ISSUE` env var, else `issue-N` parsed out of
    the branch name (matches `agent-ticket.yml`'s branch convention), else
    `current_issue_number()` from `scripts/review_common.sh` (an open PR's
    "Closes #N" body).
  - Resolves a slug: optional `$1` arg, else the descriptive part of the
    branch name, else the `# Plan: ...` heading in `Plan.md`, else a plain
    `plan` fallback — never fails the whole script just because a slug
    couldn't be inferred well.
  - Falls back to today's date (`YYYY-MM-DD`) as the prefix when no issue
    number can be resolved.
  - Writes `docs/plans/<prefix>-<slug>.md`: `Plan.md`'s content, then
    (if present) `Implement.md`'s content below a separator, with a small
    header noting the source branch and archive timestamp.
- **`Makefile`** — new `archive-plan` target wrapping the script
  (`make archive-plan` or `make archive-plan SLUG=my-slug`).
- **`AGENTS.md`** — new "Archiving plans" section documenting the manual
  convention (when to run it, what it does, why it's manual not automated
  here).
- **`tests/test_archive_plan.py`** — unit tests against a throwaway `git
  init` tmp repo (same pattern as `tests/test_check_file_sizes.py`):
  issue number parsed from branch name, slug fallback to the `Plan.md`
  heading when the branch name has no descriptive part, explicit slug
  argument override, and `Implement.md` being included when present.

## Out of scope

- Editing `.github/workflows/*`, `.githooks/pre-commit`, or
  `.githooks/pre-push` (per this issue's explicit constraint).
- Changing the existing `require_plan_staged` gate itself.
- Backfilling `docs/plans/` for already-merged historical branches (#1, #3,
  #15, #18, #19, ...) — out of scope per the issue; only new archiving
  going forward.
- Issues #25/#26/#28/#29 — other sessions own those.

## Verification

- `make lint` — ruff + import-linter + file-size check.
- `make test` — unit tests, including the new `tests/test_archive_plan.py`.
- No runtime/app code touched, so `make smoke` isn't expected to catch
  anything new, but I'll run it anyway since it's cheap.
- `make agent-review-local` / `make agent-review-cloud` before pushing.
