# Plan: Recover the stranded continuous-maintenance review fixes

## Context

PR #13 ("Add three scheduled Continuous Maintenance workflows") merged only
the first commit of its source branch (`add-continuous-maintenance-workflows`).
A second commit on that same branch — "Apply 11 rounds of agent-review-cloud
fixes to the continuous-maintenance workflows" (`337214b`) — was pushed to
the remote branch *after* #13 had already merged, so it never made it into
`main` and has no PR of its own. It sat there, reachable only via
`origin/add-continuous-maintenance-workflows`, until this branch recovers it.

This branch is exactly that recovery: `git cherry-pick 337214b` onto current
`main`, nothing else. No new behavior beyond what that commit already
contained and had already been through 11 rounds of `agent-review-cloud` for.

## What's in the recovered commit

Real bugs found and fixed across `doc-gardener.yml`, `garbage-collector.yml`,
`quality-grader.yml`, `scripts/gate_and_merge.sh`, and
`scripts/quality_report_data.sh` (the full round-by-round narrative is
preserved verbatim in commit `337214b`'s own message, carried into this
branch by the cherry-pick — not repeated here to avoid a second,
divergent copy of the same history):

- A GitHub Actions script-injection hole: `quality-grader.yml` interpolated
  an untrusted step output (file paths an unattended, `bypassPermissions`
  Claude session chose) directly into a `run:` script body instead of
  passing it via `env:`.
- `gitleaks/gitleaks-action@v2` silently scanning this repo's entire git
  history instead of just the current diff on `workflow_dispatch`/`schedule`
  triggers, which would have permanently disabled auto-merge on any
  pre-existing secret-shaped string unrelated to the actual change.
- Untracked-file and staged-file gaps in all three workflows' "did anything
  change" detection, which could silently no-op a run that actually produced
  a diff.
- `doc-gardener.yml` and `garbage-collector.yml` both missing a
  `docs/quality.md` carve-out, so either could have auto-merged over
  `quality-grader.yml`'s report with no human ever seeing it.
- `quality-grader.yml`'s out-of-scope-file discard mishandling staged
  deletions and staged new files.
- An off-by-one in the gitleaks commit range (`${merge_base}^..HEAD`
  over-scanned one already-merged `main` commit).
- Commit-before-verify step ordering, so gitleaks/lint/test actually scope
  themselves against the diff about to become the PR, not a stale range.

## Out of scope

- Anything beyond what `337214b` already contained -- this branch is a pure
  recovery, not a chance to make further changes to these workflows. Any
  further work (e.g. #15's provider-toggle) belongs in its own branch, based
  on top of this one once merged.

## Verification

1. `git diff 416e342 337214b -- .github/workflows/ scripts/` reviewed
   directly to confirm the cherry-pick's content matches what was described
   in the original 11-round review (no drift from rebasing/cherry-picking).
2. `make lint` and `make test` run against the merged result.
3. Not independently re-verified end-to-end beyond what `337214b`'s own
   commit message already documents (its point 7: the actual `claude -p`
   prompts haven't executed end-to-end outside a real Actions run) -- this
   branch doesn't change that; it only stops the fixes from being lost.
