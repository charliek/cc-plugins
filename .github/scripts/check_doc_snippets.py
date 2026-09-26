#!/usr/bin/env python3
"""Syntax-check every ```bash / ```sh block in the repo's markdown with `bash -n`.

The plugins' markdown is executable instructions: agents copy these snippets
and run them. A snippet that doesn't parse (an unclosed heredoc, a stray
quote) fails at the worst moment, mid-flow. `bash -n` parses without running
anything, so placeholders like "<plan-file-path>" inside quotes are fine.

Usage: check_doc_snippets.py [root]   (default: the repository root)
"""

import re
import subprocess
import sys
import textwrap
from pathlib import Path

# A fence may be indented (a code block inside a list item); the closing
# fence must match the opening indentation.
FENCE = re.compile(r"^([ \t]*)```(?:bash|sh)[ \t]*\n(.*?)^\1```[ \t]*$", re.S | re.M)
SKIP_DIRS = {".git", "node_modules", ".venv"}


def blocks(path: Path):
    text = path.read_text(encoding="utf-8")
    for match in FENCE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        yield line, textwrap.dedent(match.group(2))


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])
    checked, failures = 0, []
    for path in sorted(root.rglob("*.md")):
        if SKIP_DIRS.intersection(path.relative_to(root).parts):
            continue
        for line, body in blocks(path):
            checked += 1
            result = subprocess.run(["bash", "-n"], input=body, capture_output=True, text=True)
            # An unterminated heredoc is only a *warning* to `bash -n` (exit 0),
            # and it is exactly the bug this check exists for: any output fails.
            if result.returncode != 0 or result.stderr.strip():
                failures.append((path.relative_to(root), line, result.stderr.strip()))
    for rel, line, err in failures:
        print(f"{rel}:{line}: bash -n failed\n  {err}")
    print(f"checked {checked} shell blocks; {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
