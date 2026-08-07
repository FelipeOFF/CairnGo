---
phase: 27-disagreement-trend-across-cycles
plan: "01"
subsystem: cli
tags: [trend, milestones, verification, not-applicable, frontmatter, stdlib, bats]

requires:
  - phase: 23-not-applicable-as-a-check-state
    provides: "o quarto estado com escopo nomeado — sem ele o vão do miolo somaria com o veredito"
provides:
  - "cairn-trend.py / cairn-trend.sh: os ciclos descobertos do disco, sem lista de versões em código"
  - "read_frontmatter(): parser mínimo de frontmatter com contagem de itens de lista, stdlib pura"
  - "quatro estados de ciclo: comparable, e not-applicable com escopo no-frontmatter / no-verdict / no-input"
  - "modelo com valores já formatados (coverage, status_line), para que o render não compute nada"
  - "tests/cairn-trend.bats: 16 testes, com fixture de ciclos local ao arquivo"
affects: [trend-axes, trend-ambiguity]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "estado de ciclo com escopo nomeado, herdado literal do vocabulário do cairn-doctor (⊘, `scope` só quando not-applicable)"
    - "teste-âncora em três direções, porque a contaminação de denominador tem três formas e uma asserção só é cega a duas"
    - "expectativa recomputada do disco dentro do teste, jamais literal — nem chave de milestone, nem contagem"
    - "render sem cálculo: toda string formatada nasce no modelo, o que torna a promessa do TREND-02 verificável depois"

key-files:
  created:
    - cairn/scripts/cairn-trend.py
    - cairn/scripts/cairn-trend.sh
    - tests/cairn-trend.bats
  modified: []

key-decisions:
  - "A varredura de milestones é REIMPLEMENTADA, não importada: o 27-CONTEXT.md a atribui ao cairn-bookkeep.py e ela está no cairn-doctor.py:649 — medido, o bookkeep não menciona `milestones` uma vez sequer. Como o doctor está fora do escopo e a casa não tem lib compartilhada, copia-se a FORMA (a âncora do vN-ROADMAP.md), nunca o módulo"
  - "`no-frontmatter` é escopo NOVO e não reusa `no-input`: dizer que não há insumo apagaria o fato de que o v1.2 e o v1.3 têm três arquivos de verificação cada, escritos e commitados — o que falta é o formato"
  - "`no-verdict` existe para uma forma que o disco não tem hoje (frontmatter sem `status`), porque o parser não pode ser obrigado a escolher entre duas respostas erradas"
  - "O denominador da cobertura são fases COM veredito, nunca fases do ciclo: contar fase sem verificação como não-aprovada inventaria reprovação, o irmão gêmeo do que o TREND-02 proíbe"
  - "O ciclo aberto leva ressalva própria — a cobertura dele conta fases que ainda não começaram e não se compara com a de um ciclo fechado"

status: complete
---

# Phase 27 Plan 01: Os ciclos e o quarto estado Summary

Os cinco ciclos deste repositório saem do disco com um estado cada, e os dois vãos do
miolo aparecem como `not-applicable / no-frontmatter` com o motivo escrito, em vez de
virarem zero numa coluna.

## O que foi construído

`cairn-trend.py` e o par `.sh`. Ele descobre ciclos por duas âncoras já estabelecidas
nesta casa — o `vN-ROADMAP.md` sob `.planning/milestones/` para os arquivados, o
marcador `🚧` do `ROADMAP.md` para o corrente — lê o frontmatter de todo
`*VERIFICATION.md` sob as fases de cada ciclo, e classifica cada ciclo em exatamente
um estado.

Medido contra a árvore real:

```
· v1.1  veredito em 6/6 fases    gaps_found 2 · passed 4
⊘ v1.2  not-applicable / no-frontmatter
⊘ v1.3  not-applicable / no-frontmatter
· v1.4  veredito em 6/7 fases    gaps_found 2 · human_needed 1 · passed 3
· v1.5  veredito em 7/10 fases   gaps_found 3 · human_needed 1 · passed 3
```

## A série do 27-CONTEXT.md, reconferida

Todas as contagens do D-01 bateram, uma a uma, contra a árvore de hoje: v1.1 com
`passed 4 · gaps_found 2` em seis arquivos com frontmatter; v1.2 e v1.3 com três
arquivos de verificação cada e zero frontmatter; v1.4 com `passed 3 · gaps_found 2 ·
human_needed 1`; v1.5 com `passed 3 · gaps_found 3 · human_needed 1` em sete. Nada
precisou ser corrigido na série.

## Correções ao contexto

**1. A varredura de milestones não está onde o contexto diz.** O `<code_context>`
registra que `cairn-bookkeep.py` "já lê `.planning/milestones/` ... (`archived_milestones()`,
entregue na fase 23)". Medido: `archived_milestones()` vive em `cairn-doctor.py:649`, e
`cairn-bookkeep.py` não contém a palavra `milestones` nenhuma vez (`grep -c` = 0). A
consequência é de escopo: o doctor está explicitamente fora do escopo desta fase, e a
casa não tem lib compartilhada — o asset é reusável como **forma**, não por import.
Copiei a âncora (`ARCHIVED_ROADMAP`, o roadmap arquivado como evidência) e a razão dela.

**2. A cobertura do v1.4 não é 6 de 6.** O `19-ship-v1-4` tem diretório de fase e não
tem `VERIFICATION.md` — o ciclo fechou com uma fase sem veredito. Isso não aparece na
série do contexto porque a série conta arquivos, não fases; a cobertura é um dado
separado e o comando a mostra ao lado.

## Deviations from Plan

Uma, e ela nasceu de uma medição durante a execução.

**[Rule 1 - Bug] O teste-âncora era cego à contaminação que ele existia para pegar**

- **Achado durante:** Task 1, ao aplicar a quebra que força `classify()` a devolver
  sempre `comparable`.
- **Problema:** a âncora somava `with_verdict` dos ciclos comparáveis. Um ciclo sem
  frontmatter contribui **zero** vereditos, então a soma não se move quando ele invade
  a série — o teste ficava verde com o defeito instalado. A contaminação de denominador
  tem três formas (um ponto a mais na série, vereditos a mais, arquivos contados no
  lugar de vereditos) e a versão original enxergava só uma delas, a menos provável.
- **Correção:** três asserções no lugar de uma, com a medição registrada em comentário
  no próprio teste.
- **Verificado:** com a quebra reaplicada, o teste 5 fica vermelho junto com os testes
  2, 3 e 4; restaurado da cópia, 16/16 verde.
- **Commit:** 6617418

## Verificação

`bash cairn/scripts/cairn-test.sh --jobs 4 tests/cairn-trend.bats` — 16/16, lido do log
inteiro com a marca de fim conferida.

Quatro quebras aplicadas ao fonte e medidas, com restauro por cópia (`cp`), nunca por
`git checkout --`:

| Quebra | Vermelho |
|---|---|
| `no-frontmatter` colapsa em `no-input` | teste 2 |
| `classify()` devolve sempre `comparable` | testes 2, 3, 4, 5 |
| o `not-applicable` renderiza a cobertura | teste 9 |
| a ressalva do ciclo aberto sai sempre | teste 10 |

## Self-Check: PASSED

- `cairn/scripts/cairn-trend.py` — existe
- `cairn/scripts/cairn-trend.sh` — existe
- `tests/cairn-trend.bats` — existe
- commits `6617418`, `3dcac20` — no histórico
