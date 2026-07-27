# Plan: Issue #25 — Add ARCHITECTURE.md

## Problem
`docs/architecture/` only has two narrow docs (`api-conventions.md` for
layering rules, `agent-providers.md` for the agent-provider dispatch
decision). There's no single birds-eye-view document of the system for
someone new to the repo. `AGENTS.md` covers adjacent ground but is written
as operating instructions for agents working *in* the repo, not an
architecture overview.

## Change
Add `docs/architecture/ARCHITECTURE.md`, a new top-level overview doc that
links out to existing docs rather than duplicating them. Sections:

1. **System summary** — one paragraph: Python 3.14 / FastAPI / SQLModel
   (async) / Postgres habit-tracking API.
2. **Request flow** — `routes -> schemas -> services -> repository -> db`,
   one line per layer's responsibility, linking to
   `docs/architecture/api-conventions.md` for the enforced rules rather
   than repeating them.
3. **Domains** — currently just `habits` (covers the `completions`
   sub-resource too); link to `docs/domains/habits/README.md`.
4. **Deployment topology** — prod: Render, via `render.yaml`
   (`habit-tracker-api` web service + `habit-tracker-db` Postgres,
   deployed only through `.github/workflows/deploy.yml` on push to `main`,
   `autoDeploy: false` so it can't race ahead of required checks); local:
   `make dev` (docker-compose brings up Postgres + Prometheus, uvicorn runs
   on the host).
5. **Observability** — `/health` (real `SELECT 1`), `/metrics`
   (Prometheus text format, `http_requests_total` /
   `http_request_duration_seconds` labeled by method/handler/status), local
   Prometheus UI via `make dev`, `make metrics-query`. Note: no logging
   pipeline yet.
6. **Automation pipeline map** — one line each for agent-ticket,
   agent-followup, doc-gardener, garbage-collector, quality-grader (what
   triggers each, whether it can auto-merge) with an explicit pointer to
   `AGENTS.md`'s "CI/CD" section for full detail — not a copy of it.

## Cross-links
- `README.md`: add a line pointing to `docs/architecture/ARCHITECTURE.md`.
- `AGENTS.md`'s "Where things live" section: add a bullet pointing to
  `docs/architecture/ARCHITECTURE.md` as the birds-eye overview, alongside
  the existing `docs/architecture/` line.

## Out of scope
- Rewriting `api-conventions.md` or `agent-providers.md`.
- `docs/adr/` (#26), doc-gardener extension (#28), or any other
  issue #26-#29 work — other sessions own those; not touching them even
  though issue bodies cross-reference this doc.

## Verification
- `make lint` (file-size limit applies; keep the doc well under 400 lines
  by linking out instead of duplicating).
- `make test`
- `make agent-review-local`, then `make agent-review-cloud` once clean.
- No runtime code touched, so `make smoke` is not required by AGENTS.md's
  loop ("if you touched anything runtime-relevant"); skipping it here.
