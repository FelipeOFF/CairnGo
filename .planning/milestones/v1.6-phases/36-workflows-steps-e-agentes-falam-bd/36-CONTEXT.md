# Phase 36: Workflows, steps e agentes falam bd - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A camada prompt vendorizada passa a falar com o binário python do próprio repo e a
tratar o bd como dono do estado: o preâmbulo shim aponta `cairn/scripts/cairn-gsd.sh`,
os sítios de estado dos 8 workflows e dos 16 agentes deixam de ler `.planning/*.md`
como FATO, e o mecanismo de composição por `section_manifest` é preservado e corrigido.
Os 40 arquivos de `references/` citados pelos workflows ficam FORA desta fase, com a
lacuna medida e registrada. A troca de plugin é da fase 37; a paridade ponta a ponta é
da 38.

</domain>

<decisions>
## Implementation Decisions

### O preâmbulo é a onda zero (achado do research, não do roadmap)
- **D-01:** A primeira onda troca os 34 blocos de preâmbulo shim para resolver o binário
  do repo. Motivo medido: nenhum dos 169 arquivos vendorizados menciona `cairn-gsd` ou
  `cairn/scripts` hoje — os testes das fases 33-35 provam o binário, e o caminho que um
  usuário executa resolve `gsd-tools.cjs`. Antes desta troca, nenhuma outra edição da
  fase tem efeito observável. A forma nova é testada rodando, não só escrita. —
  **Reversibility:** reversible — é substituição textual de bloco, com o bloco antigo
  no histórico.

### Escopo: workflows + agentes, references fora
- **D-02:** A fase adapta os 8 workflows (50 arquivos com fragments, 189 chamadas) e os
  16 agentes (65 chamadas, 8 blocos de shim próprios) — todo caminho de execução que o
  usuário dispara. Os 40 `references/` citados (18 chamadas, ~33 sítios de estado,
  incluindo o `cat .planning/STATE.md` de `autonomous-smart-discuss.md:24`) NÃO entram:
  a lacuna é medida, registrada em divergences.json e no SUMMARY, e vira alvo da 37/38.
  — **Reversibility:** reversible — ampliar depois é somar arquivos ao mesmo trabalho.

### Composição preservada, tipo corrigido (ADAPT-01)
- **D-03:** O mecanismo `section_manifest` + steps é PRESERVADO. Achatar inlinaria 21
  arquivos (806 linhas, +12,4% sobre as 6.502 linhas lidas sempre) para adaptar 10 das 38
  chamadas dos fragments, com o estado em markdown 65-vs-8 a favor da raiz. Junto vai a
  correção do bug de tipo: os 6 sítios que emitem `section_manifest: []` passam a emitir
  `null` (o valor "degradado / lê tudo" que a camada prompt especifica; `[]` não é nem
  null nem objeto com `.included`), com os 6 goldens regravados. Preencher o manifesto de
  verdade é incremento posterior, NUNCA no mesmo plano. — **Reversibility:** reversible.

### resolve-execution: falha nomeada e sítio cortado (ADAPT-05)
- **D-04:** `resolve-execution` (recuperação de quota) não existe no universo de 87 e o
  sítio consome o JSON em 5 `jq` sem tolerar falha. O binário responde com a falha nomeada
  padrão e o caminho de quota-recovery passa a descrever recuperação manual. Zero código
  novo; o comportamento degradado fica escrito em vez de quebrar no meio de um pipe. —
  **Reversibility:** reversible — implementar o verbo depois é somar handler + golden.

### Claude's Discretion
- Forma exata do preâmbulo novo (resolução do binário, env necessária, fallback quando o
  repo não é o cwd), desde que testada rodando e idêntica nos 34 blocos salvo motivo escrito.
- Ordem das fatias depois da onda zero (o roadmap sugere fast/debug primeiro,
  execute-phase por último — mantida salvo motivo medido).
- Como provar "zero leitura de `.planning/` como fonte de estado" por workflow: a métrica
  não pode ser grep por nome de arquivo (há 13 linhas que referenciam estado por variável).
- Tratamento dos outros dois itens de ADAPT-05 (`intel api-surface`, `graphify`) — decisão
  explícita registrada, nunca silêncio.
- O descompasso de grafia de `worktree.set-baseref` (uma linha em references) entra se a
  fase tocar o arquivo; caso contrário fica registrado.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/36-workflows-steps-e-agentes-falam-bd/36-RESEARCH.md` — os números
  medidos, as duas armadilhas de métrica e a correção de laudo. Insumo primário.
- `cairn/gsd/gsd-core/workflows/` — os 8 raiz + 42 fragments; `execute-phase.md:85,92`
  é onde o `section_manifest` é capturado e gateia.
- `cairn/gsd/agents/` — 16 agentes, 8 com preâmbulo shim próprio.
- `cairn/scripts/cairn-gsd.sh` + `cairn-gsd.py` + irmãos state/init/check — o binário
  que o preâmbulo passa a resolver; `cairn-gsd-init.py` linhas 574/583/614/786/823/856
  são os 6 sítios do `section_manifest`.
- `cairn/gsd/contracts/` — a letra de cada verbo e suas grafias.
- `tests/cairn-gsd.bats` + `tests/fixtures/gsd-goldens/` — harness herdado; 6 goldens
  congelam o `section_manifest: []`.
- SUMMARYs 35-01..35-05 — desvios da fase anterior e o estado do guard 87/87.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Binário completo: 87 verbos respondendo pelo dispatcher único, com goldens por forma.
- `cairn-inventory.py` — a ferramenta canônica do milestone (BROAD_RE declarada); qualquer
  contagem desta fase sai dela ou declara por que não.

### Established Patterns
- Fato vem do label projetado no bd (5 dimensões da fase 34); documento vem do arquivo.
- Falha nomeada com o comando que cria o fato; nunca fallback markdown, nunca forma vazia.
- Divergência consciente vai a divergences.json com motivo.

### Integration Points
- Fase 37 remove o plugin externo: depois dela, um preâmbulo que ainda resolva
  `gsd-tools.cjs` falha com exit 1. É o que torna a onda zero desta fase pré-requisito.
- O bookkeep do cairn também escreve ROADMAP/REQUIREMENTS — nenhum workflow adaptado
  pode passar a escrever nesses arquivos por outro caminho.

</code_context>

<specifics>
## Specific Ideas

- Medir antes e depois com a ferramenta canônica, e publicar o número mesmo quando for
  zero (regra herdada do roadmap).
- O incidente `current_phase 18` está morto no binário e vivo no caminho executado até a
  onda zero fechar — o teste de ponta a ponta desta fase precisa exercer o caminho real,
  não o `$GSD` do harness.

</specifics>

<deferred>
## Deferred Ideas

- Preencher `section_manifest` com included/excluded de verdade (ganho de contexto):
  incremento medido, fase própria ou 38.
- Os 40 `references/` citados e os 193 caminhos `$HOME/.claude`: registrados, alvo da 37/38.
- `--wave` declarado como bool_flag no handler enquanto o workflow passa valor: correção
  barata, fora do caminho crítico desta fase.

</deferred>

---

*Phase: 36-workflows-steps-e-agentes-falam-bd*
*Context gathered: 2026-08-11*
