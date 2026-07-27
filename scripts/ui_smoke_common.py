"""Shared helpers for Playwright-driven ui-smoke checks.

Any check that drives a real headless browser -- `scripts/ui_smoke_check.py`
today (`/docs`), a future dashboard check per #36 (`/dashboard`), or anything
else added later -- can call `capture_screenshot()` below instead of
reimplementing capture logic. This is issue #37's "reusable screenshot
helper": it exists so visual proof for UI-touching PRs (see AGENTS.md's "How
to verify your work") is one function call, not copy-pasted `page.screenshot`
boilerplate per check.

Screenshots are local-only proof-of-work artifacts: written under a
git-ignored directory (`.ui-smoke-artifacts/`, see `.gitignore`), never
committed, never read back by any check or CI job. A human/agent attaches
them to the PR description by hand as evidence a UI-touching change was
actually driven through a real browser.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

# Repo root is this file's grandparent (scripts/ui_smoke_common.py -> scripts/ -> root).
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / ".ui-smoke-artifacts"


def capture_screenshot(page: "Page", check_name: str, step: str) -> Path:
    """Save a timestamped full-page PNG of `page`'s current state.

    Written to `<repo-root>/.ui-smoke-artifacts/<check_name>-<step>-<UTC
    timestamp>.png`. `check_name` identifies which ui-smoke check took the
    shot (e.g. "docs"); `step` identifies which point in that check's flow
    (e.g. "loaded", "try-it-out"). Both are free-form but should stay
    filesystem-safe (no `/`).

    Returns the path written, so callers can log/print it for the human/agent
    who'll attach it to the PR description.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    path = ARTIFACTS_DIR / f"{check_name}-{step}-{timestamp}.png"
    page.screenshot(path=str(path), full_page=True)
    return path
