---
description: Plan a phase as a vertical MVP slice — the plan recorded on beads, the tracer wave first, and the map reconciled
argument-hint: "<phase-number>"
wraps: mvp-phase
implementation: inline
wrap-family: phase
---

Plan phase **$ARGUMENTS** as a vertical MVP slice, under the `cairn`
conventions.

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

What cairn adds to this verb: the SPIDR split produces slices that do not map
one-to-one onto the phase's existing issues — that divergence gets named here
rather than found at execution time, and every slice is a plan record
`/cairn:work` can claim and close.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and records.

2. **Read the map and the carrier first** (`cairn-map.sh <N>`, `bd show
   <carrier> --json | jq -r '.description, .design'`), so the slicing starts
   from the tracked work rather than from scratch. No `## CONTEXT` → run
   `/cairn:discuss-phase <N>` first.

3. **Claim.** For every id on the map: `bd update <id> --claim`.

4. **Cut the slice, and record it as plan records.** The **tracer wave comes
   first** — one thin path that crosses every layer end to end and is
   production quality, never a throwaway; every wave after it expands the
   slice, nothing before it exists. Each record names the requirement ids it
   advances and, per task, the check that fails if the task is not done:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" plan --phase "$N" --plan 01 \
     --title "Phase <N> plan 01 — the tracer" <<'BODY'
   <REQ-IDs>. Which layer is the thinnest honest slice, and why that one…
   BODY
   ```
   A plan that stacks layers instead of crossing them is the failure this
   command exists to prevent.

5. **A slice with no issue gets one**:
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

6. **Work the MVP defers is released, not closed.** A slice pushed out of the
   MVP is still real: `bd update <id> --assignee "" --status open` keeps it in
   `/cairn:status`'s ready lane. Use `bd close <id> --reason="…"` only for what
   the slicing genuinely finished or genuinely killed.

7. **Refresh and check the map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N" --check
   ```
   `--check` exits `3` with a diff when the map is stale; exit `5` means bd is
   unavailable and degrades without blocking. The map's requirement-gap list
   is the proof the requirement step was complete — read it rather than
   assuming.

Next: `/cairn:work <N>`.
