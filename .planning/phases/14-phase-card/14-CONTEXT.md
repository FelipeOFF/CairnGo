# Phase 14: Phase card - Context

**Gathered:** 2026-07-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Toda superfície passa a dizer o que a fase É e por onde ela passou, na mesma
leitura. Hoje o card carrega número, título, estado e o que espera; propósito,
research, planos, issues e veredito de verificação não aparecem em lugar nenhum.

Requisitos: CARD-01 … CARD-04. Issues bd: ver `14-BEADS-MAP.md`.

Herdado da fase 13 e **não reaberto**: uma leitura (`phase_model()`) alimenta as
três superfícies; `disk_state` mantém as quatro chaves; o marcador de conflito
ocupa uma linha só; terminal e HTML provados idênticos por teste que renderiza os
dois e compara.

</domain>

<decisions>
## Implementation Decisions

### Layout do painel

- **D-01: tabela com colunas, mais uma lista de propósitos ao final, indexada
  pelo número da fase.** Escolhido depois de quatro variantes renderizadas no
  terminal; nenhuma das quatro serviu, e esta é do Felipe. A tabela permite
  varredura vertical (ler a coluna `issues` de todas as fases de uma vez), e o
  propósito de toda fase aparece **sem truncar**, o que uma coluna não permitiria.

  ```
  PENDING PHASES  4
     #  fase                  estado        rsch  plans  issues  verify   espera
    14  Phase card            executed       —     3/3    2/4    pend.      —
    15  Phase lease           not planned    a fazer 0/0   0/5      —        —
    16  Transition journal    not planned    —     0/0    0/5      —        15
    17  Semantic escalation   not planned    —     0/0    0/4      —        16

    para que serve
    14  toda superficie diz o que a fase e e por onde ela passou
    15  dois agentes na mesma fase vira fato visivel antes de comecar
    16  o historico sobrevive a uma queda e explica um conflito
    17  quando as fontes discordam, uma investigacao propoe a reconciliacao
  ```

  Custo aceito conscientemente: para uma fase, o leitor olha em dois lugares.
  Rejeitado explicitamente: coluna `para quê` truncada (frase cortada em ~28
  colunas vira ruído, não informação) e bloco de três linhas por fase (com cinco
  fases pendentes o painel deixa de caber na tela junto com as lanes).

- **D-02: `NEXT COMMANDS` deixa de ser seção separada.** A tabela ganha uma coluna
  `próximo`, e a **razão da ordem** passa a viver na lista do fim, ao lado do
  propósito. Uma seção de estado, uma de texto, e o número da fase deixa de
  aparecer em três lugares. A razão não podia virar coluna — `"nada bloqueia, e a
  16 e a 17 esperam pela 15"` não cabe, e é metade do valor do CARD-04.

### De onde vem o propósito

- **D-03: campo `**Card:**` dedicado no ROADMAP, com fallback para a primeira
  frase do `**Goal:**`.** Nunca fica vazio — roadmap que nunca ouviu falar do
  campo continua rendendo uma linha útil — e quem quer controle fino tem onde
  escrever uma frase construída para caber. As duas fontes são um custo assumido;
  a alternativa sem fallback some quando alguém esquece de preencher, e a
  alternativa sem campo depende de todo autor de Goal começar por uma frase que se
  sustente sozinha.

### Fase que ainda não tem nada

- **D-04: traço em toda coluna, e o `/cairn:doctor` nomeia o que falta.** A tabela
  já diz `not planned`; repetir cinco ausências por linha não acrescenta. O
  itemizado por artefato mora no doctor, que é onde a fase 13 já colocou o
  itemizado por fonte — a mesma divisão de trabalho entre as duas superfícies, não
  uma exceção nova.

  Isto **estreita o critério 3 do roadmap** (o CARD-03 em REQUIREMENTS.md é a
  paridade terminal↔HTML, outro requisito), e o estreitamento é deliberado, não
  omissão: no
  board a ausência esperada é um traço; a ausência **inesperada** (uma fase
  `executed` sem SUMMARY, por exemplo) é o que merece marca, e nomear qual
  artefato falta é trabalho do doctor.

### Claude's Discretion

- Larguras exatas das colunas e comportamento em terminal estreito.
- Glifos/abreviações de cada coluna (`rsch`, `pend.`, `—`).
- Como a tabela degrada em `--plain` e `--ascii`.
- Onde exatamente a lista de propósitos entra no HTML (o HTML tem espaço; não
  precisa imitar a separação do terminal, desde que os **campos** sejam os mesmos).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O que a fase 13 deixou pronto e esta fase consome
- `.planning/phases/13-state-corroboration/13-CONTEXT.md` — D-01 (cairn nunca
  grava sozinho e nunca para o fluxo), D-02 (script reporta, prosa pergunta),
  D-03 (uma fase, uma linha, para conflito), D-04 (terminal ≡ HTML)
- `.planning/phases/13-state-corroboration/13-02-SUMMARY.md` — o helper
  compartilhado e a razão de o teste renderizar os dois e comparar
- `cairn/scripts/cairn-status.py` — `phase_model()` e as chaves `evidence`,
  `corroboration`, `conflicts`, `needs_doctor`; as funções de render
  `phase_state_text()`, `phase_panel_lines()`, `html_phases()`, `next_commands()`

### Requisitos e escopo
- `.planning/REQUIREMENTS.md` — CARD-01…04
- `.planning/ROADMAP.md` §`Phase 14: Phase card` — os 4 critérios de sucesso

### Convenções da casa (obrigatórias)
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `die()`,
  `EXIT_*`, docstring como spec
- `cairn/templates/status-board.html` — o bloco gerado vive entre
  `<!-- cairn:generated:board:start -->` e `:end`; fora dos marcadores é do usuário

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `phase_model()` já entrega, por fase: `title`, `requirements`, `disk_state`,
  `plans_done`/`plans_total`, `depends_on`/`blocked_by`, `next_command`,
  `corroboration`. Falta ler: research (existe `NN-RESEARCH.md`?), issues
  fechadas/total (o bd já é buscado antes), e veredito (`status:` no frontmatter
  do `NN-VERIFICATION.md`).
- `conflict_summary_text()` (fase 13) é o precedente do helper compartilhado entre
  as duas superfícies — o card segue o mesmo desenho.
- `roadmap_phase_rows()` já parseia o ROADMAP por forma; o campo `**Card:**` entra
  ali, junto de onde `**Requirements**:` já é lido.

### Established Patterns
- Um teste renderiza terminal e HTML e compara, extraindo o valor do `--json` em
  vez de comparar contra string escrita à mão nos dois lados — senão as duas
  superfícies podem derivar juntas para o mesmo valor errado e o teste passa.

### Integration Points
- `phase_panel_lines()` e `html_phases()` são os dois renderizadores.
- `next_commands()` some como seção mas a função continua — vira a coluna
  `próximo` e a razão na lista do fim.
- `roadmap_phase_rows()` para o campo `**Card:**`.

</code_context>

<specifics>
## Specific Ideas

- O layout foi escolhido comparando quatro renderizações reais no terminal, e a
  quinta — a que venceu — foi proposta pelo Felipe depois de ver as quatro.
- Eu havia aprovado internamente o template B, que na própria legenda dizia que o
  propósito não caberia no terminal. Isso teria removido o CARD-01 e o critério 1
  do roadmap por via de layout, sem ninguém decidir remover. Foi levantado antes
  de virar decisão; a lista ao final existe por causa disso.

</specifics>

<deferred>
## Deferred Ideas

- **Execução paralela de fases por múltiplos agentes** — pedida pelo Felipe
  durante esta conversa. Não é card; é orquestração, e depende do lease (15) e do
  journal (16) existirem. Entra como fase própria no fim do milestone.
- Severidade de conflito com mais de dois níveis (CORR-09, v2).
- Visão de tendência entre milestones (CORR-10, v2).

</deferred>

---

*Phase: 14-Phase card*
*Context gathered: 2026-07-30*
