# CairnGo

## What This Is

CairnGo ("cairn") é um plugin de Claude Code que funde GSD (planejamento por fases) com beads/bd (issue tracker git-nativo) num lifecycle único: comandos `/gsd:*` criam, claimam e fecham issues bd automaticamente, com ship gate por hook de git. v1.0.0 shipada e pública em `FelipeOFF/CairnGo`. Este ciclo estrutura o próximo diferencial: **provar com números que o cairn gasta menos tokens que as alternativas**.

## Core Value

Workflow unificado plan→work→ship que custa menos tokens que as alternativas — e agora provado por benchmark reproduzível, não por afirmação.

## Requirements

### Validated

- ✓ Unificação GSD↔beads (issues por requirement, label pair `m-<milestone>`+`phase-<N>`, stamp `metadata.gsd`) — v1.0
- ✓ Scripts determinísticos: cairn-map, cairn-relabel, cairn-gate, cairn-doctor, cairn-migrate (detect/plan/apply com journal) — v1.0
- ✓ Migração de repos existentes (modos A/B/C/W/D) — v1.0
- ✓ Sync adapters (jira, github, gitlab, azure-boards, asana) via gbsync — v1.0
- ✓ Integração context-mode (memória intent-aware escopada por issue+fase) — v1.0
- ✓ Suite bats (92+ testes) + CI — v1.0

### Active

(milestone v1.1 — Metrics & Benchmarks; requirements formais serão definidos após a pesquisa)

- [ ] Benchmark suite reproduzível: conjunto fixo de tarefas de desenvolvimento executadas por harness, N repetições, resultados determinísticos o suficiente pra comparação honesta
- [ ] Métrica: consumo de tokens por tarefa (input/output/cache, custo estimado)
- [ ] Métrica: tempo de ação e execução por tarefa (wall-clock, nº de tool calls/turnos)
- [ ] Baselines comparados: Claude Code vanilla, GSD puro (sem cairn), e ao menos um plugin de workflow concorrente
- [ ] Demonstração visual: gráficos comparativos gerados por script e commitados no repo (README)

### Out of Scope

- Dashboard/página web de resultados — futuro; gráficos commitados primeiro (decisão do Felipe, 2026-07-25)
- Telemetria contínua de sessões reais — não escolhida; reproduzibilidade e credibilidade vêm da suite fixa
- GIF/asciinema como demonstração principal — Felipe escolheu gráficos de benchmark como o visual

## Context

- Brownfield: mapa da codebase em `.planning/codebase/` (7 docs, 2026-07-25).
- Quick task em voo (CairnGo-4ju): redesign do `/cairn:status` como board kanban + documentação dos 22 comandos — corre fora deste roadmap.
- Concerns conhecidos do mapa: race no gbsync id-map, parsing regex leniente de ROADMAP/STATE, adapters sem cobertura funcional. Não são deste milestone, ficam registrados.

## Constraints

- **House style**: python3 zero-dependências + wrappers bash + testes bats — benchmark harness segue o molde de `cairn/scripts/`.
- **Custo**: benchmarks executam Claude Code real (custo de API por rodada) — a suite precisa ser rodável por terceiros com custo previsível e documentado.
- **Honestidade metodológica**: comparação só é diferencial se a metodologia aguentar escrutínio público (tarefas idênticas, mesmas condições, variância reportada).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Visual = gráficos de benchmark commitados (não GIF, não web) | Embed direto no README, gerável por script, zero infra | — Pending |
| 3 baselines: vanilla, GSD puro, plugin concorrente | Vanilla = leitura universal; GSD puro = isola ganho do cairn; concorrente = diferencial competitivo | — Pending |
| Coleta via suite reproduzível (não telemetria) | Credibilidade: qualquer um reproduz; telemetria não é comparável | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-25 after initialization (milestone v1.1 — Metrics & Benchmarks)*
