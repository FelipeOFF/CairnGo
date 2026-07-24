---
description: Plan a phase — GSD plan-phase plus beads map reconciliation
argument-hint: <phase-number>
---

Plan phase **$ARGUMENTS** under the `cairn` conventions:

1. Resolve the phase directory and READ its beads map first. Under
   `.planning/phases/`, the directory is the one whose numeric prefix equals
   phase $ARGUMENTS — the prefix may be zero-padded (`3` matches both `3-auth`
   and `03-auth`) and may carry an optional project-code prefix
   (e.g. `myproj-03-auth`). Then read the `*-BEADS-MAP.md` file inside it:
   ```bash
   n=$((10#$ARGUMENTS))   # normalize: '3' and '03' are the same phase
   dir=$(ls -d .planning/phases/*/ | grep -E "/([A-Za-z0-9]+-)?0*${n}-[^/]*/$" | head -1)
   cat "${dir}"*-BEADS-MAP.md
   ```
2. Run `/gsd:plan-phase $ARGUMENTS`.
3. Reconcile divergence: where a bd issue conflicts with the phase `CONTEXT.md`,
   **CONTEXT wins** — flag it ⚠ and `bd update` the issue to match (with a dated
   note pointing at the GSD doc). Create issues for any unmapped requirement and
   add them to the map.
4. Set each generated `PLAN.md`'s `beads:` frontmatter to the bd ids it advances.

Next: `/cairn:work $ARGUMENTS`.
