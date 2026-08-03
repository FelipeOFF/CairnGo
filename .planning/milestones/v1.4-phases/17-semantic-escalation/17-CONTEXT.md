# Phase 17: Semantic escalation - Context

**Gathered:** 2026-07-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Quando as fontes discordam, uma investigação lê código, história e memória e
**propõe** uma reconciliação. Aplicar é ato humano, e a incapacidade de gravar é
por construção, não por instrução.

Requisitos: ESC-01 … ESC-04. Issues bd: ver `17-BEADS-MAP.md`.

Herdado e **não reaberto**: o cairn nunca grava estado sozinho e nunca para o
fluxo (D-01 da fase 13); o script reporta e a prosa pergunta (D-02 da fase 13);
`.cairn/conflicts.json` está gitignored e **reservado sem uso desde o v1.0** —
o slot existe esperando exatamente isto.

</domain>

<decisions>
## Implementation Decisions

### A arquitetura, em camadas

- **D-01: coletor em código, intérprete em agente, aplicador humano.**

  ```
  cairn-reconcile.py collect <fase>   → pacote de evidência + hash
     │  sem verbo de escrita, provado por grep e por bats
     ▼
  subagente restrito                  → lê o pacote, escreve a proposta
     │  sem ferramenta de escrita, garantia do harness
     ▼
  .cairn/conflicts.json               → proposta + citações + hash
     │
     ▼
  cairn-doctor --apply-reconciliation → humano, enumera antes de mudar
  ```

  **Isto resolve um conflito real entre a primeira resposta e o critério de
  sucesso 1 do próprio roadmap**, e o registro importa porque a tensão volta se
  alguém simplificar. A resposta inicial foi "subagente com toolset restrito", e
  ela é uma garantia forte — mas mora no harness, não em arquivo nenhum, e o
  critério exige literalmente *"um `grep` sobre o caminho de análise não encontra
  nenhum verbo de escrita do bd, e um teste roda esse caminho contra um fixture e
  afirma que nada mutou"*. Um subagente não tem caminho para grepar.

  A camada de coleta resolve as duas metades: ela é código, então é grepável e
  testável; e é ela que produz a lista do que foi lido, que a D-04 precisa e que
  um agente lendo livremente não produziria de forma confiável — produziria uma
  narrativa do que acha que leu.

  Rejeitado só-script: perde a leitura semântica, que é literalmente o que o
  ESC-01 pede ao dizer "lê código, história e memória". Rejeitado só-subagente com
  reescrita do critério: troca uma garantia verificável por uma que depende do
  harness cooperar.

### Onde a proposta vive

- **D-02: `.cairn/conflicts.json`**, o slot gitignored e reservado desde o v1.0
  ao lado de `id-map.json`, `state.json` e `hook.log`. Local e descartável, como
  convém a algo transitório; o comando de aplicar lê dali.

  Rejeitado artefato versionado na pasta da fase: uma proposta é transitória por
  natureza e não merece entrar no histórico do repositório.

### Verificação de citação

- **D-03: arquivo + linha + o texto literal, relido e comparado.** Cada alegação
  cita caminho, número de linha e o trecho exato; um checador reabre o arquivo e
  compara. **Uma citação que não bate invalida a proposta inteira**, não apenas
  aquela alegação — uma proposta com uma citação falsa não é uma proposta com um
  erro, é uma proposta em que não se pode confiar.

  Isto **fecha o item de research** que o roadmap tinha marcado para esta fase
  ("o esquema de verificação de citação não tem precedente neste código"): o
  esquema está decidido aqui, e o plano não precisa pesquisá-lo.

  Rejeitado hash do trecho: imune a espaço em branco, e ilegível para quem lê a
  proposta — e a proposta é lida por humano. Rejeitado só arquivo e linha: não
  prova nada, porque a linha existe sempre, diga ela o que disser.

### Cache do veredito

- **D-04: hash só das fontes que aquele conflito cita** — os arquivos da fase, as
  issues do bd envolvidas, o trecho do roadmap. Edição em outro canto do
  repositório não invalida um veredito ainda válido.

  A lista vem do **coletor**, não da narrativa do agente. É a razão de D-01 ter
  uma camada de código: sem ela, "o que a investigação leu" seria autodeclarado.

  Rejeitado tree hash do repositório inteiro: qualquer commit invalidaria todo
  veredito e o cache nunca acertaria — numa sessão como esta, nem uma vez.

### Claude's Discretion

- Forma exata do pacote de evidência que o coletor emite.
- Schema do `conflicts.json`, desde que carregue as citações e o hash.
- Como o subagente restrito é declarado e onde a restrição é documentada.
- Texto do enumerado que o `--apply-reconciliation` mostra antes de mudar.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O que as fases anteriores travaram e esta consome
- `.planning/phases/13-state-corroboration/13-CONTEXT.md` — D-01 e D-02; e o
  `conflicts` por fase que esta fase investiga
- `.planning/phases/16-transition-journal/16-CONTEXT.md` — D-04: o histórico
  aparece no relatório de conflito e no comando de leitura, e esta fase é o
  terceiro consumidor legítimo dele

### Pesquisa
- `.planning/research/ARCHITECTURE.md` §5 — a separação analisar/aplicar como
  divisão de capacidade, não como instrução
- `.planning/research/PITFALLS.md` — Pitfall 12 (o agente que grava o que devia
  só propor) e 13 (custo e não-reprodutibilidade de um veredito semântico)
- `.planning/research/FEATURES.md` — a convergência de Terraform, Ansible e
  Pulumi em reportar-e-exigir-confirmação, nunca reconciliar sozinho

### Código
- `cairn/scripts/cairn-doctor.py` — `check_phase_corroboration()` produz o
  conflito que dispara isto; `--close-completed` e `--link-refs` são o padrão de
  leitura-por-default/escrita-atrás-de-flag que o `--apply-reconciliation` segue
- `cairn/scripts/cairn-journal.py` — `last-moved` e `history` alimentam a
  investigação com a linha do tempo
- `cairn/scripts/cairn-status.py` — `phase_model()` e as chaves de corroboração
- `.gitignore` — `.cairn/conflicts.json` já está lá
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.cairn/conflicts.json` já declarado no `.gitignore` e nunca escrito — o slot
  estava reservado desde o v1.0.
- `cairn-doctor.py` já tem o padrão exato de que o `--apply-reconciliation`
  precisa: checagens read-only por default, escrita atrás de flag nomeada, cada
  id impresso, idempotente (`--close-completed`, `--link-refs`).
- `cairn-journal.py history` e `last-moved` são a linha do tempo que a
  investigação lê — construídos na fase 16 sem saber que serviriam a esta.

### Established Patterns
- Todo `cairn-X.py` tem par `.sh` e `tests/cairn-X.bats`.
- Um teste que passaria com a feature removida não é prova — cada onda da fase 16
  provou seus testes quebrando o código e vendo vermelho.

### Integration Points
- `cairn-reconcile.py` / `.sh` (novos) e `tests/cairn-reconcile.bats` (novo).
- `cairn-doctor.py` — a flag `--apply-reconciliation`.
- Um comando de prosa que dispara a investigação (o subagente restrito).

</code_context>

<specifics>
## Specific Ideas

- A arquitetura em camadas não foi a primeira resposta. Ela nasceu de um conflito
  levantado durante a conversa entre a resposta inicial (subagente restrito) e o
  critério 1 do roadmap (grep + teste sobre o caminho de análise). Registrado
  porque a simplificação "é só usar um subagente restrito" vai parecer atraente
  para quem ler isto depois, e ela custa exatamente a verificabilidade.

</specifics>

<deferred>
## Deferred Ideas

- Severidade de conflito com mais de dois níveis — CORR-09, v2.
- Visão de tendência de conflitos entre milestones — CORR-10, v2.
- Aplicar reconciliação automaticamente sob qualquer condição — fora de escopo
  por construção: o ESC-03 exige comando separado e invocado por humano.

</deferred>

---

*Phase: 17-Semantic escalation*
*Context gathered: 2026-07-31*
