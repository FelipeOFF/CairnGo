---
description: Generate the AI design contract (AI-SPEC.md) for a phase that builds an AI system — GSD ai-integration-phase, with its requirements tracked
argument-hint: "[phase number]"
wraps: ai-integration-phase
implementation: inline
wrap-family: phase
---

Produce the AI contract for phase **$ARGUMENTS** under the `cairn` conventions.

What cairn adds to this verb: an AI-SPEC carries evaluation
criteria, not just features — and an eval nobody tracked is an eval nobody
runs. Every requirement the contract names arrives as a stamped issue in the
same run.


1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else shapes the artifact written below.

2. **Claim** the phase's ids: `bd update <id> --claim`.

3. **Write the AI-SPEC.**

   The deliverable is `.planning/phases/<NN>-<nome>/<NN>-AI-SPEC.md`:

   - **The task** — what the model does, stated as an input/output contract.
   - **Evaluation** — the eval set (where it lives, how many cases) and the
     pass bar **as a number**. "Works well" is not a bar.
   - **Failure modes** — what the model gets wrong, and the fallback for each.
     A path with no fallback is an outage waiting for traffic.
   - **Budget** — cost and latency ceilings, per call and per run.

   Written before the first prompt: what "good enough" is, numerically. A
   system whose success criterion is written after the results is measuring
   nothing.

4. **Every AI-SPEC requirement gets an issue** — including the evaluation
   criteria, which are the ones most easily lost:
   ```bash
   bd create "<REQ-ID>: <title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`.

5. **Close what the contract settled** (`bd close <id> --reason="…"`); release
   and leave open what it deferred (`bd update <id> --assignee "" --status
   open`).

6. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check`.

Next: `/cairn:plan <N>`.
