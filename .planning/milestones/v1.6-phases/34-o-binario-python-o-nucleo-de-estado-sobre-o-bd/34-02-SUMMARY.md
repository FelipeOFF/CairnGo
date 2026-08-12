---
phase: 34-o-binario-python-o-nucleo-de-estado-sobre-o-bd
plan: 02
subsystem: gsd-dispatcher
tags: [bd, estado, caso-18, idempotencia, coleções]
requires: [34-01]
provides:
  - família estado completa (10 verbos) no cairn-gsd-state.py
  - labels de coleção gsd-blocker/gsd-decision
  - teste canônico do caso current_phase 18
affects: [34-03, 34-04, 34-05]
tech-stack:
  added: []
  patterns: [metadata não-transição (molde write_lease), derivado calculado na leitura, caminho único de transição de posição]
key-files:
  created:
    - tests/fixtures/gsd-goldens/state-update-*.golden.json
    - tests/fixtures/gsd-goldens/state-advance-plan*.golden.json
    - tests/fixtures/gsd-goldens/state-record-*.golden.json
    - tests/fixtures/gsd-goldens/state-add-*.golden.json
    - tests/fixtures/gsd-goldens/state-planned-phase.golden.json
  modified:
    - cairn/scripts/cairn-gsd-state.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "métricas e sessão são payload não-transição em cairn.gsd.* do metadata do portador — nunca label, nunca markdown"
  - "atribuição de record-metric vem SEMPRE do fato do portador; flags --phase/--plan aceitas mas não atributivas"
  - "planned-phase implementado junto da Task 1 (compartilha transition_position — uma implementação de transição, não duas)"
metrics:
  duration: ~30min
  completed: 2026-08-10
status: complete
---

# Phase 34 Plan 02: Família estado completa Summary

**One-liner:** os 8 verbos restantes de estado respondem do bd sobre a arquitetura do tracer — escritores de dimensão via set-state, coleções por label projetado, derivado calculado na leitura, e o caso current_phase 18 morto por teste que replayeia o incidente.

## Destino escolhido para métricas e sessão (registro pedido pelo plano)

- **Métricas (record-metric):** payload não-transição em `cairn.gsd.metrics[]` no metadata do portador — append de `{phase, plan, duration, tasks, files}` onde phase/plan vêm dos LABELS do portador (fato), nunca das flags nem de STATE.md. Leitura de fato não transiciona: labels byte-iguais antes/depois (provado por teste).
- **Sessão (record-session):** a dimensão `session=YYYY-MM-DD` transiciona via set-state (fato consultável por label); `stopped_at`/`resume_file` viram payload não-transição em `cairn.gsd.session` (molde write_lease). Envelope sem timestamp — nenhum mask necessário; o fato de tempo vive no label.

## Divergências declaradas novas (family estado)

1. `record-metric-destination` — tabela Performance Metrics de STATE.md deixa de ser escrita; destino é metadata do portador.
2. `record-metric-attribution-from-fact` — atribuição sempre do fato (o incidente 18 na raiz).
3. `update-progress-derived-only` — nada persistido; derivado na leitura.
4. `record-session-destination` — dimensão session + payload metadata em vez do bloco ## Session.
5. `update-envelope-lists-field` — `{updated: [<campo>]}` em vez de `{updated: true}` (paridade com o resto do irmão).

## O caso canônico (CORE-03)

Teste bats nomeado "caso canonico current_phase 18": fixture com `.planning/STATE.md` dizendo `Phase: 18` e portador com `phase:34`/`plan:34-02`; `state.record-metric --phase 18 --plan 18-02 --duration 5min` invocado DUAS vezes. As três asserções passam: (a) ambas atribuem a 34 (envelope cita 34/34-02, nunca 18); (b) labels do portador byte-iguais antes, entre e depois; (c) STATE.md byte-igual (sha256) — o verbo não escreve markdown. Regressão a leitura de prosa reprova a suíte.

## Guard de cobertura

`trivial_verbs_of` ganhou a família `estado`: o comm exige os 10 verbos de estado.json no `--list-implemented` agregado. Direção "extra" segue contra o universo completo do contrato (transição incremental — fecha bidirecional por família no plano 05).

## Desvios do plano

1. **planned-phase adiantado para a Task 1** — compartilha `transition_position` com begin-phase (o plano manda "uma implementação de transição, não duas"); o cenário/golden dele entrou na Task 2 como planejado.
2. **Linha `query state.update|estado|fase 34` removida do teste de representantes** — o verbo foi implementado; a via exit-4 do irmão segue coberta por roadmap.get-phase e pelos fantasmas.
3. Nenhum outro desvio — plano executado como escrito.

## Verificação

- `bats tests/cairn-gsd.bats` — 66/66 verde offline (fases 33 e plano 01 sem regressão).
- 10/10 verbos de estado em `--list-implemented`; guard comm vazio (universo trivial+estado ⊆ implementado; implementado ⊆ universo do contrato).
- `git status --porcelain cairn/gsd/` vazio.
- `wc -l cairn-gsd-state.py` = 759 (≤ 1500, D-01).

## Commits

- d84ca32 test(34-02): cenários dos escritores de dimensão (RED)
- 5ffc7e7 feat(34-02): escritores de dimensão — update, advance-plan, update-progress, record-session (GREEN)
- 724b2b2 test(34-02): caso canônico 18, coleções e guard com estado (RED)
- 8245e3f feat(34-02): família estado completa — coleções e record-metric do fato (GREEN)

## Self-Check: PASSED

- 11 goldens novos state-* existem e passam serialização da casa ✓
- commits d84ca32/5ffc7e7/724b2b2/8245e3f existem na branch ✓
- teto D-01 respeitado (759 ≤ 1500) ✓
