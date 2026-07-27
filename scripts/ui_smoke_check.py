"""Playwright driver for `make ui-smoke` -- see scripts/ui_smoke.sh.

Two independent checks against the same running app, each using its own
page (and its own console-error listener, so a JS error on one page can't
be misattributed to the other):

1. `check_docs` -- loads the Swagger UI (/docs), confirms it renders with
   the expected routes and no console errors, then drives "Try it out" on
   GET /health to get a real response back through the browser -- the one
   thing `make smoke` structurally can't check, since it only ever calls
   the API directly over HTTP, never through a rendered page.
2. `check_dashboard` -- drives the actual habits dashboard (/dashboard,
   issue #36): fills and submits the add-habit form, confirms the new habit
   appears without a page reload, then clicks "Mark done today" and
   confirms the UI reflects success.

Both checks capture screenshots via `ui_smoke_common.capture_screenshot`,
which writes timestamped PNGs under `ui_smoke_common.ARTIFACTS_DIR`
(`.ui-smoke-artifacts/`, git-ignored) -- see AGENTS.md's "How to verify
your work" for why: this is the visual proof-of-work attached to UI-touching
PRs, not a manually-taken screenshot.
"""

import sys
import time

from playwright.sync_api import Browser, Page, sync_playwright

import ui_smoke_common
from ui_smoke_common import capture_screenshot

EXPECTED_ROUTES = ["/health", "/habits"]
CHECK_NAME_DOCS = "docs"
CHECK_NAME_DASHBOARD = "dashboard"


def check_docs(browser: Browser, base_url: str) -> int:
    console_errors: list[str] = []
    page = browser.new_page()
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    page.goto(f"{base_url}/docs", wait_until="networkidle")
    page.wait_for_selector(".swagger-ui", timeout=10_000)

    if console_errors:
        print(f"ui_smoke: FAIL -- browser console errors on /docs: {console_errors}", file=sys.stderr)
        page.close()
        return 1

    page_text = page.content()
    for route in EXPECTED_ROUTES:
        if route not in page_text:
            print(f"ui_smoke: FAIL -- expected route '{route}' not found on /docs", file=sys.stderr)
            page.close()
            return 1

    loaded_screenshot = capture_screenshot(page, CHECK_NAME_DOCS, "loaded")
    print(f"ui_smoke: screenshot saved to {loaded_screenshot}")

    # Swagger UI's DOM id for an untagged operation is
    # "operations-default-<operationId>" -- FastAPI's operationId for
    # `GET /health` (no `tags=`) is "health_health_get" (confirmed via
    # /openapi.json), not a guessable "<path>_<method>" shorthand. This
    # id, and the response-table classes below, are internal to the
    # swagger-ui bundle FastAPI vendors -- re-check both if `make
    # ui-smoke` starts failing after a FastAPI upgrade.
    health_op = page.locator("#operations-default-health_health_get")
    health_op.click()
    health_op.get_by_role("button", name="Try it out").click()
    health_op.get_by_role("button", name="Execute").click()

    # Two tables match ".responses-table .response-col_description pre" in
    # this DOM: the live "Server response" table (class
    # "live-responses-table") with the real body, and a second static
    # docs table listing possible response codes/schemas (its "Example
    # Value" panel is a generic placeholder, e.g. additionalProp1/2/3 for
    # an untyped dict response) -- scope explicitly to the live one so a
    # DOM-order assumption can't silently grab the wrong pre.
    # The same live table cell also renders a second .microlight <pre> for
    # response *headers* below the body -- .first pins this to the body,
    # which always renders first within the cell.
    response_body = health_op.locator(
        "table.live-responses-table .response-col_description pre.microlight"
    ).first
    response_body.wait_for(timeout=10_000)
    body_text = response_body.inner_text()

    if '"status"' not in body_text or "ok" not in body_text:
        print(f"ui_smoke: FAIL -- unexpected /health response via Try it out: {body_text!r}", file=sys.stderr)
        page.close()
        return 1

    if console_errors:
        print(f"ui_smoke: FAIL -- browser console errors after Try it out: {console_errors}", file=sys.stderr)
        page.close()
        return 1

    try_it_out_screenshot = capture_screenshot(page, CHECK_NAME_DOCS, "try-it-out")
    print(f"ui_smoke: screenshot saved to {try_it_out_screenshot}")

    page.close()
    print("ui_smoke: PASS (/docs rendered, expected routes present, Try it out on GET /health returned a real response)")
    return 0


def _habit_item(page: Page, habit_name: str):
    return page.locator(".habit-item", has_text=habit_name)


def check_dashboard(browser: Browser, base_url: str) -> int:
    console_errors: list[str] = []
    page = browser.new_page()
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    # Unique per run so re-running ui-smoke against a persistent local DB
    # (this script never tears down/resets data -- ui_smoke.sh only tears
    # down the uvicorn process) can't collide with a habit an earlier run
    # already created, which would make the "new habit appears" assertion
    # below pass vacuously against a stale list item instead of the one
    # this run just created.
    habit_name = f"UI Smoke Habit {int(time.time())}"

    page.goto(f"{base_url}/dashboard", wait_until="networkidle")
    page.wait_for_selector("#add-habit-form", timeout=10_000)
    # The page's own initial `loadHabits()` fetch (fired from a plain
    # <script> tag, not from Playwright) races networkidle above -- wait
    # for its result to actually land in the DOM before screenshotting
    # "before", so the before/after pair genuinely brackets the add, not
    # an accidental mid-fetch frame.
    page.wait_for_selector("#habit-list, #habit-list-empty:not([hidden])", timeout=10_000)

    if console_errors:
        print(f"ui_smoke: FAIL -- browser console errors loading /dashboard: {console_errors}", file=sys.stderr)
        page.close()
        return 1

    before_screenshot = capture_screenshot(page, CHECK_NAME_DASHBOARD, "before-add")
    print(f"ui_smoke: screenshot saved to {before_screenshot}")

    page.fill("#habit-name-input", habit_name)
    page.fill("#habit-daily-target-input", "3")
    page.fill("#habit-category-input", "QA")
    page.click("#add-habit-submit")

    new_habit = _habit_item(page, habit_name)
    try:
        new_habit.wait_for(timeout=10_000)
    except Exception:
        print(
            f"ui_smoke: FAIL -- new habit '{habit_name}' did not appear in the list "
            "after submitting the add-habit form",
            file=sys.stderr,
        )
        page.close()
        return 1

    add_error = page.locator("#add-habit-error")
    if add_error.is_visible():
        print(f"ui_smoke: FAIL -- add-habit form showed an error: {add_error.inner_text()!r}", file=sys.stderr)
        page.close()
        return 1

    after_screenshot = capture_screenshot(page, CHECK_NAME_DASHBOARD, "after-add")
    print(f"ui_smoke: screenshot saved to {after_screenshot}")

    new_habit.locator(".mark-done-btn").click()
    status = new_habit.locator(".completion-status")
    try:
        status.filter(has_text="Done today").wait_for(timeout=10_000)
    except Exception:
        print(
            f"ui_smoke: FAIL -- completion status for '{habit_name}' never showed "
            f"success: {status.inner_text()!r}",
            file=sys.stderr,
        )
        page.close()
        return 1

    marked_done_screenshot = capture_screenshot(page, CHECK_NAME_DASHBOARD, "marked-done")
    print(f"ui_smoke: screenshot saved to {marked_done_screenshot}")

    if console_errors:
        print(f"ui_smoke: FAIL -- browser console errors driving /dashboard: {console_errors}", file=sys.stderr)
        page.close()
        return 1

    page.close()
    print(
        "ui_smoke: PASS (/dashboard listed real habits, add-habit form created one live, "
        f"'Mark done today' reflected success -- screenshots in {ui_smoke_common.ARTIFACTS_DIR})"
    )
    return 0


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8099"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        docs_result = check_docs(browser, base_url)
        dashboard_result = check_dashboard(browser, base_url)

        browser.close()

    return 1 if (docs_result or dashboard_result) else 0


if __name__ == "__main__":
    sys.exit(main())
