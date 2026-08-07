# Fase 25: Measured cleanup — Resumo

**Fechada em 2026-08-07.** Dezenove issues, dez planos, três agentes, e a última
fase do milestone v1.5.

## O que a fase era

Dezoito defeitos que já vieram com a medição junto — e virou dezenove, porque um
quarto apareceu durante a execução. Nenhum deles afetava veredito. Todos faziam uma
superfície dizer algo que não é verdade, que é o tema do ciclo inteiro aparecendo uma
última vez **dentro da própria ferramenta que o persegue**:

```
cairn-parallel   anunciava concorrência que o ROADMAP nega
reconcile        dizia "nothing to change" sobre discordância que acabou de imprimir
o contador       47 planos completos de um total de 39
o mapa do help   derivava metade dos comandos e mantinha metade à mão — e já mentia
o hook de push   gateava com um portão de cinco versões atrás, calado
```

## Os dez planos

| Plano | Issues | Entrega |
|---|---|---|
| 25-01 | `64u` `dsh` `4oq` `4p1` | A prosa do roadmap vira a terceira fonte de dependência; `discovered-from` deixa de bloquear; fase fora do roadmap sai de `runnable` |
| 25-02 | `6bx` `0po` | O summary de fase deixa de contar como plano, nos dois lugares; leitor independente do contador |
| 25-03 | `ctr` | AUTO-10: `close` escreve `active_phase` ao lado de `current_phase`; doctor ganha `state-dialect`, que compara e nunca recomputa |
| 25-04 | `ozy` `66o` | `nothing to change` passa a significar zero discordâncias; `bookkeep plan <NN-MM>`, a porta cirúrgica por plano |
| 25-05 | `rhq` `r4g` | `worktree_dirty` ignora `.cairn/journal/`; `phase_layout` adota antes de derivar |
| 25-06 | `php` `ce3` | `lease retire` e `cleanup --phase`, invocados pelo `close` |
| 25-07 | `026` | O prompt do doctor aprende os quatro estados, o veredito `INCOMPLETE`, e roteia por endereço em vez de copiar |
| 25-08 | `q9l` | O mapa do help deriva as **duas** metades; cada comando declara seu grupo |
| 25-09 | `3w9` | `/cairn:land` e `/cairn:review` ganham as duas portas; guarda para o próximo caso |
| 25-10 | `tuh` `gbu` `13t` | `status` vira fato sobre o portador sozinho; `sync_push` sai da declaração; o mapa deixa de ser pedido antes do diretório existir |

**68 testes novos. 31 quebras aplicadas ao fonte, cada uma restaurada de cópia.**

## Como a fase foi executada, e por que importa

Três agentes, em sequência e depois em paralelo. O primeiro foi interrompido por
acidente com 544 linhas não commitadas; o trabalho foi salvo fora do git antes de
qualquer outra coisa, auditado, e commitado — **commit é backup**, e essa lição custou
um susto.

A segunda rodada foi em dois worktrees isolados, com a **fronteira de posse declarada
por caminho e não por tema**. O motivo é um par de arquivos homônimos:

```
cairn/commands/doctor.md        o prompt          → uma frente
cairn/docs/commands/doctor.md   a página-contrato → a outra
```

É a forma exata da colisão que corrompeu o canário de contagem nas fases 23 e 24 — duas
branches, cada uma certa sozinha, mescladas sem conflito num resultado errado. Desta vez
o merge foi limpo **e** correto, e a prova é cruzada: um teste que só existia numa frente
(`every check id the doctor reports has an entry in the routing table`) aprovou a
checagem que só existia na outra.

## Os três defeitos que a medição redefiniu

- **A lease nunca foi liberada por ferramenta nenhuma.** A issue dizia "deixou de
  liberar a partir da fase 20", porque as das fases 18 e 19 estavam fechadas. Não existe
  um único `bd close` no `cairn-lease.py`: aquelas duas foram fechadas **à mão**, a um
  segundo uma da outra, com razão em prosa que nenhuma ferramenta daqui gera. A issue
  descrevia uma regressão que nunca houve.

- **Os três worktrees órfãos já eram `removable`.** Limpos e mesclados. Faltava a
  chamada, não a capacidade. E a mesma medição expôs que um `cleanup --apply` global
  naquele instante teria apagado os dois worktrees das frentes que estavam trabalhando.

- **O quarto defeito, achado sem issue, dentro do diff herdado.** `plan_depends_on()`
  lia todo dígito do frontmatter de um `PLAN.md` como número de **fase**, mas o GSD
  escreve `depends_on:` ali para ordenar as **ondas**. `22-02-PLAN.md` dizia
  `depends_on: ["01"]` querendo dizer "a onda anterior"; o modelo entendeu "as fases 1 a
  4", de um milestone arquivado que nunca entra em `done_set` e portanto bloqueia para
  sempre. Registrado como `CairnGo-4p1`.

## A prova que fecha a fase

O critério 5 se verificou no repositório real, não em fixture — medido antes e depois do
próprio comando que a fase consertou:

```
antes    claims-stale  not-applicable   state-dialect  not-applicable
depois   claims-stale  ok               state-dialect  ok
```

Duas checagens saíram de "não consegui checar" para "checado" porque a chave que faltava
nasceu do `close`. Doctor ao fim: **22 checagens, zero falhas.**

E o `cleanup` removeu **cinco worktrees de uma vez**, incluindo os dois em que as
frentes acabaram de trabalhar — a ferramenta da fase provando-se na própria fase.

---

*Phase: 25-Measured cleanup*
*Closed: 2026-08-07*
