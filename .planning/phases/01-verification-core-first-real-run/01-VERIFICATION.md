---
phase: 01-verification-core-first-real-run
verified: 2026-07-25T00:00:00Z
status: passed
score: 4/4 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
---

# Phase 1: Verification Core + First Real Run Verification Report

**Phase Goal:** Prove the harness's two highest-uncertainty pieces — an objective, agent-unwritable pass/fail check and a real (non-stubbed) `claude -p` invocation — before any statistics or presentation layer is built on top of unverified assumptions
**Verified:** 2026-07-25
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria 1-4)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A task's `verify.sh` objectively passes against a hand-crafted "solved" fixture and fails against a hand-crafted "unsolved" fixture, proven by bats tests with no agent involved | VERIFIED | `bats tests/bench-verify.bats` -> 3/3 pass (independently re-run). `bash benchmarks/tasks/smoke-convert/verify.sh benchmarks/tasks/smoke-convert/fixture` independently re-run: exits 1 (unsolved fixture correctly fails). `verify.sh` lives at `benchmarks/tasks/smoke-convert/verify.sh`, one level above `fixture/` (`find` confirms no copy under `fixture/`); test 3 in bats asserts it never gets staged into the checked workdir. |
| 2 | `bench-run.py` executes one (task, baseline, rep) run against a stubbed `claude` binary via an env-var seam, and the deterministic harness logic runs in bats CI at zero API cost | VERIFIED | `bats tests/bench-run.bats` -> 3/3 pass (independently re-run). `resolve_claude_bin()` in `benchmarks/scripts/bench-run.py` reads `CAIRN_BENCH_CLAUDE_BIN` env var, falls back to `shutil.which("claude")`. Independently re-ran `bench-run.py` against a hand-written stub script (not the bats fixture) -- one JSONL row written, `verify_passed` correctly `false` since stub never edits the fixture. Zero real API calls involved in any stub-based test. |
| 3 | `bench-run.py` executes one real, non-stubbed `claude -p --output-format json` call and correctly captures `total_cost_usd`, full `usage` (input/output/cache_creation/cache_read), `duration_ms`, `duration_api_ms`, `num_turns`, and `is_error` into a JSONL row | VERIFIED | `benchmarks/results/smoke-convert.jsonl` contains 2 committed rows from genuinely live `claude -p` calls (git-committed at a8df90d). Independently parsed both rows with `jq`/`python3`: every required field (`total_cost_usd`, `usage.{input_tokens,output_tokens,cache_creation_input_tokens,cache_read_input_tokens}`, `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`) is present and non-null in both rows. Neither row carries `parse_error`. `task_id`/`wall_clock_ms`/`verify_passed` (harness-added fields) also present; `verify_passed:true` in both, matching a real `verify.sh` re-check. |
| 4 | Running the harness twice against the same stub input produces byte-identical JSONL output | VERIFIED | Independently re-ran `bench-run.py` twice against a self-authored stub (separate from the plan's bats fixture) into two fresh output files; `diff <(jq -S 'del(.wall_clock_ms)' out1) <(jq -S 'del(.wall_clock_ms)' out2)` produced zero output ("IDENTICAL"), confirming byte-identical output across all deterministic fields with only `wall_clock_ms` excluded (as documented). Bats test 3 in `tests/bench-run.bats` proves the same property independently. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `benchmarks/tasks/smoke-convert/verify.sh` | Objective exit-code checker, outside fixture/ | VERIFIED | Executable, lives at task-dir root; `find benchmarks/tasks/smoke-convert -name verify.sh` returns exactly one path, not under `fixture/` |
| `benchmarks/tasks/smoke-convert/task.json` | Task manifest | VERIFIED | Valid JSON: `id`, `timeout_s`, `max_turns`, `prompt_file`, plus `model` (full pinned id `claude-haiku-4-5-20251001`, added during live-run task per FAIR-02 early-adoption) |
| `benchmarks/tasks/smoke-convert/fixture/convert.py` | Unsolved starting state | VERIFIED | `raise NotImplementedError`, confirmed via direct read and by verify.sh failing against it |
| `benchmarks/tasks/smoke-convert/fixture/tests/test_convert.py` | FAIL_TO_PASS oracle | VERIFIED | 3 test methods, all fail against unsolved fixture (confirmed via direct execution) |
| `tests/bench-verify.bats` | bats proof of verify.sh contract | VERIFIED | 3 tests, all pass, zero API/agent involvement |
| `benchmarks/scripts/bench-run.py` | HARN-02 runner | VERIFIED | Compiles cleanly (`py_compile` exit 0), stdlib-only imports (json/os/shutil/subprocess/sys/tempfile/time/pathlib), no `shell=True`, `EXIT_OK=0`/`EXIT_USAGE=2` contract present |
| `benchmarks/scripts/bench-run.sh` | Thin wrapper | VERIFIED | Executable, exec's bench-run.py |
| `tests/bench-run.bats` | Stub-based CLI-contract tests | VERIFIED | 3 tests, all pass, zero API cost; canned payloads reconciled to real live-run schema (drift found and fixed per 01-03-SUMMARY) |
| `benchmarks/results/smoke-convert.jsonl` | First real committed benchmark data point | VERIFIED | 2 rows, both from genuine live `claude -p` calls, all HARN-02 fields non-null |
| `benchmarks/README.md` | Methodology doc | VERIFIED | Documents real observed cost (`0.1223481`, `0.167407`), the client-side-estimate caveat, the `CAIRN_BENCH_CLAUDE_BIN` seam mechanics, and observed exit-code/is_error findings |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/bench-verify.bats` | `benchmarks/tasks/smoke-convert/verify.sh` | `run bash <task-dir>/verify.sh <workdir>` | WIRED | Confirmed in bats file; independently re-run, passes |
| `benchmarks/tasks/smoke-convert/verify.sh` | `fixture/tests/test_convert.py` | `python3 -m unittest tests.test_convert -v` | WIRED | Confirmed by reading verify.sh; independently executed against both unsolved and hand-solved copies |
| `benchmarks/scripts/bench-run.py` | `CAIRN_BENCH_CLAUDE_BIN` env var | `resolve_claude_bin()` | WIRED | Function reads env var first, falls back to `shutil.which("claude")`; independently exercised with a custom stub, correctly routed |
| `benchmarks/scripts/bench-run.py` | `verify.sh` | `subprocess.run(["bash", verify_sh_path, workdir])` | WIRED | Confirmed in source; `verify_passed` field is computed from `verify_proc.returncode == 0`, not hardcoded -- proven by bats test 1 (`verify_passed:false` against a stub that never solves the fixture) and by the two live rows (`verify_passed:true`, matching real solved workdirs) |
| `tests/bench-run.bats` | `benchmarks/scripts/bench-run.py` | `env CAIRN_BENCH_CLAUDE_BIN=$STUB bash bench-run.sh ...` | WIRED | Confirmed in bats file, independently re-run |
| `.github/workflows/ci.yml` (Lint Python scripts) | `benchmarks/scripts/bench-run.py` | `python3 -m py_compile ... benchmarks/scripts/*.py` | WIRED | Confirmed: `grep` shows glob includes `benchmarks/scripts/*.py`; no `pytest`/`pip install` anywhere in ci.yml |

### Data-Flow Trace (Level 4)

`verify_passed` in the JSONL row is not a static/hardcoded value — traced to `verify_proc.returncode == 0` where `verify_proc` is a live `subprocess.run` of the real `verify.sh` against the actual staged (and possibly agent-modified) workdir. Confirmed two independent ways: (a) a stub-based bats/manual run that never edits `convert.py` correctly yields `verify_passed:false`; (b) the two committed live rows, where the real `claude` agent did edit the fixture, correctly yield `verify_passed:true`. Data genuinely flows end-to-end, not a stub value. FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| verify.sh fails on committed (unsolved) fixture | `bash benchmarks/tasks/smoke-convert/verify.sh benchmarks/tasks/smoke-convert/fixture` | exit 1, 3 unittest errors | PASS |
| bats suite for verify.sh contract | `bats tests/bench-verify.bats` | 3/3 pass | PASS |
| bats suite for bench-run.py contract | `bats tests/bench-run.bats` | 3/3 pass | PASS |
| bench-run.py compiles | `python3 -m py_compile benchmarks/scripts/bench-run.py` | exit 0 | PASS |
| Determinism (independent re-run, not just trusting bats) | ran bench-run.py twice against a self-authored stub, diffed JSONL excluding wall_clock_ms | zero diff | PASS |
| Live JSONL rows have all HARN-02 fields non-null | independently parsed `benchmarks/results/smoke-convert.jsonl` with python3/jq | both rows: all required fields present, non-null, no `parse_error` | PASS |
| Locked decision: stdlib-only | `grep -n "^import\|^from" benchmarks/scripts/bench-run.py` | json, os, shutil, subprocess, sys, tempfile, time, pathlib only | PASS |
| Locked decision: verify.sh outside fixture/ | `find benchmarks/tasks/smoke-convert -name verify.sh` | one file, at task-dir root | PASS |
| Locked decision: model pinned full id | `cat benchmarks/tasks/smoke-convert/task.json` | `"model": "claude-haiku-4-5-20251001"` | PASS |
| Locked decision: no Phase-2 machinery | `grep -n "baseline\|HOME" benchmarks/scripts/bench-run.py` | only a comment referencing future Phase 2 baseline work; no `--baseline` flag, no `HOME` override logic | PASS |
| CI lint covers benchmarks/scripts | `grep -n -A2 "Lint Python scripts" .github/workflows/ci.yml` | glob includes `benchmarks/scripts/*.py`; no pytest/pip install anywhere in ci.yml | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HARN-01 | 01-01 | Objective per-task verify.sh, bats-testable, zero API cost | SATISFIED | `tests/bench-verify.bats` 3/3 pass; verify.sh proven both directions. REQUIREMENTS.md checkbox still shows "Pending" — this is bookkeeping staleness (not part of any plan's `files_modified`), not a functional gap; the underlying requirement is functionally met. |
| HARN-02 | 01-02, 01-03 | bench-run.py invokes claude -p headless, writes JSONL with full field set | SATISFIED | Both stub-path (01-02) and live-path (01-03) proven; 2 live rows committed with all required fields. REQUIREMENTS.md already marks this Complete. |
| HARN-03 | 01-02 | Deterministic harness logic testable via stub seam; CI never pays API | SATISFIED | `CAIRN_BENCH_CLAUDE_BIN` seam confirmed; `tests/bench-run.bats` 3/3 pass at zero cost; CI's ci.yml has no pytest/pip-install step for this suite. REQUIREMENTS.md checkbox still shows "Pending" — same bookkeeping-staleness note as HARN-01. |

No orphaned requirements found: REQUIREMENTS.md's Phase 1 mapping (HARN-01/02/03) matches exactly what the three plans declare.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `benchmarks/scripts/bench-run.py` | 14 | Docstring's `Behavior` step 4 still lists `--bare` in the example claude invocation, but the actual `cmd` list (line ~112) deliberately omits `--bare` (removed live due to OAuth incompatibility, per inline comment at line 104 and 01-03-SUMMARY.md) | INFO | Documentation drift only — the inline comment at the omission site correctly explains the deviation, and `benchmarks/README.md` documents it accurately. Does not affect behavior or any must-have. Worth a follow-up docstring fix but not goal-blocking. |

No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers found in any phase 1 file. No `pytest` references anywhere in `benchmarks/`. No `shell=True` in bench-run.py.

### Human Verification Required

None. All truths for this phase are mechanically verifiable (exit codes, JSON field presence, byte-diff determinism) and were independently re-executed during this verification, not merely trusted from SUMMARY.md claims.

### Gaps Summary

No gaps. All 4 ROADMAP success criteria independently re-verified against the live codebase (not merely re-reading SUMMARY.md claims): both bats suites re-run and passing (6/6 total), verify.sh's solved/unsolved behavior independently re-executed, bench-run.py's determinism independently re-proven against a self-authored stub (not the committed bats fixture, to avoid circular trust), and the two live JSONL rows independently parsed and field-checked. All locked decisions from 01-CONTEXT.md honored: stdlib-only (zero pip deps, confirmed via import list), verify.sh outside fixture/, model pinned as a full id in task.json, and no Phase-2 machinery (no `--baseline` flag or `HOME` override) leaked into bench-run.py. CI's lint glob correctly covers `benchmarks/scripts/*.py` with no new pytest dependency.

The only deviations from the original plans (two live rows instead of one; `--bare` removed; out-dir validated before spend; model pinned as a hard requirement) were explicitly requested/expected per the verification task's own instructions (2 rows) or are well-documented, evidence-backed corrections discovered during the live run and recorded transparently in 01-03-SUMMARY.md and benchmarks/README.md — none weaken any ROADMAP success criterion.

One minor bookkeeping note (not a gap): REQUIREMENTS.md's checkboxes for HARN-01 and HARN-03 still show "Pending" even though the functional work is complete and verified; this is standard end-of-phase orchestrator bookkeeping (checkbox sync), not a code or functionality gap.

---

*Verified: 2026-07-25*
*Verifier: Claude (gsd-verifier)*
