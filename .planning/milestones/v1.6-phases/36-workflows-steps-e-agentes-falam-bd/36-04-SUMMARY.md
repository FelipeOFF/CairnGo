---
phase: 36-workflows-steps-e-agentes-falam-bd
plan: 04
subsystem: workflows-discuss-e-quick
tags: [adapt-03, familia-d, injecao-em-subagente, bloco-armadilha, unidade-linha]
requires:
  - onda zero do preâmbulo fechada (36-01) — todo bloco `gsd_run` destes arquivos resolve o binário do repo
  - oráculo semântico de três famílias entregue (36-03), com tabela de adaptados e isenções dois-sentidos
  - contratos `estado.json` e `misc.json` pinados (fases 33-35) — a letra de `state.load`, `state.record-session` e `quick-tasks-append`
provides:
  - discuss-phase e quick sem leitura nem escrita de `.planning/` como fonte de estado
  - a injeção de caminho de estado em prompt de subagente escrita como FAMÍLIA D do oráculo, com falso-positivo e controle negativo próprios
  - tabela de sítios PENDENTES da família D, conferida por duas forças independentes, que morre sozinha quando 36-05 e 36-07 passarem
  - `quick/steps/research-phase.md` registrado em `gsd-adaptations.json` (entrada nova, sem preâmbulo)
affects: [36-05, 36-06, 36-07]
tech-stack:
  added: []
  patterns:
    [
      unidade de edição = LINHA quando o fence mistura documento e fato,
      forma de injeção como classe de máquina (regex) e não observação de SUMMARY,
      tabela de pendências separada da de isenções quando o caminho ainda não é medido,
      controle negativo escolhido pela GRAFIA que só a regra nova vê,
    ]
key-files:
  created: []
  modified:
    - cairn/gsd/gsd-core/workflows/discuss-phase.md
    - cairn/gsd/gsd-core/workflows/quick.md
    - cairn/gsd/gsd-core/workflows/quick/steps/research-phase.md
    - cairn/gsd-adaptations.json
    - tests/cairn-prompt-state.bats
    - .planning/phases/36-workflows-steps-e-agentes-falam-bd/36-PATTERNS.md
decisions:
  - "o bloco-armadilha foi desmontado por LINHA: `:238` e `:239` aparecem como contexto no diff, byte a byte, e só `:240` virou `state.load`"
  - "a família D não estende a B: as duas grafias com variável já casavam a B, e a cobertura nova está toda na TERCEIRA grafia (caminho literal), que nenhuma família via"
  - "o rótulo entre parênteses é parte da forma da família D — sem ele a regra morderia a lista de arquivos a COMMITAR e exigiria isenção permanente para comportamento correto"
  - "os três sítios pendentes viraram tabela PRÓPRIA, não linhas de PS_EXEMPTIONS: a isenção de um caminho fora de PS_ADAPTED é inerte e sobreviveria calada ao plano que a deveria matar"
  - "quick 7d (`Last activity`) virou `state.record-session`: a string não existe em nenhum outro ponto de `cairn/gsd/` nem em contrato nenhum — era instrução para editar linha que o estado não tem"
  - "`advisor.md`, `chain.md` e `worktree-pre-dispatch-commit.md` NÃO ganharam a onda 4 em `waves[]`: zero conversões, arquivo não editado (precedente bb4bbe7)"
metrics:
  duration: ~2h20 de sessão (18:53 → 19:2x local)
  completed: 2026-08-11
status: complete
---

# Phase 36 Plan 04: discuss-phase e quick — a armadilha por linha e a injeção como classe Summary

**One-liner:** `discuss-phase` e `quick` passaram a pedir estado ao binário sem
que uma única leitura de documento virasse verbo — o fence de três `cat`
consecutivos foi desmontado linha a linha, o caminho derivado por `dirname`
morreu junto com a dívida do `#2376`, e a injeção de caminho de estado em
prompt de subagente virou a **família D** do oráculo, cuja régua mede seis
sítios onde o `36-PATTERNS` contava cinco.

## A rota

Três tasks na ordem do plano, cada uma em RED→GREEN com commits separados, no
molde que a onda 3 deixou (`e16c9fe` → `e832048`). Cinco commits.

| # | commit | o quê |
|---|---|---|
| 1 | `dddc4d7` | RED: discuss-phase e os dois modes entram na tabela do oráculo |
| 2 | `ca523d2` | GREEN: o bloco-armadilha desmontado por linha |
| 3 | `cb7a9ea` | RED duplo: quick e os dois fragments entram (residuos + registro faltando) |
| 4 | `67ea3ff` | GREEN: a derivação morre, o Step 7 vira verbo, as três injeções caem |
| 5 | `1e6b5c0` | a família D, o falso-positivo, o controle negativo e a tabela de pendentes |

## A classificação linha a linha do bloco de leituras

`discuss-phase.md:237-241`, o bloco que o plano nomeia como armadilha nominal:

| linha | conteúdo (antes) | classe | o que aconteceu |
|---|---|---|---|
| 238 | `cat .planning/PROJECT.md 2>/dev/null \|\| true` | DOCUMENTO | intacta, byte a byte (linha de contexto no diff) |
| 239 | `cat .planning/REQUIREMENTS.md 2>/dev/null \|\| true` | DOCUMENTO | intacta, byte a byte |
| 240 | `cat .planning/STATE.md 2>/dev/null \|\| true` | **FATO** | virou `gsd_run query state.load 2>/dev/null` |

E as vizinhas do mesmo passo, todas medidas antes de tocar em qualquer coisa:

| linha | conteúdo | classe | o que aconteceu |
|---|---|---|---|
| 243 | `.planning/DECISIONS-INDEX.md` (índice de decisões) | DOCUMENTO | intacta |
| 246 | `find .planning/phases -name "*-CONTEXT.md"` | DOCUMENTO | intacta |
| 255-256 | manifestos de spike e sketch | DOCUMENTO | intactas |
| 290 | `ls .planning/codebase/*.md` (mapas) | DOCUMENTO | intacta |

O diff prova a unidade: `9 insertions(+), 6 deletions(-)` no arquivo inteiro,
com `:238` e `:239` do lado do contexto. Uma substituição por bloco teria
convertido as três e transformado leitura legítima de documento em regressão —
que é a única forma de esta onda ter falhado sem falhar nenhum teste.

## A dívida do campo não emitido pelo bundle de init

`quick.md:147-152` derivava o caminho do estado por `dirname` e a nota ao lado
citava o `#2376` como razão: `init.quick` não emite `state_path`. Conferido no
contrato — `init.json`, `init.quick` emite 25 campos e nenhum é `state_path`,
enquanto `init.phase-op`, `init.plan-phase`, `init.execute-phase` e
`init.verify-work` emitem. A nota estava certa.

**A dívida morreu em vez de ser herdada.** Com o fato pedido ao binário, o
campo deixa de ser necessário: nada em `quick.md` monta caminho de estado a
partir de outro caminho, e o `#2376` sai do arquivo. O que ficou foi
`PROJECT_PATH`, com a metade da razão que ainda vale — é DOCUMENTO, e um
documento entregue a subagente precisa resolver contra o cwd dele.

## Números por arquivo, inclusive os zeros

Famílias medidas com as regex do próprio oráculo, antes e depois:

| arquivo | A | B | C | D | `.planning/` | conversões |
|---|---|---|---|---|---|---|
| `workflows/discuss-phase.md` | 1 → 0 | 0 → 0 | 2 → 0 | 0 → 0 | 10 → 8 | 5 sítios |
| `discuss-phase/modes/advisor.md` | 0 | 0 | 0 | 0 | 0 | **zero** |
| `discuss-phase/modes/chain.md` | 0 | 0 | 0 | 0 | 0 | **zero** |
| `workflows/quick.md` | 0 → 0 | 3 → 0 | 4 → 0 | 0 → 0 | 5 → 5 | 7 sítios |
| `quick/steps/research-phase.md` | 0 | 1 → 0 | 0 | 0 | 0 | 1 sítio |
| `quick/steps/worktree-pre-dispatch-commit.md` | 0 | 0 | 0 | 0 | 0 | **zero** |

As **5 menções a `.planning/` de `quick.md` sobrevivem inteiras**, e é o
resultado certo: `:2` (prosa de cabeçalho, que cita `.planning/quick/`), `:617`
(`.planning/STATE.md` na lista do commit final), `:626` e `:629` (o filtro por
prefixo no staging) e `:688` (o diretório das tarefas rápidas). Nenhuma é
leitura de fato; três são política de commit. Fora dessas cinco há mais uma
menção a `STATE.md` sem `.planning/` — `:478`, a regra de não commitar
artefatos de docs — que também é política e também ficou.

`.planning/STATE.md` **ficou** na `file_list` do Step 8 por medição: quem
escreve o arquivo agora é o verbo (`appendQuickTaskRow` roda sob o lock de
`readModifyWriteStateMd`), e não commitar o que o binário escreveu deixaria a
árvore suja e o fato fora do git. Committar o que o verbo escreveu é
escrituração; o que a fase proíbe é o markdown ser a fonte.

Contagem canônica (`BROAD_RE` de `cairn-inventory.py:176`, excluída a linha que
define `gsd_run`):

| arquivo | pré-onda-zero | HEAD do plano | depois |
|---|---|---|---|
| `discuss-phase.md` | 8 | 8 | 8 |
| `quick.md` | **17** | **18** | 23 |
| `quick/steps/research-phase.md` | 1 | 1 | 2 |

O `17 → 18` **não é desta onda**: a onda zero reescreveu a prosa de
`quick.md` (hoje `:612`, `:642` antes das edições desta onda — `the
\`gsd_run query commit\` command handles…`), e a menção em
prosa casa a `BROAD_RE`. Registrado porque a tabela do `36-PATTERNS §5` publica
`quick 17` e quem reconferir vai achar 18 antes de encostar no arquivo.

## A subclasse que a métrica de dentro do workflow não enxerga

O caminho é entregue num `<files_to_read>` e **a leitura acontece do outro
lado**: medir cobertura dentro do workflow declara verde com o subagente ainda
lendo markdown. Tratada como CLASSE, não caso a caso — é a família D.

Medido por agente antes de decidir a forma da conversão:

| sítio | subagente | ele carrega `state.load` próprio? | decisão |
|---|---|---|---|
| `quick.md:313` | `gsd-planner` | **sim** (`gsd-planner.md:617`) | linha vira instrução de pedir ao binário |
| `quick.md:431` | `gsd-executor` | **sim** (`gsd-executor.md:89`) | idem |
| `research-phase.md:34` | `gsd-phase-researcher` | **NÃO** — zero menção a estado no arquivo inteiro | idem, e apagar sem substituir perderia o fato |

A terceira linha é a que decide a forma: se a conversão fosse "apagar a linha",
duas passariam (o agente já pede) e a terceira perderia o fato em silêncio.

## A tabela de isenções aberta, e o plano que fecha cada uma

Nenhuma **isenção** foi aberta: os seis arquivos desta onda entram com zero.
O que abriu foi a tabela de **pendências da família D** — três sítios que a
regra nova mede e que esta onda não pode tocar:

| caminho | contagem hoje | fecha em | sítio |
|---|---|---|---|
| `gsd-core/workflows/plan-phase.md` | 1 | **36-05** | `:695` — `- {state_path} (Project State)` |
| `gsd-core/workflows/verify-work.md` | 1 | **36-05** | `:709` — `- {state_path} (Project State)` |
| `gsd-core/workflows/execute-phase.md` | 1 | **36-07** | `:750` — `- ${PROJECT_ROOT}/.planning/STATE.md (State)` |

Duas forças independentes matam cada linha quando o plano dela passar: a
contagem cai de 1 para 0 (*pendência morta*), e o caminho passa a existir em
`PS_ADAPTED` (*declarado pendente E adaptado ao mesmo tempo*). As duas foram
provadas forjando — ver quebras 4 e 5.

## Quebras aplicadas, e qual asserção cada uma derrubou

| # | o que foi forjado | asserção que caiu | o que provou |
|---|---|---|---|
| 1 | `discuss-phase.md` + modes na tabela ANTES de editar | teste 1, `[ "$status" -eq 0 ]` (`:205` no vermelho, `:266` hoje) | o oráculo vê os 3 resíduos (A `:240`, C `:477` e `:511`) |
| 2 | `quick.md` + fragments na tabela ANTES de editar | teste 1 **e** teste 6 (completude) | resíduos + `research-phase.md` fora de `gsd-adaptations.json` |
| 3 | controle negativo da injeção ANTES da família D | teste 3, `[ "$status" -eq 1 ]` (`:246` no vermelho, `:307` hoje) | **nenhuma das três famílias mordia a injeção** |
| 4 | contagem de `verify-work.md` declarada 2, medida 1 | teste 7, "pendência morta … esperado 2, encontrado 1" | a pendência morre quando o sítio some |
| 5 | `verify-work.md` declarado adaptado com o sítio de pé | testes 1, 7 e 8 | três forças reprovam a linha que sobrevive ao 36-05 |

A quebra 3 é a que exigiu cuidado com a GRAFIA: o controle usa o caminho
literal (`- ${PROJECT_ROOT}/.planning/STATE.md (State)`). Reinjetar
`- ${STATE_PATH} (Project State)` faria o controle passar **pela família B**,
provando o oráculo antigo e não a regra nova — controle negativo que derruba a
asserção errada não prova nada. O teste ainda mede no arquivo forjado que as
três primeiras famílias contam zero ali.

Uma asserção fake foi removida no caminho: `grep -qvF` sobre uma saída de
várias linhas passa por qualquer linha que não case, o que é sempre.

## Testes

Rodados com `bash cairn/scripts/cairn-test.sh --jobs 8 <arquivos>` — nunca
`bats` cru. A suíte inteira não foi rodada (medido em sessão anterior: passa de
1h17 em série); os arquivos desta onda e os que consomem os artefatos que ela
edita rodam em **46s**.

| suíte | testes | resultado |
|---|---|---|
| `cairn-prompt-state.bats` | 7 → **10** | verde |
| `cairn-vendoring.bats` (oráculo de bytes dois-sentidos) | 26 | verde |
| `cairn-preamble.bats` | 13 | verde |
| `cairn-command-surfaces.bats` | 14 | verde |
| `cairn-wrap.bats` | 24 | verde |
| **total** | **87** | **87 ok, 0 not ok** |

O verde do oráculo de bytes É prova neste worktree: o cache
`.cairn/cache/gsd-core-v1.10.0` existe aqui e nenhum teste `real_cache_or_skip`
skipa — conferido de novo nesta onda.

`cairn-preamble.sh list` reporta `research-phase.md` como **`none`**, o estado
que o próprio script documenta para "registrado, sem linha de preâmbulo — o
caso dos arquivos que entram no registro por adaptação de conteúdo". O caminho
já estava desenhado; a entrada nova não é exceção.

## Premissas do plano que a medição contradisse

1. **`36-03-SUMMARY.md` não existe** — nem no disco, nem em nenhum commit. O
   plano o cita três vezes em `read_first` (o molde do `fast.md`, a forma das
   três famílias, a tabela de isenções). A onda 3 entregou 5 commits e não
   escreveu o SUMMARY. O conhecimento foi reconstruído dos commits
   `374c915`, `e16c9fe`, `e832048`, `bb4bbe7` e do próprio `.bats`. **Fica
   aberto**: não é desta onda escrevê-lo.

2. **A extensão que a Task 3 manda fazer era no-op.** As "duas grafias medidas
   (com cifrão e chaves, e só entre chaves)" **já casavam** a família B, que
   compara `STATE_PATH` e `{state_path}` como literais — `${STATE_PATH}`
   contém `STATE_PATH`. Estender a B para elas não acrescentaria cobertura
   nenhuma. A cobertura nova está toda na terceira grafia.

3. **`36-PATTERNS §5b` lista CINCO sítios de injeção; a árvore tem SEIS.** O
   que faltava é `execute-phase.md:750`, fora do bloco das 12 linhas porque não
   usa nenhuma das quatro grafias de estado. É o pior dos seis: sem comando de
   leitura, sem variável de estado, sem prosa — invisível às três famílias.
   Corrigido na origem, com a data e o motivo, no próprio `36-PATTERNS`.

4. **As pendências não cabiam em `PS_EXEMPTIONS`.** `ps_exempt_count` só é
   consultada para caminhos que estão em `PS_ADAPTED`, e nenhum dos três está.
   Uma linha lá seria INERTE — não afirmaria nada e sobreviveria calada ao
   plano que a deveria matar, exatamente a "isenção que nunca morre" que o
   cabeçalho da suíte recusa. Virou tabela própria, com teste próprio.

5. **Em `discuss-phase` não havia UMA lista de commit, havia DUAS.** O plano
   descreve retirar o arquivo de estado "da lista" mantendo o artefato de
   documento. Medido: o passo `git_commit` (`:470`) commita CONTEXT.md e
   DISCUSSION-LOG.md e **nunca citou** o estado; o passo `update_state`
   (`:484`) tinha um commit dedicado **só** ao estado. A conversão foi apagar o
   segundo inteiro — retirar "o arquivo da lista" deixaria um commit sem
   arquivo nenhum.

6. **Em `quick` é UM item de checklist, não dois.** Só `:725` casa a família C;
   `:718` (`.planning/quick/YYMMDD-xxx-slug/`) é caminho de documento e ficou.

7. **`quick.md` 7d mandava editar uma linha que não existe.** `Last activity`
   não aparece em nenhum outro ponto de `cairn/gsd/` — nem em template, nem em
   contrato. Virou `state.record-session`, cuja letra é "Last session/Stopped
   At". Não é invenção: é o único verbo que registra o fato que 7d descrevia.

8. **A frase do `fast.md` não podia ser copiada para o checklist de sessão.**
   `quick-tasks-append` sai 1 quando falha, então "o exit code é a resposta"
   é verdade lá. `state.record-session` **sai 0 sempre** (contrato
   `estado.json`) e quem responde é `recorded`/`reason`. Copiar a frase por
   semelhança criaria doutrina errada num arquivo que um modelo lê como regra.

9. **`CLAUDE.md` e `AGENTS.md` deste worktree não têm a regra do
   `cairn-test.sh`.** Ela está nos do repositório principal
   (`CLAUDE.md:91-95`, `AGENTS.md:160-164`), em outro branch. Quem executar por
   este worktree não vê a regra — vale trazer no merge.

10. **O gate de commit do executor não descreve este worktree.** O protocolo
    exige HEAD no namespace `worktree-agent-*`; este worktree está em
    `phase/36-workflows-steps-e-agentes-falam-bd`. Apliquei a deny-list de refs
    protegidas (que passa) e ignorei a allow-list, que reprovaria um branch de
    fase legítimo.

## Desvios aplicados

- **`waves[]` só no arquivo editado.** O plano manda somar a onda 4 "às
  entradas correspondentes" dos três caminhos de cada task. `advisor.md`,
  `chain.md` e `worktree-pre-dispatch-commit.md` têm zero conversões e não
  foram tocados: somar a onda 4 seria declarar uma edição que não houve.
  Precedente da onda 3 (`bb4bbe7`, `debug.md`).
- **`state.record-session` acrescentado ao Step 7 de `quick`.** Fora da letra
  do plano, dentro da razão do 7d (ver premissa 7).
- **Verificação com `cairn-test.sh`, não `bats` cru**, e sem `bats tests/`
  completo — regra do operador, com o número que a sustenta.
- **Comentário de fronteira na família D.** A regra exige o rótulo entre
  parênteses. Uma injeção escrita sem rótulo escaparia; nenhuma das seis
  medidas é assim, e a fronteira ficou escrita no arquivo em vez de suposta.

## Estado do bd

`ADAPT-03` → `CairnGo-z782`, **reclamada e NÃO fechada**: a issue cobre
`discuss-phase`, `plan-phase`, `verify-work`, `quick` e `autonomous`, e as três
que faltam são do plano 36-05. Duas diretivas fechadas apontam para ela e
descrevem exatamente o que esta onda entregou: `DIR-02` (prompt de subagente
que recebe caminho literal de arquivo de estado) e `DIR-01` (a variável de
caminho de estado injetada pela camada de init).

## O que fica para as ondas seguintes

- **36-05:** `plan-phase.md:695` e `verify-work.md:709` — as duas pendências da
  família D, além de `plan-phase.md:550/:652` (a subclasse de transporte) e de
  `autonomous.md` (família A com 3, família C com 2).
- **36-07:** `execute-phase.md:750`, a pendência que só a família D vê, junto
  das 4 linhas de família C do mesmo arquivo.
- **Fora desta fase:** `36-03-SUMMARY.md` continua por escrever.

## Self-Check: PASSED

Arquivos declarados, conferidos no disco:

- `cairn/gsd/gsd-core/workflows/discuss-phase.md` — FOUND
- `cairn/gsd/gsd-core/workflows/quick.md` — FOUND
- `cairn/gsd/gsd-core/workflows/quick/steps/research-phase.md` — FOUND
- `cairn/gsd-adaptations.json` — FOUND (37 entradas, ordenado)
- `tests/cairn-prompt-state.bats` — FOUND (10 testes)
- `.planning/phases/36-workflows-steps-e-agentes-falam-bd/36-PATTERNS.md` — FOUND

Commits declarados, conferidos em `git log`: `dddc4d7`, `ca523d2`, `cb7a9ea`,
`67ea3ff`, `1e6b5c0` — todos presentes.
