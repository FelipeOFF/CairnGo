---
phase: 36-workflows-steps-e-agentes-falam-bd
plan: 01
subsystem: camada-prompt-vendorizada
tags: [d-01, onda-zero, preambulo, vend-bytes, vend-revert, allowlist, porcelain-invertido]
requires:
  - superfície 87/87 pelo dispatcher único (fase 35)
  - byte-paridade contra o cache pinado (fases 33-35)
provides:
  - cairn-preamble.py/.sh — fonte única da linha canônica, reescritor cirúrgico
  - cairn/gsd-adaptations.json — allowlist versionada, três consumidores
  - oráculo de bytes dois-sentidos + recusa nominal do vendor
  - 34 blocos de preâmbulo resolvendo o binário python do repo
affects: [fase-36-planos-02-a-07, fase-37]
tech-stack:
  added: []
  patterns:
    [
      allowlist dois-sentidos (fora igual / dentro divergente),
      registro resolvido pelo --dest e nunca pela raiz do projeto,
      PORCELAIN invertido (conjunto divergente == conjunto registrado),
      invariante no lugar de contagem em suíte permanente,
    ]
key-files:
  created:
    - cairn/scripts/cairn-preamble.py
    - cairn/scripts/cairn-preamble.sh
    - cairn/gsd-adaptations.json
    - tests/cairn-preamble.bats
  modified:
    - cairn/scripts/cairn-inventory.py
    - tests/cairn-vendoring.bats
    - tests/cairn-command-surfaces.bats
    - 36 arquivos sob cairn/gsd/ (34 com bloco de preâmbulo + 2 fragments órfãos)
decisions:
  - "escopo por PADRÃO e não por diretório: os 3 blocos fora de workflows/agents entram porque D-02 delimita sítio de ESTADO, não sítio de preâmbulo"
  - "a categoria 'menção ao runtime morto' é ELIMINADA sob workflows/ e agents/, não excetuada: 10 linhas em 8 arquivos convertidas em três grupos"
  - "gate de revisabilidade deixou de ser numstat 1/1 e virou propriedade de conteúdo por linha — mais forte, e compatível com as conversões"
  - "a suíte permanente assere INVARIANTE do registro, nunca contagem: um número fixado aqui envelheceria no plano 03"
metrics:
  duration: retomada de sessão interrompida
  completed: 2026-08-11
status: complete
---

# Phase 36 Plan 01: A onda zero do preâmbulo Summary

**One-liner:** a camada prompt passou a resolver o binário python do próprio
repo em 34 blocos idênticos, provados RODANDO em três posições; a árvore
adaptada ganhou registro versionado com motivo por caminho, lido por três
consumidores; e as duas guardas que desfariam a fase em silêncio (byte-paridade
cega e re-vendorização) foram fechadas na mesma onda da primeira escrita sob
`cairn/gsd/`.

## A retomada: a rota escolhida e a razão medida

Esta sessão retomou o plano com Tasks 1 e 2 commitadas e o trabalho da Task 3
aplicado mas não commitado. O diagnóstico de partida supunha que o GREEN da
Task 2 não existia e que a ordem TDD havia sido quebrada. **A medição
contradisse a suposição:** o commit `957d0b9`, rotulado `test(36-01)`, contém
`cairn/scripts/cairn-inventory.py` (+55) e `tests/cairn-vendoring.bats`
(+134/-14) — isto é, RED e GREEN da Task 2 no mesmo commit. A Task 2 estava
completa e na ordem certa; o que faltava era só a Task 3 commitada.

Escolhida a **rota A (preservar)**, e a etapa de reordenação saiu vazia porque
não havia nada fora de ordem. A rota B (descartar e refazer) foi medida e
rejeitada pelo custo assimétrico:

- Reaplicação do reescritor sobre a árvore de `HEAD`, com o registro atual,
  num diretório temporário: `34 trocado(s), 0 já na forma canônica, 2
  registrado(s) sem preâmbulo`, e o `diff -rq` contra a árvore de trabalho deu
  **28 dos 36 arquivos byte-idênticos**. As rotas A e B **convergem byte a byte
  na parte mecânica** — evidência forte de determinismo do reescritor.
- Os **8** que divergiram são exatamente os 8 das conversões manuais (Grupos
  A/B/C, 10 linhas), que o reescritor não faz. Refazê-las à mão sob a rota B
  não teria garantia de convergência, e o diff conferido linha a linha provou
  que as 10 já aplicadas são exatamente as 10 que o plano especifica, sem
  nenhuma edição carona.

**Único defeito real encontrado:** dois testes da Task 1 em
`tests/cairn-preamble.bats` fixavam o estado *transitório* do registro vazio
(`length == 0`, e um caminho literal "ausente" que só era ausente porque o
registro estava vazio). Não era regressão: o próprio plano manda o registro sair
de 0 para 36 na Task 3, e o `verify` da Task 3 exige a suíte verde. Os dois
evoluíram junto com a aplicação (ver Desvios).

## A forma nova, e por que UMA só

```
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
```

Uma linha, quatro elos (variável já exportada → variável de projeto → toplevel
do git → `$PWD`), falha nomeada com `exit 1` dizendo o último caminho tentado e
o comando que cria o fato, e `gsd_run` como função de despacho.

**O colapso das duas variantes upstream** (longa de 19 ramos, curta de 3) numa
só: os ramos existiam para achar um runtime FORA do repo, varrendo diretórios de
host. O binário do repo não tem essa incerteza — ou o checkout está aqui, ou não
está, e nesse caso a resposta certa é a falha nomeada, não mais um diretório
para tentar. O append de PATH em `$CLAUDE_ENV_FILE`, que só a variante longa
fazia, saiu junto porque exportava o diretório do runtime antigo.

Verificação de que a forma é única: `sort -u` sobre a linha `CAIRN_GSD` dos 34
arquivos que a carregam devolve **1**.

## Escopo por PADRÃO: os 3 fora de workflows/agents

`commands/gsd/discuss-phase.md`, `skills/gsd-discuss-phase/SKILL.md` e
`gsd-core/references/planner-load-graph-context.md` carregam bloco de preâmbulo
e por isso entram, apesar de morarem fora dos diretórios de massa. A razão está
escrita no `reason` de cada entrada do registro: **D-02 delimita sítio de
ESTADO**, não sítio de preâmbulo; e um preâmbulo não trocado vira `exit 1` na
fase 37 — o de `planner-load-graph-context.md` é carregado pelo `gsd-planner`.

## As duas contagens, e o destino dos 6 da diferença

Medidas sobre a árvore em `HEAD` antes da Task 3 (comandos abaixo):

| medida | comando | valor |
|---|---|---|
| arquivos com MARCADOR de bloco | `grep -rl '_GSD_SHIM_NAME=' cairn/gsd --include='*.md'` | **34** |
| arquivos que citam o NOME do runtime | `grep -rl 'gsd-tools\.cjs' cairn/gsd --include='*.md'` | **40** |

Os **6** da diferença citam o runtime sem carregar bloco. Destino de cada um:

| arquivo | destino |
|---|---|
| `gsd-core/workflows/discuss-phase/modes/text.md` | **adaptado** (fragment órfão, Grupo A) |
| `gsd-core/workflows/plan-phase/steps/adr-ingest-express-path.md` | **adaptado** (fragment órfão, Grupo A) |
| `commands/gsd/plan-phase.md` | **lacuna medida** — superfície de comando |
| `skills/gsd-plan-phase/SKILL.md` | **lacuna medida** — superfície de skill |
| `gsd-core/references/execute-phase-between-wave-reset.md` | **lacuna medida** — references |
| `gsd-core/references/universal-anti-patterns.md` | **lacuna medida** — references |

## As 10 menções fora de bloco, em três grupos

Nenhuma exceção: a fase 37 remove o plugin, e instrução apontando runtime
inexistente é armadilha herdada.

**Grupo A — SEIS instruções de comando, viram `gsd_run` na grafia contratada:**

| sítio | de | para |
|---|---|---|
| `plan-phase.md:595` | `gsd-tools.cjs query config-set …` | `gsd_run query config-set …` |
| `execute-phase.md:425` | `gsd-tools.cjs query config-set …` | `gsd_run query config-set …` |
| `execute-phase.md:1561` | `gsd-tools.cjs query agent.classify-failure` | `gsd_run query agent.classify-failure` |
| `quick.md:642` | `gsd-tools.cjs query commit` (+ menção a "legacy") | `gsd_run query commit` (a menção a legado SAI) |
| `discuss-phase/modes/text.md:21` | `gsd-tools.cjs query config-set …` | `gsd_run query config-set …` |
| `plan-phase/steps/adr-ingest-express-path.md:12` | `gsd-tools.cjs query commit …` | `gsd_run query commit …` |

Os dois fragments órfãos usam `gsd_run query …` como o resto do corpus, e não a
variável do preâmbulo, porque não carregam bloco.

**Grupo B — UMA afirmação FALSA desde a fase 35, reescrita inteira**
(`verify-work.md:634`); trocar só o nome do runtime e manter a afirmação errada
seria pior que não tocar:

- **antes:** ``` `audit-open` is CJS-only until registered on `gsd-tools.cjs query`: ```
- **depois:** ``` `audit-open` is served by the repo dispatcher — `gsd_run query audit-open` answers with exit 0: ```

**Grupo C — TRÊS comentários de design/ambiente, que passam a nomear o binário
do repo:** `execute-phase/steps/codebase-drift-gate.md:11`
(`gsd-tools.cjs present` → `cairn-gsd.sh present`),
`execute-phase/steps/executor-isolation-dispatch.md:53`
(`inside gsd-tools.cjs` → `inside cairn-gsd.sh`) e `:92`
(`gsd-core/bin/gsd-tools.cjs` → `cairn/scripts/cairn-gsd.sh`).

6 + 1 + 3 = **10**.

## Os dois gates por nome do runtime, com valores diferentes e ambos exatos

- sob `cairn/gsd/gsd-core/workflows/` e `cairn/gsd/agents/`: **0 arquivos** — a
  categoria foi eliminada, não excetuada;
- na árvore inteira: **4 arquivos, 5 linhas** — exatamente os de fora do escopo,
  nomeados com linha: `references/execute-phase-between-wave-reset.md:2`,
  `references/universal-anti-patterns.md:37` e `:56`,
  `commands/gsd/plan-phase.md:43`, `skills/gsd-plan-phase/SKILL.md:43`.

Um gate tree-wide em zero seria insatisfazível por decisão; um gate só por
marcador de bloco deixaria as 10 menções passarem despercebidas.

## O gate de revisabilidade que substituiu o numstat 1/1

O numstat por arquivo ficou mutuamente inconsistente com as conversões (seis
arquivos passaram a ter duas linhas mudadas). A propriedade que o numstat
aproximava foi afirmada direto: **toda linha mudada sob `cairn/gsd/` cita o
runtime antigo, a forma nova, `gsd_run` ou o binário do repo.** Verificado com
`git diff -U0 -- cairn/gsd/` filtrado — saída vazia.

Efeito colateral medido e vale registrar: a troca é **1:1 e neutra em linhas** —
`36 files changed, 44 insertions(+), 44 deletions(-)`.

## Números antes/depois, e a razão do seam

Ambos pela ferramenta canônica, medidos em 2026-08-11:

| medida | comando | `files` | `lines` |
|---|---|---|---|
| ANTES (fecho do upstream) | `cairn-inventory.sh closure --json` sobre o cache pinado | 171 | 29957 |
| DEPOIS (árvore adaptada) | `cairn-inventory.py closure --source <cópia> --expect-commit <sha> --cache-dir <tmp> --json` | 171 | 29957 |

**Iguais, e isso é o resultado certo:** a onda zero troca linha por linha, sem
adicionar nem remover nenhuma. O número que a fase realmente move não é o do
`closure` — é o do registro de adaptações (0 → 36 caminhos divergentes do
cache), e esse tem gate próprio no bats.

**Razão do seam (INV-ESCOPO):** `closure` sempre resolve o corpus para o cache e
exige `HEAD == TAG_COMMIT`, então não há como apontá-lo para a árvore adaptada
sem o seam. O "depois" foi medido copiando `cairn/gsd/` para um diretório
temporário, com `git init` + commit + `git tag v1.10.0`, e rodando `closure` com
`--source`/`--expect-commit`/`--cache-dir` — o mesmo seam que
`tests/cairn-inventory.bats:37-46` já exercita. Sem ele, a contagem "depois"
seria imensurável pela ferramenta canônica.

## O que a onda zero NÃO resolve (NODE-SOBREVIVE)

Trocar o preâmbulo **não remove `node` do caminho executado**. Medido em
2026-08-11: **14 sítios `node -e` no corpus vendorizado**, 9 em escopo de massa e
5 em references.

| arquivo | sítios | fecha em |
|---|---|---|
| `gsd-core/workflows/execute-phase.md` | 4 | planos 03-06 (o workflow tem plano próprio) |
| `gsd-core/workflows/execute-phase/steps/executor-isolation-dispatch.md` | 2 | plano do execute-phase |
| `agents/gsd-verifier.md` | 2 | plano dos agentes |
| `gsd-core/workflows/plan-phase.md` | 1 | plano do plan-phase |
| `gsd-core/references/specless-probe-fallback.md` | 3 | **plano 07** (lacuna de references consolidada) |
| `gsd-core/references/checkpoints.md` | 2 | **plano 07** |

## Desvios do plano

1. **`tests/cairn-preamble.bats` não consta em `<files>` da Task 3, mas o
   `verify` da Task 3 exige a suíte verde.** Os dois testes que fixavam o estado
   transitório do registro vazio evoluíram no MESMO commit da aplicação, porque
   registro-cheio e expectativa-de-registro-vazio não podem coexistir verdes. Não
   houve `test(...)` RED separado: seria um RED fabricado — os dois testes não
   descrevem comportamento novo, descrevem o mesmo comportamento sem depender de
   um estado transitório.
2. **A contagem saiu da suíte permanente.** O teste do registro parou de asserir
   `length == 0` (ou qualquer número) e passa a asserir o INVARIANTE: forma da
   entrada (`path`/`phase`/`waves` não-vazio/`reason` não-vazia), ordenação por
   `path`, unicidade, e existência no disco de todo caminho registrado. A razão
   está escrita no teste: os planos 03 a 07 registram caminhos novos, e um número
   fixado aqui viraria falso-vermelho no primeiro deles. A contagem exata de cada
   onda mora no `verify` do plano correspondente, que é datado por construção.
3. **O caminho "ausente do registro" do teste de recusa passou a ser DERIVADO**
   (`comm` entre os `.md` da árvore, menos `contracts/`, e os `path` do registro)
   em vez de literal. Um literal viraria falso-VERDE no dia em que aquele caminho
   entrasse no registro — o teste seguiria passando por outro motivo.
4. **Task 2 commitada como `test(...)` contendo RED e GREEN.** Registrado aqui
   por honestidade de histórico; o conteúdo está correto e na ordem, o rótulo é
   que não separou.

## Quebras reais aplicadas (nenhum teste passaria com a feature removida)

Cada guarda reescrita foi quebrada no fonte, com `cp` de backup e restauração da
cópia (nunca `git checkout`), e a asserção derrubada foi registrada:

| quebra aplicada | asserção que ficou vermelha |
|---|---|
| registro perde `reason` numa entrada | `jq -e 'all(.adaptations[]; has("path") and has("phase")…` (linha 163) |
| registro fora de ordem (duas entradas trocadas) | `jq -e '[.adaptations[].path] == (… \| sort)'` (linha 169) |
| registro aponta caminho inexistente, preservando a ordem | `[ -f "$CAIRN_REPO_ROOT/cairn/gsd/$p" ]` (linha 176) |
| `cairn-preamble.py` perde a recusa por caminho não registrado | `[ "$status" -eq 2 ]` (linha 195) |

A terceira quebra precisou de duas tentativas: a primeira versão renomeava o
`path` para algo que também quebrava a ordenação, e derrubava a asserção errada.
Registrado porque é o tipo de falso-positivo que faz um controle negativo mentir.

## Verificação

- `bats tests/cairn-preamble.bats` — **13/13 verde**.
- `bats tests/cairn-vendoring.bats` — **26/26 verde**, com o cache pinado
  presente: o oráculo dois-sentidos está de fato mordendo (36 caminhos
  registrados, todos exigidos divergentes), não skipando.
- `bats tests/cairn-inventory.bats` e `bats tests/cairn-command-surfaces.bats` —
  verdes (consumidores do que a fase mudou).
- `cairn-preamble.sh check` → exit 0 (`✓ todo caminho registrado está na forma
  canônica`); `list` reporta os 34 na forma nova e 0 na antiga.
- Bloco `<automated>` do `verify` da Task 3 rodado **na íntegra**, incluindo o
  seam de medição — todos os gates verdes.
- `git status --porcelain` limpo, tirando um arquivo de journal do próprio cairn
  em `.cairn/journal/` que já estava lá, não rastreado e deliberadamente não
  adicionado (ver Pendências).

## Commits

- `f16ca5c` feat(36-01): cairn-preamble — a forma nova do preambulo, provada rodando, e o reescritor que a aplica
- `957d0b9` test(36-01): oraculo de bytes dois-sentidos (VEND-BYTES) e recusa nominal do vendor (VEND-REVERT)
- `3f95273` feat(36-01): os 34 blocos e os 2 fragments orfaos — registrados, trocados e medidos

## Pendências e o que os planos seguintes recebem

- **Regra do registro, válida para os planos 03 a 07:** todo caminho editado sob
  `cairn/gsd/` é registrado na MESMA task que o edita — caminho já registrado
  ganha a onda em `waves[]`, caminho novo ganha entrada nova. Registrar antes de
  editar deixa o oráculo vermelho; editar sem registrar, também.
- **PORCELAIN não é copiado.** O gate equivalente é o conjunto de caminhos
  divergentes do cache == conjunto da allowlist, por `comm` nos dois sentidos, e
  ele vale antes e depois do commit.
- **Lacuna medida para o plano 07:** os 4 arquivos com 5 linhas citando o runtime
  morto (2 references, 1 command, 1 skill) e os 5 sítios `node -e` de references.
- **Higiene do worktree:** `.cairn/journal/*.jsonl` não está no `.gitignore` e o
  nome do arquivo carrega o hostname da máquina. Não foi adicionado, e um
  `git add -A` numa sessão futura o publicaria. Vale um `.gitignore` — fora do
  escopo deste plano.
