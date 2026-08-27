---
description: Record the UI design contract for a frontend phase — the UI-SPEC on the phase carrier, with its requirements tracked as stamped issues
argument-hint: "[phase]"
wraps: ui-phase
implementation: inline
wrap-family: phase
---

Produce the UI contract for phase **$ARGUMENTS** under the `cairn` conventions.

**The record is the bead.** Nothing this command produces is a file: every
piece of prose goes through one boundary,
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" <kind> --phase <N>`,
body on stdin, and lands on the phase carrier (`design` for the design
kinds, one `## KIND` section each; `acceptance_criteria` for a verification;
`notes` for a review) or on a plan record (`plan-NN`, a child of the carrier).
Read it back with `bd show <carrier> --json | jq -r .design`, and the phase's
table with `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>`. A
`.planning/` directory, when present, is a GSD project waiting to be
imported — never a place this command writes.

What cairn adds to this verb: a UI-SPEC is a phase record with requirements
in it — screens, states, acceptance criteria — and those need issues like any
other requirement. A design contract nobody tracked is a contract nobody
ships against.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the record. When
   it is omitted, the active phase is `cairn-status.sh --json` →
   `phase.active`.

2. **Read the map and the carrier**, then **claim** the phase's ids:
   `bd update <id> --claim`.

3. **Write the UI-SPEC and record it:**
   - **Screens and states** — every screen, and for each one its loading,
     empty, error and populated states. An unlisted state is one nobody builds.
   - **Component contract** — per screen, the components it needs and the data
     each one receives.
   - **Interaction** — what responds to what, and what the response is.
   - **Accessibility floor** — keyboard path, focus order, contrast, and the
     reduced-motion behaviour.
   Written before any component: the visual direction, named — not "clean and
   modern", but a decision specific enough that two people would build the
   same thing from it.
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" ui-spec --phase "$N" <<'BODY'
   …
   BODY
   ```

4. **Every UI-SPEC requirement gets an issue**:
   Every requirement the record introduces becomes an issue, with the label
   pair and the stamp — labels use the **unpadded** number (`phase-3`, never
   `phase-03`), and the milestone is the open cycle
   (`cairn-status.sh --json` → `milestone`):
   ```bash
   bd create "<REQ-ID>: <title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   A requirement the record drops does not lose its issue in silence: close
   it with the reason (`bd close <id> --reason="dropped — <why>"`), or release
   it and leave it open when it is merely deferred
   (`bd update <id> --assignee "" --status open`). Deleting is never the answer.

5. **Refresh the map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```
   The map is printed live from bd — there is no stored copy to go stale, so
   there is nothing to `--check`. Exit `5` means bd is unavailable and
   degrades without blocking. The map's requirement-gap list is the proof the
   requirement step was complete — read it rather than assuming.

Next: `/cairn:plan <N>`.
