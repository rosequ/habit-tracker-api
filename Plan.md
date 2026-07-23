# Plan: Force-push agent/issue-N branches in agent-ticket.yml

## Context

Issue #19 ("Add GET /habits to list all habits") was labeled `agent-ready`
and picked up by `agent-ticket.yml`. The first run failed at the
"Push branch and open PR" step because the repo's Actions permissions had
"Allow GitHub Actions to create and approve pull requests" disabled
(`gh pr create` returned a GraphQL permission error). After that setting
was enabled and the job was rerun, it failed again at the same step, this
time with `git push` rejected as non-fast-forward: the first (failed) run
had already pushed `agent/issue-19` to the remote, and the rerun's fresh
local branch of the same name no longer matched it.

`agent/issue-N` branches are exclusively created and pushed by this job —
no human or other workflow ever pushes to them, and a PR only exists
against one if this same job already succeeded in opening it. A retry
(manual rerun, or a second `agent-ready` labeling of the same issue) should
therefore be free to overwrite its own previous attempt instead of failing
and requiring someone to manually delete the stale remote branch first.

## What this branch changes

**`.github/workflows/agent-ticket.yml`** — the "Push branch and open PR"
step now runs `git push --force origin "$BRANCH"` instead of a plain
`git push origin "$BRANCH"`, with a comment explaining why the force-push
is safe (branch is exclusively owned by this job).

## Out of scope

- Deleting old `agent/issue-N` branches after their PR merges or closes —
  separate cleanup concern, not needed for retries to work.
- Any change to the PR-creation permission itself (already fixed via repo
  settings, not code).

## Verification

- Change is a single-line flag addition to an existing, already-exercised
  `git push` invocation; no new logic paths. Confirmed the line still
  reads as valid YAML/bash (`bash -n` equivalent by inspection — it's a
  single-word flag inserted into an existing `run:` block).
