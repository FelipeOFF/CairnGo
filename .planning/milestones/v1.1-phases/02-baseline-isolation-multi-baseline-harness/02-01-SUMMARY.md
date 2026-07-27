---
phase: 02-baseline-isolation-multi-baseline-harness
plan: "01"
subsystem: benchmarks
tags: [python, bats, isolation, baselines, fair-01, fair-02]
requires:
  - "benchmarks/scripts/bench-run.py (Phase 1 runner: task.json, stub seam, JSONL row)"
  - "tests/bench-run.bats + tests/helpers.bash (stub factory, assert_json_eq)"
provides:
  - "benchmarks/baselines/{vanilla,gsd-only,cairn}.json — manifests pinados, claude_flags byte-idêntico, só provisioning difere (FAIR-02)"
  - "isolated_claude_env(fresh_home) — env explícito {HOME, PATH, ANTHROPIC_API_KEY-se-presente} SÓ no subprocess claude (FAIR-01)"
  - "load_baseline(path) — validação parse→keys→staged_path com die(EXIT_USAGE) antes de qualquer spend"
  - "--baseline obrigatório em bench-run.py; row ganha baseline_id"
  - "make_env_asserting_claude_stub — stub que ecoa HOME/env/argv observados no payload (prova a $0)"
affects:
  - "02-02 (staging/build dos plugins nos staged_path que os manifests apontam)"
  - "02-03 (seed/run_order_index: keys já reservadas no opts dict)"
tech-stack:
  added: []
  patterns:
    - "env= explícito substitui (nunca merge) o ambiente no arm medido; oracle (verify.sh) segue com env herdado completo"
    - "stub-asserts-its-environment: isolamento vira contrato black-box testável via jq"
key-files:
  created:
    - benchmarks/baselines/vanilla.json
    - benchmarks/baselines/gsd-only.json
    - benchmarks/baselines/cairn.json
  modified:
    - benchmarks/scripts/bench-run.py
    - benchmarks/scripts/bench-run.sh
    - tests/bench-run.bats
    - tests/helpers.bash
key-decisions:
  - "seed/run_order_index reservados no opts dict (None) SEM branches de argv — plan 02-03 Task 1 adiciona e testa os branches (instrução do plan-checker)"
  - "Teste de staged_path ausente roda com cwd=BATS_TEST_TMPDIR: determinístico mesmo depois que 02-02 stagear plugins reais na raiz do repo"
  - "task.json não exige mais 'model': manifest é a única fonte de verdade dos claude flags (timeout_s/id/prompt_file seguem no task.json)"
duration: 16min
completed: 2026-07-26
---

# Phase 2 Plan 01: Baseline Isolation + Manifests Summary

**Env do subprocess claude agora é um dict explícito {HOME, PATH, ANTHROPIC_API_KEY-se-presente} (substitui, nunca faz merge), com vanilla/gsd-only/cairn como manifests JSON pinados e tudo provado 8/8 em bats a custo $0.**

## Accomplishments

- **Task 1** (`fb150d7`): 3 manifests em `benchmarks/baselines/`. `claude_flags` byte-idêntico nos três (verificado com `diff <(jq -Sc ...)`); model pinado `claude-haiku-4-5-20251001`; `plugin_dirs` = 0/1/3 entradas; ordem no cairn: gsd → context-mode → cairn. cairn.json documenta no próprio `description` por que context-mode entra (dependência hard do plugin.json; excluir seria arm "rigged"). gsd-only.json registra o rename do source (buildomator/buildomator@v4.3.1, ex-jnuyens/gsd-plugin).
- **Task 2 RED** (`dc06309`): `make_env_asserting_claude_stub` em helpers.bash (ecoa `stub_observed_home`/`leak_marker`/`api_key_present` booleano/`argv`); 3 testes existentes atualizados com `--baseline`; 5 testes novos. Suite rodada: 8/8 falhando (bench-run.py ainda rejeitava `--baseline` — RED genuíno observado).
- **Task 2 GREEN** (`c6a8ca9`): `isolated_claude_env()`, `load_baseline()`, `--baseline` obrigatório, cmd 100% manifest-driven (`--bare` retorna via manifest, um par `--plugin-dir <staged_path>` por entrada, lista argv, nunca shell=True), `env=` SÓ na chamada do claude, `baseline_id` na row, fresh HOME descartável com rmtree no finally, docstring reescrita como contrato novo.

## Verification Evidence (tudo executado de verdade)

- `bats tests/bench-run.bats` → `1..8`, `ok 1`..`ok 8` (observado pós-GREEN; pré-GREEN as 8 falhavam)
- `python3 -m py_compile benchmarks/scripts/bench-run.py` → exit 0
- `grep -c 'env=isolated_claude_env'` → 1, na chamada `subprocess.run` do claude (linhas 194-196); a chamada do verify.sh (214-215) segue sem nenhum kwarg `env=`
- `--plugin-dir` aparece só dentro do loop `for entry in manifest["provisioning"]["plugin_dirs"]` (linha 190-191), nunca hardcoded
- Task 1 verify: JSON válido x3 + `jq -Sc '.claude_flags'` idêntico nos 3 arquivos
- Scan de literal de API key em benchmarks/ e tests/: limpo; o stub afirma apenas PRESENÇA booleana (T-02-02)
- `git diff --diff-filter=D` nos 3 commits: zero deleções

## Deviations from Plan

### Auto-fixed / directed adjustments

**1. [Checker directive] `--seed`/`--run-order-index` sem branches de argv**
- **Found during:** Task 2
- **Issue:** O action do plan mandava "parse all three flags", ambíguo vs. plan 02-03
- **Fix:** Keys `seed`/`run_order_index` reservadas no opts dict (default `None`), NENHUM branch de argv adicionado — conforme instrução explícita do plan-checker
- **⚠️ Para o executor do 02-03:** o Task 1 de 02-03 deve ADICIONAR e testar os branches `--seed`/`--run-order-index` em `parse_args`; as keys já existem no dict
- **Commit:** c6a8ca9

**2. [Rule 2 - Docs] bench-run.sh usage comment atualizado**
- **Found during:** Task 2
- **Issue:** `bench-run.sh` (fora da lista de files do plan) anunciava `--task <dir> --out <path>`, contrato agora stale
- **Fix:** Uma linha: usage passa a incluir `--baseline <manifest.json>` (a convenção da casa é docstring/usage = contrato)
- **Commit:** c6a8ca9

**3. [Rule 2 - Test robustness] Teste de staged_path ausente roda com `cd "$BATS_TEST_TMPDIR"`**
- **Found during:** Task 2
- **Issue:** O teste dependia de `benchmarks/plugins/gsd/v4.3.1` não existir relativo ao cwd do bats (raiz do repo) — o plan 02-02 vai criar exatamente esse diretório, o que quebraria o teste depois
- **Fix:** O teste muda o cwd para `BATS_TEST_TMPDIR`, onde o path relativo nunca resolve; comportamento testado é o mesmo do plan (staged_path inexistente → exit 2 antes de row/stub)
- **Commit:** dc06309

**4. [Minor] Asserção extra de `--bare` no teste de argv**
- O teste de construção de `--plugin-dir` também afirma `--bare` presente no argv do stub, provando a construção manifest-driven do flag que retorna neste plan. Além do mínimo do plan, sem alterar comportamento.

## Assumption Drift (advisory)

- **Planned:** o teste negativo de staged_path assumia que `benchmarks/plugins/gsd/v4.3.1` "does not yet exist on disk" na raiz do repo. **Actual:** isso deixa de ser verdade assim que 02-02 stagear os plugins. **Why it matters:** o teste ficaria vermelho por razão errada; resolvido via cwd isolado (deviation 3). Nenhum outro drift material.

## Pending (não é gap de mecanismo)

- **Validação live do auth isolado** (CONTEXT.md a sanciona como opcional, 1 run barato): NÃO executada — constraint do orchestrator para este plan é zero live API calls. O caminho de auth (`--bare` + ANTHROPIC_API_KEY no env escopado) está provado a $0 via stub; a prova live fica para quando um plan/operador autorizar spend.

## Known Stubs

Nenhum stub em código de produto. Os stubs de teste (`make_claude_stub`, `make_env_asserting_claude_stub`, tripwire) são fixtures deliberadas da suite $0, não placeholders.

## Threat Flags

Nenhuma superfície nova além do threat model do plan. Mitigations implementadas: T-02-01 (argv como lista, nunca shell=True/interpolação), T-02-02 (key só em env dict runtime; bats afirma presença booleana), T-02-03 (staged_path validado antes de qualquer subprocess).

## Runtime artifacts fora de escopo (não commitados)

`.beads/interactions.jsonl`, `.planning/phases/01-.../01-BEADS-MAP.md`, `.beads/hooks/pre-push.old`, `.planning/.pending-auth-captures.jsonl`, `.pr-autopilot/` — modificados/criados por hooks/ambiente durante a sessão, não por este plan. Deixados intocados (scope boundary).

## Next Plan Readiness

- 02-02 pode stagear/buildar os plugins exatamente nos `staged_path` que os manifests declaram; `load_baseline()` já falha loud se faltar
- 02-03 herda `--baseline`, `baseline_id` e as keys reservadas `seed`/`run_order_index`

## Self-Check: PASSED

7/7 arquivos presentes, 3/3 commits no log, `make_env_asserting_claude_stub` presente em helpers.bash.
