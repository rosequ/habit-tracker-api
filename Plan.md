# Plan: Redesign the habits dashboard's visual layer (#41)

## Context

#36 (PR #39, not yet merged) added a functional but visually bare-bones
habits dashboard at `app/static/index.html`: default system font, a fixed
`640px` centered column, plain bordered `<li>` boxes for habit cards, no
color palette beyond a couple of inline status colors, no elevation, no
responsive behavior below the fixed column, no loading/transition states,
no dark mode. #41 redesigns the visual layer only, on top of #36 -- no new
backend data, no new endpoints, no framework/build step. Because `main`
doesn't have `app/static/index.html` yet, this branch (`agent/issue-41`)
is stacked on `agent/issue-36`, not `main`, and its PR targets
`agent/issue-36` (PR #39) rather than `main`.

(Note for anyone diffing this branch against `main` rather than against
`agent/issue-36`'s pre-#41 tip: since #41's PR targeted and already merged
into this same branch/PR -- not `main` directly -- the diff vs `main` also
still contains all of #36's original dashboard work described above
(`app/static/index.html`'s existence, its mount in `app/main.py`,
`tests/test_dashboard.py`), not just this redesign. That's expected: #36
and #41 land in `main` together, as one PR (#39).)

## What this branch changes

Everything is in **`app/static/index.html`** only (markup/CSS/JS) -- no
touches to `app/routes/`, `app/services/`, `app/repository/`, or
`app/db/`, matching the issue's explicit scope boundary.

1. **Design tokens** -- a `:root` block of CSS custom properties for
   color, an 8-step spacing scale, a small type scale, radius steps, and
   three shadow/elevation levels. Every rule in the file references a
   token instead of a one-off value.
2. **Habit cards** -- `.habit-item` is now an elevated card
   (`box-shadow`, hover lift) inside a responsive CSS grid
   (`repeat(auto-fill, minmax(min(100%, 260px), 1fr))`), not a bordered
   `<li>`. Category is rendered as a `.category-chip` pill whose color is
   derived from the category string via a small `hashHue()` function
   (character-code hash -> `hue % 360`, applied as an inline
   `--chip-h` custom property) -- no new data, same category always maps
   to the same hue. Background/text lightness gap is fixed regardless of
   hue, which keeps contrast well within WCAG AA for any category.
3. **Interaction states** -- `setButtonLoading()` disables the button,
   toggles an `.is-loading` class (hides the label, shows a CSS spinner
   via `::after`), and sets `aria-busy` for the duration of the
   add-habit and mark-done fetches, restoring it in a `finally` block so
   it resets even on error. A newly-added habit card gets a
   `habit-item--enter` class driving a `card-in` keyframe
   (fade + slight rise), removed after `animationend`; respects
   `prefers-reduced-motion`. `.completion-status` and the add-habit error
   are restyled as pill/banner badges (`.completion-status.success` /
   `.already-done` / `.error`, `.alert-danger`) instead of plain colored
   text.
4. **Empty state** -- `#habit-list-empty` (still the same id/hidden
   toggle logic) is now a designed empty state: icon, heading, short
   copy, and an "Add a habit" link that focuses the name input.
5. **Responsive layout** -- `.page` uses a fluid `width: min(880px,
   100%)` with `clamp()` padding instead of a fixed `640px` column; the
   habit grid and add-habit form naturally collapse to a single column
   on narrow viewports. Verified down to a 375px-wide viewport (see
   Verification below).
6. **Accessibility** -- a global `:focus-visible` rule gives every
   interactive element (inputs, buttons, the empty-state link) a visible
   focus ring; palette pairs (text/background, chip text/background,
   badge text/background) were chosen for WCAG AA contrast; the existing
   `role="alert"` on `#add-habit-error` and `aria-live="polite"` on
   `.completion-status` are unchanged and still correct after the
   restyle, plus `aria-busy` is now set on buttons during in-flight
   requests.
7. **Dark mode** -- a `prefers-color-scheme: dark` block overrides the
   color tokens (surface, text, status, chip lightness values) with a
   dark palette; spacing/type/radius tokens are unchanged since they're
   not color-dependent.

All DOM hooks `scripts/ui_smoke_check.py`'s `check_dashboard()` and
`tests/test_dashboard.py` depend on are unchanged: `#add-habit-form`,
`#habit-name-input`, `#habit-daily-target-input`, `#habit-category-input`,
`#add-habit-submit`, `#add-habit-error`, `.habit-item`, `.mark-done-btn`,
`.completion-status`, `#habit-list`/`#habit-list-empty`. Only their
styling and, where noted, their internal wrapper markup (e.g. a
`<div class="field">` around each label/input instead of a nested
`<label>`) changed -- ids, classes, and `data-habit-id` attributes did
not.

## Explicitly out of scope (per the issue)

- No progress ring/indicator implying same-day multi-completions --
  `daily_target` is not a same-day completion count (`DuplicateCompletionError`
  caps a habit at one completion per day).
- No streaks or completion history (`GET /habits` returns no completion
  data; see #23, still open).
- No editing/deleting habits, auth, or multi-page routing.
- No backend changes of any kind.

## Verification

- `make lint`
- `make test` (including the existing `tests/test_dashboard.py`, unmodified
  in what it asserts)
- `make ui-smoke` -- `check_dashboard()` passes unmodified in what it
  asserts; screenshots land in `.ui-smoke-artifacts/` per the shared
  `capture_screenshot()` helper (#37).
- A standalone, uncommitted Playwright script captured an additional
  screenshot at a 375px-wide mobile viewport (the `ui-smoke` check only
  screenshots at its default desktop viewport) -- copied into
  `docs/screenshots/issue-41/` for the PR body.
- `make agent-review-local`

## Screenshots

`docs/screenshots/issue-41/` holds the before/after proof for the PR body:

- `before-redesign-desktop.png` -- the old #36 dashboard, for comparison
  (captured by temporarily serving #36's original `index.html` from disk,
  not a code change).
- `after-redesign-desktop-before-add.png` /
  `after-redesign-desktop-after-add.png` /
  `after-redesign-desktop-marked-done.png` -- the redesigned dashboard's
  three states from a real `make ui-smoke` run.
- `after-redesign-empty-state.png` -- the designed empty state (point 4),
  captured from the standalone script below since `check_dashboard()`
  never runs against a truly-empty list.
- `after-redesign-mobile-375.png` -- a ~375px mobile viewport shot (point
  5), from the standalone script noted in Verification since `ui-smoke`
  only screenshots at its default desktop viewport.
- `after-redesign-dark-mode.png` -- the `prefers-color-scheme: dark`
  variant (point 7), also from the standalone script.
