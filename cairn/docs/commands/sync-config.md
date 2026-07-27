# /cairn:sync-config

> Configure two-way bd↔external sync (GitHub/GitLab/Jira/Asana/Azure Boards) — writes .cairn/sync.json

## Usage

```text
/cairn:sync-config
```

No arguments. The command is interactive (AskUserQuestion, multi-select).

## What it does

Sets up the cairn sync backends for the repo. The model is **hub-and-spoke**:
bd is the hub and single source of truth; every external tool syncs to bd, and
tools never sync to each other.

1. **Confirms prerequisites:** the repo has `.beads/`. If not → run
   [`/cairn:init`](init.md) first; the command stops.
2. **Seeds or edits the config:** if `.cairn/sync.json` does not exist, it is
   seeded from `${CLAUDE_PLUGIN_ROOT}/templates/sync.json.example`; otherwise
   it is edited in place, preserving existing values.
3. **Pre-detects Jira usage:** runs
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-migrate.sh" detect --json`.
   When the JSON carries `external.jira` with `detected: true` (the repo
   already references Jira issue keys; `prefixes` lists the key prefixes
   found, most frequent first, and `source` says where), the **Jira** backend
   is pre-selected in the next step and `project_key` pre-filled with the
   most frequent prefix — the user confirms or overrides both. Without a
   detection the question is asked cold.
4. **Asks which backends to enable** (multi-select) and collects each one's
   `config` fields, setting `"enabled": true`:
   - **github** — `repo` (owner/name). Uses the `gh` CLI's existing auth; no
     token field.
   - **gitlab** — `project` (numeric id or `namespace/project`), `base_url`
     (default `https://gitlab.com`; set for self-hosted), env var name
     `token_env`.
   - **jira** — `base_url`, `project_key`, `issue_type`, env var names
     `email_env` / `token_env`, plus `transitions.in_progress` /
     `transitions.closed`.
   - **asana** — `project_gid`, env var name `token_env`.
   - **azure-boards** — `org_url`, `project`, `work_item_type`, env var name
     `pat_env`, and `states.in_progress` / `states.closed` matching the
     project's process template.
5. **Applies the secrets rule:** only **env var names** go into `sync.json`,
   never token values. After saving, the command lists exactly which env vars
   to export and where to mint each credential (GitLab PAT with `api` scope,
   Jira API token, Asana PAT, Azure DevOps PAT with Work Items Read & Write;
   GitHub needs only `gh auth status`).
6. **Offers the initial Jira import** (when Jira was enabled — especially
   after a step-3 detection). Pull is mapped-items-only, so cards that
   predate the sync wiring never arrive on their own; the one-shot import
   adopts them:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/gbsync.sh" import --project <KEY>
   ```
   (`--query '<JQL>'` for a narrower slice, `--dry-run` to preview; capped
   at 200 items per run — slice a bigger backlog by JQL.) One bd issue is
   minted per card and `.cairn/id-map.json` seeded, after which normal
   push/pull cover them; re-runs skip already-mapped cards. Requires the env
   vars from step 5 to be exported first, and only runs on the user's yes.
7. **Explains the generated files:** `.cairn/id-map.json`, `.cairn/state.json`,
   and `.cairn/conflicts.json` are created automatically at sync time — never
   by hand. `sync.json` is meant to be **committed**; the generated three are
   gitignored by default (`cairn-init.sh` adds the entries). A team that wants
   to commit one of them can remove its `.gitignore` line.
8. **Tells the user how to drive it:** PUSH happens automatically during the
   `cairn-sync` lifecycle, or manually with
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gbsync.sh" update <bd_id>`; PULL is
   [`/cairn:sync-pull`](sync-pull.md); IMPORT of pre-existing Jira cards is
   `gbsync.sh import` (step 6). To validate the config **without calling any
   API**, run a single `gbsync.sh update <bd_id>` and read the per-backend
   result lines (add `--dry-run` for a fully read-only check).

## Flags & arguments

None on the command itself. Backend choice and config fields are collected
interactively. The underlying dispatcher (`gbsync.sh`) accepts `--dir <path>`
and `--dry-run`, and its `import` action takes exactly one of
`--query '<JQL>'` / `--project <KEY>` plus optional `--backend <type>` — see
the [sync guide](../sync.md#8-commands).

## Examples

```text
/cairn:sync-config
```

→ user picks **GitHub** + **Jira**; the command writes both backend blocks to
`.cairn/sync.json` and finishes with:
`export JIRA_EMAIL=… ; export JIRA_API_TOKEN=…` plus the token-minting URL,
and a reminder that GitHub rides on the existing `gh` auth.

```text
/cairn:sync-config       # in a repo without .beads/
```

→ stops immediately and routes to [`/cairn:init`](init.md).

## Files touched

- **Reads:** `.beads/` (existence check),
  `${CLAUDE_PLUGIN_ROOT}/templates/sync.json.example` (seed),
  `.cairn/sync.json` (when editing in place).
- **Writes:** `.cairn/sync.json` (creates `.cairn/` if needed). Committed;
  holds env var **names** only, never secrets.
- **Never creates:** `id-map.json` / `state.json` / `conflicts.json` — those
  belong to the dispatcher at sync time.

## Related

- [`/cairn:sync-pull`](sync-pull.md) — pull external edits back into bd
- [`/cairn:init`](init.md) — prerequisite setup (also gitignores the generated files)
- [`/cairn:status`](status.md) — surfaces sync staleness when `sync.json` exists
- [Cairn sync guide](../sync.md) — architecture, adapter contract, per-backend setup
