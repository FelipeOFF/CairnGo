---
description: Gather phase context before planning — the decisions recorded on the phase carrier, and the phase's beads reconciled against them
argument-hint: "<phase> [--auto] [--assumptions]"
wraps: discuss-phase
wrap-family: phase
implementation: inline
---

Gather context for phase **$ARGUMENTS** under the `cairn` conventions.

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

What this verb settles is what `/cairn:plan` then treats as **authoritative
on divergence**: if the context and the phase's beads disagree about what the
phase is, the disagreement is named here, while someone is still thinking
about it — not discovered at planning time.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the record;
   `--auto` answers every gray area with a sensible default recorded as
   *Claude's Discretion*, `--assumptions` lists the assumptions the phase
   rests on before asking anything.

2. **Read the phase's beads first**, so the discussion starts from what is
   already tracked rather than from a blank page:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   bd show <carrier> --json | jq -r '.description, .design'
   ```
   Exit `5` (bd unavailable) stops here — the record has nowhere to go.

3. **Find the facts yourself, then put the decisions to the user.** A gray
   area whose answer lives in the code (a file, a measured output, a current
   behaviour) is yours to look up, never the user's to guess. What remains
   is a decision, and each one goes to the user as one `AskUserQuestion` —
   a recommended option first, the trade-off in each description. Under
   `--auto`, skip the questions and record the recommendation as the
   decision, marked *Claude's Discretion*.

4. **Claim what you are about to move:** for every id on the map,
   `bd update <id> --claim`.

5. **Record the context on the carrier** — what exists today (measured, with
   sites), the decisions (`D-nn` by the user, `C-nn` by Claude, each with its
   reason), and the waves the plan will cut:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" context --phase "$N" <<'BODY'
   …
   BODY
   ```
   It writes the `## CONTEXT` section of the carrier's `design` and leaves
   every other section (`## RESEARCH`, `## SPEC`…) as it was.

6. **Reconcile, and name every divergence.** Where the recorded context
   contradicts a bead, **the context wins**: `bd update` the bead to match,
   with a dated note. A requirement the context introduces and no bead covers
   becomes one:
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

7. **Close what the discussion actually settled** —
   `bd close <id> --reason="<1–2 sentences>"`. Discussion rarely finishes an
   implementation issue: what is merely deferred is **released and left open**
   (`bd update <id> --assignee "" --status open`), never closed by giving up.

8. **Refresh the map** so it reflects the reconciliation:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```
   The map is printed live from bd — there is no stored copy to go stale, so
   there is nothing to `--check`. Exit `5` means bd is unavailable and
   degrades without blocking. The map's requirement-gap list is the proof the
   requirement step was complete — read it rather than assuming.

Next: `/cairn:plan <N>`.
