---
description: Generate the AI design contract (AI-SPEC.md) for a phase that builds an AI system — GSD ai-integration-phase, with its requirements tracked
argument-hint: "[phase number]"
wraps: ai-integration-phase
wrap-family: phase
---

Produce the AI contract for phase **$ARGUMENTS** under the `cairn` conventions.

What this adds over `/gsd:ai-integration-phase`: an AI-SPEC carries evaluation
criteria, not just features — and an eval nobody tracked is an eval nobody
runs. Every requirement the contract names arrives as a stamped issue in the
same run.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight ai-integration-phase
   ```
   Exit `6` or `5` **stops here** — print the script's message verbatim.

2. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else goes **only** to `/gsd:ai-integration-phase`.

3. **Claim** the phase's ids: `bd update <id> --claim`.

4. **Run `/gsd:ai-integration-phase $ARGUMENTS`.**

5. **Every AI-SPEC requirement gets an issue** — including the evaluation
   criteria, which are the ones most easily lost:
   ```bash
   bd create "<REQ-ID>: <title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`.

6. **Close what the contract settled** (`bd close <id> --reason="…"`); release
   and leave open what it deferred (`bd update <id> --assignee "" --status
   open`).

7. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check`.

Next: `/cairn:plan <N>`.
