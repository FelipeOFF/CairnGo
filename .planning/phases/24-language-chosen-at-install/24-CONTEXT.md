# Phase 24: Language chosen at install - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A linguagem de resposta deixa de ser algo que alguém descobre no meio de um ciclo.

Requisitos: LANG-01, LANG-02. Issues bd: ver `24-BEADS-MAP.md`.

Dentro do escopo: onde a escolha é feita (instalação), onde ela é gravada, e o
caminho mecânico que a leva até **cada** subagente que o lifecycle spawna.

Fora do escopo: traduzir a base de código. Comentários, docstrings e nomes de
`cairn/` seguem em inglês — esta fase decide como a escolha do usuário viaja, não
em que língua o código é escrito.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo. Toda decisão abaixo é Claude's Discretion e está
registrada por escrito. Nenhuma é palpite: cada uma cita a medição que a produziu,
e onde algo **não** foi medido está dito que não foi.

### O defeito, e por que "a chave está no arquivo" não prova nada

- **D-00: o ponto de entrega é o prompt do subagente, não o `config.json`.**

  O defeito é real e observado neste ciclo: subagentes spawnados pelo lifecycle
  responderam em inglês num projeto cujo planejamento inteiro é PT-BR. E — isto é
  o que torna o critério do LANG-02 literal em vez de retórico — **isso aconteceu
  com a chave presente e correta**. Medido: `.planning/config.json:69` já diz
  `"response_language": "pt-BR"` neste repositório. Um teste que afirmasse "a
  chave está no `.json`" estaria **verde no exato estado em que o defeito
  ocorreu**. Por isso ele não é aceito como prova aqui.

  A causa está no que o GSD diz aos seus próprios workflows. Medido em
  ~30 arquivos de `~/.claude/gsd-core/workflows/*.md`, a diretiva padrão é:

  > "Technical terms, code, file paths, **and subagent prompts stay in English**
  > — only user-facing output is translated."

  Um único arquivo diz o contrário — `references/execute-phase-response-language.md`
  (#2402): *"Pass `response_language: {value}` into every spawned subagent prompt"*.
  Ou seja: na maioria dos pontos de spawn do GSD a regra escrita é **não** repassar.
  O valor existia; o repasse não. É exatamente a classe de defeito que este
  projeto existe para remover — uma promessa em prosa que nenhum mecanismo cumpre.

### O inventário completo de quem spawna, medido e não presumido

- **D-01: o lifecycle tem dois pontos de spawn próprios do cairn, e nenhum a mais.**

  Medido por `grep -rln "subagent\|[Ss]pawn" cairn/commands/ cairn/skills/
  cairn/capability/fragments/` — o resultado é exatamente dois arquivos:

  | ponto | quem nasce | como o prompt é montado |
  |---|---|---|
  | `cairn/commands/autonomous.md` passo 3 | um agente por fase preparada | dos campos de `cairn-parallel.py prepare --json`, dentro do bloco delimitado `SUBAGENT-PROMPT-BEGIN/END` |
  | `cairn/commands/reconcile.md` passo 3 | `reconcile-investigator` (Task tool) | prosa do passo 3 + o caminho do bundle de evidências |

  `work.md`, `plan.md`, `verify.md`, `milestone.md`, `ship.md` e `quick.md` não
  spawnam nada: delegam a `/gsd:*`, e o subagente que nasce ali é do GSD, lendo
  `.planning/config.json:response_language` pelo caminho do próprio GSD.

  Portanto "todo subagente spawnado pelo lifecycle" tem duas metades, e **as duas
  precisam ser fechadas** para a afirmação do LANG-02 ser literal:

  1. os dois pontos do cairn — fechados por esta fase, com teste no payload;
  2. os pontos do GSD — fechados garantindo que `.planning/config.json:response_language`
     **esteja setado**, que é a metade que o LANG-01 entrega.

  O `reconcile-investigator` conta: seu grant é `Read, Grep, Glob` e sua mensagem
  final é prosa citada que um humano lê ("propose — in plain, cited language",
  `cairn/agents/reconcile-investigator.md`). Não é um agente que devolve só JSON.

### Onde a resposta é gravada: três medições derrubam a decisão anterior

- **D-02: a resposta do instalador é gravada em `.cairn/config.json`, chave
  `agents.response_language`, default `"English"`.**

  Isto **corrige uma decisão registrada** e a correção fica escrita em vez de a
  frase antiga sumir. `bd show CairnGo-0rk` carrega, no campo DESIGN:

  > DECIDIDO (Felipe, 2026-07-30): reusar `response_language` do config do GSD,
  > **não criar chave de lingua em `.cairn/config.json`**.

  A intenção dessa decisão — *uma pergunta, um dono, não inventar um segundo lugar
  onde a mesma resposta mora* — continua de pé e é honrada por D-03. O que muda é
  o **onde**, e muda por três medições feitas agora, todas depois daquela data:

  **M-1 — `gsd-tools query config-set response_language` CRIA `.planning/`.**
  Repositório sem `.planning/` algum:
  ```
  $ node ~/.claude/gsd-core/bin/gsd-tools.cjs query config-set response_language "Portuguese"
  {"updated": true, "key": "response_language", "value": "Portuguese"}   # rc=0
  $ ls -a          # .planning/ passou a existir, contendo só config.json
  ```

  **M-2 — um `.planning/` com só `config.json` faz o `detect` mentir.**
  ```
  $ bash cairn/scripts/cairn-migrate.sh detect
  A
  .planning present, .beads absent -> GSD-only backfill (plan --mode A)
  $ rm -rf .planning && bash cairn/scripts/cairn-migrate.sh detect
  D
  neither present -> greenfield (/gsd:new-project, then /cairn:init)
  ```
  `classify()` (`cairn-migrate.py:725-728`) decide por `planning.is_dir()`, nada
  mais. E `cairn/commands/init.md:20-22` manda o estado A **parar o init** e
  desviar para `/cairn:migrate`. Ou seja: se o `/cairn:init` gravasse a chave do
  GSD na hora de perguntar, ele reclassificaria de D para A o repositório que ele
  mesmo acabou de tocar, e uma segunda execução se recusaria a continuar. O hook
  de `session-start.sh:53-57` passaria a imprimir o nudge de migração pelo mesmo
  motivo.

  **M-3 — o init é proibido de criar `.planning/`, por escrito.**
  `cairn/commands/init.md:153`: *"`.planning/` is created by GSD, not by cairn — do
  NOT create it yourself."*

  Consequência: no instante em que o `/cairn:init` pergunta, `.planning/` **não
  existe e não pode ser criado**. O único lugar gravável e correto é
  `.cairn/config.json`, que a fase 29 acabou de entregar com schema fechado e
  leitor nomeado por chave.

  Perguntar depois — só quando `.planning/` já existir — foi considerado e
  rejeitado com razão medida: o `/gsd:new-project` **spawna os próprios
  subagentes** (researcher, synthesizer, roadmapper). Perguntar depois dele é
  perguntar depois de os primeiros subagentes do projeto já terem respondido na
  língua errada, que é literalmente o defeito que o LANG-01 existe para impedir.
  "Chosen at install" quer dizer *antes do primeiro subagente*.

- **D-03: a chave do cairn é subordinada, não paralela — `.planning/config.json`
  vence sempre que estiver setada.**

  Isto é o que impede o segundo caso do defeito que o próprio `cairn-config.py`
  documenta ("One fact, one owner… Storing the same thing in both is where the
  next disagreement starts"). A resolução é uma só, escrita e testada:

  ```
  .planning/config.json : response_language   (setado)     -> source "planning"
  .cairn/config.json    : agents.response_language (setado) -> source "file"
  "English"                                                 -> source "default"
  ```

  A chave do GSD vence porque é lida por ~30 workflows do GSD **e** pelo cairn; a
  do cairn é lida por um resolvedor só. Se as duas divergirem, honrar a mais
  estreita faria os subagentes do cairn responderem numa língua e os do GSD em
  outra **na mesma execução** — que é a divergência, não a solução. E `get --json`
  devolve `source`, então qual das duas governa nunca é adivinhação.

  A chave do cairn **é lida de verdade**, e o estado em que ela governa é o estado
  real da instalação: greenfield, `.planning/` ainda inexistente. Não é uma chave
  decorativa — é a regra de entrada do `cairn-config.py` sendo cumprida, não
  dobrada.

- **D-04: `set agents.response_language` propaga para `.planning/config.json`
  quando esse arquivo JÁ existe, e nunca o cria.**

  Mecanismo em vez de prosa. O defeito original foi "a prosa mandava repassar e
  ninguém repassou"; consertá-lo com mais uma frase de prosa seria repetir a
  causa. Escrever a chave do GSD é o que fecha a metade GSD do D-01, e a condição
  "só se o arquivo já existir" é exatamente M-1/M-2/M-3 respeitadas: propagar
  jamais pode inventar `.planning/`.

  No fluxo greenfield isso significa: o `set` na hora de perguntar não propaga
  (não há para onde), e o mesmo `set`, re-executado depois do hand-off para
  `/gsd:new-project`, propaga. Idempotente por construção — mesmo comando, mesmo
  valor. O `cairn-doctor` ganha a rede que pega o passo pulado (D-06).

### O que o teste do LANG-02 lê, e o que ele honestamente não prova

- **D-05: a prova tem duas metades, e o limite de cada uma está escrito.**

  **Metade mecânica (a forte):** `cairn-parallel.py prepare --json` passa a
  carregar `response_language` e `response_language_source` no payload. Esse
  payload é, medido, o que o montador do prompt lê — `autonomous.md:159` diz
  "prints `worktree`, `branch`, `base_commit`, the resulting `lease.holder` and
  `planning_files_forbidden`", e os cinco itens do bloco do prompt saem dali. O
  teste roda `prepare` numa fixture e lê o valor **na saída do script**, não na
  config. Fica vermelho de três formas independentes: se a chave sumir do schema,
  se o `prepare` parar de resolver, ou se o resolvedor trocar a precedência.

  **Metade de prosa (a que o repositório já sabe testar):** o bloco delimitado por
  `SUBAGENT-PROMPT-BEGIN/END` ganha um sexto item, e o teste assere sobre a
  **região**, não sobre o arquivo. Este é o mecanismo que a fase 18-04 já
  estabeleceu exatamente para isto: *"marcadores de região em markdown para que 'o
  prompt diz X' seja afirmação sobre o prompt, não sobre o arquivo"*
  (`18-04-SUMMARY.md:23`), e `tests/cairn-parallel-autonomous.bats:139-147` já o
  exercita para os três arquivos proibidos.

  **O que NÃO é provado, dito antes que alguém pergunte:** que o modelo de fato
  cole o item no prompt do Task tool. `bats` não spawna o Task tool — a mesma
  limitação que `reconcile.md:29-31` já registra por escrito ("bats cannot spawn
  the Task tool to prove a live run"). Nenhum teste desta fase vai afirmar isso, e
  o SUMMARY vai repetir o limite em vez de deixá-lo implícito.

- **D-06: `cairn-doctor` ganha um check `response-language`.**

  A rede da propagação. Warn quando `.cairn/` tem resposta gravada e
  `.planning/config.json` existe com a chave **ausente** (propagação nunca
  aconteceu) ou com valor **diferente** (alguém editou um dos dois à mão).
  Nomeia o comando exato que fecha. Não é fail: divergir não quebra nada
  mecanicamente, só faz metade dos subagentes responder na língua errada — que é
  precisamente o que ninguém percebeu da última vez, e por isso merece uma linha
  no relatório de saúde em vez de silêncio.

### Detalhes de forma, decididos para não virarem discussão no plano

- **D-07: tipo `str`, validado, e a contagem do teste de chaves sobe de 6 para 7.**

  `cairn-config.py` hoje conhece `int`, `int_or_null`, `bool` e `enum`. Língua não
  é enum — `references/planning-config.md:238` diz "Any language name". Entra um
  tipo `str` com validação explícita (não-vazio depois de `strip`, uma linha só,
  ≤ 40 caracteres), e a garantia existente segue valendo: valor rejeitado sai com
  3 e **deixa o arquivo exatamente como estava**.

  `tests/cairn-config.bats:167` afirma o conjunto exato de chaves e diz "six" no
  título. Sobe para sete, com o motivo escrito ao lado — do mesmo jeito que o
  plano 29-04 fez quando `jira.link` virou a sexta. A regra de entrada é
  satisfeita, não dobrada: o leitor é nomeado, é executável e chega no mesmo
  ciclo.

- **D-08: o nome é `agents.response_language`, e o default é `"English"`.**

  Grupo `agents` porque é o que a chave governa, e porque toda chave existente do
  schema é agrupada (`autonomous.*`, `bookkeep.*`, `ship.*`, `test.*`, `jira.*`);
  uma chave solta no topo seria a primeira exceção sem motivo. O nome da folha é
  idêntico ao do GSD de propósito — a mesma pergunta deve ter o mesmo nome nos
  dois lugares, senão a relação entre elas vira algo que se descobre lendo código.
  Default `"English"` é literal no LANG-01, e é **explícito**: o `list` e o `get`
  dizem `source: "default"`, então "inglês" nunca é o silêncio de uma chave
  ausente.

- **D-09: idempotência do init é decidida pelo `source`, não por heurística.**

  Critério 3 do roadmap: "rodar o init de novo é idempotente e não sobrescreve
  escolha existente". Mecanismo: `cairn-config.sh get agents.response_language
  --json` devolve `source`. `"file"` ou `"planning"` significa que já houve
  escolha — o init informa qual é, **não pergunta e não escreve**. Só `"default"`
  abre a pergunta. Um projeto já instalado não é alterado sem pedido porque a
  única porta que escreve é a pergunta, e a pergunta não abre.

</decisions>

<canonical_refs>
## Canonical References

**Config e schema**
- `cairn/scripts/cairn-config.py` — schema fechado, regra de entrada ("no key
  without a reader"), `effective()`, `ELSEWHERE`. Docstring é especificação.
- `tests/cairn-config.bats:167` — o conjunto exato de chaves (hoje seis).
- `cairn/commands/config.md` — as duas portas, a batch única de `AskUserQuestion`.

**Pontos de entrega**
- `cairn/commands/autonomous.md:177-202` — o bloco `SUBAGENT-PROMPT-BEGIN/END`,
  cinco itens hoje.
- `cairn/scripts/cairn-parallel.py:967-978` — o payload de `prepare`.
- `cairn/scripts/cairn-parallel.py:1032-1057` — `config_value()`/`config_int()`,
  o shell-out defensivo para `cairn-config.py` e o seam `CAIRN_CONFIG`.
- `cairn/commands/reconcile.md:52-64` — o spawn do `reconcile-investigator`.
- `tests/cairn-parallel-autonomous.bats:139-147` — como se assere sobre a região.

**Instalação**
- `cairn/commands/init.md` — passos 0 (detect), 4 (`cairn-init.sh`), 6 (hand-off).
- `cairn/scripts/cairn-migrate.py:725-742` — `classify()`, decide por `is_dir()`.
- `cairn/hooks/session-start.sh:53-57` — o nudge que M-2 dispararia por engano.

**GSD (leitura, nunca edição)**
- `~/.claude/gsd-core/references/execute-phase-response-language.md` — o único
  ponto que manda repassar.
- `~/.claude/gsd-core/references/planning-config.md:238` — tipo e domínio da chave.
- `~/.claude/gsd-core/bin/lib/config-loader.cjs:755` — de onde o init JSON a tira.

</canonical_refs>

<code_context>
## Code Context

**Já existe e é reusado, não reimplementado:**
- `config_value(top, key, fallback)` em `cairn-parallel.py:1032` — shell-out
  defensivo já pronto (subprocesso que não sobe, exit não-zero, JSON ilegível e
  payload sem `value` degradam para o fallback). `prepare` usa a mesma função que
  `batch` já usa; não nasce um segundo resolvedor de config aqui.
- O seam `CAIRN_CONFIG` (`cairn-parallel.py:595-598`) — os testes apontam para um
  stub sem precisar de `.cairn/config.json` real.
- `make_tmp_repo` / `assert_json_eq` em `tests/helpers.bash`.

**Regras da casa que valem em cada arquivo tocado:**
- `python3` stdlib apenas, sem type hints, sem dataclasses, `EXIT_*` nomeados.
- Docstring de módulo é especificação canônica e registra **medido vs. assumido**.
- Todo `cairn-X.py` tem `cairn-X.sh` fino e `tests/cairn-X.bats` próprio.
- Asserção de status sobre o valor exato, nunca sobre a negação.
- Cada teste nomeia a quebra que o deixa vermelho.
- Suíte: `bash cairn/scripts/cairn-test.sh --jobs 2 tests/` (concorrência limitada
  — três fases rodando em 8 cores; `-j 8` em três árvores travou a suíte antes).

**Proibido nesta worktree** (`cairn-parallel prepare` D-03): `.planning/STATE.md`,
`.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`.

</code_context>

<specifics>
## Specific Requirements

**LANG-01** — `/cairn:init` pergunta a linguagem e grava a escolha na config
local, com inglês como default.
- Pergunta ANTES do hand-off do passo 6 (razão: D-02, os subagentes do
  `/gsd:new-project`).
- Grava em `.cairn/config.json:agents.response_language` (D-02).
- `"English"` é a opção default e pré-selecionada, e `source: "default"` a torna
  explícita (D-08).
- Re-executar o init não pergunta nem sobrescreve quando `source` já é `file` ou
  `planning` (D-09).
- `/cairn:config` ganha a mesma pergunta na batch única, seção nova.

**LANG-02** — a escolha alcança todo subagente spawnado pelo lifecycle, provado
por teste que lê o valor no ponto de entrega.
- `prepare --json` carrega `response_language` + `response_language_source`; teste
  lê o payload do script (D-05, metade mecânica).
- Sexto item no bloco `SUBAGENT-PROMPT-BEGIN/END`; teste sobre a região (D-05,
  metade de prosa).
- `reconcile.md` passo 3 passa a língua ao `reconcile-investigator`, lida do
  script — sem tocar no `bundle` de evidências, porque `evidence_hash` é
  computado sobre ele e um campo novo mudaria o hash e invalidaria o cache do D-04
  da fase 17 (`cairn-reconcile.py:525-531`).
- Metade GSD fechada por propagação (D-04) + check do doctor (D-06).
- O limite (bats não spawna Task tool) fica escrito no teste e no SUMMARY (D-05).

**Critério 3 do roadmap** — projeto já instalado não é alterado sem pedido:
coberto por D-09, com teste.

</specifics>

<deferred>
## Deferred

- **Traduzir `cairn/` para PT-BR** — fora de escopo, e provavelmente nunca:
  comentários e docstrings em inglês são o idioma do código, não a língua do
  usuário. Esta fase separa as duas coisas em vez de misturá-las.
- **Hook de `session-start` propagando a chave** — considerado e rejeitado por
  medição: em worktree de fase, `.planning/config.json` é conteúdo versionado, e
  um hook que o escreve a cada sessão cria diff sujo em toda árvore paralela. A
  propagação fica no `set` (D-04), que é explícita, e o doctor vira a rede (D-06).
- **`cairn.sync_push`** — segue ausente do schema pela mesma razão de sempre
  (`CairnGo-gbu`). Nada nesta fase o toca.
- **Config por workstream** — `cairn-config.py` resolve do project dir e nada
  mais, por decisão da fase 29. Continua assim.
- **Fazer `classify()` do migrate olhar conteúdo em vez de `is_dir()`** — seria a
  outra saída para M-2, e é uma mudança de comportamento do `/cairn:migrate` para
  todo mundo que tem `.planning/` vazio. Não cabe nesta fase; fica anotado aqui
  porque foi considerado, não esquecido.

</deferred>
