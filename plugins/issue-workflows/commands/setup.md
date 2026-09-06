# Issue workflow setup

Make a machine, and a set of repos, ready for the issue conventions in
`references/conventions.md` and the epic model in `references/epic-model.md`.

Idempotent: safe to re-run, and re-running after adding a repo is the
intended way to onboard it. `$ARGUMENTS` may name repos (`shed roost`),
`--all` for every repo the user owns with issues enabled, or be empty
(current repo only). Add `--epics` to also provision the shared board.

## 1. Check the machine's gh token — do this first, always

```bash
gh auth status
```

The scopes line must include **`project`** (or `read:project` for
read-only use). It is stored per machine in `~/.config/gh/hosts.yml`, so a
second computer needs it again even though the Project already exists.

If it is missing, stop and tell the user to run:

```bash
gh auth refresh -s project
```

That is interactive (it opens a browser), so **the user must run it, not
you** — suggest they type `! gh auth refresh -s project` to run it in
this session. Everything except `--epics` still works without it; only the
Project steps need it. Say which steps you are skipping rather than
failing the whole command.

## 2. Reconcile labels, per repo

For each target repo, bring it onto the three-axis standard.

Create the canonical set (skip any that exist — `gh label create` fails
loudly on a duplicate, so use `--force` to make it an upsert):

```bash
gh label create type/bug              -R "$R" -c B60205 -d "A defect"  --force
gh label create type/enhancement      -R "$R" -c 0E8A16 -d "New or improved behavior" --force
gh label create type/docs             -R "$R" -c 006B75 -d "Documentation" --force
gh label create type/chore            -R "$R" -c BFD4F2 -d "Maintenance, no behavior change" --force
gh label create type/ci               -R "$R" -c 5319E7 -d "Build, test, or release plumbing" --force
gh label create priority/high         -R "$R" -c D93F0B --force
gh label create priority/medium       -R "$R" -c FBCA04 --force
gh label create priority/low          -R "$R" -c C2E0C6 --force
gh label create effort/small          -R "$R" -c EDEDED --force
gh label create effort/medium         -R "$R" -c D4D4D4 --force
gh label create effort/large          -R "$R" -c BBBBBB --force
gh label create status/needs-triage   -R "$R" -c FEF2C0 -d "Not yet understood, or not yet decided" --force
gh label create status/blocked        -R "$R" -c 000000 -d "Waiting on something named in a comment" --force
```

Then migrate the legacy schemes named in `conventions.md` § 4. For each
mapping, relabel the issues that carry the old label before deleting it:

```bash
# example: prox severity:high -> priority/high
for n in $(gh issue list -R "$R" --state all --label "severity:high" --limit 200 --json number --jq '.[].number'); do
  gh issue edit "$n" -R "$R" --add-label priority/high --remove-label "severity:high"
done
gh label delete "severity:high" -R "$R" --yes
```

**Never delete a label before its issues are relabelled**, and report how
many issues moved per mapping.

Finally, remove the stock labels the convention drops. `good first issue`
and `help wanted` go **regardless of usage** — these repos are public but
are not seeking contributors, so the labels are actively misleading. For
`bug`, `enhancement`, `documentation` and `question`, migrate any issues
onto the `type/` axis first, then delete. **Ask before deleting** —
deletion is not reversible:

```bash
gh label list -R "$R" --limit 100 --json name,description
gh issue list -R "$R" --state all --label "<name>" --limit 1 --json number
```

Leave dependabot's labels (`dependencies`, `github_actions`, `rust`,
language names) alone — they are machine-owned.

## 3. Provision the epics board — only with `--epics`, and only with `project` scope

Look for an existing board before creating one:

```bash
gh project list --owner "$OWNER" --format json
```

If a board named `StrideLabs Epics` exists, reuse it — **never create a
second**. Otherwise:

```bash
gh project create --owner "$OWNER" --title "StrideLabs Epics"
```

Then ensure the custom fields from `references/epic-model.md` exist
(`gh project field-list` first, `gh project field-create` for the missing
ones): `Epic` and `Phase` as `SINGLE_SELECT`, `Blocked by` as `TEXT`.

Three names are already taken by built-ins and must not be recreated:
`Status`, `Repository`, and — the one that surprises — **`Milestone`**,
which Projects v2 ships to mirror each issue's native repo milestone.
That collision is why the epic's own sequencer is called `Phase`.

Field *values* are per-epic and are added by `/issue-workflows:epic`, not
here. This step only guarantees the board and its field shapes.

## 4. Report

State plainly, per repo: labels created, issues migrated by mapping, stock
labels removed or left, and whether the board was created or reused. If
step 1 skipped the board, end by repeating the one command the user needs
and that it is per machine.
