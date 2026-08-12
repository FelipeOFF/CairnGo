---
phase: 31-a-baseline-remedida-contra-a-tag
plan: "01"
subsystem: tooling
tags: [gsd-core, inventory, corpus, regex, git-clone, bats, python-stdlib]

# Dependency graph
requires: []
provides:
  - "cairn-inventory: comando reproduzível que mede o corpus GSD v1.10.0 sítio a sítio (arquivo, linha, escopo, verbo) sobre clone cacheado com commit pinado"
  - "Interface JSON consumida pelos planos 02-04 e pelo harness da fase 33: source/metric/scopes/sites/verbs/summary/accounting"
  - "Universo de verbos dos escopos workflows8 e agents (.verbs | keys[]) como insumo dos contratos"
  - "Cache .cairn/cache/gsd-core-v1.10.0 (gitignored) reutilizável pela fase 32 (vendoring)"
affects: [31-02, 31-03, 31-04, fase-32-vendoring, fase-33-harness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Script de rede declarada: clone on-demand em cache validado por commit pinado, cache-hit 100% offline (molde cairn-review.py)"
    - "Bloco datado MEASURED VERSUS ASSUMED com comando ao lado de cada contagem + GUARD numbers_not_in_json (molde cairn-trend.py)"
    - "Normalização de grafia dupla dirigida pelo dado: `query X Y` só vira `X.Y` quando a forma pontuada existe no corpus"

key-files:
  created:
    - cairn/scripts/cairn-inventory.py
    - cairn/scripts/cairn-inventory.sh
    - tests/cairn-inventory.bats
  modified:
    - .gitignore
    - tests/cairn-command-surfaces.bats

key-decisions:
  - "TAG_COMMIT pinado em 68a04ccf8ef74803bdb651e12c3b85b218bbccdf: a tag v1.10.0 é lightweight (ls-remote não devolve linha peeled), o sha da tag É o commit"
  - "AGENTS_SCOPE fixado em 16 nomes pela interseção mecânica agents/ × referências word-boundary nos 8 workflows; o fecho de 13 do research é exatamente esta lista menos o trio ui-* (1.178 linhas)"
  - "Verbos distintos dos 8 = 59 (medido; research balizou 60-61 pré-normalização) — o teste asserta o valor MEDIDO com o comando junto, nunca o script foi dobrado para forçar o número do research"
  - "Token de subcommand exige [a-z][a-z-]* como token completo (não o [a-z-]+ literal do plano) para nunca capturar flags como --json"

patterns-established:
  - "Contabilidade de completude por escopo: total_raw = calls + shim_preambles + other, identidade assertada em cada fatia com controle negativo"

requirements-completed: [REM-01, REM-02]

coverage:
  - id: D1
    description: "cairn-inventory.sh --json devolve, por sítio, arquivo/linha/escopo/verbo medidos exclusivamente sobre o clone cacheado da tag v1.10.0 (REM-01)"
    requirement: REM-01
    verification:
      - kind: integration
        ref: "tests/cairn-inventory.bats#clone from a local source produces --json with the expected sites"
        status: pass
      - kind: integration
        ref: "tests/cairn-inventory.bats#real corpus: 189 sites in the 8 workflows under the broad metric"
        status: pass
    human_judgment: false
  - id: D2
    description: "Métrica única declarada no artefato: BROAD_RE como constante comentada e como metric.regex no --json; CALIBRATION_RE só como reprodução documentada (REM-02)"
    requirement: REM-02
    verification:
      - kind: unit
        ref: "tests/cairn-inventory.bats#the declared metric and its calibration twin travel literally in --json"
        status: pass
      - kind: unit
        ref: "tests/cairn-inventory.bats#calibration feeds summary.corpus_calibration only — never sites or verbs"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cache-hit 100% offline; cache com HEAD divergente morre com exit 6 nomeando os dois shas (D-01)"
    verification:
      - kind: integration
        ref: "tests/cairn-inventory.bats#a cache hit is 100% offline: --source pointing nowhere still answers"
        status: pass
      - kind: integration
        ref: "tests/cairn-inventory.bats#a cache whose HEAD is not the expected commit dies 6 naming both shas"
        status: pass
    human_judgment: false
  - id: D4
    description: "Números de aceitação do research reproduzidos ou corrigidos com comando junto, contra o cache real; GUARDs de proveniência com controle negativo"
    verification:
      - kind: integration
        ref: "tests/cairn-inventory.bats#real corpus: the workflows8 slice reproduces 651 = 189 + 460 + 2"
        status: pass
      - kind: unit
        ref: "tests/cairn-inventory.bats#GUARD: every number in the human output is a value in the JSON"
        status: pass
    human_judgment: false
  - id: D5
    description: "Os sítios de accounting.*.other_sites no corpus real são de fato prosa (backstop: julgamento humano sítio a sítio)"
    verification: []
    human_judgment: true
    rationale: "Julgar se uma ocorrência é prosa ou chamada disfarçada é semântica, não padrão mecânico. Veredito do executor registrado no bloco datado do .py: os 4 sítios (execute-phase.md:378, autonomous.md:81, gsd-debug-session-manager.md:337, gsd-planner.md:658) são menções em backtick dentro de comentário."

# Metrics
duration: 100min
completed: 2026-08-10
status: complete
---

# Phase 31 Plan 01: cairn-inventory Summary

**Inventário executável do corpus GSD v1.10.0 sobre clone cacheado com commit pinado: 189 sítios/59 verbos nos 8 workflows sob a métrica larga declarada, contabilidade 651 = 189 + 460 + 2 reproduzida exata, calibração 534/116 exata — REM-01 e REM-02 fechados.**

## Performance

- **Duration:** ~100 min (≈25 min de implementação; o resto foi a regressão `bats tests/` completa, ~1000 testes)
- **Started:** 2026-08-10T04:10Z
- **Completed:** 2026-08-10T05:50Z
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments

- `cairn-inventory.py` (567 linhas, stdlib-only) + wrapper + suíte bats de 24 testes: clone `--depth 1 --branch v1.10.0` em cache sob `.cairn/cache/`, HEAD validado contra `TAG_COMMIT` em TODA execução (exit 6 nomeando os dois shas na divergência), cache-hit 100% offline provado por teste com `--source /nonexistent`.
- Números de aceitação contra o corpus real, todos com comando junto no bloco datado:
  - **189 sítios** nos 8 workflows (métrica larga) — reproduz o research **exato**; **59 verbos** distintos (research balizou 60-61; a normalização da grafia dupla que este inventário fixa mede 59 — valor medido assertado).
  - **Calibração 534 chamadas / 116 verbos** no corpus — **exato**.
  - **17 sítios** de `loop render-hooks` nos 8 — **exato**.
  - **Contabilidade workflows8: 651 = 189 + 460 + 2** — **exato**, com os 2 `other` enumerados e julgados prosa; fatia agents: 227 = 65 + 160 + 2, identidade assertada nas DUAS fatias com controle negativo.
  - **Agents: 65 sítios / 42 verbos** sobre os 16 nomes de `AGENTS_SCOPE` (research: 64/42 sobre "12 despachados" sem comando registrado; a lista declarada decide, comando de derivação no bloco datado).
- Normalização data-driven da grafia dupla: `query verification status` == `verification.status` = UM verbo, duas spellings — sem lista hardcoded (`query X Y` só normaliza quando a forma pontuada existe no corpus).
- GUARDs de proveniência portados do trend: todo número da saída humana existe como escalar no `--json` (com controle negativo de forja); nenhuma contagem viva fora do bloco datado `MEASURED VERSUS ASSUMED` no `.py` nem no `.sh`.

## Task Commits

1. **Task 1 (tracer): clone cacheado + varredura larga + --json** - `4d79a31` (feat)
2. **Task 2 RED: testes da classificação completa** - `5953aa6` (test)
3. **Task 2 GREEN: escopos, normalização, contabilidade por escopo** - `75bcdb5` (feat)
4. **Task 3 RED: GUARDs + números de aceitação skip-gated** - `59d249b` (test)
5. **Task 3 GREEN: render mecânico + bloco datado** - `daca13d` (feat)
6. **Fix regressão: razão do inventory no guard de alcançabilidade** - `a99be69` (fix)

## Files Created/Modified

- `cairn/scripts/cairn-inventory.py` - o inventário: corpus/varredura/classificação/modelo único, bloco datado MEASURED VERSUS ASSUMED
- `cairn/scripts/cairn-inventory.sh` - wrapper exec python3, contrato no cabeçalho sem contagens vivas
- `tests/cairn-inventory.bats` - 24 testes: fixtures locais (zero rede), GUARDs com controles negativos, bloco real skip-gated
- `.gitignore` - entrada `.cairn/cache/` com dono, chave de invalidação e motivo (D-01)
- `tests/cairn-command-surfaces.bats` - razão escrita do script sem comando `/cairn:` (exigência do guard de alcançabilidade)

## Decisions Made

- **TAG_COMMIT = 68a04cc…**: pinado pela linha da tag do `ls-remote` (tag lightweight — ver desvio 1); validado por `rev-parse HEAD` do clone real.
- **AGENTS_SCOPE = 16 nomes**: interseção mecânica `agents/*.md` × grep -w nos 8 (idêntico incluindo subdirs). Divergência com o research anotada: o fecho de 13 = os 16 menos o trio ui-* (457+341+380 = 1.178 linhas — a diferença exata entre 9.900 e 8.722).
- **59 verbos assertados (não 60-61)**: cláusula "reproduzi-los ou corrigi-los com o comando junto" aplicada — o teste carrega o valor medido e o comando, o script nunca foi ajustado para forçar o número do research.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Premissa do plano] A tag v1.10.0 é lightweight, não anotada**
- **Found during:** Task 1 (precondition check)
- **Issue:** O plano instruía pinar o sha peeled pela linha `^{}` do ls-remote ("tag anotada: usar a linha ^{}"); o ls-remote não devolve linha peeled — a tag é lightweight e o sha da tag é o próprio commit.
- **Fix:** `TAG_COMMIT` pinado pela linha da tag, com a derivação documentada na constante e no bloco datado; a validação `rev-parse HEAD` do clone real confirma.
- **Files modified:** cairn/scripts/cairn-inventory.py
- **Verification:** execução real: `.source.commit` == TAG_COMMIT, exit 0
- **Committed in:** 4d79a31

**2. [Rule 2 - Correção de padrão] Token de subcommand não captura flags**
- **Found during:** Task 1/2
- **Issue:** O plano dizia "o token `[a-z-]+` imediatamente após o match" — esse padrão literal capturaria `--json`/`--pick` como subcommand (o hífen inicial casa).
- **Fix:** fullmatch `[a-z][a-z-]*` sobre o token completo (começa em letra); `gsd_run query state.load --json` fica com subcommand null, `gsd_run loop render-hooks` captura render-hooks.
- **Files modified:** cairn/scripts/cairn-inventory.py
- **Verification:** testes 9 e 10 da suíte
- **Committed in:** 4d79a31

**3. [Rule 3 - Blocking] Guard de alcançabilidade exigiu razão escrita para o script novo**
- **Found during:** verificação (regressão `bats tests/`)
- **Issue:** `tests/cairn-command-surfaces.bats` falha para qualquer script sem comando `/cairn:` e sem razão na tabela — o cairn-inventory é medição de mantenedor, sem comando por desenho.
- **Fix:** entrada `inventory)` na tabela do teste, no estilo da entrada `trend`.
- **Files modified:** tests/cairn-command-surfaces.bats
- **Verification:** `bats tests/cairn-command-surfaces.bats` verde (14/14)
- **Committed in:** a99be69

**4. [Nota] 31-PATTERNS.md referenciado pelo plano não existe**
- O read_first da Task 1 aponta `.planning/phases/31-a-baseline-remedida-contra-a-tag/31-PATTERNS.md`, ausente do disco. Executado com os análogos diretos (cairn-trend.py, cairn-review.py, cairn-trend.sh, cairn-trend.bats), que o próprio plano lista.

---

**Total deviations:** 3 auto-fixed (1 premissa, 1 padrão, 1 blocking) + 1 nota
**Impact on plan:** Nenhum scope creep; os três fixes eram necessários para correção. A divergência de tag é só de derivação do sha — o pino e a validação funcionam como especificados.

## Issues Encountered

- **Regressão `bats tests/` (~1000 testes) leva >40 min** nesta máquina; rodada em lotes. Resultado: únicas falhas foram a do guard de alcançabilidade (causada pelo plano, corrigida — desvio 3) e **uma falha pré-existente** em `tests/cairn-trend.bats` ("real tree: the series is not contiguous…"), que reproduz idêntica no checkout main sem nenhum commit deste plano — registrada em `deferred-items.md` da fase, não corrigida (fora de escopo).

## Known Stubs

Nenhum — nenhum valor hardcoded vazando para saída, nenhum TODO/FIXME, nenhum teste pulado (os skip-gated reais RODARAM nesta máquina, cache presente).

## Next Phase Readiness

- O universo de verbos (`.verbs | keys[]`) e a interface JSON estão prontos para os planos 02-04 (contratos por verbo) e para o harness da fase 33.
- O cache `.cairn/cache/gsd-core-v1.10.0` fica disponível para a fase 32 (vendoring) — mesma fonte, mesmo commit verificado.
- `cairn/scripts/cairn-doctor.py` intocado por todos os commits do plano (D-03): `git log 21b76ed..HEAD -- cairn/scripts/cairn-doctor.py` vazio.

---
*Phase: 31-a-baseline-remedida-contra-a-tag*
*Completed: 2026-08-10*

## Self-Check: PASSED

Arquivos criados e todos os 6 commits verificados no repositório (2026-08-10).
