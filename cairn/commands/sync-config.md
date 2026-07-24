---
description: Configure two-way bd↔external sync (GitHub/GitLab/Jira/Asana/Azure Boards) — writes .cairn/sync.json
---

Set up the cairn sync backends for this repo. bd is the hub/source of
truth; tools sync to bd (hub-and-spoke). Do the following:

1. Confirm prerequisites: the repo has `.beads/` (run `ls .beads/`). If not,
   tell the user to run `/cairn:init` first and stop.

2. If `.cairn/sync.json` does not exist, create `.cairn/` and seed it
   from the template:
   ```bash
   mkdir -p .cairn
   cp "${CLAUDE_PLUGIN_ROOT}/templates/sync.json.example" .cairn/sync.json
   ```
   If it already exists, read it and edit in place (preserve existing values).

3. Ask the user (AskUserQuestion) which backends to enable: **GitHub**,
   **GitLab**, **Jira**, **Asana**, **Azure Boards** (multiSelect). For each
   chosen backend, collect the required `config` fields and set `"enabled": true`:
   - **github**: `repo` (owner/name). Uses the `gh` CLI's existing auth — no token field.
   - **gitlab**: `project` (numeric id or `namespace/project`), `base_url`
     (default `https://gitlab.com`; set for self-hosted), and ENV VAR NAME `token_env`.
   - **jira**: `base_url`, `project_key`, `issue_type`, and the ENV VAR NAMES
     `email_env` / `token_env`, plus `transitions.in_progress` / `transitions.closed`.
   - **asana**: `project_gid` and ENV VAR NAME `token_env`.
   - **azure-boards**: `org_url`, `project`, `work_item_type`, ENV VAR NAME
     `pat_env`, and `states.in_progress` / `states.closed` (match the project's
     process template).

4. **Secrets rule:** write only ENV VAR NAMES into `sync.json`, never token
   values. After saving, tell the user exactly which env vars to export
   (e.g. `export JIRA_API_TOKEN=…`) and where to mint each credential:
   - GitLab token (`api` scope): https://gitlab.com/-/user_settings/personal_access_tokens
   - Jira token: https://id.atlassian.com/manage-profile/security/api-tokens
   - Asana PAT: https://app.asana.com/0/my-apps
   - Azure DevOps PAT (Work Items Read & Write): `https://dev.azure.com/<org>/_usersSettings/tokens`
   - GitHub: `gh auth status` (no separate token needed)

5. Explain the generated files: `.cairn/id-map.json`, `.cairn/state.json`, and
   `.cairn/conflicts.json` are generated automatically at sync time — do not
   create them by hand. `sync.json` is meant to be committed; the generated
   three are gitignored by default (`cairn-init.sh` adds the entries) — a team
   that prefers to commit any of them can remove its line from `.gitignore`.

6. Tell the user how to drive it:
   - PUSH happens automatically during the `cairn-sync` lifecycle, or
     manually: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gbsync.sh" update <bd_id>`
   - PULL on demand: `/cairn:sync-pull`
   - Validate config without calling APIs: run a single
     `gbsync.sh update <bd_id>` and read the per-backend result lines.
