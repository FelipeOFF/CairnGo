---
phase: 27-disagreement-trend-across-cycles
plan: "03"
subsystem: cli
tags: [trend, ambiguity, disambiguation, guard, derivation, bats]

requires:
  - phase: 27-02
    provides: "a série com direção por eixo, e o render que não computa nada"
provides:
  - "disambiguation(): o veredito unresolved/resolvable derivado do namespace `verifier_*`"
  - "READINGS: as duas leituras opostas por direção, com a frase que o leitor não pode levar embora"
  - "a declaração de ambiguidade colada na linha, e ausente quando não há linha em movimento"
  - "numbers_not_in_json(): a guarda mecânica do TREND-02, com controle negativo"
  - "a guarda de contagem viva fora do bloco de medição datado, sobre o .py e o .sh"
affects: []

actuals:
  tokens: 20000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "veredito por NAMESPACE e não por lista de nomes: uma lista de nomes conhecidos seria a lista escrita à mão que a fase caça"
    - "advertência condicionada ao fato: sem linha em movimento, sem declaração — aviso que sai sempre vira ruído que ninguém lê"
    - "guarda numérica possível porque o render não computa: todo token da prosa tem de existir como valor no --json"
    - "guarda com controle negativo próprio, e com liveness do próprio padrão — um regex que não casa nada fica verde para sempre"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-trend.py
    - tests/cairn-trend.bats

key-decisions:
  - "O desambiguador é um PREFIXO (`verifier_`), não uma lista de nomes: uma lista ficaria desatualizada no instante em que alguém escolhesse um nome fora dela, e o comando diria `unresolved` com o dado na frente"
  - "A chave tem de estar em TODO ciclo comparável — a mesma regra que decide o que é eixo, aplicada no mesmo lugar. Uma chave de um ciclo só não desambigua série nenhuma"
  - "A declaração não sai com série plana nem com série insuficiente: só existe ambiguidade quando existe uma linha em movimento para ser mal lida"
  - "`one` e `um` ficaram fora da lista de numerais da guarda de docstring: nas duas línguas funcionam como artigo indefinido, e os três precedentes desta casa foram todos contagem de conjunto"
  - "Não houve página em `cairn/docs/commands/`: sem comando slash, uma página ali seria reportada como órfã pelo `cairn-wrap.py docs` — sinal falso. O contrato mora no docstring, que a casa declara canônico"

status: complete
---

# Phase 27 Plan 03: A ambiguidade declarada Summary

A linha que cai sai com a declaração de que ela é ambígua na raiz — e a declaração
nasce de uma busca no disco, não de uma frase impressa.

## O que foi construído

```
! a direção de `primeira aprovação` é ambígua na raiz, e este comando não a
  resolve. 67% → 50% → 43% é igualmente consistente com (a) a qualidade caindo —
  mais fases chegando ao fim com lacuna e (b) o escrutínio subindo — o verificador
  ficando mais rigoroso e achando o que antes passava. Nenhuma chave `verifier_*`
  é comum aos 3 ciclos comparáveis, então nada no dado separa as duas. Leia a
  linha como "o par qualidade×escrutínio mudou", nunca como "a qualidade caiu".
```

Nenhuma palavra disso é impressa incondicionalmente. O veredito pergunta ao disco se
existe chave do namespace `verifier_*` comum a todo ciclo comparável; não achando
nenhuma, o veredito é `unresolved` e a declaração existe. Acrescentar
`verifier_rigor` ao frontmatter de todos os ciclos comparáveis — e nada mais — vira o
veredito para `resolvable` e **a declaração some**, porque deixou de ser verdadeira.

## O desenho que resolve o problema real

Declarar a ambiguidade em prosa fixa seria fácil e inútil: uma frase impressa sempre
não é uma checagem, é um aviso, e um aviso que nunca muda vira ruído que ninguém lê.
Pior, ela continuaria impressa no dia em que o dado passasse a desambiguar — o mesmo
envelhecimento dos três precedentes desta casa, na forma de advertência em vez de
número.

Três decisões fazem a declaração ser uma leitura e não uma frase:

1. **Um prefixo, não uma lista de nomes.** `DISAMBIGUATOR_PREFIX = "verifier_"`. Uma
   lista (`verifier_version`, `verifier_rigor`, …) seria exatamente a lista escrita à
   mão que esta fase persegue.
2. **Em TODO ciclo comparável.** A mesma regra que decide o que vira eixo. Uma chave
   que só o ciclo mais recente carrega não desambigua série nenhuma — e há teste para
   o atalho: sem ele, uma implementação que aceitasse "a chave em qualquer lugar"
   passaria no teste de acréscimo.
3. **Condicionada à linha.** Série plana ou insuficiente: sem declaração. Só existe
   ambiguidade quando existe uma linha em movimento para ser mal lida.

## A guarda contra o quarto precedente

Afirmar "nenhum número é digitado" não vale nada. A guarda roda o comando duas vezes
contra o mesmo alvo, uma em humano e uma em `--json`, e afirma que **todo token
numérico da saída humana existe como valor no JSON**. Dois alvos — a árvore real e um
fixture — porque um comando que derivasse num e carimbasse no outro passaria numa
checagem de alvo único. E controle negativo: um número forjado é rejeitado, senão uma
extração de tokens quebrada ficaria verde para sempre.

Ela só é possível por causa de uma decisão dos planos anteriores: o render não computa
nada. Toda porcentagem, toda contagem e toda linha de pontos nasce formatada no
modelo. Sem isso, `67%` não teria valor por trás e a promessa do TREND-02 seria
inverificável.

A segunda guarda cobre o lugar onde os três precedentes nasceram: a prosa do próprio
arquivo. Nenhuma contagem sobre o estado do repositório vive fora do bloco `MEASURED
VERSUS ASSUMED` datado, no `.py` e no `.sh`.

**E ela pegou o meu próprio docstring**, em duas linhas — `"v1.2 and v1.3 have three
verification files each"` e `"vanished for two cycles"`, ambas contagens vivas escritas
fora do bloco datado. Corrigidas: a prosa passou a descrever o mecanismo e as contagens
ficaram onde a data as protege. Era o quarto precedente nascendo dentro do commit que
existe para impedi-lo.

## Deviations from Plan

**[Rule 1 - Bug] A guarda de docstring marcava definição como contagem**

- **Achado durante:** Task 2, na primeira execução da guarda.
- **Problema:** o padrão incluía `one`/`um` na lista de numerais, e casava
  `"at least one verification file"` — que é a definição do estado `comparable`, não
  uma contagem que envelhece.
- **Correção:** `one` e `um` fora da lista, com a razão escrita no teste: nas duas
  línguas funcionam como artigo indefinido, e os três precedentes desta casa foram
  todos contagem de conjunto (`fifteen`, `17`, `18`, `nineteen`). O dígito `1` fica.
- **Verificado:** dois casos de liveness no próprio teste garantem que o padrão
  continua casando o que deve.

## Verificação

`bash cairn/scripts/cairn-test.sh --jobs 4 tests/cairn-trend.bats` — 34/34, lido do
log inteiro.

Cinco quebras aplicadas ao fonte, uma a uma, com restauro por cópia:

| Quebra | Vermelho |
|---|---|
| `shared` vira união (chave em qualquer ciclo basta) | testes 26, 27, 29 |
| a declaração sai com qualquer direção, inclusive plana | teste 28 |
| o veredito é sempre `unresolved` | testes 25, 27 |
| o render volta a computar um número | teste 30 (GUARD) |
| ciclos `not-applicable` contribuem chaves | teste 29 |

## Achado de processo: outra sessão commitou nesta árvore

Os commits deste plano **não existem com mensagem própria**. Entre 19:37 e 19:44 de
2026-08-06 outra sessão, na mesma árvore, executou commits sobre `.planning/PROJECT.md`
usando um `add` abrangente, e arrastou junto os meus arquivos:

| Commit alheio | Mensagem | O que arrastou |
|---|---|---|
| `2c618d3` | `docs(v1.6): gerar markdown não economiza token…` | `cairn-trend.py` +116 |
| `3b04940` | `docs(v1.6): o que fica com o GSD são os agentes…` | `cairn-trend.py` +9, `cairn-trend.bats` +237 |

O conteúdo está **íntegro** — conferido byte a byte contra a cópia de trabalho, e a
suíte roda 34/34 depois do fato. O que se perdeu foi a atribuição: quem procurar a
origem da declaração de ambiguidade vai encontrá-la dentro de um commit que fala de
PROJECT.md.

Não reescrevi histórico. Reescrever exige autorização explícita e há outra sessão
ativa na mesma árvore, onde um force-push destruiria trabalho concorrente. O registro
fica aqui, com os hashes, para que o histórico continue navegável. Uma cópia dos três
arquivos foi guardada fora do git antes de qualquer outra ação.

## Self-Check: PASSED

- `cairn/scripts/cairn-trend.py` — existe, com `disambiguation`, `READINGS`, `wrap`
- `tests/cairn-trend.bats` — existe, 34 testes
- commits `2c618d3`, `3b04940` — no histórico, carregando este trabalho sob mensagem
  alheia (documentado acima)
