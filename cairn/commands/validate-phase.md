---
description: Retroactively fill validation gaps on a completed phase — the verification recorded on the carrier, and any issue the audit re-opens re-opened in bd too
argument-hint: "[phase number]"
wraps: validate-phase
implementation: inline
wrap-family: phase
---

Audit and fill the validation gaps of phase **$ARGUMENTS**, under the `cairn`
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

What cairn adds to this verb: it works on a **completed** phase, whose issues
the ship gate has already closed. When the audit re-opens work, bd has to
follow — otherwise the gate keeps reading the phase as done while someone is
actively fixing it.

**This wrapper never re-opens on its own initiative.** Re-opening asserts that
finished work is unfinished, and that assertion belongs to the audit, not to
the wrapper. Every re-open below is conditional on the audit actually having
re-opened something.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the record; when
   omitted, the phase is the last completed one on `cairn-status.sh --json`.

2. **Record the closed set:** `bd list -l phase-<N> --all --limit 0 --json`,
   noting which ids are already closed. The difference after the audit is what
   step 5 acts on. Read the success criteria off the carrier (`bd show
   <carrier> --json | jq -r '.design, .acceptance_criteria'`) and its plan
   records.

3. **Write the validation record and record it** on the carrier's
   `acceptance_criteria`:
   - One row per success criterion the plan records and the SPEC named.
   - For each: **how it was checked** (the command, the file, the observation)
     and the verdict. A criterion checked by reading the summary is not
     checked — the summary is the claim, not the evidence.
   - The gaps, named individually.
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" verification --phase "$N" <<'BODY'
   …
   BODY
   ```
   An unmet criterion **re-opens its issue** (`bd update <id> --status open`);
   it does not become a note. That re-opening is the whole point of running
   this on finished work.

4. **Gaps the audit found become issues**:
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

   Then claim them: `bd update <id> --claim`.

5. **If — and only if — the audit re-opened phase work**, re-open the
   matching issues: `bd update <id> --status open`. Name each one and why. A
   phase the audit left intact gets no re-opens at all.

6. **Close what the validation actually completed**
   (`bd close <id> --reason="<1–2 sentences>"`). A gap merely recorded is not
   a gap filled: leave its issue open.

7. **Refresh and check the map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N" --check
   ```
   `--check` exits `3` with a diff when the map is stale; exit `5` means bd is
   unavailable and degrades without blocking. The map's requirement-gap list
   is the proof the requirement step was complete — read it rather than
   assuming.

Next: `/cairn:verify <N>`.
