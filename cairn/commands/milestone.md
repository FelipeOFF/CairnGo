---
description: Milestone lifecycle — new (roadmap + stamped issues + maps) or complete (gate → reconcile → archive → compact)
argument-hint: <new|complete>
group: loop
---

Run the milestone lifecycle under the `cairn` conventions. `$ARGUMENTS` picks
the mode; with neither `new` nor `complete`, ask which one.

## `new` — start the next milestone

1. **Agree the cycle with the user, and write it to the tracker — not to a
   document.** A milestone is its requirements, its phases and their order;
   all three are bd issues, and none of them is a file. Ask what the cycle is
   for, what it must deliver, and how the work splits into phases. Then go
   straight to step 2 — there is no document to edit first.

   Phase numbering is **continuous across milestones** (v1.0 ended at phase 5
   → v1.1 starts at phase 6) — never restart at 1. Read the last number used
   from the tracker, not from a roadmap:

   ```bash
   bd list --all --limit 0 --json \
     | jq -r '[.[].labels[]? | select(startswith("phase-")) | ltrimstr("phase-") | tonumber] | max'
   ```

   Give each phase a **carrier**: one bead with the label pair and NO
   `gsd.req`, no `plan-NN`, no parent suffix. Its title is the phase's name
   and its description is what the phase promises — that bead is what
   inherited the roadmap checkbox, and `/cairn:status`, `cairn-gate` and the
   corroboration all read it. A phase without a carrier has no name, and the
   board says so rather than borrowing a requirement's title.

   Give the **milestone** a carrier too — always, with or without an
   external tracker. It is one bead with the marker label `milestone` and
   the `m-<new-milestone>` label, **no** `phase-N`, no `gsd` stamp; its
   title is the cycle's name and its description is the cycle's promise:

   ```bash
   bd create "<cycle name>" -t task -l m-<new-milestone>,milestone \
     -d "<what this cycle promises>"
   ```

   Until it exists the cycle has no name, no promise and nowhere to hang an
   outside link (`external_ref` is a field of this bead, filled in by the
   Jira link when there is one). `/cairn:doctor` reports an open cycle
   without one; `/cairn:status` reads the header from it; `complete` closes
   it last, after the gate passes. The label chosen here is the **intent** —
   the final version is decided at close, and `complete` renames the whole
   cycle when they diverge.

   **A `.planning/` still waiting to be imported is the exception, and the
   only one.** If this repo has one, it is the INPUT of a GSD that has not
   been migrated yet: run `/cairn:migrate` first, and open the cycle after —
   never edit those documents to open a milestone, because the import is what
   makes them history.
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
3. **Decide the final version, then close the cycle's own bead.** The
   label chosen at `new` was the intent; the version that ships is decided
   here, by the CHANGELOG's contract criterion (a contract change is a
   major, a new surface a minor, the rest a patch). Ask the user for it,
   then let the script turn the answer into bd writes:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-bookkeep.sh" milestone --release <X.Y.Z>
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-bookkeep.sh" milestone --release <X.Y.Z> --apply
   ```
   Read mode names the writes and exits 3: a `cairn-relabel rename` of the
   whole cycle when `m-vX.Y` differs from the open label (every bead, the
   carrier's title included — `.cairn/id-map.json`, branches and the journal
   are reported, not touched), then `bd close <carrier> --reason "release
   X.Y.Z"`. Exit 6 is a refusal with ids: a non-closed bead of the cycle
   other than the carrier — back to step 2. Exit 4 means the cycle has no
   carrier, or two; `/cairn:doctor`'s `milestone-carrier` check says which.

   **In a tracker-owned repo there is nothing to archive** — the closed beads
   ARE the archive, queryable by `bd list -l m-<X.Y> --all` forever. Run
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-bookkeep.sh"`; where the
   planning documents do not exist it reports `documents: not-applicable /
   out-of-scope` and exits 0, which is the correct answer and not a skipped
   step.

   **Only a repo that still carries an unimported `.planning/` has anything to
   move**: its `ROADMAP`/`REQUIREMENTS` and phase dirs go to
   `.planning/milestones/v<X.Y>-phases/`, whole — that is correct history for
   documents that were the input. With a GSD plugin installed alongside cairn,
   `/cairn:gsd complete-milestone` runs the upstream workflow for that case.
4. Offer semantic compaction of aged closed issues:
   `bd admin compact --analyze --json` lists candidates (~30 days closed) with
   full content. Present the findings; only on explicit user confirmation
   apply per issue: `bd admin compact --apply --id <id> --summary -` (piped
   summary). Compaction is permanent. (Top-level `bd compact` is Dolt commit
   squashing — a different tool; don't confuse them.)
5. Suggest `/cairn:milestone new` to start the next cycle.
