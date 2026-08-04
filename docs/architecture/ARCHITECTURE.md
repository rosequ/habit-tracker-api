# Architecture

A birds-eye view of the Habit Tracker API for anyone new to the system.
This doc links out to the narrower docs it summarizes rather than
duplicating them — treat it as a map, not the source of truth for any one
topic.

## System summary

Python 3.14, FastAPI, SQLModel (async), Postgres. A single-service HTTP
API with one domain so far (`habits`, including its `completions`
sub-resource).

## Request flow

Every request flows through one direction only:

```
routes -> schemas -> services -> repository -> db
```

- `app/routes/` — HTTP layer only: parses requests, calls a service,
  returns a schema. No business logic.
- `app/schemas/` — request/response shapes, separate from the DB models.
- `app/services/` — business logic.
- `app/repository/` — the only layer allowed to touch `app/db/`.
- `app/db/` — engine, session, SQLModel table definitions.

The dependency direction and other enforced rules (no raw SQL outside
`app/repository/`, async I/O throughout, error response conventions) are
documented in full in
[`docs/architecture/api-conventions.md`](api-conventions.md) and enforced
by `make lint` (import-linter layering contract, not just convention).

## Domains

One domain exists today: `habits` (a user-defined habit plus its daily
completions/check-ins). See
[`docs/domains/habits/README.md`](../domains/habits/README.md) for fields,
operations, and business rules. Its routes live in `app/routes/habits.py`,
covering both the `habits` and `completions` resources.

## Deployment topology

**Production** — [Render](https://render.com), configured in
[`render.yaml`](../../render.yaml): a `habit-tracker-api` web service plus a
managed `habit-tracker-db` Postgres instance. `autoDeploy` is deliberately
off — deploys happen only via `.github/workflows/deploy.yml` on push to
`main`, so a deploy can never race ahead of `main`'s checks. See
`AGENTS.md`'s CI/CD section for the `deploy.yml` trigger details.

**Local** — `make dev` brings up `docker-compose.yml` (Postgres +
Prometheus) and runs `uvicorn` on the host (not containerized), namespaced
per-worktree via `.envrc` (`DB_PORT`, `APP_PORT`, `PROMETHEUS_PORT`).
`make smoke` does the same but headless, for a one-shot boot-and-`/health`
check.

## Observability

- `/health` — runs a real `SELECT 1` against Postgres; used as the Render
  health check and by `make smoke`.
- `/metrics` — Prometheus text-format metrics, wired directly on the app.
  `http_requests_total` and `http_request_duration_seconds` are both
  labeled by `method`, `handler`, and `status`.
- `make dev` also starts a local Prometheus that scrapes `/metrics`; UI at
  `http://localhost:$PROMETHEUS_PORT`. `make metrics-query QUERY='...'`
  runs a one-off PromQL query against it.
- No logging pipeline yet — metrics only.

Full detail (label conventions, example PromQL queries) is in `AGENTS.md`'s
"Observability (local)" section.

## Automation pipeline

CI/CD is not just human-triggered: five `.github/workflows/*.yml` jobs run
headless coding agents against this repo. Rough map (see `AGENTS.md`'s
"CI/CD" section for the full detail — triggers, gating, auto-merge
conditions, and the provider-dispatch mechanism):

- `agent-ticket.yml` — implements an issue labeled `agent-ready` on a new
  branch; opens a `needs-human-review` PR, never merges.
- `agent-followup.yml` — dispatched on integration-test failure; fixes
  forward on a new branch, opens a `needs-human-review` PR.
- `doc-gardener.yml` — daily cron; fixes stale/contradictory docs. Can
  auto-merge if the diff stays within `docs/`/`AGENTS.md` and gates pass.
- `garbage-collector.yml` — weekly cron; small architecture-deviation
  refactors. Can auto-merge under tighter conditions (diff size, path
  restrictions).
- `quality-grader.yml` — monthly cron; writes `docs/quality.md`. Never
  auto-merges.

All human and agent PRs alike are gated by `ci.yml`'s `fast-gates` check
(lint, test, gitleaks) — see [`api-conventions.md`](api-conventions.md) for
what lint enforces, and `AGENTS.md` for everything workflow-specific.

## See also

- [`docs/architecture/api-conventions.md`](api-conventions.md) — layering
  and coding rules, enforced by lint.
- [`docs/architecture/agent-providers.md`](agent-providers.md) — how the
  automation pipeline above picks which agent CLI/model to run.
- [`docs/domains/habits/README.md`](../domains/habits/README.md) — the
  `habits` domain in detail.
- `AGENTS.md` — operating instructions for agents working in this repo,
  including the full CI/CD and branching sections summarized above.
