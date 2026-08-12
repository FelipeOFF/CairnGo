---
phase: 37-troca-de-plugin
plan: 03
subsystem: docs, bookkeeping
tags: [migracao, readme, pin, precedente]
requires: [37-01, 37-02]
provides: [capítulo v1.6 da migração, garantia asserida, pin do doctor atualizado]
affects: [phase-38 paridade]
tech_stack_added: []
patterns: [precedente preservado, garantia como asserção]
key_files_created: []
key_files_modified:
  - cairn/docs/gsd-core-migration.md
  - README.md
  - cairn/README.md
  - tests/cairn-gsd.bats
  - tests/cairn-standalone.bats
decisions: [D-06 janelas herdadas]
requirements: [PLUG-05]
status: complete
completed: 2026-08-12
---

# Phase 37 Plan 03: A migração escrita e a escrituração Summary

A troca aconteceu nos planos 01 e 02. Este escreve o que aconteceu para quem
chega depois com um repo já instalado, e transforma a garantia repetida do
research — *"nada em `.planning/` nem `.beads/` muda"* — em teste, porque
garantia sem oráculo é frase.

## O capítulo v1.6, e o precedente que ele não reescreve

`cairn/docs/gsd-core-migration.md` ganhou o capítulo da troca. A decisão que
governa a forma: **o capítulo v1.4 não foi reescrito.** Ele é o precedente que
esta remoção segue, e reescrever um precedente é apagá-lo. O título do
documento passou a anunciar as duas migrações, com um parágrafo dizendo
explicitamente que tudo acima da divisa descreve a v1.4 e fica como está.

O capítulo cobre, na forma que o v1.4 estabeleceu:

- **o que mudou** — o runtime GSD passou a viver dentro do plugin; `gsd-core`
  saiu do marketplace e das `dependencies`;
- **preciso fazer algo?** — instalação nova, não; existente, **sim**, e é a
  metade fácil de pular: remover a entrada do marketplace não desinstala nada,
  então o `gsd-core` continua no disco respondendo `/gsd:*` com workflows que
  não sabem nada de bd, ao lado de um `/cairn:*` que sabe;
- **como migrar** — `/cairn:doctor` acusa, um `uninstall`, `/reload-plugins`,
  e a limpeza do resíduo que o doctor nomeia;
- **o precedente** — a entrada `gsd` 4.x saiu na v1.4 pelo mesmo caminho,
  citado por nome e por versão, com a única diferença que importa dita em voz
  alta: em v1.4 a resposta era instalar *outro* plugin; agora não há o que
  instalar;
- **a garantia** — nada em `.planning/` nem `.beads/` muda, agora com o ponteiro
  para o teste que a prova.

A seção do defeito de manifesto do gsd-core upstream **ficou**, com uma nota de
que deixou de se aplicar a quem desinstalou: ela documenta um defeito real e o
raciocínio que produziu o reparo, e `repair-manifest` continua existindo para
quem roda gsd-core por conta própria.

## A garantia virou asserção

`tests/cairn-standalone.bats`, teste 8: comparado com a base da fase, nenhum
arquivo sob `.planning/` fora de `.planning/phases/37-troca-de-plugin/` mudou, e
nenhum sob `.beads/` — com `.beads/issues.jsonl` como **única** exceção,
nomeada e não por padrão largo, porque é o export passivo do tracker e se move
quando uma issue da fase abre ou fecha.

A base é derivada, nunca digitada: o pai do primeiro commit que tocou o
diretório desta fase. A primeira versão usava `git merge-base` contra o branch
do milestone e reprovava listando 12 arquivos da **fase 36** — trabalho
legítimo, de outra fase. Um oráculo que reprova por trabalho alheio não mede o
que promete.

## Os READMEs

`README.md` e `cairn/README.md` pararam de prometer a dependência:

- a tabela de plugins publica **um** plugin, com um parágrafo explicando por que
  (dois plugins versionam independentemente, e a máquina acaba com um `/gsd:*`
  velho respondendo do cache ao lado de um `/cairn:*` novo);
- a linha da **GSD capability** virou a linha do **runtime vendorizado**, com a
  nota de que o ship gate nunca dependeu de host de plugin — ele roda do
  `pre-push` do próprio git;
- o parágrafo de abertura passou a dizer `/cairn:*` onde dizia `/gsd:*`.

## O pin do doctor

`tests/cairn-gsd.bats`, teste `CHECK-04`: atualizado para o blob novo
(`1249752b…`, 4112 linhas, de `94e26233…`, 4042) **com a razão escrita**, no
molde que o próprio teste exige. O texto anterior nomeava a fase 37 como dona
desta atualização; a entrada nova registra o que mudou — a inversão do check 10,
a ordem de decisão, o seam `CAIRN_VENDORED_GSD` — e aponta para as 9 asserções
que provam a inversão nas duas direções. As entradas de 2026-08-11 (checks 22 e
24) continuam lá: o registro acumula, não substitui.

## Números

| Suíte | Resultado |
|---|---|
| `tests/cairn-standalone.bats` | 8/8 verdes |
| `tests/cairn-wrap.bats` | verde |
| `tests/cairn-init.bats` | verde |
| `tests/cairn-command-surfaces.bats` | verde |
| `tests/cairn-doctor-lineage.bats` | 9/9 verdes |
| `tests/cairn-release.bats` | verde |
| `tests/cairn-doctor.bats` | 125/125 verdes, exit 0 |
| `tests/cairn-gsd.bats` | 90 testes, verde com o pin novo |

## Desvios do plano

**Nenhuma das duas janelas herdadas da fase 36 precisava do conserto que o
plano previa.** A Task 3 previa acrescentar a linha de roteamento de
`export-identity` em `cairn/docs/commands/doctor.md`, que a fase 36 documentou
como dívida com o teste 54 vermelho. Medido ao início desta fase:
`grep -c export-identity cairn/docs/commands/doctor.md` → **1**, e
`tests/cairn-command-surfaces.bats` sai **0**. A dívida já estava paga, e o
registro ficou em `deferred-items.md` para que ninguém "conserte" o que está de
pé. Só a metade do pin do doctor era real.

## Premissas que a medição contradisse

1. **"A fase 36 deixou duas janelas quebradas para a 37."** Deixou uma. A outra
   já tinha sido fechada entre o fim da 36 e o começo desta fase — e a única
   maneira de saber isso era rodar, não ler o `deferred-items.md` herdado.
2. **"A base de comparação de um branch de fase é o merge-base com o branch do
   milestone."** Não é, quando o branch nasceu da ponta da fase anterior: o
   merge-base engloba a fase anterior inteira. A base honesta é o primeiro
   commit da própria fase.

## Commits

| Hash | Mensagem |
|---|---|
| `f6918d7` | docs(37-03): o capítulo v1.6 da migração, os READMEs e o pin do doctor |

## Self-Check: PASSED
