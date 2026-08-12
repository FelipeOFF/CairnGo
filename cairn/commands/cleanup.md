---
description: Archive phase directories from completed milestones — GSD cleanup, refusing to archive over open issues or a missing beads map
argument-hint: "[milestone]"
wraps: cleanup
implementation: inline
wrap-family: milestone
---

Archive the phase directories of a completed milestone, under the `cairn`
conventions.

What cairn adds to this verb, and it is the only one of the thirteen
whose carelessness **destroys record**: the `NN-BEADS-MAP.md` files live inside
the directories being archived. They are the phase↔issue record. Archiving a
phase whose issues are still open, or whose map is missing, buries the only
written link between the work and the tracker.

So this wrapper checks **before** delegating, and names what it finds instead
of archiving over it.


1. **Resolve the milestone.** `$ARGUMENTS` may name it; otherwise take the
   completed milestone from ROADMAP.md's headers, or STATE.md. Everything below
   is scoped by `m-<milestone>`.

2. **Enumerate what would be archived**, then check each phase, and do this
   **before** running anything:
   ```bash
   bd list -l m-<milestone>,phase-<N> --status open --json
   ```
   - **Any open issue → stop and name it**, with its id and title. Do not
     archive. The fix is `/cairn:milestone complete`, whose gate exists for
     exactly this, or closing the work.
   - **A phase directory with no `NN-BEADS-MAP.md` → regenerate it first**
     (`cairn-map.sh <N>`), so what gets archived carries its record. Exit `5`
     (bd unavailable) means the map cannot be rebuilt: **stop** rather than
     archive a phase whose record you could not write. This is the one place
     in cairn where exit `5` blocks, and the reason is that the loss is
     permanent.

3. **Claim the milestone's remaining bookkeeping**, if any is still assignable:
   `bd update <id> --claim` (atomic: assigns and sets `in_progress`).

4. **Archive the phase directories.**

   The deliverable is the completed milestone's phase directories moved from
   `.planning/phases/` to `.planning/milestones/<vX.Y>-phases/`, matching the
   layout the earlier milestones already use.

   Moved whole, never filtered: `NN-BEADS-MAP.md` travels **inside** the
   directory it belongs to. That file is the only written link between the work
   and the tracker, and archiving a phase without it is the record loss this
   command refuses to commit.

   `.planning/phases/` keeps only the active milestone's phases afterwards.

5. **Verify the archive kept the record.** Every archived phase directory still
   contains its `NN-BEADS-MAP.md`. Report any that does not — with its path,
   not a count.

6. **Close the bookkeeping issue** for the cleanup itself, when there is one:
   `bd close <id> --reason="<1–2 sentences>"`. Issues belonging to archived
   phases are **not** touched here: they were already closed in step 3, or the
   command stopped. Labels use the **unpadded** number — `phase-3`, never
   `phase-03` — and the pair is `m-<milestone>` + `phase-<N>`; anything created
   here carries the `metadata.gsd` stamp like everything else.

Next: `/cairn:status`.
