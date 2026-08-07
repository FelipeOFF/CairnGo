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

3. Reconciliation is **last-writer-wins by `updated_at`**:
   - external newer than bd → applied to bd via `bd update`
   - bd newer → left for the next push
   - both changed since last pull → **conflict**, logged to
     `.cairn/conflicts.json` with the chosen resolution

4. After it runs, read `.cairn/conflicts.json`. If there are new entries,
   summarize them for the user (bd_id, backend, which side won) and ask whether
   any auto-resolution should be overridden by hand.

5. Report the per-backend `applied / conflicts / skipped` counts from the
   dispatcher output.
