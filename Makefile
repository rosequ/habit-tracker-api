.PHONY: dev smoke ui-smoke lint lint-docs test test-integration metrics-query agent-review-local agent-review-cloud

dev:
	docker-compose up -d
	direnv exec . uv run uvicorn app.main:app --reload --port $${APP_PORT:-8000}

# Actually boots the app (docker-compose + uvicorn) and hits /health, then
# tears down. Catches runtime crashes (missing env vars, port already in
# use, docker-compose not up) that a text-only diff review can't see.
smoke:
	@bash scripts/smoke_test.sh

# Boots the app the same way `make smoke` does, then drives a real headless
# Playwright browser against both the Swagger UI (/docs) and the habits
# dashboard (/dashboard) instead of curl-ing /health directly -- catches a
# broken UI render, or a route/form that 500s via "Try it out" / the
# add-habit form / "Mark done today", that no other check exercises.
# Screenshots of the dashboard flow land in artifacts/ui-smoke/ (gitignored).
# Local-only (not wired into CI); requires
# `uv run playwright install chromium` once beforehand.
ui-smoke:
	@bash scripts/ui_smoke.sh

lint:
	uv run ruff check .
	uv run lint-imports
	uv run python scripts/check_file_sizes.py

# Placeholder doc-freshness check (non-blocking in CI): AGENTS.md and docs/
# exist and are non-empty. Not a real freshness check yet -- see the script.
lint-docs:
	@bash scripts/check_docs_freshness.sh

test:
	uv run pytest tests --ignore=tests/integration

test-integration:
	uv run pytest tests/integration

# Runs a PromQL instant query against the local Prometheus; prints the raw
# number only. Usage: make metrics-query QUERY='sum(rate(http_requests_total[1m]))'
metrics-query:
	@bash scripts/query_metrics.sh '$(QUERY)'

# Fast, cheap pass: lint + a Haiku-powered check that the diff matches Plan.md.
# Run this first, in a loop, while implementing.
agent-review-local:
	@bash scripts/agent_review_local.sh

# Deeper pass: an isolated, read-only Sonnet/Opus reviewer subagent checks the
# diff against Plan.md and the linked GitHub issue's acceptance criteria.
# Run this once agent-review-local passes clean.
agent-review-cloud:
	@bash scripts/agent_review_cloud.sh
