---
phase: 06-reporting-charts-publication
plan: "03"
subsystem: benchmarks
tags: [bash, bats, orchestration, cost-safety, reproduction]

# Dependency graph
requires:
  - phase: 06-01
    provides: "bench-chart.py --in/--out-dir/--label CLI (aggregated.json -> SVGs)"
  - phase: 06-02
    provides: "bench-publish.py --in/--benchmarks/--label/--readme CLI + BENCHMARKS.md/README.md generated-marker blocks"
  - phase: 05-corpus-baselines-aggregation
    provides: "stage-plugins.py / bench-matrix.py / bench-aggregate.py CLIs, 4 pinned baselines, 6-task corpus, ~$40 Cost model worked example, CAIRN_BENCH_CLAUDE_BIN seam"
provides:
  - "benchmarks/scripts/bench-all.sh — the single REPT-04 reproduction command: plan+ceiling always printed first, --dry-run default (zero invocation, $0), --yes gated on the explicit flag AND a non-empty ANTHROPIC_API_KEY"
  - "tests/bench-all.bats — mechanical tripwire proof of the zero-invocation contract, usage-error proofs, full $0 stub pipeline filling a temp BENCHMARKS.md, never-in-CI grep guard, repo-hygiene proof"
affects: [first real collection run once ANTHROPIC_API_KEY exists, any future cost-model change]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "orchestrator-only bash: bench-all.sh adds no new numeric exit contract — 0/2 plus propagated step exit codes under set -e"
    - "CAIRN_BENCH_SCRIPTS_DIR seam (mirrors CAIRN_BENCH_CLAUDE_BIN philosophy): tests point the orchestrator at tripwire stubs without touching real scripts"
    - "tripwire testing: sentinel-touching stubs turn 'we never invoke X' from code inspection into a mechanical assertion"

key-files:
  created:
    - benchmarks/scripts/bench-all.sh
    - tests/bench-all.bats
  modified: []

key-decisions:
  - "--baselines-dir added as an explicit flag (default benchmarks/baselines) feeding stage-plugins manifest paths, bench-matrix --baselines-dir, and label derivation (plan-checker fix)"
  - "never-in-CI invariant enforced mechanically: absence-grep over .github/workflows/ in bats, mirroring the bench-bias-controls neutrality-grep (plan-checker fix)"
  - "LABEL derived via python3 (not jq) from the first resolved baseline manifest's model + UTC date, matching the 'claude-haiku-4-5-20251001 - 2026-07-26' precedent in tests/bench-chart.bats"

patterns-established:
  - "spend gate pattern: default mode is dry-run regardless of env; spend requires explicit --yes AND a present key; the plan+ceiling always prints before anything can spend"

requirements-completed: [REPT-04]

# Metrics
duration: 51min
completed: 2026-07-26
---

# Phase 6 Plan 03: bench-all.sh One-Command Reproduction Summary

**bench-all.sh orchestrates stage->matrix->aggregate->chart->publish behind a plan-first print with the verbatim ~$40 ceiling, a tripwire-proven $0 dry-run default, and a --yes+key double gate — 6 new bats tests, 199/199 suite green, zero real-file mutation, zero API spend**

## Performance

- **Duration:** ~51 min (2026-07-26T09:41:38Z -> 2026-07-26T10:32Z approx; most of it two full-suite regression runs, one stalled by a pre-existing bd flake)
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments

- REPT-04 complete: one documented command (`bench-all.sh --yes`) reproduces the full 120-run matrix; the estimated cost (~$40, restated verbatim from `benchmarks/README.md` Cost model and `BENCHMARKS.md`) prints before anything can spend, in every mode.
- Safety contract proven mechanically, not by inspection: a tripwire `CAIRN_BENCH_SCRIPTS_DIR` full of sentinel-touching stubs shows `--dry-run`, the no-flags default with no key, AND the no-flags default with a key present all invoke zero downstream scripts (no sentinel exists afterward).
- `--yes` without `ANTHROPIC_API_KEY` (unset or empty) dies exit 2 naming the key, before the plan print and before any step line; `--dry-run --yes` together die exit 2.
- Full pipeline exercised end-to-end at $0 against the `CAIRN_BENCH_CLAUDE_BIN` stub (1 task x 1 baseline x 1 rep): `matrix.jsonl` (1 row) -> `aggregated.json` (1 cell) -> chart SVGs -> temp `BENCHMARKS.md` Results block filled with the `smoke-convert`/`vanilla` row, pending notice gone, outside bytes diff-identical to the committed original.
- The whole Phase 1-6 benchmark pipeline is now one explicitly-authorized command away from real, publishable results.

## Task Commits

1. **Task 1: bench-all.sh orchestrator** - `f62f0c0` (feat)
2. **Task 2: tests/bench-all.bats** - `0aae722` (test)

## Files Created/Modified

- `benchmarks/scripts/bench-all.sh` - plan-first, dry-run-default, explicit-yes-to-spend orchestrator; header documents flags, exit codes (0/2/propagated), the hardcoded-ceiling rationale, the CAIRN_BENCH_SCRIPTS_DIR/CAIRN_BENCH_CLAUDE_BIN seams, and the never-wire-into-CI constraint (T-06-10)
- `tests/bench-all.bats` - 6 tests: mutual exclusion, key-gate ordering, tripwire zero-invocation (3 invocations), full $0 stub pipeline into temp copies, never-in-CI absence-grep, real-repo hygiene

## Deviations from Plan

### Plan-checker fixes (orchestrator-directed, honored)

**1. [Checker fix] `--baselines-dir <dir>` added as an explicit flag**
- **Found during:** Task 1 (plan's actions referenced `<baselines-dir>` without defining it)
- **Fix:** flag with default `benchmarks/baselines`; feeds stage-plugins manifest paths, `bench-matrix.py --baselines-dir`, and LABEL model derivation; exercised end-to-end by the full-pipeline test with an absolute path
- **Commit:** `f62f0c0`

**2. [Checker fix] Mechanical never-in-CI guard**
- **Found during:** Task 2
- **Fix:** bats test greps `.github/workflows/` recursively for `bench-all` and asserts absence (same style as the task-prompt neutrality grep), turning the T-06-10 "documented constraint" into an enforced invariant
- **Commit:** `0aae722`

### Minor additions within plan intent

**3. Tripwire test also covers no-flags-with-key-present**
- The plan required `--dry-run` and the no-flags/no-key cases; a third invocation with a dummy key set proves the documented "default is dry-run regardless of env" claim mechanically (T-06-09 hardening). Same test, three invocations, zero sentinels.

**4. LABEL derivation uses python3, not jq**
- Plan suggested `jq` as an example; python3 is already a hard dependency of every pipeline step, so no new tool requirement was introduced.

## Verification Evidence (all observed, not inferred)

- `bash -n benchmarks/scripts/bench-all.sh` — exit 0
- `ANTHROPIC_API_KEY= bash benchmarks/scripts/bench-all.sh --dry-run` — exit 0; stdout contains `DRY-RUN`, `~$40`, `total_runs:    120 (6 tasks x 4 baselines x 5 reps)`, `ANTHROPIC_API_KEY present: no`, and `dry-run: no downstream script invoked, $0 spent`
- `bash benchmarks/scripts/bench-all.sh --dry-run --yes` — exit 2, "mutually exclusive"
- `ANTHROPIC_API_KEY= bash benchmarks/scripts/bench-all.sh --yes` — exit 2 naming ANTHROPIC_API_KEY, no plan/step output
- `bats tests/bench-all.bats` — `1..6`, 6 ok, 0 not ok, exit 0
- Full-suite regression: all 21 test files run individually, every file exit 0; 199/199 ok, 0 not ok (193 pre-existing + 6 new; plan line `1..199` observed). One earlier single-invocation `bats tests/` run stalled in a pre-existing bd-dependent `cairn-status.bats` test (intermittent embedded-dolt hang, file untouched since `b6bdc30` 2026-07-25, passed 22/22 on re-run) — logged in `deferred-items.md`, out of scope.
- `git status --porcelain -- BENCHMARKS.md README.md benchmarks/results benchmarks/charts` after all test runs — empty (exit 0)
- Ceiling consistency: `~$40` printed by bench-all.sh matches `benchmarks/README.md:283` and `BENCHMARKS.md:55`/`BENCHMARKS.md:104` verbatim
- Zero live API calls: every claude invocation went through the local `CAIRN_BENCH_CLAUDE_BIN` stub; the only ANTHROPIC_API_KEY values used were dummy strings, and the live-path output was grepped to prove the key value never echoes

## Known Stubs

- Inherited (not created here): `BENCHMARKS.md` Results and `README.md` teaser remain in their deliberate pending state until the first real collection run — the exact state 06-02 shipped, now resolvable by `bench-all.sh --yes` once an operator supplies a key and accepts the ~$40 ceiling.

## Threat Flags

None new. T-06-09 (accidental spend), T-06-10 (CI wiring), T-06-11 (key leak) all mitigated as planned and bats-proven; T-06-12 (ceiling drift) accepted per plan, with the figure cross-checked verbatim at authoring time.

## User Setup Required

None. Live collection remains blocked only on `ANTHROPIC_API_KEY` (pre-existing, unchanged).

## Next Phase Readiness

- Milestone-final piece delivered: `benchmarks/scripts/bench-all.sh --yes` is the entire remaining distance to real published results.
- When the cost model ever changes, three locations must move together (benchmarks/README.md, BENCHMARKS.md, bench-all.sh) — T-06-12's accepted single-source risk.

## Self-Check: PASSED

- FOUND: benchmarks/scripts/bench-all.sh
- FOUND: tests/bench-all.bats
- FOUND: .planning/phases/06-reporting-charts-publication/deferred-items.md
- FOUND: commit f62f0c0 (feat, Task 1)
- FOUND: commit 0aae722 (test, Task 2)
- must_haves contains-patterns verified: `stage-plugins.py` and `bench-chart.py` and `$40` in bench-all.sh; `tripwire` in bench-all.bats

---
*Phase: 06-reporting-charts-publication*
*Completed: 2026-07-26*
