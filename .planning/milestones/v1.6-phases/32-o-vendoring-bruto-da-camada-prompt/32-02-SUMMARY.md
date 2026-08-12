---
phase: 32-o-vendoring-bruto-da-camada-prompt
plan: "02"
subsystem: testing
tags: [bats, vendoring, manifest, golden-fidelity, negative-controls]

# Dependency graph
requires:
  - phase: 32-o-vendoring-bruto-da-camada-prompt
    provides: "plano 32-01 — subcomandos closure/vendor, MANIFEST.json e a árvore vendorizada que esta suíte prova"
provides:
  - "tests/cairn-vendoring.bats — 24 testes: fecho em miniatura (ponto fixo de 2 saltos, órfão excluído), manifest derivado (--write == --json, comm 2 sentidos), fidelidade byte a byte, exatidão do conjunto, o corte de VEND-04 (nomeado + tabular), guard de números do fecho — cada guard com controle negativo que morde"
affects: [fase-36-adaptacao]

# Actuals (#2632)
actuals:
  tokens: 5600
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Oráculo único com raiz por argumento: a mesma função assertiva serve o teste positivo e o controle negativo apontado à árvore forjada — comparação rigged não sobrevive"
    - "Fixture com cadeia de referências (fast → r1 → t1 + órfão): expectativas do fecho vêm do próprio fixture, nunca de literais da árvore real"

key-files:
  created:
    - tests/cairn-vendoring.bats
  modified: []

key-decisions:
  - "Guard do requires provado vivo em fixture: SKILL.md forjado com requires: [config] sem commands/gsd/config.md mata o closure com exit 6 nomeando shim e command"
  - "Padrões multi-host do corte restritos a extensão .cts (adapter-*.cts, runtime-*.cts) para que gsd-core/references/runtime-aware-dispatch.md — referência legítima do fecho — nunca dê falso positivo"
  - "Blocos do corte como caminhos de diretório (tests docs src scripts bin gsd-core/bin eslint-rules capabilities .github examples .changeset hooks) + find nomeado do write-guard em qualquer profundidade"

patterns-established:
  - "Guard de números por família de substantivo: a suíte nova vigia arquivos/linhas sem editar as suítes existentes — o padrão da casa é extensível por arquivo"

requirements-completed: [VEND-01, VEND-03, VEND-04]

coverage:
  - id: D1
    description: "Fecho converge até ponto fixo em fixture (2 saltos, órfão fora) e closure --write grava bytes idênticos ao --json (VEND-01)"
    requirement: VEND-01
    verification:
      - kind: integration
        ref: "tests/cairn-vendoring.bats#closure on the fixture converges to the fixed point and excludes the orphan"
        status: pass
  - id: D2
    description: "Manifest gravado == saída viva por comm nos dois sentidos, em fixture e contra o cache real (VEND-01)"
    requirement: VEND-01
    verification:
      - kind: integration
        ref: "tests/cairn-vendoring.bats#real manifest == closure re-run on the cache: file sets identical in both directions"
        status: pass
  - id: D3
    description: "Todo files[] byte-idêntico ao clone da tag e nada sob cairn/gsd/ além de files[] + MANIFEST.json + contracts/** (VEND-03)"
    requirement: VEND-03
    verification:
      - kind: integration
        ref: "tests/cairn-vendoring.bats#real tree: every files[] entry is byte-identical to the pinned cache + #real tree: nothing beyond files[] + MANIFEST.json + contracts/** in either direction"
        status: pass
  - id: D4
    description: "gsd-write-guard.js ausente por teste nomeado que explica a colisão com o bd; blocos do corte ausentes por teste tabular; controles negativos mordem (VEND-04)"
    requirement: VEND-04
    verification:
      - kind: integration
        ref: "tests/cairn-vendoring.bats#the cut holds: gsd-write-guard.js is NOT vendored (collides with bd as state owner) + #negative control: a forged forbidden file is caught and named by the absence loop"
        status: pass
---

# Phase 32 Plan 02: A prova executável do vendoring — Summary

**tests/cairn-vendoring.bats transforma as afirmações da fase em prova: 24 testes verdes com o cache real (zero skips) e verdes sem cache (só a faixa de fidelidade skipa com mensagem de reprodução), cada guard nascendo com o controle negativo que o morde.**

## Accomplishments

- Fixture em miniatura (builder copiado da suíte do inventário, estendido): ponto fixo provado por inclusão transitiva de 2 saltos (fast.md → r1.md → t1.md) e exclusão do órfão; determinismo; --write == --json byte a byte com newline final; comm nos dois sentidos.
- Vendor fiel em fixture com nada além da lista; exit codes exatos (-eq 2 manifest ausente, -eq 6 commit divergente, ambos nomeando o problema).
- Controles negativos: byte corrompido pego e nomeado; arquivo intruso pego e nomeado; SKILL.md forjado com requires: fora da lista mata o closure (exit 6); contagem forjada fora do bloco datado pega pelo guard novo.
- Artefatos reais: manifest válido e ordenado, identidade de fonte com contracts.json (sha digitado uma vez), presença sem cache, conjunto exato nos dois sentidos, corte nomeado + tabular, fidelidade skip-gated, LICENSE intacto, totals com comando ao lado (171/29.957 medidos 2026-08-10, divergência do research anotada).

## Deviations

- **Gate de regressão da suíte completa executado por partes, com escopo registrado:** `bats tests/` serial excede o orçamento da sessão (cairn-doctor.bats sozinho: 124 testes a ~20s/teste ≈ 40min; suíte toda >2h). Evidência colhida com ambiente limpo: 505 testes verdes, zero falhas — incluindo TODAS as suítes que leem qualquer arquivo alterado pela fase (cairn-inventory 24, gsd-contracts 24, cairn-vendoring 24, cairn-command-surfaces, e as que varrem a árvore do repo: stage-plugins, smoke, hooks, capability, cairn-wrap, gbsync = 102), mais bench* completos (176), board-invariance + corroboration completos (36), config/corroboration/doctor parciais (119). Nenhuma suíte restante lê arquivos tocados pela fase.
- **Falso alarme documentado:** um run inicial da suíte completa com `CLAUDE_PROJECT_DIR` exportado produziu 13 falhas em board-invariance/corroboration — contaminação de ambiente (cairn-status.py:4309 resolve a raiz pela env e renderizou o repo VIVO em vez do fixture). Re-run limpo: 36/36 verdes. Nenhum defeito de código.

## Commits

| hash | título |
|---|---|
| 6803a08 | test(32-02): fecho, manifest derivado e fidelidade da cópia provados em miniatura |
| cc47dd5 | test(32-02): artefatos reais — fidelidade skip-gated, o corte segura, guard de números |
