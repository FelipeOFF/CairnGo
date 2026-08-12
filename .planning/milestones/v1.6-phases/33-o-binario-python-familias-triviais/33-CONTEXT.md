# Phase 33: O binário python, famílias triviais - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A fase entrega o binário python respondendo as cinco famílias triviais (config,
commit, skills, loop-hooks, dispatch/model — ~96 sítios pelo research) na forma
dos contratos da fase 31, e o harness diferencial bats que compara cada verbo
python com o gsd-tools real da tag. O produto durável é o harness: as fases 34 e
35 o herdam pronto. Nenhum verbo de estado, checagem ou órfão entra aqui.

</domain>

<decisions>
## Implementation Decisions

### Onde o binário vive e em que forma
- **D-01:** Dispatcher único `cairn/scripts/cairn-gsd.py` + wrapper `cairn-gsd.sh` + `tests/cairn-gsd.bats`, padrão da casa (sem lib compartilhada; as famílias triviais cabem num script). O preâmbulo shim dos workflows passa a apontar pra ele na fase 36. Como as famílias das fases 34-35 crescem (mesmo arquivo ou scripts irmãos) é decisão adiada e registrada, tomada na fase 34 com o tamanho medido na mão. — **Reversibility:** costly — o caminho do binário é o alvo do preâmbulo shim da fase 36 e do harness; mover depois toca os dois.

### Harness diferencial (TRIV-04)
- **D-02:** Goldens gravados da tag: as respostas do gsd-tools.cjs do clone são gravadas uma vez como golden files versionados (por verbo/cenário); o bats diferencial roda contra os goldens, offline e determinístico. Um modo `--record` re-grava executando o binário real do clone, skip-gated quando node ou o clone não estão disponíveis. — **Reversibility:** reversible — trocar goldens por execução viva depois é mudança local no harness.

### Claude's Discretion
- Layout dos goldens (diretório, um arquivo por verbo/cenário, formato) e a mecânica exata do `--record`.
- Envelope de saída do dispatcher: o contrato da fase 31 manda; onde o contrato registrar divergência deliberada (bd como fonte), a diferença é declarada em tabela no próprio contrato, não improvisada.
- Tratamento de verbo não implementado nesta fase: falha nomeada apontando a família e a fase que o entrega (nunca resposta vazia).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Insumos da fase
- `cairn/gsd/contracts/` — os contratos por verbo da fase 31 (`contracts.json` agregado + por família): a FORMA de cada resposta vem daqui, verbo a verbo, com source_ref.
- `.planning/research/v1.6-transplante-gsd.md` — §4 (famílias, custos, o que o cairn reaproveita: config ~80 linhas com config-defaults.manifest.json de 106 linhas; commit wrapper de git; loop-hooks como tabela; dispatch devolve o role).
- `.planning/ROADMAP.md` — Goal da Phase 33.
- `cairn/scripts/cairn-inventory.py` — resolução do clone em cache (reusar, não duplicar).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Cache do clone da tag (fase 31) com verificação de commit — o `--record` usa o mesmo cache.
- `cairn/scripts/cairn-config.py` (782 linhas) já cobre parte da família config; o dispatcher reusa a lógica sem importar módulo (padrão da casa: forma se copia, módulo não).
- Descobertas da fase 31 registradas nos contratos: `phase.list-artifacts` e `plan.task-structure` são verbos fantasma na tag; `summaries_total` e `uat_path` são pedidos por workflows e nunca emitidos — o dispatcher precisa decidir resposta honesta para esses casos conforme o contrato.

### Established Patterns
- py + sh + bats por superfície; die() por script; `--json` obrigatório; exit codes 0/2 + semântica registrada.
- Serialização estável (indent 2, sort_keys, newline).

### Integration Points
- O harness vira o molde das fases 34-35 (elas herdam o formato de golden + diferencial).
- A fase 36 aponta o preâmbulo `gsd_run()` para `cairn-gsd.sh`.

</code_context>

<specifics>
## Specific Ideas

- O diferencial compara envelope inteiro (stdout, exit code; stderr quando o contrato registrar) por verbo/cenário contra o golden.
- Cobertura da fase provada contra o inventário: os ~96 sítios das 5 famílias respondem; sítio de família trivial sem verbo implementado reprova.

</specifics>

<deferred>
## Deferred Ideas

- Como as famílias das fases 34-35 se distribuem em arquivos (decisão na 34, com medida).

</deferred>

---

*Phase: 33-o-binario-python-familias-triviais*
*Context gathered: 2026-08-10*
