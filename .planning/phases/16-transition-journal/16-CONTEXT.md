# Phase 16: Transition journal - Context

**Gathered:** 2026-07-31
**Status:** Ready for planning

<domain>
## Phase Boundary

O histórico do que realmente aconteceu sobrevive a uma queda e consegue explicar
um conflito — sem nunca virar autoridade sobre o estado corrente.

Requisitos: JOUR-01 … JOUR-05. Issues bd: ver `16-BEADS-MAP.md`.

Herdado e **não reaberto**: o journal é local, gitignored e JSONL append-only
(a pesquisa fechou isso — mantê-lo fora do git dissolve o problema do
`merge=union`, que reordena e deduplica registros); o append usa
`os.open(O_APPEND)` com um `os.write()` por linha, a única receita que garante
atomicidade por POSIX; `cairn-migrate.py` já tem o idioma como precedente na casa.

</domain>

<decisions>
## Implementation Decisions

### O que se registra

- **D-01: estado de fase, lease e veredito de corroboração.** As transições
  `none→planned→executed→verified→complete`, mais aquisição e liberação de lease,
  mais a mudança de veredito `ok↔conflict↔unknown`.

  A razão de não ser só estado de fase é o JOUR-02: para dizer "quando cada lado
  se moveu", o journal precisa ter visto o lado que se moveu. Um conflito
  disco-versus-bd nasce de uma issue que fechou ou de um lease que mudou de mão,
  e nenhum dos dois é transição de fase.

  Rejeitado registrar tudo o que o cairn faz (close de issue, geração de mapa,
  rodada de doctor): vira log de aplicação, cresce rápido e afoga o sinal.

### Quem escreve

- **D-02: um `cairn-journal.py`, com par `.sh` e bats próprio, chamado pelos
  demais scripts.** Uma implementação de append atômico, num lugar só.

  A alternativa — cada script abrindo o arquivo e dando append — produziria três
  cópias da receita `O_APPEND`, que é exatamente o problema que a fase 15 evitou
  ao fazer o shim de capability um delegador em vez de uma cópia. Rejeitado também
  escrever pelos hooks: eles saem 0 por contrato e a falha some, e a fase 13 já
  teve que inventar `.cairn/hook.log` por causa disso.

### Compactação

- **D-03: automática por tamanho, escrevendo um arquivo novo e trocando por
  `os.rename`.** Passou do limiar, o journal compactado é escrito num temporário
  irmão e o rename troca os dois — operação atômica no POSIX.

  A resposta inicial foi compactar em linha, dentro do append. Isso foi
  questionado e mudado: o journal existe para sobreviver a uma queda, e compactar
  dentro do append põe uma **reescrita** no caminho onde a queda faz mais estrago.
  Uma queda ali não deixa uma linha rasgada (que o JOUR-04 sabe tratar) — deixa o
  arquivo inteiro em estado intermediário. Com o rename, uma queda no meio deixa o
  journal antigo intacto e um temporário órfão, nunca um arquivo pela metade.

  **Simetria que vale registrar:** a pesquisa da fase 15 mediu que `os.rename`
  **sobrescreve em silêncio**, e foi por isso que ele foi rejeitado para adquirir
  lock. Aqui, sobrescrever em silêncio é precisamente a propriedade desejada. O
  mesmo achado, com implicações opostas conforme o uso — o plano deve dizer isso,
  para ninguém "corrigir" um dos dois pelo outro.

### Onde o histórico aparece

- **D-04: dentro do relatório de conflito, mais um comando de leitura.** No
  conflito, cada lado ganha o instante em que se moveu pela última vez — que é
  literalmente o JOUR-02. Fora disso, um comando de leitura sob demanda, para
  post-mortem.

  Rejeitado pôr a última transição no board: informação que só importa quando algo
  discorda vira ruído permanente quando nada discorda.

### Claude's Discretion

- O limiar de compactação e o que a compactação preserva (provavelmente a última
  transição por fase mais os eventos ainda não explicados).
- Nome e forma exata do comando de leitura.
- Schema exato do registro, desde que carregue actor, instante, fase e evento
  (JOUR-01) e um nonce que impeça dois registros idênticos de se confundirem.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pesquisa que já fechou parte do desenho
- `.planning/research/SUMMARY.md` §"Collision 4" — por que o journal é local e
  gitignored, e por que ele nunca é autoridade sozinho
- `.planning/research/STACK.md` — a receita `os.open(O_APPEND)` + um `os.write()`
  por linha; por que `PIPE_BUF` é a constante errada; e a medição de que
  `os.rename` sobrescreve em silêncio
- `.planning/research/PITFALLS.md` — Pitfall 8 (crescimento sem limite),
  9 (reordenação por merge), 10 (escrita rasgada), 11 (journal como verdade única)

### O que as fases anteriores travaram e esta consome
- `.planning/phases/13-state-corroboration/13-CONTEXT.md` — D-01 (nunca grava
  sozinho, nunca para o fluxo), D-02 (script reporta, prosa pergunta)
- `.planning/phases/15-phase-lease/15-CONTEXT.md` — os eventos de lease que este
  journal registra, e o shim delegador como precedente de "uma implementação só"

### Código
- `cairn/scripts/cairn-migrate.py` — o journal JSONL resumível já existente
- `cairn/scripts/cairn-lease.py` — emite os eventos de lease
- `cairn/scripts/cairn-status.py` — `corroborate()` emite a mudança de veredito
- `cairn/scripts/cairn-doctor.py` — `check_phase_corroboration()` é onde o
  instante de cada lado entra no relatório
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`,
  `die()`, um bats por script, docstring como spec

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cairn-migrate.py`'s resumable JSONL journal — o idioma, já em produção aqui.
- `.cairn/` já é o lugar de estado local gitignored (`id-map.json`, `state.json`,
  `conflicts.json`, `hook.log`, `state/`). O journal entra ao lado, e o
  `.gitignore` precisa da entrada nova.
- `cairn-lease.py` e `cairn-status.py` já são os pontos onde os eventos nascem.

### Established Patterns
- Hooks nunca falham o chamador; se o journal for escrito a partir de um caminho
  de hook, a falha precisa ficar observável — a fase 13 resolveu isso escrevendo
  em `.cairn/hook.log`, e o teste afirma o conteúdo, nunca o código de saída.
- Escrita atrás de flag nomeada, leitura por default (`--close-completed`,
  `--link-refs`) — o padrão da casa para qualquer coisa que muta.

### Integration Points
- `cairn-journal.py` / `.sh` (novos) e `tests/cairn-journal.bats` (novo).
- Chamadores: `cairn-lease.py` (aquisição/liberação) e o caminho que computa o
  veredito de corroboração.
- `cairn-doctor.py` `check_phase_corroboration()` — para o instante de cada lado.
- `.gitignore` — a entrada do journal.

</code_context>

<specifics>
## Specific Ideas

- A decisão de compactação mudou durante esta conversa depois de ser questionada.
  A primeira resposta foi compactar dentro do append; ao ver que isso põe uma
  reescrita no caminho da queda que o journal existe para sobreviver, o Felipe
  escolheu o rename atômico. Fica registrado que a mudança foi deliberada, não
  esquecimento da primeira resposta.

</specifics>

<deferred>
## Deferred Ideas

- **Journal versionado em git e durável entre máquinas** — JOUR-06, já registrado
  como v2. Exige antes a alternativa de hash-chain; um `merge=union` cru reordena
  e deduplica registros.
- Registrar close de issue, geração de mapa e rodada de doctor — rejeitado em D-01
  por afogar o sinal, não por não ser possível.
- Última transição visível no board — rejeitado em D-04.

</deferred>

---

*Phase: 16-Transition journal*
*Context gathered: 2026-07-31*
