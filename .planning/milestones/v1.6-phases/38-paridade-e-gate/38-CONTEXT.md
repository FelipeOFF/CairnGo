# Phase 38: Paridade, ponta a ponta e gate de saída - Context

**Mapeado:** 2026-08-12 (branch `phase/38-paridade-e-gate`, base `54770b3`, árvore limpa)
**Requisitos:** PAR-01 … PAR-04
**Research durante o planejamento:** não precisa (decisão do ROADMAP).
**Modo:** fase autônoma, sem checkpoint. Toda área cinzenta foi decidida aqui e está
marcada **Claude's Discretion**.

---

## Phase Boundary

É o fecho do milestone, e fecho é **consolidação**, não construção nova. O card cobre
quatro verbos — discuss, plan, execute, verify — e mais nada. Tudo que entra aqui ou
mede um deles, ou prova que o binário responde, ou fecha uma dívida medida da 37.

**Entra:** o guard de cobertura por verbo do binário python; o guard de paridade
executável (todo `gsd_run` do corpo vendorizado resolve num verbo que o binário serve);
o repositório de teste sem `gsd-core` que fecha o ciclo, sai limpo no doctor e verde no
gate; e a decisão vendorizar-ou-descartar dos 10 comandos que a fase 37 deixou medidos.

**Não entra:** vendorizar os 8 verbos fora do ciclo (ver D-01); remover fisicamente
`cairn/capability/` (dívida 2 da 37, continua candidata a fase posterior); aprofundar os
12 contratos inline (dívida 3 — este gate mede, aprofundar é trabalho com dado).

---

## O que foi MEDIDO antes de decidir

Toda medição abaixo é de 2026-08-12, na ponta de `phase/38-paridade-e-gate`, antes de
qualquer edição de produção.

### M1 — cobertura por verbo (PAR-01): já de pé, e é isso que o guard tem que travar

`cairn-gsd.py --list-implemented` → **87 verbos**. Cruzando com
`tests/fixtures/gsd-goldens/scenarios.json` (153 cenários) e com os 53 arquivos `.bats`:

| Fonte de cobertura | Verbos |
|---|---|
| cenário golden (`scenarios[].verb`) | 86 |
| teste bats direto (`run-with-timeout`, 9 testes) | 1 |
| **sem cobertura** | **0** |

Ou seja: PAR-01 **já está satisfeito de fato** e nunca foi travado por asserção. Um guard
escrito hoje nasce verde — e verde na chegada não mede nada. Por isso o oráculo do plano
01 é o **controle negativo**: um handler forjado sem cenário e sem bats tem que vazar
pela mesma comparação. Se não vazar, o guard é decoração.

### M2 — paridade executável (PAR-02): duas rotas mortas, silenciadas por `|| true`

Varrendo todo `gsd_run` dos 184 arquivos de `cairn/gsd/` contra a tabela
spelling→verbo que o dispatcher constrói (89 spellings, de `contracts.json` mais os
`spellings[]` de cada família), **2 chamadas não resolvem**:

| Chamada | Arquivo | Efeito real hoje |
|---|---|---|
| `gsd_run query worktree.set-baseref` | `gsd-core/references/execute-phase-between-wave-reset.md:30` | exit 2, engolido por `2>/dev/null \|\| true` |
| `gsd_run query requirements.revert-phase` | `gsd-core/references/execute-phase-requirement-revert.md:5` | exit 2, engolido por `>/dev/null 2>&1 \|\| true` |

Este é o achado da fase, e ele é exatamente a classe que o critério de honestidade
nomeia: **a superfície responde sem ter medido**. O workflow chama, o dispatcher morre 2,
o `|| true` apaga a morte, e o reset de baseRef entre ondas / o revert de requisito
simplesmente não acontecem — sem uma linha de erro.

**Por que ninguém tinha visto:** `cairn-inventory.py` — a fonte do universo de 87 —
varre `workflows8` (os 8 workflows e seus subdiretórios de steps) mais `agents`.
**`gsd-core/references/` está fora do escopo varrido.** As duas chamadas moram lá. O
universo estava certo para o que ele mediu, e cego para o que o runtime executa.

Falso positivo descartado: `gsd_run query verification status` (`execute-phase.md:367`,
forma com espaço) **resolve** — `query verification status` está registrado como spelling
de `verification.status`. Uma primeira varredura o acusou; a normalização de token
(tirar `)`, crase e vírgula de fim, que vêm de `$( )` e de prosa) o inocentou. Registrado
para que ninguém "conserte" o que está certo.

### M3 — a dívida dos 10 comandos (herdada da 37): 23 menções, 10 são passo

`grep -rn "/gsd:" cairn/commands/` → 23 ocorrências em 11 arquivos. Classificadas à mão,
uma a uma:

| Classe | Qtd | O que é |
|---|---|---|
| passthrough declarado (`gsd.md`) | 3 | intencional (D-05 da 37), fora do universo |
| **passo** — manda RODAR um verbo que a instalação limpa não resolve | **10** | `new:13`, `init:179`, `init:199`, `ship:16`, `milestone:12`, `milestone:55`, `progress:6`, `migrate:87`, `config:77`, `status:44` |
| prosa / instrução negativa ("nunca rode X") | 10 | `new:10`, `migrate:11`, `migrate:90`, `init:23/56/69/116`, `help:21/49`, `config:30`, `sync-config:44` |

Os 8 verbos nomeados (`new-project`, `new-milestone`, `complete-milestone`, `ship`,
`onboard`, `ingest-docs`, `progress`, `config`) não estão entre os 8 vendorizados em
`cairn/gsd/commands/gsd/` — em instalação limpa, nenhum deles resolve.

---

## Decisões

### D-01 — Os 8 verbos fora do ciclo: **descartar**, não vendorizar (Claude's Discretion)

A decisão que o research exigiu ("vendorizar ou descartar, nunca silêncio"), agora com o
dado que a 37 mandou buscar aqui.

**Custo medido de vendorizar:** os 8 arquivos de comando são pequenos (24–143 linhas),
mas cada um puxa seu workflow, e os workflows puxam references, templates e subagentes.
O vendor hoje tem 184 arquivos / 1,9 MB para 8 verbos; os 8 novos incluem
`new-project` e `onboard`, que abrem seus próprios subagentes. É ordem de grandeza de
dobrar a árvore vendorizada — e cada arquivo novo é superfície de deriva contra o pin
v1.10.0. Isso é um milestone, não o fecho de um.

**Descartar quer dizer três coisas concretas, nenhuma delas silêncio:**
1. Todo **passo** que manda rodar um verbo não resolvível é reescrito para algo que
   resolve, ou passa a dizer, na cara, que o cairn não vendoriza aquele verbo.
2. Toda menção que sobrevive fica **registrada** em `cairn/gsd/parity.json`, com
   disposição e motivo, verbo a verbo.
3. Um guard bats trava o registro **nos dois sentidos**: menção sem entrada reprova, e
   entrada sem menção (allowlist obsoleta) também reprova.

O que NÃO muda: `/cairn:gsd` continua sendo o passthrough declarado. Quem tem um GSD
instalado por fora segue podendo chamar; quem não tem lê a verdade em vez de um passo
que morre.

### D-02 — As 2 rotas mortas: implementar no binário, não apagar a chamada

`worktree.set-baseref` e `requirements.revert-phase` são verbos reais do upstream
(`command-aliases.cts` do clone pinado os traz como canônicos). Apagar a chamada
esconderia a regressão; implementar fecha a paridade. As duas são pequenas:
`set-baseref` é escrita no-clobber de `worktree.baseRef = "head"` em
`.claude/settings.local.json` (semântica copiada de `cmdWorktreeSetBaseRef` do clone
pinado); `revert-phase` é o inverso exato de `requirements.mark-complete`, que já
existe na casa.

### D-03 — O universo ganha as 2, com a cegueira DECLARADA (Claude's Discretion)

Somar os 2 verbos a `contracts.json` deixa o guard "universo == handlers" verde, mas
brigaria com o teste `cobertura cruzada`, que compara `contracts.json` com o inventário
vivo do clone — inventário que varre workflows8+agents e **não** varre `references/`.

Duas saídas ruins e uma boa. Ruim 1: deixar os verbos fora do universo (quebra o guard de
cobertura). Ruim 2: estender o escopo do inventário para `references/` — recomputa
`call_sites` de todo verbo e derruba a medição 97/12 que a 33 fixou. Boa: as 2 entradas
carregam `scope: "references"`, e o teste de cobertura cruzada passa a comparar o
inventário vivo **mais o conjunto declarado fora de escopo**. A cegueira do inventário
vira dado escrito, não exceção silenciosa. O somatório 97/12 não se move: ele soma as 5
famílias triviais, e as duas entradas caem em `worktree.json` e `misc.json`.

### D-04 — PAR-02 é provado no que é executável (Claude's Discretion)

"Fecha discuss, plan, execute e verify inteiros" não é rodável dentro de `bats`: os
quatro verbos são prompts que um agente executa. O que É verificável, e é o que o plano
03 prova num repositório de teste construído do zero, sem `gsd-core` instalado:

1. cada comando do ciclo aponta arquivos que **existem** dentro do plugin, e nenhum deles
   nomeia `/gsd:`;
2. toda chamada `gsd_run` que esses quatro caminhos atravessam resolve num verbo que o
   binário serve (é o guard do plano 02, aplicado ao ciclo);
3. os verbos que o ciclo de fato executa respondem no repositório novo (`state.load`,
   `init.*`, `phase.*`, `verify.*`, `commit`);
4. `cairn-doctor` sai **0** ali, com zero `✗`;
5. `cairn-gate` sai **0** ali — e **6** quando uma issue aberta é plantada numa fase
   completa, senão o verde não vale nada.

O item 5 é o controle: um gate que nunca fica vermelho não é gate.

### D-05 — Os testes novos moram em `tests/cairn-parity.bats` (Claude's Discretion)

Arquivo único e novo, porque é o oráculo desta fase e ele precisa ser rodável sozinho —
a suíte inteira passa de 1 h em série. Exceção: os testes de comportamento dos 2 verbos
novos vão para junto dos seus irmãos, em `tests/cairn-gsd.bats`.

### D-06 — Nome de `@test` sem acento, sempre

Medido na 37: `bats -j` não resolve nome de `@test` com caractere acentuado — 4 testes
viraram `unknown test name` e não rodaram, com a suíte saindo 1 pelos outros. Todo nome
de teste desta fase é ASCII. A prosa dos comentários continua em PT-BR com acento.

### D-07 — `cairn_gsd_render.py`: decidir era a entrega; a partição é trabalho próprio (Claude's Discretion)

`CairnGo-zzgn` estava aberta com label `phase-38` e o design dela dizia, com todas as
letras, "duas saídas possíveis, **decidir na 38**". A entrega devida era a decisão.

**Decidido: saída (a)** — partir `cairn_gsd_render.py` (1536 linhas) em envelope
(~8 símbolos compartilhados por 2+ irmãos) mais um substrato de documento, devolvendo ao
`cairn-gsd-check.py` os 24 símbolos que só ele usa. A saída (b) — manter um substrato
compartilhado e estender o teto a todo arquivo — foi descartada porque estender o teto
hoje o deixaria vermelho em três arquivos de uma vez, e um gate que nasce vermelho é
gate que alguém desliga.

**A execução não foi feita aqui, e não está escondida:** virou `CairnGo-2fyg` (backlog).
Refatorar 1536 linhas do binário na hora de fechar o milestone é o oposto de consolidar.

**O que a fase 38 entregou da dívida, e é a parte que importava:** o gate que faltava. O
teto D-01 da fase 34 ("nenhum arquivo passa de ~1.5k") **nunca teve teste** — vivia como
asserção de plano, o que quer dizer que valia no dia em que foi escrita e em nenhum
outro. Agora `tests/cairn-gsd.bats` carrega dois: um **pino por arquivo que só desce**
(nada cresce em silêncio) e a **lista fechada** dos três arquivos que já passam de 1500,
cada um com dívida nomeada — um quarto estourando o teto reprova a suíte. A cegueira que
a issue nomeia ("o gate media a coisa certa para o arquivo errado") está fechada.

Controle medido: duas linhas acrescentadas a `cairn-gsd-record.py` deixam o pino
vermelho, nomeando arquivo e números.

---

## Planos

| Plano | Requisito | Entrega | Oráculo (o que fica vermelho ANTES) |
|---|---|---|---|
| 38-01 | PAR-01 | guard de cobertura por verbo | controle negativo: handler forjado sem cobertura vaza |
| 38-02 | PAR-02 | paridade executável + os 2 verbos | scan acusa 2 rotas mortas; controle: chamada forjada vaza |
| 38-03 | PAR-02/03/04 | repositório novo + doctor + gate + registro de paridade dos comandos | 10 passos mortos; `parity.json` ausente; gate plantado sai 6 |
