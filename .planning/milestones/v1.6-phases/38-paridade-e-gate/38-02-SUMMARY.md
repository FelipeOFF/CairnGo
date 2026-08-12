---
phase: 38-paridade-e-gate
plan: 02
subsystem: dispatcher
tags: [paridade, contratos, verbos, bats]
requires:
  - cairn/gsd/contracts/ (universo da fase 33)
  - clone pinado v1.10.0 (semântica de cmdWorktreeSetBaseRef)
provides:
  - scanner de paridade `gsd_run` → verbo servido, com seam de corpus
  - worktree.set-baseref e requirements.revert-phase servidos
  - universe.references_extension — a cegueira do inventário declarada no dado
affects:
  - cairn/scripts/cairn-gsd.py
  - cairn/scripts/cairn-gsd-init.py
  - cairn/scripts/cairn-gsd-state.py
  - cairn/gsd/contracts/
tech-stack:
  added: []
  patterns: [duas grafias e uma implementação; tolerância declarada no dado, lida pelo teste]
key-files:
  created: [tests/parity-scan.py, tests/fixtures/parity-corpus/forged-call.md]
  modified:
    - cairn/scripts/cairn-gsd.py
    - cairn/scripts/cairn-gsd-init.py
    - cairn/scripts/cairn-gsd-state.py
    - cairn/gsd/contracts/contracts.json
    - cairn/gsd/contracts/worktree.json
    - cairn/gsd/contracts/misc.json
    - tests/cairn-gsd.bats
    - tests/gsd-contracts.bats
    - tests/fixtures/gsd-goldens/divergences.json
key-decisions:
  - "implementar os dois verbos, não apagar as chamadas — apagar esconderia a regressão"
  - "a cegueira do inventário (references/ fora do escopo varrido) vira dado datado, não exceção anônima no teste"
metrics:
  duration: 41min
  completed: 2026-08-12
status: complete
---

# Phase 38 Plan 02: Paridade executável — duas rotas mortas, achadas e fechadas Summary

**O runtime vendorizado chamava dois verbos que o binário não servia, e os dois estavam
embrulhados em `|| true` — o dispatcher morria exit 2 e ninguém via.**

## O achado

Varrendo todo `gsd_run` dos 184 arquivos de `cairn/gsd/` contra a tabela spelling→verbo
que o dispatcher constrói:

| Chamada | Sítio | O que não acontecia |
|---|---|---|
| `query worktree.set-baseref` | `references/execute-phase-between-wave-reset.md:30` | o reset de baseRef entre ondas |
| `query requirements.revert-phase` | `references/execute-phase-requirement-revert.md:5` | o revert de requisito marcado cedo demais |

**Por que ninguém tinha visto:** `cairn-inventory.py`, fonte do universo de 87, varre
`workflows8` + `agents`. `gsd-core/references/` — que o runtime executa — está fora do
escopo varrido. O universo estava certo para o que mediu, e cego para o resto.

Falso positivo inocentado no caminho: `gsd_run query verification status` (forma com
espaço) **resolve**; quem o acusou foi uma varredura sem normalização de token. O
fixture do controle negativo carrega esse caso de propósito, para que ninguém
"conserte" o que está certo.

## O que foi feito

- `tests/parity-scan.py`: a varredura, com seam de corpus. Duas regras vindas de falso
  positivo medido — menção dentro de crase é prosa, não chamada; e token normaliza a
  pontuação que `$( )` e prosa grudam nas pontas.
- `worktree.set-baseref`: grafia pontuada delegando para a **mesma** escrita no-clobber
  de `worktree set-baseref`. Duas cópias da mesma escrita concordariam entre si até no
  dia em que as duas estivessem erradas.
- `requirements.revert-phase`: inverso exato de `mark-complete`. O shape do envelope do
  binário real não é medível daqui (o clone pinado não expõe a fonte deste verbo), então
  ele espelha o par e a divergência está **declarada** em `divergences.json`.
- Universo 87 → 89, com `universe.references_extension` datado, com método escrito e com
  a razão da cegueira. Os dois testes que comparam universo e inventário passaram a ler
  a extensão **do dado**; um terceiro fecha a brecha provando que todo verbo declarado
  tem sítio real sob `references/`.

## O oráculo

RED medido antes de qualquer edição de produção: o scan acusou as duas linhas, nomeando
arquivo e número. GREEN depois: saída vazia. O controle negativo (corpus fixture com uma
chamada forjada mais duas armadilhas que precisam ser ignoradas) reporta exatamente uma
linha — a forjada.

## Deviations from Plan

**1. [Rule 1 - Bug] O pin de 87 em `tests/cairn-gsd.bats` precisou de razão escrita**

- **Encontrado em:** Task 2, ao rodar a suíte
- **Issue:** o guard de cobertura prende o universo ao número 87 por literal
- **Fix:** 87 → 89 com o parágrafo que explica o terceiro escopo medido; a regra da casa
  é que o pin só se move com razão escrita, e ela foi escrita
- **Commit:** `8b6f48b`

**2. [Rule 2] O clone pinado foi religado no worktree**

Dois testes de universo são skip-gated em `.cairn/cache/gsd-core-v1.10.0`, ausente neste
worktree. Rodar a mudança de D-03 com eles pulando seria provar nada, então o cache foi
religado (symlink, diretório já ignorado pelo git) e os dois rodaram de verdade: 25/25 em
`gsd-contracts.bats` sem um único skip, e `cobertura cruzada` verde em `cairn-gsd.bats`.

## Verificação

- `tests/cairn-parity.bats` — 4/4
- `tests/cairn-gsd.bats` — 97/97 (2 skips remanescentes, ambos de outra gating)
- `tests/gsd-contracts.bats` — 25/25, zero skip
- `python3 tests/parity-scan.py --contracts cairn/gsd/contracts --corpus cairn/gsd` — vazio

## Commits

- `8422bbc` test(38-02): o scanner de paridade acusa as duas rotas mortas do vendor
- `8b6f48b` feat(38-02): os dois verbos mortos passam a ser servidos, e o universo declara a cegueira
