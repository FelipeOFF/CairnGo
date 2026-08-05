---
phase: 21-the-grouped-board
plan: "02"
subsystem: cairn-status
tags: [board, render, width, golden-file, dead-code, bats]

requires:
  - phase: 21-the-grouped-board
    provides: "render_groups() e a lista agrupada no caminho largo (plano 21-01)"
provides:
  - "um caminho de render humano só, para toda largura — sem limiar, sem degrade"
  - "NARROW_BODY: a forma estreita, em que o corpo cai para linha própria sob o id"
  - "BOARD-03 provado de 30 a 140 colunas, não mais só acima de 64"
  - "w50.txt e w38.txt regenerados a partir da lista, com o diff lido"
  - "onze nomes do kanban removidos, mais as oito letras de box-drawing do Style"
affects: [21-03, 22-non-tty-split]

tech-stack:
  added: []
  patterns:
    - "Remoção de código morto confirmada por AST, nunca por grep — grep conta prosa de docstring"
    - "Estado só-de-escrita tratado como pior que estado ausente: as oito letras de box-drawing saíram por não terem leitor"
    - "Teste reescrito, nunca apagado: o comentário nomeia o que a asserção antiga guardava e qual guarda a mesma coisa agora"
    - "Refute que ficou infalsificável é rotulado como guarda de reintrodução, não como prova"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-status.py
    - tests/cairn-status.bats
    - tests/cairn-tracker-card.bats
    - tests/cairn-board-invariance.bats
    - tests/cairn-grouped-board.bats
    - tests/fixtures/board-render/w50.txt
    - tests/fixtures/board-render/w38.txt

key-decisions:
  - "Os três renderizadores viram um: três colunas não cabem num terminal estreito, uma cabe em qualquer um, então os dois degrades não tinham mais o que resolver"
  - "LANES fica de pé: stage_symbol(), group_rows() e render_plain() a leem, e render_plain() é contrato da fase 22"
  - "As oito letras de box-drawing do Style saíram junto — não estavam no plano, mas ficaram write-only com render_board fora, e a AST prova"
  - "NARROW_BODY = 24: abaixo disso o corpo cai para linha própria. Decisão de legibilidade, não de correção — por isso ganhou teste próprio em vez de entrar de carona nas asserções de BOARD-03"
  - "O painel de fases continua sendo impresso em toda largura, como o plano escreveu, mesmo tendo piso de 92 células — suprimi-lo seria decisão de outra fase, e o defeito virou issue"

requirements-completed: []

coverage:
  - id: D1
    description: "Um caminho de render humano só, sem limiar de largura"
    requirement: "BOARD-06"
    verification:
      - kind: unit
        ref: "AST: nenhum dos onze nomes (render_board, make_cell, lane_rows, lane_header_text, render_stacked, render_raw, MIN_INNER, MAX_INNER, N_LANES, STACK_BELOW, RAW_BELOW) tem referência executável restante"
        status: pass
      - kind: integration
        ref: "tests/cairn-status.bats#--width 50 renders the same list, wrapped sooner"
        status: pass
      - kind: integration
        ref: "tests/cairn-status.bats#--width 30 keeps every id and title intact, wrapping instead of cutting"
        status: pass
    human_judgment: false
  - id: D2
    description: "BOARD-03 vale de 30 a 140 colunas, não só acima de 64"
    requirement: "BOARD-03"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#a genuinely long title is never truncated, at any width that holds a word — laço 30 38 50 60 64 80 100 140"
        status: pass
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#no row overflows its width, and the one exception is a token that cannot fit — laço 30 38 50 64 72 100 140"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nenhuma constante nem função órfã de pé"
    verification:
      - kind: unit
        ref: "AST sobre cairn-status.py: os onze nomes fora, as oito letras de box-drawing com zero referências, zero glifos de caixa no arquivo"
        status: pass
    human_judgment: false
  - id: D4
    description: "w50 e w38 regenerados com o diff lido; as outras cinco byte a byte imóveis"
    verification:
      - kind: integration
        ref: "bats tests/cairn-board-invariance.bats — 9/9, com as âncoras de w50 e w38 trocadas"
        status: pass
      - kind: other
        ref: "cmp contra a cópia em /tmp/p21-fixtures-antes: w100, ascii100, maxrows, plain e brief idênticos byte a byte"
        status: pass
    human_judgment: false

duration: 95min
completed: 2026-08-05
status: complete
---

# Phase 21 Plano 02: Uma lista, toda largura Summary

**Os três renderizadores de largura (`render_board` >= 64, `render_stacked` >= 40, `render_raw` < 40) existiam por um motivo só — três colunas não cabem num terminal estreito — e uma coluna cabe em qualquer um, então os dois degrades foram removidos junto com as onze constantes e funções que os serviam, e BOARD-03 passou a valer de 30 a 140 colunas em vez de só acima de 64.**

## Performance

- **Duration:** ~95 min, dos quais ~60 min de espera por suíte. Medido: `uptime` marcou `load average 13.7 → 16.8` sobre 8 núcleos com três worktrees (`CairnGo`, `CairnGo-phase-21`, `CairnGo-phase-24`) rodando bats ao mesmo tempo; `tests/cairn-status.bats` sozinho levou **12:55**, contra os ~3:17 de `cairn-grouped-board.bats`.
- **Tasks:** 3
- **Files modified:** 7

## O que mudou no código

`main()` perdeu os dois limiares:

```python
cols = opts["width"] if opts["width"] is not None else terminal_cols()
lines = render_groups(data, cols, opts["max_rows"], style)
lines += footer_lines(data, cols, style)
lines += phase_panel_lines(data, cols, style)
```

Removidos, com a ausência de referência executável confirmada por AST e não por
`grep` (a fase 20 já foi mordida por `grep` contando prosa de docstring —
divergência 1 do 20-03-SUMMARY): `render_board`, `make_cell`, `lane_rows`,
`lane_header_text`, `render_stacked`, `render_raw`, `MIN_INNER`, `MAX_INNER`,
`N_LANES`, `STACK_BELOW`, `RAW_BELOW`.

`LANES` ficou. Três leitores executáveis: `stage_symbol()`, `group_rows()` e
`render_plain()` — e `render_plain()` é contrato da fase 22.

## O diff das duas referências que mudaram, lido

Disciplina do 21-01: as sete foram copiadas para `/tmp/p21-fixtures-antes/`
antes de rodar `regenerate.sh` uma vez, e comparadas com `cmp` depois — a
verificação não depende de `git`, para que uma área de stage errada não possa
fabricar um "não mudou".

**As cinco previstas como imóveis ficaram imóveis, medido por `cmp`:**
`w100.txt`, `ascii100.txt`, `maxrows.txt`, `plain.txt`, `brief.txt`. Nenhuma
delas passa pelos degrades — as três primeiras já eram a lista desde o 21-01, e
as duas últimas são fronteira da fase 22.

**`w50.txt` — 384 → 1130 bytes.** Sai o empilhado: os três cabeçalhos de raia
(`READY (3)`, `DOING (1)`, `BLOCKED (1)`) e as cinco linhas `id  title` de dois
espaços. Entram, na ordem, a linha de contagens `ready 3 · doing 1 · blocked 1 ·
done 1`, o rótulo `v1.1 Surface`, as duas linhas de fase (`◔ 3`, `◌ 4`), o grupo
`No milestone`, e as cinco linhas de tarefa com símbolo de etapa. Três ganhos
concretos e um custo:

- `brd-004` deixa de ser `Hold the lease while ex…` e volta inteiro, quebrado em
  duas linhas com continuação alinhada na coluna do corpo.
- `⧗ brd-001` vira `blocked by brd-001` escrito em palavras, e o `⧗` passa a ser
  o símbolo de etapa da linha — a mesma troca que o 21-01 fez em `w100`.
- **O painel `PENDING PHASES` e a lista `PURPOSE` aparecem pela primeira vez a
  50 colunas.** `render_stacked()` devolvia `lines + footer_lines(...)` e nunca
  chamava `phase_panel_lines()`; o degrade engolia o painel inteiro em silêncio.
  Esse é o único achado do diff que não estava previsto no plano.
- O custo: a 50 colunas a coluna `phase` do painel sai como um `…` sozinho, e as
  três linhas da tabela têm 85–90 células. Ver a seção de achados.

**`w38.txt` — 357 → 1141 bytes.** Sai a lista crua `LANE  id  title`. Entra a
mesma lista, agora na forma estreita: o id fica sozinho na linha e o corpo cai
para linhas próprias com dois espaços de recuo além do recuo da linha. A linha
de fase ainda cabe ao lado do número (`  ◔ 3  Phase model — read what a phase` +
continuação), porque o prefixo de fase é de 8 células e sobram 30; a linha de
tarefa não cabe (prefixo de 16, sobram 22 < `NARROW_BODY`).

Três larguras, três formas — e é isso que faz `w50` e `w38` continuarem valendo
um arquivo cada mesmo depois de virarem o mesmo renderizador: `w50` é o único
onde um título quebra **ao lado** do id, `w38` é o único onde o corpo cai
**abaixo** dele. As âncoras do teste 9 de `cairn-board-invariance.bats` foram
trocadas para exatamente essas duas propriedades, e não para algo que `w100`
também contenha: uma âncora compartilhada com `w100` deixaria qualquer um dos
dois arquivos virar cópia de `w100` em silêncio e ainda passar.

## Deviations from Plan

### 1. [Rule 2 — funcionalidade crítica ausente] As oito letras de box-drawing do `Style` saíram junto

- **Found during:** Task 1, na verificação por AST.
- **Issue:** o plano mandou remover cinco constantes nomeadas. Com `render_board`
  fora, `tl/tm/tr`, `bl/bm/br`, `h` e `v` ficaram **write-only** nos dois ramos
  do `Style` (ASCII e Unicode): a AST conta 2 referências para cada uma, e as
  duas são a própria atribuição. Nada mais no arquivo — nem `render_plain`, nem
  o painel de fases, nem o HTML — lê uma delas.
- **Fix:** removidas. O arquivo agora tem **zero** glifos de caixa. Estado
  só-de-escrita é pior que estado ausente: diz ao próximo leitor que ainda
  existe um grid em algum lugar.
- **Efeito colateral honesto:** os `refute_in_output '┌'` / `'│'` dos dois testes
  reescritos passaram a ser **infalsificáveis por mudança neste renderizador** —
  o caractere não existe mais no fonte. Não foram apagados: guardam contra
  reintrodução, e ganharam comentário dizendo em letras que a prova são os
  `grep` positivos ao lado, não eles.
- **Files modified:** `cairn/scripts/cairn-status.py`
- **Commit:** `0d47e15`

### 2. [Rule 2] `NARROW_BODY = 24` — a forma estreita, que o plano não previu

- **Found during:** Task 2, escrevendo a asserção de `--width 30`.
- **Issue:** o plano pediu para afirmar o título inteiro das três issues a 30
  colunas. Nada era truncado sem a mudança — mas **medido a `--width 30` com um
  id de 11 células, o orçamento de corpo inline é de 9 células** e cada palavra
  cai numa linha sozinha (`de`, `largura`, `com`, `—`). A forma empilhada dá 22.
- **Fix:** abaixo de 24 células de corpo, a linha para de tentar pôr o corpo ao
  lado do id e o deixa cair para linhas próprias.
- **Honestidade sobre a prova:** isto é legibilidade, não correção. **Todas** as
  asserções de BOARD-03 continuam verdes com `NARROW_BODY` removido — medido. Por
  isso ganhou teste próprio (`a narrow width drops the body under the id instead
  of squeezing it`, no plano 21-03) em vez de entrar de carona numa asserção que
  já estava verde.
- **Commit:** `0d47e15`

### 3. [Rule 1] `tests/cairn-tracker-card.bats` entrou nos arquivos tocados

- **Issue:** não estava na lista `<files>` da Task 2, mas carregava a isenção
  `assert limit < 64 or seen > 0` — escrita no 21-01 justamente porque abaixo de
  64 os degrades não emitiam linha de seis espaços, e o próprio comentário dizia
  "esta isenção sai com eles".
- **Fix:** isenção removida; a asserção passou a ser `assert seen > 0` em toda
  largura. Um filtro que não casa com nada é sempre bug do filtro quando existe
  linha de board em toda largura.

### 4. Escopo do teste de transbordo corrigido para o que ele afirma

O teste `no row overflows its width` media **todas** as linhas do bloco. A 30
colunas quem estoura não é linha de tarefa: é a **linha de contagens**
(`ready 3 · doing 1 · blocked 1 · done 1`, 37 células), que começa na coluna
zero e não é uma linha do renderizador de linhas. O teste passou a filtrar por
linhas que começam com dois espaços — que é a definição de linha de fase ou de
tarefa — e o comentário registra que a linha de contagens e a linha meta do
rodapé estouram em terminal estreito desde a fase 13, como transbordo
pré-existente de outros renderizadores, em vez de serem dobradas em silêncio
dentro desta asserção.

## Achados que viraram issue

**`CairnGo-cdx` — a tabela `PENDING PHASES` tem piso de 92 células e estoura de
64 a 90 colunas.** Medido rodando o script e medindo `display_width()` do
painel:

| largura | painel (células) | cabe? |
| ------- | ---------------- | ----- |
| 64      | 92               | não   |
| 72      | 92               | não   |
| 80      | 92               | não   |
| 90      | 92               | não   |
| 100     | 98               | sim   |
| 120     | 118              | sim   |

**Não é regressão desta fase, e a medição é o que prova isso:** 64 já era o
caminho largo antes da fase 21, e 92 > 64. `phase_panel_lines()` encolhe só a
coluna `phase`; as outras oito são fixas. A fase 21 unificou o caminho e por
isso o painel passou a aparecer também abaixo de 64 — aumentou a faixa em que o
defeito é **visível**, não criou o defeito. Nenhum critério desta fase alcança o
painel, então ele não foi mexido; virou issue com a medição por extenso.

## Self-Check: PASSED

- `cairn/scripts/cairn-status.py` — presente, AST válida, zero glifos de caixa
- `tests/fixtures/board-render/w50.txt` — 1130 bytes, difere do backup
- `tests/fixtures/board-render/w38.txt` — 1141 bytes, difere do backup
- as outras cinco referências — `cmp` idêntico ao backup em `/tmp/p21-fixtures-antes/`
- `tests/cairn-board-invariance.bats` — 9 `@test`, plano `1..28` conferido junto com tracker-card, 28 `ok`, 0 `not ok`
