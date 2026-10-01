#!/usr/bin/env python3
"""Syntax-check every ```bash / ```sh block in the repo's markdown with `bash -n`.

The plugins' markdown is executable instructions: agents copy these snippets
and run them. A snippet that doesn't parse (an unclosed heredoc, a stray
quote) fails at the worst moment, mid-flow. `bash -n` parses without running
anything, so placeholders like "<plan-file-path>" inside quotes are fine.

An unclosed code fence is reported too: it silently swallows the rest of the
document, including any shell block after it.

Usage: check_doc_snippets.py [root]   (default: the repository root)
"""

import re
import subprocess
import sys
import textwrap
from pathlib import Path

# CommonMark fences: 3+ backticks or tildes, optionally indented (a block
# inside a list item). Blockquoted fences ("> ```") are not tracked.
OPENER = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})[ \t]*(?P<info>[^`\s]*)")
SHELLS = {"bash", "sh"}
SKIP_DIRS = {".git", "node_modules", ".venv"}


def blocks(path: Path):
    """Yield (line, info, body, closed) for every fenced block in the file."""
    lines = path.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines):
        opened = OPENER.match(lines[i])
        if not opened:
            i += 1
            continue
        fence, start = opened.group("fence"), i
        closer = re.compile(rf"^[ \t]*{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$")
        i += 1
        body = []
        while i < len(lines) and not closer.match(lines[i]):
            body.append(lines[i])
            i += 1
        closed = i < len(lines)
        yield start + 1, opened.group("info").lower(), textwrap.dedent("\n".join(body) + "\n"), closed
        i += 1


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])
    checked, failures = 0, []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if SKIP_DIRS.intersection(rel.parts):
            continue
        for line, info, body, closed in blocks(path):
            if not closed:
                failures.append((rel, line, "code fence is never closed"))
                continue
            if info not in SHELLS:
                continue
            checked += 1
            result = subprocess.run(["bash", "-n"], input=body, capture_output=True, text=True)
            # An unterminated heredoc is only a *warning* to `bash -n` (exit 0),
            # and it is exactly the bug this check exists for: any output fails.
            if result.returncode != 0 or result.stderr.strip():
                failures.append((rel, line, "bash -n: " + result.stderr.strip()))
    for rel, line, err in failures:
        print(f"{rel}:{line}: {err}")
    print(f"checked {checked} shell blocks; {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
