# Fase 36 — itens fora de escopo, encontrados durante a execução

Achados que a onda que os encontrou NÃO consertou, por estarem fora do escopo do
plano dela. Cada um traz a medição que o sustenta.

## 1. `tests/cairn-gsd.bats` teste 16 vermelho — baseline do doctor (onda 5)

`CHECK-04: baseline do cairn-doctor fixada — a fase 35 nao evolui o doctor` reprova
com `cairn-doctor.py MUDOU dentro da fase 35 (blob 94e26233… != baseline e2040aea…)`.

**Não é desta fase.** `cairn-doctor.py` foi alterado pelos commits `19f00ee`
(`export-identity`) e `a2527ee` (`a checagem 23 pergunta se as issues sobrevivem a esta
máquina`), que chegaram ao branch da fase pelo merge `8b5714f` vindo de
`feat/v1.6-transplante`. Nenhuma onda da 36 tocou o arquivo: `git status` na onda 5
não o lista, e o blob no disco é o mesmo do commit. O pin é atualizado deliberadamente
pela fase que evoluir o doctor — o próprio teste diz "a 37".

**Ação:** atualizar o pin em `tests/cairn-gsd.bats` no plano/fase que assumir a
evolução do doctor, com o blob novo e a razão escrita.

## 2. Partição de journal com hostname cru, anterior ao `fix(identity)` (onda 5)

`.cairn/journal/<particao-deste-worktree>` (id 777ec9808394) — **não rastreada**,
e `.gitignore` a deixa passar por desenho (`!.cairn/journal/*.jsonl`, fase 28: as
partições são o único versionado sob `.cairn/`).

Medido: 1 registro, `ts 2026-08-11T13:45:08Z`, `"machine"` com o hostname cru (valor nao reproduzido aqui: CairnGo-xclf),
`holder` com o caminho absoluto do worktree, e o hostname sanitizado no NOME do arquivo.
É exatamente o que `dc9ad45` (`fix(identity)`, 2026-08-11T19:39 local) fechou — e o
arquivo é **anterior** a ele por ~6h, o que faz dele resíduo, não regressão: o escritor
já digere o hostname desde aquele commit.

**Não deletar às cegas.** `dc9ad45` tratou o irmão dela renomeando a partição e
reescrevendo os 161 registros em um passo, porque o nome do arquivo é chave de partição
do journal. O mesmo tratamento vale aqui.

**Ação:** limpar no molde de `dc9ad45` (renomear + reescrever `machine`/`holder`) antes
que um `git add -A` a rastreie. Enquanto isso ela NÃO entra em commit nenhum.

## 3. `tests/cairn-command-surfaces.bats` teste 54 vermelho — `export-identity` sem rota (onda 5)

`every check id the doctor reports has an entry in the routing table` reprova com
`check id(s) with no entry in cairn/docs/commands/doctor.md: export-identity`.

**Mesma origem do item 1, e não é desta fase.** O check `export-identity` nasceu em
`19f00ee` (2026-08-11 13:57), que chegou ao branch pelo merge `8b5714f`; a tabela de
roteamento em `cairn/docs/commands/doctor.md` não ganhou a linha correspondente
(`grep -c export-identity` = 0). Nenhuma onda da 36 tocou nem o doctor nem `cairn/docs/`.

**Ação:** acrescentar a entrada de roteamento de `export-identity` em
`cairn/docs/commands/doctor.md` — o teste diz o que falta e onde.
