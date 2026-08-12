---
phase: 38-paridade-e-gate
plan: 01
subsystem: testes
tags: [bats, cobertura, dispatcher]
requires:
  - cairn-gsd.py --list-implemented (superfície de teste da fase 33, TRIV-04)
  - tests/fixtures/gsd-goldens/scenarios.json (harness da fase 33)
provides:
  - guard executável de cobertura por verbo, com controle negativo que prova que morde
affects:
  - tests/cairn-parity.bats
tech-stack:
  added: []
  patterns: [uma função de comparação usada pelos dois testes]
key-files:
  created: [tests/cairn-parity.bats]
  modified: []
key-decisions:
  - "cobertura é cenário golden OU invocação direta em bats — menção em comentário não conta"
metrics:
  duration: 12min
  completed: 2026-08-12
status: complete
---

# Phase 38 Plan 01: A cobertura por verbo vira asserção Summary

**Os 87 verbos do binário python já tinham cobertura executável; o que faltava era
a asserção que impede o 88º de nascer sem ela.**

## O que foi feito

`tests/cairn-parity.bats` nasce com a função `uncovered_handlers` e dois testes sobre
ela. Cobertura é uma de duas coisas, e as duas são executáveis: um cenário no manifesto
golden (`scenarios[].verb`, que o comparador diferencial roda contra o binário) ou uma
**invocação** direta num `.bats` — o token logo depois de um dispatcher, com `query`
opcional no meio. Menção em comentário não conta, e essa distinção é o ponto: contar
citação como cobertura seria exatamente a mentira que o arquivo existe para impedir.

## Medição

| Fonte | Verbos |
|---|---|
| cenário golden | 86 |
| bats direto (`run-with-timeout`) | 1 |
| **sem cobertura** | **0** |

## O oráculo

O guard nasceu verde — 87/87 — e verde na chegada não mede nada. A prova de que ele
morde é o controle negativo: os insumos reais mais uma linha forjada, pela **mesma**
função, e a saída tem que ser exatamente a linha forjada. Verificado neutralizando a
função (`print(verb)` → `pass`): o teste 2 fica vermelho, o teste 1 continua verde.
Um guard cuja prova de mordida roda outro código não provou nada.

## Deviations from Plan

Nenhuma — o plano foi executado como escrito.

## Commits

- `c2ced57` test(38-01): a cobertura por verbo vira assercao, e o controle prova que ela morde
