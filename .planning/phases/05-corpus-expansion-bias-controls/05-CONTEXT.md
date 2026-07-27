# Phase 5: Corpus Expansion + Bias Controls - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning
**Source:** Autonomous run. Gray areas are Claude's Discretion.

<domain>
## Phase Boundary

The task corpus grows to a diverse, pre-declared set including an honest non-win category for cairn, with the full run's cost documented and predictable before anyone spends. Requirements: CORP-01 (diverse corpus + variance pilot + unfavorable category), CORP-02 (documented predictable cost). bd issues: CairnGo-me5, CairnGo-6qo — see `05-BEADS-MAP.md`.

</domain>

<decisions>
## Implementation Decisions (locked)

### Corpus composition (CORP-01)
- **Pre-declared** (pitfall: cherry-picking — the corpus is committed BEFORE any full data collection; tasks are never added/removed after results exist without a dated changelog entry in BENCHMARKS.md).
- Target: **6 tasks** across distinct categories (research may adjust 5-8 with rationale). Every task = same fixture contract as smoke-convert (task.json + prompt.md + fixture/ + verify.sh outside fixture, unittest-stdlib only, bats-provable solved/unsolved both directions at $0):
  1. `smoke-convert` (exists) — trivial single-function fix
  2. bugfix: multi-file bug with a failing test (cross-file reasoning)
  3. feature: small test-guided addition (new capability from spec)
  4. refactor: behavior-preserving restructure (tests must stay green — verify.sh runs BOTH the old tests and an anti-cheat check that structure actually changed)
  5. **honest non-win: micro-edit** — a one-line typo/docstring fix where ANY workflow overhead (planning, issue bookkeeping) is pure cost; cairn is expected to LOSE or tie this category, and that's the point (credibility)
  6. long-horizon: multi-step task (implement + wire + test across ≥3 files) where plan-first workflows should shine
- Every task pins the same model id in task.json (current pinned haiku) — model stays a baseline-manifest concern; task.json keeps timeout/max_turns tuned per task size.

### Variance pilot (CORP-01)
- The pilot (2-3 tasks × 2 arms × N=5, measuring run-to-run spread to calibrate final N) requires live spend → **conditional on ANTHROPIC_API_KEY**, same discipline as Phases 2/4: absent → the pilot procedure ships as a documented, one-command runnable script/recipe with PENDING status; present → run it (cost ceiling declared before running).
- The corpus itself (fixtures + verify.sh + bats) is built and proven entirely at $0.

### Cost documentation (CORP-02)
- `benchmarks/README.md` gains a **Cost model** section: formula (tasks × arms × reps × per-run estimate), per-run estimate derived from the 2 real Phase 1 rows (~$0.12-0.17 haiku on smoke-convert) with explicit caveats (larger tasks cost more; estimate per category), and a worked example for the full matrix (6 × 4 × 5 = 120 runs) with a stated ceiling.
- CI-enforced: a bats test asserts the Cost model section exists and names every corpus task (docs that rot fail the build).

### Bias controls
- The unfavorable category is REQUIRED and labeled as such in task.json metadata (`"category"` field incl. `"honest-non-win"`), surfacing automatically in aggregated output per task.
- Task prompts are workflow-neutral: they state the task, never "plan first" nor "just edit" — no arm-favoring language. A bats check greps prompts for arm names (cairn/gsd/ralph) — must be absent.

### Claude's Discretion
- Exact fixture designs per category, timeout/max_turns per task, pilot script shape, category taxonomy field values.

</decisions>

<canonical_refs>
## Canonical References

- `benchmarks/tasks/smoke-convert/` — the fixture contract to replicate ×5
- `tests/bench-verify.bats` — the solved/unsolved proof pattern per task
- `.planning/research/PITFALLS.md` — pitfalls 3 (cherry-picking), 1 (variance), 8 (cost explosion)
- `.planning/research/FEATURES.md` — honest non-win as credibility differentiator
- `benchmarks/scripts/bench-matrix.py` — single --task today; multi-task support lands HERE (cell = task × baseline × rep now real)

</canonical_refs>

<specifics>
## Specific Ideas

- bench-matrix grows `--tasks` (list or dir glob, sorted) — the Phase 3 aggregate already keys cells by task_id::baseline_id, so aggregation needs zero changes (that was deliberate).

</specifics>

<deferred>
## Deferred Ideas

- Full live data collection + charts + README embed — Phase 6 (with key). Second competitor arm (superpowers) — backlog.

</deferred>

---
*Phase: 05-corpus-expansion-bias-controls*
*Context gathered: 2026-07-26 via autonomous run*
