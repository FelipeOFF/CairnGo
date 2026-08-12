---
phase: 35-o-binario-python-checagem-e-verbos-orfaos
plan: 03
subsystem: gsd-dispatcher
tags: [checagem, check, predicate, adr-2008, recorded, tdd]
requires:
  - família verify no irmão check (35-02)
  - cache do clone da tag + node (gravação do diferencial)
provides:
  - check (hub de gates, 12 subcommands) + check.decision-coverage-plan
  - avaliador de predicado ADR-2008 com goldens RECORDED (CHECK-02)
  - teste de reprodução do recorder DESTRAVADO (rodando verde)
affects: [35-04, 35-05, fase-36]
tech-stack:
  added: []
  patterns:
    [
      normalização pontos→hifens provada por par de goldens,
      diferencial recorded contra o binário real,
      divergência declarada por cenário (divergent_from_real),
    ]
key-files:
  created:
    - tests/fixtures/gsd-goldens/check-*.golden.json (10)
  modified:
    - cairn/scripts/cairn-gsd-check.py
    - cairn/scripts/cairn_gsd_render.py
    - cairn/scripts/cairn-gsd-record.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/scenarios.json
    - tests/fixtures/gsd-goldens/divergences.json
decisions:
  - "teto D-01 exercido pela discrição do CONTEXT: substrato de parsing de documento (frontmatter subset, must_haves, tasks, decisões, UI-presence, conflito #968) movido para cairn_gsd_render.py — precedente 34-05 desvio 2; check em 1271/1500"
  - "cenário 'composto' do predicado = artifact-frontmatter-equals (multi-condição) — a gramática da tag NÃO tem composição booleana de predicados; a forma saiu do fonte, não da imaginação"
  - "irreprodutibilidade declarada por cenário: divergent_from_real no manifesto é o dono; o recorder pula com mensagem e o teste de reprodução exige a declaração para toda ausência"
metrics:
  duration: ~80min
  completed: 2026-08-11
status: complete
---

# Phase 35 Plan 03: O hub check e o predicado ADR-2008 Summary

**One-liner:** check roteia os 12 subcommands com pontos→hifens (par auto-mode/auto.mode byte-igual por golden), decision-coverage-plan cobre fail-closed #2770 / skip verde / cobertura real com a extração de decisões portada de decisions.cts, e o predicado ADR-2008 responde na semântica integral da tag com diferencial RECORDED do binário real — de quebra, o teste de reprodução da 34 (latente, nunca rodado) foi destravado e roda verde.

## Semântica transcrita do predicado (registro pedido pelo plano)

Fonte: `src/gate-predicate-evaluator.cts` (267 linhas, port integral) + `parsePredicateFlags`/`buildPredicateDeps` de `src/check-command-router.cts` L956-L1029. Dois kinds (a gramática NÃO tem composição booleana):

- **command-exit-zero:** `sh -c` em subprocess limitado (timeout default 30s, flag `timeout` em segundos positivos finitos), interpolação `${PHASE_NUMBER|PHASE_DIR|PHASE_REQ_IDS}`, caps de 4096 chars no comando e 2000 no tail da mensagem; exit 0 → block false "command exited 0"; não-zero → block true com código + tail de stderr/stdout; estouro → block true "command timed out after Ns".
- **artifact-frontmatter-equals:** artifact resolvido por basename-only sem traversal (findPhaseArtifact: direto, .planning/, sufixo `-<artifact>`), campo comparado por igualdade estrita OU igualdade das projeções string; ausência do artefato → block true.
- Malformado (JSON inválido, kind desconhecido, campos ausentes) → exit 1 via die — o `throw` do avaliador que o wrapper da tag converte em `error()`.

## Resultado do diferencial (CHECK-02)

Fechou limpo: 4 goldens `recorded` gravados do gsd-tools real (`check-predicate-passa`, `-reprova`, `-malformado` exit 1, `-composto` = artifact-frontmatter-equals) e reproduzidos byte a byte pelo runner offline E pelo `--record` skip-gated. Nenhuma divergência do avaliador python contra o real — nenhuma entrada nova de divergences.json para o predicado.

## Subcommands declarados indisponíveis (check)

api-coverage-verify-pre, decision-coverage-verify, gap-analysis-plan-post, prohibition-enforcement, tdd-review-checkpoint, ui-safety-gate — sem sítio no universo da 31; respondem `{available: false, reason}` exit 0 (molde 34-05). verify-schema-drift honra `GSD_SKIP_SCHEMA_CHECK=true` e senão declara indisponibilidade; verify-codebase-drift delega à função do 35-02. Implementados da semântica da tag: auto-mode, decision-coverage-plan (mesma função do verbo dedicado), ui-plan-gate (computeUiPlanGate + checkUiPresence #2150), predicate.

## Desvios do plano

1. **[Rule 3 - teto D-01] Substrato de parsing movido para cairn_gsd_render.py** — com o hub check o irmão bateu 1654 linhas; a discrição do CONTEXT ("uso de cairn_gsd_render.py se o teto apertar") foi exercida no precedente 34-05 (desvio 2): frontmatter subset, must_haves, task-infos, fences, decisões, seções designadas (#2372), UI-presence e o conflito #968 agora vivem no módulo compartilhado (670 linhas), com proveniência por função; o check fechou em 1271. Semântica de veredito (exits, shapes, rotas) continua no irmão.
2. **[Rule 1 - Bug latente da 34] Recorder sem fixture.git_commit** — o builder do bats cria o commit base; o recorder não criava. Exposto quando a gravação do predicado buildou o runtime do clone e o skip-gate do teste de reprodução abriu pela primeira vez. Corrigido no espelho do builder.
3. **[Rule 1/2 - Teste latente da 34] Reprodução nunca-rodada nasceu insatisfazível** — 21 cenários da 33/34 materializam divergências CONSCIENTES da casa (fato no bd → die exit 1 contratado; shapes próprios de worktree/init/windows/quick-tasks) e jamais reproduzem do binário real. Correção declarada, nunca silenciada: `divergent_from_real: true` no manifesto (o dono da declaração), recorder pula com mensagem nomeada, e o teste de reprodução REPROVA ausência sem declaração. A divergência de shape até então não-declarada (entry interno do worktree.create: casa `path/base` vs real `worktree_path/expected_base`) entrou em divergences.json.
4. **Cenário check-decision-coverage-plan-fail-closed usa argv com token vazio** (`""`) — o builder do bats propaga o vazio como posicional; nenhum ajuste de runner foi necessário.

## Verificação

- `bats tests/cairn-gsd.bats` — **79/79 ok, 0 skip** (o teste de reprodução roda verde pela primeira vez).
- E2E: par auto-mode/auto.mode byte-igual; check nao-existe exit 1.
- `--list-implemented` agregado: 79 (8/11 da checagem: +check, +check.decision-coverage-plan).
- `git status --porcelain cairn/gsd/` vazio; teto: check 1271 ≤ 1500; pin CHECK-04 verde.

## Commits

- eff77b8 test(35-03): cenarios RED do check — auto-mode, normalizacao, decision-coverage
- ce2d664 feat(35-03): check — dispatcher de gates com normalizacao e coverage (GREEN)
- 74abfb0 test(35-03): diferencial RED do predicado ADR-2008 — goldens RECORDED
- 194833a feat(35-03): avaliador de predicado ADR-2008 + reproducao destravada (GREEN)

## Self-Check: PASSED

- 8 verbos no --list-implemented do irmão check; 4 commits no branch; suíte 79/79 sem skip.
