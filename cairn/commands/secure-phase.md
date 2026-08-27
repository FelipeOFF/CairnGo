---
description: Retroactively verify a completed phase's threat mitigations — the security review recorded on the carrier, and an unmitigated threat a tracked issue rather than a note
argument-hint: "[phase number]"
wraps: secure-phase
implementation: inline
wrap-family: phase
---

Verify the threat mitigations of phase **$ARGUMENTS**, under the `cairn`
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

What cairn adds to this verb: same shape as `validate-phase`, on a
**completed** phase whose issues are already closed — plus one thing specific
to security work. **An unmitigated threat recorded only as prose is the way
security findings die.** Every one of them leaves this command as a tracked
issue with an id someone can be assigned.

**This wrapper never re-opens on its own initiative.** Re-opening asserts that
finished work is unfinished; that assertion belongs to the audit.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the record; when
   omitted, the phase is the last completed one on `cairn-status.sh --json`.

2. **Record the closed set:** `bd list -l phase-<N> --all --limit 0 --json`,
   and read the phase's threat register off its plan records
   (`bd list --parent <carrier> --json`, then `bd show <record> --json`).

3. **Write the security review and record it** — appended to the carrier's
   notes, dated, so audits accumulate:
   - One row per threat in the register, with its disposition.
   - For each threat marked `mitigate`: **the evidence the mitigation is in
     the code** — file and line, not an assertion that it was handled.
   - Any surface the phase introduced that the register never named.
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" review --phase "$N" <<'BODY'
   SECURITY REVIEW <date> — …
   BODY
   ```

4. **Every unmitigated threat becomes an issue**, with the threat named in
   the title rather than "security fix", priority 1:
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

   Then claim what you will work now: `bd update <id> --claim`.

5. **If — and only if — the audit re-opened phase work**, re-open the
   matching issues: `bd update <id> --status open`, naming each and why.

6. **Close only a mitigation that is verified**
   (`bd close <id> --reason="<how it was verified>"`). "Looks fine" is not a
   verification, and a reason that does not say how it was checked is the same
   silence in different words.

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
