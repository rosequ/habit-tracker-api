# Plan: Fix `make dev` and close the runtime-gating gap it exposed

## Context

No GitHub issue is linked to this branch — it started as an ad-hoc fix for
`make dev` crashing, and grew to include a gap it exposed in the review
tooling added in PR #6 (`agent-review-local` / `agent-review-cloud`,
documented in `AGENTS.md`).

## Part 1 — `make dev` fixes (already committed: 18df950, d872487)

**Problem:** `make dev` only ran `uvicorn` directly, which had two failures:
1. `uvicorn` only inherits `.envrc`'s env vars (`DATABASE_URL`, `APP_PORT`,
   etc.) if the calling shell already had direnv's hook fire for this
   directory. Any other invocation path (script, editor terminal, fresh
   shell) skipped that and crashed on startup with a missing `DATABASE_URL`.
2. It never started `docker-compose` (`db`, `prometheus`), leaving Postgres
   and Prometheus undiscoverable unless you separately remembered
   `docker-compose up -d`.

**Fix:**
- `Makefile`: route the app command through `direnv exec .` so `.envrc` is
  loaded explicitly regardless of caller shell state, and prepend
  `docker-compose up -d` so one command brings up db, prometheus, and the
  app together.
- `AGENTS.md`: document that `make dev` now brings up docker-compose too.

## Part 2 — Close the gap these fixes exposed in review gating

**Problem:** neither `make dev` fix commit was actually checked by
`agent-review-local`/`agent-review-cloud` before merging — `Plan.md` at the
repo root was still the one from an earlier, unrelated feature (Issue #3,
completions), and `.agent-review/` had no review log for either commit. Two
runtime bugs surfaced afterward as a result:
- `make dev` failing with "Address already in use" (a stale uvicorn process
  from an earlier run was still bound to the port) — invisible to review even
  in principle, since `agent-review-local` runs with no tools at all and
  `agent-review-cloud` is read-only (`Read/Glob/Grep`, no `Bash`); neither
  ever executes anything, so a process-lifecycle bug can't be caught by
  reading a diff.
- `make metrics-query` erroring on a multi-series PromQL query — not
  actually a bug (the script's guard at `scripts/query_metrics.sh:34-41` is
  intentional), but it highlighted that this repo's gating has no way to
  distinguish "reviewed and passed" from "never reviewed at all."

This part of the branch closes both holes: a stale/irrelevant `Plan.md` can
no longer silently pass unrelated work as "planned," and there's now a cheap
way to actually *run* the app as part of the fast review loop instead of only
reading its diff.

**1. `scripts/review_common.sh` — `require_plan` checks relevance, not just existence**

Previously `require_plan` only checked that some `Plan.md` file exists at the
repo root. Now it also fails if other tracked or untracked files changed
since `BASE_REF` (`main`) but `Plan.md` itself didn't — the exact situation
that let the `make dev` commits merge against a stale, unrelated plan.

**2. `scripts/smoke_test.sh` + `make smoke`**

A new target that actually boots the app the way `make dev` does
(`docker-compose up -d`, then `direnv exec . uv run uvicorn app.main:app`)
on `SMOKE_PORT` (default 8098, deliberately separate from `APP_PORT` so it
doesn't collide with a `make dev` already running in another terminal),
polls `/health` (which runs a real `SELECT 1` against Postgres) for up to
20s, then tears the uvicorn process down via a `trap ... EXIT` cleanup.
Fails loudly if the port's already taken, uvicorn exits early, or `/health`
never responds — covering exactly the class of bug (env vars, docker-compose
state, port conflicts) that a text-only diff review structurally cannot see.

**3. `scripts/agent_review_local.sh` — wire `make smoke` into the fast gate**

Runs `make smoke` right after `make lint` and before the Plan.md diff check,
so the loop you're meant to run repeatedly while implementing
(`agent-review-local` -> fix -> repeat) now includes a real runtime check,
not just lint + a text-only scope check.

**4. `AGENTS.md`**

Documents `make smoke` and the new `require_plan` behavior under "How to
verify your work."

## Out of scope

- Actually merging `.githooks/pre-push` (branch `add-pre-push-hook` / PR #11)
  into `main` — that's a separate, already-tracked piece of work.
- Server-side branch protection (blocked on issue #7 — private repo on
  GitHub's Free plan).
- Any change to `scripts/query_metrics.sh` itself — its multi-series guard
  is correct as-is; it was misdiagnosed as a bug in conversation before being
  confirmed as intentional.

## Verification

1. `make lint` — ruff, import-linter, file-size guard (unchanged by this branch).
2. `make smoke` — confirms the new target itself boots cleanly end-to-end.
3. Manually confirmed `require_plan` fails against the stale completions-era
   `Plan.md` (other files changed, `Plan.md` didn't) and passes once
   `Plan.md` is actually updated.
4. `make agent-review-local` — now exercises lint + smoke + the corrected
   plan-relevance check together.
