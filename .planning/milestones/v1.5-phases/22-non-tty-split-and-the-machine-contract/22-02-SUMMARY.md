---
phase: 22-non-tty-split-and-the-machine-contract
plan: "02"
subsystem: cairn-status
tags: [non-tty, pipe, machine-contract, bats, tautological-test]

requires:
  - phase: 22-non-tty-split-and-the-machine-contract
    provides: "a referência do contrato de máquina, capturada antes do split (plano 22-01)"
  - phase: 21-the-grouped-board
    provides: "a lista agrupada como único renderizador humano, sem um glifo de caixa"
provides:
  - "um pipe recebe o board humano em texto puro, sem uma sequência ANSI"
  - "--plain como única porta do contrato de máquina"
  - "o teste do acoplamento partido em duas afirmações positivas"
affects: [22-03, 22-04, 22-05]

tech-stack:
  added: []
  patterns: ["a ausência de TTY decide cor e largura, nunca renderizador"]

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-status.py
    - tests/cairn-status.bats

decisions:
  - "O não-TTY passa pelo MESMO caminho do TTY — board completo, com rodapé e painel — em vez de uma variante estreita: dois renderizadores humanos seria refazer o que a fase 21 acabou de desmontar"
  - "A asserção de igualdade do teste antigo não é substituída por sua negação, e sim por duas afirmações positivas, uma por superfície"
  - "O teste de --color=always foi reescrito porque virou tautologia, não porque ficou vermelho"

metrics:
  duration: 45min
  completed: 2026-08-06

requirements-completed: [PIPE-02, PIPE-03]
status: complete
---

# Phase 22 Plan 02: O split não-TTY Summary

**A cláusula composta que fazia `--plain` ser dois programas virou
`elif opts["plain"]:`, e um pipe passou a receber o mesmo board que um terminal
— sem cor e a 80 colunas, decidido por quem já decidia isso.**

## O diff que é a fase inteira

```python
-    elif opts["plain"] or (opts["width"] is None and
-                           opts["color"] != "always" and
-                           not sys.stdout.isatty()):
+    elif opts["plain"]:
```

Quarenta e nove linhas inseridas, vinte removidas, e quase tudo é docstring: a
mudança de comportamento cabe em três linhas apagadas. Era para ser assim. A
razão original do acoplamento — pipes nunca receberem box-drawing — **morreu na
fase 21**, que tirou o último glifo de caixa do arquivo. Esta fase não desfez uma
decisão errada; ela recolheu uma decisão cuja premissa tinha acabado.

## Os dois md5, agora diferentes

No repositório real, depois do split:

```
não-TTY sem flag   94c8e805a5d0c04df9b0140972252e9e
--plain            052ee127550fafd12822339d0621abee
escapes no pipe    0
```

E as primeiras linhas do que sai por um pipe:

```
ready 26 · doing 2 · blocked 0 · done 90

v1.5 Legible State
  ✓ 20  Group model
  ✓ 21  The grouped board
  ◕ 22  Non-TTY split and the machine contract
```

Antes desta fase esses mesmos bytes eram `READY\tCairnGo-...\t1\t...`.

## O que decide o quê, agora

Nada foi inventado para o caminho não-TTY. As duas diferenças entre pipe e
terminal já estavam resolvidas em outro lugar, e o split só as deixou visíveis:

| decisão | quem decide | valor num pipe |
| --- | --- | --- |
| cor | `Style._color_enabled()`, que termina em `isatty(stdout)` | desligada |
| largura | `terminal_cols()` → `shutil.get_terminal_size((80, 24))` | **80** (medido) |

80 é a mesma largura que um terminal sem `$COLUMNS` recebe. O não-TTY não ganhou
régua própria.

## O PIPE-03, e por que a igualdade não virou desigualdade

O teste `non-TTY without flags defaults to --plain` terminava em
`[ "$output" = "$piped" ]` — o contrato do acoplamento, escrito como asserção.
Ele foi **partido em dois**, nunca apagado:

| novo `@test` | o que afirma |
| --- | --- |
| `non-TTY without flags renders the grouped list in plain text` | contagens, símbolo de etapa + id + título por issue, rodapé, `PENDING PHASES`, zero `\x1b`, e a única negação do teste: `READY\t` não pode aparecer |
| `--plain is the machine contract: tab-separated rows and meta rows` | as três linhas de raia com tabulação, as meta-rows, zero `\x1b`, e nenhum símbolo de etapa |

A tentação óbvia era substituir a igualdade pela negação (`[ "$a" != "$b" ]`).
Duas afirmações positivas são mais fortes: uma igualdade diz que as duas
superfícies são a mesma sem dizer o que nenhuma delas **é**, e a diferença entre
elas passa a ser consequência do que cada uma afirma, não uma asserção própria.

**Quebra medida, com o acoplamento religado no fonte** (backup por `cp`, restauro
pela cópia, nunca `git checkout --`):

```
1..56   ok=54   not ok=2
not ok  7  non-TTY without flags renders the grouped list in plain text
not ok 14  piping decides color, not the renderer
```

Exatamente dois, e são os dois que descrevem a separação. O teste do `--plain`
seguiu verde, como tem de seguir: `--plain` não mudou.

## O achado: um teste que ia virar tautologia em silêncio

`@test "--color=always piped without --width opts into the board renderer"`
afirmava que a flag **força** o renderizador humano num pipe. No instante em que
o pipe passou a renderizar o board por padrão, **todas** as asserções dele
passariam com a flag removida por inteiro — `grep '◔'` fica verde de qualquer
jeito. Um teste que não pode falhar não é teste, e ele teria ficado verde para
sempre, parecendo cobertura.

Reescrito como `piping decides color, not the renderer`: duas execuções no mesmo
pipe e na mesma largura, uma sem flag (board, zero escape) e outra com
`--color=always` (mesmo board, pintado). Nenhuma das metades prova sozinha; o par
prova. E ele reprova de verdade — é um dos dois vermelhos da religação acima.

Esse tipo de achado não aparece rodando a suíte: ela ficaria verde. Apareceu
porque o plano mandava reler os testes vizinhos procurando exatamente isso.

## As oito referências, e a previsão que se confirmou

A previsão escrita no plano antes de rodar: **nenhuma se move**, porque todas
passam flag explícita (`--width`, `--ascii`, `--max-rows`, `--plain`, `--brief`) e
nenhuma exercita o caminho sem flag. Conferido:

```
tests/cairn-board-invariance.bats   1..11   ok=11   not ok=0
git status --short tests/fixtures/  (vazio)
```

## Superfície de risco, medida antes de mexer

Varredura sobre o repositório inteiro: **nenhum** script, hook, adapter, comando
ou skill do cairn chama `cairn-status` sem flag de saída. `/cairn:status` usa
`--width 100`; `/cairn:autonomous` e `/cairn:reconcile` usam `--json`. O único
consumidor do caminho sem flag em toda a árvore era `tests/cairn-status.bats:235`.

A fronteira que a mudança cria — `cairn-status > arquivo` num script de terceiros
passa a receber o board — está escrita no docstring, em maiúsculas, no passo 5, e
vai para `cairn/docs/commands/status.md` no plano 22-05.

## Verificação

| suíte | plano | ok | not ok |
| --- | --- | --- | --- |
| `tests/cairn-status.bats` | `1..56` | 56 | 0 |
| `tests/cairn-board-invariance.bats` | `1..11` | 11 | 0 |
| `tests/cairn-grouped-board.bats` | `1..11` | 11 | 0 |

`cairn-status.bats` tinha 55 `@test` e passou a ter 56: nenhum apagado, um
partido em dois, um reescrito. Cada plano `1..N` foi conferido contra a soma de
`ok` + `not ok` contada sobre o log inteiro, não sobre a cauda.

## Commits

| hash | mensagem |
| --- | --- |
| `aaccea4` | `feat(22-02): o não-TTY renderiza o board, e --plain volta a ser só flag` |

## Self-Check: PASSED

- `cairn/scripts/cairn-status.py` — FOUND (`elif opts["plain"]:` na linha 3697)
- `tests/cairn-status.bats` — FOUND (56 `@test`)
- commit `aaccea4` — FOUND
