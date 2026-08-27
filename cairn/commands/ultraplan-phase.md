---
description: Offload planning to the ultraplan cloud and import it back — the imported plan lands as plan records that name the requirements they advance
argument-hint: "[phase-number]"
wraps: ultraplan-phase
implementation: inline
wrap-family: phase
---

Plan phase **$ARGUMENTS** via ultraplan, under the `cairn` conventions.

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

What cairn adds to this verb, and it is the sharpest gap on the whole wrap
list: **the plan comes back from the cloud knowing nothing about this
tracker.** Imported as it arrives, `/cairn:work` would find no requirement to
claim and execute the phase untracked. This wrapper closes that gap in the
same run as the import.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and records.

2. **Record the phase's ids before the round trip:**
   `bd list -l phase-<N> --all --limit 0 --json`, and read the carrier
   (`bd show <carrier> --json`). The imported plan will not mention them, so
   the mapping has to exist on this side.

3. **Claim** each of them: `bd update <id> --claim`.

4. **Send the phase out with its record, and import what comes back as plan
   records.** The cloud planner receives the carrier's promise, its `design`
   and the map; each plan it returns becomes one record:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" plan --phase "$N" --plan PP \
     --title "Phase <N> plan PP — <what the wave delivers>" <<'BODY'
   <REQ-IDs>. <the imported plan, verbatim where it is right>
   BODY
   ```
   The import is **not complete** until every record names the requirement
   ids it advances — the step this wrapper exists for. Match each plan to
   the ids from step 2; a plan you cannot match is a signal, not a rounding
   error: say so rather than recording it unlinked.

5. **A plan the cloud invented with no issue behind it gets one**:
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

6. **Close only what the planning genuinely finished**
   (`bd close <id> --reason="…"`); anything the imported plan dropped is
   released and left open (`bd update <id> --assignee "" --status open`), never
   closed because a remote planner stopped mentioning it.

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
