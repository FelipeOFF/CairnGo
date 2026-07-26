---
phase: 03-repetition-aggregation-cost-decomposition
verified: 2026-07-26T04:54:41Z
status: passed
score: 4/4 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
---

# Phase 3: Repetition, Aggregation & Cost Decomposition Verification Report

**Phase Goal:** Comparative numbers are statistically defensible — repeated enough times, gated on success, and aggregated deterministically — instead of single-run point estimates
**Verified:** 2026-07-26T04:54:41Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, METR-01..03)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each (task, baseline) cell runs N≥5 repetitions, and `bench-aggregate.py` reports median plus spread per task, not only a single blended aggregate | VERIFIED | `bench-matrix.py --reps` defaults to 5 (live default, not merely parsed — `bats` test "omits --reps and still defaults to 5" produces 15 rows for 3 baselines with no flag). Independently reran `bench-matrix.py --baselines vanilla,gsd-only,cairn --reps 5 --seed 42` against a hand-authored stub (not the bats fixture): 15 rows, every baseline's `rep_index` set is exactly `{0,1,2,3,4}`. `bench-aggregate.py`'s `cell_stats()` computes `cost_median`/`cost_min`/`cost_max`/`cost_iqr` **per** `(task_id, baseline_id)` cell (`out["cells"][f"{task_id}::{baseline_id}"]`), never one blended figure across cells. |
| 2 | A run that fails `verify.sh` is excluded from the cost/token averages entirely — cost-per-successfully-completed-task is the only headline number produced | VERIFIED | `is_headline_pass(row) = row.get("verify_passed") is True and not row.get("is_error", False)` gates every stat in `cell_stats()` (`costs = sorted(r["total_cost_usd"] for r in passed if ...)`, `components = [token_components(r) for r in passed]`). Independently confirmed on the `beta` cell (fixture `aggregate-gating-b.jsonl`, row 1: `verify_passed:true, is_error:true`): `n_total=3, n_passed=1` — the belt-and-braces row is counted in `n_total` but excluded from `n_passed`/cost/tokens even though `verify_passed` alone would have passed it. `gamma` cell (all rows fail) reports `pass_rate: 0.0` with `cost_median/min/max/iqr: null` and `tokens.*_median: null` — never a silent drop of the cell, never a fabricated `0` for cost. |
| 3 | Running `bench-aggregate.py` twice against the same raw JSONL produces a byte-identical `aggregated.json` | VERIFIED | `bats` tests "running twice against identical input yields byte-identical aggregated.json" (true `diff`, no `jq -S` normalization) and "multiple --in files combine identically regardless of argument order" both pass. `load_rows()` iterates `sorted(paths)`; `main()` iterates `sorted(cells)` keys; output written via `json.dumps(out, sort_keys=True, separators=(",", ":"))` with zero timestamps in the artifact. |
| 4 | `aggregated.json` reports all four cost/token components per cell separately (uncached-input, cache-write, cache-read, output), never one blended figure | VERIFIED | `token_components()` returns `{input, cache_creation, cache_read, output}` as 4 separate keys; `cell_stats()` emits `tokens.{input,cache_creation,cache_read,output}_{sum,median}` — 8 distinct fields, never summed into one number. Independently hand-computed the `alpha` cell's 4-way sums/medians from the fixture's raw per-row values and the script's output matched exactly (input_sum=52/median=13.0, cache_creation_sum=460/median=115.0, cache_read_sum=860/median=215.0, output_sum=230/median=57.5). |

**Score:** 4/4 truths verified

### PLAN.md-Level Must-Haves (03-01, 03-02 frontmatter)

| Must-have | Status | Evidence |
|-----------|--------|----------|
| `bench-matrix.py --reps` defaults to 5, launches 5 invocations/baseline | VERIFIED | `--help` shows `--reps N` default 5; live-default bats test confirms 15 rows with no flag |
| Every row carries `rep_index` alongside `seed`/`run_order_index` | VERIFIED | Independent stub run: `jq -e '[.rep_index,.seed,.run_order_index] | all(. != null)'` true on all 15 rows |
| Seeded shuffle spans full baseline x rep cross-product — no contiguous block | VERIFIED | Independent run at `--seed 42`: per-baseline `run_order_index` spread (max-min) = 13/8/6, never 4 (the contiguous-block signature). Plan's own seed-7 case also bats-verified. |
| Same `--seed` → byte-identical execution order across invocations | VERIFIED | Independent double-run at `--seed 42 --reps 5`: `diff` of `baseline_id` sequence and of `[rep_index,seed,run_order_index]` sequence both empty |
| `bench-run.py --rep-index` optional, zero regression when omitted | VERIFIED | `tests/bench-run.bats` 8/8 unchanged; `--rep-index abc` dies `EXIT_USAGE` naming the flag (code inspection, mirrors `--run-order-index` exactly) |
| `bench-aggregate.py`: real fixture rows never counted as savings | VERIFIED | Independent run on `benchmarks/results/smoke-convert.jsonl` alone: `{"cells":{},"rejected_rows":2}` (both real rows predate `baseline_id`) |
| Belt-and-braces: `verify_passed=true, is_error=true` never in `n_passed` | VERIFIED | `beta` cell: `n_total=3, n_passed=1` (code inspection + fixture evidence, both agree) |
| All-fail cell reports `pass_rate 0.0`, null stats, not dropped | VERIFIED | `gamma` cell present in output with `pass_rate:0.0`, all cost/token medians `null` |
| Rejected rows counted, never silently dropped | VERIFIED | `rejected_rows` field present and correct on every scenario tested (real-only: 2; mixed: 2; malformed-line bats test) |
| Double-run byte-identical `aggregated.json` | VERIFIED | bats + independent manual double-run both empty-diff |
| `modelUsage` preferred over `usage`, `usage` fallback when absent | VERIFIED | `token_components()` code inspection: `mu = row.get("modelUsage"); if mu: ... return agg` before falling to `usage`; fixture row 4 (no `modelUsage`) correctly produced `input=16` from `usage.input_tokens` |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `benchmarks/scripts/bench-run.py` | optional `--rep-index`, conditional row stamp | VERIFIED | `opts["rep_index"]` default `None`; argv branch mirrors `--run-order-index`; `if opts["rep_index"] is not None: row["rep_index"] = ...` |
| `benchmarks/scripts/bench-matrix.py` | `--reps` (default 5), cross-product `build_execution_order` | VERIFIED | `itertools.product(baselines, range(reps))` shuffled once via `random.Random(seed)`; `--rep-index` passed through to every `bench-run.py` invocation |
| `tests/bench-matrix.bats` | interleaving/rep_index/live-default coverage | VERIFIED | 9/9 tests pass (2 new + 5 pre-existing @ `--reps 1` + 2 more), `--reps 1` backfilled on all 4 pre-existing invocations |
| `benchmarks/scripts/bench-aggregate.py` | success-gated, 4-way decomposed, deterministic aggregator | VERIFIED | Full function set (`load_rows`, `is_headline_pass`, `token_components`, `group_cells`, `cell_stats`, `main`) present and matches plan's pre-verified algorithm verbatim |
| `benchmarks/scripts/bench-aggregate.sh` | thin CLI wrapper | VERIFIED | Executable (`-rwxr-xr-x`), matches `bench-run.sh` template |
| `tests/fixtures/aggregate-gating-a.jsonl`, `-b.jsonl` | 10 hand-verifiable synthetic rows | VERIFIED | 5+5 lines, all valid JSON, values match plan's Interfaces block exactly (byte comparison of resulting stats) |
| `tests/bench-aggregate.bats` | 6 tests: rejection, gating, decomposition, order-independence, determinism, CLI errors | VERIFIED | 6/6 pass |
| `benchmarks/README.md` | documents both features, closes "Phase 3 scope" stub note | VERIFIED | `grep -c 'Phase 3 scope'` == 0; "Repetitions" and "Aggregation" sections present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `bench-matrix.py` | `bench-run.py` | `subprocess.run(cmd)` with `--rep-index str(rep_idx)` | WIRED | Confirmed in code and by independent stub run — every row carries a non-null `rep_index` |
| `bench-run.py` row assembly | `row["rep_index"]` | conditional dict merge | WIRED | Confirmed: omitted flag → key absent (bats: `has("rep_index") | not`); present flag → JSON integer |
| `bench-aggregate.py main()` | `aggregated.json` cells | `out["cells"][f"{task_id}::{baseline_id}"] = cell_stats(...)` | WIRED | Confirmed via independent run producing exactly 3 cell keys for the 2-fixture input |
| `bench-aggregate.py load_rows()` | `aggregated.json` rejected_rows | counted, never dying | WIRED | Confirmed: real-only run → `rejected_rows: 2`, `cells: {}` |
| `bench-aggregate.py cell_stats()` | `is_headline_pass()` | `passed = [r for r in rows if is_headline_pass(r)]` | WIRED | Confirmed via belt-and-braces `beta` cell result |

### Data-Flow Trace (Level 4)

Not applicable in the UI-rendering sense (this phase produces no rendered component). Data-flow was traced end-to-end instead: raw JSONL rows (real committed rows + independently-generated stub rows) → `bench-aggregate.py` → `aggregated.json` cell stats, hand-recomputed independently and matched byte-for-byte. No hardcoded/static stand-in values found anywhere in the gating or decomposition path.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `--reps` defaults to 5, live | `bench-matrix.py --baselines vanilla,gsd-only,cairn --seed 42 --reps 5` (own stub, own run, twice) | 15 rows both times, byte-identical `baseline_id` and provenance sequences | PASS |
| No contiguous-block interleave at an independently-chosen seed | jq spread check on 15-row output | spreads 13/8/6 (never 4) | PASS |
| `bench-aggregate.py` on real committed rows alone | `--in benchmarks/results/smoke-convert.jsonl` | `{"cells":{},"rejected_rows":2}` | PASS |
| `bench-aggregate.py` on synthetic fixtures, hand-verified | `--in aggregate-gating-a.jsonl --in aggregate-gating-b.jsonl` | `alpha` cell matches hand-computed median/min/max/IQR/4-way sums exactly | PASS |
| `py_compile` all benchmark scripts | `python3 -m py_compile benchmarks/scripts/*.py` | exit 0 | PASS |
| No live API calls outside the stub seam | `grep -rn 'resolve_claude_bin\|CAIRN_BENCH_CLAUDE_BIN'` across scripts + bats | only `resolve_claude_bin()` (env-var-first) and bats stub setup; no bare `claude -p` invocation anywhere | PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention exists in this repo and neither PLAN nor SUMMARY declares probes; skipped per Step 7c (no probes declared or found).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| METR-01 | 03-01, 03-02 | N≥5 repetitions per cell; median+spread per task, not only aggregate | SATISFIED | `--reps` default 5 + interleaved cross-product (03-01); `cell_stats()` per-cell median/min/max/IQR (03-02) |
| METR-02 | 03-02 | Cost/tokens per task computed only over successfully-completed (verify-gated) runs | SATISFIED | `is_headline_pass()` belt-and-braces gate, independently confirmed on `beta`/`gamma` cells |
| METR-03 | 03-02 | Deterministic aggregator: JSONL → aggregated.json repeatable byte-for-byte | SATISFIED | `sorted()` on paths/cells + `sort_keys=True` + fixed separators; double-run and argument-order-shuffle diffs both empty |

Note: `.planning/REQUIREMENTS.md` still shows METR-01/02/03 as unchecked/"Pending" and `.planning/ROADMAP.md`'s progress table still shows Phase 3 as "Not started" / "0/2" — this is stale project bookkeeping, not a functional gap; the code-level evidence above is unambiguous. Flagged in STATE.md's Blockers/Concerns for the next planning session to sync.

### Anti-Patterns Found

None. Scanned all phase-3-modified files (`bench-run.py`, `bench-matrix.py`, `bench-aggregate.py`, `bench-aggregate.sh`, `tests/bench-matrix.bats`, `tests/bench-aggregate.bats`, both fixture files, `benchmarks/README.md`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|not yet implemented|coming soon` — zero matches.

### Locked-Decision Compliance (03-CONTEXT.md)

| Locked decision | Status | Evidence |
|---|---|---|
| Single `--task` this phase (multi-task cells deferred to Phase 5) | HELD | `bench-matrix.py` CLI still takes one `--task <TASK_DIR>` argument; `aggregated.json` schema is already keyed `task_id::baseline_id` so Phase 5 can extend without breaking, but no multi-task code exists yet |
| No Phase 4 (competitor) leakage | HELD | `benchmarks/baselines/` still holds exactly 3 manifests (vanilla, gsd-only, cairn); no 4th baseline introduced |
| No Phase 5 (corpus)/Phase 6 (report/charts) leakage | HELD | `git log` on every phase-3-touched file shows only 03-01/03-02 commits; no chart/report code, no corpus-expansion code |
| Zero live API calls | HELD | Every bats test and every independent verification run in this report used `CAIRN_BENCH_CLAUDE_BIN` pointed at a local stub; `resolve_claude_bin()` is the only real-binary fallback path and was never exercised |

## Full Bench Bats Suite

`bats tests/bench-verify.bats tests/bench-run.bats tests/bench-matrix.bats tests/stage-plugins.bats tests/bench-aggregate.bats` → **29/29 passing** (1..29, all `ok`), covering Phases 1, 2, and 3 with zero regressions.

### Human Verification Required

None. This phase is a headless CLI/data-pipeline component (no UI, no visual, no external service, no real-time behavior) — every truth is programmatically verifiable and was verified both via the bats suite and independent re-execution outside it.

### Gaps Summary

No gaps. All 4 ROADMAP success criteria, all plan-level must-haves, all key links, and all locked decisions verified against the real codebase via independent re-execution (not SUMMARY.md claims). The only non-blocking observation is stale bookkeeping in `.planning/ROADMAP.md`/`.planning/REQUIREMENTS.md` (still marked "Not started"/"Pending" for Phases 1-3), noted in STATE.md's Blockers/Concerns for a future docs-sync pass — it does not affect Phase 3's actual goal achievement.

---

*Verified: 2026-07-26T04:54:41Z*
*Verifier: Claude (gsd-verifier)*
