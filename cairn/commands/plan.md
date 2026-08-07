---
description: Plan a phase — GSD plan-phase plus beads map reconciliation
argument-hint: <phase-number> [--auto] [--research|--skip-research] [--gaps] [--skip-verify] [--prd <file>] [--reviews] [--text] [--tdd]
group: loop
---

Plan phase **$ARGUMENTS** under the `cairn` conventions.

$ARGUMENTS may carry `/gsd:plan-phase` flags after the phase number (`--auto`,
`--research`, `--skip-research`, `--gaps`, `--skip-verify`, `--prd <file>`,
`--reviews`, `--text`, `--tdd`). Split it first: the bare phase number `<N>`
drives `cairn-map` and labels; the flags go **only** to `/gsd:plan-phase`.

1. Regenerate the phase's beads map, then read it. The map is generated from
   bd state — do not hand-edit between its markers:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```
   Exit 5 means bd is unavailable — fall back to reading the existing file
   as-is (resolve the phase directory by its numeric prefix under
   `.planning/phases/`, then read its `*-BEADS-MAP.md`). `cairn-map` resolves
   the phase directory itself (`3` matches both
   `3-auth` and `03-auth`, with an optional project-code prefix like
   `myproj-03-auth`) and prints the map's path; read that
   `*-BEADS-MAP.md` file, including any manual notes outside the markers.
2. Run `/gsd:plan-phase $ARGUMENTS` — the full arguments, phase number plus
   any flags.
3. Reconcile divergence: where a bd issue conflicts with the phase `CONTEXT.md`,
   **CONTEXT wins** — flag it ⚠ (outside the markers) and `bd update` the issue
   to match (with a dated note pointing at the GSD doc). Create issues for any
   unmapped requirement (label pair + `gsd` metadata stamp, per the `cairn`
   skill), then regenerate the map; `cairn-map.sh <N> --check` verifies
   it is current (exit 3 + diff when stale).
4. Set each generated `PLAN.md`'s `beads:` frontmatter to the bd ids it advances.

Next: `/cairn:work <N>`.
