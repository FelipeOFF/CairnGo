# /cairn:sync-pull

> Reconcile external work-management tools back into bd (pull-on-demand, last-writer-wins)

## Usage

```text
/cairn:sync-pull [--since <iso8601>]
```

Flags typed by the user are passed through to the dispatcher — `--since`
forces a wider time window than the stored watermark (see Flags).


> **Hierarchy model (Jira since 4.0):** the pull is **read only** — each
> linked card's status is recorded under `.cairn/state.json` (`seen`) and
> `/cairn:doctor`'s `jira-links` names any divergence; no bead is closed,
> reopened or rewritten. Without a token in the shell the session fetches
> the cards through the MCP and records them with
> `cairn-jira.sh seen --from-json <file>`.

## What it does

Pulls edits made in the external tools (GitHub/GitLab/Jira/Asana/Azure Boards)
back into bd, the hub:

1. **Confirms** `.cairn/sync.json` exists with an enabled backend. If not →
   run [`/cairn:sync-config`](sync-config.md) first; the command stops.
2. **Runs the reconcile:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/gbsync.sh" pull
   ```
   By default the dispatcher uses the per-backend watermark stored in
   `.cairn/state.json`; only items already present in `.cairn/id-map.json`
   are considered.
3. **Resolves by last-writer-wins on `updated_at`:**
   - external newer than bd → applied to bd via `bd update`
   - bd newer → left for the next push
   - **both changed** since the last pull → **conflict**, logged to
     `.cairn/conflicts.json` with the chosen resolution (LWW still applies)
4. **Reviews conflicts:** reads `.cairn/conflicts.json`; new entries are
   summarized (bd_id, backend, which side won) and the user is asked whether
   any auto-resolution should be overridden by hand.
5. **Reports** the per-backend `applied / conflicts / skipped` counts from the
   dispatcher output.

**Side effect:** step 3 writes to the bd database (`bd update` on items where
the external side won) and advances the watermarks in `.cairn/state.json`. An
unexpected overwrite in bd after a pull is the signature of a both-changed
conflict — check `conflicts.json` before assuming data loss.

Run this after a [`/cairn:migrate`](migrate.md) when sync is configured:
mirror pushes are deliberately suppressed during migration, so one pull at the
end reconciles everything.

**Pull is mapped-items-only.** Items enter `.cairn/id-map.json` via push (bd →
tool) or via the one-shot **import** — external cards that predate the sync
wiring are otherwise invisible to pull. To adopt an existing Jira backlog
first, run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gbsync.sh" import --project
<KEY>` (or `--query '<JQL>'`; capped at 200 items per run) — it mints one bd
issue per card and seeds the id-map, after which pull covers them. See
[`/cairn:sync-config`](sync-config.md), step 6.

## Flags & arguments

| Flag | Meaning |
|---|---|
| `--since <iso8601>` | Force a wider window than the stored watermark (e.g. `--since 1970-01-01T00:00:00Z` to re-scan everything). |

The dispatcher itself also accepts `--dir <path>` (operate on a specific
project dir) and `--dry-run` (print `DRY-RUN:` lines, call no adapter, write
no state) — documented in the [sync guide](../sync.md#8-commands).

## Examples

```text
/cairn:sync-pull
```

→ `gbsync.sh pull` runs against the enabled backends; output summarized as
e.g. `github: applied 2 / conflicts 0 / skipped 5 · jira: applied 1 /
conflicts 1 / skipped 3`, followed by the conflict summary
(`proj-7hp · jira · external won`) and the override question.

```text
/cairn:sync-pull   # "pull applied nothing"
```

→ items unchanged since the watermark. Force a wider window with
`--since 1970-01-01T00:00:00Z` if you expected changes.

## Files touched

- **Reads:** `.cairn/sync.json` (config), `.cairn/id-map.json` (mapped
  items), `.cairn/state.json` (watermarks), `.cairn/conflicts.json` (review).
- **Writes:** the bd database (`.beads/`, via `bd update` for external wins),
  `.cairn/state.json` (advanced watermarks), `.cairn/conflicts.json`
  (appended conflict log).

## Related

- [`/cairn:sync-config`](sync-config.md) — enable and configure the backends
- [`/cairn:status`](status.md) — shows sync staleness and suggests a pull
- [`/cairn:migrate`](migrate.md) — pull once after migrating a synced repo
- [Cairn sync guide](../sync.md) — the LWW algorithm and troubleshooting table
