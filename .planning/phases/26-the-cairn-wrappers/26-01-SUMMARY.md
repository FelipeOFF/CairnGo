---
phase: 26-the-cairn-wrappers
plan: "01"
status: complete
requirements: [WRAP-02]
beads: [CairnGo-38j]
subsystem: cairn/scripts
tags: [wrappers, preflight, gsd-core, wrap-02]
provides:
  - "cairn-wrap preflight — a recusa nomeada quando o /gsd:* não está instalado"
  - "cairn-wrap list — os wrappers derivados do frontmatter no disco"
  - "/cairn:phase — o primeiro dos treze, com o relabel que impede o órfão"
key-files:
  created:
    - cairn/scripts/cairn-wrap.py
    - cairn/scripts/cairn-wrap.sh
    - cairn/commands/phase.md
    - tests/cairn-wrap.bats
---

# Phase 26 Plan 01: A fatia vertical — o preflight que recusa, e o primeiro wrapper

`/cairn:phase` existe, delega ao `/gsd:phase`, move os rótulos que um renumber
orfanaria — e se recusa a rodar, nomeando o que falta, quando o `/gsd:phase` não
está instalado.

## O que ficou pronto

**`cairn-wrap.py preflight <cmd>`** — a pergunta que nenhum wrapper respondia.
Dois códigos de saída, porque são dois fatos diferentes para quem depura:

| código | fato | mensagem |
|---|---|---|
| `5` | **não deu para olhar** — nenhuma superfície de comandos GSD encontrada | lista **cada** caminho tentado e por que cada um não serviu |
| `6` | **olhou e não está lá** | nomeia `/gsd:<cmd>`, o diretório, quantos comandos há nele, e o conserto |

Medido nesta máquina, os dois lados:

```
$ cairn-wrap.sh preflight phase
[cairn-wrap] ✓ /gsd:phase is installed (…/gsd-core/1.8.0/commands/gsd)   → 0

$ cairn-wrap.sh preflight banana
[cairn-wrap] error: /gsd:banana is not installed — /cairn:banana wraps it and cannot run.
  looked in: …/gsd-core/1.8.0/commands/gsd (71 command(s) found there)
  fix: claude plugin install gsd-core@cairngo, then /reload-plugins   → 6
```

**O 5 aqui não herda o "callers must NOT block on 5"** que o `CONVENTIONS.md`
registra para o `bd` no pre-push shim, e isso está escrito ao lado da constante:
lá o 5 é uma checagem opcional degradando; aqui o comando delegado **é o trabalho
todo**, e seguir em frente seria o exit-0-em-silêncio que o WRAP-02 proíbe.

**`cairn-wrap.py list`** — os wrappers saem do frontmatter no disco. Nenhum dos
treze nomes mora no `.py`; a única lista literal é o vocabulário fechado de
`wrap-family`, que é **validado** (família desconhecida é erro nomeado, com o
arquivo e o valor).

**`/cairn:phase`** — o caso mais forte do GSD-05, e o único cujo dano é
irreversível sem trabalho. O que ele acrescenta ao `/gsd:phase`: registra o
mapeamento `fase → issues` **antes** de delegar (depois o ROADMAP já não diz
quem era de quem), e move os rótulos pelo `cairn-relabel.sh renumber`, que
deep-merge o `metadata.gsd.phase` em vez de clobberar — coisa que um
`bd update --metadata` cru não faz.

## A medição que decidiu a descoberta

O gsd-core 1.8.0 põe os 71 comandos em **`commands/gsd/*.md`** — o subdiretório
`gsd/` é o que produz o namespace `/gsd:`. Procurar só `commands/*.md` acha
**zero** e faria **todo** preflight sair 6. Os dois são procurados, subdiretório
primeiro, e o porquê está em comentário no código. Esta é a diferença entre um
preflight que funciona e um que reprova tudo.

Ordem completa da descoberta: seam `CAIRN_GSD_COMMANDS_DIR` → `installed_plugins.json`
→ cache de plugins com o mesmo `_discovery_key` (linhagem antes de versão) que o
`cairn-capability.py:189` já mediu.

**Seam apontado para o nada é uso (2), não "não achei" (5).** Degradar ali
esconderia teste mal montado em vez de nomeá-lo.

## As provas por quebra — cada teste com a quebra que o deixa vermelho

Um teste que passaria com a feature removida não é prova. As três quebras foram
**aplicadas de verdade, medidas, e revertidas por cópia** (`cp` da original, nunca
`git checkout`):

| quebra aplicada | testes que ficaram vermelhos |
|---|---|
| `installed = True` — a checagem de existência deletada | 1 (a prova por ausência), 3 (superfície vazia), 6 (`--json`) |
| `wraps` por lista literal em vez do frontmatter | 7 (derivação), 8 (família), 9 (contrato) |
| `--claim` removido do `phase.md` | 9, **nomeando o arquivo** |

O par de testes 1+2 existe por isso: o 1 sozinho passaria contra um preflight que
sempre sai 6, e o 2 sozinho passaria contra um que sempre sai 0.

**Toda asserção de status é sobre o valor exato** — `-eq 6`, `-eq 5`, `-eq 2`,
`-eq 0`. Nenhum `-ne 0` no arquivo.

## O teste de contrato que vai crescer com a fase

O teste 9 varre `list --json` contra o `cairn/commands/` **real** e, para cada
wrapper, monta as agulhas **a partir do JSON** — nunca digitadas. Um wrapper que
delegue ao comando errado reprova ali. Seis exigências por arquivo: chamada do
preflight com o seu próprio `wraps`, `/gsd:<wraps>`, `bd update` + `--claim`,
`bd close`, o par de rótulos, o carimbo de metadata.

O teste 10 afirma a contagem **exata** (`length == 1`, hoje). Um `>=` esconderia
um wrapper perdido, que é o defeito desta fase.

## Desvios do plano

### 1. [Decisão de escopo] O subcomando `docs` entrou neste commit, não no do plano 02

O `26-01-PLAN.md` diz, literalmente, *"(`docs` é do plano 02 — não o escreva
aqui.)"*, e ele foi escrito junto. Registro em vez de esconder.

**O que isso NÃO comprometeu:** a restrição de ordem que importa para o WRAP-03 é
*o gerador existir antes dos doze wrappers chegarem*, e ela está intacta. E a
medição vermelha do plano 02 — o `docs --check` reprovando a página doente — foi
feita **antes de qualquer edição de documentação**, com a página exatamente como
estava:

```
$ cairn-wrap.sh docs --check --json          → exit 3
{ "changed": true,
  "orphan_pages": ["bookkeep"],
  "undocumented": ["config", "reconcile"],
  "wrappers": [] }
```

Os dois comandos que o levantamento à mão tinha achado (`config`, `reconcile`),
achados de novo pelo script, sem eu dizer os nomes a ele. O plano 02 herda essa
medição em vez de refazê-la.

**O que fica pendente para o plano 02:** os sete testes do `docs` (a prova por
acréscimo, `--check` 3 e 0, sobrevivência do que está fora dos marcadores,
idempotência por sha256 **e** mtime, a sobra nomeada, arquivo sem marcadores), e
o conserto da página.

## Verificação

- `bash cairn/scripts/cairn-test.sh --jobs 2 tests/cairn-wrap.bats` — **1..12
  anunciados, 12 executados, 12 `ok`, 0 `not ok`**.
- `preflight phase` → 0; `preflight banana` → 6; seam quebrado → 2; sem
  superfície (com `HOME` de fixture) → 5.
- `list --json` contra o `cairn/commands/` real → 1 wrapper, `phase`.

### A suíte inteira, e a anomalia da máquina

`bash cairn/scripts/cairn-test.sh --jobs 2 tests/` — **1..711 anunciados**, e o
resultado está registrado no `26-SUMMARY.md` da fase, porque a corrida foi
atravessada por uma anomalia que não é desta fase e que **não foi tocada**:

Medido com `ps`: além das três worktrees ativas (`phase-21`, `phase-24`,
`phase-26`), há uma corrida **da árvore principal** viva há **1 dia e ~12 horas**
(`-j 6`), com filhos parados a ~0% de CPU em `cairn-doctor.bats`,
`cairn-migrate.bats`, `cairn-reconcile*.bats` e `cairn-phase-model.bats`. É
exatamente a forma do travamento que a restrição `--jobs 2` existe para evitar.

**Não matei nada** — processo fora desta worktree não é meu para encerrar. Fica
relatado.

## Self-Check: PASSED

- `cairn/scripts/cairn-wrap.py` — existe
- `cairn/scripts/cairn-wrap.sh` — existe
- `cairn/commands/phase.md` — existe
- `tests/cairn-wrap.bats` — existe
- commit `a8e6512` — existe
