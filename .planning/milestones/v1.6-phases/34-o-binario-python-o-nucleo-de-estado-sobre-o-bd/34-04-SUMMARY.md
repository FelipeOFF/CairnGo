---
phase: 34-o-binario-python-o-nucleo-de-estado-sobre-o-bd
plan: 04
subsystem: gsd-dispatcher
tags: [worktree, init, bundles, composição, rollback]
requires: [34-01, 34-03]
provides:
  - cairn-gsd-init.py (6 worktree + 9 init)
  - fato de estado por composição (run_sibling → cairn-gsd-state.py)
affects: [34-05, fase-36]
tech-stack:
  added: []
  patterns: [manifest de wave por temp+rename, rollback de criação parcial (árvore E branch), bundle = config + filesystem + fato propagado]
key-files:
  created:
    - cairn/scripts/cairn-gsd-init.py
    - tests/fixtures/gsd-goldens/worktree-*.golden.json (6)
    - tests/fixtures/gsd-goldens/init-*.golden.json (11)
  modified:
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "worktree segue a letra do CONTRATO (manifest-based), não a convenção phase_layout do PATTERNS — ver desvio 1"
  - "fato dentro de bundle: propagado (execute-phase/plan-phase) ou reportado como ausência (manager/milestone-op) — divergência declarada"
  - "modelos resolvidos pelo dispatcher (resolve-model via subprocess) — o catálogo tem um dono só"
metrics:
  duration: ~45min
  completed: 2026-08-10
status: complete
---

# Phase 34 Plan 04: worktree + init no segundo irmão Summary

**One-liner:** cairn-gsd-init.py nasce com a família worktree na letra manifest-based de worktree.json (rollback de árvore E branch provado por resíduo) e os 9 bundles init compostos de config + filesystem + fato do irmão de estado — uma implementação de consulta na casa, falha nomeada propagada.

## Delta vs orçamento (o registro pedido pelo plano)

| Seção | Orçamento (research/31) | Real | Delta |
|---|---|---|---|
| worktree | ~250 | 293 | +43 |
| init (9 bundles, per_shape 490) | 490 | 520 | +30 |
| skeleton/forma da casa | — | 203 | — |
| **total cairn-gsd-init.py** | ~740 + skeleton | **1016** | dentro do teto 1500 (D-01) |

Por shape, os desvios relevantes: execute-phase real ≈ 90 (orçado 140 — o índice de planos veio pronto do irmão via phase-plan-index, não recontado); plan-phase real ≈ 75 (orçado 105 — idem, mvp-mode do irmão); os bundles pequenos ficaram no orçado ±5. O ganho vem da composição por subprocess: nenhum parser de índice/status reimplementado.

## Desvios do plano

1. **[Contrato vence o plano] worktree pela letra de worktree.json, não pela convenção phase_layout.** O plano (e o PATTERNS) descrevia `worktree.create <fase>` com phase_slug/phase_layout de cairn-parallel; o CONTRATO da fase 31 define create/record-agent/cleanup-wave *manifest-based* (`--manifest --agent-id --path --branch --base --root`), set-baseref no-clobber e base-check com curto-circuito. CORE-05 manda responder "na forma de worktree.json, verbo a verbo" e a árvore de contratos é somente-leitura — o contrato venceu. O critério de aceitação foi adaptado: create feliz + duas falhas forçadas (branch pré-existente → nada criado; escrita de manifest bloqueada → rollback de árvore E branch, provado por `git worktree list` + `show-ref`).
2. **Builder ganhou `fixture.git_commit`** — `git worktree add` exige commit base; extensão local do builder (mesmo precedente do fixture.bd).
3. **`has_verification` removido do envelope de plan-phase** — o shape carrega `verification_path` mas não a flag (conferido contra bundle_shapes).

## Divergências declaradas novas

- family worktree: `base-check-default-head`, `reap-orphans-heuristic-reduced` (órfão = diretório sumido; heurísticas de lock não portadas), `cleanup-wave-keeps-branches`.
- family init: `section-manifest-empty` (fase 36 decide preencher), `agents-from-vendored-tree` (determinístico por construção), `state-fields-from-carrier` (propagação vs relatório de ausência), `manager-render-reduced`.

## Verificação

- `bats tests/cairn-gsd.bats` — 75/75 verde offline; guard de cobertura exige config/commit/skills/loop-hooks/dispatch-model/estado/roadmap-phase/worktree/init, comm fechado.
- Rollback provado por resíduo, não por leitura de código (dois testes de falha forçada).
- Falha nomeada propagada provada em init.execute-phase (cenário + bats: stderr carrega o prefixo do irmão de estado e prescreve state.begin-phase).
- `--pick planner_model` → "opus"; `--pick chave-inexistente` → "undefined".
- `wc -l cairn-gsd-init.py` = 1016 ≤ 1500 (D-01).
- `git status --porcelain cairn/gsd/` vazio.

## Commits

- 2a16f0a test(34-04): cenários da família worktree e rollback por resíduo (RED)
- c2e130e feat(34-04): o segundo irmão nasce com a família worktree (GREEN)
- 6be0947 test(34-04): cenários dos 9 bundles init + propagação de fato (RED)
- 41c465b feat(34-04): os 9 bundles init no orçamento re-derivado (GREEN)

## Self-Check: PASSED

- cairn/scripts/cairn-gsd-init.py existe (1016 ≤ 1500) ✓
- 17 goldens novos (worktree-* + init-*) ✓
- commits 2a16f0a/c2e130e/6be0947/41c465b na branch ✓
