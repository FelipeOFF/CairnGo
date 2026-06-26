---
description: Verify a phase's work — GSD verify-work cross-checked against beads
argument-hint: "[phase-number]"
---

Verify phase **$ARGUMENTS**:

1. Run `/gsd:verify-work $ARGUMENTS`.
2. Cross-check against beads: every issue for the phase
   (`bd list -l phase-$ARGUMENTS`) that the work claims done should be **closed**.
   Flag any mismatch — GSD-verified but bd still open, or bd closed but GSD not
   satisfied — and reconcile (close the issue, or reopen the work).
