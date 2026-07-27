# Plan: Add description/version to FastAPI app metadata (#35)

## Context

`app/main.py:11` currently constructs the app as
`FastAPI(title="Habit Tracker API")` -- no `description` or `version`.
Swagger UI at `/docs` renders whatever's passed to `FastAPI(...)`'s
`title`/`description`/`version`, so today the docs header shows a bare
title with no description block and no version badge.

## What this branch changes

- **`app/main.py`** -- pass `description` and `version` to the `FastAPI(...)`
  constructor alongside the existing `title`:
  - `version="0.1.0"` -- hardcoded, matching the precedent set in #8; no real
    semantic-versioning scheme exists yet (explicitly out of scope per #35).
  - `description="Track habits and their daily completions."` -- a short,
    real sentence describing the API, not a placeholder.
  - No other constructor arguments, routes, or behavior change.
- **`tests/test_main.py`** -- new unit test asserting `app.title`,
  `app.version`, and `app.description` on the imported FastAPI `app` object,
  so a future accidental revert of this metadata is caught by `make test`
  without needing a browser.
- **`scripts/ui_smoke_check.py`** -- accepts an optional third CLI arg
  (screenshot output path). When given, after `/docs` loads and passes the
  existing console-error check, it takes a Playwright screenshot scoped to
  Swagger UI's `.information-container` (the title/version-badge/description
  block this change affects) and saves it to that path. Purely additive:
  omitting the arg (as `make ui-smoke`'s default invocation does) leaves
  existing pass/fail behavior unchanged.
- **`scripts/ui_smoke.sh`** -- reads an optional `UI_SMOKE_SCREENSHOT` env
  var and forwards it as that third arg to `ui_smoke_check.py`.

## Why the screenshot capability

#35 asks that this PR "actually look at the rendered page" rather than only
inspecting `/openapi.json`, and specifically calls out extending the
existing `make ui-smoke` Playwright tooling (from #29) to capture a
screenshot of the rendered `/docs` header as proof of work, rather than
relying on a pass/fail assertion alone. The optional-arg approach keeps
`make ui-smoke`'s default CI-equivalent behavior (used for pass/fail gating)
identical, while making the screenshot capability reusable instead of a
one-off throwaway script -- this PR's description includes before/after
screenshots produced by running it against `main` and against this branch.

## Out of scope (per #35)

- A real semantic-versioning scheme.
- Wiring `make ui-smoke` (or the new screenshot option) into CI -- it
  remains local-only, per #29's resolved open questions.
- Any route behavior change -- only `FastAPI(...)`'s constructor arguments
  and the `ui-smoke` tooling change.

## Verification

- `make lint` -- passes.
- `make test` -- includes the new `tests/test_main.py`.
- `make agent-review-local` before push.
- `make ui-smoke` run manually with `UI_SMOKE_SCREENSHOT` set, once against
  `main` and once against this branch, to produce the before/after images
  attached to this PR's description.
