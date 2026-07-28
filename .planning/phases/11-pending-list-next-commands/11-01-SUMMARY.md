---
phase: 11-pending-list-next-commands
plan: "01"
status: complete
requirements: [PANEL-02, PANEL-03]
beads: [CairnGo-y7m, CairnGo-nif]
---

# Phase 11 Plan 01 — Summary

The board now answers the question it never could: which phase to run, and why
that one.

## What shipped

**PANEL-02 — pending work is a described list.** Each pending phase renders as
its number, title, requirement ids, state (`not planned` / `planned` /
`executed` / `verified`), plan progress when known, and what it waits on.
Completed phases drop out. On this repo it reads:

```
PENDING PHASES  3
  10  Phase model — read what a phase actually is          verified · 1/1 plans
  11  Described pending list + next commands with…         not planned
  12  Parallelism surfaced + the board fills the screen    not planned · waits on 11
```

**PANEL-03 — next commands, with the reason for their order.**

```
NEXT COMMANDS
  /cairn:plan 11  nothing blocks it, and phase 12 waits on it
  /cairn:plan 12  waits on phase 11
```

Commands come from each phase's own state on disk, so they cannot claim a phase
needs planning after someone planned it. The order comes from the dependency
graph — free work first, phase number only breaking ties — because a blocked
phase 11 listed above a free phase 12 reads as an instruction to start with the
one that cannot start. Every entry states its reason rather than leaving the
order to be inferred. A milestone with nothing pending gets the closing pair,
`/cairn:ship` then `/cairn:milestone complete`.

Both blocks are computed once beside the model and rendered by the terminal
panel and the HTML page from the same strings, so a page left open on a second
screen cannot disagree with the shell that produced it.

## What the work turned up

**A dependency was being satisfied by the checkbox rather than by the work.**
Looking at the real board mid-phase: phase 10 was verified on disk, and phases
11 and 12 both still claimed to be waiting on it, because `blocked_by` was
computed from the roadmap tick. Now a phase counts as satisfied when it is
complete *or* verified on disk. Caught by reading the actual output, not by a
test.

**Phase 10 disappeared from the next commands and that was correct.** A phase
verified but not yet ticked has no legal next command — the work is done and
only the roadmap is behind. It stays visible in the pending list, marked
`verified`, rather than vanishing.

## Verified in a browser, measured rather than eyeballed

- No horizontal scroll at 1512px or at 680px; the two columns stack below 760px.
- Both column heads land on one baseline (546px); every phase number sits at
  258px and every title at 295px, so the list reads down a single line.
- Nothing overflows its card — the chamfered corner shaves no glyph.
- Contrast sampled from the **rendered pixel**, not the palette token: the
  painted background under the command column is `rgb(29,27,21)` rather than
  the raw `--stone-900`, giving 4.75–4.80:1 for secondary text. The token-based
  figure was 5.03, slightly optimistic; the real measurement still clears AA.

## Verification

- `bats tests/cairn-phase-model.bats` — 23 green, 9 new, including the
  cross-surface proof that the terminal and the HTML carry the same commands
  *and* the same reasons.
- `bats tests/cairn-status.bats` — unchanged board contract.

## Known coarseness, carried to phase 12

Phase-level `blocked_by` aggregates every issue edge in a phase, so a phase with
one free issue and one blocked issue reads as blocked. True of the phase as a
whole, but coarser than the issue lanes directly above it. That nuance is
phase 12's parallelism work.
