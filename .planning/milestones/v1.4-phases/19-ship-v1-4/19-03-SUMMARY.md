---
phase: 19-ship-v1-4
plan: "03"
subsystem: init
tags: [bash, bats, gitignore, migration, worktree]
requires:
  - "o laço idempotente de .gitignore que já existia no cairn-init.sh (grep -qxF por entrada, append só do que falta)"
provides:
  - "cairn-init.sh ignorando os 9 caminhos gerados sob .cairn/, incluindo a forma com curinga do journal"
  - "4 testes de sintoma em tests/cairn-init.bats — árvore limpa, config visível, upgrade da 1.4.x, idempotência"
  - "a razão concreta que o texto de migração do plano 19-02 vai citar: 'rode /cairn:init de novo'"
affects:
  - "cairn/docs/sync.md §4: tabela de 4 linhas -> 11, com coluna 'Committed?' preenchida"
  - "cairn/commands/sync-config.md e cairn/docs/commands/sync-config.md: a mesma afirmação de 'the generated three'"
  - ".gitignore deste repositório: + migrate-plan.json, migrate-state.json, plugin-root"
tech-stack:
  added: []
  patterns:
    - "lista explícita de caminhos, nunca ignore de diretório — a forma é presa por teste"
    - "bats: run captura, [ \"$status\" -eq N ] decide; negativa via status 1 de grep, nunca ! inline"
    - "git status --porcelain -uall nos testes: sem -uall o git colapsa .cairn/ inteiro numa linha só"
key-files:
  created: []
  modified:
    - cairn/scripts/cairn-init.sh
    - tests/cairn-init.bats
    - cairn/docs/sync.md
    - cairn/commands/sync-config.md
    - cairn/docs/commands/sync-config.md
    - .gitignore
decisions:
  - "AMPLIAÇÃO da D-03 (3 -> 9 entradas): a D-03 enumerou 3 porque 3 eram as conhecidas; a varredura do plano encontrou migrate-plan/migrate-state, e a minha encontrou plugin-root"
  - "journal por curinga (.cairn/journal.jsonl*) e não por nome exato — cairn-journal.py escreve journal.jsonl.tmp-* e journal.jsonl.compact.lock ao lado"
  - "DESVIO: 9 entradas, não as 8 que o <verify> do plano fixa — a truth #1 do próprio plano não fecha em 8 (ver Deviations)"
  - "mensagem de sucesso passa a reportar contagem em vez de nomes; a que enumera mente na próxima entrada"
metrics:
  duration: ~55min
  completed: 2026-08-01
  tasks: 2
  commits: 2
actuals:
  tokens: 9700
  tasks: 2
  commits: 2
status: complete
---

# Phase 19 Plan 03: O conjunto completo de arquivos gerados no gitignore Summary

**`cairn-init.sh` agora ignora os 9 caminhos gerados sob `.cairn/` em vez de 3 — com o journal por curinga para pegar os irmãos `.tmp-*` e `.compact.lock` — e 4 testes novos prendem o resultado pelo sintoma da fase 18 (árvore limpa) e pela forma do conserto (`sync.json` e `context.json` continuam visíveis ao git).**

## O que foi construído

### Task 1 — o script e o contrato (commit `401756d`)

`CAIRN_IGNORES` passou de 3 para 9 entradas. O mecanismo não mudou: continua `grep -qxF` por entrada e append só do que falta, com o cabeçalho escrito uma vez. O que mudou foi a lista e a mensagem.

| entrada | classe | por quê |
|---|---|---|
| `.cairn/id-map.json` | pré-1.4 | já estava |
| `.cairn/state.json` | pré-1.4 | já estava |
| `.cairn/conflicts.json` | pré-1.4 | já estava |
| `.cairn/journal.jsonl*` | v1.4, D-03 | **curinga**: `cairn-journal.py:652` cria `journal.jsonl.tmp-*` e `:580` mantém `journal.jsonl.compact.lock` ao lado |
| `.cairn/reconcile-evidence.json` | v1.4, D-03 | — |
| `.cairn/hook.log` | v1.4, D-03 | — |
| `.cairn/migrate-plan.json` | **ampliação** | plano de dry-run do `cairn-migrate`, por checkout |
| `.cairn/migrate-state.json` | **ampliação** | journal de retomada do `cairn-migrate` |
| `.cairn/plugin-root` | **ampliação minha** | `${CLAUDE_PLUGIN_ROOT}` absoluto, escrito por `/cairn:init` (`cairn/commands/init.md:75`) |

A mensagem de sucesso enumerava `(id-map, state, conflicts)` — passaria a mentir agora e mentiria de novo na próxima entrada. Virou contagem: `gitignored $ADDED generated .cairn state file(s)`. A mensagem do caso "já estava tudo lá" ficou literalmente intacta, porque dois testes dependem dela.

`cairn/docs/sync.md` §4: a tabela tinha 4 linhas e a frase abaixo dizia que o init acrescenta "the generated three" — as duas afirmações eram falsas. Tabela agora com 11 linhas (as 9 ignoradas + `sync.json` + `context.json`), cada uma com a coluna `Committed?`, e a frase descreve o conjunto e diz explicitamente por que é lista e não `.cairn/` em bloco. Acrescentado o parágrafo de upgrade ("re-run `/cairn:init`"), que é o texto que o 19-02 vai citar.

`.gitignore` deste repositório: faltavam `migrate-plan.json`, `migrate-state.json` e `plugin-root` — acrescentadas. Como o plano avisa, o diff pequeno aqui não prova nada; a prova é o teste em repositório temporário.

### Task 2 — provar pelo sintoma (commit `d4dbf49`)

`tests/cairn-init.bats`: 3 → 7 testes. A lista `CAIRN_GITIGNORE_ENTRIES` no topo foi ampliada (os 3 testes antigos iteram sobre ela, então passaram a cobrir as 9), e entrou uma `CAIRN_LEGACY_ENTRIES` com o `.gitignore` pré-1.4 verbatim.

Helpers locais no arquivo de teste: `make_cairn_generated_files` (um arquivo por caminho gerado, **incluindo** `journal.jsonl.tmp-abc123` e `journal.jsonl.compact.lock`), `make_cairn_committable_files` (`sync.json` + `context.json`) e `cairn_untracked` (lista os não rastreados sob `.cairn/`).

Detalhe que decidiu a implementação: `git status --porcelain` **colapsa** um `.cairn/` inteiramente não rastreado numa única linha `?? .cairn/`, e o teste 5 nunca veria `sync.json`. Por isso `-uall` nos dois testes — que de quebra deixa o teste 4 mais estrito, porque ele passa a nomear o arquivo que sobrou.

## Vermelho/verde — cada quebra, medida

Baseline: **7/7 verdes**. Cada quebra foi feita a partir de `cp cairn-init.sh /tmp/cairn-init.sh.orig`, restaurada com `cp` de volta, e a restauração conferida com `git diff --name-only` retornando 0 linhas (byte-identical). Nenhum `git checkout` em arquivo com trabalho não commitado.

| # | quebra | resultado | evidência |
|---|---|---|---|
| 1 | tirar `.cairn/hook.log` do array | **1 ok / 6 not ok** | teste 4 falha imprimindo `still untracked under .cairn/: .cairn/hook.log` |
| 2 | `.cairn/journal.jsonl` exato no lugar do curinga | **1 ok / 6 not ok** | teste 4 falha nomeando `journal.jsonl.compact.lock` e `journal.jsonl.tmp-abc123` — a falha um nível mais fundo que o plano previu |
| 3 | `.cairn/` em bloco **por cima** das 9 entradas | **6 ok / 1 not ok** | só o teste 5 fica vermelho: `grep -qF '?? .cairn/sync.json'` falha. Isolamento perfeito — é o único teste que pega o atalho de uma linha |
| 4 | remover a guarda `grep -qxF ... continue` do laço | **4 ok / 3 not ok** | testes 2, 6 e 7 vermelhos; o 6 pega a duplicação das 3 entradas antigas, que é exatamente o cenário do REL-04 |

A quebra 3 foi desenhada aditiva de propósito: se eu tivesse simplesmente trocado as 9 entradas por `.cairn/`, seis testes cairiam juntos e não daria para afirmar qual deles prende a **forma**. Adicionando o ignore em bloco por cima da lista completa, todos os outros continuam verdes e só o teste 5 cai — o que prova que ele, sozinho, é o que torna a forma inegociável.

Verde final: **7/7**, `bash -n` limpo, e `bats tests/cairn-gate.bats` (16 testes, que também invocam `cairn-init.sh`) sem regressão.

## Deviations from Plan

### 1. [Rule 2 — funcionalidade crítica faltando] `.cairn/plugin-root` é a 9ª entrada, e o `<verify>` do plano fixa 8

**Encontrado em:** Task 1, na varredura que o próprio plano manda fazer.

`/cairn:init` escreve `.cairn/plugin-root` com o conteúdo de `${CLAUDE_PLUGIN_ROOT}` (`cairn/commands/init.md:75`; documentado em `cairn/docs/commands/init.md:81` e `:111`). É um caminho **absoluto e por máquina** — commitá-lo publica o path do home de quem rodou e quebra a resolução em qualquer outro checkout. É a mesmíssima classe do journal, que o plano cita nominalmente como razão de information disclosure (T-19-10).

O conflito é dentro do próprio plano, não entre mim e ele:

- `must_haves.truths[0]`: *"Num repositório recém-inicializado onde **todo arquivo local que o cairn escreve** existe, `git status` não mostra nenhum não rastreado sob o diretório de estado do cairn."* — não fecha com 8 entradas, porque `plugin-root` é um arquivo local que o cairn escreve.
- `action` da Task 1: *"O conjunto completo, levantado varrendo **todo caminho sob o diretório de estado do cairn que qualquer script, hook ou adapter deste repositório escreve**"* — a definição do conjunto é a varredura, e a varredura devolve 9.
- `<verify>`: `test "$(grep -c "^  '\.cairn/" ...)" -eq 8` — a contagem literal, escrita antes da varredura.

Entreguei 9 e tratei o `-eq 8` como o defeito. Consequência a registrar: **esse `<verify>` da Task 1 fica vermelho se rodado verbatim** (`9 != 8`), e o `<done>` fala em "oito entradas". Quem verificar a fase deve ler `-eq 9`. Os outros três `<automated>` da Task 1 e os dois da Task 2 passam.

Contra-argumento considerado e rejeitado: manter 8 e só reportar. Custaria a truth #1 numa release cujo motivo de existir é justamente a pergunta de migração sem resposta — e reabriria o buraco na v1.5, obrigando a mesma nota de novo.

### 2. [Rule 1 — afirmação falsa em contrato] a mesma frase de "the generated three" vivia em mais dois arquivos

**Encontrado em:** Task 1, ao caçar referências à mensagem antiga do script.

O plano manda corrigir `cairn/docs/sync.md`. A mesma afirmação estava em `cairn/commands/sync-config.md:70` e `cairn/docs/commands/sync-config.md:66` — e a versão em `commands/` é instrução que o Claude executa, ou seja, ele diria ao usuário que são três. Corrigidos os dois, apontando para `sync.md` §4 como fonte única. Ambos também omitiam que `context.json` é commitável.

### 3. [ampliação da D-03, registrada como ampliação] `migrate-plan.json` e `migrate-state.json`

Isto veio do plano, não de mim, e está aqui porque o plano manda registrar: a D-03 do `19-CONTEXT.md` enumera **três** arquivos novos (`journal.jsonl`, `reconcile-evidence.json`, `hook.log`). As duas entradas do `cairn-migrate` são uma ampliação decidida no planejamento do 19-03, com a razão da própria D-03 aplicada a elas. Não foram decisão original da D-03 e não devem ser apresentadas como tal.

## O que o plano acertou e vale citar

- O aviso de que "um diff pequeno no `.gitignore` deste repositório não é prova de nada" — a prova em repositório temporário é o que pegou o colapso do `?? .cairn/` e forçou o `-uall`.
- A insistência no curinga do journal: a quebra 2 mostra que o nome exato deixa 2 arquivos escapando, e nenhum teste que releia o array pegaria isso.
- O `<verify>` da Task 2 rodar o arquivo inteiro em vez de filtrar por nome. Confirmado no ambiente: `bats -f` com padrão que não casa sai 1 com "no tests found", então um filtro escrito errado só sabe reprovar.

## Known Stubs

Nenhum.

## Threat Flags

Nenhuma superfície nova. As mitigações do registro do plano foram aplicadas: T-19-10 e T-19-12 pelo teste 4 (com `plugin-root` incluído, o que fecha um vazamento de path absoluto que o registro não listava), T-19-11 pelo teste 5, T-19-13 pela tabela do `sync.md`, T-19-14 pelo teste 6.

## Self-Check: PASSED

- `cairn/scripts/cairn-init.sh` — FOUND (9 entradas, `bash -n` limpo)
- `tests/cairn-init.bats` — FOUND (7 `@test`, 7 verdes)
- `cairn/docs/sync.md` — FOUND (11 linhas na tabela §4, sem "generated three")
- commit `401756d` — FOUND
- commit `d4dbf49` — FOUND
