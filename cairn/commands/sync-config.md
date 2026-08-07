---
description: Configure two-way bd↔external sync (GitHub/GitLab/Jira/Asana/Azure Boards) — writes .cairn/sync.json
group: sync
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

3. **Jira: detect first, then ask — once, and only when there is something to
   ask about.** Open with the detection, never with the question:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-jira.sh" detect --json
   ```
   Read `ask` and `reason` and take exactly one of these routes:

   - **`ask: false` with `reason: "no signal"`** — nothing in this repo points
     at Jira. **Ask nothing about it.** Do not mention it, do not offer it, go
     straight to step 5. A project with no signal is never asked; that is not
     a default, it is the rule.

   - **`ask: false` with `reason: "already answered: yes"` or `": no"`** — the
     question was answered before. Say which answer is on record and how to
     change it (`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" set
     jira.link unset`), and **do not re-ask**. A `no` has the same force as a
     `yes`.

   - **`ask: true`** — **show what was found before asking anything.** Read it
     out of `findings`: the key, in how many branches and how many commits
     (`findings.samples.<KEY>.branch_count` / `.commit_count`, with up to
     three real branch names and commit subjects to quote), and whether an
     Atlassian MCP server is declared — naming the file it is declared in
     (`findings.mcp.source`). Then ask **one** `AskUserQuestion`, in the
     `/gsd:config` shape: a single batch, the current value pre-selected,
     options **link to Jira** / **do not link**. When `findings.prefixes` has
     more than one entry, offer the found prefixes as the options, in the
     order they arrive (most frequent first) — choosing among what was found
     is still confirming, not typing.

   - **`ask: true` with `reason: "signal found, no key to confirm"`** — an
     Atlassian MCP server is declared but this repo's history names no issue
     key. Say exactly that, and say that linking here needs the project key
     typed because there is nothing to confirm. Everywhere else in this flow,
     nobody types a key.

   - **exit 5** — the detector is unavailable. Say so plainly and carry on
     with the other backends; do not guess and do not ask a Jira question you
     have no evidence for.

4. **Write the answer with the script, not by hand.** Both answers are
   recorded, so the question never comes back:
   ```bash
   # yes — the key comes from the detection; nobody typed it
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-jira.sh" apply --key <DETECTED_KEY>
   # no
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-jira.sh" decline
   ```
   `apply` derives the site from an `*.atlassian.net` git remote. When there
   is none it exits 2 and writes nothing rather than inventing a placeholder —
   pass `--base-url https://<site>.atlassian.net` after confirming the site
   with the user. On success it prints the env var **names** that have to
   exist in the shell before a push works; relay those names and never ask for
   a token. `decline` writes the `no` and nothing else.

5. Ask the user (AskUserQuestion) which of the **remaining** backends to
   enable: **GitHub**, **GitLab**, **Asana**, **Azure Boards** (multiSelect) —
   plus **Jira** only if step 3 took the "no signal" or exit-5 route, where no
   Jira question was asked. For each chosen backend, collect the required
   `config` fields and set `"enabled": true`:
   - **github**: `repo` (owner/name). Uses the `gh` CLI's existing auth — no token field.
   - **gitlab**: `project` (numeric id or `namespace/project`), `base_url`
     (default `https://gitlab.com`; set for self-hosted), and ENV VAR NAME `token_env`.
   - **jira**: `base_url`, `project_key`, `issue_type`, and the ENV VAR NAMES
     `email_env` / `token_env`, plus `transitions.in_progress` / `transitions.closed`.
     (When step 4 ran `apply`, this is already written — leave it alone.)
   - **asana**: `project_gid` and ENV VAR NAME `token_env`.
   - **azure-boards**: `org_url`, `project`, `work_item_type`, ENV VAR NAME
     `pat_env`, and `states.in_progress` / `states.closed` (match the project's
     process template).

6. **Secrets rule:** write only ENV VAR NAMES into `sync.json`, never token
   values. After saving, tell the user exactly which env vars to export
   (e.g. `export JIRA_API_TOKEN=…`) and where to mint each credential:
   - GitLab token (`api` scope): https://gitlab.com/-/user_settings/personal_access_tokens
   - Jira token: https://id.atlassian.com/manage-profile/security/api-tokens
   - Asana PAT: https://app.asana.com/0/my-apps
   - Azure DevOps PAT (Work Items Read & Write): `https://dev.azure.com/<org>/_usersSettings/tokens`
   - GitHub: `gh auth status` (no separate token needed)

7. **Initial import (Jira only, offer when detected or asked):** pull is
   mapped-items-only, so cards that predate the sync wiring never arrive by
   themselves. When Jira was enabled — especially when step 3 detected it —
   offer a one-shot import of the existing cards (after the env vars are
   exported):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/gbsync.sh" import --project <KEY>
   ```
   (`--query '<JQL>'` instead of `--project` for a narrower slice; add
   `--dry-run` to preview; capped at 200 items per run — slice a bigger
   backlog by JQL.) It creates one bd issue per card and seeds
   `.cairn/id-map.json`, after which normal push/pull cover them. Re-runs
   skip already-mapped cards. Only run it on the user's yes.

8. Explain the generated files: `.cairn/id-map.json`, `.cairn/state.json`, and
   `.cairn/conflicts.json` are generated automatically at sync time — do not
   create them by hand. `sync.json` and `context.json` are meant to be
   committed; every generated file under `.cairn/` is gitignored by default
   (`cairn-init.sh` adds one entry per file — see docs/sync.md §4) — a team
   that prefers to commit any of them can remove its line from `.gitignore`.

9. Tell the user how to drive it:
   - PUSH happens automatically during the `cairn-sync` lifecycle, or
     manually: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gbsync.sh" update <bd_id>`
   - PULL on demand: `/cairn:sync-pull`
   - IMPORT of pre-existing Jira cards: `gbsync.sh import` (step 7)
   - Validate config without calling APIs: run a single
     `gbsync.sh update <bd_id>` and read the per-backend result lines.
