# Phase 12 — Verification

**Verified:** 2026-07-28
**Requirements:** PANEL-04, PANEL-05
**Verdict:** both met. 1 known coarseness, recorded.

## PANEL-04 — what can run in parallel, said out loud

> **Done when** the panel identifies independent phases and `/cairn:autonomous`
> surfaces the order it chose instead of deciding silently.

| Claim | Evidence |
|---|---|
| Independent phases are identified | `parallelism().runnable` is every pending phase nothing still open blocks; two or more are independent by construction, since a dependency between them would have blocked the later one |
| …and named, with the split described | Rendered: "Phases 2 and 3 are independent … `/cairn:plan 2` alongside `/cairn:plan 3`. One agent per phase, or one worktree each." Test asserts `runnable == [3, 4]`, `"independent"` and `"same time"` in the note |
| The wording does not imply a sequence | `alongside`, never `, then`. The first draft read "(`/cairn:plan 2`, then `/cairn:plan 3`)", which contradicted the sentence it was in; caught by reading the rendered output |
| One free phase is not dressed up as parallelism | Test asserts `"One phase can move"` and that `"independent"` is absent |
| An undeclared graph is reported honestly | Test asserts `declared is False` and that the note carries "No dependencies are declared" / "not a verified ordering" |
| The note reaches both surfaces | Test reads the note from `--json` and asserts it appears verbatim in the HTML and its opening clause in the wrapped terminal panel |
| `/cairn:autonomous` surfaces its order | `cairn/commands/autonomous.md` step 3 resolves phases, order and reasons from `cairn-status --json`; step 4 requires announcing the order, the per-phase reason, the available concurrency, and that the run is sequential anyway so the operator can split it |
| …including when nothing is declared | Step 4 requires saying so when `parallelism.declared` is false |

## PANEL-05 — the HTML board uses the screen it is opened on

> **Done when** the board carries the phase list, the next commands and the
> parallelism note, and its layout is verified at desktop widths.

| Claim | Evidence |
|---|---|
| The board carries the phase list | `html_phases()` renders every pending phase with number, title, requirement ids, state and what it waits on |
| …the next commands | Rendered with their reasons, the runnable one in the page's accent |
| …and the parallelism note | Rendered, taking the amber edge only when more than one phase is runnable — one moving is information, two moving is a decision |
| The layout is verified at desktop widths | Measured in a browser at 1728 / 1280 / 680 (table below), not eyeballed |

| viewport | grid width | gutters | columns | prose | h-scroll | overflow |
|---|---|---|---|---|---|---|
| 1728 | 1440 | 144 / 144 | side by side, baseline 661 | ~55ch | none | none |
| 1280 | 1126 | 77 / 77 | side by side, baseline 586 | ~55ch | none | none |
| 680 | 626 | — | stacked | ~55ch | none | none |

The fixed 1024px column was leaving the right third of a 1728px screen empty;
`clamp(1024px, 88vw, 1440px)` fills it while prose keeps its own `ch` limit, so
widening the grid does not widen the sentences.

## Test evidence

- 5 new tests in `tests/cairn-phase-model.bats`: two-runnable, single-runnable,
  undeclared-graph honesty, the note reaching both surfaces, and the JSON shape.
- Full suite run with `CAIRN_REQUIRE_GSD_VALIDATOR=1` against a pinned gsd-core.

## Known coarseness, recorded

Phase-level independence aggregates every issue edge in a phase, so a phase
holding one free issue and one blocked issue reads as blocked. True of the phase
as a whole; the issue lanes directly above carry the finer picture. Left as is
rather than papered over, because the alternative — reporting a phase as free
when part of it is not — is the failure mode that costs an hour.
