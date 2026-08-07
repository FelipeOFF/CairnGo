---
phase: 24-language-chosen-at-install
plan: "02"
subsystem: config
tags: [lang, install, config, propagation]
requires:
  - "24-01: a chave agents.response_language e a precedência"
provides:
  - "propagate_to_planning(): a escolha chega sozinha na chave que o GSD lê"
  - "o passo 3.5 do /cairn:init, antes do hand-off"
  - "a seção Language do /cairn:config"
affects:
  - "cmd_set: dois campos novos no --json e uma linha no render humano"
  - "init.md: um passo novo e uma re-execução no passo 6"
tech-stack:
  added: []
  patterns:
    - "propagação condicionada a arquivo já existente — nunca criar o que outro dono cria"
    - "idempotência decidida por `source`, não por heurística sobre o conteúdo"
key-files:
  created: []
  modified:
    - cairn/scripts/cairn-config.py
    - cairn/commands/init.md
    - cairn/commands/config.md
    - cairn/docs/commands/init.md
    - tests/cairn-config.bats
    - tests/cairn-init.bats
decisions:
  - "A propagação nunca cria `.planning/`: `gsd-tools config-set` cria (M-1), e um `.planning/` só com `config.json` faz o `detect` responder A em vez de D (M-2), parando o próprio init na segunda execução"
  - "`json.dumps(indent=2)` SEM `sort_keys` no arquivo do GSD: ordem preservada. `sort_keys` continua no arquivo que é nosso — o nosso a gente ordena, o do outro a gente visita"
  - "Arquivo ilegível é deixado como está, nunca reescrito: reescrever o que não se conseguiu ler destrói o que havia"
metrics:
  duration: "~40min"
  completed: 2026-08-05
status: complete
---

# Phase 24 Plan 02: A escolha na instalação — Summary

A língua é perguntada uma vez, na instalação, antes de qualquer subagente
nascer — e a resposta chega sozinha na chave que o GSD lê.

## O que mudou

**`propagate_to_planning()` em `cairn-config.py`.** `set` de uma chave que tem
`planning_key` escreve também `.planning/config.json`, e **só se aquele arquivo já
existir**. Quatro resultados, todos reportados em `--json` (`propagated`,
`propagation_reason`) e no render humano:

| estado | resultado |
|---|---|
| `.planning/config.json` ausente | `planning-config-absent`, nada escrito, `.planning/` **não criado** |
| existe e legível | `propagated`, chave escrita, ordem preservada |
| existe e ilegível | `planning-config-unreadable`, arquivo **intocado**, exit 0 |
| chave sem `planning_key` | `key-is-cairn-only`, arquivo do GSD intocado |

A condição do primeiro caso é a fase inteira em uma linha: criar `.planning/` aqui
reclassificaria de **D** para **A** um repositório greenfield que o cairn acabou de
tocar, e `init.md:20-22` manda o estado A **parar o init** e desviar para
`/cairn:migrate`.

**O passo 3.5 do `/cairn:init`**, entre o 3 e o 4 — antes do hand-off do passo 6.
A posição é a decisão: `/gsd:new-project` spawna os próprios subagentes
(researcher, synthesizer, roadmapper), então perguntar depois dele é perguntar
depois de os primeiros subagentes do projeto já terem respondido na língua errada.

Idempotência sem heurística: o passo lê `source` do `get --json`. `file` ou
`planning` significa escolha feita — diz qual é e **não pergunta nem escreve**. Só
`default` abre a pergunta. A única porta que escreve é a pergunta, e a pergunta não
abre.

**`/cairn:config`** ganhou a seção Language, com a regra de precedência dita ao
usuário em vez de oferecer uma escolha que não vai valer.

## Deviations from Plan

**1. [Medição corrige o plano] O diff da propagação não é de uma linha.**
- **Encontrado em:** Task 1, no teste que afirmava `grep -c '^>'` igual a 1.
- **A medição:** acrescentar uma chave ao fim de um objeto JSON põe **vírgula na
  linha que era a última**. A forma honesta é **1 linha removida e 2 adicionadas**,
  as duas na fronteira da chave nova. Quando a chave já existe (o caso do
  `.planning/config.json` real deste repositório) o diff é de fato de uma linha só.
- **O que ficou no lugar:** a asserção exata (1 `<`, 2 `>`, as duas mencionando a
  chave vizinha) **mais** a metade forte — remover a chave nova do arquivo depois e
  comparar `list(items())` com o original, provando que nenhuma outra chave mudou
  de valor **ou de posição**. O título do teste também foi corrigido, porque um
  título que discorda da sua asserção é o mesmo defeito em miniatura.
- **Commit:** `3c630b6`

**2. [Rule 1 - Bug no teste] Âncora ambígua no `init.md`.**
- **Encontrado em:** Task 2, primeira execução.
- **O problema:** o teste de ordem ancorava em `/gsd:new-project`, cuja **primeira**
  ocorrência é a linha 22 — o passo 0, que proíbe rodá-lo sobre um `.planning/`
  existente. A comparação era contra a linha errada.
- **A correção:** âncora no cabeçalho `## 6. Hand off`. E a frase do default foi
  reescrita para não cruzar quebra de linha, em vez de contorcer o `grep`.
- **Commit:** `a122b41`

## Verificação

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-config.bats` — anunciou
`1..28`, executou 28, 28 ok. Log inteiro lido.

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-init.bats` — anunciou
`1..11`, executou 11, 11 ok. Log inteiro lido.

### Controles negativos

Removido o bloco de propagação do `cmd_set` (cópia por `cp`, restaurada da cópia):
`bats -f "writes GSD's key when its file exists|human render of a propagating set"`
ficou **vermelho nos dois** — `jq '.propagated' returned 'false', expected 'true'`.

Removido o passo 3.5 inteiro do `init.md` (mesma disciplina de cópia):
`bats -f "init asks the response language|init names English"` ficou **vermelho nos
dois** — âncora vazia e frase do default ausente.

## O que NÃO está provado

Que o passo 6 é de fato re-executado numa instalação real. É prosa de comando, e a
rede contra ela é o check do `cairn-doctor` do plano 24-03 — que é justamente o
motivo de aquele check existir, e não uma justificativa depois do fato.

## Self-Check: PASSED

Arquivos afirmados existem; commits `3c630b6` e `a122b41` existem em `git log`.
