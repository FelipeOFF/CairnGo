---
description: Milestone lifecycle — new (roadmap + stamped issues + maps) or complete (gate → reconcile → archive → compact)
argument-hint: <new|complete>
group: loop
---

Run the milestone lifecycle under the `cairn` conventions. `$ARGUMENTS` picks
the mode; with neither `new` nor `complete`, ask which one.

## `new` — start the next milestone

1. Run `/gsd:new-milestone` — GSD updates PROJECT.md, REQUIREMENTS.md, and
   ROADMAP.md. Phase numbering is **continuous across milestones** (v1.0 ended
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
3. Generate each new phase's map:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>   # once per new phase
   ```
4. Suggest `/cairn:doctor` to confirm the wiring, then `/cairn:plan <N>`.

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
3. Run `/gsd:complete-milestone` — archives ROADMAP/REQUIREMENTS and the phase
   dirs to `.planning/milestones/v<X.Y>-phases/`. The generated
   `NN-BEADS-MAP.md` files are archived **with** their phase dirs — that is
   correct history; do not orphan-clean or regenerate them.
4. Offer semantic compaction of aged closed issues:
   `bd admin compact --analyze --json` lists candidates (~30 days closed) with
   full content. Present the findings; only on explicit user confirmation
   apply per issue: `bd admin compact --apply --id <id> --summary -` (piped
   summary). Compaction is permanent. (Top-level `bd compact` is Dolt commit
   squashing — a different tool; don't confuse them.)
5. Suggest `/cairn:milestone new` to start the next cycle.
