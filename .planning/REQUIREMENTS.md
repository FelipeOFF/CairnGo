# Requirements: CairnGo v1.1 — Metrics & Benchmarks

**Defined:** 2026-07-25
**Core Value:** Workflow unificado plan→work→ship que custa menos tokens que as alternativas — provado por benchmark reproduzível.

## v1 Requirements

Requirements do milestone v1.1. Each maps to roadmap phases.

### Harness

- [ ] **HARN-01**: Task fixture com critério objetivo de conclusão: `verify.sh` por tarefa (exit code = pass/fail), nunca auto-relato do agente; formato bats-testável sem custo de API
- [ ] **HARN-02**: Runner (`bench-run.py`) invoca `claude -p --output-format json` headless e grava por rodada o resultado bruto em JSONL: `total_cost_usd`, `usage` completo (input/output/cache_creation/cache_read), `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`, wall-clock externo
- [ ] **HARN-03**: Lógica determinística do harness testável em bats via stub do binário `claude` (seam por env-var, padrão do repo) — CI nunca paga API; runs reais são job separado e deliberado

### Fairness

- [ ] **FAIR-01**: Cada rodada executa em ambiente isolado descartável (worktree fresco + `HOME` override) — zero herança de CLAUDE.md global, MCP servers ou hooks do operador
- [ ] **FAIR-02**: Baselines definidas por manifesto JSON explícito: mesmo modelo (id completo pinado), mesmo prompt de tarefa, `--bare` + flags explícitas (`--max-turns`, `--no-session-persistence`), mesmas condições entre vanilla / GSD puro / cairn / concorrente
- [ ] **FAIR-03**: Ordem de execução randomizada/intercalada entre baselines e custo decomposto em 4 componentes (uncached-input, cache-write, cache-read, output) — cache de prompt nunca contamina a comparação

### Metrics

- [ ] **METR-01**: N≥5 repetições por célula (tarefa × baseline); mediana e spread reportados por tarefa, não só agregado
- [ ] **METR-02**: Métrica principal = custo/tokens por tarefa **concluída com sucesso** (success-gated); rodada que falha o `verify.sh` nunca conta como economia
- [ ] **METR-03**: Agregador (`bench-aggregate.py`) determinístico: JSONL bruto → `aggregated.json` com estatísticas (repetível byte a byte sobre os mesmos dados)

### Competitor

- [ ] **COMP-01**: Baseline de ao menos um plugin de workflow concorrente rodando headless, com configuração documentada e validada (invocação justa — risco público de arm mal configurado é o maior risco reputacional)

### Corpus

- [ ] **CORP-01**: Corpus inicial de tarefas diversas (dimensionado na fase com piloto de variância), incluindo ao menos 1 categoria de tarefa desfavorável ao cairn (honest non-win)
- [ ] **CORP-02**: Custo total em $ de uma rodada completa da suite documentado e previsível antes de rodar

### Report

- [ ] **REPT-01**: `BENCHMARKS.md` methodology-first: metodologia completa, tabela de resultados, raw data (JSONL) commitado e linkado
- [ ] **REPT-02**: Gráficos comparativos SVG estáticos, datados (data + model id), gerados por script e commitados no repo
- [ ] **REPT-03**: Embed no README via generated markers (`<!-- cairn:generated:start/end -->`, padrão cairn-map)
- [ ] **REPT-04**: Reprodução em 1 comando documentada (incl. custo estimado da reprodução)

## v2 Requirements

Deferred. Tracked but not in current roadmap.

### Maintenance

- **MANT-01**: Cadência de re-run automatizada (model drift — resultados datados envelhecem)
- **MANT-02**: Archiving/pruning de `benchmarks/results/` conforme o repo crescer

### Presentation

- **PRES-01**: Dashboard/página web navegável (GitHub Pages)
- **PRES-02**: Telemetria contínua opt-in de sessões reais

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dashboard web | Decisão do Felipe: gráficos commitados primeiro; web depois |
| Telemetria de sessões reais | Não reproduzível/comparável — credibilidade vem da suite fixa |
| GIF/asciinema como visual principal | Felipe escolheu gráficos de benchmark |
| Leaderboard público multi-projeto | Escopo é comparar cairn vs alternativas, não hospedar benchmark geral |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| (preenchido na criação do roadmap) | | |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 0 (roadmap pendente)
- Unmapped: 14 ⚠️

---
*Requirements defined: 2026-07-25*
*Last updated: 2026-07-25 after research synthesis*
