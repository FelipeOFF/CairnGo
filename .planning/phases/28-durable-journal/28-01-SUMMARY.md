---
phase: 28-durable-journal
plan: "01"
subsystem: cli
tags: [journal, provenance, machine, checkout, schema-change, append-only, stdlib, bats]

requires:
  - phase: 16-transition-journal
    provides: "o envelope de registro e o `nonce` uuid4 — o ponto único onde a proveniência entra"
provides:
  - "resolve_machine() / resolve_checkout(): identidade derivada, estável, distinta, sem estado em disco"
  - "envelope com `machine` e `checkout` — vale para state_changed, verdict_changed, lease_changed e snapshot de uma vez"
  - "record_provenance(): a única leitura de proveniência, e ela nunca resolve o host atual"
  - "last-moved com proveniência por eixo, aditiva: `value` e `ts` intactos onde o doctor os lê"
  - "subcomando `provenance`: a identidade inspecionável de fora, sem escrever registro"
affects: [journal-partitions, journal-compaction, doctor-forensics]

actuals:
  tokens: 42000
  tasks: 2
  commits: 1
  tests: 7

tech-stack:
  added: []
  patterns:
    - "identidade derivada de (host, caminho) por sha256, nunca lida ou gravada em disco — partição nova em vez de estado a recuperar"
    - "campo ausente lê `null` e a leitura NUNCA chama o resolvedor: a fabricação fica impossível por construção, não por disciplina"
    - "teste-guarda da fabricação: além de afirmar `null`, afirma que o valor NÃO é o host corrente — é a asserção que cai no dia do 'conserto'"
    - "acréscimo de schema em envelope único: um ponto de nascimento, quatro tipos de registro, nenhum construtor capaz de esquecer"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-journal.py
    - cairn/scripts/cairn-journal.sh
    - tests/cairn-journal.bats

key-decisions:
  - "`machine` entra DENTRO do hash do `checkout`, não só ao lado: `/Users/x/Projects/CairnGo` é a mesma string no laptop e no desktop, e sem isso duas máquinas com o mesmo caminho colidiriam na mesma partição. Consequência registrada no docstring: a chave de partição é o PAR (machine, checkout), nunca `checkout` sozinho"
  - "Nenhum arquivo de id em disco. Um id gravado seria mais um estado per-machine sob `.cairn/`, com regra de ignore e caminho de recuperação próprios. O custo aceito no lugar: renomear o diretório (ou mudar o hostname) produz partição NOVA — seguro por construção, porque partição nova nunca conflita, e fragmenta a história"
  - "`resolve_machine()` devolve `None` com hostname vazio, nunca uma string inventada — a mesma regra que governa o registro herdado, aplicada à medição que falhou"
  - "A proveniência entra em `_last_known()` como acréscimo, com `value` e `ts` na mesma posição e com o mesmo significado: `cairn-doctor.py:_last_moved_clause` lê `entry['ts']` e não enxerga diferença nenhuma"
  - "O ramo de `snapshot` copia as entradas como já copiava, então a compactação carrega a proveniência do observador ORIGINAL — a identidade de quem compactou nunca vaza para o eixo dobrado"

status: complete
---

# Phase 28 Plan 01: Proveniência Summary

## O que foi construído

Todo registro novo do journal carrega `machine` e `checkout`, além do `actor` que já
tinha. O registro que já existe continua exatamente como está e lê como
**desconhecido** — `null` nos dois campos, nunca o host de hoje.

Medido antes de escrever qualquer linha, neste repositório, em 2026-08-06:

```
CairnGo             176 registros   35.102 bytes
CairnGo-phase-21     64 registros   12.477 bytes
CairnGo-phase-24      1 registro       253 bytes
CairnGo-phase-26      1 registro       253 bytes

actor nos 176 registros do checkout principal: FelipeOFF ×176  (um só)
campos presentes: action, actor, event, from, holder, nonce, phase,
                  prev_holder, source, to, ts
```

Quatro histórias que nunca se alcançam, na mesma máquina, sob um `actor` idêntico.
É por isso que a partição não podia ser derivada do dado que existia.

Depois do plano, no mesmo repositório:

```
$ cairn-journal.sh provenance --json
{"actor": "FelipeOFF", "checkout": "<hash12>",
 "machine": "<host>"}

$ .cairn/journal.jsonl  →  176 registros, 0 com `machine`
```

O arquivo herdado não foi tocado.

## Como a identidade é derivada

`checkout` = primeiros 12 hex de `sha256(machine + NUL + caminho-resolvido)`.
Estável (só caminho e host entram, nada de relógio, pid ou arquivo), distinta entre
checkouts da mesma máquina (caminhos distintos), e sem colisão entre máquinas que
compartilham o caminho (o host entra no hash).

Seams `CAIRN_JOURNAL_MACHINE` e `CAIRN_JOURNAL_CHECKOUT`, na convenção `CAIRN_*` da
casa — é o que permite um diretório só bancar duas máquinas nos planos seguintes.

## Os testes, e a prova de que provam

7 testes novos; 23 no arquivo. Cada quebra abaixo foi aplicada **de verdade** no
fonte, a suíte rodada, e o fonte restaurado de uma cópia (`cp`, nunca
`git checkout`):

| Quebra aplicada | Asserção que ficou vermelha |
|---|---|
| `machine` removido do `_envelope()` | 20 (registro novo carrega machine/checkout), 22 (compactação sem carimbo), 23 (os seams) |
| `resolve_checkout()` devolvendo constante | 19 (dois checkouts, ids diferentes), 23 |
| `resolve_checkout()` misturando `time.time()` | 18 (id estável entre execuções), 20 |
| `record_provenance()` caindo em `resolve_machine()` quando o campo falta — **a fabricação** | 21 (registro velho lê `null`, e não é o host corrente), 22 |

O teste 19 constrói o caso que o contexto nomeia com `git worktree add` de verdade:
dois checkouts, `checkout` diferente e `machine` **igual** — as duas metades importam,
porque `machine` igual é o que prova que o id não é um valor aleatório por execução.

O teste 21 carrega a asserção que a fase inteira depende: além de afirmar `null`,
afirma que o valor **não é** o host corrente. É ela que cai no dia em que alguém
"consertar" a leitura preenchendo o host de hoje.

## Premissa do contexto que a medição contradisse

O `28-CONTEXT.md` e o `28-RESEARCH.md` afirmam que `cairn-journal.py` tem **1.128
linhas**. Medido: **948 linhas** antes deste plano (o byte count que os dois citam,
47.001, confere). Número em prosa não datada, o quinto precedente deste repositório.

Os números de registro por checkout também envelheceram em um dia: a pesquisa mediu
141/58/1/1 em 2026-08-05, e hoje são 176/64/1/1.
