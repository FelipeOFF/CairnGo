---
description: CRUD for phases in ROADMAP.md — GSD phase, plus the relabel that keeps its issues from being orphaned
argument-hint: "[--insert | --remove | --edit] <phase-name-or-number>"
wraps: phase
implementation: inline
wrap-family: structural
---

Manage phases under the `cairn` conventions — **$ARGUMENTS**.

This is the strongest case on the wrap list, and the reason is mechanical:
`--remove` and `--insert` renumber phases, and **every bd issue carrying the old
`phase-<N>` label is orphaned the moment the ROADMAP moves under it**. Editing the roadmap
knows nothing about those labels. This wrapper moves them.


1. **Record the before-state.** Split `$ARGUMENTS`: the mode flag (`--insert`,
   `--remove`, `--edit`, or none) and the phase name-or-number. For every phase
   the operation can touch — the target and, for `--remove`/`--insert`, every
   phase numbered after it — capture the current mapping:
   ```bash
   bd list -l phase-<N> --all --limit 0 --json
   ```
   Do this **before** delegating. Afterwards the ROADMAP no longer tells you
   which issues used to belong to which number, and the mapping is unrecoverable
   without reading git history.

2. **Claim the work.** For each id you are about to move:
   `bd update <id> --claim` — atomic: it assigns the issue to you **and** sets
   `in_progress` in one call. No separate `--status`; it is idempotent when the
   issue is already yours.

3. **Edit the ROADMAP.**

   The deliverable is the edited `.planning/ROADMAP.md`, and — when the change
   adds or removes requirements — `.planning/REQUIREMENTS.md` with it:

   - **add** appends a phase; **insert** places one at a position and pushes
     the rest down; **remove** deletes one and pulls the rest up; **edit**
     rewrites a phase's card, goal, requirements or dependencies in place.
   - A phase carries: the card (the question it answers), the goal, its
     requirement ids, whether it needs research, and what it depends on.

   **Written before the ROADMAP is touched: the renumbering plan.** Insert and
   remove renumber every phase after the target, and the `phase-<N>` labels
   follow — that mapping is what step 4 replays onto bd, and deriving it after
   the file has already moved is how issues get orphaned.

4. **Move the labels.** This is the step that only exists here. For each
   renumbering the delegate performed, run the script that owns this migration —
   it deep-merges `metadata.gsd.phase` instead of clobbering it, which a plain
   `bd update --metadata` would not:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-relabel.sh" renumber \
     --from <old> --to <new> --milestone <active milestone> --dry-run
   ```
   Read the dry run, then repeat without `--dry-run`. Exit `2` is a **refusal**,
   not a crash: a target issue already carries the destination label, and the
   double label would be ambiguous. Resolve the conflict by hand — never reach
   for `--force` to get past a refusal you have not read.

   Labels use the **unpadded** phase number — `phase-3`, never `phase-03`. Strip
   any leading zero from `<N>` before building a label. The label pair is
   `m-<milestone>` + `phase-<N>`; the active milestone comes from ROADMAP.md's
   current milestone header, or STATE.md.

5. **A phase that was added needs its issues.** For each requirement the new
   phase carries, create the issue with the label pair and the house stamp:
   ```bash
   bd create "<title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   A phase that was **removed** leaves its issues behind: close them with a
   reason (`bd close <id> --reason="phase removed from ROADMAP"`), or, when the
   work is merely deferred, release and leave them open
   (`bd update <id> --assignee "" --status open`) so they stay visible in
   `/cairn:status`. Never delete an issue to tidy up a renumber.

6. **Refresh the generated maps** of every phase whose number moved:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```
   Exit `5` means bd is unavailable — degrade the way the rest of cairn already
   degrades: say so and carry on, do not block.

7. **Prove it.** `bd list -l phase-<old> --all --json` should now be empty for
   every number that moved, and the new number should hold exactly the ids you
   recorded in step 2. Report any id that did not arrive.

Next: `/cairn:status`, then `/cairn:plan <N>`.
