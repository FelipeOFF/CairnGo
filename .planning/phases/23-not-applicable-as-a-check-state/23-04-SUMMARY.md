---
phase: 23-not-applicable-as-a-check-state
plan: "04"
subsystem: infra
tags: [python, bats, cli, stdlib, doctor, orphans, milestone-archive]
requires:
  - "23-01: o status not-applicable, o campo scope, a contagem por balde"
  - "23-02: as guardas de aplicabilidade convertidas"
  - "23-03: check_orphans com os dois eixos separados no código"
provides:
  - "isenção do orphans para issue fechada de milestone arquivado (VOID-03, metade 2)"
  - "conserto da asserção do lease-stale que contava um ⊘ como regressão desde o 23-02"
  - "archived_milestones() — a leitura de .planning/milestones/ como evidência de ciclo fechado"
  - "in_archived_milestone() — o predicado das três condições, com ALL e não ANY"
  - "teste de invariante do vocabulário: quatro estados, escopo só no ⊘, contadores somando"
  - "a linha do autonomous.md que separa ⊘ de checagem do not-applicable de topo"
affects:
  - "cairn/scripts/cairn-doctor.py"
  - "cairn/docs/commands/doctor.md"
  - "cairn/commands/autonomous.md"
  - "tests/cairn-doctor.bats"
tech-stack:
  added: []
  patterns:
    - "isenção provada por teste diferencial: mesmo repo, mesmas issues, uma variável"
    - "isenção que se declara — a contagem suprimida vai para o texto do veredito"
key-files:
  created: []
  modified:
    - "cairn/scripts/cairn-doctor.py"
    - "cairn/docs/commands/doctor.md"
    - "cairn/commands/autonomous.md"
    - "tests/cairn-doctor.bats"
decisions:
  - "A evidência de arquivamento é o ROADMAP arquivado em .planning/milestones/, não recência nem posição em lista"
  - "O predicado exige TODOS os rótulos de milestone arquivados, nunca algum — é o que preserva o aviso da issue carregada"
  - "A contagem isentada conta só o que o eixo 1 teria reportado, nunca toda issue fechada do tracker"
requirements: [VOID-03]
status: complete
---

# Phase 23 Plan 04: A isenção por milestone arquivado — Summary

O `orphans` para de sinalizar issue fechada de milestone já arquivado, e a contagem
deste repositório cai de **61 para 0** — dizendo, no próprio veredito, que 61 foram
isentadas. A prova não é a contagem cair: é o arquivo do milestone ser a causa.

## A medição, antes e depois

Medido em 2026-08-05 neste repositório, contra o `bd` real e o `cairn-doctor.sh`
desta árvore.

**Antes:**

```
warn  orphans  ::  61 orphan issue(s)   (items: 61)
```

| quantidade | valor medido |
|---|---|
| itens reportados | **61** |
| do eixo 1 (rotulada para fase que o ROADMAP não tem) | **61** |
| do eixo 2 (sem rótulo de fase) | **0** |
| com status fechado | **61** (todos) |
| com status não-fechado | **0** |
| milestones dos 61 | `m-v1.4` 35, `m-v1.1` 16, `m-v1.2` 5, `m-v1.3` 5 |
| fases citadas | 1 a 19 |
| milestones arquivados lidos de `.planning/milestones/` | `v1.1`, `v1.2`, `v1.3`, `v1.4` |

A tabela bate item por item com a T-17 do plano, incluindo a distribuição por
milestone. Os 61 são exatamente a população que esta metade do VOID-03 existe para
isentar.

**Depois:**

```
ok  orphans  ::  122 issue(s), no orphans (+61 closed issue(s) of archived milestone(s) exempted)   (items: 0)
```

Os 61 saíram da lista e apareceram no texto. Nenhum deles some em silêncio.

**Re-medido ao fim da execução, depois de fechar as três issues da fase** — e o
resultado merece ser lido com cuidado, porque parece um retrocesso e não é:

```
warn  orphans  ::  3 orphan issue(s) (+61 closed issue(s) of archived milestone(s) exempted)
```

Os três itens são, literalmente:

```
CairnGo-cdx: no phase-* label (open: A tabela PENDING PHASES tem piso de 92 celulas …)
CairnGo-hbo: no phase-* label (open: Glifos east_asian_width=A … desalinham o board …)
CairnGo-uz6: no phase-* label (open: Sem secao ## Milestones no ROADMAP …)
```

Todos os três são achados do **eixo 2** — issue aberta sem nenhum rótulo de fase —
criados por uma frente irmã (o trabalho de board da fase 21) depois da minha medição.
O **eixo 1 continua em zero** e a isenção dos 61 continua de pé, como o próprio texto
do veredito mostra.

Isso é a arquitetura funcionando exatamente como projetada, e vale registrar: a
isenção do eixo 1 **não** criou silêncio no eixo 2. Um `warn` legítimo continua
aparecendo sobre trabalho vivo, com o número de suprimidas ao lado. Era esse o risco
nomeado no plano 03 — recusar o check inteiro engoliria o eixo 2 — e a re-medição
mostra os dois eixos convivendo no mesmo veredito.

## A prova: o teste diferencial

O teste central roda o doctor **duas vezes sobre o mesmo repositório**, com as
mesmas issues e os mesmos rótulos. Entre as duas rodadas muda **uma** coisa: se o
ROADMAP arquivado do ciclo está em `.planning/milestones/`.

```
run 1  (sem .planning/milestones/v0.9-ROADMAP.md)
       orphans → warn, e o id da issue aparece na saída

mkdir -p .planning/milestones
echo "# Roadmap: v0.9 (archived)" > .planning/milestones/v0.9-ROADMAP.md

run 2  (com o arquivo, e nada mais mudou)
       orphans → ok, items == 0, o id NÃO aparece
       detail casa com "1 .*archiv"
```

Um teste que só afirmasse "a contagem é zero depois de arquivar" também passaria se
alguém desligasse o eixo inteiro por engano. Este não: a quebra que o deixa vermelho
é qualquer implementação que isente sem olhar o diretório de milestones — a começar
pela mais tentadora, "toda issue fechada é isenta", que passa na rodada 2 e falha na
rodada 1.

O vermelho foi confirmado antes de escrever a implementação, e foi exatamente esse:

```
not ok 2 orphans: a closed issue is exempt only because its milestone is archived (differential)
# jq '.checks[] | select(.id=="orphans") | .status' returned 'warn', expected 'ok'
```

A linha do erro é a asserção da **segunda** rodada — a primeira já passava, que é o
comportamento antigo preservado.

## Os três contornos, e por que cada um continua avisando

O predicado exige as três condições ao mesmo tempo (T-19): a issue está fechada, ela
carrega ao menos um rótulo de milestone, e **todos** os rótulos que ela carrega
apontam para milestones arquivados.

| contorno | veredito | motivo escrito no código |
|---|---|---|
| issue **aberta** de milestone arquivado | continua `warn` | trabalho vivo pendurado num ciclo que fechou é achado, não ruído histórico |
| issue fechada **sem rótulo de milestone** | continua `warn` | sem rótulo não há prova de arquivamento; isentar por ausência de evidência é o mesmo raciocínio de aprovar por não ter comparado |
| issue fechada **carregada para o milestone ativo** | continua `warn` | `milestone.md` documenta a órfã transitória como esperada; um rótulo ativo basta para a isenção não valer |

O terceiro é o que separa a implementação correta da tentadora: a versão ingênua com
"algum rótulo arquivado" em vez de "todos" passa em todos os outros testes e falha só
nesse. É a mesma distinção ALL/ANY que o `in_done_phase` e o `--close-completed` já
seguravam.

## A isenção não é silenciosa, e a contagem não mente

O texto do veredito passa a dizer quantas foram suprimidas, sempre que alguma tiver
sido. Sem isso, um repositório com sessenta e uma issues históricas ficaria
indistinguível de um repositório com zero, e a fase teria trocado um ruído permanente
por um silêncio permanente — que é o mesmo defeito visto do outro lado.

O contador conta **só as issues que o eixo 1 teria reportado**, não toda issue fechada
do tracker. Uma issue fechada de milestone arquivado cujas fases o ROADMAP ativo ainda
lista não é isenta de nada, porque nunca seria um achado; contá-la inflaria o número e
o número passaria a mentir.

## A varredura final das dezoito checagens

Extraída do código, não de memória: para cada checagem registrada, os estados que ela
pode devolver e a família quando o estado é `⊘`.

| # | checagem | estados possíveis | família do ⊘ |
|---|---|---|---|
| 0 | `bd-version` | ok / warn / fail | — |
| 1 | `req-issue` | ok / fail / ⊘ | no-input |
| 2 | `frontmatter-ids` | ok / fail / ⊘ | no-input |
| 3 | `maps-fresh` | ok / warn / ⊘ | no-input |
| 4 | `superseded-released` | ok / warn / ⊘ | no-input |
| 5 | `phase-complete-open` | ok / warn / fail | — |
| 6 | `orphans` | ok / warn / ⊘ | no-input |
| 7 | `label-pairs` | ok / warn / fail | — |
| 8 | `claims-stale` | ok / warn / ⊘ | no-input |
| 9 | `bd-doctor` | ok / warn | — |
| 10 | `gsd-capability` | ok / warn / fail | — |
| 11 | `phase-corroboration` | ok / warn / fail | — |
| 12 | `phase-artifacts` | ok / warn | — |
| 13 | `external-ref` | ok / warn | — |
| 14 | `lease-stale` | ok / warn | — |
| 15 | `release-versions` | ok / warn / fail / ⊘ | out-of-scope |
| 16 | `test-parallel` | ok / warn / ⊘ | out-of-scope, no-input |
| 17 | `req-ledger` | ok / warn / fail / ⊘ | out-of-scope |

Oito das dezoito podem devolver o quarto estado. Sete usam `no-input` (a entrada
deveria existir e não existe — é um vão que alguém fecha), duas usam `out-of-scope` (a
entrada nunca vai existir nesta classe de repositório e nada está errado), e a
`test-parallel` é a única que usa as duas famílias, por razões diferentes em ramos
diferentes.

## O teste de invariante do vocabulário

A fase inteira pode ser desfeita sem ninguém perceber de um jeito só: alguém
acrescenta um quinto estado sem passar por aqui. O teste novo não afirma nada sobre
nenhuma checagem em particular — afirma sobre o vocabulário:

1. subtrair os quatro estados da lista de status deixa o conjunto vazio;
2. toda checagem `not-applicable` carrega escopo de uma das duas famílias, e nenhuma
   checagem que **não** seja `not-applicable` carrega escopo nenhum;
3. a soma dos quatro contadores é igual ao número de checagens registradas, e o
   objeto de contadores tem exatamente quatro chaves.

Medido nesta árvore: soma dos contadores 18, checagens registradas 18, `counts` com 4
chaves.

## A linha que faltava no consumidor autônomo

O `/cairn:autonomous` é o único consumidor do relatório que decide **parar**. O
pré-voo dele já usava a expressão "not-applicable" para o caso de topo (um lado
ausente → para e roteia para `/cairn:migrate`), e essa palavra agora também é o estado
de uma checagem — duas coisas diferentes com o mesmo nome, na superfície que decide
interromper uma corrida.

A linha acrescentada diz, explicitamente: um rodapé `INCOMPLETE` **não** interrompe a
corrida, porque o código de saída não mudou e continua `0` — a fase 23 manteve isso de
propósito, já que entrada ausente é atrito e não inconsistência. E diz o que fazer com
ele: anotar quais checagens leram `⊘` e reportar, porque são exatamente aquelas cujo
verde não se pode capitalizar depois. Se a verificação do fim se apoiar numa delas,
está se apoiando numa comparação que nunca aconteceu.

Sem essa linha, a primeira corrida autônoma que visse a palavra nova ou parava sem
motivo, ou a ignorava sem saber que podia. É o defeito da fase visto de fora: uma
superfície afirmando algo sobre um estado que ela não conhece.

## A passada final de coerência da página

Quatro planos escreveram na `cairn/docs/commands/doctor.md`. A passada encontrou e
consertou um resíduo:

- **O terceiro bloco de exemplo ainda mostrava o rodapé de três números**
  (`FAIL — 12 ok, 0 warning(s), 1 failure(s)`), de antes do plano 01, e os doze não
  somavam dezoito. Agora mostra os quatro números e a soma fecha:
  `[cairn-doctor] FAIL — 15 ok, 2 not-applicable, 0 warning(s), 1 failure(s)`.

Conferido e correto sem mudança: a contagem de checagens que o texto afirma
(`eighteen checks in total`) bate com as dezoito registradas no código; os outros dois
blocos de exemplo já traziam os quatro números somando dezoito e o símbolo `⊘`; a
tabela de chaves do veredito já dizia que os quatro contadores somam `.checks | length`
e que `scope` aparece só em checagem `not-applicable`; e a seção de códigos de saída
continua dizendo que `⊘`, de qualquer família e inclusive com rodapé `INCOMPLETE`, sai
`0` — porque nada nela mudou, e é isso que ela precisa continuar dizendo.

## Verificação executada

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-doctor.bats`, contado sobre o
log inteiro e não sobre saída truncada:

```
anunciado : 1..96
executado : 96   (96 ok + 0 not ok)
skips     : 0
exit      : 0
```

Anunciado e executado batem. Nenhum teste pulado — o que importa aqui, porque um
`skip` silencioso sobre `require_bd` transformaria esta prova em nada.

| verificação | resultado |
|---|---|
| `tests/cairn-doctor.bats` pelo runner da casa | 96/96, exit 0 |
| RED do teste diferencial, antes da implementação | falhou na asserção da 2ª rodada, como projetado |
| `orphans` neste repositório | `warn`/61 itens → `ok`/0 itens, com `+61 ... exempted` no texto |
| a saída humana (não-JSON) traz a nota de isenção | `✓ orphans  122 issue(s), no orphans (+61 …)` |
| contagem de checagens: código vs página | 18 vs 18 |
| entrada de `orphans` na página documenta a isenção | sim |
| `python3 -m py_compile cairn/scripts/cairn-doctor.py` | ok |

**Commits:**

| commit | conteúdo |
|---|---|
| `aae571d` | a isenção, os quatro testes novos, e o conserto da asserção do `lease-stale` |
| `793f84c` | a página do comando e a linha do `autonomous.md` |

## Deviations from Plan

**1. [Regra da execução] A suíte inteira do repositório não foi rodada aqui**

- **Encontrado em:** Task 2, cujo `<verify>` pedia `bash cairn/scripts/cairn-test.sh`
  sem alvo (a suíte inteira).
- **Motivo:** instrução explícita da execução, medida: a suíte inteira em primeiro
  plano excede o limite do harness e é morta, e uma fase irmã ficou 135 minutos num
  laço de morte-e-retentativa sem avançar um commit. A suíte completa roda uma vez, no
  fim, e é responsabilidade do operador.
- **O que foi rodado no lugar:** `tests/cairn-doctor.bats` inteiro pelo runner da
  casa, que é o alvo que cobre todo o código tocado por esta fase.

**2. [Medição] `lease-stale` mudou de `ok` para `warn` entre as duas rodadas do doctor**

- **Encontrado em:** ao comparar o relatório antes e depois.
- **Causa:** efeito de relógio — três leases de fase venceram entre as duas execuções,
  seguradas por agentes irmãos trabalhando em worktrees paralelas. O código tocado por
  este plano é `check_orphans` e o ponto de chamada dele; nada nele lê lease.
- **Consequência para o rodapé:** os contadores do relatório ficaram iguais antes e
  depois (`13 ok, 1 not-applicable, 2 warn, 2 fail`) por coincidência: o `orphans`
  saiu do balde `warn` e o `lease-stale` entrou. **Não creditar esse rodapé imóvel a
  este plano** — a mudança do plano está no `orphans`, e é visível checagem a
  checagem.

**3. [Regra 1 — bug da própria fase] Um teste irmão vermelho desde o plano 23-02,
encontrado pela passada completa e consertado aqui**

- **Encontrado em:** a passada completa de `tests/cairn-doctor.bats` — anunciado 96,
  executado 96, **1 falha**: `lease-stale: cairn-lease.py itself failing degrades to
  warn, never crashes the doctor run`.
- **O que a asserção dizia:** `[.checks[] | select(.id != "lease-stale" and .status
  != "ok")] | length == 0` — "nada além do lease-stale saiu de `ok`". Devolveu `2`.
- **Quais eram os dois, medido reproduzindo o cenário isolado:** `release-versions` e
  `test-parallel`, ambos `not-applicable` / `out-of-scope`. É o estado **ordinário** de
  um repositório que não é o cairn, e o plano 23-02 escreveu um teste afirmando
  exatamente isso para o fixture saudável.
- **Causa:** o plano 23-02 desta mesma fase deu o quarto estado a essas duas
  checagens, e esta asserção irmã, escrita quando só havia três estados, conta um `⊘`
  como regressão. `!= "ok"` é satisfeito por `warn` **e** por `not-applicable` — é o
  idioma que esta fase inteira existe para remover, sobrevivendo dentro da própria
  suíte da fase.
- **Prova de que é anterior a este plano, e não efeito dele:** o mesmo teste foi
  rodado contra o código do HEAD (commit `9a9e0d7`, antes de qualquer edição deste
  plano) numa worktree separada, e falhou igual, com o mesmo `returned '2', expected
  '0'`. Não foi deduzido — foi medido.
- **Conserto:** a asserção passa a perguntar o que sempre quis perguntar — se alguma
  **outra** checagem virou `warn` ou `fail`, nomeados pelo valor exato e nunca por
  negação de `ok`. Os dois `⊘` passam a ser fixados por id **e** por família, de modo
  que um terceiro aparecendo (regressão real para o quarto estado) continua deixando o
  teste vermelho. A asserção ficou mais forte do que era, não mais frouxa.
- **Arquivo:** `tests/cairn-doctor.bats`.

**4. [Fora de escopo] A falha de `phase-corroboration` na própria fase 23**

- O relatório sai com exit 7 por `phase-corroboration` e `req-ledger`. A primeira é o
  defeito FIX-05 — o disco reporta `executed` porque existe SUMMARY enquanto as issues
  seguem abertas —, conserto da fase 25, e não foi tocada aqui. O exit 7 deste
  repositório **não** é resultado deste plano.

## Threat Flags

Nenhuma superfície nova de rede, autenticação ou acesso a arquivo fora de
`.planning/`. A leitura nova é um `iterdir()` de um diretório do próprio repositório,
que devolve conjunto vazio e nunca levanta exceção quando o diretório não existe
(T-23-14, mitigado).

## Known Stubs

Nenhum. Varredura feita nos arquivos criados/modificados por este plano: nenhum valor
vazio codificado que chegue à saída, nenhum "TODO"/"FIXME"/"placeholder" novo, nenhum
teste pulado. O único `placeholder` que aparece no `cairn-doctor.py` é prosa histórica
sobre a fase 29-07, não um stub.

## Self-Check: PASSED

Arquivos afirmados neste SUMMARY, conferidos em disco: `cairn/scripts/cairn-doctor.py`,
`tests/cairn-doctor.bats`, `cairn/docs/commands/doctor.md`, `cairn/commands/autonomous.md`,
`23-04-SUMMARY.md`, `23-SUMMARY.md` — todos presentes. Commits afirmados, conferidos no
histórico: `9a9e0d7`, `aae571d`, `793f84c` — todos presentes. Nenhuma deleção de arquivo
rastreado nos commits deste plano.
