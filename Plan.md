# Plan: Implement GET /habits (issue #19), fixing an incomplete automated attempt

## Context

Issue #19 ("Add GET /habits to list all habits") was labeled `agent-ready`
and picked up by `agent-ticket.yml`. The automated run committed only a
`HabitRepository.get_all()` method — buggy (`F821 Undefined name 'session'`,
plus use of the legacy sync SQLAlchemy 1.x `Query` API instead of the async
`select()` style used elsewhere in this repo) and, more significantly,
never wired to a route or service, so `GET /habits` didn't actually exist.
`fast-gates` caught the lint error; manual inspection caught the missing
route/service/tests once lint was fixed and the PR was reviewed.

## What this branch changes

**`app/repository/habits.py`** — fixed `get_all()` to use
`select(Habit).order_by(Habit.id.asc())` via `self._session` (not the
undefined `session`), matching this repo's async 2.0-style SQLAlchemy
usage.

**`app/services/habits.py`** — added `HabitService.list_habits()`,
delegating to `repository.get_all()`.

**`app/routes/habits.py`** — added `GET /habits` (`list_habits`),
`response_model=list[HabitRead]`, calling `service.list_habits()`. No
auth/pagination/filtering, per the issue's stated scope.

**`tests/test_habits.py`** — two new unit tests: empty list when no habits
exist, and habits returned in `id` order after creating two.

**`tests/integration/test_habits_flow.py`** — one new integration test:
empty list, then a created habit appears in the list response.

## Out of scope

- Pagination, filtering, or sorting query params (per issue #19).
- Per-user scoping (no auth exists yet).

## Verification

- `make lint` — passes (the `F821` from the automated attempt is fixed).
- `make test` — all unit tests pass, including the two new ones.
- `make test-integration` — to be run before push.
