---
description: Plan a phase — context, research and one plan record per wave, all on beads
argument-hint: <phase-number> [--research|--skip-research] [--tdd]
group: loop
---

Plan phase **$ARGUMENTS** under the `cairn` conventions.

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

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and records;
   `--research` forces a research pass, `--skip-research` skips it, `--tdd`
   asks every wave to name its failing test first.

2. **Read what is already tracked** before deciding anything:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   bd show <carrier> --json | jq -r '.description, .design'
   ```
   The map gives the requirements and their ids; the carrier's description is
   the phase's promise and its `design` holds every record already made
   (`## CONTEXT`, `## RESEARCH`, `## SPEC`…). Exit `5` from the map means bd
   is unavailable — say so and stop; there is no file to fall back on.

3. **Context first, when there is none.** No `## CONTEXT` section → the
   phase has not been discussed: run the discussion (`/cairn:discuss-phase
   <N>`, in this same session) or, when the run is non-interactive, resolve
   the gray areas yourself and record them as *Claude's Discretion*:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" context --phase "$N" <<'BODY'
   …what is known, what was decided (D-nn by the user, C-nn by Claude), and why…
   BODY
   ```

4. **Research what the plan depends on** — `--research`, or any requirement
   whose implementation site you cannot name from the map alone. Measure the
   code (file and line, the command's real output), never the description of
   it, and record it:
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" research --phase "$N"`
   (body on stdin). Skip it only when `--skip-research` was given or every
   requirement already names its site.

5. **Claim** the phase's work you are about to shape: for every id on the map,
   `bd update <id> --claim` (atomic: assigns and sets `in_progress`,
   idempotent when already yours).

6. **Cut the phase into waves, one plan record each.** A wave is the unit
   `/cairn:work` executes and closes: a coherent set of requirements that
   ship together and can be verified together. For each wave `PP` (`01`,
   `02`, …), write the plan and record it — the body **names the requirement
   ids it advances** (`CARRY-01`, `LINK-02`…), because that name is the link
   `/cairn:work` resolves to bead ids through the map; a plan naming no
   requirement is a plan nothing can claim or close:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" plan --phase "$N" --plan PP \
     --title "Phase <N> plan PP — <what the wave delivers>" <<'BODY'
   <REQ-IDs>. <what changes, where (files), how it is verified, what is out>
   BODY
   ```
   Recording the same `--plan PP` again rewrites that record's description;
   a new `PP` opens a new one. Under `--tdd`, each wave's body names the
   test that fails before the change and passes after.

7. **Reconcile.** Where a bead contradicts the recorded context, the
   **context wins**: `bd update` the bead to match, with a dated note
   pointing at the record. A requirement the plan needs and no bead covers
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

8. **Refresh the map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```
   The map is printed live from bd — there is no stored copy to go stale, so
   there is nothing to `--check`. Exit `5` means bd is unavailable and
   degrades without blocking. The map's requirement-gap list is the proof the
   requirement step was complete — read it rather than assuming.

Next: `/cairn:work <N>`.
