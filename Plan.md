# Plan: agent review loop tooling

Add a two-stage agent review loop as Makefile targets, for implementers to run
against their own branches before opening/updating a PR.

## Changes

- `Makefile` — add `agent-review-local` and `agent-review-cloud` targets; add
  `scripts/check_file_sizes.py` as a third step of `make lint`.
- `scripts/check_file_sizes.py` — new. Enforces the 400-line file limit from
  AGENTS.md as part of `make lint` (previously undocumented-only).
- `scripts/review_common.sh` — new. Shared helpers: base-branch diff, Plan.md
  presence check, linked-issue-number resolution (explicit `ISSUE` env var or
  a `Closes #N`/`Fixes #N`/`Resolves #N` keyword in the PR body only --
  deliberately does not grep Plan.md prose for a bare `#N`, since a plan can
  mention an issue in passing without that issue being the one it closes).
  Also strips `CLAUDE_CODE_SESSION_ID`/`CLAUDE_CODE_CHILD_SESSION` from the
  environment so nested `claude -p` calls can never attach to the calling
  (implementer's) session. `review_full_diff` unions in untracked
  (non-ignored, not-yet-`git add`ed) files as synthetic new-file diffs, since
  plain `git diff <merge-base>` only shows changes to already-tracked paths.
- `tests/test_check_file_sizes.py` — new. Exercises `check_file_sizes.py`
  end-to-end against a throwaway git repo: one file under the limit, one over.
- `scripts/agent_review_local.sh` — new. Runs `make lint`, then asks a Haiku
  model (headless `claude -p`, no tools) whether the diff matches Plan.md.
  Exits non-zero on lint failure or unplanned diff.
- `scripts/agent_review_cloud.sh` — new. Spawns an isolated, read-only-tools
  Claude Code subagent (Sonnet by default) with the full diff, Plan.md, and
  the linked GitHub issue's acceptance criteria; exits non-zero if it
  requests changes. Writes the review to `.agent-review/`.
- `.gitignore` — ignore generated `.agent-review/` output.
- `AGENTS.md` — document the two new targets, the local -> cloud loop, and
  that the `claude` CLI must be installed/authenticated separately.
- `Plan.md` — this file.

### Robustness fixes from the review loop itself

- Both scripts' prompt heredocs use a unique delimiter (not `EOF`), since
  they interpolate untrusted/arbitrary prose (`Plan.md`, GitHub issue body)
  that could contain a bare `EOF` line and silently truncate the prompt.
- `review_merge_base` prints a warning (not silent) when it falls back to
  the repo's first commit, since that turns "diff vs `BASE_REF`" into "diff
  vs entire history."
- `agent_review_cloud.sh`'s issue section distinguishes "no issue linked"
  from "issue linked but `gh issue view` failed" instead of conflating them.

## Out of scope

- Actually implementing the habit-completion feature (issue #3) — this
  branch is tooling only.
- Auto-posting cloud review comments back to the GitHub PR (kept local to
  `.agent-review/` + stdout for now).
