---
description: Start a new cairn project — GSD new-project, then create the bd issues and generate the phase↔beads maps
group: setup
---

Kick off a new project end to end, under the `cairn` conventions.

**Guard:** if `.planning/` already exists, refuse and stop — this repo already
has GSD history. Route the user to `/cairn:migrate` instead; never run a
project-creation interview over an existing `.planning/`.

1. If `bd` or `.beads/` is missing, run `/cairn:init` first and stop.
2. Create `.planning/` + the ROADMAP. **cairn does not vendor project
   creation** — v1.6 vendored the four cycle verbs (discuss, plan, execute,
   verify) and nothing else, so there is no `new-project` inside this plugin
   to call. Two routes, in this order:
   - a GSD plugin installed alongside cairn: `/cairn:gsd new-project` (the
     declared passthrough) runs the interview;
   - otherwise author the three files here, in this command, from the
     templates: PROJECT (what and why), the phase list, and one requirement
     per row. That is this command doing its job on a directory where none
     of them exist yet, not a bookkeeping edit — nothing has counters to
     desync until a phase closes, and from the first close onward every
     tick goes through `cairn-bookkeep`, never through a keyboard.
     `/cairn:plan <N>`, `/cairn:work <N>` and `/cairn:doctor` all work from
     there. Say which route you took.
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
