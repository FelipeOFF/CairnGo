---
phase: 21-the-grouped-board
subsystem: cairn-status
tags: [board, render, unicode, east-asian-width, golden-file, bats, dead-code]

requires:
  - phase: 20-group-model
    provides: "a chave `groups` — milestone aberto → fase → issue, forma fechada e presa por 14 testes"
provides:
  - "a lista agrupada como ÚNICO renderizador humano, em toda largura"
  - "símbolos de etapa medidos por east_asian_width, com fallback ASCII de um caractere"
  - "título nunca truncado, de 30 a 140 colunas"
  - "linha bloqueada nomeando TODOS os bloqueadores em palavras"
  - "sete referências de render coerentes com o renderizador que existe"
affects: [22-non-tty-split, 23-not-applicable-state, 25-measured-cleanup]

plans: ["01", "02", "03"]

requirements-completed: [BOARD-02, BOARD-03, BOARD-05, BOARD-06]

duration: 400min
completed: 2026-08-05
status: complete
---

# Phase 21: The grouped board Summary

**O kanban de três colunas saiu inteiro — renderizador, degrades de largura e as constantes que os dimensionavam — e no lugar ficou uma lista agrupada pelo modelo da fase 20, com a etapa num símbolo de uma célula escolhido por `unicodedata` e não por aparência, o título inteiro em qualquer largura de 30 a 140 colunas, e todo bloqueador nomeado em palavras na própria linha.**

## Os quatro critérios de sucesso, julgados um a um

### 1. Nenhum título é truncado em nenhuma largura em que a linha caiba — ATENDIDO

`truncate()` não aparece mais no caminho da linha de tarefa. O teste
`a genuinely long title is never truncated, at any width that holds a word`
varre **30, 38, 50, 60, 64, 80, 100 e 140** colunas com um título de 125
caracteres, e o laço só desceu abaixo de 64 no plano 21-02: enquanto os degrades
estavam de pé, medido a `--width 60` a saída ainda era `READY (3)` / `DOING (2)`
/ `BLOCKED (2)` e ainda truncava. Afirmar a propriedade a 60 antes disso seria
afirmá-la de código que a fase ainda não tinha escrito.

A única exceção documentada é um token único mais largo que a coluna, que
**transborda** em vez de ser partido — e o fixture contém esse caso
(`brd-203`, com uma URL de 72 caracteres), para que a cláusula não seja uma
frase que ninguém exercita.

**A ressalva honesta:** a tabela `PENDING PHASES`, abaixo da lista, **ainda
trunca título de fase** — a 50 colunas a coluna `phase` sai como um `…` sozinho.
É largura fixa por desenho, nenhum critério desta fase a alcança, e virou a
issue `CairnGo-cdx` com a medição (piso de 92 células; estoura de 64 a 90
colunas, inclusive em larguras que já eram caminho largo ANTES desta fase).

### 2. Símbolos de etapa todos de largura simples, medidos por `unicodedata` — ATENDIDO

O conjunto é `◌ ◔ ◕ ✓ ⧗`, todos `east_asian_width=N`. `○` (U+25CB), `◑`
(U+25D1) e `◆` (U+25C6) são `A` — uma célula em locale latino, **duas** em CJK —
e foram descartados por isso. O teste lê os cinco símbolos **do script**, nunca
de literais retypados, e afirma `east_asian_width(ch) == 'N'` e
`char_width(ch) == 1`.

Ler a classe do script não foi zelo: medido enquanto os testes eram escritos,
com os dez símbolos codificados no teste, trocar um por um glifo `A` deixava
**seis** testes vermelhos em vez de um — o parser parava de reconhecer linhas e
a falha de largura não dizia nada de especial.

**A ressalva honesta, registrada no docstring e como issue:** os glifos `A` que
**continuam** no arquivo fora dos símbolos de etapa — `▶` (`g_next`), `◆`
(`g_who`), `·` (`g_stale` e `sep`) e `…` (`ell`). O board segue desalinhando em
locale CJK por causa deles. Issue `CairnGo-hbo`.

### 3. `--ascii` produz um conjunto equivalente e as colunas fecham alinhadas — ATENDIDO

`. o O v ~`, exatamente um caractere cada, o que torna "as colunas fecham nos
dois modos" uma afirmação mecânica: 1 caractere == 1 célula, então cada coluna
cai na mesma célula da contraparte Unicode. O teste
`--ascii swaps the symbols and moves no column` compara as duas saídas coluna a
coluna, e `x ! * #` foram recusados não por gosto mas por colisão — já são
`g_conflict`, `g_informs`, `g_stale` e `g_card` na mesma saída.

### 4. Linha bloqueada nomeia o bloqueador na própria linha — ATENDIDO

`blocked by brd-001, brd-007`, em palavras, e **todos** — não só o primeiro,
como fazia `make_cell()`. Quebra medida: voltar a `blocked_by[0]` reprova
`a blocked row names every blocker it has, on the row itself`, sozinho.

## O veredito consolidado do diff das sete referências

As sete foram congeladas pela fase 20 exatamente para que uma mudança de render
fosse impossível de fazer em silêncio. Elas mudaram, em dois atos, e cada ato
teve commit próprio cuja mensagem carrega o diff lido. O consolidado:

| arquivo        | 21-01                | 21-02                | por quê                                                                                                       |
| -------------- | -------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------- |
| `w100.txt`     | 1539 → 1096 bytes    | imóvel               | as 5 linhas do grid saem; entram contagens, rótulo de milestone, 2 linhas de fase e 5 de tarefa; 4 títulos voltam inteiros |
| `ascii100.txt` | 1153 → 1055 bytes    | imóvel               | mesma estrutura; `<- brd-001` some porque o bloqueador passou a ser escrito em palavras, iguais nos dois modos    |
| `maxrows.txt`  | `--max-rows 2` → `1` | imóvel               | o teto passou de raia para balde; a 2 nenhum balde transborda e o arquivo viraria cópia de `w100`               |
| `w50.txt`      | imóvel               | 384 → 1130 bytes     | sai o empilhado; entra a lista, e o painel de fases aparece a 50 colunas **pela primeira vez**                   |
| `w38.txt`      | imóvel               | 357 → 1141 bytes     | sai a lista crua `LANE id title`; entra a lista na forma estreita, com o corpo abaixo do id                     |
| `plain.txt`    | imóvel               | imóvel               | fronteira da fase 22                                                                                            |
| `brief.txt`    | imóvel               | imóvel               | fronteira da fase 22                                                                                            |

**As duas verificações que fazem esse quadro valer alguma coisa:** cada
regeneração foi comparada com uma cópia em `/tmp` feita ANTES (`cmp`, não `git
diff` — uma área de stage errada não pode fabricar um "não mudou"), e as
previsões de imobilidade foram escritas no plano ANTES de rodar. Nenhuma se
moveu contra a previsão.

O achado que só apareceu porque o diff foi lido: `render_stacked()` devolvia
`lines + footer_lines(...)` e **nunca** chamava `phase_panel_lines()`. O degrade
engolia o painel de fases inteiro, em silêncio, em toda largura abaixo de 64.
Isso não estava em plano nenhum e não teria aparecido se a regeneração tivesse
sido feita sem ler o diff.

## O board deste repositório, no fim da fase

`--width 100`, real, com as quatro issues da fase já fechadas — a fase 21
aparece com o símbolo de "em andamento" e sem nenhuma tarefa aberta embaixo,
que é exatamente o que uma fase pronta para fechar parece:

```
ready 31 · doing 1 · blocked 0 · done 86

v1.5 Legible State
  ✓ 20  Group model
  ◕ 21  The grouped board
  ◌ 22  Non-TTY split and the machine contract
      ◔ CairnGo-5yo  PIPE-03: O teste do acoplamento e reescrito em duas assercoes, nunca removido
      ◔ CairnGo-ca5  PIPE-01: --plain segue TSV estavel, byte a byte compativel
      ...
```

O contraste com o que existia antes da fase é o ponto inteiro: as três raias
gastavam a largura dividida por três, `READY` tinha 31 linhas e as outras duas
ficavam vazias, e todo título era cortado em ~28 caracteres.

## O que a fase entregou, por plano

| plano   | entrega                                                                                      | commits |
| ------- | ---------------------------------------------------------------------------------------------- | ------- |
| `21-01` | a lista agrupada no caminho largo; 7 propriedades com quebra medida; 3 referências regeneradas   | 5       |
| `21-02` | um renderizador só, para toda largura; 11 nomes + 8 letras de box-drawing fora; 2 referências    | 4       |
| `21-03` | o docstring como spec do que existe; 4 bordas com quebra medida; 3 achados como issue            | 3       |

Uma nota de honestidade sobre o commit `22a6a8f`: o laço de largura que é a
entrega visível do `21-02` (`64 80 100 140` → `30 38 50 60 64 80 100 140`)
viajou nesse commit do `21-03`, e não num commit do `21-02`. As duas edições
caíram no mesmo arquivo na mesma árvore de trabalho, e separá-las com um índice
parcial produziria um commit cujo estado nunca foi medido — o que é pior que um
commit com duas coisas dentro e a mensagem dizendo quais.

## A medição final, com a árvore parada

```
INICIO 2026-08-05T17:01:00Z   HEAD 0d47e15, sete arquivos modificados
1..94
EXIT=0
FIM    2026-08-05T17:16:54Z   15:53 de relógio, bats -j 2
```

94 `ok`, **0** `not ok`, e o plano `1..94` conferido contra a soma — que é a
conferência obrigatória porque um run morto imprime `1..N` e executa zero
testes, e isso aconteceu nesta fase (um log de saída ficou com 0 linhas por uma
redireção minha para o arquivo errado, e a leitura correta veio do arquivo
certo, não da suposição).

Os 94 são os quatro arquivos que a fase tocou: `cairn-grouped-board.bats` (11),
`cairn-status.bats` (55), `cairn-tracker-card.bats` (19) e
`cairn-board-invariance.bats` (9).

## Os três achados, roteados como trabalho e não como prosa

| issue         | procedência (`discovered-from`) | o que foi medido                                                                  |
| ------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| `CairnGo-uz6` | `CairnGo-qwu` (BOARD-06)        | sem `## Milestones` no ROADMAP, `roadmap_milestones()` devolve `[]` e toda issue cai em `No milestone` sem linha de fase, mesmo carregando `phase-N` |
| `CairnGo-hbo` | `CairnGo-8kf` (BOARD-02)        | `▶ ◆ · …` são `east_asian_width=A` e continuam em uso                              |
| `CairnGo-cdx` | `CairnGo-ckv` (BOARD-03)        | `PENDING PHASES` tem piso de 92 células e estoura de 64 a 90 colunas               |

## O que esta fase recusou fazer

**Não atravessou a fronteira da fase 22.** `render_plain()` não foi tocado, e
`LANES` ficou de pé só porque `render_plain()` a lê. `tests/cairn-status.bats`
segue com **55** `@test` — nenhum apagado, dois reescritos — e o teste que
afirma que `--plain` é byte a byte idêntico ao default sem TTY **continua verde
sem ter sido editado**. Ele é do `PIPE-03`, e uma mudança de render que o
quebrasse seria sinal de travessia, não licença para reescrevê-lo.

Uma correção de ponteiro, para quem for executar a fase 22: o acoplamento não
está mais na linha 208. Ele é a última asserção do `@test "non-TTY without
flags defaults to --plain: tabs, no box, no escapes"`, hoje nas linhas 246-251
(`local piped="$output"` … `[ "$output" = "$piped" ]`). A linha 208 hoje é uma
asserção de `--json`. O número andou porque este plano reescreveu dois testes
acima dele; o `PIPE-03` deve procurar pelo nome do teste, não pela linha.

**Não rodou a suíte inteira.** Por instrução direta, e com a medição que a
justifica: `load average` entre 13.7 e 16.8 sobre 8 núcleos, com três worktrees
rodando bats ao mesmo tempo (vistos por `ps`, não presumidos), e
`tests/cairn-status.bats` sozinho levando **12:55**. Rodou exatamente os quatro
arquivos que a fase tocou, com o TAP inteiro em arquivo e o plano `1..N`
conferido contra a soma de `ok` + `not ok`. A suíte completa é da árvore
principal, no merge.

**Não escriturou `STATE.md`, `ROADMAP.md` nem `REQUIREMENTS.md`**, e não rodou
ferramenta de escrituração do `gsd-tools`. Proibidos nesta worktree.
