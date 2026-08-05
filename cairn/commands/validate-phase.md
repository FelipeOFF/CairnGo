---
description: Retroactively fill validation gaps on a completed phase — GSD validate-phase, and any issue the audit re-opens is re-opened in bd too
argument-hint: "[phase number]"
wraps: validate-phase
wrap-family: phase
---

Audit and fill the validation gaps of phase **$ARGUMENTS**, under the `cairn`
conventions.

What this adds over `/gsd:validate-phase`: it works on a **completed** phase,
whose issues the ship gate has already closed. When the audit re-opens work,
bd has to follow — otherwise the gate keeps reading the phase as done while
someone is actively fixing it.

**This wrapper never re-opens on its own initiative.** Re-opening asserts that
finished work is unfinished, and that assertion belongs to the audit, not to
the wrapper. Every re-open below is conditional on the delegate actually
having re-opened something.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight validate-phase
   ```
   Exit `6` or `5` **stops here** — print the script's message verbatim.

2. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else goes **only** to `/gsd:validate-phase`. `<N>` may be omitted upstream —
   resolve the phase from STATE.md before building a label.

3. **Record the closed set:** `bd list -l phase-<N> --all --limit 0 --json`,
   noting which ids are already closed. The difference after the audit is what
   step 6 acts on.

4. **Run `/gsd:validate-phase $ARGUMENTS`.**

5. **Gaps the audit found become issues**, with the label pair and the stamp:
   ```bash
   bd create "<REQ-ID>: <gap>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Then claim them: `bd update <id> --claim`. Labels use the **unpadded**
   number — `phase-3`, never `phase-03`.

6. **If — and only if — the audit re-opened phase work**, re-open the matching
   issues: `bd update <id> --status open`. Name each one and why. A phase the
   audit left intact gets no re-opens at all.

7. **Close what the validation actually completed**
   (`bd close <id> --reason="<1–2 sentences>"`). A gap merely recorded is not a
   gap filled: leave its issue open.

8. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check`, so the
   phase's record shows the re-opened work rather than the old clean sheet.

Next: `/cairn:verify <N>`.
