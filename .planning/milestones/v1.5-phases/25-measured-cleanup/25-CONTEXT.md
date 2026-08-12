# Phase 25: Measured cleanup - Context

**Gathered:** 2026-08-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Dezoito defeitos que já vieram com a medição junto, e a última fase do v1.5.

Requisitos: FIX-01 … FIX-05, AUTO-10. Issues bd: ver `25-BEADS-MAP.md`.

**O `ROADMAP.md`, bloco `### Phase 25`, é a autoridade.** Ele carrega nove critérios,
e cada um já traz a medição que o abriu — não repito nenhuma aqui. Este documento
existe para as três coisas que o roadmap não pode dizer: **em que ordem**, **o que já
foi decidido pelo Felipe**, e **onde esta fase pode se sabotar sozinha**.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo, com as fases 20-24 e 26-30 já fechadas. Todas as
medições citadas são das issues bd e do roadmap, de 2026-08-05 a 2026-08-07.

### O risco que só esta fase tem: ela conserta as próprias ferramentas

- **D-01: duas issues consertam ferramenta que orquestra as outras.** O
  `CairnGo-64u` (P0) e o `CairnGo-4oq` mexem no `cairn-parallel`, e o `CairnGo-0po`
  (FIX-05) mexe na leitura de estado de fase que o `cairn-bookkeep` e o
  `cairn-status` usam. Foi por isso que esta fase ficou por último no ciclo inteiro.

  **A ordem é: consertar cedo, com o defeito reproduzido antes.** A regra da casa já
  cobre o risco — teste que reproduz o defeito **antes** do conserto, com a medição
  original citada no próprio teste — e ela vale aqui com força extra: um conserto
  errado numa ferramenta de orquestração contamina tudo que vem depois **sem
  ficar vermelho**, porque quem mede passa a ser o que quebrou. Depois de cada
  conserto de ferramenta, rode a suíte do arquivo tocado **e** a de quem o consome.

- **D-02: o `completed_plans` já excede o `total_plans` neste repositório agora**
  (42 contra 34, e cresce a cada fase fechada). O critério 6 é o único cuja prova
  está no disco antes de o plano existir: qualquer conserto pode ser verificado
  contra o `STATE.md` real, não só contra fixture. E a fixture é o achado —
  `tests/helpers.bash` escreve só `$nn-$idx-SUMMARY.md`, então zero fixtures do
  repositório carregam um `NN-SUMMARY.md` de fase, e o defeito **nunca chegou perto
  do teste**.

### O que o Felipe já decidiu, e não se rediscute

- **D-03: AUTO-10 (critério 5)** — escrever `active_phase` **junto** com
  `current_phase`, seguir lendo `active_phase`. Aditivo, sem migração. A divergência
  entre as duas vira checagem do doctor.
- **D-04: `sync_push` (critério 7)** — apagar a declaração, não implementar a
  leitura. O comportamento depois é byte a byte o de hoje.
- **D-05: o journal no cleanup (critério 8, terceira metade, `CairnGo-rhq`).**
  Das três saídas nomeadas, **a escolha é excluir `.cairn/journal/` da checagem de
  trabalho não commitado do `cairn-parallel`**, e a defesa é o `DJOUR-03`: o journal
  é o único artefato do cairn cuja perda **não muda veredito nenhum**, e é
  precisamente por isso que ele não pode reter um worktree. Reter é o que se faz com
  trabalho que o git não consegue recriar; o journal não é isso.

  As outras duas perdem por medição, não por gosto: commitar a partição no fim de
  fase enche o histórico de ruído forense **e ainda não resolve**, porque o worktree
  só fica removable depois de commitado *e* mesclado; e aceitar o atrito significa
  que o `cleanup --apply` nunca mais remove um worktree de fase, que é a única coisa
  que ele existe para fazer.

  **Assunção declarada:** o Felipe autorizou seguir com a fase sem escolher esta
  linha explicitamente. Ela é reversível — uma condição num filtro — e está escrita
  aqui para ser contestada. A partição deste checkout segue **não commitada**.

### A armadilha de contagem, pela terceira vez

- **D-06: o doctor vai de 20 para 22 checagens nesta fase** — uma pelo critério 5
  (divergência `active_phase` × `current_phase`) e uma pelo critério 6
  (`completed_plans > total_plans`). O `tests/cairn-doctor.bats` afirma o número em
  **dois** lugares, e o comentário acima da asserção registra por que o canário
  existe: as fases 23 e 24 rodaram em paralelo, cada uma acrescentou uma checagem sem
  saber da outra, e **o git mesclou os dois arquivos sem conflito**. Atualize os dois
  sítios, a lista numerada do docstring, e a página `cairn/docs/commands/doctor.md`.

  E o critério 9 é o mesmo erro noutra superfície: o docstring do `cairn-doctor.py`
  dizia *"eighteen checks in total"* com dezenove registradas. **Cinco precedentes
  medidos** de número à mão que envelheceu neste repositório.

### O que esta fase não pode fazer

- **D-07: nenhum conserto muda o código de saída de um caminho que hoje é verde
  legitimamente.** Está no critério 3 e é a linha que separa limpeza de refatoração.
- **D-08: os sete renders de referência da fase 20 continuam byte a byte idênticos**
  onde não há dado novo. O `30-05` acabou de provar que isso é verificável; quebrá-lo
  aqui seria desfazer a garantia mais barata do ciclo.

### Claude's Discretion

- O agrupamento das 18 issues em planos, e quantos planos.
- Se a checagem nova do critério 6 recomputa ou apenas compara — desde que **não**
  use a mesma regra que escreveu o número, que é o defeito medido (`reconcile`
  devolve `disagreements: []` imprimindo 28 e 33 no mesmo objeto JSON).
- A forma do conserto do `CairnGo-php` (lease) e do `CairnGo-ce3` (worktree): se o
  fechamento desmonta, ou se o doctor nomeia. O que não sobrevive é o silêncio.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md`, bloco `### Phase 25` — nove critérios, cada um com a
  medição que o abriu. **A autoridade.**
- `25-BEADS-MAP.md` — as 18 issues, cada uma com a medição no corpo.
- `cairn/scripts/cairn-bookkeep.py` — o `close`, e a linha 1018 do critério 6.
- `cairn/scripts/cairn-parallel.py` — três issues moram aqui.
- `cairn/scripts/cairn-doctor.py` — duas checagens novas, e o docstring numerado.
- `tests/helpers.bash` — a fixture cega do critério 6, e o `make_pinned_home` novo.
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Established Patterns
- Um teste que passaria com a feature removida não é prova.
- Toda asserção de status é sobre o valor exato, nunca sobre a negação.
- Número afirmado em prosa envelhece — cinco precedentes medidos.
- Escritor e verificador que compartilham a regra errada **concordam**, e a
  concordância é lida como saúde. É o defeito de fundo de metade desta fase.

### Integration Points
- `cairn-doctor.py` + `tests/cairn-doctor.bats` (dois sítios de canário) +
  `cairn/docs/commands/doctor.md`.
- `cairn-bookkeep.py` + `cairn-status.py` — os dois consumidores do estado de fase
  que o FIX-05 conserta.
- `capability.json` e três fragmentos de prompt, para o `sync_push` do critério 7.

</code_context>

<specifics>
## Specific Ideas

- **Esta fase fecha o milestone.** Depois dela: suíte completa uma vez, `cairn-gate`,
  e `/cairn:milestone complete`. Um defeito deixado aqui viaja para o v1.6 dentro de
  uma migração, que é o pior lugar para ele estar.

- **Metade das issues tem a mesma forma.** Uma superfície que responde com confiança
  sobre algo que não checou: o `cairn-parallel` anunciando concorrência que o roadmap
  nega, o `reconcile` dizendo `nothing to change` sobre discordância que ele acabou
  de imprimir, o `contador` passando do próprio total, o `help` derivando metade e
  mantendo metade à mão. É o tema do ciclo aparecendo uma última vez, dentro da
  própria ferramenta.

</specifics>

<deferred>
## Deferred Ideas

- `CORR-09` (severidade de conflito com allowlist configurável) segue adiado para o
  v2, com a razão registrada no `REQUIREMENTS.md`: exige corpus real de tipos de
  conflito, e inventar níveis sobre zero dado é o erro que a pesquisa do v1.4
  descreve.
- Qualquer refatoração que não seja consertar um dos dezoito. A fase é limpeza
  medida, não arrumação.

</deferred>

---

*Phase: 25-Measured cleanup*
*Context gathered: 2026-08-07*
