# Phase 28: Durable journal - Context

**Gathered:** 2026-08-06
**Status:** Ready for planning

<domain>
## Phase Boundary

O journal atravessa máquinas e checkouts sem que nada precise ser mesclado.

Requisitos: DJOUR-01, DJOUR-02, DJOUR-03, DJOUR-04. Issues bd: ver `28-BEADS-MAP.md`.

**A pesquisa já rodou e é a autoridade desta fase.** `28-RESEARCH.md`, 17 experimentos
em repositórios temporários, com o `git 2.42.1` e o `cairn-journal.py` de produção. Ela
derrubou o requisito que a encomendou e a decisão do Felipe redefiniu o alvo. Este
contexto existe para registrar **o que sobrou de pé** depois das duas coisas, porque o
`28-RESEARCH.md` recomenda um desfecho que a decisão humana descartou, e um planejador
que o lesse sozinho planejaria a fase errada.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo. Medições de 2026-08-05 (pesquisa) e 2026-08-06 (este
documento), contra a árvore com as fases 20-24, 26, 27 e 29 fechadas.

### O que a decisão do Felipe mudou, e por quê o RESEARCH sozinho engana

- **D-01: o `28-RESEARCH.md` recomenda "manter local e gitignorado". Essa recomendação
  está morta.** Ela foi escrita antes da pergunta ser feita, e a resposta foi:

  > *"Sim ele pode ser usado em mais de uma maquina e em mais de uma sessão do claude"*
  > — Felipe, 2026-08-05

  A recomendação da pesquisa dependia inteiramente do invariante de **escritor único**.
  Com mais de uma máquina e mais de uma sessão, esse invariante é falso hoje, não em
  hipótese: `git worktree list` devolve **quatro** checkouts nesta máquina agora, e a
  pesquisa mediu neles quatro journals de 141, 58, 1 e 1 registros — quatro histórias
  que nunca se alcançam, com o mesmo `actor`.

  **Quem planejar esta fase lê o `28-RESEARCH.md` pela medição, nunca pela
  recomendação.** A seção que vale é *"Se a decisão humana for versionar assim mesmo: o
  desenho correto"*, e ela deixou de ser condicional.

- **D-02: o `DJOUR-01` está fechado pelo documento, não por código.** A hash-chain foi
  medida e rejeitada duas vezes: quebra sob merge (E6 — duas cabeças, não uma) e colide
  com o `DJOUR-03`, porque cadeia de hash é a estrutura de dados da autoridade e este
  artefato não decide nada. Nenhum plano desta fase escreve hash-chain. O critério 1 se
  satisfaz com a pesquisa commitada, e já está.

### A ordem é forçada: proveniência primeiro

- **D-03: o `DJOUR-04` vem antes de tudo, porque a partição não pode ser construída a
  partir do dado que existe.** Medido hoje, primeira linha do journal deste checkout:

  ```
  ['actor', 'event', 'from', 'nonce', 'phase', 'source', 'to', 'ts']
  ```

  Não há máquina, não há checkout. E `actor` é o usuário do git — **idêntico nos quatro
  checkouts**. Particionar por `actor` produziria uma partição só, que é o desenho de
  hoje com nome novo. O campo que separa as partições precisa existir antes de existir
  partição.

- **D-04: registro antigo lê como desconhecido, nunca com valor inventado.** Está no
  requisito e é a armadilha óbvia: carimbar os 141 registros existentes com o host e o
  checkout **atuais** parece migração e é fabricação — ninguém sabe de onde eles vieram,
  e o arquivo pode ter sido copiado. O arquivo herdado é lido como uma partição de
  proveniência desconhecida, **nunca reescrito**, e os registros novos nascem no formato
  novo.

### O desenho, e as regras que a medição impõe

- **D-05: uma partição por checkout, `merge=union` em cada uma.** As duas peças são
  necessárias e nenhuma basta sozinha: E11 caso 1 prova que máquinas diferentes em
  arquivos diferentes mesclam sem conflito e sem driver nenhum; E8b prova que a **mesma
  máquina em dois worktrees** conflita se o `union` não estiver lá. E o `union` é
  built-in: E17 mediu que um driver próprio exige `merge.<nome>.driver` no `.git/config`,
  que o git **nunca clona**, e a máquina sem esse passo cai no merge padrão — conflito
  com marcadores, em silêncio, que é o pior modo de falha disponível.

- **D-06: nunca reescrever um segmento, nunca apagar um segmento selado.** Compactar
  passa a significar *selar o atual e abrir o próximo*, cuja primeira linha é o
  `snapshot` com `compacted_through_ts`. Reescrever faz o `union` **ressuscitar** o que
  foi dobrado (E5: 6 linhas onde um humano esperava 2); apagar dá `modify/delete` (E10),
  que é pior de resolver que conflito de conteúdo.

  **Contrapartida que este desenho aceita de olhos abertos:** compactar arquivo
  versionado não economiza nada durável — toda versão fica no histórico do git para
  sempre. O ganho é tempo de leitura, e segmento selado dá o mesmo ganho sem reescrever
  nada.

- **D-07: compactação restrita à própria partição, e é o teste mais importante da
  fase.** E13 é o defeito que mata o desenho ingênuo: duas máquinas compactando
  concorrentemente deixam **um JSONL válido de duas linhas** com a história inteira de
  uma delas ausente — sem conflito, sem erro, sem sinal. Com partição por checkout isso
  vira impossível por construção, e o critério 4 existe para provar a construção, não
  para prometê-la.

- **D-08: a leitura une as partições sem acordo de relógio.** Dobra os snapshots por
  `compacted_through_ts`, depois os eventos posteriores ordenados por `(ts, nonce)` —
  **dentro de cada partição**. Entre partições, a saída **nomeia de onde veio cada eixo**
  e nunca afirma ordem. Medido: desvio NTP desta máquina −16,7 ms ± 7,9; gap mínimo entre
  registros consecutivos 10,8 ms, mediano 17,7 ms. **A resolução de ordenação que o
  journal precisaria é mais fina que o acordo de relógio disponível entre máquinas.**
  Ordenar eventos cross-máquina por `ts` constrói uma linha do tempo que parece
  autoritativa e não é.

- **D-09: o `_last_known()` de produção mente sobre arquivo mesclado, e o conserto óbvio
  também.** Rodando o script real sobre o arquivo mesclado do E2, `last-moved` devolveu
  `complete` quando a verdade era `archived` — a dobra é em ordem de arquivo, e o
  docstring afirma isso como invariante (`cairn-journal.py:442`). Um `sort` por
  `(ts, nonce)` conserta o E2 e **quebra o E9**, porque o `ts` do snapshot é posterior a
  tudo que ele dobrou. Quem tocar nessa função sem tocar em `compacted_through_ts` está
  escrevendo a armadilha 1 da pesquisa.

### O que esta fase não pode quebrar

- **D-10: o `DJOUR-03` sobrevive intacto — apagar o journal não muda veredito nenhum.**
  Isso não é aspiração, é o que já está testado: o `journal_last_moved()` do doctor
  degrada a cláusula final de **um** item para nada, nunca a severidade, nunca o exit
  code; o `journal_history()` do reconcile devolve `[]` e o bundle segue. O desenho novo
  herda essa disciplina, e um plano que faça o board ou o doctor **depender** de partição
  legível quebrou o requisito.

- **D-11: `.cairn/` é 100% não rastreado hoje** (`git ls-files .cairn/` devolve vazio) e
  o `.gitignore` lista arquivo por arquivo, sem `.cairn/` guarda-chuva. O diretório de
  partições passa a ser **o primeiro artefato versionado dentro de `.cairn/`**, e não
  precisa de negação de ignore para isso. A linha 8, `.cairn/journal.jsonl*`, continua
  cobrindo o arquivo herdado.

### Claude's Discretion

- Como o id do checkout é derivado, desde que seja **estável entre execuções no mesmo
  checkout e distinto entre checkouts na mesma máquina** — os quatro worktrees medidos
  hoje são o caso de teste, não uma hipótese.
- O layout exato dos nomes de arquivo e a numeração dos segmentos.
- Se a leitura das partições é função nova no `cairn-journal.py` ou script à parte
  (com o par `.sh` e o `.bats` que a casa exige, se for à parte).
- Se o conserto do E12 (`_last_known` ciente de `compacted_through_ts`) entra nesta fase
  ou vira issue — mas **o `sort` sozinho não entra em hipótese nenhuma**.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/28-durable-journal/28-RESEARCH.md` — 17 experimentos. **Ler pela
  medição, não pela recomendação** (D-01). A seção operativa é *"Se a decisão humana for
  versionar assim mesmo: o desenho correto"*.
- `cairn/scripts/cairn-journal.py` — 1.128 linhas, escritor único, `os.open(O_APPEND)` +
  um `os.write()` por registro, `flock` entre compactações, `nonce` uuid4 por linha
  (fase 16). `_last_known()` na linha 442 é o ponto que a fase move.
- `tests/cairn-journal.bats` — 16 testes hoje, incluindo torn-tail e equivalência de
  replay pós-compactação. Os testes novos vão aqui.
- `cairn/scripts/cairn-doctor.py` / `cairn-reconcile.py` — os dois consumidores, ambos
  aditivos e com degradação já testada (D-10).
- `.planning/codebase/CONVENTIONS.md` — stdlib only, sem type hints, par `.py`/`.sh`,
  `EXIT_*` nomeados.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- O `nonce` uuid4 por registro já resolve a dedup do `union` (E3 contra E4) — a metade
  "deduplica" do `DJOUR-01` descrevia um bug que a fase 16 consertou.
- `cmd_history` já ordena por `(ts, nonce)` antes de imprimir, então o `history` já é
  determinístico sob merge. A superfície quebrada é menor e mais precisa do que parece:
  é o `last-moved`, não o journal inteiro.
- O `cairn-migrate.py` tem journal **próprio** (`migrate-state.json`), outra coisa. É o
  precedente do idioma JSONL nesta casa, não um consumidor deste arquivo.

### Established Patterns
- Um teste que passaria com a feature removida não é prova.
- Toda asserção de status é sobre o valor exato, nunca sobre a negação.
- Número afirmado em prosa envelhece — quatro precedentes medidos neste repositório.
- Toda mudança de schema em arquivo append-only lê o registro antigo como desconhecido,
  nunca com default inventado.

### Integration Points
- `.gitattributes` na raiz (não existe nenhum rastreado hoje; os três encontrados são de
  dependências vendorizadas em `benchmarks/plugins/`).
- `.gitignore` linha 8, que continua cobrindo o arquivo herdado.
- Cinco consumidores mencionam o journal: doctor, reconcile, status, parallel, config.
  Os dois que **leem** são doctor e reconcile.

</code_context>

<specifics>
## Specific Ideas

- **O gatilho de compactação nunca disparou na vida real deste projeto, e vai disparar.**
  Medido: 27.992 bytes em 5 dias ≈ 5,6 KB/dia, contra um limiar de 200 KiB — primeira
  compactação em ≈ 36 dias. O defeito que esta fase existe para impedir é justamente o
  da compactação, e ele está a um mês de distância, não num cenário remoto.

- **O modo de falha do desenho ingênuo é silencioso, e é por isso que o critério 4 pesa
  mais que os outros.** E13 não produz erro: produz um arquivo válido, menor, com a
  história de uma máquina inteira faltando. Nenhum teste comum pega isso. O teste que
  pega precisa **construir** as duas compactações concorrentes.

</specifics>

<deferred>
## Deferred Ideas

- Relógio lógico (Lamport ou vetorial) para ordem causal cross-máquina. É o único
  desenho que daria ordem verdadeira entre partições, e é desenho novo — a fase entrega
  "não afirmo ordem entre máquinas", que é honesto e barato.
- Hash-chain, em qualquer forma. Rejeitada com medição (E6), não por preferência.
- Merge driver próprio. Rejeitado com medição (E17): corretude dependente de config que
  o git não clona.

</deferred>

---

*Phase: 28-Durable journal*
*Context gathered: 2026-08-06*
