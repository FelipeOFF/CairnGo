---
phase: 25-measured-cleanup
plan: "09"
beads: [CairnGo-3w9]
status: complete
---

# Fase 25 Plano 09 — resumo

## O que mudou

`/cairn:land` e `/cairn:review` existem: prompt em `cairn/commands/`, página em
`cairn/docs/commands/`, linha na referência e no bloco derivado. O bloco passou
de **38 comandos / 25 próprios** para **40 / 27**, regenerado pelo
`cairn-wrap.sh docs` — nunca à mão.

E a guarda que fecha a classe do defeito: todo `cairn-*.py` ou tem comando, ou
tem uma razão escrita.

## O defeito, e a asserção que o fecha

| Defeito | Medição | Teste |
|---|---|---|
| Dois scripts da fase 30 sem porta nenhuma | `cairn/commands/{land,review}.md` e `cairn/docs/commands/{land,review}.md` não existiam; descoberto ao escrever uma string de roteamento para `/cairn:land`, que não existe | `the two phase-30 scripts have both doors` |
| A página derivada não tinha como notar a ausência | um script sem wrapper não é listado **por definição** | mesmo teste (os dois agora aparecem em `.commands`) + `the command reference lists every command, and its block is current` |
| Nada obrigava a decisão para o próximo script | — | `every cairn script is reachable by command, or its absence is written down` |

## Este plano é a prova ao vivo do plano 08

O teste do 08 prova por acréscimo com uma sonda em diretório temporário. Aqui o
acréscimo é real: os dois comandos entraram no mapa do `/cairn:help` **sem uma
linha de prosa editada nele** — o `help.md` não menciona `land` nem `review`
em lugar nenhum, e a asserção de "não transcreva" continua verde com 40
comandos instalados.

## As decisões, e o que foi recusado

- **Verbos `/cairn:land` e `/cairn:review`.** A convenção da casa é comando com
  o nome do script (`doctor`, `status`, `migrate`, `reconcile`, `config`).
  `/cairn:pr` foi considerado e recusado: divergir do nome do script recria a
  mesma classe de defeito ao contrário — uma superfície nomeando algo que não
  casa com o que se invoca. Medido que `/gsd:review` **não** está entre os
  treze wrappers, então `/cairn:review` não colide; o risco de ser lido como
  revisão de código é fechado na primeira linha das duas páginas
  (*pull-request state, not code review*).
- **Grupo `view` para os dois** — os dois respondem "onde este trabalho está".
- **Treze razões escritas** para os scripts sem comando, quase todas da forma
  "invocado por": `bookkeep`, `capability`, `gate`, `jira`, `journal`, `lease`,
  `map`, `parallel`, `relabel`, `release`, `test`, `trend`, `wrap`. A razão é a
  carga útil do registro: entrada sem frase não é entrada.

## A quebra guardada

| Quebra | Onde | Asserções vermelhas |
|---|---|---|
| Remover `cairn/commands/land.md` — o estado exato em que a fase 30 terminou | `cairn/commands/land.md`, restaurado de `cp` | `the two phase-30 scripts have both doors`; `every cairn script is reachable by command…` → `no /cairn: command and no written reason: land`; `the command reference lists every command, and its block is current` |

Três asserções de uma vez, que é o ponto: a ausência de porta agora aparece em
três superfícies em vez de nenhuma.

## Suítes rodadas

| Suíte | Resultado |
|---|---|
| `tests/cairn-command-surfaces.bats` (12) | verde |
| `tests/cairn-wrap.bats` (24) | verde — inclusive o 22, que reprovaria `undocumented` ou `missing_pages` diferente de zero |

## Premissas que a medição contradisse

1. **"Ganhar wrapper" seriam dois arquivos.** São quatro, mais uma regeneração:
   sem página em `cairn/docs/commands/`, o `docs --check` reporta
   `missing_page`; sem linha na seção `## View`, reporta `undocumented`; e o
   bloco derivado fica `stale` (exit 3) até ser regenerado. O teste 22 da suíte
   do wrap reprova as três coisas.
2. **A issue chama os dois de "wrapper `/cairn:*`".** No vocabulário que a
   fase 26 fixou, *wrapper* é o comando que delega a um `/gsd:*` e carrega
   `wraps:` no frontmatter — treze deles. `land` e `review` são comandos
   **próprios** do cairn, e é assim que o `cairn-wrap.py list` os classifica:
   `own`, não `wrappers`. A palavra na issue é imprecisa; o que ela pede é uma
   porta.
