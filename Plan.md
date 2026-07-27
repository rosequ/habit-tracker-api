# Plan: Add a minimal habits dashboard for agent-browser QA (#36), reconciled with #37's screenshot helper

## Context

The only "UI" this API had before this branch was FastAPI's auto-generated
Swagger page at `/docs` (see #35/#29). That's fine for exercising individual
endpoints in isolation, but there was nothing a browser-automation agent
could click through the way an actual user would: fill a form, submit,
watch a list update, mark something done. All the backend pieces this issue
needed already existed and were merged to `main` (`POST /habits`,
`GET /habits`, `GET /habits/{id}`, `POST /habits/{id}/completions`).

A sibling issue, #37 ("require agent-browser screenshot proof for any PR
that touches UI"), was implemented concurrently in a separate worktree, by
design -- neither branch blocked on the other. #37 built a generic, reusable
Playwright screenshot-capture helper (`scripts/ui_smoke_common.py`) and
wired it into the `/docs` check. This branch originally shipped its own
self-contained screenshot logic in `check_dashboard()` instead of waiting
for that helper, writing PNGs straight to a local `artifacts/ui-smoke/`
directory.

Both PRs are now implemented: #37 landed the shared helper (PR #38), and
this branch (PR #39) has merged that work in and reconciled the overlap --
see "Reconciliation with #37" below. `scripts/ui_smoke_check.py` no longer
has two separate, divergent screenshot implementations; there is one.

## What this branch changes (issue #36's dashboard)

- **`app/static/index.html`** -- new, vanilla HTML/JS dashboard, no build
  step, no framework, no external dependencies (per the issue's explicit
  scope). On load, fetches `GET /habits` and renders each as a card (name,
  category, daily target). A form posts to `POST /habits` and appends the
  new habit to the DOM directly from the response -- no page reload, no
  re-fetch of the whole list. Each habit card has a "Mark done today"
  button that posts to `POST /habits/{id}/completions` with an empty body
  (the API defaults `completion_date` to today server-side) and reflects
  the result inline: green "Done today ✓" on 201, amber "Already done
  today" on the existing 409, or a red error message otherwise (also used
  for 422s from the add-habit form, using the same field-level `detail`
  shape `app/schemas/` already returns).
- **`app/main.py`** -- mounts `app/static/` at `/dashboard` via
  `fastapi.staticfiles.StaticFiles(..., html=True)`, so `GET /dashboard`
  serves `index.html`. This is the only backend change: no new
  `app/routes/`, `app/services/`, `app/repository/`, or `app/db/` code, no
  new business logic -- purely an additive static mount, same
  layering-neutral pattern `/health` already uses directly in `main.py`.
- **`tests/test_dashboard.py`** -- two focused tests: the dashboard route
  serves HTML containing the add-habit form and habit list (both with and
  without the trailing slash StaticFiles redirects to). Deliberately not
  testing markup/styling beyond "the hooks the JS and Playwright rely on
  exist" -- the interactive behavior itself is exercised by `make
  ui-smoke`, not `make test`, since it needs a real browser.
- **`scripts/ui_smoke_check.py`** -- refactored the existing `/docs` check
  into `check_docs()` and added `check_dashboard()`: loads `/dashboard`,
  screenshots the empty/loaded state, fills and submits the add-habit form,
  waits for the new habit to appear in the DOM (asserts no reload occurred
  and no error banner shown), screenshots that state, clicks "Mark done
  today", waits for the green success text, and takes a third screenshot.
  Each check uses its own `Page` (and its own console-error listener) so a
  JS error on one page can't be misattributed to the other.
- **`scripts/ui_smoke.sh`** -- added `alembic upgrade head` right after
  `docker-compose up -d`. `make smoke`/the old `/docs`-only check never
  needed this since `/health` only runs `SELECT 1`, but the dashboard check
  does real `POST /habits`/`POST .../completions` calls that need the
  actual tables to exist.
- **`Makefile`** / **`AGENTS.md`** -- updated the `ui-smoke` descriptions to
  mention the dashboard check.
- **`.envrc`** (gitignored, per-worktree, not part of this diff) -- set
  `DB_PORT=5536` / `APP_PORT=8136` / `PROMETHEUS_PORT=9136` for this
  worktree, since every port in the low 5430s/9090s/8000s range was already
  claimed by other concurrently-running worktrees on this machine.
- **`docs/screenshots/issue-36/`** -- three PNGs (before-add / after-add /
  marked-done) copied here and committed once, specifically so the PR
  description for #36 can embed them via a `raw.githubusercontent.com` URL
  pinned to a commit SHA -- GitHub PR bodies can't inline a local,
  gitignored file. This is a one-time proof-of-work snapshot for the PR
  body, unrelated to and untouched by the reconciliation below; it stays
  where it is.

## What merged in from #37 (shared screenshot helper + policy)

- **`scripts/ui_smoke_common.py`** (new) -- `capture_screenshot(page,
  check_name, step)`: saves a timestamped full-page PNG to the git-ignored
  `.ui-smoke-artifacts/` directory at the repo root
  (`<check_name>-<step>-<UTC timestamp>.png`) and returns the path written.
  No check-specific logic lives here.
- **`scripts/ui_smoke_check.py`**'s `/docs` check -- calls
  `capture_screenshot` at two points: right after the page is confirmed
  rendered (step `"loaded"`) and right after "Try it out" returns a real
  response (step `"try-it-out"`). Assertions, control flow, and exit codes
  are unchanged from the pre-#37 `/docs` check.
- **`.gitignore`** -- `.ui-smoke-artifacts/` so these screenshots are never
  accidentally committed.
- **`AGENTS.md`** -- the "UI-touching PRs need visual proof" convention:
  any PR touching UI-facing code (`app/static/**`, any templates dir, or
  FastAPI app-metadata affecting what `/docs` renders) should run the
  relevant `ui-smoke` check and attach the resulting `.ui-smoke-artifacts/`
  screenshots to the PR description as proof. Also updates the one-line
  `make agent-review-local` description to mention the new warning.
- **`scripts/review_common.sh`** -- `UI_PATH_PATTERN` (matches
  `app/static/**`, any `templates/` dir, `app/main.py`) and
  `warn_ui_screenshot_proof()`: if the branch diff touches a UI-facing path
  but neither `Plan.md` nor the open PR body mentions
  "screenshot"/"ui-smoke"/"ui_smoke", it prints a warning to stderr. Never
  exits non-zero -- a nudge, not a hard block. Can't check that a
  screenshot *file* actually exists, since `.ui-smoke-artifacts/` is
  git-ignored and so never appears in any diff this function inspects.
- **`scripts/agent_review_local.sh`** -- calls `warn_ui_screenshot_proof`
  once, right after `require_plan`, before the Plan.md-coverage LLM check.

## Reconciliation with #37

Both branches independently modified `scripts/ui_smoke_check.py`; #36's
`check_dashboard()` had its own ad hoc `page.screenshot(...)` calls into a
separate `artifacts/ui-smoke/` directory, while #37 added
`ui_smoke_common.capture_screenshot()` writing to `.ui-smoke-artifacts/`.
Merging #37 into this branch and reconciling the overlap did:

- `check_docs()` now matches #37's version exactly: imports and calls
  `capture_screenshot(page, "docs", "loaded")` and
  `capture_screenshot(page, "docs", "try-it-out")` at the same two points
  #37 placed them.
- `check_dashboard()` keeps its own dashboard-specific logic (form fill,
  submit, mark-done) but its three screenshot calls now go through
  `capture_screenshot(page, "dashboard", "before-add")` /
  `"after-add"` / `"marked-done"` instead of raw `page.screenshot(...)`
  calls. The local `ARTIFACTS_DIR = .../"artifacts"/"ui-smoke"` constant
  and its manual `.mkdir()` call are gone -- the helper creates the
  directory itself. The final "PASS" print now references
  `ui_smoke_common.ARTIFACTS_DIR`.
- There is exactly one gitignored screenshot-artifacts directory now:
  `.ui-smoke-artifacts/`. The `artifacts/` entry from #36's `.gitignore`
  diff is gone; `artifacts/` is never created by anything in this repo
  anymore.
- `Makefile`'s `ui-smoke` target comment now says `.ui-smoke-artifacts/`
  instead of `artifacts/ui-smoke/`, and notes screenshots come from both
  flows via `capture_screenshot()`.
- `AGENTS.md`'s `make ui-smoke` bullet was rewritten as one description
  (not a concatenation of both branches' edits): boots the app +
  `alembic upgrade head`, drives a headless browser against `/docs` and
  `/dashboard`, what each check verifies, and that every screenshot (five
  per run: two from `/docs`, three from `/dashboard`) goes through
  `capture_screenshot()` into `.ui-smoke-artifacts/`. #37's separate
  "UI-touching PRs need visual proof" bullet and its `make
  agent-review-local` one-liner update are unchanged.

## Out of scope (per the issue)

- Editing/deleting habits, filtering, streaks/charts, auth, styling
  polish.
- Wiring `ui-smoke` into CI (stays local-only, same as #29's resolved
  scope).
- Any hard CI gate or `.github/workflows/*` change for the screenshot-proof
  convention (#37 is explicit: stays local-only, matching #29's resolved
  scope).
- Verifying a screenshot file actually exists on disk from
  `agent-review-local` -- structurally can't, since the artifacts directory
  is git-ignored; the warning is a prose-mention nudge only.

## Verification

- `make lint` -- passes (ruff, import-linter layering contract, file-size
  check).
- `make test` -- passes, including the two `tests/test_dashboard.py` tests.
- `make ui-smoke` -- passes: both the `/docs` check and the `/dashboard`
  check (form fill/submit, list update without reload, "Mark done today"
  success state). Confirmed `.ui-smoke-artifacts/` contains five PNGs after
  a run (`docs-loaded-*`, `docs-try-it-out-*`, `dashboard-before-add-*`,
  `dashboard-after-add-*`, `dashboard-marked-done-*`), and that `artifacts/`
  is not recreated.
- `make agent-review-local` / `make agent-review-cloud` before push/PR.
