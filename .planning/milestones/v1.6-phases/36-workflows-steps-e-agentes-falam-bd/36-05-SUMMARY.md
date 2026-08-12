---
phase: 36-workflows-steps-e-agentes-falam-bd
plan: 05
subsystem: workflows-plan-verify-autonomous
tags: [adapt-03, adapt-05, node-sobrevive, ancora-de-diretorio, predicado-que-muda-de-sentido, familia-d]
requires:
  - onda zero do preâmbulo fechada (36-01) — todo bloco `gsd_run` destes três arquivos resolve o binário do repo
  - oráculo semântico de quatro famílias entregue (36-03/36-04), com tabela de adaptados, isenções e pendências dois-sentidos
  - contratos `estado.json`, `misc.json`, `init.json` e `roadmap-phase.json` pinados (fases 33-35) — a letra de `state.load`, `state.update`, `state.add-blocker`, `state.planned-phase`, `phase.complete` e `intel`
provides:
  - plan-phase, verify-work e autonomous sem leitura nem escrita de `.planning/` como fonte de estado
  - o sítio mais crítico de NODE-SOBREVIVE fechado — o helper que parseia TODO campo do bundle de init do plan-phase
  - a âncora de diretório do artefato de intel preservada na remoção da variável de estado, e vinda do bundle
  - ADAPT-05 item intel decidido, escrito em divergences.json e com o sítio TRATANDO a resposta real do binário, provado por ponta a ponta com dois controles negativos
  - o predicado de existência de estado com significado novo e falha nomeando o comando que cria o fato
  - a subclasse de injeção em prompt de subagente ZERADA no corpus de workflows fora do execute-phase
affects: [36-06, 36-07]
tech-stack:
  added: []
  patterns:
    [
      trocar o motor de um helper provando equivalência por tabela de casos e não por leitura,
      âncora de diretório vinda de campo do bundle em vez de dirname sobre outro caminho,
      payload de capability indisponível CONSUMIDO pelo sítio e provado por ponta a ponta,
      predicado que muda de significado tem a razão escrita no próprio arquivo,
      fato de coleção (bloqueio) lido onde vive, e não numa seção de markdown,
      controle negativo forjado no ARQUIVO REAL, não só numa cópia,
    ]
key-files:
  created:
    - .planning/phases/36-workflows-steps-e-agentes-falam-bd/deferred-items.md
  modified:
    - cairn/gsd/gsd-core/workflows/plan-phase.md
    - cairn/gsd/gsd-core/workflows/verify-work.md
    - cairn/gsd/gsd-core/workflows/autonomous.md
    - cairn/gsd-adaptations.json
    - tests/cairn-prompt-state.bats
    - tests/fixtures/gsd-goldens/divergences.json
    - .planning/phases/36-workflows-steps-e-agentes-falam-bd/36-PATTERNS.md
decisions:
  - "ADAPT-05 item intel: NÃO implementar o subsistema. O binário já responde `{available:false, reason}` com exit 0 e o sítio passa a LER essa resposta — `API_SURFACE_PATH` fica vazio, que é o mesmo estado que o próprio passo já definia para 'sem hook ativo'"
  - "a âncora saiu de `dirname($STATE_PATH)` para `${PROJECT_ROOT}` — campo do bundle, declarado no `output.shape` de `init.plan-phase`; nada de `dirname` sobre outro caminho, que só trocaria de refém"
  - "`state_exists` mantém o NOME (campo de bundle é contrato da fase 34) e muda de PERGUNTA; a razão da troca ficou escrita no arquivo em vez de suposta"
  - "o adiamento de verificação virou DOIS verbos (`state.update verification pending` + `state.add-blocker`), não uma chave nova em `state.update` — medido: chave fora do `field_map` responde `updated:false` com exit 0, isto é, seria uma linha que não faz nada"
  - "os bloqueios são lidos com `bd list -l gsd-blocker` porque não existe verbo de leitura para o rótulo; falha nomeada, sem fallback markdown e sem forma vazia"
  - "os 17 fragments dos três workflows têm ZERO nas quatro famílias e nenhum foi editado — entram na tabela do oráculo, não em `waves[]` (precedente `bb4bbe7`)"
  - "`.planning/STATE.md` SAI da lista de commit do plan-phase porque nenhum verbo chamado ali escreve o arquivo — o oposto da decisão da onda 4 em `quick`, e a medição que separa os dois casos está publicada abaixo"
metrics:
  duration: ~2h de sessão
  completed: 2026-08-11
status: complete
---

# Phase 36 Plan 05: plan-phase, verify-work e autonomous — o node no caminho crítico e o predicado que muda de sentido Summary

**One-liner:** o helper que lia CADA campo do bundle de init do `plan-phase`
trocou de motor sem mudar de contrato — provado por tabela de 14 casos contra o
`node` que ele substitui — e a âncora de diretório que morreria junto com a
variável de estado sobreviveu vindo do próprio bundle; o gate de intel passou a
LER a indisponibilidade que o binário já declarava em vez de anunciar um arquivo
que ninguém escreveu, e o predicado de existência de estado deixou de perguntar
por um arquivo para perguntar pelo portador, com a falha nomeando o comando que
o cria.

## A rota

Três tasks na ordem do plano, cada uma RED→GREEN com commits separados, mais
dois commits de fechamento. Nove commits.

| # | commit | o quê |
|---|---|---|
| 1 | `ed0c981` | RED: plan-phase e três fragments entram na tabela do oráculo |
| 2 | `548546c` | GREEN: o motor do helper, a âncora e o gate de intel |
| 3 | `b5d232e` | RED: verify-work e seu fragment entram |
| 4 | `a9544d7` | GREEN: a conclusão de fase é fato, e a última injeção cai |
| 5 | `2f7e5eb` | RED: autonomous e converge-fail-fast entram |
| 6 | `389f82d` | GREEN: três leituras mecânicas e o predicado que muda de sentido |
| 7 | `f61a769` | o ponta a ponta do gate de intel e seu controle negativo |
| 8 | `9e94ffb` | NODE-SOBREVIVE corrigida na origem (7 → 14) + `deferred-items.md` |
| 9 | `4598a2d` | terceiro item deferido |

A Task 3 foi a única em que editei antes de escrever o RED. Corrigido antes de
commitar: a versão editada foi parqueada num arquivo, o original restaurado **da
cópia** (nunca `git checkout`), o RED commitado com o vermelho real, e só então a
versão editada voltou. O vermelho de `2f7e5eb` é medido, não reconstituído.

## O motor do helper — a armadilha NODE-SOBREVIVE no sítio que mais dói

`plan-phase.md:549` definia:

```bash
_gsd_field() { node -e "const o=JSON.parse(process.argv[1]); const v=o[process.argv[2]]; process.stdout.write(v==null?'':String(v))" "$1" "$2"; }
```

e **11 linhas** o chamavam em seguida (`state_path`, `roadmap_path`,
`requirements_path`, `research_path`, `verification_path`, `uat_path`,
`context_path`, `reviews_path`, `patterns_path`, `phase_dir`). Uma troca de
preâmbulo não remove `node` daqui: cada leitura de campo dispara um processo
node, e um teste de ponta a ponta que só validasse o preâmbulo declararia verde
um caminho que ainda quebra sem node.

A forma nova:

```bash
_gsd_field() { printf '%s' "$1" | jq -r --arg k "$2" 'if .[$k] == null then "" else (.[$k] | if type == "string" then . else tostring end) end'; }
```

`jq` não é escolha estética: `verify-work.md:70` e `execute-phase.md:1111-1113`
já parseiam os próprios bundles com `printf '%s' … | jq -r`.

**A equivalência foi MEDIDA, caso a caso, contra o node que ela substitui** — 14
entradas, o mesmo JSON para os dois:

| campo | valor | node | jq | igual |
|---|---|---|---|---|
| `s` | `".planning/STATE.md"` | `.planning/STATE.md` | idem | sim |
| `empty` | `""` | vazio | vazio | sim |
| `nul` | `null` | vazio | vazio | sim |
| `num` | `42` | `42` | `42` | sim |
| `zero` | `0` | `0` | `0` | sim |
| `f` | `false` | `false` | `false` | sim |
| `t` | `true` | `true` | `true` | sim |
| `multi` | `"a\nb"` | `a⏎b` | idem | sim |
| `trail` | `"a\n"` | `a` | `a` | sim |
| `q` | `"a\"b"` | `a"b` | `a"b` | sim |
| `uni` | `"café ✓"` | `café ✓` | idem | sim |
| *(ausente)* | — | vazio | vazio | sim |
| `arr` | `["a","b"]` | `a,b` | `["a","b"]` | **não** |
| `obj` | `{"k":1}` | `[object Object]` | `{"k":1}` | **não** |

12 de 14 idênticos byte a byte. Os 2 que divergem são valores **não-escalares**,
onde `String(v)` do node produzia `a,b` e `[object Object]` — nenhum dos 11 call
sites lê campo não-escalar (medido: todos são caminho), e nos dois casos a saída
do jq é a mais útil.

**O controle negativo do helper.** A forma jq *óbvia* — `.[$k] // ""` — passa
nos casos comuns e **converte `false` em string vazia**, porque `//` em jq dispara
em `null` **e** em `false`:

| campo | node | a forma enviada | a forma óbvia |
|---|---|---|---|
| `f` (`false`) | `false` | `false` | *(vazio)* |
| `num` | `42` | `42` | `42` |
| `s` | `x` | `x` | `x` |

Uma tabela de casos com só três campos de string teria dado verde nas duas.

**Nota sobre a checagem do plano.** O `<automated>` da Task 1 exige
`grep -c 'node -e' plan-phase.md == 0`. A primeira redação da prosa que EXPLICA a
troca continha o literal `node -e` e virava a checagem sozinha. Reescrita para
"shelled out to a `node` one-liner". Registro porque a checagem é textual: uma
prosa que cite a forma antiga a derruba sem que sítio nenhum tenha voltado.

## A âncora de diretório — a quebra silenciosa que não aconteceu

`plan-phase.md:652` montava o caminho do artefato de intel **a partir da variável
de estado**:

```bash
API_SURFACE_PATH="$(dirname "$STATE_PATH")/intel/API-SURFACE.md"
```

Remover `STATE_PATH` sem substituir a âncora deixaria `API_SURFACE_PATH` valendo
`/intel/API-SURFACE.md` — sem erro, sem exit não-zero, com o gate de intel
apagado em silêncio. É o pior modo de falha da onda e o motivo de a proibição do
plano existir.

A âncora nova vem do **campo do bundle**, não de `dirname` sobre outro caminho
(que só trocaria de refém):

```bash
PROJECT_ROOT=$(_gsd_field "$INIT" project_root)
...
API_SURFACE_PATH="${PROJECT_ROOT}/.planning/intel/API-SURFACE.md"
```

Medido antes de escrever: `project_root` está no `output.shape` declarado de
`init.plan-phase` (`cairn/gsd/contracts/init.json`), é emitido por `common_bundle`
(`cairn-gsd-init.py:508-533`, que todo `handle_init_*` mescla), e
`cairn-gsd.sh query init.phase-op 36 --pick project_root` devolve a raiz absoluta
neste checkout. `cairn/gsd/contracts/` **não foi tocado** — fica do lado vazio do
gate, como manda §4 do PATTERNS.

## ADAPT-05, item intel: a decisão, o texto e o sítio que a executa

**A decisão: NÃO implementar o subsistema.** O binário já responde:

```
$ cairn/scripts/cairn-gsd.sh intel api-surface
{
  "available": false,
  "reason": "intel: capability não habilitada no cairn — o subsistema foi cortado pelo research §4; nenhum call site do corpus o consome"
}
exit=0
```

(`capability_unavailable`, `cairn-gsd-init.py:1071-1080`.) O que faltava era o
**sítio tratar**. Antes ele rodava o subcomando, jogava o payload fora, montava o
caminho e ecoava `✓ API surface regenerated:` — entregando ao planner, como HINT,
o caminho de um arquivo que ninguém escreveu. Depois:

```bash
INTEL=$(gsd_run intel api-surface)
if [ "$(printf '%s' "$INTEL" | jq -r '.available // false')" = "true" ]; then
  API_SURFACE_PATH="${PROJECT_ROOT}/.planning/intel/API-SURFACE.md"
  echo "✓ API surface regenerated: ${API_SURFACE_PATH}"  # injected into step 8 as HINT
else
  API_SURFACE_PATH=""
  echo "→ intel unavailable, planning without an API surface: $(printf '%s' "$INTEL" | jq -r '.reason // "no reason given"')"
fi
```

`API_SURFACE_PATH` vazio não é invenção: é **o mesmo estado que o próprio passo já
definia** uma linha acima para "sem hook ativo de intel", e o passo 8 já omite a
entrada de API Surface quando ele está vazio.

**A entrada nova em `divergences.json`** (56 entradas; `jq -S` estável, newline
final, schema conferido pelo teste `cairn-gsd.bats:891`):

```json
{
  "aspect": "intel-api-surface-indisponibilidade-consumida",
  "cairn": "gsd_run intel api-surface responde {available: false, reason} com exit 0, e o UNICO call site do corpus (plan-phase.md §7.9) LÊ essa resposta: API_SURFACE_PATH fica vazio, o passo diz em uma linha por que segue sem o artefato, e a entrada de API Surface some do prompt do planner",
  "family": "misc",
  "reason": "ADAPT-05 item intel, decidido na fase 36 plano 05: NÃO implementar o subsistema — nenhum call site consome API-SURFACE.md além da presença do caminho, e o passo que ecoava \"✓ API surface regenerated\" sem conferir nada entregaria ao planner o caminho de um arquivo que ninguém escreveu",
  "upstream": "intel api-surface renderiza api-map.json em .planning/intel/API-SURFACE.md e o sítio assume que o artefato foi gerado",
  "verb": "intel"
}
```

**E um ponta a ponta, porque nenhuma das quatro famílias vê este sítio.** Ele não
lê estado; consome o payload de uma capability. Sem caso próprio, o JSON afirmaria
que o sítio trata a resposta e a suíte não checaria nada. O bloco é **extraído do
arquivo** por `ps_extract_bash_block` (o mesmo que já servia o `fast.md`), nunca
redigitado, e roda contra o binário real.

## A mensagem nova do predicado de existência, palavra por palavra

Antes (`autonomous.md:104`):

> **If `state_exists` is false:** Error — "No STATE.md found. Run `/gsd:new-milestone` first."

Depois:

> **If `state_exists` is false:** Error — "No state carrier in the bd (no bead labelled `gsd-state`). Run `gsd_run query state.begin-phase <N>` to create the fact."
>
> `state_exists` keeps its name — it is a field of the init bundle and the bundle is
> a pinned contract — but the question it answers has changed with the owner of the
> fact. It is no longer "does `.planning/STATE.md` exist on disk"; it is "does this
> repo have a state carrier in the bd". So the remedy changed too: the old message
> sent the user to a command that no longer creates that fact. The command named
> above is the one that does.

**Por que a mensagem antiga estava errada, medido:** `init.milestone-op` resolve
`state_exists` por `state_exists_report()` (`cairn-gsd-init.py:402-406`), que roda
`state.load` e lê o **exit** — ou seja, o campo já pergunta pelo portador desde a
fase 34. E o único caminho que **cria** o portador é `create_carrier()`
(`cairn-gsd-state.py`), chamado apenas por `transition_position`, isto é, por
`state.begin-phase` e `state.planned-phase`. `/gsd:new-milestone` não o cria.
Conferido rodando neste worktree, que não tem portador:

```
$ cairn/scripts/cairn-gsd.sh query init.milestone-op --pick state_exists
false
$ cairn/scripts/cairn-gsd.sh query init.plan-phase 36
[cairn-gsd-state] error: o bd não tem portador de estado gsd (label gsd-state) neste repo; rode 'cairn-gsd.sh query state.begin-phase <N>' para criar o fato
```

A mensagem do binário É o molde (`cairn-gsd-state.py:165-168`), e a do workflow
passou a rimar com ela.

## O adiamento de verificação: dois fatos, dois verbos, uma divergência

As duas seções de `autonomous` mandavam **anexar uma tabela markdown**
`## Deferred Verification` ao arquivo de estado, e o passo 2 relia essa tabela.
Viraram:

```bash
gsd_run query state.update verification pending
gsd_run query state.add-blocker --text "verification_deferred_human | phase ${PHASE_NUM} | resume: /gsd:verify-work ${PHASE_NUM}"
```

**Não usei `state.update` com chave nova**, que era a letra do plano. Medido:
`handle_state_update` (`cairn-gsd-state.py:339-360`) consulta o `field_map`, e
chave fora dele responde

```json
{"updated": false, "reason": "campo 'X' não projeta dimensão D-02 — documento, não fato"}
```

com **exit 0**. Seria uma linha que não faz nada — pior que o markdown que
substitui, porque parece que faz. A dimensão que EXISTE e é verdadeira para um
adiamento é `verification`, cujo vocabulário é fechado
(`passed | failed | pending`); tentar `verification_deferred_human` ali morre com
`valor fora do vocabulário` (`set_dimension:212-221`). O resto do adiamento — a
fase e o comando de retomada — é **fato de coleção**, e `state.add-blocker` é o
verbo que carrega texto livre como bead próprio.

A distância ficou registrada em `divergences.json`
(`estado / state.add-blocker / deferred-verification-sem-dimensao`), como o plano
manda: 57 entradas ao fim da onda.

Tudo conferido rodando num fixture com `git init` + `bd init` + portador:

```
$ cairn-gsd.sh query state.add-blocker --text 'verification_deferred_human — fase 3; retome com /gsd:verify-work 3'
{"added": true, "blocker": "verification_deferred_human — fase 3; retome com /gsd:verify-work 3"}
$ bd list -l gsd-blocker --limit 0 --json | jq -r '.[] | {id,title,status}'
{"id":"fx-1sx","title":"verification_deferred_human — fase 3; …","status":"open"}
$ cairn-gsd.sh query state.update verification pending
{"updated": ["verification"]}
$ cairn-gsd.sh query state.load | jq -r .state_raw
phase: 3
phase_status: executing
verification: pending
```

**Por que `bd list` e não um verbo:** não existe leitor de `gsd-blocker` no
binário — `grep -rn BLOCKER_LABEL cairn/scripts/` dá duas linhas, a definição
(`:81`) e a **escrita** (`:1108`). Ler onde o fato vive é a doutrina da fase
(o próprio ponta a ponta da suíte já faz `bd list -l gsd-quick-task`), e o sítio
leva falha nomeada, sem fallback markdown e sem forma vazia.

## Números por arquivo, inclusive os zeros

Famílias do oráculo, medidas com as regex do próprio `.bats`, antes e depois:

| arquivo | A | B | C | D | `node -e` | menções a `STATE.md` | `.planning/` |
|---|---|---|---|---|---|---|---|
| `workflows/plan-phase.md` | 0 → 0 | 3 → 0 | 0 → 0 | 1 → 0 | **1 → 0** | 5 → 0 | 4 → 5 |
| `workflows/verify-work.md` | 0 → 0 | 1 → 0 | 0 → 0 | 1 → 0 | 0 | 1 → 0 | 3 → 3 |
| `workflows/autonomous.md` | **3 → 0** | 0 → 0 | **2 → 0** | 0 → 0 | 0 | 6 → 1 | 6 → 4 |

Os fragments — **os 17 dos três workflows, não só os cinco que o plano nomeia**:

| fragment | A | B | C | D | editado |
|---|---|---|---|---|---|
| `plan-phase/steps/` (10 arquivos) | 0 | 0 | 0 | 0 | **não** |
| `verify-work/steps/` (2 arquivos) | 0 | 0 | 0 | 0 | **não** |
| `autonomous/steps/` (5 arquivos) | 0 | 0 | 0 | 0 | **não** |

Zero conversões em todos. Nenhum foi editado e nenhum ganhou a onda 5 em
`waves[]` — precedente `bb4bbe7` (onda 3) e `1e6b5c0` (onda 4): somar a onda a um
arquivo intocado é declarar uma edição que não houve. Os cinco que o plano nomeia
**entraram na tabela do oráculo** (que é sobre estar sob a régua, não sobre ter
sido editado, exatamente como `advisor.md` e `chain.md` na onda 4).

As menções sobreviventes a `.planning/`, todas conferidas uma a uma:

- `plan-phase` 5: `:431` (opt-out em `config.json`), `:668` (a âncora nova),
  `:1383` (o `ROADMAP.md` da lista de commit), `:1528` (o `cat` dos PLAN.md na
  oferta de próximos passos) e `:1541` (o item de checklist do diretório).
- `verify-work` 3: `:105`, `:289` e `:507` — **os três sítios de UAT que o plano
  manda não tocar**, e são exatamente esses três.
- `autonomous` 4: `:108` (a prosa que explica a mudança de sentido — a única
  menção a `STATE.md` que restou no arquivo, e nenhuma família a morde),
  `:125` (`config.json`), `:693` (audit de milestone) e `:749` (roadmap
  arquivado) — os dois últimos são os caminhos de documento que o plano preserva.

Contagem canônica (`BROAD_RE` de `cairn-inventory.py:176`, excluída a linha que
define `gsd_run`, contando MATCHES por linha):

| arquivo | pré-onda-zero | HEAD do plano | depois |
|---|---|---|---|
| `plan-phase.md` | 36 | 37 | **40** |
| `verify-work.md` | 18 | 19 | **21** |
| `autonomous.md` | 17 | 17 | **23** |

## Quebras aplicadas, e qual asserção cada uma derrubou

| # | o que foi forjado | asserção que caiu | o que provou |
|---|---|---|---|
| 1 | `plan-phase.md` FORA de `PS_ADAPTED` e de volta em `PS_PENDING_D` | teste 7, **só** `pendência morta: … esperado 1, encontrado 0` | a pendência morre pela contagem, sozinha — quebra cirúrgica |
| 2 | `verify-work.md` em `PS_ADAPTED` **e** em `PS_PENDING_D` | teste 7, DUAS mensagens: `pendência morta` e `declarado pendente E adaptado ao mesmo tempo` | as duas forças independentes existem e são distinguíveis |
| 3 | UMA das duas leituras idênticas reinjetada em `autonomous.md` | teste 1, família A, nomeando a linha | converter uma e esquecer a outra é pego |
| 4 | `_gsd_field` na forma jq óbvia (`// ""`) | a tabela de equivalência, no campo `false` | a forma enviada preserva `false`; a óbvia o apaga |
| 5 | gate de intel de volta à forma cega **no arquivo real** | teste 11, `API_SURFACE_PATH=[]` | o sítio realmente zera o caminho ao ler a indisponibilidade |
| 6 | a razão do binário fora da frase, **no arquivo real** | teste 11, a frase com a razão | a razão chega ao humano, não só ao `if` |

A quebra 6 nasceu de uma **asserção fraca minha, pega medindo**: exigir só a
`reason` na saída passava também na forma cega, porque ela roda
`gsd_run intel api-surface` sem redirecionar e o payload inteiro — razão inclusa —
cai no stdout. A asserção foi apertada para exigir a frase inteira numa linha.

Uma armadilha mecânica no caminho, também medida: `$(...)` come a newline final
do bloco extraído, então o `fi` colava na linha seguinte e o script gerado nem era
bash válido — o teste ficava vermelho por **sintaxe**, não por comportamento
(`status=2`, `unexpected end of file`). O `ps_extract_bash_block` do `fast.md` não
sofre porque nada é concatenado depois dele.

## A tabela de isenções e a de pendências, depois das duas mortes

`PS_EXEMPTIONS` continua **vazia** — os arquivos das ondas 3, 4 e 5 entram todos
com zero isenção. `PS_PENDING_D` perdeu duas das três linhas e fica com uma:

| caminho | contagem | fecha em |
|---|---|---|
| `gsd-core/workflows/execute-phase.md` | 1 | **36-07** |

`PS_ADAPTED` foi de 8 para 16 caminhos. A subclasse de injeção em prompt de
subagente está **zerada no corpus de workflows fora do `execute-phase`**.

## Testes

Rodados com `bash cairn/scripts/cairn-test.sh --jobs 8 <arquivos>` — nunca `bats`
cru, e com o exit code do runner capturado direto (não através de um pipe, que
devolveria o exit do último comando). A suíte inteira **não** foi rodada: medido
em sessão anterior, passa de 1h17 em série; a CI da PR #24 a roda.

| suíte | testes | resultado |
|---|---|---|
| `cairn-prompt-state.bats` | 10 → **12** | verde |
| `cairn-vendoring.bats` (oráculo de bytes dois-sentidos) | 26 | verde |
| `cairn-preamble.bats` | 13 | verde |
| `gsd-contracts.bats` | 24 | verde |
| `cairn-gsd.bats` | 90 | 89 verdes, **1 vermelho pré-existente** |
| `cairn-command-surfaces.bats` | 14 | 13 verdes, **1 vermelho pré-existente** |

Os dois vermelhos **não são desta fase** e estão em `deferred-items.md` com a
medição que os sustenta: o baseline do `cairn-doctor.py` e a rota do check
`export-identity`, ambos vindos dos commits `19f00ee`/`a2527ee` que entraram pelo
merge `8b5714f`. Nenhuma onda da 36 tocou o doctor nem `cairn/docs/`.

O verde do oráculo de bytes É prova neste worktree: `.cairn/cache/gsd-core-v1.10.0`
existe aqui e **nenhum** teste `real_cache_or_skip` skipou (`grep -ci skip` = 0 na
saída de `cairn-vendoring.bats`).

`git status --porcelain cairn/gsd/` está vazio ao fim da onda (tudo commitado), e
os caminhos que a onda tocou sob `cairn/gsd/` são exatamente três: os três
workflows raiz.

## Premissas do plano que a medição contradisse

1. **Os cinco fragments que o plano manda medir e converter têm ZERO.** Os 17
   fragments dos três workflows têm zero nas quatro famílias, zero `node -e` e
   zero menções a `STATE.md`. `files_modified` do plano lista os cinco; nenhum foi
   modificado. Convertê-los seria inventar sítio.

2. **`state.update` com chave nova não serve, e o plano manda usá-la.** A Task 3
   diz "usar o verbo de atualização de estado com a chave adequada e registrar a
   distância". Medido: chave fora do `field_map` responde
   `{updated:false, reason:"…documento, não fato"}` com exit 0 — a linha não faz
   nada. A intenção (registrar pelo verbo, não em markdown; registrar a distância)
   foi preservada com `verification pending` + `state.add-blocker`.

3. **`transition.md` não existe na árvore vendorizada.** `verify-work.md:617`,
   `autonomous.md:469` e `:477` mandam ler
   `~/.claude/gsd-core/workflows/transition.md`, e o arquivo **não está no
   `files[]` do MANIFEST** — só no cache do clone
   (`.cairn/cache/gsd-core-v1.10.0/gsd-core/workflows/transition.md`, 683 linhas).
   É um **nono workflow** citado três vezes e não vendorizado. Não é desta onda
   resolver (o plano proíbe tocar em mecanismo aqui), mas quem planejar a 37/38
   precisa saber: o `phase.complete` que a prosa nova nomeia é chamado lá dentro,
   e "lá dentro" não está no repositório.

4. **A checagem `grep -c 'node -e' == 0` do próprio plano é derrubável por prosa.**
   Qualquer explicação que cite a forma antiga a reprova. Registrado, e a prosa
   reescrita.

5. **`NODE-SOBREVIVE` conta SETE sítios; a árvore tinha 14.** Faltavam os 2 de
   `execute-phase/steps/executor-isolation-dispatch.md` (`:96`, `:176`) — **dentro
   do escopo** — e os 5 de `references/` (`specless-probe-fallback.md` 3,
   `checkpoints.md` 2), fora por D-02. Corrigido na origem, no `36-PATTERNS`, com
   data, motivo e a consequência para quem planeja. Números: 14 no corpus antes /
   **13** depois; 9 em escopo antes / **8** depois — 2 são decisão escrita do 36-06
   e 6 do 36-07. O bloco `<verification>` do plano já trazia a conta certa; era o
   `36-PATTERNS` que estava desatualizado.

6. **A tabela do `36-PATTERNS §5` está CERTA — a minha primeira medição é que
   estava errada.** Cheguei a medir `autonomous` em 16 contra os 17 publicados.
   O erro era meu: subtraí 1 por linha de preâmbulo, quando a linha do preâmbulo
   casa `BROAD_RE` **zero** vezes. Refeita com o método declarado (excluir a linha
   que define `gsd_run`, contar matches por linha), a tabela reproduz exatamente:
   147 no total e os 8 valores por arquivo. Registro o erro porque quase publiquei
   uma "correção" que teria estragado um número correto.

7. **A justificativa da onda 4 para manter `.planning/STATE.md` na lista de commit
   do `quick` não bate com o binário do cairn.** O `36-04-SUMMARY` diz "quem
   escreve o arquivo agora é o verbo (`appendQuickTaskRow` roda sob o lock de
   `readModifyWriteStateMd`)" — isso descreve o binário **upstream**. No cairn,
   `handle_quick_tasks_append` (`cairn-gsd-state.py:1322-1335`) cria um bead com
   label `gsd-quick-task` e **não escreve arquivo nenhum** (é a divergência
   declarada `quick-tasks-as-bd-issues`). A decisão desta onda para o `plan-phase`
   — tirar o estado da lista, porque `state.planned-phase` só transita dimensão no
   bd — está medida e é a certa. A linha equivalente em `quick.md:617` fica como
   **inconsistência aberta**: não é arquivo desta onda, e mexer nela seria mudar
   decisão de outra onda sem plano. Alvo natural do 36-07.

## Desvios aplicados

- **`plan-phase.md:1311` convertido além da letra do plano.** A linha dizia que o
  override de cobertura de decisão era "recorded in STATE.md", **sem comando
  nenhum** — um fato afirmado sem dono, e falso depois desta fase. Passou a nomear
  `state.add-decision`, com a invocação conferida rodando
  (`{"added": true, "decision": "[Phase 3]: decision-coverage override — …"}`).
  Rule 2: descrever comportamento correto.
- **Um teste de ponta a ponta e um controle negativo a mais** (`f61a769`), fora da
  letra do plano. Justificativa: a decisão de ADAPT-05 nasce **nesta onda** e
  nenhuma das quatro famílias vê o sítio — sem eles, `divergences.json` afirmaria
  algo que a suíte não confere.
- **Nenhuma tabela de máquina para os sítios de `node -e` restantes.** A correção
  ficou em prosa no `36-PATTERNS` porque o fecho é dos planos 06 e 07, e impor
  agora a forma da tabela que eles vão preencher é decidir por eles. **Fica a
  recomendação**: quem fechar os últimos sítios ganha barato uma tabela
  dois-sentidos no molde de `PS_PENDING_D`, e ela morre sozinha quando a contagem
  zerar.
- **`waves[]` só nos três arquivos editados**, como nas ondas 3 e 4.
- **Verificação com `cairn-test.sh`, sem `bats tests/` completo** — regra do
  operador, com o número que a sustenta.

## Estado do bd

`ADAPT-03` → `CairnGo-z782` e `ADAPT-05` → `CairnGo-zjfa`: **as duas reclamadas,
nenhuma fechada.**

- `z782` cobre `discuss-phase`, `plan-phase`, `verify-work`, `quick` e
  `autonomous`. Os cinco estão adaptados depois desta onda, mas a issue também
  cobre o que a onda 4 entregou e a decisão de fechar é de quem enxerga a fase
  inteira.
- `zjfa` cobre `graphify` **e** `intel` **e** os shims mantidos. Só o item intel
  foi decidido aqui; `graphify` e os shims são do plano 06.

## O que fica para as ondas seguintes

- **36-06:** `graphify` e os shims mantidos (o resto de ADAPT-05); os 2 sítios de
  `node -e` de `gsd-verifier.md`, que o plano 05 registra como decisão escrita.
- **36-07:** `execute-phase.md` — os 4 `node -e` do arquivo raiz, os 2 do
  `executor-isolation-dispatch.md`, a última pendência da família D (`:750`) e o
  fecho total da tabela do oráculo. Mais duas heranças: a inconsistência do
  `.planning/STATE.md` na lista de commit do `quick` (premissa 7) e a tabela de
  máquina para os `node -e` restantes.
- **Fora desta fase:** os 5 `node -e` de `references/` (lacuna D-02), o
  `transition.md` citado três vezes e não vendorizado, os três itens de
  `deferred-items.md` e o `36-03-SUMMARY.md`, que segue por escrever.

## Self-Check: PASSED

Arquivos declarados, conferidos no disco:

- `cairn/gsd/gsd-core/workflows/plan-phase.md` — FOUND
- `cairn/gsd/gsd-core/workflows/verify-work.md` — FOUND
- `cairn/gsd/gsd-core/workflows/autonomous.md` — FOUND
- `cairn/gsd-adaptations.json` — FOUND (37 entradas; `waves` `[1,5]` nos três)
- `tests/cairn-prompt-state.bats` — FOUND (12 testes)
- `tests/fixtures/gsd-goldens/divergences.json` — FOUND (57 entradas)
- `.planning/phases/36-workflows-steps-e-agentes-falam-bd/36-PATTERNS.md` — FOUND
- `.planning/phases/36-workflows-steps-e-agentes-falam-bd/deferred-items.md` — FOUND

Commits declarados, conferidos em `git log`: `ed0c981`, `548546c`, `b5d232e`,
`a9544d7`, `2f7e5eb`, `389f82d`, `f61a769`, `9e94ffb`, `4598a2d` — todos presentes.
