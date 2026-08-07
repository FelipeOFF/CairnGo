---
phase: 28-durable-journal
subsystem: cli
tags: [journal, partitions, provenance, merge-union, compaction, e13, djour]

plans: 4
requirements: [DJOUR-01, DJOUR-02, DJOUR-03, DJOUR-04]
beads: [CairnGo-st3, CairnGo-w51, CairnGo-a78, CairnGo-5bx]

provides:
  - "proveniência no registro: machine, checkout e actor, com o registro herdado lendo desconhecido"
  - ".cairn/journal/<slug>-NNNN.jsonl: uma partição por checkout, o primeiro artefato versionado dentro de .cairn/"
  - ".gitattributes rastreado com merge=union, propagado pelo cairn-init"
  - "dobra por partição ciente de compacted_through_ts, e união que nomeia cada fonte sem afirmar ordem"
  - "compactação que sela o segmento e abre o próximo, restrita à própria partição"
  - "a prova do DJOUR-03 sob o layout novo, com a guarda que impede o teste de morrer de novo"
affects: [doctor-forensics, reconcile-bundle, status-board]

actuals:
  plans: 4
  tasks: 8
  commits: 4
  tests: 23

status: complete
---

# Phase 28: Durable journal Summary

O journal atravessa máquinas e checkouts sem que nada precise ser mesclado.

## O que a fase entrega

Antes: um arquivo local e gitignorado por checkout, com registros que não diziam de
onde vinham. Medido neste repositório em 2026-08-06, ao abrir a fase:

```
CairnGo             176 registros   35.102 bytes
CairnGo-phase-21     64 registros   12.477 bytes
CairnGo-phase-24      1 registro       253 bytes
CairnGo-phase-26      1 registro       253 bytes

actor: FelipeOFF em 176 de 176 registros
campos: action, actor, event, from, holder, nonce, phase, prev_holder,
        source, to, ts
```

Quatro histórias que nunca se alcançavam, na mesma máquina, sob um `actor` idêntico.

Depois: `.cairn/journal/<slug>-NNNN.jsonl`, uma partição por checkout, versionada,
com `merge=union` em cada uma. Duas máquinas nunca escrevem o mesmo arquivo, então um
merge só precisa concatenar. A leitura dobra dentro de cada partição e, entre elas,
**nomeia de onde veio cada eixo e nunca afirma ordem**.

## Os cinco critérios

1. **`DJOUR-01` fechado pela pesquisa commitada.** Hash-chain rejeitada com a medição
   ao lado (E6: a cadeia quebra na primeira linha da outra máquina — duas cabeças, não
   uma), e nenhum plano escreveu hash-chain em forma nenhuma.
2. **Proveniência no registro** (28-01): `machine` e `checkout` no envelope, derivados
   e nunca gravados em disco; registro anterior à fase lê `null` nos dois, com um
   teste que afirma `null` **e** afirma que o valor não é o host corrente.
3. **Partição por checkout, união sem acordo de relógio** (28-02): provado por
   `git merge` real de duas máquinas simuladas, e por um merge da mesma partição em
   dois ramos onde a última linha física discorda da resposta da dobra.
4. **Compactação concorrente não descarta história alheia** (28-03): o teste do E13
   constrói as duas compactações e mescla de verdade; a asserção conta **por máquina**,
   porque o defeito produz um total plausível.
5. **Apagar o journal não muda veredito** (28-04): provado nas três superfícies de
   leitura, depois de descobrir que o teste que provava isso tinha virado teste morto.

## O que ficou fora, e por quê

- **Hash-chain**, em qualquer forma. Rejeitada com medição, não por preferência.
- **Merge driver próprio.** E17: precisa de `merge.<nome>.driver` no `.git/config`,
  que o git nunca clona.
- **Relógio lógico** (Lamport ou vetorial) para ordem causal entre máquinas. É o único
  desenho que daria ordem verdadeira entre partições, e é desenho novo. A fase entrega
  "não afirmo ordem entre máquinas", que é honesto e barato.
- **Migrar o arquivo herdado.** Proibido pelo requisito: ele é lido como partição de
  proveniência desconhecida e sai da fase byte a byte idêntico.

## Números

23 testes novos e 4 reescritos, distribuídos em cinco arquivos. 4 commits, um por
plano. 18 quebras aplicadas de verdade no fonte e restauradas de cópia, cada uma com
a asserção que derrubou registrada no SUMMARY do seu plano.
