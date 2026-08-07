---
phase: 27-disagreement-trend-across-cycles
plan: "02"
subsystem: cli
tags: [trend, intersection, axes, score, sufficiency, contiguity, bats]

requires:
  - phase: 27-01
    provides: "os estados de ciclo e o modelo com valores já formatados"
provides:
  - "field_survey(): a interseção das chaves de frontmatter, computada por ciclo a cada execução"
  - "AXIS_SPECS: como agregar cada campo — nunca quais campos existem"
  - "score_survey(): a recusa do score com as unidades medidas, que cai sozinha se elas convergirem"
  - "direction_of(): direção e monotonicidade não-estrita, reportadas separadamente"
  - "build_series(): suficiência (três pontos), contiguidade, vãos, e exit 4"
affects: [trend-ambiguity]

actuals:
  tokens: 19000
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "interseção sobre CICLOS e não sobre arquivos: `gaps` está em dois dos seis arquivos do v1.1 e isso basta, porque o ciclo sabe registrar gaps"
    - "eixo recusado com o motivo derivado do disco, e a recusa se levanta sozinha quando o dado mudar"
    - "prova por acréscimo e por remoção no mesmo par: sem a remoção, um comando que sempre declarasse direção passaria no acréscimo"
    - "cinco quebras aplicadas ao fonte, uma a uma, cada uma com o vermelho atribuído ao seu teste"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-trend.py
    - tests/cairn-trend.bats

key-decisions:
  - "`score` é reprovado como eixo, e essa é a resposta medida à pergunta que o 27-CONTEXT.md deixou em aberto (quais eixos além de status). Ele está na interseção de PRESENÇA e não na de semântica: v1.1 conta must-haves, v1.5 conta critérios, e o v1.4 mistura os dois DENTRO do mesmo ciclo"
  - "AXIS_SPECS declara como agregar, não o que existe: um eixo só é computado se o campo estiver na interseção, e a saída nomeia os ciclos onde ele falta"
  - "`gap_density` existe além de `gaps` porque os ciclos têm tamanhos diferentes (6, 6 e 7 fases com veredito) e a contagem crua favorece o ciclo maior"
  - "monotonicidade é não-estrita: 2 → 2 → 4 é `rising` e monotônica, porque nenhum passo desce"
  - "exit 4 é o estado normal de um fixture pequeno, e os seis testes de classificação do 27-01 passaram a afirmá-lo pelo valor exato em vez de 0"

status: complete
---

# Phase 27 Plan 02: Os eixos e a suficiência Summary

A série sai com quatro eixos derivados da interseção computada do disco, e com um
quinto candidato **reprovado** — `score`, cuja unidade de denominador muda entre
ciclos e dentro do v1.4.

## O que foi construído

Contra a árvore real:

```
▸ série: 3 pontos comparáveis em 5 ciclos, 2 vãos — não contígua
▸ primeira aprovação   67% → 50% → 43%       desce
▸ lacunas registradas  2 → 2 → 4             sobe
▸ lacunas por fase     0.33 → 0.33 → 0.57    sobe
▸ overrides aplicados  0 → 0 → 0             constante
⊘ score não vira série: as unidades do denominador diferem entre os ciclos
  v1.1: must-haves verified · v1.4: must-haves verified, roadmap success
  criteria fully behaviorally verified, success criteria verified ·
  v1.5: critérios verificados
```

A interseção medida é `gaps, overrides_applied, phase, score, status, verified` — a
mesma que o D-02 do contexto registra.

## Correção ao contexto: o esquema oscilou, não derivou

O D-02 diz "O v1.1 grava `has_blocking_gaps` e `deferred`; o v1.4 grava
`behavior_unverified`…". Metade disso não se sustenta contra o disco, e o próprio
comando agora o reporta em `fields.missing_from`:

```
has_blocking_gaps    falta em v1.4, v1.5     (exclusivo do v1.1 — o contexto acerta)
deferred             falta em v1.4           (está no v1.1 E no v1.5)
behavior_unverified  falta em v1.1
```

`deferred` não é um campo do v1.1: é um campo que existiu no v1.1, **sumiu no v1.4 e
voltou no v1.5**. O esquema não derivou em linha reta, ele oscilou — o mesmo padrão do
frontmatter inteiro entre v1.1 e v1.4, um andar abaixo. Um campo que some e volta é
ainda menos série que um que aparece uma vez, e é mais um argumento para a interseção
mandar em vez de uma lista escrita em código.

## O achado maior: `score` parece um eixo e não é

O contexto listava `score` entre os candidatos. Medido, ele é o candidato que precisa
ser **recusado**, e a razão não é a presença — é a unidade:

| ciclo | unidades encontradas | denominadores |
|---|---|---|
| v1.1 | `must-haves verified` | 4, 9, 15, 19 |
| v1.4 | `must-haves verified`, `success criteria verified`, `roadmap success criteria fully behaviorally verified` | 4, 5, 14 |
| v1.5 | `critérios verificados` | 3, 4, 7 |

`15/15 must-haves` e `4/4 critérios` não medem a mesma coisa, e o v1.4 usa as duas
réguas dentro de si. Uma linha ligando esses pontos seria uma linha entre réguas
diferentes: medir certo e concluir errado, que é exatamente o defeito que esta fase
existe para nomear, um andar abaixo do lugar onde a fase o esperava.

A recusa é dado, não prosa: ela carrega as unidades que encontrou, e um fixture de
unidade única faz o eixo aparecer sozinho — o que é teste.

## Deviations from Plan

**[Rule 1 - Bug] Seis testes do 27-01 afirmavam exit 0 onde o correto passou a ser 4**

- **Achado durante:** Task 2, ao introduzir `EXIT_INSUFFICIENT`.
- **Problema:** os fixtures de classificação têm um ou dois ciclos comparáveis, ou
  nenhum, então a regra dos três pontos os coloca em `insufficient` — exit 4. Os
  testes afirmavam 0.
- **Correção:** valor exato 4 em cada um, com a razão em comentário no primeiro. Não
  afrouxei para `-ne 2` nem para "qualquer coisa menos erro": uma negação aceitaria o
  código errado e esconderia a regressão, que é a nota de estilo do topo do arquivo.
- **Commit:** 79cbd9d

## Verificação

`bash cairn/scripts/cairn-test.sh --jobs 4 tests/cairn-trend.bats` — 25/25, lido do
log inteiro.

Cinco quebras aplicadas ao fonte, uma a uma, com restauro por cópia:

| Quebra | Vermelho |
|---|---|
| interseção vira união | teste 16 |
| `score` agrega sempre | teste 18 |
| `MIN_SERIES_POINTS` de 3 para 2 | testes 6, 20, 21 |
| `contiguous` sempre verdadeiro | testes 22, 23 |
| `monotonic` sempre verdadeiro | teste 19 |

## Self-Check: PASSED

- `cairn/scripts/cairn-trend.py` — existe, com `field_survey`, `score_survey`,
  `build_series`
- `tests/cairn-trend.bats` — existe, 25 testes
- commit `79cbd9d` — no histórico
