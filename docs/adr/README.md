# Architecture Decision Records

An ADR is a short document that records a single architecture-level
decision: the context that forced it, what was decided, and the
consequences (including tradeoffs, not just benefits). The goal is to
capture the *why* once, in one durable place, instead of re-explaining it
in scattered workflow comments or prose that later gets edited without the
reasoning behind it.

## When to write one

Write an ADR when a change:
- Picks between two or more real alternatives for structural reasons
  (not just a bug fix or routine feature work).
- Introduces a constraint or convention future contributors (human or
  agent) need to know about to avoid quietly re-opening a settled question.
- Works around a limitation of an external system (a platform tier, an
  API, a tool) in a way that isn't obvious from reading the code alone.

Not every change needs one — routine features, bug fixes, and refactors
that follow existing conventions don't. When in doubt, prefer writing one;
it's cheap to write and expensive to reconstruct the reasoning later.

## How to add one

1. Copy [`template.md`](./template.md) to `NNNN-kebab-case-title.md`,
   where `NNNN` is the next number below, zero-padded to four digits.
2. Fill in Context / Decision / Consequences. Set Status to `Proposed` if
   it still needs discussion, or `Accepted` if the decision is already in
   effect.
3. Add a row to the index below.
4. If a later ADR reverses or replaces an earlier one, don't delete or
   rewrite the old one — add a new ADR and update the old one's Status to
   `Superseded by [NNNN](./NNNN-....md)`. The history of *why* something
   changed is as valuable as the current state.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](./0001-two-agent-provider-variables.md) | Split `AGENT_PROVIDER` into two independent repository variables | Accepted |
| [0002](./0002-plan-md-precommit-gate.md) | Mechanical `Plan.md`-before-implementation pre-commit gate | Accepted |
| [0003](./0003-client-side-hooks-branch-protection-stopgap.md) | Client-side git hooks as a stopgap for missing branch protection | Accepted |
