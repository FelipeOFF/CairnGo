---
phase: 22-non-tty-split-and-the-machine-contract
plan: "05"
subsystem: cairn-docs
tags: [docs, contract, captured-example]

requires:
  - phase: 22-non-tty-split-and-the-machine-contract
    provides: "as três mudanças que a página precisava carregar (split, milestone, largura)"
provides:
  - "cairn/docs/commands/status.md descrevendo o renderizador que existe"
  - "quatro exemplos capturados de execução real, com procedência e data"
  - "o aviso de migração para quem lê a saída por pipe"
affects: []

tech-stack:
  added: []
  patterns: ["exemplo de doc é captura com procedência, nunca desenho"]

key-files:
  created: []
  modified:
    - cairn/docs/commands/status.md

decisions:
  - "Os exemplos são capturados de make_board_fixture (ids fixos, reprodutível) e conferidos por script contra execução nova"
  - "As quatro ocorrências restantes de 'kanban' são referências históricas explícitas ('não existe mais'), não descrições do presente"

metrics:
  duration: 40min
  completed: 2026-08-06

requirements-completed: []
status: complete
---

# Phase 22 Plan 05: A página volta a ser contrato Summary

**`cairn/docs/commands/status.md` descrevia um kanban de três raias sobre grade
de box-drawing, com degrades de largura e uma seção `NEXT COMMANDS` — nada disso
existe há uma e duas fases. O exemplo principal, que é o que a maioria lê, era um
desenho à mão, e por isso nada o obrigava a acompanhar o código.**

## As onze afirmações falsas, e quem as desmentiu

| a página afirmava | desmentida por |
| --- | --- |
| "a kanban status board (actionable, in-flight, blocked)" | fase 21 |
| "Renders a three-lane kanban board on one shared box-drawing grid … lane headers like `READY (3)`" | fase 21 |
| uma seção "**NEXT COMMANDS**" no painel | fase 13 |
| "Degrades gracefully by width: full columns → stacked lanes → raw list. The grid never wraps." | fase 21 |
| "not a TTY … automatically switches to `--plain`" | **22-02** |
| "`--plain` \| Tabular TSV-like output" (sem dizer que é o contrato de máquina) | **22-02** |
| "`--max-rows N` \| Rows per lane" | fase 21 |
| "`--ascii` \| ASCII borders" | fase 21 |
| "color … never on whole cards" | fase 21 |
| o exemplo de board inteiro, com `┌──┐`, `READY (2)` e `NEXT COMMANDS` | fase 21 |
| "Machine consumption (also what pipes get…)" | **22-02** |

Sete das onze eram dívida herdada de fases anteriores. Uma página de contrato que
descreve outro programa é pior que nenhuma: ela é lida com confiança.

## O que a página passou a dizer

- **A superfície humana**: uma lista agrupada em toda largura, símbolos de etapa
  de uma célula, título nunca truncado, e a razão de não haver mais ladeira de
  renderizadores.
- **O não-TTY**: o mesmo board em texto puro, sem ANSI e a 80 colunas, com os dois
  números e de onde vêm.
- **`--plain`**: o contrato de máquina, alcançável **só** pela flag, byte a byte o
  que sempre foi, com os caminhos das duas referências que provam isso.
- **O cabeçalho**: nomeia o ciclo aberto do roadmap, `no open milestone` quando
  não há, e por que `STATE.md` não serve.
- **A tabela**: cabe na largura pedida; coluna que sai é coluna nomeada; abaixo do
  mínimo ela cede o lugar e o `PURPOSE` continua.
- **Alinhamento e locale**: a fronteira do `CairnGo-hbo`, escrita onde o usuário a
  encontraria, apontando para o docstring de `char_width()`.

## O aviso que é o motivo de a página existir

```
> If you have a script reading this output, read this. Until this change, a
> flagless non-TTY run silently switched to --plain … It now gets the human
> board. The fix is to write --plain …
```

Em bloco de citação, dentro do passo que descreve o comportamento, e não numa
nota de rodapé.

## Os exemplos, capturados e conferidos

Os quatro blocos (`--width 100`, `--brief`, o pipe sem flag, e `--plain`) são
saída real de `make_board_fixture` — o fixture determinístico das referências, com
ids fixos — renderizado com `--color=never`, com a procedência e a data escritas
acima deles. Um script compara cada bloco com uma execução nova:

```
CONFERE  --width 100
CONFERE  --brief
CONFERE  pipe
CONFERE  --plain
RESULTADO: os quatro exemplos batem com execucao real
```

O bloco do pipe mostra **as duas superfícies lado a lado**, que é a diferença que
a fase inteira existe para produzir.

## O achado da conferência: a tabulação final

A primeira conferência acusou `DIVERGE --plain`. A causa: as linhas de issue do
`--plain` terminam em **tabulação**, e colar o exemplo a perdeu.

Não é sujeira. Uma linha de issue tem sempre cinco campos — `LANE`, `ID`,
`PRIORITY`, `TITLE`, `EXTRA` — e `EXTRA` é vazio na raia READY (carrega o
assignee em DOING e os bloqueadores em BLOCKED). Contagem de campos fixa é o que
faz `cut -f4` significar a mesma coisa em toda linha. A tabulação foi restaurada
**e documentada**, junto com a nota de que as meta-rows têm contagens próprias.

Esse detalhe só apareceu porque a conferência é por script sobre os bytes. Uma
leitura a olho teria aprovado.

## Verificação

```
grep -i "kanban|three-lane|box-drawing|READY (|NEXT COMMANDS|stacked lanes|per lane"
```

Quatro ocorrências restantes, todas **referências históricas explícitas** ("não
há mais grade kanban", "a box-drawing saiu com o kanban", "a página descrevia um
kanban um ano depois"), nenhuma descrevendo o presente. As ocorrências de `card`
que sobraram são o card de tracker externo e o `**Card:**` do ROADMAP, ambos
legítimos; `Every card on the board` virou `Every row on the board`.

`git diff --stat` deste plano: **um** arquivo.

## Commits

| hash | mensagem |
| --- | --- |
| `08c2c06` | `docs(22-05): a página volta a descrever o programa que existe` |

## Self-Check: PASSED

- `cairn/docs/commands/status.md` — FOUND (219 linhas alteradas, um arquivo)
- os quatro exemplos — conferidos contra execução nova, todos batem
- commit `08c2c06` — FOUND
