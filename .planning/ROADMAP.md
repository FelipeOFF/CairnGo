# Roadmap: CairnGo

## Milestones

- ✅ **v1.1 Metrics & Benchmarks** — Phases 1-6, shipped 2026-07-27 · [archive](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 GSD Core** — Phases 7-9, shipped 2026-07-28 · [archive](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Status Panel** — Phases 10-12, shipped 2026-07-28 · [archive](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Honest State** — Phases 13-19, shipped 2026-08-01 como cairn 1.5.0 · [archive](./milestones/v1.4-ROADMAP.md)
- 🚧 **v1.5 Legible State** — Phases 20-29, em andamento

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

### 🚧 v1.5 Legible State — onde você está (Phases 20-29)

- [ ] Phase 29: Nothing mechanical stays manual (AUTO-01 … AUTO-08) — **roda primeiro**
- [x] Phase 20: Group model (BOARD-01) — completed 2026-08-03
- [ ] Phase 21: The grouped board (BOARD-06, BOARD-02, BOARD-03, BOARD-05)
- [ ] Phase 22: Non-TTY split and the machine contract (BOARD-04, PIPE-01, PIPE-02, PIPE-03)
- [ ] Phase 23: Not-applicable as a check state (VOID-01, VOID-02, VOID-03)
- [ ] Phase 24: Language chosen at install (LANG-01, LANG-02)
- [ ] Phase 25: Measured cleanup (FIX-01 … FIX-05)
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

**Override registrado na verificação (2026-08-03):** o critério 3 pedia "chave nova
de topo" **e** "a suíte atual passa sem edição", e as duas não valem juntas —
`tests/cairn-status.bats:1189` afirma o conjunto **exaustivo** de chaves de topo, e
qualquer chave aditiva o reprova, inclusive a que esta fase existe para acrescentar.
As alternativas eram piores: aninhar em `phases[]` viola a D-02, e afrouxar para
subconjunto destrói a única asserção que pega chave renomeada. Um literal foi
editado, a intenção preservada em comentário, e os dois lugares que afirmam o
conjunto foram conferidos e concordam (15 chaves, idênticas). A metade "nenhuma
chave existente muda de nome, tipo ou significado" está atendida e agora é
mecanicamente verificável.

**BOARD-01 atravessa duas fases.** Seu texto diz "o **board** agrupa"; esta fase
entrega a metade-modelo por decisão explícita e o board não muda um byte.

A primeira tentativa foi fazer BOARD-01 atravessar as fases 20 e 21, como
`CairnGo-ro4` fez no v1.4. **Não funciona aqui, e o doctor disse na hora:**
`req-issue` reportou *"BOARD-01 (phase 21): CairnGo-8vy carry the req but none is
labeled phase-21"*, e a chave de dedup `(gsd.req, gsd.milestone)` proíbe uma segunda
issue para o mesmo requisito no mesmo milestone. Diferente do `ro4`, que atravessava
dois planos de **uma** fase, este atravessava duas fases — e fase completa com issue
aberta é conflito de corroboração legítimo, além de barrar o ship gate.

Então o requisito foi **dividido**: BOARD-01 é o modelo (fase 20, fechado), BOARD-06
é o render agrupado (fase 21). Dois requisitos, uma issue cada, cada uma carimbada
na sua fase.

**Research durante o planejamento:** não precisa. `phase_model()` é função
existente e bem entendida, e a fase 13 já estabeleceu o padrão de estender o modelo
sem mexer nas chaves que os consumidores leem.

**Depende de:** nada. É a raiz do ciclo.

**Plans:** 3 plans

- [ ] 20-01-PLAN.md — grava a referência do render do código intocado, com a prova de que a comparação está viva
- [ ] 20-02-PLAN.md — `roadmap_milestones()`, `phase_groups()` e a chave de topo `groups` no `--json`
- [ ] 20-03-PLAN.md — as bordas da D-03, o isolamento do ciclo arquivado e os travões de contrato do `--json`

---

### Phase 21: The grouped board

**Card:** o kanban de três colunas sai; entra uma lista agrupada em que o símbolo
carrega a etapa e o título tem a largura inteira.

**Goal:** as três raias `READY`/`DOING`/`BLOCKED` gastam a largura do terminal
dividida por três e cortam todo título em ~28 caracteres — `[bug] doctor da…`,
`cairn-doctor: re…`. Com 40 tarefas a coluna `READY` vira 40 linhas e as outras
duas ficam vazias. Esta fase troca a forma: uma lista, agrupada pelo modelo da fase
20, com a etapa num símbolo.

**Requirements**: BOARD-06, BOARD-02, BOARD-03, BOARD-05

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

**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04, FIX-05

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

### Phase 29: Nothing mechanical stays manual

**Card:** o que é mecânica pura e não tem regra de negócio dentro para de ser feito
à mão.

**Goal:** este é o pecado do cairn, e o ciclo v1.4 inteiro é a evidência. Marcar uma
fase completa no roadmap, marcar seus requisitos, mexer os contadores do STATE,
regenerar o mapa, liberar o lease — **nenhuma dessas coisas tem regra de negócio
dentro**, e todas foram feitas à mão, uma a uma, em toda fase. Medido em
2026-08-03: **dez commits** tocando `STATE.md`/`ROADMAP.md`/`REQUIREMENTS.md` por
edição manual, e **nenhum script no repositório faz isso**. O custo é invisível
porque quem paga é o agente, e o erro também: ao abrir o v1.5, nove issues adotadas
ficaram com o label do ciclo antigo pendurado junto do novo, e três seguiram
marcadas `quick` já tendo fase.

A mesma doença aparece na configuração. O `response_language` precisou ser
descoberto e setado no meio de um milestone. O Jira, que o `bd` já sabe guardar em
`external_ref`, exige que alguém digite a chave. A suíte roda serial porque ninguém
instalou o `parallel`.

A linha que separa o que se automatiza do que se pergunta é a do `/groom-me`:
**mudança de regra de negócio se conversa antes; mecânica se automatiza e pronto.**
Nada nesta fase cruza essa linha.

**Requirements**: AUTO-01 … AUTO-08

**Success criteria:**

1. Fechar uma fase é **um comando**. Ele marca a fase no roadmap, marca seus
   requisitos, atualiza os contadores do STATE, regenera o mapa e libera o lease —
   e é idempotente, porque rodar duas vezes é o caso normal num loop autônomo. Um
   teste roda a fase inteira do bookkeeping contra um fixture e compara com o
   resultado esperado; nenhuma edição manual sobrevive nos comandos.

2. O Jira é **detectado, confirmado e então configurado pelo cairn** — o fluxo é
   híbrido de propósito: detectar sozinho e configurar sozinho seria adivinhar
   sobre a ferramenta de outra pessoa; pedir configuração é o pecado que esta fase
   existe para corrigir. Então o cairn procura um servidor MCP do Atlassian na
   configuração de MCP, e chaves no formato `ABC-123` em nomes de branch e
   mensagens de commit; **mostra o que encontrou** ("achei DTP-142 em três branches
   e um servidor Atlassian configurado — quer vincular?"); pergunta **uma vez**; e
   a partir do "sim" grava tudo sozinho. O usuário confirma, e nunca digita chave,
   projeto nem credencial. Um projeto sem sinal nenhum jamais é perguntado, e um
   "não" é gravado com a mesma força de um "sim".

3. Um card associado a uma fase ou issue aparece no board **sem chamada de rede no
   caminho padrão** — o vínculo mora no `external_ref` do bd e no roadmap, e buscar
   título ou status no Jira ao vivo é opcional e atrás de flag. O board offline
   continua offline.

4. A suíte roda em paralelo quando o ambiente permite. Medido em 2026-08-03:
   `bats -j 6 tests/cairn-map.bats` leva 33s contra 64s serial, porque cada teste
   constrói um repo git e um banco bd e o gargalo é setup, não CPU. Quando o
   `parallel` não está instalado, o cairn **diz isso**.

   **Correção medida durante a checagem desta fase, e ela desfaz uma afirmação
   minha:** eu escrevi que sem o `parallel` o `-j` "rodaria serial em silêncio".
   Falso. Medido no bats 1.14.0 com o `parallel` fora do PATH — `parallel: command
   not found`, `Executed 0 instead of expected 2 tests`, **exit 1**. Ele executa
   **zero** testes e falha alto. A ameaça que este critério dizia mitigar não
   existe; a que existe é o inverso e é pior de outro jeito: uma suíte que não
   rodou, reportada como falha de infraestrutura em vez de suíte vazia. O critério
   passa a ser: o cairn detecta a ausência **antes** de invocar o bats, e diz que
   vai rodar serial — nunca deixa o bats executar zero testes.

5. **Nada valida a cadeia do registro de requisitos, e por isso ela derivou.**
   Medido em 2026-08-03 neste próprio repositório: **33** requisitos ativos em
   `REQUIREMENTS.md`, **31** linhas na tabela de Cobertura do ROADMAP (faltam
   `AUTO-05` e `AUTO-06`), e o rodapé afirmando **"29 requisitos, 29 mapeados"** —
   quatro números para a mesma coisa, três deles errados.

   A causa não é uma checagem que falhou: é uma que **não existe**. Ninguém valida
   requisito → tabela, nem tabela → rodapé. Esta fase acrescenta essa checagem, e
   ela falha contra o estado atual do repositório antes de qualquer conserto — se
   passar de primeira, está errada.

   **Segunda correção medida durante a revisão dos planos, e ela desfaz outra
   afirmação minha:** eu escrevi que o `req-issue` do doctor "valida requisito →
   issue e reporta corretamente". Falso. Ele reporta hoje
   `ok :: 29 requirement(s) mapped to issues` com 35 requisitos ativos, porque a
   linha `**Requirements**:` desta fase é uma **reticência** — `AUTO-01 … AUTO-08`
   — e `roadmap_requirements()` devolve dois ids em vez de oito. O mesmo silêncio
   faz o `29-BEADS-MAP.md` afirmar `None — every phase requirement is mapped`, o
   que é verdade só porque `AUTO-01` e `AUTO-08` têm issue: `AUTO-02`…`AUTO-07`
   nunca entram na conta de gaps. Uma reticência cegou a cobertura de requisitos em
   **duas** ferramentas ao mesmo tempo, e ambas dizem `ok`. O 29 que ela produz é,
   por coincidência, o mesmo 29 do rodapé errado — dois números errados por causas
   independentes batendo por acaso. A checagem desta fase cobre também esse elo: uma
   linha de requisitos ilegível é falha nomeada, nunca silêncio, e nunca expansão
   por inferência.

   **Os números deste critério envelhecem, e isso é parte do achado.** Foram 33/31
   quando escrito, 34/32 dias depois, 35/33 em 2026-08-03 — `AUTO-07` e `AUTO-08`
   nasceram no meio do planejamento da própria fase. Eles ficam registrados como
   medição datada; a regra é **re-medir na execução**, e nenhum plano carimba esses
   números em teste.

6. O cairn ganha config própria, com **duas portas para o mesmo lugar**: perguntada
   como o `/gsd:config` pergunta, e editável à mão no `.json`. Hoje o GSD expõe mais
   de trinta chaves e o cairn **zero** — o que existe está espalhado entre
   `.cairn/context.json` e `.cairn/sync.json`, e nada lista o conjunto. A config
   cobre o que não tem onde morar: commit automático, PR por fase ou por milestone,
   teto de ciclos e de laços do run autônomo. Um teste altera uma chave pela
   pergunta e lê o efeito **no ponto de consumo**, não no arquivo — ter a chave
   gravada não prova que alguém a lê.

7. **O `STATE.md` fala um dialeto e o cairn lê outro, e a checagem que deveria
   perceber isso está morta há o projeto inteiro.** Medido em 2026-08-03:
   `grep -rn current_phase cairn/` devolve **zero**, enquanto `active_phase` é lido
   por cinco superfícies (`cairn-status.py`, `cairn-doctor.py`, `cairn-lease.py`,
   `cairn-migrate.py`, `hooks/session-start.sh`). O `STATE.md` tem `current_phase` e
   não tem `active_phase`, e a consequência é
   `claims-stale :: ok :: skipped — no active_phase in STATE.md`: uma checagem que
   nunca rodou uma única vez, exibindo o marcador de sucesso.

   O critério se parte em dois, e a linha do `/groom-me` passa exatamente no meio.
   **Mecânica, e sai nesta fase:** nenhuma checagem do doctor volta a dizer `ok` por
   não ter conseguido checar — ela diz o que faltou, cita onde a decisão está, e não
   bloqueia por falta de insumo. **Regra de negócio, e NÃO sai nesta fase:** qual
   dialeto vence. Escolher muda o que cinco arquivos leem e o que acontece com todo
   repositório que já tem `STATE.md` escrito. Fica em aberto, com endereço:
   `CairnGo-rq0`. Nenhum plano desta fase escreve `active_phase` nem renomeia chave
   nenhuma.

**Research durante o planejamento:** precisa de um item — como detectar um servidor
MCP configurado a partir de um script stdlib-only, sem depender do harness. A
resposta provável é ler a configuração de MCP do projeto e do usuário, mas o formato
e a precedência precisam ser medidos, não presumidos.

**Depende de:** nada. **Roda primeiro, por decisão do Felipe (2026-08-03), e a
decisão inverte a minha.**

Eu a tinha posto no fim com o argumento de que mudar o processo no meio de um ciclo
é como se perde o fio. O argumento oposto é mais forte e é o que vale: esta fase é a
única que torna **todas as outras mais baratas**, e deixá-la para o fim significa
pagar o imposto manual nove vezes antes de removê-lo. Dez commits de bookkeeping à
mão foram medidos num único dia; multiplicar isso por nove fases para preservar uma
preferência de sequência é o cálculo errado.

**O número 29 fica.** Renumerá-la para 20 orfanaria toda issue que carrega label
`phase-N` — que é literalmente o risco descrito na `CairnGo-9xy` como razão de os
wrappers existirem. Ordem de execução e número de fase são coisas diferentes, e este
roadmap passa a demonstrar isso.

**Plans:** 6/7 plans executed

- [x] 29-01-PLAN.md — congela a discordância real como fixture e lê os três arquivos sem pressupor consistência
- [x] 29-02-PLAN.md — o caminho de escrita completo: fase, requisitos, tabela, rodapé, contadores, mapa e lease num comando
- [x] 29-03-PLAN.md — config própria do cairn, duas portas, e nenhuma chave sem leitor executável
- [x] 29-04-PLAN.md — o detector de Jira para de mentir, e o cairn pergunta uma vez e grava sozinho
- [ ] 29-05-PLAN.md — o card do rastreador no board, com prova executável de que nada toca a rede
- [x] 29-06-PLAN.md — a suíte roda em paralelo quando dá, e detecta a ausência do parallel antes de invocar o bats
- [x] 29-07-PLAN.md — `req-ledger`, e o fim do `ok` sobre checagem que não conseguiu checar

**Ondas:** 1 → 29-01, 29-03 · 2 → 29-02, 29-06 · 3 → 29-04, 29-07 · 4 → 29-05.
O 29-04 saiu da onda 2 porque ele e o 29-02 escrevem em `cairn/commands/help.md`, e
`autonomous.md:238-248` proíbe resolução automática de conflito.

---

## Cobertura

| Requisito | Fase | Status |
|-----------|------|--------|
| BOARD-01 | Phase 20 | Complete |
| BOARD-06 | Phase 21 | Pending |
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
| FIX-05 | Phase 25 | Pending |
| WRAP-01 | Phase 26 | Pending |
| WRAP-02 | Phase 26 | Pending |
| WRAP-03 | Phase 26 | Pending |
| TREND-01 | Phase 27 | Pending |
| TREND-02 | Phase 27 | Pending |
| DJOUR-01 | Phase 28 | Pending |
| DJOUR-02 | Phase 28 | Pending |
| DJOUR-03 | Phase 28 | Pending |
| AUTO-01 | Phase 29 | Pending |
| AUTO-02 | Phase 29 | Pending |
| AUTO-03 | Phase 29 | Pending |
| AUTO-04 | Phase 29 | Pending |
| AUTO-07 | Phase 29 | Pending |
| AUTO-08 | Phase 29 | Pending |

29 requisitos, 29 mapeados.

## Ordem de dependência

**A fase 29 roda primeiro**, e isso não é uma aresta do grafo — é decisão. Ela não
bloqueia ninguém tecnicamente; ela torna todas as outras mais baratas, e nove fases
pagando bookkeeping manual antes de ele ser removido é o cálculo errado. Ordem de
execução e número de fase são coisas diferentes, e o número dela fica em 29 porque
renumerar orfanaria toda issue com label `phase-N`.

Depois dela, só duas arestas reais no ciclo inteiro:

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
