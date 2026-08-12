---
phase: 33-o-binario-python-familias-triviais
plan: 01
subsystem: gsd-transplant
tags: [python, bats, gsd-tools, goldens, config, diferencial]

requires:
  - phase: 31-contratos-por-verbo
    provides: cairn/gsd/contracts/ (contracts.json + config.json) e o cache verificado .cairn/cache/gsd-core-v1.10.0
provides:
  - dispatcher cairn/scripts/cairn-gsd.py + cairn-gsd.sh roteando pelos spellings do contrato (exits 0/1/2/4)
  - família config completa — config-get com a cadeia inteira (escopo → --default → schema default via manifest em cadeia declarada) e config-set com coerção/validação/escrita atômica do upstream
  - harness diferencial tests/cairn-gsd.bats + manifesto tests/fixtures/gsd-goldens/scenarios.json (molde das fases 34-35)
  - recorder cairn-gsd-record.py/.sh (D-02) — goldens re-graváveis do binário real, skip-gated e atômico
  - 10 goldens de config com provenance `recorded` (bytes do binário real da tag) + divergences.json da fase
affects: [33-02, 33-03, fase-34, fase-35, fase-36-shim]

actuals:
  tokens: 22800
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "diferencial por provenance: golden `recorded` compara literal (bytes/json); `derived-from-contract` compara por forma (exit + stdout normalizado)"
    - "cadeia declarada de manifest: seam de env → árvore vendorizada (fase 32) → clone em cache com HEAD verificado → die nomeado"
    - "escrita atômica temp irmão + os.replace (forma do platformWriteSync do upstream)"

key-files:
  created:
    - cairn/scripts/cairn-gsd.py
    - cairn/scripts/cairn-gsd.sh
    - cairn/scripts/cairn-gsd-record.py
    - cairn/scripts/cairn-gsd-record.sh
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
    - tests/fixtures/gsd-goldens/config-defaults.fixture.json
    - tests/fixtures/gsd-goldens/*.golden.json (10, provenance recorded)
  modified:
    - tests/cairn-command-surfaces.bats

key-decisions:
  - "A semântica de saída segue o BINÁRIO real, não o texto do contrato: sem --raw é JSON.stringify(valor, null, 2); com --raw é String(valor); sem newline final — o contrato da fase 31 descreve o --raw invertido (divergência declarada)"
  - "O manifest de defaults do clone fica em gsd-core/bin/shared/config-defaults.manifest.json (caminho (b) confirmado); o config-schema.manifest.json irmão fornece validKeys/dynamicKeyPatterns ao config-set"
  - "Cenários requires:config-manifest recebem um manifest fixture COMMITADO pelo seam de env — o diferencial roda verde offline em vez de skipar; a cadeia real (b) tem testes próprios skip-gated"
  - "config.json é escrito na forma do binário (indent 2, ordem de inserção, newline final) em vez do sort_keys da casa — fidelidade byte ao upstream; idempotência e rejeição-intocada testadas"

patterns-established:
  - "Diferencial por provenance: byte-igualdade só para golden recorded; derived compara por forma"
  - "Recorder nunca clona, nunca roda no repo real, nunca deixa golden parcial (temp + rename atômico)"

requirements-completed: [TRIV-01, TRIV-04]

coverage:
  - id: D1
    description: "Dispatcher cairn-gsd responde config-get/config-set pelo contrato, com exits 2/4 nomeados para uso e família não implementada"
    requirement: TRIV-01
    verification:
      - kind: integration
        ref: "bats tests/cairn-gsd.bats (24 testes)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Harness diferencial com manifesto de cenários e 10 goldens provenance recorded, verde offline com skips nomeados"
    requirement: TRIV-04
    verification:
      - kind: integration
        ref: "bats tests/cairn-gsd.bats — diferencial + controle negativo de golden adulterado"
        status: pass
    human_judgment: false
  - id: D3
    description: "Recorder skip-gated re-grava goldens do binário real com escrita atômica e reprodução byte a byte"
    requirement: TRIV-04
    verification:
      - kind: integration
        ref: "bats tests/cairn-gsd.bats — corpus stub (gates 5/6, mask, abort) + reprodução byte a byte contra o corpus real"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-08-10
status: complete
---

# Phase 33 Plan 01: Tracer + família config + recorder Summary

**Dispatcher python cairn-gsd respondendo a família config na forma byte-exata do gsd-tools real da tag (goldens gravados do binário, provenance recorded), com harness diferencial bats e recorder atômico que as fases 34-35 herdam**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-08-10T15:39:01Z
- **Completed:** 2026-08-10T16:44:00Z
- **Tasks:** 3
- **Files modified:** 19 (2206 inserções)

## Accomplishments

- Tracer completo: `config-get` atravessa dispatcher → wrapper → cenário → golden → diferencial; exits do dispatcher (2 fora do universo, 4 família não implementada nomeando família e fase, órfãos de CHECK-03 → fase 35) testados.
- Família config no contrato (TRIV-01): cadeia completa do config-get (escopo → --default → schema default via manifest resolvido em cadeia declarada), config-set com coerção upstream ('null' desfaz a chave, Infinity não coage, project_code verbatim), validadores centrais, secrets exatos (`****`+4) e escrita atômica — concorrência termina sempre em JSON válido.
- Harness diferencial (metade mecânica de TRIV-04): manifesto único de cenários consumido pelo bats E pelo recorder; comparação por provenance com controle negativo (golden adulterado reprova); verde offline com skips nomeados.
- Recorder (D-02): gates na ordem (HEAD verificado → node → probe/build), fixture descartável por cenário, mask validada, golden em temp + rename atômico. **Gravação real executada nesta máquina: build do runtime ok (`npm install` + `npm run build:lib` no clone), os 10 goldens promovidos a `recorded` e reproduzidos byte a byte.**

## Registros pedidos pelo plano

- **Caminho de origem do manifest no clone (caminho (b) da cadeia):** `gsd-core/bin/shared/config-defaults.manifest.json` (confirmado; o irmão `config-schema.manifest.json` no mesmo diretório fornece validKeys/runtimeStateKeys/dynamicKeyPatterns ao config-set).
- **Resultado da tentativa real de --record:** SUCESSO — cache restaurado via `cairn-inventory.sh` (HEAD 68a04cc verificado), runtime buildado, `cairn-gsd-record.sh` gravou os 10 cenários com provenance `recorded`; o diferencial segue verde na comparação literal.
- **Entradas adicionadas a divergences.json (6):** workstream-root-layer (#2702 ausente), raw-flag-contract-doc (contrato da fase 31 descreve o --raw invertido; o cairn segue o binário medido), schema-default-source (manifest em cadeia vs SCHEMA_DEFAULTS+capability-registry), valid-keys-domain, capability-type-validation, stderr-form.

## Task Commits

1. **Task 1: Tracer — config-get de ponta a ponta** - `e7a05d0` (feat)
2. **Task 2: Família config completa — manifest em cadeia + config-set** - `c9a912a` (feat)
3. **Task 3: Recorder — goldens do binário real** - `0495ed0` (feat)
4. **Fix de regressão: guard de portas do command-surfaces** - `5d98662` (fix)

## Files Created/Modified

- `cairn/scripts/cairn-gsd.py` - dispatcher único das famílias triviais (D-01); roteamento por spellings do contrato
- `cairn/scripts/cairn-gsd.sh` - wrapper fino (usage + exits no header)
- `cairn/scripts/cairn-gsd-record.py` / `.sh` - recorder de goldens (D-02)
- `tests/cairn-gsd.bats` - harness diferencial + testes de dispatcher, cadeia e recorder (24 testes)
- `tests/fixtures/gsd-goldens/scenarios.json` - manifesto único de cenários (bats + recorder)
- `tests/fixtures/gsd-goldens/*.golden.json` - 10 goldens `recorded` do binário real
- `tests/fixtures/gsd-goldens/divergences.json` - tabela única de divergências deliberadas da fase
- `tests/fixtures/gsd-goldens/config-defaults.fixture.json` - manifest fixture do seam (offline)
- `tests/cairn-command-surfaces.bats` - razões escritas dos dois scripts novos no guard de portas

## Decisions Made

Ver `key-decisions` no frontmatter. A mais importante: onde o texto do contrato e o binário real divergiram, **o binário venceu** — é dele que os goldens gravam e é ele que os call sites do corpus consomem (`config-get runtime --default claude --raw` espera texto cru); a divergência de documentação ficou declarada na tabela, nunca improvisada.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Semântica do --raw invertida no contrato da fase 31**
- **Found during:** Task 2 (leitura do src/config.cts + io.cts do clone e probes do binário buildado)
- **Issue:** O contrato (e o texto do plano derivado dele) diz "sem --raw imprime String(valor); com --raw imprime JSON". O binário real faz o OPOSTO (io.cts `output()`, gsd-tools.cjs L3782-3784), e nenhuma das saídas carrega newline final.
- **Fix:** Implementação alinhada ao binário medido; goldens re-derivados e depois gravados do binário real; entrada `raw-flag-contract-doc` em divergences.json (cairn/gsd/ é somente-leitura para a 33 — o contrato não pôde ser corrigido aqui).
- **Files modified:** cairn/scripts/cairn-gsd.py, tests/fixtures/gsd-goldens/*
- **Verification:** probes byte a byte contra o binário + reprodução byte a byte do --record
- **Committed in:** c9a912a

**2. [Rule 3 - Blocking] 33-PATTERNS.md referenciado pelo plano não existe**
- **Found during:** Task 1 (read_first)
- **Issue:** `.planning/phases/33-.../33-PATTERNS.md` é citado no read_first e no context, mas o arquivo não existe no worktree.
- **Fix:** Execução seguiu o texto do plano (autossuficiente: exits, ordem de gates e formas estão inline) + os precedentes citados (cairn-inventory, cairn-config, gsd-contracts.bats).
- **Verification:** acceptance criteria de cada task batidos um a um.

**3. [Rule 1 - Regressão] Guard de portas do cairn-command-surfaces.bats reprovava os scripts novos**
- **Found during:** verificação de regressão da suíte inteira
- **Issue:** o teste "every script is either a command or carries a reason" itera `cairn/scripts/cairn-*.py`; os dois scripts novos não têm comando `/cairn:` (de propósito).
- **Fix:** razões escritas na tabela do teste — a via que a mensagem de erro do próprio teste manda.
- **Committed in:** 5d98662

### Ajustes deliberados sobre o texto do plano

- **Escrita do config.json:** forma do binário (indent 2, ordem de inserção, newline) em vez de "sort_keys da casa" — fidelidade ao upstream evita reordenar o arquivo do usuário; idempotência e "rejeitado deixa intocado" mantidos e testados por sha256.
- **Cenários `requires:"config-manifest"`:** em vez de skipar offline, o runner injeta um manifest fixture commitado pelo seam de env — o diferencial roda verde offline; a cadeia real (b) tem teste próprio skip-gated (exercitado verde nesta execução com o cache presente).
- **Acceptance do tracer "imprime quality":** o binário real imprime `"quality"` sem --raw e `quality` com --raw; os cenários cobrem os dois. Consequência direta da deviation 1.

---

**Total deviations:** 3 auto-fixadas (2×Rule 1, 1×Rule 3) + 3 ajustes deliberados documentados
**Impact on plan:** as correções foram exigidas pela fidelidade ao binário real (o objetivo da fase); nenhum scope creep.

## Issues Encountered

- **`bats tests/` inteiro não concluiu neste sandbox:** a execução completa estalou em `stage-plugins.bats` (e deixou processos pendurados em `cairn-doctor.bats`) — comportamento ambiental, sem relação com os arquivos do plano (nenhuma dessas suítes toca os artefatos novos). As suítes afetadas pelo plano foram rodadas individualmente e estão verdes: cairn-command-surfaces (14), cairn-inventory (24), gsd-contracts (24), cairn-gsd (24), cairn-wrap (24), smoke (5). Registrado em `.planning/WINDOWS.md` (kind: unrun-verify) para o gate de ship reexecutar a suíte completa.
- Nomes de @test com "í" quebram o registro de testes do bats 1.14 nesta máquina ("unknown test name") — nomes de teste ficaram sem acento.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: supply-chain | cairn/scripts/cairn-gsd-record.py | O gate (3) roda `npm install` + `npm run build:lib` DENTRO do clone em cache — executa lifecycle scripts das dependências do gsd-core pinado. Mitigação presente: só roda após verificação do HEAD contra o commit pinado da tag; ainda assim é execução de código de terceiros na máquina do mantenedor. |

## Self-Check: PASSED

- Arquivos criados existem (cairn-gsd.py/.sh, cairn-gsd-record.py/.sh, tests/cairn-gsd.bats, scenarios.json, divergences.json, 10 goldens): FOUND
- Commits existem (e7a05d0, c9a912a, 0495ed0, 5d98662): FOUND
- `git status --porcelain cairn/gsd/` vazio em todos os commits: OK
- STATE.md / ROADMAP.md / REQUIREMENTS.md intocados: OK

## Next Phase Readiness

- O formato golden+diferencial+recorder está pronto para os planos 33-02/33-03 (famílias commit, skills, loop-hooks, dispatch-model) — basta adicionar cenários ao manifesto e handlers ao dispatcher.
- O runtime do clone fica buildado no cache desta máquina; noutras máquinas o recorder skipa nomeado ou builda sob demanda.
- A fase 36 aponta o preâmbulo `gsd_run()` para `cairn/scripts/cairn-gsd.sh` (caminho estável, D-01).

---
*Phase: 33-o-binario-python-familias-triviais*
*Completed: 2026-08-10*
