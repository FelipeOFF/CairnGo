---
description: Replan until cross-AI review concerns are resolved — the plan records rewritten, the convergence log on the carrier, the requirement linkage re-resolved after every rewrite
argument-hint: "<phase> [--codex] [--gemini] [--claude] [--opencode] [--ollama] [--lm-studio] [--llama-cpp] [--agy] [--all] [--max-cycles N]"
wraps: plan-review-convergence
implementation: inline
wrap-family: phase
---

Converge the review of phase **$ARGUMENTS** under the `cairn` conventions.

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

What cairn adds to this verb: it **rewrites the plan records**, possibly
several times. Every rewrite can split a wave, merge two, or renumber them —
and the requirement ids a record named before the first cycle may be stale
after it. The linkage is **re-resolved after convergence**, never assumed to
have survived.

1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and records; every
   reviewer flag (`--codex`, `--gemini`, `--claude`, `--opencode`,
   `--ollama`, `--lm-studio`, `--llama-cpp`, `--agy`, `--all`,
   `--max-cycles N`) picks who reviews and how many cycles are budgeted.

2. **Record the linkage before the first cycle:** the plan records
   (`bd list --parent <carrier> --json`, label `plan-NN`) and the requirement
   ids each one names. This is the only record of the pre-convergence mapping.

3. **Claim** every requirement id in that record: `bd update <id> --claim`.

4. **Rewrite until the review closes.** Each cycle: collect the reviewers'
   concerns, change the plan, and rewrite the affected record:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" plan --phase "$N" --plan PP \
     --title "Phase <N> plan PP — <what the wave delivers>" <<'BODY'
   <REQ-IDs>. <the plan as the review left it>
   BODY
   ```
   The same `PP` replaces that record's description; a wave that splits gets
   a new `PP`. Append one row per cycle to the convergence log on the carrier:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" review --phase "$N" <<'BODY'
   Cycle <k> — <concern> — <change> — <open|closed>
   BODY
   ```
   Convergence is declared when **every blocking concern is closed**, never
   by reaching a cycle count. A cycle that ends with an open blocking concern
   and an exhausted budget stops and says so — it does not declare success.

5. **Re-resolve the requirement linkage on every record that now exists** —
   a fresh resolution, not a diff against step 2. A wave that was split
   inherits the ids that match its remaining scope; a wave that absorbed
   another names both. An id from step 2 that lands nowhere is **reported**,
   never quietly dropped: converging a review does not finish work.

6. **A concern the review raised that no issue covers becomes one**:
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

7. **Close only what convergence settled** (`bd close <id> --reason="…"`);
   release and leave open anything the cycles deferred
   (`bd update <id> --assignee "" --status open`).

8. **Refresh the map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```
   The map is printed live from bd — there is no stored copy to go stale, so
   there is nothing to `--check`. Exit `5` means bd is unavailable and
   degrades without blocking. The map's requirement-gap list is the proof the
   requirement step was complete — read it rather than assuming.

Next: `/cairn:work <N>`.
