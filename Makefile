.PHONY: dev lint lint-docs test test-integration agent-review-local agent-review-cloud

dev:
	uv run uvicorn app.main:app --reload --port $${APP_PORT:-8000}

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

# Fast, cheap pass: lint + a Haiku-powered check that the diff matches Plan.md.
# Run this first, in a loop, while implementing.
agent-review-local:
	@bash scripts/agent_review_local.sh

# Deeper pass: an isolated, read-only Sonnet/Opus reviewer subagent checks the
# diff against Plan.md and the linked GitHub issue's acceptance criteria.
# Run this once agent-review-local passes clean.
agent-review-cloud:
	@bash scripts/agent_review_cloud.sh
