---
phase: 29-nothing-mechanical-stays-manual
plan: "03"
subsystem: infra
tags: [python, bats, config, cli, stdlib, json]

requires:
  - phase: 18-parallel-phase-execution
    provides: "`cairn-parallel.py batch`, o consumidor real onde a primeira chave da config é lida e aplicada"
provides:
  - "`.cairn/config.json`: a config própria do cairn, com cinco chaves e duas portas para o mesmo lugar"
  - "`cairn-config.py` + `cairn-config.sh`: list/get/set com schema fechado, leitor nomeado por chave e validação antes da escrita"
  - "`/cairn:config`: a porta da pergunta — um lote de AskUserQuestion em três seções, valor corrente pré-selecionado"
  - "`batch --cycle K`: o teto de ciclos de um run autônomo, com nota que nomeia teto e ciclo"
  - "o inventário do que o cairn já guarda espalhado (sync.json, context.json, cairn.enabled), num lugar só"
affects: [29-02-bookkeep, 29-06-test, autonomous-loop, ship]

actuals:
  tokens: 19030
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Schema fechado com leitor nomeado por chave: chave sem leitor não entra"
    - "Resolução de config por subprocess degradante (forma do fetch_lease_status), nunca reimplementada no consumidor"
    - "Flag explícita > config > default do schema, com `default=None` no argparse para que a ausência da flag seja distinguível"

key-files:
  created:
    - cairn/scripts/cairn-config.py
    - cairn/scripts/cairn-config.sh
    - cairn/commands/config.md
    - tests/cairn-config.bats
  modified:
    - cairn/scripts/cairn-parallel.py
    - cairn/commands/help.md
    - tests/cairn-parallel.bats

key-decisions:
  - "A config mora em `.cairn/config.json`, arquivo próprio — e a razão do planejamento que NÃO era medição foi corrigida por escrito em vez de sumir"
  - "`cairn.sync_push` fica de fora e ganha endereço: issue bd CairnGo-gbu, com a medição e as três saídas possíveis"
  - "O teto de ciclos ganhou campo próprio (`cycle_note`) em vez de sobrescrever o `note` de passagem — desvio deliberado do plano"
  - "Toda prova de config lê no ponto de consumo (o teto que o `batch` aplica), nunca no arquivo"

patterns-established:
  - "Prova por conjunto: `list --json` é afirmado pelo SET exato de chaves, então uma sexta chave sem leitor fica vermelha em vez de entrar sem ninguém ver"
  - "Prova de duas portas: escrever à mão e ler pelo `get`, gravar pelo `set` e ler o arquivo cru, e comparar os dois arquivos byte a byte"

requirements-completed: [AUTO-05, AUTO-06]

coverage:
  - id: D1
    description: "A config existe e é lida no ponto de consumo: mudar `autonomous.max_parallel` muda quais fases o `batch` seleciona"
    requirement: AUTO-05
    verification:
      - kind: integration
        ref: "tests/cairn-parallel.bats#the ceiling comes from autonomous.max_parallel: the setting changes which phases batch selects, not just what it reports"
        status: pass
      - kind: integration
        ref: "tests/cairn-parallel.bats#with no .cairn/config.json the ceiling is still 3 — no existing repo changes behavior"
        status: pass
    human_judgment: false
  - id: D2
    description: "Duas portas para o mesmo lugar: a pergunta grava pelo `set` e a edição à mão do `.cairn/config.json` tem o mesmo efeito, byte a byte"
    requirement: AUTO-05
    verification:
      - kind: unit
        ref: "tests/cairn-config.bats#the two doors reach the same bytes: hand-write and read via get, set and read the file raw, and both orders produce identical files"
        status: pass
      - kind: unit
        ref: "tests/cairn-config.bats#a set never clobbers a key its own question did not ask about"
        status: pass
    human_judgment: false
  - id: D3
    description: "O conjunto de chaves é fechado e cada uma nomeia seu leitor; `sync_push` não está entre elas"
    requirement: AUTO-06
    verification:
      - kind: unit
        ref: "tests/cairn-config.bats#list names EXACTLY the five keys of the schema — and sync_push is not one of them"
        status: pass
    human_judgment: false
  - id: D4
    description: "O que já morava espalhado passa a ser listado num lugar só (sync.json, context.json, cairn.enabled), com dono e leitor"
    requirement: AUTO-06
    verification:
      - kind: unit
        ref: "tests/cairn-config.bats#list also inventories the config cairn keeps elsewhere, by file and by owner"
        status: pass
    human_judgment: false
  - id: D5
    description: "O teto de ciclos zera a seleção acima do limite dizendo por quê, e não faz nada abaixo dele nem para quem não conta ciclos"
    requirement: AUTO-06
    verification:
      - kind: integration
        ref: "tests/cairn-parallel.bats#the cycle ceiling has teeth: at the limit batch still selects, past it it selects nothing and names the ceiling and the cycle"
        status: pass
      - kind: integration
        ref: "tests/cairn-parallel.bats#the cycle ceiling does not apply to a caller that does not count cycles, and 0 is no ceiling at all"
        status: pass
    human_judgment: false
  - id: D6
    description: "`/cairn:config` pergunta num lote só, em seções nomeadas, com o valor corrente pré-selecionado, e declara por escrito o que ficou de fora"
    requirement: AUTO-05
    verification:
      - kind: unit
        ref: "tests/cairn-config.bats#the /cairn:config command delegates to the script and declares what it leaves out"
        status: pass
    human_judgment: true
    rationale: "O `AskUserQuestion` não roda em bats. O teste prova que o comando delega ao script (list --json / set), que a costura das duas portas é sólida e que o parágrafo do `sync_push` está lá com a issue citada — mas se as perguntas realmente aparecem agrupadas e pré-selecionadas na sessão só se vê rodando `/cairn:config`."

duration: 45min
completed: 2026-08-03
status: complete
---

# Phase 29 Plano 03: A config do cairn, com duas portas Summary

**O cairn ganhou config própria com cinco chaves, cada uma com um leitor executável nomeado, e a prova de que ela funciona lê o teto que o `batch` aplica — não o arquivo que o `set` escreveu.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3 de 3
- **Files modified:** 7 (4 criados, 3 modificados)
- **Commits:** 3

## Accomplishments

- **`cairn-config.py` + par `.sh`** — `list`/`get`/`set` sobre `.cairn/config.json`,
  schema **fechado** (chave fora dele é erro de uso, nunca gravação), validação de
  tipo **antes** da escrita (valor recusado deixa o arquivo exatamente como estava,
  inclusive ausente), e valor efetivo = arquivo quando presente e bem tipado, senão
  o default do schema. Formato de escrita igual ao `gbsync.py:write_json`
  (`indent=2, sort_keys=True` + newline), porque o arquivo é commitado e o diff é
  lido por gente.
- **O ponto de consumo, provado.** `cairn-parallel.py batch --max` trocou
  `default=3` por `default=None` e, sem a flag, tira o teto de
  `autonomous.max_parallel`. O teste que separa "chave gravada" de "chave lida"
  muda a config e verifica **quais fases o `batch` seleciona**.
- **Cinco chaves, cada uma com leitor nomeado** — `autonomous.max_parallel`,
  `autonomous.max_cycles`, `bookkeep.auto_commit`, `ship.pr_scope`, `test.jobs`.
- **`list` fecha o AUTO-06**: valor, default, origem (`file`/`default`), leitor e
  efeito por chave, **mais** o inventário do que já morava espalhado
  (`.cairn/sync.json`, `.cairn/context.json`, `cairn.enabled` em
  `.planning/config.json`), cada um com dono e leitor. O inventário é inerte: o
  `list` nomeia esses arquivos e nunca os abre.
- **Teto de ciclos com dente.** `batch --cycle K`: acima de `autonomous.max_cycles`
  a seleção é vazia, toda fase runnable é adiada com o teto nomeado como razão, e
  um `cycle_note` diz qual ciclo e qual teto. Exit continua 0 — é um planejador de
  leitura, quem para é o chamador. Sem `--cycle`, o teto não existe.
- **`/cairn:config`** — um lote de `AskUserQuestion` em três seções nomeadas
  (Bookkeeping · Autonomous run · Tests) com o valor corrente pré-selecionado,
  valores lidos do `list --json` e escrita pelo `set`, fechando com a frase que
  metade do AUTO-05 exige ser verdadeira: editar `.cairn/config.json` à mão chega
  exatamente ao mesmo lugar.

## Task Commits

1. **Task 1 (tracer): uma chave, ponta a ponta** — `a820ea6` (feat)
2. **Task 2: o resto do schema, o inventário e o teto de ciclos** — `4dc7637` (feat)
3. **Task 3: a porta da pergunta** — `e7b54ad` (feat)

## Files Created/Modified

- `cairn/scripts/cairn-config.py` — list/get/set, schema com leitor por chave,
  docstring como especificação canônica (medido versus assumido incluído)
- `cairn/scripts/cairn-config.sh` — wrapper fino, contrato de exit code no cabeçalho
- `cairn/scripts/cairn-parallel.py` — `--max` vindo da config, `--cycle K`, o
  resolvedor `config_value`/`config_int` degradante e o seam `CAIRN_CONFIG`
- `cairn/commands/config.md` — a porta da pergunta e o parágrafo do que ficou fora
- `cairn/commands/help.md` — seção CONFIG separando os três comandos de configuração
- `tests/cairn-config.bats` — 16 testes (schema, tipos, inventário, duas portas)
- `tests/cairn-parallel.bats` — 6 testes novos (31 → 37), todos no ponto de consumo

## Testes: vermelho e verde, número a número

| suíte | antes | depois |
|---|---|---|
| `tests/cairn-config.bats` | não existia | **16**, 0 falhas |
| `tests/cairn-parallel.bats` | 31 | **37**, 0 falhas |
| `tests/cairn-parallel-autonomous.bats` | 9 | 9, 0 falhas (intocada) |
| **suíte inteira** (`tests/`) | — | **600, 0 falhas** |

A suíte inteira foi medida em lotes (`77 + 183 + 122 + 83 + 73 + 62 = 600`), e o
total bate com o `1..600` que o `bats tests/` anuncia. **Não houve baseline limpo
de 556 como o prompt supunha:** quando comecei, a árvore já carregava commits dos
planos 29-01 e 29-02 desta mesma onda — a contagem estática de `@test` no HEAD de
partida já era 570. Rodar `bats -j 6 tests/` inteiro de uma vez foi abortado três
vezes no meio (`bats warning: Executed 171 instead of expected 600`), duas por
concorrência com o outro executor na mesma árvore e uma por SIGPIPE do meu próprio
`| head` — o número acima veio de lotes em foreground, sem `head` no pipe.

**Treze quebras nomeadas, cada uma executada, vista vermelha, restaurada de backup
`cp` (byte a byte, `cmp` confirmado) e vista verde de novo:**

| # | quebra | teste que ficou vermelho |
|---|---|---|
| 1 | consumidor ignora a config (usa só o fallback) | `.max` devolveu 3, esperava 1 |
| 2 | default do schema desviou 3 → 4 | dois testes: `batch` sem config e `get` sem arquivo |
| 3 | precedência invertida (config ganha da flag) | `--max 2` devolveu 1 |
| 4 | `set` sem validação de tipo | `banana` saiu 0, esperava 3 |
| 5 | schema aberto (chave desconhecida aceita) | `naosei.chave` saiu 0, esperava 2 |
| 6 | sexta chave sem leitor (o botão do `sync_push`) | conjunto de chaves divergiu |
| 7 | `list` sem o inventário | `elsewhere` vazio |
| 8 | enum não validado | `talvez` saiu 0, esperava 3 |
| 9 | comparação do teto de ciclos removida | selecionou 2 fases acima do teto |
| 10 | teto aplicado sem ninguém pedir | seleção vazia com `max_cycles=0` |
| 11 | porta da escrita normaliza diferente (`indent=4`) | `cmp` dos dois arquivos falhou |
| 12 | porta da escrita grava em outro arquivo | o arquivo da porta manual não existia |
| 13 | `set` reconstrói o arquivo em vez de mesclar | chave editada à mão desapareceu |

## Decisões Made

1. **Onde a config mora.** `.cairn/config.json`, arquivo próprio, pelas duas razões
   medidas do plano (a janela de reescrita do `config-loader.cjs:609` e o `.cairn/`
   já ser a casa do que o cairn possui). A terceira "razão" do planejamento
   anterior era um erro de aridade, não uma medição — **escrever `cairn.*` pelo
   gsd-tools está provado** — e isso está escrito no docstring em vez de a frase
   sumir.
2. **`cairn.sync_push` fora, com endereço.** Criei a issue bd **CairnGo-gbu** com a
   medição (declarada em `capability.json:43`, três fragmentos de prompt,
   `tests/capability.bats:97`, zero código executável) e as três saídas possíveis.
   O `config.md` cita a issue; o teste do conjunto exato de chaves garante que
   acrescentar o botão fica vermelho.
3. **`cycle_note` em vez de `note`.** Desvio deliberado do plano — ver abaixo.
4. **`--cycle` opcional, e o teto só se aplica a quem conta ciclos.** Inventar um
   número de ciclo dentro do `batch` seria a segunda verdade que o arquivo inteiro
   recusa.

## Deviations from Plan

### 1. [Discretion] O teto de ciclos ganhou campo próprio em vez de usar `note`

- **Encontrado em:** Task 2
- **O plano dizia:** "devolve `selected: []` com uma `note` que nomeia o teto em
  vigor e o ciclo pedido".
- **O que foi feito:** o campo é `cycle_note`, e `note` continua intocado.
- **Por quê:** `note` é passado **verbatim** do `cairn-status.py` — o docstring do
  `cairn-parallel.py` diz explicitamente que "a flag de honestidade pertence a quem
  a computou". Sobrescrevê-la colocaria as palavras de dois autores no mesmo campo,
  e um consumidor não teria como saber de quem era a frase. O `announcement` (o
  texto que o operador lê) carrega as duas.
- **Verificação:** `tests/cairn-parallel.bats#the cycle ceiling has teeth` afirma
  `.cycle_note`, `.cycle`, `.max_cycles`, a seleção vazia e a menção no
  `announcement`.
- **Commit:** `4dc7637`

### 2. [Discretion] `MAX_PARALLEL_FALLBACK` duplica o default do schema

- **Encontrado em:** Task 1
- **Issue:** o consumidor lê a config por subprocess e precisa de um número quando
  o resolvedor não roda. Isso é, literalmente, o default do schema escrito num
  segundo lugar — a doença que a fase inteira combate.
- **Decisão:** manter, com a hierarquia declarada em comentário no código: *o
  schema é a fonte; esta constante é o que mantém o `batch` de pé quando a fonte
  não pode ser alcançada; se as duas divergirem, o schema está certo*. A
  alternativa (importar o `cairn-config.py`) viola a convenção de arquivo
  autossuficiente da casa.
- **Prova de que a duplicação não escapa:** a quebra 2 (default 3 → 4) deixa
  vermelho o teste de "sem config, o teto é 3".

---

**Total de desvios:** 2, ambos de discretion documentada. Nenhum foi correção de
bug do plano — os dois são escolhas onde o plano dizia uma coisa e a convenção
existente do arquivo dizia outra.

## Issues Encontradas

- **O teste da prosa quase virou tautologia.** A primeira asserção sobre o
  `config.md` procurava a string `"edit it by hand"`, que existia no *frontmatter*
  do comando — teria passado com o passo 4 (o que de fato diz ao usuário que as
  duas portas são a mesma) inteiramente ausente. Ficou vermelha, e a asserção foi
  trocada pela frase inteira do passo 4. Um teste que passa com a feature removida
  não é prova, e este passou perto.
- **Execução concorrente na mesma árvore.** Os planos 29-01 e 29-02 commitaram no
  meio da minha sequência (`27d5830`, `1661a94`, `ce372f4` estão intercalados). Não
  toquei em `tests/helpers.bash`, `tests/README.md`, `cairn-reconcile.py` nem
  `cairn-bookkeep.py`. As Tasks 2 e 3 compartilhavam `tests/cairn-config.bats`, e a
  separação dos commits foi feita retirando o bloco da Task 3 para um backup,
  commitando a Task 2, e restaurando — `cmp` confirmou byte a byte, e as duas
  árvores intermediárias rodaram verdes.

## User Setup Required

Nenhum. `.cairn/config.json` não precisa existir: sem arquivo, todo default é o
comportamento de hoje.

## Next Phase Readiness

- **29-02 (`cairn-bookkeep.py`)** já tem `bookkeep.auto_commit` e `ship.pr_scope`
  no schema, com o leitor declarado: basta consumir por
  `cairn-config.sh get <chave>` (ou pelo mesmo padrão de subprocess degradante do
  `cairn-parallel.py`).
- **29-06 (`cairn-test.py`)** idem para `test.jobs`.
- **Aviso que vale a pena carregar:** as três chaves acima estão no schema **antes**
  de terem leitor executável. Se o ciclo terminar com alguma delas ainda não lida,
  o certo é apagar a chave, não relaxar a regra — é exatamente o estado em que o
  `sync_push` está.

## Self-Check: PASSED

- Arquivos criados/modificados: os 7 existem em disco (`cairn-config.py`,
  `cairn-config.sh`, `config.md`, `cairn-config.bats`, `cairn-parallel.py`,
  `help.md`, `cairn-parallel.bats`).
- Commits: `a820ea6`, `4dc7637`, `e7b54ad` presentes em `git log`.
- Issue de grooming citada no `config.md`: `CairnGo-gbu` existe em `bd show`.
- `git diff --quiet HEAD -- .gitignore` limpo — `.cairn/config.json` é commitado
  de propósito.
- `python3 -m py_compile` limpo nos dois scripts Python.

**Não executado, por instrução explícita do orquestrador:** as atualizações de
`.planning/STATE.md`, `.planning/ROADMAP.md` e `.planning/REQUIREMENTS.md`
(`state advance-plan`, `roadmap update-plan-progress`,
`requirements mark-complete AUTO-05 AUTO-06`). Os três arquivos são o fixture
congelado do plano 29-01 nesta mesma onda; quem fechar a fase precisa rodar essas
três verbs — ou deixar o próprio `cairn-bookkeep` (29-02) fazê-lo.

---
*Phase: 29-nothing-mechanical-stays-manual*
*Completed: 2026-08-03*
