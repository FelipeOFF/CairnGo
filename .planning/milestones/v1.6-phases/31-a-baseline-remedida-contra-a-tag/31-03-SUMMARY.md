---
phase: 31-a-baseline-remedida-contra-a-tag
plan: "03"
subsystem: tooling
tags: [gsd-core, contracts, json-schema, jq, bats, rem-03, coverage]

# Dependency graph
requires:
  - phase: 31-a-baseline-remedida-contra-a-tag (plano 01)
    provides: "universo de verbos do cairn-inventory (--json .verbs) e cache .cairn/cache/gsd-core-v1.10.0 com HEAD pinado"
  - phase: 31-a-baseline-remedida-contra-a-tag (plano 02)
    provides: "schema de contrato fixado por teste, agregado contracts.json com assignment_rule, 5 famílias triviais"
provides:
  - "Contratos das 6 famílias restantes: estado (10 verbos), roadmap-phase (12), worktree (6), init (9), checagem (10), misc (28) — 75 verbos extraídos da implementação da tag"
  - "Cobertura fechada e provada por teste: universo do inventário == índice do agregado, tolerância única lida de universe.verbs_pending_plan_04 (os 4 órfãos do plano 04), controle negativo que rejeita cobertura furada"
  - "Grafia dupla de verification.status contratada (query verification status / verification.status) para o parser da fase 35 (CHECK-01)"
  - "Quatro verbos fantasma/mismatch do corpus documentados como fatos da tag: phase.list-artifacts, plan.task-structure, is (Unknown command exit 1) e phases.list --pick summaries_total (chave nunca emitida)"
affects: [31-04, fase-33-binario-python, fase-34, fase-35, harness-diferencial]

# Actuals (#2632)
actuals:
  tokens: 29800
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tolerância de cobertura data-driven: o teste lê universe.verbs_pending_plan_04 do próprio agregado em vez de lista digitada — o plano 04 esvazia o array e o teste passa a exigir cobertura total mecanicamente"
    - "Verbo fantasma contratado como está: entrada com kind exit-only e source_ref no caminho de erro que responde à chamada — o mismatch corpus↔tag vira dado versionado, não nota de rodapé"
    - "shape [] para dispatchers multi-subcommand (check, graphify, intel), payloads dinâmicos (frontmatter.get) e top-level array (package-legitimacy) — com o payload por-subcommand descrito em notes"

key-files:
  created:
    - cairn/gsd/contracts/estado.json
    - cairn/gsd/contracts/roadmap-phase.json
    - cairn/gsd/contracts/worktree.json
    - cairn/gsd/contracts/init.json
    - cairn/gsd/contracts/checagem.json
    - cairn/gsd/contracts/misc.json
  modified:
    - cairn/gsd/contracts/contracts.json
    - tests/gsd-contracts.bats

key-decisions:
  - "Atribuição mecânica por prefixo aplicada à risca: os 4 fora-da-soma (audit-open, review-lane, agent.classify-failure, task.is-behavior-adding) e estimate-check não casam prefixo → misc, com a ambiguidade semântica anotada em notes de cada entrada"
  - "phase (bare) e phase-plan-index → roadmap-phase por decisão anotada: a regra lista phase.* com ponto, mas ambos são a família phase do research §4 (phase uat-passed e o índice de planos da fase)"
  - "Verbos fantasma contratados como estão na tag: phase.list-artifacts (2 sítios em gsd-plan-checker), plan.task-structure (2 sítios idem) e is (prosa capturada pela métrica) morrem Unknown/exit 1 — a fase 33 decide implementar ou corrigir os agentes"
  - "Tolerância do teste de cobertura lida de universe.verbs_pending_plan_04 do agregado (nunca digitada no teste) — REM-04 a esvazia"
  - "--pick é flag GLOBAL do dispatcher (captura stdout + extractField), não por-verbo: registrado nas notes dos verbos cujos call sites o usam como evidência de shape"

patterns-established:
  - "Notes por verbo carregam o roteamento completo (router + linhas) além do handler — um leitor da fase 33 acha o caminho inteiro da invocação sem grep"

requirements-completed: [REM-03]

coverage:
  - id: D1
    description: "As seis famílias restantes têm arquivo de contrato sob o schema do plano 02, com source_ref por verbo apontando a implementação na tag"
    requirement: REM-03
    verification:
      - kind: unit
        ref: "tests/gsd-contracts.bats#every verb entry carries verb, invocation, input.argv/flags, output.kind/exit_codes and a non-empty source_ref"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#no verb entry in any family file is missing its source_ref (REM-03: extraido da implementacao)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A grafia dupla de verification.status está representada no contrato (as duas spellings do research §2.3)"
    requirement: REM-03
    verification:
      - kind: other
        ref: "jq -e '.verbs[] | select(.verb == \"verification.status\") | .spellings | length >= 2' cairn/gsd/contracts/checagem.json"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cobertura fechada: todo verbo do universo tem entrada no índice e no arquivo da família, provado contra a saída real do inventário, com controle negativo"
    requirement: REM-03
    verification:
      - kind: integration
        ref: "tests/gsd-contracts.bats#real universe: every inventory verb has a contract; the only tolerance is the plan-04 orphan list (REM-04)"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#aggregate ↔ families: the verb SETS are identical in both directions (empty diff)"
        status: pass
      - kind: unit
        ref: "tests/gsd-contracts.bats#negative control: a forged verb injected into a simulated universe does NOT pass coverage"
        status: pass
    human_judgment: false
  - id: D4
    description: "Os quatro verbos fora da soma de orçamento têm contrato com source_ref em src/ (têm fonte, diferente dos 4 órfãos do plano 04)"
    requirement: REM-03
    verification:
      - kind: other
        ref: "jq: source_ref.path startswith(\"src/\") para audit-open, review-lane, agent.classify-failure, task.is-behavior-adding em misc.json"
        status: pass
    human_judgment: false
  - id: D5
    description: "Backstop: amostra de contratos confere com a implementação da tag — um verbo por família nova re-conferido abrindo o source_ref citado no clone"
    verification: []
    human_judgment: true
    rationale: "Truth marcada verification: backstop no plano (edge-probe, flagged). Veredito do executor: sed -n nas linhas citadas do clone abre exatamente a assinatura de cada handler — cmdStateLoad@state.cts:336, cmdRoadmapGetPhase@roadmap.cts:249, cmdWorktreeRecordAgent@worktree-safety.cts:1148, cmdInitAutonomous@init.cts:2558, cmdVerificationStatus@verification.cts:517, cmdTeamsStatus@teams-status.cts:74; input/output lidos do corpo dos handlers e dos routers, não de memória."

# Metrics
duration: 36min
completed: 2026-08-10
status: complete
---

# Phase 31 Plan 03: Contratos das seis famílias restantes Summary

**Os 75 verbos das famílias estado, roadmap-phase, worktree, init, checagem e misc contratados da implementação da tag v1.10.0, cobertura do universo fechada por teste contra o inventário real (tolerância única: os 4 órfãos do plano 04, lida do próprio agregado) e quatro mismatches corpus↔tag documentados como dado versionado.**

## Performance

- **Duration:** ~36 min
- **Started:** 2026-08-10T06:38Z
- **Completed:** 2026-08-10T07:14Z
- **Tasks:** 3/3
- **Files modified:** 8

## Accomplishments

- **83 verbos contratados no total** (8 do plano 02 + 75 deste): por família — estado 10, roadmap-phase 12, worktree 6, init 9, checagem 10, misc 28, mais config 2, commit 2, skills 1, loop-hooks 1, dispatch-model 2. Todo verbo com invocation, input (argv/flags com significado), output (kind/shape/exit_codes), source_ref linha a linha e call_sites por escopo.
- **Cobertura do REM-03 virou fato mecânico**: `comm -3` entre o universo do inventário (87 verbos) e o índice do agregado (83) devolve exatamente os 4 órfãos do plano 04 (dispatch-isolation, dispatch-should-flatten, run-with-timeout, user-story.validate) — e o teste 13 prova isso a cada execução contra o cache real, com a tolerância lida de `universe.verbs_pending_plan_04` (o plano 04 a esvazia). Controle negativo (teste 14) prova que um verbo forjado vaza.
- **Grafia dupla contratada** (CHECK-01): a entrada de verification.status em checagem.json lista `query verification status` E `query verification.status`, com a normalização do dispatcher (#3243, split no primeiro ponto) citada com linha.
- **Quatro mismatches corpus↔tag descobertos e contratados como estão** — insumo direto para a fase 33: `phase.list-artifacts` (2 sítios, verbo inexistente → Unknown exit 1), `plan.task-structure` (2 sítios, comando plan inexistente), `is` (prosa capturada pela métrica larga como chamada) e `phases.list --pick summaries_total` (a chave summaries_total nunca é emitida pelo handler — o `|| echo 0` do caller nem dispara porque o exit é 0).
- **Padrões transversais registrados nas notes**: `--pick` como flag global do dispatcher (captura stdout + extractField), resolução transparente de `@file:` para payloads >50KB (#1891), a convenção exit-0-com-veredito-no-envelope (e as exceções deliberadas: teams-status --active codifica o boolean no exit; worktree.cleanup-wave/create/record-agent usam exit 2 para usage).

## Task Commits

1. **Task 1: estado, roadmap-phase e worktree** - `106e19f` (feat)
2. **Task 2: init, checagem e misc + grafia dupla + fora da soma** - `8ebda1d` (feat)
3. **Task 3: cobertura provada contra o inventário real** - `aad7ba2` (test)

_Nota TDD: a Task 3 produziu um único commit (test) — ver Deviations._

## Files Created/Modified

- `cairn/gsd/contracts/estado.json` - 10 verbos state.* (handlers em src/state.cts, transições ADR-1769)
- `cairn/gsd/contracts/roadmap-phase.json` - 12 verbos roadmap/phase/phases/find-phase, incluindo o fantasma phase.list-artifacts
- `cairn/gsd/contracts/worktree.json` - 6 verbos (manifest de wave, base-check #683, reap fail-open)
- `cairn/gsd/contracts/init.json` - os 9 bundles init.* com shape completa das chaves de topo (insumo do plano 04)
- `cairn/gsd/contracts/checagem.json` - verify/verify.*/uat.*/verification.status (grafia dupla)/check/check.decision-coverage-plan
- `cairn/gsd/contracts/misc.json` - 28 verbos atômicos, incluindo os 4 fora da soma com fonte em src/ e 2 fantasmas
- `cairn/gsd/contracts/contracts.json` - índice com 83 verbos; universe com contagens (87/83), data e a lista pending do plano 04
- `tests/gsd-contracts.bats` - +3 testes: sets idênticos nos dois sentidos, cobertura real skip-gated, controle negativo (15 no total)

## Decisions Made

- **Atribuição por regra mecânica, ambiguidade em notes**: os 4 fora-da-soma e estimate-check não casam prefixo → misc; `phase` (bare) e `phase-plan-index` → roadmap-phase por decisão anotada (a regra escreve phase.* com ponto; ambos são a família phase do research §4). Nenhuma outra atribuição precisou de decisão.
- **Verbo fantasma é contrato, não omissão**: entrada com `kind: exit-only`, exit_codes só com 1, e source_ref apontando o caminho de erro que responde à chamada (o hub do router de phase, o default do runCommand). A cobertura fecha sem furo e a fase 33 herda a decisão explícita.
- **Tolerância data-driven no teste de cobertura**: lida de `universe.verbs_pending_plan_04` — quando o plano 04 esvaziar o array, o mesmo teste exige cobertura total sem edição.

## Deviations from Plan

### Auto-fixed Issues

Nenhum — nenhuma correção de código foi necessária.

### Notas

**1. [TDD] RED da Task 3 passou de imediato (15/15)**
- **Contexto:** o plano previa "GREEN: fechar o que o vermelho apontar — tipicamente verbos do universo sem entrada". As Tasks 1-2 deste mesmo plano já haviam fechado a cobertura completa (a Task 2 termina com "Fechar o índice verbs com o universo inteiro"), então os testes novos nasceram verdes.
- **Investigação (fail-fast rule):** a feature legitimamente já existia — construída neste plano, nas tasks anteriores. A capacidade de o teste FALHAR é provada pelo controle negativo (teste 14: verbo forjado vaza e é rejeitado), que é exatamente o papel que o plano lhe dá ("o teste rejeita cobertura furada").
- **Efeito:** Task 3 tem um único commit (test), sem commit GREEN — não havia nada a fechar. universe já tinha sido atualizado no commit da Task 2.

**2. [Nota] 31-PATTERNS.md referenciado pelo plano não existe**
- Mesma ausência registrada nos SUMMARYs 01 e 02. Executado com os análogos que o próprio plano lista (config.json do plano 02 como exemplar do schema, cairn-trend.bats L365-396 como molde de expectativa recomputada).

**3. [Nota] Arquivo de journal do cairn não-rastreado no worktree**
- `.cairn/journal/*.jsonl` aparece untracked — saída de runtime do tooling cairn, pré-existente ao plano (o checkout main tem o mesmo `?? .cairn/`), não gerada pelos commits deste plano. Deixado intocado (fora de escopo).

---

**Total deviations:** 0 auto-fixed + 3 notas
**Impact on plan:** Nenhum scope creep. A única divergência de processo (RED verde) é consequência da ordem interna do próprio plano e está provada inofensiva pelo controle negativo.

## Issues Encountered

- O runtime do clone não compila offline (`bin/lib` ausente, TypeScript indisponível) — a tentativa de provar `phase.list-artifacts` por execução direta do gsd-tools.cjs da tag morreu no bootstrap. A prova ficou estática e é sólida: o verbo não consta de PHASE_COMMAND_ALIASES (src/command-aliases.cts L487-L801), não há handler em src/ nem no bundle, e o caminho UnknownCommand do hub (src/phase-command-router.cts L272-L277) é o único que pode responder.

## Known Stubs

Nenhum — nenhum valor de contrato inventado, nenhum TODO/FIXME, nenhum teste pulado nesta máquina (o skip-gate da cobertura real NÃO disparou: o cache estava presente e o teste rodou de verdade). Os verbos fantasma não são stubs: são o comportamento real da tag, contratado como está.

## Next Phase Readiness

- **Plano 04**: os 4 órfãos estão nomeados em `universe.verbs_pending_plan_04`; ao contratá-los com provenance (D-04) e esvaziar o array, o teste de cobertura passa a exigir totalidade sem edição. As shapes dos 9 bundles init.* estão registradas verbo a verbo para a re-derivação da estimativa.
- **Fase 33**: quatro decisões pendentes herdadas como dado — implementar ou corrigir os call sites de phase.list-artifacts e plan.task-structure, tratar o falso positivo `is`, e decidir o destino de `phases.list --pick summaries_total`.
- `cairn/scripts/cairn-doctor.py` intocado (D-03): `git log 106e19f^..HEAD -- cairn/scripts/cairn-doctor.py` vazio.
- Regressões: `bats tests/gsd-contracts.bats` 15/15; `bats tests/cairn-inventory.bats` 24/24.

---
*Phase: 31-a-baseline-remedida-contra-a-tag*
*Completed: 2026-08-10*

## Self-Check: PASSED

6 arquivos de familia + SUMMARY verificados em disco; commits 106e19f, 8ebda1d, aad7ba2 verificados no repositorio; suite gsd-contracts 15/15 (cobertura real rodou com o cache presente) e regressao do inventario 24/24 (2026-08-10).
