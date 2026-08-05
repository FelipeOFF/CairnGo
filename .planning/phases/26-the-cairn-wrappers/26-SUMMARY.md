---
phase: 26-the-cairn-wrappers
status: complete
requirements: [WRAP-01, WRAP-02, WRAP-03]
beads: [CairnGo-9xy, CairnGo-38j, CairnGo-5mu]
plans: 3
subsystem: cairn
tags: [wrappers, gsd-05, preflight, derived-docs, drift]
provides:
  - "os treze wrappers /cairn:* decididos no GSD-05, construídos e testados"
  - "cairn-wrap preflight — a recusa nomeada quando o /gsd:* não está instalado"
  - "cairn-wrap docs — a documentação como vista do disco, com --check na suíte"
---

# Phase 26: The cairn wrappers — Summary

Os treze wrappers que o GSD-05 decidiu em 2026-07-28 e nunca foram construídos
existem. Um wrapper cujo `/gsd:*` sumiu **para e nomeia o que falta**. E a lista
deles na documentação é **derivada do disco** — provado acrescentando doze
wrappers e vendo a página crescer sozinha.

## Antes de tudo: o bloqueio anunciado desta fase era falso, e foi medido

O `/cairn:status` reporta a fase 26 como *"waits on phase 9"*. **Medido nesta
worktree: `bd blocked` devolve vazio** (`✨ No blocked issues`), e o `ROADMAP.md`
§ Phase 26 diz `**Depende de:** nada`.

A mecânica está localizada, e é o **FIX-04**, conserto já enfileirado para a
fase 25 — as duas metades incidindo sobre a mesma aresta:

- `bd show CairnGo-9xy` traz `DISCOVERED FROM ◊ ✓ CairnGo-k21`. A aresta é
  `discovered-from`, que o `/cairn:quick` documenta como procedência **que não
  bloqueia** (`commands/quick.md:28`, *"records provenance without blocking"*).
- `cairn-status.py:1002` `dep_target_ids()` coleta `depends_on_id` de toda aresta
  **sem olhar o tipo**.
- `CairnGo-k21` é da fase 9, milestone v1.2 **arquivado**; o filtro de "já
  concluída" roda contra as fases feitas do ciclo corrente, do qual uma fase
  arquivada nunca faz parte.

Esta fase **não** consertou o FIX-04 — é da fase 25, e mexer no `cairn-status.py`
aqui colidiria com ela.

## O que ficou pronto

**`cairn/scripts/cairn-wrap.py`** (+ `.sh` + `tests/cairn-wrap.bats`), três
subcomandos, um por requisito:

| subcomando | requisito | o que faz |
|---|---|---|
| `preflight <cmd>` | WRAP-02 | o `/gsd:<cmd>` está instalado nesta máquina? |
| `list [--json]` | WRAP-01 | enumera os wrappers do frontmatter **no disco** |
| `docs [--check]` | WRAP-03 | regenera o bloco derivado na documentação |

**Os treze wrappers**, em três famílias derivadas do que o GSD-05 escreveu que
cada comando faz: `phase` (9), `structural` (1 — o `phase`), `milestone` (3).

## Os dois critérios que eram fáceis de fingir

### WRAP-02 — provado escondendo o comando, não pelo caminho feliz

Dois códigos, porque são dois fatos:

| código | fato |
|---|---|
| `5` | **não deu para olhar** — nenhuma superfície GSD encontrada; a mensagem lista **cada** caminho tentado e por que não serviu |
| `6` | **olhou e não está lá** — nomeia `/gsd:<cmd>`, o diretório, quantos comandos há nele, e o conserto |

O teste monta uma superfície de fixture **sem** o comando e afirma `[ "$status"
-eq 6 ]` — valor exato. **Nenhuma asserção de status no arquivo usa negação.**

O 5 aqui **não herda** o *"callers must NOT block on 5"* que o `CONVENTIONS.md`
registra para o `bd` no pre-push shim, e isso está em comentário ao lado da
constante: lá o 5 é checagem opcional degradando; aqui o comando delegado **é o
trabalho todo**.

**A quebra, aplicada de verdade:** `installed = True` (checagem deletada) deixa
os testes 1, 3 e 6 vermelhos. E o teste 11 liga o WRAP-02 sobre o conjunto
inteiro: `preflight` sai 0 para os treze nesta máquina — não "a checagem
existe", mas "ela passa para todos".

### WRAP-03 — a lista é derivada, e a prova é por acréscimo

**A página já estava mentindo, medido antes de qualquer edição:**

```
$ cairn-wrap.sh docs --check --json                → exit 3
{ "undocumented": ["config", "reconcile"],
  "orphan_pages": ["bookkeep"],
  "wrappers": [] }
```

`cairn/docs/commands.md` dizia **"22 in total"**, linkava **23** páginas, e
`cairn/commands/` tinha **25** comandos. `/cairn:config` e `/cairn:reconcile`
existiam, funcionavam, e não apareciam em lugar nenhum da página que existe para
listá-los. O script achou os mesmos dois sem que eu lhe dissesse os nomes.

**A prova em campo**, no plano 03: o gerador nasceu com **um** wrapper; os outros
doze chegaram depois.

```
$ cairn-wrap.sh docs --check     → exit 3, 16 linhas '+', as 12 novas
$ cairn-wrap.sh docs             → 13 wrapper(s)
$ diff (fora dos marcadores, antes/depois)  → idêntico byte a byte
```

**Quebra medida:** trocar a tabela por lista literal deixa os testes 14 e 15
vermelhos.

**A sobra é nomeada, não escondida** — três formas de a página mentir, cada uma
com aviso próprio dentro do bloco, e cada aviso some sozinho quando a lacuna
fecha:

| aviso | o que pega |
|---|---|
| `⚠ Not documented` | comando sem linha em lugar nenhum — como `config` e `reconcile` estavam |
| `⚠ Missing page` | linha cujo link aponta para página inexistente — o gerador **sabe produzir** isso, escrevendo uma linha por wrapper |
| `⚠ Orphan page` | página que documenta comando nenhum — `bookkeep.md`, que continua visível de propósito |

## O que a fase encontrou e consertou

**Precedente que ela repetiria se fosse escrita à mão:**
`cairn/docs/commands/doctor.md` afirmava *"fifteen checks in total"* com
**dezesseis** registradas e sem entrada para duas delas; corrigido **à mão** em
`8d3db19`, dois dias antes desta fase. O conserto manual é o que garante a
próxima deriva.

**Três defeitos medidos, consertados:** o total escrito à mão saiu (e um teste
reprova a reintrodução de `N in total` fora do bloco); `/cairn:config` e
`/cairn:reconcile` ganharam linha e página.

**Um quarto, achado ao atualizar o `gsd-core-commands.md`:** re-derivando com a
receita que a própria página publica — 71 comandos, **31** referenciados (era
18), **40** sem referência. E `18 + 54 = 72`, um a mais que os 71 que existem:
`config` estava **dos dois lados do corte**, porque `cairn/commands/config.md` já
citava `/gsd:config`. Uma página sobre contagem, pega contando errado. Corrigido
por escrito, com a distinção que faltava.

## Deviations

Cada plano tem a sua seção; o resumo:

1. **`docs` entrou no commit do plano 01**, não no do 02 — registrado, com a
   restrição de ordem que importava (gerador antes dos doze) intacta, e a
   medição vermelha feita antes de qualquer edição.
2. **O teste do total escrito à mão pegou a mim mesmo**, porque a prosa nova
   *citava* o defeito. Afrouxar o guarda tiraria os dentes do único teste que
   pega a reintrodução; a frase foi reescrita.
3. **`missing_pages` (Rule 2)** — treze links para páginas inexistentes é a
   mesma mentira em outra forma, e produzida por esta ferramenta.
4. **`bookkeep.md` continua órfã e visível** — decisão, não mecânica; declarado
   no CONTEXT § Deferred.

## Verificação

| verificação | resultado |
|---|---|
| `cairn-test.sh --jobs 2 tests/cairn-wrap.bats` | 1..23 anunciados, **23 executados, 23 `ok`, 0 `not ok`** |
| `list --json` | **13** wrappers, conjunto de `wraps` exatamente o do GSD-05 |
| `preflight` × 13 | **0** para todos, nesta máquina |
| `docs --check` | **0**; `undocumented` e `missing_pages` vazios |
| suíte inteira, `--jobs 2` | **ver abaixo** |

### A suíte inteira, e a anomalia da máquina — anunciado versus executado

**Primeira corrida (plano 01):** anunciou `1..711`, **executou 198**, `0 not ok`,
e o bats avisou: `# bats warning: Executed 198 instead of expected 711 tests`.
**Isso não é suíte verde** — é suíte interrompida, e contá-la como verde seria
exatamente a leitura de saída truncada que esta casa proíbe. A corrida foi
terminada junto com o processo que a vigiava.

**Corrida final:** ver a linha `SUITE-FINAL` abaixo.

**A anomalia, medida com `ps` e não tocada:** além das três worktrees ativas
(`phase-21`, `phase-24`, `phase-26`), havia uma corrida **da árvore principal**
viva há **1 dia e ~12 horas** (`-j 6`), com filhos a ~0% de CPU parados em
`cairn-doctor.bats`, `cairn-migrate.bats`, `cairn-reconcile*.bats` e
`cairn-phase-model.bats`. É a forma exata do travamento que a restrição
`--jobs 2` existe para evitar, e é o que faz uma corrida completa levar mais de
uma hora nesta máquina. **Não matei nada** — processo fora desta worktree não é
meu para encerrar. Fica relatado.

<!-- SUITE-FINAL -->

## Commits

| commit | o quê |
|---|---|
| `b356d17` | contexto da fase, e a prova de que o bloqueio anunciado é falso |
| `a8e6512` | `cairn-wrap preflight`/`list` + `/cairn:phase` |
| `153e31b` | `docs` derivada, e a página consertada |
| `3df4038` | a família de fase — nove wrappers |
| `8aa5453` | a família de milestone — três wrappers |
| `6c5fe1a` | a página ganha doze linhas sem ninguém escrever prosa |

## Self-Check: PASSED

- `cairn/scripts/cairn-wrap.py` e `.sh` — existem
- 13 arquivos em `cairn/commands/` com `wraps:` — existem
- 13 páginas em `cairn/docs/commands/` — existem
- `tests/cairn-wrap.bats` — existe, 23 testes
- Os seis commits acima — existem
