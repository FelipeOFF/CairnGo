---
phase: 28-durable-journal
plan: "03"
subsystem: cli
tags: [journal, compaction, segments, e13, snapshot, stdlib, bats]

requires:
  - phase: 28-durable-journal
    provides: "as partições do 28-02 e a dobra ciente de compacted_through_ts — sem elas um segmento selado não seria legível"
provides:
  - "compact() = selar o segmento ativo e abrir o próximo, escopado à própria partição"
  - "nada é reescrito e nada é apagado: o segmento selado sai byte a byte idêntico"
  - "O_CREAT|O_EXCL no segmento seguinte, para o caso que o flock não vê"
  - "o teste do E13, que constrói as duas compactações concorrentes e mescla de verdade"
affects: [doctor-forensics, reconcile-bundle]

actuals:
  tokens: 60000
  tasks: 2
  commits: 1
  tests: 5

tech-stack:
  added: []
  patterns:
    - "selar em vez de reescrever: o ganho de leitura vem do segmento ativo curto, não de jogar coisa fora"
    - "asserção contada POR MÁQUINA, nunca pelo total — o defeito que a fase existe para impedir produz um total plausível"
    - "o seam de atraso usado do outro lado: o teste faz o arquivo concorrente APARECER na janela, em vez de esperar que ele suma"
    - "premissa de relógio declarada como [SUPOSTO] no docstring, com o alcance dela nomeado (uma máquina, não entre máquinas)"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-journal.py
    - cairn/scripts/cairn-journal.sh
    - tests/cairn-journal.bats

key-decisions:
  - "O `aborted_stale_read` foi REMOVIDO, e o motivo é estrutural, não de simplificação: ele existia para a Armadilha 14, um append pousando entre a leitura e o `os.rename` e sendo descartado pelo rename. Sem rename não há descarte — o registro concorrente fica no segmento selado, e como o `ts` dele é posterior ao `compacted_through_ts`, a dobra o aplica por cima. O teste que afirmava o aborto passou a afirmar a sobrevivência, que é a propriedade que sempre importou"
  - "`already_compacted` é guarda nova e necessária: sem ela, dois `compact` seguidos encadeariam segmentos de puro snapshot para sempre"
  - "`O_CREAT|O_EXCL` no segmento seguinte cobre exatamente o que o flock não vê — um segmento daquele número chegando pelo git no meio do voo. Medido no teste com o seam de atraso: sobrescrever apagaria a cabeça selada de outra máquina"
  - "O limiar de auto-compactação mede o SEGMENTO ATIVO, não a partição inteira. Selar só encurta o ativo; medir a partição faria o gatilho disparar toda vez, para sempre, já que os selados ficam no disco por desenho"
  - "O `tempfile` saiu dos imports: a receita de sibling+rename não existe mais em lugar nenhum do arquivo"

status: complete
---

# Phase 28 Plan 03: Compactação que sela Summary

## O que foi construído

Compactar passou a significar **selar o segmento ativo e abrir o próximo**, cuja
primeira linha é o `snapshot` com `compacted_through_ts`. Três regras, e cada uma tem
uma medição atrás:

| regra | por quê | experimento |
|---|---|---|
| nada é reescrito | reescrever faz o `union` **ressuscitar** o que foi dobrado — a outra branch ainda carrega as linhas originais | E5 (6 linhas onde um humano esperava 2) |
| nada é apagado | apagar um selado vira `modify/delete` no merge seguinte | E10 |
| nunca sai da própria partição | duas máquinas compactando o mesmo arquivo deixaram um JSONL **válido** de duas linhas com a história inteira de uma delas ausente | E13 |

A contrapartida está no docstring: compactar arquivo versionado não economiza nada
durável, porque toda versão fica no histórico do git para sempre. O ganho é tempo de
leitura, e o segmento ativo curto entrega esse ganho sem reescrever um byte.

## O teste do E13, e por que ele é o mais importante da fase

Ele **constrói** as duas compactações concorrentes: `hostA` observa três coisas e
compacta; `hostB` observa duas outras e compacta; os dois estados são commitados em
ramos e mesclados de verdade.

A asserção que carrega o teste conta **por máquina**, nunca o total:

```
[.records[] | select(.machine == "hostA")] | length  ==  4
[.records[] | select(.machine == "hostB")] | length  ==  3
```

O total não pegaria: a falha do E13 produz um arquivo válido com um total plausível e
a história de uma máquina inteira faltando.

Aplicado o desenho ingênuo no fonte — partição única compartilhada, reescrita no
lugar — a asserção cai com o número exato do defeito:

```
jq '[.records[] | select(.machine == "hostA")] | length' returned '1', expected '4'
```

Quatro registros viram um. É o E13 reproduzido dentro da suíte.

## Os testes, e a prova de que provam

5 testes novos (37 no arquivo), mais dois reescritos: o de crash-entre-sibling-e-rename
virou o do selo byte a byte, e a checagem secundária da equivalência de replay parou
de exigir que o arquivo **encolhesse** — sob journal versionado encolher é o objetivo
errado.

Cada quebra abaixo foi aplicada **de verdade** no fonte, a suíte rodada, e o fonte
restaurado de cópia (`cp`, nunca `git checkout`):

| Quebra aplicada | Asserção que ficou vermelha |
|---|---|
| `compact()` reescrevendo o segmento ativo em vez de selar | 13 (selo byte a byte), 14, 16, 18, 19, **36 (E13)**, 37 |
| `compact()` apagando os segmentos selados | 13, 14 (nenhum selado é apagado), 18, 19, **36**, 37 |
| Partição única compartilhada + reescrita no lugar — **o desenho ingênuo inteiro** | 21 testes, entre eles **36 (E13)** com hostA caindo de 4 registros para 1 |
| `O_EXCL` removido | 16 (o segmento vindo pelo git não é sobrescrito) |

## Premissa do contexto que a medição contradisse

O contexto trata a Armadilha 14 (`aborted_stale_read`) como uma defesa a preservar. A
medição mostrou que ela **deixa de existir** com o desenho novo: sem rename não há o
que descartar. Manter a revalidação de tamanho teria sido carregar um guarda-corpo em
frente a um precipício que foi aterrado — e pior, ela abortaria compactações legítimas
sempre que um append concorrente pousasse na janela. Removida com o motivo estrutural
escrito no docstring, e o teste convertido de "aborta" para "não perde".
