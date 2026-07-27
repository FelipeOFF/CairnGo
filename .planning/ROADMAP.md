# Roadmap: CairnGo

## Milestones

- ✅ **v1.1 Metrics & Benchmarks** — Phases 1-6 (shipped 2026-07-27)

## Phases

<details>
<summary>✅ v1.1 Metrics & Benchmarks (Phases 1-6) — SHIPPED 2026-07-27</summary>

- [x] Phase 1: Verification Core + First Real Run (3/3 plans) — completed 2026-07-25
- [x] Phase 2: Baseline Isolation + Multi-Baseline Harness (3/3 plans) — completed 2026-07-26
- [x] Phase 3: Repetition, Aggregation & Cost Decomposition (2/2 plans) — completed 2026-07-26
- [x] Phase 4: Competitor Baseline (1/1 plan) — completed 2026-07-26
- [x] Phase 5: Corpus Expansion + Bias Controls (2/2 plans) — completed 2026-07-26
- [x] Phase 6: Reporting, Charts & Publication (3/3 plans) — completed 2026-07-26

Full details: [milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
| ----- | --------- | -------------- | ------ | --------- |
| 1. Verification Core + First Real Run | v1.1 | 3/3 | Complete | 2026-07-25 |
| 2. Baseline Isolation + Multi-Baseline Harness | v1.1 | 3/3 | Complete | 2026-07-26 |
| 3. Repetition, Aggregation & Cost Decomposition | v1.1 | 2/2 | Complete | 2026-07-26 |
| 4. Competitor Baseline | v1.1 | 1/1 | Complete | 2026-07-26 |
| 5. Corpus Expansion + Bias Controls | v1.1 | 2/2 | Complete | 2026-07-26 |
| 6. Reporting, Charts & Publication | v1.1 | 3/3 | Complete | 2026-07-26 |

## Post-milestone operator action (v1.1)

Real data collection: `bash benchmarks/scripts/bench-all.sh --yes` with `ANTHROPIC_API_KEY` exported (~$40 ceiling, 120 runs) — fills BENCHMARKS.md Results + charts. Next milestone starts with `/cairn:milestone new`.
