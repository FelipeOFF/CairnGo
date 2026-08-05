---
phase: 24-language-chosen-at-install
plan: "03"
subsystem: doctor
tags: [lang, subagent, doctor, reconcile]
requires:
  - "24-01: a chave e o payload de prepare"
  - "24-02: a propagação em `set`"
provides:
  - "a lingua no prompt do reconcile-investigator, lida do script"
  - "o check 18 do doctor, response-language"
  - "a asserção do conjunto exato de chaves do bundle de evidências"
affects:
  - "cairn-doctor.py: dezenove checks em vez de dezoito"
  - "reconcile.md passo 3: uma leitura a mais antes do spawn"
tech-stack:
  added: []
  patterns:
    - "um check que lê CRU de propósito, porque o resolvedor esconderia o que ele procura"
    - "warn para atrito, fail para inconsistência — gastar exit 7 em atrito ensina a ignorar exit 7"
key-files:
  created: []
  modified:
    - cairn/commands/reconcile.md
    - cairn/scripts/cairn-doctor.py
    - cairn/docs/commands/doctor.md
    - tests/cairn-reconcile-agent.bats
    - tests/cairn-reconcile.bats
    - tests/cairn-doctor.bats
    - CHANGELOG.md
decisions:
  - "A língua NÃO entra no bundle de evidências: `evidence_hash` é computado sobre ele e o cache do D-04 da fase 17 compara esse hash — um campo de língua invalidaria toda proposta em cache a cada troca de língua, gastando subagente por algo que não mudou evidência"
  - "O check lê os dois arquivos crus em vez de chamar `cairn-config get`: o `get` devolve o valor RESOLVIDO e reportaria concordância exatamente na situação que o check existe para pegar"
  - "O seam `CAIRN_CONFIG` foi escrito e depois removido do doctor: não era lido por nada, que é o defeito em miniatura que este projeto persegue"
metrics:
  duration: "~45min"
  completed: 2026-08-05
status: complete
---

# Phase 24 Plan 03: O segundo spawn, e a rede — Summary

O outro ponto de spawn do lifecycle recebe a língua, e a divergência entre os dois
arquivos deixa de ser invisível.

## O que mudou

**`reconcile.md` passo 3** lê a língua do `cairn-config.sh` antes de spawnar o
`reconcile-investigator` e a entrega junto do caminho do bundle e do número da fase.
Com uma fronteira escrita: **caminhos, ids, hashes, nomes de branch e qualquer linha
citada do repositório ficam exatamente como estão** — uma citação traduzida não é
uma citação, e o valor inteiro de uma proposta citada é a citação poder ser
conferida.

A língua **não** viaja dentro do bundle de evidências, e a razão é medida:
`evidence_hash` é computado sobre o bundle (`cairn-reconcile.py:525-531`) e o passo
2 compara esse hash para decidir se reaproveita uma proposta anterior. Um campo de
língua ali invalidaria toda proposta em cache a cada troca de língua — gasto de
subagente por uma mudança que não mudou evidência nenhuma.

**`check_response_language`** no `cairn-doctor.py`, o décimo nono check. Cinco
estados, todos testados pelo **valor exato** do status:

| estado | verdicto |
|---|---|
| sem resposta gravada no cairn | `ok` — nada a manter em acordo |
| `.planning/config.json` ausente ou ilegível | `ok` — não há para onde propagar ainda |
| gravada e nunca propagada | `warn` + o comando exato que fecha |
| os dois discordam | `warn` + os dois valores + qual governa |
| os dois concordam | `ok`, dizendo a língua |

`warn` e nunca `fail`, com a razão no código: divergir não quebra nada
mecanicamente — só faz metade dos subagentes de uma execução responder numa língua
e metade em outra, que é exatamente o que passou despercebido por um milestone
inteiro. Gastar exit 7 em atrito ensina todo mundo a ignorar exit 7.

## Por que o check lê os arquivos crus

Este é o único ponto onde o "faça shell-out para o script que é dono da regra" deste
repositório estaria **errado**. `cairn-config.py get` devolve o valor **resolvido** —
a chave do GSD quando setada, a do cairn senão — então perguntar a ele reportaria
uma resposta única e concordante exatamente na situação que o check existe para
pegar. O resolvedor esconde a divergência de propósito; o trabalho do doctor é
enxergá-la. E não há segundo resolvedor: nada no check decide quem vence, ele só
relata que dois arquivos dizem coisas diferentes e qual governa.

## Deviations from Plan

**1. [Rule 2 - Chave sem leitor, em miniatura] O seam `CAIRN_CONFIG` que escrevi e
apaguei.**
- **Encontrado em:** Task 2, ao revisar o próprio diff.
- **O que era:** acrescentei `CAIRN_CONFIG = os.environ.get(...)` ao bloco de seams
  do doctor por hábito, e o check não o usa — porque ele lê cru, pelas razões acima.
- **A correção:** removido. Um seam declarado e lido por nada é exatamente o defeito
  que `cairn.sync_push` documenta e que a regra de entrada do `cairn-config.py`
  existe para impedir. Escrevê-lo "por consistência" seria criar o segundo caso.
- **Commit:** `8744a55`

**2. [Medição corrige meu literal] `context_excerpt` faltava na asserção do bundle.**
- **Encontrado em:** Task 1, primeira execução do `cairn-reconcile.bats`.
- **O que houve:** escrevi o conjunto exato de chaves do bundle de cabeça depois de
  ler a fonte, e omiti `context_excerpt`. O teste ficou vermelho e a mensagem trouxe
  o conjunto real.
- **Por que isto é bom:** é a asserção fazendo o trabalho dela na primeira execução.
  Uma asserção de conjunto exato que passasse de primeira com um literal digitado de
  memória seria sorte, não prova.
- **Commit:** `cf121af`

## Verificação

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-reconcile-agent.bats` —
anunciou `1..9`, executou 9, 9 ok. Log inteiro lido.

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-reconcile.bats` — anunciou
`1..13`, executou 13, 13 ok. Log inteiro lido.

`bats -f "response-language" tests/cairn-doctor.bats` — anunciou `1..5`, executou 5,
5 ok. Log inteiro lido. O arquivo completo (`1..87`) foi rodado à parte; ver o
`24-SUMMARY.md` para o resultado e para o que a contenção de máquina custou.

### Controles negativos

Neutralizadas as duas comparações do check (cópia por `cp`, restaurada da cópia):
`bats -f "never reached GSD's config|two different values warn"` ficou **vermelho
nos dois** — `status returned 'ok', expected 'warn'` nas duas vezes. Sem a
comparação, o check diz que está tudo bem em ambos os estados defeituosos.

## O que NÃO está provado

Que o `reconcile-investigator` de fato responde na língua entregue. `bats` não
spawna o Task tool — a limitação que o cabeçalho do próprio
`tests/cairn-reconcile-agent.bats` já registrava antes desta fase ("bats never
invokes a real LLM subagent (no such precedent exists anywhere in this test
suite)"). O que está provado é que a língua é lida do script **antes** do spawn e
que o comando manda entregá-la.

## Self-Check: PASSED

Arquivos afirmados existem; commits `cf121af` e `8744a55` existem em `git log`.
