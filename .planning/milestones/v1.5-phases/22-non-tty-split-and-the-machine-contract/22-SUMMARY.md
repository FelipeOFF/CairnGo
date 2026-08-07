---
phase: 22-non-tty-split-and-the-machine-contract
subsystem: cairn-status
tags: [non-tty, machine-contract, milestone, width, locale, golden-file]

requires:
  - phase: 21-the-grouped-board
    provides: "a lista agrupada como único renderizador humano, sem um glifo de caixa — o que tornou a separação segura"
  - phase: 20-group-model
    provides: "roadmap_milestones(), phase_groups() e o padrão de referência byte a byte com prova de liveness"
provides:
  - "`--plain` como contrato de máquina alcançável SÓ pela flag, byte a byte o que era, com duas referências independentes"
  - "o caminho não-TTY renderizando o board humano em texto puro, a 80 colunas e sem ANSI"
  - "o cabeçalho nomeando o milestone ABERTO do roadmap, ou dizendo que não há nenhum"
  - "a lista mostrando as fases pendentes quando o roadmap não declara ciclo aberto"
  - "o painel de fases cabendo em toda largura de 30 a 200, com coluna que cai sendo coluna nomeada"
  - "a fronteira de alinhamento em locale CJK, declarada por escrito ao lado da régua"
affects: [23-not-applicable-state, 25-measured-cleanup]

plans: ["01", "02", "03", "04", "05"]

requirements-completed: [PIPE-01, PIPE-02, PIPE-03, BOARD-04]

duration: 255min
completed: 2026-08-06
status: complete
---

# Phase 22: Non-TTY split and the machine contract Summary

**`--plain` fazia dois trabalhos incompatíveis: era o TSV que scripts consomem e
o fallback automático de quem não tem terminal. Esta fase separou os dois, com a
referência do "antes" gravada no primeiro plano e não no último — e no caminho
consertou o cabeçalho que anunciava um ciclo morto, a lista que escondia as
fases, e a tabela que exigia 90 colunas de um board de 50.**

## Os quatro critérios de sucesso, julgados um a um

### 1. `--plain` é byte a byte o que era, provado contra referência commitada — ATENDIDO

Duas referências, capturadas por escritores diferentes, com o mesmo md5
(`e98d3096656463236c2ed12a12be90e3`):

- `tests/fixtures/board-render/plain.txt`, commitada em `784483e` (plano 20-01) e
  sem um único commit desde;
- `tests/fixtures/machine-contract/nontty-pre-split.txt`, capturada no **plano
  22-01**, antes de uma linha de `cairn-status.py` se mover, do caminho **sem
  flag** — o que deixa de existir logo depois.

A redundância tem razão, e ela é o achado que justifica o plano 22-01 inteiro:
`plain.txt` mora sob `regenerate.sh`, que reescreve **os sete** arquivos numa
passada. Quem muda o render humano e regenera reescreve o contrato de máquina
junto, no meio de sete arquivos, dentro de um commit. Não é hipótese — os planos
22-03 e 22-04 rodaram o regenerador, de propósito, duas vezes. Nada regenera
`machine-contract/` junto com outra coisa, e o `capture.sh` recusa sobrescrever.

Quebra medida: `DONE` → `CLOSED` em `render_plain()` deixa vermelhos **os dois**
eixos e nenhum dos outros nove testes.

### 2. Sem TTY e sem flag, a lista agrupada em texto puro — ATENDIDO

```python
-    elif opts["plain"] or (opts["width"] is None and
-                           opts["color"] != "always" and
-                           not sys.stdout.isatty()):
+    elif opts["plain"]:
```

O comportamento mudou em três linhas apagadas. Nada foi inventado para o caminho
não-TTY: as duas diferenças entre pipe e terminal já estavam resolvidas em outro
lugar, e o split só as deixou visíveis — `Style._color_enabled()` termina em
`isatty(stdout)` (zero escape), e `terminal_cols()` cai em **80** (medido, a mesma
largura de um terminal sem `$COLUMNS`).

A razão original do acoplamento — pipes nunca receberem box-drawing — **morreu na
fase 21**, que tirou o último glifo de caixa do arquivo. Esta fase não desfez uma
decisão errada; recolheu uma decisão cuja premissa tinha acabado.

Superfície de risco, medida antes de mexer: **nenhum** script, hook, adapter,
comando ou skill do cairn chama `cairn-status` sem flag de saída. O único
consumidor do caminho sem flag em toda a árvore era `tests/cairn-status.bats:235`.

### 3. O cabeçalho nomeia o milestone aberto, e diz quando não há — ATENDIDO

`open_milestones` entra no modelo (aditivo, **lista** e não escalar, para nunca
escolher em silêncio entre dois ciclos abertos), e `milestone_label()` vira a
grafia única que o rodapé, o `--brief` e o cabeçalho HTML leem — no espírito de
`lease_line_text()`. A fonte é a marca `🚧` da linha do próprio ROADMAP, a mesma
que `phase_groups()` usa desde a fase 20.

O teste do critério arquiva `🚧 v1.1` → `✅ v1.1` e afirma que o board não cita
nem `v1.1` nem `v1.0`, **com `STATE.md` conferido intacto apontando para v1.0** —
sem essa conferência o teste não distinguiria "o cabeçalho trocou de fonte" de "a
fixture mudou de ideia".

### 4. O teste do acoplamento reescrito em duas asserções, nunca removido — ATENDIDO

`tests/cairn-status.bats` tinha **55** `@test` e tem **57**: nenhum apagado, um
partido em dois, um reescrito. A asserção `[ "$output" = "$piped" ]` foi
substituída por duas afirmações **positivas**, uma por superfície — não pela sua
negação. Uma igualdade diz que as duas superfícies são a mesma sem dizer o que
nenhuma delas **é**.

Quebra medida, com o acoplamento religado no fonte: `1..56`, **2** vermelhos, e
são os dois que descrevem a separação. O teste do `--plain` seguiu verde, como
tem de seguir.

## Os três defeitos herdados: dois consertados, um decidido

| issue | veredito | o que ficou |
| --- | --- | --- |
| `CairnGo-uz6` | **consertado** | sem ciclo aberto, a lista mostra as fases pendentes sob um grupo que diz isso por nome |
| `CairnGo-cdx` | **consertado** | o painel inteiro cabe de 30 a 200 colunas; coluna que cai é coluna nomeada |
| `CairnGo-hbo` | **decidido, sem código** | o alinhamento é garantido em locale ocidental e **não** em CJK, escrito no docstring de `char_width()` |

**`uz6` era pior do que a issue dizia.** Reproduzido: sem `## Milestones`, três
superfícies davam duas respostas na mesma tela (`(no open work)` na lista,
`phase 1/1 Alpha` no rodapé, `PENDING PHASES 1` na tabela). O conserto emite um
grupo com as fases **pendentes** — exatamente o conjunto que a tabela conta, que
é o que faz as três concordarem.

Uma decisão de projeto se validou contra um teste que já existia: a condição é
"nenhum ciclo aberto", nunca "nenhum grupo emitido". Com a segunda, a *variante B*
de `cairn-group-model.bats` (ciclo aberto que só nomeia fases inexistentes) teria
ficado vermelha; com a correta, passou **sem uma linha de mudança**.

**`cdx` virou problema desta fase, não só herança.** O piso era
`76 + num_w − 1 + len(next)` — 90 no fixture, 92 neste repositório — e o `PIPE-02`
passou a mandar o não-TTY por essa tabela **a 80 colunas**. `panel_columns()`
encolhe primeiro e derruba depois, com um piso por coluna que **nunca fica menor
que o próprio cabeçalho**: uma coluna cujo título sai `issu…` mente sobre estar
ali; uma ausente e nomeada diz que saiu.

**`hbo` mudou de conserto para fronteira porque a medição mandou.** 53 glifos
`east_asian_width=A` num render a 100 colunas, dos quais **12 são letras
acentuadas da prosa portuguesa**. Trocar `—` por `-` e `…` por `...` removeria 36
e não resolveria nada. E resolver `A` pelo ambiente exigiria ler `LANG`/`LC_CTYPE`
e adivinhar o que só o emulador sabe — o que este arquivo já recusou uma vez, na
escolha dos símbolos da fase 21: *"inventar essa leitura seria inventar uma fonte
de verdade"*. A fronteira está escrita ao lado da régua que a produz.

## As oito referências, plano a plano

Cada regeneração teve previsão escrita **antes** e conferência por `cmp` contra
cópias em `/tmp` — nunca `git diff`, porque uma área de stage errada pode fabricar
um "não mudou".

| arquivo | 22-03 | 22-04 | por quê |
| --- | --- | --- | --- |
| `w100`, `ascii100`, `maxrows` | rodapé: `v1.0` → `v1.1 Surface` | imóvel | a 100 colunas nenhuma coluna encolhe ou cai |
| `brief` | mesma troca, na 1ª das 3 linhas | imóvel | não tem tabela |
| `w50` | rodapé | a tabela deixa de estourar | `phase` era um `…` sozinho; virou `Phase mo…` e 5 colunas nomeadas |
| `w38` | rodapé | a tabela cede o lugar | `table needs 44 columns`; o `PURPOSE` continua |
| `plain` | **imóvel** | **imóvel** | o `PIPE-01`, conferido em três planos |
| `nontty-pre-split` | **imóvel** | **imóvel** | idem, no segundo eixo |

Nenhuma linha se moveu contra a previsão, nas duas regenerações.

## Os achados que a suíte verde não teria contado

**Um teste que ia virar tautologia em silêncio.**
`--color=always piped without --width opts into the board renderer` afirmava que a
flag **força** o renderizador. No instante em que o pipe passou a renderizar o
board por padrão, todas as suas asserções passariam com a flag removida por
inteiro. Ele ficaria verde para sempre, parecendo cobertura. Reescrito como
`piping decides color, not the renderer`, e é um dos dois vermelhos da religação.

**Um teste que pinava a própria contradição.**
`GSD repo without .beads degrades to a GSD-only board` afirmava
`grep -qF '(no open work)'` enquanto o mesmo output imprimia `PENDING PHASES 1`
logo abaixo. Zero *issues* era verdade; "nenhum trabalho aberto" não era.

**Dois estouros vizinhos, mesmo defeito, achados pela varredura.** O `PURPOSE`
quebrava em `max(30, …)` — o piso atropelava a largura pedida — e depois indentava
por `num_w + 4`, produzindo linhas de 36 células num board de 30. E a linha de
conflitos (52 células) saía sem quebra. Nenhum dos dois estava na issue.

**Uma tabulação final perdida ao colar.** A conferência por script do exemplo de
`--plain` na documentação acusou divergência: as linhas de issue terminam em
**tab** (o campo `EXTRA` vazio), e colar o bloco a perdeu. Contagem de campos fixa
é o que faz `cut -f4` significar a mesma coisa em toda linha. Restaurada e
documentada. Uma leitura a olho teria aprovado.

**Uma mutação que não mediu nada.** A primeira tentativa de quebrar o conserto do
`cdx` fez a tabela sumir em vez de estourar; a varredura passou verde e só o
segundo teste reprovou. Uma mutação que reprova pelo motivo errado não é medição —
a segunda desligou as duas coisas e reproduziu o defeito (piso de 94, vermelho de
30 a 90, verde a partir de 100, a faixa prevista).

## A tensão registrada, e as duas issues novas

`--plain` continua publicando o milestone do `STATE.md`, que pode ser o ciclo
arquivado, enquanto as três superfícies humanas nomeiam o aberto. Isso é uma
assimetria real e **deliberada**: o `PIPE-01` congela o TSV, e as duas referências
provam que ele não se moveu. Consertar exige decidir sobre o contrato externo
(versionar o formato, ou acrescentar linha — que também move bytes), o que é maior
que um conserto de fase.

| issue | o que é | procedência |
| --- | --- | --- |
| `CairnGo-fp7` | a linha `MILESTONE` do `--plain` segue vindo do `STATE.md` | `discovered-from: CairnGo-fgu` |
| `CairnGo-7yw` | a linha de contagens estoura abaixo de ~40 colunas com números de dois dígitos | `discovered-from: CairnGo-cdx` |

A `7yw` é a **única** linha do board que ainda excede a largura pedida. Mora em
`render_groups()`, outro renderizador, e no fixture cabe (38 células exatas). Não
é o transbordo que o `BOARD-03` permite — ali há quatro espaços onde quebrar.

## A entrega, por plano

| plano | entrega | commits |
| --- | --- | --- |
| `22-01` | a referência do contrato de máquina, `capture.sh` write-once, 2 testes | 2 |
| `22-02` | o split; o teste do acoplamento partido em dois; o teste tautológico reescrito | 2 |
| `22-03` | `open_milestones` + `milestone_label()`; o grupo sem ciclo aberto; 6 referências | 2 |
| `22-04` | `panel_columns()`; 2 estouros vizinhos; a fronteira do `hbo`; 2 referências | 2 |
| `22-05` | a página reescrita, com 4 exemplos capturados e conferidos | 2 |

Mais o commit dos planos: **11** no total.

## A medição final, com a árvore parada

```
INICIO 2026-08-06T20:20:47Z   HEAD 6b4bc9c
1..97
ok=97  not_ok=0
FIM    2026-08-06T20:29:29Z   8:42 de relógio, bats -j 4
```

97 `ok`, **0** `not ok`, e o plano `1..97` conferido contra a soma contada sobre o
**log inteiro** — que é a conferência obrigatória porque um run morto imprime
`1..N` e executa zero testes.

Os 97 são os quatro arquivos que a fase tocou:

| arquivo | antes | depois |
| --- | --- | --- |
| `cairn-status.bats` | 55 | **57** |
| `cairn-grouped-board.bats` | 11 | **14** |
| `cairn-group-model.bats` | 14 | **15** |
| `cairn-board-invariance.bats` | 9 | **11** |

## O que esta fase recusou fazer

**Não tocou `cairn-doctor.py`.** As fases 23 e 24 colidiram nele num auto-merge
silencioso; esta fase não tinha motivo para ir lá, e não foi.

**Não regenerou referência para um teste passar.** As oito foram conferidas por
`cmp` em cada plano que mexeu no render, com previsão escrita antes, e os dois
diffs foram lidos linha a linha e transcritos nos SUMMARY.

**Não usou `git checkout -- <arquivo>` uma vez.** As cinco quebras medidas
(mutação em `render_plain`, religação do acoplamento, `meta_parts` de volta à
fonte antiga, grupo sem-milestone removido, soma incondicional de colunas) foram
todas por backup `cp` e restauro da cópia.

**Não rodou a suíte inteira.** Por instrução direta: rodou os quatro arquivos que
tocou, com o TAP em arquivo, lido do arquivo e nunca da cauda. A suíte completa é
sua.

**Não escriturou `STATE.md`, `ROADMAP.md` nem `REQUIREMENTS.md`**, e não rodou
ferramenta de escrituração do `gsd-tools`. Conferido:
`git diff --quiet 0e67930 HEAD -- .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/STATE.md` → **limpo**.
O fechamento é seu, com `cairn-bookkeep close 22 --apply`.

## Self-Check: PASSED

- os 5 `22-NN-PLAN.md` e os 5 `22-NN-SUMMARY.md` — FOUND
- `tests/fixtures/machine-contract/` (captura + `capture.sh`) — FOUND
- 11 commits `5e6aea6..6b4bc9c` — FOUND
- 7 issues da fase fechadas, 2 novas abertas (`CairnGo-fp7`, `CairnGo-7yw`) — FOUND
- escrituração intocada — CONFERIDO
