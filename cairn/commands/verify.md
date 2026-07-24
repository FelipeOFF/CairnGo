---
description: Verify a phase's work — GSD verify-work cross-checked against beads
argument-hint: "[phase-number]"
---

Verify phase **$ARGUMENTS**:

1. Run `/gsd:verify-work $ARGUMENTS`.
2. Cross-check against beads: every issue for the phase
   (`bd list -l phase-$ARGUMENTS`) that the work claims done should be **closed**.
   Labels use the unpadded phase number (`phase-3`, never `phase-03`) — strip any
   leading zero from `$ARGUMENTS` before building the label.
   Flag any mismatch — GSD-verified but bd still open, or bd closed but GSD not
   satisfied — and reconcile (close the issue, or reopen the work).
