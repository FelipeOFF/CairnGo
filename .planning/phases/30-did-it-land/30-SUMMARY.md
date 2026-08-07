---
phase: 30-did-it-land
plans: 4
requirements: [PR-01, PR-02, PR-03, PR-04]
commits: [0823f06, 549b346, 871b2b6, 1ad90df]
status: complete
completed: 2026-08-06
---

# Fase 30: Did it land — Resumo

**O board passa a responder "isto entrou?", e responde do git que já está no
disco. A pergunta gêmea — "qual PR levou?" — recebe duas palavras, `found` e
`unknown`, e a terceira é proibida por desenho.**

## O que existe agora que não existia

| | antes | depois |
|---|---|---|
| o board sabe da branch de controle | nada | `landed` por fase e por tarefa, no modelo, no `--json` e como sufixo `⤒` |
| o doutor cobra trabalho não entregue | silêncio | checagem 19, `phase-landed`, nomeando 9 fases completas fora de `origin/main` |
| a rede | não existia caminho | um arquivo separado, atrás de `git.review_state` cujo default é `off` |
| PR não descobrível | — | `unknown` com motivo, e nenhuma superfície diz "sem PR" |

## Os números medidos contra este repositório, hoje

```
commits alcançáveis de HEAD .................... 530
commits alcançáveis de origin/main ............. 385
o conjunto "não entrou" (origin/main..HEAD) .... 145

fases que o histórico local localiza ............ 24
   landed em origin/main ....................... 13
   unlanded .................................... 11

fases completas fora da branch de controle ...... 9   (o achado novo do doutor)
fases completas que o histórico não localiza .... 6   (7 a 12, nomeadas, não cobradas)

PR descobrível offline, sobre 24 fases .......... 0   (24/24 unknown :: no-reference)
```

A última linha é a que decide se a fase foi honesta. **Cem por cento** das fases
deste projeto são indescobríveis offline — inclusive as sete que a PR #21
entregou. Uma implementação que respondesse "sem PR" estaria mentindo sobre
todas as 24, com a suíte verde.

## A arquitetura, em uma linha por seta

```
cairn-status.py ──► cairn-land.py ──► git, e o ARQUIVO de cache
cairn-doctor.py ──► cairn-land.py
cairn-review.py ──► gh / glab                          (nunca ao contrário)
```

`cairn-land.py` é o **único dono** da leitura do git por trás da pergunta. Nem o
board nem o doutor leem git para isso — dois leitores de um fato é o defeito que
este milestone já pagou duas vezes, e a checagem 17 existe por causa dele.

A rede mora num arquivo que o board não alcança, e isso é **estrutura, não
promessa**: os inventários de AST afirmam 5 sítios de `subprocess.run` no
`cairn-status.py` e 2 no `cairn-land.py`, nenhum deles ferramenta de rede, e um
teste no `cairn-review.bats` afirma a mesma fronteira pelo outro lado. Mover o
fetch para qualquer um dos dois exigiria apagar essas asserções para entregar —
que é exatamente a conversa que deve acontecer em voz alta.

## Os defeitos que a medição pegou, e que nenhum plano previu

**A branch em que HEAD está era detectada como branch de controle.** `git init`
deixa o checkout numa branch chamada `main` ou `master` — as duas nomes
convencionais —, então o detector reportava **toda fase de um repositório novo
como `landed`**. Um verde produzido pelo fixture, não pelo trabalho.

**O degrau `fail` do doutor era inalcançável por construção.**
`roadmap_completed_phases()` lê o ROADMAP corrente, e ele lista só o ciclo
aberto — nove fases, nenhuma das dezenove arquivadas. As fases que o degrau
existe para pegar são exatamente as que o arquivamento tirou daquele arquivo.

**O commit que fecha uma fase não toca a pasta dela.** `6545a5c chore(29): fecha
a fase 29` mexe em ROADMAP/STATE/REQUIREMENTS. Atribuição por diretório sozinha
perderia justamente o commit que o próprio contexto da fase nomeia.

**O docstring do `cairn-doctor.py` dizia "eighteen checks in total" com
dezenove registradas** — errado desde a fase 24. Quinto precedente medido, neste
repositório, de número mantido à mão que envelheceu.

**Uma string de roteamento apontava para `/cairn:land`, que não existe.**
Corrigida para nomear o script que existe, e a ausência dos dois wrappers virou
`CairnGo-3w9`.

## Verificação por mutação — 17 quebras, 17 asserções vermelhas

Cinco no 30-01, três no 30-02, quatro no 30-03, cinco no 30-04. Cada uma
aplicada **de verdade no fonte**, a suíte rodada, e o fonte restaurado de uma
cópia feita antes (`cp`, nunca `git checkout --`). Todas estão tabeladas no
`-SUMMARY.md` do plano que as guarda, com a asserção exata que caiu.

Duas delas ficam vermelhas em **dois lugares independentes**, o que é o desenho:
escrever um `gh` no `cairn-land.py` derruba o inventário do próprio arquivo
**e** o teste de fronteira do `cairn-review.bats`; trocar `out-of-scope` por
`no-input` na checagem 19 derruba a asserção de escopo **e** o rodapé do fixture
saudável.

## Suítes

Só os `.bats` tocados, nunca a suíte inteira — a orquestração paga essa conta
uma vez no fim.

| Lote | Suítes | Testes | Exit |
|---|---|---|---|
| A | `cairn-doctor`, `cairn-land`, `cairn-review` | 155 | 0 |
| B | `cairn-config`, `cairn-board-invariance`, `cairn-tracker-card`, `cairn-group-model`, `cairn-status`, `cairn-phase-card`, `cairn-grouped-board`, `cairn-corroboration` | 177 | 0 |
| C | `cairn-bookkeep`, `cairn-init`, `cairn-jira`, `cairn-journal`, `cairn-phase-model`, `cairn-reconcile`, `cairn-test`, `hooks` | 203 | 0 |
| D | `cairn-parallel`, `cairn-parallel-autonomous`, `cairn-migrate` | 77 | 0 |

Os lotes C e D não foram escolhidos por conforto: são **toda** suíte que cita
`cairn-status`, `cairn-config` ou `cairn-doctor` e que os lotes A e B não já
cobriam, enumerada por `grep` em vez de por memória.

**612 executados em 22 suítes, 612 verdes, 0 vermelhos**, contados sobre o log
inteiro.

`git diff --quiet HEAD -- tests/fixtures/board-render/` limpo: os sete renders de
referência não se moveram um byte, e isso foi **provado** — o sufixo tornado
incondicional derruba `the wide board renders the reference bytes`.

`git diff --quiet HEAD -- .planning/ROADMAP.md .planning/REQUIREMENTS.md
.planning/STATE.md` limpo: a escrituração é do operador.

## O que ficou por fazer, e por quê

- **Nenhuma chamada de rede real foi feita**, em teste nenhum. O `gh` da suíte é
  um stub que responde de um payload enlatado. O que **não** está provado é que
  `gh pr view --json number,state,title,url,mergedAt` devolve esses campos com
  essa grafia contra a API de verdade, e o caminho do `glab` foi escrito sem
  medição nenhuma. Está em `behavior_unverified`, com o teste humano que o cobre.
- **Os dois scripts novos não têm wrapper `/cairn:*` nem página em
  `docs/commands/`.** Fora dos quatro requisitos, registrado em `CairnGo-3w9`.
- **O board HTML não carrega aterrissagem.** Diferido por escrito no
  `30-CONTEXT.md`.
