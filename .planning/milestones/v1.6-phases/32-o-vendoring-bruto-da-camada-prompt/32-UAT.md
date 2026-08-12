---
status: complete
phase: 32-o-vendoring-bruto-da-camada-prompt
source: [32-01-SUMMARY.md, 32-02-SUMMARY.md]
started: 2026-08-10T18:30:00Z
updated: 2026-08-10T18:40:00Z
---

## Current Test

[testing complete]

## Tests

<!-- Rota coverage (#1602): o classificador devolveu todas as entradas como
     `reason: validation_failed` porque o validador da tool não re-executa
     refs bats nem comandos shell. Cada ref foi EXECUTADA diretamente nesta
     sessão de verificação (bats verde, comandos exit 0) — os passes abaixo
     são automated com a evidência ao lado, nunca palavra de SUMMARY. -->

### 1. closure --json determinístico + --write byte-idêntico (32-01/D1)
expected: closure emite o fecho sobre o corpus pinado (source.commit 68a04cc), determinístico entre execuções; MANIFEST.json gravado == saída viva
result: pass
source: automated
coverage_id: 32-01/D1
evidence: "diff <(closure --json) <(closure --json) vazio; diff <(closure --json) cairn/gsd/MANIFEST.json vazio (re-rodado na verificação)"

### 2. vendor copia exatamente files[] com fidelidade nos dois sentidos (32-01/D2)
expected: cada entrada de files[] byte-idêntica ao cache; nada sob cairn/gsd/ além de files[] + MANIFEST.json + contracts/**
result: pass
source: automated
coverage_id: 32-01/D2
evidence: "sweep python3 (filecmp shallow=False + comm dos dois sentidos) exit 0; bats 'real tree: every files[] entry is byte-identical to the pinned cache' ok"

### 3. LICENSE MIT intacto + crédito no README (32-01/D3)
expected: cairn/gsd/LICENSE byte-idêntico ao do clone; README §License & credits com open-gsd/gsd-core, v1.10.0, 68a04cc, cairn/gsd/LICENSE
result: pass
source: automated
coverage_id: 32-01/D3
evidence: "cmp exit 0; awk da seção + greps ok (re-rodados na verificação)"

### 4. Contrato flat do inventário intacto (32-01/D4)
expected: suítes existentes passam sem edição
result: pass
source: automated
coverage_id: 32-01/D4
evidence: "bats tests/cairn-inventory.bats tests/gsd-contracts.bats — 48/48 ok, duas execuções"

### 5. Fecho converge em fixture e --write == --json (32-02/D1)
expected: ponto fixo de 2 saltos com órfão excluído; bytes idênticos
result: pass
source: automated
coverage_id: 32-02/D1
evidence: "bats tests/cairn-vendoring.bats testes 1-3 ok"

### 6. Manifest == saída viva por comm nos dois sentidos (32-02/D2)
expected: nenhum resíduo em nenhum sentido, em fixture e contra o cache real
result: pass
source: automated
coverage_id: 32-02/D2
evidence: "bats testes 4 e 21 ok (cache quente, zero skips)"

### 7. Fidelidade byte a byte + exatidão do conjunto na árvore real (32-02/D3)
expected: todo files[] idêntico ao clone; nada além de files[] + MANIFEST.json + contracts/**
result: pass
source: automated
coverage_id: 32-02/D3
evidence: "bats testes 14, 15 e 20 ok"

### 8. O corte segura com controles negativos que mordem (32-02/D4)
expected: gsd-write-guard.js ausente por teste nomeado; blocos do research §3 ausentes por tabular; árvore forjada é pega
result: pass
source: automated
coverage_id: 32-02/D4
evidence: "bats testes 16, 17 e 18 ok; [ ! -e cairn/gsd/hooks/gsd-write-guard.js ] re-conferido"

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
