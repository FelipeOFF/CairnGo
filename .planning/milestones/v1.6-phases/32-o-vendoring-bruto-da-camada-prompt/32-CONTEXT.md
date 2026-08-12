# Phase 32: O vendoring bruto da camada prompt - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A fase copia o fecho transitivo dos 8 workflows (160 arquivos, 28.071 linhas na
medição do research; o número vivo sai do inventário da fase 31) do clone da tag
v1.10.0 para `cairn/gsd/`, byte a byte, com o LICENSE MIT intacto e crédito no
README. Nenhuma adaptação semântica: a prova de fidelidade é diff vazio contra o
clone na lista de inclusão, e a prova do corte é a ausência testada do que ficou
de fora (gsd-write-guard.js, tests, docs, src, instalador, multi-host,
capabilities).

</domain>

<decisions>
## Implementation Decisions

### Estrutura interna de cairn/gsd/
- **D-01:** Espelhar a árvore upstream: `cairn/gsd/workflows/`, `agents/`, `references/`, `templates/`, `contexts/`, `commands/`, `skills/` com os mesmos caminhos relativos do clone. O diff byte a byte (VEND-03) fica trivial e a fase 36 mede a própria mudança contra base idêntica ao upstream. — **Reversibility:** costly — a fase 36 edita esses arquivos em lugar; reorganizar depois quebra o diff contra o clone e o mapa mental dos sítios medidos.

### Lista de inclusão (VEND-01)
- **D-02:** O `cairn-inventory` ganha um subcomando de fecho transitivo que emite a lista de arquivos; a lista é gravada como manifest versionado em `cairn/gsd/` (ex.: `MANIFEST.json` ou equivalente). O manifest é o artefato consumido pelo vendoring e pelo teste; o subcomando é a prova de que ele é derivado — o bats compara manifest gravado com saída do comando.

### Claude's Discretion
- Nome e formato exato do manifest (JSON no padrão de serialização da casa: indent 2, sort_keys, newline final).
- Mecânica da cópia (script one-shot vs alvo no próprio inventory), desde que a prova de fidelidade seja diff vazio por teste.
- Onde o crédito entra no README (seção de créditos existente; registrar tag e commit `68a04cc` do pin).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Insumos da fase
- `.planning/research/v1.6-transplante-gsd.md` — §2.1 (superfície e fecho), §3 (plano de corte com linhas), §5 (licença).
- `.planning/ROADMAP.md` — Goal da Phase 32; o gsd-write-guard fica fora por teste.
- `cairn/gsd/contracts/` — os contratos da fase 31 (vizinhos do vendoring; não são tocados nesta fase).
- `cairn/scripts/cairn-inventory.py` — o inventário da fase 31 que ganha o subcomando de fecho.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cairn-inventory.py` (fase 31): já pina o clone da tag em cache com verificação de commit (`68a04cc`); o subcomando de fecho reusa o mesmo cache e a mesma resolução de corpus.
- Serialização da casa: `indent=2, sort_keys=True`, newline final (padrão dos contratos da 31).

### Established Patterns
- Teste de ausência: bats assertando que caminhos proibidos não existem sob `cairn/gsd/` (write-guard, tests/, docs/, src/, instalador, multi-host, capabilities/).
- LICENSE empilhado: o repo já empilha copyrights em LICENSE (precedente Felipe Oliveira + John Reed); o `cairn/gsd/LICENSE` entra intacto, sem empilhar.

### Integration Points
- A fase 36 edita os arquivos vendorizados em lugar; a base byte-idêntica é o que permite medir a mudança dela.
- O manifest é insumo do teste de fidelidade e do corte; o inventário é a única fonte da lista.

</code_context>

<specifics>
## Specific Ideas

- Número vivo: a lista sai do subcomando sobre o corpus pinado; se der diferente de 160/28.071 do research, o número medido vence e fica registrado com o comando ao lado.
- gsd-write-guard.js é o exemplo canônico de exclusão: colide com o milestone (bloqueia Write que encolha STATE/ROADMAP) e a ausência dele é assertada por teste nomeado.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 32-o-vendoring-bruto-da-camada-prompt*
*Context gathered: 2026-08-10*
