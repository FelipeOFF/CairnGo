---
phase: 29-nothing-mechanical-stays-manual
plan: "01"
subsystem: planning-bookkeeping
tags: [python, bats, fixtures, stdlib, markdown-surgery]
requires:
  - cairn-map.py's `**Requirements**:` dialect (roadmap_requirements)
  - cairn-migrate.py's CHECKBOX_PHASE_LENIENT family
  - tests/helpers.bash make_tmp_repo / make_gsd_fixture
provides:
  - cairn-bookkeep.py close — per-line ROADMAP checkbox surgery behind --apply
  - cairn-bookkeep.py reconcile — the full read-only disagreement inventory
  - tests/fixtures/bookkeep-drift/ — this repo's own drift, frozen in bytes
  - make_drift_fixture — a repo built from that fixture, with a baseline commit
affects:
  - plan 29-02 (the write path builds on plan_close/apply_edits and reconcile)
  - plan 29-07 (req-ledger consumes reconcile's exit 3 and its findings)
tech-stack:
  added: []
  patterns:
    - "line surgery over splitlines(keepends=True), never reserialization"
    - "read by default, write behind a named --apply (cairn-doctor's pattern)"
    - "fixture written by one human-run capture.sh, read by tests, never regenerated to fix a red test"
    - "test anchors hardcoded, NOT read back from the file the capture script rewrites"
key-files:
  created:
    - cairn/scripts/cairn-bookkeep.py
    - cairn/scripts/cairn-bookkeep.sh
    - tests/cairn-bookkeep.bats
    - tests/fixtures/bookkeep-drift/capture.sh
    - tests/fixtures/bookkeep-drift/MANIFEST.md
    - tests/fixtures/bookkeep-drift/ROADMAP.md
    - tests/fixtures/bookkeep-drift/REQUIREMENTS.md
    - tests/fixtures/bookkeep-drift/STATE.md
    - tests/fixtures/bookkeep-drift/phases.tsv
  modified:
    - tests/helpers.bash
    - tests/README.md
key-decisions:
  - "As âncoras do fixture são literais no .bats, não lidas do MANIFEST.md — provado por medição: com o manifesto realinhado, o guarda de sha256 fica verde e só o literal pega a captura tardia"
  - "Nenhuma flag e nenhum exit code é declarado antes de ter comportamento: sem --project-dir, sem --no-tracker, e o 5 documentado como RESERVADO em vez de prometido"
  - "A tabela de cobertura tem duas casas medidas (## Cobertura no ROADMAP, ## Traceability no REQUIREMENTS); ler só uma reportava 35 linhas faltando sobre uma tabela que estava ali"
  - "Modo leitura é provado por sha256 E mtime — uma reescrita byte-idêntica passava só pelo sha e continua sendo escrita"
metrics:
  duration: ~2h
  completed: 2026-08-03
status: complete
actuals:
  tokens: 33558
  tasks: 3
  commits: 3
---

# Phase 29 Plan 01: Congelar a doença e construir o diagnóstico — Summary

**A discordância deste próprio repositório está congelada em bytes commitados, e um comando stdlib nomeia as dez maneiras pelas quais os três arquivos de planejamento se contradizem — inclusive a reticência que hoje faz duas ferramentas responderem `ok`.**

## O que foi construído

**`cairn-bookkeep.py` / `.sh`** — o par da casa, com o docstring como especificação
canônica e uma seção que separa **medido** de **assumido**.

- `close <N> [--apply]` — a fatia fim a fim: acha a linha de checkbox da fase N por
  âncora estrutural, troca `[ ]` por `[x]` e não toca em mais nada. Sem `--apply`,
  imprime o que faria e sai 3. Ambiguidade (duas linhas para o mesmo número) é exit
  2 nomeando as duas, nunca "pega a primeira".
- `reconcile [--json]` — lê os três arquivos e a árvore de fases e devolve o
  inventário completo da discordância. **Zero escrita, e nenhuma flag `--apply`
  existe**: resolver é o 29-02.

**`tests/fixtures/bookkeep-drift/`** — cópia em bytes de `.planning/ROADMAP.md`,
`REQUIREMENTS.md` e `STATE.md` do commit `ce372f4`, congelada com a doença dentro,
mais `phases.tsv` e um `MANIFEST.md` com sha256 e o inventário. Escritor único:
`capture.sh`, rodado por gente.

**`make_drift_fixture`** (`tests/helpers.bash`) — monta um repo a partir do fixture,
reconstrói a árvore de fases por **nome** e **commita o estado inicial**.

## As dez discordâncias que o `reconcile` nomeia

Medidas duas vezes, por dois parsers independentes (o `capture.sh` e o
`cairn-bookkeep.py`), e as duas contagens batem:

| kind | subject | medido |
|---|---|---|
| `requirements-line-unreadable` | Phase 29 | `**Requirements**: AUTO-01 … AUTO-08` → 2 ids |
| `coverage-row-missing` | AUTO-05, AUTO-06 | requisito ativo sem linha na tabela |
| `requirement-checkbox-stale` | BOARD-01 | `- [ ]` com a fase 20 fechada |
| `footer-count-stale` | rodapé | afirma 29, a tabela tem 33 |
| `plan-checkbox-stale` | 20-01/02/03-PLAN.md | `- [ ]` com `-SUMMARY.md` no disco |
| `state-counter-stale` | `progress.total_plans` | 3 contra 10 no disco |
| `state-narrative-stale` | `last_activity_desc` | "(9 fases, 24 requisitos)" contra 10 e 35 |

`CORR-09` aparece em `requirements.deferred`, **fora** de `disagreements`: ausência
explicada não é discordância, e silenciá-la repetiria o defeito na direção oposta.

### A reticência, e as três coisas que o comando faz com ela

Detecta (dois sinais: a reticência entre dois ids, e a tabela mapeando
`AUTO-02/03/04/07` para uma fase cuja linha não os menciona), **nomeia** com a linha
crua e os dois ids extraídos, e **não expande**. `expected` fica `null` porque o que
a linha *deveria* dizer é genuinamente desconhecido a partir deste arquivo:
`AUTO-05` e `AUTO-06` nem estão na tabela, então nenhuma vista do ROADMAP
reconstitui os ids que faltam. Aritmética de sufixo devolveria oito e mentiria com
mais confiança que o silêncio.

## Prova: cada quebra nomeada, vermelha e restaurada

Toda quebra foi aplicada ao código, medida, e restaurada de um backup `cp`.

| # | Quebra | Vermelho | Verde após restaurar |
|---|---|---|---|
| 1 | escrita sem `--apply` | 1/9 | 9/9 |
| 2 | reflow no write (re-wrap a 80 colunas) | 2/9 | 9/9 |
| 3 | escritor incondicional (reescreve o já marcado) | 2/9 | 9/9 |
| 4 | captura tardia **com manifesto realinhado** | 1/14 | 14/14 |
| 5 | `make_drift_fixture` sem o commit inicial | 1/14 | 14/14 |
| A | parser que silencia a reticência (o de hoje) | 3/23 | 23/23 |
| B | parser esperto demais, que inventa os oito ids | 1/23 | 23/23 |
| C | contador ingênuo que mete `CORR-09` nos ativos | 3/23 | 23/23 |
| D | comando que lê o rodapé como fonte da contagem | 2/23 | 23/23 |
| E | ler a prosa do corpo do STATE (o `29 → 18`) | 1/23 | 23/23 |
| F | contadores lidos do frontmatter, não do disco | 2/23 | 23/23 |
| G | `reconcile` que reescreve o arquivo (byte-idêntico) | 1/23 | 23/23 |
| G2 | `reconcile` que "aproveita e arruma" | 4/23 | 23/23 |

A quebra 4 é a mais informativa do plano inteiro, e está detalhada abaixo.

## Contagens de teste

| | testes | falhas |
|---|---|---|
| baseline (`grep -h '^@test' tests/*.bats`) | 556 | 0 |
| `tests/cairn-bookkeep.bats` (novo) | 23 | 0 |
| `cairn-map.bats` + `cairn-status.bats` (vizinhos, `-j 6`) | 67 | 0 |
| `cairn-phase-model.bats` (consome `helpers.bash`) | 6 | 0 |
| `cairn-group-model.bats` (consome `helpers.bash`) | — | 0 |

**A suíte completa não pôde ser medida limpa, e a razão é do ambiente, não do
código.** O plano 29-03 roda concorrente na mesma árvore e a sua
`cairn-parallel.bats` gera bats aninhado: com os dois planos ativos, a máquina
chegou a **95 processos `bats-exec-file`** e o meu `bats -j 6 tests/*.bats` travou em
**171 ok / 0 not ok** por contenção, não por falha. Abortei em vez de reportar um
número que a contenção produziu. As três rodadas escopadas acima são a evidência de
regressão — e a de `cairn-map` + `cairn-status` é a que importa mais, porque prova
que o `tests/helpers.bash` compartilhado (que este plano editou) carrega e que os
builders existentes continuam funcionando.

`python3 -m py_compile cairn/scripts/cairn-bookkeep.py` limpo.
`git diff --quiet HEAD -- .planning/{ROADMAP,REQUIREMENTS,STATE}.md` sai 0 — este
plano não tocou o conteúdo de nenhum dos três, e é isso que dá valor ao fixture.

## Deviations from Plan

### 1. [Rule 1 — Bug no plano] As âncoras do fixture são literais no `.bats`, não lidas do `MANIFEST.md`

- **Encontrado em:** Task 2
- **O que o plano dizia:** "Os números esperados vêm do `MANIFEST.md` escrito pelo
  `capture.sh`, lidos pelo bats no `setup` — **não** são digitados no `.bats`."
  Justificativa: um literal envelhece entre o plano ser escrito e rodar.
- **O defeito:** o `capture.sh` escreve o fixture **e** o manifesto na mesma rodada.
  Uma captura feita depois de alguém arrumar o `.planning/` move os dois juntos, e
  todo guarda derivado do manifesto continua verde sobre uma prova vazia.
- **Demonstrado, não argumentado.** Arrumei o ROADMAP congelado (acrescentei as duas
  linhas faltantes, corrigi o rodapé para 35) e realinhei o hash do manifesto como
  uma captura tardia faria:

  ```
  ok      fixture: the frozen files still hash to what the manifest recorded
  not ok  fixture: the frozen ROADMAP still carries the disease it was frozen for
  ```

  A tautologia ficou verde; só a âncora literal pegou.
- **Por que o medo do plano não se aplica:** ele era sobre `.planning/`, que andou
  três vezes durante o planejamento (33 → 34 → 35 ativos). Uma cópia congelada **não
  envelhece** — é a razão de congelar.
- **Onde:** `tests/cairn-bookkeep.bats` (bloco de comentário acima dos guardas),
  `tests/README.md`. Commit `1661a94`.

### 2. [Rule 2 — Funcionalidade crítica ausente] O modo leitura era provado só por sha256

- **Encontrado em:** Task 3, ao rodar a quebra G
- **O defeito:** o teste chamado `read mode does not write one byte` comparava só
  `sha256`. Um `reconcile` que reescrevesse o arquivo com conteúdo **idêntico**
  passava — e uma reescrita byte-idêntica continua sendo uma escrita, e continua
  contradizendo o nome do próprio teste. A quebra G não produziu um vermelho sequer
  na primeira tentativa.
- **Conserto:** o teste compara `mtime` em nanossegundos além do sha256. As duas
  formas da quebra (byte-idêntica e "aproveita e conserta o checkbox") agora ficam
  vermelhas.
- **Onde:** `tests/cairn-bookkeep.bats` (`file_mtime`). Commit `27d5830`.

### 3. [Rule 1 — Bug] Ler só `## Cobertura` gritava 35 linhas faltando sobre uma tabela que estava ali

- **Encontrado em:** Task 3, contra `make_gsd_fixture`
- **O defeito:** o template do GSD escreve a mesma tabela de três colunas sob
  `## Traceability` no `REQUIREMENTS.md`; este repo escreve sob `## Cobertura` no
  `ROADMAP.md`. Lendo só a segunda casa, o comando reportava um
  `coverage-row-missing` **por requisito** — exatamente o comportamento que esta fase
  existe para eliminar: uma superfície respondendo sem saber sobre o que está
  respondendo.
- **Conserto:** as duas casas são lidas, ROADMAP primeiro; e uma árvore **sem** tabela
  em lugar nenhum produz **um** achado (`coverage-view-missing`), não um por
  requisito. Dois testes cobrem os dois casos.
- **Onde:** `parse_coverage()` em `cairn-bookkeep.py`. Commit `27d5830`.

### 4. [Rule 2] Nenhuma flag e nenhum exit code declarado antes de ter comportamento

- **O plano pedia** `--project-dir` e `--no-tracker` entre as flags, e o contrato de
  exit code incluindo `5 bd indisponível`.
- **O que foi feito:** `--project-dir` e `--no-tracker` **não existem** — este script
  não fala com `bd` nem precisa da raiz do projeto, e uma flag que ninguém lê é
  `cairn.sync_push` de novo, o defeito medido que o próprio 29-CONTEXT.md nomeia. O
  `--planning-dir` sozinho já põe o script além da fronteira do argparse na
  CONVENTIONS.md (3 flags).
- O exit `5` está documentado como **RESERVADO** para "bd indisponível", não
  reivindicado: o script não pode devolvê-lo hoje, e a entrada existe para que o
  29-02 não gaste o número em outra coisa. Nomear um código como reservado é a
  diferença entre uma promessa e uma mentira.

### 5. [Rule 4 — decisão estrutural, resolvida pela restrição explícita do plano] Nenhuma verb de estado do gsd-tools foi executada

O passo genérico de fecho do executor manda rodar `state advance-plan`,
`state update-progress`, `state record-metric`, `state add-decision`,
`state record-session`, `roadmap update-plan-progress` e
`requirements mark-complete`. **Nenhuma foi executada**, e não é omissão:

- o plano proíbe explicitamente tocar o conteúdo de `.planning/STATE.md`,
  `ROADMAP.md` e `REQUIREMENTS.md` — editá-los é o plano 29-02;
- todas essas verbs escrevem exatamente nesses três arquivos, pelo caminho que a
  D-01 mediu como corrompido: `state record-session` reescreveu `current_phase:
  29 → 18` lendo a prosa obsoleta, e `roadmap update-plan-progress 20` produziu
  **+31/−4** para virar três checkboxes. Rodá-las aqui reproduziria a corrupção que
  este plano existe para tornar detectável, e contaminaria a entrada que o 29-02
  precisa reconciliar;
- `requirements mark-complete AUTO-01` também seria falso: o AUTO-01 só fecha quando
  o caminho de escrita do 29-02 existir.

O commit de metadados leva **apenas** o `29-01-SUMMARY.md`. Quem move STATE, ROADMAP
e REQUIREMENTS nesta fase é o `cairn-bookkeep.py --apply` do 29-02 — que é o ponto
inteiro do milestone.

### 6. [menor] `setup()` do `.bats` deixou de escrever o ROADMAP mínimo

Cada teste de `close` chama `write_mini_roadmap` explicitamente, para que os testes
do fixture não herdem um arquivo que jogariam fora.

## O que o plano acertou e vale registrar

- **`git diff --quiet HEAD`** (com `HEAD`, não sem) — o baseline estava limpo, e a
  captura aconteceu antes de qualquer toque.
- **A âncora estrutural** em vez de literal: a linha da fase 29 já tinha mudado uma
  vez (`AUTO-07` → `AUTO-08`), e uma regex sobre o texto já estaria morta.
- **O commit em `make_drift_fixture`**: sem ele, `git rev-parse HEAD` falha e
  `git diff --numstat` mede nada contra nada. Confirmado pela quebra 5.

## Decisões não cobertas pelo plano

1. **Leitura/escrita com `newline=""`.** `Path.read_text()` dobra CRLF em LF, e a
   escrita seguinte reescreveria **todas** as linhas do arquivo — a classe exata de
   dano que o script existe para evitar. Nenhum arquivo CRLF foi visto neste repo; o
   tratamento custa nada e remove a suposição em vez de se apoiar nela (registrado
   como ASSUMIDO no docstring).
2. **`coverage-row-orphan`** — linha na tabela para um requisito que não é ativo.
   Não estava na lista do plano; produz zero no fixture de hoje, e sem ele um id
   estranho na tabela sumiria em silêncio.
3. **A varredura de fase é do arquivo inteiro**, não da seção `## Phases`. Medido:
   neste ROADMAP ela casa exatamente as dez linhas e nenhuma outra. Ambiguidade é
   exit 2, o que é mais honesto que escopo silencioso.
4. **`state.frontmatter` é ecoado cru** no `--json`, ao lado de `state.computed`.
   Quem lê vê o que o arquivo afirma e o que o disco diz, lado a lado.

## Known Stubs

Nenhum. Todo caminho de código deste plano tem teste, e todo teste tem uma quebra
nomeada que o deixa vermelho.

## Threat Flags

Nenhuma superfície nova de rede, autenticação ou acesso a arquivo fora de
`.planning/` e `tests/fixtures/`. O `reconcile` é comprovadamente livre de escrita
(sha256 **e** mtime), e o `close` escreve apenas atrás de `--apply`.

## Verificação do plano

- [x] `bats tests/cairn-bookkeep.bats` — 23/23
- [x] `git diff --quiet HEAD -- .planning/{ROADMAP,REQUIREMENTS,STATE}.md` — exit 0
- [x] `python3 -m py_compile cairn/scripts/cairn-bookkeep.py` — limpo
- [x] `bats tests/cairn-map.bats tests/cairn-status.bats` — 67/67, sem uma linha
      editada nesses arquivos

## Self-Check: PASSED

Todos os artefatos declarados existem no disco e os três commits existem no
histórico (`ce372f4`, `1661a94`, `27d5830`).
