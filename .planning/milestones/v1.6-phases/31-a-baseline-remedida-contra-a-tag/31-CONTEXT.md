# Phase 31: A baseline remedida contra a tag - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A fase entrega o inventário do corpus GSD v1.10.0 como comando executável e os
contratos de entrada/saída por verbo como dado versionado. Nenhum shim, nenhum
verbo python, nenhum vendoring: só a medição que as fases 32-38 orçam em cima.
Saídas concretas: `cairn-inventory` (script novo no padrão da casa), os contratos
em `cairn/gsd/contracts/`, a semântica dos 4 verbos órfãos extraída do bundle
bakeado, e a estimativa de init re-derivada pelos 9 shapes de bundle.

</domain>

<decisions>
## Implementation Decisions

### Corpus alvo (como o comando referencia 880k linhas fora do repo)
- **D-01:** Clone on-demand em cache local: o script clona `--depth 1 --branch v1.10.0` de open-gsd/gsd-core para um cache (`.cairn/cache/` ou equivalente, fora do controle de versão), verifica o commit da tag antes de usar, e roda sobre ele. O corpus nunca entra no repo. Precisa de rede na primeira execução, e isso é aceito e documentado.

### Contratos por verbo (a "tabela versionada" do REM-03)
- **D-02:** JSON em `cairn/gsd/contracts/`: um arquivo por família mais um agregado. As fases 33-35 e o harness diferencial consomem esse dado diretamente; o bats valida o schema. — **Reversibility:** costly — o caminho e o schema viram insumo do binário python e do harness das três fases seguintes; mudar depois toca todos os consumidores.

### Forma do inventário
- **D-03:** Script novo `cairn-inventory.py` + wrapper `.sh` + bats próprio, padrão da casa. O doctor fica intocado, o que a fase 35 (CHECK-04, baseline fixa do doctor) já exige.

### Verbos órfãos (sem fonte em src)
- **D-04:** Mesmo schema JSON dos demais contratos, com campo de proveniência (`"provenance": "extraído do gsd-tools.cjs bakeado"` + referência de linha). O harness da 33 não precisa de caso especial.

### Claude's Discretion
- Layout interno de `cairn/gsd/contracts/` (nomes de arquivo por família, shape exato do schema), desde que um só leitor sirva a todos os consumidores.
- Local exato do cache do clone e política de invalidação (commit da tag como chave).
- Formato da saída humana do `cairn-inventory` (tabela/JSON), desde que `--json` exista, como nos demais scripts da casa.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O research que dimensiona a fase
- `.planning/research/v1.6-transplante-gsd.md` — números medidos e verificados (seções 2.3 verbos, 4 binário, 6 riscos 1-2-5-6-12); a regex de calibração e as duas métricas (147/189) que o REM-02 unifica.

### O milestone
- `.planning/ROADMAP.md` — Goal e critérios da fase 31; a regra source-com-source.
- `.planning/REQUIREMENTS.md` — REM-01..05 e o que ficou fora de escopo do milestone.

[Sem specs externos além destes.]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Padrão da casa para scripts: `cairn/scripts/<nome>.py` + wrapper `<nome>.sh` (`set -euo pipefail` + exec python3) + `tests/<nome>.bats`. `die()` é reimplementado por script; não há lib compartilhada, e isso é decisão registrada da casa.
- A regex de calibração do research reproduz 516/107 na 1.9.1: `grep -rhoE 'gsd_run query [a-z][a-z0-9._-]+'`; a métrica larga (adotada pelo REM-02) é `gsd_run (query )?[a-z][a-z-]*(\.[a-z-]+)?`.

### Established Patterns
- Saída `--json` em todos os scripts de leitura (status, doctor, parallel); o inventário segue.
- Grafia dupla `verification.status` / `query verification status` existe no corpus: o parser aceita as duas (research §2.3).

### Integration Points
- `cairn/gsd/contracts/` nasce nesta fase e é lido pelas fases 33-35 (binário python) e pelo harness bats diferencial.
- O clone em cache é o mesmo insumo que a fase 32 (vendoring) usará para gerar a lista de inclusão.

</code_context>

<specifics>
## Specific Ideas

- Números de aceitação vindos do research (o inventário deve reproduzi-los ou corrigi-los com o comando junto): 534 chamadas/116 verbos no corpus da 1.10.0; 189 sítios/60-61 verbos nos 8 workflows na métrica larga; 64 sítios/42 verbos nos 12 agentes; 17 sítios de `loop render-hooks` nos 8.
- A contabilidade de completude do research (651 ocorrências = 189 chamadas + 460 preâmbulos shim + 2 prosa) vira asserção do inventário: nada escapa da regex sem ser classificado.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 31-a-baseline-remedida-contra-a-tag*
*Context gathered: 2026-08-10*
