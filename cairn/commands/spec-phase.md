---
description: Clarify WHAT a phase delivers, with ambiguity scoring — GSD spec-phase, and every requirement the SPEC names gets a stamped issue
argument-hint: "<phase> [--auto] [--text]"
wraps: spec-phase
implementation: inline
wrap-family: phase
---

Produce the SPEC for phase **$ARGUMENTS** under the `cairn` conventions.

What cairn adds to this verb: a SPEC gives the phase a **requirements
surface**, and in cairn a requirement without an issue is untracked work. The
SPEC's requirements arrive as bd issues carrying the label pair and the stamp,
in the same run that produced them.


1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; `--auto`
   and `--text` shape the artifact written below.

2. **Claim the phase's existing work** before writing over the shape of it:
   for every id on the phase's map, `bd update <id> --claim` (atomic: assigns
   and sets `in_progress`).

3. **Write the SPEC.**

   The deliverable is `.planning/phases/<NN>-<nome>/<NN>-SPEC.md`, and it
   answers WHAT the phase delivers, never HOW:

   - **Delivers** — the observable behaviour, one bullet per outcome someone
     outside the code could confirm.
   - **Requirements** — the ids this SPEC introduces (`<PREFIX>-01`, …), one
     line each. These are what step 4 turns into issues.
   - **Ambiguity** — a score per requirement (`clear` / `needs a decision`)
     and, for every one that is not `clear`, the single question that would
     settle it. An unscored requirement is the defect this artifact exists to
     catch.
   - **Out of scope** — what the phase deliberately does not deliver, so the
     boundary is written rather than remembered.

   A requirement whose ambiguity is still open when the SPEC is written gets
   the decision recorded inline, with who decided and on what basis.

4. **Turn the SPEC's requirements into issues.** For each requirement id the
   SPEC introduces that has no issue:
   ```bash
   bd create "<REQ-ID>: <title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`. The
   `metadata.gsd.req` stamp is what `cairn-map` keys the requirement table on;
   an issue without it lands in the map's "issues without a requirement" gap
   list instead of a row.

5. **A requirement the SPEC drops** does not lose its issue silently: close it
   with the reason (`bd close <id> --reason="dropped by SPEC — <why>"`), or
   release it and leave it open when it is merely deferred
   (`bd update <id> --assignee "" --status open`). Deleting is never the answer.

6. **Refresh and check the map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N" --check
   ```
   `--check` exits `3` with a diff when the map is stale; exit `5` means bd is
   unavailable and degrades without blocking. The map's requirement-gap list is
   the proof that step 5 was complete — read it rather than assuming.

Next: `/cairn:discuss-phase <N>`, then `/cairn:plan <N>`.
