---
phase: 21-the-grouped-board
plan: "03"
subsystem: cairn-status
tags: [docstring, spec, edge-cases, bats, beads, provenance]

requires:
  - phase: 21-the-grouped-board
    provides: "a lista agrupada em toda largura (planos 21-01 e 21-02)"
provides:
  - "o docstring de módulo descrevendo a lista agrupada, com medido versus assumido versus deliberado"
  - "quatro bordas com teste: board vazio, issue em duas raias, id escondido atrás do +k more, e a forma estreita"
  - "três achados como issue bd com aresta discovered-from"
affects: [22-non-tty-split, 23-not-applicable-state]

tech-stack:
  added: []
  patterns:
    - "Docstring de módulo como spec canônica: cada passo separa MEDIDO, ASSUMIDO e DELIBERADO"
    - "Premissa do fixture medida ANTES de escrever a asserção, e afirmada num bloco próprio para falhar nomeando a premissa e não o renderizador"
    - "Quebra de cada teste aplicada de verdade ao fonte e medida, com restauração por cópia em /tmp e nunca por git checkout"

key-files:
  created: []
  modified:
    - cairn/scripts/cairn-status.py
    - tests/cairn-grouped-board.bats

key-decisions:
  - "O docstring registra os glifos east_asian_width=A que CONTINUAM no arquivo (▶ ◆ · …), em vez de só celebrar os cinco que foram medidos como N"
  - "A tensão D-08 entra no passo 5b por extenso, com a medição do piso de 92 células, em vez de virar uma frase vaga sobre largura fixa"
  - "Quatro bordas, não três: a forma estreita (NARROW_BODY) foi inventada no 21-02 e precisava do teste que a reprova"
  - "Três issues, não duas: o transbordo do painel de fases é um terceiro achado, medido ao ler o diff de w50"
  - "A suíte inteira NÃO foi rodada nesta worktree — recusa registrada, com o motivo medido"

requirements-completed: [BOARD-02, BOARD-03, BOARD-05, BOARD-06]

coverage:
  - id: D1
    description: "O docstring descreve a lista agrupada, e nenhuma menção a kanban ou degrade descreve o presente"
    verification:
      - kind: other
        ref: "grep 'kanban|stacked lanes|raw list' cairn-status.py — 3 ocorrências, todas em pretérito ('lived here until Phase 21', 'Phase 21 replaces')"
        status: pass
      - kind: unit
        ref: "ast.parse() sobre o arquivo — diff só de docstring e comentário"
        status: pass
    human_judgment: false
  - id: D2
    description: "Board sem grupo nenhum diz que não há trabalho aberto e ainda imprime as contagens"
    requirement: "BOARD-06"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#a board with no open work says so, and still prints its counts"
        status: pass
      - kind: other
        ref: "quebra medida: `return []` cedo em render_groups() apaga a linha de contagens E o '(no open work)' — o render passa a começar em 'done: 0'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Uma issue que chega por duas raias aparece duas vezes, uma por ocorrência, cada uma com sua raia"
    requirement: "BOARD-06"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#an issue that arrives on two lanes is rendered once per arrival"
        status: pass
      - kind: other
        ref: "premissa medida antes: bd list --status in_progress devolve ['dup-002'] e bd blocked devolve ['dup-002'] nesta máquina"
        status: pass
      - kind: other
        ref: "quebra medida: dict.fromkeys() em group_rows() colapsa as duas em uma, e 'blocked by dup-001' some do board enquanto a linha de contagens ainda diz 'blocked 1'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Um id escondido atrás do +k more não alarga a coluna de id das linhas visíveis"
    requirement: "BOARD-03"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#an id hidden behind +k more does not widen the id column"
        status: pass
      - kind: other
        ref: "quebra medida: id_w calculado sobre bucket['issues'] em vez de sobre as linhas emitidas reprova o teste (EXIT=1)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A forma estreita cai o corpo sob o id, e isso é legibilidade e não correção"
    requirement: "BOARD-03"
    verification:
      - kind: integration
        ref: "tests/cairn-grouped-board.bats#a narrow width drops the body under the id instead of squeezing it"
        status: pass
      - kind: other
        ref: "quebra medida com NARROW_BODY = 0: os DOIS testes de BOARD-03 continuam verdes e só este fica vermelho"
        status: pass
    human_judgment: false
  - id: D6
    description: "Os achados desta fase são trabalho rastreável, não prosa de SUMMARY"
    verification:
      - kind: other
        ref: "CairnGo-uz6, CairnGo-hbo e CairnGo-cdx existem no bd, cada uma com aresta discovered-from para a issue da fase que a produziu"
        status: pass
    human_judgment: false

duration: 85min
completed: 2026-08-05
status: complete
---

# Phase 21 Plano 03: A spec canônica, as bordas, e os achados roteados Summary

**O docstring de módulo voltou a descrever o renderizador que existe — a lista agrupada, com MEDIDO, ASSUMIDO e DELIBERADO separados em cada afirmação — quatro bordas ganharam teste com a quebra de cada uma aplicada ao fonte e medida, e os três achados da fase saíram do SUMMARY e viraram issue bd com aresta `discovered-from`.**

## Performance

- **Duration:** ~85 min
- **Tasks:** 3
- **Files modified:** 2

## O docstring: o que passou a dizer

O passo 5 dizia `box-drawing kanban board … degrading gracefully — columns
(>= 64 cols) → stacked lanes (>= 40 cols) → raw list (< 40 cols)`. Descrevia
código apagado, o que é pior que não descrever nada, porque parece informação.

Agora descreve a hierarquia vinda de `groups`, a forma da linha, a regra de
quebra (o token único mais largo que a coluna **transborda** em vez de ser
partido, porque um token cortado é uma mentira sobre o título e um token que
transborda é a quebra do próprio terminal), o teto por balde, e a linha de
contagens compartilhada com `--brief`. E separa, como o resto do arquivo faz:

- **MEDIDO** — os cinco símbolos `◌ ◔ ◕ ✓ ⧗` são `east_asian_width=N`; `○`
  U+25CB, `◑` U+25D1 e `◆` U+25C6 são `A` e por isso foram descartados.
- **MEDIDO, e não corrigido aqui** — os glifos `A` que **continuam** no arquivo
  fora dos símbolos de etapa: `▶` (`g_next`), `◆` (`g_who`), `·` (`g_stale` e
  `sep`) e `…` (`ell`). O board segue desalinhando em locale CJK por causa
  deles. Um docstring que só celebrasse os cinco escolhidos daria a impressão de
  problema resolvido.
- **ASSUMIDO** — que uma issue chega no máximo duas vezes. A fila FIFO de
  `group_rows()` não depende do número; a suposição é só sobre o que se observa.
- **DELIBERADO** — a linha de fase nunca usa o símbolo de bloqueado, com o
  motivo FIX-04 escrito.

O passo 5b trocou "Below the columned/stacked board" por "Below the grouped
list" e ganhou a tensão D-08 por extenso, com a medição: o painel tem piso de
**92 células** e estoura de 64 a 90 colunas — inclusive em larguras que já
estavam no caminho largo antes da fase 21, o que é o que prova que o defeito é
dele e não da lista.

A linha de `--max-rows` passou a dizer "por balde". A de `--ascii` dizia
"+-| borders"; as bordas saíram no 21-02, e a linha agora fala dos símbolos de
etapa de um caractere.

Nenhuma linha de código mudou nesta task.

## As quatro bordas, e a quebra medida de cada uma

Nenhuma delas foi escrita e declarada verde: em cada uma a quebra foi
**aplicada ao fonte**, medida, e o fonte restaurado de uma cópia em `/tmp`
(nunca `git checkout`).

**8. Board sem trabalho aberto.** Fixture: repo novo com `bd init` e zero
issues — não o fixture da suíte com tudo fechado, porque `done: N` deve ser zero
aqui e fechar seis issues faria `done: 6` esconder um bug da linha de contagens
atrás de um número plausível. Quebra medida: `return []` cedo em
`render_groups()` apaga a linha de contagens **e** o `(no open work)`, e o
render passa a começar direto em `done: 0` — um board vazio vira
indistinguível de um board que falhou em renderizar.

**9. Issue que chega por duas raias.** A premissa foi medida **antes** de
escrever a asserção, como o plano exigia: nesta máquina,
`bd list --status in_progress` devolve `['dup-002']` e `bd blocked` devolve
`['dup-002']` — o mesmo id, de duas consultas independentes. O render carrega
as duas ocorrências, uma com `◕` e outra com `⧗ … blocked by dup-001`. O teste
afirma a premissa num bloco separado, para que uma mudança no `bd` falhe ali,
nomeando a premissa, e não lá embaixo parecendo regressão do renderizador.
Quebra medida: `dict.fromkeys()` sobre `bucket["issues"]` colapsa as duas numa
só, `blocked by dup-001` some do board inteiro, e a linha de contagens continua
dizendo `blocked 1` — o board passa a contradizer o próprio cabeçalho.

**10. Id escondido atrás do `+k more` não alarga a coluna.** Quebra medida:
calcular `id_w` sobre `bucket["issues"]` em vez de sobre as linhas emitidas
reprova o teste. Com `brd-9999999999999999` (20 células) contra `brd-00N` (7), a
coluna do título andaria 13 células por causa de uma linha que ninguém vê.

**11. A forma estreita.** Esta é minha, não do plano: `NARROW_BODY` foi
inventado no 21-02 e não tinha teste que a reprovasse. Quebra medida com
`NARROW_BODY = 0`: **os dois testes de BOARD-03 continuam verdes** e só este
fica vermelho — que é exatamente o que a torna um teste honesto e não uma
carona. Um teste que passaria com a funcionalidade removida não é prova.

## Deviations from Plan

### 1. Quatro bordas em vez de três; `@test` de `cairn-grouped-board.bats` é 11, não 10

O plano previu 10. A borda 11 (`a narrow width drops the body under the id
instead of squeezing it`) existe porque o 21-02 introduziu `NARROW_BODY` fora do
plano, e código sem teste que o reprove é código sem prova.

### 2. Três issues em vez de duas

O plano previu duas (grupo solto sem baldes de fase; glifos `A` remanescentes).
A terceira — `CairnGo-cdx`, o transbordo de 92 células do painel de fases — foi
medida lendo o diff de `w50.txt` no 21-02 e não estava prevista em lugar nenhum.
As três carregam aresta `discovered-from` de verdade (o `bd` desta máquina
aceita `--deps discovered-from:<id>`, verificado por `bd show`):

| issue          | aponta para  | achado                                                     |
| -------------- | ------------ | ---------------------------------------------------------- |
| `CairnGo-uz6`  | CairnGo-qwu  | sem `## Milestones` no ROADMAP, a lista perde a fase inteira |
| `CairnGo-hbo`  | CairnGo-8kf  | `▶ ◆ · …` são `east_asian_width=A` e continuam em uso        |
| `CairnGo-cdx`  | CairnGo-ckv  | `PENDING PHASES` tem piso de 92 células e estoura de 64 a 90 |

Nenhuma leva rótulo `phase-N`: não têm fase, e o grupo solto é onde trabalho não
roteado deve aparecer — que é a mesma propriedade que a lista agrupada existe
para tornar visível.

### 3. RECUSADO: rodar a suíte inteira

O plano 21-03, na Task 3, mandava rodar `tests/` inteiro com a árvore parada.
**Não rodei, por instrução direta e explícita**, e registro a medição que a
justifica em vez de fingir que o critério foi cumprido:

- `uptime` durante esta fase marcou `load average` entre **13.7 e 16.8** sobre
  **8 núcleos**, com **três worktrees** (`CairnGo`, `CairnGo-phase-21`,
  `CairnGo-phase-24`) rodando bats ao mesmo tempo — os processos das outras duas
  foram vistos por `ps`, não presumidos.
- Sob essa carga, `tests/cairn-status.bats` **sozinho** levou **12:55**
  (`bats -j 2`), contra ~3:17 de `cairn-grouped-board.bats` na mesma sessão.
- Uma fase irmã ficou 135 minutos num laço de morte-e-retentativa da suíte
  inteira sem avançar um commit.

**O que rodei no lugar:** exatamente os quatro arquivos que esta fase tocou, com
o TAP inteiro em arquivo e o plano `1..N` conferido contra a soma de `ok` +
`not ok`. A suíte completa é responsabilidade da árvore principal, no merge.

### 4. RECUSADO: escriturar `STATE.md`, `ROADMAP.md` e `REQUIREMENTS.md`

Proibidos nesta worktree por instrução direta. Nenhum dos três foi tocado, e
nenhuma ferramenta de escrituração do `gsd-tools` foi executada. `bd` foi usado
só para criar as três issues de achado e fechar as quatro da fase — que é
trabalho de rastreamento, não de escrituração de estado do GSD.

## Self-Check: PASSED

- `cairn/scripts/cairn-status.py` — AST válida; 3 menções a kanban/degrade, todas em pretérito
- `tests/cairn-grouped-board.bats` — 11 `@test`
- `CairnGo-uz6`, `CairnGo-hbo`, `CairnGo-cdx` — existem no bd, com `DISCOVERED FROM` conferido por `bd show`
