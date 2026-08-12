# Phase 20: Group model - Context

**Gathered:** 2026-08-03
**Status:** Ready for planning

<domain>
## Phase Boundary

O modelo passa a saber a que grupo cada coisa pertence. **Nenhum render muda** —
o board ao fim desta fase é byte a byte o que era no começo.

Requisitos: BOARD-01. Issues bd: ver `20-BEADS-MAP.md`.

Herdado e **não reaberto**: `phase_model()` é a leitura única de que as três
superfícies (terminal, `--json`, HTML) dependem, e a fase 13 estabeleceu o padrão
de estendê-la sem mexer em chave que consumidor algum lê. `disk_state` mantém seus
quatro valores por contrato — `phase_next_command()` indexa um dict cru nele, e um
quinto valor é `KeyError` direto.

</domain>

<decisions>
## Implementation Decisions

Esta fase foi aberta em modo autônomo. As decisões abaixo são **Claude's
Discretion** salvo onde marcado, e vêm do discuss que o Felipe fez sobre o board
em 2026-08-03, cujas quatro decisões já estão travadas.

### O que é um grupo

- **D-01: grupo é `{tipo, chave, rótulo, itens}`, e existem dois tipos** —
  `milestone` e `unphased`. Milestones abertos primeiro, na ordem em que o roadmap
  os lista; o grupo `unphased` sempre por último.

  Vem direto da decisão D-03 do discuss do Felipe: *milestones abertos primeiro, um
  grupo "Sem milestone" depois, e o cabeçalho admitindo quando não há ciclo aberto*.

  Rejeitado grupo por prioridade: foi exatamente a reclamação que abriu este ciclo —
  uma lista ordenada por prioridade sem hierarquia não deixa saber quem é quem.

### Onde a estrutura vive

- **D-02: chave nova no topo do modelo, ao lado das existentes, nunca dentro
  delas.** Um consumidor que hoje lê `phases[]` continua lendo `phases[]` com a
  mesma forma; quem quiser a hierarquia lê a chave nova.

  A razão é o critério de sucesso 3, e ele não é decoração: a suíte atual tem 55
  testes de `cairn-status` que leem essas chaves. Se a estrutura de grupos fosse
  aninhada dentro de `phases[]`, ela mudaria a forma de algo que três superfícies e
  55 testes consomem, e a fase deixaria de ser invisível.

### O grupo vazio

- **D-03: um grupo sem itens não é emitido, e a ausência de milestone aberto produz
  zero grupos de milestone** — nunca um grupo com o rótulo do último ciclo
  arquivado.

  Isto é o critério de sucesso 2 e ele existe porque o defeito foi **medido**: em
  2026-08-03, dez minutos após o v1.4 ser arquivado, o board ainda anunciava
  `MILESTONE v1.4`. Dizer o nome errado é pior que não dizer nada, porque parece
  informação.

### A prova de que nada mudou

- **D-04: a prova é a saída, não a intenção.** Um teste captura o render de um
  fixture antes da mudança, guarda como referência commitada, e compara byte a byte
  depois.

  Rejeitado "os testes existentes continuam passando" como prova: eles cobrem o que
  já cobriam, e uma mudança de forma no lugar errado pode passar por todos e ainda
  assim alterar espaçamento, ordem ou truncamento.

### Claude's Discretion

- Nome exato da chave nova e dos campos de cada grupo.
- Se o grupo `unphased` carrega contagem própria no modelo ou só a lista.
- Como o modelo representa milestone aberto quando não há nenhum (lista vazia
  versus chave ausente), desde que a D-03 seja respeitada.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O que o discuss deste ciclo já travou
- `.planning/ROADMAP.md` § Phase 20 e § Phase 21 — a 21 é a consumidora imediata
  deste modelo, e os símbolos dela já estão decididos e medidos
- As quatro decisões do discuss de 2026-08-03: lista agrupada no lugar do kanban;
  `--plain` intocado como contrato de máquina; milestones primeiro e backlog por
  último; símbolos de largura simples

### Código
- `cairn/scripts/cairn-status.py` — `phase_model()`, `pending_phases()`,
  `parallelism()`, `next_commands()`; e `render_board()`, que **não** muda aqui
- `tests/cairn-status.bats` — 55 testes que leem as chaves do modelo
- `tests/cairn-phase-model.bats` — 28 testes sobre o modelo em si
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `phase_model()` já lê roadmap, disco, bd e git numa passada; agrupar é
  reorganizar o que ela já tem, não buscar dado novo.
- `issue_phase_ns()` já mapeia issue para número de fase pelos labels.
- A fase 13 já provou o padrão de acrescentar chaves ao modelo sem quebrar
  consumidor.

### Established Patterns
- Um teste que passaria com a feature removida não é prova.
- Chave existente nunca muda de nome, de tipo ou de significado.

### Integration Points
- `cairn/scripts/cairn-status.py` — só o modelo.
- `tests/cairn-status.bats` e `tests/cairn-phase-model.bats` — testes novos.
- **Nada mais.** Se esta fase tocar um render, ela saiu do escopo.

</code_context>

<specifics>
## Specific Ideas

- **O pré-flight deste próprio run achou um defeito que esta fase precisa não
  repetir.** A fase 26 aparece bloqueada pela fase 9, um ciclo arquivado dois
  milestones atrás, porque `dep_target_ids()` coleta toda aresta sem olhar o tipo e
  a linha 1083 filtra contra um conjunto do qual fase arquivada nunca faz parte.
  Está registrado como FIX-04 e é conserto da fase 25, **não desta** — mas o modelo
  de grupo lê as mesmas estruturas, e agrupar por milestone sem herdar essa
  confusão entre ciclo ativo e ciclo arquivado é parte do trabalho.

</specifics>

<deferred>
## Deferred Ideas

- Render agrupado — é a fase 21, e esta fase termina com o board inalterado de
  propósito.
- Consertar o cabeçalho que anuncia milestone arquivado — é BOARD-04, fase 22.
- Consertar o bloqueio por fase arquivada — é FIX-04, fase 25.

</deferred>

---

*Phase: 20-Group model*
*Context gathered: 2026-08-03*
