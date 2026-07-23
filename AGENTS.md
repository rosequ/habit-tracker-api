# AGENTS.md

## What this repo is
Habit Tracker API. Python 3.14, FastAPI, SQLModel (async), Postgres.

## Where things live
- docs/architecture/ — layering rules, conventions
- docs/domains/<name>/ — one README per business domain (e.g. habits)
- app/routes/ — HTTP layer only
- app/schemas/ — request/response shapes
- app/services/ — business logic
- app/repository/ — the ONLY layer allowed to touch app/db/
- app/db/ — engine, session, SQLModel table definitions

## Non-negotiable rules (enforced by lint, not memory)
- Dependency direction: routes -> schemas -> services -> repository -> db
- No raw SQL or DB session objects outside app/repository/
- No business logic in app/routes/ — routes call services, nothing else
- File size limit: 400 lines (split instead of suppressing)

## How to verify your work
- `make test`  — unit + structural tests
- `make dev`   — brings up docker-compose (db, prometheus) and boots the app
  for this worktree (uses .envrc DB/port namespace)
- `make smoke` — actually boots the app (docker-compose + uvicorn) on
  `SMOKE_PORT` (default 8098, separate from `APP_PORT` so it won't collide
  with a `make dev` you already have running) and hits `/health`, which runs
  a real `SELECT 1`. Catches runtime crashes -- missing env vars, docker-compose
  not up, a stale process still bound to the port -- that a text-only diff
  review can never see, because they only manifest by actually running the
  command.
- `make lint`  — ruff + import-linter + file-size check; read the error, it tells you the fix
- `make agent-review-local` — fast/cheap: lint + smoke + flags diff not covered by Plan.md
- `make agent-review-cloud` — deeper: an isolated read-only reviewer checks the diff
  against Plan.md and the linked GitHub issue's acceptance criteria

Both require a committed `Plan.md` at the repo root that actually describes
*this* branch's changes -- `require_plan` (in `scripts/review_common.sh`) fails
if other files changed since `main` but `Plan.md` didn't, so a stale plan left
over from a previous feature/worktree can't silently rubber-stamp unrelated
work as "planned." Both also require the `claude` CLI installed and
authenticated separately (they shell out to it). Loop: implement ->
`agent-review-local` -> fix -> repeat until clean -> `agent-review-cloud` ->
address comments -> repeat.

## Branching
This is a private repo on GitHub's Free plan, which doesn't support server-side
branch protection at all (see issue #7) -- there is nothing stopping a direct
`git push` to `main`, or a push of any branch that skips lint/tests/review.
As a stopgap, run `git config core.hooksPath .githooks` once per clone: it
installs two client-side hooks (still bypassable locally -- `--no-verify`,
or just not enabling `core.hooksPath` -- same limitation as the branch
protection gap above):
- `pre-commit` — refuses to commit if `make lint` fails. Override once with
  `SKIP_COMMIT_LINT=1 git commit ...`.
- `pre-push` — refuses to push directly to `main` (override once with
  `ALLOW_PUSH_TO_MAIN=1 git push ...` if you really mean to; only bypasses
  the main-push block, not the check below). Separately, refuses to push
  **any** branch unless `make lint`, `make test`, and
  `make agent-review-local` all pass first (a pure branch deletion is
  exempt -- nothing to check). This runs on every push, including small WIP
  ones -- it boots Postgres via docker-compose, a real `uvicorn` process,
  and a `claude -p` call, so expect it to take a while and to need the
  `claude` CLI installed/authenticated. Override once with
  `SKIP_PUSH_VERIFICATION=1 git push ...`. Pushing a tag hits this same
  gate (anything with a non-zero local SHA does), not just branches.
  `make agent-review-cloud` deliberately is NOT part of this gate -- it's
  meant to run once, deliberately, before asking a human to review a PR,
  not on every push of routine work.

Always work on a branch and open a PR instead of pushing to `main` directly.

## Observability (local)
- `/metrics` — Prometheus text-format metrics on the running app, wired
  directly on `app` like `/health`. `http_requests_total` and
  `http_request_duration_seconds` are both labeled by `method`, `handler`
  (route), and `status`.
- `make dev` starts a local Prometheus (via docker-compose) that scrapes
  `host.docker.internal:$APP_PORT/metrics` (the app itself runs on the host,
  not in docker-compose). UI at
  `http://localhost:$PROMETHEUS_PORT` (see `.envrc`'s `PROMETHEUS_PORT`).
- `make metrics-query QUERY='...'` — runs a PromQL instant query, prints the
  raw number only (no JSON). Examples:
  - p95 latency: `make metrics-query QUERY='histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'`
  - request rate: `make metrics-query QUERY='sum(rate(http_requests_total[5m]))'`
  - error rate by status: `make metrics-query QUERY='sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))'`
- No logging pipeline yet — metrics only. Future work.

## Escalate to a human when
- Change touches auth, billing, or data retention
- Change requires a new external dependency
- You are not confident the fix addresses the root cause

## CI/CD (.github/workflows/)
- `ci.yml` — on every PR: `fast-gates` (lint, test, gitleaks secret scan) is
  the required check that blocks merge. `async-verification` runs
  `make test-integration` after `fast-gates` but is non-blocking, and on
  failure dispatches `agent-followup.yml`. `doc-freshness` runs
  `make lint-docs` (non-blocking placeholder).
- `agent-followup.yml` — dispatched on integration-test failure (which can
  surface after the PR already merged, since the check is non-blocking).
  Headless Claude Code fixes forward on a new branch off `main` and opens a
  PR labeled `needs-human-review`. Never pushes to `main` directly, never
  merges.
- `agent-ticket.yml` — dispatched when an issue is labeled `agent-ready`.
  Headless Claude Code implements the issue on a new branch, writes tests,
  and self-verifies with `make lint`/`test`/`test-integration` before the
  workflow independently re-runs the same three and opens a PR labeled
  `needs-human-review`. Never merges, regardless of check status.
- `deploy.yml` — on push to `main` (which requires `fast-gates` to have
  passed), triggers a Render deploy via deploy hook.

Every agent-authored PR from the two workflows above is labeled
`needs-human-review` — a human always reviews before merging, no exception.
