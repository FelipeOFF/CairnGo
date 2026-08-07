---
phase: 29-nothing-mechanical-stays-manual
plan: "07"
subsystem: infra
tags: [python, bats, cli, stdlib, doctor, ledger, requirements, false-green]

requires:
  - phase: 29-nothing-mechanical-stays-manual
    provides: "`cairn-bookkeep.py reconcile --json` (planos 29-01/29-02): a leitura única do ledger, com vocabulário de discordância e contrato de exit code — este plano é o leitor dela dentro do doctor"
provides:
  - "checagem 17 do `cairn-doctor.py` (`req-ledger`): valida requisito ativo → linha na tabela de Cobertura → número que o rodapé afirma, mais a legibilidade da linha `**Requirements**:` e os checkboxes de plano da fase; reprova o estado real deste repositório com exit 7"
  - "allowlist de returncode declarada `(0, 3)` com o contrato citado ao lado, e indisponibilidade sempre `fail` — nunca `warn`, que não move exit code"
  - "verdito não-`ok` para checagem sem insumo: `claims-stale` deixa de exibir o marcador de sucesso sobre uma comparação que nunca aconteceu, nomeia a chave ausente, as cinco superfícies que a leem e a issue `CairnGo-rq0`"
  - "varredura completa dos 21 caminhos que devolvem `ok` nas 18 checagens, com a classificação de cada um"
  - "`cairn/docs/commands/doctor.md` com a fronteira `req-issue` × `req-ledger` escrita, mais as duas entradas que faltavam e a contagem de checagens corrigida"
affects: [cairn-doctor, cairn-bookkeep, docs-doctor, fase-23-void-01, CairnGo-rq0]

actuals:
  tokens: 39000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Allowlist de returncode declarada em constante nomeada com o contrato do script chamado citado ao lado — um número mágico copiado da checagem vizinha é como o caso central vai parar no ramo de erro"
    - "Indisponibilidade é `fail`, nunca `warn`: aviso não muda exit code, então degradar para aviso é aprovar em silêncio"
    - "Vocabulário do chamado escrito por extensão, nunca por exclusão: um conjunto do tipo 'tudo que não é X' adota calado o próximo kind que o outro script criar"
    - "Achado fora da alçada da checagem é exibido como aviso, nunca descartado nem promovido a exit 7"
    - "Asserção de status sobre o valor exato (`fail`/`ok`/`warn`), nunca sobre a negação — `warn` satisfaz 'não é ok' e é justamente o estado errado por acidente"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-doctor.py
    - tests/cairn-doctor.bats
    - cairn/docs/commands/doctor.md

key-decisions:
  - "A alçada da `req-ledger` é o ledger de requisitos, e as discordâncias do `STATE.md` que o `reconcile` também nomeia saem como aviso, não como falha"
  - "Sem coverage view a checagem inteira é not-applicable, com a lacuna aceita nomeada: o elo dos checkboxes de plano fica sem leitor num repo que não tem ledger nenhum"
  - "`claims-stale` sem insumo vira `warn` e não `fail`: checagem sem entrada é atrito, não inconsistência de estado"
  - "O dialeto `current_phase` × `active_phase` continua em aberto — zero linha de código a favor de qualquer lado, com teste provando a abstenção"

patterns-established:
  - "Varredura como entregável: a lista dos caminhos que devolvem `ok` fica registrada mesmo quando só um precisa mudar"
  - "Fixture que carrega discordância real é fixture quebrado: dois fixtures pré-existentes foram tornados coerentes porque a checagem nova nomeou o que eles escondiam"

requirements-completed: [AUTO-07, AUTO-08]

duration: 2h10min
completed: 2026-08-04
status: complete
---

# Fase 29 Plano 07: `req-ledger` e o fim do `ok` sobre checagem não-executada

**A cadeia do registro de requisitos passou a ter leitor, e o doctor parou de exibir o marcador de sucesso sobre uma comparação que nunca aconteceu.**

---

## O que foi entregue

### 1. `req-ledger` — checagem 17 do `cairn-doctor.py` (commit `01dbe87`)

`check_req_ledger(root, planning_dir)` devolve o formato das vizinhas
(`{id, status, detail, items}`), entra na lista do `main()` e conta para o exit 7.

Os quatro elos que o plano nomeia, mais dois irmãos da mesma derivação:

| kind do `reconcile` | elo |
|---|---|
| `coverage-row-missing` | requisito ativo → linha na tabela |
| `coverage-row-orphan` | o mesmo elo, na outra direção |
| `footer-count-stale` | tabela → número que o rodapé afirma |
| `requirements-line-unreadable` | legibilidade da linha `**Requirements**:` |
| `plan-checkbox-stale` | SUMMARY no disco → checkbox do plano |
| `requirement-checkbox-stale` | fase completa → checkbox do requisito (derivada 2 do `reconcile`) |

A leitura é **uma só**, por invocação de `cairn-bookkeep.py reconcile --json`
através da seam `CAIRN_BOOKKEEP`. O doctor não reparseia nada do ledger — um
segundo leitor seria o quinto número para a mesma quantidade (T-29-31).

**A armadilha da allowlist, resolvida em constante nomeada:**

```python
BOOKKEEP_EXIT_OK = 0
BOOKKEEP_EXIT_DISAGREEMENT = 3
```

com o comentário ao lado explicando que `(0, 5)` — copiado de
`check_phase_corroboration()` — mandaria o exit 3 do `reconcile`, o **único**
verdito que esta checagem existe para reportar, ao ramo de "ferramenta
indisponível", que devolve `warn`, que não move exit code, que deixaria o doctor
sair 0.

**Indisponibilidade é sempre `fail`** — script ausente, exit fora da allowlist,
JSON ilegível, `OSError`. Nunca `warn`, nunca `ok`.

### 2. A documentação diz qual checagem cobre qual elo (commit `8d3db19`)

Entrada de `req-ledger` na lista numerada do docstring do módulo e em
`cairn/docs/commands/doctor.md`, com a fronteira contra `req-issue` escrita nos
dois lugares, mais a medição que originou a checagem e o comando que a resolve.

### 3. Nenhuma checagem volta a dizer `ok` por não ter conseguido checar (commit `7358e5b`)

`claims-stale` sem `active_phase` passou de `ok` a `warn`, nomeando a chave
ausente, as cinco superfícies que a leem e a issue `CairnGo-rq0`. Não bloqueia: o
doctor **não** sai 7 por causa dela.

---

## O que foi medido, com a saída literal

### Linha de base do doctor — o plano estava desatualizado, e o usuário já tinha corrigido

O plano diz, na Task 1: *"Hoje `cairn-doctor.sh` sai **0** neste repositório."*
**Falso na hora da execução.** Medido antes de escrever uma linha:

```
✗ phase-corroboration  1 corroboration item(s) across 1 phase(s)
    - 29: disk reports phase 29 executed, bd reports its issues in_progress (blocks)
⚠ lease-stale          1 stale phase lease(s) — phase 29
[cairn-doctor] FAIL — 13 ok, 3 warning(s), 1 failure(s)
```

Causa conhecida e com dono: **FIX-05** (uma fase com UM summary no disco já lê
como `executed`), consertado na fase 25, não nesta.

**Consequência direta, e ela muda a prova de aceitação do plano.** A asserção
`exit 7` do `<verification>` passou a ser **tautológica** — passaria mesmo com o
`req-ledger` removido. Um teste que passa com a feature removida não é prova, e
essa frase está na `CONVENTIONS.md` desta casa. Então a prova tem duas partes:

**Parte 1 — o verdito exato da checagem nova**

```
$ bash cairn/scripts/cairn-doctor.sh --json | jq '.checks[] | select(.id=="req-ledger")'
{
  "id": "req-ledger",
  "status": "fail",
  "detail": "12 broken link(s) in the requirement ledger — 35 active requirement(s) against 33 coverage row(s), 1 excluded by rule (deferred / out of scope) — run cairn-bookkeep.sh reconcile --apply",
  "items": [
    "Phase 29: its '**Requirements**:' line does not yield the ids the ledger assigns it — raw '**Requirements**: AUTO-01 … AUTO-08', parsed ['AUTO-01', 'AUTO-08'], signals ['ellipsis-between-ids', 'coverage-table-maps-more-ids'] [requirements-line-unreadable] .planning/ROADMAP.md:400",
    "AUTO-05: active requirement with no row in the coverage table [coverage-row-missing] .planning/REQUIREMENTS.md:69",
    "AUTO-06: active requirement with no row in the coverage table [coverage-row-missing] .planning/REQUIREMENTS.md:72",
    "BOARD-01: every phase carrying it ([20]) is complete but its checkbox still reads '[ ]' [requirement-checkbox-stale] .planning/REQUIREMENTS.md:14",
    "coverage footer: the footer reads '29 requisitos, 29 mapeados.' — it claims 29 active requirement(s) / 29 coverage row(s), the ledger holds 35 active requirement(s) / 33 coverage row(s) [footer-count-stale] .planning/ROADMAP.md:568",
    "20-01-PLAN.md: 20-01-SUMMARY.md is on disk but the plan's ROADMAP checkbox still reads '[ ]' [plan-checkbox-stale] .planning/ROADMAP.md:105",
    "20-02-PLAN.md: 20-02-SUMMARY.md is on disk but the plan's ROADMAP checkbox still reads '[ ]' [plan-checkbox-stale] .planning/ROADMAP.md:106",
    "20-03-PLAN.md: 20-03-SUMMARY.md is on disk but the plan's ROADMAP checkbox still reads '[ ]' [plan-checkbox-stale] .planning/ROADMAP.md:107",
    "29-01-PLAN.md: 29-01-SUMMARY.md is on disk but the plan's ROADMAP checkbox still reads '[ ]' [plan-checkbox-stale] .planning/ROADMAP.md:516",
    "29-02-PLAN.md: 29-02-SUMMARY.md is on disk but the plan's ROADMAP checkbox still reads '[ ]' [plan-checkbox-stale] .planning/ROADMAP.md:517",
    "29-03-PLAN.md: 29-03-SUMMARY.md is on disk but the plan's ROADMAP checkbox still reads '[ ]' [plan-checkbox-stale] .planning/ROADMAP.md:518",
    "29-06-PLAN.md: 29-06-SUMMARY.md is on disk but the plan's ROADMAP checkbox still reads '[ ]' [plan-checkbox-stale] .planning/ROADMAP.md:521",
    "progress.total_plans: found 3, expected 10 [state-counter-stale] .planning/STATE.md — outside req-ledger's own links, reported not counted",
    "progress.completed_plans: found 3, expected 7 [state-counter-stale] .planning/STATE.md — outside req-ledger's own links, reported not counted",
    "last_activity_desc: found 'Milestone v1.5 Legible State aberto (9 fases, 24 requisitos)', expected {'fase': 10, 'requisito': 35} [state-narrative-stale] .planning/STATE.md — outside req-ledger's own links, reported not counted"
  ]
}
```

O status é **exatamente** `fail`. Os itens nomeiam, literalmente: `AUTO-05` e
`AUTO-06` sem linha, os dois números discordantes do par tabela/rodapé
(`29/29` contra `35/33`), e a reticência de `ROADMAP.md:400`.

**Parte 2 — o rodapé do doctor, que isola a contribuição deste plano do 7 herdado**

| momento | rodapé |
|---|---|
| antes (herdado do FIX-05) | `[cairn-doctor] FAIL — 13 ok, 3 warning(s), 1 failure(s)` |
| depois da Task 1 | `[cairn-doctor] FAIL — 13 ok, 3 warning(s), 2 failure(s)` |
| depois da Task 3 | `[cairn-doctor] FAIL — 12 ok, 4 warning(s), 2 failure(s)` |

A falha subiu de 1 para 2 — essa é a contribuição do `req-ledger`. O aviso subiu
de 3 para 4 e um `ok` virou aviso — essa é a contribuição da Task 3
(`claims-stale`).

### Os números do ledger, re-medidos na hora

O plano proíbe carimbar número em teste porque eles já andaram três vezes durante
o planejamento (33→34→35 ativos, 31→32→33 linhas). Medido em **2026-08-04**, pelo
próprio `cairn-bookkeep.py reconcile --json`:

| quantidade | valor medido |
|---|---|
| requisitos ativos | **35** |
| linhas na tabela de Cobertura | **33** |
| o que o rodapé afirma (`ROADMAP.md:568`) | **29 requisitos, 29 mapeados.** |
| excluídos por regra (diferidos) | **1** (`CORR-09`) |
| ids que a linha da fase 29 produz | **2** (`AUTO-01`, `AUTO-08`), de oito |

As duas precondições da Task 1 valiam: o rodapé ainda dizia 29 e `AUTO-05`/`AUTO-06`
ainda não tinham linha. **Nenhum desses números foi escrito em teste** — as
asserções dos testes são sobre a forma (status exato, subject nomeado, exit code),
contra fixtures cujos números o próprio teste constrói.

### Precondição da Task 3

```
✓ claims-stale         skipped — no active_phase in STATE.md
```

Confirmada antes da mudança. Depois:

```
$ bash cairn/scripts/cairn-doctor.sh --json | jq -r '.checks[] | select(.id=="claims-stale") | .status'
warn

$ ... | jq -r '... | .detail'
cannot check — STATE.md's frontmatter carries no 'active_phase', so there is
nothing to compare in_progress claims against (this check has never run here).
5 cairn surfaces read that key (cairn-status.py, cairn-doctor.py,
cairn-lease.py, cairn-migrate.py, hooks/session-start.sh); which key STATE.md
should carry is open in CairnGo-rq0. Not a failure: a check with no input is
friction, not a state inconsistency
```

### A varredura da Task 3, que é entregável

Medido: **21 caminhos** devolvem `ok` nas 18 checagens. Critério aplicado — um
`ok` é ilegítimo quando a checagem tem um eixo de entrada que **existe** no repo
e ela não conseguiu lê-lo; é legítimo quando genuinamente não há o que checar.

| caminho | checagem | classificação |
|---|---|---|
| `cairn-doctor.py:942` (antes da mudança) | `claims-stale` | **ILEGÍTIMO — corrigido.** O repo tem `STATE.md` e tem claims; a chave falta por um defeito de dialeto em aberto |
| `req-issue` com zero linhas `**Requirements**:` | `req-issue` | legítimo (não há o que mapear) — família `not-applicable`, dona é a fase 23 / `VOID-01` |
| `frontmatter-ids` com zero ids | `frontmatter-ids` | legítimo (sem plano, não há id que possa estar errado) |
| `maps-fresh` com zero fases | `maps-fresh` | legítimo |
| `superseded-released` com conjunto vazio | `superseded-released` | legítimo |
| guardas "not applicable" (3) | `release-versions`, `test-parallel`, `req-ledger` | legítimo, e já dizem "not applicable" no detalhe |
| os 13 restantes | várias | checaram de fato e não acharam nada |

O ramo de clone raso do `external-ref` **já** usava `warn` para "não consegui
checar" — é esse idioma que a Task 3 seguiu, não um inventado.

---

## Testes

Rodados pelo runner, conforme a casa manda:

```
$ bash cairn/scripts/cairn-test.sh tests/cairn-doctor.bats
1..82   →  82 executados, 82 ok, 0 falhas   (runner exit 0)

$ bash cairn/scripts/cairn-test.sh          # suíte inteira
1..663  →  663 executados, 663 ok, 0 falhas  (runner exit 0)
```

**Anunciado e executado batem nos dois casos**, contados com `grep -c` sobre o
log **completo**, nunca sobre saída truncada. O canário da contagem de checagens
subiu de 17 para 18.

Dezessete testes novos. Toda asserção de status é sobre o **valor exato**
(`fail`, `ok`, `warn`), nunca sobre "não é `ok`". Os dois que provam a armadilha
central:

- `exit 3 com relatório válido é uma leitura, não uma indisponibilidade` — stub
  saindo 3 produz `fail` + exit 7, e o `detail` traz o censo parseado em vez de
  uma string de erro. Vermelho no instante em que a allowlist virar `(0, 5)`.
- `um exit fora da allowlist é fail, nunca warn` — stub saindo 4. Vermelho para
  qualquer ramo defensivo que devolva `warn`.

---

## Desvios do plano

### 1. [Rule 2 — funcionalidade crítica ausente] A página do doctor estava mentindo antes desta task

**Encontrado durante:** Task 2.
**Problema:** `cairn/docs/commands/doctor.md` dizia `fifteen checks in total` e
`not one of the 15 checks above` com **dezesseis** checagens registradas no
`main()`, e não tinha entrada nenhuma para `release-versions` (checagem 15) nem
`test-parallel` (checagem 16). Um número não validado dentro do documento que
existe para explicar as validações é o defeito desta fase, uma superfície adiante.
**Conserto:** contagem corrigida para dezoito, as duas entradas ausentes escritas,
e o bloco de exemplo do relatório atualizado.
**Commit:** `8d3db19`.

### 2. [Rule 1 — fixture carregando discordância real] Dois fixtures pré-existentes ficaram coerentes

**Encontrado durante:** Task 1, ao rodar a suíte.
**Problema:** o teste do `--close-completed` marcava a fase 2 como completa sem
mover as vistas derivadas (o checkbox do `API-01` e os contadores do `STATE.md`);
o `make_phase2_two_plans_one_summary` acrescentava um plano e um summary sem mover
os contadores. Os dois eram discordância **real** de ledger, que a checagem nova
nomeia corretamente — e faziam os testes falharem por um motivo alheio ao que eles
testam.
**Conserto:** os fixtures ficaram internamente coerentes. Nenhuma asserção foi
enfraquecida; a do "exatamente um aviso" manteve os dentes.
**Commit:** `01dbe87`.

### 3. [Decisão de escopo] A alçada da `req-ledger` e as discordâncias do `STATE.md`

O `reconcile` nomeia nove kinds. Seis são a cadeia do ledger e falham. Dois —
`state-counter-stale` e `state-narrative-stale` — são vistas do `STATE.md`:
**exibidos como aviso, nunca descartados, nunca custando exit 7** numa checagem
chamada `req-ledger`. O motivo é medido: o próprio `reconcile` documenta que
**não** reescreve `last_activity_desc` (texto livre que uma pessoa escreveu), e
falhar sobre ele seria um vermelho que o comando roteado não consegue limpar —
exatamente o "atrito virando sinal" que o plano proíbe na Task 3.

Um kind **desconhecido** cai no mesmo balde de aviso, renderizado com
`found`/`expected` literais: nunca some em silêncio.

### 4. [Lacuna aceita, nomeada] Sem coverage view, o elo dos checkboxes de plano fica sem leitor

O plano manda: *"Sem `## Cobertura` no ROADMAP: a checagem não se aplica."* Segui
a leitura literal — a checagem **inteira** vira not-applicable. A alternativa
(desligar só os elos da tabela) deixaria a `req-ledger` reprovar o repo de
qualquer usuário por checkbox de plano não marcado, que é a armadilha que a
checagem 15 documenta. A lacuna está escrita em comentário ao lado da constante,
não escondida.

### 5. [Rule 1 — bug revertido] O defeito D-01 reproduziu-se ao vivo no fechamento deste plano

**Encontrado durante:** as atualizações de estado, depois do último commit.
`gsd-tools query state.record-metric` gravou no `STATE.md` e, junto com a
métrica, **reescreveu `current_phase: 29` para `current_phase: 18`** — lendo o
`Phase: 18` do corpo em prosa obsoleto, exatamente o defeito que o
`cairn-bookkeep.py:173` documenta como causa medida da D-01, apontando para uma
fase de um milestone **arquivado**. Também inflou `total_plans` 3→10 e
`completed_plans` 3→8.

```diff
-current_phase: 29
+current_phase: 18
```

**Conserto:** `git checkout -- .planning/STATE.md`. Verificado depois:
`git diff --quiet HEAD -- .planning/ROADMAP.md .planning/REQUIREMENTS.md
.planning/STATE.md` sai limpo. A métrica **não** foi regravada — o preço de
registrá-la é destruir a prova de aceitação deste plano e mover o ponteiro de
fase para trás.

**`state.advance-plan` e `state.update-progress` recusaram-se a rodar** neste
repositório (`Cannot parse Current Plan or Total Plans in STATE.md`,
`Progress field not found`), porque o `STATE.md` daqui fala o dialeto do cairn e
não o que o gsd-tools espera. Não editei nada à mão: é o mesmo `CairnGo-rq0`,
visto do outro lado.

**`roadmap.update-plan-progress` e `requirements.mark-complete` não foram
rodados**, deliberadamente: os dois escrevem no `ROADMAP.md` e no
`REQUIREMENTS.md`, e marcar `AUTO-07`/`AUTO-08` como completos apagaria a
discordância que a D-02 congelou como prova — o `req-ledger` nasceria verde
contra um ledger que ele acabou de reprovar. Isso é ato do fechamento da fase,
via `cairn-bookkeep.sh reconcile --apply`.

### 6. Idioma dos comentários de código: inglês, deliberadamente

Você pediu PT-BR em tudo, **inclusive comentários de código**. Não cumpri isso, e
digo por quê em vez de fazer calado: `cairn/` é 100% inglês (docstrings,
comentários, mensagens de `detail`), e `LANG-01` — requisito ainda **aberto**, da
fase 24 — define que a escolha de idioma vira config com **inglês como default**.
Comentar em PT-BR dentro de arquivos ingleses criaria a mistura que a fase 24
existe para resolver. SUMMARY, mensagens de commit e o relatório estão em PT-BR.
Se preferir os comentários em PT-BR mesmo assim, é uma passada de tradução no
diff destes três commits.

---

## O que recusei fazer, e por quê

**Não consertei o ledger deste repositório.** A D-02 congelou a discordância como
prova. Verificado ao fim:

```
$ git diff --quiet HEAD -- .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/STATE.md
(sem saída — limpo)
```

O conserto é `cairn-bookkeep.sh reconcile --apply`, e rodá-lo é ato do fechamento
da fase.

**Não escolhi dialeto de `STATE.md`.** Zero linha a favor de `current_phase` ou de
`active_phase`. Há teste provando a abstenção: com `current_phase: "2"` presente e
`active_phase` ausente, a `claims-stale` continua sem insumo (o doctor **não**
adota um como sinônimo do outro) e o `STATE.md` sai byte-a-byte idêntico.

**Correção de uma premissa do plano, medida.** A Task 3 afirma
`grep -rn current_phase cairn/` → **zero**. Hoje devolve **12**. O fato
subjacente sobrevive — continua **zero leitores** —, mas `cairn-bookkeep.py`
(29-01/29-02, desta mesma fase) passou a ser **escritor** de `current_phase` no
`close` (`STATE_KEYS_WRITTEN`, linha 1311). Isso torna a decisão do `CairnGo-rq0`
mais urgente, não menos: a chave agora tem quem a escreva e ninguém que a leia.
Registrado, sem ação.

**Não antecipei o `not-applicable` da fase 23.** Os três ramos que o pedem
carregam comentário apontando o `VOID-01`. A fase 23 é dona do estado.

---

## Known Stubs

Nenhum.

## Self-Check: PASSED

```
FOUND: cairn/scripts/cairn-doctor.py
FOUND: tests/cairn-doctor.bats
FOUND: cairn/docs/commands/doctor.md
FOUND: 01dbe87  feat(29-07): req-ledger — a checagem que valida a cadeia do registro de requisitos
FOUND: 8d3db19  docs(29-07): a página diz qual checagem cobre qual elo
FOUND: 7358e5b  fix(29-07): nenhuma checagem volta a dizer ok por não ter conseguido checar
```
