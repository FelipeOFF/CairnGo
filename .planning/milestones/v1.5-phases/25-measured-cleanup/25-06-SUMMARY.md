---
phase: 25-measured-cleanup
plan: "06"
requirement: null
beads: [CairnGo-php, CairnGo-ce3]
status: complete
---

# Fase 25 Plano 06 — resumo

## O que mudou

Fechar uma fase agora desmonta o que o `prepare` montou: a lease é **aposentada**
(vagada e fechada no bd) e o worktree canônico da fase é removido. Nesta ordem,
que é a única que funciona — uma lease ainda segurada por aquele worktree é, ela
própria, motivo de retenção.

## CairnGo-php — e a premissa que a medição derrubou

A issue e o roadmap descrevem um caminho de liberação que *"funcionou duas vezes
e parou de funcionar a partir da fase 20 — não é 'nunca libera', é 'deixou de
liberar'"*. **Medido em 2026-08-07, é o contrário.**

```
$ grep -n "close" cairn/scripts/cairn-lease.py
(nenhum `bd close` em lugar nenhum)

# e o ramo de vacância do write_lease:
args += ["--assignee", "", "--status", "open"]     <- REABRE, de propósito

$ bd show CairnGo-2bo   ->  closed 2026-08-03T14:39:56Z
$ bd show CairnGo-83x   ->  closed 2026-08-03T14:39:57Z
Close reason: "bookkeeping do lease da fase 18; fase completa e arquivada,
               lease vago (held=false)"
```

Um segundo de diferença, e uma razão em prosa pt-BR que nenhuma ferramenta deste
repositório escreve. **A capacidade nunca existiu**; duas execuções manuais
fizeram parecer que existia, e depois pareceu regressão. Não havia caminho a
restaurar — havia um verbo a criar.

### E o `ok` do próprio comando, medido

`cairn-bookkeep close` imprimia `tracker :: lease :: ok` com as cinco abertas, e
o `ok` não era mentira sobre o que a etapa fez: o `release` de fato vaga. Era a
palavra "liberada" significando "o subprocesso saiu 0" e sendo lida como "a
lease saiu da fila". Por isso **toda** asserção deste plano lê o bd e o sistema
de arquivos **depois**, e nenhuma lê o relatório.

### `retire`, e por que é um verbo e não uma flag

`release` significa *"solto a lease, a fase continua"* — é o que o `cleanup` faz
com uma lease órfã e o que `--mine` faz no fim de uma sessão, e ele deixa a
issue **aberta** de propósito, para o próximo `acquire` ter o que tomar.
`retire` significa que a fase acabou. Construído **sobre** o `release_one`, para
que a vacância e seu registro no journal tenham uma implementação só;
idempotente; no-op numa fase que nunca teve lease. O relatório carrega `retired`
e `issue_status` **lidos de volta** do bd.

### As cinco órfãs

Fechadas pelo verbo novo, rodado contra o repositório real: `CairnGo-55t` (20),
`CairnGo-6ox` (21), `CairnGo-u98` (24), `CairnGo-16g` (26) e `CairnGo-8y1` (29).
`bd list -l lease --all` devolve sete leases, sete fechadas.

## CairnGo-ce3 — e a segunda premissa que a medição derrubou

A issue descreve três worktrees "sobrevivendo". Medido em 2026-08-07, com o scan
que já existia, em modo leitura:

```
$ cairn-parallel.py cleanup --json --project-dir ~/Projects/CairnGo
removable: CairnGo-25-surfaces, CairnGo-25-tools,
           CairnGo-phase-21, CairnGo-phase-24, CairnGo-phase-26
retained:  []
```

Duas coisas numa linha. **Os três órfãos já eram removíveis** — limpos, sem
commit à frente de `HEAD` — e o `cleanup` sempre soube removê-los; ninguém nunca
o chamou. E **os dois primeiros são os worktrees vivos das duas frentes da fase
25**, que o `PHASE_BRANCH` casa como fase 25 exatamente como casa `phase/21`.

Um sweep por fase chaveado no número da branch, disparado pelo fecho da fase 25,
teria apagado o trabalho vivo de dois agentes. Por isso `cleanup --phase N` é
chaveado no **caminho canônico** `<root>-phase-N` — exatamente e apenas o que o
`prepare` monta. Os três órfãos casam; os dois vivos não. A quebra G20 mede isso:
com o escopo pelo número da branch, `removable` vai de 1 para 2.

## O achado que não estava em plano nenhum: os dois vereditos discordaram

Com o `25-05` no lugar, o `cairn-parallel` chama de removível um worktree cuja
única sujeira é o journal. O **git** então recusa:

```
fatal: '<path>' contains modified or untracked files, use --force to delete it
```

O git nunca ouviu falar do `DJOUR-03`. E `--force` responderia a isso desligando
a re-checagem inteira do git — que é o **segundo veredito independente** que o
`cleanup_apply` mantém de propósito sobre um ato irreversível.

O conserto: apagar **exatamente** o caminho que este script declarou irrelevante
(`.cairn/journal/` daquele worktree, já provado limpo em todo o resto) e deixar o
git julgar o que sobrou, nos termos dele, sem `--force`. Se ele ainda recusar,
havia outra coisa lá, a recusa está certa e é reportada. O `applied` carrega
`journal_dropped` com o caminho — apagado, nunca em silêncio.

## A prova por quebra

Cinco quebras, na cópia da árvore fora do repositório, restauradas de cópia e
conferidas por `shasum` (três pares idênticos).

| Guarda | O que foi removido | Asserção que ficou vermelha |
|---|---|---|
| G18 | o `bd close` sai do `retire` | `the lease issue is CLOSED in bd` — `.retired` false |
| G19 | o `close` volta a chamar `release` | `the phase's lease issue is CLOSED in bd afterwards` — bd diz `open` |
| G20 | o escopo do `--phase` vira o número da branch | `only the canonical worktree of N` — `removable` foi de 1 para **2**, a frente irmã entrou |
| G21 | o `close` deixa de chamar o cleanup | `the phase's canonical worktree is removed` — o diretório continuou lá |
| G22 | o journal deixa de ser apagado antes do remove | `a journal-only worktree is actually removed` — o git recusou, `.ok` false |

## O que ficou de fora, e por quê

**Os três worktrees órfãos deste repositório seguem no disco.** A capacidade está
entregue e provada, e as leases órfãs foram fechadas porque isso é escrita no bd
— o mesmo bd que este trabalho já usa. Remover os três é escrita no `.git`
compartilhado, sobre árvores irmãs, enquanto outra frente roda em paralelo. Fica
para quem orquestra, com o comando exato:

```
cairn-parallel.sh cleanup --phase 21 --apply --project-dir <raiz>
cairn-parallel.sh cleanup --phase 24 --apply --project-dir <raiz>
cairn-parallel.sh cleanup --phase 26 --apply --project-dir <raiz>
```

Silêncio era o que o critério proibia, e não há silêncio: os três estão nomeados
aqui, com a medição e o comando.

## Medido, e contrariou o que estava escrito

1. **"Deixou de liberar a partir da fase 20" é falso.** Nunca houve `bd close` no
   `cairn-lease.py`, e o `release` reabre a issue por design. As duas fechadas
   foram fechadas à mão, no mesmo lote, com prosa que nenhuma ferramenta gera.
2. **"Os três worktrees ficaram para trás" tem uma causa diferente da que a issue
   sugere.** Eles não estavam retidos por nada: já eram `removable`. Faltava a
   chamada, não a capacidade — e o `rhq` (plano 05), que parecia a causa, não os
   afeta, porque foram criados antes de a fase 28 versionar o journal.
3. **Um `cleanup --apply` global, hoje, apagaria as duas worktrees da fase 25.**
   Medido, e é o achado que decidiu o escopo do `--phase`. Não é hipótese: o scan
   real deste repositório lista as duas como removíveis agora.
4. **O conserto do journal do plano 05 não bastava para remover o worktree.** O
   veredito do cairn mudou e o do git não, e nenhum plano previu que os dois
   fossem discordar. Resolvido apagando só o caminho declarado irrelevante, sem
   `--force`, mantendo a segunda verificação viva.
5. **A issue de lease fica `in_progress` depois do `acquire`, não `open`.** O
   `--claim` do bd move o status, e a primeira versão do teste afirmava `open`
   antes do retire. Corrigido para o valor exato que o bd reporta.

## Suítes

`tests/cairn-lease.bats` (28 testes), `tests/cairn-parallel.bats` (53),
`tests/cairn-bookkeep.bats` (64) e `tests/cairn-doctor.bats` (117, consumidor do
`cairn-lease.py` na checagem `lease-stale`) — todas verdes.
