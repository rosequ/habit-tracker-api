# Plan.md - Documentation Freshness Fixes

This plan documents the documentation inconsistencies found in AGENTS.md and the fixes needed to reconcile them with the actual code.

## Issues Found

### 1. Inconsistent terminology in "three scheduled workflows"

**Problem:** AGENTS.md uses inconsistent terminology around "three scheduled workflows".

In AGENTS.md line 245, it says:
- "None of the three scheduled workflows above can use GitHub's native gh pr merge --auto..."

This is unclear because AGENTS.md earlier lists 5 scheduled workflows, not 3:
- `agent-ticket.yml` — implements an issue labeled `agent-ready` on a new branch; opens a `needs-human-review` PR, never merges.
- `agent-followup.yml` — dispatched on integration-test failure; fixes forward on a new branch, opens a `needs-human-review` PR.
- `doc-gardener.yml` — daily cron; fixes stale/contradictory docs. Can auto-merge if the diff stays within `docs/`/`AGENTS.md` and gates pass.
- `garbage-collector.yml` — weekly cron; small architecture-deviation refactors. Can auto-merge under tighter conditions (diff size, path restrictions).
- `quality-grader.yml` — monthly cron; writes `docs/quality.md`. Never auto-merges.

The issue is that line 245 refers to "three scheduled workflows" but it's unclear which three it's referring to. The commentary explains that `doc-gardener.yml` and `garbage-collector.yml` run the fast-gates checks inline, implying that the "three scheduled workflows" are the ones that never auto-merge (agent-ticket.yml, agent-followup.yml, quality-grader.yml).

**Fix Applied:** Updated AGENTS.md line 245 to be more precise: "None of the three workflows that never auto-merge (agent-ticket.yml, agent-followup.yml, quality-grader.yml) can use GitHub's native gh pr merge --auto..."

**Additional issue:** AGENTS.md line 285 also uses "three scheduled workflows above" but should specify "three of the scheduled workflows above" or "three of the scheduled workflows" since there are actually 5 scheduled workflows.

**Fix Applied:** Updated AGENTS.md line 285 to be more precise: "If one of the scheduled workflows above appears to have stopped running..."

## Summary of Fixed Issues

1. **AGENTS.md line 245**: Clarified which "three scheduled workflows" are being referenced by specifying "three workflows that never auto-merge (agent-ticket.yml, agent-followup.yml, quality-grader.yml)"
2. **AGENTS.md line 285**: Clarified "three scheduled workflows" by removing the count and just saying "one of the scheduled workflows"

These are documentation consistency fixes that clarify the terminology without changing the actual code or behavior.