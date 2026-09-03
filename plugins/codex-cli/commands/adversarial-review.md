---
description: Run a Codex review that challenges the implementation approach and design choices
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [--model <model>] [--effort <level>] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(codex:*), Bash(git:*), AskUserQuestion
---

Run an adversarial code review through the Codex CLI. Frame it as a **challenge review** that questions the chosen implementation, design choices, tradeoffs, and assumptions — not just a stricter pass over implementation defects.

Raw slash-command arguments:
`$ARGUMENTS`

Default model: `gpt-5.6-sol` at `model_reasoning_effort="high"` (override with `--model <id>` and/or `--effort <level>`).

Core constraint:

- This command is **review-only**. Do not fix issues, apply patches, edit files, or suggest you are about to make changes.
- Your only job is to run the review and return Codex's output verbatim.
- Keep the framing on whether the current approach is the right one, what assumptions it depends on, and where the design could fail under real-world conditions.

Determine the review target and execution mode exactly as in `/codex-cli:review`:

- `--scope working-tree`/`auto` → uncommitted changes; `--scope branch`/`--base <ref>` → branch diff against `<ref>` (default base `main`).
- `--wait` → foreground, `--background` → Claude background task, neither → size the change (`git status --short --untracked-files=all`, `git diff --shortstat [--cached]`, or `git diff --shortstat <base>...HEAD`) and ask once via `AskUserQuestion` (`Wait for results` / `Run in background`), recommending background unless the change is clearly tiny.
- Unlike `/codex-cli:review`, any trailing text after the flags is **focus text** — preserve it and steer the review toward it.

Run the review:

`codex exec review`'s scope flags cannot be combined with custom instructions, so this command uses plain `codex exec -s read-only` instead and **feeds the diff in — do not ask Codex to discover the changes itself** (same approach as the cursor plugin: a deterministic layer extracts the diff and hands it to the reviewer). Build the prompt as a single pipeline: a quoted heredoc carries the adversarial instructions (and any focus text), and `git` streams the diff into the same stdin; the trailing `-` argument tells `codex exec` to read the prompt from stdin. The quoted heredoc means focus text and diff content are never shell-expanded.

Because the heredoc body includes user-controlled focus text, **always use a per-invocation random delimiter** (shown below as `CODEX_REVIEW_9f3a2b1c`) and never the bare `CODEX_REVIEW`. The unpredictable suffix means focus text can never match the delimiter and close the heredoc early. Use the same token for the opener and closer; generate a fresh one each invocation. (The streamed diff cannot collide regardless — it arrives after the heredoc closes.)

- **Working-tree scope:**

  ```bash
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT
  {
    cat <<'CODEX_REVIEW_9f3a2b1c'
  Adversarially review the code changes below — the uncommitted working-tree changes of this repository, provided inline between the "=== BEGIN CHANGES ===" and "=== END CHANGES ===" markers. Do NOT run `git diff` or otherwise re-derive the changes yourself; they are provided. This is review-only — do not edit anything. You MAY read other files in the repo for context, but do not modify anything. Challenge the approach itself: question the design choices, tradeoffs, and assumptions; identify where this could fail under real-world conditions (scale, concurrency, failure modes, edge cases, maintainability); and propose stronger alternatives where the chosen approach is weak. Also read any untracked files listed in the changed-files section (their contents are not in the diff). <If focus text was provided, append: "Focus especially on: <focus text>."> Order findings by severity, each with exact file path and line number where applicable and a short rationale.
  CODEX_REVIEW_9f3a2b1c
    echo "=== BEGIN CHANGES ==="
    echo; echo "--- changed files ---"; git status --short --untracked-files=all
    echo; echo "--- staged diff ---"; git diff --cached
    echo; echo "--- unstaged diff ---"; git diff
    echo "=== END CHANGES ==="
  } | codex exec -s read-only -m gpt-5.6-sol -c model_reasoning_effort="high" \
    -o "$tmpdir/review.txt" - >"$tmpdir/stdout.txt" 2>"$tmpdir/stderr.txt"
  status=$?
  if [ $status -ne 0 ] || [ ! -s "$tmpdir/review.txt" ]; then
    echo "codex exec failed (exit $status). Last stderr/stdout:"
    tail -n 40 "$tmpdir/stderr.txt" "$tmpdir/stdout.txt"
    exit 1
  fi
  cat "$tmpdir/review.txt"
  ```

- **Branch / base scope** (replace `<base>` with the resolved ref, default `main`): use the same pipeline but stream `git diff --name-status <base>...HEAD` and `git diff <base>...HEAD`, and word the heredoc as "the diff of HEAD against <base>". **Validate the ref first** with `git rev-parse --verify --quiet "<base>"` and stop with an error if it doesn't resolve — a failed `git diff` inside the pipeline would otherwise feed Codex an empty diff that reads as "nothing to review" while the pipeline still exits 0.
- **Very large diffs (~900+ changed lines):** do not stream the diff inline — redirect it to a file (`git diff --cached > "$tmpdir/changes.diff"; git diff >> "$tmpdir/changes.diff"`) and point Codex at that path instead of the `=== BEGIN CHANGES ===` block. The path must be emitted **outside** the quoted heredoc (nothing expands inside it) — `echo "Read this diff file first: $tmpdir/changes.diff"` in the same `{ … }` group, after the closing delimiter. Word the heredoc: "the changes are in the diff file named below; do NOT run `git diff`; read only the functions you need, with narrow line ranges; budget 8 minutes and at most 25 file reads; print the report and stop." Also demand a fixed per-item verdict — `no issue — why, file:line`, or a finding with `file:line` plus the concrete failure scenario — and the list of files + line ranges read. A streamed 30k-line diff burns the whole cap without ever reaching a verdict.
- `-s read-only` keeps Codex read-only (it analyzes and may read files, but makes no edits). Use `timeout: 600000` on foreground runs. For `--background`, launch the pipeline with `run_in_background: true` and tell the user: "Codex adversarial review started in the background." Do not wait for it in this turn.
- If the user passed `--model <id>`, use it in place of `gpt-5.6-sol`; if `--effort <level>`, use it in place of `high`.

Present results:

- Return Codex's review output verbatim, findings first, ordered by severity, with file paths and line numbers exactly as reported. A failed or empty run is NOT "no findings" — report it as a failure.
- **CRITICAL — stop before fixing:** After presenting the findings, STOP. Do not make any code changes or fix any issues. You MUST explicitly ask the user which issues, if any, they want addressed before touching a single file.
