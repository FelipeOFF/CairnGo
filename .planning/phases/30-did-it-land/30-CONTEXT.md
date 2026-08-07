# Phase 30: Did it land - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

O board passa a responder **"isto entrou?"** — se o trabalho de uma fase ou de uma
tarefa já está na branch de controle, e qual PR o levou até lá.

Requisitos: PR-01, PR-02, PR-03, PR-04. Issues bd: ver `30-BEADS-MAP.md`.

Pedido do Felipe em 2026-08-05, com a motivação literal: *"mapear se uma determinada
feature foi concluída/entrou na branch (dev, develop, ou qualquer outra branch de
controle de gitflow)"*.

**Duas perguntas, não uma, e elas têm confianças diferentes.** Tratá-las como uma só
é o erro que esta fase precisa não cometer.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo. As decisões são Claude's Discretion, e saem de medição
feita em 2026-08-05 contra o histórico deste repositório. Onde algo não foi medido,
está escrito que não foi.

### O board hoje não sabe nada de PR, e isso foi verificado

- **D-01: ponto de partida zero.** `grep -rniE "pull.?request|gh pr|merged"` em
  `cairn-status.py` devolve dois hits, os dois sobre **junção de dados**
  (`Two sources, merged`, `merged with what is actually on disk`). Nenhum sobre
  pull request. O único arquivo do cairn que fala com o `gh` é
  `cairn/hooks/post-bd-write.sh`, e é para empurrar sincronização, não para ler
  estado.

  O `external_ref` do bd existe e a fase 29-05 acabou de trazê-lo ao board — mas ele
  carrega referência de **issue** (`gh-42`, escrito pelo `cairn-doctor --link-refs`),
  não de PR. Medido: `CairnGo-vtq` tem `external_ref: None`, e o doctor reporta
  `73 closed issue(s) lack an external ref`.

### A pergunta "entrou?" é offline e exata. A pergunta "qual PR?" não é

- **D-02: duas fontes, duas confianças, e o board nunca as confunde.**

  | pergunta | fonte | confiança |
  |---|---|---|
  | o trabalho entrou na branch de controle? | ancestralidade no git local | **exata**, sem rede |
  | qual PR o levou? | merge commit, sufixo `(#N)`, ou `gh`/`glab` | **parcial** offline |
  | em que estado está a PR? | `gh`/`glab` | exige rede |

  A necessidade que originou a fase é a **primeira**, e ela se responde com
  `git merge-base --is-ancestor <sha> <branch-de-controle>`. Zero rede, zero
  ambiguidade. Provado agora: `git merge-base --is-ancestor 6545a5c origin/main`
  devolve falso — a fase 29 está completa no disco e **não entrou** em `origin/main`,
  com 46 commits locais não empurrados. Nenhuma superfície do cairn diz isso hoje.

### O buraco do caminho offline é real, foi medido, e atinge o caso mais importante

- **D-03: quando a PR não é descobrível, o estado é `desconhecido` e diz por quê —
  nunca "sem PR".**

  Medido no histórico deste repositório:

  ```
  commits squash com (#N) no assunto ......... 14
  merge commits que nomeiam "pull request #N"   6 de 14
  PR #21 (o milestone v1.4 inteiro) .......... nenhum rastro
  ```

  O merge da #21 virou `7fa133c v1.4 Honest State: phase state that proves what it
  claims (ships cairn 1.5.0)` — título próprio, sem número de PR. **A PR mais
  importante do repositório é invisível offline.**

  Isso proíbe a inferência tentadora: "não achei PR" **não** é "não houve PR". Um
  board que reportasse "sem PR" para a #21 estaria mentindo sobre o maior merge do
  projeto. O estado certo é `desconhecido` com o motivo nomeado, e é exatamente o
  vocabulário que a fase 23 está tornando de primeira classe (`VOID-01`). Esta fase
  **consome** aquele estado; não inventa um paralelo.

### A branch de controle é detectada, confirmada uma vez, e gravada

- **D-04: o padrão do AUTO-02, reusado inteiro.** O cairn procura, mostra o que achou,
  pergunta **uma** vez, e a partir do sim grava sozinho. O usuário confirma; não
  digita.

  Fontes de detecção, em precedência: `refs/remotes/origin/HEAD`, depois os nomes
  convencionais presentes em `git branch -r` (`develop`, `dev`, `main`, `master`,
  `trunk`), depois a branch de que a atual mais descende. **Medido:
  `git symbolic-ref refs/remotes/origin/HEAD` está VAZIO neste repositório** — a fonte
  mais óbvia não existe aqui, então a detecção tem de degradar em vez de morrer.

  O valor mora na config do 29-03 (`.cairn/config.json`), com leitor nomeado, sob a
  mesma regra fechada: **nenhuma chave sem leitor executável.** Uma chave nova que
  ninguém lê é o defeito que o `cairn.sync_push` documenta (`CairnGo-gbu`).

  Mais de uma branch de controle é caso real de gitflow (`develop` **e** `main`), e o
  modelo tem de admiti-lo: "entrou na develop, ainda não na main" é informação, não
  ambiguidade.

### A rede fica atrás de config, e o cache diz a sua idade

- **D-05: o caminho padrão não faz rede, e isso é herança medida, não preferência.**
  O `AUTO-03` estabeleceu a regra e o `29-05` a provou em **três camadas** com
  controle negativo cada: tripwire de socket in-process, allowlist de `PATH` (porque o
  socket **não vê** subprocess — `curl` no mesmo processo devolvia 200), e inventário
  estrutural dos sítios de `subprocess.run`. Essa prova existe em
  `tests/cairn-tracker-card.bats` e esta fase não pode furá-la.

  Então: estado de revisão vem do `gh`/`glab` **só** com a config ligada, e o dado
  vai para cache local com carimbo de hora. O board diz que é cache **e de quando** —
  um estado de PR sem idade é pior que nenhum, porque parece atual.

  `gh` está presente nesta máquina (`gh version 2.87.3`). Isso é conveniência local,
  **não** licença para chamar rede por default.

### O board mostra; o doctor cobra

- **D-06: sem o PR-04 a fase não fecha o pedido.** Mostrar a informação e não cobrá-la
  treina todo mundo a não olhar. Uma fase marcada completa cujo trabalho não entrou na
  branch de controle vira achado **nomeado** do doctor, com a fase, a branch e o que
  falta.

  Severidade: é `warn`, não `fail`. Trabalho não empurrado é estado normal de quem
  está no meio de um ciclo — é atrito, não inconsistência —, e gastar o exit 7 com
  atrito é como o 7 deixa de significar algo. Mesma distinção que o 29-06 e o 29-07
  fizeram. **Mas** há um caso que é inconsistência de verdade e merece `fail`: fase
  completa, milestone **arquivado**, e o trabalho nunca entrou. Isso não é "ainda não
  empurrei"; é um ciclo fechado sobre trabalho que não existe na branch de controle.

### Claude's Discretion

- Como o estado aparece no board: coluna, sufixo, ou linha própria. Único travão: os
  sete renders de referência da fase 20 continuam byte a byte idênticos quando não há
  dado — o sufixo só existe quando o dado existe, exatamente como o `29-05` fez.
- Se o vínculo tarefa→PR mora no `external_ref` do bd (com prefixo próprio) ou em
  campo do modelo derivado do git. **Travão:** um fato, um dono. Guardar o mesmo
  vínculo em dois lugares é o começo da próxima discordância, e este milestone já
  pagou por isso.
- O nome da chave de config e o formato do cache.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O que esta fase herda e não pode quebrar
- `.planning/phases/29-nothing-mechanical-stays-manual/29-05-SUMMARY.md` — as três
  camadas da prova de ausência de rede, com o controle negativo de cada uma
- `tests/cairn-tracker-card.bats` — a prova executável; esta fase roda contra ela
- `tests/cairn-board-invariance.bats` e `tests/fixtures/board-render/` — os sete
  renders que não podem mover um byte
- `.planning/phases/23-not-applicable-as-a-check-state/23-CONTEXT.md` — o estado
  `not-applicable`/`desconhecido` de primeira classe que esta fase **consome**

### Código
- `cairn/scripts/cairn-status.py` — `phase_model()`, `trim_issue()`, `tracker_key()`,
  o painel de fases e as raias
- `cairn/scripts/cairn-jira.py` — o padrão detectar → mostrar → perguntar uma vez →
  gravar sozinho, a reusar inteiro para a branch de controle
- `cairn/scripts/cairn-config.py` — schema fechado, nenhuma chave sem leitor nomeado
- `cairn/scripts/cairn-doctor.py` — a forma de uma checagem e a semântica de
  `warn` versus `fail` (`:273-274` e `:2571`)
- `cairn/hooks/post-bd-write.sh` — o único lugar que hoje fala com o `gh`
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- O `29-05` já trouxe `external_ref` ao modelo e ao card, com sufixo estritamente
  condicional ao dado existir. A forma de acrescentar uma informação opcional ao
  board sem mover render está resolvida e provada.
- O `29-04` já resolveu detectar → confirmar → gravar sem o usuário digitar nada.
- O `cairn-status.py` já tem quatro sítios de `subprocess.run` inventariados e numa
  allowlist. Um quinto sítio (`git`) entra no mesmo inventário ou a prova de rede
  quebra.

### Established Patterns
- Um teste que passaria com a feature removida não é prova.
- Toda asserção de status é sobre o valor exato, nunca sobre a negação.
- Chave existente nunca muda de nome, de tipo ou de significado.
- Todo achado nomeia o subject e roteia para o comando que resolve.

### Integration Points
- `cairn/scripts/cairn-status.py` — modelo e board.
- `cairn/scripts/cairn-doctor.py` — a checagem do PR-04.
- `cairn/scripts/cairn-config.py` — a chave da branch de controle.
- `cairn/docs/commands/status.md` e `doctor.md` — página é contrato.

</code_context>

<specifics>
## Specific Ideas

- **A prova de aceitação já é verdadeira, agora, e não precisa de fixture.** A fase 29
  está completa no disco e `git merge-base --is-ancestor 6545a5c origin/main` devolve
  falso: 46 commits locais, nada empurrado. O doctor sai 7 hoje e **não diz uma
  palavra sobre isso**. É o mesmo tipo de silêncio que o `req-ledger` acabou de
  remover do registro de requisitos, num lugar diferente.

- **O caso que decide se a fase foi honesta é a PR #21.** Ela existe, foi mergeada, e
  o histórico local não a nomeia. Qualquer implementação que reporte "sem PR" para o
  merge do milestone v1.4 inteiro falhou, mesmo com todos os testes verdes.

</specifics>

<deferred>
## Deferred Ideas

- Abrir, revisar ou mergear PR pelo cairn. Esta fase **lê**; escrita em PR é ação de
  outra ferramenta e de outra conversa.
- Reconciliar automaticamente uma fase completa cujo trabalho não entrou. A checagem
  nomeia; empurrar é decisão humana, e o `/cairn:ship` já é o lugar dela.
- Estado de PR no `--html`. O board HTML é superfície própria e pode vir depois.

</deferred>

---

*Phase: 30-Did it land*
*Context gathered: 2026-08-05*
