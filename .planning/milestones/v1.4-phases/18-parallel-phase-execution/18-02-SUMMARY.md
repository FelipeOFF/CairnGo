---
phase: 18-parallel-phase-execution
plan: "02"
subsystem: parallel-execution
tags: [python, bash, bats, git, merge, reconciliation]
requires:
  - "cairn-parallel.py phase_layout() — os nomes phase/<N>-<slug> que o 18-01 travou"
  - "git merge-tree --write-tree (git >= 2.38) — conflito pré-calculado sem working tree"
provides:
  - "cairn-parallel.py reconcile — o detector de edição convergente (D-02)"
  - "EXIT_FINDINGS=6 — o mecanismo que impede um merge silenciosamente limpo de passar"
  - "o incidente 14/15 como fixture reproduzível, com as duas medições no mesmo teste"
affects:
  - "cairn/commands/autonomous.md — consumidor futuro do relatório ao fechar as fases paralelas"
  - "cairn-parallel.py cleanup (18-03) — mesmo arquivo, mesmos subparsers"
tech-stack:
  added: []
  patterns:
    - "docstring como spec canônica, com o medido separado do assumido e o limite medido escrito"
    - "garantia de não-escrita provada duas vezes: grep sobre região marcada + teste de mutação"
    - "marcadores RECONCILE-READ-ONLY-REGION-* delimitando a região que o teste estático extrai"
    - "merge de verificação sempre em clone descartável, e reconcile sempre ANTES dele"
key-files:
  created: []
  modified:
    - cairn/scripts/cairn-parallel.py
    - cairn/scripts/cairn-parallel.sh
    - tests/cairn-parallel.bats
key-decisions:
  - "A comparação de igualdade de CONTEÚDO só é provável no fixture 3 (conflito), não nos 1 e 2 como o plano supunha — medido, e a asserção foi para lá"
  - "Grep estático casa o verbo de git na CABEÇA da lista de args (`[\"branch\"`), porque `branch` e `worktree` também são chaves legítimas do JSON de saída"
  - "Marcadores da região renomeados para RECONCILE-READ-ONLY-REGION-*: o docstring repetia o marcador literal e o range do awk engolia prepare e batch inteiros"
  - "Bloco novo vazio idêntico dos dois lados (as duas branches apagando a mesma faixa) conta como convergente — é acordo que ninguém revisou, pela mesma regra"
  - "Filtros pt-BR do `<verify>` do plano (`-f \"reconcile relata\"`) casam zero testes e o bats reporta zero testes como sucesso — verify trocado por `-f \"reconcile\"` / `-f \"read-only\"`"
metrics:
  duration: ~90min
  tasks: 3
  commits: 3
  tests: 26 (16 herdados + 10 novos)
  completed: 2026-07-31
actuals:
  tokens: 13495
  tasks: 3
  commits: 3
status: complete
---

# Phase 18 Plan 02: reconcile — a edição convergente Summary

**O git reporta conflito e reporta bem; o que ele não reporta é a concordância
acidental — a linha que as duas branches mudaram para o MESMO valor e que ele
funde em silêncio. `reconcile` reporta essa, e é a classe que estragou este
repo quando as fases 14 e 15 foram mescladas.**

## O que foi construído

`cairn-parallel.py reconcile [--phases 7,9] [--project-dir DIR] [--json]` —
relatório read-only que descobre o trabalho varrendo `refs/heads/phase/*` (o
nome que o `prepare` deu, nunca o que um agente declara — D-01) e devolve
`{git_version, branches[], pairs[], planning_writes[], findings_total}`.

- **`branches[]`** — o que cada fase produziu (PAR-04): commits, arquivos,
  inserções e deleções contra `git merge-base HEAD <branch>`.
- **`pairs[]`** — por par não ordenado: `convergent_edits`, `conflicts`,
  `conflicts_note`.
- **`planning_writes[]`** — branch de fase que tocou `STATE.md`/`ROADMAP.md`/
  `REQUIREMENTS.md` (D-03). Achado nomeado, **sem efeito no exit code**.
- **Exit 6** com achado, com conflito, ou com `conflicts: null`. Exit 0 sem
  nada. Um planning write sozinho **não** move o código.

O par `.sh` moveu em lockstep: o comentário de exit codes do wrapper cita o 6
com a mesma redação do docstring.

## A detecção, exatamente como medida

Para cada par: base = `git merge-base X Y`; cada lado vira, por arquivo, uma
lista de `(início na base, quantas linhas da base são substituídas, as linhas
novas verbatim)` a partir de `git diff -U0 base..lado`. **Edição convergente**
= mesma faixa da base nos dois lados **E** bloco de linhas novas byte a byte
idêntico. Nada mais frouxo que isso.

Os três números do plano foram **reproduzidos nesta sessão**, não herdados:

| Medição | Resultado |
|---|---|
| `merge-tree --write-tree` na forma real (contagem convergente + bloco distinto distante) | exit 0, **nenhuma** linha CONFLICT |
| `git merge` real, em clone | exit 0, `Auto-merging checks.txt`, `1 insertion(+)`; arquivo com `checks = 14` e **dois** `check 13` |
| hunks `-U0` dos dois lados | `@@ -1 +1 @@` idêntico, faixa e conteúdo — o que a igualdade estrita pega |
| classe silenciosa pura, merge 1 | `a.txt \| 1 +` **e** `shared.txt \| 2 +-` |
| classe silenciosa pura, merge 2 | só `b.txt \| 1 +` — o arquivo compartilhado some por completo |
| limite medido (bloco adjacente à contagem) | `@@ -1 +1,2 @@` nos dois lados, convergência **não** declarada, e o git conflita sozinho (`merge-tree` exit 1) |

O limite medido está escrito no docstring com o arranjo que o produz. A lacuna
do detector coincide com o acerto do git: nesse arranjo o operador para de
qualquer jeito.

## Testes: 26 verdes (16 herdados + 10 novos)

Cada quebra nomeada foi **executada de fato**, vista vermelha e restaurada
byte a byte (backup por `cp`, nunca `git checkout` sobre arquivo com trabalho
não commitado). Verde de partida: 11/11 na fatia `reconcile|read-only`.

| Quebra | O que muda | Resultado |
|---|---|---|
| 1 | remove a comparação de igualdade de **conteúdo** | 10/11 — vermelho no **fixture 3** |
| 2 | igualdade estrita de **faixa** → sobreposição | 5/11 — vermelho nos fixtures 1, 3, 4, 5, 6 e no teste de mutação |
| 3 | bloco **adjacente** à contagem (perturbação de fixture) | convergência deixa de ser declarada; git conflita — **limite medido, não bug** |
| 4 | degradação devolve `[]` em vez de `None` | 10/11 — vermelho no fixture 6 |
| 5 | `planning_writes` passa a mover o exit code | 10/11 — vermelho no fixture 5 |
| 6 | um `["checkout"` dentro da região | 10/11 — vermelho no teste estático |
| 7 | `reconcile` passa a escrever um arquivo | 9/11 — vermelho no teste de mutação (e no fixture 3) |
| 8 | filtro `grep -v '^#'` removido **do teste** | 10/11 — vermelho no teste estático |

Fixture 1 carrega as **duas medições no mesmo teste**, lado a lado, porque é o
par que documenta por que o comando existe: o `git merge` de verdade num clone
descartável sai 0 sem nenhuma linha de conflito e o arquivo mergeado tem os
dois blocos numerados igual, enquanto `reconcile` nomeia `checks.txt:1` e as
duas branches, exit 6.

Fixture 2 pina a **dependência de ordem**: o primeiro merge ainda lista
`shared.txt` no diffstat; só o **segundo** não cita o arquivo de forma alguma.

Em todo teste o `reconcile` roda **antes** de qualquer merge, e todo merge de
verificação acontece em clone descartável — um merge na árvore do fixture move
a branch e o `merge-base` seguinte já conteria o que o detector procura.

## Deviations from Plan

### O plano estava errado num ponto, e foi medido

**1. [Rule 1 — plano incorreto] A quebra nomeada para os fixtures 1 e 2 não
quebra nada lá.**
- **Achado em:** Task 2, ao executar a quebra que o plano nomeia
  ("retirar a comparação de igualdade de conteúdo deixa os fixtures 1 e 2
  vermelhos").
- **Medido:** 11/11 continuam verdes com a comparação removida. Nos fixtures 1
  e 2 o único hunk co-localizado **é** o convergente, então tirar a comparação
  de conteúdo não muda o que é reportado ali.
- **Onde ela realmente dói:** fixture 3 (conflito). Medido: as duas branches
  inserem no mesmo ponto, os dois lados emitem `@@ -10,0 +11 @@` — **mesma
  faixa, texto diferente**. Sem uma asserção lá, a comparação de conteúdo
  ficava inteiramente sem cobertura.
- **Correção:** `assert_json_eq '.pairs[0].convergent_edits | length' '0'` no
  teste do fixture 3, com o motivo escrito no comentário. Depois: 10/11, a
  quebra fica vermelha. Os comentários "how to break it" dos fixtures 1 e 2
  foram reescritos com a quebra que de fato os derruba (afrouxar a igualdade
  de faixa).
- **Commit:** ae5b7c1

### Ajustes de execução

**2. [Rule 3] Marcadores da região renomeados.** O docstring descreve os
marcadores e o plano manda gravar essa descrição nele; com o marcador literal
repetido no docstring, o range do `awk` começava **no docstring** e engolia
`prepare` e `batch` inteiros (20 casamentos de verbo de escrita, todos
legítimos, todos fora do `reconcile`). Marcadores viraram
`RECONCILE-READ-ONLY-REGION-BEGIN`/`-END` e o docstring passou a citá-los sem
reproduzir a forma exata — exatamente o que a Task 3 manda ("ajuste o texto do
docstring, nunca o alvo do grep").

**3. [Rule 3] Grep de verbo de git casa na cabeça da lista de args.**
`"branch"` e `"worktree"` são chaves legítimas do JSON que este script emite;
`["branch"` só pode ser invocação de `git branch`. Efeito colateral correto:
`["merge-base"` e `["merge-tree"` não casam `["merge"`, então os subcomandos
de leitura sobrevivem de graça.

**4. [Rule 2] Filtro de comentários provado load-bearing.** O banner da região
nomeia os tokens proibidos na forma exata que o grep procura, e o teste afirma
que a mesma checagem **sem** o filtro os encontra. Sem isso, alguém
"simplifica" o filtro e o teste passa a ler só comentários. Quebra 8 acima.

**5. [Rule 2] Dois testes além dos seis fixtures do plano:** repo sem nenhuma
branch `phase/*` (exit 0, listas vazias, linha dizendo que não há o que
reconciliar — é o `<done>` da Task 1, que não tinha teste próprio) e
`--phases` (restringe; valor não numérico é erro de uso, não filtro
silenciosamente vazio — um filtro que não casa nada produziria um relatório
vazio e tranquilizador).

**6. [Rule 3] Teste 16 (`--help`) estendido em lockstep** para exigir
`reconcile` na saída, junto com `batch` e `prepare`.

### Decisão não coberta pelo plano

**Bloco novo vazio idêntico dos dois lados** (as duas branches deletando a
mesma faixa da base) satisfaz a regra e é reportado como convergente. O plano
fala em "bloco de linhas novas byte a byte idêntico" sem se pronunciar sobre o
caso vazio. Escolhido incluir, e escrito no docstring: dois acordos silenciosos
sobre o que deve sumir continua sendo um acordo que ninguém revisou.

## Verificação

- `bats tests/cairn-parallel.bats` — **26/26 verdes**.
- `bash cairn/scripts/cairn-parallel.sh reconcile --json` neste repo (sem
  branch `phase/*`) — exit 0,
  `{"git_version":"2.42.1","branches":[],"pairs":[],"planning_writes":[],"findings_total":0}`.
- Cabeçalho de `cairn-parallel.sh` cita o código 6 com a mesma redação do
  docstring (`.sh:9-12` ↔ `.py:333-335`).

**Nota sobre os `<verify>` do plano:** `bats ... -f "reconcile relata"` e
`-f "reconcile"` são filtros em pt-BR contra uma suíte cujos testes são
nomeados em inglês (todos os 16 herdados são). `-f "reconcile relata"` casa
zero testes, e o bats trata zero testes casados como **sucesso** — o verify
teria ficado verde sem executar nada. Usados `-f "reconcile"` e
`-f "read-only"`, que casam de fato.

## Known Stubs

Nenhum.

## Self-Check: PASSED

- `cairn/scripts/cairn-parallel.py` — FOUND
- `cairn/scripts/cairn-parallel.sh` — FOUND
- `tests/cairn-parallel.bats` — FOUND
- commit `4fd8557` (feat, Task 1) — FOUND
- commit `ae5b7c1` (test, Task 2) — FOUND
- commit `3269043` (test, Task 3) — FOUND
