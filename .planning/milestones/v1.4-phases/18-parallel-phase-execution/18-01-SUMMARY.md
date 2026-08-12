---
phase: 18-parallel-phase-execution
plan: "01"
subsystem: parallel-execution
tags: [python, bash, bats, git-worktree, beads, lease]
requires:
  - "cairn-status.py parallelism() — {runnable, blocked, declared, note}"
  - "cairn-lease.py acquire/status — exclusão mútua por caminho de worktree"
provides:
  - "cairn-parallel.py batch — o consumidor que faltava de parallelism()"
  - "cairn-parallel.py prepare N — worktree determinística + lease apontado para ela"
  - "nomes determinísticos phase/<N>-<slug> e ../<repo>-phase-<N> para o reconcile do 18-02"
affects:
  - "cairn/commands/autonomous.md (passo 0.4) — consumidor futuro do announcement"
tech-stack:
  added: []
  patterns:
    - "seams CAIRN_LEASE / CAIRN_STATUS no padrão CAIRN_* da casa"
    - "docstring como spec canônica, com o medido separado do assumido"
    - "par .py/.sh com a linha de exit codes repetida no cabeçalho do wrapper"
key-files:
  created:
    - cairn/scripts/cairn-parallel.py
    - cairn/scripts/cairn-parallel.sh
    - tests/cairn-parallel.bats
  modified: []
key-decisions:
  - "Sem flag --holder: prepare aponta --project-dir para a worktree e deixa o cairn-lease resolver a identidade (D-01 / princípio da fase 17)"
  - "A pré-checagem read-only NÃO recusa quando o holder vivo é a própria worktree alvo — sem isso o prepare repetido nega a si mesmo"
  - "Duas rotas distintas chegam ao EXIT_HELD (pré-checagem e corrida pós-acquire); só a segunda tem rollback a executar, e só ela pode prová-lo"
  - "Reason de teto em inglês (`above the --max N ceiling`), não o texto pt-BR do plano — saída de script neste repo é inglês"
metrics:
  duration: ~75min
  tasks: 3
  commits: 3
  tests: 16
  completed: 2026-07-31
status: complete
---

# Phase 18 Plan 01: cairn-parallel (batch + prepare) Summary

**`parallelism()` anunciava paralelismo desde a fase 13 e ninguém consumia; agora
`batch` consome e `prepare` transforma o anúncio em worktrees reais, nomeadas
pelo cairn e com o lease apontando para elas.**

## O que foi construído

`cairn/scripts/cairn-parallel.py` (725 linhas, stdlib pura, sem type hints, sem
dataclass) + o par fino `cairn-parallel.sh` + `tests/cairn-parallel.bats`
(16 testes, todos verdes).

**`prepare N`** — roda só do checkout principal (de uma worktree ligada recusa
com `EXIT_USAGE`), resolve slug/branch/caminho, e executa a ordem de aquisição
em quatro passos: pré-checagem read-only → `git worktree add -b phase/<N>-<slug>
../<repo>-phase-<N> HEAD` → `cairn-lease.py acquire N --project-dir <worktree>`
→ rollback do que esta invocação criou se o acquire perder a corrida. Devolve
`{phase, slug, branch, worktree, base_commit, created, lease, planning_files_forbidden}`.

**`batch`** — uma leitura de `cairn-status.py --json` pelo seam `CAIRN_STATUS`,
`runnable`/`blocked`/`declared`/`note` repassados verbatim, uma consulta a
`cairn-lease.py status --all --json` para tirar do lote quem já tem dono vivo,
teto `--max` (default 3), e um `announcement` pronto para o passo 0.4 do
`/cairn:autonomous`.

Os dois verbos usam **a mesma** `phase_layout()`; `argparse` já nasce com
subparsers porque `reconcile` (18-02) e `cleanup` (18-03) entram neste arquivo.

## Testes, e a evidência vermelha/verde de cada quebra nomeada

Suíte inteira: **16/16 verde**. Cada quebra abaixo foi realmente aplicada, medida
e desfeita byte a byte (`shasum` conferido contra a cópia original — nunca
`git checkout` num arquivo com trabalho não commitado).

| # | Quebra aplicada | Efeito medido |
|---|-----------------|---------------|
| 1 | Tracer: `--project-dir` do acquire trocado da worktree pela raiz principal | 1/1 **vermelho**, e só na asserção do `.holder` (`.../cairn-repo.w0gqBN` em vez de `...-phase-2`); todas as outras seguiram verdes — que é exatamente a linha entre "a worktree existe" e "a worktree é a dona da fase" |
| 2 | `batch` derivando `runnable` do ROADMAP em vez de `parallelism.runnable` | 1/1 **vermelho**: `runnable` virou `[2]` (a fase pendente do fixture) contra os `[7,9]` do stub |
| 3 | Resolução de slug sem zero à esquerda **só** no caminho do `batch` | 1/1 **vermelho** na primeira comparação da ponte: `07-alpha` deixou de resolver para a fase 7, o `batch` anunciou `phase/7` e o `prepare` criou `phase/7-alpha` |
| 4 | Rollback removido | teste da janela de corrida **vermelho** (`../<repo>-phase-3` ficou órfão); teste da recusa por lease real **continuou verde** — ver "Onde o plano estava errado" |
| 5 | Rollback **e** recusa da pré-checagem removidos | teste da recusa por lease real **vermelho** (worktree órfã) |

Depois de cada restauração: 16/16 verde de novo.

Verificação do plano, item a item: `bash cairn-parallel.sh` sem argumento sai 2
com a linha de usage; `--help` lista `batch` e `prepare`; 7 imports, todos
stdlib; o cabeçalho do `.sh` lista os mesmos códigos que as constantes `EXIT_*`
(0/2/3/4/5).

## Desvios do plano

### 1. [Regra 1 — Bug] A pré-checagem negava o `prepare` idempotente

- **Achado em:** Task 3, pelo teste de idempotência (`created: false`).
- **Problema:** a pré-checagem read-only recusava sempre que o lease estivesse
  vivo, **inclusive quando o holder era a própria worktree** que aquela chamada
  ia reusar. Um segundo `prepare 3` numa fase já preparada saía 3 em vez de 0.
- **Correção:** `same_path()` compara o holder registrado com a worktree alvo por
  `os.path.realpath` **dos dois lados** (jamais comparação de string: o git
  reporta o caminho físico e o `TMPDIR` do macOS chega por symlink), e
  "held by us" segue para o `acquire`, que já lê isso como `already_mine`.
- **Arquivo:** `cairn/scripts/cairn-parallel.py`. **Commit:** `82dadb5`.

### 2. Reason do teto em inglês, não no pt-BR que o plano escreveu

O plano especificava `reason: "acima do teto --max <N>"`, mas todo o resto do
campo (e o `reason` do lease, que o próprio plano escreveu em inglês) e toda a
saída de script deste repo são em inglês. Ficou
`"above the --max <N> ceiling"`. Registrado aqui em vez de trocado em silêncio.

### 3. `batch` ficou implementado no commit da Task 1

O docstring é a spec canônica e cobre os dois verbos, e `phase_layout()` é
compartilhada — escrevê-lo pela metade teria produzido uma spec falsa. O commit
da Task 2 carrega, portanto, os testes do `batch` e não a sua implementação. É
um desvio da atomicidade por tarefa, e está declarado.

## Onde o plano estava errado

**A quebra nomeada para o teste 1 da Task 3 não fica vermelha.** O plano diz:
"remover o rollback deixa a worktree órfã e as duas últimas asserções ficam
vermelhas". Não ficam. Com a pré-checagem no lugar, uma recusa por lease **real**
(tomado por uma segunda worktree) nunca chega a criar coisa alguma, então o
rollback não tem o que desfazer e o teste segue verde. Medido nos dois sentidos:

- rollback removido → **só** o teste da janela de corrida fica vermelho;
- rollback **e** recusa da pré-checagem removidos → o teste da recusa real fica
  vermelho.

Consequência de desenho: existem **duas rotas distintas** até o `EXIT_HELD`, e o
plano tratava como uma só. A rota da pré-checagem é inalcançável para o rollback,
e a rota da corrida é inalcançável com um lease de verdade — quando a
pré-checagem roda, o lease real já está tomado. Por isso o rollback é provado
pelo seam `CAIRN_LEASE`, com um stub que devolve "vago" no `status` e sai 3 no
`acquire`: é a única forma honesta de entrar na janela entre os passos 1 e 3.
Um terceiro teste fecha o T-18-03 pelo outro lado — worktree pré-criada à mão,
o `prepare` recusa e **não** remove nem ela nem a branch dela.

## Decisões que o plano não cobria

1. **Branch já existente sem a sua worktree** → `EXIT_GIT`, sem tocar em nada. O
   plano só nomeava "caminho ocupado" e "branch divergente"; adivinhar se aquela
   branch é o trabalho da fase seria autodeclaração pela porta dos fundos.
2. **`--max 0` ou negativo** → `EXIT_USAGE`. Um teto de zero só produz um lote
   vazio com um motivo confuso.
3. **`git worktree remove --force` no rollback.** A guarda é a reconfirmação por
   `git worktree list --porcelain` imediatamente antes; o `--force` só derrota a
   recusa do git por árvore suja numa árvore que esta mesma invocação criou
   segundos antes, e nunca amplia o alvo.
4. **`--planning-dir`, não `--project-dir`, ao chamar o `cairn-status.py`** — é a
   flag que aquele script tem. Exits 0 e 5 são aceitos com saída real (o mesmo
   contrato que o `cairn-doctor.py` e o `cairn-reconcile.py` já assumem);
   qualquer outro código, ou JSON inválido, é parada dura.
5. **Fixture com `03-gamma`, `07-alpha`, `09-beta`** e zeros à esquerda de
   propósito: é o zero à esquerda que dá dente à quebra nº 3.

## Arquivos de planejamento

`STATE.md`, `ROADMAP.md` e `REQUIREMENTS.md` **não foram tocados** — reconciliação
central, conforme a instrução desta execução (e conforme a D-03).

## Self-Check: PASSED

- `cairn/scripts/cairn-parallel.py` — FOUND
- `cairn/scripts/cairn-parallel.sh` — FOUND
- `tests/cairn-parallel.bats` — FOUND
- commits `9917323`, `6d82266`, `82dadb5` — FOUND
- `bats tests/cairn-parallel.bats` — 16/16 ok
