# Phase 18: Parallel phase execution - Context

**Gathered:** 2026-07-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Duas fases independentes passam a rodar de verdade ao mesmo tempo, cada agente na
própria worktree, e a junção do trabalho **reporta** o que aconteceu em vez de
escolher um vencedor.

Requisitos: PAR-01 … PAR-05. Issues bd: ver `18-BEADS-MAP.md`.

Herdado e **não reaberto**: o lease da fase 15 é o mecanismo de exclusão (identidade
é o caminho da worktree, TTL de 4h, a issue de lease carrega só o label `lease`); o
journal da fase 16 é o registro que sobrevive a duas escritas concorrentes; a
corroboração da fase 13 é o que torna um resultado paralelo confiável. Medido e
fechado: **`bd list` e `bd create`/`bd update` a partir de uma segunda worktree caem
no mesmo banco** — sem banco local, sem daemon, sem registro global. O roadmap
marcava só a leitura como medida; a escrita foi medida nesta sessão e cai também.
Isto **fecha metade do research** que o roadmap pedia para esta fase.

</domain>

<decisions>
## Implementation Decisions

Estas quatro decisões não vêm de hipótese. As fases 14 e 15 deste milestone foram
executadas **de verdade em paralelo**, em duas worktrees, como ensaio manual desta
fase. O que quebrou lá é o que define o desenho aqui — ver `<specifics>`.

### Quem cria a worktree

- **D-01: o cairn cria, nomeada e determinística.** `../<repo>-phase-<N>` na branch
  `phase/<N>-<slug>`, e o subagente recebe o caminho explícito. A reconciliação
  sabe qual branch juntar porque foi ela quem nomeou.

  Rejeitado deixar o harness criar (`isolation: "worktree"` da tool Agent): a
  worktree é temporária e de nome gerado, então a reconciliação teria que
  **perguntar ao agente onde ele trabalhou** — informação autodeclarada, o mesmo
  vício que a fase 17 rejeitou ao pôr a lista do que foi lido no coletor em vez de
  na narrativa do agente. E amarraria o cairn a um recurso de um harness
  específico, quando o resto do plugin é `git` e `bd` e nada mais.

### O que a reconciliação faz

- **D-02: detectar e reportar a edição convergente**, além do conflito de merge
  comum. Uma linha que as duas branches tocaram é sinalizada **mesmo quando o git
  a resolveu sozinho por serem idênticas**.

  Este é o coração da fase, e ele existe porque aconteceu: as fases 14 e 15
  editaram a mesma contagem de `13` para `14` por razões diferentes — cada uma
  tinha acrescentado uma checagem. O git viu duas mudanças idênticas e tomou uma.
  A árvore mergeada ficou com **15 checagens**, uma docstring dizendo **14**, e
  **dois itens numerados 13**.

  A forma exata importa para quem for construir o detector, e ela é reproduzível
  hoje (`git merge-tree --write-tree b9c608f b0466aa`, os dois pais reais do
  merge `672e754`):

  - o git reportou **um** conflito, e ele foi em `cairn/docs/commands/doctor.md`
    — um bloco de relatório de exemplo, **outro arquivo**;
  - `tests/cairn-doctor.bats` e `cairn/scripts/cairn-doctor.py` — que carregam a
    contagem convergente **e**, cada um, o bloco distinto que cada fase
    acrescentou — mergearam **limpos**;
  - a linha convergente é literalmente a mesma dos dois lados:
    `assert_json_eq "$output" '.checks | length' '13'` → `'14'`.

  Ou seja: o mesmo arquivo pode carregar a convergência e a divergência ao mesmo
  tempo, e ainda assim não conflitar, porque as duas ficam longe uma da outra. O
  merge estava limpo no arquivo que importava, e estava errado.

  Conflito de merge o git já reporta; ninguém precisa do cairn para isso. O que só
  o cairn pode reportar é a concordância acidental — e é justamente a classe que
  passa despercebida, porque não interrompe nada.

  Rejeitado só conflito de merge: cumpre o PAR-04 ao pé da letra e deixa passar
  exatamente o erro que a rodada manual produziu. Rejeitado não fazer merge
  nenhum: joga fora a parte que a rodada manual mostrou ser mecanizável.

### Os arquivos de planejamento

- **D-03: proibidos na worktree, reconciliados no final.** O agente paralelo não
  escreve em `STATE.md`, `ROADMAP.md` nem `REQUIREMENTS.md`; quem reconcilia aplica
  as marcações de todas as fases de uma vez, na árvore principal.

  Não é precaução teórica: os três são a superfície de colisão **garantida**, porque
  toda fase escreve nos três. Na rodada manual os cinco executores foram instruídos
  a não tocá-los e nenhum conflitou — a regra é o que fez o ensaio funcionar.

  Rejeitado deixar cada fase escrever o seu e o merge resolver: põe os três arquivos
  que decidem o que o cairn acha que aconteceu direto no caminho do conflito.

  **Registrado e não escolhido:** a variante "proibidos, e a reconciliação falha se
  uma branch de fase mexeu num arquivo de planejamento" — regra por mecanismo em vez
  de por instrução, na linha do que a fase 17 fez com as ferramentas do investigador.
  Fica como candidata natural se a regra por instrução for violada uma vez.

### A postura default

- **D-04: paralelizar por default, anunciando antes.** Decisão do Felipe, tomada
  contra a recomendação oposta, e registrada como dele.

  A recomendação era sequencial por default com `--parallel` para optar: spawnar N
  agentes que escrevem código em N worktrees é a ação mais irreversível que o cairn
  faz. A escolha foi a leitura literal do PAR-01 — *"para de anunciar o paralelismo
  e rodar em fila"* — e ela é defensável: um comando que detecta paralelismo,
  anuncia paralelismo e então enfileira é precisamente a desonestidade que este
  milestone existe para eliminar.

  O anúncio antes de começar não é decoração: é o ponto onde o operador interrompe.
  Ele já existe no `/cairn:autonomous` (passo 0.4) e passa a dizer quantas fases
  correm e por quê.

### Claude's Discretion

- Nome exato do script e das suas subcamadas de comando.
- Forma do relatório de reconciliação, desde que separe conflito de merge de edição
  convergente e nomeie arquivo e linha nos dois casos.
- Como a limpeza de worktree órfã e de lease morto é oferecida (o padrão da casa é
  leitura por default, escrita atrás de flag nomeada).
- Quantas fases no máximo correm de uma vez, se houver um teto.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O que as fases anteriores travaram e esta consome
- `.planning/phases/15-phase-lease/15-CONTEXT.md` — o lease é o mecanismo do PAR-03;
  identidade por caminho de worktree, TTL de 4h, e a limitação aceita (dois agentes
  na MESMA worktree seguem indistinguíveis — fora do alvo desta fase também)
- `.planning/phases/16-transition-journal/16-CONTEXT.md` — D-01/D-02: o journal é
  escritor único e append-only; é ele que registra o que cada execução paralela fez
- `.planning/phases/13-state-corroboration/13-CONTEXT.md` — D-01 (nunca grava sozinho,
  nunca para o fluxo), D-02 (script reporta, prosa pergunta)
- `.planning/phases/17-semantic-escalation/17-CONTEXT.md` — D-01: coletor em código
  produz a lista, agente não autodeclara o que leu. Mesmo princípio da D-01 daqui.

### Pesquisa
- `.planning/research/PITFALLS.md` — os modos de falha de execução concorrente
- `.planning/research/ARCHITECTURE.md` — reportar e exigir confirmação, nunca
  reconciliar sozinho

### Código
- `cairn/scripts/cairn-status.py` — `parallelism()` já computa `runnable` /
  `blocked` / `declared` / `note`; esta fase consome esse cálculo, **não o
  reimplementa**
- `cairn/scripts/cairn-lease.py` — `acquire` / `release` / `renew` / `status`, e o
  contrato de metadados que este script não pode driblar
- `cairn/scripts/cairn-journal.py` — escritor único; toda transição passa por ele
- `cairn/commands/autonomous.md` — o passo 0.4 (anúncio) e o laço por fase
- `cairn/commands/work.md` — já consulta o lease
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`,
  `die()`, um bats por script, docstring como spec

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parallelism()` em `cairn-status.py` já responde "quais fases podem correr agora e
  o quanto essa afirmação é honesta". Esta fase é a consumidora que faltava.
- `cairn-lease.py` já resolve exclusão mútua por worktree e já sabe soltar lease
  morto — o PAR-03 e metade do PAR-05 são wiring, não invenção.
- `cairn-journal.py` já é atômico sob append concorrente (`O_APPEND` + um `os.write`)
  — o registro de duas execuções simultâneas não precisa de nada novo.
- `git worktree add/list/remove` e `git merge` são a base; nada de biblioteca.

### Established Patterns
- Script reporta, prosa decide. O script desta fase prepara e reconcilia; quem
  spawna agente é a prosa do `/cairn:autonomous`.
- Escrita atrás de flag nomeada, leitura por default.
- Um teste que passaria com a feature removida não é prova.

### Integration Points
- Script novo + par `.sh` + `tests/<basename>.bats`.
- `cairn/commands/autonomous.md` — o laço passa a ser paralelo por default.
- `cairn-lease.py` — chamado na preparação e na limpeza.
- `cairn-journal.py` — chamado a cada aquisição/liberação e ao reconciliar.

</code_context>

<specifics>
## Specific Ideas

O ensaio manual desta fase já aconteceu: **as fases 14 e 15 deste milestone foram
executadas em paralelo de verdade**, em duas worktrees, por dois agentes. Quatro
achados, e os quatro são o desenho desta fase:

1. **Independência de dependência não é independência de arquivo.** 14 e 15 não têm
   aresta entre si no roadmap e ainda assim colidiram em cinco arquivos. O grafo diz
   o que pode começar junto, nunca o que pode terminar junto.
2. **Um merge textualmente limpo não é um merge correto.** O git reportou um
   conflito, num arquivo; o dano real estava noutro, na parte que ele juntou em
   silêncio. Ver a reprodução exata na D-02 — ela é o fixture desta fase.
3. **A superfície de reconciliação é o planejamento, não o código.** Os cinco
   executores foram proibidos de tocar em `STATE`/`ROADMAP`/`REQUIREMENTS` e nenhum
   conflitou. A proibição é o que fez funcionar.
4. **O paralelismo é limitado por worktree, não pelo grafo.** Duas fases livres no
   grafo e uma worktree só não são duas fases paralelas.

</specifics>

<deferred>
## Deferred Ideas

- Reconciliação semântica automática de edição convergente (escolher qual das duas
  intenções vence) — fora de escopo por construção: o PAR-04 exige reportar.
- Paralelismo entre repositórios ou entre máquinas — o lease é por worktree de um
  repo; cruzar máquina exige o journal durável (JOUR-06, v2).
- Falhar a reconciliação quando uma branch de fase tocou arquivo de planejamento —
  registrado na D-03 como a evolução por mecanismo da regra por instrução.

</deferred>

---

*Phase: 18-Parallel phase execution*
*Context gathered: 2026-07-31*
