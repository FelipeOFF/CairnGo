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

**v1.4 Honest State shipped 2026-08-01 como cairn 1.5.0.** Dezenove fases fechadas
e arquivadas. O estado de uma fase deixou de ser palpite tirado de quatro nomes de
arquivo: quatro fontes declaram sua alegação, a discordância é nomeada em vez de
resolvida em silêncio, e quando elas discordam a investigação **propõe** — ela não
tem ferramenta de escrita nenhuma, por construção. Fases independentes rodam de
verdade ao mesmo tempo, uma worktree cada, e a reconciliação relata inclusive a
edição convergente, que o git junta sem avisar.

O ciclo virou o número do plugin de 1.4.2 para **1.5.0**, desamarrando dois eixos
que vinham se imitando: o nome do ciclo de planejamento e a versão publicada.

Dívida assumida e registrada no arquivo do milestone: `req-issue` passa no vazio
(`CairnGo-ca3`, P1), o `orphans` do doctor nunca zera (`CairnGo-xhy`), e nenhum
teste prova dois agentes rodando ao mesmo tempo — o proxy está rotulado como
proxy.

<details>
<summary>Estado anterior (até v1.3)</summary>

**v1.3 shipped 2026-07-28; plugin na 1.4.2.** Doze fases fechadas e arquivadas. O benchmark rodou de verdade (`matrix-20260727.jsonl`, charts commitados) e a conclusão publicada é que nenhum arm é mensuravelmente mais barato — inclusive o cairn. O v1.2 descobriu que a fusão GSD↔beads nunca tinha rodado para ninguém: a linhagem antiga não tem capability, `gsd_run` não estava no PATH e um `|| echo "skipped"` convertia toda falha em sucesso. Três releases (1.4.0→1.4.2) atacaram a mesma causa: um sinal verde que não provava o que afirmava.

</details>

## Current Milestone: v1.5 Legible State

**Goal:** onde você está dentro do estado que já prova o que afirma. O board sabe
listar e não sabe situar — com muitas tarefas vira coluna plana, `READY` significa
três coisas ao mesmo tempo, o título é cortado em 28 caracteres, e fora do TTY ele
degrada para o formato de máquina sem ninguém pedir. E o doctor dá 16 ok e 0 falhas
sobre um roadmap vazio, porque três checagens passam por não ter o que checar.

**Nove fases (20-28), 24 requisitos.** Só duas arestas de dependência no ciclo
inteiro: a corrente do board (20→21→22) e a tendência que precisa do estado
não-aplicável (23→27). As outras cinco são independentes — é o primeiro roadmap do
projeto com paralelismo real disponível, e a fase 18 do ciclo anterior é quem o
executa.

A ordem numérica põe no fim o que pode ser cortado inteiro: a 26 (wrappers) é a
maior em volume e não é pré-requisito de nada, e a 28 (journal durável) é a única
cujo escopo a própria pesquisa pode redefinir.

## Próximo Milestone: v1.6 — o bd vira dono do estado

Decidido pelo Felipe em 2026-08-06. Detalhamento e medições em `CairnGo-dhl`.

**A divisão.** O GSD fica com o que ele faz bem, que é o workflow: discuss, plan,
execute, verify, e os agentes deles. O bd fica com o estado: construção de tarefa,
PRDs, `STATE`, `ROADMAP`, `REQUIREMENTS`.

A divisão sai de medição, não de preferência. As duas corrupções que o v1.5
encontrou vieram da **escrita** do gsd-tools, nenhuma do workflow:
`state.record-metric` gravou `current_phase: 18`, fase de milestone arquivado, duas
vezes, lendo prosa obsoleta; e o `_normalizeMd` produziu `+43/−7` no ROADMAP para
virar cinco checkboxes.

**O `.planning/` deixa de ser fonte e vira saída gerada.** Medido: **53 dos 91**
workflows do gsd-core leem `ROADMAP.md`, `REQUIREMENTS.md` ou `STATE.md`. O dado não
pode simplesmente sair de lá. Então o bd passa a ser a fonte, o cairn renderiza os
`.md` logo antes de invocar o GSD, e os arquivos entram no `.gitignore`. O GSD não
percebe diferença e ninguém precisa forká-lo.

Isso resolve a migração melhor do que ignorar o diretório: usuário novo recebe do
`init` a informação de que a fonte é o bd; usuário antigo tem o `.planning` existente
importado **uma** vez pelo `doctor`, e dali em diante regenerado.

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
