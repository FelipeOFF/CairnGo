---
description: Start a new cairn project — GSD new-project, then create the bd issues and phase↔beads maps
---

Kick off a new project end to end, under the `cairn` conventions:

1. If `bd` or `.beads/` is missing, run `/cairn:init` first and stop.
2. Run `/gsd:new-project` to create `.planning/` + the ROADMAP (interactive).
3. Once the roadmap exists, apply the `cairn` skill: for every requirement,
   `bd create` one issue, label it `phase-N`, and write each phase's
   `.planning/phases/NN-<slug>/NN-BEADS-MAP.md`. Capture roadmap-implied
   ordering with `bd dep add`.
4. Confirm: `bd list` shows the new issues and each phase dir has its map.

Then the loop is `/cairn:plan N` → `/cairn:work N` → `/cairn:ship`.
