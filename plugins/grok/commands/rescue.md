---
description: Delegate investigation, an explicit fix request, or follow-up work to the Grok CLI
argument-hint: "[--background|--wait] [--resume|--fresh] [--read-only] [--model <model>] [--effort <level>] [what Grok should investigate, solve, or continue]"
context: fork
allowed-tools: Bash(grok:*), Bash(python3:*), AskUserQuestion
---

Hand this request to the Grok CLI via headless `grok` and return its final message verbatim.

Raw user request:
$ARGUMENTS

Default model: `grok-4.6` at `--effort high` (override with `--model <id>` and/or `--effort <level>`). List ids with `grok models`.

Build a single `grok` invocation. **Grok headless does not treat a bare `-p` pipe as the prompt** (`-p` requires a value). Feed the task through **`--prompt-file /dev/stdin`** with a quoted heredoc on that process's stdin, never as an inline quoted `-p` argument. That prevents `$(...)`, backticks, `$VAR`, quotes, and newlines in the task from being expanded by Bash.

**Always use a per-invocation random delimiter** — append fresh random hex to the base token (shown below as `GROK_TASK_9f3a2b1c`) and never use the bare `GROK_TASK`. Because the suffix is unpredictable and unique per call, the task text can never match the delimiter and terminate the heredoc early. Use the same token for the opener and closer; generate a new one each invocation.

**Do not name the prompt file `*.json`.** `--prompt-file` parses `.json` as ACP content blocks, not raw text. `/dev/stdin` is safe.

Write-capable run (the default):

```bash
export GROK_MEMORY=0
export GROK_DISABLE_AUTOUPDATER=1
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
grok --prompt-file /dev/stdin \
  --output-format json \
  --always-approve \
  --model grok-4.6 \
  --effort high \
  --no-auto-update \
  >"$tmpdir/out.json" 2>"$tmpdir/stderr.txt" <<'GROK_TASK_9f3a2b1c'
<task text exactly as the user gave it, with routing flags stripped>
GROK_TASK_9f3a2b1c
status=$?
if [ $status -ne 0 ]; then
  echo "grok failed (exit $status). Last stderr/stdout:"
  tail -n 40 "$tmpdir/stderr.txt" "$tmpdir/out.json"
  exit 1
fi
python3 -c '
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except Exception as e:
    print(f"grok: failed to parse JSON output: {e}", file=sys.stderr)
    sys.exit(1)
text = data.get("text") or ""
sid = data.get("sessionId") or ""
if sid:
    print(f"GROK_SESSION_ID={sid}", file=sys.stderr)
if not str(text).strip():
    print("grok: empty text in JSON output (not a valid result)", file=sys.stderr)
    sys.exit(1)
sys.stdout.write(text if text.endswith("\n") else text + "\n")
' "$tmpdir/out.json"
```

Read-only run (when `--read-only` is present, or the user only wants review/diagnosis/research without edits) — keep `--always-approve` (so reads and shell do not stall) and add `--sandbox read-only`. Do **not** rely on `--disallowed-tools` or `--permission-mode plan` for this: plan mode is Grok's planning phase, not a write lock, and a tool denylist still leaves `write` / `apply_patch` / `run_terminal_cmd`.

Flag handling (strip these from the task text before placing it in the heredoc body — they are controls, not part of the prompt):

- `--background`: run the `Bash` call with `run_in_background: true` and tell the user the Grok task started in the background. Do not wait for it this turn.
- `--wait` (or neither): run in the foreground with `timeout: 600000` (the maximum; Grok tasks can run several minutes).
- `--read-only`: add `--sandbox read-only`.
- `--model <id>`: use it in place of `grok-4.6`. Validate before use: accept only ids matching `[A-Za-z0-9._-]+`; reject anything else (it would be interpolated into shell syntax outside the quoted heredoc).
- `--effort <level>`: use it in place of `high`. Allowlist strictly — accepted values are exactly `low`, `medium`, `high`, `xhigh`; reject anything else. Fast mode is `low`. Do not invent a `--fast` flag. `xhigh` is valid on `grok-4.6` only.
- `--resume <uuid>`: add `--resume <uuid>` (continue that exact session). Validate the UUID as `[A-Za-z0-9-]+`.
- `--resume` with no UUID: add `-c` (newest session in this working directory). **Caveat:** `-c` races if another Grok run is in flight here — prefer `--fresh` (with the prior context restated in the task text) when parallel runs are plausible. `--resume` **can** be combined with `--read-only`: sandbox is a process flag, not inherited from the prior session.
- `--fresh`: do not add `-c` or `--resume`. If neither `--resume` nor `--fresh` is present and the user is clearly continuing prior Grok work ("continue", "keep going", "apply the top fix", "dig deeper"), resume with `-c`; otherwise run fresh.

Output:

- Return the extracted `text` field (Grok's final message) verbatim. Do not paraphrase, summarize, rewrite, or add commentary before or after it.
- `GROK_SESSION_ID=…` on stderr is for the next `--resume <uuid>`; do not treat it as part of the answer.
- By default the run is write-capable (`--always-approve`), so Grok may edit files and run commands. Changes land in the current git repo and are reviewable via `git diff`.
- On failure, do **not** fabricate a substitute answer, and never present an empty result as "no findings". Do **not** retry with `--effort low` — that is a weaker pass, not a serving-pool backup. Report the failure concisely (most actionable stderr lines); if `grok` looks missing or unauthenticated, direct the user to `/grok:setup`.
- If the user did not supply a request, ask what Grok should investigate or fix before running.
