# 0001. Split AGENT_PROVIDER into two independent repository variables

## Status

Accepted

## Context

Every unattended-agent call site in this repo — the five
`.github/workflows/*.yml` jobs that run a headless agent, plus the two
local review scripts — pipes its prompt through `scripts/run_agent.sh`,
which reads an `AGENT_PROVIDER` env var to pick the backend (`claude` or
`north`, see `docs/architecture/agent-providers.md`).

Two of those five workflows, `doc-gardener.yml` and `garbage-collector.yml`,
can merge their own PRs to `main` with no human in the loop, gated only by
a syntax/scope-level check (lint, non-empty-docs, path/size limits). The
other three (`agent-ticket.yml`, `agent-followup.yml`, `quality-grader.yml`)
always label their PRs `needs-human-review` — a human reviews before
anything merges.

If a single `AGENT_PROVIDER` variable controlled all five workflows,
switching it to try an experimental or unverified backend (e.g. the
North Mini Code / OpenCode / OpenRouter path, whose output quality and
tool-restriction behavior haven't been compared against Claude yet — see
"What's unverified" in `docs/architecture/agent-providers.md`) would
silently also change what the two auto-merge-capable workflows run,
with no human ever looking at the result before it lands on `main`.

## Decision

Use two separate repository variables, not one variable with an override:
- `vars.AGENT_PROVIDER` — read only by the three workflows that never
  auto-merge.
- `vars.AGENT_PROVIDER_AUTOMERGE` — read only by `doc-gardener.yml` and
  `garbage-collector.yml`. Deliberately not a fallback of the first;
  setting it is a separate, deliberate action from setting the general
  variable.

Both default to `claude` when unset.

## Consequences

Trying an experimental provider on the three human-reviewed workflows
requires no extra step and carries no risk to `main`. Enabling that same
provider for the two auto-merge workflows requires a second, explicit
variable change — someone has to consciously opt the auto-merge path in,
rather than inherit it by accident from a change made for a different
reason.

The cost is two variables to keep track of instead of one, and the two can
drift out of sync (e.g. `AGENT_PROVIDER=north` for a while but
`AGENT_PROVIDER_AUTOMERGE` still `claude`) — that asymmetry is intentional,
not a bug to reconcile.
