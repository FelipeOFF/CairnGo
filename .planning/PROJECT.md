# CairnGo

## What This Is

CairnGo ("cairn") é um plugin de Claude Code que funde GSD (planejamento por fases) com beads/bd (issue tracker git-nativo) num lifecycle único: comandos `/gsd:*` criam, claimam e fecham issues bd automaticamente, com ship gate por hook de git. Público em `FelipeOFF/CairnGo`, plugin na 1.5.0. O benchmark foi coletado e publicado: nenhum arm é mensuravelmente mais barato que outro nesse corpus, cairn incluído — e isso está escrito no BENCHMARKS.md. O v1.4 atacou o que sobrou: **o estado do projeto tem que provar o que afirma** — e entregou.

## Core Value

Workflow unificado plan→work→ship cujo estado é verificável — nenhuma superfície afirma que uma fase está pronta sem ter com o que corroborar.

## Requirements

### Validated

- ✓ Benchmark harness completo e reproduzível (bench-run/matrix/aggregate/chart/publish/all, 199 testes bats a $0 de API) — v1.1
- ✓ Isolamento mecânico de ambiente (HOME fresco, env replace, manifests pinados 4 arms incl. concorrente ralph-specum) — v1.1
- ✓ Métricas honestas: success-gating belt-and-braces, decomposição 4-way modelUsage-preferred, N=5 interleaved — v1.1
- ✓ Corpus pré-declarado de 6 tasks incl. honest-non-win + cost model ~$40 CI-enforced — v1.1
- ✓ Publicação methodology-first (BENCHMARKS.md, charts determinísticos, embed por markers, reprodução 1 comando) — v1.1
- ✓ Unificação GSD↔beads (issues por requirement, label pair `m-<milestone>`+`phase-<N>`, stamp `metadata.gsd`) — v1.0
- ✓ Scripts determinísticos: cairn-map, cairn-relabel, cairn-gate, cairn-doctor, cairn-migrate (detect/plan/apply com journal) — v1.0
- ✓ Migração de repos existentes (modos A/B/C/W/D) — v1.0
- ✓ Sync adapters (jira, github, gitlab, azure-boards, asana) via gbsync — v1.0
- ✓ Integração context-mode (memória intent-aware escopada por issue+fase) — v1.0
- ✓ Suite bats (92+ testes) + CI — v1.0
- ✓ Coleta live da matriz e publicação dos números reais (charts commitados, Results preenchido, conclusão honesta de não-diferença) — v1.1
- ✓ Dependência no `open-gsd/gsd-core` oficial, pinada por tag; capability que **verifica** que registrou; doctor reporta linhagem — v1.2
- ✓ Um modelo de fase único por trás do board, do `--json` e do HTML; próximo comando computado por fase; paralelismo declarado — v1.3

### Active

- [ ] Estado de fase corroborado entre artefatos, bd, git e árvore — discordância vira `conflict`, nunca escolha silenciosa
- [ ] Lease de fase: outro agente dentro da mesma fase é fato visível, não surpresa
- [ ] Escalada semântica que propõe reconciliação e nunca grava estado sozinha
- [ ] Card de fase que diz para que a fase serve — mesma leitura no terminal e no HTML
- [ ] Journal append-only de transições: estado lido, não reconstruído

### Out of Scope

- Dashboard/página web de resultados — futuro; gráficos commitados primeiro (decisão do Felipe, 2026-07-25)
- Telemetria contínua de sessões reais — não escolhida; reproduzibilidade e credibilidade vêm da suite fixa
- GIF/asciinema como demonstração principal — Felipe escolheu gráficos de benchmark como o visual

## Current State

**v1.6 O transplante shipped 2026-08-12 como cairn 1.7.0.** Trinta e oito fases
fechadas e arquivadas. O GSD não é mais uma dependência: o runtime mora aqui, na
tag pinada v1.10.0, e a camada prompt deixou de ler markdown para saber onde o
projeto está — ela pergunta ao binário e lê o exit code.

O que a medição fecha o ciclo dizendo: quatro famílias de sítio de estado em
**zero** nos 66 arquivos do escopo, chamadas a `node` na infraestrutura de 14
para **7**, e o plugin fora das `dependencies` do `gsd-core`. O doctor ganhou
duas checagens, cada uma nascida de defeito medido nesta árvore: um clone limpo
não recuperava nenhuma das 176 issues, e o export rastreado publicava hostname e
caminho de home num repositório público.

O fio do ciclo, e o que ele deixa como método: quase toda vez que algo disse
"verde", a medição mostrou que ele não tinha olhado. Um `<verify>` que passaria
com sete sítios de estado de pé. Um fixture que mascarava a prova da inversão do
doctor. Um `§5b` que dizia 12 e listava 11. Duas rotas que morriam com exit 2
dentro de um `|| true`. O que a v1.6 entregou não foi só o transplante — foi a
régua que mede se ele aconteceu.

<details>
<summary>Estado anterior (v1.5 Legible State)</summary>

**v1.5 Legible State shipped 2026-08-07 como cairn 1.6.0.** Trinta fases fechadas
e arquivadas. O estado deixou de só provar o que afirma e passou a dizer **onde
você está dentro dele**: o board agrupa milestone → fase → tarefa e não trunca
mais título nenhum, o `--plain` voltou a ser só contrato de máquina, e o board
responde se o trabalho de uma fase entrou na branch de controle — do git local,
sem rede.

E toda superfície parou de responder sobre o que não checou. A prova aconteceu no
próprio fechamento deste ciclo: com o `.planning/phases/` esvaziado pelo
arquivamento e o `REQUIREMENTS.md` removido, o doctor responde **16 ok, 5
not-applicable, 1 warning, 0 falhas**, e cada `not-applicable` nomeia o que falta.
Antes da fase 23, esta mesma situação dava 16 ok e 0 falhas — cinco checagens
reportando sucesso por não ter o que checar. Era o defeito que o ciclo anterior
existiu para eliminar, vivendo dentro da ferramenta que o eliminou.

O journal atravessa máquinas, uma partição por checkout, sem que nada precise ser
mesclado. Fechar uma fase virou um comando. E 37 premissas escritas nos próprios
contextos e issues foram derrubadas pela medição durante a execução.

Dívida assumida: três verbos novos sem página-contrato, o executor ainda não chama
a porta cirúrgica por plano, e `machine` grava o hostname em claro — o que num
repositório público publica o nome da máquina de quem contribui.

<details>
<summary>Estado anterior (até v1.4)</summary>

**v1.4 Honest State shipped 2026-08-01 como cairn 1.5.0.** Dezenove fases fechadas
e arquivadas. O estado de uma fase deixou de ser palpite tirado de quatro nomes de
arquivo: quatro fontes declaram sua alegação, a discordância é nomeada em vez de
resolvida em silêncio, e quando elas discordam a investigação **propõe** — ela não
tem ferramenta de escrita nenhuma, por construção. O ciclo virou o número do plugin
de 1.4.2 para 1.5.0, desamarrando o nome do ciclo de planejamento da versão
publicada.

**v1.3 shipped 2026-07-28; plugin na 1.4.2.** Doze fases fechadas e arquivadas. O benchmark rodou de verdade (`matrix-20260727.jsonl`, charts commitados) e a conclusão publicada é que nenhum arm é mensuravelmente mais barato — inclusive o cairn. O v1.2 descobriu que a fusão GSD↔beads nunca tinha rodado para ninguém: a linhagem antiga não tem capability, `gsd_run` não estava no PATH e um `|| echo "skipped"` convertia toda falha em sucesso. Três releases (1.4.0→1.4.2) atacaram a mesma causa: um sinal verde que não provava o que afirmava.

</details>

</details>

## Próximo Milestone

Não definido. Abrir com `/cairn:milestone new`, que cria o ROADMAP e as issues
stamped do ciclo seguinte.

Ficou registrado como dívida medida, em `deferred-items.md` das fases 37 e 38:
os oito verbos que este plugin **não** vendoriza (`new`, `milestone`, `ship`,
`migrate`, `progress`, `status`, `config`, `sync-config`, `help`), com o custo
de vendorizá-los medido — dobraria a árvore vendorizada, e cada arquivo novo é
deriva contra o pin. A remoção física de `cairn/capability/` e a profundidade
dos 12 contratos inline também esperam decisão.

<details>
<summary>Planejamento do milestone que acabou de fechar (v1.6)</summary>

Decidido pelo Felipe em 2026-08-06. Detalhamento e medições em `CairnGo-dhl`.

**A divisão.** O GSD fica com o que ele faz bem: a **execução**, e principalmente os
**agentes**. O bd fica com o estado: construção de tarefa, PRDs, `STATE`, `ROADMAP`,
`REQUIREMENTS`.

O que fica com o GSD, explicitamente:

| workflow | o que ele traz |
|---|---|
| `discuss` | levantamento de decisão antes de planejar |
| `plan` | `gsd-planner` mais o laço de verificação do `gsd-plan-checker` |
| `execute` | `gsd-executor`, com commit atômico, desvio e checkpoint |
| `verify` | `gsd-verifier`, análise goal-backward |
| `quick` | trabalho lateral rastreado, sem cerimônia de fase |
| `fast` | tarefa trivial inline, sem subagente |
| `autonomous` | o laço fase a fase, **dirigido pelo bd** e não pelo roadmap em markdown |
| `debug` | `gsd-debugger` e o `gsd-debug-session-manager` |

São **33 agentes** no plugin, e o argumento para mantê-los não é teórico. Tudo o que
mais valeu no v1.5 saiu deles: o `gsd-planner` achou quatro premissas erradas no
contexto da fase 23 antes de escrever um plano; o `gsd-phase-researcher` rodou 17
experimentos no portão `DJOUR-01` e **derrubou o requisito que o encomendou**; e o
`gsd-verifier` encontrou, em seis verificações, a fixture cega ao defeito por
construção, o contador que passa do próprio total e o mapa do help derivado pela
metade. Nenhum executor tinha visto nenhum dos três.

O que sai são os workflows de **autoria de estado**, não os de execução.

A divisão sai de medição, não de preferência. As duas corrupções que o v1.5
encontrou vieram da **escrita** do gsd-tools, nenhuma do workflow:
`state.record-metric` gravou `current_phase: 18`, fase de milestone arquivado, duas
vezes, lendo prosa obsoleta; e o `_normalizeMd` produziu `+43/−7` no ROADMAP para
virar cinco checkboxes.

**O `.planning/` não é gerado: ele deixa de ser lido.** A primeira proposta era
renderizar os `.md` antes de invocar o GSD. Felipe apontou o furo e ele é fatal:
gerar não economiza token nenhum, porque o GSD lê o arquivo do mesmo jeito. O ganho
seria fonte única, não custo.

A saída está em **como** os workflows leem, e a medição é favorável. Dos 91 workflows
do gsd-core, **77 leem por camada de consulta** (`gsd_run query ...`) e só 21 leem
arquivo direto. Os verbos são contáveis: `init.phase-op` (21 usos),
`roadmap.get-phase` (15), `roadmap.analyze` (9), `verification.status` (8),
`state.record-session` (6). É **uma costura**, não 53 patches.

E o ponto de interceptação já existe, já prefere o local, e a cadeia de fallback foi
escrita para ser sobrescrita:

```
_GSD_RUNTIME_ROOT = git rev-parse --show-toplevel
  1. ${ROOT}/gsd-core/bin/gsd-tools.cjs          <- projeto vence
  2. ${ROOT}/.claude/gsd-core/bin/gsd-tools.cjs
  3. ${ROOT}/.codex/gsd-core/bin/...
  4. command -v gsd-tools
  5. $HOME/.claude/gsd-core/bin/...              <- global, último
```

O cairn põe um shim no caminho local, responde os verbos de **estado** a partir do
bd, e delega o resto ao gsd-tools real. E aqui aparece o ganho de token que a geração
não dava: o shim devolve **a fatia**, não o arquivo. `roadmap.get-phase 21` devolve um
objeto de fase, não 10.572 tokens de ROADMAP.

**O split é limpo, e não por acaso.** Dos oito workflows que ficam com o GSD, o total
de leituras diretas residuais é **três**: duas em `discuss-phase`, uma em
`plan-phase`. `execute-phase`, `verify-work`, `quick`, `autonomous` e `debug` leem
zero arquivos e tudo por consulta; `fast` é standalone. Já os 21 que leem arquivo
direto são quase todos os que saem: `new-project`, `new-milestone`, `edit-phase`,
`add-backlog`, `progress`, `ship`, `import`, `cleanup`, `session-report`, `undo`.

Isso reflete uma fronteira de desenho real dentro do GSD: execução lê estado por
ferramenta, autoria escreve estado direto. A divisão proposta cai em cima dela.

Migração: usuário novo recebe do `init` a informação de que a fonte é o bd; usuário
antigo tem o `.planning` existente importado **uma** vez pelo `doctor`.

**O que motivou, em tokens medidos:** `.planning/` na raiz custa 21.725 tokens em
todo contexto de agente. O `STATE.md` sozinho custa 3.490, dos quais 2.513 são o
bloco `Accumulated Context` com decisões das fases 1 a 6 do v1.1, milestone publicado
em 27 de julho. As ferramentas leem 126 tokens de frontmatter.

**O que não migra.** Fato migra: fase completa, requisito mapeado, plano executado,
veredito de verificação. É pequeno, estruturado, consultável, e é o que deriva.
Argumento fica em markdown: por que `◑` foi descartado, por que hash-chain perde duas
vezes, o que foi recusado e por quê. Prosa em coluna de banco continua prosa e perde
`git diff`, grep e review de PR.

**O ganho não é mágico, é de custo.** Com fato em banco, "fase fechada sem evento de
verificação" é uma consulta. Em markdown foi a fase 29 inteira, sete planos, para
validar uma cadeia que em consulta é um join. E foi exatamente esse o defeito que
passou: sete fases fechadas sem verificação, descoberto só quando a fase 27 foi ler a
série.

</details>

## Context

- Brownfield: mapa da codebase em `.planning/codebase/` (7 docs, 2026-07-25).
- A causa-raiz deste milestone é uma função só: `phase_disk_state()` em `cairn-status.py` decide entre quatro estados por existência de quatro nomes de arquivo. Nunca abre o arquivo, nunca lê o código, o git ou o bd. Todo trabalho que acontece sem esses arquivos aparecerem é invisível.
- O GSD precisa de `/gsd:audit-milestone` porque o estado dele é inferido de efeito colateral. O cairn tem uma vantagem estrutural que o GSD não tem: o bd é um banco com timestamp, autor e motivo de fechamento.
- Backlog fora deste milestone: `CairnGo-9xy` (13 wrappers `/cairn:*`), `CairnGo-c8v` (remover o reparo de manifesto quando o upstream resolver #2077).
- Concerns conhecidos do mapa: race no gbsync id-map, parsing regex leniente de ROADMAP/STATE, adapters sem cobertura funcional. Não são deste milestone, ficam registrados.

## Constraints

- **House style**: python3 zero-dependências + wrappers bash + testes bats — benchmark harness segue o molde de `cairn/scripts/`.
- **Custo**: benchmarks executam Claude Code real (custo de API por rodada) — a suite precisa ser rodável por terceiros com custo previsível e documentado.
- **Honestidade metodológica**: comparação só é diferencial se a metodologia aguentar escrutínio público (tarefas idênticas, mesmas condições, variância reportada).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Visual = gráficos de benchmark commitados (não GIF, não web) | Embed direto no README, gerável por script, zero infra | ✓ Good (maquinaria pronta; SVGs entram com dados reais) |
| 3 baselines: vanilla, GSD puro, plugin concorrente | Vanilla = leitura universal; GSD puro = isola ganho do cairn; concorrente = diferencial competitivo | ✓ Good (4 arms shipped; concorrente = ralph-specum v4.0.0) |
| Coleta via suite reproduzível (não telemetria) | Credibilidade: qualquer um reproduz; telemetria não é comparável | ✓ Good (bench-all.sh 1 comando) |
| --bare exige ANTHROPIC_API_KEY (OAuth não funciona headless isolado) | Verificado ao vivo na fase 1 | ✓ Good |
| Decomposição prefere modelUsage sobre usage | usage under-reporta cache_creation ~30% (verificado por aritmética vs pricing) | ✓ Good |
| Zero número sintético publicado; SVGs só com dados reais | Credibilidade methodology-first (inverso do anti-padrão claim-sem-dado) | ✓ Good |
| Core Value reescrito: de "custa menos tokens" para "estado verificável" | O próprio benchmark do projeto refutou a alegação de custo; manter a antiga seria o exato anti-padrão que o v1.1 existiu para combater | — Pending |
| Corroboração determinística antes de escalada semântica | LLM lendo codebase é caro e não-reproduzível; tripwire barato dispara, investigação profunda só no conflito | — Pending |
| A escalada nunca grava estado — só propõe | Um agente que corrige o próprio registro de estado destrói a evidência do erro | — Pending |
| Journal (C) não substitui corroboração (A) | O journal só vê o que o cairn faz; humano ou outra ferramenta editando código continua invisível | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-29 ao abrir o milestone v1.4 (Honest State)*
