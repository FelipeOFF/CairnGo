---
phase: 22-non-tty-split-and-the-machine-contract
plan: "01"
subsystem: cairn-status
tags: [golden-file, machine-contract, bats, write-once]

requires:
  - phase: 20-group-model
    provides: "tests/fixtures/board-render/ e o padrão de referência byte a byte com prova de liveness"
provides:
  - "tests/fixtures/machine-contract/nontty-pre-split.txt — os bytes do não-TTY sem flag, capturados antes do split"
  - "capture.sh write-once: o único escritor, e recusa sobrescrever"
  - "dois testes em cairn-board-invariance.bats: os bytes, e a prova de que a comparação reprova"
affects: [22-02, 22-03, 22-04]

tech-stack:
  added: []
  patterns: ["referência em dois eixos independentes, com escritores diferentes"]

key-files:
  created:
    - tests/fixtures/machine-contract/capture.sh
    - tests/fixtures/machine-contract/nontty-pre-split.txt
  modified:
    - tests/cairn-board-invariance.bats

decisions:
  - "A referência mora fora de tests/fixtures/board-render/, porque aquele diretório é território do regenerate.sh"
  - "A captura é feita SEM flag nenhuma, nem --color=never — a ausência de flags é o que faz dela evidência do caminho não-TTY"
  - "capture.sh só aceita --force para refazer captura errada ANTES do split; depois dele o arquivo não é regenerável nem em princípio"

metrics:
  duration: 35min
  completed: 2026-08-06

requirements-completed: []
status: complete
---

# Phase 22 Plan 01: A referência do contrato de máquina Summary

**Os 332 bytes que o caminho não-TTY sem flag imprime hoje estão commitados,
capturados antes de uma linha de `cairn-status.py` se mover, presos por um teste
que uma mutação em `render_plain()` comprovadamente reprova — e guardados por um
escritor que se recusa a reescrevê-los.**

## O que foi capturado, e a prova de que é o que se pensava

```
tests/fixtures/machine-contract/nontty-pre-split.txt
  bytes: 332
  md5:   e98d3096656463236c2ed12a12be90e3
```

`cmp -s` contra `tests/fixtures/board-render/plain.txt`: **idênticos**. Quatro
linhas de comando (`--plain`, `--plain --color=never`, sem flag, e a referência
commitada na fase 20) produzem hoje um único md5, que é exatamente o acoplamento
que o `PIPE-02` vai desfazer.

A captura foi feita **sem flag nenhuma**, nem `--color=never`. Isso é deliberado e
está escrito no script: a ausência de flags é o que faz do arquivo evidência do
*caminho não-TTY*, e não de `--plain`. Que `--color=never` não moveria um byte
está medido acima — mas uma flag num lado e não no outro é como duas coisas que
precisam concordar começam a divergir.

## O achado que justifica o plano inteiro

`plain.txt` já existia, já era do "antes" (commit `784483e`, plano 20-01, sem
nenhum commit desde) e já estava presa por um teste. A pergunta honesta era: por
que capturar de novo?

Porque `plain.txt` **mora sob `regenerate.sh`**, e esse script reescreve os
**sete** arquivos numa passada só. Um executor futuro que mude o render humano e
regenere reescreve o contrato de máquina junto, no meio de sete arquivos
alterados, dentro de um commit — e o `--plain` perde a guarda sem que ninguém
tenha decidido isso. Não é hipótese: os planos 22-03 e 22-04 desta mesma fase
rodam o regenerador, de propósito, duas vezes.

O segundo eixo fecha esse buraco por construção. Nada regenera
`machine-contract/` junto com outra coisa, e `capture.sh` recusa sobrescrever:

```
$ bash tests/fixtures/machine-contract/capture.sh
capture.sh: .../nontty-pre-split.txt already exists — refusing to overwrite.
  This capture is write-once: the code path it recorded no longer
  exists after the Phase 22 split ...
exit=1
```

Os dois arquivos carregam bytes idênticos hoje. É redundância com razão.

## A quebra medida, no fonte

Backup por `cp` (nunca `git checkout --`), mutação em `render_plain()` trocando o
rótulo `DONE` por `CLOSED`, e a suíte rodada inteira:

| run | plano | ok | not ok | quais falharam |
| --- | --- | --- | --- | --- |
| antes | `1..11` | 11 | 0 | — |
| com a mutação | `1..11` | 9 | **2** | `6 the machine format renders the reference bytes`, `7 --plain still renders the pre-split machine bytes` |
| restaurado | `1..11` | 11 | 0 | — |

Os dois eixos reprovaram, e só eles: os dois testes de liveness continuaram
consistentes (eles exigem vermelho, e com a mutação seguem vermelhos), e os sete
renders humanos ficaram intactos — `render_plain()` não é lida por nenhum deles.

A restauração foi feita de `/tmp/status-orig-22-01.py` por `cp`, e conferida com
`git diff --quiet -- cairn/scripts/`.

## O que este plano não fez

**Não tocou uma linha de `cairn/scripts/`.** `git status` durante o plano inteiro
mostrou apenas `tests/cairn-board-invariance.bats` modificado e
`tests/fixtures/machine-contract/` novo. Um plano que instala a régua e move a
coisa medida no mesmo commit não instalou régua nenhuma.

**Não rodou a suíte inteira.** Rodou `tests/cairn-board-invariance.bats`, o único
arquivo que este plano toca, três vezes (antes, com a mutação, depois), com o TAP
em arquivo e o plano `1..11` conferido contra a soma de `ok` + `not ok` sobre o
log inteiro — não sobre a cauda.

## Detalhe de implementação que vale registrar

`diff_render_against_reference()` foi generalizada em `diff_against_reference()`
(recebe o caminho da referência) com duas fachadas: a de render, que acrescenta
`--color=never`, e a de máquina, que não acrescenta nada. **Uma única função de
comparação para as duas direções e os dois conjuntos** — o arquivo já escrevia o
argumento para os sete renders, e ele vale igual aqui: se um teste de liveness
tivesse um diff próprio, uma comparação viciada passaria os positivos por sempre
concordar e o liveness por rodar numa cópia honesta e privada.

`assert_reference_intact()` virou fachada de `assert_file_intact()`, que aceita
caminho, para que a captura ganhe as mesmas âncoras de conteúdo (`READY\tbrd-001`,
`MILESTONE\tv1.0`) — uma referência esvaziada casaria alegremente com um
`--plain` que quebrou e não imprimiu nada.

## Commits

| hash | mensagem |
| --- | --- |
| `7770632` | `test(22-01): a referência do contrato de máquina, gravada antes de mover o não-TTY` |

## Self-Check: PASSED

- `tests/fixtures/machine-contract/nontty-pre-split.txt` — FOUND (332 bytes)
- `tests/fixtures/machine-contract/capture.sh` — FOUND (executável)
- `tests/cairn-board-invariance.bats` — FOUND (11 `@test`, era 9)
- commit `7770632` — FOUND
