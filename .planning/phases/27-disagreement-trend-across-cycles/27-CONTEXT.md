# Phase 27: Disagreement trend across cycles - Context

**Gathered:** 2026-08-06
**Status:** Ready for planning

<domain>
## Phase Boundary

A discordância entre fontes está subindo ou caindo ao longo dos ciclos?

Requisitos: TREND-01, TREND-02. Issues bd: ver `27-BEADS-MAP.md`.

**A pesquisa que o roadmap pedia já foi feita e está aqui.** Ela não confirmou o
pressuposto: mudou o que a fase pode afirmar, e trouxe uma armadilha que é o
verdadeiro trabalho desta fase.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo. Todas as medições são de 2026-08-06, contra a árvore
com as sete verificações do v1.5 já escritas. Onde algo não foi medido, está escrito.

### A série existe, tem três pontos e dois buracos

- **D-01: `v1.1 → [buraco] → [buraco] → v1.4 → v1.5`.**

  ```
  v1.1   passed 4 · gaps_found 2                    6 arquivos com frontmatter
  v1.2   3 VERIFICATION.md, ZERO com frontmatter    buraco
  v1.3   3 VERIFICATION.md, ZERO com frontmatter    buraco
  v1.4   passed 3 · gaps_found 2 · human_needed 1   6 arquivos
  v1.5   passed 3 · gaps_found 3 · human_needed 1   7 arquivos
  ```

  O roadmap supunha que a série talvez começasse só no v1.4. **Começa no v1.1**, e o
  que falta é o miolo, não a cabeça. Os buracos não são de dado ausente: os arquivos
  do v1.2 e do v1.3 **existem** e simplesmente não têm frontmatter — o formato
  estruturado nasceu no v1.1, sumiu por dois ciclos e voltou no v1.4.

- **D-02: o esquema derivou, e o comando tem de lidar com isso sem inventar.** O v1.1
  grava `has_blocking_gaps` e `deferred`; o v1.4 grava `behavior_unverified`,
  `behavior_unverified_items` e `human_verification`. A interseção é
  `phase, verified, status, score, overrides_applied, gaps` — **e é ela que define o
  que a série pode comparar.** Um campo presente em um ciclo só não é tendência.

  O v1.5 foi escrito no esquema do v1.4 de propósito, decidido antes de gerar os sete
  arquivos, justamente para não criar um terceiro dialeto.

### A armadilha que é o trabalho real desta fase

- **D-03: a taxa de aprovação de primeira cai, e o comando NÃO pode dizer por quê.**

  ```
  v1.1   4 passed de 6   67%
  v1.4   3 passed de 6   50%
  v1.5   3 passed de 7   43%
  ```

  Uma linha descendente, bonita, e **ambígua na raiz**. Ela move por duas causas
  opostas e indistinguíveis a partir do próprio número:

  1. a qualidade caindo — mais fases chegam ao fim com lacuna;
  2. **o escrutínio subindo** — o verificador ficou mais rigoroso e passou a achar o
     que antes passava.

  E há evidência direta da segunda neste ciclo: das três `gaps_found` do v1.5,
  **nenhuma é de mecanismo**. São contador errado, registro escrito desatualizado e
  lista à mão. Duas delas foram achadas por verificações que aplicaram mutação
  própria e reproduziram defeito que nenhum executor tinha visto — inclusive um caso
  em que a fixture era **cega ao defeito por construção**.

  **Um comando que desenha essa linha sem dizer isso mente com número verdadeiro.**
  É o defeito desta casa na forma mais sofisticada que ele já tomou aqui: não é
  aprovar sem checar, é medir certo e concluir errado.

  O que a fase entrega, então, não é uma linha: é a série com **a ambiguidade
  declarada ao lado dela**, e o dado que permitiria desambiguar quando existir.

### O `not-applicable` é por que esta fase dependia da 23

- **D-04: sem o quarto estado, a série somaria `ok` com "não checou".** É literal no
  `**Depende de:**` do roadmap, e agora é verificável: o v1.5 é o primeiro ciclo em
  que uma checagem sem insumo é distinguível de uma que aprovou. Se a série contar
  os dois juntos, ela mede a saúde do repositório e a cobertura da ferramenta na
  mesma coluna.

### O que o TREND-02 proíbe, e como se prova que foi obedecido

- **D-05: nenhum número digitado à mão, e a prova é por acréscimo.** O padrão já foi
  exercido duas vezes neste ciclo e funciona: a verificação da fase 26 largou um
  wrapper novo no disco e afirmou que a página o listava sozinha. Aqui o equivalente
  é acrescentar um `VERIFICATION.md` a um ciclo de fixture e afirmar que a série
  muda sem ninguém editar prosa.

  Este repositório tem três precedentes medidos de número escrito à mão que
  envelheceu — `"fifteen checks"` com dezesseis, `"17 checks"` com dezenove, e
  `"18 checks"` na linha 449 contra `"nineteen"` na 371 **do mesmo arquivo**. Um
  comando de tendência que carimbe qualquer número é o quarto.

### Claude's Discretion

- O nome e a forma do comando, e se ele é script próprio (`cairn-trend.py`) ou
  subcomando de algo que já existe.
- Quais eixos a série carrega além de `status`: `gaps`, `overrides_applied` e
  `score` estão na interseção e são candidatos.
- Como os dois buracos aparecem na saída — desde que apareçam. Ciclo sem dado
  comparável é `not-applicable`, o estado que a fase 23 entregou, e **não** zero.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O dado
- `.planning/milestones/v1.1-phases/*/*VERIFICATION.md` — 6 com frontmatter
- `.planning/milestones/v1.2-phases/`, `v1.3-phases/` — 3 cada, **sem** frontmatter
- `.planning/milestones/v1.4-phases/*/*VERIFICATION.md` — 6 com frontmatter
- `.planning/phases/*/[0-9]*VERIFICATION.md` — os 7 do v1.5, esquema do v1.4

### Código
- `cairn/scripts/cairn-doctor.py` — o vocabulário de quatro estados que a série herda
- `cairn/scripts/cairn-status.py` — como este projeto lê `.planning/` e degrada
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- O `cairn-bookkeep.py` já lê `.planning/milestones/` para saber que ciclo está
  arquivado (`archived_milestones()`, entregue na fase 23) — a varredura existe.
- O idioma de `not-applicable` com motivo nomeado está entregue e é o que os dois
  buracos devem usar.

### Established Patterns
- Um teste que passaria com a feature removida não é prova.
- Toda asserção de status é sobre o valor exato, nunca sobre a negação.
- Todo achado nomeia o subject e roteia para quem resolve.
- Número afirmado em prosa envelhece; três precedentes medidos neste repositório.

### Integration Points
- Script novo + par `.sh` + `tests/<basename>.bats` próprio.
- Possivelmente `cairn/docs/commands/` — página é contrato.
- **Nada de doctor, nada de board.** Se esta fase tocar `cairn-status.py` ou
  `cairn-doctor.py`, ela saiu do escopo.

</code_context>

<specifics>
## Specific Ideas

- **O insumo desta fase quase não existia, e a causa fui eu.** Fechei sete fases do
  v1.5 sem rodar verificação em nenhuma; o ciclo tinha **um** `VERIFICATION.md`
  contra os seis do v1.1 e os seis do v1.4. A fase teria sido construída sobre um
  arquivo que o processo corrente havia parado de produzir — uma tendência sobre
  arquivo morto. As sete verificações foram geradas antes deste contexto existir, e é
  por isso que a série tem três pontos em vez de dois.

- **A própria série registra esse buraco.** O v1.2 e o v1.3 não têm frontmatter
  porque naquele momento ninguém o exigia. O v1.5 quase repetiu isso por outra via.
  O comando que esta fase entrega é, entre outras coisas, o alarme que teria tocado.

</specifics>

<deferred>
## Deferred Ideas

- Retro-preencher o frontmatter do v1.2 e do v1.3. Seria inventar veredito sobre
  trabalho que ninguém verificou daquele jeito — exatamente o que o TREND-02 proíbe.
  Os buracos ficam, declarados.
- Tendência de qualquer métrica que não venha de artefato arquivado (tempo de
  execução, contagem de commits, tokens). Outra fase, outro requisito.
- Desambiguar qualidade versus escrutínio automaticamente. Requer registrar a versão
  do próprio verificador junto do veredito, e isso é desenho novo.

</deferred>

---

*Phase: 27-Disagreement trend across cycles*
*Context gathered: 2026-08-06*
