---
phase: 01-verification-core-first-real-run
plan: 03
status: complete
subsystem: benchmarks
tags: [benchmark, live-run, schema-validation, jsonl, cost, oauth]

# Dependency graph
requires:
  - "01-01: smoke-convert fixture + verify.sh oracle (the live runs' pass/fail judge)"
  - "01-02: bench-run.py harness + CAIRN_BENCH_CLAUDE_BIN seam (seam left unset = live run)"
provides:
  - "benchmarks/results/smoke-convert.jsonl: two committed rows from genuinely live claude -p runs (error_max_turns $0.1223481 + success $0.167407), every HARN-02 field non-null"
  - "benchmarks/README.md: methodology, real observed costs, client-side-estimate caveat, exit/is_error findings, --bare x OAuth finding, ~$2.88 total-spend transparency"
  - "tests/bench-run.bats reconciled: stub payloads key-for-key identical to the live schema (drift found and fixed)"
  - "01-RESEARCH.md Open Questions 1 AND 2 marked (RESOLVED) with empirical notes"
affects: [phase-2 baselines (ANTHROPIC_API_KEY requirement), phase-3 aggregation (verify_passed vs is_error axes), phase-5 corpus]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "live-run trigger = seam left unset (no --live flag), exactly as designed in 01-02"
    - "model id must be a full pinned id from task.json (bare aliases rejected by the API) — FAIR-02 enforced early"
    - "out-dir validated before any API spend (money-losing failure class dies at usage-error time)"

key-files:
  created:
    - benchmarks/results/smoke-convert.jsonl
    - benchmarks/README.md
  modified:
    - benchmarks/scripts/bench-run.py
    - benchmarks/tasks/smoke-convert/task.json
    - tests/bench-run.bats
    - .planning/phases/01-verification-core-first-real-run/01-RESEARCH.md

key-decisions:
  - "--bare removed from the harness invocation: verified live that it skips claude.ai OAuth and demands an API key — Phase 2 isolated baselines must pair --bare with ANTHROPIC_API_KEY"
  - "Two rows committed (error_max_turns + success) instead of the plan's one: the max-turns-5 first run and the max-turns-8 second run together prove verify_passed and is_error are independent axes (feeds METR-02)"
  - "subtype is not a success signal: auth failure emits subtype:'success' with is_error:true — is_error/terminal_reason are the reliable signals"

patterns-established:
  - "Cost transparency: every cost report carries the client-side-estimate caveat; total validation spend (~$2.88) published including the lost row and the operator-environment overhead"

requirements-completed: [HARN-02]

# Metrics
duration: 44min (incl. ~20min auth-gate checkpoint pause)
completed: 2026-07-26
---

# Phase 1 Plan 03: Live Run + Schema Reconciliation Summary

**Two genuinely live claude -p rows committed ($0.1223481 error_max_turns + $0.167407 success, both verify_passed:true), bats stub rebuilt key-for-key against the real schema, README documents real costs with the client-side-estimate caveat, both RESEARCH.md open questions resolved empirically**

## Performance

- **Duration:** ~44 min wall (executor active ~24 min; ~20 min paused at the auth-gate checkpoint)
- **Started:** 2026-07-25T23:59:28Z
- **Completed:** 2026-07-26T00:44:05Z
- **Tasks:** 2/2
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- First real benchmark data committed: `benchmarks/results/smoke-convert.jsonl`, two rows from live `claude -p --output-format json` calls through `bench-run.py`, every HARN-02 field (`total_cost_usd`, full `usage`, `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`) present and non-null, `wall_clock_ms` from the harness's own timer, no `parse_error`.
- Stub-vs-real reconciliation (RESEARCH Pitfall 2 closed): drift FOUND — the live schema carries `terminal_reason`, `stop_reason`, `uuid`, `modelUsage`, `permission_denials`, `fast_mode_*`, `api_error_status`, `time_to_request_ms`, `ttft_ms`, `ttft_stream_ms`, `errors[]`, and nested `usage.cache_creation`/`server_tool_use`/`service_tier`/`speed`/`inference_geo`/`iterations`. Stub payloads rebuilt; programmatic key-path diff now reports zero missing/extra keys both ways; passthrough asserts added.
- `benchmarks/README.md` written: scope boundary (baselines/isolation/repetition = Phase 2/3, not built), zero-cost suite command, seam mechanics, exact live command, real costs quoted exactly, client-side-estimate caveat, observed-behavior register, drift note.
- RESEARCH.md Open Questions 1 and 2 both marked `(RESOLVED)` with inline `RESOLVED:` notes (Q1: empirical is_error/terminal_reason findings, A1 MEDIUM→HIGH; Q2: single fixture kept, diversity → Phase 5/CORP-01).

## Verification Evidence (all commands actually run)

| Check | Observed result |
|-------|-----------------|
| `wc -l benchmarks/results/smoke-convert.jsonl` | 2 rows |
| `jq -e` all HARN-02 fields non-null, both rows | exit 0 ("ALL FIELDS OK") |
| `jq -e 'has("parse_error")'` | exit 1 (absent — genuine schema-conformant responses) |
| Programmatic key-path diff stub vs real rows (success + error) | `missing=NONE extra=NONE` both directions, both subtypes |
| `bats tests/bench-verify.bats tests/bench-run.bats` | 6 tests, 0 failures (post-reconciliation, post-harness-fixes) |
| `python3 -m py_compile benchmarks/scripts/bench-run.py` | exit 0 |
| README cost figures vs `jq -r '.total_cost_usd'` | 0.1223481 and 0.167407 both quoted exactly, grep -qF confirmed |
| Task 2 `<verify>` chain (grep total_cost_usd, CAIRN_BENCH_CLAUDE_BIN, (RESOLVED), RESOLVED:) | PASS |
| `bench-run.py` process exit on both live runs | 0 (observed by orchestrator; consistent with EXIT_OK contract) |

## The live runs (observed data)

| subtype | is_error | num_turns | total_cost_usd | duration_api_ms | verify_passed |
|---|---|---|---|---|---|
| error_max_turns (cap 5) | true | 6 | 0.1223481 | 17078 | **true** |
| success (cap 8) | false | 6 | 0.167407 | 18638 | true |

Key finding (feeds METR-02): **verify_passed ⊥ is_error** — the error_max_turns run had already solved the fixture before hitting the cap. Also observed: `num_turns` can exceed `--max-turns` by one; `acceptEdits` genuinely gated Bash (`permission_denials` records the agent's blocked pytest/unittest attempts in both rows).

**Total validation spend: ~$2.88** = ~$1.29 (orchestrator's direct auth/schema validation from the global environment, ~62k cache-creation tokens of ambient overhead — living evidence of the home-field-advantage pitfall Phase 2's isolation eliminates) + ~$1.30 (row lost to the out-dir bug, now guarded) + $0.1223481 + $0.167407 (committed rows).

## Deviations from Plan

### Auto-fixed / orchestrator-applied issues (validated and committed by this plan)

**1. [Rule 1 - Bug] Out-dir validated before API spend**
- **Found during:** orchestrator's live run (a row was lost to `FileNotFoundError` AFTER spending ~$1.30)
- **Fix:** `bench-run.py` now dies `EXIT_USAGE` if `--out`'s parent dir is missing, before any claude invocation
- **Files modified:** benchmarks/scripts/bench-run.py — **Commit:** a5daa66

**2. [Rule 3 - Blocking] `--bare` removed from the harness invocation**
- **Found during:** live auth validation — `--bare` skips claude.ai OAuth credentials and reports "Not logged in" even on a logged-in machine (requires API key via env/`--settings`)
- **Fix:** flag removed with an explanatory comment; documented in README. Phase 2's isolated baselines must pair `--bare` with `ANTHROPIC_API_KEY`
- **Impact on threat model:** T-01-08 listed `--bare` as a mitigation; compensating controls remain (no `--add-dir`, `acceptEdits` — proven working by `permission_denials` in both rows — and the disposable mktemp workdir). See Threat Flags.
- **Files modified:** benchmarks/scripts/bench-run.py — **Commit:** a5daa66

**3. [Rule 1 - Bug] Model must be a full pinned id from task.json**
- **Found during:** live run — the bare alias `claude-haiku` was rejected by the API (RESEARCH A3's fail-fast prediction held)
- **Fix:** `task.json` now carries required `"model": "claude-haiku-4-5-20251001"`; harness dies `EXIT_USAGE` if absent. FAIR-02's pinning discipline arrived one phase early, by necessity
- **Files modified:** benchmarks/scripts/bench-run.py, benchmarks/tasks/smoke-convert/task.json — **Commit:** a5daa66

**4. [Coordinator override] Two rows committed instead of the plan's exactly-one**
- The first API-reaching run hit `error_max_turns` at cap 5 (fixture solved anyway); a second run at cap 8 captured the success subtype. Both are real data and together prove the verify_passed/is_error independence. `task.json`: timeout_s 60→120, max_turns 5→8. Plan's `wc -l == 1` acceptance superseded by coordinator instruction.

### Stub drift (planned reconciliation — drift WAS found)

The pre-live canned payloads were missing every live-only field listed in Accomplishments; `tests/bench-run.bats` rebuilt (commit add82e0) and re-verified green.

## Authentication Gates

- **Task 1, first execution attempt:** every subagent-context invocation returned `"Not logged in · Please run /login"` (`subtype:"success"`, `is_error:true`, `terminal_reason:"api_error"`, $0, zero usage — no API contact). Three $0 attempts (sandboxed, unsandboxed, nested-env-vars cleaned) all failed: the subagent execution context cannot use the keychain OAuth credential. Returned a `human-action` checkpoint; the orchestrator (whose context CAN reach the keychain) executed the live runs and handed the rows back. Documented as normal flow.

## Assumption Drift (advisory)

- **Found during:** Task 1
- **Planned:** the executor's own shell could trigger the live run (seam unset → real `claude` on PATH)
- **Actual:** headless OAuth only works from the operator/orchestrator context; subagent contexts and `--bare` both fail auth
- **Why it matters:** future phases must route live runs through an operator context or provision `ANTHROPIC_API_KEY`; recorded in README for Phase 2 planning.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: mitigation-changed | benchmarks/scripts/bench-run.py | T-01-08's `--bare` mitigation removed (OAuth-incompatible). Compensating controls verified live: `acceptEdits` blocked all agent Bash attempts (`permission_denials` non-empty in both rows), no `--add-dir`, disposable mktemp workdir. Phase 2 must restore `--bare` alongside `ANTHROPIC_API_KEY`. |

## Known Stubs

None. (`fixture/convert.py`'s `NotImplementedError` remains the intentional unsolved starting state in the repo; the live agents solved it only inside their disposable workdir copies, which is exactly the design.)

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | a5daa66 | fix(01-03): guard out-dir before API spend, drop --bare, pin model via task.json |
| 1 | a8df90d | feat(01-03): commit first real benchmark rows from live claude -p runs |
| 1 | add82e0 | test(01-03): reconcile claude stub schema with live response shape |
| 2 | 1394685 | docs(01-03): benchmark methodology, observed live cost, schema findings |

## Next Step

Phase 1 complete pending orchestrator bookkeeping (ROADMAP/bd handled upstream). Phase 2 planning inherits: ANTHROPIC_API_KEY requirement for `--bare` isolation, pinned-model discipline already in task.json, and the verify_passed/is_error axis separation for metric design.

## Self-Check: PASSED

All 6 created/modified files exist on disk; all four commits (a5daa66, a8df90d, add82e0, 1394685) present in git log.
