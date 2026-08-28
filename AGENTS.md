# AGENTS.md

## What this repo is
Habit Tracker API. Python 3.14, FastAPI, SQLModel (async), Postgres.

## Where things live
- docs/architecture/ — layering rules, conventions; see
  docs/architecture/ARCHITECTURE.md for a birds-eye system overview
  (domains, request flow, deployment, observability, automation pipeline)
- docs/adr/ — Architecture Decision Records: the why behind structural
  decisions (see `docs/adr/README.md`). **Only records whose Status:
  "Accepted" are treated as authoritative inputs, the same way the
  actual code is.** If an accepted ADR changed a decision and
  docs/architecture/ARCHITECTURE.md and/or AGENTS.md hasn't caught
  up with it, fix the stale doc so it matches the accepted ADR's
  decision.
  - ADR 0001 (accepted) — see `docs/adr/0001-two-agent-provider-variables.md`
    for the split between `AGENT_PROVIDER` and `AGENT_PROVIDER_AUTOMERGE`.
- docs/domains/<name>/ — one README per business domain (e.g. habits)
- app/routes/ — HTTP layer only
- app/schemas/ — request/response shapes
- app/services/ — business logic
- app/repository/ — the ONLY layer allowed to touch app/db/
- app/db/ — engine, session, SQLModel table definitions

Note: The habit completion (check-in) functionality is documented in `docs/domains/habits/README.md` (section "Completions API") and the API endpoint for creating completions lives in `app/routes/habits.py` under the `/habits/{habit_id}/completions` route

## Non-negotiable rules (enforced by lint, not memory)
- Dependency direction: routes -> schemas -> services -> repository -> db
- No raw SQL or DB session objects outside app/repository/
- No business logic in app/routes/ — routes call services, nothing else
- File size limit: 400 lines (split instead of suppressing)

## How to verify your work
- `make test`  — unit + structural tests
- `make dev`   — brings up docker-compose (db, prometheus) and boots the app
  for this worktree (uses .envrc DB/port namespace)
- `make smoke` — actually boots the app (docker-compose + uvicorn) on
  `SMOKE_PORT` (default 8098, separate from `APP_PORT` so it won't collide
  with a `make dev` you already have running) and hits `/health`, which runs
  a real `SELECT 1`. Catches runtime crashes -- missing env vars, docker-compose
  not up, a stale process still bound to the port -- that a text-only diff
  review can never see, because they only manifest by actually running the
  command.
- `make ui-smoke` — boots the app the same way `make smoke` does (plus
  `alembic upgrade head`, since the dashboard check below needs real
  tables), then drives a real headless Playwright browser against two
  pages: the Swagger UI (`/docs`) and the habits dashboard (`/dashboard`,
  issue #36). On `/docs`: confirms the page renders with no console errors,
  lists the expected routes, and that "Try it out" on `GET /health` returns
  a real response through the browser. On `/dashboard`: fills and submits
  the add-habit form, confirms the new habit appears without a page reload,
  clicks "Mark done today", and confirms the UI reflects success. Catches a
  broken UI render or a route/form that renders but 500s when actually
  used -- neither `make smoke` nor any other check here drives a real
  browser. Local-only, not wired into CI (issue #29). Needs
  `uv run playwright install chromium` once before first use.
  `scripts/ui_smoke_common.py`'s `capture_screenshot(page, check_name, step)`
  is the one reusable helper both checks call to save a timestamped PNG,
  every screenshot landing in the git-ignored `.ui-smoke-artifacts/`
  directory -- five per run (two from `/docs`, three from `/dashboard`).
  Any future Playwright-driven check should call it too rather than
  reimplementing capture logic (#37).
- **UI-touching PRs need visual proof.** Any PR whose diff touches
  UI-facing code (`app/static/**`, any templates dir, or FastAPI
  app-metadata changes affecting what `/docs` renders, e.g. `app/main.py`)
  should run the relevant `ui-smoke` check locally and attach the resulting
  screenshots from `.ui-smoke-artifacts/` (git-ignored, so they must be
  attached by hand -- e.g. dragged into the PR description -- not linked)
  as proof, instead of just asserting "tested manually." `make
  agent-review-local` (below) softly flags a diff that touches UI paths
  without Plan.md or the diff giving any indication this was done -- a
  warning, not a hard block (#37).
- `make lint`  — ruff + import-linter + file-size check; read the error, it tells you the fix
- `make agent-review-local` — fast/cheap: lint + smoke + flags diff not
  covered by Plan.md + warns (non-blocking) if the diff touches UI paths
  without any sign of screenshot proof (see "UI-touching PRs need visual
  proof" above)
- `make agent-review-cloud` — deeper: an isolated read-only reviewer checks the diff
  against Plan.md and the linked GitHub issue's acceptance criteria

Both require a committed `Plan.md` at the repo root that actually describes
*this* branch's changes -- `require_plan` (in `scripts/review_common.sh`) fails
if other files changed since `main` but `Plan.md` didn't, so a stale plan left
over from a previous feature/worktree can't silently rubber-stamp unrelated
work as "planned." Both also require the agent CLI for whichever
`AGENT_PROVIDER` is active installed and authenticated separately (they
 shell out to it via `scripts/run_agent.sh` -- see
  `docs/architecture/agent-providers.md`). Loop: implement ->
 `agent-review-local` -> fix -> repeat until clean -> `agent-review-cloud` ->
 address comments -> repeat.

## Branching
This is a private repo on GitHub's Free plan, which doesn't support server-side
branch protection at all (see issue #7) -- there is nothing stopping a direct
`git push` to `main`, or a push of any branch that skips lint/tests/review.
As a stopgap (see [ADR 0003](docs/adr/0003-client-side-hooks-branch-protection-stopgap.md)
for the full decision record), run `git config core.hooksPath .githooks`
once per clone: it installs two client-side hooks (still bypassable
locally -- `--no-verify`, or just not enabling `core.hooksPath` -- same
limitation as the branch protection gap above):
- `pre-commit` — refuses to commit if `make lint` fails (override once with
  `SKIP_COMMIT_LINT=1 git commit ...`), and separately refuses to commit any
  tracked file other than `Plan.md` unless `Plan.md` has *already* been
  touched somewhere on this branch (this commit or an earlier one) --
  mechanically enforces writing/updating the plan before implementing,
  not backfilling it afterward, though it can't check the plan's content is
  actually accurate (that's `agent-review-local`'s job, at push time). See
  [ADR 0002](docs/adr/0002-plan-md-precommit-gate.md) for why this gate
  exists. Override once with `SKIP_COMMIT_PLAN_CHECK=1 git commit ...`.
- `pre-push` — refuses to push directly to `main` (override once with
  `ALLOW_PUSH_TO_MAIN=1 git push ...` if you really mean to; only bypasses
  the main-push block, not the check below). Separately, refuses to push
  **any** branch unless `make agent-review-local` (which itself runs `make
  lint` first) and `make test` both pass (a pure branch deletion is
  exempt -- nothing to check). This runs on every push, including small WIP
  ones -- it boots Postgres via docker-compose, a real `uvicorn` process,
  and a `claude -p` call so expect it to take a while and to need the
  `claude` CLI installed/authenticated. Override once with
  `SKIP_PUSH_VERIFICATION=1 git push ...`. Pushing a tag hits this same
  gate (anything with a non-zero local SHA does), not just branches.
  `make agent-review-cloud` deliberately is NOT part of this gate -- it's
  meant to run once, deliberately, before asking a human to review a PR,
  not on every push of routine work.

Always work on a branch and open a PR instead of pushing to `main` directly.

## Archiving plans

`Plan.md` (and often `Implement.md`) is mechanically required per-branch
(see `require_plan_staged` above), but every new branch/worktree just
overwrites them, so nothing keeps a running record across branches --
`git log --oneline -- Plan.md` shows it's been rewritten on essentially
every feature branch. `docs/plans/` is that record.

This is a **manual convention**, not automated: right before merging a PR
(after the last `Plan.md`/`Implement.md` update, before `gh pr merge`), run
`make archive-plan` (or `bash scripts/archive_plan.sh [slug]` directly). It
copies the branch's `Plan.md` (and `Implement.md`, if present) into
`docs/plans/<issue-or-date>-<slug>.md` -- see `docs/plans/README.md` for
the exact naming rules. Commit the resulting file as part of that same PR.

This was deliberately not wired into `ci.yml`'s merge path or a new git
hook: "this branch is about to merge" is a human/agent judgment call made
once, not something reliably inferable from inside a single commit/push
hook without either false-triggering early or missing the final update. A
skipped archive doesn't break anything -- it just means that branch's plan
is lost the same way it always has been before this existed.

## Observability (local)
- `/health` — runs a real `SELECT 1` against Postgres; used as the Render
  health check and by `make smoke`.
- `/metrics` — Prometheus text-format metrics on the running app, wired
  directly on `app` via `prometheus_fastapi_instrumentator`.
  `http_requests_total` and `http_request_duration_seconds` are both
  labeled by `method`, `handler` (route), and `status`.
- `make dev` starts a local Prometheus that scrapes
  `host.docker.internal:$APP_PORT/metrics` (the app itself runs on the host,
  not in docker-compose). UI at
  `http://localhost:$PROMETHEUS_PORT` (see `.envrc`'s `PROMETHEUS_PORT`).
- `make metrics-query QUERY='...'` — runs a PromQL instant query, prints the
  raw number only (no JSON). Examples:
  - p95 latency: `make metrics-query QUERY='histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'`
  - request rate: `make metrics-query QUERY='sum(rate(http_requests_total[5m]))'`
  - error rate by status: `make metrics-query QUERY='sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))'`
- No logging pipeline yet — metrics only. Future work.

## Escalate to a human when
- Change touches auth, billing, or data retention
- Change requires a new external dependency
- You are not confident the fix addresses the root cause

## CI/CD (.github/workflows/)
- Every workflow below that runs a headless agent, plus
  `agent-review-local`/`agent-review-cloud`, goes through
  `scripts/run_agent.sh` rather than calling `claude -p` directly. Two
  separate repository variables pick the backend (both default `claude`):
  `AGENT_PROVIDER` for the three workflows that never auto-merge
  (`agent-ticket.yml`, `agent-followup.yml`, `quality-grader.yml`), and
  `AGENT_PROVIDER_AUTOMERGE` -- deliberately distinct, not a fallback of the
  first -- for the two that can (`doc-gardener.yml`, `garbage-collector.yml`),
  so flipping the general variable can never silently change what an
  auto-merge-capable workflow runs. See `docs/architecture/agent-providers.md`
  for the North Mini Code (Cohere, via OpenCode/OpenRouter) alternative and
  what's still unverified about it.
- `ci.yml` — on every PR: `fast-gates` (lint, test, gitleaks secret scan) is
  the required check that blocks merge. `async-verification` runs
  `make test-integration` after `fast-gates` but is non-blocking, and on
  failure dispatches `agent-followup.yml`. `doc-freshness` runs
  `make lint-docs` (non-blocking placeholder).
- `agent-followup.yml` — dispatched on integration-test failure (which can
  surface after the PR already merged, since the check is non-blocking).
  Headless Claude Code fixes forward on a new branch off `main` and opens a
  PR labeled `needs-human-review`. Never pushes to `main` directly, never
  merges.
- `agent-ticket.yml` — dispatched when an issue is labeled `agent-ready`.
  Headless Claude Code implements the issue on a new branch, writes tests,
  and self-verifies with `make lint`/`test`/`test-integration` before the
  workflow independently re-runs the same three and opens a PR labeled
  `needs-human-review`. Never merges, regardless of check status.
- `deploy.yml` — on push to `main`, triggers a Render deploy via deploy
  hook. Not re-gated on its own (see `fast-gates` above) — that's not
  server-side enforced either, same issue #7 gap. Also has
  `workflow_dispatch:` so `garbage-collector.yml` can explicitly re-dispatch
  it after an auto-merge (see below — a `GITHUB_TOKEN`-authored push to
  `main` doesn't cascade into this workflow's own `push` trigger).
- `doc-gardener.yml` — daily cron. Headless Claude Code scans `docs/`
  (except `docs/quality.md` — never touch it; it's generated by
  `quality-grader.yml`'s separate, human-reviewed process) and
  `AGENTS.md` for staleness/contradictions with the actual code and fixes
  them. Auto-merges (`gh pr merge --squash`) if the diff stays entirely
  within `docs/`/`AGENTS.md` and lint/test/gitleaks pass; otherwise falls
  back to `needs-human-review` like the other agent workflows.
- `garbage-collector.yml` — weekly cron. Headless Claude Code finds one small
  deviation from `AGENTS.md`'s architecture rules that import-linter's
  layers contract wouldn't catch stylistically (dead code, a route doing
  more than calling a service, small duplicated logic) and opens a small
  refactor PR. Auto-merges only if lint/test/gitleaks pass AND the diff is
  under 50 changed lines total AND it doesn't touch `.github/workflows/`,
  `alembic/versions/`, `uv.lock`, or `pyproject.toml` — no exceptions on
  either condition. On merge, re-dispatches `deploy.yml` (see above).
  Accepted gap: because its bot-authored PR never triggers `ci.yml`'s
  `pull_request` event (same anti-recursion rule as above), a
  garbage-collector auto-merge never gets `async-verification`/
  `make test-integration` run against it — not before merge, not after.
  Strictly less test coverage than a normal human PR gets, for the one
  workflow that can auto-merge a change to `app/` code.
- `quality-grader.yml` — monthly cron. Headless Claude Code writes/updates
  `docs/quality.md`: a per-layer (routes/schemas/services/repository/db)
  table of import-linter/layering compliance, doc freshness (last
  `[doc-gardener]`-tagged touch), and open cleanup-PR counts. Deliberately no
  test-coverage-delta column (a weak/lagging signal) — the compliance column
  folds in a structural-lint-violations count instead. **Never auto-merges**,
  always `needs-human-review` — a report generator shouldn't silently
  rewrite its own audit trail.

None of the three scheduled workflows above can use GitHub's native
`gh pr merge --auto`: that feature's "wait for required checks" behavior
only exists via branch protection, which 403s on this repo (issue #7). So
`doc-gardener.yml`/`garbage-collector.yml` run the fast-gates checks inline,
in the same job, right after Claude produces a diff (committing Claude's
changes *before* running them, not after — both need a real commit to scope
themselves against), and `scripts/gate_and_merge.sh` decides merge-vs-label
synchronously from that — no cross-workflow polling or timeouts.

Because a `GITHUB_TOKEN`-authored PR doesn't trigger `ci.yml`'s own
`pull_request` event (GitHub's anti-recursion rule for the default token),
`doc-gardener.yml`/`garbage-collector.yml`'s PRs won't show a `fast-gates`
check-run on GitHub's Checks tab — that's expected, not a bug: the inline
checks are what actually gate the merge, and the PR body says so. An
earlier design fired a `gh workflow run ci.yml --ref <branch>` fire-and-forget
purely for a visible (non-gating) check-run, but that was cut: it has no
effect on the actual gate, and it introduced two real bugs across review
(a `workflow_dispatch`-triggered `ci.yml` run leaves
`github.event.pull_request.number` empty, which would have made
`async-verification`'s failure-follow-up dispatch misfire; separately,
`ci.yml`'s `gitleaks` step would inherit the same full-history-scan problem
 described below). Not worth the risk for a cosmetic nicety.

`doc-gardener.yml`/`garbage-collector.yml`'s own inline gitleaks step does
NOT use `gitleaks/gitleaks-action@v2` (unlike `ci.yml`'s `fast-gates`): that
action only scopes its scan to a commit range for `push`/`pull_request`
events (confirmed by reading its source) — for `workflow_dispatch`/
`schedule` it scans this repo's entire git history instead, which would
fail forever on any pre-existing secret-shaped string unrelated to the
current diff, permanently disabling auto-merge. Both workflows instead run
the `gitleaks` CLI directly, scoped to just the commit(s) the run adds on
top of `main`.

`doc-gardener.yml`'s auto-merge gate is syntax/scope-only by design —
`make lint-docs` only checks docs are non-empty, there's no semantic
 correctness check on doc content. Accepted: doc-only mistakes are low-stakes
 and self-correcting (next day's run, or a human revert).

GitHub auto-disables `schedule:`-triggered workflows after 60 days of no
repository activity (silently — an email, not a visible Actions-tab
failure). If one of the three scheduled workflows above appears to have
stopped running, check that first before assuming a bug in the workflow
itself.

Every agent-authored PR from `agent-followup.yml`/`agent-ticket.yml`/
`quality-grader.yml` is labeled `needs-human-review` — a human always
reviews before merging, no exception. `doc-gardener.yml`/
`garbage-collector.yml` are the only two workflows that can merge on their
own, and only under the conditions above.
