---
description: Milestone lifecycle — new (roadmap + stamped issues + maps) or complete (gate → reconcile → archive → compact)
argument-hint: <new|complete>
group: loop
---

Run the milestone lifecycle under the `cairn` conventions. `$ARGUMENTS` picks
the mode; with neither `new` nor `complete`, ask which one.

## `new` — start the next milestone

1. Update PROJECT.md, REQUIREMENTS.md and ROADMAP.md for the new cycle.
   **cairn does not vendor `new-milestone`** — v1.6 vendored the four cycle
   verbs and nothing else. With a GSD plugin installed alongside cairn, the
   declared passthrough runs it: `/cairn:gsd new-milestone`. Without one, do
   the edit yourself, with the user: the new milestone's requirements in
   REQUIREMENTS.md, its phases appended to ROADMAP.md, and PROJECT.md's current
   focus moved. Phase numbering is **continuous across milestones** (v1.0 ended
   at phase 5 → v1.1 starts at phase 6) — never restart at 1.
2. Apply the issue creation convention to the new milestone's requirements —
   **dedup key check first**: an issue with the same `(gsd.req, gsd.milestone)`
   already exists (e.g. carried over during `complete`) → update it, never
   duplicate. Otherwise:
   ```bash
   bd create "CAT-NN: <requirement title>" \
     -l m-<new-milestone>,phase-<N> \
     --metadata '{"gsd": {"req": "CAT-NN", "phase": N, "milestone": "vX.Y"}}'
   ```
   Capture roadmap-implied ordering with `bd dep add`.
3. **Nothing to generate here, and nothing that can fail.** Until v1.7 this
   step was a prohibition: the map was written into the phase's own directory,
   the directories were born in `/cairn:plan <N>`, and asking for a map at
   milestone-open time failed for every phase (measured when v1.4 opened: 5 of
   5; confirmed when v1.5 opened, `cairn-map.sh 20` → exit `4`). The map is a
   printed view of bd now — a phase is a label, not a folder — so
   `cairn-map.sh <N>` answers at any moment, including this one.
4. Suggest `/cairn:doctor` to confirm the wiring, then `/cairn:plan <N>` —
   which is where each phase gets its directory, its plan and its map.

## `complete` — close out the current milestone

1. Deterministic gate first:
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-gate.sh"` — every completed
   phase must be clean; any non-closed issue blocks (exit 6 lists the ids;
   exit 5 = bd unavailable, check by hand per `/cairn:ship`). **Stop** until
   the gate passes or step 2 resolves the stragglers.
2. Reconcile stragglers **with the user** — per non-closed issue, close or
   carry over:
   - close: `bd close <id> --reason="<why it's done or dropped>"`
   - carry to the next milestone: swap the label pair
     (`bd update <id> --remove-label m-<old>,phase-<N> --add-label m-<new>`
     — the new phase label lands when `new` places it in the next roadmap)
     and update the stamp by the read-modify-write rule: `bd update
     --metadata` replaces the whole `gsd` object, so read it from
     `bd show <id> --json`, change only `milestone`, write the full object
     back. The dedup key then makes `new` update this issue, not duplicate it.
     Until `new` re-adds a phase label, `/cairn:doctor` shows the carried
     issue as a transient orphan warn — expected; it clears when the next
     milestone's roadmap places it.
3. Archive the cycle. **cairn does not vendor `complete-milestone`**; the
   deterministic half is `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-bookkeep.sh"`
   plus moving ROADMAP/REQUIREMENTS and the phase dirs to
   `.planning/milestones/v<X.Y>-phases/`. With a GSD plugin installed
   alongside cairn, `/cairn:gsd complete-milestone` runs the upstream workflow
   instead. Phase dirs are archived whole — that is correct history.
4. Offer semantic compaction of aged closed issues:
   `bd admin compact --analyze --json` lists candidates (~30 days closed) with
   full content. Present the findings; only on explicit user confirmation
   apply per issue: `bd admin compact --apply --id <id> --summary -` (piped
   summary). Compaction is permanent. (Top-level `bd compact` is Dolt commit
   squashing — a different tool; don't confuse them.)
5. Suggest `/cairn:milestone new` to start the next cycle.
