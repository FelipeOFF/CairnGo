---
description: Offload planning to the ultraplan cloud and import it back — GSD ultraplan-phase, and the imported PLAN gets the beads frontmatter it arrives without
argument-hint: "[phase-number]"
wraps: ultraplan-phase
implementation: inline
wrap-family: phase
---

Plan phase **$ARGUMENTS** via ultraplan, under the `cairn` conventions.

What cairn adds to this verb, and it is the sharpest gap on the
whole wrap list: **the PLAN.md comes back from the cloud without `beads:`
frontmatter.** It was written somewhere that has never heard of this
repository's issue tracker. Nothing downstream notices — `/cairn:work` simply
finds no ids to claim and executes the phase untracked. This wrapper closes
that gap in the same run as the import.


1. **Split `$ARGUMENTS`.** The bare `<N>` drives labels and the map; anything
   else shapes the artifact written below.

2. **Record the phase's ids before the round trip:**
   `bd list -l phase-<N> --all --limit 0 --json`. The imported plan will not
   mention them, so the mapping has to exist on this side.

3. **Claim** each of them: `bd update <id> --claim`.

4. **Import the plan, and complete what the external planner could not know.**

   The imported plan lands as
   `.planning/phases/<NN>-<nome>/<NN>-<MM>-PLAN.md`. An external planner does
   not know this project's tracker, so the import is **not complete** until
   three frontmatter fields are filled by hand here:

   - `beads:` — the ids this plan advances (step 5 resolves them);
   - `requirements:` — the requirement ids it closes;
   - `files_modified:` — the files it touches, so the phase's own tooling can
     cross-reference them later.

   This is precisely the gap the command exists to close: a plan that arrives
   without `beads:` looks complete and is untracked.

5. **Fill `beads:` on every imported `PLAN.md`** — the step this wrapper
   exists for. Match each plan to the ids it advances, from the mapping in
   step 3. A plan you cannot match is a signal, not a rounding error: say so
   rather than leaving the key empty.

6. **A plan the cloud invented with no issue behind it gets one**, with the
   label pair and the stamp:
   ```bash
   bd create "<title>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```
   Labels use the **unpadded** number — `phase-3`, never `phase-03`.

7. **Close only what the planning genuinely finished**
   (`bd close <id> --reason="…"`); anything the imported plan dropped is
   released and left open (`bd update <id> --assignee "" --status open`), never
   closed because a remote planner stopped mentioning it.

8. **Refresh the map** (`cairn-map.sh <N>`) and verify with `--check`.

Next: `/cairn:work <N>`.
