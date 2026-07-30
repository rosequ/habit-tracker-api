# Plan: Add timeout-minutes to all agent-driven CI jobs

## Context

Issue #23 ("Add GET /habits/{habit_id}/completions") was labeled
`agent-ready` and picked up by `agent-ticket.yml` (run 30206804182). It hung
on the "Ask the agent to implement the issue" step and never completed --
GitHub eventually killed it at its hard 6-hour job ceiling
("The job has exceeded the maximum execution time of 6h0m0s"), with no PR
opened and no error surfaced anywhere a human would see it short of opening
the Actions tab.

The same thing happened the same day to a Doc Gardener rerun (run
30079528989, also killed at 6h0m0s), and again the next day to three more
`agent-ticket.yml` runs (issues #35, #36, #37) that each ran 35-50+ minutes
before being stopped. `scripts/run_agent.sh`'s `run_north()` path (OpenCode
CLI against OpenRouter) has no internal timeout, so if that endpoint stalls
or is rate-limited, the calling job just sits -- there's nothing between
"a couple minutes" and "6 hours."

Every healthy run observed so far (`agent-ticket.yml` on issues #8, #19;
`doc-gardener.yml`'s successful run) finished well under 10 minutes on the
agent step specifically, and well under 15 minutes end to end including
lint/test/smoke.

## What this branch changes

Adds `timeout-minutes: 30` to the single job in each of the five
agent-driven workflows, so a stuck agent call fails loud in ~30 minutes
instead of silently occupying a runner for up to 6 hours:

- **`.github/workflows/agent-ticket.yml`** (`implement` job)
- **`.github/workflows/agent-followup.yml`** (`fix-and-pr` job)
- **`.github/workflows/doc-gardener.yml`** (`garden` job)
- **`.github/workflows/garbage-collector.yml`** (`collect` job)
- **`.github/workflows/quality-grader.yml`** (`grade` job)

30 minutes is roughly 3x the slowest healthy run-time observed, leaving
headroom for a legitimately slow-but-working call while still cutting off
a genuine hang well short of the 6-hour ceiling.

## Out of scope

- Retrying or backing off within `run_agent.sh`/`run_north()` itself --
  that's a deeper change to the OpenCode CLI invocation; this branch only
  bounds the outer CI job.
- Alerting/notification on workflow failure (there currently isn't any,
  for any workflow) -- a real gap, but a separate concern from bounding
  run time.
- Re-triggering issue #23 -- done separately (relabel `agent-ready`) once
  this fix is merged, not part of this diff.

## Verification

- `make lint` -- passes (no app code touched, workflow YAML only).
- Each edited file: confirmed `timeout-minutes` sits at the job level
  (same indentation as `runs-on`), not nested under `services` or a step,
  by inspection of each diff.
