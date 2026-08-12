---
phase: 28-durable-journal
plan: "02"
subsystem: cli
tags: [journal, partitions, merge-union, gitattributes, fold, clock-skew, stdlib, bats]

requires:
  - phase: 28-durable-journal
    provides: "a proveniência do 28-01 — sem `machine`/`checkout` não existe chave de partição"
provides:
  - ".cairn/journal/<slug>-NNNN.jsonl: uma partição por checkout, o primeiro artefato versionado dentro de .cairn/"
  - ".gitattributes rastreado com merge=union nas partições, e o cairn-init propagando a linha"
  - "_read_partitions(): a leitura que une, com o arquivo herdado como partição de proveniência desconhecida"
  - "_last_known() com a dobra do E12: snapshots por compacted_through_ts, depois só os eventos posteriores por (ts, nonce)"
  - "_merge_last_known(): mais de uma fonte devolve ts null e nomeia cada candidato — nunca uma ordem entre máquinas"
  - "a cláusula forense do doctor nomeando cada máquina de um eixo contestado"
affects: [journal-compaction, doctor-forensics, reconcile-bundle]

actuals:
  tokens: 78000
  tasks: 3
  commits: 1
  tests: 9

tech-stack:
  added: []
  patterns:
    - "whitelist de ignore em vez de lista de sufixos: `.cairn/journal/*` + `!.cairn/journal/*.jsonl`, para que nada novo vaze por omissão"
    - "o teste copia o `.gitattributes` REAL do projeto em vez de reescrever a linha — um teste que redigitasse continuaria verde no dia em que alguém apagasse o original"
    - "asserção de carga que compara a última linha FÍSICA com a resposta da dobra: prova que a leitura não é ordem de arquivo"
    - "seam de máquina simulada (`CAIRN_JOURNAL_MACHINE`) para construir divergência real de duas máquinas dentro de um diretório"

key-files:
  created:
    - .gitattributes
  modified:
    - cairn/scripts/cairn-journal.py
    - cairn/scripts/cairn-journal.sh
    - cairn/scripts/cairn-doctor.py
    - cairn/scripts/cairn-init.sh
    - .gitignore
    - tests/cairn-journal.bats
    - tests/cairn-doctor.bats
    - tests/cairn-init.bats

key-decisions:
  - "O conserto do E12 entrou NESTA fase, e não virou issue: assim que um arquivo de partição pode ser mesclado por `union`, a ordem de arquivo dentro dele deixa de ser cronológica, então a dobra ciente de `compacted_through_ts` passou de otimização a requisito de corretude. O `sort` sozinho continua proibido — e agora tem prova: aplicá-lo derruba três testes, entre eles a equivalência de replay, que é o E9"
  - "A dedup do `observe` é contra a PRÓPRIA partição. Deduplicar contra a partição alheia faria este checkout deixar de registrar uma transição que observou, e o que ele grava passaria a depender de o merge ter chegado. Custo declarado: cada checkout registra a própria primeira visão de cada eixo"
  - "O arquivo herdado é a partição `legacy`, nunca fundida na do checkout: ninguém sabe de onde ele veio e ele pode ter sido copiado. Consequência visível e aceita: um eixo que o herdado e a partição nova observaram sai contestado, com dois candidatos"
  - "`ts` é `null` sempre que há mais de uma fonte, mas o `value` sobrevive quando todas concordam — 'o último valor conhecido é X em toda parte' não ordena nada, um timestamp só ordenaria"
  - "O lock de compactação virou POR PARTIÇÃO. Duas máquinas compactando ao mesmo tempo tocam arquivos disjuntos por construção, e um lock compartilhado faria uma delas pular sem motivo"
  - "A cláusula do doctor entrou aqui e não no 28-04, porque a forma contestada nasce aqui: deixar para depois deixaria o doctor imprimindo `last moved None` no intervalo entre os dois commits"
  - "`.gitignore` por whitelist em vez de enumerar sufixos: `.cairn/journal/*` seguido de `!.cairn/journal/*.jsonl`. Medido com `git check-ignore`: o segmento é rastreável, o lock é ignorado, o herdado continua ignorado pela linha 8"

status: complete
---

# Phase 28 Plan 02: Partições Summary

## O que foi construído

`.cairn/journal/<slug>-NNNN.jsonl` — uma partição por checkout, o primeiro artefato
versionado dentro de `.cairn/`. O `slug` é a máquina sanitizada mais o `checkout` de
12 hex do 28-01, e a numeração de quatro dígitos é o que a compactação vai usar para
selar (28-03).

As duas peças que o desenho exige, e nenhuma basta sozinha:

| peça | o que ela cobre | medida |
|---|---|---|
| um arquivo por checkout | duas máquinas nunca tocam o mesmo arquivo | E11 caso 1 |
| `merge=union` em cada um | a MESMA partição em dois ramos do mesmo checkout | E8b |

O `union` é built-in de propósito: E17 mediu que um driver próprio precisa de
`merge.<nome>.driver` no `.git/config`, que o git nunca clona.

## A leitura, e o que ela se recusa a dizer

Dentro de uma partição, a dobra é: `snapshot` primeiro, ordenados por
`compacted_through_ts`; depois **só** os eventos com `ts` posterior ao ponto já
dobrado, esses por `(ts, nonce)`. É o conserto do E12, e ele entrou agora porque
agora é necessário: `union` concatena um bloco de cada ramo, então ordem de arquivo
deixou de ser ordem cronológica.

Entre partições, nada é ordenado. Com mais de uma fonte, `last-moved` devolve
`ts: null` e nomeia cada candidato. O `value` sobrevive quando todas concordam.

O doctor passou a dizer isso em voz alta:

```
disk last moved 2026-…T…Z on hostA, 2026-…T…Z on hostB
  (order between machines not claimed)
```

## Os testes, e a prova de que provam

9 testes novos no `cairn-journal.bats` (32 no arquivo), 1 novo e 1 reescrito no
`cairn-doctor.bats` (102 no arquivo), 2 novos no `cairn-init.bats`. O reescrito é o
`gitignore:` — ele afirmava que **nada** sob `.cairn/` era estageado; agora afirma as
duas metades, que o lock e a sujeira per-machine não entram e que o segmento da
partição **entra**, porque é o primeiro artefato versionado ali dentro.

Cada quebra abaixo foi aplicada **de verdade** no fonte, a suíte rodada, e o fonte
restaurado de cópia (`cp`, nunca `git checkout`):

| Quebra aplicada | Asserção que ficou vermelha |
|---|---|
| Linha do `.gitattributes` apagada | 27 (mesma partição em dois ramos) — vira conflito |
| `_merge_last_known()` escolhendo o candidato de maior `ts` — a afirmação de ordem proibida | 30 (nomeia cada fonte, não afirma ordem) |
| `_last_known()` trocado por um `sort` por `(ts, nonce)` sozinho — **a armadilha 1 da pesquisa** | 12 (snapshot por fase), 16 (equivalência de replay, que É o E9), 22 (proveniência sob compactação) |
| Escrita de volta em `.cairn/journal.jsonl` | 19 testes, entre eles 24 (escreve na partição) |
| Dedup do `observe` olhando todas as partições | 30 e 31 (dedup escopada à própria partição) |
| Ramo de `candidates` removido do `_last_moved_clause` do doctor | o teste do eixo contestado, no `cairn-doctor.bats` |

A asserção de carga do teste 27 é a que vale mais: ela lê a **última linha física** do
arquivo mesclado (`b_second`) e a compara com a resposta da dobra (`a_newest`). As
duas discordam, e é essa discordância que prova que a leitura não é ordem de arquivo.
A dobra anterior à fase 28 responderia `b_second`.

## Premissas do contexto que a medição contradisse

- **O `.gitignore` da linha 8 não cobria tudo o que precisava.** O `28-CONTEXT.md`
  D-11 diz que a linha 8 "continua cobrindo o arquivo herdado" e que o diretório de
  partições "não precisa de negação de ignore para isso". Verdade pela metade:
  medido com `git check-ignore`, `.cairn/journal.jsonl*` não cobre
  `.cairn/journal/`, o que é o desejado, **mas também não cobre o lock de
  compactação que passa a morar lá dentro**. Sem uma regra nova, o lock per-machine
  seria versionável. A negação de ignore acabou sendo necessária — só que ao
  contrário do que o contexto previa: para **excluir** a sujeira, não para incluir a
  partição.
- **O E12 não era opcional.** O contexto o registra como discricionário ("entra nesta
  fase ou vira issue"). Sob `union` ele é requisito de corretude, não escolha.
