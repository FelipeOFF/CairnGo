---
phase: 20-group-model
verified: 2026-08-03T00:00:00Z
status: human_needed
score: 3/4 critérios verificados (1 satisfeito na substância, quebrado na letra)
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "BOARD-01: o BOARD agrupa por milestone e, dentro dele, por fase"
    addressed_in: "Phase 21"
    evidence: "Goal da Phase 21: 'Esta fase troca a forma: uma lista, agrupada pelo modelo da fase 20, com a etapa num símbolo.' A fase 20 entrega só a metade-modelo, por decisão explícita do próprio card."
human_verification:
  - test: "Aceitar (ou rejeitar) a edição de uma linha em tests/cairn-status.bats:1189 como compatível com o critério de sucesso 3"
    expected: "Decisão registrada: ou um override aqui, ou a reescrita do critério 3 no ROADMAP para 'nenhuma chave existente muda; a única edição permitida na suíte é a declaração do conjunto exaustivo de chaves de topo'"
    why_human: "As duas cláusulas do critério 3 são mutuamente insatisfazíveis — nenhuma implementação as satisfaz ao mesmo tempo. Não é defeito de código a corrigir; é um contrato a decidir."
  - test: "Decidir quem reivindica a metade-render de BOARD-01 na tabela de Cobertura (.planning/ROADMAP.md:437)"
    expected: "Ou a linha vira 'BOARD-01 | Phase 20, 21 | Pending', ou a linha de Requirements da Phase 21 (.planning/ROADMAP.md, § Phase 21) passa a listar BOARD-01"
    why_human: "Hoje BOARD-01 aponta só para a Phase 20, que termina completa e deliberadamente sem render agrupado. No fechamento do milestone a linha lê 'Phase 20 | Pending' com a fase 20 fechada — um falso sinal esperando para disparar."
---

# Phase 20: Group model — Relatório de verificação

**Goal (ROADMAP.md § Phase 20):** acrescentar ao modelo a hierarquia
milestone → fase → tarefa, **sem tocar em render nenhum** — o board ao fim da fase é
byte a byte o que era no começo.

**Verificado:** 2026-08-03
**Status:** human_needed
**Re-verificação:** Não — verificação inicial

---

## Verdades observáveis

| # | Critério | Status | Evidência |
|---|----------|--------|-----------|
| 1 | O modelo carrega, por milestone aberto, suas fases; trabalho sem milestone em grupo próprio, por último | ✓ VERIFIED | Chamada direta de `phase_groups()` (abaixo) + `cairn-group-model.bats` 1,2,5,6,7,8 |
| 2 | Sem milestone aberto → zero grupos de milestone, nunca o nome do ciclo arquivado | ✓ VERIFIED | Chamada direta (variantes A e B) + `cairn-group-model.bats` 9,10,11 |
| 3a | `--json` ganha `groups` sem que chave existente mude de nome, tipo ou significado | ✓ VERIFIED | `cairn-group-model.bats` 12,13,14 + contagem de `@test` intacta |
| 3b | "A suíte atual passa sem edição" | ✗ FALSO NA LETRA (insatisfazível) | `tests/cairn-status.bats:1189` — literal editado, intenção preservada em comentário |
| 4 | Um teste prova que o render é **byte a byte idêntico** | ✓ VERIFIED | Cadeia de proveniência reproduzida por mim, abaixo |

**Score:** 3/4 critérios verificados. O critério 3 está satisfeito na substância e
quebrado na letra, por contradição interna do próprio critério.

---

## Critério 1 — a hierarquia existe e ordena

Não confiei na contagem de testes: carreguei `cairn-status.py` como módulo e chamei
`phase_groups()` com entradas construídas à mão.

```
model: fases 1,2 (v1.0) · 3,4 (v1.1) · 5 (sem milestone)
issues: a=[phase-3] b=[phase-1] c=[] d=[phase-4,phase-3]

milestones [v1.1 aberto, v1.0 aberto]  (nessa ordem na lista)
 → [milestone v1.1: (3,[a,d]) (4,[])] [milestone v1.0: (1,[b]) (2,[])] [unphased: (null,[c])]
```

- Ordem dos grupos = ordem da lista do roadmap, não numérica (v1.1 antes de v1.0). ✓
- Baldes em ordem ascendente de fase dentro do grupo. ✓
- `unphased` sempre último. ✓
- `d`, que nomeia duas fases, cai só na menor (3) — uma vez, não duas. ✓
- Multiconjunto de ids preservado (`grouped == lanes`). ✓

Correspondentes na suíte: testes 1 (`3 4`), 2 (o mesmo com a tabela `## Progress`
removida, que é o único caminho que exercita a leitura do *range* — sem ele o código
do range seria morto em todos os fixtures), 5, 6, 7 e 8.

## Critério 2 — o silêncio honesto

Mesma técnica, chamada direta:

| Variante | Resultado |
|----------|-----------|
| Nenhum milestone aberto | `[unphased: (null,[a,b,c,d])]` — zero grupos de milestone, nada perdido |
| Aberto `v9.9` fases 90-99 (inexistentes) | `[unphased: …]` — grupo sem baldes não é emitido |

Nenhum grupo veste `v1.1`, `v1.0` ou o rótulo deles. O grupo solto tampouco é
renomeado "para dar contexto" — rótulo fixo `No milestone`, pinado no teste 10.

A leitura de "aberto" é o marcador na linha do **próprio** milestone
(`cairn-status.py:1624`: `"🚧" in line or MILESTONE_IN_PROGRESS.search(line)`), nunca
`STATE.md`. O fixture faz os dois discordarem de propósito e o teste 3 afirma essa
premissa antes de usá-la (`.milestone == v1.0`, grupo == `v1.1`).

## Critério 3 — a chave aditiva, e a contradição do critério

### 3a: nenhuma chave existente mudou — verificado mecanicamente

- Conjunto exaustivo de chaves de topo: 14 antigas + `groups` = 15. Confirmei que os
  **dois** literais concordam byte a byte (script de comparação: `AGREE: True, n=15`),
  e eles são afirmados sob **fixtures diferentes** (`make_gsd_fixture` em
  `cairn-status.bats`, `make_board_fixture` em `cairn-group-model.bats`) — uma chave
  que só aparecesse sob um fixture apareceria exatamente como divergência entre eles.
- Linhas de `phases[]`: 22 chaves, agregadas sobre **todas** as linhas
  (`[.phases[]|keys_unsorted]|add|unique`), não sobre uma amostra.
- `disk_state`: os mesmos quatro valores.
- Contagem de `@test`: `cairn-status.bats` 55→55, `cairn-phase-model.bats` 28→28.
  Nenhum teste foi apagado ou renomeado para fazer a suíte fechar.
- Nenhum renderizador lê `groups`: `grep` por `["groups"]` / `.get("groups"` no
  script inteiro devolve zero ocorrências. O único consumidor é o resumo `--json`.

### 3b: "a suíte atual passa sem edição" — falso, e insatisfazível

`tests/cairn-status.bats:1189` foi editado (1 linha de asserção + 3 de comentário):

```
-  [ "$keys" = '["blocked","counts","doing","lease",…]' ]
+  [ "$keys" = '["blocked","counts","doing","groups","lease",…]' ]
```

**Julgamento: foi a escolha certa, e o critério é que está mal escrito.** As duas
cláusulas do critério 3 não podem valer juntas: o teste 45 de `cairn-status.bats`
compara o conjunto **exaustivo** de chaves de topo com um literal, então *qualquer*
chave aditiva o reprova. As saídas alternativas são todas piores:

- aninhar `groups` dentro de `phases[]` viola D-02 e muda a forma de algo que três
  superfícies consomem;
- não emitir chave nenhuma cancela a fase;
- afrouxar o teste 45 para um teste de subconjunto destruiria a única asserção da
  suíte que pega uma chave **renomeada ou removida** — exatamente o que o critério 3
  existe para proteger.

O que foi feito é o mínimo: uma linha, no ponto que o próprio teste declara ser o
ponto de declaração, com o comentário registrando o que a lista guarda ("que nenhuma
chave EXISTENTE mude de nome ou desapareça"). E os dois literais concordam hoje —
verifiquei, não presumi.

**Isto não é um defeito para planejar conserto. É um contrato para o humano
decidir.** Ver a seção *Verificação humana*.

## Critério 4 — byte a byte, provado pela cadeia, não pela contagem de testes

Não aceitei "9/9 verde" como prova. Reconstruí a cadeia inteira:

1. **A referência foi capturada de código pré-fase.** `git diff 784483e be2a6ef --
   cairn/scripts/cairn-status.py` é **vazio** — no commit que gravou os sete
   fixtures, o script era byte a byte o de antes da fase (`be2a6ef`, fase 16-04).
2. **A referência nunca foi regenerada.** `git diff 784483e..HEAD --
   tests/fixtures/board-render/` é **vazio**. Os dois commits de fixture (`79a41cc`,
   `784483e`) são ancestrais do primeiro commit que tocou o `.py` (`6923e59`).
3. **Nenhuma função de render foi tocada.** Os cabeçalhos de hunk do diff
   `fff5809..HEAD` do `.py` são `@@ -84 @@`, `-134`, `-242`, `-1369`, `-1392`,
   `-3048`: docstring de módulo, constantes de regex, `phase_groups()` novo,
   `roadmap_milestones()` novo e a chave em `main()`. `render_board()` está na linha
   1915 — fora de todo hunk.
4. **O diff inteiro tem exatamente uma deleção de código executável**, e ela é
   inócua: `roadmap_milestone()` trocou `re.search(r"\(in progress\)", line,
   re.IGNORECASE)` pela constante `MILESTONE_IN_PROGRESS`, que é
   `re.compile(r"\(in progress\)", re.IGNORECASE)` — mesmo padrão, mesmas flags. O
   resto do diff é adição pura.
5. **O render de HOJE bate com a referência.** Rodei
   `bats tests/cairn-board-invariance.bats tests/cairn-group-model.bats` com o status
   capturado explicitamente (não via `| tail`): **EXIT=0, 23 ok, 0 not ok**.

Logo: render de HEAD == referência == render pré-fase, nos sete modos.

**A comparação está viva, e isso também foi verificado estruturalmente.** Os sete
testes de referência e o teste de vivacidade passam pela **mesma** função,
`diff_render_against_reference()` (`cairn-board-invariance.bats:43`): os sete afirmam
`-eq 0`, a vivacidade afirma `-ne 0` e ainda exige que o diff **mencione** a
perturbação (`cairn-board-invariance.bats:140`), de modo que um `sed` que deixasse de
casar não vira no-op silencioso. Uma comparação viciada para sempre concordar deixaria
os sete verdes e a vivacidade vermelha — não há cópia privada honesta onde se
esconder. Isto foi o defeito de plano que o executor de 20-01 reportou e consertou.

**Ressalva registrada, não creditada:** `--json` está deliberadamente fora da matriz
(a fase acrescenta chave a ele de propósito) e `--html` também não está. Nenhuma
função de HTML aparece em hunk nenhum, então não há risco medido — mas a prova
byte a byte cobre sete modos de terminal, não oito.

---

## D-02 — a chave é de topo, e o teste realmente agrega

`cairn-status.py:3282` põe `"groups"` ao lado de `"phases"` no dict `data`. Nada é
aninhado.

O teste 13 usa `[.phases[] | keys_unsorted] | add | unique` — agrega sobre **toda**
linha, não sobre `.phases[0]`. E afirma a premissa antes de usá-la: `.phases[0]` é a
fase 1, completa, do v1.0 **arquivado**. Reproduzi o raciocínio da wave 3 sobre o
JSON deste próprio repositório, injetando por `jq` uma chave `group` apenas nas fases
do milestone aberto:

```
agregado de chaves .phases[]        → 22   (limpo)
agregado com a violação injetada    → 23   (a extra é `group`)
```

A violação mais plausível de D-02 não é acrescentar chave a toda fase — é acrescentar
só às fases dentro do grupo aberto. No fixture, `.phases[0]` é a fase 1 (arquivada,
fora de qualquer grupo emitido), então uma amostra de uma linha ficaria **verde com a
decisão violada**. O agregado é o que fecha o buraco, e a asserção da premissa é o que
impede o fixture de mudar por baixo e esvaziar a prova. Está certo.

## FIX-04 — a confusão não foi herdada (verificado no código, por AST)

Não li a prosa: parseei o arquivo e extraí o corpo de `phase_groups()` **sem** o
docstring, listando todo identificador.

```
names : UNPHASED_KEY UNPHASED_LABEL bucket buckets by_number explicit groups iss
        issue_phase_ns issues items key loose milestones model ms n named numbers
        p set sorted str target
attrs : add append get items setdefault update
str   : ? first id issues items key label last milestone number open phase type unphased
identificadores com dep/block/depends no corpo: []   ← nenhum
```

A colocação de issue lê `issue_phase_ns()` e mais nada. `dependencies`, `blocked_by`,
`depends_on` e `dep_target_ids()` só aparecem no docstring, explicando por que **não**
são lidos.

E o contra-prova temporal: referências **executáveis** a `dep_target_ids` no arquivo,
por AST, `6d81d5c` (pré-fase) → **1**; `HEAD` → **1**. Ocorrências textuais no mesmo
intervalo: 2 → 4. Isto reproduz exatamente o terceiro defeito de plano reportado: a
verify original (`grep -c 'dep_target_ids' == 2`) reprovaria o arquivo **por ele
documentar bem a decisão**. Medir por AST é a medida certa da intenção, e ela
confirma: zero uso novo.

O teste 11 fecha o lado comportamental: uma issue com rótulo `phase-9` (ciclo
arquivado dois milestones atrás) e uma aresta `discovered-from:brd-001` cai no grupo
solto, aparece **exatamente uma vez**, não cria grupo fantasma e não move os grupos
existentes — com os conjuntos de chaves e rótulos afirmados exaustivamente, e o
`label` juntado por `|` e não por espaço, para que dois rótulos com espaço não possam
se disfarçar de um só.

## Defeitos de plano reportados pelos executores — os três, julgados

| # | Defeito | Tratamento | Verdito |
|---|---------|-----------|---------|
| 20-01 | O teste de vivacidade, como especificado, não protegia a comparação compartilhada | `diff_render_against_reference()` extraída; sete afirmam `-eq 0`, vivacidade afirma `-ne 0` na mesma função, e exige que o diff cite a perturbação | ✓ Honesto e verificado em `cairn-board-invariance.bats:43,137,140` |
| 20-02 | O critério 3 se contradiz; e o "break" nomeado para o teste 1 não avermelhava, porque o fixture tem tabela `## Progress` e o caminho do range nunca era exercitado | Contradição medida (82 ok / 1 not ok) e reportada antes de editar; teste 2 novo remove a tabela e força o range, afirmando a remoção (`grep -c '^## Progress' == 0`) | ✓ Honesto. O teste 2 é justamente o que impede código morto |
| 20-03 | A verify de `dep_target_ids` contava prosa (4, não 2) e reprovaria o arquivo por documentar bem | Intenção medida por AST, em HEAD e no commit pré-fase | ✓ Honesto. Reproduzi a medida de forma independente: 1 → 1 executável |

Nenhum dos três foi silenciado nem "consertado" alargando o teste.

## Varredura de vacuidade

- **Teste 14 (`disk_state`)**: o próprio teste declara que prova pouco — asserção de
  subconjunto sobre quatro valores, num fixture que só produz `none`. O que impede o
  `KeyError` de `phase_next_command()` é o **escopo** (nada nesta fase escreve
  `disk_state`), não este teste. Está creditado como tripwire e nada além disso.
  Correto.
- **Testes 13 e 14 passariam com `groups` removido** — são testes de contrato
  negativo, e é assim que devem ser; o teste 12 é o que exige a feature presente. Não
  há crédito indevido.
- **Teste 8** compara listas ordenadas dos dois lados **sem** `unique`, e ainda afirma
  `length == 7` para que duas listas vazias não passem por prova.
- **Mutações afirmadas, não presumidas**: `archive_the_open_milestone` e
  `open_a_milestone_with_no_phases` fazem `assert after != text` em Python e depois
  conferem o marcador no arquivo. Uma gramática de roadmap que mudasse a montante
  deixaria o milestone aberto e os testes verdes medindo nada — esse buraco está
  fechado.
- **Variante B afirma que é mesmo variante B**: chama `roadmap_milestones()`
  diretamente para provar que existe **um** milestone aberto (`v9.9`), senão ela
  degeneraria silenciosamente na variante A.
- **Nenhum marcador de dívida** (`TODO`/`FIXME`/`XXX`/`TBD`/`HACK`) nos arquivos que a
  fase tocou.
- **Nenhum fixture regenerado para fazer teste passar** — e `regenerate.sh` documenta
  que nenhum teste pode chamá-lo, o que a suíte respeita.

---

## Requisito BOARD-01 — dito sem rodeio

**BOARD-01 diz:** "O **board** agrupa por milestone e, dentro dele, por fase; trabalho
sem milestone tem grupo próprio e aparece por último."

**A fase 20 não satisfaz BOARD-01, e isso é correto.** O board renderiza hoje
exatamente as três raias que renderizava — a fase provou isso byte a byte, e o próprio
card diz "o board continua exatamente como está ao fim dela". Entregue: a **metade
modelo** de BOARD-01 (agrupamento por milestone, depois por fase, solto por último —
tudo isso existe e está testado, em `--json`). Falta: a metade **render**, que é a
fase 21.

A fase 20 **não** extrapola para a fase 21. O risco é o inverso, e é de escrituração:

- `.planning/ROADMAP.md:437` — `| BOARD-01 | Phase 20 | Pending |`
- `.planning/ROADMAP.md` § Phase 21 — `**Requirements**: BOARD-02, BOARD-03, BOARD-05`

Nenhuma fase reivindica a metade render de BOARD-01. Quando a fase 20 fechar, a linha
de cobertura vai ler "Phase 20 | Pending" apontando para uma fase completa — um falso
sinal esperando o fechamento do milestone. O checkbox em `REQUIREMENTS.md:14` continua
`- [ ]`, o que é honesto; é a tabela de cobertura que precisa dizer `Phase 20, 21`.

---

## Cobertura de requisitos

| Requisito | Plano | Status | Evidência |
|-----------|-------|--------|-----------|
| BOARD-01 | 20-01, 20-02, 20-03 | ⚠️ PARCIAL (metade modelo) | `groups` em `--json` com hierarquia completa e 14 testes; render agrupado é a fase 21 |

## Anti-padrões

Nenhum. Sem marcadores de dívida, sem retorno vazio, sem prop vazia, sem teste
apagado, sem fixture regenerado.

## Execução de testes

| Suíte | Comando | Resultado |
|-------|---------|-----------|
| Invariância + modelo de grupo | `bats tests/cairn-board-invariance.bats tests/cairn-group-model.bats` (status capturado, não via `\| tail`) | EXIT=0 — **23 ok, 0 not ok** |
| Suíte completa | `bats -j 6 tests/` | **555 ok, 0 falhas** (medição estabelecida) |

---

## Verificação humana requerida

### 1. Aceitar a edição de uma linha exigida pelo critério 3

**Arquivo:** `tests/cairn-status.bats:1189`
**O que decidir:** o critério 3 pede duas coisas que nenhuma implementação entrega
juntas. A execução escolheu a substância (nenhuma chave existente muda) e pagou a
letra (uma linha editada, no ponto de declaração, com a intenção no comentário).
**Esperado:** ou registrar o override abaixo, ou reescrever o critério 3 no ROADMAP.

```yaml
overrides:
  - must_have: "`--json` ganha a estrutura de grupos sem que nenhuma chave existente mude de nome, de tipo ou de significado; a suíte atual passa sem edição"
    reason: "As duas cláusulas são mutuamente insatisfazíveis: tests/cairn-status.bats:1189 afirma o conjunto EXAUSTIVO de chaves de topo, então qualquer chave aditiva exige editar aquele literal. A alternativa (aninhar groups em phases[]) viola D-02; afrouxar o teste para subconjunto destruiria a única asserção que pega chave renomeada. Editada 1 linha, intenção preservada em comentário, e os dois literais que pinam o mesmo conjunto foram verificados como idênticos (15 chaves)."
    accepted_by: "<nome>"
    accepted_at: "<ISO>"
```

### 2. Decidir quem reivindica a metade render de BOARD-01

**Arquivo:** `.planning/ROADMAP.md:437` (e § Phase 21, linha de `**Requirements**`)
**O que decidir:** `| BOARD-01 | Phase 20 | Pending |` aponta um requisito de render
para uma fase que, por decisão, não renderiza nada. A fase 21 entrega a lista agrupada
mas não lista BOARD-01.
**Esperado:** `| BOARD-01 | Phase 20, 21 | Pending |`, ou BOARD-01 acrescentado aos
Requirements da fase 21.

---

## Resumo

O objetivo da fase foi atingido. A hierarquia existe, ordena, cala quando não há ciclo
aberto, não perde nem duplica trabalho, não herda a confusão da FIX-04 (provado por
AST, não por prosa), vive numa chave de topo e não dentro de `phases[]` (provado por
um teste que agrega sobre todas as linhas e afirma a própria premissa), e o board
renderiza os mesmos bytes — o que verifiquei pela cadeia de proveniência inteira, não
pela contagem de testes verdes.

Os três defeitos de plano foram reportados com medição antes de qualquer edição, e os
três consertos foram verificados de forma independente aqui.

O que sobra não é código: é um critério que se contradiz e uma linha de tabela de
cobertura que aponta para a fase errada. Ambos precisam de uma decisão humana, e
nenhum dos dois se resolve replanejando a fase 20.

---

_Verificado: 2026-08-03_
_Verificador: Claude (gsd-verifier)_
