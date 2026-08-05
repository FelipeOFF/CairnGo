# Requirements: CairnGo v1.5 Legible State

**Definido 2026-08-03.** O v1.4 fez o estado provar o que afirma. Este ciclo faz
o estado dizer **onde você está dentro dele** — e faz toda superfície parar de
responder sobre o que não checou.

O padrão para qualquer critério aqui: uma superfície que responde sem saber sobre
o que está respondendo não conta como pronta.

## v1.5 Requirements

### O board que situa (BOARD)

- [x] **BOARD-01**: O **modelo** carrega a hierarquia milestone → fase → tarefa: milestones abertos primeiro, trabalho sem milestone em grupo próprio e por último
- [ ] **BOARD-06**: O **board renderiza** agrupado — milestones abertos primeiro, fases dentro deles, trabalho sem milestone por último
- [ ] **BOARD-02**: Cada linha carrega a etapa (não planejada, planejada, em execução, feita, bloqueada) num símbolo de largura simples, com fallback ASCII sob `--ascii`
- [ ] **BOARD-03**: O título de uma tarefa não é truncado no render humano, em nenhuma largura de terminal em que a linha caiba
- [ ] **BOARD-04**: O cabeçalho diz qual milestone está aberto, e diz explicitamente quando não há nenhum — nunca repete o último arquivado
- [ ] **BOARD-05**: Uma linha bloqueada nomeia por quem está bloqueada, na própria linha

### O contrato de máquina (PIPE)

- [ ] **PIPE-01**: `--plain` continua sendo TSV estável para script, byte a byte compatível com o que existe hoje
- [ ] **PIPE-02**: O caminho não-TTY deixa de degradar para `--plain` e passa a renderizar a lista agrupada em texto puro — sem box-drawing, sem ANSI, mas legível
- [ ] **PIPE-03**: O teste que hoje afirma que `--plain` é idêntico ao default não-TTY é reescrito como duas asserções separadas, nunca removido

### Não-aplicável como estado de primeira classe (VOID)

- [ ] **VOID-01**: Uma checagem sem nada para checar reporta `not-applicable`, distinto de `ok`, e o resumo do doctor conta os dois separadamente
- [ ] **VOID-02**: Um roadmap vazio não produz board verde: `req-issue`, `maps-fresh` e `orphans` reportam não-aplicável em vez de aprovar o nada
- [ ] **VOID-03**: `orphans` para de sinalizar issue fechada de milestone arquivado, e a contagem zera ao fim de um ciclo em vez de crescer para sempre

### Linguagem escolhida na instalação (LANG)

- [ ] **LANG-01**: `/cairn:init` pergunta a linguagem de resposta e grava a escolha na config local, com inglês como default
- [ ] **LANG-02**: A escolha alcança todo subagente spawnado pelo lifecycle, provado por teste que lê o valor no ponto de entrega, não na config

### Os wrappers `/cairn:*` (WRAP)

- [ ] **WRAP-01**: Os 13 wrappers decididos no GSD-05 existem e delegam ao comando `/gsd:*` correspondente, cada um com o bookkeeping bd da casa
- [ ] **WRAP-02**: Um wrapper cujo comando GSD correspondente não existe falha nomeando o que falta, em vez de sair 0 em silêncio
- [ ] **WRAP-03**: A documentação lista os wrappers a partir do que está instalado, não de uma lista escrita à mão que envelhece

### Tendência entre ciclos (TREND)

- [ ] **TREND-01**: Um comando de leitura mostra como a discordância entre fontes evoluiu ao longo dos milestones arquivados
- [ ] **TREND-02**: A tendência é derivada dos artefatos arquivados, nunca de número digitado à mão, e diz quando não há dado suficiente

### Journal durável (DJOUR)

- [ ] **DJOUR-01**: A alternativa de hash-chain é pesquisada e decidida **antes** de qualquer código: um `merge=union` cru reordena e deduplica registros, e isso precisa estar resolvido
- [ ] **DJOUR-02**: O journal sobrevive entre máquinas sem que merge reordene ou perca registro, provado por teste que mescla dois journals divergentes
- [ ] **DJOUR-03**: O journal versionado continua sem ser autoridade sobre o estado corrente — apagá-lo não muda veredito nenhum

### Limpeza medida (FIX)

- [ ] **FIX-01**: `/cairn:milestone new` para de mandar gerar mapa antes de existir diretório de fase
- [ ] **FIX-02**: O nome da branch de uma fase não deriva quando o diretório da fase passa a existir depois do `prepare`
- [ ] **FIX-03**: O campo `status` por portador do `cairn-release --json` significa "está correto", ou é renomeado para dizer o que de fato significa
- [ ] **FIX-05**: Uma fase com um plano de três executados para de ler como `executed`, e a corroboração para de fabricar conflito bloqueante a partir disso
- [ ] **FIX-04**: Uma dependência para fase de milestone arquivado deixa de bloquear para sempre, e uma aresta `discovered-from` deixa de contar como bloqueio

### Nada mecânico continua manual (AUTO)

- [x] **AUTO-01**: O bookkeeping de fim de fase — marcar a fase completa, marcar seus requisitos completos, mexer os contadores do STATE, atualizar o mapa, liberar o lease — é **um comando**, e nenhuma dessas edições volta a ser feita à mão
- [x] **AUTO-02**: O Jira é **detectado, confirmado e então configurado pelo cairn** — híbrido: ele procura o MCP do Atlassian e chaves `ABC-123` em branch e commits, mostra o que achou, pergunta **uma vez**, e a partir do "sim" grava a configuração sozinho. O usuário confirma; nunca digita chave, projeto ou credencial
- [x] **AUTO-03**: Um card do Jira associado a uma fase ou a uma issue aparece no board sem que o caminho padrão faça chamada de rede
- [x] **AUTO-04**: A suíte roda em paralelo quando o ambiente permite, e diz claramente quando não permite em vez de rodar serial em silêncio
- [x] **AUTO-05**: O cairn tem config própria, perguntada como o GSD pergunta **e** editável à mão no `.json` — as duas portas para o mesmo lugar, nunca só uma
- [x] **AUTO-07**: Uma checagem valida a cadeia inteira do registro de requisitos — requisito ativo → linha na tabela de Cobertura → número afirmado no rodapé — que hoje **ninguém** valida
- [x] **AUTO-08**: Nenhuma checagem do doctor volta a dizer `ok` por não ter conseguido checar — uma checagem sem insumo diz que está sem insumo, nomeia o que falta e roteia para quem decide, sem bloquear
- [x] **AUTO-06**: A config cobre o que hoje não tem onde morar: commit automático, PR por fase ou por milestone, teto de ciclos e de laços do run autônomo, e o que já está espalhado em `.cairn/` passa a ser listado num lugar só
- [ ] **AUTO-10**: O `STATE.md` fala o dialeto que o cairn de fato lê — hoje o cairn **escreve** `current_phase`, chave que nenhum arquivo dele lê, enquanto cinco leem `active_phase`. Qual dialeto vence é decisão de regra de negócio, aberta em grooming, e a escolha muda o comportamento de todo repositório que já tem `STATE.md` escrito

### O que entrou na branch (PR)

- [ ] **PR-01**: O board diz, por fase e por tarefa, se o trabalho já entrou na branch de controle — respondido do git local, sem rede, e a branch é detectada, confirmada uma vez e gravada, nunca digitada
- [ ] **PR-02**: A PR associada aparece quando é descobrível; quando não é, o estado é `desconhecido` e diz o que faltou — nunca "sem PR", que é o verde falso na direção oposta
- [ ] **PR-03**: O estado de revisão vem do `gh`/`glab` atrás de config, nunca no caminho padrão, e o board diz que o dado é de cache e de quando
- [ ] **PR-04**: Uma fase marcada completa cujo trabalho não entrou na branch de controle vira achado nomeado do doctor

## Deferred (v2)

- **CORR-09**: Severidade de conflito com allowlist configurável — segue adiado. Exige corpus real de tipos de conflito; inventar níveis sobre zero dado é o erro que a pesquisa do v1.4 descreve.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Remover o reparo de manifesto do gsd-core (`CairnGo-c8v`) | Auto-disparado pelo CI quando o upstream resolver; não precisa de fase |
| Board interativo (TUI com foco e navegação por teclado) | O cairn é stdlib-only; Textual e afins são dependência de terceiros, e o board é saída de comando, não aplicação |
| Emoji coloridos de largura dupla | Medido: quebram alinhamento em terminal com locale CJK. Decisão D-04 do discuss |
