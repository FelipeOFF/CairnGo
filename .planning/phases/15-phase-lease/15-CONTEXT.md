# Phase 15: Phase lease - Context

**Gathered:** 2026-07-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Dois agentes na mesma fase vira fato visível **antes** do trabalho começar, em vez
de descoberta reativa no meio da execução, id por id. Hoje o único primitivo de
concorrência é o claim por issue: `execute-wave-pre.md` documenta o próprio modo
de falha — *"se um id está claimado por outro, não roube: exponha o conflito na
saída e siga com o plano"* — o que descobre a colisão tarde e por peça.

Requisitos: LEASE-01 … LEASE-05. Issues bd: ver `15-BEADS-MAP.md`.

Herdado das fases 13 e 14 e **não reaberto**: o cairn nunca grava sozinho e nunca
para o fluxo (D-01 da 13); o script reporta e a prosa pergunta (D-02 da 13); uma
leitura alimenta as três superfícies.

</domain>

<decisions>
## Implementation Decisions

### O mecanismo

- **D-01: o lease é uma issue do bd, e isso foi medido, não suposto.** Nesta
  sessão, de dentro de uma `git worktree` recém-criada: `bd list` devolveu as
  issues do repositório principal **sem criar banco local, sem daemon e sem
  registry global**, e `bd create` a partir da worktree produziu uma issue visível
  do repositório principal. Leitura e escrita compartilham o mesmo banco. Isso
  fecha o item de research que o roadmap desta fase deixou explicitamente em
  aberto, e é o que torna o lease-como-issue viável em vez de arquivo.

### Quem é "outro agente"

- **D-02: o caminho da worktree é a identidade.** O bd identifica por actor
  (`BEADS_ACTOR`, senão `git user.name`, senão `$USER`), e dois agentes na mesma
  máquina são o **mesmo** actor para ele — inútil exatamente no cenário que a fase
  18 vai produzir. Já `git rev-parse --git-dir` é distinto por worktree enquanto
  `--git-common-dir` é compartilhado (medido nesta sessão), então duas worktrees
  chegam com identidades naturais e distintas sem inventar primitivo novo.

  **Limitação conhecida, aceita:** dois agentes na **mesma** árvore continuam
  indistinguíveis. Não é o cenário da fase 18, que dá uma worktree a cada agente,
  mas é um caso real (dois terminais na mesma pasta) e o plano deve dizer isso em
  vez de deixar o leitor descobrir. Rejeitado explicitamente: `actor+host+pid`,
  porque cada comando cairn é um processo novo e efêmero — o pid gravado no lease
  morre segundos depois, identificando o comando e não a sessão.

### Quando o lease morre

- **D-03: heartbeat nos hooks de sessão, com TTL de 4 horas.** `session-start.sh`
  renova, `session-stop.sh` libera. Sessão viva mantém o próprio lease vivo; sessão
  morta expira em 4h.

  **Risco que o plano precisa endereçar:** isto depende de os hooks efetivamente
  rodarem. Se não rodarem, o lease expira **debaixo de uma sessão viva que está
  trabalhando** — que é a forma inversa do bug desta fase e não pode passar
  despercebida. O plano precisa de um teste que force o cenário "hook não rodou" e
  prove que o resultado é visível, não silencioso.

### Barra ou avisa

- **D-04: avisa, nomeia e oferece as opções — nunca sobrepõe em silêncio, nunca
  para o fluxo.** Mesma postura travada na fase 13 (D-01 de lá): diz quem segura e
  desde quando, apresenta as saídas com a provável já pré-selecionada, e o trabalho
  continua. Rejeitado recusar de plano: para o fluxo por algo que muitas vezes é
  apenas um lease velho. Rejeitado avisar e seguir sem perguntar: vira aviso que
  ninguém lê, o modo de falha que a pesquisa da fase 13 documentou.

### Onde aparece

- **D-05: linha própria no rodapé do painel** — `◆ fase 15 em uso por <quem> desde
  <quando>` — e some quando ninguém segura nada.

  Esta escolha tem uma razão além do gosto: as fases 14 e 15 estão sendo executadas
  **em paralelo, em worktrees separadas**, e as outras duas opções (coluna na
  tabela da 14, marca na lane DOING) colidiriam com a fase 14 no mesmo arquivo e na
  mesma função. O rodapé é território que a 14 não toca. A decisão de layout aqui é
  também uma decisão de reconciliação.

### Claude's Discretion

- Formato exato do id derivado da worktree (hash do caminho, basename, caminho
  cru) — desde que seja estável entre invocações e legível no relatório.
- Onde o lease guarda o instante de aquisição e o de renovação dentro da issue.
- Texto exato da linha de rodapé e seu comportamento em `--plain` e `--ascii`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Medições desta sessão que decidem o desenho
- `.planning/phases/15-phase-lease/15-CONTEXT.md` §D-01 e §D-02 (este arquivo) — as
  duas medições de worktree, leitura e escrita
- `.planning/research/SUMMARY.md` §"Collision 3" — a comparação lease-arquivo vs
  lease-issue e o item de verificação que ficou aberto, agora fechado
- `.planning/research/STACK.md` — por que `os.rename` não serve para adquirir lock,
  e por que `.planning/`/`.cairn/` são caminhos errados para estado compartilhado
  (são fisicamente distintos por worktree)

### O que as fases anteriores travaram
- `.planning/phases/13-state-corroboration/13-CONTEXT.md` — D-01 (nunca grava
  sozinho, nunca para o fluxo) e D-02 (script reporta, prosa pergunta)
- `.planning/phases/14-phase-card/14-CONTEXT.md` — o layout da tabela, para saber
  o que **não** tocar

### Código
- `cairn/commands/work.md` e `cairn/capability/fragments/execute-wave-pre.md` — os
  dois caminhos de entrada numa fase, onde o lease é adquirido
- `cairn/hooks/session-start.sh` e `session-stop.sh` — heartbeat e liberação
- `cairn/scripts/cairn-doctor.py` check 8 `claims-stale` — o padrão de
  obsolescência a espelhar um nível acima
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bd update <id> --claim` e `bd update <id> --assignee "" --status open` são
  adquirir e liberar, já usados para issues; o lease é o mesmo primitivo um nível
  acima.
- `cairn-doctor.py` check 8 (`claims-stale`) é quase literalmente a checagem de
  lease obsoleto, um nível acima.
- `session-stop.sh` já avisa sobre claim pendente — estender para lease é o mesmo
  lugar e o mesmo formato.

### Established Patterns
- Hooks nunca falham o chamador: `set -uo pipefail` sem `-e`, tudo guardado, saída
  0 incondicional. O que significa que uma falha some — a fase 13 já teve que
  resolver isso escrevendo em `.cairn/hook.log`, e o mesmo vale aqui.

### Integration Points
- Aquisição: `work.md` e `execute-wave-pre.md`.
- Liberação: `verify.md` / `verify-post.md`, **uma vez por fase**, tenha a
  verificação passado ou falhado.
- Doctor: checagem nova de lease obsoleto.
- Rodapé do painel em `cairn-status.py` — a única superfície tocada, escolhida para
  não colidir com a fase 14.

</code_context>

<specifics>
## Specific Ideas

- As fases 14 e 15 rodam **em paralelo, em worktrees separadas**, a pedido do
  Felipe — ensaio manual do que a fase 18 vai automatizar. As decisões desta fase
  levaram isso em conta: D-05 escolheu o rodapé em parte para tornar a
  reconciliação trivial.
- Achado registrado durante esta conversa, e que vira insumo direto da fase 18:
  **independência no grafo de dependências não é independência no arquivo.** As
  fases 14 e 15 não têm aresta entre si e mesmo assim colidiriam em
  `cairn-status.py` se o lease fosse para a tabela. O critério da fase 18 não pode
  ser apenas `blocked_by == []`.

</specifics>

<deferred>
## Deferred Ideas

- Dois agentes na **mesma** worktree — fora de escopo por D-02, registrado como
  limitação conhecida e não como esquecimento.
- Lease entre máquinas diferentes: o bd sincroniza por `refs/dolt/data`, então em
  princípio funciona, mas não foi medido nesta sessão e não deve ser afirmado.
- Execução paralela de fases propriamente dita — é a fase 18.

</deferred>

---

*Phase: 15-Phase lease*
*Context gathered: 2026-07-30*
