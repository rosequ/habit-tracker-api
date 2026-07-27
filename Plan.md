# Plan: Add `make ui-smoke` — Playwright check against the Swagger UI (#29)

## Context

`make smoke` boots the real app and hits `/health` with curl, but nothing
exercises the app the way a human actually browses it: FastAPI's
auto-generated Swagger UI at `/docs` (built from `/openapi.json`). A broken
schema, a JS console error, or a route that renders in the UI but 500s when
"Try it out" is used wouldn't be caught by `make lint`, `make test`, or
`make smoke` — all non-browser.

Issue #29 raised three open questions and left them for the repo owner to
resolve rather than guessing. They've since been confirmed; recording the
decisions and the "why" here per this repo's convention for ADR-worthy calls:

1. **Tooling: Playwright, driven directly (Python).** Added as a dev
   dependency rather than reaching for an MCP-based browser tool. No new
   external service or config to run/maintain, and it stays fully
   deterministic and local — same shape as the rest of this repo's
   verification tooling (pytest, ruff, etc. are all plain Python deps too).
2. **Scope: local-only `make` target, not wired into CI.** Adds
   `make ui-smoke`, analogous to `make smoke`, but does NOT touch
   `.github/workflows/*` — headless-browser binaries are a heavier CI
   dependency than this issue is scoped to justify, and the issue explicitly
   called CI wiring a separate decision.
3. **Blocking: N/A.** Since it's local-only for now, there's nothing in CI
   for it to block; it's an opt-in check a developer runs like `make smoke`.

## What this branch changes

- **`pyproject.toml`** — adds `playwright` to `[dependency-groups].dev`.
- **`scripts/ui_smoke.sh`** — new script, modeled directly on
  `scripts/smoke_test.sh`: boots docker-compose + a real uvicorn on its own
  port (`UI_SMOKE_PORT`, default `8099` — distinct from both `APP_PORT` and
  `SMOKE_PORT` so none of the three collide if run together), waits for
  `/health`, then runs a Playwright script that:
  1. Loads `/docs` headless and asserts it doesn't throw a browser console
     error.
  2. Asserts the rendered page lists the routes we expect (`/health`,
     `/habits`).
  3. Drives Swagger UI's "Try it out" on `GET /health` and asserts a real
     `200` with `"status":"ok"` comes back through the browser, not just
     from a direct HTTP call — this is the part `make smoke` structurally
     can't check, since it only ever calls the API directly.
  4. Tears down the uvicorn process on exit (`trap ... EXIT`), same pattern
     as `smoke_test.sh`.
- **`scripts/ui_smoke_check.py`** — the actual Playwright driver script
  invoked by `ui_smoke.sh` (kept separate from the bash wrapper since the
  browser automation itself is Python, matching how the rest of this repo's
  scripts split shell orchestration from Python logic where relevant).
- **`Makefile`** — new `ui-smoke` target calling `scripts/ui_smoke.sh`, plus
  a comment matching the style of the existing `smoke` target.
- **`AGENTS.md`** — documents `make ui-smoke` next to `make smoke` in "How to
  verify your work", including that it needs
  `uv run playwright install chromium` once (browser binaries aren't a
  Python dependency `uv sync` can fetch on its own).

## Out of scope

- Wiring this into `.github/workflows/*` or `ci.yml` (resolved above — a
  deliberate non-goal of this issue).
- Evaluating MCP-based browser tooling (resolved above).
- Exercising any endpoint beyond one read-only GET through "Try it out" —
  issue #29 only asked for "at least one."
- Issues #25/#26/#27/#28, worked in sibling worktrees.

## Verification

- `make lint` — passes.
- `make test` — unaffected, still passes.
- `make ui-smoke` — new target, run directly to confirm it passes against a
  real local boot (requires `uv run playwright install chromium` once,
  first time).
- `make agent-review-local` / `make agent-review-cloud` before push/PR.
