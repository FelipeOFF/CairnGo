---
description: Execute a phase — claim its beads, run GSD execute-phase, close on success
argument-hint: <phase-number> [--wave N] [--gaps-only] [--interactive] [--tdd]
---

Execute phase **$ARGUMENTS** under the `cairn` conventions.

$ARGUMENTS may carry `/gsd:execute-phase` flags after the phase number
(`--wave N`, `--gaps-only`, `--interactive`, `--tdd`). Split it first: the
bare phase number `<N>` drives claims, labels, and `cairn-map`; the flags go
**only** to `/gsd:execute-phase`.

1. For each plan in the phase, **before starting it**: for every id in that
   plan's `beads:` frontmatter run `bd update <id> --claim` — `--claim`
   atomically assigns the issue to you AND sets its status to `in_progress`
   (no separate `--status` call needed; idempotent if already yours).
2. Run `/gsd:execute-phase $ARGUMENTS` — the full arguments, phase number
   plus any flags.
3. On a plan's successful completion **and** verification, close its ids:
   `bd close <id> --reason="<1–2 sentence summary>"`.
4. Done check: scope the list with the label pair when the milestone is known —
   `bd list -l m-<active milestone>,phase-<N> --status open` (the active
   milestone comes from ROADMAP.md's current milestone header, or STATE.md) —
   and it should be empty when the phase is complete; report anything still
   open. Labels use the unpadded phase number (`phase-3`, never `phase-03`) —
   strip any leading zero from `<N>` before building the label.
5. Refresh the phase's generated map so it reflects the closes:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```

Next: `/cairn:verify <N>` or `/cairn:ship`.
