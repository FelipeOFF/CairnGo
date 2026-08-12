---
phase: 31-a-baseline-remedida-contra-a-tag
verified: 2026-08-10T00:00:00Z
status: passed
score: 27/27 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: false
requirements_satisfied: [REM-01, REM-02, REM-03, REM-04, REM-05]
test_results:
  suites: [tests/cairn-inventory.bats, tests/gsd-contracts.bats]
  passed: 48
  failed: 0
  skipped: 0
  note: "cache quente — os testes skip-gated contra o corpus real rodaram todos"
---

# Fase 31: A baseline remedida contra a tag — Relatório de Verificação

**Goal da fase:** fixar o corpus na tag v1.10.0, adotar UMA métrica declarada
(a larga), produzir o inventário como comando executável com contrato de
entrada e saída por verbo, extrair do gsd-tools.cjs bakeado a semântica dos 4
verbos sem fonte em src, e re-derivar a estimativa de init pelos 9 shapes de
bundle. Regra permanente: source com source, nunca `~/.claude`.

**Verificado em:** 2026-08-10, no worktree `phase/31-a-baseline-remedida-contra-a-tag`.
**Método:** goal-backward — cada truth dos 4 PLANs conferida rodando o comando
real, nunca confiando nos SUMMARYs. Cache do clone quente
(`.cairn/cache/gsd-core-v1.10.0`, HEAD `68a04ccf8ef74803bdb651e12c3b85b218bbccdf`),
então até os testes skip-gated contra o corpus real executaram.

## Veredito por truth

### Plano 01 — inventário executável (REM-01, REM-02)

| # | Truth | Status | Evidência |
|---|-------|--------|-----------|
| 1 | `--json` devolve por sítio arquivo relativo, linha, escopo e verbo, medido só sobre o clone da tag (REM-01) | ✓ VERIFIED | `bash cairn/scripts/cairn-inventory.sh --json` → 254 sites; `site[0] = {file: "gsd-core/workflows/discuss-phase.md", line: 119, scope: "workflows8", verb: "init.phase-op", ...}`; `source.cache_dir` aponta o clone, `cache_state: hit` |
| 2 | Métrica única declarada: regex larga como constante comentada no .py e escalar `metric.regex` no `--json`; calibração só como reprodução documentada (REM-02) | ✓ VERIFIED | JSON: `metric = {name: "broad", regex: "gsd_run (query )?[a-z][a-z-]*(\\.[a-z-]+)?", calibration_regex: ...}`; bats 12 "the declared metric and its calibration twin travel literally in --json" e 9 "calibration feeds summary.corpus_calibration only — never sites or verbs" (ok) |
| 3 | Com cache válido a execução é 100% offline, provado por teste com `--source` inexistente | ✓ VERIFIED | bats 2 "a cache hit is 100% offline: --source pointing nowhere still answers" (ok) — teste comportamental, roda de verdade |
| 4 | Cache com HEAD divergente morre exit 6 nomeando os dois shas | ✓ VERIFIED | `cairn-inventory.py:263-266` (`die(f"cache HEAD {head} does not match the expected tag commit {expected_commit}...", EXIT_BAD_CORPUS)` com `EXIT_BAD_CORPUS = 6`); bats 3 "a cache whose HEAD is not the expected commit dies 6 naming both shas" (ok) |
| 5 | Toda ocorrência bruta classificada em calls/shim_preambles/other por escopo; other enumerado; identidade `total_raw = calls + shim + other` assertada por bats em cada escopo com controle negativo | ✓ VERIFIED | JSON real: `workflows8: 651 = 189+460+2`, `agents: 227 = 65+160+2`, `other_sites` enumerados com file/line/excerpt; bats 11, 13, 23, 24 (identidade nas duas fatias, fixture e corpus real) e 13 é o controle negativo de prosa (ok) |
| 6 | Números de aceitação do research reproduzidos ou corrigidos com comando, no bloco datado MEASURED VERSUS ASSUMED | ✓ VERIFIED | Bloco datado 2026-08-10 no .py: 534/116 exato, 189 exato, 59 verbos (corrige o 60-61 pela normalização da grafia dupla, com comando), 65/42 (corrige o 64 do research, com comando), 17 render-hooks exato, 651=189+460+2 exato; bats 19-24 asseram contra o cache real (ok) |
| 7 | AGENTS_SCOPE é constante declarada, comando de derivação no bloco datado | ✓ VERIFIED | `AGENTS_SCOPE` no .py; JSON `scopes.agents.files` = 16 arquivos; bloco datado grava o loop `for f in agents/*.md ... grep -qw` e explica a divergência com o fecho de 13 do research (trio ui-*, 1.178 linhas) |
| 8 | Todo token numérico da saída humana existe como escalar no `--json` (GUARD com controle negativo) | ✓ VERIFIED | bats 15 "GUARD: every number in the human output is a value in the JSON" e 16 "GUARD negative control: the check rejects a forged number" (ok); bats 17-18 cobrem o guard do bloco datado |
| 9 | (backstop) Os `other_sites` do corpus real são de fato prosa, julgamento nomeado no bloco datado | ✓ VERIFIED | Veredito humano registrado no bloco datado, sítio a sítio; re-conferido pelo verificador abrindo os 4 sítios no clone: `execute-phase.md:378`, `autonomous.md:81`, `agents/gsd-debug-session-manager.md:337`, `agents/gsd-planner.md:658` — todos menção em backtick dentro de prosa/comentário, nenhuma chamada |

### Plano 02 — contratos, agregado + 5 famílias triviais (REM-03)

| # | Truth | Status | Evidência |
|---|-------|--------|-----------|
| 10 | `cairn/gsd/contracts/` existe com agregado + config/commit/skills/loop-hooks/dispatch-model sob o mesmo schema (D-02) | ✓ VERIFIED | 12 arquivos em `cairn/gsd/contracts/`; bats 26 "every family file has schema_version 1, family, source{repo,tag,commit} and non-empty verbs" (ok) |
| 11 | Cada entrada carrega verb, invocation, input, output (kind + exit_codes) e source_ref com path/linhas na tag; nenhuma sem source_ref | ✓ VERIFIED | bats 27 e 31 (ok); amostra conferida: `config-get → src/config.cts L965-L1044`, aberto no clone — `cmdConfigGet` começa exatamente na L965 e a invocation bate |
| 12 | `contracts.json` indexa verbo→família/arquivo bidirecionalmente consistente, por teste | ✓ VERIFIED | bats 35, 36 ("the verb SETS are identical in both directions"), 40 (ok) |
| 13 | `tests/gsd-contracts.bats` valida schema de todo arquivo com jq e passa | ✓ VERIFIED | `bats tests/gsd-contracts.bats` → 24/24 ok |
| 14 | Todo verbo do universo do inventário nas 5 famílias tem contrato | ✓ VERIFIED | bats 37 "real universe: every inventory verb has a contract — total coverage" rodou contra a saída real (ok); 38 é o controle negativo de forja (ok) |
| 15 | (backstop) Amostra confere com a implementação da tag | ✓ VERIFIED | Verificador abriu `src/config.cts:965` no clone: assinatura e uso batem com o contrato registrado |

### Plano 03 — 6 famílias restantes + cobertura fechada (REM-03)

| # | Truth | Status | Evidência |
|---|-------|--------|-----------|
| 16 | estado/roadmap-phase/worktree/init/checagem/misc existem sob o schema do 02, com source_ref por verbo | ✓ VERIFIED | Os 6 arquivos existem; bats 26-27, 31 varrem TODOS os arquivos da pasta (ok) |
| 17 | Grafia dupla de verification.status representada no contrato | ✓ VERIFIED | `checagem.json` → entry com `spellings: ["query verification status", "query verification.status"]`; bats 10 no inventário prova que as duas grafias contam UM verbo (ok) |
| 18 | Os 4 verbos com sítio real fora da soma (audit-open, review-lane, agent.classify-failure, task.is-behavior-adding) têm contrato com source_ref em src | ✓ VERIFIED | jq: `audit-open → src/audit.cts`, `review-lane → src/review-lane-descriptor.cts`, `agent.classify-failure → src/agent-command-router.cts`, `task.is-behavior-adding → src/task-command-router.cts` — todos sem provenance de bundle |
| 19 | Cobertura fecha: todo verbo do universo tem entrada no índice e na família, teste roda contra a saída real (skip-gated) | ✓ VERIFIED | bats 37 rodou (cache quente, sem skip) e passou; universo = 87 verbos indexados |
| 20 | `contracts.json` indexa as 11 famílias com consistência bidirecional verde | ✓ VERIFIED | Agregado tem 11 famílias; bats 32 "contracts.json declares the 11 families of research §4 with one file each", 34-36 (ok) |
| 21 | (backstop) Amostra das 6 famílias confere com a tag | ✓ VERIFIED | Verificador abriu `src/state.cts:336` no clone: `cmdStateLoad` começa exatamente na linha citada por `estado.json` |

### Plano 04 — órfãos do bundle, init re-derivado, instalador (REM-04, REM-05)

| # | Truth | Status | Evidência |
|---|-------|--------|-----------|
| 22 | Os 4 órfãos têm contrato no mesmo schema, com provenance e source_ref em gsd-core/bin/gsd-tools.cjs (D-04, REM-04) | ✓ VERIFIED | jq: os 4 têm `provenance: "extraído do gsd-tools.cjs bakeado"` + `source_ref.path: gsd-core/bin/gsd-tools.cjs`; verificador abriu `gsd-tools.cjs:3452` no clone — `function runWithTimeout(argv)` e o USAGE literal batem com a invocation do contrato; bats 41 assere schema pleno (input/output/exit_codes) — nunca stub |
| 23 | Distinção testada nos dois sentidos: não-órfã sem provenance de bundle; órfã nunca aponta src/ | ✓ VERIFIED | bats 42 "no entry carrying provenance points source_ref at src/" e 43 "no entry without provenance points source_ref at the baked gsd-tools.cjs" (ok) |
| 24 | Estimativa de init re-derivada pelos 9 shapes: campos consumidos por call site, composição em src/init.cts, estimativa python por shape com método (REM-05) | ✓ VERIFIED | `init.json.bundle_shapes` = 9 shapes com `consumed_fields`, `consumption_sites`, `origin_handler`, `source_ref`, `python_estimate_lines`, rationale; `measurements.init_budget` total 490 = soma dos per_shape com método e data; bats 45-46 (ok); shape `init.execute-phase → src/init.cts L817` conferido no clone |
| 25 | Instalador com UM número oficial e filtro declarado: padrões + comando find/wc gravados, subconjunto estreito nomeado como componente | ✓ VERIFIED | `measurements.installer_cut`: `official_number: 10164` (amplo), `filter_patterns`, `command` exato, `narrow_subset` com comando próprio; bats 47 (ok) e 48 re-executa os comandos gravados contra o clone real e reproduz os números (ok) — o 10.331 esperado divergiu e foi corrigido com o comando junto, como a truth exige |
| 26 | A tolerância de cobertura do plano 03 morreu: universo e índice coincidem sem exceção | ✓ VERIFIED | bats 39 "the tolerance really died: the aggregate carries no verbs_pending_plan_04 and index == universe count" (ok) |
| 27 | (backstop) Estimativa de init defensável shape a shape | ✓ VERIFIED | Cada shape carrega composição, contagem e rationale conferíveis; amostra `init.execute-phase` conferida contra `src/init.cts:817` no clone |

**Score: 27/27 truths verificadas** (as 4 backstop confirmadas com evidência
colhida pelo próprio verificador contra o clone, não por confiança no SUMMARY).

## Proibições (checks negativos)

| Proibição | Status | Evidência |
|-----------|--------|-----------|
| Nunca ler `~/.claude` nem runtime instalado (source com source) | ✓ VERIFIED | `grep -n "\.claude" cairn/scripts/cairn-inventory.py` → única ocorrência é prosa da própria proibição no docstring; todos os source_ref dos contratos apontam paths do clone (`src/...`, `gsd-core/bin/gsd-tools.cjs`), nunca `~/.claude` |
| O corpus clonado nunca entra no controle de versão (D-01) | ✓ VERIFIED | `.gitignore` tem `.cairn/cache/` com comentário nomeando dono e chave de invalidação (commit da tag / exit 6); `git ls-files .cairn/cache/` → 0 arquivos |
| `cairn-doctor.py` intocado pela fase (D-03) | ✓ VERIFIED | `git diff $(git merge-base main HEAD)..HEAD -- cairn/scripts/cairn-doctor.py` → vazio nos 27 commits do branch |
| Nenhuma entrada de contrato de memória; órfãos nunca reduzidos a stub | ✓ VERIFIED | bats 31 (nenhuma entrada sem source_ref) + 41 (schema pleno dos órfãos) + amostras abertas no clone pelo verificador |

## Artefatos

| Artefato | Nível 1-3 | Detalhe |
|----------|-----------|---------|
| `cairn/scripts/cairn-inventory.py` | ✓ VERIFIED | 254 sítios medidos, bloco MEASURED VERSUS ASSUMED datado presente, exit codes 0/2/5/6, executado de verdade |
| `cairn/scripts/cairn-inventory.sh` | ✓ VERIFIED | `exec python3` no wrapper, cabeçalho reapresenta o contrato sem contagens vivas (bats 17 guarda isso no .py) |
| `tests/cairn-inventory.bats` | ✓ VERIFIED | 24/24 ok — fixtures sintéticos + GUARDs + asserções contra o cache real |
| `cairn/gsd/contracts/*.json` (12 arquivos) | ✓ VERIFIED | agregado + 11 famílias, 87 verbos, consistência bidirecional |
| `tests/gsd-contracts.bats` | ✓ VERIFIED | 24/24 ok — schema jq, cobertura total, provenance, measurements |
| `.gitignore` | ✓ VERIFIED | `.cairn/cache/` com comentário |

## Key links

| De | Para | Via | Status |
|----|------|-----|--------|
| cairn-inventory.sh | cairn-inventory.py | `exec python3` | ✓ WIRED |
| cairn-inventory.py | `.cairn/cache/gsd-core-v1.10.0` | clone `--depth 1 --branch v1.10.0` + `rev-parse HEAD` vs TAG_COMMIT | ✓ WIRED (cache hit real, commit `68a04cc` validado) |
| tests/*.bats | cairn-inventory.sh | CAIRN_SCRIPTS_DIR (helpers.bash) | ✓ WIRED (48 testes rodaram por esse caminho) |
| contracts.json | arquivos de família | mapa families + índice verbs | ✓ WIRED (bats 35-36, 40) |
| contratos | clone da tag | source_ref.path/lines | ✓ WIRED (4 amostras abertas no clone, todas batem na linha) |
| tests/gsd-contracts.bats | cairn-inventory.sh | teste de cobertura contra o universo real | ✓ WIRED (bats 37, rodou sem skip) |

## Cobertura de requisitos

| Req | Plano | Status | Evidência |
|-----|-------|--------|-----------|
| REM-01 | 31-01 | ✓ SATISFIED | comando reproduzível sobre a tag; sítio com file/line/scope/verb/spelling |
| REM-02 | 31-01 | ✓ SATISFIED | métrica larga única declarada no artefato; 147 vs 189 vira 189 com método (a calibração fica documentada como reprodução do 534/116) |
| REM-03 | 31-02/03 | ✓ SATISFIED | 87 verbos com contrato de entrada/saída e source_ref na tag, cobertura total testada contra o inventário real |
| REM-04 | 31-04 | ✓ SATISFIED | 4 órfãos com semântica extraída do gsd-tools.cjs do clone, provenance declarada, distinção testada nos dois sentidos |
| REM-05 | 31-04 | ✓ SATISFIED | init re-derivado: 490 linhas pelos 9 shapes com método; instalador: 10.164 (amplo, oficial) com filtro e comando gravados, estreito nomeado; comandos re-executados reproduzem os números (bats 48) |

Nenhum requisito órfão: o ROADMAP mapeia exatamente REM-01..05 à fase 31 e os
4 planos os reivindicam todos.

## Anti-patterns

Nenhum TODO/FIXME/XXX/placeholder nos arquivos da fase (o único "XXXXXX" é
template de `mktemp` em fixture de teste). Nenhum stub, nenhum retorno estático.

## Avisos do code review (31-REVIEW.md)

0 Critical / 3 Warning / 4 Info. Nenhum warning viola truth da fase:

- **WR-01/WR-02** (edge cases de `--refresh` com cache degenerado ou
  `--cache-dir` arbitrário): fora do escopo das truths — a truth de corpus
  inválido (HEAD divergente → exit 6) está verificada e testada. Ficam como
  melhoria advisória.
- **WR-03** (título de teste de spellings promete invariante não assertado):
  qualidade de documentação de teste; a truth exigia "bats valida o schema e
  passa", o que se sustenta. Advisório.

## Verificação humana

Nenhum item pendente. Os quatro backstops foram resolvidos com evidência
explícita colhida nesta verificação (leitura dos sítios de prosa e dos
source_refs no clone da tag).

## Resumo

A fase entrega o que o goal pede, verificado contra o codebase e o corpus
real: inventário executável e 100% offline com cache validado por commit
pinado, métrica única declarada no dado, contabilidade de completude fechada
nas duas fatias (651 = 189+460+2; 227 = 65+160+2), 87 verbos contratados com
source_ref conferível na tag, os 4 órfãos extraídos do bundle do clone com
proveniência, init re-derivado (490) pelos 9 shapes e instalador com número
oficial (10.164 amplo / estreito nomeado) reproduzível por comando gravado.
48/48 testes bats verdes, incluindo os que rodam contra o clone real.

---

_Verificado: 2026-08-10_
_Verificador: Claude (gsd-verifier)_
