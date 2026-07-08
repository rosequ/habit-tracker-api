#!/usr/bin/env python3
"""Fail if any tracked Python file exceeds the repo's line-count limit (see AGENTS.md)."""

from __future__ import annotations

import subprocess
import sys

LIMIT = 400


def tracked_python_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.py"], capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line]


def main() -> int:
    violations = []
    for path in tracked_python_files():
        with open(path, encoding="utf-8") as fh:
            count = sum(1 for _ in fh)
        if count > LIMIT:
            violations.append((path, count))

    if not violations:
        return 0

    print(f"Files exceeding the {LIMIT}-line limit:")
    for path, count in violations:
        print(f"  {path}: {count} lines")
    print("Split the file instead of suppressing this check.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
