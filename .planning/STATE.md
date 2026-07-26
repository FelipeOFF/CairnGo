---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: milestone
status: executing
stopped_at: Verified Phase 4 (Competitor Baseline) — 32/32 bats green, $0; 1 minor gap parked (live N>=5 matrix pending ANTHROPIC_API_KEY)
last_updated: "2026-07-26T06:01:38Z"
last_activity: "2026-07-26 — Phase 4 verified: competitor-ralph-specum manifest pinned v4.0.0 + FAIR-02 byte-identical claude_flags/model + nested plugin_dir_subpath resolution + fail-loud + $0 load-check (COMP-01), 32/32 bats, $0. 1 minor gap: ROADMAP SC4 (N>=5 live matrix in aggregated.json) not yet run — blocked on ANTHROPIC_API_KEY, deferred to Phase 5/6 per 04-CONTEXT.md"
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 9
  completed_plans: 9
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-25)

**Core value:** Workflow unificado plan→work→ship que custa menos tokens que as alternativas — e agora provado por benchmark reproduzível, não por afirmação.
**Current focus:** Phase 5 — Corpus Expansion + Bias Controls (Phase 4 complete and verified, 1 minor gap parked to backlog)

## Current Position

Phase: 4 of 6 (Competitor Baseline) — complete, verified (gaps_found: 1 minor, non-blocking)
Plan: 1 of 1 in phase (complete)
Status: Phase 4 verified gaps_found (8/9 must-haves; 1 minor gap parked); ready to plan Phase 5
Last activity: 2026-07-26 — Phase 4 verified: competitor-ralph-specum manifest pinned v4.0.0, FAIR-02 byte-identical claude_flags/model, nested plugin_dir_subpath resolution (backward-compatible), fail-loud before spend, $0 load-check proof + documented live command (COMP-01), 32/32 bats green, $0 spend. Gap: ROADMAP SC4 (N≥5 live matrix results in aggregated.json) not yet executed — no aggregated.json exists for any arm yet, blocked on ANTHROPIC_API_KEY (genuinely absent), explicitly deferred to Phase 5/6 data-collection boundary per 04-CONTEXT.md's own locked decision. Classified minor/non-blocking — parked to backlog, not escalated.

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 9
- Average duration: ~19 min (Phase 1 P03: 44min; Phase 2 P01/02/03: 16/8/15min; Phase 3 P01/02: 9/7min; Phase 4 P01: 6min)
- Total execution time: ~1h45m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | - | - |
| 2 | 3 | 39min | 13min |
| 3 | 2 | 16min | 8min |
| 4 | 1 | 6min | 6min |

**Recent Trend:**

- Last 5 plans: 02-03 (15min), 03-01 (9min), 03-02 (7min), 04-01 (6min)
- Trend: shrinking per-plan duration (harness scripts increasingly mirror established patterns)

*Updated after each plan completion*
| Phase 1 P03 | 44min | 2 tasks | 6 files |
| Phase 02 P01 | 16min | 2 tasks | 7 files |
| Phase 02 P02 | 8min | 2 tasks | 3 files |
| Phase 02 P03 | 15min | 2 tasks | 5 files |
| Phase 03 P01 | 9min | 2 tasks | 3 files |
| Phase 03 P02 | 7min | 2 tasks | 6 files |
| Phase 04 P01 | 6min | 3 tasks | 4 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- gnuplot vs. SVG stdlib hand-rolled é julgamento de valor, não fato documentado — decidir no planejamento da Phase 6
- Tamanho/diversidade do corpus (Phase 5) não tem regra universal — decisão deliberada no planejamento da Phase 5, informada pela restrição de custo previsível
- ROADMAP.md e REQUIREMENTS.md ainda mostram COMP-01 como "Pending"/unchecked — parcialmente correto agora: configuração/wiring está completa e verificada, mas nenhuma rodada ao vivo (N≥5) foi de fato executada ainda (ver 04-VERIFICATION.md gap); recomenda-se rodar o live matrix completo (4 arms x N≥5) assim que ANTHROPIC_API_KEY estiver disponível, idealmente coordenado com o planejamento da Phase 5

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260725-mbr | Status board kanban no /cairn:status + docs dos 22 comandos (bd: CairnGo-4ju) | 2026-07-25 | (ver PR) | Verified | [260725-mbr-status-board-e-docs-completa](./quick/260725-mbr-status-board-e-docs-completa/) |

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Data collection | Live N≥5 matrix (4 arms incl. competitor) in `aggregated.json` — ROADMAP Phase 4 SC4 | Parked (minor gap, non-blocking) | Phase 4 verification (2026-07-26), blocked on ANTHROPIC_API_KEY |

## Session Continuity

Last session: 2026-07-26T06:01:38Z
Stopped at: Verified Phase 4 (Competitor Baseline) — 32/32 bats green, $0; 1 minor gap parked (live N>=5 matrix pending ANTHROPIC_API_KEY, see 04-VERIFICATION.md)
Resume file: None
