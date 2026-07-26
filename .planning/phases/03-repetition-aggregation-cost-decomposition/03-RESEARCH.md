# Phase 3: Repetition, Aggregation & Cost Decomposition - Research

**Researched:** 2026-07-26
**Domain:** Python-stdlib statistics for tiny samples (N=5-10), deterministic JSON serialization, Claude API cost/cache-token mechanics as they show up in this repo's own harness output
**Confidence:** HIGH — every claim below is either executed directly against this repo's real files (`benchmarks/scripts/*.py`, `benchmarks/results/smoke-convert.jsonl`) with Python 3.12.1, or pulled from the official Anthropic pricing page fetched live. Two findings (why `claude` defaults to 1h cache TTL; the "honest" quantile method) are flagged `[ASSUMED]`/discretion explicitly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Repetition (METR-01)**
- `--reps N` lands in `bench-matrix.py` (the orchestrator — bench-run.py stays single-run by design). Default N=5; the plan may allow lower N only via explicit flag for pilots.
- Interleaving covers reps too: the seeded shuffle spans the full cell list (task × baseline × rep), so same-arm runs are not consecutive (cache fairness, FAIR-03 extended). Each row records `rep_index` alongside `seed`/`run_order_index`.
- Median + spread (IQR or min/max) reported PER task × baseline, never only aggregate. stdlib `statistics` only.

**Success gating (METR-02)**
- Headline cost/token metrics computed ONLY over rows with `verify_passed == true`. Failed rows are never "cheaper" — they surface as `pass_rate` (n_passed/n_total) per cell, reported alongside.
- A cell with pass_rate 0 reports null metrics + the failure count (no silent drop).
- `is_error` rows (api_error, max_turns etc.) count as failures for gating even if verify accidentally passes — both gates must hold (belt-and-braces; Phase 1 proved the axes are independent).

**Aggregation (METR-03)**
- New `bench-aggregate.py` (+ .sh wrapper, house style): reads raw JSONL (one or more files), emits `aggregated.json` — deterministic byte-for-byte over the same input (sort_keys, stable ordering, NO timestamps/dates inside; dating happens at report time in Phase 6 from data already in rows).
- 4-way decomposition per cell: uncached input tokens, cache_creation, cache_read, output — sums and medians; cost recomputed per component is Phase 6 material, the aggregate carries the token components + total_cost_usd stats.
- Unknown/extra row fields tolerated (schema drift lesson from Phase 1); missing REQUIRED fields (usage, verify_passed, baseline_id, task_id) → row rejected loudly with count of rejects in the output, never silently.

**Test strategy**
- Stub-first: fixture JSONL files (hand-authored, covering pass/fail/is_error/missing-fields) + stub-driven matrix runs. CI $0. Determinism proven by double-run diff in bats.
- No live calls in this phase at all (the harness mechanics don't need them; real data collection is Phase 5/6 territory).

### Claude's Discretion
- aggregated.json exact schema, quantile choice for spread (document it), how bench-matrix passes rep_index to bench-run (flag vs internal), reject-row reporting shape.

### Deferred Ideas (OUT OF SCOPE)
- Competitor arm — Phase 4. Corpus growth + variance pilot — Phase 5. Charts/report/README embed — Phase 6.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| METR-01 | N≥5 repetitions per cell (task × baseline); median and spread reported per task, not just aggregate | §1 (stdlib quantile behavior at N=5-10, verified), §4 (interleaving/cache mechanics), Code Examples (cell-list + shuffle extension) |
| METR-02 | Headline cost/tokens = success-gated (verify_passed AND NOT is_error); failing rows never counted as savings | §5 (real fixture rows are the belt-and-braces test case — but also expose a schema gap), Code Examples (gating logic) |
| METR-03 | `bench-aggregate.py` deterministic: JSONL → `aggregated.json`, byte-identical over same input | §2 (JSON determinism gotchas, verified: sort_keys recursion, glob ordering, hash-seed set ordering), §3 (which usage fields to decompose — verified via cost reconciliation) |
</phase_requirements>

## Summary

This phase is pure Python-stdlib plumbing (`statistics`, `json`, `argparse`, `random`, `itertools`) on top of two already-shipped scripts — no new external dependency, no live API calls. The two riskiest technical gotchas are not in the areas CONTEXT.md flagged as "discretion" (quantile method, schema shape); they're **empirically verified problems in the existing real fixture data**: (1) the two committed rows in `benchmarks/results/smoke-convert.jsonl` — explicitly called out in CONTEXT.md as "perfect aggregate-test fixtures" — are **missing `baseline_id`**, which under METR-03's own locked "reject loudly" rule means they'd be rejected, not accepted, as fixtures; and (2) for the **successful** row, the top-level `usage.*` token fields **do not reconcile with `total_cost_usd`** — only `modelUsage.<model>.*` does (verified by hand-computing both against live Anthropic Haiku 4.5 pricing; the top-level fields match exactly for the `is_error` row and diverge by ~30% on cache_creation for the success row). Any 4-way decomposition that blindly reads `row["usage"]["cache_creation_input_tokens"]` will silently misreport cost composition on success rows.

Separately, real committed rows show the harness's own `claude -p` invocations are landing on Anthropic's **1-hour** ephemeral cache tier (`ephemeral_1h_input_tokens` non-zero, `ephemeral_5m_input_tokens` always 0), not the 5-minute default most docs lead with. Interleaving (already shipped in Phase 2) distributes *which* rep of a cell pays the cold cache-write cost, but at 1h TTL it does **not** prevent 4 of 5 same-baseline reps from landing warm within a typical suite runtime — this is expected, not a bug, and the 4-way decomposition (already locked) is precisely the mechanism that makes it visible rather than hidden.

**Primary recommendation:** extend the existing `build_execution_order`/row-provenance pattern exactly (don't redesign it) for reps; decompose cost from `modelUsage` when present, falling back to `usage` only when it's absent (stub/minimal rows); sort every collection that touches output ordering (`sorted(glob(...))`, `sorted(set(...))`, never bare `set`/`glob` iteration) before it reaches `json.dumps(..., sort_keys=True)`; and resolve the baseline_id gap in the real fixture rows explicitly before wiring them into aggregate tests.

## Architectural Responsibility Map

Not a web app — the "tiers" here are the harness's own layers (CLI orchestrator → runner → flat-file storage → aggregator).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Cell-list construction (task × baseline × rep) + seeded shuffle | Orchestrator (`bench-matrix.py`) | — | Already owns `build_execution_order`; reps are a natural extension, not a new layer |
| Row-provenance stamping (`seed`, `run_order_index`, `rep_index`) | Runner (`bench-run.py`) | Orchestrator (passes the flag) | Only the runner writes the JSONL row; orchestrator can't stamp fields into a file it doesn't touch |
| Raw data persistence | Flat-file storage (JSONL, append-only) | — | No DB; matches house style (`benchmarks/results/*.jsonl`) |
| Success gating + statistics + 4-way decomposition | Aggregator (new `bench-aggregate.py`) | — | New component, reads raw JSONL only, writes `aggregated.json` only |
| Cost recomputation from public pricing (cross-check) | Deferred to Phase 6 | — | CONTEXT.md is explicit: "cost recomputed per component is Phase 6 material" — Phase 3 carries components + `total_cost_usd`, does not recompute $ |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `statistics` | stdlib (3.8+) | median, quantiles, pstdev | Locked: "stdlib `statistics` only" — `quantiles()` requires Python ≥3.8, confirmed available under the repo's Python 3.12.1 |
| `json` | stdlib | JSONL parsing + deterministic `aggregated.json` output | `sort_keys=True` is the whole determinism mechanism; verified recursive (see §2) |
| `argparse` | stdlib | New `--reps`/`--rep-index` flags | Matches existing `bench-matrix.py`/`bench-run.py` argparse/manual-parser idiom |
| `itertools` | stdlib | Cross-product cell list (`task × baseline × rep`, or `baseline × rep` per §4's scope question) | `itertools.product` avoids a hand-rolled nested-loop list builder |
| `random` | stdlib | `random.Random(seed).shuffle(cells)` — instance-scoped, exactly the existing pattern | Already proven deterministic in `tests/bench-matrix.bats` (test 4) |

No new external packages this phase.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `statistics.quantiles` | `numpy.percentile` | Would violate the locked stdlib-only constraint and the project's zero-dependency house style (ARCHITECTURE.md, confirmed) — not viable, not researched further |
| Manual dict-based grouping | `itertools.groupby` | `groupby` requires pre-sorted input and is easy to misuse (silently drops non-contiguous groups); a plain `dict[(task_id, baseline_id)] = [...]` accumulator is safer and just as stdlib-only |

**Installation:** none — no `pip install` needed for this phase.

**Version verification:** `python3 --version` in this repo → 3.12.1; `statistics.quantiles` confirmed present and requires `len(data) >= 2` (raises `StatisticsError` below that — relevant since a cell could theoretically have only 1 passing rep if 4/5 fail verify; aggregate must handle N=1 and N=0 passing rows explicitly, not just N≥5).

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.** Everything used (`statistics`, `json`, `argparse`, `itertools`, `random`, `pathlib`, `subprocess`) is Python stdlib, already imported by the scripts this phase extends. The Package Legitimacy Gate protocol is skipped per its own scope ("whenever this phase installs external packages").

## Architecture Patterns

### Data Flow

```
bench-matrix.py                                  bench-run.py (×N cells)
┌─────────────────────────────┐                  ┌──────────────────────────┐
│ cells = product(baselines,   │  one subprocess  │ writes ONE JSONL row,    │
│                  range(reps))│  per cell, in    │ stamps seed/             │
│ random.Random(seed)          │  shuffled order  │ run_order_index/         │
│   .shuffle(cells)             ├─────────────────▶│ rep_index (if passed)    │
│ validate ALL manifests exist │                  └──────────┬───────────────┘
│ BEFORE any invocation        │                             │ append
└───────────────────────────────┘                             ▼
                                                  results/raw/*.jsonl (append-only)
                                                             │
                                                             ▼
                                          bench-aggregate.py (NEW, this phase)
                                          ┌─────────────────────────────────┐
                                          │ 1. read + sort input file list   │
                                          │ 2. parse each line; reject rows  │
                                          │    missing usage/verify_passed/  │
                                          │    baseline_id/task_id (count)   │
                                          │ 3. group by (task_id,baseline_id)│
                                          │ 4. gate: verify_passed AND NOT   │
                                          │    is_error → "passed" subset    │
                                          │ 5. per cell: pass_rate, n_total, │
                                          │    median/spread of total_cost,  │
                                          │    4-way token decomposition     │
                                          │    (modelUsage-preferred)        │
                                          │ 6. json.dumps(sort_keys=True,    │
                                          │    consistent separators)        │
                                          └──────────────┬────────────────────┘
                                                          ▼
                                              aggregated.json (byte-identical
                                              over the same input, no dates)
```

### Pattern 1: Extend, don't redesign, the seeded-shuffle cell builder
**What:** `build_execution_order(baselines, seed)` in `bench-matrix.py` today shuffles baseline *names* only. Extend it to shuffle `(name, rep)` tuples over the full cross-product, using the same `random.Random(seed)` instance-scoped RNG.
**When to use:** METR-01's "interleaving covers reps too" requirement.
**Example (illustrative, matches existing file's style):**
```python
# Source: pattern extends benchmarks/scripts/bench-matrix.py build_execution_order
import itertools

def build_execution_order(baselines, reps, seed):
    cells = list(itertools.product(baselines, range(reps)))  # [(name, rep_idx), ...]
    random.Random(seed).shuffle(cells)
    return cells
```
The existing validate-before-spend step (resolve every manifest path, die loud if any missing) stays a per-*name* check — no change needed since the same manifest is reused across reps; re-`is_file()`-checking it `reps` times is cheap, idempotent local IO, not worth deduping.

### Pattern 2: `--rep-index` on `bench-run.py`, mirroring `--seed`/`--run-order-index` exactly
**What:** `bench-run.py`'s `parse_args` already has the exact shape needed: optional int flag, `try/except ValueError → die(EXIT_USAGE)`, conditionally added to the row dict only when not `None` (so standalone invocations keep the existing schema untouched).
**When to use:** This is the flag-vs-internal discretion point CONTEXT.md leaves open — recommend **flag**, because it's the only way that keeps schema-writing logic exclusively inside `bench-run.py` (which is the one file that touches the output JSONL), consistent with the Phase 2 precedent of `--seed`/`--run-order-index`.
**Example:**
```python
# Source: pattern extends benchmarks/scripts/bench-run.py parse_args/opts
elif arg == "--rep-index":
    if i + 1 >= len(argv):
        die(f"--rep-index needs a value\n{USAGE}", EXIT_USAGE)
    try:
        opts["rep_index"] = int(argv[i + 1])
    except ValueError:
        die(f"--rep-index must be an integer, got '{argv[i + 1]}'", EXIT_USAGE)
    i += 2
# ... row assembly, alongside the existing seed/run_order_index blocks:
if opts["rep_index"] is not None:
    row["rep_index"] = opts["rep_index"]
```

### Pattern 3: Success-gating is a dual boolean, not a single field
**What:** METR-02 is locked as belt-and-braces: `passed = row.get("verify_passed") is True and not row.get("is_error")`.
**Example:**
```python
def is_headline_pass(row):
    return row.get("verify_passed") is True and not row.get("is_error", False)
```

### Pattern 4: Token-decomposition source preference (modelUsage > usage)
**What:** Prefer `row["modelUsage"][<any model key>]` fields when present (sum across keys if more than one, though a single pinned model is expected per baseline); fall back to `row["usage"]` flat fields when `modelUsage` is absent (true for the bats stub fixtures and for `ARCHITECTURE.md`'s draft row shape, both of which only define a flat `usage` dict).
**Why:** verified by direct arithmetic — see Common Pitfalls #2.
**Example:**
```python
def token_components(row):
    mu = row.get("modelUsage")
    if mu:
        agg = {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
        for m in mu.values():
            agg["input"] += m.get("inputTokens", 0)
            agg["cache_creation"] += m.get("cacheCreationInputTokens", 0)
            agg["cache_read"] += m.get("cacheReadInputTokens", 0)
            agg["output"] += m.get("outputTokens", 0)
        return agg
    u = row.get("usage", {})
    return {"input": u.get("input_tokens", 0),
            "cache_creation": u.get("cache_creation_input_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "output": u.get("output_tokens", 0)}
```

### Pattern 5: Deterministic multi-file input + output
**What:** Sort input file paths explicitly; never rely on `glob`/`Path.glob`/`os.listdir` order (filesystem-dependent, not alphabetical — verified). Sort any `set()`-derived collection before it influences output (Python string-hash randomization makes `set` iteration order vary run-to-run — verified). Always call `json.dumps(obj, sort_keys=True, separators=(",", ":"))` with fixed `separators` (not just `sort_keys`) so pretty-printing settings can't drift between invocations.
**Example:**
```python
# Source: verified against this repo's Python 3.12.1 (see Common Pitfalls #3, #4)
import glob, json

input_files = sorted(glob.glob(pattern))          # never bare glob.glob()
baseline_ids = sorted(set(r["baseline_id"] for r in rows))  # never bare set()
out = json.dumps(aggregated, sort_keys=True, separators=(",", ":"))
```

### Anti-Patterns to Avoid
- **Trusting `usage.*` as the cost-decomposition source of truth unconditionally:** works for `is_error` rows in this repo's real data, silently under-reports `cache_creation` by ~30% for success rows (verified, see Pitfall #2).
- **`itertools.groupby` on unsorted JSONL:** silently produces multiple groups for the same `(task_id, baseline_id)` key if rows aren't pre-sorted by that key — use a plain dict accumulator instead.
- **Reusing `ARCHITECTURE.md`'s draft field name `"repetition"`:** that document is pre-CONTEXT.md speculative research; CONTEXT.md's locked field name is `rep_index` — use `rep_index`, not `repetition`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Median/quartiles of a 5-10 value sample | Manual sort + index math | `statistics.median`, `statistics.quantiles(data, n=4, method=...)` | Locked stdlib-only constraint; hand-rolled interpolation is exactly the kind of off-by-one bug that shows up in benchmark credibility post-mortems |
| Deterministic JSON diffing/canonicalization | Custom recursive key-sorter | `json.dumps(obj, sort_keys=True, separators=(...))` | `sort_keys` is recursive through nested dicts/lists-of-dicts (verified) — a hand-rolled walker would just reimplement this with more bug surface |
| Cross-product cell enumeration | Nested `for` loops with manual index bookkeeping | `itertools.product` | Same result, fewer off-by-one opportunities when reps are added on top of the existing baseline loop |

**Key insight:** every "don't hand-roll" item here is a place where the existing codebase (Phase 1/2) already chose the stdlib primitive — Phase 3's job is consistent extension, not new design decisions.

## Common Pitfalls

### Pitfall 1: The committed "perfect fixture" rows fail METR-03's own required-field check
**What goes wrong:** CONTEXT.md's `<specifics>` section calls the two rows in `benchmarks/results/smoke-convert.jsonl` "perfect aggregate-test fixtures" for the belt-and-braces gating test. Verified directly: **neither row has a `baseline_id` field** (`has_task_id=True, has_baseline_id=False` for both). Under METR-03's own locked rule ("missing REQUIRED fields (usage, verify_passed, baseline_id, task_id) → row rejected loudly"), both rows would be rejected before the gating logic even runs.
**Why it happens:** these rows predate Phase 2's baseline-manifest work (`baseline_id` was added to the row schema in Phase 2), so they're schema-stale relative to Phase 3's own required-field list.
**How to avoid:** the plan must explicitly choose one of: (a) patch a copy of these two rows with a synthetic `baseline_id` inside the test fixture (not the committed file) before using them to test belt-and-braces gating, or (b) use them, unmodified, specifically as the "missing required field → rejected loudly" test case, and author a *separate* small synthetic fixture (with `baseline_id` present) for the is_error-but-verify_passed gating test. Don't silently patch the committed file itself — it's real historical data.
**Warning signs:** an aggregate test that expects these two committed rows to appear in `aggregated.json`'s output cells will fail once required-field rejection is implemented, unless one of the above is chosen.

### Pitfall 2: `usage.*` and `modelUsage.<model>.*` disagree on success rows — only one reconciles with `total_cost_usd`
**What goes wrong:** For row 1 (`is_error: true`, max-turns), `usage.cache_creation_input_tokens` (45533) equals `modelUsage["claude-haiku-4-5-20251001"].cacheCreationInputTokens` (45533) — they match, and recomputing cost from either source using official Haiku 4.5 pricing (`$1`/`$2`/`$0.10`/`$5` per MTok for input/1h-cache-write/cache-read/output) reproduces `total_cost_usd` (0.1223481) exactly. For row 2 (`is_error: false`, success), the two sources **diverge**: `usage.cache_creation_input_tokens` = 45442 vs `modelUsage[...].cacheCreationInputTokens` = 64857 (also `input_tokens` 53 vs 56, `output_tokens` 1028 vs 1083). Recomputing from `modelUsage` reproduces `total_cost_usd` (0.167407) exactly; recomputing from `usage` gives $0.128299 — 23% off.
**Why it happens:** unconfirmed (Claude Code CLI internals not documented at this level); empirically the top-level `usage` object under-reports on the success path relative to what's actually billed, while `modelUsage` always reconciles in both observed rows. `[ASSUMED: root cause]` — but the reconciliation behavior itself is `[VERIFIED: direct arithmetic against benchmarks/results/smoke-convert.jsonl + platform.claude.com/docs/en/about-claude/pricing]`.
**How to avoid:** decompose tokens from `modelUsage` when present, fall back to `usage` only when `modelUsage` is absent (Pattern 4 above). Do not assume `usage.*` sums to `total_cost_usd` — Phase 6's eventual $ cross-check (out of scope here) must use the same field preference or it will "fail" a real, correctly-priced row.
**Warning signs:** a per-cell decomposition whose 4 components don't sum to something close to `total_cost_usd` when spot-checked manually.

### Pitfall 3: `glob`/directory-listing order is not alphabetical and not portable
**What goes wrong:** `glob.glob('*.jsonl')` in a throwaway test directory returned `['m.jsonl', 'b.jsonl', 'c.jsonl', 'a.jsonl', 'z.jsonl']` — filesystem/creation order, not sorted, and this order was stable within one directory's lifetime but is not guaranteed to match across a different machine/filesystem/re-creation of the same files. If `bench-aggregate.py` accepts "one or more" raw JSONL files via a glob pattern or directory scan (as CONTEXT.md's METR-03 decision allows), unsorted iteration breaks byte-for-byte determinism across machines even with identical input content.
**How to avoid:** always `sorted(glob.glob(pattern))` or `sorted(Path(dir).glob(pattern))` before reading. `[VERIFIED: executed directly, this session]`.

### Pitfall 4: Python's string-hash randomization breaks `set()` iteration order run-to-run
**What goes wrong:** `list({'vanilla', 'gsd-only', 'cairn'})` produced a different order on 3 different `PYTHONHASHSEED` values, and a **different order on two consecutive default (unset `PYTHONHASHSEED`) runs of the same process** — CPython randomizes `str`/`bytes` hashing by default since 3.3, and `set` iteration order depends on hash values (unlike `dict`, which is insertion-ordered but that's a separate guarantee). Any code that does `list(set(baseline_ids))` or iterates a `set` to build an output list will silently break `aggregated.json`'s determinism requirement between two runs of the exact same input, on the exact same machine, in the exact same second.
**How to avoid:** never let a bare `set` reach output ordering — always `sorted(...)` it first, or avoid `set()` for ordering-sensitive collections and use a dict-keyed accumulator (which preserves first-seen order) plus an explicit final sort. `[VERIFIED: executed directly, this session, 5 runs, 4 distinct orderings observed]`.

### Pitfall 5: `statistics.quantiles`'s default method extrapolates beyond the observed data at N=5; `method='inclusive'` does not
**What goes wrong:** at N=5, Python's default `method='exclusive'` quartiles for `[1,2,3,4,5]` are `[1.5, 3.0, 4.5]` — Q1 and Q3 are *interpolated points that were never observed*. `method='inclusive'` gives `[2.0, 3.0, 4.0]` — for N=5 specifically, `(N-1)*0.25` and `(N-1)*0.75` land exactly on integer positions (index 1 and index 3 of the sorted 5 values), so Q1/Q3 are literally the 2nd and 4th real observed values, no interpolation. On a jittered 5-cost sample, `exclusive` IQR came out 20% wider than `inclusive` IQR (0.0428 vs 0.0356) purely from the extrapolation. `statistics.quantiles` also **requires `len(data) >= 2`**, raising `StatisticsError` below that — a cell with only 1 verify-passing rep (4/5 failed) needs explicit handling (spread = null / "n=1, no spread"), not a crash.
**How to avoid:** for N=5 specifically, `method='inclusive'` reports real order statistics as the quartiles, which is more defensible in a public methodology doc than fabricated interpolated points ("Q1/Q3 are the 2nd/4th of 5 actual runs" is an easy, honest sentence to write). `min`/`max` (full range) is an even simpler, harder-to-misread alternative and is what CONTEXT.md's "IQR or min/max" discretion explicitly allows. **Recommendation:** report **both min/max (range) and median** as the primary spread metric at N=5 — min/max needs zero method-choice justification and is exactly what a skeptical reader can verify by eye against the raw JSONL rows; add IQR (`method='inclusive'`) as a secondary column once N grows past Phase 5's corpus/variance-pilot work. `[VERIFIED: computed directly this session]` for the quantile mechanics; `[ASSUMED]` for "min/max is the more honest default at N=5" — this is a judgment call CONTEXT.md leaves to discretion, not an empirical fact. For context, published agent-benchmark practice at similar tiny-N scale: SWE-bench's own pass@1 methodology is literally "the mean of 5 per-run resolution rates... with 95% confidence intervals computed over multiple trials" [CITED: verdent.ai SWE-bench Verified technical report, MEDIUM confidence, general methodology not CairnGo-specific] — i.e. N=5 with a simple mean + CI is treated as a legitimate minimum bar in the field, not merely a floor to apologize for; Aider's benchmark defaults to single-run-per-exercise across many exercises and only measured run-to-run variance via a separate 10x replication study on a subset, rather than reporting per-task variance for every number [CITED: aider.chat benchmark docs, MEDIUM confidence].

### Pitfall 6: Real invocations are landing on the 1-hour cache tier, not 5-minute — interleaving doesn't eliminate within-cell cache warmth at this N
**What goes wrong:** both committed real rows show `usage.cache_creation.ephemeral_1h_input_tokens` non-zero and `ephemeral_5m_input_tokens: 0` — i.e., these `claude -p` invocations used Anthropic's 1-hour cache tier (2x write multiplier, same 0.1x read multiplier as 5-min), not the 5-minute default that most caching documentation leads with (the 1h tier requires either the `extended-cache-ttl-2025-04-11` beta header or `cache_control: {ttl: "1h"}` explicitly — `[CITED: platform.claude.com/docs/en/build-with-claude/prompt-caching via WebSearch corroboration]`, mechanism inside the `claude` CLI itself is `[ASSUMED]`, not independently confirmed in Claude Code CLI docs this session). At a 1-hour TTL, a benchmark cell's 5 reps — even fully interleaved among 3 baselines per Phase 2's shipped mechanism — will very likely all land within the same 1-hour window for a single-task, few-baseline smoke run. Interleaving (proven in Phase 2) distributes *which specific rep* ends up paying the cold cache-write cost; it does **not** prevent the other 4 of 5 reps of that baseline from getting a warm cache hit regardless of shuffle order, because the TTL vastly exceeds the elapsed time between them.
**Why it happens:** this is the correct, expected behavior of prompt caching, not a harness bug — the interleaving requirement (FAIR-03/METR-01) exists to prevent *systematic* bias toward whichever baseline happens to run consecutively/last, not to force every rep cold. A plain `random.Random(seed).shuffle()` over the full cell list is also just a uniform random permutation — it offers no guarantee against two same-baseline cells landing adjacent by chance, but at 1h TTL that adjacency wouldn't matter anyway.
**How to avoid:** this is exactly why the 4-way decomposition is locked as a requirement rather than optional — reporting `cache_creation` and `cache_read` per cell (not just blended cost) is what lets a reader see "1 cold + 4 warm reps" instead of a cost number that looks mysteriously non-uniform. No harness change is needed to "fix" this in Phase 3; it needs to be **documented explicitly** in the methodology (Phase 6 territory) so it isn't mistaken for baseline-to-baseline unfairness. Flag for the planner: don't scope-creep Phase 3 into adding cache-busting logic — CONTEXT.md's Deferred Ideas already push the variance pilot to Phase 5.
**Warning signs:** within a cell, `cache_creation` is high on exactly one rep and near-zero on the rest, while `cache_read` shows the inverse pattern — this is the expected signature, not a defect.

### Pitfall 7: `bench-matrix.py`'s existing bats tests assume no `--reps` flag exists — adding a default breaks row-count assertions
**What goes wrong:** `tests/bench-matrix.bats` today asserts `wc -l` == 3 (one row per baseline, 3 baselines, implicit reps=1) with no `--reps` flag passed. CONTEXT.md locks "Default N=5" for `--reps`. If the flag defaults to 5 silently, every existing invocation without `--reps` starts producing 5x the rows, breaking `[ "$(wc -l < ...)" -eq 3 ]` and the `sort == [0, 1, 2]` run_order_index assertion in the existing suite.
**How to avoid:** the plan needs an explicit decision (not left implicit): either (a) existing bats invocations gain `--reps 1` explicitly to preserve current behavior and only new tests exercise `--reps 5`, or (b) `--reps` follows the `--seed` precedent and is **required** (no silent default at all — CONTEXT.md's "Default N=5" wording suggests default-with-value is intended, but the required-no-silent-default precedent is exactly what `--seed` set one plan ago). Either is workable; leaving it undecided means the RED phase of TDD will show pre-existing tests failing for the wrong reason.

### Pitfall 8: The `task × baseline × rep` cell language may not match `bench-matrix.py`'s current single-`--task` signature
**What goes wrong:** CONTEXT.md's locked text says "the seeded shuffle spans the full cell list (task × baseline × rep)," but `bench-matrix.py` today accepts exactly one `--task TASK_DIR` (singular), looping only over baselines. CONTEXT.md's own Deferred Ideas assign "Corpus growth" (i.e., more than one task) to Phase 5. This is an open scope question, not resolved by anything read this session — see Open Questions.

## Code Examples

### Aggregator core loop (illustrative shape, not final code)
```python
# Source: pattern synthesized from house style (bench-run.py/bench-matrix.py)
# + locked METR-02/METR-03 decisions in 03-CONTEXT.md
import json, statistics, sys
from collections import defaultdict

REQUIRED = ("usage", "verify_passed", "baseline_id", "task_id")

def load_rows(paths):
    rows, rejected = [], 0
    for p in sorted(paths):                      # sorted: determinism (Pitfall 3)
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if any(k not in row for k in REQUIRED):
                    rejected += 1
                    continue
                rows.append(row)
    return rows, rejected

def group_cells(rows):
    cells = defaultdict(list)
    for r in rows:
        cells[(r["task_id"], r["baseline_id"])].append(r)
    return cells                                   # keys sorted at emit time, not here

def is_headline_pass(row):
    return row.get("verify_passed") is True and not row.get("is_error", False)

def cell_stats(rows):
    passed = [r for r in rows if is_headline_pass(r)]
    n_total, n_passed = len(rows), len(passed)
    costs = sorted(r["total_cost_usd"] for r in passed if "total_cost_usd" in r)
    stats = {"n_total": n_total, "n_passed": n_passed,
             "pass_rate": (n_passed / n_total) if n_total else 0.0}
    if len(costs) >= 1:
        stats["cost_median"] = statistics.median(costs)
        stats["cost_min"] = costs[0]
        stats["cost_max"] = costs[-1]
    else:
        stats["cost_median"] = stats["cost_min"] = stats["cost_max"] = None
    if len(costs) >= 2:
        q = statistics.quantiles(costs, n=4, method="inclusive")
        stats["cost_iqr"] = q[2] - q[0]
    return stats

def emit(cells):
    out = {}
    for (task_id, baseline_id) in sorted(cells):    # sorted: determinism (Pitfall 4)
        out[f"{task_id}::{baseline_id}"] = cell_stats(cells[(task_id, baseline_id)])
    return json.dumps(out, sort_keys=True, separators=(",", ":"))
```

## State of the Art

| Old Approach (pre-Phase 3) | Current Approach (this phase) | When Changed | Impact |
|--------------------------|-------------------------------|---------------|--------|
| Single run per (task, baseline), no spread reported | N≥5 reps per cell, median + min/max (or IQR) reported | This phase, per PITFALLS.md Pitfall 1 | Directly closes the "single-run results presented as fact" credibility gap identified in project research |
| Blended cost/token averages regardless of outcome | Success-gated headline metrics + explicit `pass_rate` | This phase, METR-02 | Closes PITFALLS.md Pitfall 6 ("the most important pitfall in the whole set") |
| Single blended token count | 4-way decomposition (uncached input / cache_creation / cache_read / output) | This phase, METR-03 | Closes PITFALLS.md Pitfall 7 (order/cache-dependent cost swings) — makes the 1h-TTL cache pattern (Pitfall 6 above) visible instead of hidden |

**Outdated assumption to retire:** "Anthropic prompt cache TTL is 5 minutes" as a blanket assumption — this repo's own real invocations are observed on the 1-hour tier.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | The `claude` CLI (or Claude Code Agent SDK) internally requests the 1-hour cache tier by default for its stable system-prompt/tool-definition content, causing the `ephemeral_1h`-not-`ephemeral_5m` pattern observed in both real rows | Pitfall 6 | If wrong (e.g. it's a fluke of these two specific runs, or configurable per-baseline in a way not yet discovered), the "interleaving doesn't fully de-warm reps" conclusion could be overstated for some baselines and understated for others — worth re-checking once Phase 5's live variance pilot produces more real rows |
| A2 | `method='inclusive'` (or plain min/max) is the more "honest" spread choice at N=5 than Python's default `method='exclusive'` | Pitfall 5 | Low risk — this is explicitly a discretion area per CONTEXT.md, not a locked decision; worst case the planner picks `exclusive` anyway and the methodology doc just needs one more caveat sentence |
| A3 | `bench-matrix.py`'s `--task` stays singular this phase (task × baseline × rep cell language means baseline × rep for the one given task, not true multi-task cross-product) | Pitfall 8, Open Questions | If wrong, the cell-list/shuffle implementation shape changes materially (comma-separated `--tasks` needed, plus a bigger validate-before-spend surface) |

**If this table is empty:** N/A — see rows above.

## Open Questions (RESOLVED — see 03-CONTEXT.md "Research open questions — resolved by the autonomous run")

1. **Does "task × baseline × rep" mean `bench-matrix.py` gains multi-task support this phase, or does it stay one `--task` per invocation (with reps × baselines as the only new cross-product dimension)?**
   - What we know: CONTEXT.md's decision text uses the three-way product language; the current script signature and the existing bats tests are single-task; CONTEXT.md's own Deferred Ideas assign "Corpus growth" to Phase 5.
   - What's unclear: whether "task" in that phrase is describing the current single-task reality (cell list = baseline × rep, for whichever one task this invocation targets) or is forward-looking language for a change this phase should also make.
   - Recommendation: default to baseline × rep only (matches current signature + Deferred Ideas boundary); flag for user/planner confirmation before implementation if ambiguous.

2. **Resolution strategy for the missing `baseline_id` in the two committed real fixture rows (Pitfall 1).**
   - What we know: both rows are real, useful (is_error/verify_passed combination is the belt-and-braces test case CONTEXT.md wants); both lack `baseline_id`.
   - What's unclear: whether the plan should patch a copy for fixtures, or deliberately use them unmodified as the "reject loudly" test case and author a fresh synthetic fixture for the gating test.
   - Recommendation: do the latter (use unmodified as the required-field-rejection test; write a small synthetic 5-row fixture, with `baseline_id` present, for the gating/decomposition/statistics tests) — keeps the committed real data untouched and gets test coverage for both code paths.

3. **`--reps` default-vs-required and its effect on existing `tests/bench-matrix.bats`.**
   - What we know: CONTEXT.md says "Default N=5," `--seed` set the precedent of "required, no silent default."
   - What's unclear: whether "default" here means silently defaulting (breaking existing tests' row-count assertions) or default-with-override (still requires updating existing tests to pass `--reps 1` explicitly).
   - Recommendation: treat existing bats tests as needing an explicit `--reps 1` addition either way — this makes the RED phase of TDD clean regardless of which reading is correct.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | All new/extended scripts | ✓ | 3.12.1 (confirmed this session) | — |
| `statistics` module | METR-01 median/quantiles | ✓ | stdlib since 3.8, present in 3.12.1 | — |
| bats | Test strategy (stub-first, per CONTEXT.md) | ✓ (already used by `tests/bench-matrix.bats`) | not re-verified this session (no version drift risk — same suite Phase 2 already runs green) | — |
| jq | bats assertions on JSONL/aggregated.json | ✓ (already used by `tests/helpers.bash`/existing bats files) | not re-verified this session | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — this phase adds no new environment surface beyond what Phase 1/2 already proved available.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | No auth surface — local CLI tooling only |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes | `json.loads` per-line JSONL parsing with explicit required-field validation (already locked: reject loudly, count rejects) — never `eval`/`pickle` on untrusted raw JSONL that a third party might submit when reproducing the benchmark |
| V6 Cryptography | No | No crypto involved |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Malformed/adversarial raw JSONL (a third party runs the reproduction command and shares a corrupted or hand-edited results file) | Tampering | Per-line `json.loads` (bounded blast radius per line — one bad line can't corrupt the whole parse), required-field validation with loud, counted rejection (already locked in METR-03); never silently coerce or partially trust a malformed row |
| New subprocess invocations for reps (bench-matrix.py invoking bench-run.py once per cell) | Tampering/Elevation | No new pattern needed — continues the existing `subprocess.run(cmd_list)` with no `shell=True` (verified in Phase 2's summary: `grep -c 'shell=True'` → 0); the reps extension adds more invocations of the *same* safe call shape, not a new one |

## Sources

### Primary (HIGH confidence)
- `benchmarks/scripts/bench-matrix.py`, `benchmarks/scripts/bench-run.py` — read directly, this session (existing structure, exact extension points for `--reps`/`--rep-index`)
- `benchmarks/results/smoke-convert.jsonl` — read directly, arithmetic verified against official pricing this session (Pitfalls 1, 2, 6)
- Direct Python 3.12.1 execution this session: `statistics.quantiles`/`median` behavior at N=1-10, `json.dumps(sort_keys=True)` recursion, `glob.glob` ordering, `PYTHONHASHSEED`/`set()` ordering
- [Anthropic Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — fetched live this session; Haiku 4.5 table ($1/$1.25/$2/$0.10/$5 per MTok for base input/5m-write/1h-write/cache-read/output) and prompt-caching multiplier table (1.25x / 2x / 0.1x) used to reconcile `total_cost_usd` exactly against both real committed rows

### Secondary (MEDIUM confidence)
- [Anthropic prompt caching docs + extended-cache-ttl beta header](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — via WebSearch corroboration (5-min default, `extended-cache-ttl-2025-04-11` beta header / `cache_control.ttl:"1h"` for the 1-hour tier); mechanism by which the `claude` CLI itself lands on 1h is not independently confirmed (flagged `[ASSUMED]`)
- [SWE-bench Verified Technical Report (verdent.ai)](https://www.verdent.ai/blog/swe-bench-verified-technical-report) — pass@1-as-mean-of-5-runs-with-CI methodology, general field practice at N=5
- [Aider code editing benchmark docs](https://aider.chat/docs/benchmarks.html) — single-run-per-exercise-across-many-exercises + separate 10x variance-check methodology

### Tertiary (LOW confidence)
- None used as load-bearing claims this session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure stdlib, version-checked directly against the repo's Python
- Architecture (extension patterns): HIGH — verified against the actual existing files, not reconstructed from memory
- Pitfalls: HIGH for #1-4 (directly executed/greped this session), MEDIUM-HIGH for #6 (real data + official docs, but CLI-internal mechanism unconfirmed), MEDIUM for #5's "honest at N=5" recommendation (a documented judgment call, not a fact)

**Research date:** 2026-07-26
**Valid until:** ~30 days (stdlib behavior is stable indefinitely; Anthropic pricing/model table is the fastest-moving input here and should be re-checked if this research is reused for a plan more than a month out)
