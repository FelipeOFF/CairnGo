---
description: Reconcile external work-management tools back into bd (pull-on-demand, last-writer-wins)
argument-hint: "[--since <iso8601>]"
group: sync
---

Pull edits made in the external tools (GitHub/GitLab/Jira/Asana/Azure Boards) back into
bd, the hub. Do the following:

1. Confirm `.cairn/sync.json` exists with an enabled backend. If not, tell
   the user to run `/cairn:sync-config` and stop.

2. Run the reconcile:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/gbsync.sh" pull $ARGUMENTS
   ```
   (Flags the user typed are in $ARGUMENTS and pass through: `--since
   <iso8601>` forces a wider window than the per-backend watermark in
   `.cairn/state.json`; the dispatcher also accepts `--dir <path>` and
   `--dry-run`.)

3. A backend in the **hierarchy model** (`"model": "hierarchy"` — the Jira
   backend `/cairn:sync-config` writes) is **read only** here: the pull
   records each linked card's status under `.cairn/state.json` (`seen`) and
   `/cairn:doctor`'s `jira-links` names any divergence (a card Done with
   its bead open, or the reverse). Nothing closes, reopens or rewrites a
   bead — the bead is the source. When the dispatcher reports
   `skip … no <token> in the shell`, do the read yourself: fetch each
   linked key through the MCP (`getJiraIssue`, per `/cairn:jira`), save
   the JSON, and record it with
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-jira.sh" seen --from-json <file>`
   — then run the doctor.

   For a flat backend, reconciliation is **last-writer-wins by `updated_at`**:
   - external newer than bd → applied to bd via `bd update`
   - bd newer → left for the next push
   - both changed since last pull → **conflict**, logged to
     `.cairn/conflicts.json` with the chosen resolution

4. After it runs, read `.cairn/conflicts.json`. If there are new entries,
   summarize them for the user (bd_id, backend, which side won) and ask whether
   any auto-resolution should be overridden by hand.

5. Report the per-backend `applied / conflicts / skipped` counts from the
   dispatcher output.
