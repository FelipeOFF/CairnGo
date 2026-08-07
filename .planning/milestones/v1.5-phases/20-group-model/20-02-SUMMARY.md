---
phase: 20-group-model
plan: "02"
subsystem: status-model
tags: [cairn-status, json-contract, milestones, grouping, bats, jq]

requires:
  - phase: 13-phase-model
    provides: "phase_model() como leitura única — os grupos derivam dela, sem I/O novo"
  - plan: "20-01"
    provides: "make_board_fixture e os sete renders de referência, que são o gate de invariância desta mudança"
provides:
  - "roadmap_milestones(): a lista `## Milestones` lida como dados, com `open` vindo do marcador da própria linha"
  - "phase_groups(): a hierarquia milestone → fase → issue como função pura"
  - "chave de topo `groups` no `--json`, consumida pelas fases 21 e 22"
  - "tests/cairn-group-model.bats: 7 testes, cada um com a quebra medida que o vira vermelho"
affects: [20-03, 21-grouped-render, 22-header]

actuals:
  tokens: 4964
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Chave de topo derivada do modelo, ao lado de next_commands e parallelism"
    - "Partição por multiconjunto (sort dos dois lados) como invariante de 'nada perdido, nada duplicado'"
    - "Toda quebra nomeada executada de verdade: vermelho medido, restauração por cp, verde medido"

key-files:
  created:
    - tests/cairn-group-model.bats
  modified:
    - cairn/scripts/cairn-status.py
    - tests/cairn-status.bats

key-decisions:
  - "As duas issues extras (dois rótulos; rótulo de fase arquivada) nascem no setup do próprio arquivo de teste, não em make_board_fixture — mexer no fixture obrigaria a regenerar os sete renders de referência para servir a um único arquivo"
  - "Um balde é emitido para toda fase que o grupo reivindica, mesmo sem issue aberta: o grupo descreve a forma do milestone, e o consumidor já tem len() para saber se está vazio"
  - "Uma fase reivindicada por dois milestones abertos cai no primeiro, nunca em dois: o balde é criado uma vez só"
  - "O docstring do módulo passou a listar phases/next_commands/parallelism no `--json`, que já saíam e não estavam documentados"

requirements-completed: [BOARD-01]

coverage:
  - id: D1
    description: "`--json` carrega a chave de topo `groups` com a hierarquia milestone → fase → tarefa"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-group-model.bats#the open milestone group carries its phases, in ascending order"
        status: pass
      - kind: other
        ref: "bash cairn/scripts/cairn-status.sh --json | jq -e '.groups | type == \"array\"' (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A chave e o rótulo do grupo vêm do ROADMAP, nunca do STATE.md"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-group-model.bats#the group key comes from the roadmap, not from STATE.md"
        status: pass
      - kind: other
        ref: "quebra medida: tirar a chave de state_frontmatter() reprova só esse teste (2 verdes)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Colocação sai exclusivamente do rótulo phase-N, com a regra da menor fase nomeada"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-group-model.bats#a labeled issue lands in its phase's bucket, in lane order"
        status: pass
      - kind: integration
        ref: "tests/cairn-group-model.bats#an issue naming two phases lands in the smallest one it names"
        status: pass
      - kind: other
        ref: "quebra medida: ignorar issue_phase_ns() reprova 4, 5 e 6"
        status: pass
    human_judgment: false
  - id: D4
    description: "Cada issue aberta aparece exatamente uma vez em todo o modelo de grupos"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-group-model.bats#every open issue appears exactly once across all groups"
        status: pass
      - kind: other
        ref: "quebra dupla medida: duplicar reprova 4, 5, 7; perder reprova 6, 7"
        status: pass
    human_judgment: false
  - id: D5
    description: "Nenhum render mudou: os sete arquivos de referência seguem byte a byte"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "bats tests/cairn-board-invariance.bats (9/9)"
        status: pass
      - kind: other
        ref: "git diff --stat -- cairn/templates/ tests/fixtures/ vazio; nenhuma função de render no diff"
        status: pass
    human_judgment: false

duration: 95min
completed: 2026-08-03
status: complete
---

# Phase 20 Plano 02: Modelo de grupo Summary

**A hierarquia milestone → fase → issue existe como chave de topo `groups` do `--json`, tirando "aberto" do marcador da própria linha do roadmap e a colocação só do rótulo `phase-N` — com os sete renders de referência intactos byte a byte.**

## Performance

- **Duration:** ~95 min (dos quais ~40 min de espera por suítes)
- **Tasks:** 2
- **Files modified:** 3 (1 criado, 2 modificados)

## Accomplishments

- `roadmap_milestones(planning_dir)` → `[{key, label, open, first, last}]`, lendo só a seção `## Milestones` (abre no heading, fecha no próximo `## `). Medido: 5 milestones e 1 aberto (`v1.5`, fases 20-29) no ROADMAP deste repositório; 2 e 1 aberto (`v1.1`, fases 3-4) no fixture; 0 num roadmap sem a seção. O heading `## Milestone: v1.5 Legible State 🚧` logo abaixo da lista **não** reabre a seção — a regex é ancorada e plural de propósito.
- `phase_groups(model, milestones, issues)` → grupos `{type, key, label, items}` com baldes homogêneos `{phase, issues}`, milestones abertos na ordem do roadmap e o grupo `unphased` sempre por último. Função pura, sem I/O, na linha de `parallelism()`.
- Chave `groups` no dicionário `data` de `main()`, ao lado de `parallelism` — uma linha, nenhuma chave existente tocada.
- Docstring do módulo: passo `4f` novo descrevendo o que é um grupo, de onde vem "aberto", que rótulos são a única fonte de colocação e que arestas de dependência são deliberadamente ignoradas (FIX-04).
- `tests/cairn-group-model.bats`: 7 testes, arquivo novo.

## Task Commits

1. **Task 1: ler os milestones e emitir os grupos** — `6923e59` (feat)
2. **Task 2: colocação por rótulo e a partição** — `5d9c3a3` (test)

## Vermelho e verde, medidos

Toda quebra foi aplicada de verdade, restaurada por backup `cp` (nunca `git checkout`) e reconfirmada verde.

| Quebra | Vermelho | Verde |
|--------|----------|-------|
| Ignorar a célula `milestone` da tabela `## Progress` | 1, 3 | 2 |
| Ignorar o alcance `Phases A-B` | 2 | 1, 3 |
| Tirar a chave do grupo de `state_frontmatter()` | 3 | 1, 2 |
| Ignorar `issue_phase_ns()` na colocação | 4, 5, 6 | 1, 2, 3, **7** |
| Emitir o grupo `unphased` primeiro | 6 | 1-5, 7 |
| Pôr a issue de dois rótulos em **todos** os baldes | 4, 5, 7 | 1, 2, 3, 6 |
| Descartar issue cujo rótulo aponta para fase não reivindicada | 6, 7 | 1-5 |

A linha que mais informa é a quarta: a partição (teste 7) fica **verde** com a colocação inteiramente quebrada. Ela nunca prometeu pegar colocação errada — só perda e duplicação — e as duas últimas linhas mostram que pega as duas.

## Suítes

- `bats tests/cairn-group-model.bats` → **7/7**
- `bats tests/cairn-board-invariance.bats` → **9/9** (os sete renders byte a byte)
- `bats tests/cairn-status.bats tests/cairn-phase-model.bats` → **83/83** (55 + 28, contagens de `@test` intactas)
- `bats -j 6 tests/*.bats` → **548 testes, 0 falhas** (541 do baseline + 7 novos), ~20 min

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug no plano] A quebra nomeada do teste 1 não o vira vermelho, e o caminho que ela testaria estava sem teste nenhum**

- **Found during:** Task 1
- **Issue:** O plano manda provar o teste 1 removendo a leitura do alcance `Phases A-B`, "sem ela o grupo fica sem baldes". Falso neste fixture: `make_board_fixture` tem tabela `## Progress` com coluna Milestone, então as fases 3 e 4 entram no grupo pela **regra 1** (célula explícita) e o alcance nunca é exercido. Medido: com a leitura de alcance removida, o teste 1 fica **verde**. Pior, o alcance é o **único** caminho no ROADMAP real deste repositório, que não tem tabela de progresso — ou seja, o código que roda em produção não teria teste algum.
- **Fix:** Um teste a mais, "a milestone with no progress table still gets its phases from the range", que apaga a seção `## Progress` do roadmap do fixture e exige que o grupo continue com as fases 3 e 4. A quebra do plano agora reprova esse teste, sozinha. E a quebra correta para o teste 1 — ignorar a célula da tabela — foi medida: reprova 1 e 3.
- **Verification:** Duas quebras medidas, com restauração `cp` byte a byte entre elas.
- **Committed in:** `6923e59`

**2. [Rule 3 - Bloqueio] O plano exige chave nova no `--json` E que `tests/cairn-status.bats` passe sem edição; um teste existente torna as duas coisas incompatíveis**

- **Found during:** Task 2 (rodando o critério de sucesso 3)
- **Issue:** O teste 45 de `cairn-status.bats` (`--json's lease key is additive…`) compara o **conjunto exaustivo** de chaves de topo com um literal. Qualquer chave aditiva o reprova — inclusive a que este plano existe para acrescentar. Medido: 82 ok / 1 not ok. O critério "a suíte atual passa sem uma linha editada" e a restrição dura "chave nova de topo" não podem valer os dois.
- **Fix:** Um literal editado, com a intenção do teste preservada e escrita no comentário: o que aquela lista guarda é *nada renomeado, nada perdido*; uma chave genuinamente aditiva é esperada e é ali que se declara. A contagem de `@test` segue **55**, então a verify do plano continua satisfeita pelo número que ela mede.
- **Verification:** Teste 45 verde de novo; `grep -c '^@test'` = 55 e 28.
- **Committed in:** `5d9c3a3`

**3. [Rule 2 - Documentação incompleta] A linha de chaves do `--json` no docstring omitia três chaves que já saíam**

- **Found during:** Task 1
- **Issue:** O plano manda acrescentar `groups` à linha que lista as chaves do `--json`. Essa linha já não listava `phases`, `next_commands` nem `parallelism`, que a fase 13 acrescentou e o script emite. O docstring é a spec canônica desta casa; uma spec que omite três chaves emitidas está errada, e acrescentar uma quarta sem corrigir perpetuaria isso.
- **Fix:** As quatro estão listadas agora. Nada renomeado, nada reordenado.
- **Committed in:** `6923e59`

---

**Total deviations:** 3 auto-fixed (1 × Rule 1, 1 × Rule 3, 1 × Rule 2)
**Impact on plan:** Nenhuma expansão de escopo. A primeira é a que importa: sem ela o plano entregaria código de produção sem teste e uma prova que não provava.

## Decisões que o plano não cobria

- **As issues extras do teste 5 do plano nascem no `setup()` deste arquivo, não em `make_board_fixture`.** O plano permite acrescentá-las ao fixture e regenerar as sete referências. Não regenerei: toda issue do fixture é renderizada nos sete arquivos commitados, e mexer neles para servir a um único arquivo de teste troca uma prova estável por sete diffs a revisar. Criadas no setup local, exercitam a mesma regra e não tocam em referência nenhuma. As duas são `brd-101` (dois rótulos, `phase-3,phase-4`) e `brd-102` (`phase-1`, fase de milestone arquivado — reivindicada por nenhum grupo, e T-20-06 exige que ela continue visível).
- **Prioridade 4 nas duas**, porque `bd` recusa `-p 5` (aceita 0-4). `fetch_lanes` ordena por `(priority, id)`, então elas caem depois das issues 0/1/2 do fixture e o id desempata — as asserções comparam listas exatas, em ordem de raia.
- **Um balde é emitido para toda fase reivindicada, mesmo sem issue aberta.** D-03 fala de grupo vazio (esse não é emitido), não de balde vazio. O grupo descreve a forma do milestone; a fase 21 decide como isso aparece, e já tem `len()` para saber que está vazio.
- **Uma fase reivindicada por dois milestones abertos entra só no primeiro** (`n in buckets` guarda a criação). Sem isso a mesma fase renderia duas vezes e a partição quebraria por duplicação.
- **`(in progress)` virou a constante `MILESTONE_IN_PROGRESS`**, usada por `roadmap_milestone()` e `roadmap_milestones()`. Os dois leitores de "aberto" agora compartilham literalmente a mesma regex, que é o que o plano pede em prosa.

## Issues Encountered

- **O ROADMAP real diz `Phases 20-29`, não 20-28** como o plano registrou. Nada quebra por isso (o alcance só vira balde para fase existente no modelo), mas a medição do plano estava desatualizada em uma fase.
- **`bats -f` continua proibido** e não foi usado em nenhuma `<verify>`; um filtro sem casamento sai 1 com `ERROR: Found no tests`.
- **FIX-05 (fase 25) segue visível e intocado:** `cairn-status.py:500-501` devolve `executed` com qualquer `-SUMMARY.md` presente, então a fase 20 se descreve como `executed` com `plans_done: 1`. Não é regressão desta fase e não foi consertado aqui.

## User Setup Required

None.

## Next Phase Readiness

- O plano 20-03 tem o que testar: `groups` existe, `roadmap_milestones()` já devolve `open` por linha, e o caso "nenhum milestone aberto → zero grupos de milestone" está implementado (verificado à mão num roadmap só com `✅`) e sem teste — que é exatamente o critério de sucesso 2, trabalho dele.
- A fase 21 tem a forma fechada: `{type, key, label, items}`, `items` homogêneo, sem campo de contagem, `UNPHASED_LABEL` como ponto único para mudar o texto.
- A armadilha STATE/ROADMAP do plano 20-01 segue armada e agora é ativamente verificada por um teste.

---
*Phase: 20-group-model*
*Completed: 2026-08-03*

## Self-Check: PASSED

- Os 3 arquivos declarados existem em disco; os 2 commits de task existem em `git log`.
- `bats -j 6 tests/*.bats` → **548 ok, 0 falhas** (541 do baseline + 7 novos).
- `git diff HEAD~2..HEAD -- cairn/templates/ tests/fixtures/` vazio; o diff de `cairn-status.py` acrescenta exatamente duas funções (`roadmap_milestones`, `phase_groups`) e nenhuma função de render aparece nele.
