---
name: cairn-sync
description: Use when a repo has .cairn/sync.json with an enabled backend — mirrors bd (beads) issues two-way (hub-and-spoke) to GitHub Issues, GitLab, Jira, Asana, and/or Azure Boards. bd is the hub/source of truth. PUSH fires on bd lifecycle events; PULL reconciles external edits back to bd on demand. Complements the cairn skill.
---

# cairn sync (bd ↔ external work-management tools)

Two-way, **hub-and-spoke** sync. bd (beads) is the hub and source of truth;
every external tool syncs to bd, never tool-to-tool. Extends the `cairn`
integration with mirroring to GitHub Issues, GitLab, Jira, Asana, and Azure Boards.

## Activation gate

Apply this skill **only when** `.cairn/sync.json` exists in the repo AND has
at least one backend with `"enabled": true`. Otherwise ignore it (bd-only). If
the file is missing, the user has not opted in — do not create it implicitly;
point them at `/cairn:sync-config`.

## Two directions

| Direction | When | Command |
|---|---|---|
| **PUSH** bd → tools | on each bd lifecycle event | `bash ${plugin}/scripts/gbsync.sh <create\|update\|close> <bd_id>` |
| **PULL** tools → bd | on demand (you, or a cron) | `/cairn:sync-pull` → `gbsync.sh pull` |

`${plugin}` = `${CLAUDE_PLUGIN_ROOT}` when running as a hook/command, else the
plugin's install path.

## PUSH — fire on bd lifecycle events

When following the `cairn` lifecycle, run the matching mirror **right after**
the bd write succeeds:

- **issue created** (e.g. during `/gsd:new-project` issue creation):
  `gbsync.sh create <bd_id>`
- **claimed / in_progress** (start of `/gsd:execute-phase`):
  after `bd update <id> --claim`, run `gbsync.sh update <bd_id>`
- **closed** (plan complete):
  after `bd close <id>`, run `gbsync.sh close <bd_id>`

The dispatcher fans the event to every enabled backend and records the
`bd-id ↔ external-id` mapping in `.cairn/id-map.json`. A failing backend is
logged and skipped; it does not block the others or the bd write.

## PULL — reconcile external edits back to bd

Run `/cairn:sync-pull` (or `gbsync.sh pull`) when someone may have edited
issues in an external tool. For each mapped item the dispatcher asks the adapter
for the tool's current state and applies **last-writer-wins by `updated_at`**:

- external newer than bd → apply title/body/status to bd (`bd update`).
- bd newer → left for the next PUSH to propagate.
- **both changed since the last pull → conflict**: recorded in
  `.cairn/conflicts.json` (with the LWW resolution). Review that file and
  fix by hand if the auto-resolution was wrong.

After a pull, **review `.cairn/conflicts.json`** and surface any entries to
the user.

## State files (under `.cairn/`)

- `sync.json` — backend config (committed; contains ENV VAR NAMES, never secrets)
- `id-map.json` — `{ bd_id: { backend: external_id } }`
- `state.json` — pull watermarks `{ last_pull: { backend: iso8601 } }`
- `conflicts.json` — append-only log of both-sides-changed reconciliations

## Secrets

Adapters read API tokens from environment variables named in `sync.json`
(e.g. `token_env`, `pat_env`). Never put a token in `sync.json` or any committed
file. Confirm the env vars are exported before running a sync; if a token is
missing the adapter exits nonzero and the dispatcher logs it.

## Adding another tool

Drop a new executable in `adapters/` implementing the contract in
`adapters/_contract.md` (stdin event → external id for push; stdin pull → JSON
array of states), then add a backend block to `sync.json`. No dispatcher
changes needed.
