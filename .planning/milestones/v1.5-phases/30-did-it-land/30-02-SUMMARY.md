---
phase: 30-did-it-land
plan: "02"
subsystem: ui
tags: [git, pull-request, unknown, offline, bats]

requires:
  - phase: 30-01
    provides: "cairn-land.py, a atribuição de commit a fase, e o relatório que este plano estende"
provides:
  - "pr por fase no relatório e no --json: vocabulário de duas palavras, found e unknown, com motivo nomeado"
  - "o sufixo · #N no board, condicional ao número existir"
  - "o teste de aceitação contra a PR #21 real deste repositório"
affects: [status, doctor, ship]

actuals:
  tokens: 0
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns:
    - "um vocabulário sem a palavra que a fonte não pode justificar: `unknown` existe, `none` não"
    - "teste de aceitação contra o histórico real, com a premissa ASSERTADA e um skip nomeado se ela cair"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-land.py
    - cairn/scripts/cairn-status.py
    - cairn/docs/commands/status.md
    - tests/cairn-land.bats

key-decisions:
  - "Duas palavras, e a terceira é proibida por desenho: 'não há PR' é afirmação sobre a forge, e o script só leu um repositório git"
  - "`no-commits` e `no-reference` são silêncios diferentes e recebem valores diferentes"
  - "O assunto de merge vence o parêntese final: ali o `(#99)` é o nome da branch, não uma segunda PR — asserção corrigida de `6,99` para `6` pela medição"
  - "O board não imprime nada para `unknown`: um card que não imprime nada não afirma nada, e cobrar ausência é do doutor"

patterns-established:
  - "Quando a medição contradiz a asserção que você acabou de escrever, a asserção muda e o motivo vai no comentário — não o contrário"

requirements-completed: [PR-02]

duration: 35min
completed: 2026-08-06
status: complete
---

# Fase 30 Plano 02: a PR não descobrível é `desconhecido`, nunca "sem PR" — Resumo

**O vocabulário tem duas palavras e a terceira é proibida por desenho.**

## O caso que decide se a fase foi honesta, medido

`7fa133c` — a PR **#21**, que trouxe o milestone v1.4 inteiro — é um merge
commit de verdade (dois pais) cujo assunto é `v1.4 Honest State: phase state
that proves what it claims (ships cairn 1.5.0)`. **Nem o assunto nem o corpo
nomeiam número nenhum.** A premissa não é afirmada por este resumo: está
assertada dentro do teste, que pula com mensagem nomeada se `7fa133c` deixar de
existir no checkout.

E o resultado contra este repositório inteiro:

```
fases localizadas ......................... 24
pr unknown :: no-reference ................ 24
pr found .................................. 0
```

**Cem por cento.** Uma implementação que respondesse "sem PR" estaria mentindo
sobre as 24, com a suíte verde. É exatamente por isso que `none` não existe no
vocabulário: `unknown` é um fato sobre o histórico, "não há PR" é uma afirmação
sobre o GitHub, e nada offline pode fazê-la.

## O que mudou

- `pr` por fase: `{status, number, numbers, source, commit, reason, detail}`.
  `source` é `merge-subject` ou `squash-subject`, valores exatos.
- `reason` distingue **dois silêncios**: `no-commits` (nada atribuído à fase) e
  `no-reference` (há commits, nenhum nomeia PR). Colapsá-los seria perder a
  diferença entre "não achei a fase" e "achei a fase e ela não deixou rastro".
- `detail` nomeia o **limite**, não faz afirmação: *"the local git history is
  the only source consulted — a merge or squash whose subject was rewritten
  leaves no reference behind, so an absent number is never evidence that no
  pull request existed."*
- O board ganha `· #18` dentro do sufixo `⤒`, condicional ao número existir.

## A medição que contradisse a asserção que eu tinha acabado de escrever

Escrevi o teste do assunto de merge afirmando `numbers == "6,99"` para
`Merge pull request #6 from FelipeOFF/feat/alpha (#99)`. Ficou vermelho, e a
implementação estava certa: **um assunto nomeia uma PR**. O `(#99)` ali é o
nome da branch que o GitHub colou, não uma segunda entrega. Reportar as duas
seria o board inventar uma entrega que nunca houve. A asserção virou `6`, o
motivo foi para o comentário, e a propriedade real — uma fase entregue por duas
PRs reporta as duas — ganhou um teste próprio com dois commits distintos.

## Verificação por mutação — três quebras

| Quebra aplicada | Asserção que ficou vermelha |
|---|---|
| imprimir `"no PR"` no lugar de `pr unknown :: <reason>` | `no surface prints the words that would claim there is no pull request` |
| introduzir um terceiro veredito `none` | `unknown with no-reference` **e** o teste de aceitação `the real #21 of this repository is unknown` |
| testar o padrão de squash antes do de merge | `outranks a trailing paren` → `.source` `merge-subject` → `squash-subject` |

Com `cp` prévio e restauro **da cópia**; `diff` final vazio.

## Suítes

`cairn-land.bats` 34/34 · com `cairn-board-invariance`, `cairn-group-model` e
`cairn-status`: **117 verdes, 0 vermelhos**. Os sete renders de referência
seguem intocados.
