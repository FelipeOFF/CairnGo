---
phase: 36-workflows-steps-e-agentes-falam-bd
plan: 07
subsystem: execute-phase-executor-e-o-fecho-da-fase
tags: [adapt-04, adapt-02, node-sobrevive, escritor-unico, familia-d, completude-dois-sentidos, assercao-fraca, d-02]
requires:
  - onda zero do preâmbulo fechada (36-01) — os 34 blocos resolvem o binário do repo
  - oráculo semântico de quatro famílias com tabela de adaptados, coluna de bytes e tabela de pendentes (36-03/04/05/06)
  - o motor de JSON escolhido no 36-05 (`jq`) para o helper de leitura de campo do plan-phase
  - os dois sítios de node do gsd-verifier decididos por escrito no 36-06
provides:
  - execute-phase adaptado — os cinco sítios de fato do arquivo raiz zerados nas quatro famílias
  - o bloco do escritor único da onda sobrevive com o motivo trocado, e as CINCO cópias da instrução contam a mesma história
  - node zerado no que é infra do GSD: 6 sítios fechados (4 no raiz, 2 no fragment de isolamento), com equivalência medida em 38 casos
  - o agente executor adaptado — 7 sítios, dos quais o oráculo via 1
  - a tabela do oráculo FECHADA: 31 → 66 caminhos, com teste de completude dois-sentidos derivado do disco
  - a lacuna de D-02 medida com número e registrada, mais duas divergências novas que a medição achou
  - a dívida herdada de `quick.md:617` fechada com medição, não com argumento
affects: [37, 38]
tech-stack:
  added: []
  patterns:
    [
      motivo de uma regra trocado sem trocar a regra — última-escrita-vence vira registro duplicado,
      troca de motor provada por tabela de equivalência sobre o comportamento e não sobre o texto,
      recusa explícita com quatro diagnósticos preservada através da troca de motor,
      escopo de teste derivado do DISCO por find e não de segunda lista à mão,
      completude dois-sentidos que desconta a tabela de pendentes para não a inutilizar,
      medir a própria medição — o grep que devolveu zero por dialeto e a correção com -F,
    ]
key-files:
  created:
    - .planning/phases/36-workflows-steps-e-agentes-falam-bd/36-07-SUMMARY.md
  modified:
    - cairn/gsd/gsd-core/workflows/execute-phase.md
    - cairn/gsd/gsd-core/workflows/execute-phase/steps/executor-isolation-dispatch.md
    - cairn/gsd/gsd-core/workflows/execute-phase/steps/codebase-drift-gate.md
    - cairn/gsd/gsd-core/workflows/quick.md
    - cairn/gsd/agents/gsd-executor.md
    - cairn/gsd/agents/gsd-plan-checker.md
    - cairn/gsd/agents/gsd-verifier.md
    - cairn/gsd-adaptations.json
    - tests/cairn-prompt-state.bats
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "o bloco do escritor único da onda mantém a REGRA e troca o MOTIVO: era última-escrita-vence num markdown compartilhado, é registro DUPLICADO num bd onde o merge não colapsa duas registrations. As instruções aos agentes passam a proibir REGISTRAR, não escrever — em cinco lugares, com a mesma força"
  - "a tabela do oráculo fecha em 66 caminhos e não nos 39 do plano: o escopo é o de D-02 (os 8 workflows COM seus fragments, e os 16 agentes), medido do disco por find. Os 42 fragments dão ZERO nas quatro famílias, então os 27 a mais custaram zero conversão e fecharam o buraco por onde um sítio nasceria num fragment sem preâmbulo"
  - "a onda 7 entra no registro de adaptações só para os arquivos cujos BYTES ela mudou (7), não para os oito que o plano manda: registrar 'foi conferido' como 'diverge de propósito' é a confusão que a onda 6 desarmou com a coluna de bytes"
  - "quick.md:617 FECHADO, não registrado: medido num repo de fixture com bd que nenhum verbo do caminho do quick escreve o markdown de estado. A justificativa da onda 4 citava readModifyWriteStateMd, que descreve o UPSTREAM"
  - "as 5 menções ao runtime antigo em arquivos que já carregavam preâmbulo foram corrigidas (prosa; o código abaixo de cada uma já chamava o verbo certo); a sexta, package-legitimacy, NÃO — ela exige decidir se o cairn implementa a checagem"
  - "a lista do que `phase.complete` faz passou a descrever o payload MEDIDO do binário da casa: metade do que a prosa prometia não acontece, e cada item tem aspect próprio em divergences.json"
metrics:
  duration: ~3h de sessão
  completed: 2026-08-12
status: complete
---

# Phase 36 Plan 07: execute-phase, o executor, e o fecho da fase Summary

**One-liner:** o arquivo mais caro do corpus chegou por último com o critério
pronto — e ainda assim o achado da onda não foi a conversão, foi a medição: o
`<verify>` da Task 3 dá **T=0 contra a árvore ANTES** de qualquer edição, ou
seja, teria declarado o agente executor verde com os **sete** sítios de pé, dos
quais o próprio oráculo de quatro famílias via **um**.

## A rota

Quatro commits.

| # | commit | o quê |
|---|---|---|
| 1 | `cde8f75` | execute-phase: os sítios de fato, o escritor único e a injeção no prompt |
| 2 | `1600fed` | o manifesto de onda sem node, e os dois sítios que o mapa omitia |
| 3 | `9bbc2a9` | o agente executor, a dívida do quick, e a tabela do oráculo fechada |
| 4 | `927ab93` | a lacuna de D-02 medida com número, e o runtime antigo remedido |

## O que foi medido, antes de tocar

### O `<verify>` do plano contra a árvore pré-conversão

Rodado **antes** de qualquer edição, cheque a cheque, nas duas tasks que têm
oráculo:

**Task 1 — `execute-phase.md`:**

```
<verify> do plano                  oráculo real (4 famílias)
A imperativa .... 0                A .... 0
C imperativa .... 3                C .... 4   :41 :323 :454 :807
B variável ...... 0                D .... 1   :750
commit c/ STATE . 3                            total: 5
```

O `<verify>` morde — mas vê **3 dos 5**. A metade imperativa da família C não
pega `:807` (`- [ ] STATE.md updated with position and decisions`, a forma
passiva) e nada nele pega `:750` (a injeção do caminho literal no prompt do
executor, a grafia que criou a família D).

**Task 3 — `agents/gsd-executor.md`:** aqui não é fraqueza parcial, é zero.

```
verify DO PLANO na cópia ANTES da conversão : T=0   <- daria VERDE
oráculo REAL (família C) na mesma cópia     : 1
sítios de estado que o arquivo de fato tinha: 7
```

Seis dos sete escapam por **grafia**, e vale listar porque é o mapa de como uma
métrica textual mente:

| linha | forma | por que escapa |
|---|---|---|
| `:19` | `update STATE.md` | família C exige `Update` maiúsculo |
| `:91` | `If STATE.md missing but .planning/ exists` | predicado de AUSÊNCIA — nenhuma família |
| `:430` | ``Update `STATE.md` with…`` | a regex quer o literal colado, as crases separam |
| `:733` | `update STATE.md using \`gsd-tools query\`` | minúsculo, e ainda cita o runtime antigo |
| `:788` | lista de arquivos do commit final | política de commit, não leitura |
| `:852` | `includes SUMMARY.md, STATE.md, ROADMAP.md` | idem |
| `:850` | `- [ ] STATE.md updated (…)` | **este** é o que a onda 6 declarou pendente |

A onda 6 estava certa sobre o que a métrica morde. O que ninguém tinha medido é
o que ela não morde.

**É a terceira onda seguida com essa mesma nota.** A 5 registrou contra si
mesma, a 6 registrou contra si mesma, e a 7 registra de novo. Não é acidente de
redação: um `<verify>` escrito no plano nasce da descrição do sítio, e a
descrição é sempre mais estreita que a árvore.

## Task 1 — execute-phase, os sítios de fato

Cinco sítios, zero depois. As conversões usaram os três padrões já exercitados
em seis arquivos; nenhum padrão novo, como o plano manda.

- **`:41`** (abertura) — `Read STATE.md before any operation` passa a mandar
  carregar pelo binário, com a frase que os outros workflows já usam.
- **`:152`** (predicado) — a forma fixada em `autonomous.md:104`: pergunta pelo
  **portador no bd**, e a falha nomeia `state.begin-phase`. O parágrafo que
  explica por que `state_exists` mantém o nome e muda de pergunta veio junto,
  igual ao de lá.
- **`:182`/`:190`/`:192`** (resume gate) — a derivação do plano corrente pelos
  commits **continua sendo a fonte de verdade**, e agora com o porquê escrito:
  git é independente de quem registrou o fato. "stale `STATE.md`" virou "um
  plano registrado que fica atrás dos commits".
- **`:323`/`:454`** (as duas prosas) — viraram os verbos que o arquivo já
  usava: `state.begin-phase` e `state.advance-plan`.
- **`:750`** (família D) — a injeção sai e entra a linha que `quick.md:314` e
  `verify-work.md:717` já carregam, na mesma posição da lista.
- **`:807`** (critério) — passa a falar de fato registrado, nomeando os verbos.

### O bloco do escritor único: a regra fica, o motivo troca

Era este o sítio delicado da onda. O texto original justifica a regra com
`last-merge-wins overwrites` num arquivo compartilhado. Com o bd dono do fato,
essa justificativa deixa de existir — e a regra continua valendo por outra
razão, mais difícil de ver:

> **A recorded state** is no longer a file at all: it is a fact in the bd, and a
> git merge cannot collapse two registrations into one the way it collapses two
> edits of a markdown. Two agents registering the same wave register it TWICE —
> an appended row, a second transition in the audit trail. The failure mode
> moved from silent overwrite to silent duplication, which is why the
> instruction to the worktree agents above forbids registering rather than
> forbids writing.

ROADMAP.md continua no outro balde, e o texto diz isso em voz alta: ainda é
arquivo, ainda é última-escrita-vence, inalterado.

**A instrução aparece em CINCO lugares, não três.** O plano cita três
(`:707`, `:721`, `:728`); a medição achou mais duas no fragment de isolamento
(`:126` e `:194`) e uma no agente executor. Todas contam a mesma história
agora — proíbem REGISTRAR, não escrever. Se contassem histórias diferentes, a
onda registraria duas vezes ou nenhuma, que é exatamente o que o bloco existe
para impedir.

### Os commits que paravam de carregar o arquivo de estado

Três (`:991`, `:1456`, `:1513`), mais o `git diff --quiet` que decide se há o
que commitar. O precedente é da onda 5, `plan-phase.md:1386`, e o motivo é o
mesmo: nada no caminho executado escreve esse markdown. ROADMAP e REQUIREMENTS
ficaram exatamente onde estavam — o bookkeep é o dono e esta onda não mudou
quem escreve neles.

### O que `phase.complete` de fato faz — medido no handler

Fora do escopo estrito de estado, mas ao lado do sítio `:1440` e impossível de
ignorar depois de medido. A prosa prometia seis coisas; o handler da casa
(`cairn-gsd-state.py:896-957`) faz duas:

| a prosa dizia | medido no payload |
|---|---|
| checkbox `[x]` **com data de completude** | checkbox sim, data não (`phase-complete-date-omitted`) |
| atualiza a tabela de Progress | não acontece |
| atualiza a contagem final de planos | `plans_executed` é **reportado**, não escrito |
| avança o estado para a próxima fase | sim — transiciona `phase`/`phase_status` no portador |
| atualiza rastreabilidade em REQUIREMENTS.md | `requirements_updated: false` sempre (`phase-complete-requirements-not-edited`) |
| varre dívida de verificação | `warnings: []` e `verification_stale_check_indeterminate: true` — **não implementado** |

O último é o que mais dói: o ramo de aviso logo abaixo nunca dispara, e um
`warnings` vazio parece "sem dívida". A prosa agora diz que não é. Três das
divergências já existiam em `divergences.json` desde antes; a camada prompt é
que nunca tinha sido alinhada a elas.

## Task 2 — o motor do manifesto, e os dois sítios que o mapa omitia

Seis sítios de node fechados. O motor é `jq`, o mesmo escolhido no plano 05 —
e o mesmo que este workflow já usava para ler os próprios bundles.

**A equivalência foi medida caso a caso contra o node que sai, 38 casos:**

| sítio | casos | resultado |
|---|---|---|
| `:674` escrita do manifesto | 4 | **byte-idênticos** por `cmp -s` — incluindo raiz vazia virando `null` e aspas no caminho |
| `:897` e `:919` leitura da raiz | 9 | iguais: json normal, campo `null`, campo ausente, string vazia, json inválido, arquivo vazio, raiz array, raiz `null`, arquivo ausente |
| `:925` listagem com recusa | 10 | 9 idênticos; 1 diverge |
| fragment `:96` harnessFlag | 7 | iguais, incluindo stdin vazio e flag `false` |
| fragment `:176` fail-closed | 8 | iguais — todo payload degradado segue FATAL |

**A única divergência, medida e declarada:** no manifesto com JSON inválido, os
dois recusam com exit 1, stdout vazio e o mesmo envelope
`ERROR: cannot read worktree manifest <p>: <razão>`. O que difere é a frase do
**parser** dentro do envelope (`Unexpected token 'a'…` contra
`Invalid numeric literal at line 1, column 4`). Trocar de motor troca o
diagnóstico do motor; a recusa, o código de saída e o silêncio no stdout são os
mesmos.

**A recusa continua sendo recusa.** Quatro diagnósticos distintos —
`WAVE_WORKTREE_MANIFEST is unset`, `manifest does not exist`, `manifest is
empty`, e o erro do parser — cada um com sua frase, e a linha `BLOCKED` de
fora. A forma nova é bash chato de propósito (um `if/elif` plano, sem malabarismo
de descritor): uma conversão que transformasse essa recusa em lista vazia
trocaria um erro alto pela perda silenciosa de todas as árvores da onda.

**Divergência deliberada, uma:** com um manifesto que é JSON válido mas de raiz
não-objeto (um array, por exemplo), o node devolvia lista vazia e **exit 0**; o
jq recusa. A conversão empurra esse caso para o lado da recusa de propósito — é
a mesma escolha que o resto do bloco faz.

**Os dois sítios do fragment** (`:96`, `:176`) são os que o mapa da fase omitia
e nenhum plano anterior citava, embora o gate desta task já os exigisse em zero.
Ambos parseiam a saída do **dispatcher**, não o manifesto, e por isso nunca
herdaram o tratamento dele.

### Os fragments medidos — e são NOVE, não sete

O plano fala em "os sete fragments" de `execute-phase/steps/`. O disco tem
**nove**: os sete com preâmbulo mais `regression-gate.md` e
`worktree-recovery-policy.md`, que não carregam bloco de runtime. Medidos pelas
quatro famílias:

| fragment | A | B | C | D | `node -e` |
|---|---|---|---|---|---|
| codebase-drift-gate | 0 | 0 | 0 | 0 | 0 |
| executor-isolation-dispatch | 0 | 0 | 0 | 0 | **2** → 0 |
| gap-closure-artifacts | 0 | 0 | 0 | 0 | 0 |
| partial-wave | 0 | 0 | 0 | 0 | 0 |
| per-plan-worktree-gate | 0 | 0 | 0 | 0 | 0 |
| post-merge-gate | 0 | 0 | 0 | 0 | 0 |
| regression-gate-run | 0 | 0 | 0 | 0 | 0 |
| regression-gate *(sem preâmbulo)* | 0 | 0 | 0 | 0 | 0 |
| worktree-recovery-policy *(sem preâmbulo)* | 0 | 0 | 0 | 0 | 0 |

E, ampliando para os **42 fragments** dos oito workflows: **A=0 B=0 C=0 D=0**.
Zero em todos. Publicado porque é o número que impede a próxima fase de reabrir
trabalho já feito — e porque foi ele que tornou barato fechar a tabela em 66.

### O saldo de node, remedido

```
$ grep -rn 'node -e' cairn/gsd/ | grep -v CAIRN_GSD   →  7
   2  agents/gsd-verifier.md
   2  gsd-core/references/checkpoints.md
   3  gsd-core/references/specless-probe-fallback.md
```

**14 no início da fase → 13 após o 36-05 → 7 agora.** Os 6 fechados aqui são
exatamente os que estavam em escopo e sem decisão. Os 7 remanescentes, cada um
com sua razão escrita:

- **2 no `gsd-verifier`** — decisão escrita na onda 6 e ao lado de cada sítio: o
  runtime ali é o do **projeto verificado**, não o do GSD.
- **5 em `references/`** — fora por D-02, agora registrados com arquivo e linha.

`grep -rl 'node -e' cairn/gsd/gsd-core/workflows/` está **vazio**.

## Task 3 — o executor, a dívida do quick, e o fecho

### O agente executor: 7 sítios, e as 3 menções ao runtime que a fase 37 mata

Além dos sete sítios de estado da tabela acima, o arquivo carregava três
menções ao runtime antigo — mesma classe do `gsd-planner.md:615` que a onda 6
consertou, num arquivo cujo preâmbulo já resolve o binário python desde a onda
zero:

- `:87` **"use `node` to invoke the CLI (not `npx`)"** — prosa contra a onda
  zero, na linha imediatamente acima de uma chamada `gsd_run`.
- `:733` e `:793` — `gsd-tools query` duas vezes.

E o bloco de `<state_updates>` ganhou a condição que faltava: **pular quando o
agente roda em árvore isolada**, com o motivo escrito. É a metade do executor da
mesma história do bloco do escritor único — sem ela, o agente adaptado
registraria o que a orquestração já registrou.

### `quick.md:617` — a dívida herdada, fechada com medição

A inconsistência que a onda 5 deixou aberta: a onda 4 manteve a linha citando
`readModifyWriteStateMd`, que descreve o **upstream**, enquanto o
`handle_quick_tasks_append` do cairn cria bead. Medido num repo de fixture com
`bd init`, rodando os dois verbos do caminho de verdade:

```
quick-tasks-append --task <t>                exit=0  {"ok":true,"variant":"bd-issue"}
query state.record-session --stopped-at <t>  exit=1  falha nomeada: sem portador

STATE.md antes : 283b5d7e2c56a1516b7c0c8bf31acf0f3dc279a2
STATE.md depois: 283b5d7e2c56a1516b7c0c8bf31acf0f3dc279a2
=> NENHUM dos verbos escreveu no arquivo de estado
```

O sha1 não muda. A linha era peso morto numa lista de commit, exatamente a
mesma classe das três irmãs de `execute-phase.md` que caíram na Task 1 —
**fechada**, não registrada. O cabeçalho do teste, que usava `quick.md:617`
como âncora da fronteira "commitar não é ler", passou a descrever a **forma** em
vez do sítio, com a medição escrita ao lado: a regra não depende de existir um
exemplar vivo dela, e o caso de falso-positivo continua exercitando a forma.

### A tabela do oráculo: 31 → 66, e o teste de completude

O escopo é o de D-02 — os 8 workflows raiz **com seus fragments** e os 16
agentes — e sai do **disco**, por `find`, não de uma segunda lista à mão. Uma
lista escrita à mão concordaria consigo mesma para sempre; derivada do disco, um
arquivo novo em qualquer um dos três diretórios reprova a suíte sozinho.

O plano descreve 39 (8 + 15 fragments **com preâmbulo** + 16). Ficaram 66:
carregar preâmbulo é consequência de chamar o dispatcher, não fronteira de
escopo, e como os 42 fragments medem zero, cobrir os 27 a mais **não custou uma
conversão sequer** e fechou o buraco por onde um sítio nasceria num fragment sem
preâmbulo sem ninguém ver.

A completude confere os dois sentidos, descontando a tabela de pendentes — sem
esse desconto a tabela de pendentes ficaria impossível de usar, e a onda
seguinte teria de escolher entre mentir e não declarar a pendência.

**A coluna de bytes foi conferida contra o cache pinado, arquivo a arquivo:**
34 editados, 32 intocados, **zero discordâncias** entre o que o registro afirma
e o que `cmp` mede. `PS_PENDING` ficou vazia — as duas linhas que ela carregava
morreram nos commits que fecharam os sítios, cada uma pelas duas forças (a
contagem caiu a zero e o caminho entrou em `PS_ADAPTED`).

## Quebras aplicadas, e qual asserção cada uma derrubou

Todas no **arquivo real**, restauradas de cópia (`cp`, nunca `git checkout`), e
com `diff` provando que o arquivo voltou idêntico.

| quebra | onde | derruba | evidência |
|---|---|---|---|
| reinjeta o sítio de leitura na forma anterior | `execute-phase.md` real | "nenhum sítio depende de node" | gate `raiz=1 arquivos=1` |
| **só prosa** citando o literal `node -e` | `execute-phase.md` real | a **mesma** asserção, sem node no caminho executado | gate `raiz=1 arquivos=1` |
| apaga a linha do executor da tabela | `cairn-prompt-state.bats` real | `completude` (teste 10) | 1 not-ok, nomeado |
| linha de tabela para caminho inexistente | `cairn-prompt-state.bats` real | **três** asserções independentes: adaptados, completude parcial e completude | 3 not-ok |
| arquivo do escopo fora das duas tabelas | árvore forjada | o sentido "escopo → tabela" | `no escopo e fora das duas tabelas: …/esquecido.md` |
| declarar esse mesmo como pendente | árvore forjada | prova que a pendência desconta **exatamente** ele e nada mais | volta a exit 0 |
| linha de tabela sem arquivo no disco | árvore forjada | o sentido inverso | `na tabela de adaptados e fora do escopo do disco: fantasma.md` |
| tabela consertada | árvore forjada | prova que as duas acima reprovavam pelos motivos nomeados | exit 0 pelo mesmo laço |

A segunda linha é um resultado sobre o próprio gate: **`grep -c 'node -e' == 0`
é textual e não distingue código de prosa.** A onda 5 já tinha medido isso
contra si mesma; medi de novo porque o gate desta onda é o mesmo, e porque
escrever "a forma anterior chamava node" no arquivo o derruba.

## Os números finais, e os dois comandos que os produzem

### O fecho da ferramenta canônica

**ANTES** — o fecho sobre o cache pinado:

```bash
python3 cairn/scripts/cairn-inventory.py closure --json
→ {"files": 171, "lines": 29957}
```

**DEPOIS** — o mesmo fecho sobre a árvore ADAPTADA, pelo seam de corpus local:

```bash
T=$(mktemp -d) && mkdir -p "$T/src" && cp -R cairn/gsd/. "$T/src"
git -C "$T/src" init -q && git -C "$T/src" add -A
git -C "$T/src" -c user.email=t@e -c user.name=t commit -qm m
git -C "$T/src" tag v1.10.0 && S=$(git -C "$T/src" rev-parse HEAD)
CLAUDE_PROJECT_DIR="$PWD" python3 cairn/scripts/cairn-inventory.py closure \
  --source "$T/src" --expect-commit "$S" --cache-dir "$T/cache" --json
→ {"files": 171, "lines": 30057}
```

**A razão do seam, escrita:** a ferramenta, como está, **sempre** resolve o
corpus para o cache (`resolve_corpus`) e mata com exit 6 se o HEAD do clone
divergir do commit da etiqueta (`ensure_corpus`). Ela não mede a árvore editada
sem esse desvio — é a armadilha INV-ESCOPO do mapa da fase. O seam já existe e
já é exercitado pelos testes da própria ferramenta
(`--source <repo git local> --expect-commit <sha> --cache-dir <tmp>`): copiar a
árvore para um repositório temporário com a **mesma etiqueta** e apontar a
ferramenta para ele com o commit esperado.

**171 arquivos nos dois lados; +100 linhas.** A fase inteira acrescentou cem
linhas de prosa e não removeu nem acrescentou um arquivo.

### O inventário de chamadas

```
                ANTES (cache)      DEPOIS (árvore adaptada)
workflows8      189 sítios          221   (+32)
agents           65 sítios           72   (+7)
```

E o delta é rastreável arquivo a arquivo (soma exata: 32 e 7):

```
execute-phase.md      48 → 57 (+9)     gsd-executor.md      17 → 19 (+2)
quick.md              17 → 23 (+6)     gsd-plan-checker.md  12 → 14 (+2)
autonomous.md         17 → 23 (+6)     gsd-verifier.md      10 → 12 (+2)
plan-phase.md         36 → 40 (+4)     gsd-planner.md        7 →  8 (+1)
verify-work.md        18 → 21 (+3)     …e 4 fragments com +1
```

**Este número SOBE por desenho, e é preciso dizer por quê:** `BROAD_RE` conta
invocações **textuais**, e a fase inteira consistiu em trocar prosa que nomeava
um arquivo por prosa que nomeia um verbo. Cada sítio convertido vira mais uma
ocorrência sob a métrica. Não são 39 chamadas executáveis novas.

**Um número do payload que NÃO é comparável, e não deve ser citado:**
`summary.corpus_calibration` dá 534 antes e 178 depois. A queda não é da fase —
é do seam: o cache é o **clone inteiro** do upstream, enquanto o seam contém só
os **171 arquivos vendorizados**. Medido para provar:
`grep -rE 'gsd_run query [a-z…]'` dá 645 no cache e 253 na árvore adaptada, e o
excedente do cache vive em arquivos que o cairn não vendoriza
(`settings-advanced.md`, `execute-plan.md`, `new-milestone.md`…). Os números
comparáveis são `closure.totals` e `workflows8`/`agents`, todos escopados pelos
mesmos conjuntos declarados nos dois lados.

## A lacuna de D-02, medida com número

Três entradas novas em `divergences.json` (**63 → 66**).

### 1. `references-fora-de-escopo-lacuna-medida-em-numero`

Medido sobre os 66 arquivos em escopo:

| o quê | medido |
|---|---|
| caminhos distintos de `references/` citados | **73** (todos existem; a árvore tem 80) |
| chamadas `gsd_run` nesses 73 | **17** |
| sítios de estado sob as quatro famílias | **2** |
| sítios de `node -e` | **5** |

Os dois sítios, nominalmente:

- `gsd-core/references/autonomous-smart-discuss.md:24` — `cat .planning/STATE.md`,
  família A. É o que o research já nomeava.
- `gsd-core/references/planner-antipatterns.md:83` — `@.planning/STATE.md`,
  família A. **Nenhum documento da fase citava este.** É a mesma classe do
  `gsd-planner.md:346` que a onda 6 converteu: uma `@`-referência que carrega o
  markdown no prompt de quem ler o arquivo.

Os 5 de node: `checkpoints.md:477` e `:512`;
`specless-probe-fallback.md:98`, `:111` e `:116`.

**O CONTEXT estimava "40 arquivos citados, 18 chamadas, ~33 sítios de estado".**
Medido: 73, 17 e 2. A diferença dos sítios não é erro de contagem, é de métrica:
nesses 73 há **8 linhas citando `STATE.md` por nome** e **34 citando
`.planning/`** — que é de onde os ~33 saíram. Sob as quatro famílias, são dois.

### 2. `runtime-antigo-citado-em-22-arquivos-33-mencoes`

**22 arquivos, 33 menções.** Quatro deles carregavam preâmbulo novo e portanto
estavam **em escopo**, com 7 menções. Cinco foram corrigidas aqui — em todas, a
prosa nomeava o runtime antigo enquanto o bloco de código imediatamente abaixo
já chamava `gsd_run` desde a onda 1:

```
agents/gsd-plan-checker.md:738, :761
agents/gsd-verifier.md:241, :317
execute-phase/steps/codebase-drift-gate.md:10-11
```

Os 18 sem preâmbulo (26 menções) são o alvo da fase 37: 6 em `commands/` e
`skills/`, 11 em `gsd-core/references/`, 1 em `gsd-core/templates/summary.md`.

**O mapa da fase citava QUATRO arquivos.** São 22.

### 3. `package-legitimacy-fora-do-universo-criterio-inatingivel`

`agents/gsd-phase-researcher.md:33` exige o `OK` de
`query package-legitimacy check` para marcar um pacote como
`[VERIFIED: npm registry]`. Medido: o verbo está fora do universo de 87, o
dispatcher responde exit 2 com stdout vazio, e portanto **o `OK` nunca vem** —
nenhum pacote pode receber `[VERIFIED]` por esse caminho.

Mesma classe de D-04, sem o agravante que justificou a exceção daquela vez: aqui
não há pipe que engula a falha em silêncio, a falha é alta, e o efeito é um
critério conservador demais em vez de um passo mudo. **Não corrigido** —
corrigir exige decidir se o cairn implementa a checagem de legitimidade, e isso
é decisão de fase.

## Premissas do plano que a medição contradisse

1. **O `<verify>` da Task 3 é asserção NULA, não fraca.** `T=0` contra a árvore
   antes da conversão: teria declarado o executor verde com os sete sítios de
   pé. O da Task 1 vê 3 de 5. Terceira onda seguida com a mesma nota.
2. **"os sete fragments" de `execute-phase/steps/`** — são **nove**. Os dois a
   mais não carregam preâmbulo e medem zero, mas "os sete" não é o que está no
   disco.
3. **"a tabela de adaptados fecha com os 15 fragments com preâmbulo"** — fecha
   com 42, porque o escopo de D-02 são os workflows **com** seus fragments e os
   27 a mais custam zero.
4. **"somar a onda 7 às entradas dos oito caminhos no registro"** — só **sete**
   arquivos tiveram bytes mudados por esta onda, e apenas dois dos oito
   (`execute-phase.md` e o fragment de isolamento). Registrar "foi conferido"
   como "diverge de propósito" é a confusão que a onda 6 desarmou com a coluna
   de bytes, e reprovaria os dois sentidos do oráculo de bytes.
5. **"as três linhas que proíbem o agente de tocar os arquivos compartilhados"**
   — são **cinco**: três em `execute-phase.md`, duas no fragment de isolamento,
   mais a do agente executor.
6. **"o agente executor tem 17 chamadas ao binário"** — 17 é o número do cache
   pela regra do mapa (linhas com `gsd_run`, descontada a do preâmbulo): o cache
   tem 18 linhas, 17 sem ela. Hoje são **20 linhas, 19 sem o preâmbulo** — as
   duas a mais são conversões desta onda (`state.update last_gate_trip` e a
   menção a `state.begin-phase`), e batem com o delta que o inventário reporta
   para o arquivo (17 → 19 sítios).
7. **A lacuna de D-02: "40 arquivos, 18 chamadas, ~33 sítios"** — 73, 17 e 2.
8. **"os 4 arquivos que citam o runtime antigo"** — 22 arquivos, 33 menções, e
   quatro deles estavam dentro do escopo desta fase.
9. **`corpus_calibration` não é comparável pelo seam** — a queda de 534 para 178
   é o clone inteiro contra os 171 vendorizados, não efeito da fase.
10. **Minha própria primeira medição das menções ao runtime estava errada.** O
    `grep` BSD trata `{}` como intervalo e devolvia **zero** para o marcador do
    preâmbulo, o que pôs quatro arquivos em escopo no balde "sem preâmbulo".
    Peguei cruzando com `grep -F`; a correção está na entrada de divergência.
    Registro porque é o mesmo defeito que este SUMMARY cobra dos outros: uma
    medição que ninguém mede.

## Desvios aplicados

- **[Rule 2 — funcionalidade crítica ausente]** `agents/gsd-plan-checker.md` e
  `agents/gsd-verifier.md` não estavam em `files_modified`. Quatro linhas de
  prosa nomeavam o runtime que a fase 37 remove, em arquivos que esta fase
  declara adaptados. Corrigidas; o código abaixo de cada uma já estava certo.
- **[Rule 2]** `cairn/gsd/gsd-core/workflows/quick.md` não estava em
  `files_modified`. É a dívida herdada que esta onda tinha ordem de medir e
  fechar-ou-registrar; medida, fechou.
- **[Rule 2]** a lista do que `phase.complete` faz foi reescrita contra o
  payload medido. Fica ao lado do sítio `:1440` que o plano manda converter, e
  metade dela era falsa. **Não** cria caminho novo de escrita em ROADMAP ou
  REQUIREMENTS — diz o contrário, que o verbo não escreve REQUIREMENTS.
- **[desvio de plano, medido]** a tabela fecha em 66 e não em 39; a onda 7 entra
  no registro para 7 arquivos e não para 8. Ambos justificados acima, e ambos na
  direção de asserção mais forte.
- **Escopo respeitado:** nenhuma escrita nova em ROADMAP ou REQUIREMENTS;
  nenhum caminho de artefato de fase convertido (planos, sumários, verificações,
  todos, mapas seguem documento); o cache não foi re-pinado nem a baseline
  regravada; `cairn/gsd/MANIFEST.json` intocado.

## As duas frases que a fase 37 não deve reabrir

**MANIFEST-PROSA.** Os totais de `cairn/gsd/MANIFEST.json` (`files: 171`,
`lines: 29957`) descrevem o fecho do **UPSTREAM**, derivados do cache, e
**continuam verdadeiros** depois da adaptação — é o que a ferramenta canônica
responde ao ser apontada para o cache, e foi medido de novo nesta onda. A
contagem da árvore adaptada (171 / 30057) mora aqui e no registro de
adaptações, não lá. Não corrija o MANIFEST: ele não está desatualizado, ele
descreve outra coisa.

**SHIM-HOMÔNIMO.** O campo `summary.shim_matches` do MANIFEST tem **oito**
entradas e é outro "shim": o par comando↔skill de cada um dos 8 workflows
(`autonomous → [commands/gsd/autonomous.md, skills/gsd-autonomous/SKILL.md]`).
Não tem relação com o bloco de preâmbulo de runtime, que são **34**. Quem
confundir os dois vai procurar 16 arquivos e achar 34.

## Testes

| suíte | resultado |
|---|---|
| `tests/cairn-prompt-state.bats` | **15/15** (13 antes + os 2 da completude) |
| `tests/cairn-vendoring.bats` | **26/26** — oráculo de bytes dois-sentidos e PORCELAIN invertido |
| `tests/cairn-preamble.bats` | verde |
| `tests/cairn-gsd.bats` | verde |
| `tests/cairn-command-surfaces.bats` | verde |
| **prompt-state + vendoring + preamble + cairn-gsd** | **144 ok / 0 not ok / exit 0** |
| **confirmação pós-commit** (prompt-state + vendoring + preamble + command-surfaces) | **68 ok / 0 not ok / exit 0** |

Comando: `bash cairn/scripts/cairn-test.sh --jobs 8 tests/<arquivo>.bats`, com a
saída redirecionada para arquivo (um `| tail` devolveria o exit do `tail`).

**A suíte completa NÃO foi rodada** — passa de uma hora em série, e a instrução
desta onda é rodar só os arquivos do plano e deixar o resto para a CI. O
`<verify>` da Task 3 pede `bats tests/`; fica como o único cheque do plano não
executado, deliberadamente e por instrução.

O cache do clone **existe** nesta árvore e nenhum teste de `cairn-vendoring.bats`
skipa aqui: o verde do oráculo de bytes dois-sentidos é prova, não silêncio.

## Estado do bd

**`ADAPT-04: CairnGo-73j4`** e **`ADAPT-02: CairnGo-0yzd`** reclamadas
(`bd update --claim`) e fechadas, com os critérios medidos e não presumidos —
ser a última onda não fecha issue.

- **ADAPT-04** ("execute-phase adaptado por último, com os sítios convertidos e
  medidos"): as quatro famílias somam **A=0 B=0 C=0 D=0** em `execute-phase.md`
  e nos seus 9 fragments; `node -e` zerado no arquivo e em todo
  `gsd-core/workflows/`; os números publicados com o comando de cada um. O
  título da issue diz "49 sítios"; o que foi medido e convertido são 5 sítios de
  estado sob as quatro famílias + 6 de node — o 49 do título é a contagem de
  chamadas ao binário (48 medidas na fase 34, 57 hoje), que é outra métrica.
- **ADAPT-02** ("fast e debug adaptados: zero leitura ou escrita de `.planning/`
  como fonte de estado, preâmbulo apontando o binário, verdes de ponta a
  ponta"): `fast.md` e `debug.md` estão na tabela do oráculo desde a onda 3 e
  medem zero nas quatro famílias; o caminho executado de `execute-phase` idem; o
  preâmbulo aponta o binário do repo nos 34 blocos desde a onda zero
  (`cairn-preamble.sh list` → `38 registrado(s): new=34, none=4`); e o ponta a
  ponta de `fast.md` roda de verdade num repo de fixture com `bd`, extraindo o
  bloco **do arquivo** e provando que o fato chega ao bd
  (`tests/cairn-prompt-state.bats`, caso "ponta a ponta").

## O que fica para a fase 37 e a 38

- **Os 18 arquivos que citam o runtime antigo**, 26 menções — 6 em
  `commands/`/`skills/`, 11 em `references/`, 1 em `templates/summary.md`. É
  onde a remoção do plugin bate.
- **Os 73 references citados**: 17 chamadas, 5 sítios de node, 2 sítios de
  estado (`autonomous-smart-discuss.md:24` e `planner-antipatterns.md:83`).
- **`package-legitimacy`**: implementar a checagem ou reescrever a regra de
  proveniência do pesquisador de fase.
- **A grafia `worktree.set-baseref`** e o `gsd-tools worktree set-baseref` de
  `execute-phase-wave-guard.md:30`, registrados na onda 6.
- **O desembrulho `@file:` inerte** — 16 sítios em 12 arquivos, dívida
  registrada na onda 6.
- **A prosa de `phase.complete`** foi alinhada ao payload; se alguma fase
  implementar a varredura de dívida de verificação ou a rastreabilidade em
  REQUIREMENTS, os três aspects de `divergences.json` e essa prosa mudam juntos.

## Self-Check: PASSED

- os 10 arquivos declarados em `key-files.modified` existem no disco e aparecem
  no `git diff --stat` da onda;
- os 4 commits existem em `git log` (`cde8f75`, `1600fed`, `9bbc2a9`, `927ab93`);
- `tests/cairn-prompt-state.bats` 15/15 e `tests/cairn-vendoring.bats` 26/26
  pós-commit, exit 0;
- as quatro famílias dão zero nos 66 arquivos do escopo, medido de novo depois
  do último commit;
- `grep -rl 'node -e' cairn/gsd/gsd-core/workflows/` vazio, e o saldo do corpus
  é 7 com razão escrita para cada um.
