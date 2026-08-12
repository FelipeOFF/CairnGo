---
phase: 36-workflows-steps-e-agentes-falam-bd
plan: 03
subsystem: oraculo-de-estado
tags: [adapt-02, metrica-da-fase, tres-familias, isencoes-dois-sentidos, fast, debug]
requires:
  - onda 2 fechada (o binário emite `null`, não lista vazia)
provides:
  - o oráculo que decide, por máquina, o que conta como "zero leitura de .planning/ como fonte de estado"
  - a tabela de isenções conferida NOS DOIS SENTIDOS
  - fast.md convertido e debug.md medido em zero
affects: [fase-36-ondas-4-a-7]
key-files:
  created: []
  modified:
    - tests/cairn-prompt-state.bats
    - cairn/gsd/gsd-core/workflows/fast.md
    - cairn/gsd-adaptations.json
    - .planning/phases/36-workflows-steps-e-agentes-falam-bd/36-PATTERNS.md
status: complete
---

# Phase 36 Plan 03: o oráculo de estado Summary

> **Nota de procedência.** Este SUMMARY foi escrito depois das ondas 4 a 7, a
> partir dos oito commits da onda e do disco. A sessão que executou a onda 3
> morreu antes de escrevê-lo e eu declarei que o escreveria e não escrevi; o
> executor da onda 4 teve que reconstruí-lo dos commits para poder trabalhar,
> e foi ele quem reportou a falta. O conteúdo abaixo é medido, mas a falha de
> processo fica registrada em vez de apagada.

## O que a onda entrega

A **métrica da fase inteira**, e é por isso que ela vem antes dos seis
workflows caros. O oráculo não é um grep por nome de arquivo, e a razão é
medida: **12 linhas referenciam estado sem citar o nome do arquivo** e
escapariam, declarando verde uma cobertura que não existe.

Três famílias:

| família | o que morde |
|---|---|
| A | leitura mecânica (`cat`/`grep`/`head`/`tail`/`wc`/`test -f`, mais a `@`-referência) |
| B | as quatro grafias de estado por variável, contadas por padrão e conferidas contra a tabela |
| C | prosa imperativa **e a forma passiva** de critério de sucesso |

`state_exists` fica **fora** da família B por decisão escrita, com caso de
teste provando a exclusão: é campo do bundle de init, fato que já vem do
binário desde a fase 34. Pô-lo na família obrigaria quatro isenções
permanentes para descrever comportamento correto, e isenção que nunca morre
treina a ignorar a tabela.

A tabela de isenções é conferida **nos dois sentidos**: isenção cuja contagem
não bate mais reprova igual a sítio não convertido. Isenção morta é mentira
do mesmo tamanho.

Leitura de documento não é mordida — caso dedicado com as cinco formas
medidas.

## Os dois primeiros clientes

**`fast.md`** — o caso mais claro do corpus: um `grep` no markdown (`:77`)
decidia se o binário era chamado, com a chamada na linha seguinte. O bloco de
detecção some; a falha do verbo chega nomeada, com a razão e o comando que
registra o fato. Três resíduos nomeados no RED antes do GREEN. A prova é ponta
a ponta real: o bloco bash inteiro extraído do próprio arquivo, rodado num
repo de fixture com `bd`, exit 0 e o fato consultável por label.

**`debug.md`** — resultado medido: **zero conversões**. As 13 menções a
`.planning/` são todas caminho de documento de sessão (`.planning/debug/*.md`),
e documento não é fato. O zero vai **publicado**: o roadmap orçou a fase por
contagem de `.planning/` por workflow, `debug` é a segunda maior, e um zero
omitido deixaria a próxima fase pensando que sobrou trabalho.

## O que a medição derrubou — e o mais caro da fase até aqui

**`36-PATTERNS.md §5b` listava 11 linhas dizendo 12.** Faltava
`execute-phase.md:90`. Corrigido na origem, com a divisão medida escrita: 8
linhas nas quatro grafias + 4 de `state_exists`.

Esse é o erro caro da fase, e não pela linha: era erro **na régua**, não na
peça. Se tivesse passado, as ondas 4 a 7 mediriam cobertura contra uma lista
curta e declarariam verde uma cobertura que não existe — a tese da fase 23
reaparecendo dentro da fase que deveria estar imune a ela.

Outras três, todas conferidas contra o disco em vez da memória:

- a citação de `execute-phase.md:90` no plano tinha o trecho vizinho errado
  (`state_exists, commit_docs, sub_repos`; o real é `state_exists,
  roadmap_exists, phase_req_ids` — `commit_docs` está na mesma linha, doze
  campos antes);
- o `PATTERNS` avisava que todo `real_cache_or_skip` skipa e que um verde
  local não provava nada. **Medido: o cache está neste worktree**, nenhum
  teste de `cairn-vendoring.bats` skipa, e os dois sentidos do registro
  rodaram de fato;
- a âncora do molde citada pelo plano (`:422-448`, `:465-474`) envelheceu na
  onda 1; no arquivo de hoje são `:466-492` e `:509-518`.

## Controle negativo

Forjado e permanente, não manual: uma cópia com um sítio de cada família,
mordido e nomeado com três frases distintas. Vira teste em vez de depender de
alguém lembrar de repetir a quebra.

## Verificação

`cairn-prompt-state.bats` 7 → 10 testes. `cairn-vendoring.bats` 26, sem skip.
Suíte completa não rodada na onda (a regra da CI só passou a valer depois).

## Aberto

`ADAPT-02: CairnGo-0yzd` reclamada e **não fechada** — compartilhada com os
planos 01 e 07.
