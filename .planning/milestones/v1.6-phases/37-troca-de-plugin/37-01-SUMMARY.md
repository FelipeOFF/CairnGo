---
phase: 37-troca-de-plugin
plan: 01
subsystem: plugin-manifest, commands, wrap-tooling
tags: [plugin, marketplace, wrappers, preflight, vendoring]
requires: [phase-32 vendoring closure, phase-36 bd adaptation]
provides: [plugin autocontido, preflight interno, 13 comandos sem delegação externa]
affects: [37-02 doctor, 37-03 docs, phase-38 paridade]
tech_stack_added: []
patterns: [vocabulário fechado checado no molde de wrap-family, bloco por marcador regenerado, oráculo com controle negativo]
key_files_created:
  - tests/cairn-standalone.bats
key_files_modified:
  - .claude-plugin/marketplace.json
  - cairn/.claude-plugin/plugin.json
  - cairn/scripts/cairn-wrap.py
  - cairn/commands/ (18 arquivos)
  - cairn/docs/gsd-core-commands.md
  - tests/cairn-wrap.bats
decisions: [D-01 implementation vendored|inline, D-02 preflight resolve não aposenta, D-05 passthrough sobrevive]
requirements: [PLUG-01, PLUG-03]
status: complete
completed: 2026-08-12
---

# Phase 37 Plan 01: A troca — o plugin fica autocontido Summary

O `cairn` deixou de depender de um plugin externo: o `gsd-core` saiu do
marketplace e das `dependencies`, os 13 wrappers formais pararam de delegar para
fora, e o `preflight` que os guardava passou a resolver contra o runtime
vendorizado do próprio plugin — continuando a poder falhar, que é a única coisa
que o torna uma guarda.

## O que foi feito

### A medição que decidiu a fase

Antes de planejar, cruzamento dos 13 `wraps:` contra `cairn/gsd/commands/gsd/`:

| Medição | Valor |
|---|---|
| wrappers formais (`grep -l '^wraps:' cairn/commands/*.md`) | 13 |
| commands vendorizados (`ls cairn/gsd/commands/gsd/`) | 8 |
| dos 13, **com** contrapartida vendorizada | **1** — `discuss-phase` |
| dos 13, **sem** contrapartida | **12** |
| cache do clone upstream no worktree | ausente |

Doze dos treze delegavam para comandos que o plugin não carrega. Vendorizá-los
era impossível offline e seria errado mesmo com rede: a fase 36 adaptou 8
workflows a bd em 7 planos, e prompt não-adaptado é exatamente a coexistência
que esta fase existe para fechar.

### A conversão

- **`discuss-phase`** → `implementation: vendored`. Preflighta e então lê
  `${CLAUDE_PLUGIN_ROOT}/gsd/commands/gsd/discuss-phase.md`, já adaptado a bd.
- **Os outros 12** → `implementation: inline`. Perderam o passo de preflight, e o
  passo "Run `/gsd:X`" virou o contrato do entregável: qual arquivo produzir,
  onde, com quais seções, e qual decisão registrar antes de começar.
- Os passos foram renumerados e **as referências cruzadas corrigidas por
  medição** (`grep -n '^[0-9]\. \*\*'` por arquivo), não por suposição — seis
  ponteiros apontavam para o número antigo depois da renumeração.

### O preflight inverte de alvo, não de razão

`find_gsd_command_dir()` deixou de varrer `installed_plugins.json` e o cache do
marketplace (as três funções de descoberta externa saíram) e passou a resolver
`gsd/commands/gsd` e depois `gsd/gsd-core/workflows` sob `CLAUDE_PLUGIN_ROOT`,
com fallback relativo ao próprio script. O seam `CAIRN_GSD_COMMANDS_DIR` ficou.

O exit 5 **mudou de significado**: era "não há GSD instalado nesta máquina",
passou a ser "este plugin está incompleto". São fatos diferentes para quem
debuga, e a mensagem acompanha.

## Testes, com números

| Suíte | Antes | Depois |
|---|---|---|
| `tests/cairn-standalone.bats` (novo) | 6 vermelhas / 2 verdes de controle | **8/8 verdes** |
| `tests/cairn-wrap.bats` | 24 testes, verde no mundo antigo | **25 testes, verde** (1 invertido, 1 negativo novo) |
| `tests/cairn-release.bats` | verde | verde (controle: os carregadores de versão não foram arrastados) |
| `tests/cairn-command-surfaces.bats` | verde | verde |

### A asserção que cada quebra derrubou

**O oráculo rodou contra o estado PRÉ-conversão e ficou vermelho lá** — é a
regra da casa, e sem isso ele não mediria nada:

| # | Asserção | Vermelho medido antes |
|---|---|---|
| 1 | o marketplace não publica linhagem GSD | `cairn,gsd-core` |
| 2 | plugin.json larga gsd-core, mantém context-mode | `gsd-core,context-mode` |
| 3 | os dois carregadores de versão concordam | **já verde — é o controle** |
| 4 | nenhum `inline` delega para fora | "nenhum comando declara implementation: inline" |
| 5 | todo `vendored` aponta arquivo existente | "nenhum comando declara implementation: vendored" |
| 6 | os 13 declaram, 1 + 12 | "declaram implementation: 0 (esperado 13)" |
| 7 | valor fora do vocabulário é exit 2 | saiu 0 (a chave não existia) |
| 8 | nada fora da fase 37 se moveu | **já verde — é o controle** |

**A inversão do teste 11 de `cairn-wrap.bats`**, e ela é o par que importa:
- antes: *"every wrapper delegates to a GSD command that is actually installed"*
  — percorria os 13 e exigia `preflight <verbo>` = 0 contra a máquina de quem
  roda;
- depois: *"every vendored command resolves against the runtime this plugin
  carries"* — percorre só os `vendored` e exige 0 contra o plugin, com um
  `checked > 0` que impede o laço de passar por vacuidade;
- **e o irmão negativo, novo:** `preflight spec-phase` → **exit 6**. Sem ele, a
  inversão viraria um gate que não pode falhar — exatamente o defeito que a
  docstring de `cairn-capability.py` documenta.

Medido na árvore: `preflight discuss-phase` → 0, `preflight spec-phase` → 6.

## Desvios do plano

**[Rule 2 — funcionalidade crítica ausente] `plan`, `work`, `verify`,
`autonomous` e `quick` retargetados**
- **Encontrado em:** Task 4, ao medir o resíduo de `/gsd:` em `cairn/commands/`.
- **Problema:** os cinco não carregam `wraps:`, então estavam fora de PLUG-01 —
  mas **são o ciclo** que o card da fase promete fechar, e apontavam para
  `/gsd:plan-phase`, `/gsd:execute-phase`, `/gsd:verify-work`, `/gsd:autonomous`
  e `/gsd:quick` externos. Com o `gsd-core` fora do marketplace, "máquina nova
  instala só o cairn e fecha um ciclo" seria falso.
- **Correção:** os cinco verbos **são** vendorizados; os passos passaram a
  nomear o arquivo sob `${CLAUDE_PLUGIN_ROOT}/gsd/commands/gsd/`.
- **Commit:** o mesmo da conversão dos 13.

**[Rule 1 — bug] O oráculo de imutabilidade media a base errada**
- **Encontrado em:** Task 1, na primeira rodada vermelha.
- **Problema:** o teste 8 usava `git merge-base` contra o branch do milestone e
  reprovava listando 12 arquivos da **fase 36** — trabalho legítimo, de outra
  fase. Um oráculo que reprova por trabalho alheio não mede o que promete.
- **Correção:** a base passou a ser derivada — o pai do primeiro commit que
  tocou o diretório desta fase.

## Premissas que a medição contradisse

1. **"Os 13 wrappers viram implementação direta" sugeria 13 conversões
   equivalentes.** A medição mostrou 1 + 12: um caso tem implementação para onde
   apontar, doze não têm. Sem esse cruzamento, doze comandos teriam ficado
   apontando para arquivos inexistentes e seus próprios preflights os
   recusariam — uma superfície morta que passa em toda revisão de diff.
2. **A dívida herdada da fase 36 sobre `export-identity` já estava paga.**
   `grep -c export-identity cairn/docs/commands/doctor.md` → 1 e a suíte de
   superfícies sai 0. Registrado em `deferred-items.md` para que o plano 03 não
   "conserte" o que já está de pé.

## Teto conhecido, escrito e não escondido

Os 12 contratos inline são **mais finos** que os workflows upstream que
substituem. É regressão de profundidade de prompt, aceita para fechar a janela
de coexistência. Os doze, por nome, para que a fase 38 não precise
redescobri-los: `spec-phase`, `mvp-phase`, `ui-phase`, `ai-integration-phase`,
`ultraplan-phase`, `plan-review-convergence`, `validate-phase`, `secure-phase`,
`phase`, `cleanup`, `review-backlog`, `audit-milestone`.

## Commits

| Hash | Mensagem |
|---|---|
| `2175f8f` | test(37-01): o oráculo do plugin autocontido, vermelho contra o estado pré-conversão |
| `c2324e5` | feat(37-01): gsd-core sai do marketplace e das dependências |
| `76c4ae8` | feat(37-01): o preflight resolve dentro do plugin, e a guarda continua mordendo |
| `66f9ad3` | feat(37-01): os 13 declaram onde vive sua implementação |
| `4349d5e` | docs(37-01): a página derivada e a premissa dos 54 comandos |

## Self-Check: PASSED
