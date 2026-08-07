# Roadmap: CairnGo

## Milestones

- ✅ **v1.1 Metrics & Benchmarks** — Phases 1-6, shipped 2026-07-27 · [archive](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 GSD Core** — Phases 7-9, shipped 2026-07-28 · [archive](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Status Panel** — Phases 10-12, shipped 2026-07-28 · [archive](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Honest State** — Phases 13-19, shipped 2026-08-01 como cairn 1.5.0 · [archive](./milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 Legible State** — Phases 20-30, shipped 2026-08-07 como cairn 1.6.0 · [archive](./milestones/v1.5-ROADMAP.md)
- 🚧 **v1.6 O bd vira dono do estado** — Phases 31-37, em andamento

## Milestone: v1.6 O bd vira dono do estado 🚧

**O GSD fica com a execução. O bd fica com o fato.**

O v1.5 fez o estado dizer onde você está dentro dele, em trinta fases. Este ciclo troca
quem é dono desse estado. O GSD mantém o que faz bem — a execução, e principalmente os
33 agentes, de onde saiu tudo o que mais valeu no ciclo passado: o planejador que achou
quatro premissas erradas antes de escrever um plano, o pesquisador que rodou 17
experimentos e derrubou o requisito que o encomendou, o verificador que achou a fixture
cega ao defeito por construção. O bd passa a ser a fonte do fato.

E o `.planning/` **não é gerado**: ele deixa de ser lido. A primeira proposta era
renderizar os `.md` antes de invocar o GSD, e ela não economiza token nenhum, porque o
GSD lê o arquivo do mesmo jeito. A saída está em **como** os workflows leem — e é por
isso que a fase 31 existe antes de qualquer código.

**Nenhuma das seis premissas que abriram este milestone sobreviveu à reverificação.**
`gsd_run` não existe; são dois binários e duas linhas de runtime instaladas ao mesmo
tempo; os oito workflows que ficam carregam 23 leituras diretas e não 3; e o teto de
token caiu pela metade sozinho, com o arquivamento do v1.5. O ciclo começa medindo o
contrato porque a última vez que ele foi medido à mão, errou em todos os eixos.

## Phases

### 🚧 v1.6 O bd vira dono do estado (Phases 31-37)

- [ ] Phase 31: O contrato medido (INV-01, INV-02, INV-03, INV-04, INV-05, INV-06)
- [ ] Phase 32: O shim que delega sem inventar (SHIM-01, SHIM-02, SHIM-03, SHIM-04, SHIM-05)
- [ ] Phase 33: Fato em banco, argumento em markdown (FACT-01, FACT-02, FACT-03, FACT-04, FACT-05, FACT-06)
- [ ] Phase 34: Os verbos de estado respondem do bd (READ-01, READ-02, READ-03, READ-04)
- [ ] Phase 35: A escrita, ou duas fontes que divergem (WRIT-01, WRIT-02, WRIT-03, WRIT-04)
- [ ] Phase 36: As leituras que o shim não vê (DIR-01, DIR-02, DIR-03, DIR-04, DIR-05)
- [ ] Phase 37: A porta de entrada e o contexto que para de crescer (DOOR-01, DOOR-02, DOOR-03, DOOR-04, DOOR-05)

## Detalhe das fases

### Phase 31: O contrato medido

**Card:** Contra qual runtime este milestone está sendo escrito, e quais verbos e leituras ele de fato tem de responder?

**Goal:** Três das cinco premissas que motivaram o v1.6 mudaram ou caíram na reverificação, e caíram todas do mesmo jeito: a contagem veio de um grep feito à mão sobre um corpus que não era o pinado. `gsd_run` não existe na linha gsd 4.x; `verification.status` tem 6 usos no gsd-core 1.8.0 — que é o que o `marketplace.json` pina — e zero no gsd/4.4.0 que está instalado ao lado. O `cairn-capability.py:286` já sabe disso e escreveu na própria função: "gsd_run is a shim that gsd-core ships; the 4.x line has no gsd_run at all, only gsd-tools.cjs". Ou seja: o projeto tem duas linhas de runtime na máquina, com camadas de consulta diferentes e superfícies de verbo que discordam, e a decisão de contra qual escrever ainda não foi tomada. Esta fase não escreve shim. Ela produz o inventário como artefato executável, para que a próxima medição seja um comando e não um grep de sessão — e para que um bump de gsd-core deixe de mudar o contrato em silêncio.

**Requirements**: INV-01, INV-02, INV-03, INV-04, INV-05, INV-06

**Success criteria:**

1. Um comando enumera, para uma raiz de runtime dada, todo sítio de chamada da camada de consulta com binário, verbo, workflow e linha. **Medição de aceitação:** sobre `gsd-core/1.8.0` devolve 494 sítios e 102 verbos distintos; sobre `gsd/4.4.0` devolve a superfície `bm-sdk query`, 472 sítios e 91 verbos. Os dois números saem do mesmo comando sem editar nada.

2. O relatório nomeia a divergência entre as duas linhas em vez de escolher uma em silêncio. **Medição:** `verification.status` mede 6 em 1.8.0 e 0 em 4.4.0; `config-get` mede 114 contra 105; `commit` mede 62 contra 68. Verbo presente numa linha e ausente na outra sai marcado, e o teste reprova se a saída não distinguir as duas.

3. Cada verbo é classificado como ESTADO, CONFIG-OU-EXECUÇÃO ou DESCONHECIDO, e a classificação é tabela versionada, não ramo de código. **Medição:** os ~50 verbos de estado do 1.8.0 (`init.phase-op` 21, `roadmap.get-phase` 15, `roadmap.analyze` 9, `verification.status` 6, `state.record-session` 6, `state.load` 5, `frontmatter.set` 5, `state.update` 4, e a cauda) somam a contagem que o relatório publica; mudar uma linha da tabela muda o número sem tocar no script.

4. A contagem de leitura direta descarta argumento de escrita e prosa, e diz o que descartou. **Medição:** o grep ingênuo devolve 41 no corpus de referência e 22 sobrevivem; o relatório lista os 19 descartados com o motivo (argumento `--files` de `commit`, string de erro, linha de tabela em prosa). Reprovar `plan-phase.md` — cuja linha só documenta que a FERRAMENTA lê o arquivo — falha o teste, porque ele é o exemplar do padrão desejado, não uma violação.

5. A leitura direta é reportada por mecanismo, separada, porque os três exigem conserto diferente e o shim só alcança um. **Medição nos 8 workflows que ficam:** 6 em shell do orquestrador, 9 em `<files_to_read>` com caminho literal de subagente, 7 em variável de caminho injetada — 23 sítios em 7 dos 8, e `debug` mede zero. A premissa original dizia 3 em 2 workflows; o inventário publica o número medido.

6. O inventário é o baseline: um sítio de chamada que apareça no runtime e não esteja registrado reprova a suíte. É o que torna a fase 32 possível — um diferencial sem inventário testa o que alguém lembrou, não o que existe.

**Research durante o planejamento:** **precisa.**

**Depende de:** nada. É a raiz do ciclo, e a razão é a reverificação: das cinco premissas que abriram este milestone, uma mudou de corpus, duas foram refutadas e duas trocaram de número. Nenhuma fase pode ser dimensionada antes de o corpus alvo estar fixado por comando.

---

### Phase 32: O shim que delega sem inventar

**Card:** O shim já está no caminho de todas as chamadas — e o GSD consegue notar alguma diferença?

**Goal:** O ponto de interceptação existe e prefere o local, mas a cadeia não é a de cinco passos que o `PROJECT.md:136-142` documenta: são 20 ramos, a raiz é `${RUNTIME_DIR:-$(git rev-parse --show-toplevel || pwd)}` e não o git toplevel, e o global `$HOME/.claude` é o ramo 5, com 15 homes de outro agente depois dele. Pior: `cairn-capability.py:discover_gsd_bins()` resolve pela ordem oposta — PATH primeiro, projeto nunca — então hoje o doctor pode validar um binário e os workflows rodarem outro. Esta fase planta o shim e não responde verbo nenhum. É deliberado: o shim fica no caminho de 494 sítios, dos quais cerca de 330 não são de estado (`config-get` 114, `commit` 62, `config-set` 38, `agent-skills` 33). Qualquer infidelidade de passthrough é defeito silencioso em toda a superfície do GSD — exatamente a classe que o v1.5 inteiro existiu para remover. Provar que o shim não muda nada é pré-requisito para deixá-lo mudar alguma coisa.

**Requirements**: SHIM-01, SHIM-02, SHIM-03, SHIM-04, SHIM-05

**Success criteria:**

1. Com o shim instalado e zero verbos implementados, o inventário inteiro da fase 31 roda e devolve stdout, stderr e código de saída idênticos byte a byte aos do gsd-tools real. **O oráculo é o binário real, não um modelo dele.** Um verificador que compartilhasse o modelo do shim concordaria com ele sobre a regra errada e o verde seria lido como saúde.

2. O shim é encontrado pelo mesmo cálculo de raiz que os workflows fazem. **Medição:** quatro casos, quatro asserções — `RUNTIME_DIR` exportado vence o git; worktree; submódulo; e fora de repositório git, onde a cadeia cai em `pwd`. Plantar relativo a uma raiz e ser procurado em outra é o modo de falha, e ele é invisível até alguém abrir um worktree.

3. Verbo desconhecido é delegado **e registrado**, e um comando lista o que caiu no fallback. **Medição:** 58 verbos com ≤2 usos respondem por 16,3% do tráfego e ficam legitimamente em passthrough no dia um — desde que apareçam na lista. Delegar em silêncio é o que faria o shim virar a nova fonte de deriva.

4. O doctor e os workflows resolvem o mesmo binário no mesmo repositório, ou o doctor reporta a divergência nomeando os dois caminhos. **Medição:** num repo com `gsd-core/bin/gsd-tools.cjs` local e um `gsd-tools` diferente no PATH, hoje o doctor valida o do PATH (ramo 1 da política dele) e os workflows rodam o local (ramo 1 da cadeia deles). O teste constrói esse repo e exige que alguém diga o nome dos dois.

5. Um canário de contrato falha quando a cadeia do upstream muda de forma. **Medição:** 20 ramos, global no ramo 5, e três formas convivendo dentro da mesma 1.8.0 — 102 arquivos com 20 ramos, 4 com 19, 3 com a forma legada de 4 sem `.codex`. O teste afirma a forma medida, e o bump de gsd-core passa a ser uma falha vermelha em vez de uma surpresa em produção.

**Research durante o planejamento:** **precisa.**

**Depende de:** Phase 31 — o diferencial precisa do inventário de verbos para saber o que exercitar. Sem ele o teste cobre o que alguém lembrou de listar, que é o defeito de método que derrubou três premissas deste milestone.

---

### Phase 33: Fato em banco, argumento em markdown

**Card:** Que fato do `.planning` entra no bd, e o que continua sendo prosa versionada em markdown?

**Goal:** A regra já está decidida e é o que separa este milestone de uma migração ingênua: FATO migra — fase completa, requisito mapeado, plano executado, veredito de verificação — porque é pequeno, estruturado, consultável e é o que deriva. ARGUMENTO fica em markdown: por que `◑` foi descartado por `east_asian_width=A`, por que hash-chain perde duas vezes, o que foi recusado e por quê. Prosa em coluna de banco continua prosa, e perde `git diff`, grep e review de PR — é o produto mais valioso deste projeto. O veículo já existe e não estava sendo usado: `bd set-state <id> verified=passed --reason '...'` cria event bead como fonte de verdade mais label como cache de lookup, e `bd history` mostra versão a versão. "Fase 21 verificada, passed, 4/4, nesta data, por esta razão" é exatamente um `set-state`. Esta fase também enfrenta o acervo real, que não é limpo: 5 ROADMAPs arquivados, 36 diretórios de fase, 98 planos, e uma deriva de schema medida — 6 dos 28 `VERIFICATION.md` não têm frontmatter nenhum.

**Requirements**: FACT-01, FACT-02, FACT-03, FACT-04, FACT-05, FACT-06

**Success criteria:**

1. O conjunto de fatos está fechado e escrito, e cada um entra por `bd set-state ... --reason`, que cria event bead como fonte e label como cache. **Medição:** `bd history` sobre um fato importado mostra ator, data e motivo; fato gravado sem `--reason` reprova, porque um evento sem motivo é um número sem premissa.

2. Nenhum campo importado carrega argumento em prosa. **Medição:** um teste reprova qualquer campo importado acima de um limite de caracteres declarado no próprio teste, e a razão fica escrita ao lado do limite. O corte é grosseiro de propósito: ele não decide o que é argumento, ele impede que a decisão seja esquecida.

3. A importação roda uma vez e é idempotente. **Medição:** contagem de issues e de eventos antes e depois da segunda execução é idêntica, e a segunda execução **diz** que já rodou. Sair 0 em silêncio é o defeito que o v1.2 encontrou e que este projeto não repete.

4. Fonte sem frontmatter importa como **desconhecido**, nunca com valor inventado, e aparece numa lista do que não pôde ser lido. **Medição:** os 6 `VERIFICATION.md` sem frontmatter (3 em v1.2, 3 em v1.3, contra 22 com) aparecem na lista pelo nome do arquivo.

5. A contagem que valida a importação vem de implementação que **não compartilha parser** com a que importou. **Medição:** o número de fases nos cinco `*-ROADMAP.md` arquivados e o número de fatos de fase no bd batem, contados por dois caminhos independentes. O mapa da codebase já registra "parsing regex leniente de ROADMAP/STATE" como concern conhecido: com um parser só, escritor e verificador concordariam sobre a mesma leitura errada e a concordância seria lida como saúde.

6. O destino de `.planning/milestones/` é decidido e registrado — importado ou história congelada — e, seja qual for a resposta, o doctor diz quais milestones têm fato no bd e quais não têm. **Medição:** 5 ROADMAPs, 36 diretórios de fase, 98 planos; nenhum deles pode ficar num estado que o doctor não saiba nomear.

**Research durante o planejamento:** **precisa.**

**Depende de:** Phase 31 — a classificação ESTADO/CONFIG do inventário é o que decide qual fato migra. Não depende da fase 32 e pode correr em paralelo com ela: uma mexe no caminho de execução, a outra no acervo.

---

### Phase 34: Os verbos de estado respondem do bd

**Card:** Os verbos de estado param de delegar e passam a responder do bd — e a resposta é a mesma?

**Goal:** Com o passthrough provado fiel (32) e o fato no banco (33), os verbos de estado viram. A ordem de implementação sai da medição do corpus alvo e não da lista que abriu o milestone, e a diferença é grande: no gsd-core 1.8.0 os verbos de estado mais chamados são `init.phase-op` (21), `roadmap.get-phase` (15), `roadmap.analyze` (9), `verification.status` (6), `state.record-session` (6) e `state.load` (5) — e os 45 sítios da família `init.*` são o maior lever único, porque é dela que saem os caminhos que a fase 36 vai redirecionar. O ganho que a geração de markdown não dava aparece aqui: o shim devolve **a fatia**, não o arquivo. Mas o ganho tem de ser medido onde ele acontece. O teto caiu: a raiz do `.planning/` custa hoje 10.438 tokens e não 21.725, o arquivamento do v1.5 já colheu 51,6% e 99,9% disso veio do ROADMAP sozinho, que hoje é 235 tokens — 2,3% da raiz. E ninguém instrumentou quais desses arquivos são de fato carregados em cada contexto de agente: o que existe é tamanho de arquivo, não leitura efetiva.

**Requirements**: READ-01, READ-02, READ-03, READ-04

**Success criteria:**

1. Cada verbo de estado respondido do bd devolve a mesma **forma** de payload que o gsd-tools real devolve para a mesma entrada — mesmas chaves, mesmos tipos. **Medição:** diferencial contra o binário real sobre repositório de fixture, verbo a verbo, e a lista dos verbos exercitados sai do inventário da fase 31, não de uma lista escrita à mão.

2. Verbo de estado que o bd não sabe responder **falha nomeando o fato que falta**. Não devolve forma vazia, não cai no arquivo em silêncio, não inventa default. Uma superfície que responde sem saber sobre o que está respondendo não conta como pronta — foi o doctor com 16 ok e 0 falhas sobre um roadmap vazio que ensinou isso, e ele estava dentro da própria ferramenta construída para não mentir.

3. A ordem de implementação é a medida no corpus alvo, e o relatório prova a ordem. **Medição:** `init.phase-op` 21, `roadmap.get-phase` 15, `roadmap.analyze` 9, `verification.status` 6, `state.record-session` 6, `state.load` 5. Uma implementação que comece pela lista antiga entregaria cobertura mínima achando que entregou o núcleo.

4. O ganho de token é medido **no contexto que o agente recebe**, não no tamanho do arquivo. **Medição:** a mesma operação de fase, antes e depois, com a contagem de tokens efetivamente entregue ao agente. Se a medição der zero, zero é o resultado registrado — o v1.1 existiu para combater o anti-padrão de alegação sem dado, e o próprio benchmark deste projeto já refutou uma alegação de custo antes.

5. A cobertura é derivada do inventário: o relatório diz qual fração dos sítios de estado é respondida do bd e qual caiu em passthrough, e a fração é conferível rodando o comando da fase 31 em vez de acreditar no relatório.

**Research durante o planejamento:** não precisa.

**Depende de:** Phase 32 e Phase 33 — precisa do caminho provado fiel (32) e do fato no banco (33). Responder verbo de estado sem uma das duas é inventar resposta com aparência de fonte única.

---

### Phase 35: A escrita, ou duas fontes que divergem

**Card:** Agora que o dono do estado mudou, quem escreve estado escreve onde?

**Goal:** É o furo que a reverificação abriu e o mais caro de todos. A premissa dizia que a autoria de estado saía junto com os workflows que saem; medido, não sai: os 8 workflows que **ficam** carregam 24 instruções de escrita de estado, `execute-phase` sozinho tem 9 (`Update STATE.md for phase start`, e mais), e `verify-work` marca fase completa no ROADMAP tendo zero leitura direta. Se o bd vira dono do estado e esses continuam escrevendo markdown, o v1.6 fabrica duas fontes que divergem — a mesma classe de defeito que o v1.5 gastou trinta fases removendo, agora com a corrupção vindo do workflow e não da escrita do gsd-tools. Além disso, dois dos três verbos mais chamados são de escrita (`commit` 62, `config-set` 38): um shim desenhado como camada de consulta pura não os atende, e precisa de contrato de escrita, semântica de erro e decisão explícita de idempotência. O v1.5 já viu o que a escrita sem guarda faz: `state.record-metric` gravou `current_phase: 18` — fase de milestone arquivado — duas vezes, lendo prosa obsoleta.

**Requirements**: WRIT-01, WRIT-02, WRIT-03, WRIT-04

**Success criteria:**

1. Todo verbo de escrita de estado grava no bd como evento consultável com ator, data e motivo. **Medição:** a lista sai do inventário — `state.update`, `state.record-session`, `state.record-metric`, `roadmap.update-plan-progress`, `frontmatter.set`, `phase.complete`, `requirements.mark-complete`, `quick-tasks-append` — e cada um tem evento correspondente no `bd history` depois de exercitado.

2. Gravar duas vezes o mesmo fato é idempotente ou versionado, e o histórico diz qual venceu e por quê. **Medição:** o teste reproduz a entrada concreta que causou o defeito — `state.record-metric` escrevendo `current_phase: 18` a partir de prosa obsoleta, duas vezes — e prova que o caminho novo não repete o resultado.

3. Instrução de escrita direta em `.planning/*.md` dentro do laço é **detectada e nomeada**. **Medição:** 24 instruções de escrita de estado nos 8 workflows que ficam, distribuídas em 7 deles, com `execute-phase` em 9. A detecção é o entregável desta fase; a conversão do residual vem depois e vem com o próprio número, para que o escopo não seja estimado por adjetivo.

4. Verbo de escrita que não é de estado continua delegando com fidelidade, e isso vira portão permanente. **Medição:** `commit` (62) e `config-set` (38) são 100 dos 494 sítios do corpus; o diferencial da fase 32 roda sobre eles a cada mudança do shim, e não só quando alguém lembra.

**Research durante o planejamento:** não precisa.

**Depende de:** Phase 34 — a escrita só faz sentido depois que a leitura do bd tem forma acordada. Inverter cria evento cuja leitura ninguém sabe devolver, que é fonte única no papel e duas fontes na prática.

---

### Phase 36: As leituras que o shim não vê

**Card:** E as leituras que nunca passam pela camada de consulta, inclusive as nove que rodam dentro do subagente?

**Goal:** O shim fica no caminho da consulta. As leituras diretas passam ao largo dele, por construção. Medido nos 8 workflows que ficam: 23 sítios, em 7 dos 8, por **três mecanismos que exigem três consertos diferentes**. Seis são `cat`/`Read` no orquestrador (`discuss-phase` 228-230, `execute-phase` 1688, `fast` 72, `autonomous` 562) e podem ser alcançados por hook de Bash. Nove são `<files_to_read>` com caminho literal dentro de prompt de subagente (`execute-phase` 598, 599, 1445; `verify-work` 563, 564; `quick` 371, 372, 429, 666) — esses rodam no contexto do agente spawnado, então hook no orquestrador **nunca os vê**; é o buraco mais caro e o mais fácil de esquecer. Sete são variáveis `{state_path}`, `{roadmap_path}` e `{requirements_path}` resolvidas pelo init JSON e declaradas em `plan-phase.md:58` — e essa é a alavanca real: mudar a resolução redireciona as sete de uma vez sem tocar no texto do workflow. A premissa original tinha isso invertido: dava `plan-phase` como o caso trivial de uma leitura e não mencionava `execute-phase` nem `quick`, que são os difíceis.

**Requirements**: DIR-01, DIR-02, DIR-03, DIR-04, DIR-05

**Success criteria:**

1. A variável de caminho injetada pela camada de init aponta para o alvo do desenho e o texto do workflow não muda. **Medição:** os 7 sítios de `plan-phase.md` (`{requirements_path}` e `{state_path}` em 496-497; `{state_path}`, `{roadmap_path}`, `{requirements_path}` em 864-866; `{roadmap_path}` e `{requirements_path}` em 1204-1205) mudam de destino com `git diff plan-phase.md` **vazio** — zero linha alterada. É a prova de que a interceptação é central e não 7 remendos.

2. Prompt de subagente que recebe caminho literal de arquivo de estado fora do inventário reprova a suíte. **Medição:** os 9 sítios são enumerados por arquivo e linha, cada um com a decisão registrada e a razão ao lado; um décimo que apareça sem estar no inventário falha o teste.

3. Cada uma das 6 leituras em shell do orquestrador tem destino decidido e registrado. **Medição:** `discuss-phase` 228, 229 e 230 são um bloco `bash` único no step `load_prior_context` e podem ter uma decisão só; `execute-phase` 1688, `fast` 72 e `autonomous` 562 são independentes e têm três. Um sítio sem decisão escrita reprova.

4. Workflow com superfície zero sai de escopo **com a medição ao lado**, para ninguém replanejar contra ele. **Medição:** `debug` mede 0 leituras diretas, e o skill `debug` sequer carrega `workflows/debug.md` — o corpo está no próprio `SKILL.md`. As duas medições ficam no artefato.

5. O arquivo alvo de cada workflow é provado pelo que a skill carrega, não pelo nome. **Medição:** "verify" é `verify-work.md`, carregado por `skills/verify-work/SKILL.md:23` e invocado por `commands/verify.md:9`; `verify-phase.md` é órfão — nada em `skills/` ou `workflows/` o carrega. Planejar contra o órfão somaria 2 sítios fantasma e deixaria os 2 reais de fora.

**Research durante o planejamento:** não precisa.

**Depende de:** Phase 34 — o critério 1 exige que a resolução de caminho vinda de `init`/`state.load` já tenha para onde apontar. Antes disso a alavanca existe e não tem destino.

---

### Phase 37: A porta de entrada e o contexto que para de crescer

**Card:** Como o usuário novo descobre a mudança, como o usuário antigo atravessa uma vez só, e o que fazer com o bloco que ninguém consulta e viaja em todo contexto?

**Goal:** Fecha a migração e enfrenta o alvo de custo que sobreviveu à remedição — que não é o que o milestone pensava. O arquivamento do v1.5 cortou 51,6% da raiz do `.planning/`, mas 99,9% do corte veio do ROADMAP sozinho (45.495 → 942 bytes), que hoje é 235 tokens, 2,3% do total. Qualquer trabalho justificado por tamanho de ROADMAP perdeu o insumo. O que o arquivamento **não** tocou é o alvo real: o bloco `Accumulated Context` do `STATE.md` saiu byte a byte idêntico e subiu de 11,8% para 24,6% da raiz — 10.253 bytes, cerca de 2.563 tokens, com decisões das fases 1 a 6 do v1.1, milestone publicado em 27 de julho, e as ferramentas leem 126 tokens de frontmatter. Ele é imune ao ciclo de milestone e só encolhe se este milestone criar mecanismo próprio. `STATE` e `PROJECT` juntos são 69,2% da raiz. Do outro lado, a migração: usuário novo sabe pelo `init` que a fonte é o bd; usuário antigo tem o `.planning` existente importado **uma** vez pelo `doctor`.

**Requirements**: DOOR-01, DOOR-02, DOOR-03, DOOR-04, DOOR-05

**Success criteria:**

1. O `/cairn:init` diz ao usuário novo que a fonte do estado é o bd, e um repositório novo fecha um ciclo de fase sem ninguém escrever `.planning/STATE.md` à mão. **Medição:** teste de ponta a ponta em repositório temporário, com asserção sobre o que existe em disco ao fim e sobre o que a saída do `init` afirmou.

2. O `doctor` detecta `.planning` nunca importado, propõe, importa uma vez, e recusa a segunda — reportando quantos fatos entraram e quantas fontes não pôde ler. **Medição:** o segundo número inclui os 6 `VERIFICATION.md` sem frontmatter, nomeados; e a terceira invocação não muda contagem nenhuma.

3. O bloco `Accumulated Context` tem regra própria de expiração, porque o ciclo de milestone não o alcança. **Medição:** ele atravessou o arquivamento do v1.5 byte a byte idêntico — o `STATE.md` inteiro perdeu 15 bytes, e o diff é só o front-matter YAML. Hoje são 10.253 bytes ≈ 2.563 tokens. O critério é o número medido depois da regra, e a regra de descarte escrita ao lado do número.

4. Nenhuma superfície publica número de token que não venha da medição de consumo da fase 34. **Medição:** um grep prova que `21.725` não aparece em README, docs, `PROJECT.md` nem issue do bd — o número está morto, o teto de hoje é 10.438, e o único número publicável é o de contexto entregue ao agente.

5. A checagem de importação em repositório sem `.planning` reporta **não-aplicável**, nunca `ok`. É o estado que a fase 23 criou exatamente para isso, e o defeito que abriu o v1.5 foi o doctor dando 16 ok e 0 falhas sobre um roadmap vazio: três checagens passando por não ter o que checar.

**Research durante o planejamento:** **precisa.**

**Depende de:** Phase 33, Phase 35 e Phase 36 — é a porta de entrada, e porta que abre antes de o caminho existir entrega meia migração ao usuário antigo: fato importado (33), escrita apontando para o bd (35) e leitura direta com destino (36).

---

## Cobertura

| Requisito | Fase | Status |
|-----------|------|--------|
| INV-01 | Phase 31 | Pending |
| INV-02 | Phase 31 | Pending |
| INV-03 | Phase 31 | Pending |
| INV-04 | Phase 31 | Pending |
| INV-05 | Phase 31 | Pending |
| INV-06 | Phase 31 | Pending |
| SHIM-01 | Phase 32 | Pending |
| SHIM-02 | Phase 32 | Pending |
| SHIM-03 | Phase 32 | Pending |
| SHIM-04 | Phase 32 | Pending |
| SHIM-05 | Phase 32 | Pending |
| FACT-01 | Phase 33 | Pending |
| FACT-02 | Phase 33 | Pending |
| FACT-03 | Phase 33 | Pending |
| FACT-04 | Phase 33 | Pending |
| FACT-05 | Phase 33 | Pending |
| FACT-06 | Phase 33 | Pending |
| READ-01 | Phase 34 | Pending |
| READ-02 | Phase 34 | Pending |
| READ-03 | Phase 34 | Pending |
| READ-04 | Phase 34 | Pending |
| WRIT-01 | Phase 35 | Pending |
| WRIT-02 | Phase 35 | Pending |
| WRIT-03 | Phase 35 | Pending |
| WRIT-04 | Phase 35 | Pending |
| DIR-01 | Phase 36 | Pending |
| DIR-02 | Phase 36 | Pending |
| DIR-03 | Phase 36 | Pending |
| DIR-04 | Phase 36 | Pending |
| DIR-05 | Phase 36 | Pending |
| DOOR-01 | Phase 37 | Pending |
| DOOR-02 | Phase 37 | Pending |
| DOOR-03 | Phase 37 | Pending |
| DOOR-04 | Phase 37 | Pending |
| DOOR-05 | Phase 37 | Pending |

35 requisitos, 35 mapeados.

## Riscos registrados na abertura

- **Duas linhas de runtime instaladas ao mesmo tempo, e a escolha ainda não foi feita.** O `marketplace.json` pina `gsd-core` v1.8.0 (camada `gsd_run query` / `gsd-tools.cjs`, 494 sítios, 102 verbos), mas o cache tem `gsd` 4.3.1 e 4.4.0 (camada `bm-sdk query`, 472 sítios, 91 verbos). As superfícies discordam de verdade: `verification.status` tem 6 usos numa e 0 na outra. Um shim escrito contra uma não atende a outra, e `cairn-capability.py:286` já registra a diferença sem que nada a resolva.
- **O shim vira a nova fonte de deriva.** Ele fica no caminho de 494 sítios, dos quais cerca de 330 não são de estado (`config-get` 114, `commit` 62, `config-set` 38, `agent-skills` 33). Infidelidade de passthrough é defeito silencioso em toda a superfície do GSD, e é exatamente a classe que o v1.5 inteiro existiu para remover. Por isso a fase 32 responde zero verbos.
- **A escrita é o furo mais caro e a premissa original o escondia.** Os 8 workflows que FICAM carregam 24 instruções de escrita de estado, `execute-phase` sozinho com 9 e `verify-work` marcando fase completa no ROADMAP sem ler nada. Se o bd vira dono e eles continuam escrevendo markdown, este milestone fabrica duas fontes divergentes — a mesma classe de defeito que o v1.5 gastou trinta fases removendo, agora com a corrupção vindo do workflow.
- **Os 9 sítios `<files_to_read>` rodam dentro do subagente spawnado.** Hook no orquestrador nunca os vê. É o mecanismo que o desenho tende a esquecer porque não aparece em nenhuma camada interceptável, e são 9 dos 23 sítios do conjunto que fica.
- **O ganho de token pode ser zero, e o registro honesto do zero é o resultado.** O teto caiu de 21.589 para 10.438 tokens; o arquivamento do v1.5 já colheu 51,6% e quase tudo veio do ROADMAP, hoje 2,3% da raiz. E ninguém instrumentou quais arquivos são de fato carregados em cada contexto de agente: o que existe é tamanho de arquivo, não leitura efetiva. Uma fase justificada por economia pode medir nada.
- **Deriva de schema no acervo.** 6 dos 28 `VERIFICATION.md` não têm frontmatter (3 em v1.2, 3 em v1.3), e são 98 planos em 36 diretórios de fase sob 5 ROADMAPs. Import que assume frontmatter inventa valor ou perde fato, e as duas falham em silêncio.
- **Cadeia de resolução de terceiro que já drifta dentro da própria versão.** 20 ramos, raiz calculada por `${RUNTIME_DIR:-...}` e não pelo git toplevel, global no ramo 5 com 15 homes de agente depois, e três formas convivendo na mesma 1.8.0 (102 arquivos com 20 ramos, 4 com 19, 3 com a legada de 4). Um bump de gsd-core muda o contrato sob o shim sem aviso.
- **Escritor e verificador que compartilham a mesma regra errada concordam.** O import, o shim e o doctor podem herdar o mesmo parser de ROADMAP/STATE — e o mapa da codebase já registra "parsing regex leniente de ROADMAP/STATE" como concern conhecido. O verde sairia da concordância, não da verdade, e seria lido como saúde.
- **O doctor pode validar um binário e os workflows rodarem outro.** `cairn-capability.py:discover_gsd_bins()` procura PATH primeiro e nunca olha o projeto; a cadeia dos workflows procura o projeto no ramo 1 e o PATH só no ramo 4. Enquanto as duas políticas divergirem, o portão de verificação do v1.6 não significa nada.

Trabalho aberto e sem fase vive no beads (`bd ready`), não aqui.
