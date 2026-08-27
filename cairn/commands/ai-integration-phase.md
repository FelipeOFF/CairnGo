---
description: Record the AI design contract for a phase that builds an AI system — the AI-SPEC on the phase carrier, with its requirements and evals tracked
argument-hint: "[phase number]"
wraps: ai-integration-phase
implementation: inline
wrap-family: phase
---

Produce the AI contract for phase **$ARGUMENTS** under the `cairn` conventions.

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

What cairn adds to this verb: an AI-SPEC carries evaluation criteria, not
just features — and an eval nobody tracked is an eval nobody runs. Every
requirement the contract names arrives as a stamped issue in the same run.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the record.

2. **Read the map and the carrier**, then **claim** the phase's ids:
   `bd update <id> --claim`.

3. **Write the AI-SPEC and record it:**
   - **The task** — what the model does, stated as an input/output contract.
   - **Evaluation** — the eval set (where it lives, how many cases) and the
     pass bar **as a number**. "Works well" is not a bar.
   - **Failure modes** — what the model gets wrong, and the fallback for each.
     A path with no fallback is an outage waiting for traffic.
   - **Budget** — cost and latency ceilings, per call and per run.
   Written before the first prompt: what "good enough" is, numerically.
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" ai-spec --phase "$N" <<'BODY'
   …
   BODY
   ```

4. **Every AI-SPEC requirement gets an issue** — including the evaluation
   criteria, which are the ones most easily lost:
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
