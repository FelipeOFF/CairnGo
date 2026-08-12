---
phase: 05-corpus-expansion-bias-controls
verified: 2026-07-26T00:00:00Z
status: passed
score: 15/15 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
---

# Phase 5: Corpus Expansion + Bias Controls Verification Report

**Phase Goal:** The benchmark measures a deliberately diverse, pre-declared task set — including at least one category where cairn's overhead is a real cost, not a win — sized to actually distinguish baselines from noise.
**Verified:** 2026-07-26
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | [ROADMAP SC1] Corpus contains multiple representative dev-workflow categories, selection criteria documented before any comparative results exist | VERIFIED | 6 task dirs (`smoke`, `bugfix`, `feature`, `refactor`, `honest-non-win`, `long-horizon`); `benchmarks/README.md` "## Task corpus" section (rationale paragraph + table) present at commit 4cd83c1; no `aggregated.json` or full-corpus results committed anywhere (`find . -name aggregated.json` empty) — rationale predates any results |
| 2 | [ROADMAP SC2] At least one category explicitly unfavorable to cairn, runs through the same 4-arm pipeline as every other task | VERIFIED | `microedit-greet` is the sole `honest-non-win` task (`jq -r .category benchmarks/tasks/*/task.json \| sort \| uniq -c` = 1 each of 6 categories); ran it independently through `bench-run.py` under 2 differently-provisioned synthetic manifests via my own stub — both rows carried `category: "honest-non-win"`; `tests/bench-bias-controls.bats` test 7 proves this in CI |
| 3 | [ROADMAP SC3] Total dollar cost of the full expanded corpus calculated and documented before the full run is executed | VERIFIED | `benchmarks/README.md` "## Cost model" section: formula `tasks × arms × reps`, per-category $/run table anchored to the 2 real Phase-1 rows, worked example `6×4×5=120 runs`, declared ceiling `~$40`; no live run has occurred (only pre-existing Phase-1 `smoke-convert.jsonl`, confirmed via `git log --follow`) |
| 4 | [ROADMAP SC4] Task-selection rationale (why these tasks, why this count) written down and committed alongside the corpus | VERIFIED | "## Task corpus" section's "Selection rationale" paragraph, committed in the same phase (commits 0b02dca…573417a) as the fixtures themselves |
| 5 | [05-01] 5 new fixtures each follow the smoke-convert contract exactly (task.json + prompt.md + fixture/ + verify.sh, stdlib unittest only) | VERIFIED | Directory listing + file inspection for all 5 task dirs; `python3 -m py_compile` on every fixture `.py` file succeeds; import scan finds zero non-stdlib, non-local imports |
| 6 | [05-01] Every new task's verify.sh exits non-zero unsolved / 0 solved, proven at $0 via bats, both directions, all 5 tasks | VERIFIED | `bats tests/bench-corpus.bats` — 10/10 ok. Independently re-proved by hand (fresh copies, not the bats fixtures) for `bugfix-inventory` (unsolved: exit 1, `FAILED (failures=2)`; hand-solved: exit 0, `OK`) and `longhorizon-notify` (unsolved: exit 1, `AttributeError: no attribute 'summary'`; hand-solved: exit 0, `OK`) |
| 7 | [05-01] microedit-greet labeled `category: honest-non-win` | VERIFIED | `jq -r .category benchmarks/tasks/microedit-greet/task.json` = `honest-non-win`; exactly one across the corpus |
| 8 | [05-01] refactor-report's verify.sh rejects a functionally-correct-but-unrefactored fixture via structural anti-cheat, not just behavior tests | VERIFIED (hand-reproduced independently) | Raw fixture: `python3 -m unittest tests.test_report` alone → exit 0, `OK` (4/4 pass — duplication is functionally correct); full `verify.sh` on the same raw fixture → exit 1, anti-cheat message "'total += r[\"amount\"]' still appears 3 times". Hand-refactored copy → `verify.sh` exit 0, "duplication check passed (1 occurrence(s))" |
| 9 | [05-01] longhorizon-notify requires implementing NotificationLog + record_notification and wiring into app.py's setup() before its 5 tests pass | VERIFIED (hand-reproduced independently) | Unsolved fixture (`NotificationLog: pass`, `record_notification` raising `NotImplementedError`, `setup()` no-op) → `AttributeError`, 5 errors. Hand-solved implementation + wiring → all 5 tests pass |
| 10 | [05-01] No new task's prompt.md mentions any arm name or arm-favoring language | VERIFIED | `grep -riE 'cairn\|gsd\|ralph\|plan first\|just edit' benchmarks/tasks/*/prompt.md` → no match (exit 1) across all 6 prompts, run independently |
| 11 | [05-02] bench-matrix.py accepts --tasks (comma list or sorted glob), shuffling the full task×baseline×rep cross-product with the existing seeded RNG; --task unchanged | VERIFIED (hand-reproduced independently) | Wrote my own claude stub + 2 fresh baseline manifests, ran `--tasks "<abs-glob>/*" --baselines alpha,beta --reps 2 --seed 42` twice: 24 rows each run, identical execution order both times (`diff` after removing `wall_clock_ms` → identical); rows carry `task_id`, `baseline_id`, `rep_index`, `run_order_index`, `seed`, `category`. `bats tests/bench-matrix.bats` 12/12 ok (7 pre-existing + 5 new) |
| 12 | [05-02] category flows from task.json into every JSONL row (when declared) and every aggregated cell (always present, null when absent) | VERIFIED (hand-reproduced independently) | Ran `bench-aggregate.py` on my own 24-row run above: 12 cells (`task_id::baseline_id`), every cell's `.category` matches the source task's category exactly (`bugfix`, `feature`, `long-horizon`, `honest-non-win`, `refactor`, `smoke`) |
| 13 | [05-02] CI-enforced bats check fails the build if the Cost model section stops naming any of the 6 corpus task ids | VERIFIED | `tests/bench-bias-controls.bats` test "README Cost model section names every corpus task id" exists, extracts the section via awk and greps every live `task.json .id` inside it; passes (confirmed running, plus manually confirmed all 6 ids appear in the section text) |
| 14 | [05-02] CI-enforced bats check fails the build if any task prompt contains an arm name, case-insensitive | VERIFIED | `tests/bench-bias-controls.bats` test present and passing; independently reproduced the same grep by hand (truth #10 above) |
| 15 | [05-02] The honest-non-win task runs through bench-run.py identically under differently-provisioned baseline manifests (no category-based special-casing) | VERIFIED | `tests/bench-bias-controls.bats` test 7 passing; category passthrough (truth #12) is provisioning-agnostic by construction (reads only `task["category"]`, never touches `manifest["provisioning"]`) |

**Score:** 15/15 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `benchmarks/tasks/bugfix-inventory/` | full fixture contract, category bugfix | VERIFIED | exists, verified both directions independently |
| `benchmarks/tasks/feature-todo/` | full fixture contract, category feature | VERIFIED | exists, bats 2/2 |
| `benchmarks/tasks/refactor-report/` | fixture + 2-layer anti-cheat verify.sh | VERIFIED | anti-cheat reproduced by hand |
| `benchmarks/tasks/microedit-greet/` | honest-non-win fixture | VERIFIED | reproduced by hand, category confirmed |
| `benchmarks/tasks/longhorizon-notify/` | 3-file implement+wire+test fixture | VERIFIED | reproduced by hand |
| `tests/bench-corpus.bats` | 10 two-direction $0 tests | VERIFIED | 10/10 ok |
| `benchmarks/scripts/bench-matrix.py` | `resolve_tasks`, `--tasks` cross-product | VERIFIED | `grep -c 'def resolve_tasks'` = 1; `--help` mentions both flags; reproduced independently |
| `benchmarks/scripts/bench-run.py` | `row["category"]` optional stamp | VERIFIED | `grep -c` = 1; reproduced independently |
| `benchmarks/scripts/bench-aggregate.py` | `stats["category"]` always-present-possibly-null | VERIFIED | `grep -c` = 1; reproduced independently |
| `benchmarks/README.md` | Task corpus + Cost model + Variance pilot (PENDING) | VERIFIED | all 3 headings present, content matches plan exactly |
| `tests/bench-bias-controls.bats` | 7 CI-enforced bias-control checks | VERIFIED | 7/7 ok, logic independently reviewed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `task.json .category` | JSONL row | `bench-run.py` row construction | WIRED | independently reproduced, row carries category when task declares it |
| JSONL rows' `.category` | `aggregated.json` cell | `bench-aggregate.py cell_stats()` | WIRED | independently reproduced, 12/12 cells correct |
| `benchmarks/README.md` Cost model | `tests/bench-bias-controls.bats` doc-rot test | `extract_section` + grep per task id | WIRED | test passing, all 6 ids present in section text |
| `bench-matrix.py --tasks` | `bench-run.py` per-cell invocation | subprocess per shuffled cell | WIRED | independently reproduced, 24/24 rows correct across 2 identical-seed runs |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Required 7-file bats suite | `bats tests/bench-verify.bats tests/bench-corpus.bats tests/bench-matrix.bats tests/bench-bias-controls.bats tests/bench-run.bats tests/bench-aggregate.bats tests/stage-plugins.bats` | `1..57`, 57/57 ok | PASS |
| 2 hand-picked fixtures, fresh copies, both directions | manual `cp -r` + `bash verify.sh` | bugfix-inventory and longhorizon-notify both directions confirmed | PASS |
| refactor-report anti-cheat (raw passes unittest, fails verify.sh; hand-refactored passes both) | manual `python3 -m unittest` + `bash verify.sh` on raw and hand-refactored copies | exact behavior claimed, reproduced | PASS |
| Independent multi-task matrix (own stub, `--tasks` abs glob, `--reps 2`, seed) | own claude stub + own baseline manifests + `bench-matrix.py` twice with seed 42 | 24 rows both runs, byte-identical order (excl. wall_clock_ms), `task_id×baseline_id×rep_index` present | PASS |
| Aggregate keys per task with category surfaced | `bench-aggregate.py` on the 24-row run | 12 cells, category matches source task exactly for all 12 | PASS |
| README sections + neutrality grep + `py_compile` | direct grep/awk + `python3 -m py_compile benchmarks/scripts/*.py` + all fixture `.py` | all sections present with correct content; zero arm-name matches; all scripts and fixtures compile | PASS |
| Locked decisions: pre-declared corpus, no results yet, stdlib-only | `find . -name aggregated.json`, `git log --follow benchmarks/results/smoke-convert.jsonl`, import scan | no aggregated.json anywhere; the one committed results file predates Phase 5 (Phase 1 commit a8df90d); zero non-stdlib imports | PASS |
| Full-suite regression (`bats tests/`) | ran in background for supplementary confidence | in progress at write time, all observed rows `ok` through test 69/178 (no failures observed); SUMMARY claims 178/178 with 1 pre-existing unrelated environment skip | PASS (partial — see note below) |

Note on the full-suite regression check: the 7 explicitly required bats files (57 tests) were run to completion synchronously with 57/57 green — this fully satisfies the phase's own required verification command. The broader `bats tests/` run (178 tests total per SUMMARY, covering unrelated prior-phase and `cairn-doctor` suites) was additionally started as supplementary due diligence; every test observed before this report was finalized passed with zero failures, consistent with SUMMARY's claim of zero regression.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CORP-01 | 05-01, 05-02 | Diverse pre-declared corpus incl. honest-non-win category (variance pilot sized during phase) | SATISFIED | 6-category corpus, both-direction $0 proofs, honest-non-win category wired end-to-end, variance pilot recipe documented PENDING (key genuinely absent) |
| CORP-02 | 05-02 | Total $ cost of a full run documented and predictable before running | SATISFIED | Cost model section: formula, per-category estimates, worked example, ~$40 declared ceiling |

Informational note (non-blocking): `.planning/REQUIREMENTS.md`'s tracking table still shows CORP-01/CORP-02 as "Pending" and the mapped beads (`CairnGo-me5`, `CairnGo-6qo`) as `IN_PROGRESS` rather than closed. This is a documentation/issue-tracker sync lag (the same pattern already present for Phase 4's COMP-01 per STATE.md's own Blockers/Concerns note), not a code or capability gap — every mechanism the requirements describe is implemented, tested, and independently reproduced above.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `benchmarks/tasks/feature-todo/fixture/todo.py` | 27 | `# TODO: implement pending() and summary()` | Info | Intentional — this is the fixture's unsolved starting state (the feature the agent-under-test must add), documented as a "Known Stub" in 05-01-SUMMARY.md, proven rejected by `verify.sh` via bats |
| `benchmarks/tasks/longhorizon-notify/fixture/app.py` | 7 | `"""TODO: subscribe record_notification(log)..."""` | Info | Intentional — same as above, the wire-half stub of the implement+wire task |

No `TBD`/`FIXME`/`XXX` debt markers found anywhere in phase 5 files. No placeholder/stub patterns found in any harness script (`bench-matrix.py`, `bench-run.py`, `bench-aggregate.py`) or in `tests/bench-bias-controls.bats`.

### Human Verification Required

None. This phase is entirely CLI/file/bats-verifiable (task fixtures, harness scripts, documentation sections, CI-enforced bias-control checks) — no UI, real-time behavior, or external-service integration exists in this phase's scope.

### Gaps Summary

None. All 15 merged must-haves (4 ROADMAP success criteria + 11 plan-level truths from 05-01/05-02) verified independently against the actual codebase — file contents read directly, bats suites re-executed for real (57/57 on the required 7 files), and 2 fixtures plus the anti-cheat mechanism plus the multi-task matrix plus category passthrough hand-reproduced from scratch with fresh copies and an independently-written stub, not the repo's own bats fixtures. Zero blocking gaps. One informational note (REQUIREMENTS.md/beads tracking-table lag) recorded above, non-blocking, consistent with an existing project-wide pattern already acknowledged in STATE.md for Phase 4.

---

*Verified: 2026-07-26*
*Verifier: Claude (gsd-verifier)*
