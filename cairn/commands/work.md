---
description: Execute a phase — claim its beads, run GSD execute-phase, close on success
argument-hint: <phase-number>
---

Execute phase **$ARGUMENTS** under the `cairn` conventions:

1. For each plan in the phase, **before starting it**: for every id in that
   plan's `beads:` frontmatter run `bd update <id> --claim` — `--claim`
   atomically assigns the issue to you AND sets its status to `in_progress`
   (no separate `--status` call needed; idempotent if already yours).
2. Run `/gsd:execute-phase $ARGUMENTS`.
3. On a plan's successful completion **and** verification, close its ids:
   `bd close <id> --reason="<1–2 sentence summary>"`.
4. Done check: `bd list -l phase-$ARGUMENTS --status open` should be empty when
   the phase is complete — report anything still open. Labels use the unpadded
   phase number (`phase-3`, never `phase-03`) — strip any leading zero from
   $ARGUMENTS before building the label.

Next: `/cairn:verify $ARGUMENTS` or `/cairn:ship`.
