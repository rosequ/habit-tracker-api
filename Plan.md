# Plan: Continuous Maintenance — three scheduled Claude Code workflows

## Context

No GitHub issue is linked to this branch — it implements a standalone
request to add "Continuous Maintenance" for this repo: three scheduled
GitHub Actions workflows, each running headless Claude Code on a cron
trigger, in the same style as the existing event-triggered
`agent-followup.yml`/`agent-ticket.yml`.

## What this branch adds

**1. `.github/workflows/doc-gardener.yml`** (daily cron) — headless Claude
Code scans `docs/` and `AGENTS.md` for staleness/contradictions with the
actual code (a documented endpoint that no longer exists, an outdated
architecture description, a broken cross-reference) and fixes them.
Auto-merges (`gh pr merge --squash`) if the diff stays entirely within
`docs/`/`AGENTS.md` and lint/test/gitleaks pass; otherwise falls back to
`needs-human-review`. Every PR it opens is also labeled `doc-gardener`
(created via `gh label create --force`, same as the existing workflows do
for `needs-human-review`) so `quality-grader.yml` can enumerate open
doc-gardener PRs later.

**2. `.github/workflows/garbage-collector.yml`** (weekly cron) — headless
Claude Code finds one small deviation from `AGENTS.md`'s architecture rules
that import-linter's layers contract wouldn't catch stylistically (dead
code, a route doing more than calling a service, small duplicated logic)
and opens a small refactor PR. Auto-merges only if lint/test/gitleaks pass
AND the diff is under 50 changed lines total AND it doesn't touch
`.github/workflows/`, `alembic/versions/`, `uv.lock`, or `pyproject.toml` —
no exceptions on either condition. Every PR it opens is also labeled
`garbage-collector` (created via `gh label create --force`), same reason as
doc-gardener's label above.

**3. `.github/workflows/quality-grader.yml`** (monthly cron) — headless
Claude Code writes/updates `docs/quality.md`: a per-layer
(routes/schemas/services/repository/db) table of import-linter/layering
compliance, doc freshness (last `[doc-gardener]`-tagged touch), and open
cleanup-PR counts. Deliberately no test-coverage-delta column (a weak/
lagging signal) — the compliance column folds in a structural-lint-
violations count instead. **Never auto-merges** — always labeled both
`needs-human-review` and `quality-report` (both created via
`gh label create --force`), since a report generator shouldn't silently
rewrite its own audit trail.

## Why the merge gating works the way it does

This repo can't use GitHub's native `gh pr merge --auto`: that feature's
"wait for required checks" behavior only exists via branch protection,
which 403s here (private repo, Free plan — issue #7; `gh api` also confirms
`allow_auto_merge: false` at the repo level). So `doc-gardener.yml`/
`garbage-collector.yml` run the fast-gates-equivalent checks (lint, test,
gitleaks) inline in their own job right after Claude produces a diff, and a
new shared script decides merge-vs-label synchronously from that result —
no cross-workflow polling or timeouts.

Separately, `GITHUB_TOKEN`-authored pushes/PRs don't cascade into other
workflows' triggers (GitHub's anti-recursion rule). Without accounting for
that, a bot-opened PR would never show a real `fast-gates` check-run, and a
`garbage-collector` auto-merge (a push to `main`) would silently fail to
trigger a Render redeploy.

**4. `scripts/gate_and_merge.sh`** (new) — shared by both auto-merge-
eligible workflows. Reuses `scripts/review_common.sh`'s `review_merge_base`
rather than re-deriving "where did this branch fork from." Computes total
changed lines via `git diff --shortstat`, parsing insertions/deletions
independently (shortstat omits either or both clauses for a mode-only/
binary-only change). Enforces an allow-list (`--require-path-prefix`/
`--require-exact-path`, used by doc-gardener) or a deny-list (`--deny-glob`,
used by garbage-collector) of paths. Merges via `gh pr merge --squash
--delete-branch --subject "<marker> ..."` (explicit subject so the
`[doc-gardener]`/`[garbage-collector]` marker survives regardless of this
repo's ambient squash-message setting, for `quality-grader.yml`'s doc-
freshness tracking) or labels `needs-human-review` with a comment
explaining which condition failed.

**5. `scripts/quality_report_data.sh`** (new) — read-only data-gathering for
`quality-grader.yml`: `lint-imports` output, per-layer file counts, doc-
freshness dates (via `git log --grep '\[doc-gardener\]'`, with a small,
explicit, script-owned mapping from layer to the doc file(s) that describe
it, since `docs/` isn't organized per-layer today), and open cleanup-PR
counts per layer (via `gh pr list` + per-PR `gh pr diff --name-only`
bucketing — PR labels alone only say which workflow opened a PR, not which
layer it touches).

**6. `.github/workflows/deploy.yml`** (edited) — gains a
`workflow_dispatch:` trigger so `garbage-collector.yml` can explicitly
re-dispatch it after an auto-merge: a `GITHUB_TOKEN`-authored push to `main`
doesn't cascade into this workflow's own `push` trigger (GitHub's
anti-recursion rule), so without this, a `garbage-collector` merge would
silently never deploy. `ci.yml`'s `on:` triggers are **not** touched (see
"Fixes made after `agent-review-cloud`" below — an earlier version of this
plan added `workflow_dispatch:` there too, for a purely cosmetic visible
check-run on bot PRs; cut after it caused two real bugs across review for
no gating benefit). `ci.yml` does still get one small, unrelated edit: the
`doc-freshness` job's comment ("Placeholder until a real doc-gardener agent
exists") was stale the moment `doc-gardener.yml` existed, so it's corrected
in this same PR rather than left knowingly wrong.

**7. `AGENTS.md`** (edited) — documents all three new workflows in the
existing "CI/CD" section, plus two accepted risks worth knowing about
later: `doc-gardener.yml`'s auto-merge gate is syntax/scope-only by design
(`make lint-docs` only checks docs are non-empty, no semantic correctness
check), and GitHub auto-disables `schedule:`-triggered workflows after 60
days of repo inactivity (silently — an email, not a visible Actions-tab
failure).

## Fixes made after `agent-review-cloud` (two rounds)

Round 1 caught two real bugs and confirmed a design risk worth investigating:
- `doc-gardener.yml`/`garbage-collector.yml`'s "Check for changes" step used
  `git diff --quiet && git diff --cached --quiet`, which never reports
  brand-new untracked files -- a fix that *adds* a file would report
  `changed=false` and get silently discarded with no PR and no explanation.
  Fixed by unioning in `git ls-files --others --exclude-standard` (the
  pattern `quality-grader.yml`'s own scope check already used correctly).
- `gitleaks/gitleaks-action@v2` only scopes its scan to a commit range for
  `push`/`pull_request` events (verified by reading its actual source on
  GitHub) -- for `workflow_dispatch`/`schedule` (these workflows' own
  triggers) it silently falls back to scanning this repo's *entire* git
  history, which would fail forever on any pre-existing secret-shaped
  string unrelated to the current diff, permanently disabling auto-merge.
  Fixed by running the `gitleaks` CLI directly, scoped to
  `<merge-base>^..HEAD`.

Round 2 caught a bug the round-1 fix introduced: the gitleaks scoping fix
computed `git merge-base HEAD main` and scanned `${merge_base}^..HEAD`, but
at that point in the job nothing had been committed yet (the commit
happened later, in "Push branch and open PR") -- so `HEAD == main`, the
range covered zero of Claude's actual changes, and the "scoped" gitleaks
check was a no-op that would always report clean regardless of what the
agent wrote. Fixed by moving the commit to immediately after the
changes-check, before verification/gitleaks, so both actually run against
the commit that's about to become the PR.

This second bug is a good illustration of a real limitation in the
verification approach below: testing `scripts/gate_and_merge.sh` in
isolation (item 3) validates the *script's* decision logic correctly, but
can't catch a bug in the *surrounding workflow's step ordering* -- that
only surfaced from a reviewer reading the full file, not from a synthetic
harness around one script. The first real `workflow_dispatch` run of each
workflow is still the only true end-to-end check of this interaction.

Round 3 found that adding `workflow_dispatch:` to `ci.yml` (originally done
so `gate_and_merge.sh` could fire-and-forget `gh workflow run ci.yml --ref
<branch>` for a purely cosmetic visible check-run) broke
`async-verification`'s existing failure-follow-up dispatch:
`github.event.pull_request.number` is empty on a `workflow_dispatch`-
triggered run, so `agent-followup.yml` could get dispatched with an empty
`pr_number` if `fast-gates` passed but `make test-integration` then failed.
The same round also flagged that `ci.yml`'s own `gitleaks` step would
inherit the same full-history-scan problem described above once reachable
via `workflow_dispatch`, meaning the "visible check-run" would likely show
red forever regardless of the actual diff -- directly undermining the
auditability it was meant to provide. Given this was the second and third
distinct bug traced back to a feature that never gated anything, the fix
was to cut it entirely rather than patch it a third time: `ci.yml` is back
to its original `on: pull_request:` only, and `gate_and_merge.sh` no longer
dispatches it. `doc-gardener.yml`/`garbage-collector.yml` PRs simply won't
show a `fast-gates` check-run on the Checks tab -- expected, not a bug,
since the inline checks are what actually gate the merge (and the PR body
says so).

Round 4 caught two real bugs plus three cheap non-blocking fixes, none of
them related to the three earlier rounds' fixes (which the reviewer
independently confirmed still held):
- `doc-gardener.yml`'s docs-scan glob (`find docs -type f -name '*.md'`) and
  its merge gate's allow-list (`docs/`/`AGENTS.md`) had no carve-out for
  `docs/quality.md` once `quality-grader.yml` creates it -- doc-gardener's
  daily cron could have auto-merged a rewrite of the monthly report with no
  human ever seeing it, directly contradicting the "never auto-merges"
  guarantee stated three times elsewhere in this same PR. Fixed by adding
  `--deny-glob "docs/quality.md"` to doc-gardener's `gate_and_merge.sh` call
  and telling Claude explicitly not to touch that file.
- `quality-grader.yml`'s "out-of-scope" path (Claude's diff touching
  anything besides `docs/quality.md`) printed a warning and `exit 1`'d --
  no commit, no push, no PR, contradicting its own documented "always opens
  a PR" behavior and burying the only trace in an Actions log nobody
  reviewing PRs would see. Fixed: the "Enforce scope" step now discards
  (via `git checkout --`/`rm -f`) any out-of-scope files before ever
  committing, so this workflow can never ship an app-code diff regardless
  of what Claude wrote; if `docs/quality.md` itself still changed, the PR
  opens as normal with a note listing what was discarded; if
  `docs/quality.md` didn't change at all, a `needs-human-review`-labeled
  issue is filed instead (an unattended agent touching unexpected files is
  worth a human's attention even when nothing merges).
- Non-blocking, also applied: removed `doc-gardener.yml`'s unused
  `actions: write` permission (only `garbage-collector.yml`'s `--redeploy`
  path needs it); both workflows now capture the new PR's number from `gh
  pr create`'s own URL output instead of a separate `gh pr list` lookup
  afterward (avoids an extra round-trip and a small eventual-consistency
  race); `quality_report_data.sh`'s doc-freshness mapping comment no longer
  overstates how clean the routes/schemas vs. services/repository/db split
  actually is.

Round 5 caught two more real bugs in the "changed files" detection this PR
had already patched once (round 1) and once more (round 4's out-of-scope
handling) — both rounds fixed the untracked-file gap but missed a sibling
gap in the same logic:
- `changed="$(git diff --name-only; git ls-files --others --exclude-standard)"`
  (in all three workflows) still missed **staged** changes: bare `git diff
  --name-only` only reports unstaged modifications to tracked files.
  Nothing in any of the three prompts forbids Claude from running `git
  add`, only `git commit`/`push`/`pr create` — so a session that staged its
  edit would make the whole run silently no-op, the exact failure mode
  these checks exist to prevent. Fixed by also unioning in
  `git diff --cached --name-only` everywhere this pattern appears.
- `quality-grader.yml`'s out-of-scope discard used `git checkout --
  "$f"` (no tree-ish), which restores the working tree from the **index**,
  not from `HEAD` — a no-op if the out-of-scope file was staged, since the
  index already matches the working tree at that point. Fixed by using
  `git checkout HEAD -- "$f"` instead, which resets both.
- Non-blocking, also applied: `deploy.yml`'s and `AGENTS.md`'s "main is
  protected and requires fast-gates" comments were stale (directly
  contradicted by this same PR's own issue #7 discussion a few lines away
  in both files) — corrected while already touching both. `AGENTS.md`'s
  `doc-gardener.yml` bullet now mentions the `docs/quality.md` carve-out.
  `doc-gardener.yml`'s `docs_tree` glob now excludes `docs/quality.md`
  (harmless before, but no reason to spend prompt context on a file Claude
  is told never to touch). Clarified this section's own wording: `ci.yml`'s
  triggers aren't touched, but its `doc-freshness` comment is (a small,
  unrelated, worthwhile fix while already in the file).

Round 6 caught one more real bug in the exact same `quality-grader.yml`
discard logic rounds 4 and 5 had already touched twice — deciding
restore-vs-remove by whether the path was currently *in the index*
(`git ls-files --error-unmatch`) rather than whether it exists *in HEAD*
mishandled two more unattended-agent scenarios: a staged deletion of a
tracked out-of-scope file (`git rm`) fell into the `rm -f` no-op branch,
silently leaving the deletion staged and riding along into the commit; a
staged brand-new out-of-scope file took the `git checkout HEAD --`
branch, which errors out (no HEAD blob to restore) and aborts the whole
step under GitHub Actions' default `bash -eo pipefail`. Fixed by
unconditionally `git reset -q HEAD --`-ing the path first, then deciding
restore-vs-remove via `git cat-file -e "HEAD:$f"` instead of the index —
this handles staged modifications, staged deletions, and staged/unstaged
new files uniformly, and can't fail on a path `HEAD` never had. Also
applied two non-blocking suggestions: `garbage-collector.yml`'s inline
verification now also runs `make lint-docs` (nothing in its prompt forbids
touching `docs/`, even though it's scoped to `app/`), for consistency with
`doc-gardener.yml` rather than silently having no check there at all; the
gitleaks release asset name (`gitleaks_8.24.3_linux_x64.tar.gz`) was
already directly confirmed to exist via `gh api
repos/gitleaks/gitleaks/releases/tags/v8.24.3` while building this (not
left as an unverified assumption) — noting that explicitly here since the
reviewer couldn't see that check from the diff alone.

Round 7 found one real, blocking **security** bug (a first for this PR's
review history) plus more cheap non-blocking fixes:
- **GitHub Actions script injection via unsanitized `${{ }}` interpolation
  directly into a `run:` script body**, in `quality-grader.yml`'s "Push
  branch and open PR" and "File an issue" steps. `steps.scope.outputs.out_of_scope`
  is built from file paths an unattended, `--permission-mode
  bypassPermissions` Claude session chose (via `git diff`/`git ls-files`) --
  `${{ }}` expressions are substituted into the script text *before* bash
  ever runs it, so a path containing `"`, a backtick, or `$(...)` could
  break out of the script and execute arbitrary shell with this job's
  `contents`/`issues`/`pull-requests: write` token. The exact threat model
  ("Claude's own output is untrusted-shaped text") was already reasoned
  about elsewhere in this same PR (the heredoc-delimiter comments in all
  three prompts) but missed here specifically. Fixed at both call sites by
  passing `out_of_scope` via `env: OUT_OF_SCOPE: ${{ ... }}` and referencing
  `"$OUT_OF_SCOPE"` in the script instead -- `env:` values are data, never
  re-parsed as script, closing off the injection vector entirely. (The
  remaining `${{ steps.verify.outcome }}`/`${{ steps.gitleaks.outcome }}`
  usages elsewhere are safe as-is: those are GitHub-controlled enum values,
  not attacker-influenced text.)
- Non-blocking, also applied: `garbage-collector.yml`'s `gate_and_merge.sh`
  call now also `--deny-glob`s `docs/quality.md` (nothing previously stopped
  a small, otherwise-compliant garbage-collector diff from touching and
  auto-merging over the quality report, the same invariant doc-gardener's
  round-4 fix specifically protects); both workflows' gitleaks download now
  points at `https://github.com/gitleaks/gitleaks/releases/...` directly
  instead of `zricethezav/gitleaks` (a redirect that happens to work today,
  but that's a fragile foundation for something that permanently gates
  auto-merge if it ever stops); `quality_report_data.sh` now has a comment
  flagging its flat-directory-structure assumption explicitly.
- Explicitly deferred as a real but out-of-scope follow-up: `agent-followup.yml`
  still uses the old `git diff --quiet && git diff --cached --quiet`
  change-detection pattern (misses untracked files) that this PR fixed
  three times over in the new workflows -- not touched here since it's an
  existing, separately-shipped workflow, but the bug class is now well
  understood and worth a dedicated follow-up.

Round 8: `APPROVE`, no blocking issues -- this round specifically
stress-tested the two highest-risk-looking patterns (heredoc interpolation
of untrusted doc content, and the Round 7 injection fix itself) and
independently re-verified every prior round's fix against the actual repo
state, confirming each still holds. Two trivial, purely cosmetic fixes
applied anyway: `"${failed[*]}"` with `IFS=', '` only actually joins on
the *first* character of IFS (a comma, no space), so `verify_detail`'s
failed-checks list was silently missing the intended space -- fixed with
`printf ', %s' "${failed[@]}"` + strip the leading separator, in both
`doc-gardener.yml` and `garbage-collector.yml`. Fixed a grammar slip in
`AGENTS.md` ("fire-and-forgot" a `gh workflow run`, missing the verb).

Round 9 caught a real off-by-one in the one piece of logic this PR's own
review history had already spent two whole rounds getting right:
- **`${merge_base}^..HEAD` (with the caret) is not "just the commits this
  branch adds on top of main"**, contrary to what the comment on that same
  line (and `AGENTS.md`, and this very Plan.md) claimed. `A^..B` excludes
  ancestors of `A^` (A's parent) -- but `A` itself (`merge_base`) is not an
  ancestor of its own parent, so `A` is included too. Since these branches
  always add exactly one commit on top of `main`, this over-scanned an
  extra, already-merged `main` commit on every run. Verified directly with
  a throwaway two-commit-deep repo: `git log merge_base^..HEAD` returned
  both the new commit and `main`'s tip; `git log merge_base..HEAD` (no
  caret) returned only the new commit, as intended. Impact was over-scanning
  (a false-fail risk on an already-vetted `main` commit under gitleaks CLI
  detection-rule/version drift vs. `ci.yml`'s `gitleaks-action@v2`), not
  under-scanning -- but still undermined the one property (auto-merge
  reliability) these workflows exist to provide. Fixed by dropping the caret
  in both `doc-gardener.yml` and `garbage-collector.yml`.
- Non-blocking, also applied: `quality-grader.yml`'s `grep -vx`/`grep -qx`
  scope checks against the literal string `docs/quality.md` used an
  unescaped `.` (matches any character, not just a literal dot) -- switched
  to `grep -vFx`/`grep -qFx` (fixed-string) for precision, even though the
  practical risk was negligible. Added an explicit accepted-gap note to
  `AGENTS.md`'s `garbage-collector.yml` bullet: because its bot-authored PR
  never triggers `ci.yml`'s `pull_request` event (same anti-recursion rule
  used throughout this PR), a garbage-collector auto-merge never gets
  `async-verification`/`make test-integration` run against it at all --
  strictly less test coverage than a normal human PR gets, for the one
  workflow that can auto-merge a change to `app/` code.
- Checked, not changed: the extracted gitleaks release tarball's `gitleaks`
  binary already has its executable bit set in the archive itself
  (confirmed via `tar -tvzf` on the actual v8.24.3 asset: `-rwxr-xr-x`), so
  no explicit `chmod +x` is needed after `tar -xz`. `gh pr merge`'s
  non-interactive behavior with an explicit `--squash` wasn't independently
  re-verified against a real merge into `main` -- doing so would mean
  fabricating a real, hard-to-cleanly-reverse merge into this repo's actual
  history just to test an unknown that's low-risk (gh CLI's prompt library
  is TTY-gated, and CI-driven `gh pr merge` with an explicit strategy flag
  is an extremely common, well-established pattern industry-wide) and that
  the reviewer itself frames as a first-real-run check, not a
  diff-blockable one.

Round 10: `APPROVE` again, independently re-verifying every prior round's
fix against the actual repo state (not just trusting this Plan.md's
narrative) — explicitly confirmed the Round 9 range fix, the Round 7
injection fix, the Round 6 discard logic, `gate_and_merge.sh`'s parsing,
and the flat-`app/`-structure assumption all hold as described. Three
remaining non-blocking suggestions, explicitly noted as not affecting
correctness/security: applied the cheap one (`quality-grader.yml`'s "File
an issue" step now creates the `needs-human-review` label itself rather
than assuming another workflow already has, for self-containment); left
two as accepted, genuinely low-impact nits rather than continuing to chase
diminishing returns after two consecutive `APPROVE` verdicts (`gh pr
create`'s stdout URL-parsing could use `--json url` on a `gh` version that
supports it instead of `${pr_url##*/}`; `quality-grader.yml` leaves no
trail at all in the one edge case where Claude decides literally nothing
needs updating and never touches an out-of-scope file either).

## Out of scope

- Seeding an initial `docs/quality.md` — left for `quality-grader.yml`'s
  first real run to create, not manually pre-populated by this branch.
- A PAT-based alternative to `deploy.yml`'s `workflow_dispatch:` re-dispatch
  (would let it fire naturally on a `garbage-collector` merge instead of
  being explicitly re-dispatched) — considered and rejected for now given
  this is a solo-maintainer repo and the shim avoids a new secret/bus-factor
  concern.
- A semantic/LLM-judge correctness gate on doc-gardener's content (beyond
  the mechanical docs/AGENTS.md-only scope check) — the existing
  `make lint-docs` non-emptiness placeholder is the only content-adjacent
  check; adding more is future work, not this branch's.

## Verification

1. `make lint` — passes (ruff, import-linter, file-size guard; none of
   these files are Python so only the workflow/script additions themselves
   are new surface area, and none trip the file-size limit).
2. All new/edited YAML parses (`yaml.safe_load`); every embedded `run:`
   bash block extracted and passed `bash -n`.
3. `scripts/gate_and_merge.sh`'s decision logic exercised against 5
   synthetic scenarios in an isolated scratch git repo (outside this
   working tree): a small in-scope diff merges; a >50-line diff, a diff
   touching a denied path, a diff touching a path outside doc-gardener's
   allow-list, and a diff with `--verify-passed false` all correctly fall
   back to labeling instead of merging.
4. The `git diff --shortstat` line-count parser verified directly against
   insertions-only / deletions-only / mode-only (neither clause present)
   inputs.
5. `scripts/quality_report_data.sh` run directly against this repo's real
   state — correct per-layer file counts, correct doc-freshness dates for
   the two existing doc files.
6. Confirmed live via `gh api repos/rosequ/habit-tracker-api` that branch
   protection 403s and `allow_auto_merge` is `false` — the fact this whole
   design works around.
7. Not independently verifiable without a real Actions run: the actual
   `claude -p` prompts inside each workflow haven't executed end-to-end (a
   dry run in an isolated git worktree was attempted and blocked by this
   environment's own permission classifier for spawning a nested unattended
   Claude session) — the first `workflow_dispatch` run of each new workflow
   after merge is the real first test of prompt quality.
