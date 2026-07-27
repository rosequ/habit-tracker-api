# 0003. Client-side git hooks as a stopgap for missing branch protection

## Status

Accepted

## Context

This repo is private and on GitHub's Free plan, which does not support
server-side branch protection at all (issue #7). That means nothing on
GitHub's side stops a direct `git push` to `main`, or a push of any branch
that skips lint, tests, or review — the usual guarantee that a required
check must pass before merge simply doesn't exist here, at any price point
short of upgrading the plan.

Doing nothing would mean every safeguard in this repo (layering rules,
`Plan.md`-vs-diff review, lint, tests) is opt-in per push, with no
mechanism forcing it.

## Decision

Install two client-side git hooks, enabled per clone via
`git config core.hooksPath .githooks`:
- `pre-commit` — refuses to commit if `make lint` fails, and separately
  enforces the `Plan.md`-before-implementation rule (see
  [0002](./0002-plan-md-precommit-gate.md)).
- `pre-push` — refuses to push directly to `main`, and separately refuses
  to push any branch unless `make agent-review-local` and `make test` both
  pass.

Both hooks support a documented one-time override
(`SKIP_COMMIT_LINT`, `SKIP_COMMIT_PLAN_CHECK`, `SKIP_PUSH_VERIFICATION`,
`ALLOW_PUSH_TO_MAIN`) for genuine false positives, rather than a silent
bypass.

## Consequences

Anyone who runs `git config core.hooksPath .githooks` gets real local
enforcement of the rules this repo cares about, without waiting on a
GitHub plan upgrade. But this is explicitly a stopgap, not a fix: it is
still fully bypassable — `--no-verify`, simply not enabling
`core.hooksPath` on a given clone, or one of the documented `SKIP_*`/
`ALLOW_PUSH_TO_MAIN` overrides all skip it entirely — so it protects
against accidental mistakes, not a deliberate or compromised actor. It also
only runs where someone has opted in locally; it does nothing for pushes
made through any other path (e.g. the GitHub UI, or a different clone that
never ran the `core.hooksPath` config). If this repo is ever upgraded off
the Free plan, server-side branch protection should replace this as the
actual guarantee, and this stopgap can be reassessed (kept as
defense-in-depth, or retired).
