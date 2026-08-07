---
phase: 29-nothing-mechanical-stays-manual
verified: 2026-08-06T21:20:07Z
status: gaps_found
score: 6/7 critérios verificados, 8/8 requisitos entregues
behavior_unverified: 0
behavior_unverified_items: []
human_verification:
  - test: "Rodar `/cairn:config` num repo real e responder o lote de AskUserQuestion nas três seções"
    expected: "Uma pergunta só, valor corrente pré-selecionado em cada chave, e o `.cairn/config.json` gravado com o que foi escolhido"
    why_human: "A porta da pergunta é prosa executada por agente (cairn/commands/config.md), não código — o bats prova a porta do `set` e o ponto de consumo, nunca a apresentação da pergunta"
  - test: "Rodar `/cairn:sync-config` num repo com chave `ABC-123` em nome de branch"
    expected: "O cairn MOSTRA as amostras que achou (branches e assuntos de commit) antes de perguntar, pergunta uma vez, e não pede chave nem credencial"
    why_human: "O mecanismo (detectar, rotear por reason literal, gravar sim e não) tem 14 testes verdes; o que nenhum teste alcança é se a pergunta de fato exibe a evidência em vez de decretar"
overrides_applied: 0
gaps:
  - truth: "A cadeia do ledger de PLANOS não tem leitor independente — o contador que o cairn-bookkeep escreve no STATE.md é aritmeticamente impossível, e o reconcile da própria ferramenta certifica zero discordâncias sobre ele"
    status: partial
    reason: >-
      A fase construiu o `req-ledger` (AUTO-07) para a cadeia de REQUISITOS e deixou
      a cadeia de PLANOS sem checagem nenhuma. Medido por mim em 2026-08-06 no
      próprio repositório: `.planning/STATE.md` carrega `total_plans: 28` e
      `completed_plans: 33` — completo MAIOR que o total. Contado no disco:
      28 `NN-MM-PLAN.md`, 28 `NN-MM-SUMMARY.md` de plano e 5 `NN-SUMMARY.md` de
      fase; 33 = 28 + 5. A causa é `cairn-bookkeep.py:1018`, que globa
      `*-SUMMARY.md` (casa summary de plano E de fase) contra o par assimétrico
      `*-PLAN.md` (só casa plano, porque fase não tem `NN-PLAN.md`), e a linha 1087
      soma `len(summaries)` como `completed_plans`. O agravante é o que pertence a
      esta fase: `cairn-bookkeep.sh reconcile --json` devolve `disagreements: []`
      exibindo `computed.total_plans: 28` e `computed.completed_plans: 33` no MESMO
      objeto — escritor e verificador computam com a mesma regra errada, então
      concordam. É a doença que a fase existe para remover, dentro da cura.
      A fixture congelada não pode ver o defeito por construção: `make_drift_fixture`
      (tests/helpers.bash) só gera `NN-<idx>-SUMMARY.md` a partir de `phases.tsv` e
      nunca cria um `NN-SUMMARY.md` de fase. O teste que o critério 1 exige roda o
      ciclo inteiro contra uma árvore incapaz de expor o erro.
      Registrado em `CairnGo-6bx` [P1] com label `phase-25` — mas a seção Phase 25 do
      ROADMAP não nomeia este defeito em nenhum requisito (FIX-01..FIX-05, AUTO-10)
      nem em nenhum critério de sucesso, então o contrato do roadmap não o difere.
    artifacts:
      - path: "cairn/scripts/cairn-bookkeep.py:1018"
        issue: "glob `*-SUMMARY.md` casa summary de fase; o par `*-PLAN.md` não. A assimetria está DOCUMENTADA no docstring da linha ~166 e a consequência não foi percebida"
      - path: "cairn/scripts/cairn-bookkeep.py:1087"
        issue: "`completed_plans` = len(summaries), herdando o glob errado — e `percent` sai inflado junto"
      - path: "tests/helpers.bash (make_drift_fixture)"
        issue: "reconstrói a árvore de fases a partir de phases.tsv sem jamais criar um `NN-SUMMARY.md` de fase; a fixture é cega ao defeito por construção"
      - path: ".planning/STATE.md:15-16"
        issue: "estado vivo no repositório hoje: total_plans 28, completed_plans 33"
      - path: ".planning/ROADMAP.md:672"
        issue: "`**Plans:** 6/7 plans executed` com os 7 checkboxes marcados logo abaixo. Escrito pelo gsd-tools no fecho do 29-04 (commit 49e2b45); `grep` em cairn-bookkeep.py não acha leitor nem escritor desta linha, e o req-ledger não a cobre"
    missing:
      - "Separar os dois globs por forma de nome: `[0-9]*-[0-9]*-SUMMARY.md` para summary de plano, e contar `NN-SUMMARY.md` de fase à parte (ou não contar)"
      - "Um elo de ledger de planos no `req-ledger` (ou checagem irmã) que reprove `completed_plans > total_plans` — hoje nada, independente do escritor, valida esse par"
      - "Estender `make_drift_fixture`/`phases.tsv` com uma quinta coluna para o `NN-SUMMARY.md` de fase, para que a fixture consiga reproduzir o defeito antes do conserto"
      - "Dono declarado para `**Plans:** N/M plans executed` no ROADMAP: ou o cairn-bookkeep passa a escrevê-la no close, ou ela sai"
      - "Carregar `CairnGo-6bx` para o contrato do ROADMAP (requisito ou critério da fase 25); hoje só o label do bd o difere"
---

# Fase 29: Nothing mechanical stays manual — Relatório de verificação

**Objetivo da fase:** o que é mecânica pura e não tem regra de negócio dentro para
de ser feito à mão — marcar fase, marcar requisitos, mexer contadores, regenerar
mapa, liberar lease, configurar Jira, rodar a suíte em paralelo — sem nunca cruzar
a linha do `/groom-me`.

**Verificado:** 2026-08-06, sobre `main` em `6545a5c` + os fechos posteriores
**Status:** gaps_found
**Re-verificação:** Não — verificação inicial
**Modo:** goal-backward. Os sete `-SUMMARY.md` foram lidos como afirmação, não como
prova; toda medição abaixo foi refeita por mim contra o código, os testes e o
estado atual do repositório.

---

## O que foi executado nesta sessão

126 testes, 0 falhas, três suítes com exit 0 — somente os `.bats` da fase, via
`cairn-test.sh --jobs 3`, lidos de log em arquivo:

| Suíte | Testes | Exit |
| ----- | ------ | ---- |
| `tests/cairn-bookkeep.bats` | 50 | 0 |
| `tests/cairn-config.bats` + `tests/cairn-test.bats` + `tests/cairn-jira.bats` | 57 | 0 |
| `tests/cairn-tracker-card.bats` | 19 | 0 |

Além dos testes, seis medições ao vivo contra este repositório, todas em modo
leitura (`git status` limpo depois de cada uma):

- `cairn-bookkeep.sh close 29` (sem `--apply`)
- `cairn-bookkeep.sh reconcile --json`
- `cairn-config.sh list --json`
- `cairn-test.sh --check-env` e `--print-command`
- `cairn-doctor.sh` (texto e exit code)
- contagem própria de `*-PLAN.md` / `*-SUMMARY.md` por diretório de fase

Nenhuma ferramenta de escrituração do gsd-tools foi executada. Nada foi consertado.

---

## Critérios de sucesso (o padrão desta fase, vindos do ROADMAP)

### CS1 — Fechar uma fase é um comando, idempotente, com teste de ciclo inteiro contra fixture ⚠️ PARCIAL

**O que está entregue, e eu confirmei cada peça:**

`cairn/scripts/cairn-bookkeep.py` (76 KB) + `.sh` existem e são executáveis.
`close <N> --apply` faz as seis edições, regenera o mapa e libera o lease numa
invocação — teste `close --apply: the map is regenerated and the lease released`
(linha 958) verde.

**A prova de ponta a ponta está registrada e é reproduzível.** O commit `6545a5c`
é o primeiro uso real contra o próprio repositório, e a comparação que ele afirma
eu remedi no diff:

| Caminho | ROADMAP.md | linhas em branco injetadas |
| ------- | ---------- | -------------------------- |
| gsd-tools (fecho do 29-04) | +43/−7 para cinco checkboxes | 29 |
| cairn-bookkeep (`6545a5c`) | +30/−16 | **2 adicionadas, 1 removida** |

As −16 são exatamente as 16 edições cirúrgicas que a mensagem de commit afirma; as
+30 são essas 16 mais 14 inserções legítimas (as linhas de cobertura de AUTO-05 e
AUTO-06 que destravaram, e o rodapé). O contraste central — reflow do `_normalizeMd`
contra cirurgia de linha — está medido e confere.

**Idempotência, medida agora e não lida do SUMMARY:** `close 29` em modo leitura,
hoje, não propõe uma única edição de fase, requisito, tabela ou rodapé. As três
edições que ele propõe (`current_phase`, `current_phase_name`, `last_updated`) são
consequência do fecho da fase 22 que aconteceu depois, não da 29. O teste
`close --apply twice: the second run writes nothing, by sha AND mtime` (linha 742)
prova o mesmo por dois canais — e prova por mtime, não só por sha, porque uma
reescrita byte-idêntica passa pelo sha e continua sendo escrita.

**"Nenhuma edição manual sobrevive nos comandos":** `autonomous.md:274` invoca
`cairn-bookkeep.sh close <N> --apply`, e o teste `no cairn command instructs a hand
edit of the three planning files` (linha 1197) é a guarda estrutural, com o par
negativo `autonomous: no hand edit survives inside that step` (linha 1169).

**Por que PARCIAL, e é a parte que exige julgamento escrito.**

O critério inclui "atualiza os contadores do STATE". Ele atualiza. Hoje, os
contadores que ele escreveu dizem `total_plans: 28` e `completed_plans: 33` —
completo maior que o total. A causa e a medição estão no bloco `gaps` acima.

**A distinção que faço, e faço por escrito porque ela decide o veredito:**

- **AUTO-01 pela letra está entregue.** O requisito diz que o bookkeeping é *um
  comando* e que nenhuma daquelas edições volta a ser feita à mão. É um comando, é
  idempotente, foi provado contra o repositório real, e nenhum comando do cairn
  instrui edição à mão. O requisito não diz que o comando está correto.
- **O critério 1 pela letra também está entregue**, no sentido literal de que existe
  um teste que roda o ciclo inteiro contra a fixture e compara com o esperado.
- **O que falha é o critério 1 contra o objetivo da fase**, e é isto: o "resultado
  esperado" contra o qual o teste compara foi computado pela mesma regra que está
  sob teste, e a fixture é *estruturalmente incapaz* de produzir a forma de nome que
  quebra a regra. `make_drift_fixture` gera apenas `NN-<idx>-SUMMARY.md`. Nenhum
  `NN-SUMMARY.md` de fase existe em fixture alguma. O defeito não passou pelo teste:
  ele nunca chegou perto do teste.

E o agravante que o torna desta fase e não de outra: `reconcile` é vendido no
29-01-SUMMARY como "the full read-only disagreement inventory". Ele devolve
`disagreements: []` exibindo `computed.total_plans: 28` e
`computed.completed_plans: 33` no mesmo objeto JSON. Um verificador que imprime um
par impossível e o declara concordante é verde falso — a espécie exata que o
critério 7 proíbe para o doctor e que o critério 5 chama de "uma checagem que não
existe". A fase removeu essa doença da cadeia de requisitos e a deixou de pé na
cadeia de planos.

**Segunda superfície, mesma raiz:** `.planning/ROADMAP.md:672` afirma
`**Plans:** 6/7 plans executed` com os sete checkboxes `[x]` logo abaixo. Escrita
pelo gsd-tools no fecho do 29-04; `grep` em `cairn-bookkeep.py` não encontra leitor
nem escritor dessa linha, e o `req-ledger` não a cobre. É "um campo que ninguém
recalcula e ninguém reporta" — que o próprio docstring do `cairn-bookkeep.py`
identifica como "exatamente como o rodapé de cobertura chegou a 29".

**Sobre a deferência:** `CairnGo-6bx` está aberta com label `phase-25`. Apliquei o
teste conservador de deferência da fase 25: nem os requisitos (FIX-01..FIX-05,
AUTO-10) nem os cinco critérios de sucesso da Phase 25 nomeiam este defeito. FIX-05
é o parente mais próximo ("uma fase com um plano de três executados para de ler como
`executed`") e trata de detecção de fase executada, não do contador. O label do bd
não é o contrato; o ROADMAP é. **Não difiro.**

### CS2 — Jira detectado, confirmado, e então configurado pelo cairn ✓ VERIFICADO

`cairn/scripts/cairn-jira.py` (21 KB) + `.sh`, 14 testes verdes (44–57):

- `a repo with no signal at all is never asked` — o "jamais perguntado sem sinal".
- `a key only in commit messages is still not enough to be asked` — o sinal fraco que
  não decide sozinho, medido no summary como 21/21 falsos positivos de git-log.
- `a branch carrying the key makes it ask, with evidence to ask with` — a amostra
  viaja no payload, para a pergunta mostrar em vez de decretar.
- `a recorded no is as durable as a yes` — o "não" gravado com a mesma força.
- `apply writes the jira backend with env var NAMES and no credential` e
  `apply refuses to invent a site rather than writing a placeholder` — o usuário
  nunca digita chave nem credencial, e o comando recusa em vez de inventar.
- `an Atlassian MCP server DECLARED in .mcp.json is a signal`,
  `an Atlassian server declared in ~/.claude.json IS read`,
  `claudeAiMcpEverConnected alone is NOT a declaration` e
  `a malformed .mcp.json degrades to 'not declared', never a crash` — o item de
  pesquisa do roadmap (como detectar MCP de script stdlib-only) foi respondido por
  medição, com o assumido explicitamente fora do predicado.
- `detection is not reimplemented here: no detector, exit 5, no writes` — um dono da
  regra, provado pelo avesso.

`jira.link` está no schema fechado do `cairn-config.py` com leitor nomeado
(`cairn-jira.py detect`) — confirmado ao vivo no `list --json`. `sync-config.md`
roteia por `reason` literal em quatro rotas.

A apresentação da pergunta em si é prosa de agente; vai para `human_verification`,
não porque o mecanismo esteja em dúvida, mas porque grep não vê apresentação.

### CS3 — Card do rastreador no board sem chamada de rede no caminho padrão ✓ VERIFICADO

19 testes verdes em `tests/cairn-tracker-card.bats`. O que me convenceu não foi a
existência dos tripwires, foi o **controle negativo de cada camada**:

| Camada | Prova | Controle negativo |
| ------ | ----- | ----------------- |
| socket dentro do processo | `the whole render runs under both tripwires and still prints the card` | `layer 1 is alive: an in-process socket raises under the same PYTHONPATH` |
| allowlist de PATH fora do processo | idem | `layer 2 is alive exactly where layer 1 is blind` |
| inventário estrutural por AST | `every subprocess.run in the renderer invokes an allowlisted binary` | `layer 3 is alive: a synthetic curl call site is rejected` |

Uma camada que não falha quando deveria é decoração; as três têm o seu.

Fiação confirmada no código: `TRACKER_LABEL` (`cairn-status.py:431`),
`tracker_key()` (linha 2076), `external_ref` carregado cru no modelo (linha 610) e
consumido em `make_cell` (linhas 2342-2343). O sufixo é estritamente condicional ao
dado — `every unmarked card renders the bytes it rendered before the mark` é a
suíte de invariância que prova isso em vez de afirmar.

Nota factual: este repositório não tem nenhuma linha `**Tracker:**` no ROADMAP, então
a metade de fase do recurso está provada por teste e não exercitada em produção aqui.

### CS4 — Suíte em paralelo, e a ausência detectada ANTES de invocar o bats ✓ VERIFICADO

O critério foi reescrito no meio da fase por uma medição que desfez a afirmação
original (bats 1.14.0 sem `parallel` executa **zero** testes e sai 1, em vez de
rodar serial em silêncio). O que a fase entregou responde à ameaça corrigida:

- `without GNU parallel the -j is removed BEFORE bats is invoked, and the warning
  names the cost and the fix` — a detecção acontece enquanto o comando é montado.
- `flock and shlock both missing also removes the -j` — o achado de que `bats -j`
  exige **dois** pré-requisitos, não um (macOS não tem `flock`); o plano nomeava só
  o primeiro.
- `the warning lives on stderr, so --print-command's stdout stays exactly one line`.
- `a bats that exits 5 exits 5 here too, AND the output says the 5 came from bats` —
  fronteira temporal em vez de tradução de exit code.

Medido ao vivo por mim:

```
$ cairn-test.sh --check-env
{"bats": "/opt/homebrew/bin/bats", "jobs": 8, "jobs_source": "cpu count",
 "parallel_binary": "parallel", "can_parallelize": true, "blockers": [],
 "measured_cost": "tests/cairn-map.bats takes 64s serial against 33s at -j 6 (measured 2026-08-03)"}

$ cairn-test.sh --print-command --jobs 4 tests/cairn-config.bats
/opt/homebrew/bin/bats -j 4 tests/cairn-config.bats
```

E a checagem 16 do doctor roteia esse veredito em vez de reimplementar a detecção:
`✓ test-parallel   the suite can run in parallel (bats -j 8, from cpu count)`.

Eu mesmo usei essa porta para rodar as três suítes desta verificação.

### CS5 — `req-ledger` valida a cadeia do registro de requisitos ✓ VERIFICADO

Checagem 17 do `cairn-doctor.py`, 13 testes verdes. O critério exigia que ela
**falhasse contra o estado real antes de qualquer conserto** — "se passar de
primeira, está errada". Confirmei que o código do `req-ledger` já existia em
`6545a5c~1` (13 ocorrências), e a mensagem de `6545a5c` registra a transição:

```
req-ledger  13 elos rompidos  →  every requirement-ledger link agrees
req-issue   29 mapeados       →  36 mapeados
rodapé      29 requisitos, 29 mapeados  →  36 requisitos, 36 mapeados
```

Estado hoje, medido por mim:
`✓ req-ledger  every requirement-ledger link agrees — 41 active requirement(s)
against 41 coverage row(s), 1 excluded by rule (deferred / out of scope)` e
`✓ req-issue  41 requirement(s) mapped to issues`.

O elo da reticência, que cegava duas ferramentas ao mesmo tempo, tem teste próprio:
`an elided **Requirements**: line fails, naming the phase and the ids parsed` — falha
nomeada, nunca silêncio, e o docstring documenta a recusa de expandir
`AUTO-01 … AUTO-08` em oito ids por inferência.

O cuidado que me convenceu de que a checagem não é decorativa: a allowlist de
returncode é constante nomeada `(0, 3)` com o contrato citado ao lado, e
indisponibilidade é `fail` e nunca `warn` — `an exit outside the allowlist is fail,
never warn` e `req-ledger: cairn-bookkeep.py out of place is exactly fail, and the
doctor exits 7`. Aviso não move exit code, então degradar para aviso seria aprovar
em silêncio.

Os números do critério envelheceram como previsto (33/31 → 35/33 → 41/41) e nenhum
teste carimbou os números datados.

### CS6 — Config própria do cairn, duas portas para o mesmo lugar ✓ VERIFICADO

`.cairn/config.json` com sete chaves, cada uma com **leitor nomeado** — medido ao
vivo:

| Chave | Tipo | Leitor |
| ----- | ---- | ------ |
| `agents.response_language` | str | `cairn-parallel.py prepare` |
| `autonomous.max_cycles` | int | `cairn-parallel.py batch --cycle K` |
| `autonomous.max_parallel` | int | `cairn-parallel.py batch` |
| `bookkeep.auto_commit` | bool | `cairn-bookkeep.py` |
| `jira.link` | enum | `cairn-jira.py detect` |
| `ship.pr_scope` | enum | `cairn-bookkeep.py` |
| `test.jobs` | int_or_null | `cairn-test.py` |

AUTO-06 pede nominalmente commit automático (`bookkeep.auto_commit`), PR por fase ou
milestone (`ship.pr_scope`), teto de ciclos (`autonomous.max_cycles`) e de laços do
run autônomo (`autonomous.max_parallel`) — os quatro estão lá. E o inventário do que
estava espalhado existe como chave `elsewhere` do `list --json`, nomeando
`.cairn/sync.json`, `.cairn/context.json` e `cairn.enabled` em `.planning/config.json`,
cada um com quem escreve e quem lê.

**A prova no ponto de consumo, que é o que o critério exige:** o teste
`test.jobs in the config is READ: with no flag at all the command carries -j 4` lê o
efeito no comando composto, não no arquivo. E eu observei dois leitores ao vivo na
saída do `close 29`:

```
[cairn-bookkeep] commit :: nothing was written, so there is nothing to commit
[cairn-bookkeep] pr_due :: True (ship.pr_scope = 'phase')
```

Isso é a chave sendo lida no ponto de consumo, num comando que eu invoquei, não uma
afirmação de summary.

O schema é fechado e a prova é por conjunto (`list --json` afirmado pelo SET exato de
chaves), então uma oitava chave sem leitor fica vermelha em vez de entrar sem
ninguém ver. A porta da pergunta (`/cairn:config`, um lote de AskUserQuestion em três
seções, chamando `cairn-config.sh set`) está fiada e vai para `human_verification`.

### CS7 — Nenhuma checagem do doctor volta a dizer `ok` por não ter conseguido checar ✓ VERIFICADO

Este é o critério mais bem entregue da fase. Medido ao vivo:

```
⊘ claims-stale  cannot check — STATE.md's frontmatter carries no 'active_phase',
   so there is nothing to compare in_progress claims against (this check has never
   run here). 5 cairn surfaces read that key (cairn-status.py, cairn-doctor.py,
   cairn-lease.py, cairn-migrate.py, hooks/session-start.sh); which key STATE.md
   should carry is open in CairnGo-rq0. Not a failure: a check with no input is
   friction, not a state inconsistency

[cairn-doctor] INCOMPLETE — 17 ok, 1 not-applicable, 1 warning(s), 0 failure(s)
```

`exit 0` — não bloqueia. E `.ok` é `false` enquanto `.failed` é `false`: a chave de
saúde não pode mais ser verdadeira com uma checagem dentro da alçada do doctor sem
ter recebido insumo. Diz o que faltou, cita onde a decisão está, e roteia.

Quatro testes sustentam isso, e o que me convenceu foi o **controle positivo**:
`claims-stale: with active_phase present the check really runs and returns ok` — a
primeira prova neste projeto de que a checagem aprova quando tem algo a comparar.
Um ramo que nunca devolve `ok` mente na outra direção. Junto com
`no verdict change removes a check from the report` e a asserção sobre o valor exato
(`not-applicable`, nunca "não é ok", porque `warn` satisfaria a negação e é
justamente o estado errado por acidente).

**A metade que a fase deliberadamente NÃO fez, e fez certo em não fazer:**
`the doctor never writes active_phase and never reads current_phase` — teste que
prova a abstenção. Zero linha de código a favor de qualquer dialeto. O critério 7 do
roadmap dividia o requisito exatamente na linha do `/groom-me`, e o texto de AUTO-08
em `REQUIREMENTS.md` foi reescrito no fecho para o que foi entregue, com a metade do
dialeto virando AUTO-10 na fase 25. **O texto atual de `REQUIREMENTS.md` é o que
julguei**, e ele é honesto sobre o escopo.

---

## Cobertura de requisitos

| Requisito | Plano | Status | Evidência |
| --------- | ----- | ------ | --------- |
| AUTO-01 | 29-01, 29-02 | ✓ SATISFEITO (letra) | `cairn-bookkeep.py` close/reconcile, 50 testes, prova end-to-end em `6545a5c`, idempotência re-medida hoje. Ressalva de correção no bloco `gaps` |
| AUTO-02 | 29-04 | ✓ SATISFEITO | `cairn-jira.py`, 14 testes: sem sinal nunca pergunta, sinal fraco não decide, "não" tão durável quanto "sim", `apply` recusa placeholder |
| AUTO-03 | 29-05 | ✓ SATISFEITO | `external_ref` + `**Tracker:**` no board, 19 testes, três camadas de tripwire de rede com controle negativo cada |
| AUTO-04 | 29-06 | ✓ SATISFEITO | `cairn-test.py` detecta os dois pré-requisitos antes de compor o comando; checagem 16 do doctor; `--check-env` medido ao vivo |
| AUTO-05 | 29-03 | ✓ SATISFEITO | 7 chaves com leitor nomeado, duas portas, prova no ponto de consumo (`test.jobs` no comando, `ship.pr_scope` observado ao vivo) |
| AUTO-06 | 29-03 | ✓ SATISFEITO | auto_commit, pr_scope, max_cycles, max_parallel + inventário `elsewhere` dos três lugares espalhados |
| AUTO-07 | 29-07 | ✓ SATISFEITO | checagem 17 `req-ledger`, 13 testes, reprovou o estado real (13 elos rompidos) antes do conserto |
| AUTO-08 | 29-07 | ✓ SATISFEITO | `claims-stale` → `⊘ not-applicable/no-input`, `.ok false` sem bloquear, com controle positivo e teste de abstenção do dialeto |

**8/8 entregues pela letra do `REQUIREMENTS.md` atual.** Nenhum requisito órfão: os
oito da linha `**Requirements**:` da fase têm linha na tabela de Cobertura, os oito
estão `[x]`, e o `req-ledger` confirma a cadeia inteira.

Observação de rastreabilidade, não é lacuna: **AUTO-01 não aparece em nenhum
`requirements-completed:` de summary** — o 29-01 não tem o campo e o 29-02 tem `[]`.
Os outros sete requisitos têm portador declarado. AUTO-01 está marcado no
`REQUIREMENTS.md` e na tabela de Cobertura, mas nenhum SUMMARY o reivindica.

---

## Anti-padrões

| Arquivo | Achado | Severidade | Impacto |
| ------- | ------ | ---------- | ------- |
| `cairn-bookkeep.py:1018,1087` | glob assimétrico `*-SUMMARY.md` × `*-PLAN.md` | 🛑 Blocker | contador impossível vivo no STATE.md; ver `gaps` |
| `tests/helpers.bash` | fixture incapaz de gerar `NN-SUMMARY.md` de fase | 🛑 Blocker | o teste de ciclo inteiro não pode ver o defeito acima |
| `.planning/ROADMAP.md:672` | `**Plans:** 6/7` com 7 checkboxes marcados | ⚠️ Aviso | superfície sem dono, sem leitor e sem checagem |
| `.planning/STATE.md:27,31` | prosa ainda diz `Milestone v1.4` e `Phase: 18` | ℹ️ Info | item já registrado em `deferred-items.md`; neutralizado no caminho do cairn porque `reconcile: computes the STATE counters from disk, never from the prose` é teste verde, mas continua vivo para o gsd-tools |

Nenhum marcador de dívida (`TBD`/`FIXME`/`XXX`) sem referência formal foi encontrado
nos arquivos da fase.

---

## Resumo das lacunas

A fase entregou muito e entregou com rigor incomum: 126 testes verdes, controle
negativo em toda camada de tripwire, controle positivo na checagem que passou a
poder dizer `not-applicable`, allowlist de returncode com o contrato citado ao lado,
abstenção provada por teste na decisão que era de regra de negócio. Os sete
critérios têm entrega real e os oito requisitos estão satisfeitos pela letra.

A lacuna é uma só, e é de espécie: **a fase construiu um leitor independente para a
cadeia de requisitos e deixou a cadeia de planos sem nenhum.** O resultado é um
contador que a própria ferramenta da fase escreve errado (`completed_plans: 33` de
`total_plans: 28`) e que o `reconcile` da mesma ferramenta certifica como
concordante, imprimindo os dois números no mesmo objeto. Escritor e verificador
partilham a regra errada, então nada os separa.

Marco isso como lacuna, e não como aviso, por três razões que sustento por escrito:

1. **O número errado está vivo no repositório agora**, escrito pelo entregável desta
   fase, e nada no repositório o contradiz.
2. **O contrato do roadmap não o difere.** A issue `CairnGo-6bx` tem label
   `phase-25`, mas a seção Phase 25 do ROADMAP não o nomeia em requisito nem em
   critério. Label de bd não é contrato.
3. **É a doença da fase, dentro da cura da fase.** O critério 5 diz que a causa "não
   é uma checagem que falhou: é uma que não existe", e o critério 7 proíbe o
   marcador de sucesso sobre comparação não feita. Registrar `passed` aqui
   propagaria para a série temporal da fase 27 exatamente o verde falso que esta
   fase existiu para remover.

O que **não** marco como lacuna, e a distinção importa: AUTO-01 pela letra pede
consolidação num comando, e consolidação foi entregue e provada. O defeito é de
correção, não de consolidação. É por isso que o placar diz 8/8 requisitos e 6/7
critérios — a lacuna mora no critério 1, na cláusula dos contadores e na cegueira
estrutural da fixture, não no texto do requisito.

Duas verificações humanas ficam pendentes, ambas sobre apresentação de pergunta
(`/cairn:config` e `/cairn:sync-config`), nenhuma sobre mecanismo — os mecanismos das
duas têm teste verde.

---

_Verificado: 2026-08-06T21:20:07Z_
_Verificador: Claude (gsd-verifier), modo goal-backward, postura adversarial_
