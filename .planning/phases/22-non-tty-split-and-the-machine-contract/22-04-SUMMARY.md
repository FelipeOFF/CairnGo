---
phase: 22-non-tty-split-and-the-machine-contract
plan: "04"
subsystem: cairn-status
tags: [width, phase-panel, east-asian-width, locale, cdx, hbo]

requires:
  - phase: 22-non-tty-split-and-the-machine-contract
    provides: "o split que manda o não-TTY por esta tabela a 80 colunas"
provides:
  - "panel_columns(): encolhe, depois derruba, e nomeia o que caiu"
  - "o painel de fases inteiro cabendo de 30 a 200 colunas"
  - "a fronteira de alinhamento em locale CJK, declarada onde a régua mora"
affects: [22-05]

tech-stack:
  added: []
  patterns: ["coluna que não cabe é retirada e nomeada, nunca espremida até virar reticência"]

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-status.py
    - tests/cairn-grouped-board.bats
    - tests/fixtures/board-render/w50.txt
    - tests/fixtures/board-render/w38.txt

decisions:
  - "Encolher primeiro, derrubar depois — encolher salva a coluna que está a uma célula de caber; derrubar impede que ela vire uma reticência"
  - "O piso de uma coluna nunca é menor que o próprio cabeçalho: uma coluna cujo título sai `issu…` mente sobre estar ali; uma ausente e nomeada diz que saiu"
  - "Uma coluna encolhida NÃO volta a crescer quando outra cai: reempacotar daria arrumação melhor e contrato pior, porque a largura de uma coluna passaria a depender do que aconteceu com outra"
  - "Abaixo do mínimo do núcleo a tabela não imprime — o PURPOSE abaixo carrega tudo, wrapped, em qualquer largura, então não se perde nada"
  - "CairnGo-hbo resolvido como FRONTEIRA DECLARADA, não como conserto: o alinhamento vale em locale ocidental e não em CJK"

metrics:
  duration: 65min
  completed: 2026-08-06

requirements-completed: []
status: complete
---

# Phase 22 Plan 04: A tabela que cabe, e a fronteira que se declara Summary

**A tabela `PENDING PHASES` deixou de exigir 90 colunas de um board de 50, e o
alinhamento em locale CJK deixou de ser uma promessa não dita para virar uma
fronteira escrita ao lado da régua que a produz.**

## A varredura, antes e depois

Medida com largura de coluna real (`east_asian_width`, nunca `len()`) e sobre a
linha **sem padding à direita**, para não contar espaço em branco como estouro:

| largura | ANTES | DEPOIS |
| --- | --- | --- |
| 30 | 90 células — ESTOURA | cabe |
| 38 | 90 — ESTOURA | cabe |
| 44 | 90 — ESTOURA | cabe |
| 50 | 90 — ESTOURA | cabe |
| 60 / 64 / 70 / 80 / 90 | 90-92 — ESTOURA | cabe |
| 100 / 120 / 140 / 200 | cabe | cabe (bytes idênticos a 100) |

O piso era `76 + num_w − 1 + len(next)` — 90 no fixture, 92 neste repositório —
porque as seis larguras opcionais eram somadas incondicionalmente enquanto
`phase` colapsava para **uma** célula. Já era defeito; o `PIPE-02` o tornou
urgente, porque o caminho não-TTY passou a renderizar esta tabela a **80**.

## Como ela passou a caber

`panel_columns(width, num_w)` resolve em duas fases, ambas na mesma ordem de
sacrifício — `waits`, `rsch`, `verify`, `issues`, `plans`:

1. **Encolhe** até o piso de cada coluna. É o que salva a coluna que está a uma
   célula de caber.
2. **Derruba**, e **nomeia** as que saíram (`hidden at this width: …`). É o que
   impede que uma coluna vire uma reticência.

A ordem tem razão escrita por posição, não gosto: `waits` primeiro porque a mesma
informação está em palavras no `PURPOSE` logo abaixo; `rsch` porque é um sinal
`yes/—` que raramente decide sozinho; `verify` porque só fala de fase já
executada; `issues` e `plans` por último porque são as duas que respondem "quanto
já andou".

**A regra dos pisos é uma só: nenhuma coluna encolhe abaixo do próprio
cabeçalho.** Uma coluna cujo título sai `issu…` mente sobre estar ali; uma ausente
e nomeada diz que saiu. A única exceção é `verify`, com piso 8 contra um
cabeçalho de 6, porque `verified` e `pending` têm 8 e 7 células e uma coluna de
veredito que não mostra seus vereditos mais comuns não carrega informação,
carrega reticência.

**Uma coluna encolhida não volta a crescer quando outra cai.** Reempacotar depois
de cada queda daria arrumação melhor e contrato pior: a largura de uma coluna
passaria a depender do que aconteceu com uma coluna do outro lado da tabela.

Abaixo do mínimo do núcleo (`# phase state next`), a tabela **não imprime** e diz
quanto precisa. Nada se perde: o `PURPOSE` abaixo já carrega cada fase pendente,
com número, propósito e razão de roteamento, **wrapped**, em qualquer largura. É
por isso que "não imprimir" é resposta legítima para esta tabela e não seria para
a lista agrupada.

## Os dois estouros vizinhos que a varredura encontrou

Nenhum dos dois estava na issue, e os dois são o mesmo defeito noutro lugar da
mesma função:

**O `PURPOSE` quebrava em `max(30, width − num_w − 4)`** — o piso 30 atropelava a
largura pedida — e depois indentava por `num_w + 4`, produzindo linhas de 35-36
células num board de 30. O piso virou `max(10, …)`, baixo o bastante para nunca
brigar com a subtração.

**A linha de conflitos** (`✗ 1 blocks — /cairn:doctor for the itemized report`,
52 células) saía sem quebra e vazava de um board de 50. Passou a quebrar por
`wrap_spans`, que preserva as cores vermelho/amarelo dos marcadores através da
quebra — `textwrap` as achataria em texto puro.

E **as duas notas que este plano introduziu** (`hidden at this width: …` e
`table needs N columns …`) nascem quebradas por `panel_note_lines()`: uma
mensagem sobre não caber que não cabe é exatamente a piada que este plano existe
para parar de contar.

## A quebra medida, e a primeira tentativa que não mediu nada

A primeira mutação (fazer `need` absurdamente negativo, para nada encolher nem
cair) **não reproduziu o defeito**: com `available` negativo, `show_table` virava
falso e a tabela simplesmente sumia. A varredura passou verde e só o segundo
teste reprovou. Uma mutação que reprova pelo motivo errado não é medição.

A segunda mutação desligou as duas coisas — a soma condicional **e** o
`show_table` — e aí sim reproduziu:

```
--width 30   maior 94   7 ESTOURAM
--width 38   maior 94   7 ESTOURAM
--width 50   maior 94   6 ESTOURAM
--width 64   maior 94   6 ESTOURAM
--width 80   maior 94   6 ESTOURAM
--width 90   maior 94   5 ESTOURAM
--width 100  maior 100  OK
```

Vermelho de 30 a 90, verde a partir de 100 — a faixa prevista no plano. Os dois
testes novos reprovaram. Restauro por `cp` da cópia, nunca `git checkout --`.

## `CairnGo-hbo`: a decisão, e por que não é código

Medido em 2026-08-06, render a `--width 100` deste repositório: **53** ocorrências
de caracteres `east_asian_width=A`, 9 distintos.

| glifo | ocorrências | origem |
| --- | --- | --- |
| `—` EM DASH | 28 | pontuação do script e da prosa do roadmap |
| `…` ELLIPSIS | 8 | `Style.ell` |
| `·` MIDDLE DOT | 4 | `Style.sep`, `g_stale` |
| `▶` | 1 | `g_next` |
| **`á ê ó í é`** | **12** | **letras acentuadas da prosa** |

(O contexto da fase registra 51 num render anterior; a diferença é o board ter
mudado de conteúdo entre as duas leituras, não desacordo de método.)

Os 12 acentos são o número que decide. Trocar `—` por `-` e `…` por `...`
removeria 36 das 53 e **não resolveria nada**: enquanto a prosa for portuguesa,
cada `á` vale duas células num terminal CJK. Escolher glifos não resolve um
problema que a língua cria.

A outra saída — resolver `A` pelo ambiente — foi recusada pela razão que este
arquivo já registrou uma vez, na escolha dos símbolos de etapa da fase 21:
exigiria ler `LANG`/`LC_CTYPE` e decidir por heurística o que só o emulador de
terminal sabe, e *"inventar essa leitura seria inventar uma fonte de verdade"*.
Resolver metade (os símbolos) e adivinhar a outra (a prosa) é pior que uma
fronteira honesta.

**A decisão, escrita no docstring de `char_width()`, ao lado da régua:**

> The board's column alignment is guaranteed in a WESTERN locale.
> It is NOT guaranteed in a CJK locale.

A nota do passo 5 do módulo, que descrevia o mesmo achado como pendência, foi
**reescrita** e não apagada: deixou de ser pendência e passou a apontar para a
fronteira.

## As oito referências: previsão e resultado

Previsão escrita antes de rodar: movem-se `w50` e `w38`; ficam imóveis `w100`,
`ascii100`, `maxrows`, `brief`, `plain` e `nontty-pre-split`. Conferido por `cmp`
contra cópias em `/tmp` feitas ANTES:

```
MOVEU    w38.txt   w50.txt
IMOVEL   w100.txt  ascii100.txt  maxrows.txt  brief.txt  plain.txt  nontty-pre-split.txt
```

O diff é a melhoria visível:

```
 PENDING PHASES  2                                   (w50)
-  #  phase  state             rsch   plans   issues   verify            waits    next
-  3  …  planned           —      0/1 p…  0/2      —                 —        /cairn:work 3
+  #  phase      state             next
+  3  Phase mo…  planned           /cairn:work 3
+  hidden at this width: waits, rsch, verify,
+  issues, plans — widen, or /cairn:status --json
```

A 50 colunas a coluna `phase` era **um `…` sozinho**; agora mostra `Phase mo…` e
`Board fi…`, `state` sai inteiro, `next` sai inteiro, e as cinco que saíram estão
nomeadas. A 38 a tabela cede o lugar (`table needs 44 columns`) e o `PURPOSE`
continua.

## O que este plano NÃO consertou, com número

Sobrou **uma** linha do board que ainda excede a largura pedida, e não é do
painel: a linha de contagens (`ready 23 · doing 2 · blocked 0 · done 94`, 40
células a `--width 30` e `38`). Ela mora em `render_groups()`, outro renderizador,
e no fixture cabe (números de um dígito, 38 células exatas). Não é o transbordo
que o `BOARD-03` permite — ali há quatro espaços onde quebrar. Registrada como
**`CairnGo-7yw`**, `discovered-from: CairnGo-cdx`.

## Verificação

| suíte | plano | ok | not ok |
| --- | --- | --- | --- |
| `tests/cairn-status.bats` | `1..57` | 57 | 0 |
| `tests/cairn-grouped-board.bats` | `1..14` | 14 | 0 |
| `tests/cairn-group-model.bats` + `cairn-board-invariance.bats` | — | 26 | 0 |

`cairn-grouped-board.bats` passou de 12 para 14 `@test`.

## Commits

| hash | mensagem |
| --- | --- |
| `4253610` | `fix(22-04): a tabela cabe na largura pedida, e o alinhamento ganha fronteira escrita` |

## Self-Check: PASSED

- `cairn/scripts/cairn-status.py` — FOUND (`panel_columns`, `panel_note_lines`, `PANEL_SACRIFICE`, docstring de `char_width`)
- `tests/fixtures/board-render/w50.txt`, `w38.txt` — FOUND, movidos conforme previsto
- as outras seis referências — FOUND, imóveis por `cmp`
- issue `CairnGo-7yw` — FOUND
- commit `4253610` — FOUND
