---
phase: 36-workflows-steps-e-agentes-falam-bd
plan: 06
subsystem: references-quota-grafo-e-agentes
tags: [adapt-05, d-04, excecao-nomeada, graphify, node-sobrevive, oraculo-dois-sentidos, assercao-fraca]
requires:
  - onda zero do preâmbulo fechada (36-01) — os 34 blocos resolvem o binário do repo
  - oráculo semântico de quatro famílias entregue (36-03/36-04/36-05), com tabela de adaptados, isenções e pendências dois-sentidos
  - ADAPT-05 item intel decidido e escrito no plano 05
  - contrato `misc.json` pinado — a letra de `graphify` e a nota de que a capability foi cortada
provides:
  - o único sítio do corpus que consumia um verbo fora do universo sem tolerância deixou de existir, com recuperação manual escrita e o motivo em voz alta
  - a exceção a D-02 nomeada no registro de adaptações, com motivo, em vez de escorregada
  - os dois sítios de contexto de grafo tratando a resposta real do binário
  - ADAPT-05 fechado — três itens, três decisões escritas, cada uma com aspect próprio em divergences.json
  - os 16 agentes medidos pelas quatro famílias, com o número publicado, e 15 sob o oráculo (o executor virou pendência declarada)
  - os dois sítios de node do gsd-verifier com razão escrita ao lado de cada um, e o saldo de NODE-SOBREVIVE remedido na origem
affects: [36-07]
tech-stack:
  added: []
  patterns:
    [
      falha nomeada aplicada a PROSA em vez de a código — o caminho automático some e o degradado fica escrito,
      exceção a uma fronteira de escopo é NOMEADA no registro com motivo,
      payload de capability indisponível consumido por uma condição a mais no ramo que já existia,
      tabela de teste com coluna que separa "sob a métrica" de "bytes mudados",
      pendência declarada com família quando o arquivo está proibido ao plano,
      decisão de NÃO converter escrita ao lado do sítio e no JSON versionado,
    ]
key-files:
  created:
    - .planning/phases/36-workflows-steps-e-agentes-falam-bd/36-06-SUMMARY.md
  modified:
    - cairn/gsd/gsd-core/references/execute-phase-quota-recovery.md
    - cairn/gsd/gsd-core/references/planner-load-graph-context.md
    - cairn/gsd/agents/gsd-phase-researcher.md
    - cairn/gsd/agents/gsd-planner.md
    - cairn/gsd/agents/gsd-verifier.md
    - cairn/gsd-adaptations.json
    - tests/cairn-prompt-state.bats
    - tests/fixtures/gsd-goldens/divergences.json
    - .planning/phases/36-workflows-steps-e-agentes-falam-bd/36-PATTERNS.md
decisions:
  - "D-04 aplicado com zero código novo: o bloco que chamava o verbo de recuperação de quota e os cinco filtros somem; o 7.1a passa a declarar que a escalada automática não existe nesta instalação, e o 7.1b — que o arquivo já trazia — é nomeado como o único caminho"
  - "o arquivo de references tocado entra no registro como EXCEÇÃO NOMEADA a D-02, com o motivo escrito: os 40 ficam fora por escopo de massa, este entra sozinho porque o sítio não tolera falha"
  - "ADAPT-05 item graphify: NÃO implementar o subsistema. Os dois sítios passam a ler o `{available:false, reason}` que o binário responde com exit 0 e seguem pelo ramo de 'sem contexto de grafo' que a prosa já tinha"
  - "os dois sítios de node do gsd-verifier FICAM, com a razão ao lado de cada um: o runtime ali é o do projeto verificado (uma resposta de API, um export de módulo), e convertê-los adaptaria o projeto sob verificação em vez da camada prompt"
  - "gsd-executor.md NÃO foi tocado — o plano o proíbe por escrito — e o sítio que a medição achou nele virou pendência declarada com família, contagem e o plano que a fecha"
  - "a tabela do oráculo ganhou terceira coluna (editado|intocado) porque 8 dos 16 agentes têm zero sítio de estado sem nunca terem sido editados; registrá-los em gsd-adaptations.json reprovaria os dois sentidos do oráculo de bytes"
  - "o desembrulho `@file:` inerte foi REGISTRADO como dívida e não corrigido: 16 sítios em 12 arquivos markdown para apagar código que nunca dispara"
metrics:
  duration: ~2h de sessão
  completed: 2026-08-11
status: complete
---

# Phase 36 Plan 06: quota manual, grafo indisponível e os 16 agentes medidos Summary

**One-liner:** o passo de recuperação de quota deixou de consumir um verbo que
não existe — e a medição mostrou que ele não quebrava barulhento, ficava em
SILÊNCIO, que é pior; os dois sítios de grafo passaram a ler a indisponibilidade
que o binário já declarava; e os 16 agentes, que o plano dava como zero, foram
medidos em três sítios, dois convertidos e um declarado pendente porque o
arquivo está proibido a este plano.

## A rota

Seis commits.

| # | commit | o quê |
|---|---|---|
| 1 | `c8a09fe` | D-04: a recuperação de quota deixa de chamar um verbo que não existe |
| 2 | `ad0e966` | graphify: os dois sítios leem a resposta que o binário de fato dá |
| 3 | `bc50f02` | os agentes medidos — três sítios onde o plano previa zero |
| 4 | `5c422fb` | o oráculo com os 15 agentes, coluna de bytes e coluna de família |
| 5 | `a0ace04` | PATTERNS corrigido na origem (`@file:` em 12 arquivos, saldo de node) |
| 6 | `ff73c54` | o 7.1a passa a dizer o que a medição mostra: silêncio, não quebra |

O commit 6 corrige a mim mesmo: escrevi "quebra no meio de um pipe" repetindo o
plano, e a medição depois mostrou outra coisa. Está detalhado abaixo.

## D-04 — o que o sítio fazia de verdade

O verbo, medido:

```
$ bash cairn/scripts/cairn-gsd.sh query resolve-execution gsd-executor \
    --attempt 1 --failure-class quota-exceeded
[cairn-gsd] error: verbo desconhecido (fora do universo do contrato): query resolve-execution
exit 2, stdout VAZIO
```

O sítio antigo (`execute-phase-quota-recovery.md:13-19`) capturava essa saída e
a passava por cinco `jq` encadeados, sem `|| true` e sem `2>/dev/null`. O plano
descrevia isso como "quebra no meio de um pipe". **Medido, não é o que
acontece:**

```
captura_exit=2 len=0
jq_exit=0 ESCALATED=[]
NENHUM RAMO CASA — vazio nao e nem true nem false
```

`jq` com entrada vazia sai **0** e não imprime nada. O pipe não aborta: as cinco
variáveis saem **vazias**, e vazio não casa `"true"` nem `"false"`, então
**nenhum dos três ramos de prosa** disparava. Numa falha de quota — o único
momento para o qual o caminho existe — o passo ficava em silêncio, sem instrução
nenhuma para o agente. É pior que quebrar barulhento, e é a razão de o texto novo
dizer isso em vez de repetir a suposição herdada.

### O texto que entrou no lugar

O bloco e os cinco filtros somem. `QUOTA_ATTEMPT` sai junto: medido
(`grep -rn 'QUOTA_ATTEMPT' cairn/ tests/`), as três ocorrências viviam todas
dentro do trecho removido — o contador só existia para alimentar o verbo.

O 7.1a passou a ser, na íntegra:

> **7.1a — automatic provider escalation does not exist in this installation.**
> Upstream GSD swaps PROVIDER on a quota failure (#2296, opt-in through
> `dynamic_routing.provider_escalation`) by asking the binary which execution
> target comes next. That verb is outside the cairn universe of 87: the
> dispatcher answers
>
> ```text
> [cairn-gsd] error: verbo desconhecido (fora do universo do contrato)
> ```
>
> on stderr with exit 2 and writes nothing to stdout. The branch that used to
> read the answer piped that empty string through five `jq` filters with no
> `|| true` and no default. Measured: the pipe does not abort — `jq` on empty
> input exits 0 and prints nothing — so all five variables come out EMPTY, and
> empty is neither `"true"` nor `"false"`, so NONE of the three prose branches
> below matched. On a quota failure, the one moment this path exists for, the
> step went silent. There is no ladder to configure and none to spend: recovery
> here is MANUAL, and 7.1b below is the whole of it. Escalating later is adding
> the handler plus its golden and restoring this branch; until then the degraded
> behaviour is written down instead of breaking mid-pipe. The decision is
> recorded in `tests/fixtures/gsd-goldens/divergences.json`.

O 7.1b — as três opções manuais que o arquivo **já trazia** — passou de "default
when escalation is not configured" para "the only path", e ganhou duas linhas no
fim: nunca repetir a mesma runtime em silêncio, e que a Opção 2 é uma troca na
própria invocação, porque nada nesta instalação a reescreve por você.

Nenhum procedimento novo foi inventado: o plano manda ancorar nas opções que o
arquivo já descreve, e foi o que ficou.

### A exceção a D-02, nomeada

D-02 mantém os 40 arquivos de `references/` fora da fase por escopo de massa.
Este entrou sozinho, e o registro diz por quê — a entrada em
`cairn/gsd-adaptations.json` (onda 6, sem preâmbulo, adaptação de conteúdo):

> D-04, EXCEÇÃO NOMEADA a D-02: os 40 arquivos de references ficam fora desta
> fase por ESCOPO DE MASSA, e este entra sozinho porque o sítio não tolera falha
> — era o único do corpus que consumia um verbo fora do universo de 87 em cinco
> jq encadeados, sem `|| true` e sem `2>/dev/null`. […] Registrar a exceção com
> o motivo é o que a separa de uma abertura de escopo.

`cairn-preamble.sh list` depois da entrada: **38 registrados, new=34, none=4** —
os quatro "sem preâmbulo" são as adaptações de conteúdo, e o script já tinha o
caso previsto (`registrado(s) sem preâmbulo`), então registrar um arquivo sem
bloco de runtime não inventa edição nenhuma.

## As duas divergências que a fase decide NÃO corrigir

Ambas com nome de arquivo e linha, como o plano manda:

| aspect | sítio | por que fica |
|---|---|---|
| `requirements-revert-phase-fora-do-universo-nao-corrigida` | `references/execute-phase-requirement-revert.md:5` | a chamada já é `>/dev/null 2>&1 \|\| true` por desenho upstream — a falha é absorvida no próprio sítio; e o arquivo é um dos 40 de D-02 |
| `worktree-set-baseref-descompasso-de-grafia-nao-corrigido` | `references/execute-phase-between-wave-reset.md:30` | o verbo EXISTE e responde exit 0; o que diverge é a grafia (`query worktree.set-baseref` em vez de `worktree set-baseref`). O sítio tem `2>/dev/null \|\| true`, falha calada. O CONTEXT fixou a condição: entra se a fase tocar o arquivo, fica registrada se não tocar — não tocou |

Medido junto, e **não** registrado como divergência porque é de outra família:
`references/execute-phase-wave-guard.md:30` manda rodar
`gsd-tools worktree set-baseref` — grafia de subcomando certa, binário errado
(`gsd-tools` é o runtime que a fase 37 remove). Cai no lote dos 40 de D-02, e
está anotado aqui para o 37/38 não precisar redescobrir.

## ADAPT-05 fechado: três itens, três aspects

```
$ jq -r '[.divergences[] | select(.aspect|test("intel-api-surface|graphify-indisponibilidade|quota-recovery-sem-escalada")) | .aspect]' \
    tests/fixtures/gsd-goldens/divergences.json
[
  "intel-api-surface-indisponibilidade-consumida",          ← plano 05
  "quota-recovery-sem-escalada-automatica-resolve-execution", ← plano 06
  "graphify-indisponibilidade-consumida-nos-dois-sitios"      ← plano 06
]
```

### graphify: a resposta real, medida nos três subcomandos

```
$ bash cairn/scripts/cairn-gsd.sh graphify status     → exit 0
$ bash cairn/scripts/cairn-gsd.sh graphify query auth --budget 1500 → exit 0
$ bash cairn/scripts/cairn-gsd.sh graphify build      → exit 0
{"available": false, "reason": "graphify: capability não habilitada no cairn — …"}
```

Os dois sítios (`agents/gsd-phase-researcher.md` Step 1.3 e
`references/planner-load-graph-context.md`) ganharam **um parágrafo**, na mesma
posição e na mesma forma do parágrafo de frescor que já existia — nenhum verbo
novo, nenhuma reestruturação do passo:

> If the response instead carries `available: false` with a `reason`, the graph
> subsystem is not implemented in this installation. That payload is a DECLARED
> unavailability — it exits 0, so nothing failed and nothing is silent. Note the
> reason in the same place the freshness annotation would have gone, skip the
> query below (it answers the same payload), and take the branch this step
> already had for an absent graph.json: continue […] without graph context. The
> decision not to implement the subsystem is recorded in
> `tests/fixtures/gsd-goldens/divergences.json` under the `graphify` verb.

A checagem de existência de `graph.json` permanece: é documento, e é ela que
evita a consulta na maioria dos casos.

## Os 16 agentes: o número medido, inclusive onde é zero

Comando (as **quatro** famílias do oráculo, não as três do `<verify>` do plano):

```bash
cd cairn/gsd/agents
for f in *.md; do
  a=$(grep -cE "$PS_RE_A" "$f"); c=$(grep -cE "$PS_RE_C" "$f")
  d=$(grep -cE "$PS_RE_D" "$f"); b=<soma dos 4 literais de PS_PATTERNS_B>
done
```

| agente | A | B | C | D |
|---|---|---|---|---|
| gsd-advisor-researcher | 0 | 0 | 0 | 0 |
| gsd-code-reviewer | 0 | 0 | 0 | 0 |
| gsd-codebase-mapper | 0 | 0 | 0 | 0 |
| gsd-debug-session-manager | 0 | 0 | 0 | 0 |
| gsd-debugger | 0 | 0 | 0 | 0 |
| **gsd-executor** | 0 | 0 | **1** | 0 |
| gsd-integration-checker | 0 | 0 | 0 | 0 |
| gsd-nyquist-auditor | 0 | 0 | 0 | 0 |
| gsd-pattern-mapper | 0 | 0 | 0 | 0 |
| gsd-phase-researcher | 0 | 0 | 0 | 0 |
| gsd-plan-checker | 0 | 0 | 0 | 0 |
| **gsd-planner** | **1** | 0 | **1** | 0 |
| gsd-ui-auditor | 0 | 0 | 0 | 0 |
| gsd-ui-checker | 0 | 0 | 0 | 0 |
| gsd-ui-researcher | 0 | 0 | 0 | 0 |
| gsd-verifier | 0 | 0 | 0 | 0 |
| **total (16)** | **1** | **0** | **2** | **0** |

**A premissa do plano era zero. São três.** Treze dos dezesseis agentes de fato
não tinham nada, e esse zero vai publicado; mas "os 16 agentes têm zero" seria
afirmação não medida.

### Os dois do gsd-planner, e o que cada um era

`:346` — dentro do **template de PLAN.md que o próprio agente emite**:

```
 <context>
 @.planning/PROJECT.md
 @.planning/ROADMAP.md
-@.planning/STATE.md
+
+# Project state is NOT in this list and is NOT a file to read: it is a FACT, and
+# every executor asks the binary for it with `gsd_run query state.load` from its
+# own preamble. Listing it here would hand the markdown to every plan.
```

Não era um sítio do agente: era um sítio que o agente **fabricava em toda PLAN
gerada**, e a leitura aconteceria do outro lado, no executor — a mesma classe da
família D, mordida aqui pela família A por ser `@`-referência.

`:957` — o critério de sucesso: `- [ ] STATE.md read, project history absorbed`
virou `- [ ] Project state loaded from the binary (`state.load`), project
history absorbed`.

E junto foram **duas linhas irmãs do mesmo bloco que nenhuma família vê**,
porque deixá-las seria deixar o defeito de pé com o arquivo declarado verde:

- `:615` mandava **"use `node` to invoke the CLI (not `npx`)"** — prosa contra a
  onda zero, num arquivo cujo preâmbulo já resolve o binário python. Passou a
  "from the binary the preamble above resolved — state is a FACT and this is the
  one place it comes from".
- `:619` decidia o fluxo pela ausência do markdown (`If STATE.md missing but
  .planning/ exists`). Passou a decidir pela resposta do binário, com a proibição
  escrita: *never fall back to reading a planning markdown for it: there is no
  second source*.

### O terceiro sítio não foi tocado — e virou pendência declarada

`agents/gsd-executor.md:850` é família C (a forma passiva). O plano proíbe por
escrito tocar execute-phase e seu agente. Entrou na tabela de pendentes do
oráculo, que a onda 6 generalizou para carregar **família**:

```
PS_PENDING="\
gsd-core/workflows/execute-phase.md|D|1|36-07|…
agents/gsd-executor.md|C|1|36-07|…
"
```

## Os dois sítios de node do gsd-verifier: decisão escrita, e eles ficam

`Step 7b` do `gsd-verifier.md` traz exemplos de spot-check comportamental. Dois
usam `node -e`; **ambos permanecem**, agora com a razão no próprio bloco:

```bash
# API endpoint returns non-empty data. The runtime invoked below belongs to the
# VERIFIED PROJECT, not to GSD: it parses that project's API response. Rewriting it
# to speak to the cairn dispatcher would adapt the project under verification instead
# of the prompt layer, so it stays (fase 36, decisão escrita em divergences.json).
```

```bash
# Module exports expected functions. Same reason as the API spot-check above: this
# runtime is the verified project's, and the export it prints is the project's.
```

Medido no mesmo bloco: há um **terceiro** uso de node (`node $CLI_PATH --help`)
pela mesma razão, que não casa `node -e` e por isso nunca apareceu em nenhuma
contagem de NODE-SOBREVIVE.

### O saldo de NODE-SOBREVIVE, remedido

```
$ grep -rn 'node -e' cairn/gsd/ | grep -v '_GSD_SHIM_NAME'   → 13
   4  gsd-core/workflows/execute-phase.md
   3  gsd-core/references/specless-probe-fallback.md
   2  gsd-core/workflows/execute-phase/steps/executor-isolation-dispatch.md
   2  gsd-core/references/checkpoints.md
   2  agents/gsd-verifier.md
```

**14 no início da fase, 13 hoje** (o `plan-phase.md:549` fechou no 36-05). Dos
13: **6 em escopo para o 36-07** (4 no raiz + 2 no fragment de isolamento),
**2 decididos por escrito aqui** (o verificador) e **5 fora por D-02**
(references). O mapa da fase listava sete e omitia os 2 do fragment e os 5 de
references; a nota de correção do 36-05 já estava certa, e a desta onda soma o
saldo. Ambos os números foram gravados **na origem**, no `36-PATTERNS.md`.

## O oráculo: duas colunas novas, cada uma com controle negativo

### Coluna de bytes (`editado|intocado`) — o vínculo que não podia ser simples

O plano manda "acrescentar os 16 caminhos à tabela de adaptados". Medido, isso
reprovaria o teste de completude, e por um motivo real:

```
$ for f in cairn/gsd/agents/*.md; do cmp -s "$f" "$CACHE/${f#cairn/gsd/}" …
8 DIVERGEM do upstream  (exatamente os 8 registrados em gsd-adaptations.json)
8 IDÊNTICOS             (exatamente os 8 NÃO registrados)
```

Os 8 agentes sem preâmbulo nunca foram tocados por nenhuma onda **e ainda assim
têm zero sítio de estado** — isso é medição publicada, não edição. Registrá-los
em `gsd-adaptations.json` só para satisfazer o vínculo antigo ("todo caminho da
tabela está registrado") reprovaria os **dois sentidos** do oráculo de bytes de
`cairn-vendoring.bats`: `a adaptação registrada sumiu` e, no PORCELAIN
invertido, `registrados que não divergem`. O registro significa "diverge do
upstream de propósito", não "foi conferido".

A tabela passou a escrever qual é o caso, e o teste confere os dois sentidos
(`ps_registry_agrees`): **editado ⇒ registrado**, **intocado ⇒ NÃO registrado**,
qualquer outra palavra na coluna morre nomeada. O controle negativo forja os
três defeitos de uma vez e exige as três frases distintas, e depois conserta a
tabela e exige verde pelo mesmo laço — senão a asserção poderia estar reprovando
por qualquer motivo.

### Coluna de família na tabela de pendentes

A tabela nasceu só da família D. A pendência do `gsd-executor` é de família C, e
sem a coluna viraria silêncio ou uma segunda tabela quase idêntica.
`ps_family_re` resolve A, C e D; **B morre nomeada** de propósito (é lista
literal, não regex) — e há caso de teste para isso, porque devolver regex vazia
casaria toda linha de todo arquivo e daria a pendência por cumprida.

## RED antes de GREEN, medido com o laço do próprio oráculo

O `assert_no_state_facts` real, apontado para uma cópia do `gsd-planner`
anterior à conversão (cópia de backup — nunca `git checkout`), com as regex
conferidas contra o arquivo de teste antes de rodar:

```
--- RED: planner ANTES da conversao (copia forjada) ---
família A (leitura mecânica do arquivo de estado) em agents/gsd-planner.md:
346:@.planning/STATE.md
família C (prosa imperativa sobre o arquivo de estado) em agents/gsd-planner.md:
957:- [ ] STATE.md read, project history absorbed
exit=1
--- GREEN: planner no disco, depois da conversao ---
exit=0
```

## Quebras aplicadas, e qual asserção cada uma derrubou

| quebra forjada | derruba | frase exigida |
|---|---|---|
| `w/editado.md` na tabela como `editado`, ausente do registro | o sentido "editado ⇒ registrado" de `ps_registry_agrees` | `declarado editado mas não registrado` |
| `w/intocado.md` como `intocado`, **presente** no registro | o sentido inverso — o que o oráculo de bytes reprovaria pelo outro lado | `declarado intocado mas REGISTRADO` |
| coluna `conferido` (palavra que não é nenhuma das duas) | a validação do vocabulário da coluna | `coluna de bytes desconhecida` + `'conferido'` |
| tabela consertada (editado registrado, intocado fora) | prova que as três acima reprovavam pelo motivo nomeado, e não por qualquer um | `status -eq 0` |
| `ps_family_re B` | o fallback silencioso de família sem regex | `família sem regex nesta tabela: 'B'`, exit 2 |
| `ps_family_re C` devolve exatamente `$PS_RE_C` | que a resolução por família não devolve outra regex | igualdade literal |
| gsd-planner na forma anterior (cópia real, não sintética) | as famílias A e C sobre um arquivo REAL desta onda | duas frases, `:346` e `:957` |

As quebras vivem no arquivo real de teste (`tests/cairn-prompt-state.bats`), em
árvores forjadas sob `$BATS_TEST_TMPDIR`; a última é a medição de RED acima.

## Testes

| suíte | resultado |
|---|---|
| `tests/cairn-prompt-state.bats` | **13/13** (12 antes + o controle negativo novo) |
| `tests/cairn-vendoring.bats` | **26/26** — inclui o oráculo de bytes dois-sentidos e o PORCELAIN invertido |
| `tests/cairn-gsd.bats` + `cairn-preamble.bats` + `cairn-command-surfaces.bats` | verdes no mesmo run |
| **os cinco arquivos juntos** | **156 ok / 0 not ok / exit 0** |
| confirmação pós-commit (`prompt-state` + `vendoring`) | **39 ok / 0 not ok / exit 0** |
| pós-correção `ff73c54` (`cairn-gsd` + `vendoring`) | **116 ok / 0 not ok / exit 0** |

Comando: `bash cairn/scripts/cairn-test.sh --jobs 8 tests/<arquivo>.bats`, com a
saída redirecionada para arquivo (um `| tail` devolveria o exit do `tail`).

Os dois vermelhos que a onda 5 deixou registrados em `deferred-items.md`
(baseline do `cairn-doctor.py` e a rota de `export-identity`) **não apareceram**
nesta medição: `cairn-gsd.bats` e `cairn-command-surfaces.bats` passaram
inteiros. Chegaram consertados pelo merge, como o relato da onda anterior previa.

## Premissas do plano que a medição contradisse

1. **"os 16 agentes têm zero ocorrências nas três famílias"** — são **três
   sítios** (A=1, C=2). O plano previa publicar um zero; o que se publica é 3.
2. **"o sítio quebra no meio de um pipe"** (D-04, repetido do CONTEXT e do
   RESEARCH) — **não quebra**. `jq` com entrada vazia sai 0 e não imprime nada;
   as cinco variáveis saem vazias e **nenhum** dos três ramos casa. O modo de
   falha é silêncio, não interrupção. Corrigido no texto do arquivo e na entrada
   de divergência (commit `ff73c54`).
3. **O `<verify>` da Task 3 é asserção fraca** — e isso foi medido, não
   suposto. Rodado contra a árvore **antes** da conversão, com o `gsd-planner`
   original:

   ```
   verify DO PLANO na arvore ANTES da conversao: T=0
   oraculo REAL (PS_RE_A/PS_RE_C) na mesma arvore: T=3
   ```

   A regex de família A do `<verify>` exige um comando de leitura, e o sítio era
   uma `@`-referência; a de família C só tem a forma imperativa, e os dois sítios
   remanescentes são a passiva. O `<verify>` daria verde com os três de pé — o
   mesmo padrão que a onda 5 registrou contra si mesma.
4. **`[.divergences[] | select(.verb=="graphify")] | length >= 1` também é
   fraca**: já havia uma entrada `capability-declared-unavailable` com
   `verb: graphify` desde uma fase anterior, então a asserção passava **antes**
   de eu escrever qualquer coisa. A entrada nova recebeu aspect próprio
   (`graphify-indisponibilidade-consumida-nos-dois-sitios`) e a verificação foi
   refeita por `aspect`, não por `verb`.
5. **"os dois sítios de node do gsd-verifier"** — são dois de `node -e`, mas o
   bloco tem **três** usos de node; o terceiro (`node $CLI_PATH --help`) fica
   pela mesma razão e nunca entrou em contagem nenhuma.
6. **`@file:` "16 ocorrências em 10 arquivos"** (36-PATTERNS §7) — são **16
   sítios em 12 arquivos markdown**. Quinze usam `if [[ … == @file:* ]]`; o
   décimo sexto é a forma inline de `discuss-phase.md:119`, invisível a uma busca
   pelo `if`. Corrigido na origem.
7. **A mensagem do próprio binário está imprecisa para graphify.** `CAP_MSG`
   (`cairn-gsd-init.py:890`) diz *"nenhum call site do corpus o consome"*, e o
   corpus tem **dois** call sites de graphify, quatro chamadas. A frase é
   genérica do handler de capability compartilhado; não a alterei (mudaria o
   payload de outros verbos e seus goldens), e o fato está escrito na entrada de
   divergência.

## Desvios aplicados

- **[Rule 2 — funcionalidade crítica ausente]** `agents/gsd-planner.md` não
  estava em `files_modified`, mas o próprio plano manda converter qualquer sítio
  que a medição encontre ("Se a medição encontrar qualquer sítio de fato,
  convertê-lo pelo critério já fixado nos planos 03 a 05, e publicar"). Foram 3
  edições no arquivo, mais 2 linhas irmãs do mesmo bloco que nenhuma família vê.
- **[Rule 3 — bloqueio]** o vínculo "todo caminho da tabela está registrado em
  `gsd-adaptations.json`" impedia pôr os 16 agentes sob o oráculo sem quebrar o
  oráculo de bytes. Resolvido com a coluna de bytes e o teste dois-sentidos, em
  vez de afrouxar a asserção.
- **Escopo respeitado:** `execute-phase.md` e `agents/gsd-executor.md` não foram
  tocados (proibição escrita do plano); o sítio achado no executor virou
  pendência declarada. Os 40 `references/` continuam fora, com a única exceção
  nomeada de D-04.

## Estado do bd

`ADAPT-05: CairnGo-zjfa` reclamada (`bd update --claim`) e **fechada**, medindo
os dois critérios em vez de presumir:

- os **três** itens têm decisão escrita, cada um com aspect próprio em
  `divergences.json` (intel no 05; graphify e o verbo de quota no 06);
- "os shims mantidos estão adaptados" — `cairn-preamble.sh list` responde
  **38 registrados: new=34, none=4**, ou seja, nenhum bloco de preâmbulo na
  forma antiga;
- o plano 07 **não** depende dela: `requirements: [ADAPT-04, ADAPT-02]`, e
  `grep -n 'ADAPT-05\|graphify\|quota\|intel'` no `36-07-PLAN.md` não devolve
  nada.

## O que fica para as ondas seguintes

- **36-07:** `execute-phase.md` (4 sítios de `node -e` + a injeção da família D
  em `:750`), `executor-isolation-dispatch.md` (2 sítios) e
  `agents/gsd-executor.md` (`:850`, pendência declarada). O fecho da tabela do
  oráculo são exatamente esses dois caminhos.
- **37/38:** os 40 `references/` (5 sítios de `node -e` entre eles), a grafia
  `worktree.set-baseref`, o `gsd-tools worktree set-baseref` de
  `execute-phase-wave-guard.md:30`, e o desembrulho `@file:` inerte.

## Self-Check: PASSED

- os 9 arquivos declarados em `key-files` existem no disco;
- os 6 commits existem em `git log` (`c8a09fe`, `ad0e966`, `bc50f02`, `5c422fb`,
  `a0ace04`, `ff73c54`);
- `tests/cairn-prompt-state.bats` 13/13 e `tests/cairn-vendoring.bats` 26/26
  pós-commit, exit 0.
