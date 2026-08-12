---
phase: 20-group-model
plan: "01"
subsystem: testing
tags: [bats, bd, beads, golden-file, cairn-status, render-invariance]

requires:
  - phase: 13-phase-model
    provides: "phase_model() como leitura única das três superfícies — é o render dela que esta referência congela"
provides:
  - "make_board_fixture: fixture de board determinístico (ids de bd fixos, prefixo literal)"
  - "tests/fixtures/board-render/: sete renders de referência do código intocado + o regenerador"
  - "tests/cairn-board-invariance.bats: comparação byte a byte, com prova de que a comparação está viva"
affects: [20-02, 20-03, 21-grouped-render]

actuals:
  tokens: 4732
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Golden file capturado ANTES da mudança, do código intocado"
    - "Regenerador como único escritor, que o suite nunca invoca"
    - "Teste de vivacidade roteado pelo MESMO mecanismo de comparação que os testes de referência"

key-files:
  created:
    - tests/cairn-board-invariance.bats
    - tests/fixtures/board-render/regenerate.sh
    - tests/fixtures/board-render/w100.txt
    - tests/fixtures/board-render/w50.txt
    - tests/fixtures/board-render/w38.txt
    - tests/fixtures/board-render/ascii100.txt
    - tests/fixtures/board-render/maxrows.txt
    - tests/fixtures/board-render/plain.txt
    - tests/fixtures/board-render/brief.txt
  modified:
    - tests/helpers.bash
    - tests/README.md

key-decisions:
  - "Seis issues em vez das três mínimas do plano, para que READY, DOING, BLOCKED e a contagem de fechadas apareçam todos na referência"
  - "Assignee literal (cairn-tests), nunca $USER: a referência é lida em outra máquina"
  - "O teste de vivacidade passa pelo mesmo diff_render_against_reference() dos sete testes de referência — um diff próprio deixaria a comparação compartilhada morrer sem ninguém notar"
  - "Âncora de conteúdo, não contagem de bytes: maxrows.txt difere de w100.txt com os mesmos 1539 bytes"
  - "O regenerador também lista arquivos untracked, que git diff --stat não enxerga"

patterns-established:
  - "Prova por bytes: uma fase que promete não mover o render grava o 'antes' enquanto ele ainda é o presente"
  - "Todo guarda de comparação precisa do seu próprio teste de vivacidade, e ele tem de exercitar o mecanismo real"

requirements-completed: [BOARD-01]

coverage:
  - id: D1
    description: "make_board_fixture monta um repo cujo board rende os mesmos bytes em construções independentes"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-board-invariance.bats#the wide board renders the reference bytes"
        status: pass
      - kind: other
        ref: "5 construções independentes do fixture renderizaram w100 com 1539 bytes idênticos"
        status: pass
    human_judgment: false
  - id: D2
    description: "Os sete modos de render estão presos byte a byte contra o cairn-status.py intocado"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "bats tests/cairn-board-invariance.bats (testes 1-7)"
        status: pass
      - kind: other
        ref: "git diff --quiet HEAD -- cairn/scripts/cairn-status.py (exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A comparação é viva: perturbar o fixture a reprova, e uma referência esvaziada reprova o guarda"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-board-invariance.bats#perturbing the fixture makes the comparison fail"
        status: pass
      - kind: other
        ref: "quebra medida: comparação sempre-concorda deixa 1-7 verdes e reprova só o teste 8; maxrows.txt esvaziado reprova 5 e 9"
        status: pass
    human_judgment: false
  - id: D4
    description: "Regenerar a referência é ato deliberado: script separado que o suite nunca invoca, documentado no tests/README.md"
    verification:
      - kind: other
        ref: "grep -v '^[[:space:]]*#' tests/cairn-board-invariance.bats | grep -c 'regenerate' == 0"
        status: pass
    human_judgment: false

duration: 75min
completed: 2026-08-03
status: complete
---

# Phase 20 Plano 01: Referência de render do board Summary

**Sete renders de referência do `cairn-status.py` intocado, capturados de um fixture com ids de bd fixos, com um teste de vivacidade que mata qualquer comparação que sempre concorde.**

## Performance

- **Duration:** ~75 min (dos quais ~16 min de espera pelo baseline dos suites existentes)
- **Tasks:** 3
- **Files modified:** 11 (9 criados, 2 modificados)

## Accomplishments

- `make_board_fixture` em `tests/helpers.bash`: `.planning/` com as três formas de roadmap que o parser desta fase lê (lista `## Milestones`, checkboxes `## Phases`, tabela `## Progress`) e um banco bd de seis issues espalhadas por READY/DOING/BLOCKED/fechadas. Determinismo garantido por `bd init --prefix brd` **literal** mais `bd create --id` em toda issue, e prioridade distinta por issue porque `fetch_lanes` ordena por `(priority, id)`.
- A discordância deliberada entre `STATE.md` (`milestone: v1.0`, o ciclo arquivado) e `ROADMAP.md` (`🚧 v1.1` aberto) está armada e **visível na referência**: o rodapé de `w100.txt` imprime `· v1.0 ·`. É a armadilha que o plano 20-02 precisa encontrar.
- Sete referências commitadas em `tests/fixtures/board-render/`, uma por modo, capturadas do script intocado.
- `regenerate.sh`: único escritor desses arquivos, nunca chamado por teste, termina imprimindo o diff que produziu.
- `tests/cairn-board-invariance.bats`: 9 testes — sete comparações byte a byte, um teste de vivacidade, um teste de referência não-degenerada.

## Task Commits

1. **Task 1: o caminho fim a fim** — `79a41cc` (test)
2. **Task 2: a matriz de modos e o regenerador** — `784483e` (test)
3. **Task 3: provar que a comparação está viva** — `fff5809` (test)

## Files Created/Modified

- `tests/helpers.bash` — `make_board_fixture`, com o comentário que explica por que o prefixo é literal e por que a discordância STATE/ROADMAP não deve ser "consertada"
- `tests/cairn-board-invariance.bats` — 9 testes
- `tests/fixtures/board-render/regenerate.sh` — o regenerador
- `tests/fixtures/board-render/{w100,w50,w38,ascii100,maxrows,plain,brief}.txt` — as sete referências
- `tests/README.md` — `make_board_fixture` na lista de helpers e uma seção sobre quando (e como) regenerar

## Decisions Made

- **Seis issues, não três.** O plano pedia "ao menos" três (fase pendente 1, fase pendente 2, sem fase). Com só essas três, DOING e BLOCKED sairiam vazios e nem o sufixo de assignee, nem o de dependência, nem a contagem `done:` entrariam na referência — três caminhos de render ficariam de fora da prova. As seis mantêm as três exigidas e acrescentam uma em `in_progress`, uma bloqueada e uma fechada.
- **Assignee literal `cairn-tests`.** `bd update --claim` usaria `$USER`, e a referência é commitada e lida em outra máquina.
- **`maxrows` guarda de verdade.** `--max-rows 2` sobre uma raia READY de três issues troca a última linha por `+1 more` — confirmado por `diff`, não assumido. Detalhe medido: o arquivo difere de `w100.txt` **com a mesma contagem de bytes** (1539), porque as células da raia são preenchidas até largura fixa.
- **Um teste por modo, um teste só para as sete âncoras.** Cada teste reconstrói o fixture (~12 s cada, o custo de `bd init` + seis `bd create`); as verificações de âncora leem só bytes commitados, então agrupá-las num teste economiza ~85 s sem perder informação de falha — a mensagem nomeia o arquivo e a âncora perdida.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] O teste de vivacidade não protegia o mecanismo que os outros sete usam**

- **Found during:** Task 3
- **Issue:** Escrito como o plano descreve, o teste de vivacidade tinha um `run diff` próprio, separado do helper `assert_render_matches`. Isso deixa aberto exatamente o buraco que ele existe para fechar: quem trocasse a comparação **compartilhada** por uma que sempre concorda (um `|| true`, um diff do arquivo consigo mesmo) passaria pelos sete testes de referência **e** o teste de vivacidade continuaria verde na cópia privada e ainda honesta dele. Ninguém pegaria.
- **Fix:** Extraí `diff_render_against_reference()`; os sete testes afirmam `status -eq 0` sobre ele e o teste de vivacidade afirma `status -ne 0` sobre o mesmo. Uma comparação morta agora reprova o teste 8.
- **Verification:** Quebra aplicada (`run diff -u ref ref`): testes 1-7 verdes, **teste 8 vermelho**, sozinho. Restaurado de backup `cp`, byte a byte, e 9/9 verde.
- **Committed in:** `fff5809`

**2. [Rule 2 - Missing Critical] `git diff --stat` é cego para uma referência nova**

- **Found during:** Task 2
- **Issue:** O plano manda o regenerador terminar em `git diff --stat -- tests/fixtures/board-render/`, e a intenção é "regenerar sempre deixa um diff visível para revisar". Só que `diff --stat` não diz nada sobre arquivo que o git nunca viu: rodando o regenerador com seis dos sete arquivos ainda untracked, a saída foi **vazia** — silêncio total, exatamente o "passou silencioso" que o plano quer evitar.
- **Fix:** Depois do `diff --stat`, o script lista `git ls-files --others --exclude-standard` da mesma pasta, prefixado com `untracked`.
- **Verification:** Rodado com os seis untracked — os seis apareceram nomeados.
- **Committed in:** `784483e`

**3. [Rule 2 - Missing Critical] Uma perturbação que parasse de casar viraria um teste verde e mudo**

- **Found during:** Task 3
- **Issue:** O teste de vivacidade afirma que o `diff` falha depois de um `sed` no `ROADMAP.md` do fixture. Se um dia esse `sed` deixar de casar (título renomeado no helper, por exemplo), ele vira no-op — e aí o `diff` também deixaria de falhar, então o teste ficaria vermelho, não verde. O risco real é o inverso: o `diff` falhar por **outro** motivo qualquer e o teste declarar vivacidade que não mediu.
- **Fix:** Além de `[ "$status" -ne 0 ]`, o teste exige que o diff **mencione o texto perturbado**.
- **Verification:** Verde com a perturbação real; a quebra do item 1 (comparação morta) o reprova pela mensagem de âncora ausente.
- **Committed in:** `fff5809`

---

**Total deviations:** 3 auto-fixed (3 × Rule 2 — funcionalidade crítica ausente, todas no próprio mecanismo de prova)
**Impact on plan:** Nenhuma expansão de escopo. As três endurecem guardas que o plano já queria; a primeira é a que importa — sem ela o plano entregaria uma prova que não provava o que dizia.

## Issues Encountered

- **`git diff --stat` sem `HEAD` compara worktree contra o índice.** Já avisado no briefing; a verify da Task 1 usa `HEAD` e foi confirmada em exit 0 depois de cada commit.
- **Custo de tempo dos suites existentes.** `bats tests/cairn-status.bats tests/cairn-phase-model.bats` leva ~15-16 min nesta máquina. Não é regressão desta fase — o baseline fechou 83/83 sem uma linha editada neles — mas explica por que os 9 testes novos levam ~1 min 50 s: cada teste reconstrói o fixture bd.

## User Setup Required

None.

## Next Phase Readiness

- O "antes" está gravado e commitado do código intocado. O plano 20-02 pode mudar o modelo e provar a invariância rodando `bats tests/cairn-board-invariance.bats`.
- A armadilha STATE/ROADMAP está armada: se o modelo de grupo tirar o rótulo do milestone do `STATE.md`, o render vai anunciar o ciclo arquivado `v1.0` e os sete testes ficam vermelhos.
- `--json` ficou de fora da matriz de propósito — a chave nova do 20-02 não colide com nada aqui.

---
*Phase: 20-group-model*
*Completed: 2026-08-03*

## Self-Check: PASSED

- 11 arquivos declarados existem em disco; 3 commits de task existem em `git log`.
- `bats tests/cairn-board-invariance.bats` → **9/9 ok**.
- `bats tests/cairn-status.bats tests/cairn-phase-model.bats` → **83/83 ok, 0 falhas** (55 + 28).
- `git diff --quiet HEAD -- cairn/scripts/cairn-status.py` → exit 0.

