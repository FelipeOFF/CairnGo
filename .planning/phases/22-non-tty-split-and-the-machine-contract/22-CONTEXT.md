# Phase 22: Non-TTY split and the machine contract - Context

**Gathered:** 2026-08-06
**Status:** Ready for planning

<domain>
## Phase Boundary

`--plain` volta a ser só contrato de máquina, e quem lê fora do TTY passa a receber
algo legível.

Requisitos: BOARD-04, PIPE-01, PIPE-02, PIPE-03. Issues bd: ver `22-BEADS-MAP.md`.

**Esta fase herda três defeitos que a fase 21 expôs**, movidos para cá porque são
todos do board e a 21 já estava fechada quando apareceram: `CairnGo-cdx`,
`CairnGo-uz6` e `CairnGo-hbo`. Eles não têm requisito próprio — são consertos, e a
fase decide quais cabem.

</domain>

<decisions>
## Implementation Decisions

Fase aberta em modo autônomo. Todas as decisões saem de medição feita em 2026-08-06
contra a árvore já com a fase 21 mesclada. Onde algo não foi medido, está escrito.

### O acoplamento é literal e está provado

- **D-01: hoje `--plain` e o default sem TTY são byte-idênticos, e há md5 disso.**

  ```
  cairn-status.sh --plain | md5   8ae01413710044cf2b7de6863cb4161f
  cairn-status.sh         | md5   8ae01413710044cf2b7de6863cb4161f
  ```

  A asserção que fixa isso está em `tests/cairn-status.bats:246-251` — **não** na
  linha 208, que é onde o roadmap ainda a coloca; a fase 21 reescreveu dois testes
  acima e o número andou. Ela é literalmente:

  ```bash
  # Explicit --plain is byte-identical to the non-TTY default.
  local piped="$output"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --plain
  [ "$status" -eq 0 ]
  [ "$output" = "$piped" ]
  ```

  O `PIPE-03` manda **reescrever, nunca remover**: uma asserção afirma que o
  não-TTY sem flag produz a lista agrupada em texto puro, e outra afirma que
  `--plain` continua o TSV de sempre. Duas afirmações separadas sobre duas
  superfícies que deixam de ser a mesma.

### A referência do `--plain` é gravada antes, não depois

- **D-02: o byte-a-byte do `PIPE-01` precisa de uma referência commitada capturada
  ANTES de a fase mudar o caminho não-TTY.** É o mesmo padrão da fase 20 com os sete
  renders, e pela mesma razão: depois da mudança, "byte a byte compatível com o que
  existe hoje" não tem mais com o que comparar.

  Sem isso o `PIPE-01` vira auto-referência — o teste compara a saída nova consigo
  mesma e fica verde para sempre, provando nada. Este é o primeiro plano da fase.

### Um roadmap sem `## Milestones` faz o board se contradizer na mesma tela

- **D-03: o `CairnGo-uz6` é mais grave do que "perde a fase", e a medição mostra.**
  Reproduzido num repositório temporário, roadmap com uma fase e **sem** a seção
  `## Milestones`:

  ```
  ready 0 · doing 0 · blocked 0 · done 0

    (no open work)                 <- a lista agrupada
  phase 1/1 Alpha · done: 0        <- o rodapé
  PENDING PHASES  1                <- a tabela
  ```

  A lista diz que não há trabalho aberto enquanto o rodapé e a tabela, na mesma
  tela, dizem que há uma fase. **Três superfícies, duas respostas.** Com a seção
  presente o mesmo fixture rende `v9.9 Teste` / `◌ 1 Alpha`, correto.

  Isso é exatamente o que este milestone existe para eliminar, e está dentro do
  escopo do `BOARD-04`, que é sobre o cabeçalho dizer a verdade sobre o milestone —
  inclusive quando não há um.

### A tabela tem piso de 92 colunas, medido em quatro larguras

- **D-04: `CairnGo-cdx` reproduzido, e a faixa é maior que a da issue.**

  ```
  --width 60   maior linha 92 colunas   ESTOURA
  --width 70   maior linha 92 colunas   ESTOURA
  --width 80   maior linha 92 colunas   ESTOURA
  --width 90   maior linha 92 colunas   ESTOURA
  --width 100  maior linha 100 colunas  cabe
  --width 120  maior linha 120 colunas  cabe
  ```

  A linha culpada é sempre a mesma, a de uma fase na tabela `PENDING PHASES`.
  Medido com largura de coluna real (`east_asian_width`), não com `len()` — o board
  tem multibyte e contar caracteres daria número errado.

### O alinhamento em locale CJK não se conserta trocando glifo

- **D-05: `CairnGo-hbo` medido, e a conclusão muda o que a issue pedia.** Num render
  a `--width 100` há **51** glifos de largura ambígua (`east_asian_width=A`):

  | glifo | ocorrências |
  |---|---|
  | `—` EM DASH | 28 |
  | `…` ELLIPSIS | 8 |
  | `·` MIDDLE DOT | 4 |
  | `▶` | 1 |
  | `á ê ó í é` | 12 |

  A fase 21 mediu os **símbolos de etapa** e escolheu só os de largura `N`. Mas a
  prosa do próprio board é português — `não`, `está`, `é`, `próxima` — e **toda letra
  acentuada é `A`**. Em terminal com locale CJK cada uma ocupa duas colunas.

  Então trocar `—` por `-` e `…` por `...` melhora, e **não resolve**: enquanto o
  board falar português, o alinhamento em locale CJK depende de resolver `A` por
  locale, não de escolher glifos. As duas saídas honestas são (a) uma função de
  largura que resolve `A` conforme o ambiente, ou (b) declarar por escrito que o
  alinhamento é garantido em locale ocidental e não em CJK. **Escolher entre elas é
  decisão de produto e fica para o plano registrar**, com a medição junto.

### Claude's Discretion

- Quais dos três defeitos herdados entram nesta fase. O `uz6` é o mais forte
  candidato porque é contradição de estado, não estética. O `hbo` pode sair com a
  decisão escrita e sem código.
- A forma exata do texto puro do não-TTY: o mesmo layout agrupado sem ANSI, ou uma
  variante mais estreita.
- Se a referência do `PIPE-01` mora em `tests/fixtures/board-render/` junto com as
  outras sete ou num diretório próprio.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### O que esta fase não pode quebrar
- `tests/fixtures/board-render/` e `tests/cairn-board-invariance.bats` — os sete
  renders de referência, regenerados pela fase 21 com o diff lido linha a linha
- `.planning/phases/21-the-grouped-board/21-SUMMARY.md` — o que a 21 entregou e as
  ressalvas que ela deixou por escrito

### Código
- `cairn/scripts/cairn-status.py` — o render agrupado, o caminho não-TTY e a
  tabela `PENDING PHASES`
- `tests/cairn-status.bats:228-251` — o teste do acoplamento que o `PIPE-03`
  reescreve
- `cairn/docs/commands/status.md` — página é contrato
- `.planning/codebase/CONVENTIONS.md` — stdlib only, par `.py`/`.sh`, `EXIT_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- A fase 20 já resolveu como capturar render de referência e provar que a comparação
  está viva (um teste perturba o fixture e exige que a comparação falhe).
- A fase 21 já provou o padrão de mutação: aplicar a quebra ao fonte, com backup por
  `cp`, e medir que o teste fica vermelho.

### Established Patterns
- Um teste que passaria com a feature removida não é prova.
- Toda asserção de status é sobre o valor exato, nunca sobre a negação.
- Chave existente nunca muda de nome, de tipo ou de significado.
- Nunca regenerar referência de render para um teste passar; ler o diff é o
  entregável.

### Integration Points
- `cairn/scripts/cairn-status.py` e `tests/cairn-status.bats` — o grosso.
- **Nada de doctor.** As fases 23 e 24 acabaram de colidir em `cairn-doctor.py` num
  auto-merge silencioso; esta fase não tem motivo para tocá-lo.

</code_context>

<specifics>
## Specific Ideas

- **O acoplamento que esta fase desfaz foi decisão consciente um dia.** `--plain`
  virou fallback de não-TTY para que pipes nunca recebessem box-drawing. A fase 21
  removeu todo box-drawing do fonte — zero glifos de caixa restam. **A razão original
  do acoplamento deixou de existir**, e é isso que torna a separação segura agora e
  não antes.

- **Este ciclo já pagou pelo teste que o `PIPE-03` protege.** A fase 21 encostou nesse
  acoplamento, viu que a mudança dela o quebraria, e **parou** em vez de editar o
  teste — registrando no SUMMARY que cruzar ali seria entrar na fase 22. A disciplina
  já foi exercida; esta fase só executa o que aquela recusou fazer sozinha.

</specifics>

<deferred>
## Deferred Ideas

- Resolver largura ambígua por locale em todo o board. Se o plano concluir que é a
  saída certa, ela é grande e merece fase própria; o que **não** é aceitável é a
  fase terminar sem dizer qual das duas saídas foi escolhida.
- O board HTML. Superfície própria, fora desta fase.
- Reduzir a largura mínima do board abaixo de 60 colunas.

</deferred>

---

*Phase: 22-Non-TTY split and the machine contract*
*Context gathered: 2026-08-06*
