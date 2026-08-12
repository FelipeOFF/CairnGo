---
phase: 31-a-baseline-remedida-contra-a-tag
plan: "04"
subsystem: tooling
tags: [gsd-core, contracts, bundle, provenance, init-budget, installer-cut, rem-04, rem-05]

# Dependency graph
requires:
  - phase: 31-a-baseline-remedida-contra-a-tag (plano 01)
    provides: "universo medido do cairn-inventory e cache .cairn/cache/gsd-core-v1.10.0 pinado em 68a04cc"
  - phase: 31-a-baseline-remedida-contra-a-tag (plano 03)
    provides: "83 verbos contratados, shapes de topo dos 9 bundles init.*, tolerancia data-driven verbs_pending_plan_04"
provides:
  - "Os 4 orfaos do bundle contratados no schema pleno com provenance exata de D-04 e source_ref com linhas do gsd-tools.cjs bakeado: run-with-timeout L3452-L3590 (misc), user-story.validate L3179-L3230 (checagem), dispatch-isolation L1624-L1764 e dispatch-should-flatten L1575-L1623 (dispatch-model)"
  - "Distincao provenance <-> bundle testada nos dois sentidos em glob sobre todas as familias"
  - "bundle_shapes em init.json: 9 shapes com campos consumidos (call site arquivo:linha), composicao em src/init.cts e estimativa python com rationale por shape"
  - "measurements.init_budget: 490 linhas (soma por shape, metodo escrito) — substitui o ~500 refutado"
  - "measurements.installer_cut: oficial 10.164 (filtro amplo, comando reproduzivel), estreito 6.049 como componente nomeado — fecha o 7.726 refutado"
  - "Cobertura total sem excecao: universo do inventario == indice do agregado (87 == 87), tolerancia removida do agregado e da suite"
affects: [fase-32-vendoring, fase-33-binario-python, fase-34, fase-35, harness-diferencial]

# Actuals (#2632)
actuals:
  tokens: 10900
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provenance como marcador mecanico de extracao do bundle: a string exata de D-04 identifica unicamente os 4 orfaos; fantasmas carregam provenance propria distinta — o invariante provenance <-> gsd-tools.cjs vale para TODAS as entradas, testado em glob nos dois sentidos"
    - "Consumo de bundle registrado por sitio, nao por suposicao: consumption_sites com arquivo:linha dos blocos Parse/Extract reais + cross-check por teste de que todo campo consumido existe na shape contratada"
    - "Numero de medicao com comando gravado ao lado e re-executado por teste contra o clone real (installer_cut.command re-medido no bats)"

key-files:
  created: []
  modified:
    - cairn/gsd/contracts/misc.json
    - cairn/gsd/contracts/checagem.json
    - cairn/gsd/contracts/dispatch-model.json
    - cairn/gsd/contracts/init.json
    - cairn/gsd/contracts/contracts.json
    - tests/gsd-contracts.bats

key-decisions:
  - "Fantasmas is/plan.task-structure ganham provenance PROPRIA ('verbo fantasma — semantica extraida do caminho Unknown command...'), distinta da string D-04: o sentido inverso 2 do plano exige provenance em toda entrada que aponta o bundle, e a string exata de D-04 segue identificando so os 4 orfaos"
  - "quick-tasks-append repontado de gsd-tools.cjs L1115-L1145 para src/markdown-table.cts L737-L797 (appendQuickTaskRow, a implementacao que as proprias notes ja nomeavam) — nao-orfao nao aponta o bundle; o roteamento inline segue citado em notes"
  - "installer_cut oficial = filtro AMPLO medido (10.164), nao o esperado 10.331: o numero medido vale e o comando ao lado prova (clausula do plano 01); estreito 6.049 reproduziu exato"
  - "Premissa 'shapes lidos por --pick' corrigida no registro: 1 unico sitio usa --pick literal (plan-phase.md:1361); os demais 16 capturam o envelope e parseiam em contexto — gravado em bundle_shapes_note"

patterns-established:
  - "Helpers compartilhados contados UMA vez no primeiro shape que os exige (convencao escrita nas rationales do init_budget) — evita dupla contagem na soma por shape"

requirements-completed: [REM-04, REM-05]

coverage:
  - id: D1
    description: "Os 4 verbos sem fonte em src tem contrato no schema pleno com provenance exata de D-04 e source_ref com linhas no gsd-tools.cjs bakeado do clone"
    requirement: REM-04
    verification:
      - kind: unit
        ref: "tests/gsd-contracts.bats#the 4 bundle-only orphans are contracted in full schema with provenance and bundle source_ref (REM-04, D-04)"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#the aggregate index carries the 4 orphans, each in its assigned family (REM-04)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A distincao orfao/bundle e testada nos dois sentidos: provenance nunca aponta src/, e apontar o bundle exige provenance"
    requirement: REM-04
    verification:
      - kind: unit
        ref: "tests/gsd-contracts.bats#reverse direction 1: no entry carrying provenance points source_ref at src/"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#reverse direction 2: no entry without provenance points source_ref at the baked gsd-tools.cjs"
        status: pass
    human_judgment: false
  - id: D3
    description: "Init re-derivado pelos 9 bundle shapes: campos consumidos por call site, composicao em src/init.cts e estimativa por shape somando 490 com metodo escrito"
    requirement: REM-05
    verification:
      - kind: unit
        ref: "tests/gsd-contracts.bats#init.json carries the 9 bundle_shapes with consumed fields, composition source_ref and a python estimate each (REM-05)"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#measurements.init_budget: total = sum of per_shape, with a written method and date (REM-05)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Instalador descartavel com UM numero oficial, filtro declarado e comando que reproduz o numero no clone"
    requirement: REM-05
    verification:
      - kind: unit
        ref: "tests/gsd-contracts.bats#measurements.installer_cut: official number with declared filter, exact command and narrow component (REM-05)"
        status: pass
      - kind: integration
        ref: "tests/gsd-contracts.bats#real clone: re-running the recorded installer_cut commands reproduces the recorded numbers"
        status: pass
    human_judgment: false
  - id: D5
    description: "A tolerancia do plano 03 morreu: universo do inventario e indice do agregado coincidem sem excecao nomeada"
    requirement: REM-04
    verification:
      - kind: integration
        ref: "tests/gsd-contracts.bats#real universe: every inventory verb has a contract — total coverage, no tolerance (REM-03 + REM-04)"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#the tolerance really died: the aggregate carries no verbs_pending_plan_04 and index == universe count"
        status: pass
    human_judgment: false
  - id: D6
    description: "Backstop: a estimativa de init re-derivada e defensavel — cada um dos 9 shapes tem composicao e contagem justificadas shape a shape, confereiveis contra src/init.cts e os call sites citados"
    requirement: REM-05
    verification: []
    human_judgment: true
    rationale: "Truth marcada verification: backstop no plano (edge-probe, flagged). Veredito do executor: os 17 sitios de consumo foram abertos um a um no clone (blocos 'Parse JSON for:'/'Extract from init JSON:' com linha citada em consumption_sites), a composicao de cada shape confere com o range em src/init.cts (soma 1.229 linhas de handler), o cross-check consumido⊆shape roda por teste, e cada estimativa carrega rationale com a classificacao dos campos (passthrough/existencia/computado/complexo) e a convencao de helpers compartilhados. Julgar se 490 e um orcamento BOM segue sendo juizo humano da fase 34."

# Metrics
duration: 19min
completed: 2026-08-10
status: complete
---

# Phase 31 Plan 04: Órfãos do bundle e os dois números refutados Summary

**Os 4 verbos sem fonte em src contratados do gsd-tools.cjs bakeado com provenance e linha (REM-04/D-04), init re-derivado shape a shape para 490 linhas python (substitui o ~500 refutado), instalador descartável fechado em 10.164 (amplo, medido) / 6.049 (estreito, exato) com comando reproduzível — e a cobertura da fase agora é total, sem exceção nomeada (87 == 87).**

## Performance

- **Duration:** ~19 min
- **Started:** 2026-08-10T07:19:57Z
- **Completed:** 2026-08-10T07:38:44Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- **REM-04 fechado — as linhas do bundle por órfão** (todas conferidas por `sed -n` no clone, cada primeira linha contém o identificador do handler):
  - `run-with-timeout` (misc): `runWithTimeout` **L3452-L3590** + interceptação no main() L3712-L3721 (antes do parsing global — argv do comando embrulhado é opaco); exit codes idênticos ao GNU timeout (124/125/126/127/128+n/2), 5 call sites.
  - `user-story.validate` (checagem): `routeUserStory` **L3179-L3230** + router L3395; JSON {valid, errors, slots}, história inválida sai 0 com veredito no envelope; 2 call sites com `--pick valid`.
  - `dispatch-isolation` (dispatch-model): `routeDispatchIsolation` **L1624-L1764** + sentinel writer L1776-L1800 (#3045: side effect inescapável); fail-closed `none` (ADR-1239); 6 call sites.
  - `dispatch-should-flatten` (dispatch-model): `routeDispatchShouldFlatten` **L1575-L1623**; fail-closed imprime `true`; 2 call sites.
- **Init re-derivado (REM-05)**: `bundle_shapes` em init.json — 9 shapes, 17 sítios de consumo abertos no clone (13 nos 8 + 4 em agents), campos consumidos por sítio com arquivo:linha, composição por handler (1.229 linhas somadas em src/init.cts) e estimativa com rationale. **Total 490 linhas python** (delta −10 contra o ~500 refutado: o número quase bate, a fundamentação agora existe — era isso que o risco 6 pedia). Método gravado em `measurements.init_budget.method`.
- **Instalador com filtro declarado (REM-05)**: oficial = **10.164** (amplo: `src/install*.cts` + `installer-migrations/**` + `agent-install-check.cts` + `runtime-artifact-*.cts`; esperado ≈10.331, delta −167 — o medido vale, comando gravado e RE-EXECUTADO por teste). Estreito = **6.049 exato** (componente nomeado). O 7.726 da abertura segue refutado. Sem dupla contagem (migrações são `NNN-*.cts`, não casam o glob).
- **A tolerância morreu**: `verbs_pending_plan_04` removido do agregado; o teste de cobertura real exige diferença vazia nos dois sentidos, sem ler lista nenhuma; teste novo prova que a chave não existe e que índice == universo == 87.
- **Suíte 24/24** (15 do plano 03 + 4 de órfãos/proveniência + 5 de measurements/cobertura), com o cache real presente — os testes reais RODARAM, nenhum skip disparou.

## Task Commits

1. **Task 1 RED: testes dos 4 órfãos + dois sentidos** - `2613f78` (test)
2. **Task 1 GREEN: os 4 órfãos extraídos do bundle** - `1cf5b6f` (feat)
3. **Task 2: bundle_shapes + measurements + tolerância morta** - `16e7c9d` (feat)

## Files Created/Modified

- `cairn/gsd/contracts/misc.json` - +run-with-timeout (provenance de bundle); quick-tasks-append repontado para src; fantasmas is/plan.task-structure com provenance própria
- `cairn/gsd/contracts/checagem.json` - +user-story.validate (provenance de bundle)
- `cairn/gsd/contracts/dispatch-model.json` - +dispatch-isolation, +dispatch-should-flatten (provenance de bundle)
- `cairn/gsd/contracts/init.json` - +bundle_shapes (9) com nota de método; 3 lacunas de shape corrigidas contra src
- `cairn/gsd/contracts/contracts.json` - +4 verbos no índice (87), +measurements {init_budget, installer_cut}, −verbs_pending_plan_04
- `tests/gsd-contracts.bats` - +9 testes (24 no total); cobertura sem tolerância

## Decisions Made

- **Provenance de fantasma distinta da de órfão**: o sentido inverso 2 exige provenance em TODA entrada que aponta o bundle; `is` e `plan.task-structure` (contratados pelo plano 03 no caminho de erro do dispatcher) ganham provenance própria de fantasma. A string exata de D-04 segue identificando unicamente os 4 órfãos — a distinção do plano fica testável por igualdade.
- **quick-tasks-append aponta src**: as notes do plano 03 já nomeavam `appendQuickTaskRow` em src/markdown-table.cts; source_ref agora aponta essa implementação (L737-L797) e o roteamento inline do bundle fica em notes. Não-órfão não aponta o bundle.
- **O número medido vale**: amplo 10.164 ≠ 10.331 esperado; gravado o medido com o comando ao lado (mesma cláusula dos planos 01 e 03 para divergência de expectativa).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Dado inconsistente] 3 entradas pré-existentes violavam o sentido inverso 2**
- **Found during:** Task 1 (RED — o teste novo mordeu dados do plano 03)
- **Issue:** `is`, `plan.task-structure` e `quick-tasks-append` apontavam source_ref no bundle SEM provenance — exatamente o furo que o invariante do plano 04 fecha.
- **Fix:** quick-tasks-append repontado para a fonte em src que suas notes já citavam; os dois fantasmas ganham provenance própria (distinta da string D-04 — ver Decisions).
- **Files modified:** cairn/gsd/contracts/misc.json
- **Verification:** testes 18-19 (glob nos dois sentidos) verdes
- **Committed in:** 1cf5b6f

**2. [Rule 1 - Shape incompleta] 3 chaves emitidas pelo src ausentes das shapes do plano 03**
- **Found during:** Task 2 (mapeando o consumo contra as shapes)
- **Issue:** os callers consomem `phase_req_ids` (execute-phase), `granularity` (plan-phase) e `phases` (manager); as shapes do plano 03 não as listavam. Conferido no src: emitidas em init.cts L883, L1027 e L2489.
- **Fix:** as 3 chaves adicionadas às shapes dos verbos; o cross-check consumido⊆shape agora roda por teste.
- **Files modified:** cairn/gsd/contracts/init.json
- **Verification:** teste 21 verde (inclui o cross-check)
- **Committed in:** 16e7c9d

### Notas

**3. [Nota] A premissa "lidos por --pick" do research vale para 1 sítio** — só plan-phase.md:1361 usa `--pick phase_req_ids` literal; os outros 16 sítios capturam o envelope inteiro e parseiam em contexto. Corrigido no registro (bundle_shapes_note e no method do init_budget), sem impacto na re-derivação.

**4. [Nota] 4º mismatch corpus↔tag descoberto**: verify-work.md:51 pede `uat_path`, chave que `cmdInitVerifyWork` NUNCA emite (existe só nos bundles de plan-phase e phase-op). Mesma classe do `phases.list --pick summaries_total` do plano 03; documentado em consumption_sites e excluído de consumed_fields. Herança para a fase 33.

**5. [Nota] Instalador amplo mediu 10.164, não 10.331** — cláusula do plano aplicada: o medido vale, o comando prova, o delta (−167) registrado na note do measurement.

---

**Total deviations:** 2 auto-fixed (Rule 1) + 3 notas
**Impact on plan:** Nenhum scope creep. Os dois fixes eram exigidos pelos próprios invariantes do plano; as notas corrigem premissas contra a medição, que é o ofício desta fase.

## Issues Encountered

None — a execução foi direta; toda divergência está documentada como desvio ou nota acima.

## Known Stubs

Nenhum — nenhum valor inventado, nenhum TODO/FIXME, nenhum teste pulado nesta máquina (o cache estava presente: os testes reais de cobertura e de re-execução do comando do instalador RODARAM).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Fase 33 (binário python)**: os 4 órfãos têm semântica completa com linha citada — o harness não precisa de caso especial (D-04); herda também o 4º mismatch (`uat_path`) junto dos 4 do plano 03.
- **Fase 34 (CORE-05)**: orça init por `measurements.init_budget` (490, método escrito) em vez do ~500 sem fundamento.
- **Fase 32 (vendoring)**: o corte do instalador tem número oficial com filtro e comando (10.164 amplo / 6.049 estreito).
- **A fase 31 fecha com a tabela versionada cobrindo 100% do universo medido** (87 verbos, 0 exceções) — critério de sucesso da fase atendido.
- `cairn/scripts/cairn-doctor.py` intocado (D-03): último commit que o toca é a2527ee, anterior à fase.
- Regressões: `bats tests/gsd-contracts.bats` 24/24; `bats tests/cairn-inventory.bats` 24/24.

---
*Phase: 31-a-baseline-remedida-contra-a-tag*
*Completed: 2026-08-10*

## Self-Check: PASSED

6 arquivos modificados verificados em disco; commits 2613f78, 1cf5b6f e 16e7c9d verificados no repositório; suíte gsd-contracts 24/24 com o cache real presente e regressão do inventário 24/24 (2026-08-10). Citações de linha dos 4 órfãos conferidas por sed no bundle do clone.
