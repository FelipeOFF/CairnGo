# Phase 11: Described pending list + next commands with their order - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning
**Source:** Interactive autonomous run. Requirements come from a live walkthrough the operator gave, captured in `.planning/research/status-phase-panel.md`.

<domain>
## Phase Boundary

The board gains the two blocks that turn it from a snapshot into something to
act on. Requirements: PANEL-02, PANEL-03. bd issues: CairnGo-y7m, CairnGo-nif —
see `11-BEADS-MAP.md`.

Depends on phase 10: everything here renders from `phase_model()`. Phase 12
adds the parallelism note and the desktop layout.

</domain>

<decisions>
## Implementation decisions (locked)

- **Both blocks are computed in the model layer, not in a renderer.**
  `pending_phases()` and `next_commands()` sit beside `phase_model()`, so the
  terminal panel and the HTML page render the same strings. A reason written
  twice is a reason that will eventually read differently in two places.
- **Order comes from the dependency graph, never the phase number.** A blocked
  phase 11 above a free phase 12 reads as an instruction to start with the one
  that cannot start. Free work sorts first; phase number only breaks ties.
- **The reason is stated, not implied.** Every command carries why it sits
  where it does — "nothing blocks it, and phase 12 waits on it", "waits on
  phase 11" — because an order with no reason is indistinguishable from an
  arbitrary one.
- **The commands are `/cairn:*`, not `/gsd:*`.** The surface speaks the
  vocabulary the operator drives.
- **A dependency is satisfied by the work, not by the checkbox.** A phase
  verified on disk whose roadmap box nobody has ticked yet no longer keeps
  everything behind it reading "waits on 10". This was found by looking at the
  real board: phase 10 was verified and phases 11 and 12 still claimed to be
  waiting on it.
- **Blocked commands are shown, not hidden.** Knowing what comes after is the
  point of a list; they are simply set back tonally so the runnable one is
  where the eye lands.
- **An empty milestone gets the closing pair**, `/cairn:ship` then
  `/cairn:milestone complete` — the one case where the next step is not a
  phase.

</decisions>

<risks>
- Phase-level `blocked_by` aggregates every issue edge in the phase, so a phase
  with one free issue and one blocked issue reads as blocked. That is true of
  the phase as a whole (it cannot finish), but it is coarser than the issue
  lanes directly above it. Phase 12's parallelism work is where that nuance
  belongs.
</risks>
