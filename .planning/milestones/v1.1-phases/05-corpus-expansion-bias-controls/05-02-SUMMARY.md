---
phase: 05-corpus-expansion-bias-controls
plan: "02"
subsystem: benchmarks
tags: [benchmark, corpus, bias-controls, cost-model, bats]
requires:
  - "05-01: the 5 new task fixtures (microedit-greet et al.) the multi-task and bias-control tests run against"
provides:
  - "bench-matrix.py --tasks (comma list or sorted glob) generalizing the shuffle to the full task x baseline x rep cross-product; --task unchanged"
  - "category passthrough: task.json -> JSONL row (present only when declared) -> aggregated.json cell (always present, null when absent)"
  - "benchmarks/README.md: Task corpus rationale, Cost model with ~$40 declared ceiling for the 6x4x5=120-run matrix, Variance pilot recipe marked PENDING"
  - "tests/bench-bias-controls.bats: 7 CI-enforced CORP-01/CORP-02 bias-control checks at $0"
affects: [06]
tech-stack:
  added: []
  patterns:
    - "stdlib glob.glob() for absolute glob patterns (pathlib Path.glob() raises NotImplementedError on absolute patterns in py3.12)"
    - "row-level optional-omit vs cell-level always-present-possibly-null: each side follows its own file's pre-existing precedent"
    - "doc-rot guard: bats extracts a README section and greps every task.json's live .id inside it"
key-files:
  created:
    - tests/bench-bias-controls.bats
  modified:
    - benchmarks/scripts/bench-matrix.py
    - benchmarks/scripts/bench-run.py
    - benchmarks/scripts/bench-aggregate.py
    - benchmarks/tasks/smoke-convert/task.json
    - tests/bench-matrix.bats
    - tests/bench-run.bats
    - tests/bench-aggregate.bats
    - benchmarks/README.md
key-decisions:
  - "cell_stats surfaces category via stats[\"category\"] assignment (not the dict-literal form in the plan's target snippet) to satisfy the plan's own machine-checked acceptance grep; behavior identical under sort_keys=True"
  - "import glob added to bench-matrix.py — the plan's target file called glob.glob() without importing it (guaranteed NameError on the glob path)"
metrics:
  duration: 37m
  completed: 2026-07-26
---

# Phase 5 Plan 02: Corpus Generalization + Bias Controls Summary

**bench-matrix.py now runs the full 6-task corpus via --tasks (list or glob) through the identical seeded 4-arm pipeline, the honest-non-win category flows from task.json into every aggregated cell, and the README's corpus rationale / ~$40 cost ceiling / PENDING variance pilot are all CI-enforced by 7 new $0 bats checks.**

## Tasks Completed

| Task | Name | Commits | Verification observed |
|------|------|---------|----------------------|
| 1 | bench-matrix.py --tasks (task x baseline x rep) | 392e347 (RED), 7ff7651 (GREEN) | `bats tests/bench-matrix.bats`: 12/12 ok (7 pre-existing unmodified + 5 new) |
| 2 | category passthrough (task.json -> row -> cell) | 9e6c111 (RED), 6b35adc (GREEN) | `bats tests/bench-run.bats tests/bench-aggregate.bats`: 20/20 ok |
| 3 | Corpus/cost-model docs + CI bias controls | 573417a | `bats tests/bench-bias-controls.bats`: 7/7 ok |

## Evidence (all commands actually run, real output observed)

- **Full suite:** `bats tests/` → `1..178`, exit 0, **178 ok, 0 failures**, 1 pre-existing environment skip (`gsd-core validator not found` — unrelated to this plan). Zero regression anywhere.
- **TDD RED observed for real:** Task 1 RED run: tests 8/9/12 failed (`--tasks` unknown); Task 2 RED run: tests 12/20 failed (`.category` returned null). Note: the two usage-error tests (--task+--tasks together / neither) passed pre-implementation coincidentally — old argparse already exited 2 for different reasons; investigated per the fail-fast rule, they assert the same exit-code contract the new implementation preserves.
- **Task 1 acceptance:** `bench-matrix.py --help` exit 0 mentioning both `--task` and `--tasks`; `grep -c 'def resolve_tasks'` = 1. Glob test (test 9) runs `--tasks "$BENCH_TASKS_DIR/*"` — an absolute glob pattern — resolving all 6 corpus dirs sorted, matching `ls -d */`.
- **Task 2 acceptance:** regression sweep `bats tests/bench-matrix.bats tests/bench-verify.bats tests/stage-plugins.bats tests/bench-corpus.bats` → 30/30 ok; `grep -qF '"category": "smoke"' benchmarks/tasks/smoke-convert/task.json` OK; `grep -c 'row\["category"\]' bench-run.py` = 1; `grep -c 'stats\["category"\]' bench-aggregate.py` = 1.
- **Task 3 acceptance:** all three section greps (`## Task corpus`, `## Cost model`, `## Variance pilot (CORP-01)`) exit 0; `PENDING` appears 3x in README (pre-existing live load-check + isolation smoke check, plus the new pilot).
- **Cost-model CI check names all 6 tasks:** bias-controls test 4 extracts the Cost model section and greps each task.json's live `.id` (smoke-convert, bugfix-inventory, feature-todo, refactor-report, microedit-greet, longhorizon-notify) — observed ok.
- **Neutrality:** bias-controls test 3 greps every `benchmarks/tasks/*/prompt.md` case-insensitively for `cairn|gsd|ralph` — no match in any of the 6 prompts, observed ok.
- **No category special-casing:** bias-controls test 7 ran microedit-greet through bench-run.py under a bare and a plugin-provisioned synthetic manifest via the stub seam — both rows carry `category: "honest-non-win"` with the correct `baseline_id`, observed ok.
- **ANTHROPIC_API_KEY absent** (checked in this execution environment, 2026-07-26) — variance pilot ships as the documented PENDING recipe; zero live API calls made by any command in this plan (every run went through `CAIRN_BENCH_CLAUDE_BIN` stubs).
- **No file deletions** across the 5 commits (`git diff --diff-filter=D 392e347~1 HEAD` empty).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing `import glob` in the plan's target bench-matrix.py**
- **Found during:** Task 1 (GREEN)
- **Issue:** The plan's Interfaces block target file calls `glob.glob(tasks_arg)` in `resolve_tasks` but its import list omits `import glob` — a guaranteed `NameError` on every glob-pattern invocation.
- **Fix:** Added `import glob` to the imports; everything else copied exactly.
- **Files modified:** benchmarks/scripts/bench-matrix.py
- **Commit:** 7ff7651

**2. [Rule 3 - Plan-internal inconsistency] `stats["category"]` acceptance grep vs dict-literal target snippet**
- **Found during:** Task 2 (GREEN)
- **Issue:** The plan's target `cell_stats()` snippet uses the dict-literal form (`"category": rows[0].get("category")`), which cannot satisfy the plan's own must_haves `contains` and acceptance criterion `grep -c 'stats\["category"\]' == 1` (observed 0).
- **Fix:** Used the assignment form (`stats["category"] = rows[0].get("category")`) after the literal — the form the plan's key_links also cites. Behavior identical: output uses `json.dumps(sort_keys=True)`, so key insertion order is irrelevant. Re-ran `bats tests/bench-aggregate.bats` → 7/7 ok.
- **Files modified:** benchmarks/scripts/bench-aggregate.py
- **Commit:** 6b35adc

## TDD Gate Compliance

Both tdd tasks carry the full gate sequence in git log: `test(05-02)` 392e347 → `feat(05-02)` 7ff7651 (Task 1), `test(05-02)` 9e6c111 → `feat(05-02)` 6b35adc (Task 2). No refactor commits needed.

## Known Stubs

None introduced by this plan. The Variance pilot section in `benchmarks/README.md` is explicitly documented PENDING by design (CORP-02 discipline, key absent), CI-enforced by bias-controls test 6 — not a code stub. 05-01's fixture stubs are unchanged and remain the deliverable.

## Next Phase Readiness

- CORP-01 and CORP-02 fully satisfied: corpus runs through the identical 4-arm pipeline (`--tasks` glob proof), honest-non-win labeled and auto-surfaced in aggregated output, selection rationale + $40 matrix ceiling + $10 pilot ceiling committed before any spend.
- Phase 6 live collection has its exact one-command pilot recipe waiting in the README; nothing needs to change when a key appears.
- Constraint compliance: zero live API calls; no bd issues closed; ROADMAP.md and STATE.md untouched per orchestrator instruction (mirroring 05-01's precedent — final commit carries only this SUMMARY).

## Self-Check: PASSED

- All 9 plan files exist on disk and contain their must_haves markers (`resolve_tasks`, `row["category"]`, `stats["category"]`, `## Cost model`, `honest-non-win`), verified by explicit grep/test -f.
- Commits 392e347, 7ff7651, 9e6c111, 6b35adc, 573417a all present in `git log`.
