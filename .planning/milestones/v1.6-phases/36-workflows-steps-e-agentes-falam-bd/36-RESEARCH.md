# Phase 36: Workflows, steps e agentes falam bd — Research

**Data:** 2026-08-11
**Método:** 5 frentes de pesquisa independentes, cada uma seguida de um cético que
re-mediu os números com comando próprio. Todo número abaixo traz o comando que o
produziu. O que o orquestrador re-verificou pessoalmente está marcado **[verificado]**;
o que veio de agente e não foi re-medido está marcado *(laudo)*.

> **Correção de laudo registrada:** o cético da frente 4 afirmou que 3 verbos chamados
> pelo vendorizado são recusados pelo binário. Re-medi: são **2**. `worktree set-baseref`
> responde exit 0 com payload correto — é subcommand do verbo `worktree`, não verbo
> próprio, e o cético o testou pela grafia pontuada que o contrato não declara. Laudo é
> hipótese, não veredito.

---

## 1. O achado que reordena a fase: a camada prompt não chama o binário

**[verificado]** Nenhum dos 169 arquivos vendorizados menciona o binário python:

```
grep -rl 'cairn-gsd\|cairn/scripts' cairn/gsd --include='*.md' | wc -l   → 0
```

O que existe são **34 blocos de preâmbulo shim** (8 nos workflows raiz, 8 nos agentes,
o resto em steps/modes), em duas variantes, todos declarando
`_GSD_SHIM_NAME="gsd-tools.cjs"` e definindo `gsd_run() { node "$GSD_TOOLS" "$@"; }`
após tentar ~20 caminhos de `gsd-core/bin/gsd-tools.cjs`, terminando em `exit 1`.

```
grep -rl '_GSD_SHIM_NAME=' cairn/gsd --include='*.md' | wc -l            → 34
grep -l  '_GSD_SHIM_NAME=' cairn/gsd/gsd-core/workflows/*.md | wc -l     → 8
grep -rl '_GSD_SHIM_NAME=' cairn/gsd/agents --include='*.md' | wc -l     → 8
```

Consequência que a fase precisa encarar de frente: **os testes das fases 33-35 provam o
binário, não o caminho executado.** O harness roda `$GSD = cairn-gsd.sh` (python); um
workflow rodando hoje resolveria `gsd-tools.cjs` e falaria markdown. O incidente
`current_phase 18` está morto no binário e vivo no caminho que o usuário executa. Trocar
o preâmbulo é, portanto, o **primeiro** trabalho da fase 36, não um detalhe de ADAPT-02:
antes disso, nenhuma outra edição desta fase tem efeito observável.

Duas variantes de preâmbulo *(laudo, hash por linha)*: 31 arquivos com a forma longa
(~4,5 KB, 20 ramos de caminho) e 3 com a curta (~880 B, 4 ramos). A forma nova precisa
resolver o binário do próprio repo — `cairn/scripts/cairn-gsd.sh` — e a proposta tem que
ser testada rodando, não só escrita.

---

## 2. A decisão ADAPT-01: preservar a composição

**[verificado]** O mecanismo existe e é real. `section_manifest` (com underscore — o
primeiro pesquisador procurou com hífen e concluiu que não havia mecanismo; o cético
derrubou) é um campo do bundle de init que gateia a leitura dos steps:

| Medida | Valor | Comando |
|---|---|---|
| workflows raiz / linhas | 8 / 6.502 | `find … -maxdepth 1 -name '*.md' \| xargs wc -l` |
| fragments sob `workflows/*/` | 42 / 2.585 linhas | `find … -mindepth 2 -name '*.md' \| xargs wc -l` |
| steps gatados por manifesto | 21 / 806 linhas | cruzamento id×glob (script python) |
| steps não gatados | 10 / 892 linhas | idem |
| gates literais no texto | 21 | `grep -rh 'If \`section_manifest\` is \`null\` or' \| wc -l` |
| chamadas `gsd_run`: raiz / steps / modes | 147 / 38 / 4 | regex canônica da fase 31 |
| chamadas dentro de steps: gatados / não | 10 / 28 | script python |
| `.planning/` citado: raiz / steps | 65 / 8 | `grep -rhoE '\.planning/'` |

**Preservar é a recomendação, e o motivo é medido, não estético.** Achatar exigiria
inlinar 21 arquivos (806 linhas) em 6 workflows raiz — +12,4% sobre as 6.502 linhas que
são lidas *sempre* — reescrever 21 marcadores `<!-- gsd:section -->` e resolver 2 leituras
aninhadas step→step. E o ganho de adaptação seria quase nulo: só 10 das 38 chamadas dos
steps estão nos arquivos gatados, e o estado em markdown está 65-vs-8 a favor da raiz.
O trabalho de adaptação mora nos 8 workflows raiz; os fragments são carona.

### O bug de tipo que veio junto

**[verificado]** O binário emite `section_manifest: []` em 6 sítios
(`grep -n 'section_manifest' cairn/scripts/cairn-gsd-init.py` → linhas 574, 583, 614,
786, 823, 856, todas `[]`), e 6 goldens congelam esse valor.

A camada prompt especifica dois valores: `null` (degradado — lê todos os steps, "the safe
superset", `execute-phase.md:92`) ou um objeto com `.included`/`.excluded`/`.read`. Uma
lista vazia não é nenhum dos dois. `debug.md:31` diz textualmente que *null e um included
vazio não são a mesma coisa*.

O cético fez uma ressalva justa: afirmar que `[]` **faz** os 21 steps serem pulados é
inferência, não medição — o gate é prosa lida por um modelo, que pode ler `[]` como
ausência. Mas o tipo está errado dos dois jeitos, e o custo de corrigir é ~6 linhas mais
6 goldens regravados. Fica como primeira tarefa barata da fase, com o valor correto
(`null`) declarado no contrato.

Preencher o manifesto de verdade (o ganho de contexto) é incremento separado: dos 21
marcadores, 10 dependem de flags que o handler já parseia e descarta e 5 de estado já
computado; sobram 3 predicados sem fonte. Não misturar com a correção de tipo.

---

## 3. O escopo real é maior que "8 workflows"

O roadmap orça a fase em 189 sítios de verbo e 129 de estado nos 8 workflows. **[verificado]**
A camada prompt não termina ali:

| Superfície | Arquivos | Chamadas `gsd_run` | Blocos shim |
|---|---|---|---|
| workflows (raiz + fragments) | 50 | 189 | 18 |
| agents | 16 | 65 | 8 |
| references | 80 | 18 | 1 *(laudo)* |

```
find cairn/gsd/agents -name '*.md' | wc -l                                    → 16
grep -rhoE 'gsd_run (query )?[a-z][a-z-]*(\.[a-z-]+)?' cairn/gsd/agents | wc -l → 65
grep -rhoE '…' cairn/gsd/gsd-core/references | wc -l                          → 18
grep -rhoE '(gsd-core/)?references/[a-z0-9-]+\.md' cairn/gsd/gsd-core/workflows | sort -u | wc -l → 40
```

Os workflows citam **40 arquivos de `references/` distintos**, e é dentro deles que vivem
os sítios mais delicados (ver §4). Um agente com preâmbulo shim próprio é um caminho de
execução independente: adaptar só os workflows deixa 8 agentes falando `gsd-tools.cjs`.

*(laudo, não re-medido)* A camada prompt **própria do cairn** (`cairn/commands`,
`cairn/skills`, `cairn/agents`: 44 arquivos) tem 40 menções a `.planning/` e zero chamadas
`gsd_run` — superfície diferente, decisão separada.

---

## 4. Os verbos que o universo não cobre

**[verificado]** Cruzando o que o vendorizado chama contra os 87 do contrato, **2 verbos
não existem no binário** — e ambos vivem em `references/` carregados por `execute-phase.md`:

| Verbo | Sítio | Tolerância no sítio | Exit do binário |
|---|---|---|---|
| `resolve-execution` | `references/execute-phase-quota-recovery.md:13` | **nenhuma** — a saída alimenta 5 `jq` seguidos | 2 (fora do universo) |
| `requirements.revert-phase` | `references/execute-phase-requirement-revert.md:5` | `>/dev/null 2>&1 \|\| true` | 2 (fora do universo) |

O primeiro é o que importa: é o caminho de recuperação de quota (troca de provider quando
o modelo estrangula), e o sítio consome o JSON sem rede de proteção. `requirements.revert-phase`
já é tolerante a falha por desenho upstream.

Terceiro caso, **corrigido do laudo**: `worktree set-baseref` funciona.

```
bash cairn/scripts/cairn-gsd.sh worktree set-baseref   → exit 0, {"changed":true,"baseRef":"head",…}
```

O que existe é um descompasso de grafia: `references/execute-phase-between-wave-reset.md:30`
chama `gsd_run query worktree.set-baseref`, grafia que o contrato não declara (o verbo é
`worktree`, subcommand `set-baseref`). O sítio tem `2>/dev/null || true`, então falha calada
— é edição de uma linha no reference, não implementação.

---

## 5. A fronteira fato-vs-documento, e onde ela é armadilha

O vocabulário está fixado desde a fase 34 (`phase`, `phase_status`, `plan`, `verification`,
`session`), e a regra é: fato vem do label projetado no bd, documento vem do arquivo.
Aplicá-la sítio a sítio nos workflows é o miolo de ADAPT-02/03/04.

Duas armadilhas de medição que os céticos expuseram e que o planejamento precisa herdar:

1. **`grep 'STATE.md'` não acha tudo.** Há 13 linhas *(laudo)* que referenciam o estado por
   variável (`${STATE_PATH}`, `{state_path}`, `state_raw`, `state_exists`) sem citar o nome
   do arquivo — cinco delas no mesmo padrão já classificado como leitura de fato. Quem
   inventariar por nome de arquivo vai declarar cobertura que não tem.
2. **`references/` ficou fora de toda medição do roadmap.** Exemplo concreto encontrado:
   `references/autonomous-smart-discuss.md:24` faz `cat .planning/STATE.md` — leitura
   mecânica de estado que não entrou em nenhuma conta.

*(laudo)* Total de menções a `.planning/` na camada prompt vendorizada: 224.

---

## 6. Bugs do binário que esta fase expõe (candidatos a correção barata)

**[verificado]** `section_manifest: []` (§2) — 6 sítios, 6 goldens.

*(laudo, alta confiança — vem com comando)* `--wave` está declarado em `bool_flags` no
handler `init.execute-phase`, mas `execute-phase.md:84-85` monta e passa `--wave <valor>`.
Medido: `query init.execute-phase 1 --wave 2` → exit 0, 48 chaves, nenhuma contendo "wave";
o valor é descartado e o `2` vira posicional extra. Insumo pela metade para preencher o
manifesto depois.

*(laudo)* 193 referências a `$HOME/.claude` / `~/.claude` na camada prompt — furo de
reprodutibilidade: editar o arquivo vendorizado não muda o comportamento nesses caminhos,
porque o runtime resolvido é outro.

---

## 7. O que isto muda no plano da fase

1. **Ordem invertida em relação ao roadmap:** o preâmbulo vem primeiro. Antes de ele
   apontar o binário do repo, nenhuma outra edição da fase tem efeito observável, e
   qualquer teste de ponta a ponta mede o runtime errado.
2. **Escopo a decidir com o usuário:** workflows apenas, ou workflows + agentes +
   os 40 references citados. Os números de cada opção estão em §3.
3. **ADAPT-01 tem resposta medida:** preservar a composição, corrigindo `[]` → `null`
   como tarefa barata; preencher o manifesto é incremento posterior, nunca no mesmo plano.
4. **ADAPT-05 ganha um terceiro item:** além de `intel api-surface` e `graphify`,
   `resolve-execution` precisa de decisão explícita (implementar, falha nomeada, ou cortar
   o caminho de recuperação de quota), porque o sítio não tolera falha.
5. **Fatiamento do barato ao caro continua válido** — fast e debug primeiro, execute-phase
   por último — mas agora com o preâmbulo como onda zero, comum a todos.

---

*Fase: 36-workflows-steps-e-agentes-falam-bd*
*Research: 2026-08-11 — 5 frentes, 5 céticos, 10 agentes, 0 erros*
