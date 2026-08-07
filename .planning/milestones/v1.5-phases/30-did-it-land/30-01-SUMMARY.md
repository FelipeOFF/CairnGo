---
phase: 30-did-it-land
plan: "01"
subsystem: ui
tags: [git, control-branch, landing, board, config, tripwire, offline, bats, ast, stdlib]

requires:
  - phase: 29-03
    provides: "o .cairn/config.json de esquema fechado, onde git.control_branches passa a morar"
  - phase: 29-05
    provides: "as três camadas de prova de ausência de rede, e a disciplina do sufixo condicional ao dado"
provides:
  - "cairn-land.py: o único dono da leitura do git por trás de 'isto entrou na branch de controle?'"
  - "git.control_branches no esquema fechado, com três leitores nomeados"
  - "landed por fase e por tarefa no modelo e no --json; sufixo ⤒ condicional no board"
  - "tests/cairn-land.bats: 27 testes, com as três camadas de tripwire apontadas para o script novo"
affects: [status, doctor, autonomous, ship, html-board]

actuals:
  tokens: 0
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "ancestralidade por complemento: `git rev-list HEAD --not <branch>` responde para todos os commits numa chamada, com o mesmo veredito de merge-base --is-ancestor por par"
    - "atribuição por duas fontes nomeadas, porque cada uma sozinha foi medida perdendo commit real"
    - "a branch em que HEAD está nunca é branch de controle detectada — ela contém o trabalho por construção"
    - "verificação por mutação com cópia de arquivo e restauro da cópia, nunca git checkout --"

key-files:
  created:
    - cairn/scripts/cairn-land.py
    - cairn/scripts/cairn-land.sh
    - tests/cairn-land.bats
  modified:
    - cairn/scripts/cairn-status.py
    - cairn/scripts/cairn-config.py
    - cairn/docs/commands/status.md
    - cairn/docs/commands/config.md
    - tests/cairn-tracker-card.bats
    - tests/cairn-group-model.bats
    - tests/cairn-config.bats
    - tests/cairn-status.bats

key-decisions:
  - "A leitura do git mora num script próprio, não no cairn-status.py: a mesma forma que o check_maps_fresh usa para o cairn-map.py e o check_req_ledger para o cairn-bookkeep.py, e é o que permite o doutor do 30-04 consumir o MESMO relatório em vez de reimplementar a pergunta"
  - "`git rev-list HEAD --not <branch>` em vez de um merge-base por par: mesmo veredito, uma chamada por branch, e o custo escala com o quanto o checkout está adiantado — 145 aqui"
  - "Duas fontes de atribuição, path E scope, porque medido cada uma sozinha perde commit real"
  - "A branch corrente nunca é detectada — defeito real que o fixture pegou"
  - "landed por tarefa é PROJEÇÃO da fase, não uma segunda leitura do git: as 41 menções a id do bd em corpo de commit são referências em prosa, não atribuições"

patterns-established:
  - "Chave de config nova chega com TODOS os seus leitores nomeados e todos entregues no mesmo ciclo"
  - "Um relatório degradado devolve TODAS as chaves do caminho normal — uma chave a menos vira KeyError no renderizador duas linhas depois"

requirements-completed: [PR-01]

duration: 95min
completed: 2026-08-06
status: complete
---

# Fase 30 Plano 01: "isto entrou?", respondido do git local — Resumo

**O board passa a dizer, por fase e por tarefa, se o trabalho entrou na branch
de controle, e quem responde é um script novo que é o único dono dessa leitura
do git — o `cairn-status.py` não tem a string `git` em lugar nenhum.**

## Realizações

- **`cairn-land.py`, com três verbos.** `detect` (candidatas + evidência),
  `apply` (a confirmação única, gravada **através do `cairn-config.py`**, que é
  o dono do arquivo), `report` (o veredito por fase). O `cairn-status.py` e o
  `cairn-doctor.py` do 30-04 consomem o mesmo relatório: dois leitores de git
  que pudessem discordar sobre o mesmo repositório é o defeito que este
  milestone já pagou duas vezes.
- **A ancestralidade sai por complemento, não por par.** `git merge-base
  --is-ancestor A B` é exato e é o que o contexto prescreve, mas responde UM
  par por processo — dez fases × duas branches seriam vinte processos por
  render. `git rev-list HEAD --not <branch>` é exatamente o conjunto dos
  commits alcançáveis de HEAD que **não** entraram na branch, então o teste
  vira pertinência de conjunto com o mesmo veredito. **Medido:** 530 commits
  de HEAD, 385 de `origin/main`, conjunto complementar de **145** — e o
  veredito para a fase 29 é `unlanded`, que concorda com o
  `git merge-base --is-ancestor 6545a5c origin/main` falso do contexto.
- **Duas fontes de atribuição, e cada uma cobre o que a outra perde.**
  `path` (o commit tocou `<planning>/phases/NN-*/`) e `scope` (o escopo do
  conventional commit nomeia a fase). Medido: `6545a5c chore(29): fecha a fase
  29` — o commit que **fecha** a fase 29 — toca ROADMAP/STATE/REQUIREMENTS e
  **não** a pasta da fase; e 313 dos 530 commits carregam escopo de fase, o que
  é convenção deste projeto e não de todos.
- **O relatório inteiro, contra este repositório:** fases 1–6 e 13–19
  `landed` em `origin/main`; 20–30 `unlanded`. Fase 29: 34 commits, nenhum na
  branch de controle. Nenhuma superfície do cairn dizia isso antes.
- **A prova de ausência de rede, apontada para o arquivo novo.** As três
  camadas do 29-05 (`sitecustomize` de socket, allowlist de `PATH` com `curl`,
  `wget`, `gh` e `glab` armadilhados, inventário de AST) agora rodam contra o
  `cairn-land.py`, que é o arquivo onde alguém plausivelmente escreverá um
  fetch ao vivo. Inventário: **2 sítios** (`git` e `sys.executable`).
  `cairn-status.py` foi de 4 para **5** sítios, e o quinto é `sys.executable` —
  é assim que a resposta chega ao board sem que a palavra `git` seja escrita
  ali.

## Defeito real, achado pelo fixture

**A branch em que HEAD está era detectada como branch de controle.** `git init`
deixa o checkout numa branch chamada `main` ou `master` — as duas nomes
convencionais —, então o detector tomava a branch corrente e reportava **toda
fase de um repositório novo como `landed`**: um verde produzido pelo fixture,
não pelo trabalho. Uma branch em que você está contém o seu trabalho por
construção, e perguntar se o trabalho entrou nela não é a pergunta de ninguém.
A regra virou código, virou teste nomeado, e só um `apply` explícito pode
nomear a branch corrente.

Segundo defeito, do mesmo tipo: o retorno degradado de `build_report` (sem git)
devolvia menos chaves que o caminho normal, e o renderizador estourava
`KeyError` duas linhas depois. "Degrada com elegância" com uma chave a menos é
um traceback com outro nome.

## Verificação por mutação — cinco quebras, cinco asserções vermelhas

| Quebra aplicada | Asserção que ficou vermelha |
|---|---|
| apaga a passada de atribuição por escopo | `the closing commit is attributed by SCOPE` → `.phases["3"].commits` 2 → 1 |
| deixa a branch corrente ser detectada | `the branch HEAD is standing on is never detected` → `.source` `none` → `conventional` |
| colapsa `unknown` em `unlanded` sem branch | `no control branch is unknown with a reason, never unlanded` |
| torna o sufixo incondicional | `renders no landing suffix at all` **e** `the wide board renders the reference bytes` (os sete renders) |
| escreve um `subprocess.run(["curl", …])` real | camada 3 (`invokes an allowlisted binary`) **e** camada 2 (`runs under both tripwires`); os **três** controles negativos seguiram verdes |

Todas com `cp` prévio e restauro **da cópia**, nunca `git checkout --`, e o
`diff` final contra as cópias saiu vazio nos dois arquivos.

## Suítes

`tests/cairn-land.bats` 27/27 · `cairn-config.bats`, `cairn-status.bats`,
`cairn-group-model.bats`, `cairn-board-invariance.bats`,
`cairn-tracker-card.bats` — **158 verdes, 0 vermelhos**, contados sobre o log
inteiro. `git diff --quiet HEAD -- tests/fixtures/board-render/` limpo: nenhuma
referência regenerada.

## O que eu recusei fazer

**Não li o corpo dos commits.** O log com corpo é 476216 bytes contra 80605 sem
ele, e o único uso que teria era atribuir commit a issue do bd — medido, as 41
menções a id do bd em corpo neste histórico são referências em prosa
(`bd issue CairnGo-gbu`, `(CairnGo-0rk)`), não atribuições. Ler seis vezes os
bytes para inferir um vínculo que ninguém escreveu é como um board inventa um
fato. `landed` por tarefa é projeção da fase, e está escrito que é.

**Não toquei em ROADMAP.md, REQUIREMENTS.md nem STATE.md.** A escrituração é do
operador. Verificado: `git diff --quiet HEAD --` nos três sai limpo.

**Não fiz chamada de rede em caminho nenhum**, nem escondida atrás de flag.
O `gh` está nesta máquina; isso é conveniência local, não licença.
