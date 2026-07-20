#!/usr/bin/env bash
# Placeholder for `make lint-docs`: checks that AGENTS.md and docs/ files
# exist and are non-empty. A real doc-gardener agent (checking content
# actually matches the code) is future work -- this just catches the trivial
# "docs got deleted or left empty" case.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

status=0

if [[ ! -s AGENTS.md ]]; then
    echo "AGENTS.md is missing or empty" >&2
    status=1
fi

doc_files="$(find docs -type f -name '*.md' 2>/dev/null || true)"
if [[ -z "$doc_files" ]]; then
    echo "No markdown files found under docs/" >&2
    status=1
else
    while IFS= read -r f; do
        if [[ ! -s "$f" ]]; then
            echo "$f is empty" >&2
            status=1
        fi
    done <<< "$doc_files"
fi

if [[ "$status" -eq 0 ]]; then
    echo "docs look present and non-empty"
fi

exit "$status"
