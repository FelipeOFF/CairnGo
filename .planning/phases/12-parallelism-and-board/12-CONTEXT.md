# Phase 12: Parallelism surfaced + the board fills the screen - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning
**Source:** Interactive autonomous run. Both requirements come from the operator's live walkthrough (`.planning/research/status-phase-panel.md`), including the complaint that the board leaves its space empty on a desktop.

<domain>
## Phase Boundary

The panel says out loud what can proceed at the same time, and the page uses the
screen it is opened on. Requirements: PANEL-04, PANEL-05. bd issues:
CairnGo-ymq, CairnGo-cj9 — see `12-BEADS-MAP.md`.

Depends on phases 10 and 11: the graph and the panel already exist; this adds
the concurrency statement and the desktop layout.

</domain>

<decisions>
## Implementation decisions (locked)

- **"Independent" is a claim about what is recorded, and it says so.** A
  roadmap where nobody registered a dependency reports every phase as free.
  That is a statement about the records, not about the work, so the note
  carries `declared: false` and spells it out rather than letting the reader
  take it for a verified ordering. Overclaiming here is worse than saying
  less: it would send someone to run two phases in parallel that genuinely
  conflict.
- **The wording never implies a sequence.** `alongside`, never `, then` — the
  entire point of the sentence is that these do not have to be ordered.
- **The accent is spent only when there is a choice.** One phase moving is
  information; two moving at once is a decision, and only that case takes the
  amber edge.
- **`/cairn:autonomous` reads the model instead of re-deriving it.** It now
  resolves the order from `cairn-status --json` and **announces** the order,
  the reason for each position and what could have run concurrently — plus the
  fact that the run executes sequentially anyway, so the operator can stop it
  and split the work. An order chosen silently is an order nobody can disagree
  with before it costs an hour.
- **The measure grows on a desktop, but is bounded.** A fixed 1024px column
  left the right third of a 1728px screen empty; a column that tracks the
  viewport becomes unreadable. `clamp(1024px, 88vw, 1440px)` for the grid,
  with prose blocks keeping their own `ch` maximum on top, so the layout
  spreads while the sentences stay at ~55 characters.

</decisions>

<risks>
- Phase-level independence is coarser than issue-level: a phase holding one
  free issue and one blocked issue reads as blocked. True of the phase as a
  whole, and the lanes above it carry the finer picture, but a reader could
  take the phase note as the last word. Accepted rather than papered over.
</risks>
