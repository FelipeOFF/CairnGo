---
description: Clarify WHAT a phase delivers, with ambiguity scoring — GSD spec-phase, and every requirement the SPEC names gets a stamped issue
argument-hint: "<phase> [--auto] [--text]"
wraps: spec-phase
wrap-family: phase
---

Produce the SPEC for phase **$ARGUMENTS** under the `cairn` conventions.

What this adds over `/gsd:spec-phase`: a SPEC gives the phase a **requirements
surface**, and in cairn a requirement without an issue is untracked work. The
SPEC's requirements arrive as bd issues carrying the label pair and the stamp,
in the same run that produced them.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight spec-phase
   ```
   Exit `6` or `5` **stops here** — print the script's message verbatim. It
   names what is missing, where it looked, and the fix. Do not run anyway.

2. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; `--auto`
   and `--text` go **only** to `/gsd:spec-phase`.

3. **Claim the phase's existing work** before writing over the shape of it:
   for every id on the phase's map, `bd update <id> --claim` (atomic: assigns
   and sets `in_progress`).

4. **Run `/gsd:spec-phase $ARGUMENTS`.**

5. **Turn the SPEC's requirements into issues.** For each requirement id the
   SPEC introduces that has no issue:
   ```bash
   bd create "<REQ-ID>: <title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`. The
   `metadata.gsd.req` stamp is what `cairn-map` keys the requirement table on;
   an issue without it lands in the map's "issues without a requirement" gap
   list instead of a row.

6. **A requirement the SPEC drops** does not lose its issue silently: close it
   with the reason (`bd close <id> --reason="dropped by SPEC — <why>"`), or
   release it and leave it open when it is merely deferred
   (`bd update <id> --assignee "" --status open`). Deleting is never the answer.

7. **Refresh and check the map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N" --check
   ```
   `--check` exits `3` with a diff when the map is stale; exit `5` means bd is
   unavailable and degrades without blocking. The map's requirement-gap list is
   the proof that step 5 was complete — read it rather than assuming.

Next: `/cairn:discuss-phase <N>`, then `/cairn:plan <N>`.
