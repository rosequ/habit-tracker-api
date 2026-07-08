# Plan: Log a habit completion for a given day (Issue #3)

## Context

Issue #3 (https://github.com/rosequ/habit-tracker-api/issues/3) asks for
`POST /habits/{habit_id}/completions` to record that a habit was done on a
given day. This worktree branches from `origin/main` (PR #2, which already
merged the Habit model, `POST`/`GET /habits`, and the `/health` +
out-of-process integration test infrastructure), so that foundation is
already in place — this plan only adds the completions endpoint on top of
it, following the existing 5-layer architecture.

## Acceptance criteria (from the issue)

- `POST /habits/{habit_id}/completions` with a date (defaults to today if omitted)
- Returns 201 + the created completion record
- Duplicate completion for the same habit + date returns 409 (not a silent upsert)
- Completion date cannot be in the future — 422 if it is
- Habit must exist — 404 if `habit_id` is invalid
- Out of scope: editing/deleting completions, streak calculation

## Existing patterns being reused

The codebase already has a full vertical slice for `Habit`
(`app/db/models.py`, `app/schemas/habits.py`, `app/repository/habits.py`,
`app/services/habits.py`, `app/routes/habits.py`) enforced by an
import-linter "layers" contract (`app.routes` → `app.schemas` →
`app.services` → `app.repository` → `app.db`, higher layers may depend on
lower ones only) and a 400-line-per-file guard
(`scripts/check_file_sizes.py`, run via `make lint`). The completions
feature will add one new file per layer, mirroring `*_habits.py` naming,
rather than growing the existing habit files.

Key existing pieces to reuse directly:
- `app/repository/habits.py::HabitRepository.get_by_id` — used to check the
  habit exists before recording a completion.
- `app/db/session.py::get_session` — the `AsyncSession` dependency, same as
  `HabitRepository`.
- `tests/integration/conftest.py` — already spins up a real `uvicorn`
  subprocess (`live_server` fixture) and truncates all `SQLModel.metadata`
  tables between tests; no changes needed there, just add a new test module.
- `tests/conftest.py::_clean_habits_table` — needs to also delete rows from
  the new `completions` table (FK to `habits`) so per-test cleanup doesn't
  hit a foreign-key violation.

## Implementation

**1. Model — `app/db/models.py`**

Add a `Completion` SQLModel table:
- `id: int | None` primary key
- `habit_id: int` — `ForeignKey("habits.id")`, not null
- `completion_date: date` — not null
- `created_at: datetime` — tz-aware, default `datetime.now(timezone.utc)` (same pattern as `Habit.created_at`)
- `UniqueConstraint("habit_id", "completion_date")` — this is what turns a
  duplicate insert into a DB-level conflict rather than a silent upsert.

**2. Migration — `alembic/versions/`**

Run `alembic revision --autogenerate -m "create completions table"` against
the local dev Postgres (`DATABASE_URL` from `.envrc`), review the generated
`create_table` (FK constraint + unique constraint), then `alembic upgrade
head` to apply it before running tests.

**3. Schemas — `app/schemas/completions.py`**

- `CompletionCreate`: `completion_date: date | None = None`
- `CompletionRead` (`from_attributes=True`): `id`, `habit_id`,
  `completion_date`, `created_at`

**4. Repository — `app/repository/completions.py`**

`CompletionRepository.create(habit_id, completion_date)`: insert, commit,
and catch `sqlalchemy.exc.IntegrityError` from the unique constraint,
rolling back and raising a repository-level `DuplicateCompletionError`.
Plus the standard `get_completion_repository` FastAPI dependency.

**5. Service — `app/services/completions.py`**

`CompletionService.create_completion(habit_id, completion_date)`:
- Resolve `completion_date` to today (UTC) if not supplied.
- Raise `FutureCompletionDateError` if the resolved date is after today (UTC).
- Look up the habit via `HabitRepository.get_by_id`; raise
  `HabitNotFoundError` if missing.
- Delegate to `CompletionRepository.create`, translating the repository's
  `DuplicateCompletionError` into a service-level `DuplicateCompletionError`
  (keeps the repository's SQLAlchemy-flavored exception out of the service/route
  contract).
- `get_completion_service` dependency wires both `HabitRepository` and
  `CompletionRepository`.

**6. Route — `app/routes/habits.py`**

Add `POST /{habit_id}/completions` to the existing `habits` router (same
file, since it's nested under `/habits` and the file is well under the
400-line cap). Catch the three service exceptions and map to HTTP status
codes: `HabitNotFoundError` → 404, `FutureCompletionDateError` → 422
(`status.HTTP_422_UNPROCESSABLE_CONTENT`, the non-deprecated constant),
`DuplicateCompletionError` → 409. Return `CompletionRead` with 201 on success.

**7. Tests**

- `tests/test_completions.py` (unit/functional, in-process ASGI client via
  the existing `client` fixture): happy path with explicit date, default-to-today,
  duplicate → 409, future date → 422, missing habit → 404.
- `tests/integration/test_completions_flow.py` (out-of-process, real
  `uvicorn` subprocess via the `live_server`/`client` fixtures in
  `tests/integration/conftest.py`): happy path, 409 duplicate, 422 future
  date (the three cases the task explicitly calls out).
- Update `tests/conftest.py`'s `_clean_habits_table` fixture to delete
  `Completion` rows before `Habit` rows (FK ordering).

**8. Plan.md**

Commit this plan as `Plan.md` at the repo root of this worktree, since the
review infrastructure checks the implementation against it.

## Verification

1. `make lint` — ruff, import-linter (layered architecture contract still
   holds — completions files sit at the same layers as habits files), and
   the file-size guard.
2. `make test` — in-process unit tests (`tests/test_completions.py` +
   existing `tests/test_habits.py`).
3. `make test-integration` — out-of-process tests against a live `uvicorn`
   subprocess (`tests/integration/test_completions_flow.py` + existing
   `tests/integration/test_habits_flow.py`), confirming the happy path, 409
   duplicate, and 422 future-date cases work against a real running server
   and real Postgres.
4. Commit the implementation + `Plan.md` in this worktree.
