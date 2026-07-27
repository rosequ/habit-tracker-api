# Plan: Introduce docs/adr/ (Architecture Decision Records) (issue #26)

## Context

Real architecture decisions already exist in this repo (the
`AGENT_PROVIDER`/`AGENT_PROVIDER_AUTOMERGE` split, the `Plan.md`-before-
implementation pre-commit gate, the client-side-hooks stopgap for branch
protection) but they're only documented as prose scattered across
`AGENTS.md` and `docs/architecture/agent-providers.md`, or not documented
in a structured way at all. There's also no lightweight format for
recording *future* decisions, so "explain the why in a workflow comment"
keeps repeating instead of being captured once, in one place.

## What this branch changes

**`docs/adr/template.md`** — standard ADR shape: Title, Status, Context,
Decision, Consequences. New ADRs are copies of this file.

**`docs/adr/README.md`** — short index explaining what an ADR is, when to
write one, the naming convention (`NNNN-kebab-title.md`, zero-padded,
monotonically increasing), and a table listing the ADRs that exist so far.

**`docs/adr/0001-two-agent-provider-variables.md`** — backfills the
`AGENT_PROVIDER` vs `AGENT_PROVIDER_AUTOMERGE` split, citing
`docs/architecture/agent-providers.md` and `AGENTS.md`'s CI/CD section as
prior art for the decision.

**`docs/adr/0002-plan-md-precommit-gate.md`** — backfills the
`Plan.md`-before-implementation mechanical pre-commit gate
(`.githooks/pre-commit`, `require_plan_staged` in `scripts/review_common.sh`).

**`docs/adr/0003-client-side-hooks-branch-protection-stopgap.md`** —
backfills the client-side-hooks stopgap adopted because this repo is
private/Free-tier and GitHub's server-side branch protection 403s
(issue #7).

**`AGENTS.md`** — add a short pointer under "Where things live" (or a new
small section) noting that new architecture decisions get recorded as an
ADR in `docs/adr/` going forward, referencing the template.

**`.gitignore`** — add `/TASK.md` alongside the existing "Claude Code local
state" entries: this worktree came with an untracked `TASK.md` (the task
briefing dropped in by the harness, not project content), which the
review scripts' untracked-file union would otherwise flag as unplanned
scope on every run in this worktree.

## Out of scope

- Converting every historical decision into an ADR retroactively — just
  the three decisions above, enough to establish the pattern.
- Any change to `.github/workflows/*`, `.githooks/*`, or issues
  #25/#27/#28/#29 (owned by other in-flight sessions).

## Verification

- `make lint` — docs-only change plus an `AGENTS.md` edit; should pass
  unchanged (no code touched).
- `make test` — should pass unchanged (no runtime code touched).
- `make agent-review-local` / `make agent-review-cloud` — run per the
  standard loop before pushing/opening the PR.
- No `make smoke` needed — nothing runtime-relevant is touched.
