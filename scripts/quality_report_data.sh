#!/usr/bin/env bash
# Gathers the raw, ground-truth data quality-grader.yml's Claude Code
# invocation needs to write docs/quality.md, so the model synthesizes a
# report from real numbers instead of guessing them from a diff (same
# pre-fetch-then-synthesize pattern agent-followup.yml/agent-ticket.yml use
# for PR diffs and issue bodies). Entirely read-only: no DB needed, only
# git/gh and the already-installed import-linter.
#
# Deliberately best-effort throughout (`|| true` on nearly every git/gh
# call): this is a monthly report, not a gate -- a transient gh API hiccup
# should degrade one section to "couldn't fetch this" in the model's input,
# not fail the whole workflow run. Claude still sees the gap (an empty/error
# string in its prompt context) and can call it out in the report narrative.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

LAYERS=(routes schemas services repository db)

# Every glob below (`app/$layer/*.py`, `docs/domains/*/README.md`) assumes a
# flat, one-level directory per layer/domain -- true of this repo today
# (verified), but it would silently under-count files if any layer ever
# grows subpackages. Revisit if that happens.
echo "=== import-linter (uv run lint-imports) ==="
uv run lint-imports || true
echo

echo "=== Per-layer file counts ==="
for layer in "${LAYERS[@]}"; do
    count="$(git ls-files "app/$layer/*.py" | wc -l | tr -d ' ')"
    echo "app/$layer: $count files"
done
echo

# Doc-freshness mapping: docs/ isn't organized per code-layer today (only
# docs/architecture/api-conventions.md and docs/domains/*/README.md exist),
# so this mapping is owned here, in one place, rather than invented by the
# model each run. It's a simplification, not a precise partition -- e.g.
# api-conventions.md's "Schemas vs DB models" section and its layering
# description are just as relevant to routes/schemas as to
# services/repository/db, which this split doesn't capture. Assigned
# routes/schemas -> the domain READMEs (endpoint/field-facing) and
# services/repository/db -> api-conventions.md (business-logic/async/storage
# conventions) as the more-relevant-in-practice split; revisit if docs/ ever
# grows a real per-layer structure.
echo "=== Doc freshness (last [doc-gardener]-tagged commit, or last commit by anyone if none yet) ==="
freshness_for() {
    local label="$1"; shift
    local paths=("$@")
    local existing=()
    for p in "${paths[@]}"; do
        while IFS= read -r f; do
            [[ -n "$f" ]] && existing+=("$f")
        done < <(git ls-files "$p" 2>/dev/null || true)
    done
    if [[ ${#existing[@]} -eq 0 ]]; then
        echo "$label: (no matching doc files exist yet)"
        return
    fi
    local tagged
    tagged="$(git log -1 --grep '\[doc-gardener\]' --format=%aI -- "${existing[@]}" 2>/dev/null || true)"
    if [[ -n "$tagged" ]]; then
        echo "$label: $tagged (doc-gardener touch) -- ${existing[*]}"
    else
        local any
        any="$(git log -1 --format=%aI -- "${existing[@]}" 2>/dev/null || true)"
        echo "$label: ${any:-never} (no doc-gardener touch yet; last touch by anyone) -- ${existing[*]}"
    fi
}
freshness_for "routes/schemas"  "docs/domains/*/README.md"
freshness_for "services/repository/db" "docs/architecture/api-conventions.md"
echo

echo "=== Open cleanup PRs per layer ==="
if command -v gh >/dev/null 2>&1; then
    for label in doc-gardener garbage-collector; do
        pr_numbers="$(gh pr list --state open --label "$label" --json number -q '.[].number' 2>/dev/null || true)"
        if [[ -z "$pr_numbers" ]]; then
            echo "$label: 0 open PRs"
            continue
        fi
        echo "$label open PRs:"
        while IFS= read -r n; do
            [[ -z "$n" ]] && continue
            files="$(gh pr diff "$n" --name-only 2>/dev/null || true)"
            echo "  #$n touches:"
            for layer in "${LAYERS[@]}"; do
                touched="$(grep -c "^app/$layer/" <<< "$files" || true)"
                [[ "$touched" -gt 0 ]] && echo "    app/$layer: $touched file(s)"
            done
            grep -q "^docs/" <<< "$files" && echo "    docs/: yes"
        done <<< "$pr_numbers"
    done
else
    echo "gh CLI not available -- cannot enumerate open PRs"
fi
