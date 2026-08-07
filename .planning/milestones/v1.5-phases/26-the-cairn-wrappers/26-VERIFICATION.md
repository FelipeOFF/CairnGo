---
phase: 26-the-cairn-wrappers
verified: 2026-08-06T22:06:51Z
status: gaps_found
score: 3/3 critérios verificados, 3/3 requisitos entregues
behavior_unverified: 0
behavior_unverified_items: []
human_verification:
  - test: "Rodar um dos treze de verdade (ex.: `/cairn:discuss-phase 27`) num repo com issues abertas na fase"
    expected: "As issues da fase saem para `in_progress` atribuídas antes do `/gsd:discuss-phase`, e o que a discussão fechou sai fechado com razão; o que ficou pendente é liberado e continua aberto"
    why_human: "O bookkeeping dos wrappers é prosa executada por agente (`cairn/commands/<nome>.md`), não código. O teste 9 prova que cada arquivo NOMEIA `bd update --claim`, `bd close`, o par de labels e o carimbo `metadata.gsd` — nenhum teste roda um `bd` de verdade por um wrapper"
  - test: "Desinstalar/renomear um comando do gsd-core e rodar o wrapper correspondente pela interface do Claude Code"
    expected: "O agente para no passo 1, imprime a mensagem do script literalmente (exit 6, nome do comando, diretório, quantos comandos há nele, o conserto) e NÃO executa nada depois"
    why_human: "A recusa determinística do script está provada (exit 6 exato, medido nesta verificação). O que nenhum teste alcança é se o agente obedece à instrução de parar — a metade humana do WRAP-02"
overrides_applied: 0
gaps:
  - truth: "A lista de comandos que o usuário mais lê deixou de ser escrita à mão"
    status: partial
    reason: >-
      A metade dos wrappers foi de fato derivada: `cairn/commands/help.md` invoca
      `cairn-wrap.sh list` e o teste 23 reprova qualquer nome de wrapper transcrito
      dentro do bloco ```text. A outra metade do MESMO arquivo — o mapa dos 25
      comandos próprios — continua lista escrita à mão, sem guarda nenhuma, e
      medida por mim em 2026-08-06 ela já está mentindo: 23 dos 25 aparecem no mapa;
      `/cairn:reconcile` não aparece em lugar nenhum dele, apesar de existir
      (`cairn/commands/reconcile.md`, 5053 bytes), ter página
      (`cairn/docs/commands/reconcile.md`) e ter linha na referência
      (`cairn/docs/commands.md:48`). O outro ausente é `/cairn:help`, auto-referência,
      e não conta. `/cairn:reconcile` é literalmente um dos dois comandos que esta
      fase encontrou invisíveis e declarou consertados — consertados em `commands.md`,
      não no mapa do help. O `docs --check` só vigia `cairn/docs/`, e o teste 23 só
      sabe REPROVAR nomes de wrapper presentes; nenhuma das duas guardas consegue
      ver um comando próprio ausente. Como no gap registrado na fase 29: o contrato
      do ROADMAP § Phase 26 não difere este defeito — o critério 3 e o WRAP-03 falam
      da lista de WRAPPERS, e essa está derivada e verificada. Fica em `gaps` porque
      é da classe exata que a fase existe para matar, no arquivo que a própria fase
      voltou para consertar em `aa48bb3`, e é acionável em minutos.
    artifacts:
      - path: "cairn/commands/help.md"
        issue: "o bloco ```text lista à mão 23 dos 25 comandos próprios; `/cairn:reconcile` não está lá"
      - path: "tests/cairn-wrap.bats:480 (teste 23)"
        issue: "guarda só a direção 'nenhum wrapper transcrito'; um comando próprio ausente do mapa passa verde"
      - path: "cairn/scripts/cairn-wrap.py:471 (build_block)"
        issue: "`undocumented` é calculado contra `doc_text` de `cairn/docs/commands.md`; o mapa do help nunca entra na conta"
    missing:
      - "Dar linha a `/cairn:reconcile` no mapa do `/cairn:help` (seção MIGRATE & HEALTH, ao lado de `/cairn:doctor`)"
      - "Uma guarda que veja a direção que falta: um teste que rode `cairn-wrap.sh list --json` e afirme que TODO comando próprio (menos `help`) aparece no mapa — o simétrico do teste 23"
      - "Ou, a versão que não envelhece: fazer o help derivar também os próprios, do mesmo jeito que já deriva os wrappers"
---

# Phase 26: The cairn wrappers — Relatório de verificação

**Objetivo da fase:** os 13 wrappers `/cairn:*` que o GSD-05 decidiu e nunca foram
construídos existem, delegam ao `/gsd:*` correspondente com o bookkeeping bd da
casa, recusam-se a rodar quando o comando delegado sumiu, e a documentação lista
esses wrappers a partir do disco.

**Verificado:** 2026-08-06T22:06:51Z
**Veredito:** `gaps_found` — os três critérios do roadmap estão entregues e medidos;
uma lacuna adjacente, da mesma classe, sobrevive no `/cairn:help`.
**Re-verificação:** não — é a primeira desta fase.

## Critérios de sucesso (ROADMAP § Phase 26)

| # | Critério | Status | Evidência medida por mim |
|---|---|---|---|
| 1 | Cada wrapper existe, delega ao comando GSD correspondente, e faz claim/close das issues bd da fase ativa | ✓ VERIFICADO | 13 arquivos com `wraps:` em `cairn/commands/`; nos 13, `preflight <wraps>` = 1 ocorrência e o passo `Run /gsd:<wraps>` = 1 ocorrência, conferidos um a um com o nome tirado do próprio frontmatter; nos 13, `bd update` + `--claim` + `bd close` + `m-<milestone>` + `phase-<N>` + `metadata` presentes |
| 2 | Um wrapper cujo comando GSD não existe **falha nomeando o que falta** | ✓ VERIFICADO | Medido escondendo o comando: superfície de fixture com `plan-phase`/`ship`/`execute-phase`, `preflight ui-phase` → **exit 6**, mensagem nomeando `/gsd:ui-phase`, o diretório, `3 command(s) found there` e o conserto. Sem superfície nenhuma (HOME falso) → **exit 5** listando os três caminhos tentados. O par verde existe: `preflight ship` na mesma superfície → **exit 0** |
| 3 | A lista na documentação é derivada do que está instalado, não escrita à mão | ✓ VERIFICADO | Prova por acréscimo, feita por mim numa cópia: um 14º wrapper (`zeta-probe`, `wraps: docs-update`) largado em `commands/` fez a página ganhar a linha `\| [/cairn:zeta-probe](./commands/zeta-probe.md) \| /gsd:docs-update \|` sozinha, e o `diff` da prosa fora dos marcadores saiu **idêntico**. Nenhum nome de wrapper existe fora do bloco gerado em `cairn/docs/commands.md`; nenhum `N in total` fora dele |

## Requisitos

| Requisito | Status | Evidência |
|---|---|---|
| **WRAP-01** — os 13 existem e delegam com o bookkeeping da casa | ✓ ENTREGUE | `list --json` devolve 13 wrappers, e o conjunto de `wraps` é exatamente o do GSD-05: `ai-integration-phase, audit-milestone, cleanup, discuss-phase, mvp-phase, phase, plan-review-convergence, review-backlog, secure-phase, spec-phase, ui-phase, ultraplan-phase, validate-phase`. Os 13 têm página em `cairn/docs/commands/` |
| **WRAP-02** — recusa nomeada, em vez de exit 0 silencioso | ✓ ENTREGUE | Exit 6 e exit 5 reproduzidos por mim (acima). Os 13 `preflight` saem **0** nesta máquina. O teste 1 afirma `-eq 6` sobre uma superfície de onde o comando foi **retirado** — não é caminho feliz |
| **WRAP-03** — documentação derivada do instalado | ✓ ENTREGUE | `docs --check --json` na página real: `changed: false`, `undocumented: []`, `missing_pages: []`, `orphan_pages: ["bookkeep"]` (sobra declarada de propósito no CONTEXT § Deferred). Prova por acréscimo acima |

## Os dois critérios que eram fáceis de fingir — como conferi

### WRAP-02: o teste remove o comando, não roda o verde

`tests/cairn-wrap.bats:81` monta uma superfície GSD **com outros três comandos e sem
o procurado** e afirma `[ "$status" -eq 6 ]` — valor exato — mais cinco `grep -qF` na
mensagem (`/gsd:phase`, `is not installed`, o caminho, `3 command(s) found there`,
`fix:`). O par que impede o teste-tautologia está ao lado (`-eq 0` para um comando
presente na mesma superfície), e há um terceiro separando *não deu para olhar* (5) de
*olhou e não está lá* (6). **Nenhuma das 24 asserções de status usa negação** —
`grep` por `-ne` / `!=` sobre `$status` no arquivo devolve zero; as 24 são `-eq`.

Reproduzi os três casos fora do bats, com o script direto: 6, 0 e 5, com as mensagens
que o critério exige.

### WRAP-03: a derivação é real, e a prova é por acréscimo

`cairn-wrap.py` não carrega nenhuma lista de treze nomes: `collect()` varre
`commands_dir.glob("*.md")` e chama wrapper todo arquivo cujo frontmatter tem
`wraps:`. Conferido: `grep` pelos nomes dos treze dentro do `.py` não acha lista
literal — o único lugar onde os treze estão escritos é o teste 11, que é justamente
quem afirma acordo com a decisão GSD-05.

A prova independente que rodei (cópia em `/tmp`, repositório intocado):

```
$ cp -R cairn/commands  → +zeta-probe.md (wraps: docs-update)
$ cairn-wrap.sh docs --commands-dir <cópia> --doc <cópia>/commands.md
  … updated — 14 wrapper(s)
  ⚠ missing page: commands/zeta-probe.md
$ grep zeta-probe <cópia>/commands.md      → linha 99, na tabela
$ diff (prosa fora dos marcadores, antes/depois) → IDÊNTICA
```

Uma lista literal no lugar do gerador nunca produziria a linha 99. E a mesma corrida
mostra o gerador **nomeando a própria sobra** (`⚠ Missing page`) em vez de escondê-la.

O bloco derivado é a única casa da lista: fora dos marcadores, `cairn/docs/commands.md`
não contém nenhum `/cairn:<wrapper>` nem nenhum `N in total` — os dois guardas
(testes 22 e 24) rodam contra a página real, não contra fixture.

### O conserto do `/cairn:help` (aa48bb3): derivou de verdade — pela metade

`aa48bb3` existe, é ancestral de `HEAD`, e mexe em dois arquivos (`help.md` +19,
`cairn-wrap.bats` +24). O conserto é derivação genuína, não troca de lista por lista:
o `help.md` manda rodar `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" list`,
mostrar a saída sob `WRAPPED GSD COMMANDS`, e diz explicitamente *"Do not transcribe
that list into the map above"*, citando o defeito medido. O teste 23 afirma as duas
metades e eu confirmei a segunda: **nenhum** dos treze nomes aparece dentro do bloco
```text.

O que ele **não** cobre está no `gaps` do frontmatter: os 25 comandos próprios
continuam lista à mão no mesmo bloco, e essa lista já está desatualizada —
`/cairn:reconcile` não está lá. Ver a seção "Lacuna" abaixo.

## Artefatos

| Artefato | Esperado | Status | Detalhe |
|---|---|---|---|
| `cairn/scripts/cairn-wrap.py` | preflight + list + docs | ✓ VERIFICADO | 625 linhas, stdlib only, três subcomandos, códigos 0/2/3/5/6 documentados e observados |
| `cairn/scripts/cairn-wrap.sh` | shim | ✓ VERIFICADO | 14 linhas, `set -euo pipefail`, `exec python3` |
| `cairn/commands/*.md` (13 com `wraps:`) | os treze wrappers | ✓ VERIFICADO | os 13, cada um com preflight, delegação e bookkeeping |
| `cairn/docs/commands/*.md` (13) | página por wrapper | ✓ VERIFICADO | as 13 existem; `missing_pages: []` |
| `cairn/docs/commands.md` | bloco derivado | ✓ VERIFICADO | `changed: false`; lista só dentro dos marcadores |
| `cairn/docs/gsd-core-commands.md` | status atualizado | ✓ VERIFICADO | `**Status: decided and built.** Phase 26 shipped all thirteen`; contagens re-derivadas por mim pela receita que a própria página publica: **71** comandos instalados, **31** referenciados em `cairn/`, **40** sem referência — bate exatamente com o que a página afirma |
| `tests/cairn-wrap.bats` | as provas | ✓ VERIFICADO | 24 `@test`, 24 asserções `-eq`, zero negações |
| `cairn/commands/help.md` | mapa que não omite | ⚠ PARCIAL | deriva os wrappers; os próprios continuam à mão, e um falta |

## Elos

| De | Para | Via | Status |
|---|---|---|---|
| os 13 `cairn/commands/*.md` | `cairn-wrap.sh preflight <cmd>` | passo 1 de cada um | ✓ LIGADO — uma checagem, treze chamadores; nenhum escreve preflight próprio |
| `cairn-wrap.py list` | `cairn/commands/*.md` frontmatter | `collect()` + `glob("*.md")` | ✓ LIGADO — derivação do disco |
| `cairn-wrap.py docs` | `cairn/docs/commands.md` | `splice()` entre marcadores | ✓ LIGADO — vista do disco, prosa preservada |
| `docs --check` | suíte | teste 22, contra a página real | ✓ LIGADO — a página não envelhece em silêncio |
| `cairn/commands/help.md` | `cairn-wrap.sh list` | invocação + proibição de transcrever | ✓ LIGADO (wrappers) / ⚠ não existe para os próprios |

## Execução dos testes

Comando, exatamente o que foi pedido, em segundo plano com a saída lida de arquivo:

```
bash cairn/scripts/cairn-test.sh --jobs 3 tests/cairn-wrap.bats
```

Contagem feita **sobre o log inteiro** (27 linhas), não sobre saída truncada:

| medida | valor |
|---|---|
| plano anunciado pelo bats | `1..24` |
| `^ok` | **24** |
| `^not ok` | **0** |
| `# skip` | 0 |
| `bats warning: Executed N instead of expected M` | **nenhum** |
| exit code do runner | **0** |
| última linha antes do `EXIT_CODE` | `ok 24 the real command reference states no hand-written total` |

Anunciado = executado = verde. A única linha do log com a palavra *warning* é o nome
do teste 19 (`…is NAMED, and the warning clears`), não um aviso do bats — conferido.

`tests/` inteiro **não foi rodado**, por instrução.

## Verificações de comportamento que rodei fora do bats

| O quê | Comando | Resultado |
|---|---|---|
| lista derivada | `cairn-wrap.sh list --json` | 38 comandos: 13 wrappers, 25 próprios; conjunto de `wraps` = o do GSD-05 |
| página corrente | `cairn-wrap.sh docs --check --json` | exit 0, `undocumented: []`, `missing_pages: []`, `orphan_pages: ["bookkeep"]` |
| recusa nomeada | `preflight ui-phase` com o comando escondido | **exit 6** + mensagem completa |
| não deu para olhar | `preflight ui-phase` com HOME falso | **exit 5** + os três caminhos tentados |
| par verde | `preflight ship` na mesma superfície | exit 0 |
| os treze nesta máquina | `preflight <wraps>` × 13 | **0** para todos |
| derivação por acréscimo | 14º wrapper numa cópia | linha nova na página, prosa fora dos marcadores idêntica |
| contagens do `gsd-core-commands.md` | a receita publicada na própria página | 71 / 31 / 40 — bate |

## Anti-padrões

| Arquivo | Marcador | Severidade |
|---|---|---|
| os 13 wrappers, `cairn-wrap.py`, `.sh`, `.bats`, `commands.md`, `help.md` | `TBD` / `FIXME` / `XXX` / `HACK` / `PLACEHOLDER` / `TODO` | **nenhum encontrado** |

Os nove commits declarados no `26-SUMMARY.md` existem e são todos ancestrais de
`HEAD` (`b356d17`, `df1ce87`, `a8e6512`, `153e31b`, `3df4038`, `8aa5453`, `6c5fe1a`,
`a7c46df`, `aa48bb3`).

## Lacuna

**O mapa do `/cairn:help` continua lista escrita à mão para os comandos próprios, e
já está mentindo.** Medido em 2026-08-06: 23 dos 25 comandos próprios aparecem no
bloco ```text; faltam `/cairn:help` (auto-referência, irrelevante) e
**`/cairn:reconcile`** — que existe, funciona, tem página própria e tem linha na
referência (`cairn/docs/commands.md:48`).

O agravante é a identidade: `/cairn:reconcile` é **um dos dois comandos** que esta
fase encontrou invisíveis (`docs --check` nasceu vermelho apontando
`undocumented: ["config", "reconcile"]`) e declarou consertados. Foi consertado em
`commands.md`; no arquivo que o usuário mais lê, continua invisível.

Nenhuma guarda pega isso: o `docs --check` só olha `cairn/docs/`, e o teste 23 só sabe
afirmar a ausência de nomes de wrapper — a direção oposta (um próprio que sumiu) passa
verde por construção.

**O contrato do roadmap não difere este defeito** — o critério 3 e o WRAP-03 falam da
lista de *wrappers*, e essa está derivada, provada e verde. Fica registrado como
lacuna pelo mesmo motivo que a fase 29 registrou a dela: é a classe exata que a fase
existe para matar, no arquivo que a própria fase voltou para consertar, e o conserto
cabe em minutos.

**Precedente conferido, e ele agora é triplo.** O `cairn/docs/commands/doctor.md`
dizia *"fifteen checks in total"* com dezesseis registradas (consertado à mão em
`8d3db19`). Hoje a linha 371 diz *"nineteen checks in total"* e são de fato 19
funções `check_*` — essa envelheceu e foi corrigida. Mas a linha 449 da mesma página
diz *"It is not one of the **18** checks above"*: número escrito à mão, desatualizado
em um, vivo agora. Fora do escopo do WRAP-03 (não é lista de wrappers, e é outra
página), registrado como evidência de que a tese da fase está certa e de que o alcance
do `docs --check` é menor que a doença.

## O que não consegui verificar

1. **O bookkeeping em execução.** Os wrappers são prosa executada por agente. Provei
   que os treze *nomeiam* claim, close, o par de labels e o carimbo `metadata.gsd`;
   nada aqui roda um `bd` de verdade por um wrapper. Item 1 de `human_verification`.
2. **A obediência à recusa.** O script sai 6 e nomeia o que falta — medido. Se o
   agente de fato **para** ao ver 6 é a metade humana do WRAP-02. Item 2.
3. **Teste de mutação.** O `26-SUMMARY.md` afirma que `installed = True` deixa os
   testes 1, 3 e 6 vermelhos e que trocar a tabela por lista literal derruba 14 e 15.
   Não reproduzi as mutações (exigiria mexer no script do repositório); o que fiz no
   lugar foi ler as asserções e reproduzir os três códigos fora do bats — o teste 1
   não passaria com a checagem deletada, porque afirma `-eq 6` sobre uma superfície
   de onde o comando foi retirado.
4. **Estado das issues bd da fase** (`CairnGo-9xy`, `CairnGo-38j`, `CairnGo-5mu`).
   Não há `.beads/issues.jsonl` nesta árvore para leitura passiva, e não rodei
   ferramenta de escrituração. Fora dos critérios do roadmap.
5. **A suíte completa.** Não rodada, por instrução. O `26-SUMMARY.md` documenta por
   que ela não foi rodada na worktree da fase e registra uma corrida da árvore
   principal travada há mais de um dia — não confirmei nem refutei isso.

---

_Verificado: 2026-08-06T22:06:51Z_
_Verificador: Claude (gsd-verifier)_
