---
phase: 22-non-tty-split-and-the-machine-contract
verified: 2026-08-06T21:49:31Z
status: passed
score: 4/4 critérios verificados, 4/4 requisitos entregues
behavior_unverified: 0
behavior_unverified_items: []
human_verification: []
overrides_applied: 0
gaps: []
---

# Phase 22: Non-TTY split and the machine contract — Relatório de verificação

**Goal da fase:** `--plain` fazia dois trabalhos incompatíveis — era o TSV que
scripts consomem **e** o fallback automático de não-TTY. Foi assim que o formato
de máquina apareceu na tela de quem só queria olhar o board. Esta fase separa os
dois e conserta o cabeçalho que continuava anunciando o último milestone
arquivado como se fosse o atual.

**Verificado em:** `HEAD=5f3a815`, árvore sem mudança de código pendente
**Status:** passed
**Re-verificação:** Não — verificação inicial (não existia `22-VERIFICATION.md`)

## Método

Goal-backward e adversarial. Parti dos quatro critérios do ROADMAP § Phase 22 e,
para cada um, procurei a forma de ele estar **verde e vazio**: uma referência
capturada tarde demais, um teste apagado em vez de reescrito, um conserto que
existe no SUMMARY e não na árvore, uma declaração escrita onde ninguém a acha.

Onde o SUMMARY afirmou um número, refiz a medição por outro caminho: cronologia
por `git log`/`git merge-base --is-ancestor` em vez de leitura do texto, contagem
de `@test` por `grep -c` sobre as duas versões do arquivo, md5 e largura de coluna
medidos no repositório real, e a recusa do `capture.sh` executada de verdade.

**Rodei em segundo plano, lendo o log de arquivo, exatamente os quatro `.bats`
que a fase tocou — não rodei `tests/` inteiro.** A contagem abaixo é sobre o log
inteiro, não sobre a cauda, e a marca `FIM` chegou ao arquivo.

| campo | valor |
| --- | --- |
| comando | `bash cairn/scripts/cairn-test.sh --jobs 3 tests/cairn-status.bats tests/cairn-grouped-board.bats tests/cairn-group-model.bats tests/cairn-board-invariance.bats` |
| plano anunciado | `1..97` |
| `ok` contados no log inteiro | **97** |
| `not ok` | **0** |
| `# skip` | 0 |
| maior número de teste visto | 97 |
| exit | 0 |
| relógio | `INICIO 21:38:16Z` → `FIM 21:48:50Z` (10m34s) |

O plano anunciado e a soma contada coincidem — a conferência que separa um run
real de um run morto, que imprime `1..N` e executa zero.

## Goal Achievement

### Verdades observáveis

| # | Verdade (critério do ROADMAP) | Status | Evidência |
| --- | --- | --- | --- |
| 1 | `--plain` é byte a byte o que era, contra referência commitada | ✓ VERIFICADO | duas referências, ambas **ancestrais** do commit que mudou o comportamento, com zero diff desde a entrada; `ok 92` e `ok 93` |
| 2 | Sem TTY e sem flag, a lista agrupada em texto puro | ✓ VERIFICADO | medido por mim no repositório real: 0 bytes ESC, 0 glifos de caixa, maior linha 80 células; `ok 8` |
| 3 | O cabeçalho nomeia o milestone aberto, e diz quando não há | ✓ VERIFICADO | `milestone_label()` lê `open_milestones` (marca `🚧` do ROADMAP), nunca `STATE.md`; `ok 7` arquiva `v1.1` e prova que nem ele nem o `v1.0` do `STATE.md` aparecem |
| 4 | O teste do acoplamento reescrito em duas asserções, nunca deletado | ✓ VERIFICADO | 55 → 57 `@test`, diff de nomes mostra um partido em dois e **nenhum removido**; `ok 8` e `ok 9` |

**Score:** 4/4 verdades verificadas (0 presentes com comportamento não exercido).

---

### Critério 1 — PIPE-01, e a armadilha da auto-referência

Este é o critério fácil de fingir: se a referência do "antes" tiver sido
capturada **depois** da mudança, o teste compara a saída nova consigo mesma e
fica verde para sempre. A checagem não é ler o SUMMARY, é ler a história.

**A cronologia, medida por `git`, não por texto:**

| arquivo | commit de entrada | é ancestral do split (`aaccea4`)? | diff desde a entrada |
| --- | --- | --- | --- |
| `tests/fixtures/board-render/plain.txt` | `784483e` — `test(20-01)` | **SIM** (`git merge-base --is-ancestor`) | **vazio** |
| `tests/fixtures/machine-contract/nontty-pre-split.txt` | `7770632` — `test(22-01)` | **SIM** | **vazio** |

O commit que mudou o comportamento é `aaccea4` — `feat(22-02): o não-TTY renderiza
o board, e --plain volta a ser só flag`. As duas referências entraram antes dele
e **não têm um único byte de diferença desde então** (`git diff --stat` vazio nos
dois casos, contra os respectivos commits de entrada). A referência não pode ter
sido ajustada para caber: ela é anterior ao que mede.

`nontty-pre-split.txt` é ainda mais forte que `plain.txt` porque foi capturada do
caminho **sem flag** — o caminho que deixou de existir. O teste
`diff_machine_against_reference()` roda `--plain` **hoje** contra os bytes que o
`cairn-status.sh` **sem flag nenhuma** imprimia em 2026-08-06. Não é o formato
comparado consigo mesmo; é uma superfície comparada com a outra, através do tempo.

Os dois arquivos têm o mesmo md5, conferido por mim:
`e98d3096656463236c2ed12a12be90e3`.

**A redundância tem razão e ela se sustenta.** `plain.txt` mora sob
`regenerate.sh`, que reescreve os sete arquivos numa passada — e os planos 22-03 e
22-04 rodaram esse regenerador. Conferido: dos sete, **seis** aparecem no diff da
fase (`w100`, `ascii100`, `maxrows`, `brief`, `w50`, `w38`); `plain.txt` **não
aparece**. O segundo eixo não é decorativo: nada regenera `machine-contract/`
junto com outra coisa.

**O write-once do `capture.sh`, executado e não lido:**

```
$ bash tests/fixtures/machine-contract/capture.sh
capture.sh: .../nontty-pre-split.txt already exists — refusing to overwrite.
exit=1     md5 antes = md5 depois = e98d3096656463236c2ed12a12be90e3
```

É esse guarda que impede a auto-referência de nascer no futuro: quem tentar
"consertar" um vermelho regenerando a referência é recusado, e a mensagem explica
por quê.

**A comparação está viva.** `diff_against_reference()` faz `run diff -u` sem
`|| true`, e é a **mesma função** que os testes positivos e os dois de liveness
usam — uma comparação viciada reprovaria os dois eixos de uma vez. Os dois
liveness passaram: `ok 95` (perturba o ROADMAP) e `ok 96` (perturba o
`milestone:` do `STATE.md`, que é o campo que `render_plain()` imprime verbatim,
fazendo a perturbação atravessar o caminho inteiro).

---

### Critério 2 — PIPE-02, medido no repositório real

O código diz o que precisa dizer. O despacho em `cairn-status.py:4005` é hoje
`elif opts["plain"]:` e nada mais; a condição antiga, conferida em
`git show 0e67930:cairn/scripts/cairn-status.py:3681-3683`, era:

```python
elif opts["plain"] or (opts["width"] is None and
                       opts["color"] != "always" and
                       not sys.stdout.isatty()):
```

**A medição do acoplamento, refeita à minha maneira.** No repositório real, hoje:

```
--plain  →  ba2afe62c616a5b1989c914d160c32a4
sem flag →  9c9e9589b9949638b0fde0e55bbcf8ae
```

Dois md5 diferentes. Antes da fase eram um só — é o que o teste que a fase
reescreveu afirmava literalmente (`[ "$output" = "$piped" ]`).

**O que o não-TTY entrega, medido e não afirmado:**

| propriedade | medido |
| --- | --- |
| sequências ANSI | **0** |
| glifos de box-drawing (`│ ─ ┌ └ ├`) | **0** |
| maior linha | **80 células** (largura de coluna real, `east_asian_width`) |
| conteúdo | contagens, grupo `v1.5 Legible State`, fases com símbolo de etapa, ids e títulos quebrados — legível |

Nada foi inventado para esse caminho: `Style._color_enabled()` já terminava em
`isatty(stdout)` e `terminal_cols()` já caía em 80. O split só deixou as duas
diferenças visíveis.

**A superfície de risco, varrida por mim.** Toda invocação de `cairn-status.sh`
na árvore carrega flag: `--json` (`autonomous.md`, `reconcile.md`, `doctor.bats`,
`phase-model.bats`, `phase-card.bats`, `corroboration.bats`), `--width 100`
(`commands/status.md`), `--html`. Nenhum consumidor sem flag fora dos testes da
própria fase — a afirmação do SUMMARY se confirma por varredura independente.

---

### Critério 3 — BOARD-04

`milestone_label()` (`cairn-status.py:2874`) lê `data["open_milestones"]`, que vem
da marca `🚧` da linha do próprio ROADMAP — a mesma fonte que `phase_groups()` usa
desde a fase 20 — e devolve `no open milestone` em palavras quando a lista está
vazia. É lista e não escalar, com ` +N` quando há mais de um ciclo aberto: nunca
escolhe em silêncio.

Três superfícies humanas leem essa grafia única e conferi as três:
`meta_parts()` (rodapé, linha 2458), `render_brief()` (via `meta_parts`, linha
2966) e o cabeçalho HTML (linha 3485). **`render_plain()` não usa `meta_parts` —
conferido lendo a função inteira** — e segue publicando `data["milestone"]`, que é
exatamente o que o PIPE-01 exige que não se mova.

O teste do critério (`ok 7`) arquiva `🚧 v1.1` → `✅ v1.1` no ROADMAP e afirma
três coisas, não uma: que `v1.1 Surface` sumiu, que `no open milestone` apareceu,
e que **não caiu no `v1.0` do `STATE.md`** — com o `STATE.md` conferido intacto no
meio do teste. Sem essa terceira asserção o teste não distinguiria "o cabeçalho
trocou de fonte" de "a fixture mudou de ideia". Ele também prova que as fases
pendentes continuam na lista: BOARD-04 tira um nome, nunca o trabalho.

Medido no repositório real: o cabeçalho imprime `v1.5 Legible State`, que é o
único `🚧` do ROADMAP.

`--json` ganhou `open_milestones` de forma aditiva; a asserção **exaustiva** de
chaves de topo (`cairn-status.bats:1408`) lista 16 chaves em ordem e passou.

---

### Critério 4 — PIPE-03, o teste que não podia sumir

O acoplamento estava em `tests/cairn-status.bats:246-251` — conferido em
`git show 0e67930`, o comentário na 246 e o `[ "$output" = "$piped" ]` na 250,
exatamente onde o `22-CONTEXT.md` disse (o ROADMAP ainda cita a linha 208, que a
fase 21 tornou obsoleta).

**Contagem de `@test`, medida nas duas versões do arquivo:**

| arquivo | em `0e67930` | em `HEAD` |
| --- | --- | --- |
| `cairn-status.bats` | 55 | **57** |
| `cairn-grouped-board.bats` | 11 | **14** |
| `cairn-group-model.bats` | 14 | **15** |
| `cairn-board-invariance.bats` | 9 | **11** |
| **soma** | 89 | **97** |

O `diff` dos **nomes** dos testes é o que fecha a questão, porque contagem sobe
também quando se apaga um e acrescenta três:

```
- non-TTY without flags defaults to --plain: tabs, no box, no escapes
+ archiving the open milestone stops the board from naming it
+ non-TTY without flags renders the grouped list in plain text
+ --plain is the machine contract: tab-separated rows and meta rows
- --color=always piped without --width opts into the board renderer
+ piping decides color, not the renderer
```

Uma remoção e uma reescrita, ambas com substituto nomeado. Nos outros três
arquivos o diff é puramente aditivo, salvo um rename em `cairn-group-model.bats`
(`variant A: ... means no milestone group` → `... yields one unnamed group, never
the archived name`), que é a inversão que o conserto do `uz6` exigia. **Nenhum
`@test` desapareceu sem substituto em nenhum dos quatro arquivos.**

As duas asserções que substituem a igualdade são **positivas**, uma por
superfície, e cada uma diz o que sua superfície **é** — a lista agrupada com
símbolo de etapa e id de um lado, o TSV com `READY\t…` e as meta-linhas do outro.
Uma igualdade diz que as duas são a mesma sem dizer o que nenhuma delas é.

O bloco de comentário em `tests/cairn-status.bats:279-295` registra a data, o
requisito, o md5 do acoplamento e a razão de a igualdade ter saído — o teste conta
a própria história para quem chegar depois.

## Cobertura dos requisitos

| Requisito | Issue bd | Status | Evidência |
| --- | --- | --- | --- |
| BOARD-04 | `CairnGo-fgu` | ✓ ENTREGUE | `milestone_label()` + `open_milestones`; `ok 7` |
| PIPE-01 | `CairnGo-ca5` | ✓ ENTREGUE | duas referências pré-mudança, imóveis; `ok 92`, `ok 93`, `ok 96` |
| PIPE-02 | `CairnGo-vpc` | ✓ ENTREGUE | despacho reduzido a `elif opts["plain"]`; medição própria; `ok 8` |
| PIPE-03 | `CairnGo-5yo` | ✓ ENTREGUE | 55 → 57, nada apagado; `ok 8`, `ok 9` |

Nenhum requisito órfão: o `22-BEADS-MAP.md` mapeia os quatro e o `REQUIREMENTS.md`
marca os quatro `[x]`.

## Os três defeitos herdados

| issue | estado no bd | verificado |
| --- | --- | --- |
| `CairnGo-uz6` | closed | ✓ código em `phase_groups()` (`cairn-status.py:1678`), grupo com `key: None` e rótulo `No open milestone`; `ok 60`, `ok 79`, `ok 80`, `ok 81` |
| `CairnGo-cdx` | closed | ✓ `panel_columns()` (`cairn-status.py:2533`), encolhe-então-derruba; medido por mim de 30 a 200 colunas; `ok 58`, `ok 59` |
| `CairnGo-hbo` | closed | ✓ decidido sem código, e a declaração **tem endereço** — dois |

**A medição de largura que refiz**, no repositório real, com largura de coluna e
não `len()`:

| `--width` | maior linha |
| --- | --- |
| 30 | 40 |
| 38 | 40 |
| 40 / 50 / 60 / 70 / 80 / 90 / 100 / 120 | exatamente a pedida |
| 200 | 198 |

A única linha que excede é a de contagens
(`ready 26 · doing 0 · blocked 0 · done 96`, 40 células), e só abaixo de 40
colunas — isolada por mim linha a linha. É exatamente `CairnGo-7yw`, aberta pela
fase com `discovered-from: CairnGo-cdx`. O painel `PENDING PHASES`, que é o que o
`cdx` acusava, cabe em toda a faixa.

**Sobre o `hbo`: a declaração está escrita, e em dois lugares onde alguém a
encontra.**

1. `cairn/scripts/cairn-status.py:1949-1982` — docstring de `char_width()`, a
   própria régua: *"The board's column alignment is guaranteed in a WESTERN
   locale. It is NOT guaranteed in a CJK locale."* Com a medição junto (53
   glifos `east_asian_width=A`, 9 distintos, dos quais **12 são letras acentuadas
   da prosa portuguesa**) e o argumento de por que trocar `—` por `-` removeria 36
   dos 53 e não resolveria nada.
2. `cairn/docs/commands/status.md:151-156` — a página de referência do comando,
   logo abaixo da tabela de flags e da precedência de cor, sob o título
   **"Alignment and locale"**, com ponteiro para a docstring.

Não é promessa sem endereço: é a mesma frase nos dois lugares que um leitor
consultaria, um deles voltado ao usuário. A alternativa recusada (resolver `A`
lendo `LANG`/`LC_CTYPE`) está registrada com a razão — o arquivo já recusou essa
leitura uma vez, na escolha dos símbolos da fase 21.

## Varredura de anti-padrões

Sete arquivos de código/doc/teste alterados pela fase, varridos por
`TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER`: **zero ocorrências**. Nenhum marcador de
débito sem referência, nenhum stub, nenhuma função vazia.

`.beads/interactions.jsonl` e os seis fixtures regenerados completam o diff; a
escrituração (`ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md`) está intocada entre
`0e67930` e `6b4bc9c` — conferido com `git diff --quiet`, saiu limpo. O que move
esses três arquivos é o commit de fechamento `5f3a815`, do `cairn-bookkeep`, que é
o passo do usuário.

## Riscos residuais que não são lacunas

**A fase rodou quatro dos `.bats` da árvore, e as mudanças dela são visíveis a
outros arquivos.** Varri estaticamente as quatro superfícies alteradas contra os
outros arquivos de teste e não achei asserção que elas quebrem:

- caminho sem flag: nenhuma invocação fora dos quatro arquivos;
- segmento de milestone no rodapé/`--brief`/HTML: `--brief` não é usado fora dos
  quatro; os `--html` de fora afirmam exit code e existência de arquivo, não o
  `<span class="m">`; `cairn-phase-model.bats:118-120` afirma
  `phases[].milestone` do `--json`, campo que a fase não tocou;
- `(no open work)`: as 10 ocorrências vivem todas nos quatro arquivos rodados;
- largura do painel: `cairn-tracker-card.bats:405-418` roda `--width` de 38 a 200
  mas **filtra explicitamente** a tabela `PENDING PHASES` e a linha de contagens,
  registrando por escrito que ambas transbordavam; as mudanças do `cdx` só
  estreitam linhas, então esse teste só pode ficar mais verde.

Isso não é certeza de suíte inteira — é a razão pela qual está escrito aqui em vez
de virar `passed` silencioso. A suíte completa é do usuário.

**A assimetria deliberada do `--plain`.** A linha `MILESTONE` do TSV continua vindo
do `STATE.md`, que pode ser o ciclo arquivado, enquanto as três superfícies humanas
nomeiam o aberto. É consequência direta do PIPE-01 congelar o contrato externo, está
escrita no docstring de `milestone_label()` e virou `CairnGo-fp7` (aberta,
`discovered-from: CairnGo-fgu`). Consertar exige decidir sobre versionar o formato
— maior que um conserto de fase.

## Divergências de documentação encontradas

Nenhuma delas move a agulha, e nenhuma virou lacuna:

- **O ROADMAP cita `tests/cairn-status.bats:208`** no critério 4; o acoplamento
  estava de fato em 246-251 desde a fase 21. O `22-CONTEXT.md` já corrigiu o
  endereço e a fase trabalhou sobre o correto.
- **O `22-CONTEXT.md` diz "51 glifos de largura ambígua"** enquanto sua própria
  tabela soma 53 (28+8+4+1+12). A fase adotou 53, que é o número aritmeticamente
  consistente, e o repetiu na docstring e na página. A correção é do lado certo.

## O que eu não consegui verificar

- **As cinco quebras medidas pelo executor** (mutação em `render_plain`, religação
  do acoplamento, `meta_parts` de volta à fonte antiga, grupo sem-milestone
  removido, soma incondicional de colunas). Não as reproduzi porque mutar
  `cairn-status.py` durante um run de 10 minutos envenenaria o próprio run, e
  havia outras verificações em paralelo nesta máquina. **Não é ponto cego:** os
  dois testes de liveness que a fase entregou (`ok 95`, `ok 96`) provam
  mecanicamente, dentro da suíte, que as duas comparações de referência reprovam
  quando a entrada muda — que é a propriedade que aquelas mutações mediram à mão.
- **O comportamento em terminal real (TTY).** Toda medição aqui é por pipe, que é
  o que a fase existe para consertar. A cor e a largura do TTY seguem decididas por
  `Style._color_enabled()` e `terminal_cols()`, código que a fase não alterou.
- **A linha de conflitos de 52 células** que o SUMMARY diz ter consertado: não
  reproduzi o estado de conflito necessário para vê-la. Não é critério da fase.

## Veredito

**passed.** Os quatro critérios do ROADMAP têm evidência de comportamento, não só
de presença: o eixo do PIPE-01 é provado por duas referências cuja anterioridade
ao commit da mudança está registrada na história do git, não no SUMMARY; o PIPE-02
foi medido por mim no repositório real; o BOARD-04 tem um teste que descarta as
duas fontes erradas; e o PIPE-03 se verifica por contagem e por diff de nomes, que
é o que distingue "reescrito" de "apagado e substituído por outra coisa".

Os quatro requisitos estão entregues e suas issues fechadas. Os três defeitos
herdados foram resolvidos — dois com código medido, um com uma fronteira escrita
em dois endereços legítimos. As duas issues novas (`CairnGo-fp7`, `CairnGo-7yw`)
registram o que ficou, com procedência, e nenhuma delas é critério desta fase.

---

_Verificado: 2026-08-06T21:49:31Z_
_Verificador: Claude (gsd-verifier)_
