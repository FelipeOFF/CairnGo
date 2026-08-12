# Phase 37: A troca de plugin, única e curta - Context

**Mapeado:** 2026-08-12 (branch `phase/37-troca-de-plugin`, base `9605dbd`, árvore limpa)
**Requisitos:** PLUG-01 … PLUG-05
**Issues bd:** `CairnGo-l069` (01), `CairnGo-rt4j` (02), `CairnGo-qebd` (03), `CairnGo-h6sp` (04), `CairnGo-xy2d` (05)
**Research durante o planejamento:** não precisa (decisão do ROADMAP). O insumo é
`.planning/research/v1.6-transplante-gsd.md` §2.1/§3/§G, já escrito.

---

## Phase Boundary

A fase é **uma chave que vira de uma vez**. A janela em que `/gsd:*` velho (markdown,
cache 1.8.0) e `/cairn:*` novo (bd) coexistem é a classe de defeito que o v1.5 inteiro
caçou; diluir a troca em duas fases recria a janela. Por isso: 3 planos, 3 ondas, e
nenhum deles entrega meia troca.

**Entra:** o `gsd-core` sai do `marketplace.json` e das `dependencies` do `plugin.json`;
os 13 wrappers formais deixam de delegar para fora; `cairn-wrap.py preflight` resolve
contra o runtime vendorizado do próprio plugin; o check 10 do doctor inverte o sentido;
`cairn-init.sh` perde a recomendação do plugin externo; a capability em `.gsd/` é
arquivada com fix de limpeza; a migração vira capítulo de `gsd-core-migration.md`.

**Não entra:** vendorizar os 12 workflows upstream que a fase 32 deixou fora do fecho
(ver D-01); deletar `cairn/capability/` (ver D-04); a cobertura bats por verbo e o fluxo
ponta-a-ponta num repositório limpo — isso é a fase 38.

**Garantia repetida do research, e ela é asserção, não promessa:** nada em `.planning/`
nem em `.beads/` muda. É troca de plugin, não migração de dados. O plano 03 prova isso
com um oráculo de diff, não com uma frase.

---

## Implementation Decisions

### O estado medido que decide tudo (2026-08-12)

| Medição | Comando | Valor |
|---|---|---|
| wrappers formais | `grep -l '^wraps:' cairn/commands/*.md \| wc -l` | **13** |
| commands vendorizados | `ls cairn/gsd/commands/gsd/` | **8** (autonomous, debug, discuss-phase, execute-phase, fast, plan-phase, quick, verify-work) |
| dos 13, com contrapartida vendorizada | cruzamento | **1** — `discuss-phase` |
| dos 13, sem contrapartida | cruzamento | **12** |
| cache do clone upstream no worktree | `ls .cairn/cache/` | **ausente** (não versionado) |
| blob do doctor (pin da 35) | `git hash-object cairn/scripts/cairn-doctor.py` | `94e26233…`, 4042 linhas |

A terceira linha é o fato que governa a fase inteira: **12 dos 13 wrappers delegam para
comandos que o plugin não carrega.** Vendorizá-los agora é impossível offline (o cache
não está aqui) e seria errado mesmo com rede: a fase 36 adaptou 8 workflows a bd em 7
planos, e vendorizar prompt não-adaptado é exatamente a coexistência que esta fase existe
para fechar.

### D-01 — Claude's Discretion: o que "implementação direta" significa para cada um dos 13

Três caminhos foram pesados. **Vendorizar os 12** está fora (medição acima). **Aposentar
os 12** é a opção destrutiva e irreversível, e o ROADMAP pediu implementação direta, nunca
remoção. Fica a terceira, que é a conservadora: **a delegação morre, a implementação passa
a ser declarada, e onde ela é o próprio prompt isso fica escrito no frontmatter.**

- O frontmatter `wraps:` **sobrevive** com o valor intacto — ele agora nomeia o *verbo GSD
  que este comando implementa*, não o comando externo para onde ele delega. Preservar a
  chave preserva `cairn-wrap.py list`/`docs` e a derivação de `cairn/docs/commands.md`,
  que é o antídoto contra a lista tipada à mão. Renomear a chave custaria ~15 testes por
  nada.
- Uma chave nova, `implementation:`, com **vocabulário fechado** `vendored` | `inline`,
  diz **onde** a implementação vive. `vendored` → `discuss-phase` (1). `inline` → os
  outros 12.
- Um comando `implementation: vendored` mantém o passo de preflight, agora resolvido
  **dentro do plugin**. Um comando `implementation: inline` **perde o passo de preflight**
  — não há nada externo para checar — e seu passo "Run `/gsd:X`" vira o **contrato do
  entregável**: qual arquivo produzir, onde, com quais seções, e qual decisão registrar.

**Teto conhecido, e ele fica escrito no SUMMARY, não escondido:** os 12 contratos inline
são mais finos que os workflows upstream que substituem. É regressão de profundidade de
prompt, aceita conscientemente em troca de fechar a janela de coexistência. Quem mede isso
é o gate de paridade da fase 38, e o SUMMARY do plano 01 nomeia os 12 por nome para que a
38 não precise redescobri-los.

### D-02 — Claude's Discretion: `cairn-wrap.py preflight` resolve, não é aposentado

O ROADMAP ofereceu "resolve preflight contra os commands do próprio plugin **ou** aposenta
o subcomando". Escolha: **resolve**. Aposentar apaga uma guarda de recusa e seus testes, e
a razão de ela existir (`attempting is not running`, o `|| echo "capability install
skipped"` que engoliu um erro por semanas) não mudou de lugar — só mudou de alvo.

`find_gsd_command_dir()` deixa de varrer `installed_plugins.json` e o cache do marketplace
e passa a resolver, nesta ordem: `${CLAUDE_PLUGIN_ROOT}/gsd/commands/gsd`, depois
`${CLAUDE_PLUGIN_ROOT}/gsd/gsd-core/workflows`, com o fallback relativo à raiz do repo
quando `CLAUDE_PLUGIN_ROOT` não está setado. O seam `CAIRN_GSD_COMMANDS_DIR` **fica**:
ele é o que faz o teste não depender do cache de plugins de quem roda.

**A guarda continua mordendo:** contra o alvo novo, `preflight spec-phase` sai 6 — porque
o plugin não carrega `spec-phase`. É por isso que os 12 `inline` deixam de chamar preflight;
chamá-lo seria declarar delegação que não existe. Um preflight que não pode falhar seria o
mesmo defeito do gate vazio que `cairn-capability.py` documenta.

### D-03 — Claude's Discretion: o sentido novo do check 10, e o oráculo bidirecional

O check 10 hoje pergunta *"a capability cairn está registrada contra o gsd-core instalado?"*
e trata `gsd` 4.x como FAIL com prescrição de **instalar** `gsd-core@cairngo`. Depois da
troca, essa pergunta está de cabeça para baixo: quem responde `/gsd:*` deve ser o runtime
vendorizado, e **qualquer** linhagem externa instalada (`gsd-core@cairngo` **ou** `gsd`
4.x) é achado com prescrição de **uninstall**.

O check novo, id mantido (`gsd-capability` continua sendo o id que a tabela de roteamento
conhece — trocá-lo quebraria o teste 106 de `cairn-command-surfaces.bats` sem ganho):

| Estado | Verdict | Detalhe |
|---|---|---|
| runtime vendorizado íntegro, nenhuma linhagem externa | `ok` | nomeia o manifesto e a contagem de arquivos conferida |
| runtime vendorizado ausente/incompleto | `fail` | é o plugin quebrado, não o ambiente |
| linhagem externa instalada (`gsd-core` ou `gsd` 4.x) | `fail` | prescrição `claude plugin uninstall <nome>@<marketplace>` + `/reload-plugins` |
| resíduo em `.gsd/capabilities/cairn` ou `.gsd-capabilities.json` | `warn` | fix de limpeza; nunca FAIL, nunca deleta sozinho |

**Cuidado exigido pelo usuário, e ele é a razão do plano 02 existir sozinho:** um check que
valida o contrário do que validava é onde um teste que não morde passa despercebido. O
plano 02 prova as duas direções antes de trocar uma linha de implementação:
1. **a asserção nova fica vermelha contra o estado antigo** (doctor pré-conversão, fixture
   novo → falha);
2. **a asserção antiga ficaria vermelha contra o estado novo** (o fixture legado que hoje
   dá FAIL com "instale gsd-core" deve deixar de produzir esse texto).

Sem as duas, a inversão não está medida.

### D-04 — Claude's Discretion: "arquivada" não é "deletada"

`cairn/capability/` **não é removido do disco nesta fase.** Removê-lo cascateia em
`cairn-capability.py`, no check 15 (`release-versions`, que lê
`cairn/capability/capability.json` como eixo semver próprio), em `tests/capability.bats` e
em `tests/cairn-capability.bats` — quatro frentes por um ganho estético, na fase em que a
chave já está virando.

Arquivar, aqui, é: (a) o bundle ganha um `ARCHIVED.md` dizendo que não há mais host
externo, desde quando e por quê; (b) `cairn-init.sh` para de instalá-lo; (c) o doctor para
de exigir registro e passa a acusar resíduo. A remoção física é candidata a uma fase
posterior e entra em `deferred-items.md`, não em silêncio.

### D-05 — Claude's Discretion: `cairn/commands/gsd.md` sobrevive como passthrough

O research já previu ("pode sobrar como passthrough de compatibilidade"). Fica, com o texto
ajustado para dizer que ele endereça um GSD externo que o cairn **não** requer mais — é a
saída para quem tem o plugin instalado por outro motivo. Sem ele, quem depende de um
comando dos 54 não-wrapped fica sem rota nenhuma.

### D-06 — Claude's Discretion: janelas quebradas herdadas entram no plano 03

Dois itens de `36/deferred-items.md` pertencem a esta fase por nome:
- o pin de baseline do doctor em `tests/cairn-gsd.bats` (o próprio teste diz "a 37");
- a linha de roteamento de `export-identity` em `cairn/docs/commands/doctor.md`, que deixa
  o teste 54 de `cairn-command-surfaces.bats` vermelho.

O pin **só** é atualizado depois que o plano 02 muda o doctor, com o blob novo e a razão
escrita — nunca "para o teste passar".

---

## Canonical References

- `.planning/ROADMAP.md` §Phase 37 — o card e o goal.
- `.planning/REQUIREMENTS.md:71-75` — PLUG-01 … PLUG-05.
- `.planning/research/v1.6-transplante-gsd.md:145-157` — a superfície medida (314
  ocorrências de `/gsd:` em 29 commands), os quatro riscos da remoção (a-d) e os passos de
  migração DOCTOR/INIT/WRAP/DOCS.
- `cairn/docs/gsd-core-migration.md` — o precedente: a entrada `gsd` 4.x saiu na v1.4 e o
  documento já tem a forma do capítulo ("Do I need to do anything?", "The old entry is
  gone", "Nothing in `.planning/` or `.beads/` changes").
- `cairn/docs/gsd-core-commands.md` — a decisão GSD-05 e a tabela dos 13.
- `.planning/phases/36-*/36-PATTERNS.md` — os padrões da casa herdados (bloco por
  marcador, `--check` com diff, write-only-when-changed, oráculo tabular com controle
  negativo).

---

## Existing Code Insights

### Ativos reusáveis

- `cairn-wrap.py:548-599` `replace_block()` — bloco por marcador, idempotente. É o que
  regenera `cairn/docs/commands.md`; a mudança de frontmatter passa por ele, não por mão.
- `cairn-capability.py:189` `_discovery_key()` — a regra "linhagem supera versão" que o
  doctor herda para detectar **qual** externo está instalado.
- `cairn-doctor.py` `check_lease_stale()` — a forma de degradar (`subprocess` falhou →
  WARN com detalhe, nunca crash) que o check 10 novo copia.
- `tests/cairn-doctor.bats:81` `wire_capability_ok()` — o fixture que já monta um GSD
  falso; é ele que vira o controle negativo da inversão.

### Padrões estabelecidos que valem aqui

- Oráculo tabular com controle negativo (`tests/cairn-vendoring.bats:422` `assert_cut_holds`).
- Exit codes nomeados `EXIT_*`, python3 só stdlib, sem type hints, sem dataclasses.
- Docstring de módulo como especificação canônica, registrando **medido vs. assumido**.
- Runner: `bash cairn/scripts/cairn-test.sh --jobs 8 tests/<arquivo>.bats`, exit capturado
  por arquivo. Nunca `bats` cru, nunca a suíte inteira.

### Pontos de integração

`marketplace.json` (raiz) ↔ `cairn/.claude-plugin/plugin.json` ↔ check 15
(`release-versions`) — os carregadores de versão precisam continuar concordando depois da
remoção da entrada `gsd-core`; o check 15 lê `metadata.version` do marketplace, não a lista
de plugins, então a remoção não o toca. Confirmado por leitura antes de planejar.

---

## Ondas

| Onda | Plano | Requisitos | Por que nesta ordem |
|---|---|---|---|
| 1 | `37-01` A troca: o plugin fica autocontido | PLUG-01, parte de PLUG-03 | Nada depende dele, e ele é o que remove a dependência externa |
| 2 | `37-02` O doctor inverte o sentido | PLUG-02, PLUG-04, parte de PLUG-03 | O check novo valida o mundo que o plano 01 criou |
| 3 | `37-03` A migração escrita e a escrituração | PLUG-05 | Documenta os dois, e atualiza o pin do doctor que o 02 moveu |

---

## Deferred Ideas

- Remoção física de `cairn/capability/` (D-04).
- Decisão de vendorizar ou descartar os 54 comandos não-wrapped de
  `gsd-core-commands.md` — a fase 38 mede a paridade e decide com dado.
- Aprofundar os 12 contratos inline até a profundidade dos workflows upstream (D-01).
