# Plan: Issue #1 — Create a habit

## Research findings

**Repo state:** `add-habit-create` branched off the initial commit, before the
scaffold (`AGENTS.md`, docs, `app/` package skeleton, `pyproject.toml`, etc.)
was added on `main`. Merged `main` into this branch (fast-forward, no
conflicts) to get the scaffold before starting. `uv sync` installs cleanly;
Python 3.14 + uv are available locally.

**AGENTS.md — non-negotiable rules:**
- Dependency direction: `routes -> schemas -> services -> repository -> db`.
- `app/repository/` is the ONLY layer allowed to touch `app/db/` (no raw SQL
  or session objects elsewhere).
- No business logic in `app/routes/` — routes call services, nothing else.
- File size limit: 400 lines.
- Verify with `make test`, `make dev`, `make lint`.

**api-conventions.md:**
- Layering enforced by `import-linter` (`pyproject.toml`
  `[tool.importlinter]`, contract type `layers`, list `[app.routes,
  app.schemas, app.services, app.repository, app.db]`). I inspected the
  installed `import_linter` contract source directly: layers are ordered
  highest → lowest, and a **higher layer may import any lower layer**
  (not just the adjacent one) — imports are only forbidden in the reverse
  (lower importing higher) direction. `app/routes/` must never import
  `app/db/`.
- All I/O is async (`async def`, `await session.execute/commit`).
- DB models (`app/db/models.py`, `SQLModel table=True`) are distinct from
  `app/schemas/` request/response models — a DB row is never returned
  directly from a route.
- Validation errors → 422 with field-level message; not-found → 404; no raw
  stack traces.

**Key layering implication for this design:** since `app.schemas` sits
*above* `app.services` in the layer list, `app/services/` importing
`app/schemas/` would be a forbidden reverse import. So schemas are consumed
only in `app/routes/` (parsing the request body, shaping the response);
routes unpack the validated Pydantic model into plain primitives before
calling the service. Services and repositories work in plain
values/ORM objects, never Pydantic request/response types.

**docs/domains/habits/README.md — Habit fields:**
- `name`: string, 1–100 chars, required
- `daily_target`: integer, > 0, required
- `category`: string, 1–50 chars, required
- `created_at`: set server-side (app layer), not client-provided
- Out of scope now: update/delete, listing, check-ins/streaks.

**Issue #1 acceptance criteria:**
- `POST /habits` accepts `{name, daily_target, category}`.
- Missing/invalid fields → HTTP 422, field-level error.
- Success → HTTP 201 with `{id, name, daily_target, category, created_at}`.
- Persisted in Postgres `habits` table (not in-memory).
- `GET /habits/{id}` returns the exact habit just created.
- Structural lint definition is pending Lesson 6 — only `ruff` +
  `import-linter` run today.
- Out of scope: update/delete/list/check-ins.
- PR must include: successful POST log, a 422 validation-failure log, and
  the `habits` table schema.

**Environment:** `.envrc` (direnv, already loaded) namespaces this worktree
to `DB_PORT=5433`, `APP_PORT=8001`, pointing at a separate `docker-compose`
Postgres project (default project name = directory name `add-habit-create`,
so it won't collide with the unrelated `habit-tracker-api-db-1` container
already running on port 5432 from another checkout).

**Migrations:** Resolved — a real Alembic migration is expected, not
`create_all`. `app/db/models.py` (`Habit`) and `app/db/session.py` (async
engine + `get_database_url()`) now exist, along with a full Alembic
scaffold (`alembic init -t async alembic`) wired to `SQLModel.metadata` and
`DATABASE_URL`. The initial `create habits table` migration is generated,
reviewed, and applied (`alembic upgrade head`); downgrade/upgrade round-trip
verified against the docker-compose Postgres. Table creation is owned
solely by `alembic upgrade head` from here on — `app/main.py`'s future
lifespan must NOT call `SQLModel.metadata.create_all`.

Note: SQLAlchemy's `greenlet` dependency (required for the async engine's
`run_sync`, which Alembic's async template relies on) has a platform marker
that checks for `aarch64` and misses macOS Apple Silicon's `arm64` — added
`greenlet` explicitly as a direct dependency (`uv add greenlet`) to fix this
on this machine.

## Approach (routes → schemas → services → repository → db)

1. **`app/db/models.py`** — `Habit(SQLModel, table=True)`: `id` (PK,
   optional int), `name` (1–100), `daily_target` (int, gt=0), `category`
   (1–50), `created_at` (datetime, `default_factory=utcnow`).
2. **`app/db/session.py`** — async engine from `DATABASE_URL` env var,
   `async_sessionmaker`, `get_session()` FastAPI dependency (yields
   `AsyncSession`).
3. **`app/repository/habits.py`** — `HabitRepository` with `create(*, name,
   daily_target, category) -> Habit` and `get_by_id(habit_id) -> Habit |
   None`; plus a `get_habit_repository(session=Depends(get_session))`
   FastAPI dependency provider. Only file besides `app/db/*` that imports
   `app.db`.
4. **`app/services/habits.py`** — `HabitService` wrapping a
   `HabitRepository`, exposing `create_habit(*, name, daily_target,
   category)` and `get_habit(habit_id)` (thin pass-through today; this is
   where future business rules land). Plus `get_habit_service(repository=
   Depends(get_habit_repository))` dependency provider. Imports only
   `app.repository`.
5. **`app/schemas/habits.py`** — `HabitCreate` (name/daily_target/category
   with `Field` constraints matching the domain doc, giving free 422s from
   FastAPI/Pydantic) and `HabitRead` (id, name, daily_target, category,
   created_at; `from_attributes=True` so it can be built straight from the
   ORM row). No imports from lower layers.
6. **`app/routes/habits.py`** — `APIRouter(prefix="/habits")`:
   - `POST /habits` → 201, body `HabitCreate`, calls
     `service.create_habit(...)`, returns via `response_model=HabitRead`.
   - `GET /habits/{habit_id}` → 200 `HabitRead`, or raises
     `HTTPException(404)` if the service returns `None`.
   Imports only `app.schemas` and `app.services`.
7. **`app/main.py`** — FastAPI app; lifespan does NOT create tables (that's
   `alembic upgrade head`'s job now); includes the habits router.
   (Composition root, outside the layer contract, so it's the one place
   allowed to touch `app.db` and `app.routes` together.)
8. **Tests (`tests/`)** — pytest-asyncio + httpx `ASGITransport` against the
   real app, backed by the real docker-compose Postgres (matches "not
   in-memory" requirement); a fixture creates tables and cleans up rows
   between tests. Cover: successful create+fetch round trip, and a 422 on
   invalid payload (e.g. empty `name`).
9. Add `[tool.pytest.ini_options] asyncio_mode = "auto"` to `pyproject.toml`
   so async tests run without per-test markers.
10. Bring up `docker-compose up -d` for this worktree, run `make lint` and
    `make test`, then manually exercise `POST /habits` and `GET
    /habits/{id}` (including a bad payload) to capture the logs the PR
    requires.

## Open assumption to flag
~~Using `create_all` instead of an Alembic migration for the `habits`
table.~~ Resolved: real Alembic migrations are used instead (see
"Migrations" above). Remaining feature work (routes, schemas, services,
repository, tests) is still pending — only the DB layer + migration
tooling has been built so far.
