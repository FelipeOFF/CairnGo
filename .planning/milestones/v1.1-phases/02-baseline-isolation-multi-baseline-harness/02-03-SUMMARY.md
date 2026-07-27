---
phase: 02-baseline-isolation-multi-baseline-harness
plan: "03"
subsystem: benchmarks
tags: [python, bats, interleaving, seed, fair-03]
requires:
  - "benchmarks/scripts/bench-run.py (02-01: --baseline, baseline_id, keys seed/run_order_index reservadas no opts dict)"
  - "benchmarks/plugins/{gsd/v4.3.1,context-mode/v1.0.169} staged (02-02)"
  - "tests/helpers.bash (make_env_asserting_claude_stub, assert_json_eq)"
provides:
  - "bench-run.py: --seed/--run-order-index opcionais (int-cast, die EXIT_USAGE em não-inteiro), stamped na row como JSON integers só quando presentes"
  - "benchmarks/scripts/bench-matrix.py — build_execution_order (random.Random(seed).shuffle) + orquestração 1×bench-run.py por baseline na ordem embaralhada"
  - "tests/bench-matrix.bats — 5 testes: stamps int, guard de regressão, ordem contígua 0..N-1, determinismo do seed, isolamento preservado sob orquestração"
  - "benchmarks/README.md — Baselines/staging/ordering documentados + live smoke check PENDING"
affects:
  - "Phase 3 (repetição/agregação consome seed/run_order_index já presentes nas rows)"
tech-stack:
  added: []
  patterns:
    - "shuffle com RNG instance-scoped (random.Random(seed)), nunca o módulo random compartilhado"
    - "orquestrador sem check=True: exit code de cada run é dado, nunca aborta o batch"
key-files:
  created:
    - benchmarks/scripts/bench-matrix.py
    - tests/bench-matrix.bats
  modified:
    - benchmarks/scripts/bench-run.py
    - benchmarks/scripts/bench-run.sh
    - benchmarks/README.md
key-decisions:
  - "--seed REQUIRED no bench-matrix.py (sem default aleatório silencioso) — T-02-11/FAIR-03"
  - "Live smoke check: branch PENDING tomado (ANTHROPIC_API_KEY re-checado ausente em 2026-07-26); zero chamadas live, comando exato documentado no README"
  - "README sem o literal do prefixo de API key (precedente: deviation 3 do 02-02 com shell=True) — grep de key material fica limpo nos dois branches"
duration: 15min
completed: 2026-07-26
---

# Phase 2 Plan 03: Seeded Interleaving + Live-Check Documentation Summary

**bench-matrix.py embaralha os baselines declarados com random.Random(seed) e invoca bench-run.py uma vez por arm na ordem embaralhada, com seed/run_order_index stamped como JSON integers em toda row (contíguos 0..N-1, mesma ordem para o mesmo seed), provado 5/5 em bats a $0 — e o smoke check live de auth isolado documentado honestamente como PENDING (key ausente, re-checada na execução).**

## Accomplishments

- **Task 1 RED** (`24d7d8a`): tests/bench-matrix.bats com os 5 comportamentos do plan; fixtures alpha/beta/gamma.json escritos em `$BATS_TEST_TMPDIR` (claude_flags espelhando vanilla.json, provisioning vazio — nada commitado em benchmarks/baselines/). RED genuíno observado: 4/5 falhando (`--seed` era unknown option; bench-matrix.py inexistente). Teste 2 passou no RED **por design**: é o guard de regressão que trava o comportamento JÁ correto (flags ausentes ⇒ row sem as keys) — não é um feature test passando inesperadamente.
- **Task 1 GREEN** (`a120c7b`): bench-run.py ganhou os branches `--seed`/`--run-order-index` no shape idêntico aos demais flags (`int(argv[i+1])` em try/except ValueError → `die("--seed must be an integer, got '...'", EXIT_USAGE)`), ambos opcionais; row assembly adiciona as keys só quando não-None, antes do `json.dumps(sort_keys=True)`. bench-matrix.py criado com argparse (idioma do cairn-relabel.py): `--baselines` (nomes, não paths), `--baselines-dir` (default benchmarks/baselines), `--task`/`--out` passthrough, `--seed` required int; `build_execution_order` verbatim do Interfaces block (sem dimensão de N-runs — escopo Phase 3 honrado); validação da lista resolvida COMPLETA antes de qualquer invocação; loop `subprocess.run(cmd)` sem check=True; uma linha por run + summary final; exit EXIT_OK após lançar todas as invocações.
- **Task 2** (`91885df`): ANTHROPIC_API_KEY re-checada na execução → AUSENTE → branch PENDING: zero chamadas live. README ganhou "Live isolation smoke check: PENDING" (por quê, comando exato para quando houver key, e que o mecanismo já está provado a $0), seção "Baselines" (tabela dos 3 manifests, contrato de isolamento, modelo de staging do stage-plugins.py), seção "Randomized execution order" (contrato do --seed, campos seed/run_order_index), e o parágrafo-resumo do topo atualizado (isolation/baselines/staging/ordering construídos; repetição/agregação seguem Phase 3).

## Verification Evidence (tudo executado de verdade)

- `bats tests/bench-matrix.bats` → `1..5`, ok 1..ok 5 (pós-GREEN; pré-GREEN 4/5 not ok). Teste 5 rodou DE VERDADE contra os manifests reais vanilla/gsd-only (staged trees do 02-02 presentes — skip não acionado): ambas as rows com `stub_observed_home != $HOME` e contendo `cairn-bench-home-`.
- `bats tests/bench-run.bats` → `1..8`, 8/8 ok — zero regressão nos testes do 02-01.
- Suite completa `bench-verify + bench-run + stage-plugins + bench-matrix` → 21 ok / 0 not ok.
- `python3 -m py_compile benchmarks/scripts/bench-run.py benchmarks/scripts/bench-matrix.py` → exit 0.
- `grep -n 'reps\|repetition' benchmarks/scripts/bench-matrix.py` → sem matches (exit 1) — fronteira de escopo Phase 3 confirmada.
- `grep -c 'shell=True' benchmarks/scripts/bench-matrix.py` → 0.
- Sanity extra observado: `--seed abc` → `[bench-run] error: --seed must be an integer, got 'abc'`, exit 2; manifest inexistente no bench-matrix → die nomeando o path, exit 2 antes de qualquer invocação.
- Determinismo (must_have): teste 4 roda o MESMO seed duas vezes em outs separados e faz `diff` da sequência de `baseline_id` — vazio, byte-idêntico.
- Task 2 verify: `grep -qF "PENDING" benchmarks/README.md` → ok (branch key-ausente); `grep -c 'sk-ant-'` no README → 0; doc-coverage (vanilla/gsd-only/cairn.json + stage-plugins.py + bench-matrix.py) → ok.
- `git diff --diff-filter=D` nos 3 commits: zero deleções.

## TDD Gate Compliance

RED (`24d7d8a`, test) → GREEN (`a120c7b`, feat) na ordem exigida; refactor não foi necessário. O único teste verde durante o RED é o guard de regressão do comportamento pré-existente (documentado acima), não um feature test.

## Deviations from Plan

### Auto-fixed / minor

**1. [Rule 2 - Docs] bench-run.sh usage comment atualizado com os flags opcionais**
- **Found during:** Task 1 GREEN
- **Issue:** wrapper (fora da lista de files do plan) anunciava contrato sem os novos flags; convenção da casa é usage = contrato (mesmo precedente da deviation 2 do 02-01)
- **Fix:** linha de usage ganha `[--seed <int> --run-order-index <int>]`
- **Commit:** a120c7b

**2. [Rule 2 - Docs] Dois bullets stale do README corrigidos**
- **Found during:** Task 2
- **Issue:** "**--bare** ... bench-run.py therefore omits it" e "task.json now requires a full id" descreviam o comportamento pré-02-01 (hoje --bare e o model vêm do manifest)
- **Fix:** bullets reescritos para o contrato manifest-driven atual; comando histórico dos live runs anotado como pré-`--baseline`
- **Commit:** 91885df

**3. [Minor] Instrução do check de key material sem o literal do prefixo**
- A primeira redação do PENDING continha o prefixo `sk-ant-` literal, o que deixava `grep -c` do acceptance criterion em 1 no próprio README. Reescrito como "keys share a fixed, greppable prefix" (precedente: deviation 3 do 02-02 com o literal `shell=True`). Grep final: 0.
- **Commit:** 91885df

## Assumption Drift (advisory)

Nenhum drift material. O plan previa skip gracioso do teste 5 caso os staged trees não existissem; existiam (02-02), então o teste rodou no caminho real — cenário já previsto pelo próprio plan, não drift.

## Live smoke check: PENDING (não é gap de mecanismo)

`[ -n "${ANTHROPIC_API_KEY:-}" ]` re-checado no momento da execução do Task 2 (2026-07-26): ausente. Zero chamadas live nesta execução (custo $0). O README registra o comando exato do run único barato (vanilla) para quando um operador disponibilizar a key. Critério "exits 0 regardless of branch" cumprido.

## Known Stubs

Nenhum stub em código de produto. Fixtures de teste (alpha/beta/gamma.json em tmpdir, `make_env_asserting_claude_stub`) são fixtures deliberadas da suite $0.

## Threat Flags

Nenhuma superfície nova além do threat model do plan. T-02-09 (accept): nomes → paths via lista Python, nunca shell=True. T-02-10 (mitigate): branch PENDING não tocou key nenhuma; grep de key material limpo em README e diffs. T-02-11 (mitigate): `--seed` required, `seed`+`run_order_index` em toda row orquestrada.

## Runtime artifacts fora de escopo (não commitados)

Mesmo conjunto pré-existente registrado em 02-01/02-02 (`.beads/hooks/pre-push.old`, `.planning/.pending-auth-captures.jsonl`, `.pr-autopilot/`) — intocados (scope boundary).

## Next Phase Readiness

- Phase 3 (repetição/agregação) consome rows que já carregam `baseline_id`, `seed` e `run_order_index`; a dimensão de N repetições entra em `build_execution_order` sem quebrar o contrato atual (flags do bench-run.py já aceitos e opcionais).
- O smoke check live fica a um comando de distância quando houver ANTHROPIC_API_KEY (documentado no README).

## Self-Check: PASSED

6/6 arquivos presentes, 3/3 commits no log.
