# Phase 13: State corroboration - Context

**Gathered:** 2026-07-30
**Status:** Ready for planning

<domain>
## Phase Boundary

O modelo de fase para de decidir o estado a partir de quatro nomes de arquivo e
passa a comparar fontes independentes, nomeando a discordância em vez de eleger
um vencedor. Requisitos: CORR-01 … CORR-08. Issues bd: ver `13-BEADS-MAP.md`.

A raiz é uma função: `phase_disk_state(pdir)` em `cairn/scripts/cairn-status.py`
retorna um de `none|planned|executed|verified` puramente por existência de
arquivo — nunca abre o arquivo, nunca consulta o bd, nunca consulta o git.

Esta fase constrói a corroboração e a expõe nas três superfícies que já leem de
`phase_model()`. O card rico (fase 14), o lease (15), o journal (16) e a escalada
semântica (17) consomem o que aqui for produzido.

</domain>

<decisions>
## Implementation Decisions

### Princípio que atravessa tudo (o fio condutor das quatro áreas)

- **D-01: o cairn nunca grava estado sozinho, e também nunca para o fluxo.**
  Diante de falha ou divergência ele apresenta as opções com a saída provável já
  **pré-selecionada e marcada como recomendada**, e o trabalho continua. Um enter
  resolve o caso óbvio. Isto preserva CORR-02 (nenhuma fonte vence em silêncio)
  inteiro, sem transformar cada divergência num pedido para o usuário ir digitar
  comando.
- **D-02: perguntar é trabalho do comando, não do script.** `AskUserQuestion` é
  ferramenta de agente e não existe dentro de um processo Python. Portanto
  `cairn-status.py` e `cairn-doctor.py` **reportam** (estruturado, determinístico,
  testável em bats); a prosa de `cairn/commands/*.md` é que oferece as opções.
  Isto respeita a regra da casa ("se uma frase de SKILL.md pode ser uma checagem
  de script, faça script") sem fingir que um script pode conversar.

### Exibição do conflito

- **D-03: template A — uma fase, uma linha, sempre.** O marcador e o motivo cabem
  na própria linha da fase no board. Escolhido entre quatro variantes renderizadas
  no terminal:

  ```
  PENDING PHASES  5
    13  State corroboration      not planned
    14  Phase card               ✗ conflict — disco executed, bd 2 abertas
    15  Phase lease              not planned  ·  waits on 13
    16  Transition journal       ⚠ divergente — STATE.md aponta 16, disco verified
    17  Semantic escalation      not planned  ·  waits on 13 and 16

    ✗ 1 bloqueia · ⚠ 1 informa — /cairn:doctor para o itemizado
  ```

  O motivo é truncado quando não cabe; o itemizado completo por fonte vive em
  `/cairn:doctor` e no `--json`, nunca no board.
- **D-04: terminal e HTML idênticos.** Mesmos campos, mesma leitura. Um teste
  renderiza as duas superfícies e compara — não é inspeção visual. Antecipa
  CARD-03 (fase 14) em vez de criar uma paridade para consertar depois.
- **D-05: o próximo comando depende de qual fonte discorda.** Um ponteiro velho
  no STATE.md não invalida `/cairn:work N`; disco contra bd invalida. Onde a
  saída for ambígua, o comando pergunta (D-01) em vez de escolher.

### Quórum e fontes ilegíveis

- **D-06: todas as fontes legíveis precisam concordar, sem exceção.** Sem
  maioria, sem desempate. Duas fontes legíveis discordando já é `conflict`.
  Rejeitada explicitamente a regra de maioria: ela elege um vencedor em silêncio,
  que é o que CORR-02 proíbe.
- **D-07: bd indisponível vira alerta com opções, não um veredito inventado.**
  Nem "tudo `unknown`" (board fica mudo toda vez que o bd tosse) nem "ok
  silencioso". O eixo do bd fica sem voto, o fato é dito, e o usuário recebe as
  opções de conserto pelo mecanismo de D-01.
- **D-08: a corroboração roda local e interativa apenas — não no CI.** O research
  reproduziu ao vivo um falso positivo do pickaxe na fronteira de um clone raso, e
  `actions/checkout` usa `fetch-depth: 1` por padrão, que este repo não sobrescreve.
  Corroborar sobre história truncada é corroborar sobre dado corrompido.

### Severidade

- **D-09: dois níveis, desde já: bloqueia e informa.** É o mínimo que D-05 e D-01
  exigem — sem severidade não há como dizer "depende de qual fonte discorda". O
  research alertou contra inventar níveis sobre zero dado, então o escopo é dois e
  **cada classificação nasce com justificativa escrita**, no mesmo espírito da
  allowlist de diferenças inócuas (CORR-07).
- **D-10: o ship gate barra apenas os bloqueantes.** `cairn-gate.py` e
  `cairn/capability/scripts/cairn-loop-gate.py` recebem a checagem aditiva em
  lockstep — os dois ou nenhum, porque um gate que passa enquanto o gêmeo barra é
  a mesma classe de mentira que esta fase existe para remover.

### Vínculo git (CORR-08)

- **D-11: backfill por `--link-refs` no `cairn-doctor`.** Segue o padrão já
  provado de `--fix-labels` e `--close-completed`: leitura por default, escrita
  atrás de flag nomeada, imprime cada id que tocou, idempotente. E o mais
  automático possível — o doctor oferece o backfill como opção (D-01) em vez de
  exigir que o usuário descubra a flag.
- **D-12: `post-bd-write.sh` grava o `--external-ref` no fechamento.** O hook já
  existe e já observa comandos `bd`. **Ressalva que o plano precisa endereçar:** o
  contrato dele é "fire-and-forget, nunca falha o chamador", o que significa que
  uma falha de gravação some em silêncio — exatamente a forma de bug deste
  milestone. Precisa de um teste que prove que a falha aparece em algum lugar
  observável.
- **D-13: o trailer `Bd-Issue:` é escrito pelo `prepare-commit-msg` do beads.**
  **Limitação conhecida, aceita com os olhos abertos:** este repo faz squash-merge,
  e o squash descarta os commits da branch — então o trailer some no merge
  exatamente como sumiu antes (zero de 239 commits carregam id de bd hoje). O
  trailer serve para inspeção local e para histórico não-squashado; quem realmente
  sobrevive ao merge é o `--external-ref` casado com o `(#N)` do assunto do squash.
  Não é surpresa futura: está escrito aqui.

### Claude's Discretion

- Nomes exatos das chaves aditivas no `--json` (o research sugere
  `evidence` / `corroboration` / `conflicts`; a forma final é do planner).
- Estrutura interna do itemizado no `/cairn:doctor`.
- Onde exatamente a comparação vive dentro de `phase_model()`.
- Conteúdo inicial do corpus de diferenças inócuas (CORR-07), desde que cada
  entrada carregue sua justificativa.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pesquisa deste milestone (decisões já fechadas — não reabrir)
- `.planning/research/SUMMARY.md` — resolve as quatro colisões entre os
  pesquisadores; a §"Collision 2" é a razão de a corroboração ser estrutura
  paralela e não um quinto valor de enum
- `.planning/research/ARCHITECTURE.md` §0-§1 — mapeia `phase_model()`,
  `phase_disk_state()` e `phase_next_command()` por arquivo e linha, e prova que
  alargar o enum quebra com `KeyError`
- `.planning/research/STACK.md` — o sinal de git está vazio (0 de 239 commits),
  e as receitas de git verificadas ao vivo neste repo
- `.planning/research/PITFALLS.md` — Pitfall 1 (cry-wolf), 3 (fail-open) e 4
  (o conflito que ninguém limpa) são os que esta fase precisa evitar

### Requisitos e escopo
- `.planning/REQUIREMENTS.md` — CORR-01…08 e a tabela "Decisões travadas antes
  do roadmap"
- `.planning/ROADMAP.md` §"Phase 13: State corroboration" — os 5 critérios de
  sucesso desta fase

### Convenções da casa (obrigatórias)
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `die()`,
  constantes `EXIT_*`, um `.bats` por script, docstring como spec
- `.planning/codebase/ARCHITECTURE.md` — como as peças existentes se ligam
- `CONTRIBUTING.md` — "se uma frase de SKILL.md pode ser uma checagem de script,
  faça script"

### Contexto das fases que construíram o que esta estende
- `.planning/milestones/v1.3-phases/10-phase-model/10-CONTEXT.md` — as decisões
  travadas de "uma leitura, três superfícies" e "next_command computado, nunca
  escrito à mão"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `phase_model(planning_dir, issues)` (`cairn/scripts/cairn-status.py`) — a
  leitura única que board, `--json` e HTML já consomem. Uma mudança aditiva aqui
  chega às três superfícies sem nenhum call site novo.
- A lista de issues do bd **já é buscada** antes de `phase_model()` rodar
  (`fetch_lanes(root)` em `main()`), então o eixo do bd custa zero I/O novo.
- `cairn-doctor.py` já tem os dois padrões de que esta fase precisa: o par
  leitura-por-default / escrita-atrás-de-flag (`--close-completed`), e a checagem
  de obsolescência (`claims-stale`).
- `dep_target_ids(iss)` já sabe que o bd reporta arestas em duas formas
  diferentes — precedente de que uma fonte pode mentir por omissão.

### Established Patterns
- Marcadores de bloco gerado (`<!-- cairn:generated:...:start/end -->`) com
  semântica replace-only-inner, caso o itemizado precise ser embutido em markdown.
- Códigos de saída são contrato documentado: `0` ok/não-aplicável, `2` uso,
  `5` bd indisponível, `6` gate, `7` doctor falhou. `5` nunca é falha de checagem.

### Integration Points
- `phase_next_command(p)` faz **subscript direto em dict** sobre `disk_state`;
  qualquer valor fora das quatro chaves levanta `KeyError`. É a razão concreta de
  a corroboração ser chave paralela e não um quinto estado.
- `cairn-gate.py` e `cairn/capability/scripts/cairn-loop-gate.py` são gêmeos —
  D-10 exige que a checagem entre nos dois no mesmo commit.
- `cairn/hooks/post-bd-write.sh` para D-12.

</code_context>

<specifics>
## Specific Ideas

- O template do board foi **escolhido a partir de quatro variantes renderizadas
  no terminal**, não descrito em prosa. O bloco em D-03 é o alvo literal.
- A frase que resume a postura do produto, nas palavras do Felipe: o cairn dá as
  opções e o projeto segue, sem ficar "parando" o processo.

</specifics>

<deferred>
## Deferred Ideas

- **Severidade com mais de dois níveis** e allowlist configurável no estilo
  `.tfdriftignore` — CORR-09, já registrado como v2 em REQUIREMENTS.md. Espera
  corpus real de tipos de conflito.
- **Corroboração no CI** — descartada em D-08 por causa do clone raso, não
  esquecida: volta se alguém quiser pagar `fetch-depth: 0`.
- **Visão de tendência de conflitos entre milestones** — CORR-10, v2.
- Defeitos encontrados durante esta conversa e registrados no bd, fora do escopo
  desta fase: `CairnGo-ca3` (o check `req-issue` passa no vazio), `CairnGo-xhy`
  (doctor marca issue fechada de milestone arquivado como órfã), `CairnGo-13t`
  (mapas pedidos antes de existir o diretório da fase), `CairnGo-0rk`
  (`/cairn:init` deve perguntar a linguagem e gravar em `response_language`).

</deferred>

---

*Phase: 13-State corroboration*
*Context gathered: 2026-07-30*
