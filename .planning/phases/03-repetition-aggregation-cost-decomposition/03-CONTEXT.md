# Phase 3: Repetition, Aggregation & Cost Decomposition - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning
**Source:** Autonomous run — locked from project research + Phases 1-2 deliverables. Gray areas are Claude's Discretion.

<domain>
## Phase Boundary

Results become statistically honest: N≥5 repetitions per cell (task × baseline), success-gated cost metrics, deterministic aggregation with full 4-way cost decomposition. Requirements: METR-01 (repetitions + median/spread per task), METR-02 (success-gated cost), METR-03 (deterministic bench-aggregate.py). bd issues: CairnGo-x60, CairnGo-uyr, CairnGo-o7b — see `03-BEADS-MAP.md`.

</domain>

<decisions>
## Implementation Decisions (locked)

### Repetition (METR-01)
- `--reps N` lands in `bench-matrix.py` (the orchestrator — bench-run.py stays single-run by design). Default N=5; the plan may allow lower N only via explicit flag for pilots.
- Interleaving covers reps too: the seeded shuffle spans the full cell list (task × baseline × rep), so same-arm runs are not consecutive (cache fairness, FAIR-03 extended). Each row records `rep_index` alongside `seed`/`run_order_index`.
- Median + spread (IQR or min/max) reported PER task × baseline, never only aggregate. stdlib `statistics` only.

### Success gating (METR-02)
- Headline cost/token metrics computed ONLY over rows with `verify_passed == true`. Failed rows are never "cheaper" — they surface as `pass_rate` (n_passed/n_total) per cell, reported alongside.
- A cell with pass_rate 0 reports null metrics + the failure count (no silent drop).
- `is_error` rows (api_error, max_turns etc.) count as failures for gating even if verify accidentally passes — both gates must hold (belt-and-braces; Phase 1 proved the axes are independent).

### Aggregation (METR-03)
- New `bench-aggregate.py` (+ .sh wrapper, house style): reads raw JSONL (one or more files), emits `aggregated.json` — deterministic byte-for-byte over the same input (sort_keys, stable ordering, NO timestamps/dates inside; dating happens at report time in Phase 6 from data already in rows).
- 4-way decomposition per cell: uncached input tokens, cache_creation, cache_read, output — sums and medians; cost recomputed per component is Phase 6 material, the aggregate carries the token components + total_cost_usd stats.
- Unknown/extra row fields tolerated (schema drift lesson from Phase 1); missing REQUIRED fields (usage, verify_passed, baseline_id, task_id) → row rejected loudly with count of rejects in the output, never silently.

### Test strategy
- Stub-first: fixture JSONL files (hand-authored, covering pass/fail/is_error/missing-fields) + stub-driven matrix runs. CI $0. Determinism proven by double-run diff in bats.
- No live calls in this phase at all (the harness mechanics don't need them; real data collection is Phase 5/6 territory).

### Research open questions — resolved by the autonomous run (2026-07-26)
- **Cell = baseline × rep, single `--task`** this phase. Multi-task cells arrive with the corpus in Phase 5 (per this file's own Deferred Ideas). aggregated.json's schema must still be shaped per task_id so Phase 5 extends without breaking.
- **The 2 committed real rows (missing `baseline_id`) become the rejection-path fixture** — used unmodified to prove loud rejection; a separate synthetic fixture (with baseline_id, covering pass/fail/is_error) drives the gating/stat tests.
- **`--reps` defaults to 5**; existing bench-matrix.bats row-count assertions get updated to pass explicit `--reps 1` where they assert single-run behavior (never silently change their meaning).
- **4-way decomposition prefers `modelUsage.<model>.*` with `usage.*` fallback** — verified by hand arithmetic: `usage.cache_creation_input_tokens` under-reports ~30% on the real success row; only modelUsage reconciles with total_cost_usd. Document the preference in the aggregate schema.
- **Spread = median + min/max primary** (no quantile-method ambiguity at N=5); IQR via `statistics.quantiles(method='inclusive')` secondary, method documented.
- **Determinism hard rules:** `sorted()` on every glob and set iteration before output; `json.dumps(sort_keys=True)`.

### Claude's Discretion
- aggregated.json exact schema, how bench-matrix passes rep_index to bench-run (flag vs internal), reject-row reporting shape.

</decisions>

<canonical_refs>
## Canonical References

- `benchmarks/scripts/bench-matrix.py` + `bench-run.py` — the scripts this phase extends
- `.planning/phases/02-baseline-isolation-multi-baseline-harness/02-03-SUMMARY.md` — seed/run_order_index mechanics as shipped
- `benchmarks/results/smoke-convert.jsonl` — 2 real rows (fixture material for aggregate tests)
- `.planning/research/PITFALLS.md` — pitfalls 1 (variance), 6 (success-gating: THE hard gate), 2 (cache contamination)
- `.planning/research/ARCHITECTURE.md` — build order step 4 (aggregation layer)
- `tests/bench-matrix.bats`, `tests/helpers.bash` — patterns to extend

</canonical_refs>

<specifics>
## Specific Ideas

- The 2 committed real rows (success + error_max_turns, both verify_passed) are perfect aggregate-test fixtures: error row must be gated OUT of headline metrics despite verify_passed=true (METR-02 belt-and-braces in action).

</specifics>

<deferred>
## Deferred Ideas

- Competitor arm — Phase 4. Corpus growth + variance pilot — Phase 5. Charts/report/README embed — Phase 6.

</deferred>

---
*Phase: 03-repetition-aggregation-cost-decomposition*
*Context gathered: 2026-07-26 via autonomous run*
