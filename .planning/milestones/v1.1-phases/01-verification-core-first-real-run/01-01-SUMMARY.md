---
phase: 01-verification-core-first-real-run
plan: 01
status: complete
subsystem: testing
tags: [benchmark, bats, unittest, verify-oracle, fixture]

# Dependency graph
requires: []
provides:
  - "smoke-convert task fixture: task.json manifest, prompt.md, unsolved convert.py, 3-case unittest FAIL_TO_PASS oracle"
  - "verify.sh objective exit-code checker (verify.sh <workdir>, exit 0 = solved), living at the task-dir root, never inside any workdir"
  - "tests/bench-verify.bats: bats proof of the exit-code contract against hand-crafted unsolved and solved states, zero API cost"
affects: [01-02 bench-run harness, 01-03, phase-2 baselines, phase-5 corpus]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "verify.sh oracle: exit code is the sole pass/fail signal, invoked with the workdir path as its only argument"
    - "stdlib-only fixture testing via python3 -m unittest tests.test_convert (namespace package, no __init__.py, no conftest)"
    - "bats file defines local BENCH_TASKS_DIR off CAIRN_REPO_ROOT (hooks.bats local-dir-var pattern); tests/helpers.bash untouched"

key-files:
  created:
    - benchmarks/tasks/smoke-convert/task.json
    - benchmarks/tasks/smoke-convert/prompt.md
    - benchmarks/tasks/smoke-convert/fixture/convert.py
    - benchmarks/tasks/smoke-convert/fixture/tests/test_convert.py
    - benchmarks/tasks/smoke-convert/verify.sh
    - tests/bench-verify.bats
  modified: []

key-decisions:
  - "stdlib unittest, not pytest, for the fixture suite and verify.sh invocation — keeps the harness genuinely stdlib-only (CONTEXT.md locked decision); zero third-party deps, CI needs no install step"
  - "verify.sh lives at the task-dir root, one level above fixture/, so it is structurally impossible to stage into an agent workdir by copying fixture/"

patterns-established:
  - "Task oracle contract: verify.sh <workdir> — exit 0 solved, non-zero not solved; proven against both hand-crafted states before any runner exists"

requirements-completed: [HARN-01]

# Metrics
duration: 5min
completed: 2026-07-25
---

# Phase 1 Plan 01: Verification Core Fixture + verify.sh Oracle Summary

**smoke-convert benchmark fixture with an agent-unwritable verify.sh whose exit code is proven (via bats, zero API calls) to be the sole pass/fail signal in both directions**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-07-25T23:33:52Z
- **Completed:** 2026-07-25T23:38:33Z
- **Tasks:** 2/2
- **Files modified:** 6 created

## Accomplishments

- Built the full smoke-convert task directory: `task.json` (id/timeout_s/max_turns/prompt_file), `prompt.md` (exact vetted prompt text), unsolved `fixture/convert.py` (`raise NotImplementedError`), and the 3-case `fixture/tests/test_convert.py` FAIL_TO_PASS oracle (freezing 0→32, boiling 100→212, body temp 37→98.6).
- `verify.sh` at the task-dir root: `#!/usr/bin/env bash`, `set -euo pipefail`, `cd "$1"`, `exec python3 -m unittest tests.test_convert -v` — the workdir is only ever a path argument.
- `tests/bench-verify.bats` proves HARN-01: unsolved copy → non-zero, hand-solved copy (`c * 9 / 5 + 32`) → zero, and the checker never leaks into the checked workdir.

## Verification Evidence (all commands actually run)

| Check | Observed result |
|-------|-----------------|
| `bats tests/bench-verify.bats` | exit 0; TAP `ok 1..3`; pretty formatter summary "3 tests, 0 failures" |
| `bash benchmarks/tasks/smoke-convert/verify.sh benchmarks/tasks/smoke-convert/fixture` | exit 1 (committed fixture stays unsolved) |
| Manual unsolved-copy proof (fixture copied to a throwaway dir, `python3 -m unittest tests.test_convert -v`) | "Ran 3 tests ... FAILED (errors=3)", exit 1 |
| `python3 -m json.tool task.json` | exit 0; contains smoke-convert, timeout_s, max_turns, prompt_file |
| `grep -c 'raise NotImplementedError' fixture/convert.py` | 1 |
| `grep -c 'def test_' fixture/tests/test_convert.py` | 3 |
| `test -x verify.sh` / `test ! -f fixture/verify.sh` | both pass |
| `grep -ri pytest benchmarks/` | 0 matches (stdlib-only confirmed) |
| `grep -c '@test' tests/bench-verify.bats`; `load 'helpers'`; `BENCH_TASKS_DIR` | 3; present; present |

Note: the manual unsolved-copy proof ran in the session scratchpad directory instead of the plan's literal `/tmp/cairngo-manual-check` path (environment policy routes temp files to the session scratchpad); identical copy/run/assert semantics, observed exit 1, throwaway dir removed after.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- `benchmarks/tasks/smoke-convert/fixture/convert.py` — `celsius_to_fahrenheit` raises `NotImplementedError` **by design**: it is the deliberately unsolved FAIL_TO_PASS starting state the benchmark hands to an agent. It must remain unsolved in the repo; solving it would invalidate the fixture (plan 01-02's runner stages a copy for the agent to solve).

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 4e77753 | feat(01-01): add smoke-convert task fixture with objective verify.sh oracle |
| 2 | bbb6c57 | test(01-01): prove verify.sh exit code is the sole pass/fail signal |

## Next Step

Plan 01-02 builds `bench-run.py`/`bench-run.sh` on top of this proven oracle (stub-seam `CAIRN_BENCH_CLAUDE_BIN`, JSONL rows), consuming `task.json` and invoking `verify.sh` exactly as contracted here.

## Self-Check: PASSED

All 7 claimed files exist on disk; both task commits (4e77753, bbb6c57) present in git log.
