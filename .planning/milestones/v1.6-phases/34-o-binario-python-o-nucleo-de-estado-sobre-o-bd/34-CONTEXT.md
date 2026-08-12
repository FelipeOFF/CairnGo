# Phase 34: O binário python, o núcleo de estado sobre o bd - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Os verbos de ESTADO passam a responder do bd: estado (state.*), roadmap/phase,
worktree, init e misc, na forma dos contratos da fase 31, com as três regras que
a medição do bd impôs (label projetado como única chave de consulta; toda
transição via set-state com ator e motivo; falha nomeada para fato ausente).
Famílias de checagem e órfãos ficam na 35. O harness da 33 (goldens + diferencial)
é herdado, não reinventado.

</domain>

<decisions>
## Implementation Decisions

### Onde as famílias vivem (a decisão adiada da 33, agora tomada)
- **D-01:** Scripts irmãos por grupo: `cairn-gsd.py` segue dispatcher/roteador; as famílias pesadas viram irmãos invocados por exec — `cairn-gsd-state.py` (estado + roadmap/phase) e `cairn-gsd-init.py` (init + worktree + misc). Nenhum arquivo passa de ~1.5k linhas; o precedente cairn-doctor (3.9k) é teto desconfortável, não alvo. — **Reversibility:** costly — o roteamento do dispatcher e o harness apontam pros irmãos; fundir depois toca os dois.

### Vocabulário de dimensões e labels (CORE-02, schema permanente)
- **D-02:** Dimensões semânticas mínimas via `bd set-state`: `phase` (número corrente), `phase_status` (planned/executing/verified/complete), `plan` (NN-MM corrente), `verification` (passed/failed/pending), `session` (última atividade). Labels projetados legíveis (`phase_status:verified`); consulta sempre `bd query "label=dim:valor"`. Os verbos gsd MAPEIAM para essas dimensões no dispatcher; o vocabulário do upstream não vira schema. — **Reversibility:** one-way — labels projetados são o índice de consulta permanente do bd deste e de todo repo que adotar o cairn; renomear dimensão depois exige migração de labels em todo acervo. Racional: é exatamente o schema que o veredito do bd (metadata aninhado não consultável) exige decidir antes de código.

### Claude's Discretion
- Partição exata dos verbos misc entre os dois irmãos, registrada no plano.
- Forma do mapeamento verbo→dimensão (tabela no próprio script ou em cairn/gsd/contracts/, desde que uma fonte só).
- Cenários de golden para os verbos de estado (herdam o layout da 33).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `cairn/gsd/contracts/` — contratos por verbo (estado, roadmap-phase, worktree, init, misc) com source_ref; a forma de payload vem daqui (CORE-01).
- `.planning/research/v1.6-transplante-gsd.md` — §4 (famílias e reuso: bookkeep 2.006, journal 1.482, status 4.532), regras do bd (set-state, labels, rc 0 silencioso), caso current_phase 18.
- `.planning/ROADMAP.md` — Goal da Phase 34 e as três regras não opcionais.
- `cairn/scripts/cairn-gsd.py` + `tests/cairn-gsd.bats` + `tests/fixtures/gsd-goldens/` — o dispatcher e o harness da 33 que esta fase estende.
- `31-04/33-*` SUMMARYs da fase — o init re-derivado (delta −10 vs ~500) e as descobertas (verbos fantasma, summaries_total/uat_path nunca emitidos).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bd set-state <id> <dim>=<val> --actor --reason` cria event bead + label projetado (provado no research; a auditoria SÓ existe por esse caminho — `bd update` direto vira root sem motivo).
- `cairn-bookkeep.py`, `cairn-status.py`, `cairn-lease.py`: parsing e semântica de fase/plano que os verbos de estado reaproveitam por cópia de forma.
- Harness da 33: goldens por provenance, `--record` skip-gated, seam de reuso provado por teste.

### Established Patterns
- Falha nomeada (CORE-04): o dispatcher já falha nomeando família/fase para verbos das fases seguintes — os verbos de estado herdam o padrão para FATO ausente ("o bd não tem phase_status para este repo; rode X").
- Consulta nunca por metadata aninhado (rc 0 silencioso, medido).

### Integration Points
- A fase 36 aponta os preâmbulos shim pro dispatcher; a 35 acrescenta a família de checagem nos mesmos moldes.
- O caso de reentrada `current_phase 18` (state.record-metric lendo prosa obsoleta) é o teste canônico de idempotência do CORE-03.

</code_context>

<specifics>
## Specific Ideas

- Migração de dados fora de escopo: verbo de estado num repo sem fato no bd FALHA nomeando o fato e o comando que o cria (CORE-04); nunca lê markdown como fallback (duas fontes é a doença que o milestone mata).
- Ganho de token: se medido, medido no contexto entregue; zero é resultado publicável (regra herdada do roadmap).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 34-o-binario-python-o-nucleo-de-estado-sobre-o-bd*
*Context gathered: 2026-08-10*
