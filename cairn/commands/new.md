---
description: Start a new cairn project — GSD new-project, then create the bd issues and generate the phase↔beads maps
group: setup
---

Kick off a new project end to end, under the `cairn` conventions.

**Guard:** if `.planning/` already exists, refuse and stop — this repo already
has GSD history. Route the user to `/cairn:migrate` instead; never run
`/gsd:new-project` over an existing `.planning/`.

1. If `bd` or `.beads/` is missing, run `/cairn:init` first and stop.
2. Run `/gsd:new-project` to create `.planning/` + the ROADMAP (interactive).
3. Once the roadmap exists, apply the `cairn` skill: for every requirement,
   `bd create` one issue with the label pair `m-<milestone>,phase-<N>` and the
   metadata stamp
   `--metadata '{"gsd": {"req": "CAT-NN", "phase": N, "milestone": "vX.Y"}}'`
   (dedup on `(gsd.req, gsd.milestone)` — update, don't duplicate). Capture
   roadmap-implied ordering with `bd dep add`.
4. Generate each phase's map — never hand-write the tables:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>   # once per phase
   ```
5. Confirm: `bd list` shows the new issues and each phase dir has its
   generated `NN-BEADS-MAP.md`.

Then the loop is `/cairn:plan N` → `/cairn:work N` → `/cairn:ship`.
