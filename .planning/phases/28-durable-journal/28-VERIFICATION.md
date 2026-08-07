---
phase: 28-durable-journal
verified: 2026-08-07T00:05:00Z
status: gaps_found
score: 5/5 critérios verificados, 4/4 requisitos entregues
behavior_unverified: 1
behavior_unverified_items:
  - behavior: "Duas máquinas FÍSICAS distintas, cada uma com seu próprio relógio e seu próprio hostname, escrevendo e mesclando pelo remoto"
    why: "Toda divergência foi construída com o seam CAIRN_JOURNAL_MACHINE dentro de um diretório, e todo merge foi local. O que isso NÃO alcança: um hostname que muda sozinho (DHCP/.local no macOS), um relógio com desvio real entre as duas, e um `git pull --rebase` vindo de um remoto de verdade. O E15 mediu que o `union` vale para rebase, cherry-pick e pull em clones reais, mas isso foi medido na pesquisa, não nesta suíte"
human_verification:
  - test: "Rodar o cairn num segundo checkout desta máquina, depois `git pull` no principal, e olhar `cairn-journal.sh history --json | jq '.partitions'`"
    expected: "Duas partições nomeadas, com machine igual e checkout diferente, e nenhum conflito de merge"
    why_human: "A suíte simula as duas máquinas por env seam. O caso real usa os quatro worktrees que já existem nesta máquina, e ninguém pode construí-lo dentro de um teste sem virar o mesmo simulacro"
  - test: "Deixar o journal crescer até passar de 200 KiB e observar a primeira compactação automática da vida real deste projeto"
    expected: "Um segmento `-0002.jsonl` aparece, o `-0001.jsonl` fica byte a byte idêntico, e `last-moved` responde o mesmo antes e depois"
    why_human: "O gatilho nunca disparou fora de teste. Medido hoje: 35.102 bytes contra 200 KiB, e a taxa observada em 24 h foi de ~7,1 KB/dia — a primeira compactação real está a algumas semanas, não a um comando"
overrides_applied: 0
gaps:
  - truth: "Um worktree de fase que journaliza nunca fica `removable` para o `cairn-parallel cleanup`, e nada no fluxo do cairn resolve isso"
    status: partial
    reason: >-
      Descoberto ao rodar a suíte inteira do lote, não previsto por nenhum plano.
      Com o journal versionado, medido nos dois lados: sem commitar a partição, o
      cleanup dá `uncommitted changes (git cannot recreate these)`; commitando a
      partição, dá `carries commits HEAD lacks`. Um worktree que journalizou só
      fica removable depois de a partição ser commitada E mesclada de volta, e o
      fluxo do cairn não faz nenhuma das duas. O teste da suíte passou a fazer as
      duas, porque as duas são verdadeiras e escondê-las seria o teste mentir — mas
      o atrito real continua vivo em `/cairn:parallel cleanup --apply`.
      Fora do escopo de DJOUR-01..04, que não mencionam `cairn-parallel`.
      Registrado em `CairnGo-rhq` [P2] com label `phase-28`.
      Evidência ao vivo no próprio checkout principal ao fechar a fase: o
      `git status` passou a mostrar
      `?? .cairn/journal/macbook-pro-de-felipe-2-fca41f649dbf-0001.jsonl`
      com 55 registros — a partição deste checkout, não rastreada, deixada de
      propósito para quem escritura decidir se entra no commit de fecho. Este é o
      mesmo atrito, na árvore de verdade e não numa fixture.
    artifacts:
      - path: "tests/cairn-parallel.bats:1645"
        issue: "a premissa escrita no teste ('the tree is clean') deixou de ser verdadeira; o fixture agora commita e mescla a partição para restaurá-la"
      - path: "cairn/scripts/cairn-parallel.py"
        issue: "conta a partição do journal como trabalho não commitado — defensável, e em tensão com o DJOUR-03, que diz que a perda do journal não muda veredito nenhum"
    next:
      - "Decidir entre: excluir `.cairn/journal/` da checagem de trabalho não commitado (defensável pelo DJOUR-03), commitar a partição no fim de fase, ou aceitar e documentar o atrito"
---

# Fase 28: Durable journal — Relatório de verificação

**Objetivo da fase:** o journal atravessa máquinas e checkouts sem que nada precise
ser mesclado.

**Verificado:** 2026-08-07, sobre `main` em `cce6ba4`
**Status:** gaps_found
**Re-verificação:** Não — verificação inicial
**Modo:** goal-backward. Os quatro `-SUMMARY.md` foram lidos como afirmação, não como
prova; toda medição abaixo foi refeita contra o código, os testes e o estado atual do
repositório.

---

## O que foi executado nesta sessão

Somente os `.bats` tocados, nunca a suíte inteira — a orquestração paga essa conta uma
vez no fim.

| Suíte | Testes | Exit |
| ----- | ------ | ---- |
| `tests/cairn-journal.bats` | 37 | 0 |
| `tests/cairn-doctor.bats` | 103 | 0 |
| `tests/cairn-init.bats` | 13 | 0 |
| `tests/cairn-status.bats` | 57 | 0 |
| `tests/cairn-reconcile.bats` | 14 | 0 |
| `tests/cairn-lease.bats` + `cairn-parallel.bats` + `cairn-tracker-card.bats` + `cairn-migrate.bats` | as demais do lote de 331 | 0 |

Além dos testes, medições ao vivo contra este repositório, todas em leitura:

- `cairn-journal.sh provenance --json` -> `{"actor":"FelipeOFF","checkout":"fca41f649dbf","machine":"MacBook-Pro-de-Felipe-2.local"}`
- contagem de registros e campos dos quatro checkouts desta máquina
- `git check-ignore` sobre segmento, lock e arquivo herdado
- `git worktree list`

**18 quebras foram aplicadas de verdade no fonte**, a suíte rodada, e o fonte
restaurado de cópia (`cp`, nunca `git checkout`). Cada uma está registrada no SUMMARY
do seu plano com a asserção exata que derrubou.

---

## Critérios de sucesso (vindos do ROADMAP)

### CS1 — `DJOUR-01` fechado pela pesquisa commitada, hash-chain rejeitada com medição ✓

`28-RESEARCH.md` está commitado, com 17 experimentos. O E6 mostra a cadeia quebrando
na primeira linha da outra máquina — duas cabeças, não uma — porque uma cadeia de hash
codifica ordem total de escrita e duas máquinas offline não têm uma.

Verificado por ausência, que é a única prova possível aqui: `grep -rniE
'prev_hash|hash.?chain|merkle'` em `cairn/scripts/` não devolve nada. **Nenhum plano
desta fase escreveu hash-chain em forma nenhuma.**

### CS2 — O registro carrega proveniência; registro antigo lê desconhecido ✓

`machine` e `checkout` entram no `_envelope()`, o único ponto onde qualquer registro
nasce — o que faz o acréscimo valer para `state_changed`, `verdict_changed`,
`lease_changed` e `snapshot` sem nenhum construtor capaz de esquecer.

O `checkout` é `sha256(machine + NUL + caminho)[:12]`. Três propriedades, as três
testadas: estável entre execuções, distinta entre checkouts da mesma máquina
(construído com `git worktree add` real, não suposto), e sem colisão entre máquinas
que compartilham o caminho.

A metade que importa mais é a segunda. `record_provenance()` **não chama**
`resolve_machine()`, então carimbar o host de hoje num registro herdado é impossível
por construção. E o teste não se contenta com `machine == null`: ele afirma também que
o valor **não é** o host corrente. Aplicada a fabricação no fonte, é essa asserção que
cai.

Medido no repositório real depois da fase: o `.cairn/journal.jsonl` herdado continua
com **176 registros e zero com `machine`**. Nada foi reescrito.

### CS3 — Cada checkout na sua partição, união sem acordo de relógio ✓

`.cairn/journal/<slug>-NNNN.jsonl`. As duas peças que o desenho exige, e nenhuma basta:
arquivos diferentes mesclam sem driver (E11 caso 1), mas a mesma partição em dois ramos
é add/add sem `merge=union` (E8b). O driver é o built-in e nunca um próprio — E17
mediu que um `merge.<nome>.driver` mora no `.git/config`, que o git nunca clona.

A divergência real foi construída duas vezes, com `git merge` de verdade dentro do
teste:

1. **Duas máquinas, dois arquivos:** 4 registros escritos, 4 legíveis, 0 conflitos,
   duas partições nomeadas.
2. **A mesma partição em dois ramos:** e aqui está a asserção que carrega o critério.
   O teste lê a **última linha física** do arquivo mesclado (`b_second`) e a compara
   com a resposta da dobra (`a_newest`). **As duas discordam** — e é essa discordância
   que prova que a leitura não é ordem de arquivo. A dobra anterior à fase 28
   responderia `b_second`.

E a linha do `.gitattributes` é carga, não decoração: o mesmo caso 2 sem ela conflita,
com marcadores.

Sobre o acordo de relógio: com mais de uma fonte, `last-moved` devolve `ts: null` e
nomeia cada candidato. O `value` sobrevive quando todas concordam, porque "o último
valor conhecido é X em toda parte" não ordena nada. O doctor diz isso em voz alta:
`(order between machines not claimed)`.

**A armadilha 1 da pesquisa foi respeitada e provada.** A dobra é snapshots por
`compacted_through_ts`, depois só os eventos posteriores por `(ts, nonce)` — nunca um
`sort` sozinho. Trocado por um `sort` sozinho no fonte, três testes caem, entre eles a
equivalência de replay, que **é** o E9.

### CS4 — Compactação concorrente nunca descarta a história de outra partição ✓

Compactar passou a significar selar o segmento ativo e abrir o próximo. Três regras,
três medições: reescrever faz o `union` ressuscitar o que foi dobrado (E5); apagar um
selado vira `modify/delete` (E10); sair da própria partição é o E13.

O teste do E13 **constrói** as duas compactações: `hostA` observa três coisas e
compacta, `hostB` observa duas outras e compacta, os dois estados vão para ramos e são
mesclados. A asserção conta **por máquina**, nunca o total, porque a falha do E13
produz um arquivo válido com um total plausível:

```
[.records[] | select(.machine == "hostA")] | length  ==  4
[.records[] | select(.machine == "hostB")] | length  ==  3
```

Aplicado o desenho ingênuo no fonte — partição única compartilhada, reescrita no lugar
— a asserção cai com o número exato do defeito: `hostA` de 4 registros para 1. É o E13
reproduzido dentro da suíte.

### CS5 — Apagar o journal continua não mudando veredito nenhum ✓

E aqui está o achado que mais vale desta fase. O teste que provava isso **tinha virado
teste morto e nada ficou vermelho**: o `rm -f .cairn/journal.jsonl` do
`cairn-status.bats` deixou de apagar o journal quando a escrita mudou de caminho, e o
diff estrutural seguinte comparava um render consigo mesmo.

O conserto não foi só apontar o `rm` para o lugar certo. Entrou a asserção que prova
que o apagar acertou o alvo — `history --json` com zero registros e zero partições —, e
ela é o que impede a mesma morte silenciosa de acontecer de novo. Aplicada a quebra
que é literalmente o código commitado antes do plano, a asserção devolve `10`, não `0`.

A prova foi estendida às três superfícies de leitura, e uma sutileza quase produziu uma
asserção errada: **a própria execução do doctor journaliza como efeito colateral**, então
o journal apagado é repopulado pela execução que está sendo medida e a cláusula
`last moved` volta, com timestamps novos. Isso é o journal se reconstruindo, não o
veredito se movendo. A asserção normaliza os timestamps e compara o resto byte a byte;
a metade "a cláusula some de fato" é medida à parte, com o `CAIRN_JOURNAL` inexistente.

---

## Cobertura de requisitos

| Requisito | Plano | Status | Evidência |
| --------- | ----- | ------ | --------- |
| DJOUR-01 | — (documental) | ✓ SATISFEITO | `28-RESEARCH.md` commitado, 17 experimentos; hash-chain rejeitada com E6; `grep` confirma zero implementação em `cairn/scripts/` |
| DJOUR-02 | 28-02, 28-03 | ✓ SATISFEITO | partições + `merge=union`, dobra ciente de `compacted_through_ts`, compactação por selo; os **dois** testes que o requisito nomeia (divergência real e compactação concorrente) existem e são vermelhos sob quebra |
| DJOUR-03 | 28-04 | ✓ SATISFEITO | apagar a superfície inteira não move status, severidade nem exit code nas três superfícies; o teste morto foi encontrado e reparado com guarda |
| DJOUR-04 | 28-01 | ✓ SATISFEITO | `machine`/`checkout` no envelope; herdado lê `null` com teste-guarda contra a fabricação; `git worktree add` real prova a distinção |

**4/4 entregues.** Nenhum requisito órfão: os quatro da linha `**Requirements**:` da
fase têm linha aqui e issue bd fechada com razão.

---

## Anti-padrões

| Arquivo | Achado | Severidade | Impacto |
| ------- | ------ | ---------- | ------- |
| `28-CONTEXT.md` / `28-RESEARCH.md` | "`cairn-journal.py` — 1.128 linhas" | ℹ️ Info | medido 948 antes da fase (o byte count citado, 47.001, confere). Quinto precedente medido de número escrito à mão que envelheceu neste repositório |
| `28-CONTEXT.md` D-01 | "141, 58, 1 e 1 registros" | ℹ️ Info | medido 176/64/1/1 um dia depois. Número vivo em prosa não datada |
| `28-CONTEXT.md` D-11 | "não precisa de negação de ignore" | ℹ️ Info | verdade pela metade: a linha 8 de fato não cobre `.cairn/journal/`, mas também não cobre o lock que passa a morar lá dentro. A negação foi necessária — ao contrário do previsto, para EXCLUIR a sujeira |
| `28-CONTEXT.md` (discrição) | "se o conserto do E12 entra nesta fase ou vira issue" | ℹ️ Info | não era discricionário: sob `union` a dobra ciente de `compacted_through_ts` virou requisito de corretude |
| `28-CONTEXT.md` D-10 | "não é aspiração, é o que já está testado" | ⚠️ Aviso | a degradação do código estava intacta, mas **o teste que a provava tinha deixado de provar**. Reparado no 28-04 |

Nenhum marcador de dívida (`TBD`/`FIXME`/`XXX`) sem referência formal foi introduzido.

---

## Resumo das lacunas

**Uma**, e ela não é de nenhum critério desta fase: versionar o journal fez todo
worktree de fase que journaliza deixar de ser `removable` para o
`cairn-parallel cleanup`. Medido nos dois lados — sem commitar a partição, o cleanup
diz `uncommitted changes`; commitando, diz `carries commits HEAD lacks`. Um worktree
que journalizou só fica removable depois que a partição é commitada **e** mesclada de
volta, e nada no fluxo do cairn faz nenhuma das duas.

O teste da suíte passou a fazer as duas, porque as duas são verdadeiras e escondê-las
seria o teste mentir. O atrito real continua vivo, registrado em `CairnGo-rhq` [P2].

Os cinco critérios estão verificados e os quatro requisitos entregues.

O que fica registrado como limite conhecido, não como lacuna: toda divergência entre
máquinas foi construída com o seam `CAIRN_JOURNAL_MACHINE` dentro de um diretório, e
todo merge foi local. Duas máquinas físicas com relógios e hostnames próprios, e um
`git pull --rebase` vindo de um remoto real, seguem fora do alcance desta suíte — o E15
mediu esse caminho em clones reais, mas na pesquisa, não aqui. Está em
`behavior_unverified`, com o teste humano que o cobre.

---
