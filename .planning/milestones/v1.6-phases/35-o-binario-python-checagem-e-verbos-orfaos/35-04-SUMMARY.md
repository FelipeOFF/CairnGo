---
phase: 35-o-binario-python-checagem-e-verbos-orfaos
plan: 04
subsystem: gsd-dispatcher
tags: [checagem, user-story, uat, coverage, tdd]
requires:
  - hub check no irmão (35-03)
provides:
  - user-story.validate (string pura, guards por cláusula)
  - uat.render-checkpoint (bloco do teste corrente, response_language)
  - uat.classify-coverage (classificador fail-safe do bloco coverage)
  - 11/11 da família checagem — --list-implemented agregado 82
affects: [35-05, fase-36]
tech-stack:
  added: []
  patterns:
    [
      guards por cláusula antes da regex cheia,
      auto-pass estreito totalmente provado,
      fail-safe — na dúvida vai a humano,
    ]
key-files:
  created:
    - tests/fixtures/gsd-goldens/user-story-*.golden.json (4)
    - tests/fixtures/gsd-goldens/uat-*.golden.json (6)
  modified:
    - cairn/scripts/cairn-gsd-check.py
    - cairn/scripts/cairn_gsd_render.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "caminho exit-1 de subcommand ≠ validate é INALCANÇÁVEL pela rota por spelling da casa — query user-story.<outro> morre exit 2 do dispatcher; cenário grava a letra da casa, divergência declarada (o split-no-primeiro-ponto #3243 é mecanismo da tag)"
  - "frames do checkpoint reduzidos a english + portuguese (as línguas da casa); demais caem em english — redução declarada"
  - "mini-YAML do coverage e validação de shape movidos pro render (teto D-01); veredito auto_passed/present/reasons fica no irmão"
metrics:
  duration: ~45min
  completed: 2026-08-11
status: complete
---

# Phase 35 Plan 04: Os três verbos de conteúdo — 11/11 da checagem Summary

**One-liner:** user-story.validate valida a string canônica com guards por cláusula (erros um a um, acionáveis — inválido nunca é erro de processo), uat.render-checkpoint renderiza o bloco do teste corrente na forma de buildCheckpoint no response_language do config, e uat.classify-coverage classifica o bloco coverage com auto-pass estreito e fail-safe pro humano — a família checagem fecha 11/11, agregado 82.

## Forma do bloco renderizado (proveniência parseCurrentTest/buildCheckpoint)

Fonte: `src/uat.cts` L235-L324 (cmdRenderCheckpoint + parseCurrentTest) e L577-L594 (buildCheckpoint). Seção `## Current Test` coletada level-bounded na forma leniente da casa (molde verification_status: regex + strip); comentário HTML de abertura removido; `[testing complete]` → exit 1 nomeado; `number:`/`name:`/`expected:` (inline ou bloco `|` com de-indent de 2 espaços). O bloco: caixa de 64 colunas com o banner do frame, `**Test N: nome**`, o expected, régua de 62 e a instrução do frame. `--raw` emite só o texto do checkpoint (raw_value da tag).

## Tratamento do mode legacy (classify-coverage)

`parseCoverage` port fiel (mini-YAML de 3 níveis com guarda de prototype-pollution): sem chave `coverage:` no frontmatter → `mode: legacy` com errors vazios; bloco presente mas imparsável → legacy + erro `malformed_block` (fail-safe: nunca all_auto_covered com bloco quebrado); `coverage: []` ou corpo vazio → coverage com zero entradas. auto_passed exige: zero erros de validação + `human_judgment: false` estrito + verification NÃO-vazia + todo status `pass` — o guard não-vazio derrota o every vácuo, o boolean estrito derrota flag de string.

## Contagem --list-implemented

Agregado **82** = 71 (fase 34) + 11 (checagem completa: check, check.decision-coverage-plan, uat.classify-coverage, uat.render-checkpoint, user-story.validate, verification.status, verify, verify.artifacts, verify.commits, verify.key-links, verify.plan-structure). Só os 5 órfãos separam de 87.

## Manutenção do bats (registro)

Os testes de representante-de-família da era 33/34 saíram (o representante único e a tabela exit-4) — com 11/11 implementados não sobra verbo pra repontar; a mecânica cumpriu o papel. Guardas remanescentes: o controle negativo do verbo forjado e o representante de órfão (até o 35-05).

## Divergências declaradas (novas — 2)

1. `user-story.validate` / `subcommand-path-unreachable`: a rota por spelling não tem caminho pra subcommand desconhecido — `query user-story.<outro>` sai exit 2 do dispatcher (a tag splitaria e sairia exit 1); cenário marcado divergent_from_real.
2. `uat.render-checkpoint` / `render-checkpoint-reducoes`: frames en/pt (demais → english), sem parseFirstPendingTest, sem sanitizeForDisplay, largura por len() — reduções declaradas.

## Desvios do plano

1. **[teto D-01] parseCoverage + validação de shape movidos pro render** — mesma discrição já exercida no 35-03; check em 1463/1500, render 954.

## Verificação

- `bats tests/cairn-gsd.bats` — verde, zero falhas (diferencial + reprodução).
- E2E: uat.render-checkpoint e uat.classify-coverage sem flag → exit 1; agregado 82 confirmado por gate.
- `git status --porcelain cairn/gsd/` vazio; pin CHECK-04 verde.

## Commits

- e9f23e7 test(35-04): cenarios RED de user-story.validate
- ff86bda feat(35-04): user-story.validate — guards por clausula, string pura (GREEN)
- bc4ecc6 test(35-04): cenarios RED dos leitores de UAT/SUMMARY
- 6969d44 feat(35-04): uat.render-checkpoint e uat.classify-coverage (GREEN)

## Self-Check: PASSED

- 11 verbos de checagem no irmão; agregado 82; 4 commits no branch; suíte verde.
