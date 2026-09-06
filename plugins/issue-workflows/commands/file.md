# File an issue

Write and file one well-formed GitHub issue following
`references/conventions.md`. `$ARGUMENTS` is the raw report — a symptom, a
paste of failing output, a rough idea, or nothing at all (then use what
this session already found).

This is the command that makes the convention stick: it labels every issue
without being asked, which is why the corpus is unlabelled today.

## 1. Decide whether it should exist

If you cannot write the "Why it matters" line, say so and stop. A finding
nobody will act on is noise in a list of eighty. Also check it is not
already filed:

```bash
gh issue list -R "$R" --state all --search "<distinctive words>" --limit 10
```

## 2. Separate what you observed from what you inferred

Before drafting, split the material into three piles: what was **observed**
(commands run, output seen, file:line read), what is **inferred**, and what
is **guessed**. Only the first goes in Evidence as fact; the second is
written with `Hypothesis:` in front of it; the third is left out.

Getting this wrong is the most damaging thing an agent-filed issue can do,
because a confident wrong cause sends the next session down a dead end.

## 3. Draft the title

Rule 1 of the conventions: a finding, not a topic. `<area>: <the claim>,
<the consequence>`. Present tense for defects, "should become true" for
changes. No bare imperatives.

Read it back as if it were the only line you would ever see about this
problem. If it does not say what breaks, it is not done.

## 4. Draft the body

Sections from the conventions, in order, dropping any that would be
padding — except **Acceptance, which is required if anyone will work
this**. Write acceptance as checkboxes that someone else can verify.

Reference related issues inline by number.

## 5. Choose labels

- `type/` — required. Exactly one.
- `effort/` — apply it; you have just reasoned about the work, and it is
  what lets a later session pick something it can finish.
- `priority/` — only if the evidence supports it. Leaving it off honestly
  means unprioritised; guessing high is worse than leaving it blank.
- `status/needs-triage` — apply it when the report is incomplete, or when
  it is understood but nobody has decided to do it or when. Filing from
  someone else's bug report, or from a symptom you could not reproduce,
  almost always warrants it. Applying it is far better than inventing the
  missing detail — and never remove it from an existing issue, because
  that is a human decision, not a task.
- `area/` — only if the repo already uses that value.

If a required label does not exist in the repo, run
`/issue-workflows:setup` for it rather than inventing a near-miss.

## 6. File it

Build the label list from step 5 — do not hardcode it; a `--label` the
repo does not have makes `gh` fail the whole create:

```bash
LABELS=(--label "$TYPE")                       # required, from step 5
[ -n "${EFFORT:-}" ]   && LABELS+=(--label "$EFFORT")
[ -n "${PRIORITY:-}" ] && LABELS+=(--label "$PRIORITY")
[ -n "${TRIAGE:-}" ]   && LABELS+=(--label status/needs-triage)

gh issue create -R "$R" --title "$TITLE" --body-file "$BODY" "${LABELS[@]}"
```

Use `--body-file` with a heredoc, never `--body` with an inline string —
backticks and `$` in evidence get mangled by the shell otherwise.

## 7. Report

Print the URL and the labels applied. If the issue belongs to an active
epic, say so and point at `/issue-workflows:epic` to add it to the board —
do not add it silently.
