---
phase: 18-parallel-phase-execution
plan: "04"
subsystem: parallel-execution
tags: [prose, command, docs-as-contract, bats, proxy-test, d-03, d-04]
requires:
  - "cairn-parallel.py batch --json — selected[]/deferred[]/max/announcement, com independência consumida de parallelism() (18-01)"
  - "cairn-parallel.py prepare N --json — worktree/branch/base_commit/lease.holder/planning_files_forbidden (18-01)"
  - "cairn-parallel.py reconcile --json — branches[]/pairs[]/planning_writes/findings_total, exit 6 (18-02)"
  - "cairn-parallel.py cleanup --apply — órfãos e remoção só do que é limpo E mesclado (18-03)"
  - "cairn/commands/work.md — já adquire o lease e resolve identidade pelo diretório de trabalho"
provides:
  - "/cairn:autonomous com execução paralela por default, anunciada antes de criar qualquer coisa (D-04)"
  - "o laço em quatro momentos: planejar central -> prepare -> subagentes concorrentes -> reconciliar/mesclar/marcar/limpar"
  - "o bloco delimitado do prompt do subagente (SUBAGENT-PROMPT-BEGIN/END) com a proibição literal dos três arquivos de planejamento"
  - "tests/cairn-parallel-autonomous.bats — 9 testes estáticos, rotulados PROXY no cabeçalho"
affects:
  - "cairn/docs/commands/autonomous.md — contrato atualizado em lockstep (flags, regras de parada, Files touched)"
tech-stack:
  added: []
  patterns:
    - "prosa como mecanismo: quando o que separa o agente dos arquivos compartilhados é texto, travar o texto é travar o mecanismo"
    - "marcadores de região em markdown (SUBAGENT-PROMPT-BEGIN/END) para que 'o prompt diz X' seja afirmação sobre o prompt, não sobre o arquivo"
    - "grep negativo que se autoinvalidaria se a proibição fosse escrita por extenso — proibição em palavras, valores nus entre crases"
    - "âncora por número de linha delimitando a seção, não só presença no arquivo"
    - "teste proxy rotulado no cabeçalho, apontando onde está a prova mecânica"
key-files:
  created:
    - tests/cairn-parallel-autonomous.bats
  modified:
    - cairn/commands/autonomous.md
    - cairn/docs/commands/autonomous.md
key-decisions:
  - "O anúncio precisa acrescentar o teto à mão: build_announcement() do 18-01 só menciona --max dentro do reason de um deferred, então num lote que nada cortou o teto vigente não apareceria — a prosa passa a nomeá-lo a partir de result.max sempre"
  - "O checkpoint de fase (doctor + bd list) migrou para depois do merge, na árvore principal: dentro da worktree ele julgaria uma fase cujas marcações de conclusão a D-03 proíbe de existir ali"
  - "prepare exit 4 (caminho ocupado / branch sem worktree) tratado como exit 3: tira aquela fase do lote e o run continua — o plano só nomeava o 3, e parar tudo por um caminho ocupado seria uma regra de parada nova não pedida"
  - "Marcadores HTML delimitando o prompt do subagente, em vez de grep no arquivo inteiro: sem eles o teste da proibição passaria com os três caminhos citados só no parágrafo que os discute"
  - "Sob --sequential o batch continua rodando e sendo anunciado — anunciar paralelismo e enfileirar é honesto exatamente aqui, porque o operador pediu por nome"
metrics:
  duration: ~70min
  tasks: 2
  commits: 2
  tests: 9 novos (tests/cairn-parallel.bats segue 31/31)
  completed: 2026-08-01
actuals:
  # chars/4 sobre as linhas adicionadas do diff realizado (git diff HEAD~2 HEAD)
  tokens: 8065
  tasks: 2
  commits: 2
status: complete
---

# Phase 18 Plan 04: o laço paralelo do /cairn:autonomous — Summary

`/cairn:autonomous` passa a executar em paralelo o que ele mesmo já
identificava como paralelizável: o lote vem do `batch`, o anúncio do passo 0.4
diz quantas fases correm, por quê, em que worktree e sob que teto **antes** de
criar qualquer coisa, e o laço se parte em planejar central / preparar /
executar concorrente / reconciliar-mesclar-marcar-limpar.

## O que foi construído

### Task 1 — `cairn/commands/autonomous.md` + a doc em lockstep

- **Passo 0.3** roda também `cairn-parallel.sh batch --json` e a prosa diz
  explicitamente para não decidir independência ali: quem computa é
  `parallelism()` em `cairn-status.py`, e uma segunda opinião sobre o mesmo
  fato é a segunda verdade que este milestone existe para eliminar.
- **Passo 0.4** imprime o `announcement` do batch verbatim e acrescenta as
  duas coisas que ele não carrega: o teto `max` em vigor com `--max N` como
  forma de mudá-lo, e a frase de que este é o ponto de interrupção — o próximo
  passo cria worktrees e spawna agentes que escrevem código.
- **O laço em quatro momentos**, cada um com a razão ao lado da regra:
  1. **Planejar no principal, em sequência.** Razão mecânica, não cautelar:
     `/gsd:plan-phase` escreve `ROADMAP.md`, então uma fase planejada dentro da
     própria worktree quebraria a D-03 no primeiro passo. Planejar central *é*
     a aplicação central que a D-03 pede. O passo de discussão do
     `--interactive` vive aqui, na vez de cada fase.
  2. **`prepare "$N" --json` por fase.** Exit 3 (lease vivo) e exit 4 (caminho
     ocupado / branch sem worktree) tiram aquela fase do lote com o motivo
     nomeado; o run continua com as outras.
  3. **Executar.** Um subagente por fase, spawados juntos. O bloco delimitado
     por `SUBAGENT-PROMPT-BEGIN/END` carrega os cinco itens do prompt: onde
     trabalha (caminho absoluto vindo do `prepare`, nunca perguntado ao
     agente), o que roda (`/cairn:work N` e `/cairn:verify N` ali dentro, com a
     nota de que o `acquire` do work resolve identidade pelo diretório e
     reconhece o lease como seu), o que não pode escrever (os três caminhos,
     literais), commitar sem mesclar e sem push, e o que reportar.
  4. **Reconciliar, mesclar, marcar, limpar.** `reconcile --json` primeiro:
     exit 6 é regra de parada e o relatório inteiro vai ao operador antes de
     qualquer merge; `planning_writes` é apresentado **mesmo com exit 0**.
     Merge uma branch por vez com `git merge --no-ff` puro, conflito do git é
     parada, e nenhuma estratégia que escolha um lado em silêncio é permitida
     em lugar nenhum. Depois as marcações dos três arquivos de todas as fases
     de uma vez, na principal, e o checkpoint de fase (doctor + `bd list`)
     também ali. Por último `cleanup --apply`.
- **`--sequential`** documentado como a saída nomeada: uma fase por vez na
  árvore principal, momentos 2 e 3 não rodam.
- **Regras de parada** ganharam reconcile exit 6 e conflito de merge, e
  ganharam a lista explícita do que **não** é parada: `prepare` exit 3 e a
  falha de uma fase paralela.
- A frase antiga do passo 0.4 — "executa em sequência mesmo assim" — saiu. A
  frase sobre `parallelism.declared` false ficou.
- `cairn/docs/commands/autonomous.md` foi atualizada no mesmo commit: resumo
  dos passos, tabela de flags (`--sequential`, `--max N`, `--interactive`),
  regras de parada, exemplos e "Files touched" (worktrees irmãs, branches
  `phase/<N>-<slug>`, e a nota de que os três arquivos de planejamento só são
  escritos na principal, depois dos merges).

### Task 2 — `tests/cairn-parallel-autonomous.bats`, 9 testes

O cabeçalho diz primeiro o que o arquivo **não** prova: nenhum bats mostra dois
subagentes LLM rodando ao mesmo tempo, porque quem spawna agente aqui é prosa
lida por um modelo. Aponta a prova mecânica em `tests/cairn-parallel.bats` (31
testes — o stub `CAIRN_STATUS` que contradiz o ROADMAP do fixture, e a
comparação por `realpath` entre `batch` e `prepare`) e diz que um verde aqui
não é evidência equivalente. Mesma forma de `tests/cairn-reconcile-agent.bats`.

| # | Teste | O que trava |
|---|---|---|
| 1 | artefatos existem | os dois arquivos |
| 2 | default paralelo | "Parallel execution is the default" + `--sequential` como saída nomeada |
| 3 | ordem | `batch` < planejar-no-principal < `prepare` < `reconcile` < `cleanup`, por número de linha |
| 4 | proibição D-03 | os três caminhos literais **dentro** do bloco delimitado do prompt |
| 5 | grep negativo | 4 cadeias × 2 arquivos = 8 checagens; a falha nomeia cadeia e arquivo |
| 6 | regras de parada | exit 6 para o run; uma fase falhando não para as outras |
| 7 | `planning_writes` | a frase do exit 0, ancorada na frase e não no verbo `reconcile` |
| 8 | teto | `--max` nomeado **dentro** do passo do anúncio, delimitado por linha |
| 9 | doc em lockstep | mesma frase do default paralelo + linhas da tabela de flags |

## Prova por quebra

Oito mutações, cada uma vermelha em exatamente o seu teste com os outros oito
verdes, cada arquivo restaurado byte a byte de um backup `cp` (nunca
`git checkout`) e conferido por md5:

| Quebra | Resultado | Teste vermelho |
|---|---|---|
| A — remover a frase do `--sequential` | 8/1 | 2 |
| B — trocar as linhas de invocação de `prepare` e `reconcile` | 8/1 | 3 |
| C1 — escrever uma invocação de estratégia no comando | 8/1 | 5 |
| C2 — escrever outra invocação de estratégia na doc | 8/1 | 5 |
| D — apagar a frase do `planning_writes` com exit 0 | 8/1 | 7 |
| E — tirar um dos três caminhos do bloco do prompt | 8/1 | 4 |
| F — remover a frase do teto do anúncio | 8/1 | 8 |
| G — remover `--sequential` da tabela de flags da doc | 8/1 | 9 |

Depois das restaurações: **9/9 verde**. A mensagem de falha da C2 saiu como
`forbidden merge-strategy chain '--strategy=ours' appears 1 time(s) in
.../cairn/docs/commands/autonomous.md` — cadeia e arquivo nomeados, que é o
motivo de serem oito checagens e não dois loops sobre um blob juntado.

## Desvios do plano

Nenhum desvio de regra 1–4 no sentido de bug corrigido: o trabalho é prosa. Os
quatro pontos abaixo são decisões que o plano não cobria ou onde ele estava
impreciso.

**1. [Achado] O `announcement` do 18-01 não nomeia o teto quando nada foi
cortado.** O must-have exige que o anúncio nomeie o teto em vigor. Lendo
`build_announcement()` em `cairn-parallel.py`, `--max` só aparece dentro do
`reason` de um `deferred` ("above the --max 3 ceiling"). Num lote em que o teto
não cortou nada — o caso comum — o texto pronto não carrega o número, e é
exatamente o caso em que o operador não consegue distinguir "só duas fases
estão livres" de "cinco estão livres e o teto cortou três". A prosa passa a
nomear o teto a partir de `result.max` sempre, como acréscimo explícito ao
texto do script. A alternativa por mecanismo — `build_announcement()` sempre
emitir a linha do teto — é uma mudança no 18-01 e fica registrada aqui como
candidata, não aplicada.

**2. [Decisão] O checkpoint de fase migrou para depois do merge.** O plano não
disse onde o `doctor` + `bd list -l m-<milestone>,phase-N --all` roda num run
paralelo. Dentro da worktree ele julgaria uma fase cujas marcações de conclusão
a D-03 proíbe de existir ali — o checkpoint reprovaria por construção. Ficou no
momento 4, na árvore principal, por fase mesclada.

**3. [Decisão] `prepare` exit 4 recebe o mesmo tratamento do exit 3.** O plano
só nomeava o 3. Exit 4 é git recusando (caminho ocupado, ou branch existindo
sem worktree) — uma fase que não pode ser preparada, não um run que precisa
parar. Tirar aquela fase do lote e continuar é a leitura coerente com a PAR-05;
parar o run inteiro seria inventar uma regra de parada que ninguém pediu.

**4. [Achado no plano] O `<verify>` da Task 1 aponta para um arquivo que só a
Task 2 cria.** `bats tests/cairn-parallel-autonomous.bats` não existe no
momento em que a Task 1 termina. Na prática as duas foram escritas e depois
commitadas em ordem, com a suíte rodada uma vez cobrindo as duas — o que a
verificação queria dizer. Registrado porque um executor que seguisse o plano ao
pé da letra teria travado ali.

## Regras de parada / gates de autenticação

Nenhum. Nenhuma instalação de pacote, nenhum gate de auth, nenhum checkpoint.

## Limites, ditos em voz alta

- **A concorrência não está provada aqui e não pode estar.** Este plano entrega
  a metade declarativa do critério 1 do roadmap. A metade mecânica é 18-01
  (isolamento de worktree, recusa por lease, `batch` consumindo `parallelism()`,
  ponte `batch`→`prepare` por realpath), 18-02 (edição convergente) e 18-03
  (execução morta e órfão).
- **O grep negativo protege os dois arquivos, não o repo.** Nada impede a
  cadeia proibida de aparecer noutro comando; o alvo é o comando que faz merge
  e a sua doc.
- O journal de uma worktree de fase morre com a árvore (JOUR-06, v2) — a nota
  ficou registrada no rodapé do comando em vez de descoberta depois.

## Verificação

- `bats tests/cairn-parallel-autonomous.bats` — 9/9.
- `bats tests/cairn-parallel.bats` — 31/31, intocado (medido antes e depois).
- `bats tests/cairn-reconcile-agent.bats` — 7/7, e
  `bats tests/cairn-corroboration.bats` — 22/22. São as duas únicas suítes
  além da nova que leem markdown de `cairn/commands/` ou citam
  `/cairn:autonomous` (`grep -ln "cairn/commands\|docs/commands" tests/*.bats`),
  ou seja, todo o raio de alcance possível de uma mudança que só toca markdown.
- `bats tests/` inteiro **não terminou dentro desta sessão** — as suítes
  `bench-*` dominam o tempo e passaram de 25 minutos. Dito assim em vez de
  omitido: o que a `<verification>` do plano pedia foi coberto por suíte, não
  por uma execução única do diretório.
- Grep negativo manual das quatro cadeias contra os dois arquivos: 0 ocorrências
  em todas as oito combinações.
- Os três arquivos de planejamento (`STATE.md`, `ROADMAP.md`,
  `REQUIREMENTS.md`) não foram tocados — reconciliação central, por instrução
  do operador.

## Commits

| Commit | Task |
|---|---|
| `5c84a47` | Task 1 — o laço paralelo no comando + doc em lockstep |
| `01a2174` | Task 2 — o teste proxy, rotulado como proxy |

## Self-Check: PASSED

Arquivos declarados: os quatro existem em disco. Commits declarados: `5c84a47`
e `01a2174` presentes em `git log --all`. `.planning/STATE.md`,
`.planning/ROADMAP.md` e `.planning/REQUIREMENTS.md` seguem intocados por
instrução do operador (reconciliação central), então os passos de atualização
de estado do executor foram deliberadamente pulados.
