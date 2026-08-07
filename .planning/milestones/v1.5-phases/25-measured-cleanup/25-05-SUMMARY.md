---
phase: 25-measured-cleanup
plan: "05"
requirement: FIX-02
beads: [CairnGo-rhq, CairnGo-r4g]
status: complete
---

# Fase 25 Plano 05 — resumo

## O que mudou

O `cairn-parallel` para de reter um worktree por causa do journal, e o nome da
branch de uma fase para de mudar quando o diretório da fase aparece depois.

## CairnGo-rhq — o journal deixa de ser motivo de retenção (D-05)

`worktree_dirty()` passa a ignorar `.cairn/journal/`, e só ele. É a decisão
D-05, defendida pelo `DJOUR-03`: o journal é o único artefato do cairn cuja
perda **não muda veredito nenhum**, e é por isso que ele não pode reter — reter
é o que se faz com trabalho que o git não consegue recriar.

### As duas medições que decidiram a implementação

**A primeira, tomada antes de escrever a condição:** o filtro ingênuo seria
inerte.

```
$ git status --porcelain           # o que worktree_dirty() chamava
?? .cairn/                         <- o DIRETÓRIO, colapsado
$ git status --porcelain -uall
?? .cairn/journal/-0001.jsonl      <- só agora o filtro tem caminho para casar
```

Com `-u normal` o git colapsa um diretório inteiramente não rastreado numa
linha, e `.cairn/` não começa com `.cairn/journal/`. A chamada passou a
`--porcelain -z -uall`.

**A segunda, encontrada por um teste negativo, e é a mais barata de não ter
visto:** `run_git()` faz `.strip()` no stdout, o que **come o espaço inicial**
do par de status do porcelain. Um arquivo não rastreado (`?? path`) sobrevive
ao strip porque começa com `?`; um arquivo modificado (` M path`) não —
o deslocamento do caminho muda em um byte e o filtro para de casar em silêncio.

O teste `a committed journal partition, modified in place, still does not
retain` ficou vermelho e nomeou o defeito. Sem ele, o filtro funcionaria
exatamente para o caso testado e falharia no caso não testado. A chamada usa
`run_git_raw()`, que existe neste arquivo precisamente para isso.

### O teste da fase 28 perdeu a premissa, não a asserção

O teste `cleanup reports a stale lease whose holder is a live worktree`
commitava a partição do journal **e a mesclava de volta** para restaurar a
premissa "a árvore está limpa" — com o comentário registrando que as duas
razões de retenção eram verdadeiras e escondê-las seria o teste mentir. Com o
conserto a premissa some: o commit e o merge foram removidos, o comentário
registra por quê, e o que mantém aquela árvore fora de `removable` é a lease,
que é o que o teste sempre foi.

## CairnGo-r4g (FIX-02) — a branch adotada antes de derivada

`phase_layout()` deixa de derivar o nome sempre e passa a adotar o que já
existe, em três degraus: o **worktree canônico** (a identidade que a própria
issue nomeia como estável), senão **exatamente uma** branch `phase/<N>…`, senão
deriva do slug como antes. O resultado carrega `branch_source`
(`worktree` / `existing-branch` / `derived`), no `prepare` e no `batch`.

### A demonstração do defeito ficou melhor do que o plano previa

O plano dizia que a segunda `prepare` **adotaria** a branch existente. Medido: o
`prepare` **recusa**, com o exit 4 e a mensagem que ele já tinha para esse caso
(*"branch 'phase/7' already exists but has no worktree — refusing to guess"*).
E é uma prova mais forte, porque explica o defeito inteiro:

- **antes:** a fase resolvia `phase/7-alpha`, que não existia, passava direto
  pela recusa e criava a **segunda** branch da mesma fase, em silêncio;
- **depois:** resolve `phase/7`, que existe, e bate na recusa que sempre esteve
  lá.

A guarda não estava faltando; ela estava sendo **contornada** por um nome que
mudou.

### Duas branches para uma fase não matam o `batch`

A regra da casa é nunca "pegar a primeira" de um casamento ambíguo, e aqui ela
cede a uma medição: duas branches para uma fase é o estado **ordinário** de uma
fase dividida entre duas frentes — `phase/25-tools` e `phase/25-surfaces` neste
repositório, agora. Morrer ali derrubaria o `batch` inteiro por causa de uma
fase. O terceiro degrau mantém o comportamento de hoje byte a byte (D-07) e o
`branch_source` diz que a escolha foi derivada, não lida.

## A prova por quebra

Seis quebras, na cópia da árvore fora do repositório, restauradas de cópia e
conferidas por `shasum`.

| Guarda | O que foi removido | Asserção que ficou vermelha |
|---|---|---|
| G12 | o `-uall` sai da chamada | `only untracked work is the journal is removable` — `retained` voltou a 1 |
| G13 | o filtro `.cairn/journal/` sai | a mesma — `retained` 1 |
| G14 | `run_git_raw` volta a `run_git` | `committed journal partition, modified in place` — `removable` 0 |
| G15 | nada é considerado sujo | `one other untracked file beside the journal` — `removable` 1, com `wip.txt` dentro |
| G16 | a adoção sai, o nome volta a derivar sempre | `a branch made before the phase directory` — a segunda branch nasceu |
| G17 | `die()` quando há mais de uma branch | `two branches for one phase` — o batch inteiro morreu |

## Medido, e contrariou o que estava escrito

1. **O `.strip()` do `run_git` teria tornado o filtro correto-para-o-caso-
   testado.** Só o teste do arquivo *modificado* pegou; o do arquivo *não
   rastreado* passava com o bug. Um filtro que casa em 50% dos casos e nunca
   avisa é pior que nenhum filtro.
2. **O plano previa que a segunda `prepare` adotaria a branch; ela recusa.** E
   a recusa é a prova, não uma falha do conserto — ver acima.
3. **O `git worktree remove` do próprio git recusa um worktree que journalizou**
   (`contains modified or untracked files`). O atrito que a issue mede uma
   camada acima aparece aqui na voz do git, e o teste precisa de `--force` para
   montar o cenário. Registrado no teste.
4. **Os três worktrees órfãos deste repositório não são retidos pelo journal.**
   Medido: `git status --porcelain` vazio nos três, porque foram criados antes
   da fase 28. O defeito do `rhq` é real para worktrees novos e **não** é a
   causa de os três estarem lá — essa é do `ce3` (plano 06).

## Suítes

`tests/cairn-parallel.bats` (49 testes, verde) e
`tests/cairn-parallel-autonomous.bats` (13 testes, verde) — o consumidor do
anúncio.
