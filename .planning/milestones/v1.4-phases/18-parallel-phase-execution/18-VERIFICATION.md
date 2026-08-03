---
phase: 18-parallel-phase-execution
verified: 2026-08-01T03:52:16Z
status: gaps_found
score: 4/5 must-haves verified
behavior_unverified: 1
overrides_applied: 0
gaps:
  - truth: "A reconciliação nomeia arquivo E LINHA nos dois casos — edição convergente e conflito de merge (18-CONTEXT.md D-02, Claude's Discretion, linha 120)"
    status: partial
    reason: >-
      A edição convergente é reportada com arquivo e linha (`base_line`). O
      conflito de merge é reportado APENAS com o arquivo — não há linha nem no
      texto humano nem no JSON. O 18-02-PLAN.md:21 reescreveu o must-have como
      "reportado com o arquivo", estreitando a D-02 sem registrar o
      estreitamento como desvio; o 18-04 então reinstalou a promessa forte na
      prosa entregue. Resultado medido: `cairn/commands/autonomous.md:224-225`
      diz ao operador que o relatório carrega "file and line of every conflict
      and every convergent edit", e o script entregue não carrega a linha do
      conflito. Numa milestone chamada "Honest State" isto é a classe exata de
      defeito que a fase existe para eliminar — a prosa promete mais do que o
      mecanismo entrega.
    artifacts:
      - path: "cairn/scripts/cairn-parallel.py"
        issue: >-
          `merge_tree_conflicts()` (linhas 1195-1228) devolve
          `{path, messages}` por conflito, sem número de linha;
          `print_report()` (linha 1283) imprime `say(f"  {c['path']}")`.
      - path: "cairn/commands/autonomous.md"
        issue: >-
          Linhas 224-225 afirmam "file and line of every conflict and every
          convergent edit" — afirmação que a saída do `reconcile` contradiz.
      - path: "tests/cairn-parallel.bats"
        issue: >-
          O teste do conflito (linha 879) afirma `.conflicts[0].path` e
          `.messages`, nunca uma linha — nenhum teste pega a divergência entre
          a prosa e a saída.
      - path: "tests/cairn-parallel-autonomous.bats"
        issue: >-
          O teste PROXY (linha 180) valida que a string "Exit 6 is a stop rule"
          existe, e abençoa a frase seguinte sem confrontá-la com a saída real
          do script.
    missing:
      - >-
        Escolher UM dos dois e fechar: (a) acrescentar a linha do conflito ao
        `conflicts[]` — lendo os marcadores do blob conflitado que o
        `merge-tree --write-tree` já produz — e cobrir com asserção no teste da
        linha 879; ou (b) corrigir `cairn/commands/autonomous.md:224-225` para
        "file of every conflict and file and line of every convergent edit" e
        registrar em 18-CONTEXT.md que a metade "linha" da D-02 vale só para a
        edição convergente, com a razão (git dá a linha no merge).
behavior_unverified_items:
  - truth: >-
      "Com duas fases sem dependência entre si, /cairn:autonomous executa as
      duas CONCORRENTEMENTE" (SC1, metade em prosa)
    test: >-
      Rodar /cairn:autonomous num milestone com duas fases independentes
      pendentes e observar se dois subagentes são realmente spawnados juntos,
      cada um na worktree que o `prepare` nomeou, e se o anúncio do passo 0.4
      aparece ANTES de qualquer worktree existir.
    expected: >-
      Anúncio primeiro (quantas fases correm, por quê, teto --max em vigor),
      depois duas worktrees `../CairnGo-phase-<N>` criadas e dois agentes
      escrevendo ao mesmo tempo; ao final, reconcile antes de qualquer merge.
    why_human: >-
      Quem spawna agente aqui é prosa lida por um modelo. Nenhum bats prova que
      dois subagentes LLM rodaram ao mesmo tempo — o próprio arquivo de teste
      declara isso no cabeçalho (tests/cairn-parallel-autonomous.bats:7-19) e
      aponta onde está a prova mecânica. Só uma execução real fecha esta metade.
---

# Phase 18: Parallel phase execution — Relatório de verificação

**Objetivo (ROADMAP):** o `/cairn:autonomous` para de executar em sequência o que
ele próprio já identifica como paralelizável — worktree por fase, lease impedindo
dois agentes na mesma fase, journal registrando, e reconciliação que **reporta**
divergência em vez de escolher um vencedor.

**Verificado:** 2026-08-01T03:52:16Z · HEAD `2a4c00e` · branch `feat/v1.4-honest-state`
**Status:** `gaps_found` (1 gap) · 1 item de verificação humana
**Re-verificação:** não — verificação inicial

---

## Achievement do objetivo

### Critérios de sucesso, um a um

| # | Critério | Status | Evidência |
|---|---|---|---|
| 1 | Duas fases independentes correm concorrentemente, com anúncio antes | ⚠️ PARCIAL — metade mecânica VERIFICADA, metade em prosa não exercida | ver SC1 abaixo |
| 2 | Cada fase numa worktree própria; edições de uma não aparecem na outra | ✓ VERIFICADO | ver SC2 |
| 3 | Duas execuções na mesma fase impedidas pelo lease, por mecanismo | ✓ VERIFICADO | ver SC3 |
| 4 | Reconciliação relata o que cada fase produziu; conflito reportado, nunca resolvido | ✓ VERIFICADO no texto do ROADMAP · ✗ gap contra a D-02 ("arquivo e linha nos dois casos") | ver SC4 |
| 5 | Falha/interrupção não corrompe a outra nem deixa lease órfão | ✓ VERIFICADO | ver SC5 |

**Score:** 4/5 critérios verificados (1 presente e cabeado, comportamento não exercido).

---

### SC1 — concorrência real, anunciada antes

**O split é real e está declarado, não descoberto por mim.**
`tests/cairn-parallel-autonomous.bats:7-19` abre com *"WHAT THIS FILE CANNOT
PROVE, said first because it is the point"*, declara que a metade de concorrência
do PAR-01 **não está sob teste ali**, e aponta nominalmente onde está a prova
mecânica. O rótulo PROXY está no cabeçalho do arquivo, como o 18-04-PLAN exigia.

**Nada mecanicamente provável foi rebaixado a proxy.** As duas afirmações que
podiam ser provadas por máquina estão em `tests/cairn-parallel.bats`, e as duas
são substantivas:

- *`batch` consome `parallelism()` e nunca recomputa* — teste da linha 217. O stub
  `CAIRN_STATUS` devolve `runnable: [7, 9]`, enquanto o ROADMAP do fixture
  descreve as fases 1 e 2 (o teste faz `grep -qF "Phase 2: API"` no ROADMAP para
  garantir a contradição). Qualquer implementação que derivasse independência do
  roadmap selecionaria 2 ou nada. `blocked`, `declared`, `note`, `next_command` e
  `reason` são conferidos verbatim.
- *A ponte batch→prepare* — teste da linha 282. Roda os dois verbos sobre DUAS
  fases, compara branch por string e worktree por `realpath` nos dois lados, e
  depois escreve arquivos reais nas duas árvores provando que não se enxergam.

Verifiquei o código do consumidor: `cmd_batch` (linha 926) lê `parallelism` de
uma única chamada `cairn-status.py --json` e só subtrai lease vivo e teto `--max`,
cada um com motivo nomeado em `deferred[]`. Não há segundo cálculo de
independência no arquivo.

**A metade em prosa** — "dois subagentes rodam ao mesmo tempo" — está entregue em
`cairn/commands/autonomous.md` (paralelo por default, linha 12; anúncio no passo
0.4, linhas 62-89; spawn conjunto no momento 3, linhas 172-175) e no doc page
(`cairn/docs/commands/autonomous.md:15-17, 34-39`). É contrato de texto, não
mecanismo verificável por teste → item de verificação humana, não gap.

**Status:** ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (metade em prosa) · metade mecânica ✓ VERIFICADA

---

### SC2 — uma worktree por fase, isolamento real

`tests/cairn-parallel.bats:117` ("the tracer") cria a worktree via `prepare`,
escreve `only-in-the-phase-worktree.txt` dentro dela e afirma que o arquivo
**não** existe na árvore principal. O teste da ponte (linha 282) faz o mesmo com
duas worktrees ao mesmo tempo, nos dois sentidos.

Medi por fora, com `prepare` real num fixture com bd: a worktree
`…/pf-phase-7` nasceu na branch `phase/7-alpha`, e o caminho vem impresso na
saída do script (`"worktree": "…/pf-phase-7"`) — nunca perguntado ao agente
(D-01). `phase_layout()` (linha 676) é o único resolvedor de nomes, e recusa
colocar a worktree fora do diretório-pai do repo.

**Status:** ✓ VERIFICADO

---

### SC3 — o lease impede, por mecanismo

`tests/cairn-parallel.bats:372` usa uma **segunda worktree de verdade**
(`git worktree add`) e um `cairn-lease.sh acquire` real: `prepare` sai 3, imprime
o holder e o `acquired_at`, e — as duas asserções que carregam o peso — não deixa
diretório nem ref para trás. O lease do outro não é perturbado.

A identidade não é declarável: `lease_acquire()` (linha 741) aponta
`--project-dir` para a worktree recém-criada e deixa o `cairn-lease.py` resolver o
holder sozinho. Não existe flag `--holder` no arquivo.

**Rollback (defeito do executor 18-01) — confirmado por mutação minha.**
O plano dizia que remover o rollback deixaria um teste vermelho; o executor mediu
duas rotas distintas ao `EXIT_HELD` e provou o rollback pela costura `CAIRN_LEASE`.
Reproduzi: desabilitando `rollback(...)` em `cmd_prepare`,

```
ok  prepare on a phase held by a live holder exits 3 … leaves no worktree
not ok  prepare rolls back its own worktree and branch when the lease is lost
        in the race window  →  `[ ! -d "$MAIN_ROOT-phase-3" ]' failed
ok  prepare never removes a worktree it did not create
```

Exatamente o que o executor reportou: a rota do pre-check fica verde (ela nunca
cria nada), e quem prova o rollback é o teste da costura. O conserto está no
código e no teste, não só na prosa do SUMMARY.

**Status:** ✓ VERIFICADO

---

### SC4 — reconciliação: relata, nunca resolve

#### A afirmação central da fase (D-02), construída por mim

Montei o fixture do zero com a forma que o briefing descreve — contagem numa
linha, cada branch acrescentando seu próprio bloco distinto num marcador
**distante**, as duas subindo a contagem de forma idêntica:

```
git merge-tree --write-tree ph14 ph15  → exit 0, nenhuma linha CONFLICT
git merge phase/15-beta                → exit 0, "Auto-merging checks.txt"
                                          1 file changed, 1 insertion(+)
arquivo mergeado: total: 14 · linha 43 "check 13" · linha 85 "check 13"
```

Idêntico à referência medida. E o detector dispara:

```
[cairn-parallel] convergent edits — both branches changed these to the SAME
                 value, and git took one without asking:
[cairn-parallel]   checks.txt:1  phase/14-alpha + phase/15-beta
[cairn-parallel]     total: 14
exit=6
```

Nomeia arquivo, linha, o conteúdo convergente e as duas branches, num merge que o
git chamou de limpo. **O ponto da fase está entregue.**

#### As garantias read-only, medidas por fora

- Rodei `reconcile` sobre o fixture e comparei antes/depois: `git status
  --porcelain` UNCHANGED, todas as refs UNCHANGED, hash de todos os arquivos
  UNCHANGED.
- `grep -rn "git stash"` em `cairn/` e `tests/`: **uma única ocorrência**, e é a
  lista de tokens proibidos no banner da região read-only
  (`cairn-parallel.py:1009`). Nenhuma invocação em lugar nenhum.
- O teste estático da linha 1091 é anti-vacuidade de verdade: extrai a região
  pelos marcadores, filtra comentários, e **afirma que a extração achou o alvo**
  (`def cmd_reconcile`, `def convergent_edits`, >100 linhas, zero `def cmd_prepare`)
  antes de contar zeros — e ainda afirma que o mesmo grep sobre o texto NÃO
  filtrado casa, de modo que o filtro não pode ser "simplificado" para uma
  checagem que só lê comentário.
- `cleanup` sem `--apply`: medido em fixture, `applied: []`, inventário de
  worktrees idêntico, lease ainda `held=true`.

#### Guarda de falso positivo, confirmada

Duas branches editando o MESMO arquivo em trechos disjuntos:
`convergent_edits: 0`, `conflicts: 0`, `findings_total: 0`, exit 0.

#### Defeito do executor 18-02 — confirmado por mutação minha

O plano dizia que remover a comparação de igualdade de **conteúdo** deixaria os
fixtures 1 e 2 vermelhos; o executor mediu falso e disse que a cobertura estava no
fixture 3. Removi `if by_range_a[key] != by_range_b[key]: continue` e rodei a
suíte inteira: **exatamente 1 teste vermelho**, e é o do conflito (fixture 3, teste
19). Fixtures 1 e 2 seguem verdes, o disjunto também. A correção do executor está
certa e a asserção mora onde ele disse.

#### O gap: "arquivo e linha nos dois casos"

`18-CONTEXT.md:120` (D-02, Claude's Discretion) exige que o relatório *"separe
conflito de merge de edição convergente e **nomeie arquivo e linha nos dois
casos**"*.

Medido num conflito real:

```
[cairn-parallel] merge conflicts between phase/7-alpha + phase/9-beta …
[cairn-parallel]   code.txt

JSON: [{"path": "code.txt",
        "messages": ["CONFLICT (content): Merge conflict in code.txt"]}]
```

Arquivo sim, linha não — nem no texto humano (`print_report`, linha 1283) nem no
JSON (`merge_tree_conflicts`, linhas 1195-1228).

O rastro do estreitamento:

| onde | o que diz |
|---|---|
| `18-CONTEXT.md:120` | "nomeie arquivo **e linha** nos dois casos" |
| `18-02-PLAN.md:21` | "Conflito de merge é reportado **com o arquivo**" (a linha some, sem nota de desvio) |
| `18-04-PLAN.md:154` | "o relatório inteiro — **arquivo e linha de cada conflito** e de …" |
| `cairn/commands/autonomous.md:224-225` | "The report goes to the operator — **file and line of every conflict** and every convergent edit" |

A prosa **entregue** promete ao operador a linha do conflito; o script entregue
não a tem. Nenhum teste pega isso: o teste do conflito (linha 879) afirma só
`path` e `messages`, e o teste PROXY (linha 180) valida a existência da string
"Exit 6 is a stop rule" e passa por cima da frase seguinte sem confrontá-la com a
saída real.

Isto não põe merge silencioso em risco — o conflito continua reportado e nunca
resolvido, e o git dá a linha na hora do merge. Mas numa milestone cujo nome é
"Honest State", uma frase entregue que promete mais do que o mecanismo entrega é
precisamente o defeito que a fase existe para eliminar. Fechável dos dois lados
(ver `gaps.missing` no frontmatter).

**Status:** ✓ VERIFICADO contra o texto do SC4 do ROADMAP · ✗ gap contra a D-02

---

### SC5 — falha não corrompe a outra, nem deixa lease órfão

`tests/cairn-parallel.bats:1215` é um teste real, não uma simulação: duas fases
preparadas em duas worktrees, dois processos em background, `kill -9` no primeiro
e **`[ "$a_status" -eq 137 ]`** — a asserção que prova que o kill foi de verdade.
Depois:

- o sobrevivente chega ao fim (commit feito, lease `held=false`);
- nada cruzou fronteira de árvore (`a-step-1.txt` só onde foi escrito, ausente na
  outra worktree e na principal);
- o lease do morto está `held=true` e **`stale=false`** — uma varredura por TTL
  olharia e não veria nada errado;
- `cleanup` sem `--apply` não move um byte; com `--apply`, `worktree_prune` +
  `lease_release`, e o `status` do lease passa a `held=false`.

A guarda `stale_but_live` (teste 1348) é o contraprovar: mesma staleness,
veredicto oposto, decidido por o dono existir ou não. E o teste 1529 prova que um
inventário sem o checkout principal para a varredura com `EXIT_GIT` em vez de
declarar o repo inteiro órfão.

**Defeito do executor 18-03 — confirmado, e é uma limitação honesta, não maquiagem.**
Medi nos dois estados:

| fixture | `git status --porcelain` na worktree preparada | veredicto do cleanup |
|---|---|---|
| sem regra de ignore | `?? .cairn/` | `retained` para sempre ("uncommitted changes") |
| com `.cairn/journal.jsonl*` | vazio | `retained` só pelo lease; depois de release+merge → **`removable` dispara** |

O conserto está em três lugares reais: a nota medida no docstring
(`cairn-parallel.py:342-351`), o `.gitignore` no fixture do teste
(`tests/cairn-parallel.bats:73`) e o comentário que explica por que um fixture sem
a regra seria o infiel (linhas 61-63). Provei a ponta boa de fim a fim: worktree
preparada + regra de ignore + branch mesclada + lease liberado → `removable: [phase 7]`.

**Status:** ✓ VERIFICADO

---

## D-03 — a fase cumpriu a própria regra

```
$ git log --format='%h %s' 30b3cfc..HEAD -- .planning/STATE.md \
      .planning/REQUIREMENTS.md .planning/ROADMAP.md
8634aaa docs(18-parallel-phase-execution): create phase plan
```

Um único commit, e é o do `/gsd:plan-phase` na árvore principal, tocando só o
`ROADMAP.md` — exatamente o caso previsto e a razão de a D-03 existir. Dos 20
commits da fase, nenhum outro tocou nos três arquivos; `STATE.md` e
`REQUIREMENTS.md` não foram tocados por commit nenhum da fase.

Estado da árvore: 0 stash entries, nenhuma branch `phase/*`, uma única worktree
(o checkout principal).

---

## Cobertura de requisitos

| Req | Descrição | Status | Evidência |
|---|---|---|---|
| PAR-01 | autonomous executa concorrentemente o que identifica como independente | ⚠️ parcial | metade mecânica provada (batch consome `parallelism()`, ponte batch→prepare); concorrência de subagentes = verificação humana |
| PAR-02 | worktree própria; edições não vazam antes da reconciliação | ✓ | testes 117 e 282, mais medição própria |
| PAR-03 | duas execuções impedidas pelo lease, por mecanismo | ✓ | teste 372 (worktree + lease reais), rollback pela costura (teste 402) |
| PAR-04 | reconciliação relata; conflito reportado, nunca resolvido | ✓ com gap | detector medido por mim; falta a linha do conflito (D-02) |
| PAR-05 | falha não corrompe as outras nem deixa lease órfão | ✓ | teste 1215 (SIGKILL 137), 1348, 1529 |

Nenhum requisito órfão: os cinco PAR estão reivindicados pelos quatro planos.
As marcações em `REQUIREMENTS.md` seguem `- [ ]`/`Pending` — correto, porque pela
D-03 elas são aplicadas de uma vez na árvore principal no fechamento, não pelos
commits da fase.

---

## Anti-padrões

| Arquivo | Padrão | Severidade | Nota |
|---|---|---|---|
| — | `TBD` / `FIXME` / `XXX` | — | nenhum nos seis arquivos da fase |
| — | `TODO` / `HACK` / `PLACEHOLDER` | — | nenhum |
| `cairn/commands/autonomous.md:224` | prosa afirma mais do que o script entrega | ⚠️ Warning → contabilizado como o gap acima | ver SC4 |

Vacuidade procurada e **não** encontrada nos pontos quentes: o stub de `batch`
contradiz o ROADMAP de propósito; o teste do git antigo usa o fixture disjunto
para que o 6 seja comprado *só* pelo não-saber, e ainda roda o mesmo fixture no
git real para provar que o 0 é o controle; o teste estático da região read-only
afirma que achou o alvo antes de contar zeros. As três mutações que rodei
(igualdade de conteúdo, rollback) mataram teste — nenhuma passou despercebida.

---

## Verificação humana necessária

### 1. Duas fases rodando de verdade ao mesmo tempo

**Teste:** rodar `/cairn:autonomous` com duas fases independentes pendentes.
**Esperado:** o anúncio do passo 0.4 aparece **antes** de qualquer worktree
existir e nomeia quantas fases correm, por quê, e o teto `--max` em vigor; em
seguida duas worktrees `../CairnGo-phase-<N>` e dois subagentes escrevendo ao
mesmo tempo; ao final, `reconcile` antes de qualquer merge.
**Por que humano:** quem spawna agente é prosa lida por um modelo. O próprio
arquivo de teste declara esse limite no cabeçalho
(`tests/cairn-parallel-autonomous.bats:7-19`) em vez de escondê-lo.

---

## Resumo dos gaps

Um gap, pequeno e preciso: a reconciliação nomeia arquivo **e linha** para a
edição convergente — a parte difícil, a que só o cairn pode reportar, e ela está
certa — mas para o conflito de merge nomeia só o arquivo, enquanto
`cairn/commands/autonomous.md:224-225` diz ao operador que ele receberá "file and
line of every conflict". A D-02 pedia os dois casos; o 18-02-PLAN estreitou a
exigência sem registrar o estreitamento como desvio (ao contrário dos três outros
defeitos, que foram medidos e reportados com exemplaridade); o 18-04 reinstalou a
promessa forte na prosa entregue. Fecha-se acrescentando a linha ao `conflicts[]`
com asserção no teste, ou corrigindo a frase e registrando a razão na D-02.

Tudo o mais que a fase prometeu está entregue e foi medido de fora, não aceito de
SUMMARY: o isolamento, o lease por mecanismo, o SIGKILL, o órfão nomeado enquanto
o relógio ainda diz que está tudo bem, o read-only do `reconcile`, e — o coração
da fase — a edição convergente nomeada num merge que o git deu por limpo.

---

_Verificado: 2026-08-01T03:52:16Z_
_Verificador: Claude (gsd-verifier)_
