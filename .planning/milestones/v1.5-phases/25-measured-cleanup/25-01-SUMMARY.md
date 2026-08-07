---
phase: 25-measured-cleanup
plan: "01"
requirement: FIX-04
beads: [CairnGo-64u, CairnGo-dsh, CairnGo-4oq, CairnGo-4p1]
status: complete
---

# Fase 25 Plano 01 — resumo

## O que mudou

`cairn-status.py` responde a "quem pode correr junto" a partir de **três**
fontes de dependência em vez de duas, filtra aresta de bd por tipo, deixa de
tratar fase de ciclo arquivado como bloqueio eterno, distingue índice de plano
de número de fase, e nomeia a fase que existe só como diretório em vez de
mandá-la executar. `cairn-parallel.py` passa o campo novo adiante verbatim e o
imprime no anúncio. `cairn/docs/commands/status.md` documenta as duas mudanças
de contrato.

## Os quatro defeitos, e a asserção que fecha cada um

| Defeito | Medição | Teste |
|---|---|---|
| `CairnGo-64u` (P0) — a prosa do roadmap não era fonte de dependência | 2026-08-05: `batch` anunciou 21 e 22 na mesma rodada com `**Depende de:** Phase 21` escrito sob a fase 22 | `the roadmap's **Depends on** prose blocks the phase, with no PLAN.md and no bd edge` |
| `CairnGo-dsh` (FIX-04, P1) — `discovered-from` contava como bloqueio | 2026-08-03: fase 26 como "waits on phase 9" sobre aresta de procedência, com o bd reportando `[READY]` | `a discovered-from edge records provenance and never blocks` |
| `CairnGo-dsh` (segunda metade) — fase arquivada bloqueia para sempre | a fase 9 saiu do `ROADMAP.md` com o v1.2, nunca entra em `done_set` | `a dependency on a phase the roadmap no longer lists never blocks` |
| `CairnGo-4oq` (P2) — diretório de fase lido como entrada de roadmap | 2026-08-05: `30-did-it-land/` com um `30-CONTEXT.md` voltou em `runnable`; só o teto de concorrência a segurou | `a phase that exists only as a directory is not runnable, and is named` |
| `CairnGo-4p1` (P1, achado aqui) — índice de plano lido como número de fase | 2026-08-07: `22-02-PLAN.md` com `depends_on: ["01"]` produziu `depends_on: [1, 2, 3, 4, 21]` no `cairn-status.py` do HEAD | `a plan waiting on a PLAN of its own phase is not waiting on a phase` |

## O quarto defeito, e por que ele conta

Ele não é uma das dezoito. Apareceu ao medir o `depends_on` da fase 22 para
conferir o conserto do `CairnGo-64u`, e é da mesma família — uma superfície
afirmando com confiança uma dependência cuja origem ela não checou. Aqui o erro
não é deixar de ler a fonte: é ler a fonte certa com a regra errada, tratando
índice de plano como número de fase porque as duas coisas são dígitos.

A medição foi feita com o `cairn-status.py` do HEAD (`8dd2dfd`) extraído para
fora da árvore de trabalho, para não depender do conserto em curso:

```
$ python3 <HEAD:cairn-status.py> --json | jq '.phases[]|select(.number==22)'
depends_on: [1, 2, 3, 4, 21]
blocked_by: [1, 2, 3, 4]
```

Os dois defeitos se somam: `blocked_by` **manteve** as quatro, porque fase de
milestone arquivado nunca entra em `done_set`. Ficou invisível só porque as
quatro estão completas; com qualquer uma pendente, a fase 22 leria bloqueada
por trabalho com o qual não tem relação. Registrado como `CairnGo-4p1`.

## Cada metade negativa, e por que ela existe

Um teste que passaria com a feature removida não é prova. Três guardas têm par:

- `a bare number with no plan of that index is still read as a phase` — sem
  ele, "nenhum número cru é fase" passaria.
- `a blocks edge alongside a discovered-from edge still blocks` — sem ele,
  "nada bloqueia nunca" passaria.
- `a phase named in the roadmap keeps its directory and stays runnable` — sem
  ele, "todo diretório é inconsistente" passaria.

## A prova por quebra

Sete guardas, sete quebras reais no fonte, cada uma rodada isolada. As quebras
de `cairn-status.py` correram numa cópia da árvore fora do repositório, porque
a suíte do repositório estava rodando ao mesmo tempo e um agente que edita o
arquivo que outro está medindo produz laudo sobre um arquivo que já não existe.
A restauração foi sempre de cópia, nunca `git checkout`, e o script conferiu
byte a byte no fim.

| Guarda | O que foi removido | Asserção que ficou vermelha |
|---|---|---|
| G1 | a prosa do roadmap sai da união de fontes em `phase_model()` | `[ "$(… phase_field 4 depends_on)" = "[3]" ]` |
| G2 | `DEP_DECLARATION_END` deixa de cortar declaração de justificativa | `[ "$(… phase_field 4 depends_on)" = "[]" ]` |
| G3 | o filtro de `type` sai de `dep_target_ids()` | `[ "$(… phase_field 4 depends_on)" = "[]" ]` |
| G4 | `blocked_by` volta a ignorar o conjunto `known` | `[ "$(… phase_field 4 blocked_by)" = "[]" ]` |
| G5 | `parallelism()` deixa de tirar `in_roadmap: False` de `pending` | o bloco `python3 -c` que afirma `9 not in par["runnable"]` |
| G6 | o descarte de índice de plano sai de `plan_depends_on()` | `[ "$(… phase_field 4 depends_on)" = "[]" ]` |
| G7 | `cmd_batch` deixa de repassar `inconsistent` | `jq '.inconsistent \| length' returned '0', expected '1'` |

## Medido, e contrariou o que estava escrito

Cinco premissas do contexto ou das issues que a medição de hoje não sustenta.
Nenhuma invalida um conserto; todas mudam o que se pode afirmar sobre ele.

1. **`CairnGo-64u` diz "duas dependências declaradas, as duas ignoradas". Só
   uma se reproduz hoje.** Medido com o `cairn-status.py` do HEAD: a fase 27
   sai `depends_on: []` com `**Depende de:** Phase 23` escrito sob ela — essa é
   a metade que se reproduz. A fase 22 sai `depends_on: [..., 21]` **já no
   HEAD**, porque uma aresta do bd foi criada depois da medição de 2026-08-05 e
   cobre justamente essa dependência. A prosa seguia sem ser lida nos dois
   casos; o efeito visível sobrevivia num só.

2. **`CairnGo-4oq` não se reproduz mais ao vivo.** A issue mede
   `grep -c 'Phase 30' .planning/ROADMAP.md` → `0`. Hoje devolve **6**: a fase
   30 entrou no roadmap durante o ciclo. O defeito era real e o conserto vale,
   mas a prova é de fixture, não de repositório — e é por isso que o teste
   constrói a sua própria fase 9 no disco em vez de apontar para a 30.

3. **Os números de linha das issues envelheceram, os do plano não.**
   `CairnGo-dsh` cita `dep_target_ids()` na "linha ~900" e o `blocked_by` na
   "linha 1083"; no HEAD são **1259** e **1450**. O `25-01-PLAN.md` cita
   `cairn-status.py:1285-1289` para o docstring do `issue_phase_deps`, e essa
   está exata. É o sexto precedente medido neste repositório de número à mão
   que envelheceu — os cinco anteriores estão registrados no docstring do
   `cairn-doctor.py`.

4. **A afirmação do comentário de `NON_BLOCKING_DEP_TYPES` foi conferida, e
   está certa.** Contei as arestas do `bd list --all --json` hoje:
   `{'blocks': 42, 'discovered-from': 8}`, 50 no total, exatamente os dois
   tipos que o comentário diz existirem. Registro aqui porque a premissa era
   verificável e ficaria de pé sem verificação nenhuma.

5. **A fase 25 tem um quarto defeito da mesma família, e ele não é uma das
   dezoito.** O `25-CONTEXT.md` fecha o escopo em "dezoito defeitos que já
   vieram com a medição junto". O `CairnGo-4p1` foi achado no meio do conserto,
   medido, e registrado — o mapa de beads passa a ter dezenove.

## Suítes

Rodadas sobre a árvore principal, com o conserto aplicado. As quatro últimas
correram em paralelo depois de a versão serial se mostrar cara demais em tempo
de parede; são arquivos independentes, cada um com o seu `BATS_TEST_TMPDIR`.

| Suíte | Papel | Resultado |
|---|---|---|
| `tests/cairn-phase-model.bats` | arquivo tocado — carrega os oito testes novos | 38/38 |
| `tests/cairn-parallel.bats` | quem consome — carrega o teste novo do `batch` | 42/42 |
| `tests/cairn-parallel-autonomous.bats` | quem consome o anúncio | exit 0 |
| `tests/cairn-corroboration.bats` | quem consome o `disk_state`/`depends_on` | 22/22 |
| `tests/cairn-board-invariance.bats` | os sete renders de referência da fase 20 (D-08) | 11/11 |
| `tests/cairn-status.bats` | arquivo tocado — regressão do render | 57/57 |

Nenhum render de referência da fase 20 se moveu: o `inconsistent[]` novo entra
no `--json` e no anúncio do `batch`, e nenhuma das superfícies do board o
imprime quando está vazio.

## O que fica para os planos seguintes

Este plano fecha o critério 4 do roadmap e a parte de `cairn-parallel` do
critério 3 (nenhum código de saída de caminho verde mudou). Os outros oito
critérios seguem abertos, com o `25-02-PLAN.md` já escrito para o critério 6 e
o FIX-05.
