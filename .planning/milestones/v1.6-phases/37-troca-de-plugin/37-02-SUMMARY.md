---
phase: 37-troca-de-plugin
plan: 02
subsystem: doctor, init, capability
tags: [doctor, inversao, lineage, capability, init]
requires: [37-01]
provides: [check 10 invertido, init sem plugin externo, capability arquivada]
affects: [37-03 pin do doctor, phase-38 doctor limpo em repo novo]
tech_stack_added: []
patterns: [seam CAIRN_* para estado global, degradar para WARN nunca crash, ordem de decisão asserida]
key_files_created:
  - tests/cairn-doctor-lineage.bats
  - cairn/capability/ARCHIVED.md
key_files_modified:
  - cairn/scripts/cairn-doctor.py
  - cairn/scripts/cairn-capability.py
  - cairn/scripts/cairn-init.sh
  - cairn/commands/init.md
  - cairn/docs/commands/doctor.md
  - cairn/README.md
  - tests/cairn-doctor.bats
  - tests/cairn-init.bats
decisions: [D-03 sentido novo e ordem de decisão, D-04 arquivar não é deletar]
requirements: [PLUG-02, PLUG-03, PLUG-04]
status: complete
completed: 2026-08-12
---

# Phase 37 Plan 02: O doctor inverte o sentido Summary

O check 10 perguntava *"a capability cairn está registrada contra o gsd-core
instalado?"* e prescrevia **instalar** `gsd-core@cairngo`. Passou a perguntar
*"o runtime vendorizado está inteiro, e sobrou linhagem externa por limpar?"*,
com prescrição de **uninstall**. A inversão foi provada nas duas direções antes
de uma linha de implementação mudar.

## O oráculo bidirecional, e por que ele precisou de duas rodadas

Um check que valida o contrário do que validava é onde um teste que não morde
passa despercebido. `tests/cairn-doctor-lineage.bats` mede as duas direções:

| | Asserção | Contra o doctor antigo |
|---|---|---|
| A1 | sem linhagem externa + runtime vendorizado → `ok` | vermelho (dava `warn`, "no GSD binary found") |
| A2 | `gsd-core` instalado → `fail` com uninstall | vermelho (era `ok`) |
| A2b | 4.x instalada → `fail` com uninstall | vermelho (falhava, mas mandando **instalar**) |
| A2c | as duas juntas → as duas nomeadas | vermelho |
| A3 | runtime vendorizado incompleto → `fail` acusando o plugin | vermelho (o doctor nem olhava para lá) |
| A4 | resíduo em `.gsd/` → `warn` com `rm -rf` nomeado | vermelho |
| A4b | ordem: linhagem externa vence resíduo, `fail` não vira `warn` | vermelho |
| B1 | `claude plugin install gsd-core@cairngo` não sai mais | **verde na 1ª rodada — e isso era defeito do teste** |
| B2 | nenhum caminho manda re-rodar `/cairn:init` | **verde na 1ª rodada — idem** |

**B1 e B2 saíram verdes contra o doctor antigo, e isso não era prova — era um
fixture que não chegava ao caminho medido.** Com `HOME` limpo o doctor antigo
parava em `no GSD binary found` e nunca emitia a prescrição velha. Um stub de
binário GSD (nas duas formas: 4.x, e core respondendo com lista de capabilities
vazia) faz o caminho antigo ser realmente percorrido — e só então as duas ficam
vermelhas. **9/9 vermelhas** foi o baseline registrado antes da implementação;
9/9 verdes depois.

## Números

| Suíte | Antes | Depois |
|---|---|---|
| `tests/cairn-doctor-lineage.bats` (novo) | **9/9 vermelhas** | **9/9 verdes** |
| `tests/cairn-doctor.bats` | 131 testes | **125 testes, 125 ok, exit 0** |
| `tests/cairn-init.bats` | 13 testes, 3 novas vermelhas + 1 controle verde | **17/17 verdes** |
| `tests/capability.bats` + `tests/cairn-capability.bats` | verdes | verdes (controle: arquivar não quebrou quem lê o bundle) |
| `tests/cairn-command-surfaces.bats` | verde | verde (o id `gsd-capability` foi preservado de propósito) |

## O check novo

Ordem de decisão, e ela é load-bearing — asserida por A4b:

1. **runtime vendorizado incompleto → FAIL.** Defeito do *install*, não do
   ambiente, e a mensagem diz isso: nenhum plugin externo supre. Primeiro
   porque nenhuma afirmação sobre o ambiente vale enquanto o próprio plugin
   está quebrado.
2. **linhagem externa instalada → FAIL**, nomeando cada id, com
   `claude plugin uninstall <id>` + `/reload-plugins`.
3. **resíduo em `.gsd/` → WARN** com `rm -rf` nomeado. Por último de propósito:
   uma máquina que migrou tem **as duas coisas**, e avaliar resíduo primeiro
   reportaria como aviso o achado que exige ação.

Resíduo nunca FAIL, pela razão que os checks 8 e 14 já registram: resíduo é
atrito, não inconsistência de estado, e exit 7 gasto com atrito para de
significar alguma coisa. O doctor **nomeia** o fix; quem apaga é a pessoa.

Toda leitura é delegada: `vendored_runtime_report()` lê o `MANIFEST.json` que a
fase 32 derivou, `external_gsd_lineages()` chama `cairn-capability.py`, que já é
dono das regras de linhagem. Falha em qualquer um degrada para WARN com a razão
— a forma de `check_lease_stale()`, nunca um crash.

## Desvios do plano

**[Rule 3 — bloqueio] `cairn-capability.py` não expunha `installed_gsd` quando
nenhum binário GSD era descoberto**
- **Encontrado em:** Task 2, com A2/A2b/A2c/A4b ainda vermelhas depois da
  implementação.
- **Problema:** `detect --json` curto-circuita em `lineage: absent` e omite o
  campo. O doctor ficava cego exatamente para a máquina que precisa acusar: uma
  com `gsd-core` instalado e nenhum binário no PATH.
- **Correção, na origem:** o campo passou a ser reportado também nesse caminho.
  A justificativa é semântica, não conveniência — **se um plugin está instalado
  é fato independente de haver binário no PATH**, porque a superfície do plugin
  é markdown e responde `/gsd:*` dentro do Claude Code do mesmo jeito.

**[Rule 2 — funcionalidade crítica ausente] o seam `CAIRN_INSTALLED_PLUGINS`**
- **Encontrado em:** Task 2, ao medir o que a inversão faria com a suíte.
- **Problema:** o check lê estado **global**, e esta máquina de desenvolvimento
  tem `gsd-core@cairngo` instalado. Sem seam, o check 10 viraria FAIL em todo
  fixture e a suíte inteira passaria a depender da lista de plugins de quem
  roda — a mesma classe de defeito que `CAIRN_GSD_BIN` já existia para evitar.
- **Correção:** seam na convenção `CAIRN_*` da casa, honrado por
  `installed_gsd_plugins()`, com a medição escrita na docstring.

## Seis testes removidos, com a razão de cada um escrita

Saíram de `cairn-doctor.bats` porque descreviam a **pergunta antiga**, não
porque regrediram. Removê-los em silêncio apagaria a memória da inversão, então
a nota ficou no lugar deles:

| Teste | Por que não tem tradução |
|---|---|
| *the 4.x lineage fails the doctor* | ainda falha, mas exigia `claude plugin install gsd-core@cairngo` na saída — a frase que B1 agora proíbe |
| *gsd-core without a registered capability fails* | registro de capability deixou de ser o que o check mede |
| *a staged bundle missing its gate script fails* | o bundle staged hoje é resíduo, e resíduo é WARN (A4) |
| *no GSD binary at all warns* | a ausência de binário virou **estado esperado**; A1 asserta isso como `ok` |
| *an unloadable gsd-core manifest fails* | o defeito é do plugin upstream que cairn não instala mais; se estiver instalado, o check já falha antes pedindo uninstall |
| *two GSD lineages installed at once* | agora **uma** já basta para falhar; o caso das duas virou A2c, com a asserção de que são nomeadas intacta |

## Premissas que a medição contradisse

1. **"O doctor lê o ambiente, então o teste é do ambiente."** Era o contrário:
   sem seam, o teste vira refém do ambiente. A suíte teria ficado vermelha por
   um `gsd-core` instalado na máquina de quem roda — e verde na CI, que é o
   pior dos dois mundos.
2. **"A ausência de binário GSD é sinal ambíguo."** Era, enquanto o GSD morava
   fora. Depois da vendorização é o estado **esperado**, e o teste que a tratava
   como `warn` virou o teste que a trata como `ok`.
3. **`bats -j` não resolve nome de `@test` com `í` acentuado.** Quatro dos nove
   testes viraram `unknown test name` e **não rodaram**, com a suíte ainda
   saindo 1 pelos outros — um teste que não roda parece ausência de problema. Os
   títulos passaram a evitar o caractere, com a nota no cabeçalho do arquivo.

## D-04 aplicado: arquivar não é deletar

`cairn/capability/` continua no disco, com `ARCHIVED.md` registrando desde
quando, por quê, o que substituiu cada uma das cinco contributions, e o que a
remoção física cascatearia (`cairn-capability.py`, o check 15, duas suítes
bats). A remoção está em `deferred-items.md`, não em silêncio.

## Commits

| Hash | Mensagem |
|---|---|
| `54283c4` | test(37-02): o oráculo bidirecional da inversão do check 10, 9/9 vermelho antes |
| `fcafc31` | feat(37-02): o check 10 inverte o sentido — valida o vendorizado, acusa o externo |

## Self-Check: PASSED
