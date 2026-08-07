---
phase: 23-not-applicable-as-a-check-state
plan: "01"
subsystem: infra
tags: [python, bats, cli, stdlib, doctor, false-green, status-vocabulary]
requires:
  - "cairn-doctor.py com dezoito checagens registradas (fase 29)"
  - "o ramo sem insumo de claims-stale entregue em warn pelo 29-07"
provides:
  - "o status not-applicable como valor de primeira classe, com o campo scope"
  - "contagem por balde em main(), derivada das chaves de SYMBOL"
  - "summary.counts, summary.failed, e summary.ok exigindo insumo"
  - "o veredito INCOMPLETE na linha final"
affects:
  - "cairn/scripts/cairn-doctor.py"
  - "cairn/scripts/cairn-doctor.sh"
  - "cairn/docs/commands/doctor.md"
  - "tests/cairn-doctor.bats"
tech-stack:
  added: []
  patterns:
    - "vocabulário fechado com fonte única (SYMBOL) e die() no desconhecido"
    - "contagem por balde, nunca por subtração"
key-files:
  created: []
  modified:
    - "cairn/scripts/cairn-doctor.py"
    - "cairn/scripts/cairn-doctor.sh"
    - "cairn/docs/commands/doctor.md"
    - "tests/cairn-doctor.bats"
decisions:
  - "not-applicable ganha duas famílias (out-of-scope, no-input) e só a segunda derruba summary.ok"
  - "o símbolo é ⊘ (U+2298), medido east_asian_width N"
  - "o exit code não se move — D-04 do CONTEXT, recusa por escrito"
status: complete
---

# Phase 23 Plan 01: A fatia vertical do estado não-aplicável — Summary

O doctor ganhou um quarto status (`not-applicable`, símbolo `⊘`) com duas famílias
de escopo, e o rodapé passou a **contar** os quatro estados em vez de derivar o
contador de sucesso por subtração — que era o lugar exato onde um quarto estado
nasceria já contado como verde.

## Linha de base, re-medida na hora

Medido em 2026-08-05 neste repositório, **antes da primeira edição**, com
`bash cairn/scripts/cairn-doctor.sh`:

```
[cairn-doctor] ok — 16 ok, 2 warning(s), 0 failure(s)     EXIT=0
```

Pelo `--json`: `{'ok': 16, 'warn': 2}` sobre 18 checagens, `.ok true`,
`.applicable true`. Os dois avisos eram `orphans` (61 itens) e `claims-stale`
(sem `active_phase`).

**Divergência registrada.** O prompt de execução anunciou
`15 ok, 3 warning(s), 0 failure(s)`. Não foi o que medi: foram **16 ok, 2
warnings**. O número que medi bate exatamente com o que o T-07 do plano registrou
para 2026-08-05. Como o exit era 0 nos dois casos, segui — mas o terceiro aviso
que o prompt viu não existia na minha medição, e a diferença provavelmente vem de
`maps-fresh`, que é sensível a claim de issue (ver abaixo).

**Deriva observada durante a execução, e que não é efeito do código.** Depois de
eu rodar `bd update CairnGo-6yj --claim`, o `maps-fresh` passou de `ok` para
`warn` com o item `phase 23: stale map 23-BEADS-MAP.md`. O claim mudou o status
da issue e o mapa gerado da fase 23 ficou desatualizado. Não é efeito de nenhuma
linha desta fase, e some quando os beads da fase fecharem e o mapa for
regenerado. Registro aqui porque, sem isso, a contagem depois da mudança
(`15 ok, 1 not-applicable, 2 warn`) pareceria creditar à fase um aviso que não é
dela.

## A varredura dos três idiomas (entregável D-02)

Feita por AST sobre todos os pontos de retorno de todas as checagens, com os
números de linha reconferidos na árvore de 2026-08-05 (`cairn-doctor.py` tinha
2575 linhas antes da edição). O CONTEXT dizia "três checagens"; são **nove** que
aprovam sem ter comparado nada, em **três** dialetos.

### Idioma 1 — prosa `"not applicable — …"` vestindo `ok` (4 sítios)

| checagem | linha do `return` | condição |
|---|---|---|
| `release-versions` | 1730 | sem `cairn/.claude-plugin/plugin.json` sob a raiz |
| `test-parallel` | 1814 | idem |
| `req-ledger` | 2068 | `.planning/` sem `REQUIREMENTS.md`/`ROADMAP.md`/`STATE.md` |
| `req-ledger` | 2100 | roadmap sem vista de cobertura |

Bate com a tabela T-08 do plano 02 (que citava as faixas 1729-1734, 1813-1818,
2067-2072, 2099-2105). **Plano 02 os converte.**

### Idioma 2 — contagem zero vestindo `ok` (9 caminhos, 8 checagens)

Todos com a forma `status: "…" if items else "ok"`, onde `items` vazio pode
significar tanto "varri e está tudo certo" quanto "não havia o que varrer":

| checagem | linha do `return` | o que a contagem zero significa |
|---|---|---|
| `req-issue` | 757 | ROADMAP sem nenhuma linha `**Requirements**:` |
| `frontmatter-ids` | 779 | inventário de planos vazio, ou nenhum plano com id |
| `maps-fresh` | 815 | ROADMAP sem fase nenhuma |
| `superseded-released` | 835 | inventário de planos vazio |
| `orphans` | 917 | roadmap vazio (eixo 1 desligado pelo `if roadmap_phases:`) |
| `phase-complete-open` | 895 | nenhuma fase marcada completa |
| `label-pairs` | 946 | tracker sem issue |
| `external-ref` | 1696 | zero issues fechadas |
| `lease-stale` | 1766 | nenhuma lease registrada |

**Planos 03 decide cada um, com a razão ao lado.**

### Idioma 3 — `"cannot check — …"` vestindo `warn` (3 sítios)

| checagem | linha do `return` | condição | destino |
|---|---|---|---|
| `claims-stale` | 1001 | `STATE.md` sem `active_phase` | **convertida neste plano** |
| `test-parallel` | 1847 | bats fora do PATH | plano 02 (`no-input`) |
| `external-ref` | 1580 | clone raso | plano 03 mantém `warn` (T-15) |

Não é "consertei as três do roadmap": são nove aprovações vazias em três
dialetos, e o inventário acima é o que permite fechar em um.

## O que mudou

### `cairn-doctor.py`

- **Constantes** junto ao bloco `EXIT_*`: `NOT_APPLICABLE`, `NA_OUT_OF_SCOPE`,
  `NA_NO_INPUT`, com a regra que separa as duas famílias escrita ao lado.
- **`SYMBOL`** passa a quatro entradas e vira a **fonte única do vocabulário**.
- **`main()`**: a linha `n_ok = len(checks) - n_fail - n_warn` foi substituída por
  contagem por balde, com os baldes derivados das chaves de `SYMBOL`. Um status
  fora do vocabulário chama `die()` com `EXIT_FAILED`, nomeando o id da checagem
  e o valor recebido.
- **`summary`**: ganha `counts` (os quatro números), `failed` (espelho exato do
  código de saída) e `ok` passa a exigir `n_fail == 0 and n_no_input == 0`. As
  chaves entram também na inicialização, para que as saídas antecipadas de
  repositório não-cabeado emitam a mesma forma.
- **Veredito**: `FAIL` > `INCOMPLETE` > `ok`. A falha sempre vence.
- **`sys.exit` inalterado** — a D-04 recusou alargar o 7 por escrito.
- **`check_claims_stale`**: ramo sem `active_phase` vira `not-applicable` +
  `scope: no-input`, `detail` preservado integralmente.

### Símbolo, medido e não olhado

`unicodedata.east_asian_width` em 2026-08-05:

| candidato | codepoint | width | veredito |
|---|---|---|---|
| `⊘` | U+2298 CIRCLED DIVISION SLASH | `N` | **adotado** |
| `✓` U+2713, `⚠` U+26A0, `✗` U+2717 | (já em uso) | `N` | confirmam a regra |
| `◌` | U+25CC | `N` | descartado: já é símbolo de etapa do board da fase 21 |
| `○` U+25CB, `·` U+00B7, `…` U+2026 | — | `A` | fora (largura 2 sob locale CJK) |

O teste afirma a propriedade, não o desenho: conjunto de chaves de `SYMBOL`,
`⊘ != ✓`, e `east_asian_width == "N"` para os quatro.

### Contrato escrito (Task 2)

- Docstring do módulo: vocabulário de quatro valores, bloco sobre o significado
  do estado novo, as duas famílias e o critério, o fato de `scope` só existir
  quando o status é o novo, e a regra dos contadores. Registra **medido versus
  assumido**: a largura do símbolo foi medida; a família de cada ramo é decisão
  escrita.
- Tabela de códigos de saída do docstring: a entrada do `0` ganhou a frase de
  que um `not-applicable` — inclusive um rodapé `INCOMPLETE` — continua saindo
  0, e **por quê**. A entrada do `7` está intacta.
- `cairn-doctor.sh`: cabeçalho em lockstep.
- `cairn/docs/commands/doctor.md`: legenda de quatro símbolos, explicação do que
  o `⊘` diz e do que não diz, tabela das chaves de veredito do `--json`
  (`.failed`, `.ok`, `.counts`, `.checks[].scope`) com a pergunta que cada uma
  responde, entrada de `claims-stale` atualizada, bloco de exemplo com rodapé de
  quatro números e um segundo exemplo mostrando `INCOMPLETE`, e a linha do `0` na
  tabela de códigos de saída.

## Testes: cada um com a quebra que o deixa vermelho

| teste | quebra nomeada |
|---|---|
| `report footer: four counters, summing to the check count, none by subtraction` | derivar qualquer contador como `len(checks) - os outros` — um quinto status cairia no balde de sucesso em silêncio |
| `status vocabulary: four symbols, the new one distinct and single-width` | reusar `✓` para o estado novo, ou escolher um caractere de largura 2 sob locale CJK |
| `claims-stale: no active_phase is not-applicable/no-input, routes, and never blocks` | manter o `ok` de antes do 29-07, manter o `warn` que o 29-07 deixou como marcador, ou promover insumo ausente a falha bloqueante |
| `healthy wired fixture` (asserção nova `.failed false`) | tratar `.failed` como complemento de `.ok` — são perguntas diferentes |
| `claims-stale: the doctor never writes active_phase and never reads current_phase` | (inalterada) tomar partido no dialeto |

Toda asserção de status é sobre o **valor exato**. Nenhuma negação.

## Deviations from Plan

### 1. [Rule 1 — premissa do plano corrigida] O plano previa **uma** mudança de teste; são **duas**

- **Encontrado durante:** Task 1, ao rodar o RED.
- **Achado:** o plano diz que "a mudança esperada é **uma só**: o teste do
  `claims-stale` sem insumo". Existe um segundo: `claims-stale: the doctor never
  writes active_phase and never reads current_phase` (`tests/cairn-doctor.bats`)
  também afirmava `.status == 'warn'` para o mesmo ramo, porque exercita o mesmo
  cenário por outro motivo (provar que `current_phase` não é adotado como
  sinônimo).
- **Decisão:** movido junto, com o valor exato (`not-applicable` + `scope`), e um
  comentário registrando que **o valor** moveu e **a abstenção que o teste
  protege** não. Nenhuma asserção foi afrouxada.
- **Commit:** feb02e2

### 2. [Rule 1 — premissa do CONTEXT corrigida] `SYMBOL` não pode usar as constantes como chaves

- **Encontrado durante:** Task 1.
- **Achado:** o gate de verificação do próprio plano lê `SYMBOL` com
  `ast.literal_eval`. Escrever `{NOT_APPLICABLE: "⊘"}` quebraria o gate, porque
  `literal_eval` não resolve nomes.
- **Decisão:** `SYMBOL` usa strings literais; `NOT_APPLICABLE` continua sendo a
  constante nomeada usada nos retornos das checagens e na contagem. O comentário
  ao lado registra que `SYMBOL` é a fonte do vocabulário.

### 3. [Registro, sem ação] A linha de base do prompt diverge da medida

Ver "Linha de base" acima: prompt anunciou `15 ok / 3 warn`, medi `16 ok / 2
warn`. Exit 0 nos dois. Não alterei nada por causa disso.

### 4. [Achado, deferido] O cabeçalho de `tests/cairn-doctor.bats` diz "seventeen checks"

`tests/cairn-doctor.bats:8` ainda diz *"all seventeen checks ✓"*; são dezoito
desde o 29-07. Não é sítio desta task (o plano 01 fecha docstring, página e
wrapper). Levado para a passada final de coerência do plano 04, Task 2.

## Threat Flags

Nenhuma superfície nova. A fase não abre endpoint, não toca autenticação e não
instala pacote (python3 stdlib apenas). O `die()` no status desconhecido é o
T-23-01 do threat model aplicado.

## Known Stubs

Nenhum.
