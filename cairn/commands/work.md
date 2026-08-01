---
description: Execute a phase — claim its beads, run GSD execute-phase, close on success
argument-hint: <phase-number> [--wave N] [--gaps-only] [--interactive] [--tdd]
---

Execute phase **$ARGUMENTS** under the `cairn` conventions.

$ARGUMENTS may carry `/gsd:execute-phase` flags after the phase number
(`--wave N`, `--gaps-only`, `--interactive`, `--tdd`). Split it first: the
bare phase number `<N>` drives claims, labels, and `cairn-map`; the flags go
**only** to `/gsd:execute-phase`.

1. Acquire this phase's coordination lease before anything else:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-lease.sh" acquire "$N"
   ```
   `${CLAUDE_PLUGIN_ROOT}` is correct here — work.md IS a cairn command, not
   a capability fragment, so it resolves to cairn's own plugin root
   directly. Do not "fix" this to the CAP-locator pattern the fragments
   below use; that pattern exists only for prose injected into a *different*
   plugin's workflow (a bare `/gsd:*` run), which does not apply to a cairn
   command running under `${CLAUDE_PLUGIN_ROOT}` itself. Exit 3 means
   another live worktree currently holds the lease — this is purely
   informational, never a reason to block (D-04: never overwrite silently,
   never break the flow): surface the script's printed report verbatim (who
   holds it, and since when), then continue immediately into the per-plan
   claim loop below regardless. Exit 5 (bd unavailable) degrades the same
   non-blocking way the rest of this command already treats bd being
   unavailable. Any other outcome needs no message beyond acquire's own
   one-line report.
2. For each plan in the phase, **before starting it**: for every id in that
   plan's `beads:` frontmatter run `bd update <id> --claim` — `--claim`
   atomically assigns the issue to you AND sets its status to `in_progress`
   (no separate `--status` call needed; idempotent if already yours).
3. Run `/gsd:execute-phase $ARGUMENTS` — the full arguments, phase number
   plus any flags.
4. On a plan's successful completion **and** verification, close its ids:
   `bd close <id> --reason="<1–2 sentence summary>"`.
5. Done check: scope the list with the label pair when the milestone is known —
   `bd list -l m-<active milestone>,phase-<N> --status open` (the active
   milestone comes from ROADMAP.md's current milestone header, or STATE.md) —
   and it should be empty when the phase is complete; report anything still
   open. Labels use the unpadded phase number (`phase-3`, never `phase-03`) —
   strip any leading zero from `<N>` before building the label.
6. Refresh the phase's generated map so it reflects the closes:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```

Next: `/cairn:verify <N>` or `/cairn:ship`.
