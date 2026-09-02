# Ask-panel procedure

Run after `harness.md` and `plan.md`. Once a plan file exists in house
style, make it review-ready, run three seats in parallel, synthesize,
incorporate, report.

## 1. Locate or create the plan

Follow `plan.md` "When to write vs review":

1. If `$ARGUMENTS` has a leading `--harness gx|cursor|claude`, strip it.
   Treat the **entire remainder** as a plan path only when it is a single
   path-shaped token (no spaces unless quoted as one path) that exists as a
   file after `~` expansion (`test -f`). Otherwise it is a **scope brief**,
   even if some word in it happens to match a filename.
2. Else if a plan is already active in this conversation, use it.
3. Else if the user asked to make a plan (brief in `$ARGUMENTS` or in this
   conversation), write one per `plan.md` and continue.
4. Else search both `~/.cursor/plans/<repo>/` and `~/.claude/plans/<repo>/`
   (whichever are readable) and take the newest `*.md`; report which path.
5. If still none, ask for a path or a brief and stop.

## 2. Readiness checklist

Read the plan. Edit it to fill gaps before sending to reviewers. Required:

- [ ] Context: why this change is being made
- [ ] File list of paths to create or modify
- [ ] Acceptance criteria a reader can treat as exit criteria
- [ ] Test / verification plan
- [ ] Standalone: understandable without prior chat
- [ ] Matches the repo's existing patterns

## 3. Launch three seats in parallel

Warn that this may take a couple of minutes. Read the full plan so it can go inline in each prompt. **Do not combine reviewers into one spawn or one shell command.**

Shared review questions (every seat):

1. Is the plan standalone without conversation context?
2. Are acceptance criteria clear, actionable, and sufficient as exit criteria?
3. Does it include adequate test / verification coverage?
4. Does it match the repo's architectural patterns and conventions?
5. Risks, gaps, or missing edge cases?

Weight by agreement and by evidence cited — do not treat any one seat as automatically strongest.

### gx and Cursor — native `explore` subagents

Spawn three `explore` children with `run_in_background: true`, `model` from the harness table, description prefixed `(model) Panel: …`. Paste the full plan between `---BEGIN PLAN---` / `---END PLAN---`. Instruct: read-only; you MAY read other repo files for context; do not edit; return specific actionable findings by category and severity.

| Seat | gx `model` | Cursor `model` |
|---|---|---|
| Sol | `gpt-5.6-sol` | `gpt-5.6-sol-high` |
| Grok | `grok-4.6` | `cursor-grok-4.6-high` |
| Third | `glm-5.3` | `gemini-3.7-flash-high` |

Batch-wait (10-minute cap, then kill). Empty output is a failed seat, not "no findings".

OpenRouter Sol is never a panel fallback. If ChatGPT-plan Sol fails, report that seat failed.

### Claude Code — compatibility column (shell-outs)

Check `codex --version` and `opencode --version`. Warn and skip a missing CLI. If none of the three can run, stop.

**Sol** (if `codex` is available) — pipe the plan as **data**, never interpolate
it into a double-quoted shell string. Set the shell-tool timeout to 600000 and
kill the process at 600s (`perl -e 'alarm 600; exec @ARGV' --`). Trailing `-`
reads stdin. `codex exec` is `-s read-only`.

```bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
run_codex() { perl -e 'alarm 600; exec @ARGV' -- "$@"; }
{
  cat <<'EOF'
Review the following implementation plan. Evaluate standalone readability, acceptance criteria, test coverage, and repo pattern alignment. Provide specific, actionable feedback organized by category.
---BEGIN PLAN---
EOF
  cat -- "<plan-file-path>"
  echo '---END PLAN---'
} | run_codex codex exec -m gpt-5.6-sol -c model_reasoning_effort="high" -s read-only \
  -o "$tmpdir/codex.txt" - 2>"$tmpdir/stderr.txt"
if [ $? -ne 0 ] || [ ! -s "$tmpdir/codex.txt" ]; then
  cat "$tmpdir/stderr.txt"
  exit 1
fi
cat "$tmpdir/codex.txt"
```

**GLM** (if `opencode` is available) — pipe the plan via stdin; always use `--` before the message:

```bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
cat "<plan-file-path>" | opencode run \
  -m "zai-coding-plan/glm-5.3" \
  -- "Review the following implementation plan. Evaluate: 1) Is the plan standalone? 2) Are acceptance criteria clear? 3) Does it include test coverage? 4) Does it match repo conventions? Provide specific, actionable feedback." \
  > "$tmpdir/output.txt" 2>"$tmpdir/stderr.txt"
if [ $? -ne 0 ] || [ ! -s "$tmpdir/output.txt" ]; then
  cat "$tmpdir/stderr.txt"
  exit 1
fi
cat "$tmpdir/output.txt"
```

Launch each of those as its own sonnet-class (`model: sonnet`) **`Explore`**
subagent (`run_in_background: true`) that returns only the review text.
`Explore` is read-only; do not use writable `general-purpose` for panel seats.
The wrapper may run `codex`/`opencode` (those CLIs are `-s read-only` / stdin
review) but must not edit the workspace.

**CodeRabbit:** spawn `subagent_type: "coderabbit:code-reviewer"` with
`model: sonnet` if the spawn tool accepts it (otherwise inherit), the full
plan, and the shared review questions; ask it to read relevant repo files and
**not** edit. If that agent type is missing, skip and say so.

## 4. Synthesize and incorporate

Evaluate every finding on its own merit. Consensus (multiple seats) is higher confidence; a single-seat finding is still valid. When seats contradict, flag for the user rather than picking autonomously. Skip only genuine nitpicks and style-only suggestions. Apply the rest to the plan file. Record panel corrections in the plan's header, including any degraded quorum (`degraded panel (1/3)`).

## 5. Report

- Per-reviewer finding counts
- Multi-reviewer findings (highest confidence)
- Single-reviewer findings addressed
- Findings skipped, and why
- Contradictions flagged for the user
- Tool / seat failures
- Quorum: 3/3, 2/3, or degraded
