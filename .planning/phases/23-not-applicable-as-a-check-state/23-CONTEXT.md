# Phase 23: Not-applicable as a check state - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

O doctor para de dar verde sobre o que não checou.

Requisitos: VOID-01, VOID-02, VOID-03. Issues bd: ver `23-BEADS-MAP.md`.

**A fase não inventa um conceito — ela promove uma palavra que o código já escreve.**
Medido em 2026-08-05: três checagens já dizem literalmente `"not applicable — …"` no
seu `detail` enquanto carregam `status: "ok"`. O trabalho é tirar essa palavra da
prosa e pô-la no campo que as ferramentas leem.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo. As decisões abaixo são Claude's Discretion, e todas
saem de medição feita em 2026-08-05 contra a árvore de trabalho, depois de a fase 29
ter fechado. Onde algo não foi medido, está escrito que não foi.

### O número do roadmap está velho, e o novo é pior

- **D-01: a linha de base é `16 ok, 1 warning, 1 failure` sobre roadmap vazio, não
  `16 ok, 0 avisos, 0 falhas`.**

  O `**Goal:**` da fase no ROADMAP cita a medição de 2026-08-03, quando o doctor
  tinha 16 checagens. Ele tem **18** agora — a fase 29 acrescentou `test-parallel` e
  `req-ledger`. Reproduzido num repositório temporário com `ROADMAP.md` sem nenhuma
  fase e `STATE.md` sem `active_phase`:

  ```
  OK    req-issue            no '**Requirements**:' lists found in ROADMAP.md
  OK    maps-fresh           0 phase map(s) current
  OK    orphans              0 issue(s), no orphans
  OK    frontmatter-ids      0 plan bead id(s) verified
  OK    superseded-released  0 superseded plan(s), no live beads
  OK    external-ref         0 closed issue(s) lack an external ref, …
  OK    release-versions     not applicable — no cairn/.claude-plugin/plugin.json …
  OK    test-parallel        not applicable — no cairn/.claude-plugin/plugin.json …
  OK    req-ledger           not applicable — .planning/ carries no REQUIREMENTS.md …
  WARN  claims-stale         cannot check — STATE.md's frontmatter carries no 'active_phase'
  FAIL  gsd-capability       the capability did not register …
  ```

  (O `gsd-capability` falha porque o diretório temporário não é uma instalação do
  cairn; num repositório de verdade ele passa. Não é achado desta fase.)

  **Nove das dezoito checagens aprovam sem ter comparado nada.** O roadmap dizia três.

### Existem três idiomas para a mesma coisa, e é isso que a fase unifica

- **D-02: o inventário dos três idiomas é o primeiro entregável, antes de qualquer
  estado novo.**

  | idioma | status hoje | quem usa |
  |---|---|---|
  | prosa `"not applicable — …"` | `ok` | `release-versions` (1731), `test-parallel` (1815), `req-ledger` (2069, 2101) |
  | contagem zero (`0 phase map(s) current`) | `ok` | `req-issue`, `maps-fresh`, `orphans`, `frontmatter-ids`, `superseded-released`, `external-ref` |
  | `"cannot check — …"` | `warn` | `claims-stale` (entregue na fase 29, com comentário apontando para cá) |

  Três dialetos para "não tinha o que checar", dentro do mesmo arquivo, escritos pela
  mesma mão. A fase termina com **um**.

  A varredura é entregável por si: a lista das checagens que caem em cada idioma vai
  para o SUMMARY, e cada uma que mudar de estado é nomeada. Uma varredura que produz
  "consertei as três do roadmap" repete o defeito com número menor.

### O `n_ok` é subtração, e essa é a armadilha central

- **D-03: `n_ok` passa a ser contagem própria, e o teste que prova isso vem antes do
  estado novo.**

  Medido, `cairn-doctor.py:2555-2557`:

  ```python
  n_fail = sum(1 for c in checks if c["status"] == "fail")
  n_warn = sum(1 for c in checks if c["status"] == "warn")
  n_ok   = len(checks) - n_fail - n_warn      # <- subtração
  ```

  Acrescentar um quarto status **sem tocar nessa linha** faz o resumo contar
  `not-applicable` como `ok` em silêncio: a linha final diria `17 ok` com três
  checagens que não checaram nada. A fase existe para acabar com o verde falso e a
  primeira coisa que ela toca é o lugar onde um verde falso novo nasceria pronto.

  Um teste afirma que `n_ok + n_na + n_warn + n_fail == len(checks)` e que nenhuma das
  quatro é derivada por subtração.

### O estado novo não move o exit code, e isso é decisão, não omissão

- **D-04: `not-applicable` não conta para o exit 7.** Medido em
  `cairn-doctor.py:2571`: `sys.exit(EXIT_OK if n_fail == 0 else EXIT_FAILED)` — só
  `fail` move o código. `not-applicable` é ausência de insumo, não inconsistência de
  estado, e gastar o 7 com ausência de insumo é como o 7 deixa de significar algo. É a
  mesma distinção que o 29-06 fez entre atrito e inconsistência e que o 29-07 aplicou
  ao `claims-stale`.

  **Mas o critério de sucesso 2 exige que o board não leia como saudável**, e exit 0
  com dezoito `ok` é exatamente ler como saudável. Então o veredito muda **onde se lê**,
  não no código de saída: o resumo conta os quatro estados separadamente, o símbolo
  do `not-applicable` é distinto do `✓`, e a chave `ok` do `--json` de topo deixa de
  poder ser verdadeira quando nada foi checado. Como exatamente — chave nova, ou `ok`
  passando a exigir ao menos uma checagem efetiva — é Claude's Discretion, desde que
  um consumidor que só lê `summary.ok` não seja enganado.

### O código já pediu esta fase por escrito, em cinco lugares

- **D-05: as anotações existentes são requisito, não sugestão.** O
  `cairn-doctor.py` carrega cinco referências diretas a esta fase, cada uma marcando
  um sítio que deliberadamente não antecipou o estado:

  - `264` — `test-parallel`, ramo "a suíte não roda aqui de jeito nenhum"
  - `988`/`991` — `claims-stale`, sem `active_phase`
  - `1808` — `release-versions`
  - `1923`-`1927` — o comentário que diz, literalmente, *"não antecipe o estado novo
    aqui — a fase 23 é dona dele"*

  Cada um desses sítios sai da fase usando o estado, ou sai com a anotação
  atualizada dizendo por que não usou. Um comentário que promete uma fase e sobrevive
  intacto à fase é dívida que ninguém volta a ler.

### O `orphans` é conserto de linha, não de conceito

- **D-06: `cairn-doctor.py:904`, o `if roadmap_phases:` que pula a comparação
  inteira.** A linha era a 803 quando a fase foi escrita; o arquivo cresceu. O
  VOID-03 tem duas metades e elas são independentes:

  1. roadmap vazio → a checagem não se aplica (é o VOID-02 alcançando o `orphans`);
  2. issue **fechada** de milestone **arquivado** deixa de ser órfã (`CairnGo-xhy`),
     e a contagem zera ao fim de um ciclo em vez de crescer para sempre.

  A segunda não depende do estado novo e pode ser provada sozinha: um teste arquiva
  um ciclo e afirma que a contagem cai a zero. Medido no repositório real hoje:
  `external-ref` reporta `73 closed issue(s) lack an external ref` — a população de
  fechadas que o `orphans` varre cresce a cada milestone e nunca encolhe.

### Claude's Discretion

- O nome exato do estado no campo `status` (`not-applicable`, `na`, `skip`) e o
  símbolo que o representa no render. Único travão: **não pode ser `✓`**, e o símbolo
  tem de ser de largura simples pela mesma regra medida na fase 21 (`east_asian_width`
  `N`, verificado por `unicodedata`, nunca pela aparência).
- Se a chave `ok` do `--json` de topo ganha companhia ou muda de significado.
- Se as seis checagens do idioma "contagem zero" migram todas ou só as que o VOID-02
  nomeia — desde que a escolha esteja **escrita** e não seja por omissão.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Código
- `cairn/scripts/cairn-doctor.py:2555-2571` — o `n_ok` por subtração e o exit code
- `cairn/scripts/cairn-doctor.py:904` — o `if roadmap_phases:` do `orphans`
- `cairn/scripts/cairn-doctor.py:2393` — o `applicable` que já existe **no topo** do
  resumo, para repositório não-cabeado; o vocabulário existe, falta descer por checagem
- `cairn/scripts/cairn-doctor.py` linhas 264, 988, 991, 1808, 1923-1927 — as cinco
  anotações que esperam esta fase
- `cairn/scripts/cairn-doctor.py:1731, 1815, 2069, 2101` — as quatro que já escrevem
  `"not applicable"` em prosa vestindo `ok`
- `tests/cairn-doctor.bats` — 82 testes; a suíte que a fase 29 deixou
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

### Consumidores do veredito (quem quebra se o contrato mudar mal)
- `cairn/commands/autonomous.md` — a regra de parada por exit 7
- `cairn/scripts/cairn-test.py`, `cairn-bookkeep.py`, `cairn-lease.py`,
  `cairn-migrate.py`, `cairn-map.py`, `cairn-parallel.py`, `cairn-capability.py`,
  `cairn-reconcile.py` — todos citam o doctor

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- O `summary["applicable"]` de topo já resolve a pergunta "este repositório é
  cabeado?" — a forma existe, falta a granularidade por checagem.
- O `29-07` já entregou o idioma de "não consegui checar" com motivo nomeado e
  roteamento, no `claims-stale`. Ele é o modelo, e é o primeiro consumidor.
- A disciplina de asserção da fase 29: **status exato, nunca negação.** `!= "ok"` é
  satisfeito por `warn`, e foi assim que um verde falso quase passou por um teste
  escrito contra verde falso.

### Established Patterns
- Um teste que passaria com a feature removida não é prova.
- `EXIT_*` nomeados; `0` ok · `2` uso · `5` bd ausente · `6` achado · `7` doctor.
- Toda checagem diz **o que** faltou, e roteia para quem resolve.

### Integration Points
- `cairn/scripts/cairn-doctor.py` e `tests/cairn-doctor.bats` — o grosso.
- `cairn/docs/commands/doctor.md` — a página é contrato; um estado novo sem entrada
  é um estado que ninguém sabe interpretar quando aparece.
- **Nada mais.** Se esta fase tocar o board, ela saiu do escopo.

</code_context>

<specifics>
## Specific Ideas

- **A fase tem um consumidor escrito antes de ela existir.** O `claims-stale` saiu da
  fase 29 com `warn` e um comentário dizendo que o veredito certo é o desta fase.
  Terminar a 23 sem converter o `claims-stale` deixa a anotação mentindo — e é a
  checagem mais visível do doctor neste repositório, porque é a única que está sem
  insumo o tempo todo.

- **O defeito de contagem e o defeito de estado são o mesmo defeito em escalas
  diferentes.** `n_ok` por subtração aprova por default o que não conhece; uma
  checagem que devolve `ok` por não ter comparado nada aprova por default o que não
  viu. Consertar o segundo e deixar o primeiro faz a linha final voltar a mentir com
  a informação certa logo acima dela.

</specifics>

<deferred>
## Deferred Ideas

- Fazer o board do `/cairn:status` mostrar o estado novo — o board é fase 21/22, e
  esta fase termina sem tocar em render nenhum.
- Reduzir a população de issues fechadas que o `orphans` varre por compactação
  semântica (`bd admin compact`) — é lifecycle de milestone, não checagem.
- Mudar o exit code do doctor para distinguir "nada checado" de "tudo ok". Foi
  considerado e **recusado por escrito** na D-04: o 7 é para inconsistência de
  estado, e alargá-lo é como ele deixa de significar algo.

</deferred>

---

*Phase: 23-Not-applicable as a check state*
*Context gathered: 2026-08-05*
