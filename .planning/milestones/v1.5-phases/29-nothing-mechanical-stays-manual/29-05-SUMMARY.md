---
phase: 29-nothing-mechanical-stays-manual
plan: "05"
subsystem: ui
tags: [board, tracker, external-ref, roadmap, tripwire, offline, bats, ast, stdlib]

requires:
  - phase: 29-04
    provides: "o detector de Jira e o cairn-jira.py — o backend que um dia poderá preencher o external_ref que este plano exibe"
provides:
  - "external_ref no modelo (trim_issue) e no card (make_cell), como sufixo ⧉ estritamente condicional ao dado"
  - "tracker_key(): a chave humana para exibição, sem jamais reescrever o dado"
  - "**Tracker:** por fase no ROADMAP, lido no mesmo laço de **Card:**/**Goal:**"
  - "a chave da fase ao lado do título na tabela PENDING PHASES, com orçamento reservado e piso de legibilidade"
  - "tests/cairn-tracker-card.bats: 19 testes, incluindo três camadas de tripwire de rede com controle negativo cada"
affects: [status, autonomous, sync-pull, adapters-jira, html-board]

actuals:
  tokens: 13073
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "sufixo condicional ao dado: sem o campo, os bytes de antes — provado pela suíte de invariância, não afirmado pelo plano"
    - "prova de ausência em duas fronteiras: socket dentro do processo, allowlist de PATH fora dele, cada uma com controle negativo"
    - "inventário estrutural por AST: pega o sítio novo no dia em que ele é escrito, não no dia em que ele roda"
    - "verificação por mutação com cópia de arquivo e restauro da cópia, nunca git checkout --"

key-files:
  created:
    - tests/cairn-tracker-card.bats
  modified:
    - cairn/scripts/cairn-status.py
    - cairn/docs/commands/status.md
    - tests/cairn-group-model.bats
    - .planning/phases/29-nothing-mechanical-stays-manual/deferred-items.md

key-decisions:
  - "gh-42 mantém o prefixo: cortar deixaria um `42` que não nomeia nada, e é a forma que o cairn-doctor --link-refs escreve em produção — desvio deliberado do plano, medido e escrito no docstring"
  - "A chave da fase RESERVA orçamento na coluna e trunca o título; a chave da issue CAI primeiro e preserva o título. Regras opostas porque as colunas são opostas"
  - "O tracker de fase não vira coluna nova: uma coluna imprime cabeçalho e células vazias em todo board e moveria os sete renders de referência"
  - "O inventário de subprocess resolve nomes POR ESCOPO de função — medido: resolver no módulo colapsava dois `cmd` diferentes e reportava a chamada do journal como `bd`"
  - "A varredura de largura afirma só sobre a GRADE de raias; o estouro do rodapé e da tabela é pré-existente, medido idêntico com e sem card, e foi para deferred-items.md"

patterns-established:
  - "Controle negativo por camada: uma camada que não falha quando deveria é decoração — as três têm o seu, e as três foram verificadas por mutação"
  - "ASSUMIDO escrito onde a prova acaba: o comportamento interno do bd está fora do alcance das três camadas, e o cabeçalho do teste diz isso"
  - "Literal de conjunto de chaves editado uma vez, com a intenção preservada em comentário, nunca afrouxado para subconjunto"

requirements-completed: [AUTO-03]

coverage:
  - id: D1
    description: "uma issue com external_ref mostra a chave do card no board humano, nas duas formas (com prefixo e sem) e nos dois glyph sets"
    requirement: AUTO-03
    verification:
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#an issue with an external_ref shows its tracker key on the board"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#a bare tracker key is shown exactly as stored"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#a gh-<number> ref keeps its prefix instead of degrading to a digit"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#the ascii board carries the card with an ascii glyph"
        status: pass
    human_judgment: false
  - id: D2
    description: "uma issue sem external_ref renderiza exatamente os bytes de antes, e os sete renders de referência da fase 20 não se movem"
    requirement: AUTO-03
    verification:
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#every unmarked card renders the bytes it rendered before the mark"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#the marked card line keeps its width — the suffix eats padding"
        status: pass
      - kind: integration
        ref: "bash cairn/scripts/cairn-test.sh tests/cairn-board-invariance.bats → 9/9, os sete renders byte a byte"
        status: pass
      - kind: integration
        ref: "git diff --quiet HEAD -- tests/fixtures/board-render/ → limpo, nenhuma referência regenerada"
        status: pass
    human_judgment: false
  - id: D3
    description: "--json carrega o dado cru, com prefixo e sem normalização, e null quando não existe"
    requirement: AUTO-03
    verification:
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#--json carries the external_ref raw, backend prefix and all"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#--json reports null for an issue with no external_ref"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#--json carries the phase tracker raw, prefix and all"
        status: pass
    human_judgment: false
  - id: D4
    description: "o sufixo entra na conta de largura e o título vence: nenhum card sai da raia, em nenhuma largura"
    requirement: AUTO-03
    verification:
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#no card is pushed out of its lane, at any width (11 larguras varridas)"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#when the lane is too narrow the card falls out and the title stays"
        status: pass
    human_judgment: false
  - id: D5
    description: "uma fase com **Tracker:** mostra seu card no painel; uma fase sem ele renderiza como hoje"
    requirement: AUTO-03
    verification:
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#a phase with a Tracker line shows its key beside the title"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#a phase without a Tracker line changes nothing on the board"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#a narrow panel drops the phase key and gives the title its column"
        status: pass
    human_judgment: false
  - id: D6
    description: "o render inteiro roda sob as duas fronteiras de tripwire, cada uma com seu controle negativo verde, e o inventário estrutural cobre a terceira"
    requirement: AUTO-03
    verification:
      - kind: integration
        ref: "tests/cairn-tracker-card.bats#the whole render runs under both tripwires and still prints the card"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#layer 1 is alive: an in-process socket raises under the same PYTHONPATH"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#layer 2 is alive exactly where layer 1 is blind"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#every subprocess.run in the renderer invokes an allowlisted binary"
        status: pass
      - kind: unit
        ref: "tests/cairn-tracker-card.bats#layer 3 is alive: a synthetic curl call site is rejected"
        status: pass
      - kind: other
        ref: "verificação por mutação: subprocess curl injetado → camadas 2 e 3 vermelhas; urllib in-process injetado → camada 1 vermelha; nenhum controle negativo se moveu"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-08-05
status: complete
---

# Fase 29 Plano 05: O card do rastreador, e a prova de que o board segue offline — Resumo

**O card externo aparece no board vindo de dois lugares que já eram locais — o `external_ref` do bd e uma linha `**Tracker:**` no ROADMAP — e a ausência de rede deixou de ser uma frase: três camadas de tripwire, cada uma com controle negativo próprio, e as duas fronteiras verificadas por mutação real do script.**

## Performance

- **Duração:** ~65 min
- **Tasks:** 2 de 2
- **Arquivos criados/modificados:** 5 (+885 / −20)
- **Suíte:** 157 anunciados, 157 executados, 157 verdes, 0 pulados — contado sobre o log inteiro (159 linhas), não sobre saída truncada

## Realizações

- **O card vem do dado, e só quando o dado existe.** `external_ref` entra em `trim_issue()` e vira um sufixo `⧉ CHAVE` em `make_cell()`, no mesmo mecanismo dos sufixos que já existiam. Sem o campo, o card renderiza os bytes de sempre — e quem afirma isso não é este plano, é a `tests/cairn-board-invariance.bats`, cujo fixture não carrega `external_ref` nenhum e continua batendo os sete renders de referência byte a byte.
- **A metade da fase do AUTO-03.** `**Tracker:**` é lido no **mesmo laço**, no mesmo `flush()`, na mesma passada única que já colhia `**Card:**` e `**Goal:**`. Nenhuma segunda leitura do arquivo.
- **A prova de ausência de rede, nas duas fronteiras.** O render inteiro roda sob um `sitecustomize` que estoura em `socket.connect` **e** sob um `PATH` de allowlist com `curl`/`wget` presentes e armadilhados. Sai 0, imprime os dois cards, e o registro de ferramentas de rede fica vazio.
- **A medição do plano, reproduzida offline.** O plano mediu que, com o tripwire de socket instalado, um `subprocess.run(['curl', …])` devolve 200 — o filho não herda o patch. Aqui isso virou o controle negativo da camada 2: sob **as duas** camadas armadas, o curl é alcançado, a camada 1 não levanta nada, e quem o registra é a camada 2. A mesma verdade, sem precisar da internet.
- **A camada que pega o defeito antes de ele rodar.** Um inventário por AST de todo `subprocess.run` do `cairn-status.py`: quatro sítios, dois `bd` e dois `sys.executable`, todos na allowlist. Um `curl` escrito no arquivo fica vermelho no dia em que é escrito, não no dia em que alguém renderiza um board com ele.
- **Verificação por mutação, porque verde é barato.** Injetei duas chamadas de rede reais no `cairn-status.py`, com cópia prévia do arquivo e restauro **da cópia** (nunca `git checkout --`). Um `subprocess.run(['curl', …])` no caminho do render deixou vermelhas as camadas 2 e 3 e verdes os três controles negativos. Um `urllib.request.urlopen` in-process deixou vermelha a camada 1 e verde a camada 3. É a demonstração de que as duas fronteiras cobrem coisas diferentes e que nenhuma das duas é dispensável.

## Commits por task

1. **Task 1 (tracer): o card vem do dado local e o render não se move** — `071f38b` (feat)
2. **Task 2: o tracker por fase, e a prova de ausência de rede** — `a0e6044` (feat)

O gate do tracer rodou na forma autônoma (`workflow.auto_advance: true` na config do projeto): o `<verify>` da Task 1 foi reexecutado ponta a ponta antes de qualquer trabalho de expansão e saiu 19/19, incluindo os sete renders.

## Arquivos criados/modificados

- `tests/cairn-tracker-card.bats` — 19 testes, cada um nomeando a quebra que guarda; cabeçalho declara MEDIDO versus ASSUMIDO das três camadas
- `cairn/scripts/cairn-status.py` — `tracker_key()`, `TRACKER_BACKEND_PREFIX`, `TRACKER_LABEL`, `TRACKER_TITLE_FLOOR`, `Style.g_card`; `external_ref` em `trim_issue()`, sufixo em `make_cell()`, `tracker` no dicionário da fase e na coluna `phase` do painel
- `cairn/docs/commands/status.md` — duas seções novas: *What the board reads from ROADMAP.md* (a gramática dos três rótulos) e *The board never touches the network* (a tabela das camadas, o medido e o assumido)
- `tests/cairn-group-model.bats` — literal de 22 para 23 chaves de `phases[]`, com a intenção preservada em comentário
- `deferred-items.md` — o estouro de largura pré-existente do rodapé e do painel, com a tabela de medição

## Decisões tomadas

**`gh-42` mantém o prefixo — desvio deliberado do plano.** O plano manda cortar `jira-` e `gh-` para exibição. Cortar `jira-DTP-142` para `DTP-142` está certo: sobra a chave que a pessoa cita. Cortar `gh-42` deixa `42`, um dígito nu ao lado de um id de issue num board de largura fixa, nomeando nada — e essa é justamente a forma que o `cairn-doctor.py --link-refs` escreve **em produção**, neste repositório. A regra implementada corta o prefixo só quando o que sobra ainda identifica a issue sozinho, o que um número puro não faz. Está no docstring do `tracker_key()` como desvio, com a medição, e virou teste nomeado.

**A chave da fase reserva orçamento; a chave da issue cai primeiro.** Regras opostas de propósito, e as duas medidas. Na raia, o sufixo compete com o título dentro de um card estreito e o título vence — é a regra que a fase 20 já escreveu ali. Na tabela `PENDING PHASES`, a coluna `phase` tem **8 células a `--width 100` e 50 a 140**: o título já é truncado em qualquer terminal comum, e um sufixo que só cabe quando sobra espaço apareceria acima de ~160 colunas e em lugar nenhum — uma feature que ninguém veria. Então lá a chave reserva as células dela e o título trunca em volta, com piso de 12 células de título; abaixo disso a chave cai e o título retoma a coluna inteira. Medido: aparece a partir de 120 colunas, some em 110.

**O tracker de fase não virou coluna.** Uma coluna nova imprime cabeçalho e célula vazia em **todo** board, inclusive nas fases que não têm tracker nenhum — e isso moveria os sete renders de referência. Ele anda dentro da coluna `phase`, ao lado do que já identifica a fase.

**O inventário de subprocess resolve nomes por escopo de função.** Primeira versão resolvia no módulo e reportava a chamada do `cairn-journal.py` como `bd`, porque dois `cmd` diferentes colapsavam num só. Um verde que nomeia o binário errado é pior que nenhum inventário. Está corrigido, e o motivo está escrito no docstring da função `scan()`.

**A varredura de largura afirma sobre a grade, e diz isso.** O rodapé e a tabela do painel estouram o `--width` hoje. Medido antes e depois de qualquer `external_ref`, com números idênticos — não é meu. Em vez de alargar o filtro do teste até ele passar sem dizer nada, o teste afirma sobre as linhas da grade (`┌ │ └ + |`), declara em comentário que essa é a fronteira dele, e aponta para o `deferred-items.md`.

## Desvios do plano

### 1. [Regra 1 — bug no plano] `gh-` na lista de prefixos cortados incondicionalmente

- **Encontrado em:** Task 1
- **Problema:** o plano lista `gh-` entre os prefixos de backend removidos para exibição. Aplicado literalmente, o `gh-42` que o `cairn-doctor.py --link-refs` escreve hoje neste repositório renderizaria como `42`.
- **Correção:** o prefixo sai só quando o resto ainda identifica a issue sozinho. `jira-DTP-142` → `DTP-142`; `gh-42` → `gh-42`. Documentado como desvio no docstring de `tracker_key()`, com a medição, e afirmado por `tests/cairn-tracker-card.bats#a gh-<number> ref keeps its prefix instead of degrading to a digit`.
- **Commit:** `071f38b`

### 2. [Regra 3 — bloqueante] `tests/cairn-group-model.bats` afirma o conjunto exaustivo de chaves de `phases[]`, e o plano não o listou

- **Encontrado em:** Task 2
- **Problema:** a Task 1 do plano manda procurar asserção exaustiva de chaves **por issue** (não existe) e a Task 2 acrescenta `tracker` ao dicionário da **fase** sem citar a `cairn-group-model.bats:439`, que afirma as 22 chaves de `phases[]`. O `<verify>` da Task 2 lista `cairn-status.bats` e `cairn-phase-model.bats`, mas não a `cairn-group-model.bats` — o bloco `<verification>` global do plano, sim.
- **Correção:** literal editado de 22 para 23 chaves, com a intenção preservada em comentário (contrato, nunca subconjunto), exatamente a disciplina que a Task 1 descreve para o caso das issues.
- **Verificação:** `tests/cairn-group-model.bats` 14/14 verde.
- **Commit:** `a0e6044`

### 3. [Regra 3 — bloqueante] O `python3` da máquina é um shim de gerenciador de versão

- **Encontrado em:** Task 2, montando a camada 2
- **Problema:** com um `PATH` contendo só a allowlist, o render saía **127** com `env: bash: No such file or directory`. Medido: `command -v python3` resolve para `~/.asdf/shims/python3`, um script bash que faz `exec asdf exec python3`. A allowlist estava testando o gerenciador de versão, não o renderizador.
- **Correção:** o stub `python3` aponta para o interpretador real (`sys.executable`), não para o que o `PATH` resolve. Motivo e medição escritos ao lado do código em `arm_tripwires()`.
- **Commit:** `a0e6044`

### 4. [Regra 1 — bug meu, pego por medição] A varredura de largura media a coisa errada

- **Encontrado em:** Task 1
- **Problema:** escrevi um teste afirmando que nenhuma linha do render passa do `--width`. Ficou vermelho — e a medição mostrou que ele reprovava um comportamento **pré-existente** (rodapé de 70 células, tabela de 85–90), idêntico antes e depois de qualquer `external_ref`. Um teste que reprova o que o plano não tocou é um teste que vai ser desligado por alguém, não um teste que protege.
- **Correção:** a asserção passou a ser sobre a grade de raias, que é o que um sufixo de card pode quebrar, com a fronteira declarada em comentário e o achado registrado em `deferred-items.md`. O board **não** foi consertado: está fora do escopo.
- **Commit:** `071f38b`

## O que eu recusei fazer, e por quê

**Não rodei nenhuma ferramenta de escrituração do gsd-tools.** Nada de `roadmap.update-plan-progress`, `requirements.mark-complete`, `state.record-metric`, `state.update-progress` ou `phase.complete`. Medido no fecho do plano anterior: o `_normalizeMd` do `gsd-tools` injetou 29 linhas em branco no `.planning/ROADMAP.md` (`+43/−7` para marcar cinco checkboxes) — é a medição 1 da decisão D-01 do `29-CONTEXT.md` se reproduzindo dentro da fase que existe para removê-la, registrada em `CairnGo-66o`. Além disso, mexer no ROADMAP/REQUIREMENTS/STATE apagaria a prova de aceitação do 29-07, que reprova o `req-ledger` **de propósito** (D-02 congelou essa discordância). O fechamento da fase 29 é do operador, com `cairn-bookkeep.sh close 29 --apply`.

Verificado ao final: `git diff --quiet HEAD -- .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/STATE.md` sai limpo.

**Não regenerei nenhuma referência de render.** `git diff --quiet HEAD -- tests/fixtures/board-render/` sai limpo. Os sete renders passaram sem toque porque o sufixo é condicional ao dado e o fixture não tem `external_ref` — que é o desenho, não sorte.

**Não consertei os dois defeitos que o doctor reprova.** `phase-corroboration` (FIX-05, fase 25) e `req-ledger` (a checagem do 29-07, reprovando de propósito). O rodapé do doctor segue **`12 ok, 4 warning(s), 2 failure(s)`**, idêntico ao medido antes deste plano.

**Não consertei o estouro de largura do rodapé e do painel.** Pré-existente, medido idêntico com e sem card, fora do alcance de qualquer mudança deste plano, e decidir o que um rodapé de 70 células faz numa janela de 40 é decisão de produto sobre três renderizadores que este plano não abre. Foi para `deferred-items.md` com a tabela de medição.

**Não implementei nem esbocei busca ao vivo.** Nem `--fetch`, nem placeholder. Está diferido por escrito no `29-CONTEXT.md`, e este plano existe para tornar essa ausência *provada* em vez de prometida.

## O que ficou ASSUMIDO

O comportamento interno do `bd` não é alcançável por nenhuma das três camadas: é um binário Go de terceiro, sentado na allowlist justamente porque o board precisa dele. O que está **provado** é que *este script* não abre socket e não invoca ferramenta de rede, nem no próprio processo nem nos filhos que ele inicia. O que **não** está é o que o `bd` faz dentro do processo dele. Isso está escrito no cabeçalho do `tests/cairn-tracker-card.bats` e na seção nova do `cairn/docs/commands/status.md`, com a fronteira nomeada — nenhum teste deste arquivo finge o contrário.

## Prontidão para a próxima fase

O `AUTO-03` fecha aqui: um card associado a uma fase **ou** a uma issue aparece no board sem chamada de rede no caminho padrão, o vínculo mora no `external_ref` do bd e no roadmap, e o board offline continua offline com prova executável.

Quando o backend do 29-04 começar a preencher `external_ref` de verdade, nada aqui precisa mudar: o sufixo aparece sozinho. Se alguém for implementar a busca ao vivo diferida, as três camadas ficam vermelhas — que é exatamente o momento em que a conversa sobre `--fetch` deve acontecer, e não depois.

## Self-Check: PASSED

Arquivos afirmados, todos presentes em disco: `tests/cairn-tracker-card.bats`, `cairn/scripts/cairn-status.py`, `cairn/docs/commands/status.md`, `tests/cairn-group-model.bats`, `29-05-SUMMARY.md`, `deferred-items.md`.

Commits afirmados, ambos no histórico: `071f38b`, `a0e6044`. Nenhum arquivo apagado por eles.

`git diff --quiet HEAD -- .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/STATE.md` → limpo.
`git diff --quiet HEAD -- tests/fixtures/board-render/` → limpo.

Nenhum stub, nenhum teste pulado, nenhum `<verify>` deixado sem rodar.
