---
phase: 18-parallel-phase-execution
plan: "03"
subsystem: parallel-execution
tags: [python, bash, bats, git, worktree, lease, sigkill]
requires:
  - "cairn-parallel.py phase_layout() / PHASE_BRANCH — os nomes phase/<N>-<slug> travados no 18-01"
  - "cairn-lease.py status --all --json — todo lease que já existiu, com holder e stale"
  - "cairn-lease.py release <N> — quem vacúa o metadado INTEIRO e escreve o `released` no journal"
  - "git worktree list --porcelain — a marca `prunable` que o próprio git dá"
provides:
  - "cairn-parallel.py cleanup [--apply] — as cinco categorias e a detecção de órfão POR MECANISMO"
  - "a prova mecânica do PAR-05: SIGKILL num escritor, o outro chega ao fim, o lease morto é liberável"
  - "o guard de inventário (T-18-11) — inventário sem o checkout principal é EXIT_GIT, não lista vazia"
affects:
  - "cairn/commands/autonomous.md — consumidor futuro do encerramento (cleanup depois do reconcile)"
  - "tests/cairn-parallel.bats — make_parallel_fixture agora commita um .gitignore"
tech-stack:
  added: []
  patterns:
    - "docstring como spec canônica, escrita antes da implementação, com o medido separado do assumido"
    - "leitura por default, escrita atrás de flag nomeada (--apply)"
    - "verbo seguro do git como segunda opinião: `worktree remove` sem --force e `branch -d` em vez de -D"
    - "espera por efeito colateral em arquivo (wait_for_file), nunca sleep de tempo fixo"
    - "quebra medida: cada regra tem um teste que fica vermelho quando a regra sai"
key-files:
  created: []
  modified:
    - cairn/scripts/cairn-parallel.py
    - cairn/scripts/cairn-parallel.sh
    - tests/cairn-parallel.bats
key-decisions:
  - "Lease HELD pela própria worktree retém a árvore, stale ou não — não estava no plano, e sem isso `--apply` apagaria a worktree recém-preparada de um agente vivo (ela é limpa e mesclada)"
  - "Inventário de worktree sem o próprio checkout principal é EXIT_GIT — sem esse guard, um `git worktree list` vazio faria TODO lease do repo parecer órfão e `--apply` despejaria todo mundo (T-18-11)"
  - "orphan_registration é relatado no repo inteiro, não só para worktree de fase, porque `git worktree prune` é repo-wide — relatório mais estreito que a ação subestimaria o que --apply vai fazer"
  - "O fixture ganhou .gitignore com `.cairn/journal.jsonl*`: sem ele toda worktree preparada é permanentemente suja (`?? .cairn/`) e `removable` nunca dispararia — o repo do cairn ignora exatamente esse caminho"
  - "Verificação `grep -c 'stash'` do plano já era falsa desde o 18-02: são 6 linhas, 5 no docstring e 1 no banner da região read-only, que PRECISA nomear `[\"stash\"` na forma que o grep estático procura"
metrics:
  duration: ~75min
  tasks: 2
  commits: 3
  tests: 31 (26 herdados + 5 novos)
  completed: 2026-07-31
actuals:
  tokens: 12787
  tasks: 2
  commits: 3
status: complete
---

# Phase 18 Plan 03: cleanup — o órfão detectado por mecanismo Summary

**O holder de um lease é um caminho de worktree, então um holder que não está
em `git worktree list` é, por construção, um dono que não existe — e isso é
visível no minuto seguinte à morte, enquanto o TTL de 4h ainda diz que está
tudo bem.**

## O que foi construído

`cairn-parallel.py cleanup [--apply] [--project-dir DIR] [--json]` — o quarto
verbo do mesmo arquivo. Cruza `git worktree list --porcelain` com
`cairn-lease.py status --all --json` e devolve
`{apply, orphan_registrations[], orphan_leases[], stale_but_live[],
retained[], removable[], applied[]}`, saindo sempre 0.

As cinco categorias, e o que `--apply` faz com cada uma:

| categoria | o que é | `--apply` |
|---|---|---|
| `orphan_registration` | registro que o git marca `prunable`, ou cujo diretório sumiu | `git worktree prune` |
| `orphan_lease` | lease `held` cujo holder, com realpath, não está entre as worktrees vivas | `cairn-lease.py release <N>` |
| `stale_but_live` | lease `stale` cujo holder AINDA é worktree viva | **nada** — relato apenas |
| `retained` | worktree de fase com alteração não commitada, commit não mesclado, ou lease ainda em suas mãos | **nada** — relato + comando manual |
| `removable` | worktree de fase limpa, inteiramente mesclada em `HEAD`, sem lease | `git worktree remove` + `git branch -d` |

A assimetria de exit code em relação ao `reconcile` está escrita no docstring
com a razão: o 6 do `reconcile` existe porque os achados dele são *juízos* que
alguém precisa fazer; os do `cleanup` são condições que o próprio comando
conserta inteiras, então não sobra nada para um exit não-zero proteger.

## Por que não é uma checagem de TTL

O ponto inteiro do desenho, e a linha que separa duas categorias com a mesma
staleness e veredictos opostos:

- **`orphan_lease`** — o dono não existe. Fato sobre a máquina.
- **`stale_but_live`** — o dono não bate heartbeat há 4h, mas a árvore está
  ali no disco. O `acquire` do próprio `cairn-lease` sabe reclamar isso, e o
  faz no momento em que alguém de fato quer a fase — o único momento em que o
  risco do reclaim se paga. Liberar aqui seria correr com ele por um agente
  que pode estar só lento.

O teste do SIGKILL afirma `.orphan_leases[0].stale == false`. Aquele lease foi
tomado segundos antes; com TTL de 4h, uma varredura por relógio olha direto
para ele e não vê nada de errado.

## Testes

31/31 verdes (26 dos planos 18-01 e 18-02, intocados; 5 novos).

| # | teste | prova |
|---|---|---|
| 27 | SIGKILL mid-flight | o outro termina, nada cruza fronteira de árvore, o lease morto é nomeado e liberado |
| 28 | stale com holder vivo | relatado, nunca liberado, e a árvore dele nunca removida |
| 29 | removable vs retained | limpa+mesclada removida; com commit não mesclado, mantida |
| 30 | trabalho não commitado | `--apply` não toca, e `refs/stash` não existe depois |
| 31 | inventário sem o checkout principal | EXIT_GIT sem decidir nada |

### O teste do SIGKILL, e o que ele NÃO prova

Escrito no comentário do próprio teste: ele **não** prova que dois agentes LLM
rodaram ao mesmo tempo — nenhum bats prova isso, porque quem spawna agente é
prosa lida por um modelo. Ele prova a metade mecânica que o PAR-05 pede, com
processos e sinais de verdade.

Duas fases preparadas em duas worktrees reais; dois processos em background
escrevendo cada um na sua; `kill -9` no primeiro enquanto o segundo está
comprovadamente em voo (ele bloqueia num marcador até o teste ter matado o
irmão). `wait` devolvendo **137** é a asserção de que a morte foi real — uma
morte simulada não produz 137.

Depois: o sobrevivente escreveu, commitou na própria branch e liberou o
próprio lease (`held=false`); o arquivo meio-escrito existe **só** na árvore
que o escreveu; e depois de `rm -rf` na árvore morta, `cleanup` nomeia o
registro e o lease, e `--apply` faz `prune` + `release`.

### Prova por quebra — cada regra, medida

Cada quebra foi aplicada, medida vermelha, e o arquivo restaurado
byte-a-byte a partir de um backup `cp` (sha256 idêntico antes e depois de
cada uma; conferido no fim com `diff`):

| quebra | testes vermelhos |
|---|---|
| regra de órfão por TTL em vez de inventário | 2 (27 e 28) |
| registro morto contado como worktree viva | 1 (27) |
| sem checagem `rev-list HEAD..<branch>` | 1 (29) |
| sem checagem `git status --porcelain` | 1 (30) |
| sem guard de inventário | 1 (31) |
| sem guard de lease em mãos da árvore | 1 (28) |

Verde antes: 31/31. Vermelho durante cada quebra: como na tabela. Verde
depois: 31/31.

## Desvios do plano

### Auto-corrigidos

**1. [Rule 2 - funcionalidade crítica ausente] Lease em mãos da própria árvore retém a worktree**

- **Encontrado em:** Task 1, ao desenhar `removable`.
- **Problema:** o plano define `removable` como "worktree de fase limpa e já
  inteiramente mesclada em `HEAD`". Uma worktree recém-preparada por
  `prepare`, onde o agente ainda nem escreveu, é exatamente isso — limpa e com
  zero commits à frente. `--apply` a apagaria debaixo de um agente vivo.
- **Correção:** qualquer lease `held` cujo holder seja aquela worktree
  (stale ou não) manda a árvore para `retained`. Staleness deliberadamente não
  discrimina aqui, pela mesma razão que não discrimina em `stale_but_live`:
  recusar liberar o lease e ao mesmo tempo apagar a árvore embaixo dele seria
  a meia-medida incoerente.
- **Arquivos:** `cairn/scripts/cairn-parallel.py`
- **Commit:** ccfbf62

**2. [Rule 2 - funcionalidade crítica ausente] Inventário não confiável é parada dura**

- **Encontrado em:** Task 1, revisando T-18-11.
- **Problema:** `worktree_entries()` devolve `[]` quando o `git worktree list`
  falha. Com lista vazia, *todo* holder do repo fica "fora do inventário" e
  `--apply` liberaria todos os leases de uma vez.
- **Correção:** se o inventário não contém o próprio checkout principal, sai
  `EXIT_GIT` sem decidir nada. Teste 31 e o `<automated>` da quebra 5.
- **Arquivos:** `cairn/scripts/cairn-parallel.py`, `cairn/scripts/cairn-parallel.sh` (código 4 na tabela)
- **Commit:** ccfbf62

**3. [Rule 3 - bloqueio] `.gitignore` no fixture, ou `removable` nunca dispara**

- **Encontrado em:** Task 2, com o teste 28 medindo `reasons | length` = 2 em
  vez de 1.
- **Problema:** `prepare` toma o lease de dentro da worktree nova, o
  `cairn-lease` registra isso no journal, e o journal cai em
  `<worktree>/.cairn/journal.jsonl` — a divisão que o próprio docstring do
  18-01 já registrava. Sem regra de ignore, `git status --porcelain` reporta
  `?? .cairn/` em **toda** worktree preparada: ela é permanentemente suja e
  `removable` seria código morto na prática.
- **Correção:** `make_parallel_fixture` passa a commitar um `.gitignore` com
  `.cairn/journal.jsonl*`, que é literalmente o que o repo do cairn ignora
  (`.gitignore:8`). O fixture sem a regra é que era o infiel. A consequência
  ficou escrita no docstring como nota medida: um projeto que não ignore esse
  caminho retém as worktrees para sempre — direção de falha correta, e por
  isso é nota e não caso especial no código.
- **Arquivos:** `tests/cairn-parallel.bats`, `cairn/scripts/cairn-parallel.py` (nota)
- **Commits:** d6fa08f (fixture + testes), d4fb371 (a nota medida no docstring)

## O que o plano errou

**1. A verificação do `grep -c 'stash'` já era falsa antes deste plano.**
O plano pede que o grep "só encontre a menção no docstring". Medido:
`grep -c 'stash' cairn/scripts/cairn-parallel.py` = **6**. Cinco linhas são o
docstring (a proibição e a razão, linhas 104-116) e a sexta é a linha 1009 —
o banner da região `RECONCILE-READ-ONLY-REGION`, do plano 18-02, que
**precisa** nomear `["stash"` na forma exata que o teste estático procura, ou
estaria enunciando uma regra em palavras que a checagem não consegue ver. Ou
seja: a expectativa do plano já estava violada quando ele foi escrito, por
código que o próprio 18-02 introduziu de propósito.

O que importa foi verificado diretamente e é verdade: **não existe nenhuma
invocação de `git stash` no arquivo** — nenhum `["stash"` numa lista de args,
nenhum `run_git(... stash ...)`. A verificação certa seria "nenhuma linha é
uma invocação", não "só uma linha menciona".

**2. O plano descreve `removable` como "o encerramento normal depois da
reconciliação" sem notar que, do jeito que `prepare` funciona, isso nunca
aconteceria** num projeto que não ignore `.cairn/journal.jsonl`. Ver desvio 3.

**3. O `<behavior>` da Task 1 não previu o caso da worktree recém-preparada**
(limpa, mesclada, e com um agente dentro dela). Ver desvio 1.

**4. Uma correção ao 18-02-SUMMARY.md, não a este plano.** Aquele resumo
afirma que "o bats reporta zero testes como sucesso". Medido aqui no bats
1.14.0 deste repo: `bats tests/cairn-parallel.bats -f "cleanup relata"` sai
**1** com `ERROR: Found no tests. (Try --allow-empty-suite?)`. Falha alta, não
falso verde. O comentário do `<verify>` **deste** plano já dizia isso
corretamente; quem está errado é o resumo do 18-02.

## Decisões não cobertas pelo plano

- **`orphan_registration` é relatado no repo inteiro**, não só para worktrees
  de fase, porque `git worktree prune` é repo-wide. Um relatório mais estreito
  que a ação que ele dispara subestimaria o que `--apply` está prestes a
  fazer.
- **`git worktree remove` sem `--force` e `git branch -d` em vez de `-D`**:
  as formas seguras de propósito, para que o git reconfira "limpa" e
  "mesclada" pelos critérios dele e recuse se a leitura deste script estiver
  errada. Dois vereditos independentes para um ato irreversível.
- **`worktree_dirty()` e `commits_ahead()` retêm quando não conseguem medir**
  (status ilegível, contagem que falha). O que não é mensurável nunca é
  removível.
- **`retained` carrega `reasons[]` (lista) e um `manual_command`**, escolhido
  pela primeira razão em ordem de prioridade: não commitado → mostrar o
  status; não mesclado → `git merge <branch>`; lease em mãos → `cairn-lease
  status <N>`.

## Verificação do plano

| passo | resultado |
|---|---|
| `bats tests/cairn-parallel.bats` inteiro | 31/31 verde |
| `cairn-parallel.sh cleanup --json` em repo sem worktree de fase | exit 0, todas as listas vazias |
| `grep -c 'stash' cairn-parallel.py` | 6 — ver "O que o plano errou", item 1 |

O filtro `<automated>` do plano (`bats tests/cairn-parallel.bats -f "cleanup"`)
casa 6 testes (os 5 novos mais o de `--help`, que agora lista `cleanup`) e sai
0.

## Self-Check: PASSED

- `cairn/scripts/cairn-parallel.py` — presente, modificado
- `cairn/scripts/cairn-parallel.sh` — presente, modificado
- `tests/cairn-parallel.bats` — presente, modificado
- commit `ccfbf62` — presente
- commit `d6fa08f` — presente
- commit `d4fb371` — presente
