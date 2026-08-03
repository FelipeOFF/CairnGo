---
phase: 14-phase-card
plan: "02"
subsystem: cli
tags: [python, cairn-status, html, terminal-rendering]

requires:
  - phase: 14-phase-card plan 01
    provides: "phases[].purpose / research_done / issues_done+issues_total / verify_status"
provides:
  - "phase_purpose_text()/phase_research_text()/phase_issues_text()/phase_verify_text() — the four shared render helpers both surfaces call"
  - "phase_panel_lines() rewritten to the D-01/D-02 table + PURPOSE layout, with no NEXT COMMANDS section"
  - "html_phases() mirroring purpose/research/issues/verify in the same `<li>`"
  - "a cross-surface parity test (tests/cairn-phase-card.bats) that extracts from --json and greps both terminal and HTML renders"
affects: ["14-03 (phase card follow-on, if any)", "future cairn-status.py rendering work"]

tech-stack:
  added: []
  patterns:
    - "Two-pass table rendering: gather every row's untruncated content first, then size the one variable-width column (`state`) from the actual per-render maximum before any row is truncated or printed — the header sub-row is built from the same width variables so header and data can never drift apart"
    - "A single non-branching width formula (`state_w = max(floor, min(natural_max, cap))`) handles both the narrow-terminal degrade case and the wide-terminal exact-fit case with no special-casing"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-status.py
    - cairn/templates/status-board.html
    - tests/cairn-phase-card.bats
    - tests/cairn-phase-model.bats

key-decisions:
  - "PURPOSE section is guarded on `pending or global_cmds`, never on `pending` alone — this is the fix for the exact bug the plan-checker flagged: gating on `pending` would silently drop /cairn:ship and /cairn:milestone complete from the terminal in the all-complete case, while --json and HTML kept them"
  - "The `state` table column's width is computed dynamically per render from the actual maximum untruncated row content (capped so `phase` never collapses), rather than a fixed constant — this is what lets a ~76-cell conflict detail render whole at --width 200/240 while a short 'not planned' still fits at --width 100, from one formula with no per-case branching"
  - "VERIFY_W bumped from the plan's 12-cell starting point to 16 cells so a realistic verify_status value ('needs-revision', 14 chars) renders whole in the terminal at a normal width — caught by the new parity test itself, not asserted blind"
  - "PLANS_W/ISSUES_W/WAITS_W/NEXT_W kept close to the plan's starting-point numbers since no pre-existing test asserts their exact content at narrow widths; truncation there is expected, harmless degradation"

requirements-completed: [CARD-01, CARD-02, CARD-03, CARD-04]

coverage:
  - id: D1
    description: "Terminal renders a PENDING PHASES table (#, phase, state, rsch, plans, issues, verify, waits, next) plus an untruncated PURPOSE list keyed by phase number, with no separate NEXT COMMANDS section"
    requirement: "CARD-01"
    verification:
      - kind: unit
        ref: "tests/cairn-phase-model.bats#pending phases are described, not listed as bare numbers"
        status: pass
      - kind: unit
        ref: "tests/cairn-phase-model.bats#the next command carries the reason it sits where it does"
        status: pass
    human_judgment: false
  - id: D2
    description: "A phase's purpose is never truncated in the terminal (wrapped instead), unlike the fixed-width table columns above it"
    requirement: "CARD-01"
    verification:
      - kind: unit
        ref: "tests/cairn-phase-model.bats#pending phases are described, not listed as bare numbers"
        status: pass
    human_judgment: false
  - id: D3
    description: "research/plans/issues/verify/waits/next render per pending phase, with a dash for a phase with nothing built yet"
    requirement: "CARD-02"
    verification:
      - kind: unit
        ref: "tests/cairn-phase-card.bats#purpose/research/issues/verify render identically across --json, the terminal panel and the HTML page"
        status: pass
    human_judgment: false
  - id: D4
    description: "Terminal and HTML render purpose/research/issues/verify from the identical phases[] data, proven by a test that extracts from --json and greps both surfaces (never by comparing each surface's own hardcoded string)"
    requirement: "CARD-03"
    verification:
      - kind: unit
        ref: "tests/cairn-phase-card.bats#purpose/research/issues/verify render identically across --json, the terminal panel and the HTML page"
        status: pass
    human_judgment: false
  - id: D5
    description: "When every phase is complete, the terminal still shows /cairn:ship and /cairn:milestone complete with their reasons — not only --json and HTML"
    requirement: "CARD-04"
    verification:
      - kind: unit
        ref: "tests/cairn-phase-model.bats#a milestone with nothing pending is told to ship, then close out"
        status: pass
    human_judgment: false
  - id: D6
    description: "A conflicting phase's marker and reason still occupy exactly one line, inherited unchanged from Phase 13's D-03, now in a narrower column"
    verification:
      - kind: unit
        ref: "tests/cairn-corroboration.bats#a blocks conflict's detail string is verbatim-identical across --json, the terminal panel and the HTML page"
        status: pass
      - kind: unit
        ref: "tests/cairn-corroboration.bats#a blocks conflict and an informs-only conflict render as one PENDING PHASES line each, with the panel summary counting each severity separately"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-07-31
status: complete
---

# Phase 14 Plan 02: Phase card rendering Summary

**Terminal `PENDING PHASES` table (9 columns) plus an untruncated `PURPOSE` list replaces the old state-column-append + separate `NEXT COMMANDS` section; HTML mirrors purpose/research/issues/verify via the same shared helpers; a cross-surface parity test extracts from `--json` and greps both renders.**

## Performance

- **Duration:** ~45 min (commit-to-commit; excludes plan/context reading and long bats-run wait time)
- **Completed:** 2026-07-31
- **Tasks:** 2/2
- **Files modified:** 4 (`cairn/scripts/cairn-status.py`, `cairn/templates/status-board.html`, `tests/cairn-phase-card.bats`, `tests/cairn-phase-model.bats`)

## Accomplishments

- Four new shared render helpers (`phase_purpose_text()`, `phase_research_text()`, `phase_issues_text()`, `phase_verify_text()`) live next to `phase_progress_text()`, called by both the terminal table and `html_phases()` — the single source of wording for both surfaces.
- `phase_panel_lines()` rewritten to a two-pass table renderer: pass 1 gathers every pending phase's untruncated row content; the `state` column's width is then computed once from the actual per-render maximum (floor 16, capped so `phase` never collapses), so a plain `not planned` renders whole at `--width 100` and a ~76-cell conflict detail renders whole at `--width 200`/`240` — from one non-branching formula, with no special-casing between the two cases.
- `NEXT COMMANDS` no longer exists as a terminal section. The command is the table's `next` column; the routing reason moved to the `PURPOSE` list beside each phase's purpose. `PURPOSE` is guarded on `pending or global_cmds`, not `pending` alone — the fix for the exact bug the plan-checker's blocker section describes: when every phase is complete, `pending` is `[]` and the old design would have silently dropped `/cairn:ship`/`/cairn:milestone complete` from the terminal while `--json` and HTML kept them.
- `html_phases()` gained a `.phase-purpose` paragraph (right after the title span, before `{reqs}`) and three new `.phase-meta` spans (research/issues/verify, inserted after the existing plans-progress span, before the `blocked_by` append) — reusing the exact same four helper functions, never re-deriving wording.
- `tests/cairn-phase-card.bats` gained a cross-surface parity test that reads `--json`'s raw `purpose`/`research_done`/`issues_done`/`issues_total`/`verify_status` scalars, builds the expected display strings **itself** by literal string formatting (never by calling `phase_research_text()`/`phase_issues_text()`/`phase_verify_text()`), then asserts each string is a literal substring of both `--width 200` terminal output and a generated `board.html`.
- `tests/cairn-phase-model.bats`: the two pre-existing tests broken by the redesign were repaired (the `NEXT COMMANDS` assertion removed; the state-column `"waits on 3"` assertion replaced with the relocated `"waits on phase 3"` reason text), and the "milestone with nothing pending" test was extended with a terminal-side (`--width 100`) assertion for `/cairn:ship`/`/cairn:milestone complete` — the specific regression coverage that did not exist before this plan and is exactly what would have caught the global-command drop.

## Task Commits

Each task was executed and committed atomically, split from a combined working-tree edit into two clean per-task commits via `git apply --cached` on hand-split hunks (index-only surgery, no working-tree mutation — the working tree held the full final state throughout, verified against a plain-file backup before and after the split):

1. **Task 1: Terminal — table + purpose list, NEXT COMMANDS folded in (D-01, D-02, D-04)** — `52deffa` (feat)
2. **Task 2: HTML mirror + cross-surface parity test (D-01, D-02, D-04, CARD-03)** — `f8df980` (feat)

**Plan metadata:** this SUMMARY's own commit (see below) — `STATE.md`/`ROADMAP.md`/`REQUIREMENTS.md` are intentionally NOT updated or committed from this worktree; the orchestrator reconciles those shared files at wave merge time, per this plan's explicit execution instructions.

## Files Created/Modified

- `cairn/scripts/cairn-status.py` — four new `phase_*_text()` helpers; `phase_panel_lines()` rewritten (table + PURPOSE, no `NEXT COMMANDS`); `html_phases()` extended (purpose paragraph + three meta spans); module docstring step `5b` added documenting the new terminal layout; `html_phases()`'s own docstring updated
- `cairn/templates/status-board.html` — `.phase-purpose` CSS rule added after `.phase-title`
- `tests/cairn-phase-card.bats` — new cross-surface parity test (`purpose/research/issues/verify render identically across --json, the terminal panel and the HTML page`) plus its `write_parity_roadmap()` fixture builder
- `tests/cairn-phase-model.bats` — two pre-existing tests repaired, one extended with terminal-side regression coverage

## Decisions Made

- **PURPOSE guard on `pending or global_cmds`** (not `pending` alone) — this is the load-bearing fix the plan exists to deliver; verified directly by the extended "milestone with nothing pending" test at `--width 100`.
- **Dynamic `state` column width, not a fixed constant** — computed once per render from the actual maximum untruncated row content across all pending phases, floored at 16 cells (enough for the shortest possible conflict marker prefix, `"x conflict -"`, under both `--ascii` and unicode ellipsis widths) and capped so `phase` retains at least 1 cell. This single formula, verified against the existing `--width 100`/`200`/`240` corroboration tests, produces the same behavior the old code got "for free" by putting `state` last on the line with nothing after it — without reintroducing that constraint now that six more columns follow it.
- **`VERIFY_W` raised from the plan's 12-cell starting point to 16** — discovered via the new parity test itself failing on a realistic `verify_status` value (`"needs-revision"`, 14 chars) truncating in the terminal at `--width 200`. Fixed by widening the column rather than shortening the test fixture's status string, since arbitrary-length frontmatter text is the real shape of this field.
- **`next` column colored green when the phase is unblocked, dim otherwise** — a small design choice not spelled out in the plan (column glyphs/abbreviations are explicitly Claude's discretion per `14-CONTEXT.md`), carrying forward the old `NEXT COMMANDS` section's "only the runnable command is spent on light" intent into the new column.
- **`PLANS_W`/`ISSUES_W`/`WAITS_W`/`NEXT_W` kept close to the plan's starting-point numbers** (6/7/7/16) since no pre-existing test asserts their exact untruncated content at narrow widths — unlike `state` and `verify`, which the new/existing tests do pin.

## Deviations from Plan

None — plan executed exactly as written, including the D-02 blocker fix (`pending or global_cmds` guard) that was the explicit reason for this plan's second revision round.

One process note, not a code deviation: to keep the two tasks' git history atomic (separate commits, each independently bisectable) while implementing both tasks' edits to `cairn/scripts/cairn-status.py` together for efficiency, the final combined diff was split into two commits via `git apply --cached` on hand-extracted hunks — an index-only operation that never touched the working tree (verified: `git diff <task1-commit> <task2-commit> --stat` after both commits reproduces the exact same 335-insertion/47-deletion combined diff as the original single working-tree diff, byte for byte). `git stash` was never used (per this worktree's standing prohibition).

## Anti-False-Green Sanity Check (required by this plan's acceptance criteria)

Before committing Task 2, the three new `meta.append(...)` calls in `html_phases()` (research/issues/verify) were temporarily commented out and the new parity test re-run in isolation: it failed exactly as expected (`AssertionError: ('research', 'html', 'yes')`), confirming the test genuinely exercises the HTML side rather than passing vacuously. The temporary change was reverted before committing; `git diff` was inspected afterward to confirm the revert restored the exact intended code with no leftover debug markers.

## Known Stubs

None — every field this plan renders (`purpose`, `research_done`, `issues_done`/`issues_total`, `verify_status`) is wired to Plan 14-01's real data-layer reads, on both surfaces, proven by the parity test.

## Issues Encountered

- The first run of the new parity test failed with `bd init` erroring — `setup()` in `tests/cairn-phase-card.bats` already runs `bd init --prefix pc` before every test in the file; the new test's own redundant `bd init --prefix px` call was removed (Rule 1 — the test itself was buggy, not the production code).
- The second run failed on `verify_status` ("needs-revision", 14 chars) truncating in the terminal's `verify` column at `--width 200` — `VERIFY_W` was 12. Widened to 16 (see Decisions above); re-run confirmed both terminal and HTML now carry the full string.
- Both fixes are captured in the Task 2 commit; no separate deviation entries were needed since the plan explicitly reserves both column widths and test-fixture correctness to this task's own scope.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The `PENDING PHASES` table + `PURPOSE` list layout (D-01/D-02) and the HTML mirror (CARD-03) are both live and covered by `bats tests/cairn-phase-card.bats tests/cairn-phase-model.bats tests/cairn-corroboration.bats` — 58/58 passing.
- `NEXT COMMANDS` no longer exists as a terminal section anywhere in `cairn-status.py`; no other renderer (`render_plain`/`render_raw`/`render_brief`) referenced it, so no follow-on cleanup is needed there.
- Column-width constants (`RSCH_W`, `PLANS_W`, `ISSUES_W`, `VERIFY_W`, `WAITS_W`, `NEXT_W`, `PHASE_TABLE_FLOOR`, `STATE_TABLE_FLOOR`) are now named module-level constants immediately above `phase_panel_lines()` — a future plan wanting to adjust the table's shape has one place to look.

---
*Phase: 14-phase-card*
*Completed: 2026-07-31*

## Self-Check: PASSED
