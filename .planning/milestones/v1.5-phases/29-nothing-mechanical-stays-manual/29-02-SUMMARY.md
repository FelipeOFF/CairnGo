---
phase: 29-nothing-mechanical-stays-manual
plan: "02"
subsystem: planning-bookkeeping
tags: [python, bats, stdlib, markdown-surgery, idempotence, tracker]

requires:
  - plan: "29-01"
    provides: "cairn-bookkeep.py's reader, the frozen drift fixture and make_drift_fixture"
  - plan: "29-03"
    provides: "cairn-config.py, and the two keys this plan is the named reader of"
provides:
  - "cairn-bookkeep.py close <N> --apply: the whole end-of-phase bookkeeping in one invocation, idempotent"
  - "cairn-bookkeep.py reconcile --apply: the same edits without marking any phase complete"
  - "--no-tracker: the file half on purpose, with the skipped half named"
  - "cairn/docs/commands/bookkeep.md: contract, exit codes, derivation rule, and what the command does not do"
  - "the executable reader of bookkeep.auto_commit and ship.pr_scope"
affects: [29-07-req-ledger, autonomous-loop, ship]

tech-stack:
  added: []
  patterns:
    - "line surgery with two operations only: replace at an original index, insert at a planned position"
    - "one-way rule: a view is moved to done, never back — the reverse is reported as *-ahead"
    - "the tracker half is invoked by subprocess and gated BEFORE the first write"
    - "structural prose test: positive (the invocation) AND negative (no instruction beside it), scoped to the step"

key-files:
  created:
    - cairn/docs/commands/bookkeep.md
  modified:
    - cairn/scripts/cairn-bookkeep.py
    - cairn/scripts/cairn-bookkeep.sh
    - cairn/commands/autonomous.md
    - cairn/commands/help.md
    - cairn/docs/commands/autonomous.md
    - tests/cairn-bookkeep.bats

key-decisions:
  - "O rodapé passa a afirmar DOIS números — requisitos ativos e linhas mapeadas — corrigindo a regra 4 do 29-01: contar linhas duas vezes torna o rodapé impossível de contradizer a REQUIREMENTS.md, e faria o comando escrever `33 requisitos` num arquivo com 35"
  - "Linha de cobertura NUNCA é inventada para requisito sem portador legível: AUTO-05/AUTO-06 ficam em `unresolved` com `blocked_by`, porque a única fonte da célula de fase é a linha que é reticência"
  - "O comando só move uma vista para `done`; a direção inversa (vista adiantada) é reportada como `*-ahead` e nunca escrita"
  - "Os dois timestamps do STATE só andam junto com uma mudança real — escrevê-los sozinhos faria toda segunda passada de um comando idempotente ser escrita"
  - "Os testes de cirurgia passam `--no-tracker`: a afirmação deles é sobre a edição de linha, e o gate do bd tem testes próprios com require_bd"

requirements-completed: []

duration: ~3h
completed: 2026-08-04
status: complete
actuals:
  tokens: 27680
  tasks: 3
  commits: 3
---

# Phase 29 Plano 02: Fechar uma fase vira um comando — Summary

**`cairn-bookkeep.sh close <N> --apply` faz as seis edições, regenera o mapa e libera o lease numa invocação; contra a discordância congelada o diff é 15 linhas para 15, a segunda passada não escreve um byte, e as duas coisas que ele se recusa a escrever ele nomeia em vez de fingir que resolveu.**

## Performance

- **Duration:** ~3h
- **Tasks:** 3 de 3
- **Files:** 7 (1 criado, 6 modificados)
- **Commits:** 3

## O que foi construído

**`close <N> --apply` — as seis edições, mais o tracker.** Cada uma ancorada no
estado PRE, `count=1` por construção (substituição de uma posição da lista de
linhas), sem parser de markdown e sem reserialização:

1. o checkbox da fase, mais o sufixo `— completed <data>` na forma que a fase 20
   já carrega;
2. o checkbox de todo requisito cujas fases estão todas fechadas;
3. a célula de status desses requisitos → `Complete`, e uma linha nova para
   requisito ativo sem linha, inserida no fim do grupo da sua fase;
4. o rodapé, recontado;
5. cada checkbox de plano cujo `-SUMMARY.md` está no disco;
6. o frontmatter do STATE — e só as nove chaves listadas exaustivamente no
   docstring e na página;
7. `cairn-map.py <N>` e `cairn-lease.py release <N>`, por subprocess.

**`reconcile --apply`** faz 2 a 6 **sem marcar fase nenhuma** — o caminho para
arrumar discordância que já existe sem fingir que uma fase acabou de fechar.

**`--no-tracker`** é a metade de arquivo pedida de propósito, e o relatório diz
o que não rodou. **Sem `bd` e sem `--no-tracker`, exit 5 antes do primeiro
byte.**

**A página `cairn/docs/commands/bookkeep.md`** com a regra de derivação inteira
(uma autoridade, cinco vistas derivadas), a tabela de exit codes, as nove
chaves do STATE, as duas chaves de config e uma seção **"what it does not
do"**.

## Prova: 16 quebras nomeadas, cada uma vermelha e restaurada de backup `cp`

Nenhuma restauração usou `git checkout` — `cp` do backup, e `cmp` confirmando
byte a byte depois de cada uma.

| # | Quebra | Vermelho | Verde após restaurar |
|---|---|---|---|
| 1 | rodapé localizado por busca de texto no arquivo inteiro | 13/37 | 37/37 |
| 2 | rodapé contando as linhas da tabela duas vezes | 4/37 | 37/37 |
| 3 | timestamps do STATE escritos incondicionalmente | 1/37 | 37/37 |
| 4 | checkbox de plano adiantado sendo desmarcado | 1/37 | 37/37 |
| 5 | fase da linha nova adivinhada pelo prefixo do id | 6/37 | 37/37 |
| 6 | dois rodapés, "pega o primeiro" | 1/37 | 37/37 |
| 7 | chave `active_phase` inventada | 4/37 | 37/37 |
| 8 | checagem do `bd` movida para depois da escrita | 1/44 | 44/44 |
| 9 | shell-outs de mapa e lease pulados | 1/44 | 44/44 |
| 10 | `git add -A` varrendo a árvore para o commit | 1/44 | 44/44 |
| 11 | `pr_due` constante | 1/44 | 44/44 |
| 12 | `--no-tracker` pulando em silêncio | 1/44 | 44/44 |
| 13 | **instrução manual viva AO LADO da invocação** | 1/50 | 50/50 |
| 14 | invocação removida do passo | 1/50 | 50/50 |
| 15 | proibição da worktree enfraquecida | 1/50 | 50/50 |
| 16 | página perdendo a seção "what it does not do" | 1/50 | 50/50 |

A **13** é a mais informativa: com as duas instruções vivas ao mesmo tempo,
`grep -c "cairn-bookkeep.sh" autonomous.md` continua devolvendo 1 — a asserção
de presença aprova exatamente o arquivo que o `<done>` da task nega. Só a
asserção negativa escopada ao passo pegou.

A **1** é a mais cara: 13 testes vermelhos, porque a prosa do critério 5 é lida
por vários deles.

## Contagens de teste

| suíte | antes | depois | falhas |
|---|---|---|---|
| `tests/cairn-bookkeep.bats` | 23 | **50** | 0 |
| `tests/cairn-status.bats` (leitor) | 55 | 55 | 0 |
| `tests/cairn-map.bats` (leitor) | 12 | 12 | 0 |
| `tests/cairn-gate.bats` (leitor) | 16 | 16 | 0 |
| `tests/cairn-lease.bats` (leitor) | 24 | 24 | 0 |
| `tests/cairn-migrate.bats` (leitor) | 20 | 20 | 0 |
| `tests/capability.bats` | 20 | 20 | 0 |
| `tests/cairn-parallel-autonomous.bats` (contrato do `autonomous.md`) | 9 | 9 | 0 |

Os **cinco leitores** que o plano pede (`status`, `gate`, `migrate`, `map`,
`lease`) somam **127 testes, 0 falhas** — é neles que a forma de uma linha
editada apareceria se a cirurgia a tivesse mudado.

**A suíte inteira não foi rodada de uma vez, e a razão é medida, não
preguiça.** `bats -j 6 tests/` trava: `tests/cairn-parallel.bats` exercita um
script que roda suítes, então `-j` nos dois níveis é recursivo. As rodadas
acima são por arquivo, em foreground, sem `head` no pipe. Um número produzido
sob contenção não é medição.

`python3 -m py_compile cairn/scripts/cairn-bookkeep.py` limpo.
`git diff --quiet HEAD -- .planning/{ROADMAP,REQUIREMENTS,STATE}.md` sai 0 —
este plano **não** rodou o comando contra este repositório.

## Deviations from Plan

### 1. [Rule 1 — bug no plano] As linhas de `AUTO-05` e `AUTO-06` não podem ser escritas, e o plano pedia que fossem

- **Encontrado em:** Task 1, ao escrever a inserção.
- **O que o plano dizia:** "as linhas de `AUTO-05` e `AUTO-06` existem na tabela
  com `Phase 29 | Pending`".
- **O defeito:** a célula do meio de uma linha nova precisa de uma fase, e a
  única fonte legível disso é a linha `**Requirements**:` da fase. Medido: nem
  `AUTO-05` nem `AUTO-06` aparecem em linha de requisitos de fase nenhuma —
  porque a da fase 29 é a reticência, e o `REQUIREMENTS.md` não nomeia fase. A
  única maneira de escrever `Phase 29` ali é inferir do padrão que as outras
  linhas `AUTO-*` formam. **Isso é expandir a reticência com passos a mais**, e
  é exatamente o que o 29-01 se recusou a fazer com os ids.
- **Conserto:** a linha não é escrita. `coverage-row-missing` fica em
  `unresolved` com `blocked_by` nomeando a causa e as fases cuja linha de
  requisitos é ilegível. **E a inserção é provada assim mesmo**: um teste
  escreve os oito ids na linha (a única edição que sobra para uma mão) e então
  as duas linhas aparecem, agrupadas com a Phase 29, na ordem de planejamento,
  e o rodapé passa a `35 requisitos, 35 mapeados.` — o que prova a inserção
  **e** que ela estava barrada pela legibilidade, não quebrada.
- **Quebra que a guarda:** a #5 acima (fase adivinhada pelo prefixo) — 6
  vermelhos.

### 2. [Rule 1 — bug no plano] `disagreements` vazio depois do `--apply` seria mentira, e o próprio plano diz por quê

- **Encontrado em:** Task 1.
- **O que o plano dizia:** "`reconcile --apply` e depois `reconcile --json`:
  `disagreements` vazio, exit 0."
- **O defeito:** o mesmo plano, duas seções abaixo, exige que
  `last_activity_desc` **continue** sendo nomeado em `disagreements[]` e que a
  reticência **nunca** seja expandida. As duas afirmações não podem ser
  verdadeiras juntas. Vazio só seria alcançável escrevendo o que o comando
  declara que não escreve.
- **Conserto:** o teste afirma o **conjunto exato** que sobra —
  `coverage-row-missing/AUTO-05`, `coverage-row-missing/AUTO-06`,
  `requirements-line-unreadable/Phase 29`,
  `state-narrative-stale/last_activity_desc`. É uma asserção mais forte que
  "vazio": uma contagem sozinha passaria por um comando que resolvesse os
  errados.

### 3. [Rule 2 — correção à regra 4 do 29-01] O rodapé afirma dois números, não o mesmo duas vezes

- **Encontrado em:** Task 1, ao escrever o valor novo.
- **O defeito:** `N requisitos, N mapeados` lido como "linhas da tabela, linhas
  da tabela" produz um rodapé auto-consistente **por construção** — ele nunca
  pode contradizer o `REQUIREMENTS.md`, e um número que não pode estar errado
  não é checagem. Pior: faria este comando **escrever** `33 requisitos` num
  arquivo cuja seção de requisitos tem 35. Escrever número falso
  automaticamente é a versão automatizada do defeito que a fase existe para
  remover.
- **Conserto:** `35 requisitos, 33 mapeados.` — quantos existem, quantos a
  tabela mapeia. O rodapé passa a dizer onde está o buraco. O teste do 29-01
  continua verde porque ele afirmava só a contagem do achado, não os valores.
- **Quebra que a guarda:** a #2 acima — 4 vermelhos.

### 4. [Discretion] A regra de mão única, que o plano não cobria

O plano descrevia marcar (`[ ]` → `[x]`, `Pending` → `Complete`) e nunca disse
o que fazer na direção inversa. Uma vista **adiantada** da sua autoridade (um
requisito marcado com uma fase ainda aberta, um plano marcado sem SUMMARY, uma
linha `Complete` sob fase aberta) é reportada como `*-ahead` e **não** é
escrita. Razão: marcar completo é corroborado por um artefato que existe;
desmarcar afirma uma **ausência**, e ausência tem muitas causas — branch não
mesclada, rename, fase dividida. Um bookkeeper que pode descompletar trabalho
de alguém em silêncio é pior que um que não consegue terminar.

### 5. [Discretion] `--no-tracker` nos testes de cirurgia, e o motivo escrito no cabeçalho

A Task 2 fez `close --apply` recusar sem `bd`. Os 20 testes de cirurgia da
Task 1 rodam sobre fixtures sem banco bd, então passaram a levar
`--no-tracker`. Não é enfraquecimento: a afirmação deles é sobre a edição de
linha, e `--no-tracker` é o nome exato dessa metade. O cabeçalho do `.bats`
explica isso, e a metade do tracker tem testes próprios com `require_bd`.

### 6. [Discretion] O `help.md` registra um script, não um comando de barra

Não criei `/cairn:bookkeep`. A página fica em `cairn/docs/commands/bookkeep.md`
como o plano pediu, e a primeira linha dela diz que documenta um **script**. O
`help.md` o registra sob LOOP com o caminho da página. Um comando de barra novo
com prosa que nenhum teste dirige é o tipo de coisa que esta fase desconfia.

### 7. [menor] O `docs/commands/autonomous.md` também mentia, e o plano não o listava

A varredura pedida era em `cairn/commands/` e `cairn/skills/`. Rodando-a também
em `cairn/docs/`, a linha 110 do `docs/commands/autonomous.md` afirmava que os
três arquivos são escritos "**via GSD**" — o caminho que a D-01 mediu como
corrompido. Corrigido para nomear o script. A página é contrato: a
`cairn-parallel-autonomous.bats` já a lê como tal.

## Decisões não cobertas pelo plano

1. **`CAIRN_NOW` valida antes de escrever.** Um valor que não começa com
   `YYYY-MM-DD` é exit 2, não uma data lixo em três arquivos.
2. **Idempotência do sufixo é por presença, nunca por data.** Um teste roda a
   segunda passada com `CAIRN_NOW` de outro ano: sem isso, todo ciclo autônomo
   penduraria mais um `— completed`.
3. **A aritmética mora num lugar só.** `carriers_of`, `derive_complete` e
   `compute_counters` são chamados pelo leitor **e** pelo escritor. Duas cópias
   da mesma conta que podem divergir é a doença deste milestone.
4. **Dois rodapés dentro da seção é exit 2 nomeando os dois** — a mesma postura
   que a âncora de fase já tinha, e o contrário de "pega o primeiro".
5. **O commit usa pathspec explícito nas duas chamadas** (`git add -- <paths>`
   e `git commit -m … -- <paths>`), então nem um índice sujo alarga o escopo. O
   teste do arquivo não relacionado prova isso.
6. **A raiz do projeto é o pai do `--planning-dir`.** Uma segunda flag poderia
   apontar para outro repositório; uma não pode.

## Known Stubs

Nenhum. Todo caminho de código tem teste, e todo teste tem uma quebra nomeada
que o deixa vermelho.

## Threat Flags

Nenhuma superfície de rede nova. Duas superfícies novas de escrita, ambas com
teste:

- **`git commit` disparado por script** (T-29-13): default `false`, pathspec
  explícito nas duas chamadas, e um teste que põe um arquivo sujo não
  relacionado no índice e confirma que ele não entra no commit.
- **escrita parcial se o `bd` sumir** (T-29-11): checagem antes da primeira
  escrita, exit 5, sha256 dos três arquivos idêntico — provado com um `PATH`
  stub que o próprio teste verifica não alcançar o `bd`.

## Não executado, e por quê

`state advance-plan`, `state update-progress`, `state record-metric`,
`state add-decision`, `state record-session`, `roadmap update-plan-progress` e
`requirements mark-complete` **não** foram rodadas, pela mesma razão dos planos
29-01 e 29-03: todas escrevem exatamente nos três arquivos que este plano
proíbe tocar (`<objective>`: "Tocar `.planning/ROADMAP.md`,
`.planning/REQUIREMENTS.md` ou `.planning/STATE.md` por Edit. Se este plano os
editar à mão, ele desmente a própria tese"), e pelo caminho que a D-01 mediu
como corrompido.

**`--apply` não foi rodado contra este repositório.** O plano é explícito:
"Consertar `.planning/*` deste repo… é ato do fechamento desta fase, não deste
plano". O comando existe, é testado contra a cópia congelada desse mesmo
estado, e quem fechar a fase 29 roda:

```bash
bash cairn/scripts/cairn-bookkeep.sh close 29 --apply
```

O que ele encontraria hoje, medido em modo leitura agora
(`reconcile --json`, 13 discordâncias): `footer-count-stale [29,29] → [35,33]`,
`requirement-checkbox-stale BOARD-01`, cinco `plan-checkbox-stale` (20-01…03,
29-01, 29-03), `state-counter-stale` em `total_plans` (3→10) e
`completed_plans` (3→5), mais as três que ele nomeia sem resolver.

O commit de metadados leva **apenas** o `29-02-SUMMARY.md`.

## Self-Check: PASSED

- `cairn/docs/commands/bookkeep.md` existe no disco; os outros seis arquivos
  declarados existem e estão modificados no histórico.
- Commits `9680718`, `7e05550`, `54d2880` presentes em `git log`.
- `git status --short` vazio; `git diff --quiet HEAD` nos três arquivos de
  planejamento sai 0.
- `python3 -m py_compile` limpo.

---
*Phase: 29-nothing-mechanical-stays-manual*
*Completed: 2026-08-04*
