---
phase: 28-durable-journal
plan: "04"
subsystem: cli
tags: [journal, djour-03, degradation, dead-test, doctor, reconcile, status, bats]

requires:
  - phase: 28-durable-journal
    provides: "o layout particionado do 28-02 e a compactação por selo do 28-03 — a superfície que agora precisa ser apagada inteira"
provides:
  - "a prova do DJOUR-03 sob o layout novo, com a superfície inteira apagada"
  - "a guarda que impede este teste de morrer de novo: zero registros e zero partições depois do apagar"
  - "a prova nas outras duas superfícies de leitura: severidade e exit code do doctor, e o bundle do reconcile"
affects: []

actuals:
  tokens: 38000
  tasks: 1
  commits: 1
  tests: 2

tech-stack:
  added: []
  patterns:
    - "teste de apagar que primeiro PROVA que apagou: sem a asserção de zero, um `rm` no alvo errado deixa o diff comparando um render consigo mesmo"
    - "normalizar o timestamp e comparar o resto byte a byte, em vez de contar itens — o journal se repopula sozinho e a diferença legítima é só o relógio"
    - "duas metades da degradação medidas separadamente: apagar (o journal volta) e neutralizar o script (o journal não volta)"

key-files:
  created: []
  modified:
    - tests/cairn-status.bats
    - tests/cairn-doctor.bats
    - tests/cairn-reconcile.bats

key-decisions:
  - "O teste do JOUR-03 no `cairn-status.bats` tinha VIRADO um teste morto e nada ficou vermelho: o `rm -f .cairn/journal.jsonl` dele deixou de apagar o journal quando a escrita mudou de caminho, e o diff estrutural seguinte comparava um render consigo mesmo. Consertar o `rm` não bastava — entrou a asserção de que o apagar acertou o alvo, que é o que impede a morte silenciosa de acontecer de novo"
  - "A asserção do doctor NÃO pode ser 'a cláusula sumiu': a própria execução do doctor journaliza como efeito colateral, então o journal apagado é repopulado pela execução que está sendo medida e a cláusula VOLTA, com timestamps novos. Isso é o journal se reconstruindo, não o veredito se movendo. A asserção certa normaliza os timestamps e compara o resto byte a byte"
  - "Por isso a prova tem duas metades: apagar (o journal volta, e nada além do relógio muda) e neutralizar o `CAIRN_JOURNAL` (o journal não volta, a cláusula some, e o veredito continua o mesmo)"
  - "Nenhum arquivo de produção foi tocado neste plano, de propósito: se algum precisasse mudar para o requisito valer, o requisito já estaria quebrado e isso seria achado, não tarefa. Nenhum precisou"

status: complete
---

# Phase 28 Plan 04: DJOUR-03 sobrevive Summary

## O achado, e ele é o mais importante deste plano

O teste do `JOUR-03` no `cairn-status.bats` já provava que apagar o journal não muda
o render. Depois do 28-02 ele continuou **verde e parou de medir qualquer coisa**:

```bash
rm -f .cairn/journal.jsonl      # não existe mais no caminho de escrita
...
diff <(jq -S . <<<"$before_output") <(jq -S . <<<"$after_output")   # trivialmente igual
```

O `rm` não apagava nada, e o diff comparava um render consigo mesmo. Nenhuma suíte
ficaria vermelha por isso. É a forma mais silenciosa de teste morto: a feature que ele
guardava continua funcionando, e a guarda deixou de existir sem avisar.

O conserto não é só apontar o `rm` para o lugar certo. Entra uma asserção que **prova
que o apagar acertou o alvo**, e é ela que impede a mesma morte de acontecer de novo:

```
history --json  ->  .records | length == 0
                    .partitions | length == 0
```

## A prova, nas três superfícies

| superfície | o que foi apagado | o que não se moveu |
|---|---|---|
| `cairn-status.sh --json` | `.cairn/journal/` + `.cairn/journal.jsonl*` | o render inteiro, byte a byte por `jq -S` |
| `cairn-doctor.sh --json` | idem | status de toda checagem, contagem e texto de cada item (timestamps normalizados), exit code |
| `cairn-reconcile.sh collect` | idem, mais o `CAIRN_JOURNAL` neutralizado | `journal.history == []`, `last_moved == null`, e todas as outras seções do bundle |

**A sutileza que quase produziu uma asserção errada:** a própria execução do doctor
journaliza como efeito colateral (o `cairn-status.py --json` dela observa), então o
journal apagado é **repopulado pela execução que está sendo medida** e a cláusula
`last moved` volta, com timestamps novos. Afirmar "a cláusula sumiu" seria afirmar
uma coisa falsa sobre um comportamento correto. A asserção normaliza os timestamps e
compara o resto byte a byte; a metade "a cláusula some de fato" é medida à parte, com
o `CAIRN_JOURNAL` apontado para um caminho inexistente — o caso em que o journal não
pode voltar.

## Os testes, e a prova de que provam

2 testes novos (doctor, reconcile) e 1 reescrito (status). Cada quebra foi aplicada
**de verdade** no fonte e restaurada de cópia:

| Quebra aplicada | Asserção que ficou vermelha |
|---|---|
| `journal_last_moved()` do doctor com `check=True`, sem degradar | o teste do doctor |
| `journal_history()` do reconcile levantando no `returncode != 0` | o teste do reconcile |
| O `rm` do teste de status apagando só o arquivo herdado — **o estado exato em que este plano o encontrou** | `.records \| length == 0` devolveu `10` |

A terceira linha é o ponto: a quebra é literalmente o código que estava commitado
antes deste plano, e a asserção nova o reprova.

## Premissa do contexto que a medição contradisse

O `28-CONTEXT.md` D-10 diz que o `DJOUR-03` "não é aspiração, é o que já está
testado". A degradação do código estava mesmo intacta — mas **o teste que a provava
tinha deixado de provar**, e o contexto não podia saber porque o layout ainda não
existia quando ele foi escrito. Continuar confiando nele teria fechado a fase com um
critério satisfeito por um teste vazio.
