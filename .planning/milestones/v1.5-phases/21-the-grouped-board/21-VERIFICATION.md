---
phase: 21-the-grouped-board
verified: 2026-08-06T21:19:28Z
status: passed
score: 4/4 critérios verificados, 4/4 requisitos entregues
behavior_unverified: 0
behavior_unverified_items: []
human_verification: []
overrides_applied: 0
gaps: []
---

# Phase 21: The grouped board — Relatório de verificação

**Goal da fase:** as três raias `READY`/`DOING`/`BLOCKED` gastavam a largura do
terminal dividida por três e cortavam todo título em ~28 caracteres. Esta fase
troca a forma: uma lista, agrupada pelo modelo da fase 20, com a etapa num
símbolo.

**Verificado em:** `HEAD=5f3a815` (árvore limpa, `git status --porcelain` vazio),
com a fase 22 já fechada por cima
**Status:** passed
**Re-verificação:** Não — verificação inicial (não existia `21-VERIFICATION.md`)

## Método

Goal-backward e adversarial. Parti dos quatro critérios do ROADMAP, localizei o
código que deveria satisfazer cada um, e então perguntei se o teste que o cobre
continuaria verde caso a propriedade fosse revertida. Onde a resposta não era
óbvia, **apliquei a quebra numa cópia fora da árvore** e medi (dois testes de
mutação, abaixo). Li `render_groups()`, `group_rows()`, `stage_symbol()`,
`issue_body_spans()`, `Style.__init__` e o despacho de `main()` inteiros, não só
os diffs. Rodei em segundo plano, lendo o log de arquivo, exatamente os dois
`.bats` que a fase tocou — **não** rodei `tests/` inteiro.

**O que rodei, e a contagem sobre o log inteiro (não sobre saída truncada):**

| comando | plano anunciado | ok | not ok | skip | exit |
| --- | --- | --- | --- | --- | --- |
| `bash cairn/scripts/cairn-test.sh --jobs 3 tests/cairn-grouped-board.bats` | `1..14` | 14 | 0 | 0 | 0 |
| `bash cairn/scripts/cairn-test.sh --jobs 3 tests/cairn-board-invariance.bats` | `1..11` | 11 | 0 | 0 | 0 |

Os dois planos conferem contra a soma `ok + not ok` — que é a conferência que
distingue um run vivo de um run morto que imprime `1..N` e executa zero testes.

## Os quatro critérios, julgados um a um

### Critério 1 — Nenhum título truncado em nenhuma largura em que a linha caiba — **ATENDIDO**

**O que medi:**

- **AST, não grep:** percorri `cairn-status.py` com `ast.parse()` e listei as
  chamadas de cada função do caminho agrupado. `render_groups` chama
  `clean, counts_parts, display_width, group_rows, issue_body_spans,
  issue_priority, len, max, render_spans, stage_symbol, str, sum, wrap_spans`.
  **`truncate` não está lá, nem em `issue_body_spans`, nem em `wrap_spans`.** A
  única ocorrência da palavra no bloco é o próprio docstring explicando a
  ausência — um grep ingênuo devolve um falso positivo aqui, e o AST não.
- **Teste:** `ok 6 — a genuinely long title is never truncated, at any width
  that holds a word`, varrendo **30, 38, 50, 60, 64, 80, 100 e 140** com um
  título de **125 caracteres** (medi o comprimento: 125, como o SUMMARY diz). O
  teste afirma que o título inteiro está no corpo E que `…`/`...` não aparecem E
  que os sufixos `DTP-142` e `cairn-tests` não foram descartados para caber.
- **Render ao vivo, neste repositório**, a 30 / 38 / 60 / 100: todo título volta
  inteiro, quebrado em continuação alinhada à coluna do corpo. A 30 colunas o id
  fica sozinho na linha e o corpo desce — a forma estreita, não um corte.
- **Um renderizador só:** `main()` linha 4032 é o único ramo humano
  (`render_groups`), sem limiar de largura. Confirmei por AST que
  `render_board`, `render_stacked`, `render_raw`, `make_cell`, `lane_rows` e
  `lane_header_text` **não existem mais como nome referenciado** — sobrevivem
  apenas em comentários no pretérito. Idem as constantes `STACK_BELOW`,
  `RAW_BELOW`, `MIN_INNER`, `MAX_INNER` e `N_LANES`. `LANES` fica, e continua
  tendo leitor (`render_plain`, `group_rows`, `stage_symbol`).

**A exceção documentada é exercitada, não é frase:** um token único mais largo
que a coluna transborda em vez de ser partido, e o fixture carrega esse caso
(`brd-203`, URL de 72 caracteres). `ok 9` afirma que **toda** linha que passa da
largura é prefixo + um token, e que esse token é o da URL.

### Critério 2 — Símbolos de etapa de largura simples, provados por `unicodedata` — **ATENDIDO**

Este é o critério que o pedido mandou olhar com atenção: o teste tem que afirmar
a **propriedade**, não o desenho.

**O teste afirma a propriedade.** `ok 5 — every stage symbol is one cell,
measured by unicodedata, not by eye` carrega os cinco símbolos **para fora do
script** (`cs.Style({'ascii': False, ...})`, o módulo carregado por
`importlib`), nunca de literais retypados, e assere
`unicodedata.east_asian_width(ch) == 'N'` e `cs.char_width(ch) == 1`. Um literal
copiado para o teste continuaria verde depois de alguém trocar o script; ler do
script não deixa.

**Medi eu mesmo, com a árvore parada:**

| símbolo | codepoint | `east_asian_width` | `char_width()` |
| --- | --- | --- | --- |
| `◌` | U+25CC | N | 1 |
| `◔` | U+25D4 | N | 1 |
| `◕` | U+25D5 | N | 1 |
| `✓` | U+2713 | N | 1 |
| `⧗` | U+29D7 | N | 1 |

Fallback ASCII: `.` `o` `O` `v` `~` — cinco, distintos, um caractere, todos
`ord < 128`, e nenhum colide com `g_conflict` (`x`), `g_informs` (`!`),
`g_stale` (`*`) nem `g_card` (`#`), colisão que o próprio teste assere.

**A quebra, aplicada e medida (teste de mutação, numa cópia em scratchpad —
nunca na árvore):** troquei `◕` (U+25D5, `N`) por `◑` (U+25D1, `A`) e rodei o
corpo da asserção contra a cópia mutada. Falhou, nomeando o glifo e a classe:

```
AssertionError: '◑' U+25D1 is east_asian_width=A, not N
```

É a prova de que o critério 2 não passa por aparência: o glifo mutante desenha
igual num terminal latino e o teste o reprova mesmo assim.

**A fronteira, medida e batendo com o SUMMARY:** os glifos `A` que **continuam**
no arquivo fora dos símbolos de etapa. Medi os nove e o resultado é exatamente o
que o SUMMARY declara — nem um a mais:

`g_next` `▶` = A · `g_who` `◆` = A · `g_stale` `·` = A · `ell` `…` = A ·
`sep` ` · ` contém A. Já `g_dep` `⧗`, `g_conflict` `✗`, `g_informs` `⚠` e
`g_card` `⧉` são todos N.

O critério 2 do ROADMAP diz "os **símbolos de etapa** são todos de largura
simples" — escopo que estes quatro não invadem. A fase os declarou como achado
(`CairnGo-hbo`), e a fase 22 os converteu em **fronteira escrita** no docstring
do módulo ("GUARANTEED IN A WESTERN LOCALE AND NOT IN A CJK ONE", com as 53
ocorrências medidas, 12 delas letras acentuadas da própria prosa do board). Não
é lacuna: é limite declarado.

### Critério 3 — `--ascii` produz conjunto equivalente e as colunas fecham alinhadas — **ATENDIDO**

- **O conjunto é ASCII puro e de um caractere:** medido acima.
- **Teste:** `ok 8 — --ascii swaps the symbols and moves no column` compara as
  duas saídas linha a linha em **células** (`display_width`), afirma o mesmo
  número de linhas físicas, a mesma sequência de `(kind, key)`, o mapeamento
  posição-a-posição de cada símbolo, e que nenhum glifo unicode vazou para a
  saída ASCII.
- **Medi ao vivo neste repositório, que é um fixture mais hostil que o do
  teste:** a coluna do corpo começa **na célula 21 nos dois modos** — que é o
  que "as colunas fecham alinhadas" afirma. Das 76 linhas, 3 diferem em largura
  total, e todas as 3 pela mesma razão de **conteúdo**, não de coluna: um `…`
  dentro do texto (`FIX-01 … FIX-05`, `AUTO-01 … AUTO-08`) vira `...` no
  `asciify`, +2 células, e o `—` do rodapé vira `-`. A coluna não se moveu; o
  texto ficou mais comprido.

**O limite honesto do critério, medido:** `--ascii` não torna a saída inteira
ASCII. Restam `á â ã ç é ê` (títulos de issue e a seção `PURPOSE`, prosa em
português) e `—` (dentro de um título de issue e como marcador de célula vazia
da tabela `PENDING PHASES`). Isso é deliberado e está no docstring de
`Style.asciify`: "Issue titles keep their own characters". O critério fala de
"um **conjunto** equivalente sem nenhum caractere fora de ASCII", e o conjunto —
os cinco símbolos — é ASCII puro. Registro a medição para que ninguém leia o
critério como uma garantia sobre a saída inteira.

### Critério 4 — Linha bloqueada nomeia o bloqueador na própria linha — **ATENDIDO**

- **Código:** `issue_body_spans()` faz `", ".join(clean(b) for b in
  as_str_list(iss.get("blocked_by")))` — **todos**, não o primeiro.
- **Teste:** `ok 7 — a blocked row names every blocker it has, on the row
  itself` exige `brd-002` **e** `brd-003` depois do literal `blocked by`.
- **Exercitei a função real** com uma issue de dois bloqueadores e li a saída:
  `Wait on two things at once  blocked by brd-002, brd-003`.
- **A quebra, aplicada e medida (segunda mutação, em cópia):** trocando o join
  por `as_str_list(...)[0]` — que é o que `make_cell()` fazia — a saída vira
  `blocked by brd-002` e a asserção falha nomeando o que sumiu:
  `AssertionError: brd-003 NAO nomeado`.

Este repositório tem 0 issues bloqueadas hoje, então não há amostra viva no
board; a evidência é o código real executado com dado de duas dependências, o
que é comportamento medido e não presunção.

## As cinco referências regeneradas — o ponto que o pedido mandou checar

A fase 20 congelou sete referências byte a byte exatamente para que uma mudança
de render fosse impossível de fazer em silêncio, e a 21 é a fase que muda o
render de propósito. Recomputei o tamanho de cada objeto **direto do git**
(`git cat-file -s`) em quatro pontos da história:

| arquivo | pré-21 (`784483e`) | pós-`21-01` (`6cec88b`) | pós-`21-02` (`b43138e`) | previsto pelo SUMMARY | bate? |
| --- | --- | --- | --- | --- | --- |
| `w100.txt` | 1539 | **1096** | 1096 | 1539 → 1096 | sim |
| `ascii100.txt` | 1153 | **1055** | 1055 | 1153 → 1055 | sim |
| `maxrows.txt` | 1539 | **994** | 994 | mudou (`--max-rows 2` → `1`) | sim |
| `w50.txt` | 384 | 384 | **1130** | imóvel no 21-01; 384 → 1130 no 21-02 | sim |
| `w38.txt` | 357 | 357 | **1141** | imóvel no 21-01; 357 → 1141 no 21-02 | sim |
| `plain.txt` | 332 | 332 | 332 | imóvel nos dois | sim |
| `brief.txt` | 183 | 183 | 183 | imóvel nos dois | sim |

**Cinco moveram, duas não, e cada previsão de imobilidade estava escrita no
plano ANTES do run.** Nenhuma se moveu contra a previsão.

**O diff foi lido, e há três evidências independentes disso:**

1. **A explicação por arquivo existe em nível de conteúdo**, não de "regenerei",
   e existe em dois lugares: o `21-01-SUMMARY.md` / `21-02-SUMMARY.md` e a
   **mensagem dos próprios commits** `6cec88b` e `b43138e`, que carregam o diff
   por arquivo (quais cinco linhas do grid saem, quais entram, quais quatro
   títulos voltam inteiros, por que `<- brd-001` some, por que `--max-rows`
   passou de 2 para 1).
2. **A comparação foi feita com `cmp` contra uma cópia em `/tmp` tirada ANTES**,
   e não com `git diff` — porque uma área de stage errada pode fabricar um "não
   mudou" e `cmp` não pode. Está registrado no plano e na mensagem do commit.
3. **O achado que só existe porque alguém leu o diff:** `render_stacked()`
   devolvia `lines + footer_lines(...)` e **nunca** chamava
   `phase_panel_lines()`. O painel de fases inteiro era engolido, em silêncio,
   em toda largura abaixo de 64 — e apareceu como "o `PENDING PHASES` surge a 50
   colunas pela primeira vez" ao comparar `w50`. Não estava em plano nenhum.
   Regeneração cega não produz esse achado.

**As âncoras dos testes foram trocadas junto**, e por um motivo que importa:
apontavam para `DOING (1)` e `BLOCKED  brd-005`, bytes que nenhum renderizador
produz mais. Foram trocadas pelo que faz `w50` e `w38` serem **diferentes** de
`w100` (em `w50` um título quebra ao lado do id; em `w38` o corpo cai abaixo
dele). Ancorar num byte que `w100` também tem deixaria qualquer um dos dois
virar cópia silenciosa de `w100` e ainda passar.

`tests/cairn-board-invariance.bats` roda hoje 11/11 verde, incluindo os dois
testes que **perturbam** o fixture e exigem que a comparação falhe nomeando a
perturbação — a proteção contra um comparador que sempre concorda.

## Requisitos

| Requisito | Issue | Estado | Evidência |
| --- | --- | --- | --- |
| BOARD-06 — board agrupado, milestones abertos primeiro, fases dentro, trabalho solto por último | `CairnGo-qwu` | closed | `ok 4`; render vivo: `v1.5 Legible State` no topo, fases 20–30 dentro, `No milestone` por último |
| BOARD-02 — etapa num símbolo de largura simples, fallback ASCII | `CairnGo-8kf` | closed | `ok 5` + medição própria + mutação `◕`→`◑` reprovada |
| BOARD-03 — título de tarefa nunca truncado no render humano | `CairnGo-ckv` | closed | `ok 6` (8 larguras) + AST sem `truncate()` no caminho + render vivo a 30/38/60/100 |
| BOARD-05 — linha bloqueada nomeia o bloqueador | `CairnGo-3y2` | closed | `ok 7` + função exercitada + mutação `[0]` reprovada |

`21-BEADS-MAP.md` não tem gap: os quatro requisitos estão mapeados e as quatro
issues estão fechadas. `.planning/REQUIREMENTS.md` marca os quatro `[x]`.

## Anti-padrões

Varri `cairn-status.py`, `cairn-grouped-board.bats`, `cairn-board-invariance.bats`
e `regenerate.sh` por `TBD|FIXME|XXX|HACK|PLACEHOLDER`: **zero ocorrências**.
Nenhum marcador de dívida sem referência formal.

## Fronteiras medidas — declaradas, roteadas, e fora do escopo dos quatro critérios

Nenhuma destas é lacuna. Todas foram declaradas pela própria fase antes de eu
encontrá-las, e todas viraram trabalho rastreável. Registro a medição para que a
fase 27 as veja como série, não como surpresa.

| o que | medição minha, hoje | issue | por que não é lacuna |
| --- | --- | --- | --- |
| A tabela `PENDING PHASES` ainda **trunca** o título da fase | a 50/80/100 colunas sai `Measure…`, `Disagre…`, `Did it…`; só a 140 vem inteiro | `CairnGo-cdx` (closed na 22) | BOARD-03 escopa a "título de uma **tarefa**", e a tabela é largura fixa por desenho, fora da lista agrupada. A fase 22 corrigiu o **transbordo** (`ok 1` da grouped-board hoje), não a truncagem |
| Glifos `east_asian_width=A` fora dos símbolos de etapa | `▶ ◆ · …` = A, confirmados um a um | `CairnGo-hbo` (closed na 22) | o critério 2 escopa aos símbolos de etapa; a 22 transformou o resto em fronteira escrita no docstring |
| A linha de contagens estoura larguras estreitas | a `--width 30` ela ocupa 40 células | `CairnGo-7yw` (**aberta**) | nenhum dos quatro critérios fala da linha de contagens; `ok 9` **exclui** a linha explicitamente e diz por quê, em vez de dobrar a asserção até ela passar |
| Sem `## Milestones` no ROADMAP, tudo cai em `No milestone` sem linha de fase | — | `CairnGo-uz6` (closed na 22) | achado da fase, roteado; a 22 fechou com `ok 3` |

Uma nota sobre a última coluna: o padrão que se repete nas quatro é o oposto do
verde falso. Em cada caso a fase mediu o defeito, escreveu o limite no lugar em
que ele morde, e recusou enfraquecer uma asserção para acomodá-lo — `ok 9`
excluindo a linha de contagens com a razão escrita é o exemplo mais claro.

## O que não consegui verificar

- **Uma linha bloqueada renderizada ao vivo neste repositório.** `blocked 0`
  hoje, então não há amostra no board real. Compensei executando
  `issue_body_spans()` com uma issue de dois bloqueadores e lendo a saída — é
  comportamento medido do código real, mas não é o board inteiro com uma linha
  bloqueada dentro. `ok 7` cobre o caminho de ponta a ponta com fixture.
- **A suíte completa.** Por instrução, rodei só os dois `.bats` da fase. Não
  reafirmo nem contesto os 781/781 de `0e67930`; o que digo é que os 25 testes
  que cobrem esta fase estão verdes hoje, em `HEAD=5f3a815`.
- **Alinhamento em locale CJK.** Não tenho terminal CJK aqui e a defesa da fase
  é justamente não depender de um: os símbolos são `N` por medição. Os glifos
  `A` remanescentes são fronteira escrita, não hipótese que eu pudesse testar.

## Veredito

**passed — 4/4 critérios, 4/4 requisitos.**

Os quatro critérios da fase 21 estão atendidos no código que existe em
`HEAD=5f3a815`, não só no SUMMARY. As duas propriedades mais fáceis de fingir —
"o teste prova a largura do símbolo" e "as referências foram regeneradas com o
diff lido" — foram as que ataquei mais, e as duas resistiram: a primeira caiu na
mutação que eu apliquei (o teste reprova um glifo `A` que desenha igual), e a
segunda tem tamanho por objeto conferindo com a previsão escrita antes do run,
explicação por arquivo em nível de conteúdo, `cmp` contra cópia externa em vez de
`git diff`, e um achado (`render_stacked()` engolindo o painel de fases) que
regeneração cega não produziria.

O SUMMARY não escondeu nada que eu tenha encontrado depois. As quatro fronteiras
que ele declara batem, uma a uma, com a minha medição independente.

---

_Verificado: 2026-08-06T21:19:28Z_
_Verificador: Claude (gsd-verifier), goal-backward, postura adversarial_
