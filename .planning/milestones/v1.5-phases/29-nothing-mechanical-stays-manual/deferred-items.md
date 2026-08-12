# Itens diferidos — fase 29

Achados fora do escopo do plano em que apareceram. Registrados, não consertados.

## `STATE.md` tem prosa defasada que faz a ferramenta de estado escrever errado

**Achado em:** 29-04, no fecho do plano
**Onde:** `.planning/STATE.md`, seção `## Current Position` (e `## Project
Reference` → "Current focus")

O texto ainda diz:

```
**Current focus:** Milestone v1.4 (Honest State) — 13 a 17 fechadas; 18 e 19 pendentes
...
Phase: 18 — Parallel phase execution (não planejada)
Status: Fases 13-17 fechadas — próxima é a 18
Last activity: 2026-07-31 — Fases 14 e 15 em paralelo, mescladas e fechadas
```

O milestone aberto é o **v1.5** e a fase corrente é a **29**.

**Por que importa, medido:** rodar `gsd-tools query state.update-progress` no
fecho do 29-04 sobrescreveu `current_phase: 29` com `current_phase: 18`,
deixando o frontmatter em contradição com o próprio `current_phase_name`
("Nothing mechanical stays manual", que é a 29). A ferramenta leu a prosa velha
e a promoveu a fato. Foi corrigido à mão naquele fecho, mas **o próximo fecho
vai reintroduzir**, porque a causa continua no arquivo.

O `cairn-doctor` já reprova isso como `state-narrative-stale` e
`state-counter-stale` — a checagem existe e está certa; falta o conserto da
prosa.

**Dono natural:** o `cairn-bookkeep` (AUTO-01, plano 29-02) é quem move
contadores e narrativa do STATE. Uma linha ao fechar a fase 29 resolve.

**Não consertado aqui porque:** é anterior ao 29-04, tem dono declarado, e
editar a narrativa de estado de outra fase de dentro deste plano seria
exatamente o tipo de escrita silenciosa que este milestone existe para acabar.

---

## O rodapé e a tabela `PENDING PHASES` do board estouram o `--width` pedido

**Achado em:** 29-05, Task 1, ao escrever a varredura de largura
**Onde:** `cairn/scripts/cairn-status.py` — `footer_lines()` e
`phase_panel_lines()`

**Medido** na fixture `make_board_fixture`, **antes e depois** de qualquer
`external_ref` (números idênticos nas duas medições, ou seja: nada disto vem
deste plano):

| `--width` | linhas acima do limite | pior caso |
| --------- | ---------------------- | --------- |
| 38 | 6 | `READY  brd-001  Read the roadmap into a phase model` = 51 células |
| 40–58 | 1 | rodapé `phase 3/4 … · v1.0 · done: 1` = 70 células |
| 64 | 4 | rodapé (70) + cabeçalho da tabela (85) + linha de fase (90) |
| 72–80 | 3 | tabela `PENDING PHASES` = 85–90 células |
| 100–200 | 0 | — |

A grade de raias (`┌ │ └`) **respeita** o limite em todas as larguras, com e
sem card — é essa a invariante que o `tests/cairn-tracker-card.bats` afirma, e
está escrito lá que ela é só sobre a grade, junto com o motivo.

Quem estoura são três renderizadores com regras próprias de largura: o modo
`raw` (< 40 colunas) imprime título inteiro por contrato, o rodapé não trunca,
e a tabela do painel tem colunas de largura fixa (`RSCH_W`, `PLANS_W`,
`ISSUES_W`, `VERIFY_W`, `WAITS_W`, `NEXT_W`) que somam mais que uma janela
estreita antes de qualquer conteúdo.

**Não consertado aqui porque:** é anterior a este plano, não é alcançável por
nenhuma mudança dele, e decidir o que um rodapé de 70 células faz numa janela
de 40 (trunca? quebra? some?) é decisão de produto sobre três renderizadores
que este plano não abre.
