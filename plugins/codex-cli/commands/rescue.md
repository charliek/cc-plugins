---
description: Delegate investigation, an explicit fix request, or follow-up work directly to the Codex CLI (codex exec)
argument-hint: "[--background|--wait] [--resume|--fresh] [--read-only] [--model <model>] [--effort <level>] [what Codex should investigate, solve, or continue]"
context: fork
allowed-tools: Bash(codex:*), AskUserQuestion
---

Hand this request to the Codex CLI via `codex exec` and return its final message verbatim.

Raw user request:
$ARGUMENTS

Default model: `gpt-5.6-sol` at `model_reasoning_effort="high"` (override with `--model <id>` and/or `--effort <level>`).

Build a single `codex exec` invocation. **Pass the task text via a quoted heredoc on stdin, never as an inline quoted argument** — this prevents `$(...)`, backticks, `$VAR`, quotes, and newlines in the task from being expanded by Bash. The trailing `-` argument tells `codex exec` to read the prompt from stdin.

**Always use a per-invocation random delimiter** — append fresh random hex to the base token (shown below as `CODEX_TASK_9f3a2b1c`) and never use the bare `CODEX_TASK`. Because the suffix is unpredictable and unique per call, the task text can never match the delimiter and terminate the heredoc early. Use the same token for the opener and closer; generate a new one each invocation.

Write-capable run (the default):

```bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
codex exec -m gpt-5.6-sol -c model_reasoning_effort="high" -s workspace-write \
  -o "$tmpdir/last.txt" - <<'CODEX_TASK_9f3a2b1c' >"$tmpdir/stdout.txt" 2>"$tmpdir/stderr.txt"
<task text exactly as the user gave it, with routing flags stripped>
CODEX_TASK_9f3a2b1c
status=$?
if [ $status -ne 0 ] || [ ! -s "$tmpdir/last.txt" ]; then
  echo "codex exec failed (exit $status). Last stderr/stdout:"
  tail -n 40 "$tmpdir/stderr.txt" "$tmpdir/stdout.txt"
  exit 1
fi
cat "$tmpdir/last.txt"
```

Read-only run (when `--read-only` is present, or the user only wants review/diagnosis/research without edits) — replace `-s workspace-write` with `-s read-only`.

Flag handling (strip these from the task text before placing it in the heredoc body — they are controls, not part of the prompt):

- `--background`: run the `Bash` call with `run_in_background: true` and tell the user the Codex task started in the background. Do not wait for it this turn.
- `--wait` (or neither): run in the foreground with `timeout: 600000` (the maximum; Codex tasks can run several minutes).
- `--read-only`: use `-s read-only` instead of `-s workspace-write`.
- `--model <id>`: use it in place of `gpt-5.6-sol`.
- `--effort <level>`: use it in place of `high` in `-c model_reasoning_effort="..."`. Accepted values: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`.
- `--resume`: use `codex exec resume --last - <<'...'` to continue the most recent Codex session in this repo. **Caveats:** `resume` accepts `-m`, `-c`, and `-o` but NOT `-s` (the sandbox mode carries over from the resumed session), and `--last` picks the newest session in this repo — if several Codex tasks run here in parallel, it may continue the wrong one, so prefer `--fresh` (with the prior context restated in the task text) when parallel runs are plausible. `--fresh`: run fresh. If neither is given and the user is clearly continuing prior Codex work ("continue", "keep going", "apply the top fix", "dig deeper"), resume; otherwise run fresh.

Output:

- Return the contents of `$tmpdir/last.txt` (Codex's final message) verbatim. Do not paraphrase, summarize, rewrite, or add commentary before or after it.
- By default the run is write-capable (`-s workspace-write`), so Codex may edit files and run commands inside its workspace-write sandbox. Changes land in the current git repo and are reviewable via `git diff`.
- On failure, do **not** fabricate a substitute answer, and never present an empty result as "no findings". Report the failure concisely (most actionable stderr lines); if `codex` looks missing or unauthenticated, direct the user to `/codex-cli:setup`.
- If the user did not supply a request, ask what Codex should investigate or fix before running.
