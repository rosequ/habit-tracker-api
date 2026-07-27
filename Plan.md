# Plan: Require agent-browser screenshot proof for UI-touching PRs (#37)

## Context

`make ui-smoke` (#29/PR #34) already proves `/docs` renders and "Try it out"
works, but it's pass/fail only -- no artifact is left behind. As UI surface
grows (#36 adds a real dashboard; more will likely follow), there's no
reusable way to capture visual proof from a Playwright run, no
repo-documented expectation that UI-touching PRs include it, and no
automated nudge when a diff changes UI-facing code without any.

This branch implements the three-part proposal from #37 exactly, and
nothing beyond it: no new backend endpoints, no hard CI gate, no changes to
`.github/workflows/*` (stays local-only, matching #29's resolved scope).
The actual habits dashboard (#36) is out of scope here and is being built
concurrently in a separate worktree -- this branch does not depend on it and
does not touch `app/static/` itself; it only teaches the *existing* `/docs`
check to use the new helper, and documents/soft-flags the convention for
whichever PR (almost certainly #36) is the first to add real UI-facing
files.

## What this branch changes

- **`scripts/ui_smoke_common.py`** (new) -- a small, generic
  `capture_screenshot(page, check_name, step)` helper any Playwright-driven
  check can call. Saves a timestamped full-page PNG to the git-ignored
  `.ui-smoke-artifacts/` directory at the repo root
  (`<check_name>-<step>-<UTC timestamp>.png`) and returns the path written.
  No check-specific logic lives here -- it only knows how to name and save a
  file, so #36's future dashboard check (or anything else added later) can
  reuse it as-is instead of reimplementing capture logic.
- **`scripts/ui_smoke_check.py`** -- now imports and calls
  `capture_screenshot` at two points in the existing `/docs` flow: right
  after the page is confirmed rendered (step `"loaded"`) and right after
  "Try it out" returns a real response (step `"try-it-out"`). Assertions,
  control flow, and exit codes are unchanged -- the check still passes or
  fails exactly as before; it just also leaves two screenshots behind on a
  passing run.
- **`.gitignore`** -- adds `.ui-smoke-artifacts/` so these screenshots are
  never accidentally committed.
- **`AGENTS.md`** -- documents the "UI-touching PRs need visual proof"
  convention right next to the existing `make ui-smoke` docs: any PR
  touching UI-facing code (`app/static/**`, any templates dir, or FastAPI
  app-metadata affecting what `/docs` renders) should run the relevant
  `ui-smoke` check and attach the resulting `.ui-smoke-artifacts/`
  screenshots to the PR description as proof. Also updates the one-line
  `make agent-review-local` description to mention the new warning.
- **`scripts/review_common.sh`** -- adds `UI_PATH_PATTERN` (matches
  `app/static/**`, any `templates/` dir, `app/main.py`) and a new
  `warn_ui_screenshot_proof()` function: if the branch diff touches a
  UI-facing path but neither `Plan.md` nor the open PR body mentions
  "screenshot"/"ui-smoke"/"ui_smoke", it prints a warning to stderr. Never
  exits non-zero -- purely a nudge, matching the issue's explicit "warning,
  not a hard block" requirement. Can't check that a screenshot *file*
  actually exists, since `.ui-smoke-artifacts/` is git-ignored by design and
  so never appears in any diff this function inspects either way -- this is
  a prose-mention nudge, not proof-of-work verification.
- **`scripts/agent_review_local.sh`** -- calls `warn_ui_screenshot_proof`
  once, right after the existing `require_plan` call, before the
  Plan.md-coverage LLM check. Purely additive -- doesn't change the script's
  exit code or existing pass/fail behavior.

## Out of scope

- The actual habits dashboard UI (#36) -- separate worktree, separate PR.
- Any hard CI gate or `.github/workflows/*` change (issue is explicit: stays
  local-only, matching #29's resolved scope).
- Verifying a screenshot file actually exists on disk from
  `agent-review-local` -- structurally can't, since the artifacts directory
  is git-ignored; the warning is a prose-mention nudge only, as scoped by
  the issue ("Plan.md / the diff gives no indication screenshot proof
  exists").
- Wiring #36's future dashboard check to this helper -- #37 explicitly
  leaves that reconciliation to a human at merge time, since #36 is being
  built concurrently in a different worktree.

## Verification

- `make lint` -- passes.
- `make test` -- unaffected, still passes.
- `make ui-smoke` -- still passes with the same assertions; now also leaves
  `.ui-smoke-artifacts/docs-loaded-*.png` and
  `.ui-smoke-artifacts/docs-try-it-out-*.png` behind. Confirmed the files
  are actually created after a real run.
- `make agent-review-local` -- confirmed the new `warn_ui_screenshot_proof`
  warning actually fires by temporarily creating a dummy
  `app/static/x.txt` on top of this branch's real diff (no `Plan.md`/PR-body
  mention of "screenshot") and observing the warning print, then removing
  it again before committing -- #37 itself doesn't add any real
  `app/static/` files, so nothing under that path should exist in the
  actual diff this branch commits.
