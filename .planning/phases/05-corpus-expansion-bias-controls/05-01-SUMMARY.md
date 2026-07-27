---
phase: 05-corpus-expansion-bias-controls
plan: "01"
subsystem: benchmarks
tags: [benchmark, corpus, fixtures, bats, bias-controls]
requires: []
provides:
  - "5 new benchmark task fixtures (bugfix-inventory, feature-todo, refactor-report, microedit-greet, longhorizon-notify) following the smoke-convert contract"
  - "tests/bench-corpus.bats: two-direction $0 proof (unsolved fails / hand-solved passes) for all 5"
  - "honest-non-win category (microedit-greet) — the corpus's required unfavorable category"
  - "refactor-report two-layer oracle: unittest + structural anti-cheat duplication check"
affects: [05-02]
tech-stack:
  added: []
  patterns:
    - "two-layer verify oracle (behavior tests + structural anti-cheat grep) for refactor tasks"
    - "two-direction bats proof per fixture: cp fixture -> verify fails; overwrite with hand-solve -> verify passes"
key-files:
  created:
    - benchmarks/tasks/bugfix-inventory/ (task.json, prompt.md, verify.sh, fixture/)
    - benchmarks/tasks/feature-todo/ (task.json, prompt.md, verify.sh, fixture/)
    - benchmarks/tasks/refactor-report/ (task.json, prompt.md, verify.sh, fixture/)
    - benchmarks/tasks/microedit-greet/ (task.json, prompt.md, verify.sh, fixture/)
    - benchmarks/tasks/longhorizon-notify/ (task.json, prompt.md, verify.sh, fixture/)
    - tests/bench-corpus.bats
  modified: []
key-decisions:
  - "refactor-report anti-cheat is a literal-substring grep (<=1 occurrence of the accumulation line), documented as a heuristic proxy, not AST analysis (T-05-03)"
  - "microedit-greet is the sole honest-non-win task — verified exactly one task.json carries that category"
metrics:
  duration: 4m17s
  completed: 2026-07-26
---

# Phase 5 Plan 01: Corpus Expansion (5 New Task Fixtures) Summary

**Five new $0-provable benchmark fixtures (bugfix, feature, refactor-with-anti-cheat, honest-non-win micro-edit, 3-file long-horizon) replicating the smoke-convert contract, each proven in both directions by tests/bench-corpus.bats (10 tests) with zero API involvement.**

## Tasks Completed

| Task | Name | Commit | Verification observed |
|------|------|--------|----------------------|
| 1 | bugfix-inventory + feature-todo + bats proofs | 0b02dca | `bats tests/bench-corpus.bats`: 4/4 ok |
| 2 | refactor-report (anti-cheat) + microedit-greet + bats proofs | 2ab1857 | `bats tests/bench-corpus.bats`: 8/8 ok |
| 3 | longhorizon-notify + final bats proofs + full-corpus sanity | 1c6175d | `bats tests/bench-verify.bats tests/bench-corpus.bats`: 13/13 ok |

## Evidence (all commands actually run, real output observed)

- `bats tests/bench-verify.bats tests/bench-corpus.bats` → `1..13`, all `ok` (3 pre-existing smoke-convert + 10 new). Zero regressions.
- Raw bugfix-inventory fixture genuinely broken: `python3 -m unittest tests.test_orders` on a temp copy → `FAILED (failures=2)`.
- refactor-report two-half anti-cheat proof (temp copy of raw fixture):
  - `python3 -m unittest tests.test_report` alone → exit 0 (duplication is functionally correct)
  - `bash verify.sh <copy>` → exit 1 (anti-cheat grep counts 3 occurrences of `total += r["amount"]`, expected <=1)
- Categories: `jq -r '.category'` across all 6 task.json → bugfix, feature, refactor, honest-non-win, long-horizon, null (smoke-convert's null is expected — its category lands in companion plan 05-02, wave 2).
- Exactly one `honest-non-win` task.json (`grep -l | wc -l` = 1).
- Corpus-wide prompt neutrality: `grep -riE 'cairn|gsd|ralph|plan first|just edit' benchmarks/tasks/*/prompt.md` → no match (exit 1) across all 6 prompts.
- All 5 new verify.sh committed with mode 100755 and `test -x` passing (checker-fix requirement applied to every task, not only Task 1).
- 6 task dirs under `benchmarks/tasks/` (`ls -d | wc -l` = 6).
- No file deletions across the 3 commits (`git diff --diff-filter=D HEAD~3 HEAD` empty).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking/verification correction] Task 1 acceptance command `unittest discover` finds 0 tests**
- **Found during:** Task 1
- **Issue:** The plan's acceptance command `python3 -m unittest discover -s <fixture> -t <fixture>` reports "NO TESTS RAN" — the fixture's `tests/` dir has no `__init__.py` (namespace package), which `discover` does not descend into.
- **Fix:** Ran the intent-equivalent check instead: copied the raw fixture to a scratch dir and ran `python3 -m unittest tests.test_orders` (the same invocation verify.sh uses) → `FAILED (failures=2)`, proving the bug is genuinely present. No product files changed.
- **Files modified:** none
- **Commit:** n/a (verification-only)

## Known Stubs

The stubs below are the deliverable, not defects: each is a benchmark task's intentional unsolved starting state, and bench-corpus.bats proves verify.sh rejects each of them as shipped.

| File | Stub | Intentional because |
|------|------|---------------------|
| benchmarks/tasks/feature-todo/fixture/todo.py | `# TODO: implement pending() and summary()` | the feature the agent-under-test must add |
| benchmarks/tasks/longhorizon-notify/fixture/notifications.py | `NotificationLog: pass`, `raise NotImplementedError` | the implement half of the implement+wire task |
| benchmarks/tasks/longhorizon-notify/fixture/app.py | `setup()` no-op | the wire half of the implement+wire task |
| benchmarks/tasks/bugfix-inventory/fixture/orders.py | never calls `reserve()` | the planted bug |
| benchmarks/tasks/refactor-report/fixture/report.py | 3x duplicated loop | the duplication to be refactored away |
| benchmarks/tasks/microedit-greet/fixture/greet.py | "Retun" typo | the planted micro-edit target |

## Next Phase Readiness

- 05-02 (wave 2) can now run: all 5 fixtures exist for the four-arm pipeline proof and smoke-convert's category backfill.
- Constraint compliance: zero live API calls; no bd issues closed; ROADMAP.md and STATE.md untouched per orchestrator instruction.

## Self-Check: PASSED

- All 29 created files exist on disk (28 fixture-contract files across the 5 task dirs + tests/bench-corpus.bats), verified via an explicit `test -f` scan; zero missing.
- Commits 0b02dca, 2ab1857, 1c6175d present in `git log`.
