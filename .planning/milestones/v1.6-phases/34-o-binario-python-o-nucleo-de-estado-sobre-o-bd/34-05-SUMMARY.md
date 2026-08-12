---
phase: 34-o-binario-python-o-nucleo-de-estado-sobre-o-bd
plan: 05
subsystem: gsd-dispatcher
tags: [misc, guard, cobertura, fecho]
requires: [34-01, 34-02, 34-03, 34-04]
provides:
  - misc completo nos dois irmãos (7 + 17)
  - guard de cobertura total (10 famílias, comm bidirecional, órfãos pela constante)
  - cairn_gsd_render.py (fonte única do envelope medido)
affects: [fase-35, fase-36]
tech-stack:
  added: []
  patterns: [indisponibilidade declarada no envelope, fantasma respondido pelo caminho de erro do contrato, cobertura derivada do inventário]
key-files:
  created:
    - cairn/scripts/cairn_gsd_render.py
    - tests/fixtures/gsd-goldens/*(24 goldens novos)
  modified:
    - cairn/scripts/cairn-gsd-state.py
    - cairn/scripts/cairn-gsd-init.py
    - tests/cairn-gsd.bats
    - tests/cairn-command-surfaces.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "envelope medido extraído para cairn_gsd_render.py — uma fonte para os dois irmãos (o dispatcher mantém a original); módulo, não CLI: sem wrapper .sh"
  - "websearch declara a WebSearch nativa do host; graphify/intel declaram capability cortada; package-legitimacy offline devolve unverified (fail-safe)"
  - "fantasmas (is, plan.task-structure, phase.list-artifacts) respondem o caminho de erro do CONTRATO, exit 1 nomeado — nunca envelope inventado"
metrics:
  duration: ~75min
  completed: 2026-08-10
status: complete
---

# Phase 34 Plan 05: O fecho — misc completo e o guard total Summary

**One-liner:** os 24 verbos misc entram nos dois irmãos pela partição do plano 01 (7 planning-docs no estado, 17 genéricos no init), e a cobertura da fase vira fato derivado: 71 verbos implementados == 71 do universo coberto (10 famílias − 5 órfãos), comm vazio nos dois sentidos, com os órfãos excluídos pela constante do dispatcher.

## Partição misc final (registro pedido pelo plano)

Exatamente a 7/17 do plano 01, sem ajuste:
- **Estado (7):** summary-extract, todo.match-phase, requirements.mark-complete, quick-tasks-append, history-digest, research-plan, research-store.
- **Init (17):** classify-confidence, estimate-check, frontmatter.get/set/validate, git.base-branch, graphify, intel, is, learnings.copy/query, normalize-test-command, package-legitimacy, plan.task-structure, teams-status, websearch, windows.
- **Órfãos (5, fase 35):** audit-open, review-lane, agent.classify-failure, task.is-behavior-adding, run-with-timeout — exit 4 nomeando a fase 35, excluídos NOMINALMENTE do guard pela constante `ORPHANS_PHASE_35` (extraída do dispatcher pelo teste, nunca segunda lista).

## Contagens de linha vs orçamento (D-01)

| Arquivo | Linhas | Teto | Nota |
|---|---|---|---|
| cairn-gsd-state.py | 1499 | 1500 | duas passadas de compressão (docstrings 1-linha, dedup need_phase/to_int/die_missing_dim, render extraído) |
| cairn-gsd-init.py | 1325 | 1500 | — |
| cairn_gsd_render.py | 87 | — | fonte única do envelope medido, compartilhada pelos irmãos |
| cairn-gsd.py (dispatcher) | 2108 | — | precedente da 33; a fase 34 só somou roteamento |

O teto de 1500 do irmão de estado só fechou com a extração do bloco de render/parse (idêntico nos dois irmãos) para `cairn_gsd_render.py` — decisão registrada: duas cópias que podem divergir da semântica medida é a doença do milestone com outro chapéu; o dispatcher mantém a cópia original (é dele que a forma foi medida). O módulo não é CLI e não ganhou wrapper .sh (nota da convenção da casa registrada no próprio docstring).

## Inventário de divergências da fase (consolidado)

47 entradas em divergences.json ao fim da fase (13 herdadas da 33 + 34 novas), por família: estado 10, roadmap-phase 7, worktree 3, init 4, misc 10. Toda mudança deliberada de semântica (fonte de fato, destino de escrita, indisponibilidade de host único, fantasmas, determinismo) está declarada em tabela — nada para ser descoberto em produção.

## Cobertura (CORE-05, fato derivado)

- `--list-implemented` agregado: **71 verbos** (10 dispatcher + 29 estado + 32 init).
- Universo coberto derivado de contracts.json: **71** (87 − 11 checagem − 5 órfãos).
- comm vazio NOS DOIS SENTIDOS; controle negativo (verbo forjado) detecta; cada órfão conferido fora do conjunto; `query verify.plan-structure`/`query audit-open` seguem exit 4 nomeando a fase 35.
- 107 cenários no manifesto; **todo verbo coberto tem ≥1 cenário com golden derived-from-contract** (checado por script: lista de verbos sem cenário = vazia).

## Desvios do plano

1. **[Rule 1] command-surfaces:** o guard "every cairn script is reachable by command" exige razão escrita para script novo — os dois irmãos ganharam a razão ("detalhe de implementação do dispatcher, nunca comando"). Commit 0816f3e.
2. **[Rule 3 - teto D-01] extração do cairn_gsd_render.py** — sem ela o irmão de estado não fecharia em 1500 com os 7 misc; a alternativa (comprimir handlers até ilegível) seria pior que a fonte única.
3. **git.base-branch no cenário testa a DEGRADAÇÃO** (repo sem branch → "main" com warning, semântica medida #3057) — o caminho verificado depende do init.defaultBranch da máquina e não é determinístico em golden; a ordem main→master→corrente está declarada em divergences.
4. **Fantasmas todos pelo caminho de erro do contrato** (exit 1 nomeado) — o teste da 33 que esperava exit 4 foi atualizado.

## Verificação

- `bats tests/cairn-gsd.bats` — 78/78 verde offline.
- `bats tests/` inteiro (via cairn-test.sh, -j 8) — **1125/1125 verde**, zero regressão na suíte completa da casa. (Uma passada serial parcial pré-correção acusou a única falha da fase — o guard de command-surfaces exigindo razão escrita para os irmãos novos — corrigida no commit 0816f3e antes da passada limpa.)
- Tetos D-01: 1499 e 1325 ≤ 1500.
- `git status --porcelain cairn/gsd/` vazio; divergences.json consolidado.

## O que a fase 35 recebe

- Harness pronto: fixture.bd (init+seeds declarativos com @id), fixture.git_commit, goldens por forma de contrato, masks por valor (nunca chave de tempo), guard generalizado que deriva o universo do inventário e os órfãos da constante do dispatcher.
- Os 5 órfãos e a família checagem (11 verbos) são a única superfície que nega — com endereço.
- `cairn_gsd_render.py` para o terceiro consumidor que precisar do envelope medido.

## Commits

- 2b676cd refactor(34-05): docstrings de função comprimidas (teto D-01)
- e4443cf test(34-05): cenários dos 7 misc de planning-docs (RED)
- d628743 feat(34-05): 7 misc de planning-docs no irmão de estado (GREEN)
- abef993 test(34-05): cenários dos 17 misc genéricos (RED)
- 58806e7 feat(34-05): 17 misc genéricos no irmão de init (GREEN)
- 0816f3e test(34-05): guard total — cobertura derivada do inventário

## Self-Check: PASSED

- cairn_gsd_render.py existe; 24 goldens novos existem ✓
- commits 2b676cd/e4443cf/d628743/abef993/58806e7/0816f3e na branch ✓
- 71 == 71 (implementado == universo coberto) ✓
