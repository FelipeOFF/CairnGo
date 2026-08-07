# Requirements: CairnGo v1.6 — o bd vira dono do estado

**Definido 2026-08-07.** O v1.5 fez o estado dizer onde você está dentro dele. Este
ciclo troca **quem é dono** desse estado: o GSD fica com a execução e com os seus 33
agentes, e o bd passa a ser a fonte do fato — fase completa, requisito mapeado, plano
executado, veredito de verificação.

O `.planning/` não é gerado. Ele **deixa de ser lido**.

## O que a reverificação mudou, antes de escrever qualquer requisito

Este milestone foi decidido em 2026-08-06 sobre seis medições. Todas as seis foram
refeitas em 2026-08-07, contra o runtime instalado, e **nenhuma sobreviveu intacta**:

| afirmação de 06/08 | medido em 07/08 |
|---|---|
| a camada de consulta é `gsd_run query` | **`gsd_run` não existe na linha 4.x.** São `bm-sdk query` (fallback `gsd-sdk`) e `gsd-tools.cjs` — **duas** superfícies |
| 91 workflows | 90 no topo, mais 14 em subdiretório. O 92 contava dois diretórios como arquivo |
| 21 leem arquivo direto, e são os que saem | 22, e **17 já usam a camada** — a migração real são 5 arquivos, não 21 |
| os 8 que ficam somam 3 leituras diretas | **23**, em 7 dos 8, por três mecanismos diferentes |
| 53 verbos, `init.phase-op` no topo | **91 verbos distintos**, 472 sítios, e o topo é `config-get` com 105 |
| a cadeia de resolução tem 5 ramos | **20**, duplicada em 102 de 112 arquivos, e o global não é o último |
| `.planning/` custa 21.725 tokens | **10.438.** O arquivamento do v1.5 cortou metade antes de o ciclo começar |

Duas consequências que os requisitos abaixo carregam:

- **Existem duas linhas de runtime instaladas ao mesmo tempo** — `gsd-core` 1.8.0, que
  o `marketplace.json` pina, e `gsd/4.4.0`, no cache do plugin. Elas têm camadas de
  consulta diferentes e superfícies de verbo que discordam. Escolher uma em silêncio é
  o primeiro jeito de este milestone mentir.
- **O ganho de token pode ser zero.** O teto caiu pela metade sozinho. Se a medição da
  fase 34 der zero, zero é o resultado publicado — o v1.1 existiu para combater o
  anti-padrão de alegação sem dado, e não é neste ciclo que ele volta.

O padrão daqui, herdado e endurecido: **escritor e verificador que compartilham a
mesma regra errada concordam, e a concordância é lida como saúde.** Todo verificador
deste ciclo é independente de quem escreveu.

## v1.6 Requirements

### O contrato medido (INV)

- [ ] **INV-01**: Um comando enumera, para uma raiz de runtime GSD dada, todo sítio de chamada da camada de consulta com binário, verbo, workflow e linha.
- [ ] **INV-02**: O relatório nomeia a divergência entre as duas linhas de runtime instaladas em vez de escolher uma em silêncio.
- [ ] **INV-03**: Cada verbo é classificado como estado, configuração-ou-execução, ou desconhecido, e a classificação é dado versionado, não ramo de código.
- [ ] **INV-04**: A contagem de leitura direta de arquivo de estado exclui argumento de escrita e prosa, e lista o que descartou com o motivo.
- [ ] **INV-05**: A leitura direta é reportada separada por mecanismo: shell do orquestrador, caminho literal em prompt de subagente, e variável de caminho injetada.
- [ ] **INV-06**: Um sítio de chamada que apareça no runtime e não esteja no inventário reprova a suíte.

### O shim que delega sem inventar (SHIM)

- [ ] **SHIM-01**: Com nenhum verbo implementado, toda invocação através do shim devolve stdout, stderr e código de saída idênticos aos do gsd-tools real.
- [ ] **SHIM-02**: O shim é resolvido pelo mesmo cálculo de raiz que os workflows fazem, inclusive sob RUNTIME_DIR, em worktree, em submódulo e fora de repositório git.
- [ ] **SHIM-03**: Verbo desconhecido é delegado e registrado, e um comando lista o que caiu no fallback.
- [ ] **SHIM-04**: O doctor e os workflows resolvem o mesmo binário gsd-tools, ou o doctor reporta a divergência nomeando os dois caminhos.
- [ ] **SHIM-05**: A suíte falha quando a cadeia de resolução do upstream muda de forma.

### Fato em banco, argumento em markdown (FACT)

- [ ] **FACT-01**: Fase completa, requisito mapeado, plano executado e veredito de verificação existem no bd como evento com ator, data e motivo.
- [ ] **FACT-02**: Nenhum campo importado carrega argumento em prosa; o argumento continua em markdown versionado.
- [ ] **FACT-03**: A importação do .planning existente roda uma vez, e a segunda execução não cria fato nenhum e diz que já rodou.
- [ ] **FACT-04**: Fonte sem frontmatter importa como desconhecido e aparece numa lista do que não pôde ser lido.
- [ ] **FACT-05**: A validação da importação é produzida por implementação que não compartilha parser com a que importou.
- [ ] **FACT-06**: O destino do acervo arquivado é declarado, e o doctor diz quais milestones têm fato no bd e quais não têm.

### Os verbos de estado respondem do bd (READ)

- [ ] **READ-01**: Verbo de estado respondido do bd devolve a mesma forma de payload que o gsd-tools real devolve para a mesma entrada.
- [ ] **READ-02**: Verbo de estado sem fato correspondente falha nomeando o que falta, em vez de devolver forma vazia ou cair no arquivo.
- [ ] **READ-03**: O ganho de token é medido no contexto que o agente recebe, e o número publicado é o medido, inclusive quando é zero.
- [ ] **READ-04**: A cobertura dos verbos de estado é derivada do inventário, não de lista escrita à mão.

### A escrita, e as duas fontes que podem divergir (WRIT)

- [ ] **WRIT-01**: Escrita de estado feita pela camada de ferramenta grava no bd como evento consultável.
- [ ] **WRIT-02**: Gravar duas vezes o mesmo fato é idempotente ou versionado, e o histórico diz qual venceu e por quê.
- [ ] **WRIT-03**: Instrução de escrita direta em .planning/*.md dentro do laço é detectada e nomeada.
- [ ] **WRIT-04**: Verbo de escrita que não é de estado continua delegando com fidelidade, e o diferencial roda sobre ele a cada mudança do shim.

### As leituras que o shim não vê (DIR)

- [ ] **DIR-01**: A variável de caminho de estado injetada pela camada de init aponta para o alvo do desenho sem que o texto do workflow mude.
- [ ] **DIR-02**: Prompt de subagente que recebe caminho literal de arquivo de estado fora do inventário reprova a suíte.
- [ ] **DIR-03**: Cada leitura direta em shell do orquestrador tem destino decidido e registrado.
- [ ] **DIR-04**: Workflow com superfície de leitura zero é declarado fora de escopo com a medição ao lado.
- [ ] **DIR-05**: O arquivo alvo de cada workflow do conjunto que fica é provado pelo que a skill carrega, não pelo nome do arquivo.

### A porta de entrada, e o contexto que para de crescer (DOOR)

- [ ] **DOOR-01**: O init diz ao usuário novo que a fonte do estado é o bd, e um repositório novo fecha um ciclo sem ninguém escrever .planning/STATE.md à mão.
- [ ] **DOOR-02**: O doctor detecta .planning nunca importado, propõe, importa uma vez, recusa a segunda, e reporta quantos fatos entraram e quantas fontes não pôde ler.
- [ ] **DOOR-03**: O bloco de contexto acumulado tem regra própria de expiração, independente do ciclo de milestone.
- [ ] **DOOR-04**: Nenhuma superfície publica número de token que não venha da medição de consumo.
- [ ] **DOOR-05**: Checagem de importação em repositório sem .planning reporta não-aplicável, nunca ok.

## Deferred (v2)

- **CORR-09**: Severidade de conflito com allowlist configurável — adiado desde o v1.4.
  Exige corpus real de tipos de conflito, e inventar níveis sobre zero dado é o erro que
  a pesquisa daquele ciclo descreve.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Substituir os agentes do GSD | São o ativo. Neste ciclo eles ganham fonte de estado nova, não substituto |
| Migrar argumento para o banco | Prosa em coluna de banco continua prosa, e perde `git diff`, grep e review de PR |
| Reescrever `.planning/milestones/` arquivado | O destino é decidido na fase 33; reescrever história é outra decisão |
| Um shim que assuma um ponto de entrada só | Medido: são dois binários. Um shim com essa premissa deixa `pr-branch` e `spec-phase` para trás |
