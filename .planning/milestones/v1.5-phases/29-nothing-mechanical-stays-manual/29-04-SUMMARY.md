---
phase: 29-nothing-mechanical-stays-manual
plan: "04"
subsystem: infra
tags: [jira, deteccao, mcp, sync, gbsync, bats, stdlib]

requires:
  - phase: 29-03
    provides: ".cairn/config.json com schema fechado e dono único (cairn-config.py), onde a resposta da pergunta passa a morar"
provides:
  - "detect_jira com três guardas: denylist do histórico, sinal fraco que não decide sozinho, e o sinal mcp declarado"
  - "cairn-jira.py/.sh: a decisão de perguntar, a gravação do sim e a gravação do não"
  - "amostras de evidência (branches e assuntos de commit) no payload do detector"
  - "chave jira.link no schema do cairn-config.py, com leitor nomeado"
  - "/cairn:sync-config abrindo pela detecção, com quatro rotas amarradas a reason literal"
affects: [sync-config, migrate, init, gbsync, adapters-jira]

actuals:
  tokens: 18678
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "detector único consumido por subprocess (formato defensivo do fetch_lease_status)"
    - "medido versus assumido registrado no docstring, com o assumido fora do predicado"
    - "HOME fixado em teste quando o predicado lê arquivo do home do usuário"

key-files:
  created:
    - cairn/scripts/cairn-jira.py
    - cairn/scripts/cairn-jira.sh
    - tests/cairn-jira.bats
  modified:
    - cairn/scripts/cairn-migrate.py
    - cairn/scripts/cairn-config.py
    - cairn/commands/sync-config.md
    - cairn/commands/help.md
    - cairn/docs/commands/sync-config.md
    - tests/cairn-migrate.bats
    - tests/cairn-config.bats

key-decisions:
  - "A denylist sai do REQUIREMENTS.md ativo MAIS .planning/milestones/*REQUIREMENTS.md, por regex crua e não por parse_requirements_md — medido: 27 prefixos, zero sobreviventes"
  - "git-log sozinho nunca liga detected (21/21 falsos positivos); branch liga sozinho (0 em 25)"
  - ".claudeAiMcpEverConnected fica fora do predicado e marcado como ASSUMIDO — não foi medido se significa 'agora' ou 'alguma vez'"
  - "jira.link entra no schema fechado do cairn-config.py em vez de ser gravado por fora: um dono por arquivo"
  - "apply recusa gravar quando não consegue derivar base_url, em vez de escrever placeholder"
  - "reason 'signal found, no key to confirm' nomeia o único caso em que confirmar é impossível"

patterns-established:
  - "Detector único: cairn-jira.py invoca cairn-migrate.py detect --json e não re-deriva nada; um teste prova pelo avesso (sem o detector, exit 5)"
  - "Amostra como evidência: o payload carrega até três branches e três assuntos de commit por prefixo, para a pergunta mostrar em vez de decretar"
  - "Override documentado: literal de teste movido com o motivo escrito ao lado, intenção preservada"

requirements-completed: [AUTO-02]

coverage:
  - id: D1
    description: "detect_jira devolve detected:false neste repositório, contra o true com nove prefixos de requisito local reproduzido no planejamento"
    requirement: AUTO-02
    verification:
      - kind: integration
        ref: "python3 cairn/scripts/cairn-migrate.py detect --json → external.jira.detected == false, prefixes == []"
        status: pass
      - kind: unit
        ref: "tests/cairn-migrate.bats#detect denylists requirement prefixes from ARCHIVED milestones too"
        status: pass
      - kind: unit
        ref: "tests/cairn-migrate.bats#a key only in commit messages is reported but never detects"
        status: pass
      - kind: unit
        ref: "tests/cairn-migrate.bats#the same key in a branch name is the signal that does detect"
        status: pass
    human_judgment: false
  - id: D2
    description: "cairn-jira decide se pergunta com base em sinal e em resposta anterior; um projeto sem sinal nunca é perguntado"
    requirement: AUTO-02
    verification:
      - kind: unit
        ref: "tests/cairn-jira.bats#a repo with no signal at all is never asked"
        status: pass
      - kind: unit
        ref: "tests/cairn-jira.bats#a recorded no is as durable as a yes — the question does not come back"
        status: pass
    human_judgment: false
  - id: D3
    description: "apply grava o backend jira com o conjunto exato de campos e NOMES de variável de ambiente, nunca credencial"
    requirement: AUTO-02
    verification:
      - kind: unit
        ref: "tests/cairn-jira.bats#apply writes the jira backend with env var NAMES and no credential"
        status: pass
      - kind: unit
        ref: "tests/cairn-jira.bats#apply preserves another backend already configured in sync.json"
        status: pass
      - kind: integration
        ref: "bash cairn/scripts/cairn-test.sh tests/gbsync.bats — o arquivo que apply escreve é o que o gbsync lê"
        status: pass
    human_judgment: false
  - id: D4
    description: "MCP entra como DECLARADO em arquivo e nunca como conectado"
    requirement: AUTO-02
    verification:
      - kind: unit
        ref: "tests/cairn-jira.bats#claudeAiMcpEverConnected alone is NOT a declaration"
        status: pass
      - kind: unit
        ref: "tests/cairn-jira.bats#an Atlassian MCP server DECLARED in .mcp.json is a signal"
        status: pass
      - kind: unit
        ref: "tests/cairn-jira.bats#a malformed .mcp.json degrades to 'not declared', never a crash"
        status: pass
    human_judgment: false
  - id: D5
    description: "/cairn:sync-config mostra o que achou, pergunta uma vez e grava a partir do sim, sem ninguém digitar chave, projeto ou credencial"
    requirement: AUTO-02
    verification:
      - kind: unit
        ref: "tests/cairn-jira.bats#the three routes are distinguishable by reason, and the command names them"
        status: pass
    human_judgment: true
    rationale: "AskUserQuestion não roda em bats. O teste prova que os três reason são distintos e que a prosa nomeia cada rota e cada invocação; ele não prova — e diz isso em comentário — que o usuário é mostrado a evidência, perguntado uma vez e perguntado bem. Essa camada é conversa e precisa de olho humano."

duration: 50min
completed: 2026-08-05
status: complete
---

# Fase 29 Plano 04: Jira detectado, confirmado, então configurado — Resumo

**O detector parou de chamar id de requisito do próprio cairn de "projeto Jira": neste repositório ele saiu de `detected: true` com nove prefixos para `detected: false` com zero, e um par novo (`cairn-jira.py`/`.sh`) passou a decidir se pergunta e a gravar as duas respostas com a mesma durabilidade.**

## Performance

- **Duração:** ~50 min (execução 35 min; a suíte completa levou ~25 min em paralelo)
- **Tasks:** 3 de 3
- **Arquivos criados/modificados:** 10 (+1354 / −62)

## Realizações

- **A medição de aceitação virou.** Antes: `detect --json` devolvia `detected: true`, `prefixes: ["JOUR","ESC","PAR","CARD","GSD","FAIR","REL","HARN","LEASE"]`, `signals: ["git-log"]`. Depois: `{"detected":false,"prefixes":[],"signals":[]}`. Nenhum desses nove era Jira; todos eram ids de requisito do cairn/GSD, e era o `JOUR` que entraria pré-preenchido como `project_key` na ferramenta de outra pessoa.
- **Três guardas, cada uma com a medição ao lado do código.** Denylist do histórico (27 prefixos, zero sobreviventes), sinal fraco (`git-log` sozinho nunca decide), e o `mcp` declarado.
- **Um detector só, provado pelo avesso.** `cairn-jira.py` consome `cairn-migrate.py detect --json` por subprocess. Um teste copia o par para um diretório sem o detector e exige exit 5 — se este script ganhasse regex próprio, o teste ficaria verde enquanto os dois começavam a discordar sobre o mesmo repo.
- **O não tem a mesma força do sim.** Ambos gravados em `jira.link`, no arquivo que o `cairn-config.py` já possuía.
- **Nenhuma credencial é gravável.** O conjunto de campos escritos é afirmado por teste, e não existe ali campo que pudesse conter um segredo.

## Commits por task

1. **Task 1 (tracer): o detector para de mentir** — `d1d21c9` (fix)
2. **Task 2: o MCP declarado, e a decisão de perguntar** — `0f969c6` (feat)
3. **Task 3: mostra, pergunta uma vez, grava a partir do sim** — `3a5e241` (docs)

## Arquivos criados/modificados

- `cairn/scripts/cairn-jira.py` — a decisão de perguntar e as duas gravações; docstring canônico com medido versus assumido
- `cairn/scripts/cairn-jira.sh` — wrapper fino do par
- `tests/cairn-jira.bats` — 14 testes, cada um nomeando a quebra que guarda
- `cairn/scripts/cairn-migrate.py` — `requirement_prefixes`, `read_json_file`, `mcp_server_maps`, `detect_mcp_atlassian`, `detect_jira` reescrito com amostras e `site`
- `cairn/scripts/cairn-config.py` — chave `jira.link` no schema fechado, com leitor nomeado
- `cairn/commands/sync-config.md` — abre pela detecção; quatro rotas amarradas a `reason` literal
- `cairn/commands/help.md` — a linha do `/cairn:sync-config` diz o que ele agora faz sozinho
- `cairn/docs/commands/sync-config.md` — espelho de referência, atualizado junto
- `tests/cairn-migrate.bats` — 3 testes novos (23 no total)
- `tests/cairn-config.bats` — literal de cinco para seis chaves, com override documentado

## Decisões tomadas

**A denylist é regex crua, não `parse_requirements_md`.** Medido: o `REQ_ITEM` daquele parser só casa `- **ID**: título`, e os arquivos v1.2/v1.3 escrevem `### GSD-01:`. Com o parser, `GSD` sobrevive à exclusão e o detector continua mentindo. Efeito colateral documentado em comentário: `ABC` entra na denylist porque `ABC-123` aparece na prosa dos requisitos como exemplo de formato. Sobre-excluir é a direção segura de errar.

**`git-log` é o único sinal fraco; `branches` não é.** As duas medições estão no comentário ao lado do predicado: 21/21 falsos positivos em mensagem de commit, 0 matches em 25 branches. Por isso a guarda nomeia `git-log` em vez de exigir dois sinais quaisquer — um branch sozinho basta.

**`.claudeAiMcpEverConnected` fica fora do predicado.** Medido nesta máquina: `mcpServers` tem quatro servidores e nenhum é Atlassian, enquanto o conector Rovo está ativo. O único rastro em arquivo é essa lista, e o nome dela sugere "alguma vez" — mas sugestão não é medição. Fica ASSUMIDO no docstring e um teste exige `declared:false` quando é o único rastro.

**`apply` recusa em vez de inventar.** `base_url` só é derivável sem perguntar quando um remote nomeia um host `*.atlassian.net`. Sem isso, exit 2 e nada gravado — um backend com base_url de mentira falha no push com um erro que ninguém lê.

## Desvios do plano

### 1. [Regra 3 — bloqueante] O plano mandava gravar em `.cairn/config.json` sem notar que o arquivo tem schema fechado

- **Encontrado em:** Task 2
- **Problema:** o plano diz "registra a resposta `yes` em `.cairn/config.json` (o arquivo do plano 29-03)". Mas o 29-03 deu a esse arquivo um **schema fechado** com regra de entrada ("nenhuma chave sem leitor") e `tests/cairn-config.bats:167` afirma o **conjunto exato** de chaves. Gravar por fora do schema faria do `cairn-jira.py` um segundo dono do arquivo, e a chave ficaria invisível ao `list` — que é exatamente a doença ("nada lista o conjunto") que o 29-03 existe para curar. `cairn-config.py` e `tests/cairn-config.bats` não estavam em `files_modified`.
- **Correção:** `jira.link` (`unset|yes|no`, default `unset`) entrou no schema com o leitor nomeado — `cairn-jira.py detect` —, e o `cairn-jira.py` escreve e lê **através** do `cairn-config.py` por subprocess. A regra de entrada foi satisfeita, não dobrada: o leitor chega no mesmo ciclo, que é o critério que o próprio docstring do 29-03 define. O literal do teste foi movido de cinco para seis chaves com o motivo escrito ao lado, preservando a intenção (uma chave não pode entrar despercebida).
- **Verificação:** `tests/cairn-config.bats` 16/16 verde.
- **Commit:** `0f969c6`

### 2. [Regra 2 — funcionalidade crítica ausente] O quarto estado: sinal sem chave para confirmar

- **Encontrado em:** Task 2, escrevendo o teste do `.mcp.json`
- **Problema:** o plano previa três estados (`no signal` / `already answered` / `ask`). Existe um quarto, e ele apareceu como caso real de teste: servidor Atlassian **declarado** num repo cuja história não nomeia chave nenhuma. Há sinal, então `ask` é `true` — mas `prefixes` está vazio, e a pergunta "confirme a chave" não teria o que oferecer. Cair no ramo genérico faria o comando pedir que alguém **digitasse** a chave sem dizer que estava fazendo isso, que é o pecado que a fase corrige.
- **Correção:** `reason: "signal found, no key to confirm"`, e o comando diz em voz alta que este é o único caso em que vincular exige digitar a chave, porque não há o que confirmar.
- **Verificação:** `tests/cairn-jira.bats#an Atlassian MCP server DECLARED in .mcp.json is a signal`.
- **Commit:** `0f969c6`

### 3. [Regra 2] O `mcp` chegou no commit da Task 1, e não no da Task 2

- **Problema:** o plano põe o sinal `mcp` na Task 2, mas ele vive **dentro** do mesmo `detect_jira` e do mesmo predicado `detected` que a Task 1 reescreve. Separar exigiria escrever a função duas vezes.
- **Correção:** o sinal foi junto no `d1d21c9`, dito na mensagem do commit. Os testes do `mcp` continuaram na Task 2, pela superfície certa (`cairn-jira.bats`), como o plano planejou.

### 4. [Regra 2] `cairn/docs/commands/sync-config.md`, fora do conjunto do plano

- **Problema:** o espelho de referência descrevia o passo 3 antigo — "pré-preenche `project_key` com o prefixo mais frequente". Essa frase é a descrição literal do defeito que este plano conserta.
- **Correção:** atualizado junto, com as quatro rotas.
- **Commit:** `3a5e241`

### 5. [Regra 2] `site` derivado do remote entrou no detector, não no consumidor

- **Problema:** o `apply` precisa de `base_url`, e a única fonte derivável é um remote `*.atlassian.net`. Derivar isso dentro do `cairn-jira.py` significaria um segundo script lendo git sobre o mesmo repo.
- **Correção:** `detect_jira` passou a reportar `site`; o `cairn-jira.py` só lê. Toda leitura de git segue num script só.

### 6. [Correção de asserção minha, não do código] Ordem das amostras de commit

- Escrevi a asserção esperando `commits[0]` == o commit mais antigo. `git log` é do mais recente para o mais antigo. **O código estava certo e o teste errado** — corrigi o teste e documentei que a ordem é a do `git log`, porque "mais recente primeiro" é o lado útil para "este repo usa Jira hoje".

---

**Total de desvios:** 6 (1 bloqueante, 4 de funcionalidade crítica, 1 correção de asserção própria)
**Impacto no plano:** nenhum aumento de escopo. Os desvios 1 e 2 são pré-requisitos de correção que o plano não tinha medido; os demais são coerência de propriedade (um dono por arquivo, um leitor de git) e documentação que contradizia o comportamento.

## Problemas encontrados

**A hermeticidade dos testes ficou dependente do `$HOME` de quem roda.** O sinal `mcp` lê `~/.claude.json`. Um contribuidor com servidor Atlassian declarado veria testes sobre outra coisa mudarem de resultado. Resolvido fixando `HOME` num diretório vazio em todo teste novo — em `tests/cairn-jira.bats` via `setup()`, e em `tests/cairn-migrate.bats` via `run env HOME=…`, seguindo o estilo que o próprio arquivo já usava para `JIRA_SITE`.

**A ferramenta de estado do GSD escreveu `current_phase: 18` no `STATE.md`.**
Ao rodar `state.update-progress` no fecho deste plano, o `current_phase` foi de
`29` para `18` — com `current_phase_name` continuando "Nothing mechanical stays
manual", que é a 29. A causa provável está à vista no mesmo arquivo: a seção
`## Current Position` ainda diz "Phase: 18 — Parallel phase execution" e
"Milestone v1.4", texto defasado que o `cairn-doctor` já reprova como
`state-narrative-stale` e que pertence a outro dono. A ferramenta leu a prosa
velha e sobrescreveu o frontmatter certo com ela.

Corrigi as três coisas que este fecho estragou — `current_phase` de volta para
`29`, as quatro decisões que entraram como `[Phase ?]` para `[Phase 29]`, e um
cabeçalho de tabela duplicado que o `record-metric` inseriu no meio da tabela
existente de métricas. **Não** mexi na prosa defasada da `## Current Position`:
ela é anterior a este plano, tem dono declarado e mexer nela seria escopo alheio.
Fica anotada em `deferred-items.md`.

Vale dizer também: `requirements.mark-complete` respondeu
`"write_set_complete": true` — o mesmo literal que esta fase já mediu como verde
falso. Não confiei nele; li o diff, e desta vez ele estava certo (`AUTO-02`
marcado, uma linha).

## O que foi recusado

- **Não escrevi placeholder de `base_url`.** Um backend habilitado com site falso passa no teste e falha no push.
- **Não tratei `.claudeAiMcpEverConnected` como estado de conexão**, mesmo com o nome sugerindo histórico e mesmo sendo o único rastro do conector ativo aqui. Sugestão do nome não é medição.
- **Não consertei `phase-corroboration` (FIX-05, fase 25) nem `req-ledger` (29-07).** As duas continuam reprovando de propósito; o `cairn-doctor` segue em exit 7 com o rodapé idêntico ao de antes deste plano.
- **Não afirmei prova sobre a camada de conversa.** `AskUserQuestion` não roda em bats; o teste diz em comentário o que prova e o que não prova, em vez de fingir verde.

## Medições literais

```
$ python3 cairn/scripts/cairn-migrate.py detect --json | jq -c '.external.jira | {detected, prefixes, signals}'
{"detected":false,"prefixes":[],"signals":[]}

$ bash cairn/scripts/cairn-jira.sh detect --json | jq -c '{ask, reason, already}'
{"ask":false,"reason":"no signal","already":"unset"}

$ bash cairn/scripts/cairn-test.sh tests/cairn-migrate.bats tests/cairn-jira.bats tests/gbsync.bats
EXIT=0 · anunciado 1..51 · ok 51 · not ok 0

$ bash cairn/scripts/cairn-test.sh              # suíte inteira
EXIT=0 · anunciado 1..680 · ok 680 · not ok 0 · skip 1
  (o único skip é pré-existente: o validador do gsd-core, ausente sem checkout local)

$ bash cairn/scripts/cairn-doctor.sh
EXIT=7 · 12 ok, 4 warning(s), 2 failure(s)     # idêntico ao estado antes deste plano
```

## Prontidão para a próxima fase

O `29-05` é o único plano restante da fase 29. Nada aqui bloqueia: os arquivos deste plano não se cruzam com os dele, e as duas reprovações do doctor continuam sendo as mesmas duas de antes, ambas de outros donos.

Uma coisa fica anotada para quem tocar em `.cairn/config.json` a seguir: o schema agora tem **seis** chaves, e o teste que afirma o conjunto exato ficou com a razão do sexto escrita ao lado. Um sétimo continua tendo de chegar com leitor.

## Self-Check: PASSED

Os 10 arquivos afirmados existem em disco; os 3 commits (`d1d21c9`, `0f969c6`,
`3a5e241`) existem no histórico; `tests/cairn-jira.bats` tem 14 `@test` e
`tests/cairn-migrate.bats` tem 23, os números citados acima. Nada faltando.

---
*Fase: 29-nothing-mechanical-stays-manual*
*Concluído: 2026-08-05*
