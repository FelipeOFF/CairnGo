---
phase: 01-verification-core-first-real-run
plan: 02
status: complete
subsystem: testing
tags: [benchmark, harness, jsonl, stub-seam, bats, ci]

# Dependency graph
requires:
  - "01-01: smoke-convert fixture + verify.sh oracle (bench-run.py stages fixture/ and invokes verify.sh exactly as contracted there)"
provides:
  - "bench-run.py harness: stage fixture to mktemp workdir, invoke claude -p headless via argv list, parse JSON regardless of returncode, run verify.sh, append one sorted JSONL row, exit 0"
  - "CAIRN_BENCH_CLAUDE_BIN env-var stub seam (falls back to claude on PATH when unset) — the HARN-03 zero-API-cost testability primitive"
  - "bench-run.sh thin exec wrapper (cairn-map.sh shape)"
  - "tests/bench-run.bats: 3 stub-based CLI-contract tests incl. error-subtype parse proof and byte-identical determinism proof (wall_clock_ms excluded, documented)"
affects: [01-03 live run, phase-2 baselines, phase-5 corpus]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "canned-output claude stub: executable in BATS_TEST_TMPDIR emitting schema-identical JSON then a chosen exit code, wired via CAIRN_BENCH_CLAUDE_BIN"
    - "run-outcome-as-data: every claude failure mode (non-zero exit, timeout, unparseable stdout, unlaunchable binary) becomes an is_error JSONL row; harness exits 0 unless usage error (2)"
    - "JSONL append with json.dumps(row, sort_keys=True) — deterministic field order for byte-identical comparison"

key-files:
  created:
    - benchmarks/scripts/bench-run.py
    - benchmarks/scripts/bench-run.sh
    - tests/bench-run.bats
  modified: []

key-decisions:
  - "CI lint glob for benchmarks/scripts/*.py was already present in ci.yml (pre-applied by plan-revision commit cc5d9e4) — verified via grep + running the exact extended py_compile command; no edit made"
  - "Unlaunchable claude binary (FileNotFoundError) is recorded as a synthesized is_error row, not a traceback — same data-not-failure philosophy the plan mandates for timeout and parse failure"

patterns-established:
  - "Stub seam contract: bats always sets CAIRN_BENCH_CLAUDE_BIN explicitly; a bare manual invocation naturally resolves to the real claude on PATH (no --live flag needed for plan 03)"

requirements-completed: [HARN-02, HARN-03]

# Metrics
duration: 14min
completed: 2026-07-25
---

# Phase 1 Plan 02: bench-run Harness + Stub-Based Contract Tests Summary

**bench-run.py measurement harness proven at zero API cost: stubbed claude via CAIRN_BENCH_CLAUDE_BIN, one sorted JSONL row per run wired to the real verify.sh, JSON parsed regardless of exit code, byte-identical determinism (wall-clock excluded)**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-07-25T23:42:34Z
- **Completed:** 2026-07-25T23:56:35Z
- **Tasks:** 2/2
- **Files modified:** 3 created (ci.yml verified already-correct, unmodified)

## Accomplishments

- `bench-run.py`: house docstring contract, `EXIT_OK`/`EXIT_USAGE` only, hand-rolled `--task`/`--out` parsing, `resolve_claude_bin()` seam, fixture staged to `mkdtemp("cairn-bench-")`, claude invoked as an argv list with the exact planned flags (`-p <prompt> --bare --output-format json --max-turns N --model claude-haiku --permission-mode acceptEdits --no-session-persistence`), `verify.sh` run against the workdir, one `sort_keys=True` JSONL line appended, workdir rmtree'd in `finally`.
- `bench-run.sh`: thin exec wrapper restating the Usage + exit-code contract, matching `cairn-map.sh` byte-for-byte in shape.
- `tests/bench-run.bats`: 3 tests, all against Plan 01's real `verify.sh`, never the real claude binary — success row (verify_passed genuinely false because the stub never solves the fixture), error_max_turns row with non-zero stub exit still carrying `usage`/`total_cost_usd`, and the determinism diff.

## Verification Evidence (all commands actually run)

| Check | Observed result |
|-------|-----------------|
| `python3 -m py_compile benchmarks/scripts/bench-run.py` | exit 0 |
| `test -x` both scripts | pass |
| `grep -c 'CAIRN_BENCH_CLAUDE_BIN'` bench-run.py / bench-run.bats | 2 / 5 |
| `grep -c 'shell=True' bench-run.py` | 0 |
| `--bogus-flag` and no-flags invocations | both print exit=2 |
| `grep -c 'EXIT_OK = 0'` / `'EXIT_USAGE = 2'` | 1 / 1 |
| `bats tests/bench-run.bats` | exit 0; TAP `1..3` all ok; pretty summary "3 tests, 0 failures" |
| `grep -qF` load 'helpers' / wall_clock_ms / error_max_turns in bench-run.bats | all present |
| `grep -qF 'benchmarks/scripts/*.py' .github/workflows/ci.yml` | present |
| `python3 -m py_compile cairn/scripts/*.py cairn/adapters/*.py cairn/capability/scripts/*.py benchmarks/scripts/*.py` (exact CI command) | exit 0 |
| Spot-check `CAIRN_BENCH_CLAUDE_BIN=/bin/false` (missing binary on this macOS) | exit 0; exactly 1 row; `{"is_error":true,"parse_error":"claude binary not found: [Errno 2]..."}` |
| Spot-check `CAIRN_BENCH_CLAUDE_BIN=/usr/bin/false` (launches, exits 1, empty stdout) | exit 0; exactly 1 row; `{"is_error":true,"parse_error":"Expecting value: line 1 column 1 (char 0)"}` |
| `bats tests/bench-run.bats tests/bench-verify.bats` (post-fix) | 6 tests, 0 failures |
| `bats tests/cairn-map.bats` (regression sample) | 12 tests, 0 failures |

Note: the plan's spot-check output path (`/tmp/cairngo-check.jsonl`) was routed to the session scratchpad directory per environment temp-file policy; identical semantics observed.

Not verified here (by design): any real `claude` invocation — zero API calls were made; the live-run schema validation is Plan 01-03's job.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Unlaunchable claude binary crashed the harness with a raw traceback**
- **Found during:** Plan-level verification spot-check (Task 2 complete, pre-summary)
- **Issue:** `subprocess.run` raises `FileNotFoundError` when the resolved claude binary does not exist; the plan's action only caught `TimeoutExpired` and `JSONDecodeError`, so the harness exited 1 with a traceback and wrote no row — violating both the repo's no-raw-traceback convention and the plan's own "a run's outcome is data, never a harness failure" truth
- **Fix:** catch `FileNotFoundError` alongside `TimeoutExpired`, synthesizing `{"is_error": true, "parse_error": "claude binary not found: ..."}`; docstring Behavior step 5 updated
- **Files modified:** benchmarks/scripts/bench-run.py
- **Commit:** 2f052b5

**2. [Rule 2 - Missing critical functionality] `die(EXIT_USAGE)` guard added for a missing prompt file**
- **Found during:** Task 1
- **Issue:** plan listed `die` cases for missing task dir / missing or unparseable task.json only; a missing `<task-dir>/<prompt_file>` would have raised a raw `FileNotFoundError` traceback
- **Fix:** `if not prompt_path.is_file(): die(f"prompt file not found: ...", EXIT_USAGE)` — same malformed-task-dir class as the plan's listed cases
- **Files modified:** benchmarks/scripts/bench-run.py
- **Commit:** 25651e2

### Observations (no code change)

- **CI edit already satisfied:** Task 2's ci.yml change (extend the lint glob with `benchmarks/scripts/*.py`) was already present — pre-applied by plan-revision commit cc5d9e4. Verified by grep and by running the exact extended `py_compile` command; ci.yml untouched by this plan. (Between cc5d9e4 and Task 1's commit, that glob matched nothing, which would have failed CI's lint step; Task 1 creating bench-run.py resolves it.)
- **Minor test addition within plan spirit:** `wall_clock_ms` presence assertions added to tests 1 and 2 so the determinism test's inline comment ("required present in every row, proven by the two tests above") is actually proven, not just claimed.

## Assumption Drift (advisory)

- **Found during:** Plan-level verification spot-check
- **Planned:** verification step assumed `/bin/false` exists (`env CAIRN_BENCH_CLAUDE_BIN=/bin/false ...`)
- **Actual:** Darwin 25.4.0 ships only `/usr/bin/false`; the literal spot-check therefore exercises the missing-binary path, not the launches-and-fails path
- **Why it matters:** this is exactly what surfaced deviation #1; both paths are now spot-checked and both yield one synthesized error row + exit 0

## Known Stubs

None introduced by this plan. (`fixture/convert.py`'s `NotImplementedError` remains 01-01's intentional unsolved starting state.)

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 25651e2 | feat(01-02): add bench-run harness with stubbable claude seam |
| 2 | 9b5b50c | test(01-02): prove bench-run contract via stubbed claude at zero API cost |
| fix | 2f052b5 | fix(01-02): record unlaunchable claude binary as an error row, not a traceback |

## Next Step

Plan 01-03 performs the single genuinely live `claude` run (seam unset → real binary on PATH), validates the real JSON schema against the stub's canned payload (RESEARCH.md Pitfall 2), and commits the first real JSONL row.

## Self-Check: PASSED

All 3 created files exist on disk; all three commits (25651e2, 9b5b50c, 2f052b5) present in git log.
