#!/usr/bin/env bash
# Render start command: migrate then boot the app.
set -euo pipefail

# Render's managed Postgres connectionString uses the plain postgresql://
# scheme. app/db/session.py needs the asyncpg dialect prefix (see .envrc for
# the same convention locally).
export DATABASE_URL="${DATABASE_URL/postgresql:\/\//postgresql+asyncpg:\/\/}"

uv run alembic upgrade head
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
