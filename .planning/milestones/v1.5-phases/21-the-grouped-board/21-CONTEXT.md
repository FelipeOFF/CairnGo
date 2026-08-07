# Phase 21: The grouped board - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

O kanban de três colunas sai do render de terminal. Entra **uma** lista agrupada
pelo modelo que a fase 20 entregou: milestone aberto → fase → tarefa, com a etapa
num símbolo de largura simples e o título ocupando a largura inteira.

Requisitos: BOARD-06, BOARD-02, BOARD-03, BOARD-05. Issues bd: ver
`21-BEADS-MAP.md`.

**O que esta fase muda:** `render_board()`, `render_stacked()`, `render_raw()`,
`make_cell()`, `lane_rows()`, `lane_header_text()` — o caminho de render humano
de terminal — e as sete referências em `tests/fixtures/board-render/`.

**O que esta fase NÃO toca:**

- `render_plain()` e o ramo não-TTY de `main()` (linhas 3447-3454). Medido:
  `tests/cairn-status.bats:208` afirma que `--plain` é **byte a byte idêntico**
  ao default sem TTY, e reescrever essa asserção em duas é PIPE-03, fase 22.
  Se uma mudança daqui reprovar aquele teste, isso é sinal de que a fronteira
  foi cruzada — não licença para editar o teste.
- `render_brief()`. Três linhas, nenhuma delas é linha de tarefa. `brief.txt`
  sai desta fase byte a byte igual, e essa é uma afirmação verificável, não uma
  esperança.
- `data["milestone"]` e o rodapé que o imprime. Ele lê `STATE.md` primeiro e por
  isso anuncia o ciclo arquivado — é BOARD-04, fase 22. Ver D-09.
- `phase_panel_lines()` (PENDING PHASES / PURPOSE). Ver D-08.
- O render HTML (`html_lanes()` e vizinhos). Ver D-10.
- `phase_groups()`, `roadmap_milestones()` e a chave `groups` do `--json`. O
  modelo está fechado e preso por 14 testes; esta fase é **consumidora** dele.

**Herdado e não reaberto:** um grupo é `{type, key, label, items}`; `items` é
homogêneo e sempre uma lista de `{phase, issues}`; `issues` é lista de **ids**,
não de objetos; nenhum grupo e nenhum balde carrega contagem (contagem é
`len()`); grupo vazio não é emitido; `unphased` sempre por último.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo. Tudo abaixo é **Claude's Discretion** salvo onde
marcado como travado pelo roadmap, e cada decisão traz a medição que a sustenta.

### O conjunto de símbolos

- **D-01 (travado pelo roadmap, e re-medido aqui): `◌ ◔ ◕ ✓ ⧗`, todos
  `east_asian_width=N`.** Medido nesta worktree em 2026-08-05 com
  `unicodedata.east_asian_width`:

  | símbolo | ponto | eaw | veredito |
  |---|---|---|---|
  | `◌` U+25CC | DOTTED CIRCLE | `N` | adotado |
  | `◔` U+25D4 | CIRCLE WITH UPPER RIGHT QUADRANT BLACK | `N` | adotado |
  | `◕` U+25D5 | CIRCLE WITH ALL BUT UPPER LEFT QUADRANT BLACK | `N` | adotado |
  | `✓` U+2713 | CHECK MARK | `N` | adotado |
  | `⧗` U+29D7 | BLACK HOURGLASS | `N` | adotado |
  | `○` U+25CB | WHITE CIRCLE | `A` | descartado |
  | `◑` U+25D1 | CIRCLE WITH RIGHT HALF BLACK | `A` | descartado |
  | `◆` U+25C6 | BLACK DIAMOND | `A` | descartado |

  O teste afirma a propriedade por `unicodedata`, **nunca pela aparência**.

- **D-02: por que `A` é fatal aqui, e não é opinião.** `char_width()` (linha
  1795) devolve `2` só para `W` e `F`; um caractere `A` conta **1** para o
  script e desenha **2** num terminal com locale CJK. O script não tem como
  detectar isso — não existe leitura de locale nele, e acrescentar uma seria
  inventar uma fonte de verdade nova. A única defesa é não usar `A`. É por isso
  que a propriedade é asserida sobre o ponto de código e não sobre o render.

- **D-03: o `⧗` já significa "dependência" neste arquivo** (`style.g_dep`, linha
  1885) e é exatamente o mesmo significado que o roadmap lhe dá como etapa
  bloqueada. Reaproveitar é vocabulário único, não colisão.

### O fallback ASCII

- **D-04: cinco símbolos ASCII de exatamente um caractere — `.` `o` `O` `v` `~`.**

  | etapa | unicode | ascii |
  |---|---|---|
  | não planejada | `◌` | `.` |
  | planejada | `◔` | `o` |
  | em execução | `◕` | `O` |
  | feita | `✓` | `v` |
  | bloqueada | `⧗` | `~` |

  **Um caractere, sempre**, porque é isso que faz o critério de sucesso 3 ("as
  colunas fecham alinhadas nos dois modos") virar afirmação mecânica: se todo
  símbolo ocupa 1 célula nos dois modos, cada coluna do bloco agrupado cai na
  **mesma** célula nos dois renders, e um teste pode comparar
  `display_width()` linha a linha entre a saída unicode e a ASCII.

  Os quatro candidatos ASCII óbvios foram descartados por **colisão de
  significado dentro da mesma saída**, não por gosto: `x` já é
  `style.g_conflict` e aparece como `x N blocks` no painel de fases; `!` já é
  `style.g_informs`; `*` já é `style.g_stale`; `#` já é `style.g_card`.

### O que cada linha carrega

- **D-05: duas espécies de linha, um vocabulário só.** A linha de fase usa
  `◌ ◔ ◕ ✓`; a linha de tarefa usa `◔ ◕ ⧗`. Cada um dos cinco símbolos aparece
  em alguma linha; nenhum aparece com dois significados.

  | linha | origem do estado | símbolo |
  |---|---|---|
  | fase | `complete` ou `disk_state == "verified"` | `✓` |
  | fase | `disk_state == "executed"` | `◕` |
  | fase | `disk_state == "planned"` | `◔` |
  | fase | `disk_state == "none"` | `◌` |
  | tarefa | raia `BLOCKED` | `⧗` |
  | tarefa | raia `DOING` | `◕` |
  | tarefa | raia `READY` | `◔` |

- **D-06: a linha de fase NÃO usa `⧗`, mesmo quando `blocked_by` não está
  vazio.** Medido e herdado: `dep_target_ids()` conta toda aresta sem olhar o
  tipo, e a fase 26 aparece bloqueada pela fase 9, um ciclo arquivado dois
  milestones atrás (FIX-04, fase 25). `phase_groups()` recusou ler aresta pelo
  mesmo motivo, escrito no próprio docstring dela. Pintar `⧗` numa fase por
  `blocked_by` importaria o defeito para uma superfície nova. O `waits` do
  painel de fases continua contando essa história, onde ela já é conhecida.

  Consequência aceita e registrada: o símbolo de fase descreve **progresso em
  disco**, e só isso.

### O título, e o que acontece quando a linha não cabe

- **D-07: a lista nunca trunca. Quando a linha excede a largura, ela quebra numa
  linha de continuação alinhada à coluna do título.** É o que torna o critério 1
  verificável em vez de aproximado. `truncate()` continua existindo e continua
  sendo usado pelo painel de fases e pelo rodapé — o que sai é o uso dele na
  lista de tarefas.

  - A quebra mede em **células**, não em caracteres. `textwrap` conta
    caracteres, e o mesmo arquivo que se dá ao trabalho de ter `display_width()`
    não pode quebrar por `len()`. Um `wrap_cells()` de ~12 linhas resolve.
  - Um token único mais largo que o espaço disponível **transborda** em vez de
    ser partido no meio. Partir um id ou uma URL é uma forma de truncar, e o
    critério 1 já exclui explicitamente o caso "a linha não cabe".
  - Nenhum sufixo é descartado por falta de espaço. Isto **remove** a
    precedência que `make_cell()` construiu na fase 29 (o card do tracker cai
    primeiro, depois o resto, o título sempre vence). Aquela precedência
    existia porque a célula tinha largura fixa; sem célula fixa, ela não tem o
    que resolver. A propriedade que a substitui é mais forte: nada cai, nunca.

- **D-08: `phase_panel_lines()` fica como está.** BOARD-03 fala do "título de
  uma **tarefa**"; a coluna `phase` daquela tabela é título de **fase**, dentro
  de uma tabela de largura fixa cujo dimensionamento é trabalho medido da fase
  13 e do plano 29-05. Mexer nela é escopo que nenhum critério desta fase pede,
  e apagá-la destruiria as colunas `state`, `rsch`, `plans`, `verify` e `waits`,
  que a lista agrupada não substitui. Registrado como tensão conhecida: a mesma
  saída passa a ter títulos inteiros na lista e títulos cortados na tabela.

### As duas coisas que vão parecer defeito e não são

- **D-09: o cabeçalho de grupo e o rodapé vão citar milestones diferentes, e
  isso é o defeito da fase 22 ficando visível.** O cabeçalho de grupo vem de
  `groups[].label`, que só existe para milestone **aberto**
  (`roadmap_milestones()` lê o marcador da própria linha). O rodapé vem de
  `data["milestone"]`, que é `STATE.md` primeiro e o roadmap depois. No fixture
  `make_board_fixture` os dois discordam **de propósito** desde o plano 20-01:
  `STATE.md` diz `v1.0` (arquivado), `ROADMAP.md` diz `🚧 v1.1 Surface`. Depois
  desta fase a referência vai mostrar `v1.1 Surface` no topo e `· v1.0 ·` no
  rodapé, na mesma tela.

  **Consertar o rodapé aqui é atravessar para BOARD-04, fase 22.** O que esta
  fase faz é anotar isso no SUMMARY como consequência esperada e medida.

- **D-10: o board HTML continua com as três raias.** É um quarto renderer sobre
  o mesmo `data`, e nenhum critério desta fase o menciona. `groups` está lá
  quando alguém quiser. Registrado como fronteira, não como esquecimento.

### Mecânica

- **D-11: o renderer resolve id → issue por fila FIFO montada de `_lanes`.**
  `groups[].items[].issues` carrega **ids**, e a etapa de uma tarefa vem da
  raia. `phase_groups()` recebe `ready + doing + blocked` nessa ordem e coloca
  **por ocorrência de entrada**, sem deduplicar (uma issue pode chegar duas
  vezes: `bd list --status in_progress` e `bd blocked` são consultas
  independentes). Uma fila por id, consumida na ordem em que os ids aparecem
  nos baldes, reproduz exatamente o par (ocorrência, raia) — e não inventa uma
  segunda colocação, que é o que o arquivo inteiro existe para evitar.

  Rejeitado: acrescentar `stage` dentro de `items[]`. Mudaria a forma de uma
  chave pública com um ciclo de idade, e os testes 12 e 13 de
  `cairn-group-model.bats` afirmam o conjunto exaustivo de chaves.

- **D-12: os três renderers de largura viram um.** `render_board` (≥64),
  `render_stacked` (≥40) e `render_raw` (<40) existem porque **três colunas** não
  cabem num terminal estreito. Uma coluna cabe em qualquer largura. Os degrades e
  as constantes `STACK_BELOW`, `RAW_BELOW`, `MIN_INNER`, `MAX_INNER`, `N_LANES`
  saem junto se ficarem sem leitor. `LANES` **fica** — `render_plain()` a usa, e
  `render_plain()` é da fase 22.

  As referências `w38.txt` e `w50.txt` continuam existindo e continuam provando
  o render nessas larguras. O que elas passam a provar é a lista, e o diff delas
  é onde o colapso dos três modos fica legível.

- **D-13: `--max-rows` passa a limitar por balde**, com a mesma linha `+k more`.
  A raia era o container; o balde é o container agora. Linhas de grupo e de fase
  nunca são limitadas — elas são a estrutura, não o conteúdo.

- **D-14: uma linha de contagens no topo da lista, com a grafia do `--brief`.**
  As raias carregavam `READY (3)` / `DOING (1)` / `BLOCKED (1)`; sem elas, o
  board default perde as contagens (hoje elas só existem no `--brief`). A
  grafia é extraída para um helper compartilhado, de modo que `--brief` continue
  **byte a byte** o que era — e isso passa a ser a prova de que a extração foi
  fiel.

- **D-15: sem grupo nenhum, a lista diz que não há trabalho aberto** em vez de
  não imprimir nada. Um espaço em branco onde havia três raias vazias é menos
  informação, não mais.

### Claude's Discretion (aberto no planejamento)

- Indentação exata, ordem dos sufixos na linha, e a redação de "no open work".
- Se o cabeçalho de grupo leva contagem própria (é `len()` de baldes, então
  pode; a fase 20 recusou guardá-la no modelo, não exibi-la).
- Nome das funções novas.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contrato da fase
- `.planning/ROADMAP.md` § Phase 21 (os quatro critérios), § Phase 20 (o modelo
  consumido) e § Phase 22 (a fronteira que não se atravessa)
- `.planning/REQUIREMENTS.md` — BOARD-02, BOARD-03, BOARD-05, BOARD-06

### O modelo que esta fase consome
- `.planning/phases/20-group-model/20-CONTEXT.md` — D-01 a D-04 do modelo
- `20-02-SUMMARY.md` — a forma fechada `{type, key, label, items}`
- `20-03-SUMMARY.md` — as bordas e o aviso explícito de que a fase 21 **vai**
  regenerar as sete referências e **deve** a explicação de cada linha

### Código
- `cairn/scripts/cairn-status.py` — docstring de módulo (passo 5 e 5b),
  `Style`, `make_cell`, `lane_rows`, `render_board`, `render_stacked`,
  `render_raw`, `char_width`, `display_width`, `truncate`, `main()` 3444-3468
- `tests/cairn-board-invariance.bats` e `tests/fixtures/board-render/`
- `tests/cairn-status.bats` — 10 testes afirmam a forma do kanban (medido:
  L77, L139, L151, L190, L229, L245, L313, L330, L456, L1296)
- `tests/cairn-tracker-card.bats` — L385 e L433 afirmam a precedência de
  sufixo dentro da célula de largura fixa
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### O que já existe e é reaproveitado
- `display_width()` / `char_width()` — a medição por célula já está pronta e
  correta para `W`/`F`; o que falta é usá-la na quebra de linha.
- `clean()` — todo texto de bd/tracker já passa por ele; a lista não afrouxa
  isso.
- `tracker_key()` — o card `⧉ KEY` continua com a mesma regra de prefixo.
- `find_phase(model, n)` — resolve o balde para a fase modelada.
- `render_spans()` / `Style.paint()` — cor aplicada depois da medição.

### Padrões da casa
- Um teste que passaria com a feature removida não é prova; cada teste nomeia a
  quebra que o deixa vermelho.
- Toda asserção de status é sobre o valor exato, nunca sobre a negação.
- Docstring de módulo é a spec canônica e registra **medido versus assumido**.

### Medições feitas na abertura desta fase (2026-08-05)
- O board real deste repositório, `--width 100`: `READY (37)`, `DOING (0)`,
  `BLOCKED (0)`; 15 linhas visíveis mais `+22 more`; duas colunas inteiramente
  vazias; nenhum título íntegro. É literalmente o defeito que o card descreve.
- `groups` no repositório real: 1 grupo de milestone (`v1.5 Legible State`) com
  10 baldes (fases 20-29, duas delas sem issue aberta) e 1 grupo `unphased`
  com 6 issues.
- `bats` total do repositório: 39 arquivos, ~555 testes.

### Integration Points
- `cairn/scripts/cairn-status.py` — só o caminho de render de terminal.
- `tests/fixtures/board-render/*.txt` — **regenerados de propósito**, com o
  diff lido linha a linha e explicado no SUMMARY.
- `tests/cairn-status.bats`, `tests/cairn-tracker-card.bats` — testes
  **reescritos**, nunca apagados.
- Arquivo de teste novo para as propriedades novas (largura dos símbolos,
  título longo, alinhamento entre modos, nada perdido).

</code_context>

<specifics>
## Specific Ideas

- **Regenerar é o entregável; o diff é a evidência.** As sete referências foram
  congeladas pela fase 20 justamente para que uma mudança de render fosse
  impossível de fazer em silêncio. Regenerar para um teste passar é o verde
  falso mais caro deste projeto. A ordem é: mudar o render → **ler** o diff das
  sete → escrever no SUMMARY o que mudou em cada uma e por quê → commitar a
  regeneração como ato próprio e visível.

- **Duas das sete não devem mudar**, e isso é uma previsão falseável:
  `plain.txt` (fronteira da fase 22) e `brief.txt` (três linhas, nenhuma de
  tarefa). Se qualquer uma das duas se mover, alguma coisa vazou de escopo.

- **Um defeito pré-existente que esta fase não conserta, e deve registrar:** o
  render de hoje já usa caracteres `east_asian_width=A` fora dos símbolos de
  etapa — `▶` (`g_next`), `◆` (`g_who`), `·` (`g_stale` e `sep`), `…` (`ell`) e
  todo o box-drawing `┌┬┐└┴┘─│`. Ou seja, o board de hoje **já** desalinha em
  terminal com locale CJK, e o critério 2 desta fase cobre só os símbolos de
  etapa. A lista agrupada elimina o box-drawing e torna `…` raro na lista por
  efeito colateral; os outros ficam. Isso vira issue bd `discovered-from`, não
  escopo silencioso.

- **A fase 23 roda em paralelo e vai precisar de um símbolo próprio para
  `not-applicable`, distinto de `✓`.** O conjunto adotado aqui deixa livres, com
  `east_asian_width=N`: `⊘` U+2298, `⦸` U+29B8, `∅` U+2205, `⋯` U+22EF. Não
  consumir esse espaço é parte do contrato desta fase.

</specifics>

<deferred>
## Deferred Ideas

- Cabeçalho que nomeia o milestone aberto e admite quando não há nenhum —
  BOARD-04, fase 22.
- `--plain` deixar de ser o fallback não-TTY, e o não-TTY passar a emitir a
  lista agrupada em texto puro — PIPE-02/PIPE-03, fase 22. Esta fase entrega o
  render que aquela vai emitir.
- Fase bloqueada por ciclo arquivado, e aresta `discovered-from` contando como
  bloqueio — FIX-04, fase 25.
- Fase com um plano de três lendo como `executed` — FIX-05, fase 25. Afeta o
  símbolo `◕` que esta fase pinta, e é por isso que D-05 diz que o símbolo de
  fase descreve disco e nada mais.
- Board HTML agrupado — sem requisito, sem fase.
- Glifos `east_asian_width=A` remanescentes fora dos símbolos de etapa —
  issue bd nova, sem fase.

</deferred>

---

*Phase: 21-The grouped board*
*Context gathered: 2026-08-05*
