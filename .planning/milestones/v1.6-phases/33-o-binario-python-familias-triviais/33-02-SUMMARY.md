---
phase: 33-o-binario-python-familias-triviais
plan: 02
subsystem: gsd-transplant
tags: [python, bats, gsd-tools, goldens, commit, skills, loop-hooks, dispatch-model]

requires:
  - phase: 33-o-binario-python-familias-triviais
    provides: dispatcher cairn-gsd.py + harness diferencial + recorder + manifesto de cenários (plano 33-01)
provides:
  - família commit no dispatcher — `query commit` com a cadeia de reasons do contrato (committed | skipped_commit_docs_false | skipped_gitignored | nothing_to_commit | staging_failed | commit_failed) e `query commit-to-subrepo` agrupando --files por sub-repo dono
  - família skills — `query agent-skills` com bloco XML cru por default, IR Resolution com --json e os 4 reasons do contrato
  - família loop-hooks — `loop render-hooks <point>` por tabela NATIVA de cairn/capability/capability.json, vocabulário canônico de 12 pontos, --active-cap limpo
  - família dispatch/model — dispatch-isolation (com sentinel), dispatch-should-flatten, resolve-model e resolve-dispatch-type, todos fail-closed, host único claude
  - 27 cenários novos no manifesto (25 goldens recorded do binário real + 2 derived da tabela nativa) — os 10 verbos das 5 famílias triviais cobertos
affects: [33-03, fase-34, fase-35, fase-36-shim]

actuals:
  tokens: 25700
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "tabela estática de host único: o descritor claude (dispatch + harnessIsolationFlag) vendorizado do capability-registry com source_ref, fail-closed para qualquer outro runtime"
    - "tabela nativa de hooks: capability.json do cairn como fonte de activeHooks, ativação when → config do projeto → default do próprio manifest"
    - "goldens recorded para tudo que coincide byte a byte com o binário; derived só onde a divergência é declarada (tabela nativa do loop)"

key-files:
  created:
    - tests/fixtures/gsd-goldens/commit-*.golden.json (9)
    - tests/fixtures/gsd-goldens/agent-skills-*.golden.json (5)
    - tests/fixtures/gsd-goldens/loop-*.golden.json (4)
    - tests/fixtures/gsd-goldens/dispatch-*.golden.json (3)
    - tests/fixtures/gsd-goldens/resolve-*.golden.json (6)
  modified:
    - cairn/scripts/cairn-gsd.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json

key-decisions:
  - "A semântica do --raw segue o binário (doutrina do plano 01): sem --raw sai o envelope JSON; com --raw sai o texto (hash no commit, model id no resolve-model, modo cru no dispatch-isolation) — o texto do plano descrevia o inverso em alguns acceptance; a divergência de doc já está declarada desde o 33-01"
  - "dispatch-isolation em claude resolve harness-worktree (com flag isolation=\"worktree\"), NÃO o none do texto do plano: o registry da tag declara harness-worktree para claude e o binário medido imprime isso — o cairn espelha o binário via tabela estática; none continua sendo o fail-closed"
  - "dispatch-should-flatten em claude dá TRUE (não o false que o plano assumia): shouldFlattenDispatch exige backgroundDispatch:true e o descritor claude da tag declara false — base declarada: a função portada exata sobre o descritor vendorizado, valor idêntico ao binário medido"
  - "Fonte de MODEL_PROFILES: o config-defaults.manifest.json da tag NÃO carrega model_profiles (medido), então a tabela veio copiada de gsd-core/bin/shared/model-catalog.json .agents com source_ref em comentário no cairn-gsd.py — fallback offline por construção"
  - "commit_docs com .planning gitignored: comportamento MEDIDO no binário — o default merged é suprimido (config {} → skipped_commit_docs_false antes do check de gitignore; só commit_docs:true explícito alcança skipped_gitignored); dois goldens recorded provam os dois ramos"

patterns-established:
  - "recordar sempre que a forma coincide: 25 dos 27 goldens novos são recorded — o diferencial morde em bytes, não em forma"
  - "mask do harness aceita golden já mascarado (test(re) or == \"<masked>\"), mantendo o controle negativo"

requirements-completed: [TRIV-02, TRIV-03]

coverage:
  - id: D1
    description: "query commit emite o envelope {committed, hash, reason, skipped} com os seis reasons do contrato, exit 0 em todo envelope e exit 1 só sem mensagem; commit-to-subrepo agrupa por sub-repo dono; agent-skills responde os 4 reasons com bloco cru/IR"
    requirement: TRIV-02
    verification:
      - kind: integration
        ref: "bats tests/cairn-gsd.bats — diferencial (14 cenários commit/skills, goldens recorded) + 8 testes diretos (staging_failed, commit_failed, --no-verify, --amend, sanitize, multi-repo, configured_unresolved, configured_empty)"
        status: pass
    human_judgment: false
  - id: D2
    description: "loop render-hooks valida os 12 pontos canônicos e monta activeHooks da tabela nativa do capability.json; --active-cap imprime true|false limpo; dispatch-isolation/should-flatten/resolve-dispatch-type fail-closed com sentinel provado; resolve-model com unknown_agent"
    requirement: TRIV-03
    verification:
      - kind: integration
        ref: "bats tests/cairn-gsd.bats — diferencial (13 cenários loop/dispatch/model, 11 recorded + 2 derived) + 12 testes diretos (sentinel, .gsd travado, force-isolation, runtime desconhecido, config corrompida, --pick)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-10
status: complete
---

# Phase 33 Plan 02: Famílias commit, skills, loop-hooks e dispatch/model Summary

**Os 8 verbos das 4 famílias restantes respondem no dispatcher python na forma byte-exata do gsd-tools da tag onde a forma coincide (25 goldens recorded) e por tabela nativa declarada onde o cairn corta o capability-registry (2 goldens derived) — os 10 verbos das 5 famílias triviais fecham**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-08-10T17:25Z
- **Tasks:** 2
- **Files modified:** 31 (2458 inserções nos dois commits)

## Accomplishments

- **TRIV-02 (commit + skills):** `handle_commit` porta o cmdCommit inteiro — posicionais unidos (routeCommit), sanitize de invisíveis/injection (sanitizeForPrompt exato), staging com rollback do index (#2608), pathspec escopado (#2112), arquivos ausentes pulados em --files explícito (#2014). `commit-to-subrepo` porta groupFilesBySubrepo (#311/#391) com prefixo mais específico. `agent-skills` emite o bloco XML byte-idêntico ao binário e o IR com a ordem de chaves exata (incluindo source/degraded e o envelope Resolution em .value).
- **TRIV-03 (loop + dispatch/model):** tabela nativa do loop nasce de cairn/capability/capability.json (contributions em plan:post/execute:wave:pre/post/verify:post + gate ship:pre), ativação `when` → config do projeto → default do manifest (cairn.enabled default true). Os 4 verbos de dispatch/model reproduzem o binário medido em claude e provam o fail-closed por teste (runtime desconhecido → none/true/eco; sentinel gravado em toda invocação; .gsd ilegível não falha o verbo).
- **Diferencial:** 27 cenários novos no manifesto; `bats tests/cairn-gsd.bats` com 44 testes verdes offline; reprodução byte a byte dos goldens recorded contra o corpus real re-exercitada verde nesta máquina.

## Registros pedidos pelo plano

- **Persona fallback (#2454):** não portado — o ramo é gated a runtime !== claude no upstream; em host único claude é código morto. Declarado em divergences.json (family skills).
- **Base do should-flatten:** a função `shouldFlattenDispatch` portada exata sobre o descritor claude vendorizado → **true** (backgroundDispatch:false na tag), idêntico ao binário medido. O "claude → false" assumido no texto do plano não corresponde ao registry da tag.
- **Modo natural do isolation em host único:** **harness-worktree** com `harnessFlag isolation="worktree"` — o cairn espelha o binário (registry claude declara isso) em vez do "none natural" do texto do plano; none permanece como fail-closed (provado por teste com runtime desconhecido). Goldens recorded byte a byte.
- **Fonte de MODEL_PROFILES:** o manifest de defaults resolvido pela cadeia do plano 01 não carrega `model_profiles` (medido em gsd-core/bin/shared/config-defaults.manifest.json), então a tabela foi copiada de `gsd-core/bin/shared/model-catalog.json` `.agents` (tag v1.10.0, commit 68a04cc) com source_ref em comentário no próprio cairn-gsd.py; a escada de effort prefere o manifest em cadeia com cópia embutida como fallback offline.

## Entradas novas em divergences.json (7)

branch-precreation (commit), persona-fallback-2454 (skills), skills-path-validation-detail (skills), native-hook-table (loop-hooks), warnings-always-present (loop-hooks), static-host-table (dispatch-model), model-resolution-subset (dispatch-model). Os contratos sob cairn/gsd/ ficaram intocados.

## Task Commits

1. **Task 1: commit, commit-to-subrepo e agent-skills** - `467a8e3` (feat)
2. **Task 2: loop render-hooks nativo + 4 verbos dispatch/model** - `5e750a6` (feat)

## Files Created/Modified

- `cairn/scripts/cairn-gsd.py` - +8 handlers; tabelas estáticas HOST_RUNTIMES e MODEL_CATALOG_AGENTS com source_ref; sanitize; sentinel atômico
- `tests/cairn-gsd.bats` - 44 testes (20 novos diretos das 4 famílias); mask do harness aceita golden já mascarado
- `tests/fixtures/gsd-goldens/scenarios.json` - 27 cenários novos (37 no total)
- `tests/fixtures/gsd-goldens/*.golden.json` - 25 recorded + 2 derived novos (35 no total)
- `tests/fixtures/gsd-goldens/divergences.json` - 7 entradas novas (13 no total)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] apply_mask_file do harness reprovava golden já mascarado**
- **Found during:** Task 1 (primeiro cenário com mask)
- **Issue:** o caminho de mask do comparador (nunca exercitado no plano 01 — todos os cenários tinham mask null) validava o valor do GOLDEN contra o regex, e o golden gravado carrega `"<masked>"`, que não casa — todo cenário mascarado reprovaria.
- **Fix:** o predicado aceita `test($re) or . == "<masked>"`; o controle negativo continua mordendo (hash errado reprova).
- **Files modified:** tests/cairn-gsd.bats
- **Committed in:** 467a8e3

**2. [Rule 1 - Bug] Semântica medida de commit_docs com .planning gitignored**
- **Found during:** Task 1 (diferencial reprovou o golden recorded de commit-skip-gitignored)
- **Issue:** o texto do contrato sugere o check de gitignore como segundo skip incondicional; o binário real, com .planning gitignored e config sem a chave, resolve commit_docs falsy ANTES (o default merged é suprimido) e responde skipped_commit_docs_false.
- **Fix:** implementação alinhada ao binário; dois cenários (commit-skip-gitignored com commit_docs:true explícito → skipped_gitignored; commit-gitignored-suppresses-default com config {} → skipped_commit_docs_false), ambos recorded.
- **Committed in:** 467a8e3

### Ajustes deliberados sobre o texto do plano

- **--raw nos acceptance:** o plano descreve `commit --raw` e `resolve-model --raw` devolvendo envelope; o binário faz o oposto (envelope sem flag, texto com --raw — divergência raw-flag-contract-doc declarada desde o 33-01). Os acceptance foram batidos na forma do binário: envelope testado sem --raw, texto cru com --raw.
- **Isolation/should-flatten:** ver "Registros pedidos pelo plano" — o cairn espelha o binário medido (harness-worktree / true) em vez das simplificações que o texto do plano antecipava (none / false), o que dispensou as divergências condicionais que o plano previa declarar e permitiu goldens recorded byte a byte.
- **loop `--raw`:** no binário, `--raw` e default emitem o MESMO envelope JSON (output sem rawValue); implementado igual. O envelope do cairn carrega `warnings` sempre (o shape de 4 chaves do contrato) — divergência warnings-always-present declarada.

---

**Total deviations:** 2 auto-fixadas (Rule 1) + 3 ajustes deliberados documentados
**Impact on plan:** todas as correções vieram da fidelidade ao binário real (o objetivo da fase); nenhum scope creep.

## Issues Encountered

- **`bats tests/` inteiro:** não re-exercitado de ponta a ponta nesta execução — o plano 01 registrou que a suíte completa estala em suítes ambientais (stage-plugins, cairn-doctor) neste sandbox, e a entrada unrun-verify correspondente já está aberta em `.planning/WINDOWS.md` para o gate de ship. As suítes tocadas ou vizinhas rodaram individualmente verdes: cairn-gsd (44), cairn-command-surfaces (14), gsd-contracts (24), cairn-inventory (24), cairn-wrap (24), smoke (5).
- **Golden recorded vs re-record em famílias divergentes:** um `cairn-gsd-record.sh` SEM `--only` re-grava também os 2 goldens derived do loop com os bytes do binário (que carregam hooks first-party do upstream) e quebraria o diferencial. Mitigação atual: o teste de reprodução compara derived só por exit; operador que re-gravar tudo deve restaurar os 2 derived (documentado aqui; candidato a flag `record:false` por cenário no 33-03 se incomodar).

## Known Stubs

Nenhum — nenhum valor hardcoded, placeholder ou verbo sem implementação real entrou neste plano.

## Threat Flags

Nenhuma superfície nova fora do threat model do plano: os handlers falam com git por subprocess com argumentos em lista (sem shell), a mensagem de commit é sanitizada antes do `-m`, e a escrita do sentinel é atômica e engolida em falha (contrato).

## Self-Check: PASSED

- Arquivos criados existem (27 goldens novos, cenários, divergências): FOUND
- Commits existem (467a8e3, 5e750a6): FOUND
- `git status --porcelain cairn/gsd/` vazio em todos os commits: OK
- STATE.md / ROADMAP.md / REQUIREMENTS.md intocados: OK
- `bats tests/cairn-gsd.bats`: 44/44 verde

## Next Phase Readiness

- Os 10 verbos das 5 famílias triviais respondem — o plano 33-03 (se existir verificação/fechamento) e as fases 34-35 herdam o dispatcher com o padrão handler + cenário + golden já provado em 4 famílias novas.
- A tabela estática de host (HOST_RUNTIMES) e o MODEL_CATALOG_AGENTS carregam source_ref para a tag pinada — um bump de tag na fase futura atualiza os dois pontos nomeados.

---
*Phase: 33-o-binario-python-familias-triviais*
*Completed: 2026-08-10*
