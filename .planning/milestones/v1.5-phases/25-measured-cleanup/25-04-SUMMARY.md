---
phase: 25-measured-cleanup
plan: "04"
requirement: null
beads: [CairnGo-ozy, CairnGo-66o]
status: complete
---

# Fase 25 Plano 04 — resumo

## O que mudou

O `cairn-bookkeep` deixa de dizer que não havia trabalho quando havia trabalho
recusado, e ganha a porta cirúrgica **por plano** que só existia por fase.

## CairnGo-ozy — `nothing to change` passa a significar zero discordâncias

Antes, `nothing to change` era impresso quando o plano de edições estava vazio.
Quatro dos nove tipos que o `reconcile` nomeia não existiam para o escritor —
não viravam edit **nem** `unresolved` — então a mensagem era impressa por cima
deles. Medido três vezes em 2026-08-05, sempre sobre linha escrita menos de uma
hora antes.

Agora: `if not edits and not unresolved`. E toda finding sem escritor sai pelo
caminho que o comando já usava para recusar, com o motivo, **nas duas saídas**
(humana e `--json`) — a linha humana ganhou o `because ...` que só existia no
JSON.

### A lista de kinds sem escritor é derivada, e essa é a decisão do plano

O caminho óbvio seria uma tupla com os quatro kinds de hoje. Seria o **sexto**
fato mantido à mão neste repositório: certo hoje, obsoleto no primeiro kind
novo, e silencioso a respeito.

Em vez disso: cada edit passa a carregar o `kind` que ele responde, e
`finding_family()` — uma função, aplicada aos **dois** lados — reduz
`requirement-checkbox-stale`, `-ahead` e `-written` à mesma família. O que o
leitor achou menos o que o plano endereçou é o que é reportado. Um kind que
ganhe escritor some daqui sozinho; um kind inventado sem escritor aparece aqui
sozinho, com o motivo genérico em vez de invisível.

O teste `the list of writerless kinds is derived, never hand-kept` injeta um
kind inexistente **numa cópia do script** (nunca no fonte do repositório) e
afirma que ele sai nomeado, sem uma linha de código em lugar nenhum saber que
ele existe.

## CairnGo-66o — `cairn-bookkeep.py plan <NN-MM>`

Medido no fecho do 29-04 (commit 49e2b45): `+43/-7` no `ROADMAP.md`, 29 delas
linhas em branco injetadas pelo `_normalizeMd`, para virar cinco checkboxes e um
contador.

Medido neste checkout, e é a metade que decidiu o conserto:

```
$ grep -rn "cairn-bookkeep" cairn/commands/ cairn/hooks/
cairn/commands/autonomous.md:  cairn-bookkeep.sh close <N> --apply
cairn/commands/help.md:        cairn-bookkeep.sh close <N> --apply
```

Só existia porta de **fase**. O comando novo fecha **um** checkbox mais os
contadores do `STATE.md` que já mudaram quando o summary chegou ao disco, e nada
mais. Medido: `1 1 .planning/ROADMAP.md`, com o `REQUIREMENTS.md` fora do diff.

A regra de mão única continua valendo: o checkbox segue o `SUMMARY` no disco,
nunca o pedido. Um plano nomeado sem summary sai como `plan-summary-missing`; um
plano que o roadmap não lista é `EXIT_NO_PHASE` (4) com o arquivo byte a byte
igual.

**O que este plano não entrega, e fica dito:** fazer o `gsd-executor` chamar a
porta. O caminho de fecho por plano vive no agente do GSD e nos prompts
`/cairn:*`; os prompts são da outra frente desta fase e o agente é de outro
repositório. Entregue: a porta, e a medição de que ela não existia.

## A prova por quebra

Seis quebras, na cópia da árvore fora do repositório, restauradas de cópia e
conferidas por `shasum`.

| Guarda | O que foi removido | Asserção que ficou vermelha |
|---|---|---|
| G6 | `nothing to change` volta a olhar só os edits | `a refusal is never announced as nothing to change` — `refute_in_output "nothing to change"` |
| G7 | a varredura independente (`writerless_findings`) sai | a mesma — o `NOT written :: state-narrative-stale` sumiu |
| G8 | `finding_family` vira identidade | `rows plan themselves` — nove findings viraram `NOT written`, incluindo as sete que o plano escreveu |
| G9 | o filtro por plano sai do edit 5 | `one checkbox, and the ROADMAP diff is one line` — o `20-03` foi marcado junto |
| G10 | a recusa `plan-summary-missing` sai | `no summary on disk is refused BY NAME` — `unresolved` vazio |
| G11 | o `die` de plano inexistente sai | `a plan the roadmap does not list is exit 4` |

O G8 é o mais informativo: sem a família, **tudo** que o plano acabou de
escrever volta como "não escrito". A comparação por endereço não é um detalhe,
é o que separa um leitor independente de um gerador de ruído.

## Medido, e contrariou o que estava escrito

1. **O teste `with the ids written out, the rows plan themselves` afirmava
   `.unresolved | length == 0`.** Com o conserto, ele passa a ser 1 — o
   `state-narrative-stale` que ninguém reescreve. A asserção virou o
   **conjunto** exato, que é mais forte: zero era verdade só porque a
   discordância era invisível para o escritor.
2. **Um teste que edita o fonte que ele testa deixa a árvore quebrada na
   primeira falha no meio.** A primeira versão do teste do kind derivado
   remendava `cairn/scripts/cairn-bookkeep.py` no lugar e restaurava no fim —
   e um `assert` no meio deixaria o repositório com o remendo. Reescrito para
   remendar uma **cópia** no `BATS_TEST_TMPDIR` e rodar a cópia. A regra da casa
   sobre nunca perder trabalho vale também para o fonte que o teste toca.
3. **A mensagem do tracker dizia `reconcile owns no phase`, e agora há dois
   comandos sem fase.** Passou a `this run owns no phase (reconcile, plan)`.
   Um comando novo herdou uma frase escrita para outro; nomear os dois é mais
   barato que descobrir isso num relatório.
4. **O campo `planned` do `--json` não carregava o `kind` que cada edit
   responde** — não podia, porque não existia. Agora carrega `kind` e
   `subject`, aditivamente, e é o que o teste do par `20-1` / `20-01-PLAN.md`
   usa para afirmar qual plano foi escolhido sem depender de texto de prosa.

## Suítes

`tests/cairn-bookkeep.bats` (61 testes, verde) e `tests/cairn-doctor.bats`
(117 testes, `--jobs 6`, verde) — o consumidor, porque a `req-ledger` e a
`plan-counters` roteiam para este comando.
