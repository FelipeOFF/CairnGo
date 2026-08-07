---
description: Generate the UI design contract (UI-SPEC.md) for a frontend phase — GSD ui-phase, with its requirements tracked as stamped issues
argument-hint: "[phase]"
wraps: ui-phase
wrap-family: phase
---

Produce the UI contract for phase **$ARGUMENTS** under the `cairn` conventions.

What this adds over `/gsd:ui-phase`: a UI-SPEC is a phase artifact with
requirements in it — screens, states, acceptance criteria — and those need
issues like any other requirement. A design contract nobody tracked is a
contract nobody ships against.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight ui-phase
   ```
   Exit `6` or `5` **stops here** — print the script's message verbatim.

2. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else goes **only** to `/gsd:ui-phase`. `<N>` may be omitted upstream — when
   it is, resolve the active phase from STATE.md before building any label.

3. **Claim** the phase's ids: `bd update <id> --claim`.

4. **Run `/gsd:ui-phase $ARGUMENTS`.**

5. **Every UI-SPEC requirement gets an issue**, with the label pair and the
   stamp:
   ```bash
   bd create "<REQ-ID>: <title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`.

6. **Close what the contract settled** (`bd close <id> --reason="…"`); release
   and leave open what it deferred (`bd update <id> --assignee "" --status
   open`). A screen postponed is not a screen finished.

7. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check` — its
   requirement-gap list is the proof that step 5 was complete.

Next: `/cairn:plan <N>`.
