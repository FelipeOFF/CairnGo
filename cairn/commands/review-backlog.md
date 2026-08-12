---
description: Promote backlog items into the active milestone — GSD review-backlog, and every promoted item arrives as a stamped bd issue
argument-hint: "[milestone]"
wraps: review-backlog
implementation: inline
wrap-family: milestone
---

Review the backlog and promote into the active milestone, under the `cairn`
conventions.

What cairn adds to this verb: promoting an item **creates tracked
work**. An item that moves into the milestone as a line of markdown and nothing
else is exactly the off-the-books work cairn exists to prevent — it will not
appear in `/cairn:status`, will not gate a ship, and will not show up in any
phase's map.


1. **Resolve the active milestone** from ROADMAP.md's current milestone header,
   or STATE.md. Everything below is scoped by `m-<milestone>`.

2. **Record what is already tracked**, so promotion does not duplicate it:
   `bd list -l m-<milestone> --all --limit 0 --json`. An item whose issue
   already exists is **claimed**, not re-created:
   `bd update <id> --claim` (atomic: assigns and sets `in_progress`).

3. **Promote the items.**

   The deliverable is twofold, and neither half is optional:

   - `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` gain the promoted
     items — a promoted item that appears in no roadmap phase is a decision
     nobody can act on;
   - the backlog source loses them, or marks them promoted, so the same item
     cannot be promoted twice.

   Each promoted item names the phase it lands in and the requirement id it
   becomes. Step 4 is what turns those ids into stamped issues; an item
   promoted without one is untracked work wearing a checkmark.

4. **Every promoted item becomes an issue** — this is the step the wrapper
   exists for:
   ```bash
   bd create "<title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   The label pair is `m-<milestone>` + `phase-<N>`, with the **unpadded**
   number — `phase-3`, never `phase-03`. An item promoted into the milestone
   but not yet into a phase carries the milestone label and **no** `phase-*`
   label, the same rule `/cairn:quick` follows for unphased work — never a
   guessed phase number.

5. **An item the review declined stays declined, on the record.** Leave it in
   the backlog; do not create an issue for it, and do not delete anything.

6. **Close the review's own bookkeeping issue**, when there is one:
   `bd close <id> --reason="<what was promoted, in 1–2 sentences>"`. The
   promoted items stay **open** — they are the work, not the review of it.

7. **Refresh the map of every phase that gained an item**: `cairn-map.sh <N>`,
   then `--check`.

Next: `/cairn:plan <N>`.
