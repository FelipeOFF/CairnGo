---
phase: 35-o-binario-python-checagem-e-verbos-orfaos
plan: 02
subsystem: gsd-dispatcher
tags: [checagem, verify, plan-structure, must-haves, tdd]
requires:
  - cairn-gsd-check.py com verification.status (35-01)
provides:
  - família verify inteira no irmão check (5 verbos)
  - parser de frontmatter + extrator de must_haves compartilhados
  - port do codebase-drift (detectDrift com dados verbatim)
affects: [35-03, 35-04, 35-05, fase-36]
tech-stack:
  added: []
  patterns:
    [
      um dono por semântica (subcommand delega à função do verbo dedicado),
      indisponibilidade declarada nunca inventada,
      gate reprovado ≠ gate não avaliado,
    ]
key-files:
  created:
    - tests/fixtures/gsd-goldens/verify-*.golden.json (12)
  modified:
    - cairn/scripts/cairn-gsd-check.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "caso NUL de plan-structure conciliado pela letra dos DOIS campos do contrato: NUL no ARGUMENTO path → exit 1; NUL no CONTEÚDO do arquivo → exit 0 com {valid: false, errors} (#2701) — nenhuma escolha extra, os dois campos convivem"
  - "echo-scan #429 omitido do plan-structure (fora da letra do contrato e do plano) — divergência declarada, nunca silenciada"
  - "cenário verify-commits-particiona usa o token HEAD (resolvível e determinístico) em vez de hash vivo com mask — payload ecoa o argv, nenhum valor variável"
metrics:
  duration: ~45min
  completed: 2026-08-11
status: complete
---

# Phase 35 Plan 02: A família verify inteira Summary

**One-liner:** os 5 verbos da família verify respondem no irmão check com UM parser de frontmatter e UM extrator de must_haves (port de parseMustHavesBlock com proveniência); a doutrina exit-code provada por cenário — gate reprovado sai 0 com valid/all_passed/all_verified false, exit 1 só para erro de uso.

## O que foi construído

- **verify.plan-structure:** campos obrigatórios do frontmatter (8), estrutura das tasks por tipo canônico (checkpoints.md — port de validatePlanTaskStructure), checkpoint vs autonomous, warning #1951 (one-way sem checkpoint:decision anterior), conflito de gate negativo file-wide (#968, port de scanFileWideNegativeGateConflict com patternRequiredIn linear), fail-loud NUL/binário ANTES das checagens (#2701). Arquivo inexistente → {error} exit 0; path ausente ou com NUL no argv → exit 1.
- **verify.artifacts:** must_haves.artifacts contra o disco — existência + contains/min_lines/exports; sem bloco ou arquivo → {error} exit 0.
- **verify.key-links:** aresta from→to por pattern no conteúdo real (fallback: to referenciado no from); from prometido por plano de wave igual/posterior entra em pending sem derrubar all_verified (#1202, port de collectPromisedFilesAtOrAfterWave sobre PLAN_FILE + files_modified do molde do doctor).
- **verify.commits:** git cat-file -t == "commit" pelo molde subprocess defensivo; partição valid/invalid; --raw emite valid/invalid; nenhum hash → exit 1.
- **verify (família):** dict interno com os 8 de VERIFY_SUBCOMMANDS; plan-structure/commits/artifacts/key-links delegam à MESMA função dos verbos dedicados; codebase-drift port completo (readMappedCommit via frontmatter, diff name-status contra base ou empty-tree, classificação migration/route/barrel/new_dir com os regexes verbatim da tag, threshold/action do workflow config, mensagem de buildMessage); schema-drift respeita --skip; subcommand desconhecido → exit 1 "Unknown verify subcommand. Available: ...".

## Conciliação payload×exit do caso NUL (registro pedido pelo plano)

Nenhuma escolha foi necessária: o contrato dá exit 1 para "path ausente ou com null bytes" (o ARGUMENTO) e {valid: false, errors} exit 0 para corrupção NUL no CONTEÚDO — são dois campos distintos e a implementação segue os dois. O cenário verify-plan-structure-nul cobre o caminho de conteúdo (offset no texto da mensagem, verbatim de textEncodingError).

## Divergências declaradas (novas — 2)

1. `verify` / `subcommand-nao-observado`: phase-completeness, references e o caminho não-skip de schema-drift respondem {available: false, reason} exit 0 (molde 34-05) — o universo da 31 só exercita codebase-drift.
2. `verify.plan-structure` / `echo-scan-429-omitido`: o scanner de comment-echo (#429) não roda — fora da letra do contrato e do plano.

## Desvios do plano

1. **Cenário verify-commits-particiona sem mask:** o plano previa hash real mascarado por valor; o token `HEAD` (aceito por cat-file, ecoado no payload) elimina o valor variável — determinismo sem mask. Registrado na decisão.

## Verificação

- `bats tests/cairn-gsd.bats` — 79 ok, 1 skip, zero falhas (RED→GREEN nas duas tasks).
- E2E: verify.commits com hash real all_valid true; verify nao-existe exit 1; codebase-drift skip verde.
- `--list-implemented` agregado: 77 (71 da 34 + 6 de checagem).
- `git status --porcelain cairn/gsd/` vazio; teto: 1147 ≤ 1500; pin CHECK-04 verde.

## Commits

- 30618af test(35-02): cenarios RED dos leitores de PLAN.md (8 cenarios)
- 1d85dc9 feat(35-02): os 3 leitores de PLAN.md no irmao check (GREEN)
- b36e5cc test(35-02): cenarios RED de verify.commits e da familia verify
- 26a3c89 feat(35-02): verify.commits e o comando de familia verify (GREEN)

## Self-Check: PASSED

- 6 verbos em --list-implemented do irmão check; 4 commits no branch; suíte verde offline.
