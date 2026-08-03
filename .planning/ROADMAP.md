# Roadmap: CairnGo

## Milestones

- ✅ **v1.1 Metrics & Benchmarks** — Phases 1-6, shipped 2026-07-27 · [archive](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 GSD Core** — Phases 7-9, shipped 2026-07-28 · [archive](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Status Panel** — Phases 10-12, shipped 2026-07-28 · [archive](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Honest State** — Phases 13-19, shipped 2026-08-01 como cairn 1.5.0 · [archive](./milestones/v1.4-ROADMAP.md)
- 🚧 **v1.5 Legible State** — Phases 20-28, em andamento

## Milestone: v1.5 Legible State 🚧

**Onde você está dentro do estado que já prova o que afirma**

O v1.4 fez as fontes se corroborarem: a discordância virou conflito nomeado em vez
de uma fonte vencendo em silêncio. Sobrou o outro lado. O board sabe **listar** e
não sabe **situar**: com muitas tarefas ele vira uma coluna plana onde não dá para
dizer a que ciclo cada linha pertence, `READY` significa três coisas ao mesmo tempo,
e o título é cortado em 28 caracteres. Fora do TTY ele degrada para o formato de
máquina sem ninguém ter pedido.

E o doctor, que este projeto construiu para não mentir, dá **16 ok e 0 falhas sobre
um roadmap vazio** — três checagens passam por não ter o que checar. É a mesma
classe de sinal que o ciclo anterior existiu para eliminar, dentro da ferramenta que
o eliminou.

O padrão daqui: uma superfície que responde sem saber sobre o que está respondendo
não conta como pronta.

## Phases

### 🚧 v1.5 Legible State — onde você está (Phases 20-28)

- [ ] Phase 20: Group model (BOARD-01)
- [ ] Phase 21: The grouped board (BOARD-02, BOARD-03, BOARD-05)
- [ ] Phase 22: Non-TTY split and the machine contract (BOARD-04, PIPE-01, PIPE-02, PIPE-03)
- [ ] Phase 23: Not-applicable as a check state (VOID-01, VOID-02, VOID-03)
- [ ] Phase 24: Language chosen at install (LANG-01, LANG-02)
- [ ] Phase 25: Measured cleanup (FIX-01, FIX-02, FIX-03, FIX-04)
- [ ] Phase 26: The cairn wrappers (WRAP-01, WRAP-02, WRAP-03)
- [ ] Phase 27: Disagreement trend across cycles (TREND-01, TREND-02)
- [ ] Phase 28: Durable journal (DJOUR-01, DJOUR-02, DJOUR-03)

## Detalhe das fases

### Phase 20: Group model

**Card:** o modelo de fase passa a saber a que grupo cada coisa pertence, antes de
qualquer pixel mudar.

**Goal:** `phase_model()` hoje devolve fases de um milestone só, e o board monta as
três raias a partir do `bd ready`. Nenhum dos dois carrega a hierarquia
milestone → fase → tarefa que o render agrupado precisa. Esta fase acrescenta essa
estrutura ao modelo, sem tocar em render nenhum — o board continua exatamente como
está ao fim dela.

**Requirements**: BOARD-01

**Success criteria:**

1. O modelo carrega, por milestone aberto, suas fases; e o trabalho sem milestone
   num grupo próprio, ordenado por último.
2. Um repositório sem milestone aberto produz zero grupos de milestone e um grupo
   de trabalho solto — nunca um grupo nomeado com o último ciclo arquivado.
3. `--json` ganha a estrutura de grupos sem que nenhuma chave existente mude de
   nome, de tipo ou de significado; a suíte atual passa sem edição.
4. Um teste renderiza o board antes e depois da fase e prova que a saída é
   **byte a byte idêntica** — a mudança é de modelo, não de superfície.

**Research durante o planejamento:** não precisa. `phase_model()` é função
existente e bem entendida, e a fase 13 já estabeleceu o padrão de estender o modelo
sem mexer nas chaves que os consumidores leem.

**Depende de:** nada. É a raiz do ciclo.

---

### Phase 21: The grouped board

**Card:** o kanban de três colunas sai; entra uma lista agrupada em que o símbolo
carrega a etapa e o título tem a largura inteira.

**Goal:** as três raias `READY`/`DOING`/`BLOCKED` gastam a largura do terminal
dividida por três e cortam todo título em ~28 caracteres — `[bug] doctor da…`,
`cairn-doctor: re…`. Com 40 tarefas a coluna `READY` vira 40 linhas e as outras
duas ficam vazias. Esta fase troca a forma: uma lista, agrupada pelo modelo da fase
20, com a etapa num símbolo.

**Requirements**: BOARD-02, BOARD-03, BOARD-05

**Success criteria:**

1. Nenhum título é truncado em nenhuma largura de terminal em que a linha caiba, e
   um teste prova isso com um título longo de verdade.
2. Os símbolos de etapa são todos de largura simples. **Medido no discuss e não
   presumido:** `○` (U+25CB), `◑` (U+25D1) e `◆` (U+25C6) são
   `east_asian_width=A`, ou seja largura 2 em terminal com locale CJK, e por isso
   foram descartados. O conjunto adotado é `◌ ◔ ◕ ✓ ⧗`, todos `N`. Um teste afirma
   a propriedade por `unicodedata`, não pela aparência.
3. `--ascii` produz um conjunto equivalente sem nenhum caractere fora de ASCII, e
   as colunas fecham alinhadas nos dois modos.
4. Uma linha bloqueada nomeia o bloqueador na própria linha, sem exigir um segundo
   comando para descobrir quem é.

**Research durante o planejamento:** não precisa. A largura dos candidatos foi
medida no discuss desta fase e o alinhamento foi provado num render de amostra.

**Depende de:** Phase 20 — o render consome o modelo de grupo.

---

### Phase 22: Non-TTY split and the machine contract

**Card:** `--plain` volta a ser só contrato de máquina, e quem lê fora do TTY passa
a receber algo legível.

**Goal:** `--plain` faz dois trabalhos incompatíveis hoje: é o TSV que scripts
consomem **e** o fallback automático de não-TTY. Foi assim que o formato de máquina
apareceu na tela de quem só queria olhar o board. Esta fase separa os dois e conserta
o cabeçalho que continua anunciando o último milestone arquivado como se fosse o
atual.

**Requirements**: BOARD-04, PIPE-01, PIPE-02, PIPE-03

**Success criteria:**

1. `--plain` é byte a byte o que é hoje, provado contra uma saída de referência
   commitada — o contrato externo não se move.
2. Sem TTY e sem flag, a saída é a lista agrupada em texto puro: sem box-drawing,
   sem sequência ANSI, e legível por humano.
3. O cabeçalho nomeia o milestone aberto, e diz que não há nenhum quando não há.
   Um teste arquiva um milestone e afirma que o board para de citá-lo — o caso real
   medido em 2026-08-03, dez minutos após o arquivamento do v1.4.
4. `tests/cairn-status.bats:208` afirma hoje que `--plain` é **byte a byte
   idêntico** ao default de não-TTY. Esse teste é o contrato do acoplamento que
   esta fase desfaz: ele é **reescrito em duas asserções separadas**, nunca
   deletado. Um teste que some junto com o comportamento que ele guardava é como a
   garantia evapora.

**Research durante o planejamento:** não precisa. O acoplamento foi localizado no
discuss (`tests/cairn-status.bats:190-211`), e uma varredura confirmou que nada
dentro do cairn parseia `--plain` além dos próprios testes.

**Depende de:** Phase 21 — é o render agrupado que o caminho não-TTY passa a emitir.

---

### Phase 23: Not-applicable as a check state

**Card:** o doctor para de dar verde sobre o que não checou.

**Goal:** medido em 2026-08-03, logo após arquivar o v1.4: com o `ROADMAP.md` sem
nenhuma fase, o doctor reporta **16 ok, 0 avisos, 0 falhas**. Três checagens passam
por não ter o que comparar — `req-issue` ("no `**Requirements**:` lists found"),
`maps-fresh` ("0 phase map(s) current") e `orphans` ("77 issue(s), no orphans",
um minuto depois de reportar 26 órfãs, com o mesmo número de issues). A causa do
`orphans` está em `cairn-doctor.py:803`, um `if roadmap_phases:` que pula a
comparação inteira.

Nenhuma das três está errada isoladamente — não há o que comparar. Juntas produzem
um board perfeitamente verde sobre um projeto sem roadmap, que é a forma exata de
sinal que o v1.4 existiu para eliminar.

**Requirements**: VOID-01, VOID-02, VOID-03

**Success criteria:**

1. `not-applicable` é um estado distinto de `ok` no `--json` e no resumo, e a linha
   final do doctor conta os dois separadamente em vez de somá-los.
2. Um repositório com roadmap vazio produz zero `ok` nas três checagens acima e
   três `not-applicable`, e o board **não** lê como saudável.
3. `orphans` para de sinalizar issue fechada de milestone arquivado (`CairnGo-xhy`);
   um teste arquiva um ciclo e afirma que a contagem zera em vez de crescer.
4. Cada checagem que ganhar o estado novo diz, na sua própria mensagem, **o que**
   faltou para ela poder checar.

**Research durante o planejamento:** não precisa. As três ocorrências foram medidas
e a linha exata da causa do `orphans` está localizada.

**Depende de:** nada. Independente do board; pode correr em paralelo com 20-22.

---

### Phase 24: Language chosen at install

**Card:** a linguagem de resposta deixa de ser algo que alguém descobre no meio de
um ciclo.

**Goal:** no v1.4 todo subagente respondeu em inglês contra um planejamento inteiro
em PT-BR, até `response_language` ser setado à mão no meio do milestone. A escolha
existe na config e não é oferecida na instalação, então o default silencioso vence
até alguém notar.

**Requirements**: LANG-01, LANG-02

**Success criteria:**

1. `/cairn:init` pergunta a linguagem e grava a escolha, com inglês como default
   explícito — nunca um default implícito por omissão.
2. Um teste lê o valor **no ponto de entrega ao subagente**, não na config: provar
   que o arquivo tem a chave não prova que o agente a recebeu.
3. Um projeto já instalado não é alterado sem pedido; rodar o init de novo é
   idempotente e não sobrescreve escolha existente.

**Research durante o planejamento:** não precisa. `response_language` já existe
como chave de topo do `config.json` e o config-loader já a entrega.

**Depende de:** nada.

---

### Phase 25: Measured cleanup

**Card:** três defeitos pequenos que já vieram com medição junto.

**Goal:** os três foram achados durante o v1.4, registrados com a medição que os
expôs, e nenhum afeta veredito — mas os três fazem uma superfície dizer algo que não
é verdade. `/cairn:milestone new` manda gerar mapa antes de existir diretório de
fase; o nome da branch de uma fase muda quando o diretório aparece depois do
`prepare`; e o campo `status` por portador do `cairn-release --json` reporta
"concorda com o primeiro portador legível", não "está correto" — medido com o
CHANGELOG já em 1.5.0 e os manifestos em 1.4.2, o `marketplace` levou `ok`
carregando a versão velha e o `changelog`, o único certo, levou `mismatch`.

**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04

**Success criteria:**

1. Cada um dos três tem um teste que reproduz o defeito **antes** do conserto, com a
   medição original citada no próprio teste.
2. O campo `status` do `cairn-release --json` ou passa a significar "está correto",
   ou é renomeado para o que de fato significa — nunca fica ambíguo.
3. Nenhum dos consertos muda o código de saída de um caminho que hoje é verde
   legitimamente.
4. **FIX-04, achado no pré-flight deste ciclo:** a fase 26 aparece como "waits on
   phase 9", um ciclo arquivado dois milestones atrás. Dois defeitos somados em
   `cairn-status.py` — `dep_target_ids()` coleta toda aresta de `dependencies` sem
   olhar o tipo, então `discovered-from` (documentado no `/cairn:quick` como
   procedência **sem bloquear**) conta como bloqueio; e a linha 1083 filtra contra
   o conjunto de fases feitas, do qual uma fase arquivada nunca faz parte. O
   próprio bd reporta a issue como `[READY]`. Um teste constrói uma aresta
   `discovered-from` para issue fechada de fase arquivada e afirma que a fase
   dependente segue `runnable`.

**Research durante o planejamento:** não precisa. Os três carregam a medição na
própria issue do bd.

**Depende de:** nada.

---

### Phase 26: The cairn wrappers

**Card:** os 13 wrappers decididos no GSD-05 e nunca construídos.

**Goal:** a decisão GSD-05 previu 13 wrappers `/cairn:*` que delegam ao `/gsd:*`
correspondente carregando o bookkeeping bd. Eles nunca foram construídos, e a
documentação fala deles como se existissem. Esta fase é a maior em volume do ciclo e
a mais independente de todas — nada depende dela e ela não depende de nada.

**Requirements**: WRAP-01, WRAP-02, WRAP-03

**Success criteria:**

1. Cada wrapper existe, delega ao comando GSD correspondente, e faz claim/close das
   issues bd da fase ativa como os comandos existentes já fazem.
2. Um wrapper cujo comando GSD correspondente não existe **falha nomeando o que
   falta**. Sair 0 em silêncio é o defeito que o v1.2 encontrou e que este projeto
   não repete.
3. A lista na documentação é derivada do que está instalado, não escrita à mão — uma
   lista manual envelhece e passa a mentir sozinha.

**Research durante o planejamento:** precisa de um item: quais dos 13 já têm
equivalente `/gsd:*` no gsd-core corrente. A decisão é de 2026-07 e o upstream mudou
desde então.

**Depende de:** nada. Deliberadamente no fim: é a fase que pode ser cortada sem
deixar nada pela metade.

---

### Phase 27: Disagreement trend across cycles

**Card:** a discordância entre fontes está subindo ou caindo ao longo dos ciclos?

**Goal:** o CORR-10 foi adiado no v1.4 por falta de dado. Agora existem quatro
milestones arquivados com artefatos de verificação, e a pergunta passa a ter com o
que ser respondida. Encaixa no tema do ciclo: situar não é só saber onde você está
agora, é saber para onde a coisa vem andando.

**Requirements**: TREND-01, TREND-02

**Success criteria:**

1. Um comando de leitura mostra a evolução da discordância entre fontes ao longo dos
   milestones arquivados.
2. Todo número vem de artefato arquivado; nenhum é digitado à mão em lugar nenhum.
3. Com dado insuficiente o comando **diz isso** e não desenha uma linha — uma
   tendência sobre dois pontos é ruído com aparência de sinal.

**Research durante o planejamento:** precisa. Quais artefatos arquivados de fato
carregam veredito de corroboração comparável entre ciclos: o v1.1 e o v1.2 são
anteriores à corroboração existir, então a série pode começar só no v1.4 — e se
começar, o critério 3 é o que decide.

**Depende de:** Phase 23 — a tendência só é honesta se `not-applicable` for
distinguível de `ok` na série.

---

### Phase 28: Durable journal

**Card:** o journal atravessa máquinas sem que o merge reordene ou perca registro.

**Goal:** o JOUR-06 foi adiado no v1.4 com uma razão explícita: um `merge=union` cru
reordena e deduplica registros, e o journal existe justamente para preservar ordem e
duplicata. A alternativa nomeada foi hash-chain, e ela nunca foi pesquisada. Esta
fase começa por essa pesquisa e só depois escreve código.

**Requirements**: DJOUR-01, DJOUR-02, DJOUR-03

**Success criteria:**

1. A alternativa de hash-chain é decidida **antes** de qualquer implementação, com o
   que foi medido escrito — e se a conclusão for que não vale, isso também é
   resultado e a fase entrega a decisão em vez de código.
2. Dois journals divergentes de máquinas diferentes são mesclados sem reordenar e
   sem perder registro, provado por teste que constrói a divergência.
3. Apagar o journal continua não mudando veredito nenhum. A propriedade que o v1.4
   travou — o journal explica história e nunca é autoridade sobre o presente —
   sobrevive a ele virar versionado.

**Research durante o planejamento:** **precisa, e é a única fase do ciclo em que a
pesquisa pode mudar o entregável.** Se a hash-chain não resolver reordenação sob
merge sem custo desproporcional, o resultado honesto é a decisão registrada de
manter o journal local.

**Depende de:** nada tecnicamente, mas fica por último por ser a de maior risco: é a
única cujo escopo a própria pesquisa pode redefinir.

---

## Cobertura

| Requisito | Fase | Status |
|-----------|------|--------|
| BOARD-01 | Phase 20 | Pending |
| BOARD-02 | Phase 21 | Pending |
| BOARD-03 | Phase 21 | Pending |
| BOARD-05 | Phase 21 | Pending |
| BOARD-04 | Phase 22 | Pending |
| PIPE-01 | Phase 22 | Pending |
| PIPE-02 | Phase 22 | Pending |
| PIPE-03 | Phase 22 | Pending |
| VOID-01 | Phase 23 | Pending |
| VOID-02 | Phase 23 | Pending |
| VOID-03 | Phase 23 | Pending |
| LANG-01 | Phase 24 | Pending |
| LANG-02 | Phase 24 | Pending |
| FIX-01 | Phase 25 | Pending |
| FIX-02 | Phase 25 | Pending |
| FIX-03 | Phase 25 | Pending |
| FIX-04 | Phase 25 | Pending |
| WRAP-01 | Phase 26 | Pending |
| WRAP-02 | Phase 26 | Pending |
| WRAP-03 | Phase 26 | Pending |
| TREND-01 | Phase 27 | Pending |
| TREND-02 | Phase 27 | Pending |
| DJOUR-01 | Phase 28 | Pending |
| DJOUR-02 | Phase 28 | Pending |
| DJOUR-03 | Phase 28 | Pending |

25 requisitos, 25 mapeados.

## Ordem de dependência

Só duas arestas reais no ciclo inteiro:

- **20 → 21 → 22**, a corrente do board. O modelo antes do render, o render antes do
  caminho não-TTY que o emite.
- **23 → 27**, porque uma série temporal que não distingue "não-aplicável" de "ok"
  mede a própria cegueira.

Todo o resto é independente: **23, 24, 25, 26 e 28 não têm aresta com ninguém** e
podem correr ao mesmo tempo, uma worktree cada — que é exatamente o que a fase 18 do
ciclo anterior construiu. Este é o primeiro roadmap do projeto com paralelismo real
disponível, e `/cairn:autonomous` agora executa concorrentemente em vez de anunciar e
enfileirar.

A ordem numérica coloca no fim o que pode ser cortado sem deixar nada pela metade: a
**26** é a maior em volume e não é pré-requisito de nada, e a **28** é a única cujo
escopo a própria pesquisa pode redefinir.

Trabalho aberto e sem fase vive no beads (`bd ready`), não aqui.
