---
phase: 35-o-binario-python-checagem-e-verbos-orfaos
plan: 05
subsystem: gsd-dispatcher
tags: [orfaos, check-03, run-with-timeout, review-lane, audit-open, guard-87]
requires:
  - 11/11 da checagem no irmão check (35-04)
provides:
  - os 5 ex-órfãos de CHECK-03 respondendo no irmão check
  - rota três-destinos no misc (MISC_STATE_VERBS/MISC_CHECK_VERBS/init)
  - guard de cobertura bidirecional fechado em 87/87
affects: [fase-36, fase-37]
tech-stack:
  added: []
  patterns:
    [
      exclusão→rota (a constante mudou de papel no MESMO commit do bats),
      subprocess passthrough com tabela GNU-timeout,
      kind text fora do envelope JSON,
    ]
key-files:
  created:
    - tests/fixtures/gsd-goldens/agent-classify-*.golden.json (2)
    - tests/fixtures/gsd-goldens/audit-open-*.golden.json (2)
    - tests/fixtures/gsd-goldens/task-is-behavior-adding-*.golden.json (3)
    - tests/fixtures/gsd-goldens/review-lane-*.golden.json (3)
  modified:
    - cairn/scripts/cairn-gsd.py
    - cairn/scripts/cairn-gsd-check.py
    - cairn/scripts/cairn_gsd_render.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "as duas armadilhas do PATTERNS desarmadas como escrito: rota explícita MISC_CHECK_VERBS (nunca o ramo misc default rumo ao irmão errado) e dispatcher_orphans apagada no MESMO commit da renomeação"
  - "guard fecha 87/87 com contagem pinada: universo coberto (11 famílias) == inventário inteiro; assert wc -l == 87 prende o número"
  - "masks de golden sem backslash (desvio 2 do 34-01) e argv de cenário em UMA linha (o builder do bats quebra em newline) — duas regras do harness reconfirmadas"
metrics:
  duration: ~75min
  completed: 2026-08-11
status: complete
---

# Phase 35 Plan 05: O fecho — 87/87 com os ex-órfãos Summary

**One-liner:** os 5 ex-órfãos de CHECK-03 respondem no irmão check com a semântica REM-04 (audit-open varre o .planning/ inteiro; run-with-timeout embrulha subprocess com a tabela GNU-timeout e stdio atravessando; review-lane fala texto), a exclusão do dispatcher virou rota explícita no MESMO commit em que o bats parou de derivá-la, e o guard fecha o universo 87/87 nos dois sentidos.

## Partição misc final (registro pedido pelo plano)

- **7 → cairn-gsd-state.py** (MISC_STATE_VERBS: planning-docs).
- **5 → cairn-gsd-check.py** (MISC_CHECK_VERBS: audit-open, review-lane, agent.classify-failure, task.is-behavior-adding, run-with-timeout — os ex-órfãos).
- **17 → cairn-gsd-init.py** (resto, incluindo os fantasmas com caminho de erro do contrato).

## Contagem 87/87 (comm dos dois sentidos)

`--list-implemented` agregado = **87** = universo de contracts.json. O guard de cobertura derivou o universo das 11 famílias (a exclusão por `comm -23` foi extinta junto com `dispatcher_orphans`), comparou nos DOIS sentidos (missing e extras contra o MESMO conjunto) e pinou a contagem em 87. O controle negativo do verbo forjado segue detectando (o fecho não cegou o guard). E2E da rota: audit-open (JSON com scanned_at), run-with-timeout exit 7 com argv opaco pelo exec, review-lane --selected — os três atravessando `$GSD`.

## Divergências novas da fase consolidadas

1. `review-lane` / lanes reduzidas: REVIEWER_LANES transcrito aos campos que o universo consome (12 lanes / 13 flags); sem merge de capabilities; plan/invoke declaram {available: false} — invocar CLIs headless não tem sítio na 31.
2. `run-with-timeout` / Win32 não se aplica (bash/bats, macOS/Linux); execução POSIX direta com process group.
3. (Herdadas dos planos anteriores desta fase: stale-check-indeterminate-key, subcommand-nao-observado, echo-scan-429, subcommand-path-unreachable, render-checkpoint-reducoes, worktree-entry-inner-shape.) Total do arquivo: **55 entradas**.

## Contagem final de linhas vs teto

- `cairn-gsd-check.py`: **1492 ≤ 1500** (teto D-01 respeitado até o fim).
- `cairn_gsd_render.py`: 1556 (sem teto próprio — o substrato compartilhado da discrição do CONTEXT; envelope + parsing de documento + resolução de fato defensiva + dados com proveniência).
- state 1499 e init 1325: byte-iguais ao início da fase (só o dispatcher mudou).

## Desvios do plano

1. **TDD das Tasks 1-2 sem RED de golden próprio** — o próprio plano moveu cenários/goldens para a Task 3 (runner invoca via $GSD; a rota nasce lá); o RED da Task 2 foi feito por bats direto (13 @test do irmão), e a Task 1 verificou pelo gate direto do plano.
2. **[teto D-01] mais substrato movido ao render** — scanners do audit, REVIEWER_LANES, VERIFICATION_ROUTING_TABLE, resolução de fato git/subprocess — mesma discrição dos planos 03/04.
3. **Regras do harness reconfirmadas na prática:** mask sem backslash (o `@tsv` escapa) e argv de cenário de uma linha (o builder quebra em newline) — nenhuma mudança de runner.

## Verificação

- `bats tests/cairn-gsd.bats` verde (diferencial 153 cenários + reprodução recorded); `bats tests/cairn-command-surfaces.bats` verde.
- `--list-implemented` = 87; `git status --porcelain cairn/gsd/` vazio; pin CHECK-04 verde (doctor byte-igual e2040aea).
- Suíte da casa completa re-executada ao fim da fase (registro na entrega final da fase; zero falha nos lotes).

## Commits

- 4bc8766 feat(35-05): tres orfaos de classificacao e varredura no irmao check
- e157d11 test(35-05): RED — run-with-timeout e review-lane pelo irmao direto
- af3d373 feat(35-05): run-with-timeout e review-lane no irmao check (GREEN)
- 35ec76d feat(35-05): exclusao vira rota + guard 87/87 — dispatcher e bats juntos

## O que a fase 36 recebe

- Superfície completa 87/87 pelo dispatcher único (`cairn-gsd.sh <spelling>`); os preâmbulos dos workflows podem apontar `gsd_run` para ele.
- `check` é o hub de gates (${hook.check.query} roteável, pontos→hifens); predicado ADR-2008 avaliado com diferencial recorded.
- Doutrina exit-code viva por golden: veredito no payload, exit 1 só para erro de uso.

## Self-Check: PASSED

- 16 verbos da fase no irmão check; agregado 87; 4 commits no branch; suítes gsd + command-surfaces verdes.
