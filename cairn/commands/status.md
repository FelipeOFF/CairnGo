---
description: One combined view — beads ready/blocked work plus GSD project progress
---

Show a single status view that fuses both tools:

1. `bd ready` — work claimable right now.
2. Dependency-blocked work — `bd list` and call out issues waiting on open deps.
3. The active phase's open issues — `bd list -l phase-<current> --status open`.
4. Roadmap-level state — `/gsd:progress`.

Summarize the four together in a few lines: what's in progress, what's ready to
pick up next, and what's blocking. Keep it tight.
