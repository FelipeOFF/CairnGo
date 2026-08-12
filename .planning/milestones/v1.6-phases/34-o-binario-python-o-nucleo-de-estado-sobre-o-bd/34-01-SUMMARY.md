---
phase: 34-o-binario-python-o-nucleo-de-estado-sobre-o-bd
plan: 01
subsystem: gsd-dispatcher
tags: [bd, set-state, labels, dispatcher, execv, tracer]
requires: []
provides:
  - cairn-gsd-state.py (skeleton + state.begin-phase + state.load)
  - roteamento por exec (FAMILY_SCRIPT + MISC_STATE_VERBS)
  - fixture.bd no harness de goldens
affects: [34-02, 34-03, 34-04, 34-05, fase-35]
tech-stack:
  added: []
  patterns: [bd set-state com ator/motivo, consulta por label projetado, falha nomeada para fato ausente]
key-files:
  created:
    - cairn/scripts/cairn-gsd-state.py
    - tests/fixtures/gsd-goldens/state-*.golden.json (5)
  modified:
    - cairn/scripts/cairn-gsd.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "D-02 materializado verbatim em VERB_DIMENSIONS (ver seção abaixo)"
  - "partição misc 7/17 registrada em MISC_STATE_VERBS do dispatcher"
  - "irmãos sem wrapper .sh próprio — toda entrada passa por cairn-gsd.sh"
metrics:
  duration: ~35min
  completed: 2026-08-10
status: complete
---

# Phase 34 Plan 01: Tracer estado sobre o bd Summary

**One-liner:** dispatcher roteia as 5 famílias pesadas por os.execv pros irmãos; cairn-gsd-state.py nasce com o par begin-phase/load provando as três regras do bd (label projetado como chave, set-state com ator/motivo, falha nomeada) num repo real.

## O que foi construído

- **Dispatcher (cairn-gsd.py):** `FAMILY_SCRIPT` (estado/roadmap-phase → cairn-gsd-state.py; worktree/init → cairn-gsd-init.py) + `MISC_STATE_VERBS` (roteamento por verbo); exec no ponto de inserção entre `HANDLERS.get` e o die exit 4, passando o VERBO canônico (nunca o spelling); irmão ausente do disco cai no die atual nomeando a fase (estado transitório entre ondas); `--list-implemented` agregado rodando cada irmão existente.
- **cairn-gsd-state.py:** forma da casa (docstring-contrato, exits 0/1/2/4, die com `[cairn-gsd-state]`, HANDLERS, envelope copiado do dispatcher); `run_bd`/`bd_json` (molde cairn-lease), `resolve_actor` (BEADS_ACTOR > git user.name > USER, irresolvível é die — nunca transição anônima), portador único por label âncora.
- **Harness:** `fixture.bd` no builder local (init via cd + seeds declarativos com token `@id`); 5 cenários derived-from-contract; 4 testes bats diretos (ambiguidade, ordering, fonte única, auditoria).

## Registro D-02 (decisão one-way, LOCKED — vocabulário verbatim)

Fonte única: constante `VERB_DIMENSIONS` de `cairn/scripts/cairn-gsd-state.py`.

| Dimensão | Valores permitidos | Label projetado |
|---|---|---|
| `phase` | número inteiro corrente (valor livre) | `phase:<N>` |
| `phase_status` | `planned` \| `executing` \| `verified` \| `complete` | `phase_status:<valor>` |
| `plan` | `NN-MM` corrente (valor livre com forma) | `plan:<NN-MM>` |
| `verification` | `passed` \| `failed` \| `pending` | `verification:<valor>` |
| `session` | `YYYY-MM-DD` da última atividade | `session:<data>` |

- Labels ASCII, sem espaços; consulta SEMPRE `bd list -l dim:valor` (nunca metadata aninhado — rc 0 silencioso, medido).
- `progress` NÃO é dimensão: é derivado (fatos do portador + contagem de artefatos). Nenhuma sexta dimensão, nunca.
- Os verbos gsd MAPEIAM para essas dimensões; o vocabulário do upstream (campos de STATE.md) não vira schema.
- Portador: bead único por repo com label âncora `gsd-state`; 0 → falha nomeada prescrevendo `state.begin-phase <N>`; >1 → falha nomeada de ambiguidade com os ids.

## Partição misc (discrição do CONTEXT, registrada)

- **7 verbos de planning-docs → cairn-gsd-state.py:** summary-extract, todo.match-phase, requirements.mark-complete, quick-tasks-append, history-digest, research-plan, research-store.
- **17 verbos genéricos → cairn-gsd-init.py:** classify-confidence, estimate-check, frontmatter.get/set/validate, git.base-branch, graphify, intel, is, learnings.copy/query, normalize-test-command, package-legitimacy, plan.task-structure, research… (os demais de misc.json), teams-status, websearch, windows.
- **5 órfãos (fase 35):** audit-open, review-lane, agent.classify-failure, task.is-behavior-adding, run-with-timeout — seguem exit 4 nomeando a fase 35 (checados antes do roteamento por verbo).

## Decisão .sh

Nenhum wrapper .sh próprio para os irmãos: toda entrada passa por `cairn-gsd.sh` e os irmãos são detalhe de implementação do dispatcher (PATTERNS, nota .sh). Reavaliável na fase 36 se os preâmbulos shim precisarem.

## Divergências declaradas (novas, family estado)

1. `source-of-truth-state-load` — upstream nunca falha (state_exists:false); cairn: portador ausente é falha nomeada com comando prescrito (CORE-04).
2. `source-of-truth-state-raw` — upstream: markdown cru; cairn: rendering determinístico das dimensões do portador.
3. `raw-form-state-load` — rawValue indefinido: JSON nos dois modos (o formato condensado key=value não tem consumidor no cairn).
4. `carrier-dwim-created-key` — envelope de begin-phase carrega `created: true` quando o portador nasce (DWIM registrada, nunca silenciosa).
5. `recorder-inapplicable-bd-verbs` — goldens de estado são derived-from-contract; o recorder grava do binário que lê markdown.

## Desvios do plano

1. **[Rule 3 - Bloqueio] `bd -C <dir> init` não existe** — bd exige projeto beads para aceitar `-C`; o init do builder roda com `cd` em subshell (molde helpers.bash L353). Commit a6a15fd.
2. **[Rule 1 - Bug] `@tsv` do apply_mask_file escapa backslash** — regex de mask reescrito sem backslash (`[.]planning/debug$`). Commit a6a15fd.
3. **[Rule 3 - Bloqueio] token `@id` sobrescrito por saída de set-state** — só um seed `create` alimenta o token. Commit a6a15fd.
4. **Testes da era 33 atualizados:** os bats que assertavam exit 4 para `state.load` (realidade pré-34) migraram para representantes válidos (`verify.plan-structure` para família não servida; `state.update` para verbo sem handler no irmão); o guard de cobertura compara extras contra o universo COMPLETO do contrato durante a entrega incremental da fase (o filtro por família volta a fechar bidirecional no plano 05).

## Nota sobre requisitos

REQUIREMENTS.md/STATE.md/ROADMAP.md não foram tocados (regra da execução desta fase — escrituração é do bookkeep pós-merge). Requisitos exercitados: CORE-01 (shape de estado.json em state.load), CORE-02 (labels projetados como única chave), CORE-03 (set-state com ator/motivo; reentrada idempotente), CORE-04 (falha nomeada com STATE.md presente no fixture adversarial).

## Verificação

- `bats tests/cairn-gsd.bats` — 62/62 verde offline.
- Sequência E2E manual (verify da Task 1) limpa: exit 1 nomeado → begin-phase → 1 label `phase_status:executing` → load com as 6 chaves.
- `git status --porcelain cairn/gsd/` vazio.
- Trilha de auditoria provada: event bead `<id>.1` com `created_by` = ator e description contendo o verbo.

## Commits

- c2a32fe feat(34-01): tracer estado sobre o bd — exec pros irmãos + begin-phase/load
- 37646f9 test(34-01): cenários bd do tracer + divergências declaradas (RED)
- a6a15fd feat(34-01): fixture.bd no builder do harness (GREEN)

## Self-Check: PASSED

- cairn/scripts/cairn-gsd-state.py existe (461 linhas ≤ 1500, D-01) ✓
- 5 goldens state-*.golden.json existem e passam serialização da casa ✓
- commits c2a32fe/37646f9/a6a15fd existem na branch ✓
