.PHONY: dev lint test

dev:
	uv run uvicorn app.main:app --reload --port $${APP_PORT:-8000}

lint:
	uv run ruff check .
	uv run lint-imports

test:
	uv run pytest
