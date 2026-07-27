# Roadmap: CairnGo

## Milestone: v1.1 (in progress) 🚧

**Milestone Goal:** Prove with a reproducible, credible benchmark suite that the cairn workflow costs fewer tokens than the alternatives — not by assertion, but by an honest, published, third-party-reproducible comparison (vanilla Claude Code, GSD-only, cairn, and one competing workflow plugin).

## Overview

Six phases build a benchmark harness bottom-up, front-loading the pieces that are hardest to fake or retrofit. Phase 1 proves the two riskiest primitives — an objective, agent-unwritable pass/fail check and a real `claude -p` invocation — before anything is built on top of assumptions. Phase 2 makes environment isolation mechanical (fresh worktree, scoped `HOME`, `--bare` + explicit flags) across vanilla/GSD-only/cairn, because environment leakage is the single highest-risk shortcut in this domain. Phase 3 adds repetition, success-gated cost aggregation, and four-way token decomposition, since these are harness-design-time decisions that cannot be retrofitted onto an already-run suite. Phase 4 isolates the competitor baseline into its own phase with a dedicated re-verification checkpoint, because a misconfigured competitor arm published publicly is the single worst reputational outcome available. Phase 5 expands the task corpus deliberately, including at least one category unfavorable to cairn, only once the full pipeline is proven on one task. Phase 6 is pure packaging — methodology doc, committed SVG charts, README embed, one-command reproduction — consuming already-validated data with no new data-collection risk.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Verification Core + First Real Run** - An objective `verify.sh` and a real `claude -p` invocation prove the harness's riskiest assumptions before anything else is built
- [x] **Phase 2: Baseline Isolation + Multi-Baseline Harness** - Every baseline runs in a fresh, disposable, mechanically-isolated environment with explicit, pinned configuration
- [x] **Phase 3: Repetition, Aggregation & Cost Decomposition** - Results are repeated, success-gated, and aggregated deterministically with full cost-component breakdown
- [x] **Phase 4: Competitor Baseline** - A competing workflow plugin is benchmarked fairly, on its own documented defaults, through the same isolated pipeline
- [x] **Phase 5: Corpus Expansion + Bias Controls** - The task corpus grows to a diverse, pre-declared set including an honest non-win category for cairn
- [x] **Phase 6: Reporting, Charts & Publication** - Results are packaged as credible public evidence: methodology, raw data, dated charts, one-command reproduction

## Phase Details

### Phase 1: Verification Core + First Real Run
**Goal**: Prove the harness's two highest-uncertainty pieces — an objective, agent-unwritable pass/fail check and a real (non-stubbed) `claude -p` invocation — before any statistics or presentation layer is built on top of unverified assumptions
**Depends on**: Nothing (first phase)
**Requirements**: HARN-01, HARN-02, HARN-03
**Success Criteria** (what must be TRUE):
  1. A task's `verify.sh` objectively passes against a hand-crafted "solved" fixture and fails against a hand-crafted "unsolved" fixture, proven by bats tests with no agent involved
  2. `bench-run.py` executes one (task, baseline, rep) run against a stubbed `claude` binary via an env-var seam, and the deterministic harness logic runs in bats CI at zero API cost
  3. `bench-run.py` executes one real, non-stubbed `claude -p --output-format json` call and correctly captures `total_cost_usd`, full `usage` (input/output/cache_creation/cache_read), `duration_ms`, `duration_api_ms`, `num_turns`, and `is_error` into a JSONL row
  4. Running the harness twice against the same stub input produces byte-identical JSONL output
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Task fixture + objective verify.sh, proven solved/unsolved via bats (HARN-01)
- [ ] 01-02-PLAN.md — bench-run.py harness + stub-based bats suite, byte-identical determinism (HARN-02, HARN-03)
- [ ] 01-03-PLAN.md — The single live claude -p run + methodology doc (HARN-02 live validation)

### Phase 2: Baseline Isolation + Multi-Baseline Harness
**Goal**: Every baseline (vanilla, GSD-only, cairn) runs under mechanically enforced, identical, isolated conditions, so no comparative number can later be attributed to environment leakage
**Depends on**: Phase 1
**Requirements**: FAIR-01, FAIR-02, FAIR-03
**Success Criteria** (what must be TRUE):
  1. Each run executes in a fresh, disposable worktree with an overridden `HOME`, and inspecting the actual config/context sent per baseline shows zero inherited personal CLAUDE.md, MCP servers, or hooks
  2. Vanilla, GSD-only, and cairn are each defined by an explicit baseline manifest (pinned full model id, identical task prompt, `--bare` plus explicit flags like `--max-turns`, `--no-session-persistence`)
  3. The same task run against all three baselines produces three separate JSONL rows whose environment manifests differ only in the intended baseline-specific configuration
  4. Execution order across baselines and repetitions is randomized/interleaved rather than run-all-of-one-then-next, and every run's cost is decomposed into the four components (uncached-input, cache-write, cache-read, output)
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Isolate the claude subprocess env + require --baseline; vanilla/gsd-only/cairn manifests (FAIR-01, FAIR-02)
- [ ] 02-02-PLAN.md — stage-plugins.py: pinned git/local provisioning materialization, real GSD staged (FAIR-02)
- [ ] 02-03-PLAN.md — bench-matrix.py seeded interleaving + conditional live smoke check (FAIR-03)

### Phase 3: Repetition, Aggregation & Cost Decomposition
**Goal**: Comparative numbers are statistically defensible — repeated enough times, gated on success, and aggregated deterministically — instead of single-run point estimates
**Depends on**: Phase 2
**Requirements**: METR-01, METR-02, METR-03
**Success Criteria** (what must be TRUE):
  1. Each (task, baseline) cell runs N≥5 repetitions, and `bench-aggregate.py` reports median plus spread per task, not only a single blended aggregate
  2. A run that fails `verify.sh` is excluded from the cost/token averages entirely — cost-per-successfully-completed-task is the only headline number produced
  3. Running `bench-aggregate.py` twice against the same raw JSONL produces a byte-identical `aggregated.json`
  4. `aggregated.json` reports all four cost/token components per cell separately (uncached-input, cache-write, cache-read, output), never one blended figure
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — bench-matrix.py --reps (default 5) + bench-run.py --rep-index, full baseline×rep interleave (METR-01)
- [ ] 03-02-PLAN.md — bench-aggregate.py: success-gated median/spread + 4-way modelUsage-preferred token decomposition, deterministic aggregated.json (METR-01, METR-02, METR-03)

### Phase 4: Competitor Baseline
**Goal**: A competing workflow plugin is benchmarked as a legitimate fourth arm — configured strictly from its own official defaults, version-pinned, and run through the identical isolated pipeline — so the comparison cannot be dismissed as sabotaged or unfairly configured
**Depends on**: Phase 3
**Requirements**: COMP-01
**Success Criteria** (what must be TRUE):
  1. The competitor's baseline manifest is configured strictly from its own official quickstart/documented defaults, with plugin version or commit pinned and recorded
  2. The competitor runs headless through the same isolated-worktree + `--bare` + fresh-`HOME` pipeline as vanilla/GSD-only/cairn, producing directly comparable JSONL rows
  3. The competitor's configuration is reviewed against its own documentation as an explicit re-verification checkpoint before any comparative results are generated
  4. The same task, run N≥5 times against the competitor baseline, appears in `aggregated.json` alongside the other three arms
**Plans**: 1 plan

Plans:
- [ ] 04-01-PLAN.md — competitor-ralph-specum.json (pinned tzachbon/smart-ralph@v4.0.0, defaults_source) + bench-run.py nested --plugin-dir resolution + load-check (COMP-01)

### Phase 5: Corpus Expansion + Bias Controls
**Goal**: The benchmark measures a deliberately diverse, pre-declared task set — including at least one category where cairn's overhead is a real cost, not a win — sized to actually distinguish baselines from noise
**Depends on**: Phase 4
**Requirements**: CORP-01, CORP-02
**Success Criteria** (what must be TRUE):
  1. The corpus contains multiple representative dev-workflow task categories (e.g. bugfix, feature, refactor), with selection criteria documented before any comparative results exist
  2. At least one task category is explicitly unfavorable to cairn (a trivial/single-turn task where planning overhead is pure loss) and runs through the same four-arm pipeline as every other task
  3. The total dollar cost of running the full expanded corpus once is calculated and documented before the full run is executed
  4. Task-selection rationale (why these tasks, why this count) is written down and committed alongside the corpus
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md — bugfix-inventory, feature-todo, refactor-report (anti-cheat), microedit-greet (honest-non-win), longhorizon-notify fixtures + two-direction bats proofs (CORP-01)
- [ ] 05-02-PLAN.md — bench-matrix.py --tasks (task x baseline x rep), category passthrough/surfacing, Task corpus + Cost model + Variance pilot (PENDING) docs, CI-enforced bias-control checks (CORP-01, CORP-02)

### Phase 6: Reporting, Charts & Publication
**Goal**: Results are packaged as credible public evidence — full methodology, raw data, dated script-generated charts, and a one-command reproduction path — rather than a bare marketing claim
**Depends on**: Phase 5
**Requirements**: REPT-01, REPT-02, REPT-03, REPT-04
**Success Criteria** (what must be TRUE):
  1. `BENCHMARKS.md` documents the full methodology, a results table, and links to the raw committed JSONL data
  2. Script-generated static SVG charts (comparison + cost-composition breakdown) are committed, each captioned with model id and date
  3. README embeds current results via generated markers (`<!-- cairn:generated:start/end -->`), regenerated by a script rather than hand-edited
  4. A single documented command reproduces the full benchmark run, including its estimated dollar cost
**Plans**: 3 plans

Plans:
- [ ] 06-01-PLAN.md — bench-chart.py: deterministic SVG cost+pass-rate and token-composition charts (REPT-02)
- [ ] 06-02-PLAN.md — BENCHMARKS.md (methodology-first) + bench-publish.py generated-marker regeneration (REPT-01, REPT-03)
- [ ] 06-03-PLAN.md — bench-all.sh: one-command reproduction, dry-run default, dollar cost ceiling (REPT-04)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Verification Core + First Real Run | 0/TBD | Complete | - |
| 2. Baseline Isolation + Multi-Baseline Harness | 0/3 | Complete | - |
| 3. Repetition, Aggregation & Cost Decomposition | 0/2 | Complete | - |
| 4. Competitor Baseline | 0/1 | Complete | - |
| 5. Corpus Expansion + Bias Controls | 0/TBD | Complete | - |
| 6. Reporting, Charts & Publication | 0/3 | Complete | - |
