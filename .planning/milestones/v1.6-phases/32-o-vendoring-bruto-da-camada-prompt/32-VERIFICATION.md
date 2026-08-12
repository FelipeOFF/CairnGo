---
phase: 32-o-vendoring-bruto-da-camada-prompt
verified: 2026-08-10T18:45:00Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: false
requirements_satisfied: [VEND-01, VEND-02, VEND-03, VEND-04]
test_results:
  suites: [tests/cairn-vendoring.bats, tests/cairn-inventory.bats, tests/gsd-contracts.bats]
  passed: 96
  failed: 0
  skipped: 0
  note: "cache quente — os testes skip-gated contra o corpus real rodaram todos (zero skips); sem cache a suíte nova skipa só a faixa de fidelidade, com mensagem de reprodução (provado movendo o cache)"
---

# Fase 32: O vendoring bruto da camada prompt — Relatório de Verificação

**Goal da fase:** copiar o fecho transitivo dos 8 workflows do clone da tag
v1.10.0 para `cairn/gsd/`, byte a byte, com lista de inclusão DERIVADA do
inventário (manifest versionado), LICENSE MIT intacto, crédito no README, e o
corte provado por teste (gsd-write-guard.js e blocos excluídos ausentes).

**Verificado em:** 2026-08-10, no worktree `phase/32-o-vendoring-bruto-da-camada-prompt`.
**Método:** goal-backward — cada truth dos 2 PLANs conferida rodando o comando
real, nunca confiando nos SUMMARYs. Cache do clone quente
(`.cairn/cache/gsd-core-v1.10.0`, HEAD `68a04ccf8ef74803bdb651e12c3b85b218bbccdf`).

## Veredito por truth

### Plano 01 — closure, manifest, vendor (VEND-01, VEND-02)

| # | Truth | Status | Evidência |
|---|-------|--------|-----------|
| 1 | `closure --json` emite o fecho dos 8 workflows sobre o corpus pinado (HEAD == 68a04cc), determinístico (D-02, VEND-01) | ✓ VERIFIED | `diff <(closure --json) <(closure --json)` vazio; `.source.commit == 68a04cc...`; 171 arquivos/29.957 linhas medidos (`jq .totals`) |
| 2 | MANIFEST.json gravado byte-idêntico à saída viva de `closure --json` (D-02, VEND-01) | ✓ VERIFIED | `diff <(closure --json) cairn/gsd/MANIFEST.json` vazio, re-rodado na verificação; newline final por `tail -c1 \| od` |
| 3 | Cada caminho de files[] existe sob cairn/gsd/ byte-idêntico ao clone (D-01, VEND-01) | ✓ VERIFIED | Sweep python3 (filecmp shallow=False sobre 171 entradas + comm dos dois sentidos, exclusões MANIFEST.json e contracts/**) exit 0; bats 20 ok |
| 4 | cairn/gsd/LICENSE byte-idêntico ao LICENSE do clone, sem empilhar copyright (VEND-02) | ✓ VERIFIED | `cmp` exit 0 (re-rodado); bats 22 "never stacked" ok |
| 5 | README §License & credits credita open-gsd/gsd-core com v1.10.0 e 68a04cc (VEND-02) | ✓ VERIFIED | `awk '/## License & credits/,0'` contém open-gsd/gsd-core, v1.10.0, 68a04cc e cairn/gsd/LICENSE; crédito ao fork original intacto; diff tocou só a seção |
| 6 | Invocação flat intacta — suítes existentes passam sem edição | ✓ VERIFIED | `bats tests/cairn-inventory.bats tests/gsd-contracts.bats` 48/48 ok (duas execuções); dispatch por argv[1] preserva o contrato |

### Plano 02 — a prova executável (VEND-01, VEND-03, VEND-04)

| # | Truth | Status | Evidência |
|---|-------|--------|-----------|
| 7 | Fixture prova convergência até ponto fixo e --write == --json (D-02, VEND-01) | ✓ VERIFIED | bats 1 (2 saltos fast→r1→t1, órfão fora), 2 (determinismo), 3 (bytes idênticos + newline) ok — expectativas do próprio fixture |
| 8 | Manifest == saída viva por comm nos DOIS sentidos, nenhum resíduo (VEND-01) | ✓ VERIFIED | bats 4 (fixture) e 21 (cache real) ok |
| 9 | Todo files[] byte-idêntico ao clone; nada sob cairn/gsd/ além de files[] + MANIFEST.json + contracts/**, skip-gated pelo cache (D-01, VEND-03) | ✓ VERIFIED | bats 14, 15, 20 ok com cache quente (zero skips); sem cache, só a faixa de fidelidade skipa com a mensagem de reprodução (provado movendo o cache) |
| 10 | Ausência de gsd-write-guard.js assertada por teste NOMEADO que explica a colisão com o bd (VEND-04) | ✓ VERIFIED | bats 16 "the cut holds: gsd-write-guard.js is NOT vendored (collides with bd as state owner)" ok; find por gsd-write-guard* vazio |
| 11 | Blocos do corte provados ausentes por teste tabular (VEND-04) | ✓ VERIFIED | bats 17 sobre CUT_BLOCKS (tests docs src scripts bin gsd-core/bin eslint-rules capabilities .github examples .changeset hooks) + multi-host restrito a .cts ok |
| 12 | Todo guard novo com controle negativo pareado que MORDE | ✓ VERIFIED | bats 6 (byte corrompido pego e nomeado), 7 (intruso pego), 8 (SKILL.md forjado com requires: mata o closure, exit 6), 18 (write-guard forjado pego), 24 (contagem forjada pega) ok |

## Artefatos prometidos

| Artefato | Status | Prova |
|---|---|---|
| cairn/gsd/MANIFEST.json | ✓ | contém 68a04ccf8ef74803bdb651e12c3b85b218bbccdf; files[] ordenado, 171 entradas |
| cairn/gsd/LICENSE | ✓ | "MIT License", byte-idêntico ao clone |
| cairn/gsd/gsd-core/workflows/fast.md | ✓ | diff vazio contra o cache (prova do espelhamento D-01) |
| cairn/scripts/cairn-inventory.py | ✓ | subcomandos closure e vendor sobre o mesmo ensure_corpus |
| README.md | ✓ | crédito com tag e commit na seção existente |
| tests/cairn-vendoring.bats | ✓ | 24 testes, prova executável de VEND-01/03/04 |

## Proibições do plano

- Nenhuma transformação de conteúdo na cópia: fidelidade byte a byte provada nos dois sentidos (a proibição é consequência mecânica do diff vazio).
- LICENSE nunca alterado nem empilhado: cmp exit 0.
- gsd-write-guard.js nunca em cairn/gsd/: cópia é POR LISTA (nunca copytree), e a ausência é assertada por teste nomeado + tabular + controle negativo.

## Divergências registradas (medido vence)

- Fecho medido 171/29.957 contra 160/28.071 do research §2.1 — explicado no bloco datado do cairn-inventory.py (16 agents vs 13; 16 shims 1:1 vs 8 SKILL.md; LICENSE na lista; contexts/ fora porque nenhum arquivo do corpus referencia contexts/*.md).
- `requires:` no clone real vive no frontmatter dos commands; a guarda do plano (escopo SKILL.md) passa no corpus real e sua vivacidade é provada em fixture.

## Gate de regressão

505 testes verdes com ambiente limpo, zero falhas: todas as suítes que leem
qualquer arquivo alterado pela fase rodaram COMPLETAS (inventory 24+, contracts
24, vendoring 24, command-surfaces, stage-plugins, smoke, hooks, capability,
wrap, gbsync), mais bench* (176), board-invariance + corroboration (36) e
parciais de config/corroboration/doctor (119). A suíte serial completa excede o
orçamento da sessão (doctor sozinho ≈ 40min); nenhuma suíte restante lê
arquivos tocados pela fase. Um run inicial com `CLAUDE_PROJECT_DIR` exportado
produziu 13 falsos vermelhos em board/corroboration (cairn-status.py:4309
resolve a raiz pela env e renderizou o repo vivo em vez do fixture) — re-run
limpo 36/36; nenhum defeito de código.
