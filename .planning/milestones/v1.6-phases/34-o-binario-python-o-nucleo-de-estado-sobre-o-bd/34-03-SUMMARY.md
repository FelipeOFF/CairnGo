---
phase: 34-o-binario-python-o-nucleo-de-estado-sobre-o-bd
plan: 03
subsystem: gsd-dispatcher
tags: [roadmap-phase, documento-vs-fato, phase-complete, bd]
requires: [34-02]
provides:
  - família roadmap-phase completa (12 verbos) no cairn-gsd-state.py
  - regra documento-vs-fato codificada (parsers de documento + resolvedor de fato único)
affects: [34-04, 34-05]
tech-stack:
  added: []
  patterns: [edição escopada de documento (checkbox flip por span), seção de fase por bounds de heading, frontmatter subset + truths]
key-files:
  created:
    - tests/fixtures/gsd-goldens/roadmap-*.golden.json
    - tests/fixtures/gsd-goldens/phase-*.golden.json
    - tests/fixtures/gsd-goldens/find-phase.golden.json
    - tests/fixtures/gsd-goldens/phases-list.golden.json
  modified:
    - cairn/scripts/cairn-gsd-state.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "phase.list-artifacts (fantasma da 31) responde o caminho de erro do contrato: exit 1 UnknownCommand — nunca envelope inventado"
  - "phase.complete não edita REQUIREMENTS.md (bookkeep é o dono) e não emite date (tempo vive na auditoria do bd)"
  - "update-plan-progress marca checkboxes; a tabela Progress não é editada (visão agregada é do cairn-status)"
metrics:
  duration: ~40min
  completed: 2026-08-10
status: complete
---

# Phase 34 Plan 03: Família roadmap-phase Summary

**One-liner:** os 12 verbos roadmap-phase respondem em python com a regra documento-vs-fato viva — ROADMAP/PLANs lidos do arquivo, current_phase/status lidos do label do portador, progress derivado — e phase.complete transiciona pelo caminho único auditado do set-state.

## Documento vs fato (o ponto fino, provado)

- `roadmap.analyze`: lista de fases/milestones do ROADMAP (documento) + `current_phase` do label `phase:N` do portador (fato) + `progress_percent` derivado (SUMMARYs/PLANs contados). Cenário adversarial `roadmap-analyze-fato-ausente`: ROADMAP completo, bd sem portador → exit 1 nomeado prescrevendo `state.begin-phase` — o documento NÃO responde pelo fato.
- `roadmap.update-plan-progress`: cenário dessincronizado (disco 2/2 completo, portador `phase_status:executing`) → `complete: true` (documento) e `status: "executing"` (fato) no mesmo envelope — cada fonte dona do seu campo.
- `phase.complete`: transições EXCLUSIVAS por set-state com ator/motivo — `phase_status=complete` na fase alvo, avanço `phase=<next>`/`phase_status=planned`; reentrada idempotente (labels byte-iguais, provado por bats); checkbox do ROADMAP flipado por span da regex (edição mínima, nunca rewrite).

## Divergências declaradas (family roadmap-phase, 7 novas)

1. `uat-passed-reduced` — predicado por frontmatter status; fail-closed preservado.
2. `stale-check-indeterminate` — campo emitido sempre true (mecanismo inexistente; inventar false seria afirmar checagem que não rodou).
3. `phase-complete-date-omitted` — doutrina de determinismo; tempo na auditoria do bd.
4. `phase-complete-requirements-not-edited` — bookkeep é o dono da rastreabilidade.
5. `phase-complete-no-auto-prune` — poda destrutiva sem consumidor.
6. `update-plan-progress-scoped-edit` — checkboxes sim, tabela Progress não.
7. `current-phase-from-fact` — roadmap.analyze nunca deriva posição da prosa.

## Contagem de linhas (D-01)

`cairn-gsd-state.py` = **1473 linhas** (≤ 1500). A docstring do módulo foi comprimida no passo REFACTOR para abrir espaço; o plano 05 soma ~7 handlers misc a este arquivo e fará a segunda passada de compressão (docstrings de função) com o número medido — registrado aqui como aviso ao plano 05.

## Desvios do plano

1. **Representante da via exit-4 do irmão migrou de `roadmap.get-phase` para `summary-extract`** (misc→estado, sem handler até o plano 05) — a família roadmap-phase inteira ganhou handlers.
2. **Teste dos fantasmas atualizado:** phase.list-artifacts agora exit 1 (caminho de erro do contrato); plan.task-structure segue exit 4 até o plano 05.
3. Nenhum outro desvio.

## Verificação

- `bats tests/cairn-gsd.bats` — 69/69 verde offline; regressão zero (33, 34-01, 34-02).
- 12/12 verbos da família em `--list-implemented`; guard com roadmap-phase no filtro, comm fechado.
- `git status --porcelain cairn/gsd/` vazio.
- Auditoria de phase.complete provada (event bead com motivo contendo o verbo).

## Commits

- 6b2eb15 test(34-03): cenários dos 8 leitores roadmap-phase (RED)
- b09ad5d feat(34-03): os 8 leitores roadmap-phase — documento do arquivo, fato do bd (GREEN)
- 0c04b94 test(34-03): transições roadmap-phase e guard com a família (RED)
- f94ec67 feat(34-03): os 4 mistos/transições — complete, uat-passed, annotate, update-plan-progress (GREEN)

## Self-Check: PASSED

- 13 goldens novos (roadmap-*/phase-*/find-phase/phases-list) existem ✓
- commits 6b2eb15/b09ad5d/0c04b94/f94ec67 na branch ✓
- wc -l 1473 ≤ 1500 ✓
