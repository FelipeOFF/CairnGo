---
description: Retroactively verify a completed phase's threat mitigations — GSD secure-phase, and an unmitigated threat becomes a tracked issue rather than a note
argument-hint: "[phase number]"
wraps: secure-phase
wrap-family: phase
---

Verify the threat mitigations of phase **$ARGUMENTS**, under the `cairn`
conventions.

What this adds over `/gsd:secure-phase`: same shape as `validate-phase`, on a
**completed** phase whose issues are already closed — plus one thing specific
to security work. **An unmitigated threat recorded only as prose is the way
security findings die.** Every one of them leaves this command as a tracked
issue with an id someone can be assigned.

**This wrapper never re-opens on its own initiative.** Re-opening asserts that
finished work is unfinished; that assertion belongs to the audit.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight secure-phase
   ```
   Exit `6` or `5` **stops here** — print the script's message verbatim.

2. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else goes **only** to `/gsd:secure-phase`. `<N>` may be omitted upstream —
   resolve it from STATE.md before building a label.

3. **Record the closed set:** `bd list -l phase-<N> --all --limit 0 --json`.

4. **Run `/gsd:secure-phase $ARGUMENTS`.**

5. **Every unmitigated threat becomes an issue**, with the label pair and the
   stamp, and with the threat named in the title rather than "security fix":
   ```bash
   bd create "<threat>: <what is unmitigated>" -t task -p 1 \
     -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Then claim what you will work now: `bd update <id> --claim`. Labels use the
   **unpadded** number — `phase-3`, never `phase-03`.

6. **If — and only if — the audit re-opened phase work**, re-open the matching
   issues: `bd update <id> --status open`, naming each and why.

7. **Close only a mitigation that is verified**
   (`bd close <id> --reason="<how it was verified>"`). "Looks fine" is not a
   verification, and a reason that does not say how it was checked is the same
   silence in different words.

8. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check`.

Next: `/cairn:verify <N>`.
