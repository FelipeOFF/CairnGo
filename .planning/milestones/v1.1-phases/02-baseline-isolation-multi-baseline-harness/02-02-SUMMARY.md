---
phase: 02-baseline-isolation-multi-baseline-harness
plan: "02"
subsystem: benchmarks
tags: [python, bats, provisioning, staging, fair-02]
requires:
  - "benchmarks/baselines/{gsd-only,cairn}.json (02-01: provisioning.plugin_dirs schema)"
  - "tests/helpers.bash (assert conventions, CAIRN_REPO_ROOT)"
provides:
  - "benchmarks/scripts/stage-plugins.py — materialização pinada e idempotente dos plugin_dirs (git clone --branch <ref> --depth 1 + build + node --check + .staged-ref + rename atômico)"
  - "benchmarks/plugins/gsd/v4.3.1 staged de verdade (node_modules presente, server.cjs sintaticamente válido)"
  - "benchmarks/plugins/context-mode/v1.0.169 staged de verdade (better-sqlite3 com binário prebuilt)"
  - "benchmarks/plugins/ gitignored — checkouts staged nunca commitados"
affects:
  - "02-03 (bench-matrix pode assumir staged_paths reais existentes na raiz do repo)"
tech-stack:
  added: []
  patterns:
    - "clone-to-sibling-temp-then-rename-on-success: falha nunca deixa staged_path parcial que pareça completo"
    - "url.<base>.insteadOf via GIT_CONFIG_* env como seam de rede nos testes: script byte-idêntico à produção, $0/sem rede"
key-files:
  created:
    - benchmarks/scripts/stage-plugins.py
    - tests/stage-plugins.bats
  modified:
    - .gitignore
key-decisions:
  - "load_baseline duplicado de bench-run.py SEM o check de staged_path existente (criar esses paths é o trabalho deste script; verificá-los por invocação é do runner)"
  - "temp dir de staging criado com dir=staged.parent (sibling real, mesmo filesystem) para garantir rename atômico"
  - "node --check roda em TODO entrypoint mcpServers com command=node declarado pelo plugin.json do próprio plugin staged — sintaxe apenas, servidor nunca inicia"
duration: 8min
completed: 2026-07-26
---

# Phase 2 Plan 02: Provisioning Materialization (stage-plugins.py) Summary

**stage-plugins.py materializa os plugin_dirs pinados dos manifests (clone da tag + build + verificação sintática do MCP entrypoint + .staged-ref + rename atômico), idempotente e fail-loud, provado 5/5 em bats a $0 — e o GSD v4.3.1 E o context-mode v1.0.169 reais foram staged e verificados de verdade.**

## Accomplishments

- **Task 1 RED** (`215bcff`): tests/stage-plugins.bats com 5 comportamentos contra fixtures git locais (repo bare taggeado v0.0.1 em `$BATS_TEST_TMPDIR`, reescrita `url.file://…insteadOf https://github.com/` via `GIT_CONFIG_*` env — o script sob teste continua clonando a URL de produção, nenhuma request sai da máquina). RED genuíno observado: 5/5 falhando, e os testes de exit-2 falham na mensagem de atribuição (nunca passariam espuriamente pelo exit 2 do próprio python3).
- **Task 1 GREEN** (`21ca066`): benchmarks/scripts/stage-plugins.py no house style de bench-run.py (docstring-contrato, EXIT_OK/EXIT_USAGE, die() local, argv hand-rolled `while i < len(argv)`, `--baseline` repetível / `--all`). git-type: skip idempotente se `.staged-ref == ref`; senão rmtree do stale → clone `--branch <ref> --depth 1` em temp dir sibling → build commands via `shlex.split` (lista argv, nunca shell) → `node --check` em cada entrypoint MCP `command: node` do plugin.json staged (com `${CLAUDE_PLUGIN_ROOT}` substituído) → `.staged-ref` escrito por último → `shutil.move` atômico. local_path: `is_dir()` ou die nomeando o plugin, sem fetch. Todo `subprocess.run(check=True)` embrulhado em `run_step()` que atribui plugin+step no die. `benchmarks/plugins/` no .gitignore.
- **Task 2** (sem commit — nenhum arquivo de repo mudou; as árvores staged são gitignored por design): staging REAL executado. GSD v4.3.1 staged com rede de verdade (`npm ci`, 6 pacotes pure-JS); re-invocação provou skip idempotente no checkout real; cairn.json completo passou — gsd skip, context-mode v1.0.169 staged (`npm install`, 190 pacotes, better-sqlite3 resolvido via binário prebuilt `better_sqlite3.node`), cairn local_path verificado.

## Verification Evidence (tudo executado de verdade)

- `bats tests/stage-plugins.bats` → `1..5`, `ok 1`..`ok 5` (pós-GREEN; pré-GREEN 5/5 not ok)
- Regression: `bats tests/bench-run.bats tests/stage-plugins.bats` → `1..13`, 13/13 ok — inclui o teste "unstaged staged_path" de 02-01, que segue verde mesmo com `benchmarks/plugins/gsd/v4.3.1` agora existindo na raiz (a deviation 3 de 02-01 pagou exatamente aqui)
- `git check-ignore benchmarks/plugins/gsd/v4.3.1` → exit 0; `git status --short` não lista nada sob benchmarks/plugins/
- `grep -n 'shell=True' benchmarks/scripts/stage-plugins.py` → sem matches (exit 1)
- `python3 -m py_compile benchmarks/scripts/stage-plugins.py` → exit 0
- `test -d benchmarks/plugins/gsd/v4.3.1/node_modules && node --check benchmarks/plugins/gsd/v4.3.1/mcp/server.cjs` → exit 0
- `cat benchmarks/plugins/gsd/v4.3.1/.staged-ref` → exatamente `v4.3.1`; `git log -1` no checkout: `7c3c5dd (grafted, HEAD, tag: v4.3.1)`
- `git diff --diff-filter=D` nos 2 commits: zero deleções

## Plugin staging: real materialization

**gsd-only.json** (`python3 benchmarks/scripts/stage-plugins.py --baseline benchmarks/baselines/gsd-only.json`) — sucesso, saída verbatim (trecho de advice detached-HEAD do git omitido):

```
Cloning into '~/Projects/CairnGo/benchmarks/plugins/gsd/.staging-osd5j7b7'...
Note: switching to '7c3c5dd96ed24adaaa87a4a9ae225498d2fc9c34'.
[...]
added 6 packages, and audited 7 packages in 2s

2 packages are looking for funding
  run `npm fund` for details

1 high severity vulnerability

To address all issues, run:
  npm audit fix

Run `npm audit` for details.
[stage-plugins] gsd staged at v4.3.1 -> benchmarks/plugins/gsd/v4.3.1
[stage-plugins] gsd-only: 1 plugin(s) staged/verified
```

Segunda invocação (idempotência no checkout real):

```
[stage-plugins] gsd already staged at v4.3.1, skipping
[stage-plugins] gsd-only: 1 plugin(s) staged/verified
```

**cairn.json** (`python3 benchmarks/scripts/stage-plugins.py --baseline benchmarks/baselines/cairn.json`) — **context-mode staged COM SUCESSO** (o best-effort não precisou do fallback): better-sqlite3 resolveu via binário prebuilt (`node_modules/better-sqlite3/build/Release/better_sqlite3.node` presente), nenhum compile C/C++ local foi necessário. Saída verbatim (mesmo trecho de advice omitido):

```
Cloning into '~/Projects/CairnGo/benchmarks/plugins/context-mode/.staging-55m2wtvp'...
Note: switching to '589d8214d56740a28b5f7bf63167743d586b0b40'.
[...]
npm warn deprecated prebuild-install@7.1.3: No longer maintained. Please contact the author of the relevant native addon; alternatives are available.

> context-mode@1.0.169 postinstall
> node scripts/postinstall.mjs


added 190 packages, and audited 191 packages in 15s

58 packages are looking for funding
  run `npm fund` for details

3 vulnerabilities (1 low, 2 moderate)

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
[stage-plugins] gsd already staged at v4.3.1, skipping
[stage-plugins] context-mode staged at v1.0.169 -> benchmarks/plugins/context-mode/v1.0.169
[stage-plugins] cairn is a local_path at cairn, verified
[stage-plugins] cairn: 3 plugin(s) staged/verified
```

O plugin.json do context-mode staged declara `mcpServers.context-mode = {command: "node", args: ["${CLAUDE_PLUGIN_ROOT}/start.mjs"]}` — o `node --check start.mjs` pós-build rodou e passou (staging só grava `.staged-ref` depois de todo step, e gravou `v1.0.169`). Checkout em `589d821 (tag: v1.0.169)`.

Notas de segurança observadas (não-bloqueantes, registradas): `npm ci` do GSD reporta 1 vulnerabilidade high nos devDependencies; `npm install` do context-mode reporta 3 (1 low, 2 moderate) e o deprecation de `prebuild-install`. Ambos os sources estão auditados/aprovados no threat model do plan (T-02-07) como dependências de produção já existentes deste repo; nenhuma ação tomada além do registro.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Default de parâmetro bash com `}` truncado no fixture builder**
- **Found during:** Task 1 GREEN (testes 1-2 vermelhos por motivo errado)
- **Issue:** `${1:-module.exports = {};}` — o primeiro `}` fecha a expansão, gerando `module.exports = {;}` (JS inválido) e derrubando o `node --check` legítimo do script
- **Fix:** default sem chaves (`module.exports = 0;`) + comentário explicando a armadilha
- **Files modified:** tests/stage-plugins.bats
- **Commit:** 21ca066

**2. [Minor] Fixture build usa `npm install --no-audit --no-fund`**
- O behavior dizia `build=["npm install"]`; os dois flags garantem que o install zero-dependências do fixture jamais contate o registry ($0/sem rede é requisito hard do próprio task). Mecanismo exercitado é idêntico (shlex → argv → cwd=tmp).

**3. [Minor] Docstring de `run_step` reescrita para não conter o literal `shell=True`**
- O acceptance criterion `grep -n 'shell=True'` deve retornar vazio; a primeira versão do docstring mencionava o literal ao proibi-lo. Reescrito como "argv list, never a string handed to a shell".

**4. [Minor] 5º teste bats além dos 4 behaviors**
- "syntactically broken MCP server entrypoint fails the post-build check" — prova positiva de que o branch `node --check` executa (o fixture feliz só prova que ele não falha). Cobre o lado "verification failure ⇒ fail loud" do must_have 3.

**5. [Minor] `tempfile.mkdtemp(prefix=\".staging-\", dir=staged.parent)` em vez do `tempfile.mkdtemp()` literal do action**
- O próprio plan pede "sibling temp dir" + "atomic rename-on-success"; mkdtemp default cairia em $TMPDIR (potencialmente outro filesystem), tornando `shutil.move` um copy não-atômico. `dir=staged.parent` garante o rename atômico que o plan exige. `staged.parent.mkdir(parents=True)` antes, pois `benchmarks/plugins/<name>/` não existe no primeiro staging.

## Assumption Drift (advisory)

- Assumption drift: o plan assumia que o staging do context-mode provavelmente falharia sem toolchain C/C++ (better-sqlite3 nativo) → na prática o `npm install` resolveu via binário prebuilt e passou limpo (better_sqlite3.node baixado, zero compile local). O caminho "documentar a falha" preparado pelo plan não foi necessário; o sucesso está documentado verbatim acima.

## Known Stubs

Nenhum stub em código de produto. Os fixtures bats (repo git local, tripwire de `git` no PATH, manifests sintéticos) são fixtures deliberadas da suite $0.

## Threat Flags

Nenhuma superfície nova além do threat model do plan. Mitigations implementadas: T-02-06 (clone sempre `--branch <ref>` pinado; `.staged-ref` grava o ref auditável), T-02-07 (GSD via `npm ci` com lockfile; context-mode conforme manifest; ambos pré-auditados), T-02-08 (sibling-temp + rename-on-success; `.staged-ref` escrito somente após todos os steps — tentativa falha não deixa nada em staged_path, provado no bats test 3).

## Runtime artifacts fora de escopo (não commitados)

Mesmo conjunto pré-existente registrado em 02-01 (`.beads/interactions.jsonl`, `01-BEADS-MAP.md`, `.beads/hooks/pre-push.old`, `.planning/.pending-auth-captures.jsonl`, `.pr-autopilot/`) — intocados (scope boundary).

## Next Plan Readiness

- 02-03 (bench-matrix + seed/run_order_index) roda contra staged_paths REAIS já existentes: `benchmarks/plugins/gsd/v4.3.1` e `benchmarks/plugins/context-mode/v1.0.169` prontos e verificados; `load_baseline()` do runner não vai mais morrer por staged_path ausente em gsd-only/cairn
- Branches `--seed`/`--run-order-index` continuam reservados (keys no opts dict) para o Task 1 de 02-03, conforme deviation 1 de 02-01

## Self-Check: PASSED

6/6 arquivos presentes (incl. os dois `.staged-ref` reais), 2/2 commits no log.
