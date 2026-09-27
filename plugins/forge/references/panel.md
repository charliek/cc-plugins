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

### gx and Cursor — `explore` subagents, plus the astra seat

The OpenAI seat is always **`gpt-6-astra`**: plan review is where the frontier model pays for its extra time. Spawn the subagent seats as `explore` children with `run_in_background: true`, `model` from the table, description prefixed `(model) Panel: …`. Paste the full plan between `---BEGIN PLAN---` / `---END PLAN---`. Instruct: read-only; you MAY read other repo files for context; do not edit; return specific actionable findings by category and severity.

| Seat | gx | Cursor |
|---|---|---|
| Astra | `gpt-6-astra` subagent (stock grok: the codex runner) | the codex runner, from the orchestrator's shell |
| Grok | `grok-4.7` subagent | `grok-4.7-high` subagent |
| Third | `glm-5.3` subagent | `gemini-3.7-flash-high` subagent |

A runner seat is launched the same way as in the Claude Code section below — in the background, next to the subagent seats — and batch-waited with them.

Batch-wait with the harness caps: 20 minutes for the Grok and third seats, 25 for astra, checking every 10 minutes that each seat is still producing (the runner does this itself) and killing a flat one early. Empty output is a failed seat, not "no findings". A big plan that stalls astra gets one retry with a narrower brief (design and work-breakdown sections), not a longer cap.

OpenRouter GPT ids are never a panel fallback. If the astra seat fails, report that seat failed.

### Claude Code — compatibility column (shell-outs)

Check `codex --version` and `opencode --version`. Warn and skip a missing CLI. If none of the three can run, stop.

**Panel brief** — write it once with the file-writing tool, next to the plan (`<plan dir>/panel-brief.md`, outside the repo): the shared review questions above, ending "The plan follows." The astra and GLM seats both read it, followed by the plan file itself, so nothing in the plan is ever expanded by the shell. Every command here is plain — no variables, `$(…)`, or heredocs, which a session pinned to a worktree refuses. Use resolved absolute paths in single quotes (`~` does not expand inside quotes; write an embedded `'` as `'\''`).

**Astra** (if `codex` is available) — the codex runner (`harness.md` §Codex runner; `<runner path>` from its step 1), launched by the orchestrator as a background shell call, **not** inside a subagent: astra on a whole plan can outlast the 10-minute ceiling of a subagent's foreground shell call, and the runner supervises it (25-minute cap, killed early if flat for 10 minutes).

```bash
uv run --script '<runner path>' --model astra --prompt-file '<brief path>' --prompt-file '<plan path>'
```

A non-zero exit is a failed seat; report the runner's reason. `python3 '<runner path>'` works the same where `uv` is missing.

**GLM** (if `opencode` is available) — also a background shell call from the orchestrator, not a subagent (whole-plan GLM reviews outlast a subagent's 10-minute shell call). The argument restricts its tools: in non-interactive mode, opencode kills the run as soon as GLM tries a shell command or reads outside the repo. Always use `--` before the message.

```bash
cat -- '<brief path>' '<plan path>' | opencode run -m zai-coding-plan/glm-5.3 -- 'Follow the review brief on stdin; the full plan follows it. Use ONLY your read, grep and glob tools, and ONLY on files inside the current repository directory. Do not run shell commands.'
```

Stop it with the task-stop tool if it is still running at 20 minutes. A stopped run, a non-zero exit, or empty output is a failed seat.

**CodeRabbit:** spawn `subagent_type: "coderabbit:code-reviewer"` with
`run_in_background: true`, `model: sonnet` if the spawn tool accepts it
(otherwise inherit), the full plan, and the shared review questions; ask it
to read relevant repo files and **not** edit. If that agent type is missing,
skip and say so.

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
