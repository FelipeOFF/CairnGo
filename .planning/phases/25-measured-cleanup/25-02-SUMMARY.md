---
phase: 25-measured-cleanup
plan: "02"
requirement: FIX-05
beads: [CairnGo-6bx, CairnGo-0po]
status: complete
---

# Fase 25 Plano 02 — resumo

## O que mudou

`NN-SUMMARY.md` (o fecho de uma **fase**) deixa de contar como
`NN-MM-SUMMARY.md` (o fecho de um **plano**) nos dois lugares que perguntavam
"esta fase avançou?" por sufixo em vez de por forma. O `cairn-doctor` ganha uma
vigésima checagem que compara os dois contadores do `STATE.md` sem recomputar
nenhum dos dois.

## O efeito no repositório, medido antes e depois

```
antes                            depois
total_plans:     39              total_plans:     41
completed_plans: 47   <-- >39    completed_plans: 40
```

Os 41 são os `NN-MM-PLAN.md` do disco (39 mais o `25-01` e o `25-02`); os 40
são os `NN-MM-SUMMARY.md`. Os 8 `NN-SUMMARY.md` de fase saíram da conta, que é
de onde os 47 vinham (39 + 8).

## Os dois defeitos, e a asserção que fecha cada um

| Defeito | Medição | Teste |
|---|---|---|
| `CairnGo-6bx` (P1, critério 6) — `completed_plans` excede o próprio total | 2026-08-06 e reconfirmado hoje: 47 contra 39, `47 = 39 + 8` | `reconcile: a phase's own SUMMARY is not one of its plans` (2 planos, 2 summaries de plano, 1 de fase → `completed_plans == 2`) |
| `CairnGo-6bx` (a fixture cega) | zero fixtures do repositório carregavam um `NN-SUMMARY.md` | `make_drift_fixture: rebuilds the tree by name` conta por forma; `reconcile: computes the STATE counters from disk` vira o canário |
| `CairnGo-0po` (FIX-05, P1) — um summary faz a fase inteira ler `executed` | 2026-08-03: fase 20 com `disk_state: executed`, `plans_done: 1`, `plans_total: 3` | `a phase with one summary for three plans is planned, not executed` |
| critério 6, segunda metade — leitor independente | `reconcile` devolve `disagreements: []` imprimindo 28 e 33 no mesmo JSON | `plan-counters fails a STATE.md claiming more plans done than exist` |

## Por que a checagem compara em vez de recomputar

O defeito medido não é a aritmética: é escritor e verificador derivando
`completed_plans` com a **mesma** regra e portanto concordando. Recontar a
árvore com a regra do escritor reproduziria o defeito dentro da checagem
escrita para pegá-lo. A `plan-counters` lê os dois números **como estão
escritos** e faz a única pergunta que nenhum dos dois globs responde sobre si
mesmo: podem terminar mais planos do que existem? `completed > total` é
impossível por aritmética, não por convenção, e não precisa saber nada sobre
quem produziu cada número.

Chave ausente é `⊘ no-input`, nunca falha: o bloco `progress:` é do GSD, e um
repositório que nunca criou um não tem nada de inconsistente. Dizer `ok` sobre
insumo que não chegou é a forma que a fase 23 removeu deste arquivo.

## Cada metade negativa, e por que ela existe

- `a phase whose every plan has its summary is executed` — sem ela, "nada é
  `executed`" passaria, e `executed` é o valor sobre o qual toda a corroboração
  se apoia.
- `plan-counters passes a STATE.md whose two numbers are possible` — sem ela,
  "sempre falha" passaria, numa checagem que roda em toda invocação do doctor
  em todo repositório.
- `plan-counters reports no input, never ok, when STATE.md has no counters` —
  asserção sobre o valor exato (`not-applicable` + `no-input`), nunca sobre a
  negação de `ok`.

## A prova por quebra

Seis quebras reais no fonte, cada uma isolada numa cópia da árvore fora do
repositório, restauradas de cópia em memória e conferidas byte a byte no fim.

| Guarda | O que foi removido | Asserção que ficou vermelha |
|---|---|---|
| G8 | o glob de `summaries` volta a casar por sufixo | `completed_plans returned '3', expected '2'` |
| G9 | o mesmo glob, contra a fixture que deixou de ser cega | `completed_plans returned '4', expected '3'` |
| G11 | `disk_state` volta a aceitar um summary qualquer | `a phase with one summary for three plans` cai em `status -eq 0` |
| G12 | `check_plan_counters` sai do registro | `plan-counters fails a STATE.md` cai em `status -eq 7` |
| G13 | `plan-counters` deixa de comparar os dois números | `plan-counters fails a STATE.md` cai em `status -eq 7` |

Duas quebras saíram verdes, e os dois verdes são achados.

**G10 — a fixture sozinha.** Remover só a escrita do
`NN-SUMMARY.md` da fixture, com o conserto no lugar, não derruba nada — porque
com o conserto o summary de fase de fato não muda a conta. A prova da fixture
tem de ser combinada, e foi medida assim: **glob quebrado _e_ fixture sem o
summary de fase — exatamente o estado de 2026-08-06 — e o teste passa.**

```
=== glob QUEBRADO + fixture SEM summary de fase (o estado medido em 2026-08-06)
ok 1 reconcile: computes the STATE counters from disk, never from the prose
rc = 0 -> VERDE: a fixture e' cega ao defeito
```

Com a fixture nova e o mesmo glob quebrado, o mesmo teste fica vermelho (G9).
É a demonstração literal do que a issue registra: o defeito não passou pelo
teste — ele nunca chegou perto dele.

**G14 — o escopo do ramo sem `.planning/`.** Também verde, e pela razão que o
item 4 de "medido, e contrariou o que estava escrito" registra: o doctor não
chega a rodar checagem nenhuma nesse repositório. A asserção que eu tinha
escrito para guardar a escolha era vazia e foi removida.

## O canário de contagem do doctor

De **20 para 21**, e os quatro sítios editados na mesma mudança, como o D-06
manda: as duas asserções `.checks | length` do `tests/cairn-doctor.bats`, a
lista numerada do docstring do `cairn-doctor.py` (mais a linha
`twenty` → `twenty-one` da checagem 0 e o `20 checks` do rodapé), e a página
`cairn/docs/commands/doctor.md` (a entrada nova, o `twenty-one checks in
total` e o `21 checks`). A 22ª vaga continua reservada ao critério 5.

## Medido, e contrariou o que estava escrito

1. **O `25-02-PLAN.md` previu que `plans` do `scan_phase_tree` já acertava por
   acidente. Acerta mesmo — e continua sendo um contador cuja correção repousa
   na ausência de um nome de arquivo.** Recebeu a mesma disciplina do
   `summaries`, sem mudar nenhum número hoje.
2. **A prova de fixture que o plano descreveu não funciona na forma simples.**
   O plano dizia "sem a fixture nova o buraco segue aberto"; a medição mostra
   que remover só a fixture, com o conserto no lugar, não derruba teste nenhum.
   A afirmação só se sustenta na forma combinada, e foi medida assim.
3. **O `tests/cairn-bookkeep.bats` tinha uma asserção que contava
   `*-SUMMARY.md` por sufixo** (`[ "$summaries" -eq 3 ]`), a mesma confusão que
   o conserto remove do fonte. Passou a contar por forma, e agora afirma as
   duas quantidades separadamente — 3 de plano e 1 de fase.

4. **O ramo "sem `.planning/`" da checagem nova é inalcançável pela CLI, e eu
   quase provei o contrário com um teste vazio.** Escrevi o ramo como
   `no-input` primeiro; percebi que isso derrubaria `.ok` em todo repositório
   sem GSD (D-07) e troquei para `out-of-scope`; e então escrevi uma asserção
   para guardar a troca. A quebra G14 devolveu **verde**, e a medição explicou
   por quê:

   ```
   $ cairn-doctor.sh --json   # num repo sem .planning/
   ok= True  checks= 0
   ```

   O doctor sai antes de montar a lista de checagens, então nenhuma asserção
   sobre status ou escopo de uma checagem ali prova coisa alguma — ela passaria
   contra qualquer implementação. A asserção vazia foi removida, o ramo ficou
   com o valor honesto, e o docstring diz que ele é defensivo e por que não há
   teste. É a regra da casa aplicada contra o meu próprio teste.

5. **Um helper da suíte do doctor neutralizava um confounder *usando* o
   defeito, e o conserto do FIX-05 o virou do avesso.**
   `neutralize_phase2_corroboration` fechava a issue bd da fase 2
   incondicionalmente, para tirar a corroboração da frente de um teste sobre
   `phase-artifacts`. Isso funcionava porque um único summary fazia a fase de
   2 planos ler `executed`, e disco `executed` + bd `closed` concordavam. Com
   `executed` significando *todo* plano summarizado, a mesma fase lê `planned`
   — e fechar a issue passa a **fabricar** exatamente o conflito que o helper
   existia para remover. Um teste caiu (`phase-artifacts: same two-plan/one-
   summary phase with NO VERIFICATION.md`, `[ "$status" -eq 0 ]`). O helper
   passou a receber de qual lado o disco está (`done` / `underway`), e a fase
   com plano não summarizado agora neutraliza deixando a issue **aberta**, que
   é o que uma fase em andamento deve ter. Três das quatro chamadas seguem
   `done`, porque nelas a fase tem `VERIFICATION.md`.

6. **A checagem nova reprova este repositório agora, e o conserto não é meu.**
   Rodada contra o `.planning/` real: `plan-counters fail`, `progress.completed_plans 47 > progress.total_plans 39`. O `STATE.md` está na lista do
   que esta fase não pode tocar, então o achado fica de pé e a recontagem é do
   `cairn-bookkeep reconcile`, que é de quem orquestra.

## Suítes

`tests/cairn-bookkeep.bats`, `tests/cairn-doctor.bats`,
`tests/cairn-corroboration.bats`, `tests/cairn-phase-model.bats`,
`tests/cairn-status.bats`, `tests/cairn-board-invariance.bats` (D-08).
