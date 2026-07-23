# Plan: Configurable North Mini Code provider toggle (#15)

## Stacked on PR #16 (unmerged)

This branch is based on `recover-continuous-maintenance-fixes`
(https://github.com/rosequ/habit-tracker-api/pull/16), not directly on
`main` — that branch recovers a stranded commit of already-reviewed bug
fixes to `doc-gardener.yml`/`garbage-collector.yml`/`quality-grader.yml`/
`ci.yml`/`deploy.yml`/`scripts/gate_and_merge.sh`/
`scripts/quality_report_data.sh` that this branch's own work also touches.
Until #16 merges, a diff against `main` includes both PR #16's recovered
fixes *and* this branch's new work below — see #16's own `Plan.md`/PR
description for the former. This plan describes only what's new here.

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
`bash scripts/run_agent.sh <<< "$prompt"`, adds an `AGENT_PROVIDER: ${{
vars.AGENT_PROVIDER || 'claude' }}` env var (repository variable, works
uniformly across `schedule`/`issues`/`workflow_dispatch` triggers, unlike a
workflow input), and adds `OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY
}}` alongside the existing `ANTHROPIC_API_KEY` env (empty/unused whenever
the provider stays `claude`).

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

## Out of scope

- Actually flipping `AGENT_PROVIDER` to `north` anywhere by default —
  nothing changes today's behavior; this only makes the switch possible.
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
