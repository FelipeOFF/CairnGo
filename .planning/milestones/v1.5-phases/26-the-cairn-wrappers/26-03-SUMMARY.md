---
phase: 26-the-cairn-wrappers
plan: "03"
status: complete
requirements: [WRAP-01]
beads: [CairnGo-9xy]
subsystem: cairn/commands
tags: [wrappers, wrap-01, gsd-05, derived-docs]
provides:
  - "os treze wrappers /cairn:* decididos no GSD-05, construídos"
  - "a prova em campo do WRAP-03: doze linhas de tabela sem prosa editada"
  - "missing_pages — a terceira forma de a página mentir, nomeada"
key-files:
  created:
    - cairn/commands/discuss-phase.md
    - cairn/commands/spec-phase.md
    - cairn/commands/mvp-phase.md
    - cairn/commands/ui-phase.md
    - cairn/commands/ai-integration-phase.md
    - cairn/commands/ultraplan-phase.md
    - cairn/commands/plan-review-convergence.md
    - cairn/commands/validate-phase.md
    - cairn/commands/secure-phase.md
    - cairn/commands/cleanup.md
    - cairn/commands/review-backlog.md
    - cairn/commands/audit-milestone.md
  modified:
    - cairn/docs/commands.md
    - cairn/docs/gsd-core-commands.md
    - cairn/scripts/cairn-wrap.py
    - tests/cairn-wrap.bats
---

# Phase 26 Plan 03: Os doze restantes, e a documentação crescendo sozinha

Os treze wrappers do GSD-05 existem. A página ganhou doze linhas e ninguém
escreveu prosa.

## A prova em campo do WRAP-03, medida

O gerador nasceu quando havia **um** wrapper. Os outros doze chegaram depois.
Medido, nessa ordem, antes de regenerar:

```
$ cairn-wrap.sh docs --check                      → exit 3
  16 linhas '+', 2 linhas '-'
  as 12 linhas de tabela novas, mais o cabeçalho de família
  ('Milestone-scoped …') e a frase de contagem recalculada

$ cairn-wrap.sh docs                              → 13 wrapper(s)

$ diff <(sed '/generated:start/,/generated:end/d' antes) \
       <(sed '/generated:start/,/generated:end/d' depois)
  FORA DOS MARCADORES: idêntico byte a byte
```

Isso é o requisito acontecendo em produção, não em fixture: doze wrappers
entraram e a documentação passou a listá-los **sem uma linha de prosa editada**.
A prova por fixture (o teste 14) continua verde ao lado, como garantia
permanente.

## Os treze, e o que cada um acrescenta ao `/gsd:*`

Todos com o **mesmo** preflight — uma checagem, treze chamadores; treze cópias
divergiriam em treze velocidades — mais claim antes de delegar, close/release
depois, par de rótulos com número **não padronizado** e carimbo `metadata.gsd`.

**Família `phase` (9).** O que cada um acrescenta sai da coluna *"Why it needs a
wrapper"* do GSD-05, não da imaginação:

| wrapper | o que só ele faz |
|---|---|
| `discuss-phase` | o CONTEXT vira autoridade na divergência; a discordância é nomeada aqui, não descoberta no planejamento |
| `spec-phase` | cada requisito do SPEC vira issue carimbada; sem o `metadata.gsd.req` a issue cai na lista de lacunas do mapa, não numa linha |
| `mvp-phase` | preenche `beads:` e trata a fatia sem issue |
| `ui-phase` / `ai-integration-phase` | requisitos de contrato viram issues — no caso do AI, **os critérios de avaliação**, que são os que mais se perdem |
| `ultraplan-phase` | **a lacuna mais afiada da lista:** o PLAN volta da nuvem **sem `beads:`**, escrito onde nunca se ouviu falar deste tracker. Registra os ids antes da ida e preenche na volta |
| `plan-review-convergence` | reescreve PLAN.md, então a ligação é **re-resolvida** depois — não um diff — e um id que não pousa em lugar nenhum é **reportado**, nunca sumido |
| `validate-phase` / `secure-phase` | **nunca reabrem por conta própria** |

**Família `structural` (1).** `phase` — o caso mais forte, entregue no plano 01.

**Família `milestone` (3).**

- **`cleanup`** é o único dos treze cujo descuido **apaga registro**: o
  `NN-BEADS-MAP.md` mora dentro do diretório que vai ser arquivado. Confere
  **antes** de delegar, e é **o único lugar do cairn onde o exit 5 do
  `cairn-map` bloqueia** — em todo o resto um `bd` indisponível degrada com
  aviso; aqui a perda seria permanente.
- **`review-backlog`**: promover **cria trabalho rastreado**. Item promovido para
  o milestone mas ainda sem fase leva só o rótulo de milestone, a mesma regra do
  `/cairn:quick` — nunca uma fase chutada.
- **`audit-milestone`**: aponta para o portão do `/cairn:milestone complete` em
  vez de reimplementá-lo. Dois portões para a mesma coisa é a doença que este
  milestone trata.

### A decisão que não foi minha, e está marcada

`validate-phase` e `secure-phase` **reabrirem** trabalho fechado é o que a tabela
do GSD-05 afirma; **não medi** o comportamento deles ao vivo — registrado como
ASSUMIDO no `26-CONTEXT.md` D-07. Então a prosa reabre **condicionalmente ao que
o GSD fez**, nunca por iniciativa própria: reabrir afirma que trabalho concluído
não está concluído, e essa afirmação pertence ao audit.

## Desvios do plano

### 1. [Rule 2 — funcionalidade crítica ausente] A terceira forma de a página mentir

Ao gerar a tabela com os treze, a página passou a ter **treze links para páginas
que não existiam**. O gerador escreve uma linha por wrapper exista ou não a
página — **uma tabela de links quebrados é uma mentira que esta própria
ferramenta sabe produzir**, e não reportá-la seria trocar um defeito por outro
no mesmo commit.

Acrescentado `missing_pages`, ao lado de `undocumented` e `orphan_pages`. Os
doze apareceram nomeados; as doze páginas foram escritas; o aviso sumiu sozinho.
Teste 21 prova os dois sentidos.

### 2. [Rule 1 — a página sobre contagem, pega contando errado]

Ao atualizar o `gsd-core-commands.md`, re-derivei com **a receita que a própria
página publica**:

| | antes (afirmado) | agora (medido 2026-08-05) |
|---|---|---|
| total | 71 | **71** |
| referenciados por `cairn/` | 18 | **31** |
| sem referência | 54 | **40** |

`18 + 54 = 72`, um a mais que os 71 que existem. Causa localizada: **`config`
estava dos dois lados do corte** — na tabela "use directly" e, ao mesmo tempo,
citado como `/gsd:config` pelo `cairn/commands/config.md`. Corrigido por escrito,
com a distinção que faltava: "sem referência" e "tem decisão registrada"
deixaram de ser o mesmo conjunto, e só o segundo é o que a página promete.

Também acrescentado à receita que o segmento de marketplace no caminho muda por
instalação (`cairngo/` aqui, não `gsd-core/`), e que o `installPath` do
`installed_plugins.json` é o que sempre está certo — é o que o `preflight` lê.

### 3. [Decisão de escopo] `bookkeep.md` continua órfã, e visível

O aviso `⚠ Orphan page: commands/bookkeep.md` fica na página. Decidir se
`bookkeep` vira comando é decisão, não mecânica — está no `26-CONTEXT.md`
§ Deferred. **Deixá-la visível é o comportamento certo**: o requisito é a página
não mentir.

## Verificação

- `bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-wrap.bats` —
  **1..23 anunciados, 23 executados, 23 `ok`, 0 `not ok`**.
- `cairn-wrap.sh list --json` → **13** wrappers, e o conjunto de `wraps` é
  exatamente o do GSD-05 (afirmado por nome no teste 10 — o único lugar onde a
  lista literal é correta, porque é o teste que afirma o acordo com a decisão).
- Teste 11: `preflight` sai **0** para os treze nesta máquina — WRAP-02 ligado
  sobre o conjunto inteiro, não só "a checagem existe".
- `docs --check` → **0**; `missing_pages` e `undocumented` vazios.

## Self-Check: PASSED

- Os 12 arquivos em `cairn/commands/` — existem
- As 12 páginas em `cairn/docs/commands/` — existem
- Commits `3df4038`, `8aa5453`, `6c5fe1a` — existem
