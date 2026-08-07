---
phase: 20-group-model
plan: "03"
subsystem: status-model
tags: [cairn-status, json-contract, milestones, grouping, bats, jq, d-02, d-03]

requires:
  - plan: "20-01"
    provides: "make_board_fixture e os sete renders de referência — o gate de invariância que fecha o critério 4"
  - plan: "20-02"
    provides: "roadmap_milestones(), phase_groups() e a chave de topo groups, que este plano testa nas bordas"
provides:
  - "as bordas da D-03 sob teste: sem ciclo aberto e ciclo aberto sem fase, cada uma com sua quebra medida"
  - "a prova de que a colocação não herda FIX-04: rótulo é a única fonte, aresta discovered-from não move nada"
  - "travões mecânicos dos conjuntos de chaves do --json (topo e phases[] agregado)"
  - "docstring 4g: o que o modelo de grupo mede e o que ele presume"
affects: [21-grouped-render, 22-header, 25-fix-04]

actuals:
  tokens: 3620
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Variante de fixture que assere que mutou — uma mutação que para de casar vira teste verde e mudo"
    - "Conjunto de chaves agregado sobre TODAS as linhas, nunca amostrado de uma"
    - "Toda quebra nomeada executada de verdade: vermelho medido, restauração byte a byte, verde medido"

key-files:
  created: []
  modified:
    - tests/cairn-group-model.bats
    - cairn/scripts/cairn-status.py

key-decisions:
  - "Task 1 não escreveu código: as duas regras de emissão da D-03 já estavam implementadas pelo 20-02 e o que faltava era prova. O plano listava cairn-status.py entre os arquivos da task; a task entregou três testes e nenhuma linha de produção"
  - "Variante B assere que é variante chamando roadmap_milestones() direto — o --json não expõe o marcador de aberto do roadmap, e sem essa leitura a variante B degenera silenciosamente na variante A"
  - "O teste 11 usa duas asserções para a colocação (contagem 1 E o grupo em que caiu) porque a contagem sozinha fica verde com a issue no balde errado — medido"
  - "O rótulo do grupo solto é asserido literalmente ('No milestone'): nomear o grupo solto com o último ciclo conhecido 'para dar contexto' é a mesma mentira em voz mais amigável"

requirements-completed: [BOARD-01]

coverage:
  - id: D1
    description: "Sem milestone aberto no roadmap, zero grupos de milestone e nenhum rótulo do ciclo arquivado"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-group-model.bats#variant A: no open milestone in the roadmap means no milestone group"
        status: pass
      - kind: integration
        ref: "tests/cairn-group-model.bats#variant A: no group wears the archived cycle's name, and the work stays"
        status: pass
      - kind: other
        ref: "quebra medida: cair no 'último milestone quando nenhum está aberto' reprova 8 e 9, sozinhas"
        status: pass
    human_judgment: false
  - id: D2
    description: "Um milestone aberto cujo alcance não nomeia fase existente não vira grupo (grupo sem itens não é emitido)"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-group-model.bats#variant B: an open milestone naming no existing phase is not a group"
        status: pass
      - kind: other
        ref: "quebra medida: tirar o guarda `if not items: continue` reprova 10, sozinha"
        status: pass
    human_judgment: false
  - id: D3
    description: "Issue de ciclo arquivado com aresta discovered-from cai no grupo solto e não move grupo nenhum"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-group-model.bats#an archived-cycle issue with a discovered-from edge neither groups nor vanishes"
        status: pass
      - kind: other
        ref: "quebra medida: seguir a aresta quando o rótulo não coloca reprova 11 — e falha na asserção de GRUPO, não na de contagem"
        status: pass
    human_judgment: false
  - id: D4
    description: "As chaves de uma linha de phases[] são exatamente as 22 de antes; a estrutura de grupo é chave de topo (D-02)"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "tests/cairn-group-model.bats#every phases[] row carries exactly the 22 keys it always did"
        status: pass
      - kind: other
        ref: "quebra medida sob violação da D-02: .phases[0] mostra 22 chaves (verde) e o agregado mostra 23, a extra sendo `group`"
        status: pass
    human_judgment: false
  - id: D5
    description: "Nenhum render mudou: os sete arquivos de referência seguem byte a byte"
    requirement: "BOARD-01"
    verification:
      - kind: integration
        ref: "bats tests/cairn-board-invariance.bats (9/9, dentro dos 555)"
        status: pass
      - kind: other
        ref: "git diff --stat fff5809..HEAD -- tests/fixtures/board-render/ vazio: nunca regenerado desde que o 20-01 gravou"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-08-03
status: complete
---

# Phase 20 Plano 03: As bordas do modelo de grupo Summary

**As três formas de o modelo se calar quando não tem o que dizer, cada uma com a quebra que a vira vermelha; a prova de que a colocação por rótulo não herda o FIX-04; e os travões de chave que tornam "nada mudou de nome" verificável em vez de afirmado.**

## Performance

- **Duration:** ~70 min (dos quais ~35 min de espera pela suíte completa)
- **Tasks:** 3
- **Files modified:** 2 (0 criados, 2 modificados)

## Accomplishments

- **Task 1 — o silêncio honesto.** Dois helpers de variante que mutam o `ROADMAP.md`
  do repo temporário (nunca `tests/fixtures/`), cada um asserindo que mutou: um
  `replace` que para de casar deixaria o milestone aberto e todos os testes abaixo
  verdes medindo nada. Variante A arquiva o ciclo aberto (o repositório dez minutos
  depois do `/cairn:milestone complete`); variante B arquiva v1.1 e abre um `v9.9`
  cujo alcance é `Phases 90-99`. Três testes: zero grupos de milestone, nenhum
  rótulo do ciclo arquivado entre chaves e labels, e o grupo solto carregando as sete
  issues nos dois casos.
- **Task 2 — não herdar a confusão.** Uma issue `brd-103` rotulada `phase-9` (fase de
  nenhum roadmap aqui) com `--deps discovered-from:brd-001` — a mesma forma de aresta
  que hoje faz a fase 26 ler como bloqueada pela fase 9. Aparece uma vez, no grupo
  solto; o conjunto de chaves de milestone é idêntico ao da mesma montagem sem ela; e
  os conjuntos completos de chave e rótulo não nomeiam nada que o rótulo perdido
  arrastou. Mais o `4g` do docstring de módulo, com o medido e o presumido.
- **Task 3 — os travões de contrato.** Conjunto de chaves de topo (as 14 de antes mais
  `groups`), conjunto de `phases[]` **agregado sobre todas as linhas** com a premissa
  asserida antes de ser usada, e o arame de tropeço de `disk_state` com o comentário
  que diz quanto ele não prova.

## Task Commits

1. **Task 1: o silêncio honesto** — `721aca5` (test)
2. **Task 2: o ciclo arquivado que não contamina** — `37e7106` (test)
3. **Task 3: os travões de contrato** — `fb3fbd4` (test)

## Vermelho e verde, medidos

Toda quebra foi aplicada de verdade, restaurada de backup `cp` (ou de `HEAD`, quando
não havia trabalho não commitado no arquivo) e reconfirmada verde antes da seguinte.

| Quebra | Vermelho | Verde |
|--------|----------|-------|
| Cair no "último milestone da lista quando nenhum está aberto" | 8, 9 | 1-7, **10** |
| Tirar o guarda `if not items: continue` (emitir grupo com `items: []`) | 10 | 1-9, 11 |
| Colocar por aresta quando o rótulo não coloca | 11 | 1-10 |
| Criar um grupo por rótulo encontrado, sem confrontar o roadmap | 1, 2, 3, 6, 8, 9, 10, 11 | 4, 5, 7 |
| Renomear uma chave de topo existente (`stale_complete`) | 12 | 13, 14 |
| Aninhar a chave de grupo dentro de `phases[]` (violação da D-02) | 13 | 12, 14 |

Duas linhas informam mais que o resto:

- **A primeira e a segunda são ortogonais**, e é isso que separa as duas metades da
  D-03. O fallback para o último milestone não toca na variante B (lá existe milestone
  aberto), e o guarda de grupo vazio não toca na variante A (lá não se emite grupo de
  jeito nenhum). Cada regra tem seu próprio teste, e nenhuma está sendo provada de
  carona na outra.
- **A terceira falha na asserção de grupo, não na de contagem.** Com a colocação
  seguindo a aresta, `brd-103` continua aparecendo **exatamente uma vez** — só que no
  balde da fase 3. "Aparece uma vez" nunca prometeu pegar colocação errada; é por isso
  que o teste 11 tem as duas asserções, e a medição confirma qual das duas trabalha.

### A medição que justifica agregar em vez de amostrar

Com a violação da D-02 plantada (uma chave `group` escrita nas fases que um milestone
aberto reivindica), medido sobre o fixture do 20-01:

```
.phases[0]  → 22 chaves, idênticas ao literal esperado   (verde)
agregado    → 23 chaves; a extra é `group`               (vermelho)
```

`.phases[0]` do fixture é a fase 1, `complete=true`, do ciclo **arquivado** — o
aninhamento mais plausível nunca a toca. Uma amostra de uma linha ficaria verde com a
decisão violada. O teste assere essa premissa (`.phases[0]` é `1 true`) antes de se
apoiar nela.

## Suítes

- `bats -j 6 tests/cairn-group-model.bats` → **14/14** (7 do 20-02 + 7 novos)
- `bats -j 6 tests/cairn-board-invariance.bats` → **9/9** (os sete renders byte a byte)
- `bats -j 6 tests/` → **555 ok, 0 falhas**, exit 0 (548 do baseline do 20-02 + 7)
- `grep -c '^@test'` → `cairn-status.bats` **55**, `cairn-phase-model.bats` **28**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug no plano] A verify de dep_target_ids conta prosa, e já estava falsa antes desta task começar**

- **Found during:** Task 2
- **Issue:** O plano exige
  `[ "$(grep -v '^[[:space:]]*#' cairn-status.py | grep -c 'dep_target_ids')" -eq 2 ]`.
  Medido em `HEAD` **antes** desta task: **4**, não 2. O `grep -v '^#'` tira comentário
  de linha, não docstring, e o docstring de `phase_groups()` que o 20-02 escreveu
  menciona `dep_target_ids` duas vezes — justamente para explicar por que não o usa. A
  verify reprova o arquivo por ele documentar bem a própria decisão.
- **Fix:** A intenção — *nenhum ponto de uso novo; agrupar nunca lê aresta* — é sobre
  referências executáveis. Medida por AST, que não confunde prosa com código:
  `defs=1 refs=1`, o único chamador sendo `issue_phase_deps` — **idêntico ao baseline
  pré-fase-20** (`6d81d5c`, também `defs=1 refs=1`). Nenhuma linha de código foi
  alterada para satisfazer isso; a verify é que estava medindo a coisa errada.
- **Verification:** `python3 -c ast.walk(...)` sobre `HEAD` e sobre `6d81d5c`.
- **Committed in:** `37e7106` (a medição; o código não precisou mudar)

**2. [Rule 3 - Bloqueio] O `<verify>` da Task 3 exige `bats tests/`, que sob pipe mascara o status do bats**

- **Found during:** Task 3
- **Issue:** `bats -j 6 tests/ | tail -25` devolveu exit 0 com **saída vazia**: sob
  `-j`, o bats bufferiza por arquivo e o `tail` reportou o status dele próprio, não o
  do bats. Um "verde" assim é indistinguível de uma suíte que nem rodou.
- **Fix:** TAP inteiro redirecionado para arquivo, `BATS_EXIT` anexado explicitamente,
  e as contagens lidas do arquivo: `1..555`, `ok=555`, `not ok=0`, `BATS_EXIT=0`.
- **Committed in:** `fb3fbd4` (a mensagem carrega os números)

### Divergências entre o plano e o que o repositório já era

**3. A Task 1 não tinha código para escrever.** O plano lista `cairn-status.py` entre
os arquivos da task e descreve as Regras A e B como trabalho a fazer. As duas já
estavam implementadas pelo 20-02 (`if not ms["open"]: continue` e
`if not items: continue`), e o docstring de `roadmap_milestones()` já carregava a data
da medição que o plano manda registrar. O que faltava era **prova**, e é só isso que a
task entregou: três testes, zero linhas de produção. Registrado aqui porque um
`files_modified` que promete código e entrega teste é exatamente o tipo de coisa que
uma auditoria futura leria como trabalho perdido.

**4. Duas medições do plano estavam desatualizadas.** O alcance do v1.5 é
`Phases 20-29`, não 20-28 (o 20-02 já tinha registrado isso; o `4g` usa o número
certo). E `disk_state` neste repositório hoje é `["executed","none"]`, não
`none,planned` — porque a fase 20 passou a ter SUMMARY e o FIX-05 faz um summary só
descrever a fase inteira como `executed`. Nenhuma das duas muda uma asserção: o teste
14 é subconjunto, e `executed` é um dos quatro valores.

**5. STATE.md, ROADMAP.md e REQUIREMENTS.md foram escritos pela SDK e revertidos**

- **Found during:** fechamento
- **Issue:** O passo de state updates do executor roda
  `state.advance-plan`, `roadmap.update-plan-progress` e
  `requirements.mark-complete`, que escrevem nos três arquivos. O briefing desta
  onda proíbe tocá-los, e a proibição tem razão de ser: `cairn-status.py` **lê** o
  `.planning/ROADMAP.md` deste repositório, e o `4g` que esta onda escreveu registra
  fatos medidos sobre ele (5 milestones, 1 aberto, `Phases 20-29`). Pior, o
  `roadmap.update-plan-progress` não se limitou aos checkboxes da fase 20: reflowou
  as listas de critérios de sucesso das fases 21, 22 e seguintes, inserindo linha em
  branco entre itens — 35 linhas de diff para uma mudança de 3.
- **Fix:** Os três restaurados de `HEAD`. O que a SDK escreveu está em
  `/tmp/gsd-state-writes/` para revisão, caso o Felipe queira aplicar só os
  checkboxes da fase 20. `state.record-metric` e `state.record-session` também
  rodaram e foram revertidos junto.
- **Nota:** os três estavam limpos em `HEAD` antes disso — a única mudança
  descartada foi a da própria SDK, e ela foi copiada antes de qualquer `checkout`.

---

**Total deviations:** 2 auto-fixed (1 × Rule 1, 1 × Rule 3) + 3 divergências registradas
**Impact on plan:** Nenhuma expansão de escopo, nenhuma linha de produção escrita para
satisfazer uma verify.

## Os quatro critérios de sucesso da fase 20, um a um

Esta é a última onda da fase, então o veredito completo:

1. **"O modelo carrega, por milestone aberto, suas fases; e o trabalho sem milestone
   num grupo próprio, ordenado por último."** — **Atendido.** Entregue pelo 20-02,
   preso pelos testes 1, 2 e 6 (`.groups[-1].type == "unphased"`).

2. **"Um repositório sem milestone aberto produz zero grupos de milestone e um grupo
   de trabalho solto — nunca um grupo nomeado com o último ciclo arquivado."** —
   **Atendido**, e é o que esta onda existia para fechar (testes 8, 9, 10).
   Uma nuance que o critério não escreve e a D-03 decide: se além de não haver ciclo
   aberto **também** não houver trabalho solto, não sai grupo nenhum — nem o solto,
   porque grupo vazio não é emitido. A frase "e um grupo de trabalho solto" vale
   sempre que existir trabalho solto, que é o caso de todo repositório vivo.

3. **"`--json` ganha a estrutura de grupos sem que nenhuma chave existente mude de
   nome, de tipo ou de significado; a suíte atual passa sem edição."** — **Metade
   atendida, metade impossível como escrita.**
   A primeira metade está atendida e agora é **mecanicamente verificável**, o que antes
   não era: testes 12 e 13 comparam os conjuntos exaustivos, e o 13 é o único jeito
   mecânico de provar a D-02 ("chave nova ao lado, nunca dentro").
   A segunda metade — *a suíte atual passa sem edição* — **não foi atendida, e não
   podia ser.** O teste 45 de `cairn-status.bats:1186` compara o conjunto exaustivo de
   chaves de topo com um literal, então **qualquer** chave aditiva o reprova, inclusive
   a que esta fase existe para acrescentar (medido pelo 20-02: 82 ok / 1 not ok). Uma
   linha foi editada, com a intenção do teste preservada em comentário. O critério,
   como redigido, contradiz a restrição dura da própria fase; o que ele queria dizer —
   *nada renomeado, nada perdido, nenhum consumidor quebrado* — está atendido e
   mais bem preso do que estaria pelo silêncio da suíte.
   Os dois literais foram conferidos e **concordam**: `cairn-status.bats:1186` e o teste
   12 afirmam o mesmo conjunto de 15 chaves, sob fixtures diferentes.

4. **"Um teste renderiza o board antes e depois da fase e prova que a saída é byte a
   byte idêntica."** — **Atendido.** `tests/cairn-board-invariance.bats` 9/9 dentro dos
   555. E a prova de que a prova não foi carimbada:
   `git diff --stat fff5809..HEAD -- tests/fixtures/board-render/` está **vazio** — as
   sete referências não foram regeneradas uma única vez desde que o 20-01 as gravou do
   código intocado. Nenhuma regeneração aconteceu nesta fase, então não há linha a
   explicar.

## Verificação da fase inteira (`6d81d5c..HEAD`)

- `tests/fixtures/` e `cairn/templates/`: **intocados**.
- Funções tocadas em `cairn-status.py`, por cabeçalho de hunk: `main()`,
  `next_commands()` e `roadmap_milestone()` (as duas últimas por adjacência — as
  funções novas foram inseridas depois delas), o docstring de módulo e o bloco de
  constantes. **Nenhuma função de render aparece.**
- `disk_state` e `phase_next_command`: **zero ocorrências** no lado escrito do diff da
  fase. Esta é a mitigação real do contrato dos quatro valores, e o teste 14 é
  complemento barato — sobre um fixture que só produz `none`, a asserção de subconjunto
  passa trivialmente.
- Linhas deletadas na fase inteira: **3** — duas de docstring (a lista de chaves do
  `--json`, substituída pela completa) e a regex inline de `roadmap_milestone()`,
  trocada pela constante `MILESTONE_IN_PROGRESS`. Todo o resto é aditivo (236 inserções).

## Issues Encountered

- **FIX-05 segue visível e intocado.** `cairn-status.py:500-501` devolve `executed`
  com qualquer `-SUMMARY.md` presente, então a fase 20 se descreve como `executed` com
  `plans_done` incompleto e o doctor fica vermelho nela. É trabalho da fase 25 e não
  foi tocado aqui.
- **`bats -j 6` bufferiza por arquivo.** Não dá para acompanhar progresso pelo stdout,
  e o pipe mascara o status (item 2 das divergências). Para uma suíte de 555 testes que
  leva ~20 min, redirecionar o TAP para arquivo é o único jeito honesto de medir.
- **`CairnGo-8vy` continua `in_progress`.** A issue cobre o board redesenhado inteiro
  (agrupamento, emoji por estado, degrade não-TTY do `--plain`) — fases 20, 21 e 22.
  Fechá-la aqui diria que o board foi reformatado, e ele não foi: esta fase termina com
  o render byte a byte igual, de propósito.

## User Setup Required

None.

## Next Phase Readiness

- A fase 21 tem o modelo fechado e agora **preso**: `{type, key, label, items}`, `items`
  homogêneo, grupos de milestone na ordem do roadmap, `unphased` por último, e as
  bordas (sem ciclo aberto, ciclo sem fase, rótulo órfão) todas com teste.
- As sete referências de render são o gate da fase 21 também — e ela **vai** precisar
  regenerá-las, porque é a fase que muda o render de propósito. O `regenerate.sh` é o
  único escritor, e o SUMMARY da 21 é quem passa a dever a explicação de cada linha
  mudada.
- FIX-04 (fase 25) tem, agora, um teste que documenta o comportamento correto ao lado:
  quando a fase 25 consertar o bloqueio por aresta, o teste 11 continua verde — ele
  prende a colocação por rótulo, não o defeito.

---
*Phase: 20-group-model*
*Completed: 2026-08-03*

## Self-Check: PASSED

- Os 2 arquivos declarados existem em disco; os 3 commits de task existem em `git log`.
- `bats -j 6 tests/` → **555 ok, 0 falhas**, `BATS_EXIT=0`, plano `1..555`.
- `git diff --stat fff5809..HEAD -- tests/fixtures/board-render/` vazio; nenhuma função
  de render no diff da fase; `disk_state` e `phase_next_command` ausentes do lado
  escrito.
