#!/usr/bin/env bash
# make smoke: actually boots the app the way `make dev` does and hits /health
# (which runs a real `SELECT 1` against Postgres), then tears down.
#
# Exists because agent-review-local/cloud only ever read the diff as text
# (local: --tools "", no tools at all; cloud: Read/Glob/Grep, no Bash) --
# neither can ever catch a runtime/process-lifecycle bug (crash on a missing
# env var, docker-compose not up, a stale process still bound to the port)
# since those only manifest by actually running the command. This is the
# fast, cheap way to do that: a real uvicorn subprocess against a real
# docker-compose Postgres, then a clean teardown.
#
# Runs on SMOKE_PORT (default 8098), deliberately not APP_PORT, so it doesn't
# collide with an already-running `make dev` session in another terminal.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

SMOKE_PORT="${SMOKE_PORT:-8098}"

if lsof -nP -iTCP:"$SMOKE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "smoke: port $SMOKE_PORT is already in use. Set SMOKE_PORT to a free port and retry." >&2
    exit 1
fi

echo "==> docker-compose up -d"
docker-compose up -d

UVICORN_PID=""
cleanup() {
    if [[ -n "$UVICORN_PID" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
        kill "$UVICORN_PID" 2>/dev/null || true
        wait "$UVICORN_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "==> starting uvicorn on :$SMOKE_PORT"
direnv exec . uv run uvicorn app.main:app --port "$SMOKE_PORT" &
UVICORN_PID=$!

deadline=$((SECONDS + 20))
until curl -sf "http://127.0.0.1:${SMOKE_PORT}/health" >/dev/null 2>&1; do
    if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
        echo "smoke: FAIL -- uvicorn process exited before /health responded." >&2
        exit 1
    fi
    if (( SECONDS > deadline )); then
        echo "smoke: FAIL -- /health did not respond within 20s." >&2
        exit 1
    fi
    sleep 0.5
done

echo "smoke: PASS (/health responded on :$SMOKE_PORT, DB connection confirmed)"
