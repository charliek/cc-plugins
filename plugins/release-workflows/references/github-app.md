# Release-bot App, secrets, and branch protection ruleset

This file explains how to wire the GitHub App that performs CI-driven
bot pushes (signed appcasts, etc.) and the branch protection ruleset
that lets it through without weakening protection for everyone else.

The setup skill walks the user through this once per repo. The release
skill links here when a push is rejected by branch protection — that
usually means a bypass actor is missing.

## Why an App at all

CI steps that update files in `main` after a build (a signed Sparkle
appcast, a bumped formula reference, etc.) can't use the default
`GITHUB_TOKEN` because that token is rejected by branch protection's
required-status-check rule — the new commit hasn't been built yet, so
no `ci-success` exists on it at push time.

Two viable workarounds for branch-protected bot pushes:

1. **A GitHub App with bypass.** The App's installation token is
   listed in the branch ruleset's bypass actors. The App pushes
   directly; ci-success runs after, but the push isn't gated on it.
2. **A PAT belonging to an admin.** Admins bypass protection
   regardless. PATs work but expire and live tied to a personal
   identity.

This plugin uses (1) — a single App, installed on every repo that opts
in, listed in each repo's ruleset bypass. One private key to rotate, one
audit trail, scoped permissions per installation, doesn't tie to anyone's
personal account.

The App name is up to you — the plugin doesn't hard-code it. Throughout
this doc, the App is referred to as "the release-bot App"; substitute
your own name where it appears.

## Phase 1 — Create the App (once per account)

If you already have a release-bot App for your account, skip to Phase 2.

`Settings → Developer settings → GitHub Apps → New GitHub App`:

| Field | Value |
|---|---|
| GitHub App name | Anything unique on GitHub. `<account>-release-bot` is a common shape. |
| Description | A one-liner. "Pushes release-derived artifacts on tag." |
| Homepage URL | Any HTTPS URL. Required by the form; otherwise unused. Your account page works. |
| **Webhook → Active** | **UNCHECK.** The App is invoked from CI workflows, not from webhook events. Leaving this on forces a public HTTPS receiver to exist; you'll be debugging an unrelated rabbit hole. |
| Webhook URL / Secret | Blank (greyed out once Active is off) |
| Callback URL | Blank. There is no OAuth user flow. |
| Setup URL | Blank. |
| Repository permissions → Contents | **Read and write** |
| Repository permissions → Metadata | Read-only (GitHub auto-selects this; leave it) |
| All other permissions | No access |
| Subscribe to events | None |
| Where can this GitHub App be installed? | Only on this account |

Click Create.

On the next page:

1. **Note the App ID** (top, under "About"). You'll need it for one
   secret per repo. It's a 6–7 digit integer.
2. **Generate a private key** (bottom of the page, "Private keys" →
   "Generate a private key"). Downloads a `.pem` file. GitHub never
   shows it again — copy it into a password manager. The local copy is
   needed once per repo for the secret upload below; delete after.

## Phase 2 — Install the App on each repo

Left sidebar of the App settings → "Install App" → click "Install" next
to your account.

| Field | Choice |
|---|---|
| Only select repositories | Pick this repo |
| All repositories | Don't — defeats the per-repo audit |

Click Install. Repeat for each repo that opts into this plugin's
convention.

## Phase 3 — Set the secrets on each repo

```bash
APP_ID=<your-app-id>                       # the integer from Phase 1
PEM=~/Downloads/<your-key>.private-key.pem
REPO=<owner>/<repo>

gh secret set RELEASE_BOT_APP_ID  -R "$REPO" -b "$APP_ID"
gh secret set RELEASE_BOT_APP_KEY -R "$REPO" < "$PEM"

# Verify
gh secret list -R "$REPO" | grep RELEASE_BOT_
```

Both secret names are the convention; the workflow templates expect
exactly these. Once the secrets are set on every repo, move the `.pem`
into your password manager and delete it from `~/Downloads/`.

## Phase 4 — Migrate `main` to a ruleset

Classic branch protection has no per-actor bypass for required status
checks. Even with `enforce_admins=false`, only admin *users* bypass —
Apps don't. The fix is to migrate `main` to a ruleset, which has a
per-actor bypass list.

The ruleset keeps `ci-success` required for the general case and lists
two bypass actors:

- **The release-bot App** — so the bot's post-build push (signed
  appcast, etc.) lands without waiting on its own ci-success.
- **The admin role** — so `/release-workflows:release`'s push of the
  two release commits lands; those commits don't have ci-success yet
  either at the moment of push.

Without the admin entry, even an admin's release push is rejected.
This is the gotcha that bit roost on v0.0.5 — classic protection's
`enforce_admins=false` does **not** translate to rulesets.

### Step 4.1 — Create the ruleset

```bash
REPO=<owner>/<repo>
APP_ID=<your-app-id>

cat > /tmp/main-ruleset.json <<JSON
{
  "name": "main-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "required_status_checks",
      "parameters": {
        "required_status_checks": [ { "context": "ci-success" } ],
        "strict_required_status_checks_policy": false
      }
    }
  ],
  "bypass_actors": [
    { "actor_id": ${APP_ID}, "actor_type": "Integration", "bypass_mode": "always" },
    { "actor_id": 5,         "actor_type": "RepositoryRole", "bypass_mode": "always" }
  ]
}
JSON

gh api -X POST "/repos/${REPO}/rulesets" --input /tmp/main-ruleset.json \
  | jq '{id, name, enforcement, bypass_actors}'
```

`actor_type: "Integration"` with `actor_id: <your App ID>` is the App.
`actor_type: "RepositoryRole"` with `actor_id: 5` is the admin role
(the role ID is the same across all repos; it's not configurable).

### Step 4.2 — Delete the classic protection

```bash
gh api -X DELETE "/repos/${REPO}/branches/main/protection"
```

### Step 4.3 — Verify

```bash
echo "Classic protection (should be 404):"
gh api "/repos/${REPO}/branches/main/protection" 2>&1 | head -3

echo "Ruleset (should list main-protection with both bypass actors):"
gh api "/repos/${REPO}/rulesets" --jq '.[] | {id, name, enforcement, bypass_actors}'
```

A direct push by an admin should now print
`remote: Bypassed rule violations for refs/heads/main` and succeed even
when the new commit has no ci-success yet. A bot push from CI using
the App's token should print the same and succeed.

## Phase 5 — Sanity-check the wiring

Use the bundled
[`sanity-check-app.yml`](workflows/sanity-check-app.yml.template)
workflow — `workflow_dispatch`-only, mints a release-bot token in CI
and prints which repo the token can see plus the bot's identity. Run
it from the Actions UI on the branch where you've set the secrets and
confirm:

- The repo it sees matches the repo it's running in
- The installation repository count is at least 1
- The token's identity ends with `[bot]`

If any of those don't match, fix the App install or secrets before
proceeding to the first real release.

## Rollback

If migrating the ruleset goes wrong:

```bash
# Restore classic protection
gh api -X PUT "/repos/${REPO}/branches/main/protection" \
  -f required_status_checks[strict]=false \
  -f required_status_checks[contexts][]=ci-success \
  -F enforce_admins=false \
  -F required_pull_request_reviews= \
  -F restrictions=

# Find and delete the ruleset
gh api "/repos/${REPO}/rulesets" --jq '.[] | select(.name=="main-protection") | .id'
gh api -X DELETE "/repos/${REPO}/rulesets/<id-from-previous-line>"
```

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `git push origin main` → `Required status check "ci-success" is expected` | Admin role missing from ruleset bypass | Re-run Step 4.1's ruleset PUT including `RepositoryRole` actor_id 5 |
| `git push origin main` from CI bot → same error | App missing from ruleset bypass | Re-run Step 4.1's ruleset PUT including `Integration` actor_id `<APP_ID>` |
| `actions/create-github-app-token@v2` → `Bad credentials` | `RELEASE_BOT_APP_ID` or `RELEASE_BOT_APP_KEY` not set, or `.pem` corrupted | Re-upload the `.pem` from the password manager |
| Bot push succeeds but workflow says "Resource not accessible by integration" | App is installed but doesn't have the right permission for the API call being made | Edit the App's permissions, then re-accept the installation |
| CI says `App is installed but token has no access to <repo>` | App install missed this repo | Re-run Phase 2 and add the repo |

## What the plugin doesn't ship

- The App itself. Create it once per account; the plugin is repo-agnostic.
- A management script for rotating the App's private key. If you rotate,
  re-run Phase 3 on every repo with the new `.pem` and re-run the
  sanity-check workflow to confirm.
- An automated migration for repos that already use classic protection.
  Run Step 4.1, then Step 4.2, then test.
