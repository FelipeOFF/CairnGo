---
phase: 30-did-it-land
plan: "04"
subsystem: sync
tags: [doctor, check, warn, fail, canary, archived-milestone, bats]

requires:
  - phase: 30-01
    provides: "cairn-land.py report --json — o relatório que esta checagem consome sem re-derivar um byte"
provides:
  - "checagem 19, id phase-landed: fase completa fora da branch de controle vira achado nomeado"
  - "archived_phase_numbers(): as fases dos ciclos arquivados, lidas do disco"
  - "sete testes novos, um por degrau da escada, mais o seam pinado por stub"
affects: [doctor, ship, autonomous]

actuals:
  tokens: 0
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns:
    - "a severidade separa atrito de inconsistência: warn para o ciclo aberto, fail só para o ciclo já fechado"
    - "achado nomeado sem ser cobrado: `unknown ::` nos items, sem mover o status"
    - "o seam pinado por stub que responde um veredito diferente do repositório real"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-doctor.py
    - cairn/docs/commands/doctor.md
    - tests/cairn-doctor.bats

key-decisions:
  - "O universo de 'completa' é o ROADMAP corrente UNIÃO as fases arquivadas: medido, o ROADMAP lista só o ciclo aberto (9 fases), então lê-lo sozinho tornaria o degrau `fail` inalcançável por construção"
  - "warn para o ciclo aberto, fail para o arquivado — a mesma distinção que o 29-06 e o 29-07 fizeram"
  - "fase que o histórico não localiza é NOMEADA e não cobrada: as 7 a 12 daqui são de ciclos anteriores à convenção de escopo"
  - "O doutor não lê git: `cairn-land.py` pelo seam CAIRN_LAND, forma das checagens 3 e 17"

patterns-established:
  - "O canário de contagem é editado nos DOIS sítios na mesma mudança, depois de ler a nota que explica por que ele existe"

requirements-completed: [PR-04]

duration: 45min
completed: 2026-08-06
status: complete
---

# Fase 30 Plano 04: o doutor cobra a fase completa que não entrou — Resumo

**A prova de aceitação virou verdade medida: o doutor deixou de ficar calado
sobre nove fases completas que não estão em `origin/main`.**

## Antes e depois, no repositório real

Antes deste plano o doutor saía 7 e **não dizia uma palavra** sobre nenhuma das
nove. Depois:

```
⚠ phase-landed   9 complete phase(s) have not reached the control branch yet —
                 28 complete phase(s) (19 archived), control branch
                 origin/main (detected): run /cairn:ship
   - phase 20 is complete and its 14 commit(s) are not on origin/main
   - phase 21 is complete and its 15 commit(s) are not on origin/main
   … (22, 23, 24, 26, 27, 28)
   - phase 29 is complete and its 34 commit(s) are not on origin/main
   - unknown :: phase 7 — no-commits: the local history places no commit in
     this phase, so whether its work landed cannot be answered here
   … (8, 9, 10, 11, 12)
```

As fases 1–6 e 13–19 são arquivadas **e** aterrissadas: silêncio, que é o
comportamento certo.

## O defeito que a medição pegou no meio do plano

`roadmap_completed_phases()` lê o `.planning/ROADMAP.md` **corrente**, e medido:
esse arquivo lista só o ciclo aberto — nove fases, nenhuma das dezenove já
arquivadas. Lê-lo sozinho tornaria o degrau `fail` **inalcançável por
construção**, porque as fases que ele existe para pegar são exatamente as que o
arquivamento tirou daquele arquivo. O universo virou a união com as pastas sob
`.planning/milestones/<key>-phases/`, que são completas por construção — um
ciclo só arquiva quando fecha. Verificado por mutação: sem a união, o teste do
milestone arquivado deixa de sair 7.

## A escada, e o porquê de cada degrau

| situação | status | razão escrita |
|---|---|---|
| ciclo **aberto**, ainda não empurrado | `warn` | atrito é o estado normal de quem está no meio de um ciclo, e gastar o exit 7 com atrito é como o 7 deixa de significar algo |
| milestone **arquivado**, nunca entrou | `fail` | um ciclo **fechou** sobre trabalho que a branch de controle não tem |
| o histórico não localiza a fase | nomeado, **não cobrado** | as fases 7–12 daqui são de ciclos anteriores à convenção de escopo; cobrar isso daria a todo repo antigo um achado permanente sobre histórico que ninguém vai reescrever |
| sem branch de controle | `not-applicable` / `out-of-scope` | um repo de uma branch só não tem com o que comparar, permanentemente. `no-input` daria a todos eles um rodapé INCOMPLETE para sempre |
| `cairn-land.py` quebrado | `warn`, nunca `fail` | não conseguir fazer a pergunta não é a resposta ser ruim |

## O canário de contagem, e o número em prosa que já estava errado

Os **dois** sítios de `tests/cairn-doctor.bats` foram para 20 na mesma mudança,
depois de ler a nota que registra por que o canário existe (fases 23 e 24 em
paralelo, git mesclando sem conflito, cada branch certa sozinha).

E, ao atualizar os números de prosa, apareceu um achado: o docstring do
`cairn-doctor.py` dizia **"Runs first — eighteen checks in total"** com
**dezenove** registradas — errado desde a fase 24. Corrigido para vinte, com o
episódio escrito ao lado. É o quinto precedente medido, neste repositório, de
número mantido à mão que envelheceu.

Três outros números de prosa também foram para 20: `cairn-doctor.py:435`
("of the 19 checks above"), `doctor.md` ("nineteen checks in total" e "not one
of the 19 checks").

## Verificação por mutação — cinco quebras

| Quebra aplicada | Asserção que ficou vermelha |
|---|---|
| tirar a união com as fases arquivadas | `an ARCHIVED milestone's phase that never landed fails` → exit 7 → 0 |
| cobrar `fail` também no ciclo aberto | `a complete phase ahead of the control branch warns` → exit 0 → 7 |
| cobrar os `unknown` como warnings | `a complete phase the history cannot place raises nothing` → `ok` → `warn` |
| trocar `out-of-scope` por `no-input` | `no control branch is out-of-scope, never a gap` **e**, independentemente, `healthy wired fixture` (o rodapé deixa de ler `ok`) |
| remover a checagem do registro | `healthy wired fixture` → `.checks \| length` 20 → 19 — **o canário** |

Com `cp` prévio e restauro **da cópia**; `diff` final vazio.

## Suítes

`tests/cairn-doctor.bats` 110/110 (103 antes deste plano, mais sete).
