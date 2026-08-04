# docs/plans/ — archived Plan.md / Implement.md

Every branch overwrites the repo root's `Plan.md` (and often
`Implement.md`) — they're mechanically required per-branch by
`require_plan_staged` in `.githooks/pre-commit`, but nothing keeps a
running record of them across branches. This folder is that record.

## Convention

Right before merging a PR (after the last update to `Plan.md`/
`Implement.md`, before `gh pr merge`), run:

```
make archive-plan
```

which copies the current branch's `Plan.md` (and `Implement.md`, if
present) into:

```
docs/plans/<issue-or-date>-<slug>.md
```

- `<issue-or-date>` — the GitHub issue number this branch closes, if one
  can be resolved (`ISSUE` env var, the branch name, or an open PR's
  "Closes #N" body), else today's date (`YYYY-MM-DD`).
- `<slug>` — a short descriptive slug, inferred from the branch name or
  the plan's own title if not passed explicitly
  (`make archive-plan SLUG=my-slug`).

Commit the resulting `docs/plans/*.md` file as part of the same PR that's
about to merge. See `scripts/archive_plan.sh` for the exact resolution
logic, and `AGENTS.md`'s "Archiving plans" section for why this is a
manual step rather than a `ci.yml`/git-hook automation.

This is a manual convention, not mechanically enforced — a skipped archive
doesn't break anything, it just means that branch's plan is lost the same
way it always has been.
