---
phase: 23-not-applicable-as-a-check-state
verified: 2026-08-06T21:29:50Z
status: passed
score: 4/4 critérios verificados, 3/3 requisitos entregues
behavior_unverified: 0
behavior_unverified_items: []
human_verification: []
overrides_applied: 0
gaps: []
---

# Fase 23: Not-applicable as a check state — Relatório de verificação

**Card:** o doctor para de dar verde sobre o que não checou.
**Verificado:** 2026-08-06T21:29:50Z
**Veredito:** passed
**Re-verificação:** não — verificação inicial (não havia `23-VERIFICATION.md`)

O veredito não vem do SUMMARY. Vem de três medições feitas nesta árvore: um
diferencial do doctor pré-fase contra o atual em repositório temporário, uma
enumeração por AST de todos os ramos do estado novo, e a suíte
`tests/cairn-doctor.bats` rodada inteira. A fase entrega o que prometeu.

## Verdades observáveis

| # | Verdade (critério do ROADMAP) | Estado | Evidência |
|---|---|---|---|
| 1 | `not-applicable` é estado distinto de `ok` no `--json` e no resumo, e o rodapé conta os dois separadamente em vez de somá-los | ✓ VERIFICADO | `cairn-doctor.py:3077-3092` conta quatro baldes derivados das chaves de `SYMBOL`; `n_ok = counts["ok"]` (L3089). Diferencial de git: em `feb02e2^` a linha era `n_ok = len(checks) - n_fail - n_warn` (L2557). `SYMBOL` (L544) tem quatro entradas, `⊘` = U+2298. Testes 2, 3 e 26 passaram |
| 2 | Roadmap vazio produz zero `ok` nas três checagens e três `not-applicable`, e o board não lê como saudável | ✓ VERIFICADO | Reproduzido em repositório temporário, três formas. ANTES: `ok — 17 ok, 1 warning`, `.ok: true`, `✓ req-issue / ✓ maps-fresh / ✓ orphans`. DEPOIS: `INCOMPLETE — 10 ok, 9 not-applicable`, `.ok: false`, os três `⊘`. Ver a ressalva medida abaixo |
| 3 | `orphans` para de sinalizar issue fechada de milestone arquivado, e um teste arquiva um ciclo e afirma que a contagem zera | ✓ VERIFICADO | `in_archived_milestone()` (L916-943) exige as três condições e `keys <= set(archived)` (todos os rótulos, não algum). Teste diferencial 22 + três de contorno (23, 24, 25) passaram. Neste repositório: `+61 closed issue(s) of archived milestone(s) exempted` |
| 4 | Cada checagem que ganha o estado novo diz, na própria mensagem, o que faltou para poder checar | ✓ VERIFICADO | Enumeração por AST: 11 ramos `not-applicable` em 9 checagens; todos nomeiam o insumo ausente e todos carregam `scope`; nenhuma outra checagem carrega `scope` (asserção 2 do teste 26) |

**Score:** 4/4 critérios verificados (0 presentes sem prova de comportamento).

### A medição do critério 2, feita aqui e não lida do SUMMARY

Repositório temporário de verdade, `git init` + `bd init`, `ROADMAP.md` sem
nenhuma fase, `gsd-capability` neutralizado pelo mesmo stub que a suíte usa
(`CAIRN_GSD_BIN`), o **mesmo** repositório rodado pelas duas versões do doctor:

```
ANTES  (feb02e2^)   ✓ req-issue    no '**Requirements**:' lists found in ROADMAP.md
                    ✓ maps-fresh   0 phase map(s) current
                    ✓ orphans      0 issue(s), no orphans
                    [cairn-doctor] ok — 17 ok, 1 warning(s), 0 failure(s)
                    .ok: True   | counts: ausente

DEPOIS (árvore)     ⊘ req-issue    nothing to compare — ROADMAP.md lists no phase …
                    ⊘ maps-fresh   nothing to compare — no phase directory … carries
                                   either an issue or a generated map …
                    ⊘ orphans      nothing to compare — the phase-label axis could
                                   not run …; the unlabeled-issue axis ran and found
                                   nothing over 0 issue(s)
                    [cairn-doctor] INCOMPLETE — 10 ok, 9 not-applicable, 0 warning(s), 0 failure(s)
                    .ok: False  | counts: {'ok': 10, 'not-applicable': 9, 'warn': 0, 'fail': 0}
```

Três formas do repositório vazio foram medidas, e em **todas** o número de `ok`
entre as três checagens é zero:

| forma do repositório | req-issue | maps-fresh | orphans | rodapé | `.ok` |
|---|---|---|---|---|---|
| roadmap vazio, árvore de fases vazia (a forma do `Goal`) | ⊘ no-input | ⊘ no-input | ⊘ no-input | INCOMPLETE | false |
| roadmap vazio + uma issue solta | ⊘ no-input | ⊘ no-input | ⚠ (achado real) | INCOMPLETE | false |
| roadmap vazio, com diretório de fase no disco | ⊘ no-input | ⊘ no-input | ⊘ no-input | INCOMPLETE | false |

**Ressalva medida, e ela corrige a premissa do critério, não o descumpre.** O
critério pede "três `not-applicable`", e há uma forma em que só saem dois: quando
existem mapas gerados no disco, `maps-fresh` **compara de verdade** e devolve
`warn` (é o que o teste 27 fixa, no valor exato). O motivo está no código
(`check_maps_fresh`, L1061-1076): o insumo dessa checagem é `.planning/phases/`,
não o `ROADMAP.md` — ela nunca lê o roadmap. Onde a premissa do critério vale
(nada para comparar, que é a forma pós-arquivamento que o `Goal` mediu), os três
saem `⊘`. Onde não vale, a checagem que ainda tem trabalho continua trabalhando —
que é a leitura correta e a única que não troca um verde falso por um vermelho
falso. Nenhuma das formas devolve `ok` sobre o nada.

### A armadilha do `!= "ok"`

Confirmado que as asserções são sobre o valor exato. A asserção irmã do
`lease-stale` (`tests/cairn-doctor.bats:1995-2003`) pergunta explicitamente
`select(.status == "warn" or .status == "fail")` e depois fixa os dois `⊘` por
id **e** por família — mais forte do que o `!= "ok"` que ela tinha. Varredura do
diretório `tests/`: nenhuma asserção de status de checagem do doctor sobrevive na
forma negada. A única ocorrência remanescente de `!= "ok"`
(`tests/cairn-corroboration.bats:397`) é sobre o campo `corroboration`, outro
vocabulário, fora desta fase.

### O guarda do quinto estado, exercitado

O must-have do plano 01 ("um quinto status derruba o relatório em vez de entrar
contado como sucesso") é comportamental e **nenhum teste da suíte o exercita**.
Exercitei numa cópia isolada em scratchpad (a árvore do repo não foi tocada),
injetando uma checagem com `status: "maybe"`:

```
[cairn-doctor] error: check 'quinto-estado' returned unknown status 'maybe' —
the vocabulary is ['fail', 'not-applicable', 'ok', 'warn']; a new status needs
a symbol in SYMBOL before it can be counted
exit=7   (idêntico com --json)
```

O ramo funciona. Por isso `behavior_unverified: 0`. Fica registrado que a
proteção não tem teste de regressão próprio: a asserção de vocabulário fechado
prova que ninguém devolve um quinto status hoje, mas não pegaria a remoção do
`die()`.

## Artefatos exigidos

| Artefato | Esperado | Estado | Detalhe |
|---|---|---|---|
| `cairn/scripts/cairn-doctor.py` | quarto estado, duas famílias, contagem por balde, isenção do `orphans` | ✓ VERIFICADO | `NOT_APPLICABLE`/`NA_OUT_OF_SCOPE`/`NA_NO_INPUT` (L520-544), `counts` (L3077), `in_archived_milestone` (L916), `archived_milestones` (L649) |
| `tests/cairn-doctor.bats` | aritmética do rodapé, invariante do vocabulário, roadmap vazio, isenção diferencial | ✓ VERIFICADO | Testes 1, 2, 3, 21-32, 64, 93 — todos passaram |
| `tests/helpers.bash` | fixture de ROADMAP sem fase | ✓ VERIFICADO | `make_roadmap_without_phases()` (L325), com a nota medida sobre `maps-fresh` |
| `cairn/docs/commands/doctor.md` | as duas famílias, `.counts`, `.scope`, `INCOMPLETE`, a isenção e seu limite | ✓ VERIFICADO | L24-71, L132-150, L279-343, L388; 18 das 19 checagens têm entrada em negrito, e a 19ª (`bd-version`) está descrita em L370 como a que não precisa de roteamento |
| `cairn/commands/autonomous.md` | o consumidor autônomo não para por `⊘` | ✓ VERIFICADO | L25-35 separa a nota de topo do `⊘` por checagem e manda seguir |

## Ligações-chave

| De | Para | Via | Estado |
|---|---|---|---|
| `SYMBOL` | contagem em `main()` | baldes derivados das chaves do mapa de símbolos | ✓ LIGADO (L3077) |
| `n_no_input` | `summary["ok"]` e o rodapé | só a família do vão limpa a saúde; `out-of-scope` não | ✓ LIGADO (L3095-3103, L3113-3118) |
| `.planning/milestones/` | `check_orphans` | `archived_milestones()` → `in_archived_milestone()` | ✓ LIGADO (L649, L1236) |
| eixo 2 do `orphans` | veredito | achado real ainda vira `warn` com roadmap vazio | ✓ LIGADO (L1250-1262), teste 28 |
| doctor `--json` | consumidor autônomo | `⊘` não interrompe a corrida | ✓ LIGADO (`cairn/commands/autonomous.md:29-35`) |

## Fluxo de dados (nível 4)

`counts` não é derivado por subtração nem por constante: vem de um laço sobre
`checks`, e o teste 2 recalcula cada balde a partir da própria lista de checagens
do JSON, em vez de aceitar o número que o rodapé anuncia. A `detail` de cada `⊘`
é construída no ramo da checagem, com o nome do insumo interpolado
(`{planning_dir.name}`, `{live_plans}`, `{len(issues)}`) — nenhuma frase é
literal fixa vestindo o estado.

## Checagens comportamentais

| Comportamento | Comando | Resultado | Estado |
|---|---|---|---|
| Doctor pré-fase aprova o vazio | `python3 <doctor de feb02e2^>` em repo temporário | `ok — 17 ok, 1 warning`, `.ok true` | ✓ (linha de base) |
| Doctor atual recusa aprovar o vazio | `cairn-doctor.sh` no mesmo repo | `INCOMPLETE — 10 ok, 9 not-applicable`, `.ok false` | ✓ PASSOU |
| Quinto status derruba o relatório | cópia com `status: "maybe"` injetado | erro nomeado, exit 7 | ✓ PASSOU |
| Isenção declarada neste repositório | `cairn-doctor.sh --json` | `2 orphan issue(s) (+61 closed issue(s) of archived milestone(s) exempted)` | ✓ PASSOU |
| Toda checagem registrada tem entrada na página | comparação `--json` × `doctor.md` | 19 registradas, 18 em negrito + `bd-version` descrita | ✓ PASSOU |

As duas órfãs remanescentes neste repositório (`CairnGo-7yw`, `CairnGo-fp7`) são
do eixo 2 — issues **abertas** sem rótulo de fase, achado vivo e correto —, não
resíduo histórico.

## Suíte

Rodada exigida, e só ela, pelo runner da casa:

```
bash cairn/scripts/cairn-test.sh --jobs 3 tests/cairn-doctor.bats
```

Contado sobre o log inteiro (104 linhas), não sobre saída truncada:

- **anunciado:** `1..101`
- **executado:** 101 `ok`, 0 `not ok`, 0 skips
- **marca de fim no arquivo:** `EXIT=0` na última linha

A conta fecha: 1 linha do runner + 1 do plano + 101 resultados + 1 do exit = 104.
O SUMMARY da fase declara `1..96`; a diferença são as cinco asserções de
`response-language`, que a fase 24 acrescentou a este mesmo arquivo depois do
fecho da 23 — não é discrepância desta fase.

## Cobertura de requisitos

| Requisito | Descrição | Estado | Evidência |
|---|---|---|---|
| VOID-01 | checagem sem nada para checar reporta `not-applicable`, distinto de `ok`, e o resumo conta os dois separadamente | ✓ ENTREGUE | critério 1; `CairnGo-6yj` fechada |
| VOID-02 | roadmap vazio não produz board verde | ✓ ENTREGUE | critério 2, medido em repositório temporário; `CairnGo-ca3` fechada |
| VOID-03 | `orphans` para de sinalizar issue fechada de milestone arquivado, e a contagem zera | ✓ ENTREGUE | critério 3; 61 isentas e declaradas; `CairnGo-xhy` fechada |

## Anti-padrões

Varredura de `TBD`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER`/`TODO` nos cinco arquivos
que a fase modificou: **nenhuma ocorrência**. (O único casamento, `XXXXXX` em
`tests/helpers.bash:45`, é gabarito de `mktemp`.) Nenhuma anotação pendente do
tipo "quando a fase 23 chegar" sobreviveu no doctor: as 25 menções à fase são
justificativas de decisão, não promessas em aberto.

## Achados fora do contrato da fase (não são lacunas dela)

1. **O prompt do comando `/cairn:doctor` está velho, e a velhice inclui o estado
   novo.** `cairn/commands/doctor.md` ensina o agente a explicar "one ✓/⚠/✗ line
   per check" (passo 2), roteia apenas **9** das 19 checagens (passo 5), não
   menciona `⊘`, `INCOMPLETE`, `out-of-scope` nem `no-input`, e fecha com
   "re-run the doctor to confirm a clean `ok` footer" — rodapé que pode agora ser
   inalcançável. **Não é regressão desta fase:** `git log` mostra o arquivo
   parado desde `0c87ac6` (ESC-03), muito antes da 23, e nenhum commit `23-0*` o
   tocou; a defasagem cobre também as checagens que as fases 15, 17, 24 e 29
   acrescentaram. Vale abrir issue, porque é a superfície onde um operador lê o
   veredito pela boca de um agente — exatamente a camada acima daquela que esta
   fase consertou.

2. **Aritmética da prosa dos SUMMARY, medida.** `23-SUMMARY.md` e
   `23-04-SUMMARY.md` dizem "**Oito** das dezoito podem devolver o quarto estado"
   e "duas usam `out-of-scope`". Contado por AST **no commit de fecho da própria
   fase** (`ccbe8d9`): são **nove** checagens, sete com ramo `no-input` e **três**
   com `out-of-scope` (`release-versions`, `req-ledger`, `test-parallel`). A
   tabela do próprio `23-04-SUMMARY.md` lista as nove linhas corretamente — o erro
   está só no número da frase. O código está certo; o registro escrito está um a
   menos em dois lugares.

3. **`cairn/README.md:241` chama o doctor de "the nine-check consistency
   audit"** — são 19. Defasagem antiga, alheia a esta fase.

## O que não consegui verificar

Nada dos quatro critérios ficou sem medição. Duas fronteiras ficam declaradas:

- A suíte completa do repositório não foi rodada (instrução explícita, e há outras
  verificações em paralelo nesta máquina). Só `tests/cairn-doctor.bats` correu, e
  correu inteira. Uma regressão que esta fase tenha causado em **outro** arquivo
  de teste não seria vista aqui.
- A falha de `phase-corroboration` que o SUMMARY registra como achado externo
  (FIX-05, fase 25) não aparece mais neste repositório: a rodada de hoje dá
  `17 ok, 1 not-applicable, 1 warning, 0 failure` e exit 0. Ou o fecho pelo
  `cairn-bookkeep` resolveu, ou a condição não está mais presente — não investiguei,
  porque é fora do contrato da 23.

---

_Verificado: 2026-08-06T21:29:50Z_
_Verificador: Claude (gsd-verifier)_
