---
phase: 30-did-it-land
plan: "03"
subsystem: sync
tags: [gh, glab, config, cache, timestamp, offline, bats]

requires:
  - phase: 30-02
    provides: "pr.numbers por fase — os números que este plano vai buscar, e que ele não inventa"
provides:
  - "cairn-review.py: a única superfície do cairn que fala com a forge, atrás de git.review_state (default off)"
  - ".cairn/pr-cache.json com fetched_at, e pr.review no relatório com age_seconds e stale"
  - "o sufixo do board com o estado E a idade, nunca um sem o outro"
  - "tests/cairn-review.bats: 11 testes, incluindo a fronteira afirmada pelo lado da rede"
affects: [status, sync-config, ship]

actuals:
  tokens: 0
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns:
    - "fronteira estrutural em vez de promessa: a rede num arquivo que o board não alcança, e dois inventários independentes afirmando isso de lados opostos"
    - "cache sem carimbo é tratado como ausente, nunca como atual"
    - "resposta vazia nunca sobrescreve resposta velha carimbada"

key-files:
  created:
    - cairn/scripts/cairn-review.py
    - cairn/scripts/cairn-review.sh
    - tests/cairn-review.bats
  modified:
    - cairn/scripts/cairn-land.py
    - cairn/scripts/cairn-status.py
    - cairn/scripts/cairn-config.py
    - cairn/docs/commands/status.md
    - cairn/docs/commands/config.md
    - tests/cairn-config.bats
    - .gitignore

key-decisions:
  - "A rede vai para um ARQUIVO separado, não para uma flag do cairn-land.py: um `gh` escrito ali deixaria a camada 3 vermelha, e ela estaria certa"
  - "`off` sai 3, não 0 e não erro: o interruptor desligado é a resposta à pergunta"
  - "Cache sem `fetched_at` é ausente. Não existe ramo em lugar nenhum que renderize um estado sem idade"
  - "Um fetch sem nenhuma resposta deixa o cache anterior intacto"

patterns-established:
  - "Duas afirmações independentes da mesma fronteira, de lados opostos, quando ela é a alegação que sustenta a fase inteira"

requirements-completed: [PR-03]

duration: 40min
completed: 2026-08-06
status: complete
---

# Fase 30 Plano 03: o estado de revisão atrás de config, com cache carimbado — Resumo

**A rede não entrou no caminho do board, e isso agora é estrutura, não
promessa.**

## A restrição que decidiu o desenho

O 30-01 provou em três camadas que o `cairn-land.py` não faz rede. Escrever um
`subprocess.run(["gh", …])` ali deixaria a camada 3 vermelha — e ela estaria
**certa**. Então a rede foi para um arquivo que o board não alcança:

```
cairn-status.py  ->  cairn-land.py  ->  git, e o ARQUIVO de cache
cairn-review.py  ->  gh / glab                      (nunca ao contrário)
```

E a fronteira é afirmada **duas vezes, de lados opostos e por mecanismos
independentes**: os inventários de AST do `cairn-land.bats` (2 sítios) e do
`cairn-tracker-card.bats` (5 sítios) do lado offline, e um teste no
`cairn-review.bats` que varre os dois arquivos procurando `gh`/`glab`/`curl`/
`wget` do lado da rede — com a contraprova de que o mesmo scan **encontra** os
nomes no `cairn-review.py`, para que o verde não venha de um scan quebrado.
Verificado por mutação: um `gh` escrito no `cairn-land.py` derruba as duas.

## O que mudou

- **`git.review_state`**: enum `off` | `gh` | `glab`, default **`off`**. Com
  `off`, `fetch` sai **3** tendo lido uma chave de config e tocado em nada
  mais. E o teste prova que `off` não é "a ferramenta faltou": o stub de `gh`
  está no `PATH`, observável, e o log dele fica vazio.
- **`cairn-review.py fetch`** pega os números do `cairn-land.py report --json`
  — não inventa número e não relê git. Um fato, um dono.
- **`.cairn/pr-cache.json`** (gitignored, estado por máquina) com
  `fetched_at` em ISO 8601 UTC no topo.
- **O relatório anexa `pr.review`** com `state`, `fetched_at`, `age_seconds`,
  `stale` e `tool`. `stale` é um booleano **ao lado** da idade, não no lugar
  dela: quem discorda do limiar de 24h ainda tem os segundos.
- **O board renderiza `⤒ origin/main · #18 merged (5d ago, stale)`.** O estado
  **nunca** aparece sem a idade.

## As duas regras que impedem um cache de mentir

**Cache sem carimbo é ausente, não fresco.** Um `pr-cache.json` sem
`fetched_at` faz `read_review_cache()` devolver nada, e o relatório responde
`review: null` enquanto continua respondendo tudo o que sabe offline. Não
existe um ramo em lugar nenhum que renderize um estado sem idade.

**Resposta vazia não sobrescreve resposta velha.** Um `fetch` em que a forge
não respondeu por nenhuma PR sai 5 e **deixa o cache anterior intacto**.
Trocar uma verdade velha carimbada por um vazio recém-escrito é a mesma falha
com outra roupa.

## Verificação por mutação — quatro quebras

| Quebra aplicada | Asserção que ficou vermelha |
|---|---|
| aceitar cache sem `fetched_at` | `a cache with no fetched_at is treated as absent` |
| renderizar o estado sem a idade | `the board renders the cached state with its age, or not at all` |
| buscar com o interruptor `off` | `with the switch off, fetch makes no call and writes nothing` |
| escrever um `gh` no `cairn-land.py` | `the network tools appear in cairn-review.py and in no other script` **e**, independentemente, `every subprocess.run in cairn-land.py invokes an allowlisted binary` |

## Suítes

`cairn-review.bats` 11/11 · com `cairn-land`, `cairn-config`,
`cairn-board-invariance`, `cairn-tracker-card`, `cairn-group-model` e
`cairn-status`: **176 verdes, 0 vermelhos**.

## O que eu recusei fazer

**Não fiz nenhuma chamada de rede real, em teste nenhum.** O `gh` da suíte é um
stub no `PATH` que responde de um payload enlatado, então o caminho de fetch é
exercitado de verdade sem nunca sair da máquina.

**Não li nem escrevi credencial em lugar nenhum.** O `gh`/`glab` carregam a
autenticação deles e este script nunca a vê — não há campo, flag ou variável
neste arquivo que pudesse conter um token.
