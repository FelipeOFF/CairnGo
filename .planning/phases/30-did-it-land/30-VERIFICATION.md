---
phase: 30-did-it-land
verified: 2026-08-07T05:20:00Z
status: gaps_found
score: 5/5 critérios verificados, 4/4 requisitos entregues
behavior_unverified: 2
behavior_unverified_items:
  - behavior: "Uma chamada real a `gh pr view --json number,state,title,url,mergedAt` contra a API do GitHub, e o formato que ela devolve"
    why: "Toda a suíte usa um stub de `gh` no PATH que responde de um payload enlatado — de propósito, porque nenhum teste desta fase pode sair da máquina. O que isso prova é o CAMINHO: o interruptor, o carimbo, o cache, a idade, a degradação. O que NÃO prova é que os cinco campos pedidos existem com essa grafia na resposta real, nem que `state` vem em maiúsculas (`MERGED`) como o stub assume. Nada disso foi medido contra a forge."
  - behavior: "O caminho do `glab` inteiro — `glab mr view <n> -F json` e os campos `state`/`web_url`/`merged_at`"
    why: "Escrito por simetria com o `gh`, sem uma única medição. O `glab` não está instalado nesta máquina e nenhum teste o exercita, nem por stub. É a metade menos provada de tudo que a fase entregou, e está dita aqui em vez de coberta por um teste que só confirmaria o que eu mesmo escrevi."
human_verification:
  - test: "Com `git.review_state` em `gh` e o `gh` autenticado, rodar `cairn-review.sh fetch --pr 21 --json` neste repositório e depois `cairn-land.sh report`"
    expected: "O cache ganha `prs.21` com um `state`, e o relatório passa a imprimir `[<state> — cached <idade> ago]` ao lado do número. O `fetched_at` bate com o relógio."
    why_human: "Exige credencial e rede, as duas coisas que esta fase existe para manter fora do caminho padrão. Um teste que fizesse isso destruiria a propriedade que ele estaria verificando."
  - test: "Num repositório com gitflow real (`origin/develop` e `origin/main` divergentes), rodar `cairn-land.sh report --json` e ler `.phases[].branches`"
    expected: "Uma fase mergeada em develop e não em main lê `partial`, com `origin/develop: landed` e `origin/main: unlanded` lado a lado"
    why_human: "A suíte constrói esse caso com `git update-ref`, que escreve exatamente a ref que um fetch escreveria — mas um gitflow de verdade tem release branches, hotfixes e merges de volta, e nenhum fixture reproduz esse tráfego. Este repositório tem uma branch de controle só, então o caso nunca foi visto fora de teste."
overrides_applied: 0
gaps:
  - truth: "Os dois scripts novos não têm wrapper `/cairn:*` nem página em `cairn/docs/commands/`, e a fase 26 tornou essa lista derivada do disco"
    status: partial
    reason: >-
      `cairn-land.py` e `cairn-review.py` entregaram par `.sh` e suíte `.bats`,
      que é a convenção da casa para um script determinístico — mas não ganharam
      wrapper de comando nem página própria. Descoberto ao escrever uma string de
      roteamento para `/cairn:land`, que NÃO EXISTE: um detalhe que aponta para um
      comando que ninguém pode rodar é a mesma classe de mentira que um número
      envelhecido, e a string foi corrigida para nomear o script. Fora do escopo
      de PR-01..PR-04, que não mencionam wrapper nenhum.
      Registrado em `CairnGo-3w9` [P2] com label `phase-30`.
    artifacts:
      - path: "cairn/scripts/cairn-land.py"
        issue: "a evidência de detecção agora roteia para `cairn-land.sh apply`, o comando que existe"
      - path: "cairn/docs/commands.md"
        issue: "a tabela derivada não lista os dois scripts novos, porque eles não são comandos"
    next:
      - "Decidir se `land` e `review` viram verbo de um comando existente (`/cairn:ship`, `/cairn:status`) ou wrapper próprio"
---

# Fase 30: Did it land — Relatório de verificação

**Objetivo da fase:** o board passa a responder "isto entrou?" — se o trabalho de
uma fase ou de uma tarefa já está na branch de controle, e qual PR o levou até lá.

**Verificado:** 2026-08-07, sobre `main` em `1ad90df` (mais a correção do
roteamento pendente de commit)
**Status:** gaps_found
**Re-verificação:** Não — verificação inicial
**Modo:** goal-backward. Os quatro `-SUMMARY.md` foram lidos como afirmação, não
como prova; toda medição abaixo foi refeita contra o código, os testes e o estado
atual do repositório.

---

## O que foi executado nesta sessão

Só os `.bats` tocados, nunca a suíte inteira.

| Lote | Suítes | Testes | Exit |
|---|---|---|---|
| A | `cairn-doctor` (110), `cairn-land` (34), `cairn-review` (11) | 155 | 0 |
| B | `cairn-config`, `cairn-board-invariance`, `cairn-tracker-card`, `cairn-group-model`, `cairn-status`, `cairn-phase-card`, `cairn-grouped-board`, `cairn-corroboration` | 177 | 0 |
| C | `cairn-bookkeep`, `cairn-init`, `cairn-jira`, `cairn-journal`, `cairn-phase-model`, `cairn-reconcile`, `cairn-test`, `hooks` | 203 | 0 |
| D | `cairn-parallel`, `cairn-parallel-autonomous`, `cairn-migrate` | 77 | 0 |

Os lotes C e D são **toda** suíte que cita `cairn-status`, `cairn-config` ou
`cairn-doctor` e que A e B não já cobriam — enumerada por `grep` sobre
`tests/*.bats`, não por memória, porque "acho que nada mais toca nisso" é
exatamente o raciocínio que deixa um consumidor quebrado passar.

**612 executados em 22 suítes, 612 verdes**, contados sobre o log inteiro — não
sobre saída truncada, que é o erro de relato que o canário de contagem do doutor
já pegou uma vez.

**17 quebras foram aplicadas de verdade no fonte**, a suíte rodada, e o fonte
restaurado de cópia (`cp`, nunca `git checkout --`), com `diff` final vazio em
todos os arquivos tocados. Cada uma está registrada no SUMMARY do seu plano com
a asserção exata que derrubou.

Medições ao vivo contra este repositório, todas em leitura: `git rev-list`,
`git symbolic-ref`, `git for-each-ref`, `git show -s`, o relatório do
`cairn-land.sh` e o do `cairn-doctor.sh`.

---

## Critérios de sucesso (vindos do ROADMAP)

### CS1 — O board diz, por fase e por tarefa, se o trabalho entrou, e um teste prova que o caminho padrão não faz rede ✓

`phases[].landed` e `<issue>.landed` estão no `--json` para **toda** linha, com a
mesma forma sempre (`status`, `branches`, `commits`, `reason`, `pr`) — aditivo
para todas, não só para as que têm valor, e é isso que a agregação
`[.phases[] | keys_unsorted] | add | unique` da `cairn-group-model.bats` prova e
uma amostra de uma linha não provaria.

A ancestralidade **não** é uma chamada de `git merge-base --is-ancestor` por par.
É `git rev-list HEAD --not <branch>`, que devolve exatamente o conjunto dos
commits alcançáveis de HEAD que não entraram na branch — mesmo veredito, uma
chamada por branch, e o custo escala com o quanto o checkout está adiantado.
Medido: 530 commits de HEAD, 385 de `origin/main`, complemento de **145**, e o
veredito `unlanded` para a fase 29 concorda com o
`git merge-base --is-ancestor 6545a5c origin/main` falso que o contexto mediu.

A prova de rede reusa as três camadas do 29-05, apontadas para o arquivo novo:

| Camada | O que pega | Controle negativo |
|---|---|---|
| `sitecustomize` que estoura em `socket.connect` | `urllib`/`http.client`/socket cru **dentro** do processo | um `python3 -c` que abre conexão sob o mesmo `PYTHONPATH` e **tem** de falhar |
| `PATH` de allowlist com `curl`, `wget`, `gh` e `glab` armadilhados | ferramenta de rede **fora** do processo, num filho que não herda o patch | um `curl` iniciado como filho sob as duas camadas, que **tem** de aparecer no log enquanto a camada 1 fica calada |
| inventário de AST de todo `subprocess.run` | o sítio novo no dia em que é **escrito** | um fonte sintético com um `gh` dentro, que o mesmo inventário **tem** de recusar |

O tripwire de socket **não basta**, e isso está reproduzido offline dentro da
suíte: sob as duas camadas armadas, um `subprocess.run(["curl", …])` é alcançado,
a camada 1 não levanta nada, e quem o registra é a camada 2. Verificado por
mutação: um `curl` real injetado no `cairn-land.py` deixou vermelhas as camadas 2
e 3 e **verdes os três controles negativos**.

Contagens afirmadas, para que um sítio APAGADO por refactor também seja notado:
`cairn-status.py` = 5 (2 `bd`, 3 `sys.executable`), `cairn-land.py` = 2 (`git` e
`sys.executable`).

### CS2 — A branch de controle é detectada, mostrada, confirmada uma vez e gravada ✓

Padrão do AUTO-02 reusado inteiro: `detect` mostra o que achou com a evidência,
`apply` grava **através do `cairn-config.py`**, que é o dono do
`.cairn/config.json`. `cairn-land.py` nunca abre aquele arquivo.

`git symbolic-ref refs/remotes/origin/HEAD` sai **128** aqui, e isso está
assertado dentro do teste em vez de suposto: a fonte mais óbvia não existe neste
repositório, e o teste que exercita esse degrau da precedência afirma primeiro
que ele **não** dispara aqui.

Gitflow com duas branches ao mesmo tempo é caso testado, com a frase do contexto
virando asserção: `origin/develop: landed` + `origin/main: unlanded`, veredito de
uma palavra `partial`, e uma fase que fez as duas lendo `landed` no **mesmo**
relatório — sem essa segunda metade as três linhas anteriores passariam contra um
relatório que respondesse `partial` para tudo.

**O defeito que este critério pegou e que nenhum plano previu:** `git init` deixa
o checkout numa branch chamada `main` ou `master`, as duas nomes convencionais, e
o detector as tomava. Toda fase de um repositório novo lia `landed` — uma branch
em que você está contém o seu trabalho por construção. A regra virou código,
virou teste nomeado, e a mutação que a remove derruba `.source` de `none` para
`conventional`.

### CS3 — PR não descobrível produz `desconhecido` com o motivo, nunca "sem PR" ✓

O vocabulário tem **duas** palavras, `found` e `unknown`, e a terceira não existe
por desenho: "não há PR" é uma afirmação sobre a forge, e o script só leu um
repositório git.

A #21 é o caso de aceitação, e ele roda contra o **histórico real** com a premissa
assertada dentro do teste (dois pais, nenhum número no assunto nem no corpo) e um
`skip` nomeado se `7fa133c` sumir do checkout. Medido agora: **24 de 24** fases
localizadas respondem `unknown :: no-reference`. Cem por cento. Uma implementação
que dissesse "sem PR" estaria mentindo sobre as 24 com a suíte verde.

O silêncio é distinguido: `no-commits` (nada atribuído) e `no-reference` (há
commits, nenhum nomeia PR) são valores diferentes. E um teste varre a saída humana
inteira proibindo cinco grafias da frase — `no PR`, `no pull request found`,
`sem PR`, `pr none`, `pr: none`. A mutação que imprime `"no PR"` no lugar do
`unknown` derruba exatamente esse teste; a que introduz um terceiro veredito
`none` derruba o teste de fixture **e** o de aceitação contra a #21 real.

### CS4 — Fase completa fora da branch de controle vira achado nomeado do doutor ✓

Checagem **19**, id `phase-landed`. Medido no repositório agora:

```
⚠ phase-landed  9 complete phase(s) have not reached the control branch yet —
                28 complete phase(s) (19 archived), control branch origin/main
                (detected): run /cairn:ship
```

com as nove nomeadas uma a uma (fase, contagem de commits, branch) e mais seis
linhas `unknown ::` para as fases 7 a 12. Antes desta fase, silêncio total.

`warn`, não `fail`, para o ciclo aberto, e o **exit code** é o que prova a
distinção no teste (`[ "$status" -eq 0 ]`). O degrau `fail` existe e sai 7, com
fixture que constrói um milestone arquivado no disco exatamente como o
`/gsd:complete-milestone` o deixa.

**O defeito que este critério pegou:** `roadmap_completed_phases()` lê o ROADMAP
corrente, que lista só o ciclo aberto — nove fases, nenhuma das dezenove
arquivadas. O degrau `fail` seria **inalcançável por construção**, porque as fases
que ele existe para pegar são exatamente as que o arquivamento tirou daquele
arquivo. A mutação que remove a união com as pastas de `.planning/milestones/`
derruba o teste do arquivado — de exit 7 para exit 0.

O doutor **não lê git**: chama o `cairn-land.py` pelo seam `CAIRN_LAND`. Isso está
pinado por um stub que responde um veredito diferente do repositório real e muda o
relatório — o que ele não conseguiria fazer se a resposta fosse re-derivada ali.

O canário de contagem subiu para 20 nos **dois** sítios, na mesma mudança, depois
de ler a nota que registra por que ele existe. A mutação que remove a checagem do
registro é pega por ele: `.checks | length` 20 → 19.

### CS5 — Os sete renders de referência da fase 20 continuam byte a byte idênticos ✓

`tests/cairn-board-invariance.bats` 9/9 e `git diff --quiet HEAD --
tests/fixtures/board-render/` limpo. Nenhuma referência regenerada.

E isso não é afirmado, é **provado**: tornar o sufixo incondicional (devolver um
texto quando `branches` está vazio) derruba `the wide board renders the reference
bytes` com o diff completo das seis linhas que se moveriam. O fixture do board é
um repositório git sem remote e sem commit, então não há branch de controle, não
há sufixo, não há byte — que é o desenho do 29-05 herdado inteiro, não sorte.

---

## Cobertura de requisitos

| Requisito | Plano | Status | Evidência |
|---|---|---|---|
| PR-01 | 30-01 | ✓ SATISFEITO | `cairn-land.py` dono da leitura do git; `landed` por fase e por tarefa no modelo, no `--json` e como sufixo; três camadas de prova de rede com controle negativo cada; 5 mutações |
| PR-02 | 30-02 | ✓ SATISFEITO | vocabulário de duas palavras com motivo nomeado; a #21 real assertada como `unknown`; a frase proibida varrida em cinco grafias; 3 mutações |
| PR-03 | 30-03 | ✓ SATISFEITO | `git.review_state` default `off`, rede isolada em arquivo que o board não alcança, cache sempre carimbado e nunca renderizado sem a idade; 4 mutações |
| PR-04 | 30-04 | ✓ SATISFEITO | checagem 19 com a escada completa, `warn`/`fail`/`ok`/`⊘`/degradação; 9 achados reais neste repositório; 5 mutações, uma delas pega pelo canário |

**4/4 entregues.** Nenhum requisito órfão: os quatro da linha `**Requirements**:`
da fase têm linha aqui e issue bd fechada com razão.

---

## Anti-padrões

| Arquivo | Achado | Severidade | Impacto |
|---|---|---|---|
| `cairn/scripts/cairn-doctor.py:60` | `"Runs first — eighteen checks in total"` com **dezenove** registradas | ⚠️ Aviso | errado desde a fase 24. Quinto precedente medido, neste repositório, de número mantido à mão que envelheceu. Corrigido para vinte, com o episódio escrito ao lado |
| `30-CONTEXT.md` D-02 | "qual PR o levou? … **parcial** offline" | ℹ️ Info | medido: não é parcial neste repositório, é **zero**. 24 de 24 fases respondem `unknown :: no-reference`. A estimativa era otimista, e a consequência (o vocabulário de duas palavras) ficou mais carregada do que o contexto previa |
| `30-CONTEXT.md` "Specific Ideas" | "a fase 29 está completa no disco e `git merge-base --is-ancestor 6545a5c origin/main` devolve falso" | ℹ️ Info | verdade, e incompleta de um jeito que importa: `6545a5c` **não toca** `.planning/phases/29-*/`. Atribuição por diretório sozinha perderia justamente o commit que o contexto nomeia — foi o que forçou a segunda fonte de atribuição |
| `30-CONTEXT.md` D-04 | a precedência de detecção, com três fontes | ℹ️ Info | faltava a quarta regra, e ela é eliminatória: a branch corrente nunca pode ser branch de controle detectada. Sem ela, todo repositório recém-criado lê tudo como `landed` |
| `30-CONTEXT.md` D-06 | "**Exceção que vale `fail`:** fase completa, milestone **arquivado**" | ℹ️ Info | correto, e inalcançável se implementado ao pé da letra: o ROADMAP corrente não lista fase arquivada nenhuma. O universo teve de virar união com o disco |
| `30-CONTEXT.md` D-05 | "estado de revisão vem do `gh`/`glab` **só** com a config ligada" | ℹ️ Info | a config sozinha não bastava: um `gh` escrito no `cairn-land.py` deixaria a camada 3 vermelha, e ela estaria certa. A rede teve de ir para um **arquivo** separado — a restrição virou estrutura em vez de configuração |
| Critério 1 do ROADMAP | "o board diz, por fase e **por tarefa**" | ℹ️ Info | a metade da tarefa é **projeção** da fase, não uma segunda leitura do git. Medido: 41 corpos de commit citam id do bd e todos os amostrados são referência em prosa, não atribuição; e ler o log com corpo custa 476216 bytes contra 80605 |
| `cairn/scripts/cairn-land.py` (escrito por mim) | roteava para `/cairn:land`, que não existe | ⚠️ Aviso | corrigido para nomear o script; a ausência dos dois wrappers virou `CairnGo-3w9` |

Nenhum marcador de dívida (`TBD`/`FIXME`/`XXX`) sem referência formal foi
introduzido.

---

## Resumo das lacunas

**Uma**, e ela não é de nenhum critério desta fase: `cairn-land.py` e
`cairn-review.py` entregaram par `.sh` e suíte `.bats` — a convenção da casa para
um script determinístico — mas não ganharam wrapper `/cairn:*` nem página em
`cairn/docs/commands/`, e a fase 26 tornou essa lista derivada do disco. Foi
descoberta ao escrever uma string de roteamento para um comando inexistente.
Registrada em `CairnGo-3w9` [P2].

Os cinco critérios estão verificados e os quatro requisitos entregues.

O que fica registrado como limite conhecido, não como lacuna: **nenhuma chamada
de rede real foi feita em teste nenhum**, de propósito, porque um teste que a
fizesse destruiria a propriedade que estaria verificando. O `gh` da suíte é um
stub. O que isso deixa sem prova é o formato da resposta real — os cinco campos e
a grafia de `state` — e o caminho do `glab` inteiro, escrito por simetria e sem
uma única medição. Está em `behavior_unverified`, com os dois testes humanos que
o cobrem.
