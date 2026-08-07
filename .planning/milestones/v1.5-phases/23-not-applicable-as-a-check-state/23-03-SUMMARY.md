---
phase: 23-not-applicable-as-a-check-state
plan: "03"
subsystem: infra
tags: [python, bats, cli, stdlib, doctor, false-green, empty-roadmap]
requires:
  - "23-01: o status not-applicable, o campo scope, a contagem por balde"
  - "23-02: as guardas de aplicabilidade já convertidas"
provides:
  - "req-issue, maps-fresh, orphans, frontmatter-ids e superseded-released deixam de aprovar o vazio"
  - "check_orphans com os dois eixos separados no código"
  - "helper make_roadmap_without_phases"
  - "o veredito escrito das nove checagens do idioma da contagem zero"
affects:
  - "cairn/scripts/cairn-doctor.py"
  - "cairn/docs/commands/doctor.md"
  - "tests/cairn-doctor.bats"
  - "tests/helpers.bash"
tech-stack:
  added: []
  patterns:
    - "eixos independentes separados no código para que a promoção de um não silencie o outro"
key-files:
  created: []
  modified:
    - "cairn/scripts/cairn-doctor.py"
    - "cairn/docs/commands/doctor.md"
    - "tests/cairn-doctor.bats"
    - "tests/helpers.bash"
decisions:
  - "maps-fresh lê .planning/phases/ em disco, não o ROADMAP — correção medida à T-13"
  - "frontmatter-ids com inventário vazio é no-input, não ok — mesmo eixo do superseded-released"
  - "o clone raso do external-ref permanece warn, com a recusa registrada no código"
status: complete
---

# Phase 23 Plan 03: O terceiro idioma, decidido checagem a checagem — Summary

Um repositório cujo ROADMAP não lista fase nenhuma deixou de produzir board
verde: `req-issue` e `orphans` passaram a dizer que não compararam nada, o
rodapé lê `INCOMPLETE`, e o código de saída continua 0. As nove checagens do
idioma da contagem zero têm agora veredito escrito — cinco convertidas, quatro
mantidas com a razão ao lado.

## A linha de base do cenário, re-medida

Repositório temporário cabeado (`bd init`, `.planning/` com `ROADMAP.md` sem
nenhuma fase), medido **antes** das edições deste plano — isto é, já com os
planos 01 e 02 aplicados:

```
[cairn-doctor] FAIL — 13 ok, 4 not-applicable, 0 warning(s), 1 failure(s)
```

Sete das treze aprovações eram vazias: `req-issue` (*"no '**Requirements**:'
lists found"*), `frontmatter-ids` (*"0 plan bead id(s) verified"*),
`maps-fresh` (*"0 phase map(s) current"*), `superseded-released` (*"0
superseded plan(s)"*), `phase-complete-open`, `orphans` (*"0 issue(s), no
orphans"*), `label-pairs`.

A falha é o `gsd-capability` num diretório temporário que não é uma instalação
do cairn — a D-01 do CONTEXT já registrou que não é achado desta fase.

Isto substitui tanto o número do ROADMAP (`16 ok, 0 avisos, 0 falhas`,
2026-08-03, dezesseis checagens) quanto o da D-01 (`16 ok, 1 warning, 1
failure`).

## A tabela final dos nove vereditos

| checagem | condição | veredito | divergiu de T-13? |
|---|---|---|---|
| `req-issue` | ROADMAP sem nenhuma linha `**Requirements**:` | `not-applicable` / `no-input` | não |
| `maps-fresh` | **nenhum diretório de fase com issue ou mapa** | `not-applicable` / `no-input` | **sim, no insumo** |
| `orphans` | roadmap vazio **e** zero achados no eixo sem-rótulo | `not-applicable` / `no-input` | não |
| `orphans` | roadmap vazio **com** achados no eixo sem-rótulo | `warn` | não |
| `frontmatter-ids` | inventário de planos vazio | `not-applicable` / `no-input` | **sim, no veredito** |
| `frontmatter-ids` | planos presentes, nenhum com id de bead | `not-applicable` / `no-input` | não |
| `superseded-released` | inventário de planos vazio | `not-applicable` / `no-input` | não |
| `superseded-released` | planos presentes, nenhum superseded | `ok` | não |
| `phase-complete-open` | nenhuma fase marcada completa | `ok` | não |
| `label-pairs` | tracker sem issue / nenhuma sem par | `ok` | não |
| `external-ref` | zero issues fechadas | `ok` | não |
| `external-ref` | clone raso | `warn` (T-15) | não |
| `lease-stale` | nenhuma lease registrada | `ok` | não |

As quatro mantidas carregam, ao lado do retorno, um comentário que começa com
*"Phase 23 evaluated and KEPT `ok`"* e diz **por quê** pela régua de T-12. Sem
ele, daqui a seis meses a decisão é indistinguível de omissão — que é
exatamente o que o CONTEXT proíbe.

## Duas divergências medidas em relação à T-13

### 1. O insumo do `maps-fresh` não é o ROADMAP

**T-13 diz:** `maps-fresh | ROADMAP sem fase nenhuma | not-applicable /
no-input`.

**Medido:** `check_maps_fresh()` itera `phase_dirs(planning_dir)`, que lê
`.planning/phases/` **em disco**. A função nunca toca `roadmap_phases`. Um
ROADMAP vazio **não** silencia essa checagem.

**Efeito prático, e por que importa:** um teste escrito contra a premissa da
T-13 teria montado um roadmap vazio, visto `maps-fresh` continuar rodando, e
— na leitura mais provável — o executor teria "consertado" a checagem para ler
o roadmap. Isso quebraria a checagem: os mapas são gerados por diretório de
fase, não por linha de roadmap.

**O que ficou:** a conversão é sobre `checked == 0`, e os dois lados estão
provados por teste:

- roadmap vazio, diretórios de fase presentes → `maps-fresh` reporta **`warn`
  exato** (os mapas ficaram stale no instante em que o roadmap mudou debaixo
  deles). A checagem que ainda tem insumo continua comparando.
- diretórios de fase vazios → `not-applicable` / `no-input`.

O helper de fixture carrega a nota medida, para o próximo leitor não repetir a
confusão.

### 2. `frontmatter-ids` com inventário vazio é lacuna, não sucesso

**T-13 diz:** `frontmatter-ids | inventário de planos vazio | ok | vacuamente
verdadeiro`, e na linha seguinte `superseded-released | inventário de planos
vazio | not-applicable / no-input | o eixo é o inventário de planos`.

**O problema:** as duas checagens leem **o mesmo** `plans` de
`plan_inventory()`. Dar vereditos opostos ao mesmo insumo é decisão por
omissão, que é o que o CONTEXT proíbe nesta escolha.

**Decisão:** as duas viram `not-applicable` / `no-input` com inventário vazio.
Pela régua de T-12: com nenhum PLAN.md em disco, nenhuma das duas garantias
foi verificada neste repositório, e escrever um plano é a ação concreta. É
também o que o critério 2 do ROADMAP pede — um projeto onde nada foi conferido
não pode ler como saudável.

Isto **não** contradiz a T-04: aquele travão é sobre ausências de **escopo**
(as manifests do cairn num repo que não é o cairn), que ficam permanentemente
`out-of-scope` e não tornam o relatório incompleto. Um projeto sem plano nenhum
é lacuna transitória, some ao primeiro plano escrito, e é exatamente o que o
`INCOMPLETE` existe para dizer sem bloquear.

## O `orphans`, e a armadilha que o plano nomeou

`check_orphans()` foi reescrita com os dois eixos separados por nome no código
(`unplaced` e `unlabeled`), com um docstring que explica por que a checagem
**não** pode ser recusada inteira. O veredito com roadmap vazio depende do eixo
2, e nos dois casos o `detail` diz que a comparação com o roadmap não pôde
acontecer — inclusive quando há aviso, para que a informação não se perca
debaixo do achado.

Gate mecânico do plano, verde: `check_orphans` contém `NOT_APPLICABLE` e tem
**3** `return {` (o plano exigia ≥ 2).

## Testes: cada um com a quebra que o deixa vermelho

| teste | quebra nomeada |
|---|---|
| `empty roadmap: the checks that compared nothing say so…` | qualquer uma das nomeadas voltando a aprovar o vazio; asserção por id, no valor exato |
| `orphans with an empty roadmap: the axis that still works keeps reporting` | recusar a checagem inteira com roadmap vazio — a versão ingênua, que engole todo achado do eixo 2 |
| `maps-fresh: no phase directory at all is not-applicable/no-input…` | pendurar a promoção no roadmap: nunca dispararia aqui, e dispararia no teste acima onde a checagem ainda tem trabalho |
| `plan-inventory checks: no PLAN.md at all…` | promover pelo eixo errado; era `ok` nas duas antes |
| `frontmatter-ids: plans present but none stamped…` | ler a ausência de estampa como verdade vacuosa — é a lacuna que o cairn existe para não ter |
| `phase 23 decided NOT to promote these four: they stay exactly ok` | promover por reflexo, numa passada futura, uma checagem que esta fase decidiu deixar quieta |

O teste do clone raso já existia e já afirmava `warn` exato; T-15 o mantém e
só o código ganhou o registro da recusa.

## Verificação executada

Mesmo método do plano 02 (ver lá o porquê). Run serial dirigido — filtro
`plan-inventory checks|frontmatter-ids|superseded-released|phase 23 decided NOT|empty roadmap|maps-fresh|orphans`:

```
1..12
ok:     12
not ok: 0        EXIT=0
```

**12 anunciados, 12 executados**, `grep -c` sobre `/tmp/t03.log` inteiro.

Gate: `[.checks[]|select(.status=="not-applicable" and (.scope|not))]|length == 0` — verde.

### O doctor deste repositório saiu FAIL, e não é desta fase

Depois deste plano, `cairn-doctor.sh` neste repositório reporta
`FAIL — 13 ok, 1 not-applicable, 2 warning(s), 2 failure(s)`. As duas falhas
são do meu trabalho **em voo**, não do código:

1. `phase-corroboration` — *"disk reports phase 23 executed, bd reports its
   issues in_progress"*. Consequência do `bd update CairnGo-6yj --claim`
   somado aos SUMMARY em disco. Fecha quando os beads da fase fecharem.
2. `req-ledger` — *"23-02-SUMMARY.md is on disk but the plan's ROADMAP checkbox
   still reads '[ ]'"*. Consequência direta da instrução de execução: marcar
   esse checkbox é `cairn-bookkeep.sh close 23 --apply`, que é do dono do
   repositório. **Não corrigi**, deliberadamente.

O `maps-fresh` em `warn` tem a mesma origem (o claim deixou o
`23-BEADS-MAP.md` stale). E os números de fundo andaram durante a execução —
`41 active requirement(s)` onde eram 40, `5 phase map(s)` onde eram 4 —
porque outras fases estão escrevendo em `.planning/` e commitando em `main`
em paralelo (`c315501 docs(28)` caiu entre dois commits meus).

## Deviations from Plan

### 1. [Rule 1 — premissa do plano corrigida] O insumo do `maps-fresh`

Descrito acima. Divergência registrada, testes provando os dois lados.

### 2. [Rule 1 — premissa do plano corrigida] `frontmatter-ids` com inventário vazio

Descrito acima. O plano convidava explicitamente a divergir com o motivo
escrito.

### 3. [Rule 1 — erro meu de escrituração, corrigido] A Task 2 do plano 01 não teve commit próprio

- **Encontrado durante:** conferência de `git status` no fim deste plano.
- **Achado:** as edições da Task 2 do plano 01 (docstring do módulo, página do
  comando, cabeçalho do wrapper) foram escritas e verificadas, mas o commit
  atômico dela nunca aconteceu: a suíte completa que eu esperava para fechar a
  task foi morta pelo gerenciador de tarefas, e eu segui para o plano 02. As
  mudanças do `.py` e do `.md` viajaram nos commits `2b7f72e` e `3b61d94`; o
  `cairn-doctor.sh` ficou fora do índice.
- **Ação:** commit `77af539` fecha a lacuna e diz isso na mensagem, em vez de
  esconder. Nenhum conteúdo se perdeu.

## Threat Flags

Nenhuma superfície nova. Nenhum pacote instalado.

## Known Stubs

Nenhum.
