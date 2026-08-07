---
phase: 21-the-grouped-board
plan: "01"
subsystem: cairn-status
tags: [board, render, unicode, east-asian-width, golden-file, bats]

requires:
  - phase: 20-group-model
    provides: "a chave de topo `groups` — milestone aberto → fase → issue, forma fechada e presa por 14 testes"
provides:
  - "stage_symbol(), group_rows(), issue_body_spans(), render_groups(): a lista agrupada no caminho largo"
  - "wrap_spans(): quebra por célula de display, sem truncar e sem partir token"
  - "counts_parts(): uma grafia só para ready/doing/blocked/done, compartilhada com --brief"
  - "tests/cairn-grouped-board.bats: sete propriedades, cada uma com a quebra que a reprova medida"
  - "w100/ascii100/maxrows regenerados a partir do render novo"
affects: [21-02, 21-03, 22-non-tty-split]

tech-stack:
  added: []
  patterns:
    - "Símbolo de UI escolhido por east_asian_width medido, nunca por aparência"
    - "Fallback ASCII de um caractere por símbolo, para as colunas caírem na mesma célula nos dois modos"
    - "Quebra de linha por display_width, nunca por len()"
    - "Teste que lê a classe de símbolo DO script, para que uma troca de símbolo reprove um teste, não seis"
    - "Regeneração de referência como ato próprio: um commit separado cuja mensagem carrega o diff lido"

key-files:
  created:
    - tests/cairn-grouped-board.bats
  modified:
    - cairn/scripts/cairn-status.py
    - tests/cairn-status.bats
    - tests/cairn-tracker-card.bats
    - tests/cairn-board-invariance.bats
    - tests/fixtures/board-render/regenerate.sh
    - tests/fixtures/board-render/w100.txt
    - tests/fixtures/board-render/ascii100.txt
    - tests/fixtures/board-render/maxrows.txt
    - tests/README.md

key-decisions:
  - "A linha de fase nunca usa ⧗: blocked_by de fase carrega o defeito FIX-04 (fase 26 bloqueada pela fase 9, arquivada), e phase_groups() já recusou ler aresta pelo mesmo motivo"
  - "O bloqueador é escrito em palavras (`blocked by a, b`) e nomeia TODOS, não só o primeiro"
  - "A chave do tracker deixou de ser truncada em 16 células: o teto existia para proteger uma célula de largura fixa, e uma chave cortada não identifica nada"
  - "Nenhuma contagem nas linhas de grupo e de fase — uma terceira grafia de um número é uma terceira coisa que pode discordar"
  - "--max-rows passou a limitar por balde; a referência maxrows trocou de --max-rows 2 para 1 porque a 2 nenhum balde do fixture transborda"

requirements-completed: []

coverage:
  - id: D1
    description: "O board largo renderiza milestone aberto → fase → tarefa, com trabalho solto por último"
    requirement: "BOARD-06"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#the board renders milestone, then phase, then task, with loose work last"
        status: pass
      - kind: other
        ref: "quebra medida: emitir o grupo unphased primeiro reprova esse teste, sozinho"
        status: pass
    human_judgment: false
  - id: D2
    description: "Os cinco símbolos de etapa são east_asian_width=N, e o fallback ASCII tem um caractere cada"
    requirement: "BOARD-02"
    verification:
      - kind: unit
        ref: "tests/cairn-grouped-board.bats#every stage symbol is one cell, measured by unicodedata, not by eye"
        status: pass
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#--ascii swaps the symbols and moves no column"
        status: pass
      - kind: other
        ref: "quebras medidas: ◔→○ reprova só o teste 2; um símbolo ASCII de dois caracteres reprova 2 e 5"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nenhum título é truncado de 64 a 140 colunas, e nenhum sufixo cai por falta de espaço"
    requirement: "BOARD-03"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#a genuinely long title is never truncated, at any width that holds a word"
        status: pass
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#no row overflows its width, and the one exception is a token that cannot fit"
        status: pass
      - kind: other
        ref: "quebras medidas: truncate() de volta reprova 3, 5 e 6; descartar o card reprova 3; quebrar sem descontar o prefixo reprova 6"
        status: pass
    human_judgment: false
  - id: D4
    description: "Uma linha bloqueada nomeia todos os bloqueadores na própria linha"
    requirement: "BOARD-05"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#a blocked row names every blocker it has, on the row itself"
        status: pass
      - kind: other
        ref: "quebra medida: voltar a blocked_by[0] reprova esse teste, sozinho"
        status: pass
    human_judgment: false
  - id: D5
    description: "Nada é perdido nem duplicado entre as raias e a tela"
    requirement: "BOARD-06"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#every open issue on a lane reaches the screen, exactly once"
        status: pass
    human_judgment: false
  - id: D6
    description: "As três referências que deviam mudar mudaram, as quatro que não deviam ficaram byte a byte"
    verification:
      - kind: integration
        ref: "bats tests/cairn-board-invariance.bats — 9/9"
        status: pass
      - kind: other
        ref: "diff -q contra a cópia de /tmp: w50, w38, plain e brief idênticos"
        status: pass
    human_judgment: false

duration: 220min
completed: 2026-08-05
status: complete
---

# Phase 21 Plano 01: A lista agrupada Summary

**O kanban de três colunas sai do caminho largo e entra uma lista agrupada pelo modelo da fase 20, com a etapa num símbolo de uma célula medido por `unicodedata`, o título inteiro em qualquer largura que o comporte, e todos os bloqueadores nomeados na própria linha.**

## Performance

- **Duration:** ~220 min (dos quais ~120 min de espera por suítes, com `--jobs 2` obrigatório: três fases dividindo oito núcleos)
- **Tasks:** 4
- **Files modified:** 10 (1 criado, 9 modificados)

## O antes e o depois, medidos

O board real deste repositório a `--width 100`, antes:

```
┌─ READY (37) ───────────────────┬─ DOING (0) ────────────────────┬─ BLOCKED (0) ──────────────────┐
│ CairnGo-64u  cairn-parallel a… │                                │                                │
│ CairnGo-0po  FIX-05: um unico… │                                │                                │
...                             (15 linhas, depois `+22 more`)
```

Duas colunas inteiramente vazias, 37 tarefas espremidas numa terça parte da tela,
nenhum título íntegro, e nada dizendo a que fase cada linha pertence. Depois:

```
ready 31 · doing 6 · blocked 0 · done 77

v1.5 Legible State
  ✓ 20  Group model
  ◔ 21  The grouped board
      ◕ CairnGo-8kf  BOARD-02: Etapa num simbolo de largura simples, com fallback ASCII
      ◕ CairnGo-qwu  BOARD-06: o board renderiza agrupado — milestones abertos primeiro, fases
                     dentro, trabalho solto por ultimo
  ◌ 22  Non-TTY split and the machine contract
      ◔ CairnGo-5yo  PIPE-03: O teste do acoplamento e reescrito em duas assercoes, nunca removido
...
No milestone
      ◔ CairnGo-3us  PR-03: Estado de revisao vem do gh/glab atras de config, com cache carimbado
```

## O diff das sete referências, lido

Este é o entregável que a fase 20 preparou e o que esta fase deve por escrito.
`git diff --stat` da regeneração tocou **exatamente** os três arquivos previstos.

| arquivo | bytes | veredito |
|---|---|---|
| `w100.txt` | 1539 → 1096 | mudou, previsto |
| `ascii100.txt` | 1153 → 1055 | mudou, previsto |
| `maxrows.txt` | 1539 → 994 | mudou, previsto |
| `w50.txt` | 384 | **imóvel** |
| `w38.txt` | 357 | **imóvel** |
| `plain.txt` | 332 | **imóvel** |
| `brief.txt` | 183 | **imóvel** |

**`w100.txt`.** Saem cinco linhas: a borda superior com os três cabeçalhos de
raia, três linhas de célula e a borda inferior. Entram treze: a linha de
contagens (que carrega os três números das raias mais `done`), o rótulo do grupo
`v1.1 Surface`, a linha da fase 3 (`◔`, tem `03-01-PLAN.md` em disco), suas duas
tarefas, a linha da fase 4 (`◌`, não tem diretório), suas duas tarefas, o rótulo
`No milestone` e a tarefa solta. Quatro títulos voltam inteiros:
`Read the roadmap int…`, `Hold…`, `Wait on t…` e `Fill the screen at a…`. O
sufixo `⧗ brd-001` vira `blocked by brd-001`, e o `⧗` reaparece à frente da
linha como símbolo de etapa. **Rodapé, `PENDING PHASES`, `PURPOSE` e a nota de
paralelismo: byte a byte idênticos** — não aparecem no hunk.

**`ascii100.txt`.** Mesma estrutura, com `o ◔`, `O ◕`, `. ◌`, `~ ⧗` e o
separador ` | `. Um detalhe que vale registrar: `<- brd-001` (o `g_dep` ASCII)
**desaparece por completo**, porque o bloqueador passou a ser escrito em
palavras — e palavras são as mesmas nos dois modos.

**`maxrows.txt`.** Além da mudança de forma, uma mudança de **flag**: de
`--max-rows 2` para `--max-rows 1`. O teto passou a valer por balde, e o maior
balde deste fixture tem duas issues; a `--max-rows 2` nada transborda e o arquivo
sairia byte a byte igual ao `w100.txt`, que é exatamente a armadilha que o plano
20-01 descreveu ao escolher o valor original. A troca está escrita nos dois
lugares que a decidem — `regenerate.sh` e `cairn-board-invariance.bats` — e um
`+1 more` de raia virou dois `+1 more`, um por balde que transborda.

## Duas coisas que vão parecer defeito e não são

**1. `v1.1 Surface` no topo e `· v1.0 ·` no rodapé, na mesma tela.** O cabeçalho
de grupo vem de `groups[].label`, que só existe para milestone **aberto** — o
`roadmap_milestones()` lê o marcador da própria linha do ROADMAP. O rodapé vem de
`data["milestone"]`, que é `STATE.md` primeiro. O `make_board_fixture` arma essa
discordância **de propósito** desde o plano 20-01, para reproduzir o defeito
medido em 2026-08-03 (o board anunciando `MILESTONE v1.4` dez minutos depois do
v1.4 ser arquivado). O que mudou é que agora a discordância está **visível numa
tela só**, que é melhor do que estar escondida. Consertar o rodapé é BOARD-04,
fase 22, e fazê-lo aqui seria atravessar a fronteira.

**2. `MAX_INNER` ficou órfã.** A linha que a usava saiu junto com `render_board`
do ramo largo. Deixada de pé de propósito para não misturar limpeza com troca de
renderizador; o plano 21-02 a remove, e a dívida está escrita no `<objective>`
dele.

## As sete quebras, medidas

Cada uma aplicada de verdade no script, medida, e restaurada por `cp` — nunca por
`git checkout`, que descarta tudo que não está no índice.

| quebra | vermelhos |
|---|---|
| `◔` trocado por `○` (east_asian_width=A) | **2**, sozinho |
| um símbolo ASCII com dois caracteres | 2 e 5 |
| só o primeiro bloqueador nomeado | **4**, sozinho |
| `truncate()` de volta no título | 3, 5 e 6 |
| o card do tracker descartado quando aperta | **3**, sozinho |
| grupo `unphased` emitido primeiro | **1**, sozinho |
| quebra de linha sem descontar o prefixo | **6**, sozinho |

A linha que mais informa é a primeira, e ela só ficou assim depois de uma
correção. Na primeira medição, trocar um símbolo deixava **seis** testes
vermelhos, porque o parser dos testes carregava os dez símbolos escritos à mão e
parava de reconhecer linha. Seis testes vermelhos por motivo de parsing fazem a
falha do teste de largura não dizer nada de especial. A classe de símbolo passou
a ser **lida do script**, e a regressão de largura voltou a cair no único teste
que sabe explicá-la.

## Task Commits

1. **Task 1: a lista de ponta a ponta** — `8b08975` (feat)
2. **Task 2: as quebras medidas** — `efc0938` (test)
3. **Task 3: os dez testes reescritos** — `2c7afed` (test)
4. **Task 4: três referências regeneradas** — `6cec88b` (test)

## Os dez testes reescritos, nenhum apagado

`grep -c '^@test'`: `cairn-status.bats` **55**, `cairn-tracker-card.bats` **19** —
as duas contagens intactas.

Dois merecem destaque porque não são renomeações:

- **"long titles are truncated with an ellipsis inside the cell" foi
  INVERTIDO.** Ele afirmava `refute_in_output "cannot possibly fit inside one
  board cell"`. BOARD-03 faz o contrário ser o contrato, então a asserção virou
  de lado, no mesmo arquivo, sobre o mesmo título, com a data e o motivo no
  comentário. Apagá-lo teria deixado o arquivo sem nenhum teste sobre título
  longo.
- **"when the lane is too narrow the card falls out and the title stays" foi
  SUBSTITUÍDO por uma propriedade mais forte.** Ele prendia a precedência que
  `make_cell()` construiu na fase 29 (o card cai primeiro, depois o resto, o
  título sempre vence). Aquela precedência existia porque a célula tinha largura
  fixa e alguma coisa **tinha** que sair; uma linha que quebra não tem o que
  ranquear. O comentário diz isso por extenso, com data, para que uma auditoria
  futura não leia como cobertura perdida.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Verde falso] `no card is pushed out of its lane, at any width` estava verde inspecionando nada**

- **Found during:** Task 3
- **Issue:** O filtro do teste era `if line[:1] not in "┌│└+|": continue`. Em
  Python, `"" in "┌│└+|"` é **True** — a string vazia é subcadeia de qualquer
  string. Então toda linha em branco contava como linha de grid. Com o grid
  presente isso era inofensivo; sem ele, a contagem `seen > 0` passava a ser
  satisfeita **só por linhas em branco**, e o teste ficou verde acima de 64
  colunas medindo zero linhas de board. Ele foi um dos dois de
  `cairn-tracker-card.bats` que **não** apareceram vermelhos na varredura, e o
  motivo era esse.
- **Fix:** O filtro rejeita a linha vazia explicitamente e passou a reconhecer
  também a linha de tarefa da lista (seis espaços). A exceção `limit < 64` foi
  **mantida e documentada** em vez de alargada: abaixo de `STACK_BELOW` os
  degrades não produzem nem grid nem linha de seis espaços, então o filtro
  genuinamente não descreve nada ali — e dizer isso é melhor que alargar o filtro
  até passar. O plano 21-02 remove os degrades e a exceção sai com eles.
- **Verification:** Com a correção, o teste ficou **vermelho** (a asserção
  `seen > 0` disparando em 64+), o que provou que ele voltou a medir; a exceção
  documentada o devolveu ao verde sobre o que ele de fato cobre.
- **Committed in:** `2c7afed`

**2. [Rule 2 - Prova insuficiente] O parser dos testes escondia a especificidade da medição de largura**

- **Found during:** Task 2
- **Issue:** Descrito acima: com os dez símbolos escritos à mão no teste, a
  quebra B1 reprovava seis testes por motivo de parsing.
- **Fix:** `SYMS_ALL` é lido do próprio `cairn-status.py` na carga do arquivo de
  teste.
- **Verification:** B1 remedido: **só o teste 2**.
- **Committed in:** `efc0938`

**3. [Rule 1 - Bug no teste novo] Dois renders no mesmo teste gravavam no mesmo arquivo**

- **Found during:** Task 2
- **Issue:** O helper `render()` nomeava o arquivo com `$$`. Dois renders dentro
  do mesmo teste compartilham o pid, então o segundo sobrescrevia o primeiro e o
  teste de alinhamento entre modos comparava um render **consigo mesmo**.
- **Fix:** Contador por chamada.
- **Verification:** Com `$$`, o teste 5 falhava por `KeyError` no mapa de
  símbolos; com o contador, verde — e a quebra B2 o reprova, que é a prova de que
  ele agora compara duas coisas diferentes.
- **Committed in:** `efc0938`

### Divergências entre o plano e o que a árvore era

**4. `wrap_cells()` virou `wrap_spans()`.** O plano descreve um quebrador de
texto puro. O corpo de uma linha carrega segmentos **estilizados** (o marcador
`·done-phase` e a chave do tracker são dim, o bloqueador é vermelho), e um
quebrador de texto puro os apagaria. O quebrador é ciente de span; a intenção do
plano — quebrar por célula, nunca por caractere, nunca partir token — está
inteira.

**5. A varredura do plano não achou dois testes que precisavam de reescrita.** O
plano lista dez testes de `cairn-status.bats` que afirmam a forma do kanban,
achados por `grep` de box-drawing e de cabeçalho de raia. Faltaram
`long titles are truncated with an ellipsis inside the cell` (afirma `'…'`) e
`long id prefixes are truncated so the grid stays aligned` (afirma
`^[+|]` por `awk`). Os dois são justamente os mais importantes da fase, porque o
primeiro afirma o **oposto** de BOARD-03. A varredura por padrão visual não
substitui rodar a suíte: os dez vermelhos reais foram 8 em `cairn-status.bats` e
2 em `cairn-tracker-card.bats`, e a lista do plano acertou 6 deles.

**6. O teste de título longo varre de 64, não de 60.** Medido: a `--width 60` a
saída ainda é o degrade empilhado (`READY (3)` / `DOING (2)` / `BLOCKED (2)`),
que este plano deixa vivo de propósito. Afirmar BOARD-03 a 60 aqui seria afirmá-lo
de código que este plano não escreveu. O comentário do teste registra isso e o
plano 21-02 estende a varredura.

**7. A chave do tracker deixou de ser truncada em 16 células.** `make_cell()`
fazia `truncate(tracker_key(...), 16, ell)` para proteger a célula de largura
fixa. Sem célula fixa não há o que proteger, e uma chave cortada ao meio não
identifica issue nenhuma — que é o argumento que o próprio `tracker_key()`
escreve sobre `gh-42`. Mudança de comportamento deliberada, e os testes de
`cairn-tracker-card.bats` seguem verdes com chaves de até 27 caracteres.

---

**Total deviations:** 3 auto-fixed (2 × Rule 1, 1 × Rule 2) + 4 divergências
registradas
**Impact on plan:** Nenhuma expansão de escopo. A primeira é a que importa: sem
ela a fase teria deixado um teste verde que não mede nada, dentro do arquivo que
mais precisa medir.

## Achados registrados e roteados, não consertados aqui

- **Sem seção `## Milestones` no ROADMAP, a lista perde a fase.**
  `make_gsd_fixture` — o fixture GSD genérico — não tem essa seção, então
  `roadmap_milestones()` devolve `[]`, nenhum grupo de milestone é emitido (D-03
  da fase 20) e **toda** issue cai em `No milestone`, sem linha de fase, mesmo
  carregando `phase-2`. Está correto pela letra de BOARD-06 e é insatisfatório
  pelo espírito do milestone ("onde você está"). Não é conserto desta fase: exigiria
  o grupo solto ganhar baldes por fase, o que é mudança de contrato de
  `phase_groups()` — fase 20, fechada. Roteado para o plano 21-03 registrar como
  issue bd e entregar à fase 22, que já é dona de "diz explicitamente quando não
  há milestone aberto" (BOARD-04).
- **Glifos `east_asian_width=A` remanescentes.** `▶` (`g_next`), `◆` (`g_who`),
  `·` (`g_stale` e `sep`) e `…` (`ell`) são todos `A`, e o box-drawing que sai
  daqui também era. O critério 2 desta fase cobre só os símbolos de **etapa**; os
  outros ficam e o board segue desalinhando em locale CJK por causa deles.
  Registrado para virar issue bd no 21-03.

## Issues Encountered

- **Um run da suíte foi morto e reportou `exit 1` com zero testes executados.**
  `bats-exec-suite` imprimiu `Killed: 9` e
  `# bats warning: Executed 0 instead of expected 74 tests`. Um `exit 1` desses é
  indistinguível de "falhou" se alguém contar só o código de saída, e
  indistinguível de "passou" se alguém contar só `not ok`. Toda contagem desta
  fase lê o TAP inteiro do arquivo e confere o `1..N` contra a soma de `ok` e
  `not ok`.
- **O meu próprio harness de quebras teve o defeito que ele existe para pegar.**
  Ele contava linhas `not ok` do stdout; um run que não chegou a executar produz
  zero delas, e o harness reportou "NENHUM vermelho" para a quebra B3 — que, remedida
  com o TAP inteiro, reprova o teste 4 sozinha. Corrigido e remedido.
- **Um baseline de suíte inteira foi contaminado e descartado.** Ele foi lançado
  antes da primeira edição e ainda estava rodando quando o código mudou; os
  arquivos que ainda não tinham rodado passaram a rodar contra código novo.
  A parte útil dele sobreviveu e está registrada: os testes 74-80, os sete de
  invariância, rodaram **antes** de qualquer edição e fecharam verdes — que é
  exatamente o "antes" que esta fase precisava. A medição de suíte inteira é do
  plano 21-03, com a árvore parada.
- **`--jobs 2` é obrigatório e não é conservadorismo.** Três fases dividem oito
  núcleos nesta máquina; os dois runs mortos aconteceram sob contenção.

## User Setup Required

None.

## Next Phase Readiness

- O plano 21-02 tem o alvo definido: os três renderizadores viram um, `MAX_INNER`
  sai, `w50` e `w38` são regenerados, e o teste de título longo desce até 30
  colunas — a exceção `limit < 64` de `cairn-tracker-card.bats` sai junto.
- O plano 21-03 herda dois achados para virar issue bd e o docstring de módulo
  (passos 5 e 5b), que ainda descreve o kanban.
- `--plain`, `--brief` e o ramo não-TTY seguem intocados, e `plain.txt` e
  `brief.txt` provam isso byte a byte.

---
*Phase: 21-the-grouped-board*
*Completed: 2026-08-05*

## Self-Check: PASSED

- Os 10 arquivos declarados existem em disco; os 4 commits de task existem em `git log`.
- `bats tests/cairn-grouped-board.bats` → **7/7**, `EXIT=0`, plano `1..7`.
- `bats tests/cairn-status.bats tests/cairn-tracker-card.bats` → **73/74** na
  primeira leitura, com o único vermelho sendo o verde falso que esta fase
  corrigiu; **74/74** depois, plano `1..74` conferido contra a soma.
- `bats tests/cairn-board-invariance.bats` → **9/9**, plano `1..9`.
- `grep -c '^@test'`: `cairn-status.bats` 55, `cairn-tracker-card.bats` 19,
  `cairn-board-invariance.bats` 9, `cairn-group-model.bats` 14.
- `diff -q` contra a cópia de `/tmp/p21/ref-before/`: `w50`, `w38`, `plain` e
  `brief` byte a byte idênticos.
