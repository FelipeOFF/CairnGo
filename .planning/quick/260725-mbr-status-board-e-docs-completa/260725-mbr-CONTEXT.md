# Quick Task 260725-mbr: Status board elegante + documentação completa de comandos - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning
**bd issue:** CairnGo-4ju

<domain>
## Task Boundary

Duas frentes:
1. Redesign do `/cairn:status`: board visual elegante no terminal (CLI design), mostrando o que precisa e o que falta.
2. Documentação completa: todos os 22 comandos de `cairn/commands/` mapeados e bem documentados.

Entrega final: issue no GitHub + PR cobrindo as duas frentes.

**Nota de deviation:** `/gsd:quick` formalmente exige ROADMAP.md (`roadmap_exists: false` — new-project foi interrompido pelo pivô do usuário para este trabalho). Rastreamento corre pelo bd (CairnGo-4ju) + artefatos nesta pasta; sem update de STATE.md (não existe).

</domain>

<decisions>
## Implementation Decisions

### Superfície do comando
- Board vive DENTRO do `/cairn:status` — um comando só, sem `/cairn:index` ou `/cairn:board` separado.
- Flag `--brief` para versão curta (3 linhas) no dia a dia.

### Estilo visual
- **Kanban em colunas** (escolha do usuário, com preview): colunas READY / DOING / BLOCKED lado a lado em box-drawing, rodapé com fase + próxima ação.
- Renderização via **script determinístico** (não prosa): consistência pixel-a-pixel entre runs, testável em bats.
- Mitigação de terminal estreito (decisão de design minha): degradação graciosa — detectar largura (`tput cols`/`COLUMNS`) e truncar títulos com reticências; board nunca quebra linha no meio de uma célula.

### Formato da documentação
- Um arquivo por comando: `cairn/docs/commands/<cmd>.md` (22 arquivos) + índice `cairn/docs/commands.md` com tabela.
- Escala para o formato web futuro mencionado pelo usuário.

### Claude's Discretion
- Estrutura interna de cada doc de comando (seções padrão: propósito, uso, fluxo, flags, exemplos, arquivos tocados, comandos relacionados).
- Linguagem do script do board (seguir house style de `cairn/scripts/`).
- Cores ANSI: usar com parcimônia, respeitar `NO_COLOR`.
- Integração: `status.md` (prosa) passa a chamar o script e apresentar o output.

</decisions>

<specifics>
## Specific Ideas

- Usuário descreveu: "um board no terminal me falando o que precisa e o que falta, como uma linha com suas baias bem definidas".
- Preview aprovado pelo usuário (kanban colunas):
  ```
  ┌─ READY ────────┬─ DOING ────────┬─ BLOCKED ──────┐
  │ a1x gate regex │ 4ju status bo… │ c3z ⧗ a1x      │
  │ b2y timeouts   │                │                │
  └────────────────┴────────────────┴────────────────┘
  fase 2/4 · ▶ próximo: continuar 4ju
  ```
- Futuro (fora de escopo agora): formato web para acompanhar o board.
- Prioridade declarada do usuário: documentação de todos os comandos.

</specifics>

<canonical_refs>
## Canonical References

- `cairn/commands/status.md` — comando atual (prosa, seções Actionable/In flight/Blocked/Roadmap/next action)
- `cairn/docs/architecture.md` — ownership model e camadas de enforcement
- `.planning/codebase/` — mapa da codebase (7 docs, 2026-07-25)
- clig.dev e princípios de CLI design para o board

</canonical_refs>
