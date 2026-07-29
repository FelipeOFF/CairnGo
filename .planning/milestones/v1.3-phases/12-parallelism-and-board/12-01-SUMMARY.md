---
phase: 12-parallelism-and-board
plan: "01"
status: complete
requirements: [PANEL-04, PANEL-05]
beads: [CairnGo-ymq, CairnGo-cj9]
---

# Phase 12 Plan 01 — Summary

The board now says what can run at the same time, and uses the screen it is
opened on.

## What shipped

**PANEL-04 — parallelism, said out loud.** `parallelism()` returns
`{runnable, blocked, declared, note}`. Two independent phases read as:

> Phases 2 and 3 are independent — nothing still open blocks any of them, so
> they can run at the same time rather than in sequence: `/cairn:plan 2`
> alongside `/cairn:plan 3`. One agent per phase, or one worktree each.

The split is described in the actual commands, and the wording never implies an
order: `alongside`, never `, then`. One runnable phase is reported as one rather
than dressed up as concurrency, and a milestone with nothing free names the
phase to finish first.

**The honesty flag matters more than the sentence.** A roadmap where nobody
registered a dependency reports every phase as free. That is a statement about
the records, not about the work, so `declared: false` appends: *"No dependencies
are declared anywhere in this roadmap, so this reflects what is recorded, not a
verified ordering."* Without it the board would send someone to run two phases
in parallel that genuinely conflict.

**`/cairn:autonomous` no longer chooses silently.** It resolves the pending
phases and their order from `cairn-status --json` instead of re-reading
ROADMAP.md, and announces the order, the reason each phase sits where it does,
and what could have run concurrently — plus that the run executes sequentially
anyway, so the operator can stop it and split the work across agents or
worktrees.

**PANEL-05 — the board fills the desktop.** `--measure` grew from a fixed
1024px to `clamp(1024px, 88vw, 1440px)`. On a 1728px screen the grid now spans
1440px with symmetric 144px gutters instead of leaving the right third empty,
while prose blocks keep their own `ch` maximum so sentences stay at ~55
characters.

## What the work turned up

**The first wording contradicted itself.** The generated sentence read "they can
run at the same time rather than in sequence (`/cairn:plan 2`, then
`/cairn:plan 3`)" — a comma-then is exactly the sequencing the sentence denies.
Caught by reading the rendered output rather than the code.

**Widening the column is not the same as filling the screen.** A grid that
tracks the viewport makes prose unreadable, so the growth is bounded and the
text blocks carry their own limit. Measured at three widths rather than assumed.

## Verification

Measured in a real browser, not eyeballed:

| viewport | grid | gutters | columns | prose | h-scroll |
|---|---|---|---|---|---|
| 1728 | 1440 | 144 / 144 | side by side, one baseline | ~55ch | none |
| 1280 | 1126 | 77 / 77 | side by side, one baseline | ~55ch | none |
| 680 | 626 | — | stacked | ~55ch | none |

Nothing in the panel exceeds the viewport at any of the three, and no child
overflows its card, so the chamfered corner shaves no glyph.

Tests: 5 new in `tests/cairn-phase-model.bats` covering the two-runnable case,
the single-runnable case, the undeclared-graph honesty case, the note reaching
both surfaces, and the JSON shape.

## Known coarseness, accepted

Phase-level independence aggregates every issue edge in a phase, so a phase
holding one free issue and one blocked issue reads as blocked. That is true of
the phase as a whole, and the issue lanes directly above carry the finer
picture. Recorded rather than papered over.
