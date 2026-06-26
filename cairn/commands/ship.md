---
description: Ship — verify every completed phase's beads are closed, then GSD ship / push
---

Pre-ship gate, then ship:

1. For each completed phase `N`, `bd list -l phase-N --status open` must be empty.
   If any issues are still open, **stop** and report them — do not push.
2. When all completed phases are clean, run `/gsd:ship` to finalize (it handles
   the push). If the project doesn't use `/gsd:ship`, push the branch directly.

Never push with open issues on a phase marked done.
