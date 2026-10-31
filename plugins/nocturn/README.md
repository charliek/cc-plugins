# nocturn

Skill for maintaining a repository's own Nocturn contract. Nocturn is the
agent-first software upkeep tool in `stridelabs-ai/nocturn`.

## Skill

### `nocturn:nocturn-repo`

Model-invoked. Use it inside a repository that Nocturn scores, to:

- write or update `.nocturn.yaml` (targets, lockfile roles, ignored services),
- onboard the repo (`nocturn repo inspect`, the file, conformance fixes, `nocturn repo check`),
- change the file when something moves: a cutover, a moved directory, a retired service,
- bring a Rust, Go, Python, JavaScript or Flutter/Android repo into line with the standards.

It does not operate the fleet (scores, proposals, decisions, runs). The
`nocturn` skill embedded in the `nocturn` binary does that.

Needs the `nocturn` binary on `PATH` for `nocturn repo inspect` and
`nocturn repo check`. `nocturn repo check` is the authority if this skill and
the code disagree.

References:

- `skills/nocturn-repo/references/file-format.md`: every option in `.nocturn.yaml`.
- `skills/nocturn-repo/references/onboarding.md`: the onboarding steps and when to change the file.
- `skills/nocturn-repo/references/stacks/{rust,go,python,javascript,flutter-android}.md`: what each stack must conform to.
