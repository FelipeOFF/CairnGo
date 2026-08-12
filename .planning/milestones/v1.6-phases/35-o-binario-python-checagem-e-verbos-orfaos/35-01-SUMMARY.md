---
phase: 35-o-binario-python-checagem-e-verbos-orfaos
plan: 01
subsystem: gsd-dispatcher
tags: [checagem, dispatcher, execv, tracer, doctor-pin, grafia-dupla]
requires:
  - cairn_gsd_render.py (fonte única do envelope, fase 34)
  - harness de goldens da 33/34 (manifesto + goldens + guard)
provides:
  - pin CHECK-04 (baseline do cairn-doctor por blob + wc -l em bats)
  - cairn-gsd-check.py (skeleton + verification.status nas duas grafias)
  - rota checagem em FAMILY_SCRIPT do dispatcher
  - guard de cobertura em modo entrega incremental (fecho no 35-05)
affects: [35-02, 35-03, 35-04, 35-05, fase-36]
tech-stack:
  added: []
  patterns:
    [
      veredito no payload nunca no exit,
      routing table transcrita com proveniência,
      staleness fail-open flagado (#3057 B3),
    ]
key-files:
  created:
    - cairn/scripts/cairn-gsd-check.py
    - tests/fixtures/gsd-goldens/verification-status-*.golden.json (4)
  modified:
    - cairn/scripts/cairn-gsd.py
    - tests/cairn-gsd.bats
    - tests/cairn-command-surfaces.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "pin CHECK-04 na forma mínima: constantes locais do próprio @test (blob e2040aea + 3907 linhas), commit da baseline (a2527ee) em comentário — nenhum arquivo extra"
  - "VERIFICATION_ROUTING_TABLE transcrita verbatim de src/verification.cts L81-L121 da tag; chave stale-indeterminate com o nome do shape do contrato (divergência declarada)"
  - "projectNextCommand da casa: codex → $gsd-<cmd> minúsculo, demais → /gsd-<cmd> (a letra do capability-registry da tag)"
metrics:
  duration: ~50min
  completed: 2026-08-11
status: complete
---

# Phase 35 Plan 01: Pin do doctor + tracer do terceiro irmão Summary

**One-liner:** CHECK-04 fixado por teste ANTES de tudo (blob + linhas do doctor pinados no próprio @test); cairn-gsd-check.py nasce no molde do irmão de estado com verification.status atravessando dispatcher → exec → leitura de documento → envelope da fonte única, byte-igual nas duas grafias contratadas.

## O que foi construído

- **Pin CHECK-04 (tests/cairn-gsd.bats):** @test que compara `git hash-object` do cairn-doctor.py com o blob `e2040aea2068967eaec204e049fff0dbceb2ef50` e `wc -l` com `3907`; falha nomeada diz que o doctor mudou dentro da fase 35 e que o pin só muda deliberadamente na fase 37. O teste É o registro — valores como constantes locais, commit da baseline (a2527ee, 2026-08-07) em comentário.
- **cairn-gsd-check.py (326 linhas):** docstring-contrato com a doutrina da família (veredito no payload passed/active/block/valid, NUNCA no exit; exit 0 = gate avaliado; exit 1 = erro de uso do contrato), render como fonte única (import de cairn_gsd_render), die com TAG_PREFIX `[cairn-gsd-check]`, HANDLERS + main + family_of + `--list-implemented` no molde do irmão de estado; regexes de fase/plano copiadas (terceira cópia de forma, precedente da casa).
- **verification.status:** frontmatter `status:` do NN-VERIFICATION.md mais recente pelo molde leniente de cairn-status.py; VERIFICATION_ROUTING_TABLE transcrita da tag (dado com proveniência); staleness check no molde findStaleVerificationSummary — commit time de arquivo limpo, senão mtime (#2348); check que não completa vira `verification_stale_check_indeterminate: true` (fail-open flagado, #3057 B3), nunca "not stale" fingido; phase-dir ausente → die exit 1 nomeado.
- **Dispatcher:** `FAMILY_SCRIPT` ganha `"checagem": "cairn-gsd-check.py"` — script_for resolve, `--list-implemented` agrega, ponto de exec intocado. ORPHANS_PHASE_35 e o ramo misc EXATAMENTE como estavam (plano 05).
- **Grafia dupla provada por teste, não por tabela:** os spellings contratados (`query verification status` / `query verification.status`) casam pelo loop n-grama existente — cenários par com goldens idênticos provam o handler único.
- **Guard em entrega incremental:** direção "extras" contra o universo COMPLETO de contracts.json (nenhuma superfície fantasma); "missing" segue nas 10 famílias − órfãos; comentário aponta o fecho bidirecional no 35-05. Tabela de representantes: `query verification.status` saiu da via exit-4 (o verbo agora responde).

## Transcrição da VERIFICATION_ROUTING_TABLE (proveniência)

Fonte: `src/verification.cts` L81-L121 da tag v1.10.0 (cache `.cairn/cache/gsd-core-v1.10.0`, HEAD 68a04cc). Rotas: passed (next_command vazio), gaps_found (plan-phase `<N> --gaps`, computado no call site), human_needed (verify-work, #2617), stale (verify-work), missing (execute-phase), unknown (execute-phase, next_action dinâmico com o valor cru). O número da fase só entra como argumento quando é inequivocamente numérico (#2617).

## Estado do guard

Incremental neste plano: `extra` validado contra TODOS os verbos de contracts.json; `missing` derivado de 10 famílias − órfãos (constante nominal ainda de pé). O plano 35-05 soma a família checagem ao filtro (10→11), zera a exclusão e restaura o comm vazio nos dois sentidos em 87.

## Desvios do plano

Nenhum — plano executado como escrito. (Nota: o caminho real do cache da tag é `.cairn/cache/gsd-core-v1.10.0/src/...`, sem o segmento `gsd-core/` que os planos citam nos source_refs — mesmo conteúdo, prefixo diferente.)

## Divergências declaradas (novas)

1 entrada (family checagem, verb verification.status, aspect `stale-check-indeterminate-key`): a tag emite `staleCheckIndeterminate` (camelCase) nesta superfície; o contrato nomeia a projeção snake_case das superfícies downstream — a casa segue o shape contratado.

## Verificação

- `bats tests/cairn-gsd.bats` — 79 ok, 1 skip (reprodução do recorder, runtime não buildado), zero falhas.
- Sequência E2E do tracer num repo mktemp: envelopes byte-iguais nas duas grafias; exit 1 nomeado sem phase-dir.
- `git status --porcelain cairn/gsd/` vazio; doctor intocado (pin verde); teto: 326 ≤ 1500; state (1499) e init (1325) intocados.

## Commits

- 0f290e7 test(35-01): pin CHECK-04 — baseline do cairn-doctor fixada por teste
- 5c0445c feat(35-01): tracer do terceiro irmao — verification.status nas duas grafias
- b619ca3 test(35-01): cenarios das duas grafias + guard em entrega incremental

## Self-Check: PASSED

- cairn/scripts/cairn-gsd-check.py existe; 3 commits acima existem no branch; suíte verde offline.
