# CairnGo

## What This Is

CairnGo ("cairn") é um plugin de Claude Code que funde GSD (planejamento por fases) com beads/bd (issue tracker git-nativo) num lifecycle único: comandos `/gsd:*` criam, claimam e fecham issues bd automaticamente, com ship gate por hook de git. v1.0.0 shipada e pública em `FelipeOFF/CairnGo`. Este ciclo estrutura o próximo diferencial: **provar com números que o cairn gasta menos tokens que as alternativas**.

## Core Value

Workflow unificado plan→work→ship que custa menos tokens que as alternativas — e agora provado por benchmark reproduzível, não por afirmação.

## Requirements

### Validated

- ✓ Benchmark harness completo e reproduzível (bench-run/matrix/aggregate/chart/publish/all, 199 testes bats a $0 de API) — v1.1
- ✓ Isolamento mecânico de ambiente (HOME fresco, env replace, manifests pinados 4 arms incl. concorrente ralph-specum) — v1.1
- ✓ Métricas honestas: success-gating belt-and-braces, decomposição 4-way modelUsage-preferred, N=5 interleaved — v1.1
- ✓ Corpus pré-declarado de 6 tasks incl. honest-non-win + cost model ~$40 CI-enforced — v1.1
- ✓ Publicação methodology-first (BENCHMARKS.md, charts determinísticos, embed por markers, reprodução 1 comando) — v1.1
- ✓ Unificação GSD↔beads (issues por requirement, label pair `m-<milestone>`+`phase-<N>`, stamp `metadata.gsd`) — v1.0
- ✓ Scripts determinísticos: cairn-map, cairn-relabel, cairn-gate, cairn-doctor, cairn-migrate (detect/plan/apply com journal) — v1.0
- ✓ Migração de repos existentes (modos A/B/C/W/D) — v1.0
- ✓ Sync adapters (jira, github, gitlab, azure-boards, asana) via gbsync — v1.0
- ✓ Integração context-mode (memória intent-aware escopada por issue+fase) — v1.0
- ✓ Suite bats (92+ testes) + CI — v1.0

### Active

(próximo milestone a definir — candidatos: coleta live + publicação dos números (requer ANTHROPIC_API_KEY, ~$40), v2 backlog: re-run cadence, dashboard web, segundo arm concorrente)

- [ ] Coleta real da matriz completa (120 runs) e publicação dos resultados/charts

### Out of Scope

- Dashboard/página web de resultados — futuro; gráficos commitados primeiro (decisão do Felipe, 2026-07-25)
- Telemetria contínua de sessões reais — não escolhida; reproduzibilidade e credibilidade vêm da suite fixa
- GIF/asciinema como demonstração principal — Felipe escolheu gráficos de benchmark como o visual

## Current State

**v1.1 shipped 2026-07-27.** Benchmark harness completo em `benchmarks/` (~22k linhas adicionadas no milestone, 199 testes bats, $2.88 de API gastos — só validação de schema). O que existe: 6 tasks de corpus provadas bidirecionalmente, 4 arms pinados e isolados, agregação determinística success-gated, publicação methodology-first com resultados honestamente pendentes. Ação de operador pendente: `bench-all.sh --yes` com key (~$40) coleta e publica os números reais.

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
| Visual = gráficos de benchmark commitados (não GIF, não web) | Embed direto no README, gerável por script, zero infra | ✓ Good (maquinaria pronta; SVGs entram com dados reais) |
| 3 baselines: vanilla, GSD puro, plugin concorrente | Vanilla = leitura universal; GSD puro = isola ganho do cairn; concorrente = diferencial competitivo | ✓ Good (4 arms shipped; concorrente = ralph-specum v4.0.0) |
| Coleta via suite reproduzível (não telemetria) | Credibilidade: qualquer um reproduz; telemetria não é comparável | ✓ Good (bench-all.sh 1 comando) |
| --bare exige ANTHROPIC_API_KEY (OAuth não funciona headless isolado) | Verificado ao vivo na fase 1 | ✓ Good |
| Decomposição prefere modelUsage sobre usage | usage under-reporta cache_creation ~30% (verificado por aritmética vs pricing) | ✓ Good |
| Zero número sintético publicado; SVGs só com dados reais | Credibilidade methodology-first (inverso do anti-padrão claim-sem-dado) | ✓ Good |

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
*Last updated: 2026-07-27 after v1.1 milestone (Metrics & Benchmarks — shipped)*
