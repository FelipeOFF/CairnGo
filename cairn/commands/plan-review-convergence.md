---
description: Replan until cross-AI review concerns are resolved — GSD plan-review-convergence, with the beads linkage re-resolved after every rewrite
argument-hint: "<phase> [--codex] [--gemini] [--claude] [--opencode] [--ollama] [--lm-studio] [--llama-cpp] [--agy] [--text] [--ws <name>] [--all] [--max-cycles N]"
wraps: plan-review-convergence
wrap-family: phase
---

Converge the review of phase **$ARGUMENTS** under the `cairn` conventions.

What this adds over `/gsd:plan-review-convergence`: it **rewrites PLAN.md**,
possibly several times. Every rewrite can split a plan, merge two, or renumber
them — and the `beads:` frontmatter written before the first cycle is stale
after it. The linkage must be **re-resolved after convergence**, never assumed
to have survived.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight plan-review-convergence
   ```
   Exit `6` or `5` **stops here** — print the script's message verbatim.

2. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; every
   reviewer flag (`--codex`, `--gemini`, `--claude`, `--opencode`, `--ollama`,
   `--lm-studio`, `--llama-cpp`, `--agy`, `--text`, `--ws <name>`, `--all`,
   `--max-cycles N`) goes **only** to `/gsd:plan-review-convergence`.

3. **Record the linkage before the first cycle:** for each `NN-MM-PLAN.md`,
   the ids currently in its `beads:` key. This is the only record of the
   pre-convergence mapping.

4. **Claim** every id in that record: `bd update <id> --claim`.

5. **Run `/gsd:plan-review-convergence $ARGUMENTS`.**

6. **Re-resolve `beads:` on every plan that now exists** — not a diff against
   step 3, a fresh resolution. A plan that was split inherits the ids that
   match its remaining scope; a plan that absorbed another carries both. An id
   from step 3 that lands nowhere is **reported**, never quietly dropped:
   converging a review does not finish work.

7. **A concern the review raised that no issue covers becomes one**, with the
   label pair and the stamp:
   ```bash
   bd create "<title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`.

8. **Close only what convergence settled** (`bd close <id> --reason="…"`);
   release and leave open anything the cycles deferred
   (`bd update <id> --assignee "" --status open`).

9. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check`.

Next: `/cairn:work <N>`.
