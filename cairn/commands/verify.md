---
description: Verify a phase's work — every plan record's summary checked against the code and the beads, the verdict recorded on the carrier
argument-hint: "[phase-number]"
group: loop
---

Verify phase **$ARGUMENTS**:

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

1. **Read the claim and the evidence.** The claim is the phase's records:
   ```bash
   bd show <carrier> --json | jq -r '.description, .design'      # promise, context, spec
   bd list --parent <carrier> --json                              # plan records
   bd show <plan-record> --json | jq -r '.description, .notes'    # the plan, and its summary
   ```
   The evidence is the code and the suites: for every requirement each
   summary says it delivered, name the file and the test that prove it, and
   run the relevant suite (`cairn-test.sh --jobs 8 tests/<file>.bats`). A
   summary is the claim, not the proof.

2. **Cross-check against beads:** every issue for the phase
   (`bd list -l m-<milestone>,phase-<N> --all`, the milestone from
   `cairn-status.sh --json`, unpadded number) that the work claims done
   must be **closed**, and nothing closed may lack the evidence of step 1.
   Flag any mismatch — verified but still open, or closed but not satisfied —
   and reconcile: close the issue with its reason, or reopen the work
   (`bd update <id> --status open`) and say what is missing.

3. **Record the verdict on the carrier**, one line per requirement with its
   evidence, then the suites and their counts:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" verification --phase "$N" <<'BODY'
   VERIFICADO <date>. <REQ-01> ✓ <file:test> … Suites: <file> N/N …
   BODY
   ```
   A gap the verification finds and the phase cannot close now becomes a
   tracked issue (label pair, stamp) or a backlog bead — never a sentence
   only in this record.

4. **Refresh the phase's map:**
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"`.

Next: `/cairn:ship`.
