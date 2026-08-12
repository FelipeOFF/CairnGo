---
description: Verify a phase's work — GSD verify-work cross-checked against beads
argument-hint: "[phase-number]"
group: loop
---

Verify phase **$ARGUMENTS**:

1. Execute the vendored verification workflow with `$ARGUMENTS`. It ships
   inside this plugin — read it and follow it:
   ```
   ${CLAUDE_PLUGIN_ROOT}/gsd/commands/gsd/verify-work.md
   ```
2. Cross-check against beads: every issue for the phase
   (`bd list -l m-<milestone>,phase-$ARGUMENTS` when the milestone is known —
   ROADMAP.md's current milestone header — else `bd list -l phase-$ARGUMENTS`)
   that the work claims done should be **closed**.
   Labels use the unpadded phase number (`phase-3`, never `phase-03`) — strip any
   leading zero from `$ARGUMENTS` before building the label.
   Flag any mismatch — GSD-verified but bd still open, or bd closed but GSD not
   satisfied — and reconcile (close the issue, or reopen the work). Then refresh
   the phase's generated map: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$ARGUMENTS"`.
