---
phase: 29-nothing-mechanical-stays-manual
plan: "06"
subsystem: infra
tags: [python, bats, cli, stdlib, ci, parallelism, config]

requires:
  - phase: 29-nothing-mechanical-stays-manual
    provides: "`test.jobs` no schema do `cairn-config.py` (plano 29-03), com o leitor NOMEADO e não implementado — este plano é o leitor"
provides:
  - "`cairn-test.py` + `cairn-test.sh`: a porta única do suite — resolve jobs, detecta o que o `bats -j` exige ANTES de compor o comando, retira o `-j` quando falta, e repassa o exit code do bats sem tradução"
  - "`--print-command`: o argv exato numa linha de stdout, sem executar nada — a costura que torna o comportamento testável sem bats dentro de bats"
  - "`--check-env`: relatório JSON do que a máquina consegue fazer, para o doctor ROTEAR em vez de reimplementar a detecção"
  - "check 16 do `cairn-doctor.py` (`test-parallel`): a ausência do paralelismo vira aviso com custo medido e comando de instalação, e nunca exit 7"
  - "CI, CONTRIBUTING.md e tests/README.md apontando para a mesma porta, com os números medidos e as três armadilhas escritas"
affects: [ci, cairn-doctor, cairn-config, contributing, tests-readme]

actuals:
  tokens: 41000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Detecção antes da composição: o pré-requisito é checado enquanto o comando é montado, e por isso a frase impressa é verdadeira quando é impressa"
    - "Fronteira temporal em vez de tradução de exit code: 2 e 5 só existem antes do exec; depois dele todo código é do subprocesso, com linha de atribuição no stderr"
    - "Relatório JSON (`--check-env`) como superfície de roteamento: quem sabe a regra é um arquivo só, e o doctor roteia o veredito"
    - "Diagnóstico no stderr para manter stdout com exatamente uma linha machine-readable"

key-files:
  created:
    - cairn/scripts/cairn-test.py
    - cairn/scripts/cairn-test.sh
    - tests/cairn-test.bats
  modified:
    - cairn/scripts/cairn-doctor.py
    - tests/cairn-doctor.bats
    - .github/workflows/ci.yml
    - CONTRIBUTING.md
    - tests/README.md

key-decisions:
  - "`bats -j` exige DOIS pré-requisitos, não um: o binário de paralelismo e flock-ou-shlock. O plano nomeava só o primeiro; macOS não tem flock"
  - "Os avisos foram para o stderr (o plano dizia stdout), porque `--print-command` promete uma linha só em stdout"
  - "O doctor ROTEIA o veredito de `cairn-test.py --check-env` em vez de reimplementar a detecção — um dono da regra"
  - "O check do doctor só se aplica onde existe `cairn/.claude-plugin/plugin.json`, mesma guarda do check 15: o doctor roda em repo de usuário, que não tem esta suíte"
  - "A recursão que a AUTO-09 afirma NÃO existe neste repo; o guard de aninhamento não foi implementado e a medição está registrada na issue"

requirements-completed: [AUTO-04]

coverage:
  - id: D1
    description: "Sem o binário de paralelismo o `-j` sai do comando ANTES do bats ser invocado, e o aviso nomeia o custo medido e o comando de instalação"
    requirement: AUTO-04
    verification:
      - kind: unit
        ref: "tests/cairn-test.bats#without GNU parallel the -j is removed BEFORE bats is invoked, and the warning names the cost and the fix"
        status: pass
      - kind: unit
        ref: "tests/cairn-test.bats#flock and shlock both missing also removes the -j: the second thing bats -j needs"
        status: pass
    human_judgment: false
  - id: D2
    description: "O comando composto é inspecionável sem rodar a suíte, e o stdout do `--print-command` é exatamente uma linha"
    requirement: AUTO-04
    verification:
      - kind: unit
        ref: "tests/cairn-test.bats#the warning lives on stderr, so --print-command's stdout stays exactly one line"
        status: pass
    human_judgment: false
  - id: D3
    description: "O número de jobs sai da flag, da config (`test.jobs`) ou dos núcleos, nessa precedência — e `test.jobs` é lido no ponto de consumo"
    requirement: AUTO-04
    verification:
      - kind: unit
        ref: "tests/cairn-test.bats#test.jobs in the config is READ: with no flag at all the command carries -j 4"
        status: pass
      - kind: unit
        ref: "tests/cairn-test.bats#the flag beats the config: --jobs 2 against test.jobs 4 composes -j 2"
        status: pass
      - kind: unit
        ref: "tests/cairn-test.bats#with the parallel prerequisites present, the composed command carries -j at the CPU count"
        status: pass
    human_judgment: false
  - id: D4
    description: "Exit code tem origem declarada: 2 e 5 são do runner e só antes do bats; depois disso o código é do bats, repassado e atribuído"
    requirement: AUTO-04
    verification:
      - kind: unit
        ref: "tests/cairn-test.bats#bats' exit code comes back untranslated: a bats that exits 1 makes the runner exit 1"
        status: pass
      - kind: unit
        ref: "tests/cairn-test.bats#a bats that exits 5 exits 5 here too, AND the output says the 5 came from bats"
        status: pass
      - kind: unit
        ref: "tests/cairn-test.bats#no bats on PATH is exit 5, and nothing is executed"
        status: pass
    human_judgment: false
  - id: D5
    description: "O doctor reporta a ausência do paralelismo com custo e conserto, e não bloqueia por causa dela"
    requirement: AUTO-04
    verification:
      - kind: integration
        ref: "tests/cairn-doctor.bats#test-parallel: a missing parallel binary warns with the fix and the measured cost, and the doctor still exits 0"
        status: pass
      - kind: integration
        ref: "tests/cairn-doctor.bats#test-parallel: a repo without cairn's plugin manifest reads ok and says not applicable"
        status: pass
    human_judgment: false
  - id: D6
    description: "A suíte inteira roda pelo runner e termina — medida, não presumida"
    requirement: AUTO-04
    verification:
      - kind: manual
        ref: "bash cairn/scripts/cairn-test.sh -> 1..646, 646 ok, 0 falhas, exit 0, 19m38s a -j 8 (2026-08-04)"
        status: pass
    human_judgment: true
    rationale: "Não existe teste automatizado desta afirmação, e não pode existir: um bats que roda a suíte inteira é exatamente a recursão que o `--print-command` foi criado para evitar. A prova é a execução registrada, com contagem e tempo."

duration: ~4h
completed: 2026-08-04
status: complete
---

# Phase 29 Plano 06: A suíte roda em paralelo quando dá, e diz quando não dá Summary

**O `bats -j` sem GNU parallel não roda serial — roda zero testes e sai 1 —, então o cairn detecta a ausência antes de compor o comando, retira o `-j`, e só aí afirma que a suíte vai rodar serial; a frase é verdadeira no instante em que é impressa.**

## Performance

- **Duration:** ~4h (a maior parte é execução de suíte: três rodadas completas mais 17 rodadas de quebra)
- **Tasks:** 3 de 3
- **Files modified:** 8 (3 criados, 5 modificados)
- **Commits:** 4

## Accomplishments

- **`cairn-test.py` + par `.sh`** — resolve o número de jobs (`--jobs N` >
  `test.jobs` > `os.cpu_count()`), checa **antes de compor** o que o `bats -j`
  exige, retira o `-j` quando falta alguma coisa, e repassa o código de saída do
  bats sem tradução.
- **`--print-command`** — o argv exato, uma linha em stdout, exit 0 sem executar
  nada. É a costura que torna jobs, precedência e presença de pré-requisito
  observáveis sem disparar a suíte de dentro de um teste.
- **`--check-env`** — relatório JSON do que a máquina consegue fazer. Existe para
  o doctor **rotear** o veredito em vez de reimplementar a detecção; quem sabe o
  que o `bats -j` exige é um arquivo só.
- **Check 16 do doctor (`test-parallel`)** — `⚠` quando falta pré-requisito, com
  o custo medido e o comando de instalação; `ok` quando dá; **nunca** exit 7.
  Aplicável só onde existe `cairn/.claude-plugin/plugin.json`, mesma guarda do
  check 15 e pela mesma razão: o doctor roda em repo de usuário, que não tem esta
  suíte.
- **Uma porta só** — CI, `CONTRIBUTING.md` e `tests/README.md` apontam para o
  runner, e os três dizem que `bats tests/` continua funcionando.

## Task Commits

1. **Task 1 (tracer): o comando composto, inspecionável** — `a3ed65f` (feat)
2. **Task 2: o doctor enxerga o ambiente de teste** — `56c7a01` (feat)
3. **Correção de bug introduzido na Task 2** — `d4faa99` (fix)
4. **Task 3: uma porta só — CI e documentação** — `dafa4be` (docs)

## A medição que inverte o requisito, reproduzida aqui

O plano trazia a medição do planejamento; eu a reproduzi antes de escrever
qualquer linha, usando o seam do próprio bats (`BATS_PARALLEL_BINARY_NAME`
apontando para um binário que não existe), com PATH completo:

```
1..2
bats-exec-suite: line 323: parallel-nao-existe: command not found
# bats warning: Executed 0 instead of expected 2 tests
exit=1
```

Zero testes, exit 1. **E encontrei a causa de o bats não recusar direito.** Ele
tem uma guarda para isso, em `bats-exec-suite:110`:

```bash
if ! type -p "${parallel_binary_name}" >/dev/null \
   && "${parallel_binary_name}" --version &>/dev/null \
   && [[ -z "$bats_no_parallelize_across_files" ]]; then
  abort "Cannot execute \"${num_jobs}\" jobs without GNU parallel"
```

A primeira cláusula só é verdadeira quando o binário **não** está no PATH; a
segunda só é verdadeira quando executá-lo **funciona**. As duas não podem valer
ao mesmo tempo, então o `abort` é inalcançável — e a falha chega 200 linhas
depois como `command not found` dentro de um pipeline. É por isso que a checagem
tem de ser nossa: não dá para delegar ao bats uma guarda que não dispara.

## O que o plano errou, e a correção é medida

**`bats -j` exige DUAS coisas, não uma.** O plano (e a issue, e o `ci.yml`)
nomeiam só o GNU parallel. Medindo, existe um segundo pré-requisito com
exatamente o mesmo modo de falha:

```
ERROR: flock/shlock is required for parallelization within files!
exit=1
```

`bats_semaphore_setup()` (`lib/bats-core/semaphore.bash:26-33`) exige `flock`
**ou** `shlock` e sai 1 sem executar nada quando não acha nenhum dos dois. Isto
não é hipotético nas máquinas onde este repo roda: **macOS tem `shlock` e não tem
`flock`** (verificado: `/usr/bin/shlock` existe, `flock` não). Um runner que
checasse só o parallel comporia `-j` numa máquina sem nenhum dos dois e
reproduziria exatamente o estado que ele existe para impedir. Os dois são
checados, e qualquer um faltando tira o `-j`.

## Testes: vermelho e verde, número a número

| suíte | antes | depois |
|---|---|---|
| `tests/cairn-test.bats` | não existia | **14**, 0 falhas |
| `tests/cairn-doctor.bats` | 60 | **65**, 0 falhas |
| **suíte inteira** pelo runner (`-j 8`) | — | **646 anunciados, 646 ok, 0 falhas, exit 0** |

A suíte inteira foi medida duas vezes de ponta a ponta:

| rodada | resultado | tempo |
|---|---|---|
| primeira (antes do fix `d4faa99`) | 646 anunciados, 645 ok, **1 vermelho** | 20m27s, 209% CPU |
| final (depois do fix) | 646 anunciados, **646 ok**, exit 0 | 19m38s, 208% CPU |

Pico observado: **~46 processos `bats-exec`** — não travou, não deixou órfão, e o
runner reportou o exit code do bats corretamente nas duas rodadas.

**Doze quebras nomeadas no `cairn-test.py`**, cada uma executada, vista vermelha,
restaurada de backup `cp` (`cmp` confirmado byte a byte) e vista verde de novo:

| # | quebra | testes vermelhos |
|---|---|---|
| 1 | nunca compõe `-j` | 3 |
| 2 | detecção fixa em "dá para paralelizar" | 2 |
| 3 | checa só o parallel, ignora flock/shlock | 1 |
| 4 | aviso no stdout | 3 |
| 5 | ignora a config (`test.jobs`) | 1 |
| 6 | precedência invertida (config ganha da flag) | 1 |
| 7 | compõe `-j 1` para um job só | 1 |
| 8 | engole o exit code do bats | 2 |
| 9 | sem a linha que atribui o código ao bats | 1 |
| 10 | bats ausente tratado como falha de teste (1) e não como 5 | 1 |
| 11 | alvo default resolvido do cwd | 1 |
| 12 | path inexistente entregue ao bats | 1 |

**Cinco quebras nomeadas no check do doctor**, mesmo protocolo:

| # | quebra | testes vermelhos |
|---|---|---|
| 1 | sem a guarda de aplicabilidade (avisa em repo de usuário) | 1 |
| 2 | lê `can_parallelize` antes de `bats` (roteia "sem bats" para o ramo lento) | 1 |
| 3 | atrito virando bloqueio (`warn` → `fail`) | 1 |
| 4 | sem degradação no exit não-zero do reporter | 1 |
| 5 | check escrito e **não registrado** na lista | 5 |

## `test.jobs` é lido de verdade — a janela fecha

O plano 29-03 pôs `test.jobs` no schema com o leitor **nomeado e não escrito**, e
registrou a regra: *se o ciclo fechar com alguma dessas chaves não lida, a chave
deve ser apagada — é o estado exato do `cairn.sync_push`*.

Ela é lida. `resolve_jobs()` chama `config_value(root, "test.jobs")` e o valor
vira o `-j` do comando composto, e a prova está **no ponto de consumo**: o teste
grava 4 na config, não passa flag nenhuma, e afirma que o comando composto traz
`-j 4`. Quebrar a leitura (quebra 5) deixa esse teste vermelho.

As outras duas chaves da mesma janela (`bookkeep.auto_commit`, `ship.pr_scope`)
foram implementadas pelo 29-02 — `cairn-bookkeep.py:738` e `:758`, com testes em
`tests/cairn-bookkeep.bats:1043`, `:1082` e `:1100`. Com as três lidas, a janela
1 do `WINDOWS.md` foi marcada `fixed`: `open_count: 0`.

## A AUTO-09 está errada sobre a causa, e a medição está na issue

O briefing e a issue `CairnGo-idq` afirmam que `bats -j` sobre a suíte inteira é
**recursivo**, porque `tests/cairn-parallel.bats` exercita `cairn-parallel.py`,
"que prepara worktrees e roda suites — bats dentro de bats". **Isso não acontece
neste repo.** Três verificações:

1. **Nenhum arquivo `.bats` invoca `bats` como comando.** Grep por `bats` em
   posição de comando em `tests/`: a única linha que casa é o *nome* de um teste
   em `tests/cairn-test.bats`.
2. **`cairn-parallel.py` não roda suíte nenhuma.** Todos os seus subprocessos são
   `git` ou `sys.executable` (`cairn-lease.py`, `cairn-status.py`,
   `cairn-config.py`). `prepare` cria worktree e lease; quem roda a suíte dentro
   dela é um agente, não o script.
3. **A suíte inteira completou a `-j 8`**, duas vezes, com ~46 processos e sem
   travamento.

Os 112 processos a 2% de CPU vieram de **sete invocações de topo simultâneas de
executores diferentes na mesma árvore** — o próprio `29-03-SUMMARY` registra
"duas por concorrência com o outro executor na mesma árvore". A contenção era
entre executores, não recursiva.

Consequência: **o guard de aninhamento não foi implementado**, porque não tem o
que consertar. Isso está escrito na issue `CairnGo-idq` (`--append-notes`) com as
três verificações e os números, junto com a condição em que o guard passaria a
ter objeto e onde ele deveria morar.

Note que essa recomendação, se seguida às cegas, teria sido **cara**: um guard
que dropa `-j` ao detectar `BATS_*` no ambiente quebraria a invariante central
deste plano — `--print-command` deixaria de mostrar o que seria executado, já que
os testes que o inspecionam rodam sob bats.

## Deviations from Plan

### 1. [Rule 2 - correção] O `bats -j` exige um segundo pré-requisito que o plano não nomeia

- **Encontrado em:** Task 1, antes de escrever código, ao reproduzir a medição.
- **O plano dizia:** detectar `shutil.which("parallel")`.
- **O que foi feito:** detectar o binário de paralelismo **e** `flock`-ou-`shlock`.
- **Por quê:** medido — sem nenhum dos dois, `bats -j` sai 1 com zero testes
  executados, que é literalmente o estado que o requisito existe para impedir.
  macOS não tem `flock`.
- **Prova:** `tests/cairn-test.bats#flock and shlock both missing...`, e a quebra
  3 (checar só o parallel) deixa esse teste vermelho.
- **Commit:** `a3ed65f`

### 2. [Discretion] Os avisos vão para o stderr, não para o stdout

- **O plano dizia:** "uma linha vai para stdout, no formato da casa".
- **O que foi feito:** todo diagnóstico do runner (aviso de paralelismo, linha de
  atribuição do exit code, linha informativa de execução) vai para o **stderr**.
- **Por quê:** `--print-command` promete que o stdout é **exatamente o argv, uma
  linha**. Um aviso dividindo esse canal quebra a única coisa que a flag existe
  para fazer. O `run` do bats funde os dois canais, então nada sob teste perde o
  aviso.
- **Prova:** `tests/cairn-test.bats#the warning lives on stderr...` afirma que o
  stdout tem exatamente uma linha com o stderr descartado; a quebra 4 (aviso no
  stdout) deixa três testes vermelhos.
- **Commit:** `a3ed65f`

### 3. [Discretion] O doctor roteia `--check-env` em vez de refazer a detecção

- **O plano dizia:** "vira uma checagem de ambiente no `cairn-doctor.py`".
- **O que foi feito:** `cairn-test.py --check-env` emite um relatório JSON e o
  doctor apenas transforma o relatório em status, pelo seam `CAIRN_TEST`.
- **Por quê:** a alternativa era um segundo `shutil.which` do parallel e do
  flock dentro do doctor — o schema em dois lugares, que é a doença que esta fase
  trata. É também o padrão da casa (`check_maps_fresh` → `cairn-map.py`,
  `check_release_versions` → `cairn-release.py`).
- **Commit:** `56c7a01`

### 4. [Rule 2 - correção] O check do doctor precisa de guarda de aplicabilidade

- **O plano não menciona.** Sem guarda, todo usuário de um repo cabeado receberia
  um aviso sobre GNU parallel referente a uma suíte bats que ele não tem — o
  mesmo defeito que o `check_release_versions` já teve de contornar.
- **O que foi feito:** aplica só onde existe `cairn/.claude-plugin/plugin.json`.
- **Prova:** `tests/cairn-doctor.bats#test-parallel: a repo without cairn's plugin
  manifest reads ok and says not applicable`; quebra 1 deixa vermelho.
- **Commit:** `56c7a01`

### 5. [Rule 1 - bug] A contagem de checks do doctor ficou em 16 com 17 checks

- **Encontrado em:** Task 3, na primeira rodada da suíte inteira.
- **Issue:** `tests/cairn-doctor.bats:112` afirma `.checks | length == 16`. O
  check 16 tornou isso falso no commit `56c7a01`.
- **Fix:** 16 → 17, com o comentário explicando que a contagem é hardcoded de
  propósito (é o canário de "check escrito e não registrado").
- **Commit:** `d4faa99`

---

**Total de desvios:** 5 — dois de correção do plano por medição, dois de
discretion, um bug meu.

## Issues Encontradas

- **Eu declarei uma suíte verde lendo um log truncado, e isso é o defeito desta
  fase cometido por mim.** Rodei
  `time bats tests/cairn-doctor.bats 2>&1 | tail -15`, o comando foi para
  background, e o arquivo de saída guardou o que o **`tail` produziu** — quinze
  linhas. Um `grep -c "^not ok"` nesse arquivo devolve 0 porque a linha de falha
  nunca esteve nele. Reportei "65/65 verde" com base nisso, e estava errado: a
  asserção da contagem de checks estava vermelha desde o commit anterior. Quem
  pegou foi a rodada da suíte inteira pelo runner. A regra está escrita agora no
  `tests/README.md`: um resultado de suíte lido pela cauda de um log não é um
  resultado.
- **Uma asserção quase-tautológica, pega na primeira execução.** A primeira
  versão do teste "sem parallel, o comando não traz `-j 4`" refutava a string
  sobre a **saída fundida**. Mas o próprio aviso diz `` o `-j 4` foi retirado ``,
  então essa refutação **nunca poderia passar**, por mais correta que fosse a
  composição. Corrigida lendo o comando só do stdout e o aviso só do stderr.
- **`-j` como substring é frágil aqui.** O `$BATS_TEST_TMPDIR` é construído com o
  nome do teste, e um teste chamado "--jobs 1 ..." põe os caracteres `-j` dentro
  de todo caminho que ele imprime. As asserções passaram a casar `-j` como
  **token** de linha de comando.
- **`grep '^@test' | wc -l` não conta testes.** Diz 648; o bats anuncia 646. A
  diferença são duas linhas `@test` dentro de heredocs que escrevem arquivos
  `.bats` descartáveis (`tests/smoke.bats:100` e `tests/cairn-test.bats:69`),
  localizadas com `bats --count` arquivo a arquivo. Está escrito no
  `tests/README.md`.

## User Setup Required

Nenhum. Sem `.cairn/config.json` o runner usa a contagem de núcleos, e `bats
tests/` continua funcionando exatamente como antes. GNU `parallel` é opcional; o
doctor avisa e não bloqueia.

## Next Phase Readiness

- **AUTO-09 (`CairnGo-idq`)** continua aberta, mas com a causa declarada
  refutada e a medição registrada. Quem for fechá-la deve ler a nota antes: o
  conserto proposto não tem objeto.
- **A regra de orquestração que a AUTO-09 realmente quer** é "não rodar dois
  `bats tests/` de topo na mesma árvore ao mesmo tempo". Isso não é uma
  ferramenta, é disciplina de onda — e agora que existe uma porta única, dá para
  colocá-la num lugar só se alguém quiser.
- **Fase 23 / VOID-01:** quando `not-applicable` virar estado de primeira classe,
  o ramo "sem bats nenhum" do check 16 é o candidato natural. O comentário no
  código marca o ponto.

## Self-Check: PASSED

- Arquivos criados/modificados: os 8 existem em disco (`cairn-test.py`,
  `cairn-test.sh`, `tests/cairn-test.bats`, `cairn-doctor.py`,
  `tests/cairn-doctor.bats`, `ci.yml`, `CONTRIBUTING.md`, `tests/README.md`).
- Commits: `a3ed65f`, `56c7a01`, `d4faa99`, `dafa4be` presentes em `git log`.
- `python3 -m py_compile` limpo em `cairn-test.py` e `cairn-doctor.py`.
- Suíte inteira pelo runner: `1..646`, 646 ok, 0 falhas, exit 0.
- `WINDOWS.md`: janela 1 marcada `fixed`, `open_count: 0`.
- `bd show CairnGo-idq` carrega a nota com a medição.

**Não executado, por instrução explícita do orquestrador:** as atualizações de
`.planning/STATE.md`, `.planning/ROADMAP.md` e `.planning/REQUIREMENTS.md`, e
qualquer verb de estado do gsd-tools. Quem fechar a fase precisa marcar `AUTO-04`
completo — ou deixar o `cairn-bookkeep` (29-02) fazê-lo.

---
*Phase: 29-nothing-mechanical-stays-manual*
*Completed: 2026-08-04*
