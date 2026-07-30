---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Honest State
status: planning
last_updated: "2026-07-29T18:53:00.646Z"
last_activity: 2026-07-29
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-29)

**Core value:** Workflow unificado plan→work→ship cujo estado é verificável — nenhuma superfície afirma que uma fase está pronta sem ter com o que corroborar.
**Current focus:** Milestone v1.4 (Honest State) — roadmap aprovado, 5 fases (13-17), nenhuma planejada ainda

## Current Position

Phase: 13 — Corroboração de estado (não planejada)
Plan: —
Status: Roadmap aprovado, aguardando /cairn:plan 13
Last activity: 2026-07-30 — Milestone v1.4 roadmap criado e aprovado

## Performance Metrics

**Velocity:**

- Total plans completed: 14
- Average duration: ~21 min (Phase 1 P03: 44min; Phase 2 P01/02/03: 16/8/15min; Phase 3 P01/02: 9/7min; Phase 4 P01: 6min; Phase 5 P01/02: 4/37min; Phase 6 P01/02/03: 45/32/51min)
- Total execution time: ~4h34m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | - | - |
| 2 | 3 | 39min | 13min |
| 3 | 2 | 16min | 8min |
| 4 | 1 | 6min | 6min |
| 5 | 2 | 41min | 21min |
| 6 | 3 | 128min | 43min |

**Recent Trend:**

- Last 5 plans: 05-02 (37min), 06-01 (45min), 06-02 (32min), 06-03 (51min)
- Trend: Phase 6's plans ran longer than average — each combined implementation + a TDD RED/GREEN bats suite + at least one full-suite regression run (193→199 tests), consistent with the phase's "prove it, don't assert it" discipline

*Updated after each plan completion*
| Phase 1 P03 | 44min | 2 tasks | 6 files |
| Phase 02 P01 | 16min | 2 tasks | 7 files |
| Phase 02 P02 | 8min | 2 tasks | 3 files |
| Phase 02 P03 | 15min | 2 tasks | 5 files |
| Phase 03 P01 | 9min | 2 tasks | 3 files |
| Phase 03 P02 | 7min | 2 tasks | 6 files |
| Phase 04 P01 | 6min | 3 tasks | 4 files |
| Phase 05 P01 | 4min | 3 tasks | 29 files |
| Phase 05 P02 | 37min | 3 tasks | 9 files |
| Phase 06 P01 | 45min | 2 tasks | 3 files |
| Phase 06 P02 | 32min | 3 tasks | 5 files |
| Phase 06 P03 | 51min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Visual do milestone = gráficos SVG commitados, gerados por script (não GIF, não dashboard web) — Phase 6
- Roadmap: 3 baselines comparativas além do cairn (vanilla, GSD puro, concorrente) — Phases 2 e 4
- Roadmap: baseline concorrente isolada em fase própria (Phase 4) por risco reputacional público, conforme pesquisa
- [Phase 1]: Model id sempre pinado via task.json (alias claude-haiku rejeitado pela API) — FAIR-02 antecipado por necessidade
- [Phase 1]: verify_passed e is_error são eixos independentes (row error_max_turns com fixture resolvida) — base para METR-02
- [Phase 1]: Flag --bare removida do harness: ignora OAuth claude.ai (verificado ao vivo); baselines isoladas da fase 2 exigem ANTHROPIC_API_KEY
- [Phase 02]: seed/run_order_index reservados no opts dict de bench-run.py sem branches de argv — Instrução do plan-checker: 02-03 adiciona e testa os branches; evita segunda edição do parser mas não antecipa comportamento não testado
- [Phase 02]: task.json não exige mais 'model': baseline manifest é a única fonte de verdade dos claude flags — FAIR-02: pinning auditável por manifest; task.json mantém id/timeout_s/prompt_file
- [Phase 02]: 02-02: staging temp dir e sibling real (dir=staged.parent) p/ rename atomico; .staged-ref escrito por ultimo como marker de idempotencia
- [Phase 02]: 02-02: testes de staging usam url.insteadOf via GIT_CONFIG_* env como seam de rede — script identico a producao, zero rede real
- [Phase 02]: bench-matrix.py: --seed obrigatório (sem default aleatório silencioso); seed+run_order_index stampados em toda row orquestrada (FAIR-03)
- [Phase 02]: Live isolation smoke check documentado como PENDING no benchmarks/README.md (ANTHROPIC_API_KEY ausente, re-checado 2026-07-26); mecanismo provado a $0 via bats
- [Phase 02]: Verificado passed (4/4 must-haves) em 2026-07-26 — ver 02-VERIFICATION.md
- [Phase 03]: bench-matrix.py `--reps` (default 5, METR-01) shuffla o cross-product completo `baseline x rep` com um único `random.Random(seed)` — reps nunca ficam em bloco contíguo por baseline (verificado seed 7 e, independentemente, seed 42/seed 777)
- [Phase 03]: bench-run.py `--rep-index` espelha `--seed`/`--run-order-index` exatamente: opcional, stampado só quando presente (zero regressão a invocações standalone)
- [Phase 03]: bench-aggregate.py: gate belt-and-braces `verify_passed is True and not is_error` — linha com `verify_passed=true, is_error=true` nunca conta em `n_passed` nem em custo/token (METR-02), verificado por hand-computation independente
- [Phase 03]: decomposição de tokens 4-way prefere `modelUsage` sobre `usage` (usage sub-reporta ~30% em dados reais); fallback para `usage` quando `modelUsage` ausente
- [Phase 03]: aggregated.json determinístico via `sorted()` em paths/cells + `json.dumps(sort_keys=True, separators=(",",":"))`, sem timestamps — datação fica para Phase 6 a partir de dados já presentes nas rows
- [Phase 03]: linhas malformadas ou faltando campo obrigatório (usage/verify_passed/baseline_id/task_id) nunca derrubam o aggregator — contadas em `rejected_rows`, nunca descartadas silenciosamente
- [Phase 03]: Verificado passed (3/3 must-haves, 29/29 bats) em 2026-07-26 — ver 03-VERIFICATION.md
- [Phase 04]: Competidor escolhido pela pesquisa autônoma: `ralph-specum` (tzachbon/smart-ralph), pinado `v4.0.0` (tag mais recente real, re-confirmado ao vivo via `git ls-remote --tags` tanto no plan quanto na verificação); spec-kit e BMAD desqualificados estruturalmente (sem plugin.json carregável via --plugin-dir), superpowers deferido (sem escape hatch não-interativo)
- [Phase 04]: `plugin_dir_subpath` — extensão opcional e retrocompatível do schema de manifesto (`Path(staged_path) / entry.get("plugin_dir_subpath", "")`, no-op quando ausente) para plugins cujo `plugin.json` não fica na raiz do repo clonado; `stage-plugins.py` não precisou de nenhuma mudança
- [Phase 04]: Verificado gaps_found (8/9 must-haves) em 2026-07-26 — ver 04-VERIFICATION.md. 1 gap minor/não-bloqueante: ROADMAP SC4 (N≥5 rodadas ao vivo do competidor em aggregated.json) não executado — nenhum aggregated.json existe no repo para nenhum dos 4 arms ainda; bloqueado por ANTHROPIC_API_KEY ausente (confirmado independentemente); 04-CONTEXT.md já previa esse adiamento explicitamente para o limite Phase 5/6. Toda a mecânica que a SC depende (pipeline isolado, --plugin-dir resolvido, agregação success-gated) foi provada correta independentemente — falta apenas a coleta de dados ao vivo (decisão de gasto do operador, não defeito de código). Sugerido override formal em 04-VERIFICATION.md para quem aceitar o adiamento.
- [Phase 05]: Corpus de 6 categorias pré-declaradas (smoke/bugfix/feature/refactor/honest-non-win/long-horizon), commitadas antes de qualquer resultado agregado existir (nenhum aggregated.json no repo) — disciplina anti-cherry-picking (Pitfall 3)
- [Phase 05]: refactor-report usa oráculo de duas camadas: unittest (comportamento) + grep estrutural anti-cheat (`total += r["amount"]` <=1 ocorrência) — o fixture bruto passa no unittest mas falha no verify.sh, provando que "passar nos testes" não basta
- [Phase 05]: bench-matrix.py `--tasks` (lista separada por vírgula ou glob absoluto via stdlib `glob.glob`, não `pathlib.Path.glob` que rejeita padrões absolutos no py3.12) generaliza o shuffle para `task x baseline x rep`; `--task` singular permanece byte-idêntico
- [Phase 05]: `category` flui de task.json para a row (omitido quando ausente) e para toda cell agregada (sempre presente, `null` quando ausente) — filosofias deliberadamente diferentes em cada arquivo, cada uma seguindo o precedente já estabelecido no próprio arquivo
- [Phase 05]: Variance pilot documentado como PENDING (ANTHROPIC_API_KEY ausente, re-checado 2026-07-26) — receita de um comando pronta, mesma disciplina das Phases 2/4; coleta de dados ao vivo explicitamente adiada para Phase 6
- [Phase 05]: Verificado passed (15/15 must-haves, 57/57 bats nos 7 arquivos requeridos) em 2026-07-26 — ver 05-VERIFICATION.md. Nota informativa não-bloqueante: REQUIREMENTS.md/beads (CairnGo-me5, CairnGo-6qo) ainda mostram CORP-01/CORP-02 como Pending/IN_PROGRESS — lag de sincronização de tracking, mesmo padrão já reconhecido para COMP-01 na Phase 4; toda a capacidade descrita pelos requirements está implementada, testada e reproduzida independentemente.
- [Phase 06]: bench-chart.py gera SVG determinístico stdlib-only (sem gnuplot, desvio deliberado de STACK.md, decisão travada em 06-CONTEXT.md) — honestidade: célula com cost_median/token median nulo nunca renderiza barra zero fabricada, sempre um marcador "no data" pareado com o pass_rate real
- [Phase 06]: bench-publish.py porta o mecanismo exato de split_markers/replace-only-inner/append-never-destroy/write-only-when-changed de cairn-map.py, parametrizado por par de marcador — usado tanto para BENCHMARKS.md quanto para o teaser do README
- [Phase 06]: bench-all.sh nunca assume gasto pelo ambiente: modo default é sempre --dry-run mesmo com ANTHROPIC_API_KEY presente; --yes exige a flag explícita E a chave não-vazia; contrato de invocação zero provado por tripwire mecânico, não só leitura de código
- [Phase 06]: Verificado gaps_found (18/19 must-haves) em 2026-07-26 — ver 06-VERIFICATION.md. 1 gap minor/não-bloqueante, aceito: ROADMAP SC2 (gráficos SVG commitados) não satisfeito literalmente — zero SVG commitado no repo, por design (regra de honestidade de 06-CONTEXT.md: nenhum número sintético é commitado como se fosse resultado real). Bloqueado por ANTHROPIC_API_KEY ausente (confirmado independentemente); mesma disciplina já aceita nas Phases 4 e 5. Toda a maquinaria (bench-chart.py, bench-publish.py, bench-all.sh) foi reproduzida manualmente de ponta a ponta nesta verificação com dados reais (não sintéticos) do stub — determinismo, honestidade de dados nulos, regeneração byte-idêntica fora dos marcadores, e os gates de segurança dry-run/--yes todos confirmados independentemente. Falta apenas a coleta de dados ao vivo (decisão de gasto do operador, ~$40), um comando de distância (`bench-all.sh --yes`). REPT-01/03/04 plenamente satisfeitos; REPT-02 satisfeito na maquinaria, pendente na população de dados reais. Milestone v1.1: 6/6 fases executadas e verificadas — pronto para gate/ship.

### Pending Todos

None yet.

### Blockers/Concerns

- ROADMAP.md e REQUIREMENTS.md ainda mostram REPT-01..04 como "Pending"/unchecked (mesmo padrão de lag de tracking já reconhecido para COMP-01/CORP-01/CORP-02) — toda a maquinaria de publicação/gráficos/reprodução está completa, testada e reproduzida independentemente (ver 06-VERIFICATION.md); falta apenas a coleta de dados ao vivo
- Nenhuma rodada ao vivo (N≥5, 4 arms, corpus completo) foi de fato executada em nenhuma fase do milestone v1.1 — bloqueado por ANTHROPIC_API_KEY ausente em todo o ambiente de desenvolvimento; a maquinaria inteira (Phases 1-6) está a um único comando (`bench-all.sh --yes`, ~$40) de produzir resultados reais e publicáveis, assim que um operador autorizar o gasto

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260725-mbr | Status board kanban no /cairn:status + docs dos 22 comandos (bd: CairnGo-4ju) | 2026-07-25 | (ver PR) | Verified | [260725-mbr-status-board-e-docs-completa](./quick/260725-mbr-status-board-e-docs-completa/) |

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Data collection | Live N≥5 matrix (4 arms incl. competitor) in `aggregated.json` — ROADMAP Phase 4 SC4 | Parked (minor gap, non-blocking) | Phase 4 verification (2026-07-26), blocked on ANTHROPIC_API_KEY |
| Data collection | Variance pilot (3 tasks x 2 arms x N=5) + full 120-run matrix — ROADMAP Phase 5, CORP-01 | Documented PENDING recipe, not yet run | Phase 5 planning + verification (2026-07-26), blocked on ANTHROPIC_API_KEY, explicitly deferred to Phase 6 |
| Data collection | Real committed SVG charts + filled BENCHMARKS.md/README.md Results — ROADMAP Phase 6 SC1-SC3 (REPT-01/02/03) | Accepted, non-blocking gap; full publication machinery proven correct at $0 | Phase 6 verification (2026-07-26), blocked on ANTHROPIC_API_KEY, deferred to post-milestone operator action (`benchmarks/scripts/bench-all.sh --yes`) |

## Session Continuity

Last session: 2026-07-26T10:33:00Z
Stopped at: Verified Phase 6 (Reporting, Charts & Publication) — 18/19 must-haves, 21/21 phase-6 bats green (+14/14 spot-checked regression), $0; 0 blocking gaps (see 06-VERIFICATION.md). Milestone v1.1 execution complete (6 of 6 phases), pending gate/ship.
Resume file: None

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
