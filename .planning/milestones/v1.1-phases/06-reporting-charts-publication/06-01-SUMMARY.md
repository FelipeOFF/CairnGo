---
phase: 06-reporting-charts-publication
plan: "01"
subsystem: benchmarks
tags: [python, svg, bats, charts, determinism]

# Dependency graph
requires:
  - phase: 03-aggregation (bench-aggregate.py)
    provides: aggregated.json cell schema (cost/token medians, pass_rate, null-median honesty signal)
provides:
  - benchmarks/scripts/bench-chart.py — deterministic aggregated.json -> SVG renderer (grouped cost+pass-rate bars, 4-way token-composition stacked bars)
  - tests/bench-chart.bats — determinism, value-correctness, honesty, escaping, and repo-hygiene proofs
  - tests/fixtures/chart-aggregate.json — synthetic aggregated.json fixture (null-median cell, XML-hostile ids)
affects: [06-02 publication pipeline, real-data chart generation once collection exists]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - stdlib-only hand-rolled SVG (no gnuplot, no external binary — per 06-CONTEXT.md locked decision)
    - pure render functions (cells, label) -> SVG string, file I/O only in main()
    - single xml_escape() choke point for every interpolated string

key-files:
  created:
    - benchmarks/scripts/bench-chart.py
    - tests/bench-chart.bats
    - tests/fixtures/chart-aggregate.json
  modified: []

key-decisions:
  - "bench-chart.py invoked directly via python3 (bench-matrix.py precedent), no .sh wrapper"
  - "Canvas minimum width computed deterministically from caption/title text length so no text is ever clipped"
  - "Cost chart renders the cell's category as a muted group sub-label (bias-control visibility per CORP-01 intent)"

patterns-established:
  - "Chart honesty: null medians render class=\"bar-nodata\" 'no data' markers, never fabricated zero bars"
  - "SVG class names are the bats seam: bar-value / bar-passrate / bar-nodata / token-seg-<name> / chart-caption"

requirements-completed: [REPT-02]

# Metrics
duration: 45min
completed: 2026-07-26
---

# Phase 6 Plan 01: SVG Chart Machinery Summary

**Deterministic stdlib-only bench-chart.py turning aggregated.json into byte-identical grouped cost+pass-rate and 4-way token-composition SVG charts, proven by an 8-test bats suite at $0 with zero SVG committed**

## Performance

- **Duration:** ~45 min (includes two full 193-test suite runs)
- **Started:** 2026-07-26T08:44:46Z
- **Completed:** 2026-07-26T09:30Z (approx)
- **Tasks:** 2 (executed as one TDD RED->GREEN cycle)
- **Files modified:** 3 (all created)

## Accomplishments
- `bench-chart.py --in --out-dir --label` writes `<slug>-cost.svg` + `<slug>-tokens.svg`: grouped cost bars (per task, per baseline) each paired with its own `bar-passrate` text, and fixed-order input/cache_creation/cache_read/output stacked token bars with integer-rounded median values
- Honesty rule enforced end to end: null medians (n_passed == 0) render an explicit `no data` marker with the real `0/N (0%)` pass rate — never a fabricated zero bar (threat T-06-04 mitigated)
- All interpolated strings pass one shared `xml_escape()` (threat T-06-01 mitigated), proven against a `smoke&convert<x>` fixture id plus an `xml.dom.minidom` well-formedness parse
- Byte-identical double-run determinism proven by real `diff` on both SVGs; empty-cells input still yields two valid captioned documents

## Task Commits

TDD cycle (Task 1 `tdd="true"` drove the ordering — tests written first, then implementation):

1. **RED — Task 2 artifacts: failing bats suite + fixture** - `7fb8037` (test) — 7/8 tests failed as expected (script absent); test 8 (repo hygiene) legitimately script-independent
2. **GREEN — Task 1: bench-chart.py implementation** - `2ff382f` (feat) — targeted suite went 8/8

No refactor commit needed — clipping fixes found during the pre-commit design check landed inside the GREEN commit.

## Files Created/Modified
- `benchmarks/scripts/bench-chart.py` - deterministic aggregated.json -> two-SVG renderer; argparse, EXIT_USAGE=2 validation before any write, pure `render_cost_svg`/`render_tokens_svg`
- `tests/bench-chart.bats` - 8 tests: usage errors write nothing, byte-identical reruns, exact value tracing, no-data honesty, escaping + XML parse, verbatim caption, empty cells, zero-SVG-committed hygiene
- `tests/fixtures/chart-aggregate.json` - 2 tasks x 2 baselines; one null-median honesty cell; one XML-hostile `smoke&convert<x>` id

## Decisions Made
- No `.sh` wrapper — direct `python3` invocation per the `bench-matrix.py`/`stage-plugins.py` precedent (as the plan directed)
- Minimum canvas width is a deterministic function of caption/title text length (pure function of inputs, so determinism holds) — prevents edge-clipped text for any `--label` length; bar runs center when the floor widens the canvas
- Cost chart shows each task group's `category` as a muted sub-label, honoring bench-aggregate's stated purpose of surfacing honest-non-win cells to chart readers (within the plan's layout-discretion grant)
- One warm green-slate tonal palette, flat fills only, single rounded-cap axis — no gradients/glows/decoration in the SVG output

## Deviations from Plan

None - plan executed exactly as written. (Execution order note: Task 2's test artifacts were written before Task 1's implementation because Task 1 is `tdd="true"` — RED commit `7fb8037`, GREEN commit `2ff382f`.)

## TDD Gate Compliance
- RED gate: `test(06-01)` commit `7fb8037` — suite observed failing (7/8 not ok) before implementation existed
- GREEN gate: `feat(06-01)` commit `2ff382f` — suite observed passing 8/8 after implementation
- REFACTOR gate: not needed

## Issues Encountered
- Two edge-clipping defects caught by an automated SVG geometry bounds check before the GREEN commit: (1) the tokens chart's value column overflowed the right canvas edge for the last cell; (2) chart titles overflowed narrow canvases (small cell counts). Fixed by reserving `value_col` width and deriving the minimum canvas width from text length. Both fixes are inside `2ff382f`; determinism re-proven afterwards.
- First full-suite run piped through `tail`, masking bats' true exit code — re-ran with full output captured to get real evidence (193/193 ok, exit 0).

## Verification Evidence (all observed, not inferred)
- `python3 -m py_compile benchmarks/scripts/bench-chart.py` — exit 0
- `bats tests/bench-chart.bats` — `1..8`, 8 ok, 0 failures
- `bats tests/` (full suite) — `1..193`, 193 ok, 0 `not ok`, exit code 0 (zero regression)
- Determinism: bats test 2 `diff` on run1/run2 `*-cost.svg` and `*-tokens.svg` — exit 0, empty output
- Values: `$0.1234` / `$0.2000` / `$0.3500`, `4/5 (80%)` / `0/3 (0%)` / `5/5 (100%)` / `2/3 (67%)`, token medians 13/115/215/58 (57.5 -> 58) all matched via class-scoped greps
- Escaping: raw `smoke&convert<x>` count 0 in both SVGs; `smoke&amp;convert&lt;x&gt;` present; `xml.dom.minidom.parse` accepted both documents
- Repo hygiene: `find benchmarks/charts -name '*.svg' | wc -l` = 0 and `git ls-files -- benchmarks/charts | wc -l` = 0 (directory does not exist)
- Zero live API calls: no `claude` invocation anywhere in this plan's code or tests

## Known Stubs
None — no placeholder values, no unwired data paths. The zero-SVG-committed state is the phase's deliberate honesty rule, not a stub.

## Threat Flags
None — no new security surface beyond the plan's threat model; T-06-01 and T-06-04 mitigations implemented and bats-proven.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Chart machinery is ready for real data: once collection exists, `bench-aggregate.py` output feeds `bench-chart.py` directly and the first real dated SVGs can be committed (Wave 2+ concern)
- 06-02 (publication) can reference the `<slug>-cost.svg`/`<slug>-tokens.svg` naming contract and the class-name seams established here

## Self-Check: PASSED

- FOUND: benchmarks/scripts/bench-chart.py
- FOUND: tests/bench-chart.bats
- FOUND: tests/fixtures/chart-aggregate.json
- FOUND: commit 7fb8037 (test, RED)
- FOUND: commit 2ff382f (feat, GREEN)

---
*Phase: 06-reporting-charts-publication*
*Completed: 2026-07-26*
