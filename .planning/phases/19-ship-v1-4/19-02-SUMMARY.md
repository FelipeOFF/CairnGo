---
phase: 19-ship-v1-4
plan: "02"
subsystem: release
tags: [changelog, versioning, semver, release-notes, migration]
requires:
  - "o comando de verificação entregue pelo plano 19-01 (cairn-release.sh check), usado como prova nas duas direções"
  - "o conserto do gitignore do plano 19-03, que é o conteúdo real da subseção ### Upgrading"
provides:
  - "a seção `## [1.5.0] - 2026-08-01` do CHANGELOG, em inglês e em termos de quem usa o plugin"
  - "a subseção `### Upgrading`, ponto de extração estável para as notas derivadas do plano 19-04"
  - "plugin.json e marketplace.json em 1.5.0 — os três portadores em lockstep concordam e a verificação sai 0"
affects:
  - "plano 19-04: as notas de release são extraídas desta seção; a data 2026-08-01 tem que bater com a tag anotada"
  - "quem consome `cairn-release.sh check --json`: `version` passa de 1.4.2 para 1.5.0 e a tag fica `pending`"
tech-stack:
  added: []
  patterns:
    - "a divergência intermediária como prova: CHANGELOG bumpado antes dos manifestos faz a verificação sair 6 nomeando os dois lados"
    - "`### Upgrading` como subseção própria — as seis categorias do Keep a Changelog classificam mudanças, não instruções de migração"
key-files:
  created:
    - .planning/phases/19-ship-v1-4/19-02-SUMMARY.md
  modified:
    - CHANGELOG.md
    - cairn/.claude-plugin/plugin.json
    - .claude-plugin/marketplace.json
decisions:
  - "D-01 aplicada: 1.5.0 nos dois portadores em lockstep; capability.json intocado em 1.0.0 (D-02)"
  - "A subseção `### Upgrading` foi criada, e não enterrada em `### Fixed` — o leitor que veio atrás dela não teria como achá-la"
  - "O comando de detecção é `git status --porcelain -uall .cairn`, e o `-uall` é explicado no texto: sem ele o git colapsa o diretório inteiro numa linha e a resposta some"
  - "Acrescentado ao texto de migração o passo que a D-03 não previa: `git rm --cached` para quem já commitou um arquivo gerado — o gitignore sozinho não destrackeia"
  - "Uma frase de tema abre a seção, coisa que as três seções 1.4.x não têm — seis entradas sem orientação inicial obrigam o leitor a montar o tema sozinho"
  - "ACHADO não corrigido: o campo `status` por portador no `--json` da verificação é 'concorda com o primeiro portador legível', não 'está certo' (ver Deviations) — virou issue de backlog no checkpoint"
  - "CORREÇÃO no checkpoint (commit do Felipe): a latência de detecção de holder morto que eu escrevi não existia no código; a entrada passa a nomear os dois caminhos reais (ver 'A correção do checkpoint')"
metrics:
  duration: ~95min
  completed: 2026-08-01
  tasks: 3
  commits: 4 meus + 1 de correção do Felipe
actuals:
  tokens: 1700
  tasks: 3
  commits: 4
status: complete
---

# Phase 19 Plan 02: A seção 1.5.0 e o bump em lockstep Summary

**O CHANGELOG ganhou uma seção `## [1.5.0]` escrita para quem nunca abriu este repositório — seis ganhos sob `### Added`, o buraco do gitignore sob `### Fixed` descrito pelos três sintomas que o usuário vê, e um `### Upgrading` que responde "fui afetado?" com um comando cujo silêncio significa não — e os dois portadores em lockstep foram para 1.5.0, com a verificação do plano 19-01 saindo 6 antes do bump e 0 depois.**

## O que foi construído

### Task 1 — a seção (commit `f0e9a5a`, reflow em `daedd81`)

118 linhas, em inglês, acima da seção 1.4.2. A voz é a das três 1.4.x: cada entrada abre por uma frase em negrito que nomeia o que estava errado ou o que passa a ser possível, e só depois explica.

As seis entradas de `### Added`, uma por fase entregue, traduzidas para o que o leitor ganha:

| entrada | o gancho em negrito |
|---|---|
| corroboração | "A phase's state is no longer a guess made from which files happen to exist." |
| card | "The board says what each phase is for, how far it got, and what to run next." |
| lease | "Two agents on the same phase is prevented before the work starts, not discovered halfway through it." |
| journal | "A local, append-only record of what actually happened, which survives a crash." |
| escalação | "When the sources disagree, you can commission an investigation instead of picking a side." |
| paralelismo | "Independent phases now genuinely run at the same time." |

Vocabulário substituído deliberadamente, porque os nomes internos não significam nada fora daqui: *lease* virou **hold**, *journal* virou **a local, append-only record**, *corroboration* virou **four sources state their claim independently**. O que ficou nomeado é o que o usuário digita — `/cairn:status`, `/cairn:work N`, `/cairn:reconcile N`, `/cairn:doctor --apply-reconciliation N`, `/cairn:autonomous`, `--max`, `--sequential`, `--json`.

`### Fixed` descreve o conserto do 19-03 por sintoma, não pelo array: `git status` que nunca volta limpo, um caminho absoluto de máquina a um `git add .` de ser publicado, e a worktree preparada que nunca parecia removível — e por isso nunca era removida. A frase final explica por que a regra nomeia arquivo por arquivo em vez de ignorar o diretório: `sync.json` e `context.json` continuam visíveis ao git (citados como "your sync and context configuration", sem nome de arquivo).

`### Upgrading` na ordem que o plano pede: nada muda no projeto; rode `git status --porcelain -uall .cairn` para saber; se listar algo, rode `/cairn:init` de novo (idempotente, no-op se já estiver certo); e o que **não** é preciso fazer, dito explicitamente — sem migração de dados, sem mudança de configuração, sem quebra de compatibilidade, `.planning/` e `.beads/` intocados, argumentos de comando preservados.

### Task 2 — o bump (commit `1ca8e03`)

```
cairn/.claude-plugin/plugin.json   .version           1.4.2 -> 1.5.0
.claude-plugin/marketplace.json    .metadata.version  1.4.2 -> 1.5.0
cairn/capability/capability.json   .version           1.0.0 (intocado, D-02)
```

`git diff --numstat` soma 4 (uma linha alterada por arquivo): nenhum reformat escondido no diff da release.

## A divergência intermediária, medida

A ordem das tasks não é arbitrária — a Task 1 proíbe tocar nos manifestos justamente para que a verificação tenha o que detectar:

```
$ bash cairn/scripts/cairn-release.sh check          # depois da Task 1, antes da Task 2
[cairn-release] 1 finding(s):
  mismatch: cairn/.claude-plugin/plugin.json ('version') = '1.4.2'
            but CHANGELOG.md ('## [x.y.z] heading') = '1.5.0'
exit=6

$ bash cairn/scripts/cairn-release.sh check          # depois da Task 2
[cairn-release] ok — version 1.5.0 in cairn/.claude-plugin/plugin.json,
  .claude-plugin/marketplace.json, CHANGELOG.md; git tag v1.5.0 pending
  (not created yet); capability 1.0.0 on its own axis (valid semver, D-02)
exit=0
```

A tag ausente aparece como `pending`, não como falha — é o estado correto antes do plano 19-04, e é a regra que o teste 11 do 19-01 prende.

## Verificações

| verificação | resultado |
|---|---|
| cabeçalho `^## \[1\.5\.0\] - AAAA-MM-DD$` | ok |
| `### Upgrading` presente na seção | ok |
| nenhum id de requisito (`CORR\|CARD\|LEASE\|JOUR\|ESC\|PAR\|REL`-N) | grep sai 1, limpo |
| nenhum `phase 13..18` (case-insensitive) | grep sai 1, limpo |
| `.ok == false` antes do bump / `.ok == true` depois | os dois confirmados |
| `.version == "1.5.0"` nos dois manifestos, `1.0.0` no capability | os três `jq -e` verdes |
| `numstat` dos dois manifestos ≤ 4 | 4 |
| `bats tests/cairn-release.bats` | 14/14 |
| `bats tests/cairn-doctor.bats` | 60/60 |
| largura de linha ≤ 80 (a casa) | max 80, nenhuma trailing whitespace |

Todas as verificações de texto e o `check` foram **repetidos depois** da correção do checkpoint (seção abaixo): 119 linhas, max 80 caracteres, os quatro greps limpos, `check` em 0.

## A correção do checkpoint — a frase que afirmava mais do que o código faz

**Task 3 aprovada com uma correção, aplicada e commitada pelo Felipe (`baa961e`).** A entrada do hold terminava assim, escrita por mim:

> *a holder that is no longer a live worktree is visible **within a minute of the crash** rather than after a timeout expires*

Nenhuma das duas metades sobrevive à medição, e eu confirmei as duas de forma independente antes de fechar:

| alegação | medição |
|---|---|
| "after a timeout expires" para o doctor | `cairn-lease.py:168` — `LEASE_TTL_SECONDS = 4 * 60 * 60`; `check_lease_stale` (`cairn-doctor.py:1463`) faz shell em `cairn-lease.py status --all --json` e **não re-deriva nenhuma matemática de TTL**. O caminho do doctor espera 4 horas. |
| "within a minute" para o outro caminho | o caminho que não espera **não é temporal**: o `cleanup` do `cairn-parallel` classifica `orphan_lease` comparando o holder, realpath'd, com `git worktree list` (`cairn-parallel.py:338, 355`). Ele vê o holder morto no instante em que é chamado. |

Texto novo, que nomeia os dois caminhos pelo que cada um faz: *"`/cairn:doctor` reports it stale once its four-hour heartbeat lapses, and the cleanup that runs alongside concurrent phases spots it without waiting at all, by checking the holder against the worktrees that actually exist."*

**De onde veio o erro, porque isso importa mais que o erro:** peguei "no minuto seguinte à morte" da frase de abertura do `18-03-SUMMARY.md` e traduzi sem medir. O SUMMARY de outra fase é laudo, não medição — e a regra é reproduzir a medição antes de repetir o número, principalmente quando ele vai para texto público. Numa release cujo assunto inteiro é sinal que afirma mais do que prova, publicar uma latência que ninguém cronometrou seria a própria mentira verde do milestone, dentro do artefato que a anuncia.

## Deviations from Plan

### 1. [Rule 2 — instrução de migração incompleta] o gitignore sozinho não destrackeia

**Encontrado em:** Task 1, escrevendo o `### Upgrading`.

O plano (e a D-03) descrevem a migração como "rode `/cairn:init` de novo". Isso resolve quem tem o arquivo **não rastreado**. Quem já commitou um dos arquivos gerados — o caso mais grave é `.cairn/plugin-root`, que carrega o caminho absoluto da máquina e que o 19-03 identificou — continua com ele no índice depois do init, porque `.gitignore` não afeta arquivo já rastreado. Acrescentei a frase final: *"if that includes one of these generated files, drop it with `git rm --cached` once the rules are in place."* Sem ela, a nota de migração seria verdadeira e ainda assim deixaria o vazamento de path publicado no lugar.

### 2. [decisão de escrita, não prevista no plano] uma frase de tema antes de `### Added`

As três seções 1.4.x começam direto no `### Added`, e cada uma tem uma ou duas entradas. Esta tem sete. Abri com uma linha — *"cairn stops inferring that a phase is done and starts reporting what each of its sources actually claims"* — porque seis entradas soltas obrigam o leitor a montar o tema sozinho, e essa linha é também o resumo que as notas do 19-04 vão querer no topo. É desvio de forma em relação às seções vizinhas; registro aqui porque é decisão minha, não do plano.

### 3. [terceiro commit não previsto] reflow para 80 colunas

O texto saiu com nove linhas em 81 colunas e uma em 82; todas as seções de 1.3.0 para baixo param em 80. O commit `daedd81` é reflow puro (nenhuma palavra acrescentada, removida ou reordenada; só quebra de linha, e o comando `/cairn:doctor --apply-reconciliation N` puxado para uma linha só em vez de partido no meio das crases). Preferi um terceiro commit a reescrever o `f0e9a5a`, que já tinha o bump em cima.

## Achados sobre a verificação do plano 19-01 (não corrigidos aqui)

**O campo `status` por portador no `--json` quer dizer "concorda com o primeiro portador legível", não "está correto".** Com o CHANGELOG em 1.5.0 e os manifestos em 1.4.2, a saída foi:

```json
{"name": "marketplace", "value": "1.4.2", "status": "ok"},
{"name": "changelog",   "value": "1.5.0", "status": "mismatch"}
```

O `marketplace` recebeu `ok` **carregando a versão velha**, e o `changelog` — o único já correto — foi marcado `mismatch`. A causa está em `cairn-release.py:249-265`: as comparações são feitas contra `present[0]`, que é o `plugin.json`, e a escolha é documentada e deliberada (cada finding nomeia dois caminhos, duas chaves e dois valores, em vez de dizer só "as versões diferem"). O veredito de topo (`ok: false`), o texto do finding e o exit 6 estão todos corretos, então **o portão não mente**. O que pode enganar é um consumidor do JSON que filtre `status == "mismatch"` para saber o que consertar: ele seria mandado ao arquivo já certo e informado de que o desatualizado está bem.

Não corrigi: está fora do escopo deste plano, os testes do 19-01 fixam o comportamento atual, e a decisão de anexar em `present[0]` foi tomada com razão declarada. Fica como candidato — um `status` derivado do valor majoritário, ou renomeado para `agrees_with_reference`, resolveria sem tocar no texto dos findings.

**Destino:** registrado como issue de backlog no checkpoint, com a medição inteira. Não é bloqueio para o 19-04.

## O que o plano acertou e vale citar

- **Mandar escrever a seção antes do bump.** É o único jeito de a divergência intermediária existir para ser detectada; se as duas tasks fossem um commit só, o `exit 6` nunca teria sido observado e a metade "verificada" do REL-02 seria afirmação, não medição.
- **Proibir número de fase por grep.** A tentação de escrever "phases 13–18 delivered" é real e teria passado despercebida numa revisão de prosa.
- **Nomear `metadata.version` como aninhado.** O caminho não está onde a intuição procura, que é exatamente por que ele carregou 1.4.2 por três releases.

## Known Stubs

Nenhum.

## Threat Flags

Nenhuma superfície nova. Do registro do plano: T-19-06 mitigada pelos `jq -e` e pelo `numstat` (4, sem reformat); T-19-08 pelos dois greps negativos; T-19-09 pela verificação saindo 0 com os três portadores concordando.

**T-19-07 (a seção divergindo do que foi entregue) foi a que pagou.** É a ameaça que o checkpoint humano bloqueante existe para pegar, e ela pegou: a leitura a frio derrubou uma latência de detecção que nenhum grep, nenhum teste e nenhum `jq` teria questionado, porque a frase era gramatical, plausível e sobre código que existe. Registro isso como evidência a favor do gate, não como nota de rodapé — um checkpoint que nunca reprova nada não é um checkpoint.

## Estado do plano

As três tasks fechadas. **Task 3 aprovada pelo Felipe na leitura a frio, com uma correção que ele aplicou e commitou (`baa961e`)** antes da aprovação — a qualidade da prosa não é testável por comando, e o que o comando não pega foi exatamente o que o gate pegou. Nada foi feito de `.planning/STATE.md`, `ROADMAP.md` ou `REQUIREMENTS.md` por instrução explícita (o Felipe reconcilia no fim da fase), nenhuma tag foi criada e nada saiu da máquina. O 19-04 pode extrair a seção como está.

## Self-Check: PASSED

- `CHANGELOG.md` — FOUND (seção 1.5.0 com `### Added`, `### Fixed`, `### Upgrading`, 119 linhas após a correção)
- `cairn/.claude-plugin/plugin.json` — FOUND (1.5.0)
- `.claude-plugin/marketplace.json` — FOUND (`metadata.version` 1.5.0)
- `cairn/capability/capability.json` — FOUND (1.0.0, intocado)
- commit `f0e9a5a` — FOUND (a seção)
- commit `1ca8e03` — FOUND (o bump)
- commit `daedd81` — FOUND (o reflow)
- commit `a0f3370` — FOUND (este SUMMARY, primeira versão)
- commit `baa961e` — FOUND (a correção da latência, pelo Felipe no checkpoint)
- verificações repetidas após `baa961e`: 4 greps limpos, `check` em 0, max 80 colunas
