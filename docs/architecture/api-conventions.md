# API Conventions

## Layering (enforced by lint — see AGENTS.md)
routes -> schemas -> services -> repository -> db

Each layer may only import from itself or the layer directly below it.
`app/routes/` must never import anything from `app/db/`.

## Async
All I/O (DB calls, future external calls) is async. Repository methods are
`async def` and use `await session.execute(...)` / `await session.commit()`.

## Schemas vs DB models
`app/db/models.py` defines SQLModel `table=True` classes (the actual Postgres
tables). `app/schemas/` defines separate request/response models — the DB
model is never returned directly from a route, to avoid leaking internal
fields and to allow request/response shapes to diverge from storage shape.

## Error responses
Validation errors return HTTP 422 with a field-level message. Not-found
returns 404. No raw stack traces in response bodies.
