# Cairn sync — bd ↔ external work-management tools

Complete guide to the two-way synchronization layer in the `cairn` plugin:
what it is, what it does, how it works, and how to set it up.

---

## 1. What it is

`cairn sync` mirrors your [beads](https://github.com/gastownhall/beads)
(`bd`) issues to one or more external work-management tools and pulls external
edits back into bd. It exists so a team can keep planning and execution in bd
(local, fast, git-native) while stakeholders watch progress in the tool they
already use — **GitHub Issues, GitLab, Jira, Asana, or Azure Boards** — without
anyone double-entering work.

It is **thin glue**: a small dispatcher plus one adapter per tool. It does not
fork, vendor, or replace bd or any external tool. Each tool is reached through
its own public API.

### Design in one line

> **bd is the hub and single source of truth. Every external tool syncs to bd.
> Tools never sync to each other.**

This is the **hub-and-spoke** model. It is a deliberate choice over the two
alternatives:

| Model | Why not |
|---|---|
| **Mesh** (every tool ↔ every tool) | N×N adapters, N×N conflict surfaces. Unmaintainable past two tools. |
| **Full real-time two-way** (webhooks, a running service, conflict UI) | Needs hosting, receivers per tool, and a conflict-resolution UI. Wrong weight for a planning-glue plugin. |
| **Hub-and-spoke, pull-on-demand** ✅ | N adapters, one conflict surface (bd). No daemon, no webhooks. bd stays authoritative. |

---

## 2. What it does

Two directions of flow:

```
            PUSH  (on bd lifecycle events: create / claim / close)
   bd  ───────────────────────────────────────────────►  GitHub / GitLab / Jira / Asana / Azure
  (hub)                                                          (spokes)
    ▲                                                              │
    └──────────────────────────────────────────────────────────────┘
            PULL  (on demand: /cairn:sync-pull)
                  reconcile external edits back into bd
                  last-writer-wins by updated_at; conflicts logged
```

- **PUSH (bd → tools)** — when a bd issue is created, claimed (→ in_progress),
  or closed, the dispatcher fans a normalized event out to every enabled
  backend, creating/updating/closing the matching external item and recording
  the `bd-id ↔ external-id` mapping.

- **PULL (tools → bd)** — on demand, the dispatcher asks each backend for the
  current state of its mapped items and reconciles them back into bd using
  **last-writer-wins by `updated_at`**. Cases where *both* sides changed since
  the last pull are recorded as conflicts for human review.

---

## 3. Architecture

```
cairn/
├── scripts/
│   ├── gbsync.py      # the dispatcher (push + pull). Pure stdlib.
│   └── gbsync.sh      # thin bash wrapper -> python3 gbsync.py
├── adapters/
│   ├── _contract.md   # the adapter interface specification
│   ├── github.py      # gh CLI (reuses gh auth)
│   ├── gitlab.py      # REST v4, PRIVATE-TOKEN
│   ├── jira.py        # REST v3, basic auth (email + API token)
│   ├── asana.py       # REST 1.0, Bearer PAT
│   └── azure-boards.py# Work Items REST, basic auth (PAT)
└── templates/
    └── sync.json.example
```

**Dispatcher** — owns config, the id-map, the bd reads/writes, fan-out, and
reconciliation. It never makes an HTTP call itself and never touches secrets.

**Adapter** — a standalone executable that speaks one tool's API. It receives a
JSON event on stdin and prints a result to stdout (see §9). Adapters may be
written in any language; `.py` and `.sh` are auto-detected.

This separation is the whole point: **adding a tool is one new adapter file plus
one config block — no dispatcher changes.**

---

## 4. Data model & state files

All state lives under `<project>/.cairn/`:

| File | Committed? | Purpose |
|---|---|---|
| `sync.json` | **yes** | Backend config. Holds ENV VAR *names*, never secrets. |
| `id-map.json` | no (gitignored by default) | `{ bd_id: { backend: external_id } }` — the identity link. |
| `state.json` | no (gitignored) | Pull watermarks: `{ last_pull: { backend: iso8601 } }`. |
| `conflicts.json` | no (gitignored) | Append-only log of both-sides-changed reconciliations. |

`cairn-init.sh` appends the generated three (plus the local
`.cairn/.beacon-sent` marker) to the target repo's `.gitignore`, so they are
excluded by default. `sync.json` is meant to be committed so the whole team
shares the same backend config.

### Identity mapping

bd is the key space. Each bd issue maps to at most one external id per backend:

```json
{
  "proj-7hp": { "github": "42", "gitlab": "17", "jira": "PROJ-101" },
  "proj-4qv": { "github": "43" }
}
```

The dispatcher writes this on every successful push. A PULL only considers items
that already exist in the map.

---

## 5. How the two directions work

### PUSH (bd → tools)

```
gbsync.sh <create|update|close> <bd_id>
```

1. Read `.cairn/sync.json`; collect enabled backends.
2. `bd show <bd_id> --json` → normalize to `{title, body, status, labels}`.
   (bd `description` + any `notes` are combined into `body`.)
3. For each backend, build the event and run its adapter:
   - `create` → adapter mints the item, returns its external id.
   - `update` → adapter edits the item (if no mapped id yet, it creates one).
   - `close` → adapter closes/completes the item.
4. Store any returned external id in `id-map.json`.
5. A failing backend is logged and skipped — it never blocks the others or the
   bd write.

### PULL (tools → bd)

```
gbsync.sh pull [--since <iso8601>]
```

For each enabled backend, for each of its mapped items:

1. Adapter returns the item's current `{title, body, status, updated_at}`.
2. The dispatcher compares timestamps against the per-backend watermark
   (`state.json`, or `--since` override) and against bd's own `updated_at`:

```
ext_changed = external.updated_at > watermark
bd_changed  = bd.updated_at       > watermark

if not ext_changed:                      -> skip (nothing new remotely)
elif ext_changed and bd_changed:         -> CONFLICT (log it), then LWW:
        external newer -> apply to bd
        bd newer       -> leave for next PUSH
elif external newer than bd:             -> apply to bd (bd update)
else:                                     -> leave for next PUSH
```

3. "Apply to bd" = `bd update <id> --title … --body-file - [--status …]`.
4. The backend's watermark is advanced to the pull start time.

**Conflicts** are written to `.cairn/conflicts.json` with which side won;
review that file and fix by hand if the automatic resolution was wrong.

---

## 6. Quick start

```text
# 1. Make sure the repo uses bd (and, for GSD wiring, GSD):
/cairn:init

# 2. Configure which tools to mirror to:
/cairn:sync-config        # interactive; writes .cairn/sync.json

# 3. Export the API tokens it tells you to (see §7). Then:
#    - PUSH happens automatically during the cairn lifecycle, or manually:
bash <plugin>/scripts/gbsync.sh update <bd_id>

#    - PULL external edits back into bd, on demand:
/cairn:sync-pull
```

`<plugin>` is `${CLAUDE_PLUGIN_ROOT}` inside a command/hook, or the plugin's
install path otherwise.

---

## 7. Per-backend setup

Every backend block in `sync.json` has the shape:

```json
{ "type": "<tool>", "enabled": true, "adapter": "<tool>", "config": { … } }
```

Set `enabled: true` only for tools you use. Tokens are referenced by
**environment-variable name** — the value is read at sync time and never stored.

### GitHub Issues

```json
{ "type": "github", "enabled": true, "adapter": "github",
  "config": { "repo": "owner/name", "extra_labels": [] } }
```

- **Auth:** the `gh` CLI's existing auth. Run `gh auth status` to confirm; no
  token field needed.
- **Status:** GitHub issues are open/closed only. `in_progress` keeps the issue
  open; `closed` closes it with reason `completed`.

### GitLab

```json
{ "type": "gitlab", "enabled": true, "adapter": "gitlab",
  "config": { "base_url": "https://gitlab.com",
              "project": "namespace/project",
              "token_env": "GITLAB_TOKEN", "extra_labels": [] } }
```

- **Auth:** `export GITLAB_TOKEN=…` — a Personal or Project Access Token with
  the `api` scope. Mint at `https://gitlab.com/-/user_settings/personal_access_tokens`.
- **Self-hosted:** set `base_url` to your instance.
- **`project`:** numeric id or the `namespace/project` path.
- **Status:** opened/closed (the stored external id is the issue `iid`).

### Jira (Cloud)

```json
{ "type": "jira", "enabled": true, "adapter": "jira",
  "config": { "base_url": "https://yourorg.atlassian.net",
              "project_key": "PROJ", "issue_type": "Task",
              "email_env": "JIRA_EMAIL", "token_env": "JIRA_API_TOKEN",
              "transitions": { "in_progress": "In Progress", "closed": "Done" } } }
```

- **Auth:** `export JIRA_EMAIL=…` and `export JIRA_API_TOKEN=…`. Mint a token at
  `https://id.atlassian.com/manage-profile/security/api-tokens`.
- **`transitions`:** the workflow transition/status *names* used to move an issue
  to in-progress / done. Pull normalizes status via Jira's `statusCategory`
  (`new`→open, `indeterminate`→in_progress, `done`→closed), which is robust
  across custom workflows.

### Asana

```json
{ "type": "asana", "enabled": true, "adapter": "asana",
  "config": { "project_gid": "1209…", "token_env": "ASANA_TOKEN" } }
```

- **Auth:** `export ASANA_TOKEN=…` — a Personal Access Token from
  `https://app.asana.com/0/my-apps`.
- **`project_gid`:** the project tasks are created in.
- **Status:** Asana tasks have no native in-progress; `in_progress` stays
  incomplete (open), `closed` sets `completed: true`.

### Azure Boards (Azure DevOps)

```json
{ "type": "azure-boards", "enabled": true, "adapter": "azure-boards",
  "config": { "org_url": "https://dev.azure.com/yourorg", "project": "YourProject",
              "work_item_type": "Issue", "pat_env": "AZURE_DEVOPS_PAT",
              "api_version": "7.0",
              "states": { "in_progress": "Active", "closed": "Closed" } } }
```

- **Auth:** `export AZURE_DEVOPS_PAT=…` — a PAT with **Work Items (Read &
  Write)**. Mint at `https://dev.azure.com/<org>/_usersSettings/tokens`.
- **`states`:** the `System.State` values for your process template
  (Basic: `Doing`/`Done`; Agile: `Active`/`Closed`; etc.). Pull normalizes via
  the State Category when available, falling back to this map.

---

## 8. Commands

| Command | Does |
|---|---|
| `/cairn:init` | Bootstrap a repo: `git init` (if needed) + `bd init`. |
| `/cairn:sync-config` | Interactively choose backends and write `sync.json`; tells you which env vars to export. |
| `/cairn:sync-pull` | Reconcile external edits back into bd; summarizes conflicts. |

Raw dispatcher (what the commands call):

```bash
gbsync.sh create  <bd_id>      # push a new issue out to all enabled backends
gbsync.sh update  <bd_id>      # push title/body/status changes
gbsync.sh close   <bd_id>      # close the external items
gbsync.sh pull    [--since X]  # pull external state back into bd
gbsync.sh <...>   --dir <path> # operate on a specific project dir
gbsync.sh <...>   --dry-run    # print the would-be operations ("DRY-RUN:" lines)
                               # without calling adapters or writing any state
```

---

## 9. Lifecycle integration

When the repo also uses GSD + bd (the `cairn` skill), fire the matching push
right after each bd write:

| GSD / bd step | bd command | then |
|---|---|---|
| roadmap → issues | `bd create …` | `gbsync.sh create <id>` |
| start a plan | `bd update <id> --claim` | `gbsync.sh update <id>` |
| finish a plan | `bd close <id>` | `gbsync.sh close <id>` |

Run `/cairn:sync-pull` whenever someone may have edited issues in an
external tool (e.g. before a planning session).

---

## 10. The adapter contract (extending to a new tool)

To add a tool (Linear, Trello, Monday, …): write one executable in `adapters/`
that follows the contract, then add a backend block to `sync.json`. No
dispatcher changes.

**PUSH** — `create | update | close`

```
stdin : {action, bd_id, title, body, status, labels, external_id, config}
stdout: the external id (bare string)
```

**PULL** — `pull`

```
stdin : {action:"pull", config, items:[{bd_id, external_id}, …]}
stdout: JSON array [{bd_id, external_id, title, body, status, updated_at}, …]
```

Rules:
- `status` must be normalized to `open` / `in_progress` / `closed`.
- `updated_at` must be ISO-8601 UTC.
- Exit `0` on success; nonzero is logged and the dispatcher continues.
- Read tokens from the env var named in `config` — never from disk.
- On pull, omit items you cannot fetch rather than failing the whole pull.

Full spec: [`adapters/_contract.md`](../adapters/_contract.md).

### Status normalization

| normalized | meaning | GitHub/GitLab | Jira | Asana | Azure |
|---|---|---|---|---|---|
| `open` | backlog / to-do | open / opened | category `new` | incomplete | `states.in_progress` not set |
| `in_progress` | active / doing | (n/a → open) | category `indeterminate` | (n/a → open) | `states.in_progress` |
| `closed` | done | closed | category `done` | completed | `states.closed` |

---

## 11. Security

- **No secrets on disk.** `sync.json` contains only the *names* of environment
  variables (`token_env`, `email_env`, `pat_env`). The dispatcher never reads a
  token; each adapter reads its token from the environment at call time.
- **Least privilege.** Mint tokens with the narrowest scope that works
  (GitLab `api`, Azure `Work Items R/W`, etc.). Prefer project-scoped tokens.
- **`sync.json` is committed** — keep it free of anything sensitive. The
  generated `id-map`/`state`/`conflicts` files are gitignored by default.
- If a token env var is unset, the adapter exits nonzero and the dispatcher
  logs the failure for that backend only.

---

## 12. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `no .cairn/sync.json` | Run `/cairn:sync-config` first. |
| `no enabled backends` | Set `"enabled": true` on a backend in `sync.json`. |
| `missing … env var` from an adapter | Export the token env var named in that backend's config. |
| One backend shows `FAIL`, others `ok` | A push failure is isolated per backend; read the error line, fix that backend, re-run. |
| Pull applied nothing | Items unchanged since the watermark — force a wider window with `--since 1970-01-01T00:00:00Z`. |
| Unexpected overwrite in bd after pull | Both sides changed → LWW picked the remote. Check `conflicts.json` and reconcile by hand. |
| Status not reflected (e.g. "in progress") | GitHub/GitLab/Asana have no native in-progress; only open/closed mirror. |

Dry-check without changing anything: add `--dry-run` to any `gbsync.sh` call —
it prints one `DRY-RUN:` line per would-be operation and never calls an adapter
or writes `id-map.json` / `state.json` / `conflicts.json`. Note that dry-run
still exercises the real decision logic, including a local `bd show <id>`
lookup — an unknown bd id fails the same way it would on a real push.

---

## 13. Summary

- bd is the hub; tools are spokes; sync is hub-and-spoke, pull-on-demand.
- PUSH on lifecycle events; PULL on demand with last-writer-wins + conflict log.
- Config in `.cairn/sync.json` (committed, env-var names only).
- One adapter per tool, uniform stdin/stdout contract; adding a tool is one file.
- Five adapters ship today: GitHub, GitLab, Jira, Asana, Azure Boards.
