---
description: Plan a phase — GSD plan-phase plus beads map reconciliation
argument-hint: <phase-number> [--auto] [--research|--skip-research] [--gaps] [--skip-verify] [--prd <file>] [--reviews] [--text] [--tdd]
group: loop
---

Plan phase **$ARGUMENTS** under the `cairn` conventions.

$ARGUMENTS may carry vendored plan-phase flags after the phase number (`--auto`,
`--research`, `--skip-research`, `--gaps`, `--skip-verify`, `--prd <file>`,
`--reviews`, `--text`, `--tdd`). Split it first: the bare phase number `<N>`
drives `cairn-map` and labels; the flags go **only** to the vendored workflow in step 2.

1. Regenerate the phase's beads map, then read it. The map is generated from
   bd state — do not hand-edit between its markers:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```
   Exit 5 means bd is unavailable — say so and continue without the map;
   there is no cached copy to fall back to, because the map is printed from
   bd on demand and never stored.
2. Execute the vendored planning workflow with the full arguments (phase
   number plus any flags). It ships inside this plugin — read it and follow
   it:
   ```
   ${CLAUDE_PLUGIN_ROOT}/gsd/commands/gsd/plan-phase.md
   ```
3. Reconcile divergence: where a bd issue conflicts with the phase `CONTEXT.md`,
   **CONTEXT wins** — flag it ⚠ (outside the markers) and `bd update` the issue
   to match (with a dated note pointing at the GSD doc). Create issues for any
   unmapped requirement (label pair + `gsd` metadata stamp, per the `cairn`
   skill), then regenerate the map; `cairn-map.sh <N> --check` verifies
   it is current (exit 3 + diff when stale).
4. Set each generated `PLAN.md`'s `beads:` frontmatter to the bd ids it advances.

Next: `/cairn:work <N>`.
