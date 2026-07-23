# Agent provider dispatch (#15)

Every unattended-agent call site — the five `.github/workflows/*.yml` jobs
that run a headless agent (`agent-ticket.yml`, `agent-followup.yml`,
`doc-gardener.yml`, `garbage-collector.yml`, `quality-grader.yml`) plus the
two local review scripts (`agent_review_local.sh`, `agent_review_cloud.sh`)
— pipes its prompt into `scripts/run_agent.sh` on stdin instead of calling
`claude -p` directly. An `AGENT_PROVIDER` env var picks the backend in that
one place.

**Two separate repository variables feed it, not one:**
- `vars.AGENT_PROVIDER` — read by `agent-ticket.yml`, `agent-followup.yml`,
  and `quality-grader.yml`. None of these three ever auto-merge (every PR
  they open is labeled `needs-human-review`), so a bad or low-quality
  response from an experimental provider is caught by a human before it can
  land anywhere.
- `vars.AGENT_PROVIDER_AUTOMERGE` — read *only* by `doc-gardener.yml` and
  `garbage-collector.yml`, the two workflows that can merge their own PRs
  to `main` with no human in the loop, gated by nothing more than a
  syntax/scope-level check (lint, non-empty-docs, path/size limits -- see
  `AGENTS.md`). Deliberately a different variable, not a fallback/override
  of the first one: flipping the general `AGENT_PROVIDER` variable must
  never silently change what these two auto-merge-capable workflows run.
  Setting this one is a separate, deliberate decision.

Both default to `claude` (today's behavior) whenever unset.

## `AGENT_PROVIDER=claude` (default)

Unchanged from before this existed: `claude -p --model <model>
--permission-mode bypassPermissions`, authenticated via `ANTHROPIC_API_KEY`.

## `AGENT_PROVIDER=north`

Cohere's open-source North Mini Code (`north-mini-code-1.0`, a 30B-total/
3B-active MoE, Apache 2.0) run through the OpenCode CLI
(`npm install -g opencode-ai`) against OpenRouter
(`openrouter/cohere/north-mini-code:free`), authenticated via
`OPENROUTER_API_KEY`.

**Why OpenRouter and not Cohere's own hosted API directly:** North Mini
Code's exact model slug on Cohere's own platform (`docs.cohere.com`) wasn't
confirmed during this research — only inferred from their naming
convention. OpenRouter's listing (`cohere/north-mini-code:free`) is the one
integration detail directly confirmed in public sources during this work.
Swapping to Cohere's own API directly is a reasonable follow-up once someone
confirms that model slug against a real account.

**Why OpenCode as the harness:** North Mini Code has no first-party CLI of
its own — Cohere trained it against multiple existing agent harnesses
(SWE-Agent, mini-SWE-agent, OpenCode, Terminus 2) rather than shipping one.
OpenCode was picked because its `opencode run` subcommand is scriptable/
non-interactive and its per-agent config supports restricting tool access,
which `agent_review_local.sh`/`agent_review_cloud.sh` require.

**Tool restriction:** `opencode run` has no `--tools`-style flag of its own
(confirmed against its published docs while researching this). Tool access
is only configurable via an agent definition's `permission`/`tools` block,
so `run_agent.sh` generates a minimal one on the fly (via a temp file and
`OPENCODE_CONFIG`) for the two tool specs actually used today: no tools at
all (`agent_review_local.sh`), and read-only (`agent_review_cloud.sh`). Any
tool spec beyond those two is a deliberate hard failure in `run_agent.sh`,
not a silent, wrong permission set.

**System prompt:** `opencode run` has no system-prompt flag either. Folded
into the user message instead of an (unconfirmed) agent-config prompt
field.

**Prompt size:** `opencode run`'s documented interface takes the prompt as
a positional CLI argument, not stdin. Several call sites here build prompts
that embed entire files (full diffs, concatenated `docs/` trees) that could
plausibly be large enough to hit `ARG_MAX`. This wasn't testable without a
real OpenCode + OpenRouter run — see "What's unverified" below.

## What's unverified

None of the `north` path has been exercised end-to-end — no Cohere/
OpenRouter account, no OpenCode install available while building this. Before
trusting this provider anywhere, in particular before setting
`AGENT_PROVIDER_AUTOMERGE=north` for `doc-gardener.yml`/
`garbage-collector.yml` (the two workflows that can auto-merge on their
own), confirm:

1. `opencode run --model openrouter/cohere/north-mini-code:free "hello"`
   actually returns a completion with a real `OPENROUTER_API_KEY`.
2. The generated `OPENCODE_CONFIG` agent definition actually restricts tool
   access the way `run_north()` in `scripts/run_agent.sh` assumes (i.e. that
   `opencode run --agent run-agent` really refuses `write`/`edit`/`bash`).
3. A real large prompt (e.g. `doc-gardener.yml`'s full `docs/` tree) doesn't
   get truncated by an `ARG_MAX`-style limit when passed positionally.
4. Output quality is comparable to Claude Sonnet 5 for at least one real run
   of each of the five workflows — this hasn't been compared side by side at
   all yet, just made toggleable.

## How to compare

Add an `OPENROUTER_API_KEY` repository secret first (Settings -> Secrets and
variables -> Actions -> Secrets) -- every path below hard-fails immediately
and loudly without it. Then:

- For `agent-ticket.yml`/`agent-followup.yml`/`quality-grader.yml`: set the
  `AGENT_PROVIDER` repository variable to `north` (same page, Variables tab)
  and manually `workflow_dispatch` one of them against a real issue/PR, or
  wait for the next natural trigger. Set it back to `claude` (or delete it)
  to fall back to today's behavior.
- For `doc-gardener.yml`/`garbage-collector.yml`: set
  `AGENT_PROVIDER_AUTOMERGE` to `north` instead -- a separate, deliberate
  step from the one above, precisely because these two can auto-merge.
  Don't do this until the "what's unverified" items above have real
  answers, and ideally not until you've watched at least one real
  `AGENT_PROVIDER=north` run of the non-auto-merge workflows first.

Locally, prefix a single invocation instead of changing either repo-wide
default: `AGENT_PROVIDER=north make agent-review-local`.

## Related

- #10 proposes the same kind of provider swap for Moonshot's Kimi K* models,
  scoped to `agent-ticket.yml`/`agent-followup.yml` only. `run_agent.sh`'s
  dispatch point is generic enough that adding a third `AGENT_PROVIDER=kimi`
  branch later should follow the same shape as this one.
