# Plan: Configurable North Mini Code provider toggle (#15)

## Context

Issue #15 asks to evaluate replacing headless Claude Code with Cohere's
North Mini Code across every unattended-agent call site. Scoped down (per
discussion) to: make the provider configurable and toggleable per-workflow,
default to today's Claude Code behavior everywhere, and produce the
integration research the issue itself flagged as missing — not a full
replacement, since the exact CLI/harness/tool-restriction/secrets story was
unresearched going in, and two of the auto-merge-eligible workflows
(`doc-gardener.yml`, `garbage-collector.yml`) shouldn't have their backing
model changed without a side-by-side quality comparison first.

## What this branch adds

**1. `scripts/run_agent.sh`** (new) — the single provider-dispatch point
every call site now goes through instead of calling `claude -p` directly.
`AGENT_PROVIDER=claude` (default) is byte-for-byte the same invocation as
before. `AGENT_PROVIDER=north` runs North Mini Code
(`north-mini-code-1.0`) through the OpenCode CLI against OpenRouter
(`openrouter/cohere/north-mini-code:free`, auth via `OPENROUTER_API_KEY`).
Full rationale for those integration choices, and what's still unverified,
is in `docs/architecture/agent-providers.md` (new) rather than duplicated
in code comments.

**2. The five workflows** (`agent-ticket.yml`, `agent-followup.yml`,
`doc-gardener.yml`, `garbage-collector.yml`, `quality-grader.yml`) — each
drops its standalone "Install Claude Code" step (now lazy-installed inside
`run_agent.sh`), replaces its `claude -p ...` invocation with
`bash scripts/run_agent.sh <<< "$prompt"`, and adds
`OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}` alongside the
existing `ANTHROPIC_API_KEY` env (empty/unused whenever the provider stays
`claude`). The `AGENT_PROVIDER` env var they set is deliberately **not**
the same repository variable everywhere (see "Fixes made after
agent-review-cloud" below): `agent-ticket.yml`/`agent-followup.yml`/
`quality-grader.yml` read `vars.AGENT_PROVIDER`; `doc-gardener.yml`/
`garbage-collector.yml` read `vars.AGENT_PROVIDER_AUTOMERGE` instead. Both
default to `claude` whenever unset. Repository variables (not a
`workflow_dispatch` input) because they need to work uniformly across
`schedule`/`issues`/`workflow_dispatch` triggers.

**3. `scripts/agent_review_local.sh` / `scripts/agent_review_cloud.sh`** —
same swap: `claude -p --model ... --tools ... <<< "$prompt"` becomes
`CLAUDE_MODEL=... bash scripts/run_agent.sh --tools ... <<< "$prompt"`, so
`AGENT_PROVIDER=north make agent-review-local`/`agent-review-cloud` works
the same way locally as flipping the repository variable does in CI.

**4. `AGENTS.md`** — one new bullet at the top of "CI/CD" pointing at
`scripts/run_agent.sh`/`docs/architecture/agent-providers.md`; the
`agent-review-local`/`-cloud` paragraph now says "the agent CLI for
whichever `AGENT_PROVIDER` is active" instead of hardcoding "the `claude`
CLI."

## Fixes made after `agent-review-cloud`

Round 1 (`REQUEST_CHANGES`) caught one real, blocking gap: every one of the
five workflows read the *same* `vars.AGENT_PROVIDER`, so there was no way
to move the three non-auto-merging workflows to `north` while keeping
`doc-gardener.yml`/`garbage-collector.yml` on `claude` — flipping the one
shared variable would flip all five simultaneously, directly contradicting
the "don't flip this without a real comparison first" comments already
sitting in those two workflows. Fixed by splitting into two independent
repository variables (see "What this branch adds" above):
`AGENT_PROVIDER_AUTOMERGE`, read only by the two auto-merge-capable
workflows, is a distinct variable rather than a fallback/override of the
general one, so a repo-wide flip of `AGENT_PROVIDER` can never silently
change what they run. `docs/architecture/agent-providers.md` and
`AGENTS.md` updated to describe both variables and the reasoning for
keeping them separate.

## Out of scope

- Actually setting either repository variable to `north` — this branch's
  code changes leave every workflow defaulting to `claude` whenever its
  variable is unset. `AGENT_PROVIDER` (the non-auto-merge one) was
  separately set to `north` by explicit request before this gap was found;
  see the PR description for that decision. `AGENT_PROVIDER_AUTOMERGE` has
  deliberately not been set by this branch — that's a separate decision for
  whoever wants `doc-gardener.yml`/`garbage-collector.yml` on `north`, made
  with this PR's fix in place rather than the single-variable design that
  couldn't express it safely.
- The Kimi K* swap proposed in #10 — `run_agent.sh`'s dispatch is generic
  enough that a third provider branch should follow the same shape later,
  but isn't added here.
- Verifying the `north` path end-to-end (no Cohere/OpenRouter account or
  OpenCode install available while building this) — see
  `docs/architecture/agent-providers.md`'s "What's unverified" section for
  the specific open items before anyone relies on it.

## Verification

1. `make lint` / `make test` pass.
2. `bash -n` on every edited workflow's embedded shell and on
   `scripts/run_agent.sh` itself.
3. Every workflow YAML still parses (`yaml.safe_load`) after the edits.
4. The `claude` path's arguments were compared line-by-line against each
   call site's original invocation to confirm `AGENT_PROVIDER=claude` (the
   default) passes the same flags with the same values as before this
   branch, for every one of the seven call sites. Flag *order* differs for
   the two review scripts (`--tools`/`--system-prompt` now come after
   `--permission-mode` instead of before) since `run_agent.sh` appends them
   conditionally -- not re-verified against the real `claude` CLI that
   argument order is inert for it, only assumed from it being a standard
   flag-parsing CLI.
5. Not independently verified: the `north` path itself (no way to run
   OpenCode/OpenRouter in this environment) -- this is the acceptance
   criterion issue #15 itself, and `docs/architecture/agent-providers.md`
   says so plainly rather than claiming untested behavior works.
