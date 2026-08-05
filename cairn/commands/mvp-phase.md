---
description: Plan a phase as a vertical MVP slice — GSD mvp-phase, with the PLAN's beads frontmatter filled and the map reconciled
argument-hint: "<phase-number>"
wraps: mvp-phase
wrap-family: phase
---

Plan phase **$ARGUMENTS** as a vertical MVP slice, under the `cairn`
conventions.

What this adds over `/gsd:mvp-phase`: it writes a `PLAN.md`, and in cairn a
PLAN without `beads:` frontmatter is a plan nothing can trace. The SPIDR split
also produces slices that do not map one-to-one onto the phase's existing
issues — that divergence gets named here rather than found at execution time.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight mvp-phase
   ```
   Exit `6` or `5` **stops here** — print the script's message verbatim.

2. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else goes **only** to `/gsd:mvp-phase`.

3. **Regenerate and read the map first**
   (`cairn-map.sh <N>`; exit `5` degrades to reading the file as-is), so the
   slicing starts from the tracked work rather than from scratch.

4. **Claim.** For every id on the map: `bd update <id> --claim`.

5. **Run `/gsd:mvp-phase $ARGUMENTS`.**

6. **Fill each generated `PLAN.md`'s `beads:` frontmatter** with the ids that
   plan advances. This is the link that makes `/cairn:work` able to claim and
   close by plan; without it the phase executes untracked.

7. **A slice with no issue gets one**, with the label pair and the stamp:
   ```bash
   bd create "<title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`.

8. **Work the MVP defers is released, not closed.** A slice pushed out of the
   MVP is still real: `bd update <id> --assignee "" --status open` keeps it in
   `/cairn:status`'s ready lane. Use `bd close <id> --reason="…"` only for what
   the slicing genuinely finished or genuinely killed.

9. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check`.

Next: `/cairn:work <N>`.
