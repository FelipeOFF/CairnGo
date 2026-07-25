---
status: complete
quick_id: 260725-mbr
bd_issue: CairnGo-4ju
date: 2026-07-25
---

# Quick Task 260725-mbr — Summary

## O que foi entregue

**Frente 1 — Status board.** `/cairn:status` agora renderiza um board kanban em colunas via script determinístico:

- `cairn/scripts/cairn-status.py` (+ wrapper `.sh` no molde do repo): 3 lanes READY/DOING/BLOCKED em box-drawing, rodapé com posição de fase, milestone, done count e `▶ next` (síntese: in_progress > ready da fase ativa > next action do STATE). Dual-mode estilo gh CLI: TTY = board; pipe = `--plain` limpo (zero escapes); `--json` uma linha; `--brief` 3 linhas; `--width` força render determinístico (bats/pipes); degradação por largura (colunas → empilhado → lista crua); cor 4-bit com precedência `--color` > `CAIRN_NO_COLOR` > `NO_COLOR` > `TERM=dumb` > isatty; `--ascii`; truncamento por display width (east_asian_width, zero deps).
- `cairn/commands/status.md` reescrito no modelo doctor.md (roda o script, apresenta verbatim, documenta exit codes 0/2/5 com fallback). Linha do status atualizada em `help.md` + espelho em `cairn/README.md`.
- `tests/cairn-status.bats`: 22 testes, incluindo adversariais (injection de bytes de controle em títulos), bd-only sem `.planning/`, GSD-only sem `.beads/`, degraus de cor, PATH-stub exit 5, isolamento `--planning-dir`.

**Frente 2 — Documentação.** Todos os 22 comandos documentados individualmente em `cairn/docs/commands/<cmd>.md` (inglês, estrutura fixa: Usage / What it does / Flags / Exit codes / Examples / Files touched / Related; 2021 linhas no total) + índice `cairn/docs/commands.md` agrupado como o help, linkado de `cairn/README.md` e `README.md`.

## Qualidade

- Pipeline --full: plan-check (3 minors corrigidos em voo) → 4 builders → integração → verify E2E (**passed**, 9/9 checks) → code review (13 findings, todos aplicados: 1 critical de sanitização de caracteres de controle, 3 majors, 9 minors) → re-teste.
- `bats tests/cairn-status.bats`: 22/22. Suite completa: regressão zero.

## Deviations

- `/gsd:quick` exige ROADMAP.md; não existia no início (new-project foi interrompido pelo pivô do usuário). Trabalho correu rastreado pelo bd (CairnGo-4ju) com artefatos nesta pasta; STATE.md ganhou a linha do quick task retroativamente quando o roadmap do milestone v1.1 criou o arquivo.
- Decisão de superfície (usuário): board dentro do `/cairn:status` (sem comando `index`/`board` separado), visual kanban em colunas, um doc por comando.

## Artefatos

CONTEXT, PLAN, REVIEW (13 findings), research (cli-design, house-style, inventory dos 22 comandos) nesta pasta.
