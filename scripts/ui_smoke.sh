#!/usr/bin/env bash
# make ui-smoke: boots the app the same way `make smoke` does, then drives a
# real headless Playwright browser against the Swagger UI (/docs) instead of
# curl-ing /health directly.
#
# Exists because `make smoke` -- and every other check in this repo -- only
# ever talks to the API directly over HTTP or reads the diff as text. None of
# them can catch a broken Swagger UI render, a browser console error, or a
# route that renders fine in the docs page but 500s when a user actually
# clicks "Try it out" -- those only manifest by driving a real browser
# against a real running app. See scripts/ui_smoke_check.py for the
# Playwright side.
#
# Local-only by design (see Plan.md) -- not wired into .github/workflows/*.
# Requires `uv run playwright install chromium` once before first use.
#
# Runs on UI_SMOKE_PORT (default 8099), distinct from both APP_PORT and
# SMOKE_PORT so all three can run at the same time without colliding.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

UI_SMOKE_PORT="${UI_SMOKE_PORT:-8099}"

if lsof -nP -iTCP:"$UI_SMOKE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "ui_smoke: port $UI_SMOKE_PORT is already in use. Set UI_SMOKE_PORT to a free port and retry." >&2
    exit 1
fi

echo "==> docker-compose up -d"
# Deliberately `direnv exec .` here, unlike smoke_test.sh's plain
# `docker-compose up -d`: without it, docker-compose falls back to
# docker-compose.yml's default ports (5432/9090) instead of this worktree's
# .envrc ones, which collides with any other worktree's stack already
# running on those defaults.
direnv exec . docker-compose up -d

UVICORN_PID=""
cleanup() {
    if [[ -n "$UVICORN_PID" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
        kill "$UVICORN_PID" 2>/dev/null || true
        wait "$UVICORN_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "==> starting uvicorn on :$UI_SMOKE_PORT"
direnv exec . uv run uvicorn app.main:app --port "$UI_SMOKE_PORT" &
UVICORN_PID=$!

deadline=$((SECONDS + 20))
until curl -sf "http://127.0.0.1:${UI_SMOKE_PORT}/health" >/dev/null 2>&1; do
    if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
        echo "ui_smoke: FAIL -- uvicorn process exited before /health responded." >&2
        exit 1
    fi
    if (( SECONDS > deadline )); then
        echo "ui_smoke: FAIL -- /health did not respond within 20s." >&2
        exit 1
    fi
    sleep 0.5
done

echo "==> driving Playwright against /docs"
direnv exec . uv run python scripts/ui_smoke_check.py "http://127.0.0.1:${UI_SMOKE_PORT}"
