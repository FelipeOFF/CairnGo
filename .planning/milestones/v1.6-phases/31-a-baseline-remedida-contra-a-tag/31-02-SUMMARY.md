---
phase: 31-a-baseline-remedida-contra-a-tag
plan: "02"
subsystem: tooling
tags: [gsd-core, contracts, json-schema, jq, bats, rem-03]

# Dependency graph
requires:
  - phase: 31-a-baseline-remedida-contra-a-tag (plano 01)
    provides: "universo de verbos do cairn-inventory (--json .verbs) e cache .cairn/cache/gsd-core-v1.10.0 com HEAD pinado"
provides:
  - "cairn/gsd/contracts/ (D-02): agregado contracts.json + 5 arquivos de família sob schema único, validados por tests/gsd-contracts.bats"
  - "Schema de contrato fixado por teste executável: verb, spellings[], invocation, input{argv,flags,stdin}, output{kind,shape,exit_codes}, source_ref{path,lines}, call_sites{workflows8,agents}, notes"
  - "Contratos completos das 5 famílias triviais (config, commit, skills, loop-hooks, dispatch-model) — 8 verbos extraídos da implementação da tag"
  - "assignment_rule por prefixo registrada em prosa no agregado, com os casos ambíguos decididos (resolve-*, classify-confidence→misc, órfãos→plano 04)"
affects: [31-03, 31-04, fase-33-binario-python, fase-34, fase-35, harness-diferencial]

# Actuals (#2632)
actuals:
  tokens: 7726
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Contrato como dado versionado: JSON com chaves ordenadas, indent 2, newline final (diffs estáveis, molde cairn-review.py)"
    - "Decisão registrada em prosa NO dado (assignment_rule, notes por verbo) — precedente das NOTEs do capability.json"
    - "Suíte glob-driven: tests/gsd-contracts.bats itera cairn/gsd/contracts/*.json, então os arquivos dos planos 03-04 entram na validação sem tocar na suíte"

key-files:
  created:
    - cairn/gsd/contracts/contracts.json
    - cairn/gsd/contracts/config.json
    - cairn/gsd/contracts/commit.json
    - cairn/gsd/contracts/skills.json
    - cairn/gsd/contracts/loop-hooks.json
    - cairn/gsd/contracts/dispatch-model.json
    - tests/gsd-contracts.bats
  modified: []

key-decisions:
  - "shape é array das chaves de topo do payload JSON ([] quando a saída é escalar/texto); chaves extraídas por --pick nos call sites são evidência direta (resolve-model --pick model)"
  - "flags como array de objetos {flag, takes_value, meaning} — um só leitor serve schema e humanos"
  - "Órfãos dispatch-isolation/dispatch-should-flatten pertencem à família dispatch-model mas entram pelo plano 04 com provenance de bundle (D-04) — decidido e escrito na assignment_rule"
  - "classify-confidence → misc, não dispatch-model: é classificação de confiança de package-legitimacy, não de model (anotado na assignment_rule)"
  - "exit codes comunicam pouco de propósito nesta CLI: commit/commit-to-subrepo/agent-skills/resolve-dispatch-type saem 0 mesmo em falha parcial — o veredito vai no envelope (reason/unknown_agent/committed) e o contrato registra isso"

patterns-established:
  - "Consistência bidirecional agregado↔famílias testada sobre os arquivos PRESENTES: famílias declaradas no mapa mas ainda não escritas não quebram (tolerância que o plano 04 mata)"

requirements-completed: [REM-03]

coverage:
  - id: D1
    description: "Schema fixado por teste + agregado contracts.json com identidade da fonte (repo/tag/commit conferido contra o HEAD do cache), mapa das 11 famílias, universe.derived_from e assignment_rule em prosa (D-02)"
    requirement: REM-03
    verification:
      - kind: unit
        ref: "tests/gsd-contracts.bats#contracts.json declares the 11 families of research §4 with one file each"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#contracts.json carries source identity, universe.derived_from and a written assignment_rule"
        status: pass
    human_judgment: false
  - id: D2
    description: "As cinco famílias triviais com contrato completo: todo verbo com verb/invocation/input/output/source_ref/call_sites, nenhuma entrada sem source_ref, config-get e config-set presentes, render-hooks registrado"
    requirement: REM-03
    verification:
      - kind: unit
        ref: "tests/gsd-contracts.bats#every verb entry carries verb, invocation, input.argv/flags, output.kind/exit_codes and a non-empty source_ref"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#config.json contracts config-get and config-set, the most-called family"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#loop-hooks.json registers the render-hooks subcommand of loop"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#no verb entry in any family file is missing its source_ref (REM-03: extraido da implementacao)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Índice verbs do agregado bidirecional com os arquivos de família; cobertura do universo do inventário restrita às famílias deste plano (diferença = famílias dos planos 03-04 + 2 órfãos documentados)"
    requirement: REM-03
    verification:
      - kind: unit
        ref: "tests/gsd-contracts.bats#aggregate → families: every indexed verb points to a family whose file exists and contains it"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#families → aggregate: every verb present in a family file is in the aggregate index"
        status: pass
      - kind: integration
        ref: "comm -23 <(inventário .verbs keys) <(agregado .verbs keys) — diff conferido item a item contra a assignment_rule"
        status: pass
    human_judgment: false
  - id: D4
    description: "Backstop: amostra de contratos confere com a implementação da tag — um verbo por família re-conferido abrindo o source_ref citado no clone"
    verification: []
    human_judgment: true
    rationale: "O plano marca esta truth como verification: backstop (edge-probe do engine, flagged para o verificador). Veredito do executor: sed -n nas linhas citadas do clone abre exatamente a assinatura de cada handler (cmdConfigGet@config.cts:965, cmdCommit@commands.cts:793, cmdAgentSkills@init.cts:3326, cmdLoopRenderHooks@loop-resolver.cts:478, cmdResolveModel@commands.cts:495, resolveDispatchType@host-integration.cts:664-679); input/output foram lidos do corpo dos handlers, não de memória."

# Metrics
duration: 35min
completed: 2026-08-10
status: complete
---

# Phase 31 Plan 02: Contratos das famílias triviais Summary

**cairn/gsd/contracts/ nasce com o schema do REM-03 fixado por bats/jq: agregado com identidade da fonte (v1.10.0@68a04cc) e assignment_rule em prosa, mais 8 verbos das 5 famílias triviais (config, commit, skills, loop-hooks, dispatch-model) com source_ref linha a linha na implementação da tag.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-10T06:00Z
- **Completed:** 2026-08-10T06:35Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- **Schema único fixado por teste executável** (D-02, reversibility costly): 12 testes em `tests/gsd-contracts.bats` no molde jq do capability.bats validam JSON+newline, envelope de família (schema_version/family/source/verbs), schema por verbo (verb/invocation/input.argv/input.flags/output.kind∈{json,text,exit-only}/exit_codes/source_ref/spellings/call_sites) e a consistência bidirecional agregado↔famílias — em glob, cobrindo desde já o que os planos 03-04 escreverem.
- **Agregado `contracts.json`**: source pinado em open-gsd/gsd-core v1.10.0 @68a04ccf (igual ao HEAD do cache, conferido por teste de aceitação), as 11 famílias do research §4 declaradas como contrato de layout, `universe.derived_from` apontando o comando do inventário, e a regra de atribuição por prefixo escrita em prosa no próprio dado com os casos ambíguos decididos.
- **8 verbos contratados, zero de memória**: config-get (32+2 sítios) e config-set (6) lidos de src/config.cts L965-1044/L704-963 (resolução em camadas #2702, coerção de valor, unset por null #2046, secrets mascarados); commit (15+8) e commit-to-subrepo (1) de src/commands.cts L793-1035/L1088-1184 (envelope reason com os 7 valores, skips intencionais #3678, staging rollback #2608); agent-skills (13) de src/init.cts L3326-3449 (Resolution<AgentSkillsValue> de resolution.cts, 4 reasons, fallback #2454); loop render-hooks (17) de src/loop-resolver.cts L478-620 (12 pontos canônicos, fail-open #2009, modo --active-cap); resolve-model (2) de src/commands.cts L495-510 (--pick model como evidência de shape) e resolve-dispatch-type (5) de src/host-integration.cts L664-679 — com o contrato em host único registrado: named-dispatch devolve o role inalterado, e a nota cita a lógica multi-host que o justifica.

## Task Commits

1. **Task 1 RED: suíte que fixa o schema** - `a57747d` (test)
2. **Task 1 GREEN: agregado contracts.json** - `906a694` (feat)
3. **Task 2: cinco famílias + âncoras na suíte + índice verbs** - `ff9d78e` (feat)

## Files Created/Modified

- `cairn/gsd/contracts/contracts.json` - agregado: identidade da fonte, mapa das 11 famílias, índice verbs, universe, assignment_rule
- `cairn/gsd/contracts/config.json` - config-get, config-set (a família mais chamada: 38 sítios query nos 8)
- `cairn/gsd/contracts/commit.json` - commit, commit-to-subrepo
- `cairn/gsd/contracts/skills.json` - agent-skills
- `cairn/gsd/contracts/loop-hooks.json` - loop (render-hooks)
- `cairn/gsd/contracts/dispatch-model.json` - resolve-model, resolve-dispatch-type (host único)
- `tests/gsd-contracts.bats` - 12 testes: schema por jq, consistência bidirecional, âncoras do REM-03

## Decisions Made

- `shape` = array das chaves de topo do payload JSON; `[]` para saída escalar/texto — as chaves que os call sites extraem por `--pick` entram como evidência direta.
- Órfãos `dispatch-isolation`/`dispatch-should-flatten` são da família dispatch-model mas entram pelo plano 04 com provenance (D-04); escrito na assignment_rule para a cobertura do plano 04 fechar sem ambiguidade.
- `classify-confidence` → misc (package-legitimacy, não model) — anotado na assignment_rule.
- Exit codes registrados como são: vários verbos saem 0 em falha parcial e comunicam pelo envelope (reason/committed/unknown_agent) — o harness da fase 33 compara envelope, não exit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Testes-âncora da Task 2 removidos do RED da Task 1**
- **Found during:** Task 1 (GREEN)
- **Issue:** O RED inicial incluía os testes-âncora de config.json/loop-hooks.json (comportamento da Task 2); com eles o GREEN da Task 1 (`bats` sai 0 só com o agregado) era insatisfazível.
- **Fix:** Âncoras removidas do commit RED (amend local, pré-push) e re-adicionadas na Task 2, onde são satisfeitas no mesmo commit que cria os arquivos.
- **Files modified:** tests/gsd-contracts.bats
- **Verification:** GREEN da Task 1 com 9/9; suíte final com 12/12
- **Committed in:** a57747d (amend) / ff9d78e

**2. [Nota] 31-PATTERNS.md referenciado pelo plano não existe**
- Mesma ausência registrada no 31-01-SUMMARY. Executado com os análogos que o próprio plano lista (capability.json para decisões em prosa no dado, capability.bats L55-95 para o molde jq).

---

**Total deviations:** 1 auto-fixed (blocking) + 1 nota
**Impact on plan:** Nenhum scope creep; a correção só realocou asserções entre tasks para o gate de verify de cada task ser satisfazível.

## Issues Encountered

None — o cache do plano 01 estava íntegro (precondition da Task 1 verificada: `rev-parse HEAD` = 68a04cc) e a extração foi 100% offline.

## Known Stubs

Nenhum — nenhum valor de contrato inventado, nenhum TODO/FIXME, nenhum teste pulado; `verbs` das famílias 03-04 ausentes por desenho (tolerância declarada no teste, morta pelo plano 04).

## Next Phase Readiness

- Plano 03 (wave 3): schema e suíte prontos — os seis arquivos restantes entram no glob sem tocar na suíte; assignment_rule já resolve estado/roadmap-phase/worktree/checagem/init/misc.
- Plano 04: campo provenance reservado (D-04) e os 2 órfãos de dispatch-model já apontados na assignment_rule.
- `cairn/scripts/cairn-doctor.py` intocado (D-03): `git log a57747d^..HEAD -- cairn/scripts/cairn-doctor.py` vazio.

---
*Phase: 31-a-baseline-remedida-contra-a-tag*
*Completed: 2026-08-10*

## Self-Check: PASSED

7 arquivos criados verificados em disco; commits a57747d, 906a694, ff9d78e verificados no repositório; suíte 12/12 e regressão do inventário verdes (2026-08-10).
