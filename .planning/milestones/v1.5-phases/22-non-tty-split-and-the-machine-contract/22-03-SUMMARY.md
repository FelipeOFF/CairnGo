---
phase: 22-non-tty-split-and-the-machine-contract
plan: "03"
subsystem: cairn-status
tags: [board-04, milestone, group-model, golden-file, uz6]

requires:
  - phase: 22-non-tty-split-and-the-machine-contract
    provides: "o split não-TTY e a referência do contrato de máquina"
  - phase: 20-group-model
    provides: "roadmap_milestones() e a regra de que 'aberto' é a marca da própria linha"
provides:
  - "open_milestones no modelo, e milestone_label() como grafia única das três superfícies humanas"
  - "um grupo com as fases pendentes quando o roadmap não declara ciclo aberto"
  - "seis referências regeneradas com o diff lido"
affects: [22-04, 22-05]

tech-stack:
  added: []
  patterns: ["uma leitura compartilhada por todas as superfícies humanas, como lease_line_text()"]

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-status.py
    - tests/cairn-status.bats
    - tests/cairn-group-model.bats
    - tests/cairn-grouped-board.bats
    - tests/fixtures/board-render/w100.txt
    - tests/fixtures/board-render/w50.txt
    - tests/fixtures/board-render/w38.txt
    - tests/fixtures/board-render/ascii100.txt
    - tests/fixtures/board-render/maxrows.txt
    - tests/fixtures/board-render/brief.txt

decisions:
  - "open_milestones é LISTA, não escalar: um escalar obrigaria a escolher em silêncio quando o roadmap declara dois ciclos abertos"
  - "data['milestone'] fica intocado — o PIPE-01 congela o TSV, e a assimetria vira issue (CairnGo-fp7) em vez de conserto de contrabando"
  - "O grupo sem-milestone usa type 'milestone' com key null, não um terceiro valor de type que faria todo `if type == 'milestone'` já escrito parar de vê-lo"
  - "Carrega as fases PENDENTES, o mesmo conjunto que PENDING PHASES conta — é o que faz as três superfícies concordarem"
  - "A condição é 'nenhum ciclo aberto', nunca 'nenhum grupo emitido': o caso do ciclo aberto que não nomeia fase existente não foi medido e não recebe comportamento inventado"

metrics:
  duration: 70min
  completed: 2026-08-06

requirements-completed: [BOARD-04]
status: complete
---

# Phase 22 Plan 03: O cabeçalho e a fase que sumia Summary

**O board parou de anunciar um ciclo morto e parou de esconder as fases quando o
roadmap não declara ciclo nenhum — e as duas coisas são a mesma doença em órgãos
diferentes, consertadas contra a mesma fonte de verdade.**

## As quatro combinações, antes e depois

O `uz6` foi reproduzido em repositório temporário, um roadmap de uma fase, com
STATE.md sempre dizendo `milestone: v9.9`:

| `## Milestones` | issues | ANTES | DEPOIS |
| --- | --- | --- | --- |
| ausente | 0 | `(no open work)`, `groups: []` | `No open milestone` / `◌ 1 Alpha` |
| presente `🚧` | 0 | `v9.9 Teste` / `◌ 1 Alpha` | igual (nada quebrou) |
| ausente | 1 (`phase-1`) | `No milestone` / a issue **sem a linha da fase** | `No open milestone` / `◌ 1 Alpha` / a issue |
| presente `🚧` | 1 | `v9.9 Teste` / `◌ 1 Alpha` / a issue | igual |

A contradição que a issue descrevia — três superfícies, duas respostas — não
existe mais em nenhuma das quatro:

```
ANTES                        DEPOIS
  (no open work)               No open milestone
phase 1/1 Alpha · v9.9         ◌ 1  Alpha — a primeira fase
PENDING PHASES  1            phase 1/1 Alpha · no open milestone
                             PENDING PHASES  1
```

## A decisão que sustenta o BOARD-04, e o que ela custou

`data["milestone"]` **não foi tocado**. Ele é `fm["milestone"] or
roadmap_milestone()` — STATE.md primeiro, que é exatamente a fonte que continua
apontando para o ciclo arquivado — e `render_plain()` o imprime literalmente na
linha `MILESTONE`. Mudá-lo moveria os bytes do `--plain`, que o `PIPE-01` congela
e que duas referências commitadas provam.

Então o conserto foi **aditivo**: `open_milestones` no modelo, `milestone_label()`
como grafia única, e as três superfícies humanas — rodapé do board, `--brief` e
cabeçalho da página HTML — passando a lê-la. O `--plain` ficou como estava.

O preço é uma assimetria real, e ela está escrita em três lugares (no comentário
ao lado de `milestone`, no passo 3 do docstring, e aqui) mais uma issue:
**`CairnGo-fp7`**, `discovered-from: CairnGo-fgu`. Medido no fixture: o rodapé diz
`v1.1 Surface` e o `--plain` diz `MILESTONE\tv1.0` — o ciclo arquivado — na mesma
árvore. Consertar isso exige decidir sobre o contrato externo (versionar o
formato, ou acrescentar linha, que também move bytes), e isso é maior que um
conserto de fase.

`open_milestones` é **lista**, não escalar, e a razão está no comentário: um
escalar obrigaria a escolher em silêncio quando o roadmap declara dois ciclos
abertos, e escolher em silêncio é a família de defeito que o `BOARD-04` existe
para acabar. `milestone_label()` imprime `label +N` nesse caso.

## O grupo sem nome, e a condição que quase foi a errada

Sem ciclo aberto, `phase_groups()` passa a emitir **um** grupo com as fases
pendentes: `type: "milestone"`, `key: None`, `label: "No open milestone"`.

- `type` continua `"milestone"` porque um terceiro valor faria todo
  `if group["type"] == "milestone"` já escrito parar de ver este grupo. O grupo
  **é** o agrupamento por milestone; ele só não tem milestone para nomear.
- Fases **pendentes**, não todas: é o mesmo conjunto que `PENDING PHASES` conta, e
  fazer as duas superfícies contarem o mesmo é o conserto.
- A condição é **"nenhum ciclo aberto"**, nunca "nenhum grupo emitido". Essa
  escolha foi validada contra um teste que já existia: a *variante B* de
  `cairn-group-model.bats` monta um ciclo aberto cujo range só nomeia fases
  inexistentes, e afirma que nenhum grupo de milestone é emitido. Com a condição
  "nenhum grupo emitido" esse teste teria ficado vermelho; com a condição correta
  ele **passou sem uma linha de mudança**. O caso continua não medido, e o
  docstring diz isso em vez de inventar comportamento para ele.

## Os testes, e os dois que o conserto encontrou sozinho

Três testes novos e cinco atualizados. Dois dos atualizados são achados:

**`GSD repo without .beads degrades to a GSD-only board with a note`** afirmava
`grep -qF '(no open work)'` **enquanto o mesmo output imprimia
`PENDING PHASES  1`** logo abaixo. O teste estava pinando a contradição. Hoje ele
afirma `refute_in_output '(no open work)'` e a linha da fase pendente. Zero
*issues* era verdade; "nenhum trabalho aberto" não era, e um leitor agindo sobre
aquela linha agiria sobre uma contradição.

**O conjunto de chaves do `--json`** é pinado em DOIS arquivos (`cairn-group-model`
e `cairn-status:1345`), sobre fixtures diferentes, exatamente para que uma chave
que aparecesse só sob uma fixture surgisse como desacordo. Os dois foram
atualizados com `open_milestones` e com a razão da adição. (O comentário de um
deles afirma que o outro existe; conferi antes de acreditar — o meu primeiro
`grep` não achou porque os dois literais têm formatos diferentes, e reportar
"comentário aponta para teste inexistente" teria sido um achado falso.)

O teste do critério 3 da fase, `archiving the open milestone stops the board from
naming it`, arquiva `🚧 v1.1` → `✅ v1.1` e afirma que o board não cita nem `v1.1`
nem `v1.0`, **com STATE.md conferido intacto apontando para v1.0** — sem essa
conferência o teste não distinguiria "o cabeçalho trocou de fonte" de "a fixture
mudou de ideia".

## As duas quebras medidas

Backup por `cp`, restauro pela cópia, nunca `git checkout --`:

| quebra | vermelhos | quais |
| --- | --- | --- |
| `meta_parts()` volta a ler `data["milestone"]` | **6** | as seis referências regeneradas (`w100`, `w50`, `w38`, `ascii100`, `maxrows`, `brief`) |
| o grupo sem-milestone deixa de ser emitido | **4** | as três variantes A de `cairn-group-model` e o teste de tela de `cairn-grouped-board` |

A simetria da primeira é o ponto: as seis que se moveram são exatamente as seis
que reprovam quando a mudança volta atrás.

## As oito referências: previsão escrita antes, e o que aconteceu

A previsão do plano: movem-se as seis que carregam rodapé; `plain.txt` e
`nontty-pre-split.txt` ficam imóveis. Conferido com `cmp` contra cópias em `/tmp`
feitas ANTES (não `git diff` — uma área de stage errada pode fabricar um "não
mudou"):

```
MOVEU    ascii100.txt   brief.txt   maxrows.txt   w100.txt   w38.txt   w50.txt
IMOVEL   plain.txt      nontty-pre-split.txt
```

O diff das seis é **uma linha cada**, e a mesma linha:

```
-phase 3/4 Phase model — read what a phase actually is · v1.0 · done: 1
+phase 3/4 Phase model — read what a phase actually is · v1.1 Surface · done: 1
```

Nenhuma outra linha se moveu, contra a previsão. As âncoras `v1.1 Surface` e
`No milestone` de `w100`/`ascii100` sobreviveram — `make_board_fixture` **tem**
ciclo aberto, então o grupo novo não é emitido lá e `brd-003` continua caindo no
grupo solto.

## Verificação

| suíte | plano | ok | not ok |
| --- | --- | --- | --- |
| `tests/cairn-status.bats` | `1..57` | 57 | 0 |
| `tests/cairn-group-model.bats` | `1..15` | 15 | 0 |
| `tests/cairn-grouped-board.bats` | `1..12` | 12 | 0 |
| `tests/cairn-board-invariance.bats` | `1..11` | 11 | 0 |

`cairn-status.bats` passou de 56 para 57 `@test`. Cada plano `1..N` foi conferido
contra a soma de `ok` + `not ok` sobre o log inteiro.

## Commits

| hash | mensagem |
| --- | --- |
| `1010489` | `feat(22-03): o cabeçalho nomeia o ciclo aberto, e a lista para de perder a fase` |

## Self-Check: PASSED

- `cairn/scripts/cairn-status.py` — FOUND (`milestone_label`, `open_milestones`, `NO_OPEN_MILESTONE_LABEL`)
- as seis referências regeneradas — FOUND, uma linha cada
- `plain.txt` / `nontty-pre-split.txt` — FOUND, imóveis por `cmp`
- issue `CairnGo-fp7` — FOUND (criada com `discovered-from: CairnGo-fgu`)
- commit `1010489` — FOUND
