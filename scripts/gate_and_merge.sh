#!/usr/bin/env bash
# Shared merge-or-label decision for doc-gardener.yml / garbage-collector.yml.
#
# Both workflows already: ran Claude Code, ran the same checks fast-gates
# runs (inline, in their own job -- see the "why not gh pr merge --auto"
# comment in AGENTS.md), and unconditionally opened a PR regardless of
# outcome (same paper-trail-always pattern as agent-followup.yml /
# agent-ticket.yml). This script makes the actual merge-vs-label call and,
# if it merges, is the only place that runs `gh pr merge`.
#
# This repo can't use GitHub's native `gh pr merge --auto`: that feature's
# "wait for required checks" semantics only exist via branch protection,
# which 403s here (private repo, Free plan -- issue #7). So this script IS
# the gate, evaluated synchronously from the inline check result this run
# already has in hand -- no polling, no timeout to tune.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/review_common.sh

PR=""
VERIFY_PASSED=""
VERIFY_DETAIL="the inline verification (lint/test/gitleaks) did not pass"
MARKER=""
MAX_DIFF_LINES=""
REDEPLOY=0
declare -a DENY_GLOBS=()
declare -a REQUIRE_PATH_PREFIXES=()
declare -a REQUIRE_EXACT_PATHS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr) PR="$2"; shift 2 ;;
        --verify-passed) VERIFY_PASSED="$2"; shift 2 ;;
        --verify-detail) VERIFY_DETAIL="$2"; shift 2 ;;
        --marker) MARKER="$2"; shift 2 ;;
        --max-diff-lines) MAX_DIFF_LINES="$2"; shift 2 ;;
        --deny-glob) DENY_GLOBS+=("$2"); shift 2 ;;
        --require-path-prefix) REQUIRE_PATH_PREFIXES+=("$2"); shift 2 ;;
        --require-exact-path) REQUIRE_EXACT_PATHS+=("$2"); shift 2 ;;
        --redeploy) REDEPLOY=1; shift ;;
        *) echo "gate_and_merge.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$PR" || -z "$VERIFY_PASSED" || -z "$MARKER" ]]; then
    echo "gate_and_merge.sh: --pr, --verify-passed, and --marker are required" >&2
    exit 2
fi

merge_base="$(review_merge_base)"
changed_files="$(git diff --name-only "$merge_base")"

reasons=()

if [[ "$VERIFY_PASSED" != "true" ]]; then
    reasons+=("$VERIFY_DETAIL")
fi

# `git diff --shortstat` omits the insertions clause, the deletions clause,
# or both (a mode-only or binary-only change can produce just "1 file
# changed" with no numbers at all) -- extract each independently rather than
# assume a fixed field layout, which would silently break on exactly the
# kind of diff this script has to handle safely.
if [[ -n "$MAX_DIFF_LINES" ]]; then
    shortstat="$(git diff --shortstat "$merge_base")"
    insertions="$(grep -oE '[0-9]+ insertion' <<< "$shortstat" | grep -oE '[0-9]+' || true)"
    deletions="$(grep -oE '[0-9]+ deletion' <<< "$shortstat" | grep -oE '[0-9]+' || true)"
    total=$(( ${insertions:-0} + ${deletions:-0} ))
    echo "==> Diff size vs $merge_base: $total changed lines (limit: $MAX_DIFF_LINES)"
    if (( total > MAX_DIFF_LINES )); then
        reasons+=("the diff is $total changed lines, over the $MAX_DIFF_LINES-line limit")
    fi
fi

if [[ ${#DENY_GLOBS[@]} -gt 0 ]]; then
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        for pattern in "${DENY_GLOBS[@]}"; do
            # shellcheck disable=SC2053 -- intentional glob match, not literal
            if [[ "$f" == $pattern ]]; then
                reasons+=("it touches '$f', which matches denied path '$pattern'")
            fi
        done
    done <<< "$changed_files"
fi

if [[ ${#REQUIRE_PATH_PREFIXES[@]} -gt 0 || ${#REQUIRE_EXACT_PATHS[@]} -gt 0 ]]; then
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        allowed=0
        for prefix in "${REQUIRE_PATH_PREFIXES[@]}"; do
            [[ "$f" == "$prefix"* ]] && allowed=1
        done
        for exact in "${REQUIRE_EXACT_PATHS[@]}"; do
            [[ "$f" == "$exact" ]] && allowed=1
        done
        if [[ "$allowed" -eq 0 ]]; then
            reasons+=("it touches '$f', which is outside the allowed scope for this workflow")
        fi
    done <<< "$changed_files"
fi

if [[ ${#reasons[@]} -gt 0 ]]; then
    echo "==> Not auto-merging PR #$PR:"
    printf '  - %s\n' "${reasons[@]}"
    gh label create needs-human-review --color B60205 --description "Unattended agent output -- requires human review before merge" --force
    gh pr edit "$PR" --add-label needs-human-review
    body="Automated auto-merge check did not pass, so this needs a human decision instead:
$(printf -- '- %s\n' "${reasons[@]}")"
    gh pr comment "$PR" --body "$body"
    exit 0
fi

echo "==> All auto-merge conditions met for PR #$PR -- merging."
pr_title="$(gh pr view "$PR" --json title -q .title)"
if ! gh pr merge --squash --delete-branch --subject "$MARKER $pr_title" "$PR"; then
    # If the merge itself fails (e.g. main moved and now conflicts, or a
    # permissions hiccup), don't let `set -e` just abort here -- that would
    # leave the PR silently unlabeled and unmerged, with no trail explaining
    # why. Fall back to the same needs-human-review path as a failed gate.
    echo "==> gh pr merge failed for PR #$PR -- falling back to needs-human-review." >&2
    gh label create needs-human-review --color B60205 --description "Unattended agent output -- requires human review before merge" --force
    gh pr edit "$PR" --add-label needs-human-review
    gh pr comment "$PR" --body "Automated merge attempt failed (see this run's log) after all auto-merge conditions passed -- needs a human to investigate and merge manually."
    exit 0
fi

if [[ "$REDEPLOY" -eq 1 ]]; then
    # garbage-collector's merge just pushed to main via GITHUB_TOKEN, which
    # (same anti-recursion rule) does NOT cascade into deploy.yml's `push`
    # trigger -- without this, Render would silently keep serving a stale
    # build until some unrelated human push happened to land.
    gh workflow run deploy.yml --ref main || echo "warning: could not dispatch deploy.yml (non-fatal)" >&2
fi
