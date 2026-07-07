# Implementation log: Issue #1 — Create a habit

Following Plan.md. Logging steps and issues as they happen.

## Starting state
- `app/db/models.py` (`Habit`) and `app/db/session.py` (engine + `get_database_url()`)
  already existed from prior work.
- Alembic migration for `habits` table already applied.
- docker-compose Postgres for this worktree already running on port 5433
  (`add-habit-create-db-1`).

## Steps taken

1. `app/db/session.py` — added `async_session_maker` (`async_sessionmaker`) and
   a `get_session()` FastAPI dependency (`AsyncGenerator[AsyncSession, None]`)
   on top of the existing engine.
2. `app/repository/habits.py` — new `HabitRepository` (`create`, `get_by_id`)
   plus `get_habit_repository` dependency provider. Only file outside
   `app/db/*` importing `app.db`.
3. `app/services/habits.py` — new `HabitService` (`create_habit`, `get_habit`)
   wrapping `HabitRepository`, plus `get_habit_service` dependency provider.
4. `app/schemas/habits.py` — `HabitCreate` (field constraints matching the
   domain doc) and `HabitRead` (`from_attributes=True`).
5. `app/routes/habits.py` — `POST /habits` (201) and `GET /habits/{habit_id}`
   (200 or 404), importing only schemas + services.
6. `app/main.py` — FastAPI app, includes the habits router. No
   `create_all` — table creation stays owned by Alembic.
7. `pyproject.toml` — added `[tool.pytest.ini_options] asyncio_mode = "auto"`.
8. `tests/conftest.py` — `client` fixture (httpx `AsyncClient` +
   `ASGITransport` against the real app) and an autouse fixture that deletes
   all `habits` rows after each test (cleanup, not `create_all`).
9. `tests/test_habits.py` — 3 tests: create+fetch round trip, 422 on empty
   `name`, 404 on a missing id.

## Issues hit

- **First `make test` run failed** with
  `sqlalchemy.exc.InterfaceError: cannot perform operation: another operation
  is in progress` on the second/third test. Root cause: pytest-asyncio's
  default *function-scoped* event loop creates a new loop per test, but
  `app/db/session.py`'s `engine` (and its asyncpg connection pool) is a
  module-level singleton created once at import time and bound to whichever
  loop was active then — reusing it from a later test under a different loop
  corrupts the underlying asyncpg connection.
  Fix: added `asyncio_default_fixture_loop_scope = "session"` and
  `asyncio_default_test_loop_scope = "session"` to
  `[tool.pytest.ini_options]` in `pyproject.toml`, so the whole test session
  shares one event loop and matches the engine's lifetime. All 3 tests pass
  after this change.

## Verification so far

- `make lint` — ruff clean, import-linter layered architecture contract kept.
- `make test` — 3 passed.

## Manual exercise (docker-compose Postgres, `make dev` on port 8001)

Successful POST:
```
POST /habits {"name": "Read daily", "daily_target": 20, "category": "Learning"}
→ 201 {"id":3,"name":"Read daily","daily_target":20,"category":"Learning","created_at":"2026-07-07T01:15:02.609049Z"}
```

422 validation failure (empty `name`):
```
POST /habits {"name": "", "daily_target": 20, "category": "Learning"}
→ 422 {"detail":[{"type":"string_too_short","loc":["body","name"],"msg":"String should have at least 1 character","input":"","ctx":{"min_length":1}}]}
```

Fetch just-created habit and a 404 case:
```
GET /habits/3      → 200 (same body as the POST response)
GET /habits/999999 → 404 {"detail":"Habit not found"}
```

Server log (uvicorn):
```
INFO:     127.0.0.1:55651 - "POST /habits HTTP/1.1" 201 Created
INFO:     127.0.0.1:55654 - "POST /habits HTTP/1.1" 422 Unprocessable Content
INFO:     127.0.0.1:55655 - "GET /habits/3 HTTP/1.1" 200 OK
INFO:     127.0.0.1:55656 - "GET /habits/999999 HTTP/1.1" 404 Not Found
```

`habits` table schema (`psql \d habits` against the docker-compose Postgres):
```
                                        Table "public.habits"
    Column    |           Type           | Collation | Nullable |              Default
--------------+--------------------------+-----------+----------+------------------------------------
 id           | integer                  |           | not null | nextval('habits_id_seq'::regclass)
 name         | character varying(100)   |           | not null |
 daily_target | integer                  |           | not null |
 category     | character varying(50)    |           | not null |
 created_at   | timestamp with time zone |           | not null |
Indexes:
    "habits_pkey" PRIMARY KEY, btree (id)
```

## Status: done

All Plan.md steps complete: db/session dependency, repository, service, schemas,
routes, `app/main.py`, pytest async config, tests (3 passing), `make lint` and
`make test` green, manual POST/GET/404/422 exercised with logs and table schema
captured above for the PR.
