---
description: Plan a phase — GSD plan-phase plus beads map reconciliation
argument-hint: <phase-number>
---

Plan phase **$ARGUMENTS** under the `cairn` conventions:

1. READ that phase's `.planning/phases/$ARGUMENTS*-*/NN-BEADS-MAP.md` first.
2. Run `/gsd:plan-phase $ARGUMENTS`.
3. Reconcile divergence: where a bd issue conflicts with the phase `CONTEXT.md`,
   **CONTEXT wins** — flag it ⚠ and `bd update` the issue to match (with a dated
   note pointing at the GSD doc). Create issues for any unmapped requirement and
   add them to the map.
4. Set each generated `PLAN.md`'s `beads:` frontmatter to the bd ids it advances.

Next: `/cairn:work $ARGUMENTS`.
