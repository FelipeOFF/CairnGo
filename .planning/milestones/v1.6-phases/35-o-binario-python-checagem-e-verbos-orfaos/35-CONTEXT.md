# Phase 35: O binário python, checagem e verbos órfãos - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A família de checagem (dispatcher `check` + subcommands, verify.plan-structure,
avaliador de predicado do ADR-2008, uat.*, verification.status nas DUAS grafias)
e os 5 verbos órfãos (audit-open, review-lane, agent.classify-failure,
task.is-behavior-adding, run-with-timeout) respondem em python, na forma dos
contratos da fase 31, fechando o universo 87/87. A baseline do cairn-doctor é
fixada por commit antes de qualquer evolução. Workflows/steps/agentes NÃO mudam
aqui (fase 36); plugin não muda (fase 37).

</domain>

<decisions>
## Implementation Decisions

### Onde a checagem e os órfãos vivem
- **D-01:** Terceiro irmão `cairn-gsd-check.py` nasce com a família de checagem
  E os 5 órfãos, no mesmo molde exec do D-01 da fase 34 (os.execv preservando
  argv/env/exit), teto próprio de ~1.5k linhas (wc -l). `cairn-gsd-state.py`
  (1499/1500) e `cairn-gsd-init.py` (1325/1500) ficam intocados salvo o
  roteamento; o dispatcher só ganha as rotas e perde a constante
  `ORPHANS_PHASE_35` da lista de exclusão (os órfãos agora têm dono). —
  **Reversibility:** costly — mesmo custo do D-01 da 34 (roteamento + harness
  apontam pro irmão).

### Claude's Discretion
- Partição interna do arquivo (checagem primeiro, órfãos depois) e uso de
  `cairn_gsd_render.py` se o teto apertar.
- Forma do diferencial do predicate ADR-2008 (CHECK-02): cenários no harness
  da 33/34, comparação por forma contra o gsd-tools real da tag.
- Semântica dos órfãos: fiel ao extraído na 31 (REM-04), heurísticas incluídas;
  divergência consciente vai em divergences.json com motivo, nunca silenciada.
- Como fixar a baseline do doctor (CHECK-04): registro do commit + prova de
  que a fase não alterou cairn-doctor.py, na forma que o plano escolher.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `cairn/gsd/contracts/checagem.json` — os 11 verbos com source_ref; grafia
  dupla de verification.status CONTRATADA (notes do verbo).
- `cairn/gsd/contracts/misc.json` — os 5 órfãos com semântica extraída do
  bundle bakeado (REM-04, proveniência declarada).
- `cairn/scripts/cairn-gsd.py` — dispatcher; `ORPHANS_PHASE_35` (L139) é a
  constante que esta fase esvazia; molde exec dos irmãos.
- `cairn/scripts/cairn-gsd-state.py` + `cairn-gsd-init.py` +
  `cairn_gsd_render.py` — os irmãos da 34 (molde de estrutura, render de
  envelope como fonte única).
- `tests/cairn-gsd.bats` + `tests/fixtures/gsd-goldens/` — harness: goldens
  derived-from-contract, fixture.bd, masks por valor, guard de cobertura
  derivado (comm dois-sentidos).
- SUMMARYs 34-01..34-05 — desvios e descobertas (fantasmas respondem exit 1
  do contrato; guard só precisa somar a família nova ao filtro).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Harness completo da 33/34: fixture.bd (bd real em mktemp + seeds com token
  `@id`), fixture.git_commit, goldens por forma, `--record` skip-gated.
- Guard de cobertura: deriva universo do inventário × `--list-implemented`
  agregado; a 35 soma a família checagem ao filtro e implementa os 16 que
  faltam (87 − 71).
- `cairn_gsd_render.py`: envelope medido, fonte única — o terceiro irmão
  consome, não duplica.

### Established Patterns
- Falha nomeada para fato ausente com o comando que o cria (CORE-04, herdado).
- Documento vs fato: gates leem artefatos de fase (documento) e fatos do
  portador via label projetado — nunca prosa de STATE.md.
- Verbos de checagem devolvem veredito no payload (passed/active/block),
  NUNCA no exit code (exit 0 = gate avaliado; contrato).

### Integration Points
- Fase 36 aponta os preâmbulos dos workflows pro dispatcher — a superfície
  desta fase precisa estar completa (87/87) antes.
- CHECK-04: baseline do doctor fixada ANTES de evolução; a fase 37 é quem
  ensina o doctor a validar o runtime vendorizado.

</code_context>

<specifics>
## Specific Ideas

- As duas grafias (`verification.status` e `verification status`) caem no
  mesmo handler por normalização no primeiro token — igual ao upstream
  (gsd-tools.cjs L3826-L3835).
- run-with-timeout: semântica do bundle (REM-04) — subprocess com timeout e
  contrato de exit; nunca "esperar evento".
- Zero escrita sob `cairn/gsd/` (invariante das fases 32+; gate
  `git status --porcelain cairn/gsd/` vazio).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 35-o-binario-python-checagem-e-verbos-orfaos*
*Context gathered: 2026-08-11*
