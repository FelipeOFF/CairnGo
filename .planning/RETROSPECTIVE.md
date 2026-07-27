# Retrospective: CairnGo

Living retrospective — one section per shipped milestone.

## Milestone: v1.1 — Metrics & Benchmarks

**Shipped:** 2026-07-27
**Phases:** 6 | **Plans:** 14 | **Tasks:** 17

### What Was Built

Reproducible benchmark harness proving cairn's efficiency claims: objective per-task `verify.sh` oracles, isolated headless `claude -p` runner with stub seam (CI at $0), 4 pinned baseline arms (vanilla / gsd-only / cairn / competitor ralph-specum), seeded-interleaved N=5 repetitions, deterministic success-gated aggregation with 4-way token decomposition, 6-task pre-declared corpus including an honest-non-win category, and methodology-first publication machinery (BENCHMARKS.md, deterministic SVG charts, marker embeds, one-command reproduction behind a double-gated spend guard).

### What Worked

- **The autonomous loop** (`/cairn:autonomous`, first real run): plan → claim → execute → close → verify → doctor per phase closed 16/16 bd issues across 6 phases with a single human intervention (CLI auth). Checkpoints between phases caught nothing broken — because the plan-checkers caught issues *before* execution.
- **Plan-checker gates earned their cost**: caught an unprovisioned pytest dependency (would have broken CI on every fresh clone) and a py3.12 `Path.glob()` absolute-pattern crash *in the plan's own test* before any executor touched code.
- **Stub-first discipline**: 199 bats tests, $0 of API in CI, and every mechanism (isolation, gating, determinism, fairness) black-box-provable. Total API spend for the whole milestone: $2.88, all of it deliberate schema validation.
- **Front-loading the riskiest primitives** (Phase 1's live run) paid immediately: three assumptions died on contact with reality (`--bare`×OAuth, model aliases, exit-code contract) at trivial cost instead of exploding in Phase 3.

### What Was Inefficient

- ~$1.30 lost to a missing out-dir guard (API call succeeded, row write crashed) — now impossible by construction (validate-before-spend), but the lesson cost real money.
- Executor subagents cannot reach the OS keychain; the live run had to move to the orchestrator. Worth designing for upfront in future harness work.
- Full `bats tests/` grew to ~10min; two executors burned time on duplicate full-suite passes. A scoped-suite convention per plan would have saved ~20min.

### Patterns Established

- Conditional-live discipline: anything needing `ANTHROPIC_API_KEY` degrades to a documented PENDING with a verbatim reproduction command — never blocks a phase, never fakes a result.
- Honesty as mechanism, not policy: no-synthetic-numbers enforced by bats (zero SVG committed, pending notice inside generated markers), unfavorable-category task required by CI grep.
- `modelUsage`-preferred token accounting (flat `usage` under-reports cache_creation ~30%).
- Env-var stub seams (`CAIRN_BENCH_CLAUDE_BIN`) + tripwire stubs to prove non-invocation.

### Key Lessons

- Verify assumptions against the installed binary, not docs: `claude --help` was more current than the public docs page; `--bare`'s auth behavior existed nowhere in writing.
- The fairest competitor arm is the one you can prove loaded: the load-check (plugin visible in isolated env) is the difference between benchmarking a competitor and benchmarking dead weight.
- Checker feedback loops (max 3 revisions) converge in 1 iteration when research/context are strong — invest in CONTEXT.md quality, not more checker rounds.

### Cost Observations

- Model mix: researchers/planners/checkers/verifiers on sonnet; executors inherited session model; orchestration on Fable.
- ~30 subagent runs across the milestone (researchers 5, pattern-mappers 3, planners 7 incl. revisões, checkers 6, executors 11, verifiers 6).
- API (benchmark target) spend: $2.88 total, itemized in benchmarks/README.md.

## Cross-Milestone Trends

| Milestone | Phases | Plans | Bats tests | API spend | Human interventions |
|---|---|---|---|---|---|
| v1.1 | 6 | 14 | 199 | $2.88 | 1 (CLI auth) |
