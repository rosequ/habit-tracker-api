.PHONY: dev lint test test-integration

dev:
	uv run uvicorn app.main:app --reload --port $${APP_PORT:-8000}

lint:
	uv run ruff check .
	uv run lint-imports

test:
	uv run pytest tests --ignore=tests/integration

test-integration:
	uv run pytest tests/integration
