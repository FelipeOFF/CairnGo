---
description: Clarify WHAT a phase delivers, with ambiguity scoring — the SPEC recorded on the phase carrier, and every requirement it names a stamped issue
argument-hint: "<phase> [--auto]"
wraps: spec-phase
implementation: inline
wrap-family: phase
---

Produce the SPEC for phase **$ARGUMENTS** under the `cairn` conventions.

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

What cairn adds to this verb: a SPEC gives the phase a **requirements
surface**, and in cairn a requirement without an issue is untracked work. The
SPEC's requirements arrive as bd issues carrying the label pair and the stamp,
in the same run that produced them.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the record;
   `--auto` settles every open ambiguity with a recorded default instead of a
   question.

2. **Read what is tracked** (`cairn-map.sh <N>`, `bd show <carrier> --json`),
   then **claim** the phase's existing work before writing over the shape of
   it: for every id on the map, `bd update <id> --claim`.

3. **Write the SPEC and record it.** It answers WHAT the phase delivers,
   never HOW:
   - **Delivers** — the observable behaviour, one bullet per outcome someone
     outside the code could confirm.
   - **Requirements** — the ids this SPEC introduces (`<PREFIX>-01`, …), one
     line each. These are what step 4 turns into issues.
   - **Ambiguity** — a score per requirement (`clear` / `needs a decision`)
     and, for every one that is not `clear`, the single question that would
     settle it — asked now (`AskUserQuestion`), or under `--auto` answered
     with a default recorded inline, with who decided and on what basis.
   - **Out of scope** — what the phase deliberately does not deliver.
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" spec --phase "$N" <<'BODY'
   …
   BODY
   ```
   (the `## SPEC` section of the carrier's `design`; the context stays.)

4. **Turn the SPEC's requirements into issues** — for each requirement id
   the SPEC introduces that has no issue:
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

5. **Refresh and check the map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N" --check
   ```
   `--check` exits `3` with a diff when the map is stale; exit `5` means bd is
   unavailable and degrades without blocking. The map's requirement-gap list
   is the proof the requirement step was complete — read it rather than
   assuming.

Next: `/cairn:discuss-phase <N>`, then `/cairn:plan <N>`.
