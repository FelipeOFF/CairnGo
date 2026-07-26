---
phase: 03-repetition-aggregation-cost-decomposition
plan: "02"
subsystem: benchmarking
tags: [python, jsonl, statistics, bats, jq, aggregation]

# Dependency graph
requires:
  - phase: 01-verification-core-first-real-run
    provides: "raw JSONL row schema (usage/modelUsage/total_cost_usd/verify_passed/is_error) and the committed real rows in benchmarks/results/smoke-convert.jsonl"
  - phase: 02-baselines-isolation-batching
    provides: "baseline_id row stamping and the bench-run.sh wrapper / die() / bats conventions this plan mirrors"
provides:
  - "bench-aggregate.py: deterministic JSONL(s) -> aggregated.json with success-gated per-cell pass_rate/median/min/max/IQR and 4-way modelUsage-preferred token decomposition"
  - "bench-aggregate.sh thin wrapper (standard exec-python3 template)"
  - "tests/fixtures/aggregate-gating-{a,b}.jsonl synthetic gating fixtures (10 hand-verifiable rows across alpha/beta/gamma cells)"
  - "tests/bench-aggregate.bats: 6 tests covering rejection, gating, decomposition exact values, order-independence, determinism, CLI errors — all at $0"
  - "benchmarks/README.md Aggregation + Repetitions sections; stale 'not built yet' note removed"
affects: [phase-6-reporting, benchmarks, aggregation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "belt-and-braces headline gate: verify_passed is True AND NOT is_error (never trust one axis alone)"
    - "counted rejection: malformed/incomplete rows land in the output artifact's rejected_rows, never die(), never silent drop"
    - "deterministic JSON artifact: sorted input paths + sorted cell keys + sort_keys + fixed separators + zero timestamps"
    - "modelUsage-preferred token decomposition with flat-usage fallback"

key-files:
  created:
    - benchmarks/scripts/bench-aggregate.py
    - benchmarks/scripts/bench-aggregate.sh
    - tests/fixtures/aggregate-gating-a.jsonl
    - tests/fixtures/aggregate-gating-b.jsonl
    - tests/bench-aggregate.bats
  modified:
    - benchmarks/README.md

key-decisions:
  - "Implemented the plan's pre-verified algorithm verbatim; observed output byte-identical to the plan's expected aggregated.json"
  - "README avoids GSD phase framing: 'zero live API calls were spent on them' instead of naming the planning phase"

patterns-established:
  - "Aggregation artifacts assert determinism via true byte-for-byte diff (no jq -S normalization) because the emitter owns key ordering"

requirements-completed: [METR-01, METR-02, METR-03]

# Metrics
duration: 7min
completed: 2026-07-26
---

# Phase 3 Plan 02: Aggregation & Cost Decomposition Summary

**Deterministic JSONL aggregator (`bench-aggregate.py`) with belt-and-braces success gating, modelUsage-preferred 4-way token decomposition, and median+min/max/IQR per (task, baseline) cell — proven byte-for-byte against pre-verified expected output at $0.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-26T04:33:38Z
- **Completed:** 2026-07-26T04:40:17Z
- **Tasks:** 2 (Task 1 as TDD RED→GREEN)
- **Files modified:** 6

## Accomplishments
- `bench-aggregate.py` folds one or more raw JSONL files into `aggregated.json`: per-cell `pass_rate`/`n_total`/`n_passed`, cost median/min/max (inclusive-method IQR at n>=2), 4-way token sums/medians — every stat gated on `verify_passed is True and not is_error`
- Counted rejection contract: non-JSON lines and rows missing `usage`/`verify_passed`/`baseline_id`/`task_id` land in `rejected_rows` in the artifact itself; the 2 real committed rows (which predate `baseline_id`) exercise this path unmodified
- Byte-identical determinism proven three ways: double-run diff, `--in` argument-order shuffle diff, and exact byte match against the plan's pre-verified expected `aggregated.json`
- Belt-and-braces gate proven against the real `error_max_turns` row (`is_error=true`, `verify_passed=true`, cost $0.1223481): counted in `n_total`, excluded from `n_passed` and every stat (scratch copy only; committed fixture untouched)
- `benchmarks/README.md` now documents repetitions and aggregation; stale "not built yet" note removed

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): failing bats coverage + fixtures** - `bab4ecc` (test) — fixtures and the 6-test suite ran 0/6 before implementation existed
2. **Task 1 (GREEN): aggregator + wrapper** - `ee706c2` (feat) — 6/6 bats pass
3. **Task 2: README documentation** - `3d00bf7` (docs)

_Note: Task 1 was tdd="true"; Task 2's fixture/bats artifacts served as its RED phase (they ARE the feature's test file per the plan), so Task 2's remaining scope was the README commit._

## Files Created/Modified
- `benchmarks/scripts/bench-aggregate.py` - deterministic aggregator: load_rows (counted rejection), is_headline_pass, token_components (modelUsage-preferred), group_cells, cell_stats, main
- `benchmarks/scripts/bench-aggregate.sh` - standard thin exec-python3 wrapper
- `tests/fixtures/aggregate-gating-a.jsonl` - alpha cell: 4 passes (one usage-only fallback) + 1 fail
- `tests/fixtures/aggregate-gating-b.jsonl` - beta cell (belt-and-braces reject + 1 pass + 1 fail) and gamma cell (all-fail, pass_rate 0)
- `tests/bench-aggregate.bats` - 6 tests: rejection, exact-value gating/decomposition, order-independence, determinism, mixed real+synthetic, CLI usage errors
- `benchmarks/README.md` - Repetitions + Aggregation sections, updated summary paragraph and test-suite command

## Decisions Made
- Implemented the plan's pre-verified algorithm exactly as given; no redesign. Verified output is byte-identical to the plan's expected JSON.
- Documented spread nulls per the verified behavior (median/min/max null only at 0 passing rows; IQR null below 2) rather than the plan prose's looser "both null at 0 or 1" phrasing — the plan's own expected JSON has `cost_median: 0.25` on the 1-pass beta cell.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - CLAUDE.md convention] README wording avoids GSD phase framing**
- **Found during:** Task 2 (README update)
- **Issue:** Plan asked the README to state "zero live API calls were spent in Phase 3"; project executor rules forbid GSD phase numbers in product docs/comments
- **Fix:** Phrased as "Repetition and aggregation were built and proven entirely at $0 ... zero live API calls were spent on them" — same claim, behavior-framed
- **Files modified:** benchmarks/README.md
- **Verification:** `grep -c 'Phase 3 scope'` == 0; content requirements all present
- **Committed in:** 3d00bf7

**2. [Rule 2 - Docs accuracy] Added tests/bench-aggregate.bats to the README's zero-cost suite command**
- **Found during:** Task 2 (README update)
- **Issue:** README enumerates the zero-cost bats suite; omitting the new file would leave the doc stale
- **Fix:** Appended `tests/bench-aggregate.bats` to the listed command
- **Files modified:** benchmarks/README.md
- **Committed in:** 3d00bf7

---

**Total deviations:** 2 auto-fixed (both Rule 2, documentation-level)
**Impact on plan:** No behavior or scope change; all code artifacts match the plan's verified algorithm exactly.

## Assumption Drift (advisory)

- **Found during:** Task 2 (README spread-methodology bullet). **Planned:** README prose instruction said median + IQR are "both null when a cell has 0 or 1 passing rows". **Actual:** median/min/max are null only at 0 passing rows; IQR is null below 2 (the plan's own verified expected JSON shows `cost_median: 0.25`, `cost_iqr: null` on the 1-pass beta cell). **Why:** the plan's algorithm and expected output are authoritative over its README-instruction prose; documented the tested behavior.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `aggregated.json` contract (`{"cells": {...}, "rejected_rows": N}`, keys `<task_id>::<baseline_id>`) is stable and byte-deterministic — ready for report generation to consume
- Rows produced by the repetition orchestrator (plan 03-01) flow straight in: `rep_index`/`seed`/`run_order_index` are passthrough fields, and the REQUIRED-key contract matches its row schema

## Self-Check: PASSED

All 7 created/modified files exist on disk; all 3 task commits (`bab4ecc`, `ee706c2`, `3d00bf7`) present in git log; no file deletions across the commit range; 03-01's files (bench-run.py, bench-matrix.py, tests/bench-matrix.bats) untouched.

---
*Phase: 03-repetition-aggregation-cost-decomposition*
*Completed: 2026-07-26*
