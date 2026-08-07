---
phase: 26-the-cairn-wrappers
plan: "02"
status: complete
requirements: [WRAP-03]
beads: [CairnGo-5mu]
subsystem: cairn/docs
tags: [wrappers, derived-docs, wrap-03, drift]
provides:
  - "cairn-wrap docs — a lista de wrappers derivada do disco, entre marcadores"
  - "cairn/docs/commands.md sem total escrito à mão, com os 25 comandos visíveis"
  - "páginas para /cairn:config e /cairn:reconcile, que existiam e não eram documentados"
key-files:
  created:
    - cairn/docs/commands/phase.md
    - cairn/docs/commands/config.md
    - cairn/docs/commands/reconcile.md
  modified:
    - cairn/scripts/cairn-wrap.py
    - cairn/docs/commands.md
    - tests/cairn-wrap.bats
---

# Phase 26 Plan 02: A documentação vira vista do disco

A lista de wrappers sai do frontmatter dos arquivos instalados. A página perdeu
os três defeitos que carregava, e ganhou um teste que reprova a reintrodução de
cada um.

## O gerador nasceu vermelho, e isso é o resultado principal

A medição foi feita **antes de qualquer edição de documentação**, com a página
exatamente como estava no `main`:

```
$ cairn-wrap.sh docs --check --json                       → exit 3
{ "changed": true,
  "orphan_pages": ["bookkeep"],
  "undocumented": ["config", "reconcile"],
  "wrappers": [] }
```

O script achou **os mesmos dois comandos** que o levantamento à mão tinha achado
no `26-CONTEXT.md` (`/cairn:config` e `/cairn:reconcile`), sem que eu dissesse os
nomes a ele — e mais um que eu não tinha ligado: `commands/bookkeep.md`, página
para o que não é comando.

Um gerador que nascesse verde contra um estado doente estaria errado, e este
plano tinha isso como precondição escrita.

## O que ficou pronto

**`cairn-wrap.py docs [--check]`** — regenera o bloco entre
`<!-- cairn:generated:start/end -->`, o idioma que o `cairn-map.py` já
estabeleceu. Três partes, todas derivadas:

1. **A frase de contagem.** `cairn ships **26** commands: **1** wraps a /gsd:*
   … and **25** are cairn's own`. Nenhum número escrito à mão sobrevive na
   página.
2. **A tabela**, agrupada por `wrap-family`, com a descrição vinda do
   frontmatter — nunca redigitada.
3. **A sobra, nomeada.** `⚠ Not documented:` para comando sem linha,
   `⚠ Orphan page:` para página sem comando.

**A sobra ser visível é deliberado e é o oposto de esconder.** Um gerador que
omitisse `/cairn:config` teria preservado exatamente o estado que este plano
existe para consertar. O aviso some sozinho quando a linha existe — provado nos
dois sentidos pelo teste 18.

**A página consertada:** o total escrito à mão saiu; `/cairn:reconcile` entrou em
*Migrate & health*; `/cairn:config` ganhou seção própria; e as três páginas que
faltavam (`phase.md`, `config.md`, `reconcile.md`) foram escritas a partir do
comando e do script que ele chama, não de memória.

`bookkeep.md` **fica** como órfã visível — o `26-CONTEXT.md` § Deferred já
registrava que decidir se `bookkeep` vira comando é decisão, não mecânica. O
requisito é a página não mentir, não a página ficar bonita.

## As provas, cada uma com a quebra que a deixa vermelha

| teste | o que prova | quebra medida |
|---|---|---|
| 13 | **acrescentar um wrapper faz a página listá-lo, e nada fora dos marcadores muda** — o de-fora é congelado e comparado byte a byte antes/depois | tabela por lista literal → **vermelho** |
| 14 | `--check` sai **3** com diff nomeando o wrapper novo | mesma quebra → **vermelho** |
| 15 | `--check` sai **0** quando está atual | sem este par, o 14 passaria com um `--check` que sempre sai 3 |
| 16 | prosa de antes e de depois sobrevive; o bloco entra **uma** vez, e uma segunda corrida não anexa outro | |
| 17 | corrida sem mudança não escreve — **sha256 E mtime** | reescrita incondicional muda o mtime |
| 18 | a sobra é nomeada, e o aviso some sozinho quando a linha existe | omitir a sobra → vermelho |
| 19 | página órfã é nomeada | |
| 20 | a página **real** está atual e `undocumented` é vazio | acrescentar comando sem linha → vermelho |
| 21 | a página real não tem total escrito à mão fora do bloco | reintroduzir `N in total` → vermelho |

A quebra do 13/14 foi aplicada de verdade (linha da tabela filtrada por lista
literal), medida, e revertida por cópia — `cp` da original, nunca
`git checkout`.

## Desvios do plano

### 1. [Rule 1 — o teste 21 pegou a mim mesmo, no commit que o criou]

O guarda contra total escrito à mão (`' in total'` fora dos marcadores) ficou
**vermelho na primeira corrida** — porque a prosa nova que eu tinha acabado de
escrever *citava* o defeito: «this page said "22 in total"…».

Havia duas saídas: afrouxar o guarda, ou reescrever a frase. **Afrouxar seria
tirar os dentes do único teste que pega a reintrodução**, então a frase foi
reescrita para contar a história sem reproduzir o padrão («once claimed 22
commands while linking 23 pages with 25 on disk»). O guarda ficou literal.

### 2. [Rule 1 — expectativa de teste errada, comportamento certo]

O teste 18 esperava `undocumented == "ghost,solo"`. O script devolveu `"ghost"`,
e estava certo: `solo` é um **link sem arquivo de comando** — a direção órfã, que
o teste 19 cobre — enquanto `ghost` é arquivo de comando sem link, que é o que
`config` e `reconcile` eram. A expectativa foi corrigida e a distinção ficou
escrita em comentário, porque confundir as duas direções é fácil.

### 3. [Decisão de escopo] A prova em campo, à mão, fica para o plano 03

A verificação 2 deste plano pedia acrescentar um wrapper de mentira ao
`cairn/commands/` real e medir o `--check`. **Não foi feito com um arquivo de
mentira**, por dois motivos: a suíte grande estava rodando contra essa mesma
árvore, e o plano 03 faz a mesma demonstração com **doze wrappers de verdade**,
que é mais forte que um fake. A prova por fixture (teste 13) já está verde.

### 4. [Rule 2] O bloco foi movido para antes de `## See also`

O `splice` anexa ao fim quando não há marcadores, e o fim ficava depois do
"See also" — leitura ruim. Movido uma vez, à mão; a partir daí o `splice`
substitui **no lugar**, então a posição é permanente. Também corrigido o plural
da frase de contagem (`1 wraps`, `2 wrap`).

## Verificação

- `bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-wrap.bats` —
  **1..21 anunciados, 21 executados, 21 `ok`, 0 `not ok`**.
- `docs --check` contra a página real → **0**; `--json` → `undocumented: []`.
- Idempotência à mão: `sha stable`, `mtime stable`.

## Self-Check: PASSED

- `cairn/docs/commands/phase.md`, `config.md`, `reconcile.md` — existem
- `cairn/docs/commands.md` — bloco gerado presente, sem total à mão
- commit `153e31b` — existe
