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
- `make dev`   — boots the app for this worktree (uses .envrc DB/port namespace)
- `make lint`  — ruff + import-linter + file-size check; read the error, it tells you the fix
- `make agent-review-local` — fast/cheap: lint + flags diff not covered by Plan.md
- `make agent-review-cloud` — deeper: an isolated read-only reviewer checks the diff
  against Plan.md and the linked GitHub issue's acceptance criteria

Both require a committed `Plan.md` at the repo root, and the `claude` CLI installed and
authenticated separately (they shell out to it). Loop: implement -> `agent-review-local`
-> fix -> repeat until clean -> `agent-review-cloud` -> address comments -> repeat.

## Escalate to a human when
- Change touches auth, billing, or data retention
- Change requires a new external dependency
- You are not confident the fix addresses the root cause
