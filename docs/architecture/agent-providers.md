# Agent provider dispatch (#15)

Every unattended-agent call site — the five `.github/workflows/*.yml` jobs
that run a headless agent (`agent-ticket.yml`, `agent-followup.yml`,
`doc-gardener.yml`, `garbage-collector.yml`, `quality-grader.yml`) plus the
two local review scripts (`agent_review_local.sh`, `agent_review_cloud.sh`)
— pipes its prompt into `scripts/run_agent.sh` on stdin instead of calling
`claude -p` directly. `AGENT_PROVIDER` picks the backend in that one place.

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
trusting this provider anywhere, in particular before pointing
`AGENT_PROVIDER=north` at `doc-gardener.yml` or `garbage-collector.yml` (the
two workflows that can auto-merge on their own), confirm:

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

Set the `AGENT_PROVIDER` repository variable to `north` (Settings ->
Secrets and variables -> Actions -> Variables), add an `OPENROUTER_API_KEY`
repository secret, and manually `workflow_dispatch` one of the workflows
against a real issue/PR. Set the variable back to `claude` (or delete it)
to fall back to today's behavior. Locally, prefix a single invocation
instead of changing the repo-wide default: `AGENT_PROVIDER=north make
agent-review-local`.

## Related

- #10 proposes the same kind of provider swap for Moonshot's Kimi K* models,
  scoped to `agent-ticket.yml`/`agent-followup.yml` only. `run_agent.sh`'s
  dispatch point is generic enough that adding a third `AGENT_PROVIDER=kimi`
  branch later should follow the same shape as this one.
