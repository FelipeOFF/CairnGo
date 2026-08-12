# Phase 29: Nothing mechanical stays manual - Context

**Gathered:** 2026-08-03
**Status:** Ready for planning

<domain>
## Phase Boundary

O que é mecânica pura e não tem regra de negócio dentro para de ser feito à mão.

Requisitos: AUTO-01 … AUTO-06. Issues bd: ver `29-BEADS-MAP.md`.

A linha que separa o que se automatiza do que se pergunta é a do `/groom-me`:
**mudança de regra de negócio se conversa antes; mecânica se automatiza e pronto.**
Onde uma decisão desta fase cruza essa linha, ela está marcada abaixo como
pendente de grooming, e o plano **não** a resolve sozinho.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo. As decisões abaixo são Claude's Discretion, mas
nenhuma é palpite: todas saem de um workflow de pesquisa com quatro sondas
independentes (5 agentes, 758k tokens) mais medições que eu refiz à mão. Onde algo
não foi medido, está escrito que não foi.

### O bookkeeping não pode passar pelo gsd-tools

- **D-01: `cairn-bookkeep.py` stdlib, cirurgia por linha, nunca re-serialização.**

  **Quatro medições independentes decidem isso, e nenhuma é sobre preferência:**

  1. `roadmap update-plan-progress 20` produz **+31/−4** — 35 linhas de diff para
     virar 3 checkboxes. A causa não está na verb: está em `_normalizeMd`, aplicado
     por `platformWriteSync` a **todo** `.md` que o gsd-tools escreve
     (`shell-command-projection.cjs:631`). O risco é de qualquer verb, não de uma.
  2. `phase complete 20` — a operação que a mão de fato faz — **se recusa a rodar**:
     `roadmap.cjs:469` exige `summaryCount >= planCount && verificationPassed`, e a
     verificação da fase 20 saiu `human_needed`. Escreveu zero bytes.
  3. `requirements mark-complete BOARD-01` vira o checkbox, **não** toca a tabela de
     Cobertura, e reporta `"write_set_complete": true`. Verde falso dentro da
     ferramenta que se cogitava adotar.
  4. `state record-session` reescreve `current_phase: 29 → 18`, lendo o 18 da prosa
     obsoleta do corpo do STATE.md. E `state complete-phase` vai além: marca
     completa a **fase 18, de um milestone arquivado**, e reordena o frontmatter.
     Corrupção reproduzível.

  Do GSD aproveita-se só a **aritmética** — medido: os contadores que a SDK escreveu
  batem byte a byte com os que a mão digitou depois.

  O reflow **é** idempotente (segunda passada byte-idêntica), então o dano é de
  primeira passada e não acumulativo. Isso não salva a decisão: os sete fixtures de
  render da fase 20 dependem do formato atual do ROADMAP.

### A discordância de hoje é o fixture, não algo a limpar antes

- **D-02: congelar o estado atual dos três arquivos como entrada de teste, antes de
  qualquer conserto manual.**

  Medido agora: **34 requisitos** em `REQUIREMENTS.md`, **31 linhas** na tabela de
  Cobertura, e o rodapé do ROADMAP afirmando **"29 requisitos, 29 mapeados"** — um
  número que eu escrevi e nunca atualizei ao acrescentar FIX-04, FIX-05, BOARD-06,
  AUTO-05 e AUTO-06. `BOARD-01` é `- [ ]` no REQUIREMENTS e `Complete` no ROADMAP.

  **Dois dos seis requisitos desta fase já são vítimas do defeito que ela existe
  para consertar.** Consertar isso à mão antes de escrever o comando joga fora a
  única entrada realista que existe: o comando tem que **resolver** discordância,
  não pressupor consistência.

### O Jira é detectado, confirmado, e então configurado pelo cairn

- **D-03: híbrido, e a detecção nunca decide sozinha.** Três sinais, com pesos
  medidos e muito diferentes:

  | sinal | medição |
  |---|---|
  | MCP do Atlassian em arquivo | **falso negativo aqui** — predicado sobre `mcpServers` devolve `[]` com o conector Rovo ativo |
  | chave em nome de branch | limpo — **0 matches em 25 branches** neste repo |
  | chave em mensagem de commit | **inútil sozinho — 21/21 falsos positivos, 100%** |

  O único rastro em arquivo do conector ativo é `~/.claude.json` →
  `.claudeAiMcpEverConnected`, uma lista de strings de exibição. **Não foi medido**
  se ela significa "conectado agora" ou "já conectou alguma vez"; se for histórico,
  dá falso positivo silencioso. Fica como ASSUMIDO e o plano não pode tratá-la como
  estado.

  **O detector já existe e já está errado.** `cairn-migrate.py detect --json`
  reporta hoje:

  ```json
  "jira": {"detected": true,
           "prefixes": ["JOUR","ESC","PAR","CARD","GSD","FAIR","REL","HARN","LEASE"],
           "signals": ["git-log"]}
  ```

  Nove prefixos, todos de requisito do cairn/GSD, zero Jira. Ele pré-preencheria
  `project_key="JOUR"` no `/cairn:sync-config`. Causa medida:
  `cairn-migrate.py:497` só exclui prefixos de `REQUIREMENTS.md` **ativo**, e os
  milestones arquivados em `.planning/milestones/*-REQUIREMENTS.md` cobrem 13 dos 21
  prefixos do histórico.

  Conserto **verificado** pela sonda: denylist com
  `glob(".planning/milestones/*REQUIREMENTS.md")` **mais** prefixos construídos com
  `JIRA_KEY.finditer` cru → `detected: false`, que é a resposta certa para este
  repo. Armadilha medida: usando `parse_requirements_md` em vez de regex crua, `GSD`
  sobrevive, porque `REQ_ITEM` só casa `- **ID**: título` e os arquivos v1.2/v1.3
  usam `### GSD-01:`.

### A config espelha o `/gsd:config`, e tem duas portas

- **D-04: um lote de perguntas com o valor atual pré-selecionado, e o `.json`
  editável à mão continua sendo a mesma fonte.**

  Medido: o `/gsd:config` **não** é um wizard pergunta-a-pergunta — é **um** lote de
  `AskUserQuestion` agrupado em seis seções nomeadas, com o valor corrente
  pré-selecionado (`gsd-core/workflows/settings.md:90`). É o padrão a espelhar, e
  espelhá-lo é mais barato que inventar.

### Claude's Discretion

- Nome do script e a forma dos seus subcomandos.
- Onde as chaves do cairn moram: `cairn.*` dentro de `.planning/config.json` versus
  arquivo próprio. **Medido:** `query config-set cairn.enabled` sai 1, então o
  caminho pelo gsd-tools não está provado.
- Se o conserto do `detect_jira` entra nesta fase ou vira issue própria (é
  pré-requisito se o AUTO-02 chamar `detect --json` para pré-preencher).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O brief da pesquisa
- A saída completa do workflow `phase-29-research` (run `wf_85f02d68-fb5`), com as
  onze perguntas abertas que ele deixou numeradas — várias são de grooming, não de
  planejamento

### Código
- `cairn/scripts/cairn-migrate.py` — `detect_jira()` (~486-499), o detector quebrado
- `cairn/scripts/cairn-status.py` — lê o ROADMAP cujo formato o bookkeeping edita
- `cairn/hooks/post-bd-write.sh:126-152` — decide push só pela existência de
  `.cairn/sync.json`; `cairn.sync_push` é declarada e **lida por nada**
- `~/.claude/gsd-core/bin/lib/shell-command-projection.cjs:631` — o `_normalizeMd`
- `~/.claude/gsd-core/workflows/settings.md:90` — o padrão de perguntas a espelhar
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cairn-migrate.py` já tem o idioma de journal resumível e de dry-run/apply.
- O `--apply-reconciliation` do doctor é o padrão da casa para escrita atrás de flag
  nomeada com enumeração antes.
- A aritmética dos contadores do STATE já está resolvida no gsd-tools e confere.

### Established Patterns
- Escrita atrás de flag nomeada, leitura por default.
- Um teste que passaria com a feature removida não é prova.
- `EXIT_*` nomeados; `0` ok · `2` uso · `5` bd ausente · `6` achado · `7` doctor.

### Integration Points
- Script novo + par `.sh` + bats próprio.
- `cairn-migrate.py` — o conserto do `detect_jira`.
- Possivelmente `cairn-doctor.py` — se a config ganhar checagem.

</code_context>

<specifics>
## Specific Ideas

- **A fase é sobre um defeito que o próprio autor cometeu enquanto a escrevia.** O
  rodapé "29 requisitos, 29 mapeados" ficou errado por cinco entre o momento em que
  a fase foi criada e o momento em que este contexto foi escrito, no mesmo dia, pela
  mesma mão. Não é anedota: é a medição que justifica a fase e é o fixture do teste.

- **`cairn.sync_push` é declarada, documentada, testada e lida por nada.** Zero
  matches em código executável; a declaração vive em `capability.json:43`, em três
  fragmentos de prompt e em `tests/capability.bats:97`. Um wizard que ofereça esse
  botão grava valor que o hook ignora. **Implementar a leitura é mudança de
  comportamento para quem já tem `sync.json` — isso é grooming, não mecânica**, e o
  plano deve tratá-la como pendente de decisão, não decidi-la.

</specifics>

<deferred>
## Deferred Ideas

- Buscar título e status do card no Jira ao vivo — o AUTO-03 exige que o caminho
  default não faça rede; a busca fica atrás de flag, noutra fase.
- Resolver o caminho de config sob workstream (`.planning/active-workstream`) — se
  não couber, o plano declara fora de escopo **por escrito**, nunca por omissão.
- Concorrência de escrita no `config.json`: o `config-loader.cjs:609` reescreve o
  arquivo durante a leitura, fora do lock. Ou o cairn adota lock próprio, ou aceita
  a janela e documenta.

</deferred>

---

*Phase: 29-Nothing mechanical stays manual*
*Context gathered: 2026-08-03*
