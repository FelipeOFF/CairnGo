# Roadmap: CairnGo

## Milestones

- ✅ **v1.1 Metrics & Benchmarks** — Phases 1-6 (shipped 2026-07-27)
- 🚧 **v1.2 GSD Core** — Phases 7-9 (official source, working fusion)
- **v1.3 Status Panel** — Phases 10-12 (a surface you can act on)

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

### 🚧 v1.2 GSD Core — official source, working fusion (Phases 7-9)

- [x] Phase 7: Official source + proven capability install (GSD-01, GSD-02) — completed 2026-07-28
- [x] Phase 8: Upgrade path and lineage reporting (GSD-03, GSD-04) — completed 2026-07-28
- [ ] Phase 9: Adopt what gsd-core brings (GSD-05)

### v1.3 Status Panel — a surface you can act on (Phases 10-12)

- [ ] Phase 10: Phase model — read what a phase actually is (PANEL-01)
- [ ] Phase 11: Described pending list + next commands with their order (PANEL-02, PANEL-03)
- [ ] Phase 12: Parallelism surfaced + the board fills the screen (PANEL-04, PANEL-05)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
| ----- | --------- | -------------- | ------ | --------- |
| 1. Verification Core + First Real Run | v1.1 | 3/3 | Complete | 2026-07-25 |
| 2. Baseline Isolation + Multi-Baseline Harness | v1.1 | 3/3 | Complete | 2026-07-26 |
| 3. Repetition, Aggregation & Cost Decomposition | v1.1 | 2/2 | Complete | 2026-07-26 |
| 4. Competitor Baseline | v1.1 | 1/1 | Complete | 2026-07-26 |
| 5. Corpus Expansion + Bias Controls | v1.1 | 2/2 | Complete | 2026-07-26 |
| 6. Reporting, Charts & Publication | v1.1 | 3/3 | Complete | 2026-07-26 |
| 7. Official source + proven capability install | v1.2 | 1/1 | Complete | 2026-07-28 |
| 8. Upgrade path and lineage reporting | v1.2 | 1/1 | Complete | 2026-07-28 |
| 9. Adopt what gsd-core brings | v1.2 | 0/? | Not started | — |
| 10. Phase model | v1.3 | 0/? | Not started | — |
| 11. Described pending list + next commands | v1.3 | 0/? | Not started | — |
| 12. Parallelism surfaced + board fills the screen | v1.3 | 0/? | Not started | — |

## Post-milestone operator action (v1.1)

Real data collection: `bash benchmarks/scripts/bench-all.sh --yes` with `ANTHROPIC_API_KEY` exported (~$40 ceiling, 120 runs) — fills BENCHMARKS.md Results + charts. Next milestone starts with `/cairn:milestone new`.
