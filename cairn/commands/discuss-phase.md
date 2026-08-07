---
description: Gather phase context before planning — GSD discuss-phase, with the phase's beads claimed and the CONTEXT reconciled against them
argument-hint: "<phase> [--all] [--auto] [--chain] [--batch] [--analyze] [--text] [--power] [--assumptions]"
wraps: discuss-phase
wrap-family: phase
---

Gather context for phase **$ARGUMENTS** under the `cairn` conventions.

What this adds over `/gsd:discuss-phase`: the CONTEXT.md it produces is what
`/cairn:plan` treats as **authoritative on divergence**. If the CONTEXT and the
phase's bd issues disagree about what the phase is, the disagreement has to be
named here, while someone is still thinking about it — not discovered at
planning time.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight discuss-phase
   ```
   Exit `6` (looked, not there) or `5` (no GSD command surface found) **stops
   here** — print the script's message verbatim; it already names what is
   missing, every path searched, and the fix. Running anyway is the silent
   exit 0 this wrapper exists to prevent.

2. **Split `$ARGUMENTS`.** The bare phase number `<N>` drives labels and the
   map; every flag (`--all`, `--auto`, `--chain`, `--batch`, `--analyze`,
   `--text`, `--power`, `--assumptions`) goes **only** to `/gsd:discuss-phase`.

3. **Read the phase's beads first**, so the discussion starts from what is
   already tracked rather than from a blank page:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   ```
   Exit `5` (bd unavailable) degrades: read the existing `*-BEADS-MAP.md`
   as-is and say so.

4. **Claim what you are about to move.** For every id on the phase's map:
   `bd update <id> --claim` — atomic, assigns and sets `in_progress` in one
   call, idempotent when already yours.

5. **Run `/gsd:discuss-phase $ARGUMENTS`** — the full arguments.

6. **Reconcile, and name every divergence.** Where the produced CONTEXT.md
   contradicts an issue, **CONTEXT wins**: flag it ⚠ outside the map's
   generated markers and `bd update` the issue to match, with a dated note
   pointing at the GSD doc. A requirement the CONTEXT introduces and no issue
   covers becomes a new issue, with the label pair and the house stamp:
   ```bash
   bd create "<title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`; strip any
   leading zero from `<N>`. The active milestone comes from ROADMAP.md's
   current milestone header, or STATE.md.

7. **Close what the discussion actually settled** —
   `bd close <id> --reason="<1–2 sentences>"`. Discussion rarely finishes an
   implementation issue: what is merely deferred is **released and left open**
   (`bd update <id> --assignee "" --status open`), never closed by giving up.
   An issue left open stays visible in `/cairn:status`; a closed one evaporates.

8. **Refresh the map** so it reflects the reconciliation: `cairn-map.sh <N>`,
   then `cairn-map.sh <N> --check` (exit `3` + diff when stale).

Next: `/cairn:plan <N>`.
