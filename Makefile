.PHONY: dev lint test agent-review-local agent-review-cloud

dev:
	uv run uvicorn app.main:app --reload --port $${APP_PORT:-8000}

lint:
	uv run ruff check .
	uv run lint-imports
	uv run python scripts/check_file_sizes.py

test:
	uv run pytest

# Fast, cheap pass: lint + a Haiku-powered check that the diff matches Plan.md.
# Run this first, in a loop, while implementing.
agent-review-local:
	@bash scripts/agent_review_local.sh

# Deeper pass: an isolated, read-only Sonnet/Opus reviewer subagent checks the
# diff against Plan.md and the linked GitHub issue's acceptance criteria.
# Run this once agent-review-local passes clean.
agent-review-cloud:
	@bash scripts/agent_review_cloud.sh
