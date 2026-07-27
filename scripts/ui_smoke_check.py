"""Playwright driver for `make ui-smoke` -- see scripts/ui_smoke.sh.

Loads the running app's Swagger UI (/docs) in a headless browser, confirms
it renders with the expected routes and no console errors, then drives
"Try it out" on GET /health to get a real response back through the
browser -- the one thing `make smoke` structurally can't check, since it
only ever calls the API directly over HTTP, never through a rendered page.
"""

import sys

from playwright.sync_api import sync_playwright

EXPECTED_ROUTES = ["/health", "/habits"]


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8099"
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
        )

        page.goto(f"{base_url}/docs", wait_until="networkidle")
        page.wait_for_selector(".swagger-ui", timeout=10_000)

        if console_errors:
            print(f"ui_smoke: FAIL -- browser console errors on /docs: {console_errors}", file=sys.stderr)
            browser.close()
            return 1

        page_text = page.content()
        for route in EXPECTED_ROUTES:
            if route not in page_text:
                print(f"ui_smoke: FAIL -- expected route '{route}' not found on /docs", file=sys.stderr)
                browser.close()
                return 1

        # Swagger UI's DOM id for an untagged operation is
        # "operations-default-<operationId>" -- FastAPI's operationId for
        # `GET /health` (no `tags=`) is "health_health_get" (confirmed via
        # /openapi.json), not a guessable "<path>_<method>" shorthand.
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
            browser.close()
            return 1

        if console_errors:
            print(f"ui_smoke: FAIL -- browser console errors after Try it out: {console_errors}", file=sys.stderr)
            browser.close()
            return 1

        browser.close()

    print("ui_smoke: PASS (/docs rendered, expected routes present, Try it out on GET /health returned a real response)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
