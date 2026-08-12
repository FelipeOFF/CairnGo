---
description: Plan a phase as a vertical MVP slice — GSD mvp-phase, with the PLAN's beads frontmatter filled and the map reconciled
argument-hint: "<phase-number>"
wraps: mvp-phase
implementation: inline
wrap-family: phase
---

Plan phase **$ARGUMENTS** as a vertical MVP slice, under the `cairn`
conventions.

What cairn adds to this verb: it writes a `PLAN.md`, and in cairn a
PLAN without `beads:` frontmatter is a plan nothing can trace. The SPIDR split
also produces slices that do not map one-to-one onto the phase's existing
issues — that divergence gets named here rather than found at execution time.


1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else shapes the artifact written below.

2. **Regenerate and read the map first**
   (`cairn-map.sh <N>`; exit `5` degrades to reading the file as-is), so the
   slicing starts from the tracked work rather than from scratch.

3. **Claim.** For every id on the map: `bd update <id> --claim`.

4. **Write the MVP plan.**

   The deliverable is one or more `.planning/phases/<NN>-<nome>/<NN>-<MM>-PLAN.md`
   shaped as a **vertical slice**, not a layer:

   - Standard PLAN frontmatter, including `beads:` (step 5 fills it),
     `requirements:` and `files_modified:`.
   - **The tracer task comes first** — one thin path that crosses every layer
     end to end and is production quality, never a throwaway. Everything after
     it expands the slice; nothing before it exists.
   - Each task carries its own `<verify>`: the command that fails if the task
     is not done.

   Written before the first task: which layer is the thinnest honest slice, and
   why that one. A plan that stacks layers instead of crossing them is the
   failure this command exists to prevent.

5. **Fill each generated `PLAN.md`'s `beads:` frontmatter** with the ids that
   plan advances. This is the link that makes `/cairn:work` able to claim and
   close by plan; without it the phase executes untracked.

6. **A slice with no issue gets one**, with the label pair and the stamp:
   ```bash
   bd create "<title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`.

7. **Work the MVP defers is released, not closed.** A slice pushed out of the
   MVP is still real: `bd update <id> --assignee "" --status open` keeps it in
   `/cairn:status`'s ready lane. Use `bd close <id> --reason="…"` only for what
   the slicing genuinely finished or genuinely killed.

8. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check`.

Next: `/cairn:work <N>`.
