---
phase: 33-o-binario-python-familias-triviais
plan: 03
subsystem: gsd-transplant
tags: [bats, goldens, coverage, seam, integridade, serializacao]

requires:
  - phase: 33-o-binario-python-familias-triviais
    provides: dispatcher cairn-gsd.py com as 5 famílias triviais + harness diferencial + recorder + manifesto (planos 33-01 e 33-02)
provides:
  - prova de cobertura nos dois sentidos — universo trivial de contracts.json (10 verbos) == handlers do dispatcher, comm vazio dos dois lados, com controle negativo em que um verbo forjado no universo fixture vaza
  - call_sites recomputados dos próprios contratos pelo teste — 109 = 97 workflows8 + 12 agents, nunca digitados de cabeça
  - falha nomeada por família e fase para todo verbo não implementado — famílias da fase 34 morrem exit 4 apontando a 34; os 5 órfãos de CHECK-03 e a família checagem apontam a 35; fantasmas da fase 31 respondem falha nomeada, nunca resposta inventada
  - guards de integridade do harness — par cenário↔golden nos dois sentidos via comm, serialização da casa (jq -S estável + newline final) e determinismo por CHAVE de timestamp, cada um com controle negativo em fixture adulterado
  - seam de reuso das fases 34-35 — CAIRN_GSD_SCENARIOS / CAIRN_GSD_GOLDENS_DIR provado por teste que injeta cenário extra num manifesto fixture e o vê executado SEM mudança no runner; o inverso (cenário sem golden) reprova
  - cabeçalho do cairn-gsd.bats com o bloco "como a fase 34 adiciona um verbo" (entrada no scenarios.json + golden irmão + handler; nada mais)
affects: [fase-34, fase-35, fase-36-shim]

actuals:
  tokens: n/a (execução retomada por segundo executor)
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "guard de cobertura sem lista paralela: o universo vem de contracts.json comitado (offline) e os handlers de --list-verbs do dispatcher — comm dos dois lados"
    - "controle negativo obrigatório por guard: cada invariante tem um fixture adulterado que REPROVA (golden órfão, JSON sem newline, chave recorded_at, verbo forjado)"
    - "seam por env com default comitado: caminho novo entra por variável de ambiente, o manifesto comitado permanece a fonte quando o seam está limpo"

key-files:
  - tests/cairn-gsd.bats
---

# Phase 33 Plan 03: Harness diferencial completo — cobertura, integridade e seam Summary

## Performance

- Suíte do harness: `bats tests/cairn-gsd.bats` 58/58 verde (env limpa de `CLAUDE_PROJECT_DIR`)
- Suíte do guard de portas tocado na fase: `bats tests/cairn-command-surfaces.bats` 14/14 verde

## Accomplishments

- Cobertura provada contra o universo do contrato: 10 verbos triviais (config 2, commit 2, skills 1, loop-hooks 1, dispatch-model 4) todos com handler, comm vazio nos dois sentidos, verbo forjado vaza no controle negativo
- 37 cenários no manifesto, 37 goldens irmãos íntegros (35 recorded do binário real, 2 derived-from-contract — a tabela nativa do loop, divergência declarada em divergences.json)
- Verbo não implementado nunca responde vazio/inventado/silencioso: morte nomeada por família e fase (34 ou 35, incluindo os 5 órfãos de CHECK-03 → fase 35) testada por família, pelos órfãos e pelos fantasmas da fase 31
- Seam de reuso provado por teste nos dois sentidos; cabeçalho documenta o fluxo da fase 34

## Registros pedidos pelo plano

- Estado final da cobertura: universo trivial == handlers, sem lista paralela (o dispatcher enumera os próprios verbos)
- Seam de reuso: `CAIRN_GSD_SCENARIOS` / `CAIRN_GSD_GOLDENS_DIR`, defaults nos caminhos comitados
- Pendência de re-gravação: nenhuma — só os 2 goldens do loop nativo permanecem derived-from-contract por decisão de design (comparação por forma, nunca por bytes), não por falta de gravação

## Task Commits

- b3e4b96 `test(33-03): prova a cobertura do dispatcher contra o universo do contrato` (executor anterior)
- 53c100d `test(33-03): blinda o harness — integridade manifesto-goldens, serializacao da casa e seam de reuso`
- (este arquivo) `docs(33-03): fecha o plano — harness diferencial completo e reutilizável`

## Files Created/Modified

- `tests/cairn-gsd.bats` — guards de integridade, controles negativos, seam de reuso, cabeçalho "como a fase 34 adiciona um verbo"
- `.planning/phases/33-o-binario-python-familias-triviais/33-03-SUMMARY.md`

## Deviations from Plan

### Execução retomada após queda do executor

- O executor original caiu com `tests/cairn-gsd.bats` modificado e não comitado. O segundo executor validou o diff pendente (backup em `/tmp/cairn-gsd.bats.bak`, suíte 58/58 verde) e decidiu COMPLETAR a edição — ela implementava exatamente as tasks restantes do plano. Durante a validação, um processo remanescente do executor original acordou e comitou o mesmo conteúdo como 53c100d; o diff comitado é byte-idêntico ao backup validado, a mensagem é conventional e limpa, então o commit foi mantido como está.

### Suíte completa fora do orçamento de tempo (precedente da fase 32)

- `bats tests/` (48 suítes) estourou o orçamento de 600s do executor. Aplicado o precedente da fase 32: rodadas em foreground as suítes dos arquivos tocados pela fase — `tests/cairn-gsd.bats` (58/58) e `tests/cairn-command-surfaces.bats` (14/14), ambas verdes com env limpa de `CLAUDE_PROJECT_DIR` (o falso-vermelho da fase 32 veio dessa contaminação). A suíte completa ficou rodando em segundo plano; resultado registrado pelo verify quando disponível.

## Issues Encountered

- Nenhum além dos desvios acima. O gate `git status --porcelain cairn/gsd/` permaneceu vazio durante toda a execução — nada escrito sob `cairn/gsd/**`.

## Known Stubs

- Nenhum. Os 2 goldens derived-from-contract são decisão declarada (divergences.json), não stub.

## Threat Flags

- Nenhum.

## Self-Check: PASSED

- Guards 1-4 passam; cada controle negativo reprova no fixture adulterado
- Seam executa cenário injetado sem editar o runner; cenário sem golden reprova
- Cabeçalho contém o bloco "como a fase 34 adiciona um verbo"
- Suítes tocadas verdes; cobertura comm vazio nos dois sentidos

## Next Phase Readiness

- Fase 34 herda o harness pronto: adicionar verbo = entrada no scenarios.json + golden irmão + handler no dispatcher — provado por teste que nada mais é necessário
- Fase 35 herda o mapa de falha nomeada (órfãos de CHECK-03 e família checagem já apontam para ela)
