# Plan: Issue #28 — Extend doc-gardener.yml to reconcile against accepted ADRs

## What
`doc-gardener.yml`'s prompt currently tells the agent to compare
`AGENTS.md` + `docs/` against one source of truth: the actual code. Once
`docs/adr/` (issue #26) and `docs/architecture/ARCHITECTURE.md` (issue #25)
exist, an **Accepted** ADR is a second source of truth that should also
propagate into `ARCHITECTURE.md`/`AGENTS.md`, the same way a code change
does today.

## Why the mechanics don't need to change
- The `docs_tree` shell snippet already does
  `find docs -type f -name '*.md' -not -path 'docs/quality.md' ...` — that
  already recursively includes `docs/adr/*.md` and
  `docs/architecture/ARCHITECTURE.md` once they exist. Nothing to change
  there.
- `scripts/gate_and_merge.sh` is invoked with
  `--require-path-prefix docs/` and `--require-exact-path AGENTS.md` — any
  path under `docs/adr/` or `docs/architecture/` already satisfies that
  prefix. Nothing to change there either, and per the issue this
  mechanical enforcement must not be weakened.

## What actually changes
Only `.github/workflows/doc-gardener.yml`: the prompt text embedded in the
`Ask the agent to garden the docs` step, plus the file's top-of-file
descriptive comment (kept in sync with the new behavior, same as it
already documents the rest of the job):
- Add a new paragraph telling the agent to treat any `docs/adr/*.md` file
  whose front matter says `Status: Accepted` as an additional
  authoritative source (alongside the actual code) when checking
  `ARCHITECTURE.md`/`AGENTS.md` for staleness or contradictions.
- Explicitly instruct it to ignore ADRs that are `Proposed`/draft/anything
  other than `Accepted` — not yet decided, not to be reconciled against.
- Explicitly instruct it to never author a new ADR and never edit anything
  under `docs/adr/` itself — that directory is a historical record it
  reads *from*, not a target it writes *to*. (The existing hard scope
  limit paragraph — only `docs/`/`AGENTS.md`, never `docs/quality.md`,
  never code, mechanically enforced by `gate_and_merge.sh` — is left
  otherwise unchanged.)

## Out of scope (explicitly not doing)
- Not creating `docs/adr/` or `ARCHITECTURE.md` — those land from #26/#25
  in parallel worktrees.
- Not touching any other workflow file, `.githooks/pre-commit`,
  `.githooks/pre-push`, or `scripts/gate_and_merge.sh`.
- Not implementing #25/#26/#27/#29.

## Verification
Since this is a workflow-prompt-only change with no runtime code touched,
`make smoke` isn't relevant. Run `make lint`, `make test`,
`make agent-review-local`, then `make agent-review-cloud`.
