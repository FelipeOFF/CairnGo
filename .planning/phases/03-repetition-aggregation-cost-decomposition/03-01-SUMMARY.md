---
phase: 03-repetition-aggregation-cost-decomposition
plan: "01"
subsystem: testing
tags: [benchmarks, python, bats, interleaving, repetitions, seeded-shuffle]

# Dependency graph
requires:
  - phase: 02-baseline-manifests-seeded-interleaving
    provides: "bench-run.py isolated runner with --seed/--run-order-index provenance; bench-matrix.py seeded shuffled orchestrator; bench-matrix.bats fixture baselines"
provides:
  - "bench-run.py optional --rep-index flag, stamped into the row as a JSON integer only when provided (standalone rows unchanged)"
  - "bench-matrix.py --reps flag (default 5, METR-01) with build_execution_order(baselines, reps, seed) shuffling the full (name, rep_idx) cross-product via one instance-scoped random.Random(seed)"
  - "tests/bench-matrix.bats coverage: --reps 5 interleaving (no contiguous 5-run baseline block at seed 7), rep_index {0..4} per baseline, run_order_index contiguity {0..14}, live default without the flag; 4 pre-existing invocations pinned to --reps 1"
affects: [03-02-aggregation, benchmark-suite-runs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "cross-product interleaving: itertools.product(baselines, range(reps)) shuffled once with an instance-scoped RNG, never per-baseline blocks"
    - "row provenance stamps stay strictly optional and conditional (key absent when flag omitted)"

key-files:
  created: []
  modified:
    - benchmarks/scripts/bench-run.py
    - benchmarks/scripts/bench-matrix.py
    - tests/bench-matrix.bats

key-decisions:
  - "--reps 1 backfill landed in the same commit as the live default flip to 5, keeping the bats suite green at every commit"
  - "build_execution_order docstring avoids the literal 'itertools.product' so the single construction-site grep stays meaningful"

patterns-established:
  - "Interleaved repetitions: shuffle the full baseline x rep cross-product with one seeded RNG so reps never run back-to-back per baseline"

requirements-completed: [METR-01]

# Metrics
duration: 9min
completed: 2026-07-26
---

# Phase 3 Plan 01: Interleaved Repetitions Summary

**bench-matrix.py now launches N=5 seeded-interleaved repetitions per baseline across the full baseline x rep cross-product, with rep_index provenance stamped into every row via bench-run.py's new optional --rep-index**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-07-26T04:35:24Z
- **Completed:** 2026-07-26T04:44:00Z
- **Tasks:** 2 (Task 1 tdd=true: RED + GREEN commits)
- **Files modified:** 3

## Accomplishments
- `bench-matrix.py --reps` (default 5, live not just parsed): `build_execution_order(baselines, reps, seed)` shuffles the whole `(name, rep_idx)` cross-product with one `random.Random(seed)` instance — verified at seed 7 that no baseline's 5 reps occupy a contiguous `run_order_index` block (spans 13/11/10, never 4)
- `bench-run.py --rep-index` mirrors `--seed`/`--run-order-index` exactly: optional, `int`-cast with `EXIT_USAGE` on bad input, conditionally stamped as a JSON integer, key absent when omitted (zero regression to Plan 02-01 invocation shapes)
- Summary line rebuilt from resolved cells (`name#rep`) — the join-on-tuples `TypeError` flagged in the plan's Interfaces block never shipped
- bats suite grew 5 → 7 tests, all green; `bench-run.bats` 8/8 unchanged

## Task Commits

1. **Task 1 (RED): failing --reps coverage** - `da53a05` (test) — the two new @test blocks, observed failing (2 not ok / 5 ok) before any implementation
2. **Task 1 (GREEN) + Task 2 backfill** - `32adcec` (feat) — bench-run.py `--rep-index`, bench-matrix.py `--reps` + cross-product builder, `--reps 1` pinned onto the 4 pre-existing bats invocations

_No REFACTOR commit needed — GREEN landed clean._

## Files Created/Modified
- `benchmarks/scripts/bench-run.py` - optional `--rep-index` (USAGE, docstring, opts default, parse branch, conditional row stamp)
- `benchmarks/scripts/bench-matrix.py` - `--reps` argparse flag (default 5), cross-product `build_execution_order`, `--rep-index` passthrough per cell, `name#rep` summary line, docstring updated
- `tests/bench-matrix.bats` - 2 new @test blocks (interleaving/rep_index/contiguity; live default), 4 existing invocations pinned to `--reps 1`

## Decisions Made
- Backfill `--reps 1` committed atomically with the default flip: any other ordering leaves an intermediate commit where either the backfilled flags are unrecognized (exit 2) or the 3-row/2-row assertions see 15/10 rows
- Reworded `build_execution_order`'s docstring to not contain the literal `itertools.product`, keeping the acceptance grep (`count == 1`) pointing at exactly one construction site

## Deviations from Plan

### Execution-order deviation (sequencing, no scope change)

**1. Task 2's bats content executed inside Task 1's TDD cycle**
- **Found during:** Task 1 (tdd="true" requires test-first, but the test file belongs to Task 2)
- **Issue:** Task 1's RED gate needs failing tests in `tests/bench-matrix.bats` (Task 2's file); and the `--reps 1` backfill cannot be a separate later commit without breaking the suite in between
- **Fix:** RED commit (`da53a05`) carries the two new @test blocks; GREEN commit (`32adcec`) carries the implementation plus the backfill. All of Task 2's specified content shipped, just distributed across Task 1's TDD commits; Task 2's verify ran against the final state
- **Files modified:** tests/bench-matrix.bats
- **Verification:** `bats tests/bench-matrix.bats` 7/7 ok at GREEN; RED observed 2 failing / 5 passing
- **Committed in:** da53a05 + 32adcec

**2. [Checker note applied] Acceptance grep pattern corrected**
- **Found during:** Task 1 acceptance criteria
- **Issue:** Plan's grep `"','.join(order)"` lacks the space present in the real code (`', '.join(order)`)
- **Fix:** Ran the corrected pattern `', '.join(order)` — count 0 (bug did not survive); functional bats coverage is the real guard

---

**Total deviations:** 2 (1 sequencing, 1 corrected acceptance pattern)
**Impact on plan:** None on scope or outputs — every must_have truth/artifact/key_link delivered as specified.

## Assumption Drift (advisory)

None material — the plan's Interfaces simulation (seed 7 positions alpha=[0,5,9,10,13], beta=[3,7,8,12,14], gamma=[1,2,4,6,11]) reproduced exactly on this machine before the tests were written.

## Verification Evidence (observed, not assumed)

- `python3 -m py_compile benchmarks/scripts/bench-run.py benchmarks/scripts/bench-matrix.py` → exit 0
- `bench-matrix.py --help | grep -- '--reps'` → match
- `bats tests/bench-matrix.bats` → exit 0, 7/7 ok (2 new + 5 pre-existing)
- `bats tests/bench-run.bats` → exit 0, 8/8 ok (zero regression)
- `--rep-index abc` → exit 2, stderr `--rep-index must be an integer, got 'abc'`, no row file created
- `--rep-index 2` (stub) → row `rep_index == 2`, `type == "number"`; omitted → `has("rep_index") | not`
- `build_execution_order(["alpha","beta","gamma"], 5, 7)` called twice → identical lists (byte-identical order)
- Acceptance greps: bench-run `rep_index` count 6 (>=3); `itertools.product` count 1; `shell=True` count 0; `', '.join(order)` count 0; bats `--reps 1` count 4; bats `rep_index` count 2 (>=2)
- All runs via `CAIRN_BENCH_CLAUDE_BIN` stubs — zero live API calls

## Known Stubs

None — no placeholder values or unwired data paths introduced (test stubs are the suite's intentional zero-cost seam, pre-existing design).

## Issues Encountered

None beyond the documented sequencing decision.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Raw JSONL rows now carry full provenance (`seed`, `run_order_index`, `rep_index`) — Plan 03-02's `bench-aggregate.py` can group cells by `(task_id, baseline_id)` and locate any repetition by provenance alone (threat register T-03-02 mitigation delivered)
- No blockers

## Self-Check: PASSED

All 3 modified files plus this SUMMARY exist on disk; commits `da53a05` and `32adcec` present in git log.

---
*Phase: 03-repetition-aggregation-cost-decomposition*
*Completed: 2026-07-26*
