---
description: Check whether the local Cursor agent CLI is installed and authenticated
argument-hint: ""
allowed-tools: Bash(command:*), Bash(cursor-agent:*), AskUserQuestion
---

Check that the Cursor `cursor-agent` CLI is ready to use, then report a concise readiness summary.

## Steps

1. **Check the CLI is installed:**

   ```bash
   command -v cursor-agent
   ```

   - If this fails, the CLI is not installed. Tell the user to install the Cursor CLI from the official instructions at https://cursor.com/cli and stop. Do **not** auto-run an installer; let the user follow the official steps themselves (they can use the `! <command>` prefix to run a command in this session).

2. **Check version and account:**

   ```bash
   cursor-agent about
   ```

   This reports the CLI version, system info, and account.

3. **Check authentication:**

   ```bash
   cursor-agent status
   ```

   - If the output shows an authenticated account, authentication is good.
   - If it reports the user is not logged in, tell them to run `cursor-agent login` (it opens a browser). Suggest the `! cursor-agent login` prefix so the login flow runs in this session.

4. **Report a readiness summary** covering:
   - Installed? (path from step 1)
   - Authenticated? (account from `cursor-agent status`)
   - Version (from `cursor-agent about`)
   - Next steps if anything is missing (install, or `cursor-agent login`).

5. **Mention discovery:** the default model used by this plugin's commands is `cursor-grok-4.6-high`; run `cursor-agent --list-models` to see all available model ids that can be passed with `--model`.
