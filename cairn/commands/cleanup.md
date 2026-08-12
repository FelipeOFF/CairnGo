---
description: Archive phase directories from completed milestones — GSD cleanup, refusing to archive over open issues or a missing beads map
argument-hint: "[milestone]"
wraps: cleanup
implementation: inline
wrap-family: milestone
---

Archive the phase directories of a completed milestone, under the `cairn`
conventions.

What cairn adds to this verb: it refuses to archive a phase whose work is
not finished. Archiving is about the DIRECTORIES; the record lives in bd and
does not move with them — so the one thing that can still go wrong is filing
away a phase that the tracker says is open.

(Until v1.7 there was a second danger, and it was the bigger one: the
`NN-BEADS-MAP.md` inside each directory was the only written link between the
work and the tracker, so archiving without it destroyed record. The map is a
printed view now, and the link is the bd store itself — nothing is buried by
moving a directory.)

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
   - **No map to rebuild, and nothing to lose by moving a directory.** The
     phase↔issue record is in bd; inspect it any time with `cairn-map.sh <N>`,
     before or after the archive, and it reads the same.

3. **Claim the milestone's remaining bookkeeping**, if any is still assignable:
   `bd update <id> --claim` (atomic: assigns and sets `in_progress`).

4. **Archive the phase directories.**

   The deliverable is the completed milestone's phase directories moved from
   `.planning/phases/` to `.planning/milestones/<vX.Y>-phases/`, matching the
   layout the earlier milestones already use.

   Moved whole, never filtered: whatever a phase directory holds travels
   with it.

   `.planning/phases/` keeps only the active milestone's phases afterwards.

5. **Verify the archive moved what it said it moved.** Every phase directory
   named in the plan is at its new path and none is left behind. Report any
   that is — with its path, not a count.

6. **Close the bookkeeping issue** for the cleanup itself, when there is one:
   `bd close <id> --reason="<1–2 sentences>"`. Issues belonging to archived
   phases are **not** touched here: they were already closed in step 3, or the
   command stopped. Labels use the **unpadded** number — `phase-3`, never
   `phase-03` — and the pair is `m-<milestone>` + `phase-<N>`; anything created
   here carries the `metadata.gsd` stamp like everything else.

Next: `/cairn:status`.
