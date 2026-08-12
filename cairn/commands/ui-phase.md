---
description: Generate the UI design contract (UI-SPEC.md) for a frontend phase — GSD ui-phase, with its requirements tracked as stamped issues
argument-hint: "[phase]"
wraps: ui-phase
implementation: inline
wrap-family: phase
---

Produce the UI contract for phase **$ARGUMENTS** under the `cairn` conventions.

What cairn adds to this verb: a UI-SPEC is a phase artifact with
requirements in it — screens, states, acceptance criteria — and those need
issues like any other requirement. A design contract nobody tracked is a
contract nobody ships against.


1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else shapes the artifact written below. `<N>` may be omitted upstream — when
   it is, resolve the active phase from STATE.md before building any label.

2. **Claim** the phase's ids: `bd update <id> --claim`.

3. **Write the UI-SPEC.**

   The deliverable is `.planning/phases/<NN>-<nome>/<NN>-UI-SPEC.md`:

   - **Screens and states** — every screen, and for each one its loading,
     empty, error and populated states. An unlisted state is one nobody builds.
   - **Component contract** — per screen, the components it needs and the data
     each one receives.
   - **Interaction** — what responds to what, and what the response is.
   - **Accessibility floor** — keyboard path, focus order, contrast, and the
     reduced-motion behaviour.

   Written before any component: the visual direction, named — not "clean and
   modern", but a decision specific enough that two people would build the same
   thing from it.

4. **Every UI-SPEC requirement gets an issue**, with the label pair and the
   stamp:
   ```bash
   bd create "<REQ-ID>: <title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`.

5. **Close what the contract settled** (`bd close <id> --reason="…"`); release
   and leave open what it deferred (`bd update <id> --assignee "" --status
   open`). A screen postponed is not a screen finished.

6. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check` — its
   requirement-gap list is the proof that step 5 was complete.

Next: `/cairn:plan <N>`.
