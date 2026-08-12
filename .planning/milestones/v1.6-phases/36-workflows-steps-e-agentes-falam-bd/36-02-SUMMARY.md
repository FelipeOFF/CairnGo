---
phase: 36-workflows-steps-e-agentes-falam-bd
plan: 02
subsystem: bundles-de-init
tags: [adapt-01, d-03, section-manifest, goldens, derived-from-contract, tipo-vs-valor]
requires:
  - onda zero do preâmbulo fechada (36-01) — nada aqui toca cairn/gsd/
  - goldens derived-from-contract pinados na tag v1.10.0 (fases 33-35)
provides:
  - section_manifest emitido `null` nos 6 bundles de init (o valor do contrato)
  - a decisão D-03 escrita NO CÓDIGO, com o número medido que a sustenta
  - tabela permanente de TIPO nos verbos de init (6 null + 1 ausente)
  - divergences.json descrevendo de novo o estado real do binário
affects: [fase-36-planos-03-a-07, camada-prompt-21-gates]
tech-stack:
  added: []
  patterns:
    [
      edição de golden por substring dentro da string JSON escapada,
      prova de envelope por json.loads antes/depois (não por jq no campo),
      tabela de tipo com o lado "ausente" como controle negativo embutido,
      argv do teste tirado do manifesto de cenários, nunca digitado,
    ]
key-files:
  created: []
  modified:
    - cairn/scripts/cairn-gsd-init.py
    - tests/cairn-gsd.bats
    - tests/fixtures/gsd-goldens/divergences.json
    - tests/fixtures/gsd-goldens/init-autonomous.golden.json
    - tests/fixtures/gsd-goldens/init-debug.golden.json
    - tests/fixtures/gsd-goldens/init-execute-phase.golden.json
    - tests/fixtures/gsd-goldens/init-plan-phase.golden.json
    - tests/fixtures/gsd-goldens/init-quick.golden.json
    - tests/fixtures/gsd-goldens/init-verify-work.golden.json
decisions:
  - "D-03 preservar a composição: escrita no topo da família init de cairn-gsd-init.py, com os três porquês e os números (21 arquivos / 806 linhas / +12,4%; 10 de 38 chamadas; 65-vs-8), e os outros 5 sítios apontando para ela"
  - "o recorder NÃO foi executado: promoveria provenance derived-from-contract → recorded e trocaria a comparação de FORMA para BYTES"
  - "a entrada section-manifest-empty foi reescrita, não duplicada — 55 entradas antes e depois, aspect preservado apesar do nome ter envelhecido"
  - "quatro checks <automated> do próprio plano estavam errados e foram substituídos por versões que preservam a INTENÇÃO; os quatro estão registrados abaixo com a medição que os derruba"
metrics:
  duration: ~4h de sessão (13:35 → 17:4x UTC, com duas suítes longas)
  completed: 2026-08-11
status: complete
---

# Phase 36 Plan 02: `section_manifest` — o tipo corrigido e D-03 escrita Summary

**One-liner:** os 6 bundles de init passaram a emitir `section_manifest: null`
— o valor que a camada prompt lê como superset seguro e, medido no clone da
tag, o único que upstream produz nesta árvore — com os 6 goldens regravados por
edição de substring dentro da string JSON escapada (provenance intacta, sem
recorder) e a decisão D-03 registrada no código com o número que a sustenta.

## A rota

Linear, na ordem do plano. Task 1 em TDD estrito: a tabela primeiro (RED com os
6 verbos nomeados), a correção depois (GREEN), commits separados. Task 2 sobre
os goldens e a divergência. Três quebras reais no fim, cada uma restaurada de
cópia `cp` — nunca `git checkout`.

Nenhuma reordenação foi necessária e nenhum caminho sob `cairn/gsd/` foi
tocado (`git diff --name-only c433879 -- cairn/gsd/` → vazio).

## O que foi medido — e as quatro premissas que a medição contradisse

Os 6 sítios estavam exatamente onde o `36-PATTERNS.md §6` diz (574, 583, 614,
786, 823, 856, todos `[]`), e `execute-phase.md:92` e `debug.md:31` dizem
exatamente o que o plano cita. O resto não bateu.

### 1. "Upstream emite `[]`" — **FALSO**

`36-PATTERNS.md §6`, fato (2), afirma que rodar o recorder *"reintroduziria o
bug do upstream"*, porque *"Upstream emite `[]`"*. Não emite. Medido no clone
da tag em `.cairn/cache/gsd-core-v1.10.0`, sem executar nada:

- `src/init.cts:459-470` (`loadSectionManifestSections`): a leitura de
  `gsd-core/workflows/section-manifest.json` devolve `null` — *"never throws"*
  — quando o artefato falta, é ilegível, é JSON malformado, tem a forma errada,
  ou quando o workflow não tem chave nele. O caminho de sucesso devolve
  `{workflow, included, excluded, read}`. **Não existe caminho que produza
  lista.**
- A própria suíte do upstream assere isso, com estas palavras:
  `tests/section-manifest-init-facts.test.cjs:67` —
  `'an absent workflow key must degrade to null, never []'`; e
  `:75` — `'a present (even empty) workflow key must NOT degrade to null'`.
  O arquivo de teste se chama, literalmente,
  *"`section_manifest`: null (degraded) vs [] (computed, nothing applicable)"*.

O `[]` era **só da reimplementação em python**. Isso não muda a decisão (o
recorder continua a ferramenta errada, pelos outros dois motivos), mas troca o
motivo nº 1 do plano por outro.

### 2. "nem cache, nem node, nem build disponíveis" — **1 de 3**

O mesmo fato (2) do PATTERNS diz que o recorder exigiria *"o cache (`exit 6`),
`node` no PATH (`exit 5`) e um build do runtime — nenhum dos três disponível
neste checkout"*. Medido:

| exigência | estado real |
|---|---|
| clone em cache com HEAD pinado | **presente** — `.cairn/cache/gsd-core-v1.10.0`, HEAD `68a04ccf8ef74803bdb651e12c3b85b218bbccdf`, igual ao esperado |
| `node` no PATH | **presente** — v24.13.1 |
| runtime buildado | **ausente** — `gsd-core/bin/lib/cli-exit.cjs` não existe |

Só o terceiro sustenta a afirmação. O recorder não foi executado assim mesmo, e
o motivo que continua de pé é o **regime de comparação**, não a indisponibilidade.

### 3. O artefato do manifesto não é vendorizado — e isso *fortalece* `null`

`find cairn/gsd -name 'section-manifest*'` → **vazio**. O cache, por contraste,
traz `gsd-core/workflows/section-manifest.json` com 15 workflows keyed
(`autonomous=5, execute-phase=3, plan-phase=6, quick=5, verify-work=2`, e
**nenhuma chave `debug`** — que é exatamente por que `debug.md:31` diz "`null`
today").

Ou seja: rodando a lógica do upstream **nesta árvore**, o resultado dos 6
verbos seria `null`, porque o artefato que ele lê não está aqui. `null` deixou
de ser "o valor degradado que a especificação manda" e virou também "o valor
que o binário de referência produziria". É a justificativa mais forte que o
plano tinha disponível e ela não estava escrita nele.

### 4. Quatro checks `<automated>` do próprio plano estão errados

Todos foram substituídos por versões que preservam a intenção; nenhum foi
simplesmente ignorado.

| check do plano | por que não fecha | o que foi rodado no lugar |
|---|---|---|
| T1: `grep -c 'section_manifest' cairn-gsd-init.py` **= 6** | **insatisfazível junto com a própria `<action>` do plano**, que manda escrever no MESMO arquivo um comentário-decisão sobre o campo. Valor real: **8** (6 sítios + 2 linhas do comentário, uma delas a citação literal do gate) | `grep -cE '^ *(result\["section_manifest"\] =\|"section_manifest":)'` **= 6** (conta SÍTIO, não menção) |
| T1: laço com `init.verify-work` sem posicional | o verbo exige fase: sai `exit 1` com `[cairn-gsd-init] error: phase required` | mesmo laço com `init.verify-work 34` → os 4 verbos verdes |
| T2: `jq -r '.expect.stdout' "$f" \| jq -e …` sobre `init-*.golden.json` | o glob pega `init-execute-phase-fato-ausente` (stdout **vazio**, exit 1) e `init-plan-phase-pick` (stdout é texto cru, `opus`); o `jq` de dentro morre antes do guard `if has(...)` | mesmo laço, com o stdout testado por `jq -e .` antes de ser interpretado como JSON |
| T2: `grep -h 'section_manifest' *.golden.json \| grep -c '\[\]'` **= 0** | **insatisfazível por construção**: o stdout inteiro é UMA linha, que também carrega `\"missing_agents\": []`. O valor era **6 antes e 6 depois** da correção — o check nunca mediu o que queria medir | contagem da substring exata: `\"section_manifest\": []` → **0**; `\"section_manifest\": null` → **6** |

## O caminho exato usado para editar o campo escapado

O valor mora dentro de `.expect.stdout`, que é uma **string JSON escapada**;
`jq` sobre `.expect.stdout.section_manifest` não alcança caminho nenhum. A
edição foi textual sobre os bytes do arquivo:

```python
alvo = '\\"section_manifest\\": []'      # com a barra invertida do escape
novo = '\\"section_manifest\\": null'
raw = open(f).read()
assert raw.count(alvo) == 1              # uma ocorrência por arquivo, medida
open(f, "w").write(raw.replace(alvo, novo))
```

E a prova **não** foi por inspeção: cada arquivo foi carregado com `json.loads`
antes e depois, e o script exigiu, por arquivo:

- `provenance`, `schema_version`, `scenario` e `source` **iguais**;
- `expect.exit_code` igual;
- o stdout desescapado com `section_manifest == []` antes e `is None` depois;
- e, **removido esse campo dos dois lados, os payloads idênticos** — nenhuma
  outra chave mudou.

Resultado no disco: `6 files changed, 6 insertions(+), 6 deletions(-)` — uma
linha por arquivo, que é o arquivo inteiro do stdout.

## O recorder não foi executado — e o motivo que sobrou

`cairn-gsd-record.py` grava o golden **rodando o runtime do clone em cache** e
publica com `provenance: "recorded"`. Duas consequências, e só a segunda
sobrevive à medição:

1. ~~reintroduziria o `[]` do upstream~~ — falso (ver premissa 1: upstream
   emite `null` ou objeto).
2. **trocaria o regime de comparação.** `cairn-gsd.bats:216-237` compara
   `recorded` por BYTES; `:238-254` compara `derived-from-contract` por FORMA
   (`jq -S`, exit exato). Promover os 6 a `recorded` mudaria o runner de ramo e
   passaria a exigir byte-igualdade com um binário que este checkout não
   consegue nem buildar.

Os 6 seguem `derived-from-contract` com
`source.commit = 68a04ccf8ef74803bdb651e12c3b85b218bbccdf`, verificado por `jq`
depois da edição, e o guard de envelope (`:329-341`) e o de timestamp (`:344`)
continuam verdes dentro da suíte.

## A divergência reescrita (texto novo, na íntegra)

`tests/fixtures/gsd-goldens/divergences.json`, entrada `section-manifest-empty`
— **reescrita, não duplicada**: 55 entradas antes e depois, schema e ordenação
preservados, arquivo `jq -S` estável com newline final.

- **upstream:** `section_manifest é objeto {workflow, included, excluded, read}
  quando gsd-core/workflows/section-manifest.json existe, e null quando o
  artefato falta ou o workflow não tem chave nele (src/init.cts:459-470 da tag)`
- **cairn:** `section_manifest emitido null nos 6 bundles de init — o valor
  degradado que a camada prompt especifica como superset seguro, todos os steps
  lidos (execute-phase.md:92); o artefato gerado não é vendorizado e as seções
  vivem nos workflows sob cairn/gsd/`
- **reason:** `a composição por manifesto + steps foi PRESERVADA (D-03: achatar
  inlinaria 21 arquivos / 806 linhas nos workflows raiz para adaptar 10 de 38
  chamadas dos fragments); preencher included/excluded de verdade é incremento
  medido de outra fase, fora da 36`

O `aspect` ficou `section-manifest-empty` apesar de o nome ter envelhecido: é a
chave pela qual o `verify` do plano procura a entrada, e renomeá-la criaria uma
entrada nova aos olhos de quem grepa.

## A tabela de tipo, e por que o sétimo verbo está nela

`tests/cairn-gsd.bats` ganhou um `@test` tabular. Cada linha traz o id do
cenário e o valor esperado; **o argv sai do manifesto**
(`scenario_spec "$id" | jq -r '.argv[]'`), nunca digitado no teste.

```
init-autonomous null      init-quick        null
init-debug      null      init-verify-work  null
init-execute-phase null   init-phase-op     ausente   ← controle negativo
init-plan-phase null
```

`init.phase-op` é um verbo de init que nunca emitiu o campo. A linha `ausente`
é o lado *"a correção não espalha a chave"*, e ela é viva: a terceira quebra
abaixo a derruba. A falha nomeia o verbo e o valor que veio, não só "falhou".

## Quebras reais aplicadas (com a asserção que cada uma derrubou)

Todas com `cp` de backup e restauração **da cópia**; nunca `git checkout`.

| quebra | asserção derrubada |
|---|---|
| só o sítio de `handle_init_quick` volta a `[]` | `init-quick: section_manifest esperado null, veio []` — uma linha só, as outras 6 seguiram verdes |
| só o golden `init-debug` volta a `[]` | `cenário init-debug: stdout diverge do golden (forma json)` — o ramo derived-from-contract do runner, nomeando o cenário |
| a chave é ESPALHADA para o 7º verbo (`handle_init_phase_op` ganha `None`) | `init-phase-op: section_manifest esperado ausente, veio null` |

As três derrubaram a asserção certa na primeira tentativa. A terceira é a que
prova que o controle negativo da tabela não é decorativo: sem ela, "a correção
não espalha a chave" seria afirmação sem teste.

## Verificação

- `bats tests/cairn-gsd.bats` → **90 ok, 0 not ok, 1 skip** (o skip é o
  `--record` do corpus real, gated por runtime não buildado — pré-existente).
- `bats tests/cairn-vendoring.bats` → **26 ok, 0 not ok, 0 skip**. O oráculo
  dois-sentidos do 36-01 (`ok 22 PORCELAIN invertido: o conjunto divergente do
  cache é EXATAMENTE o registro`) segue verde e **inalterado** — nada foi
  adaptado sob `cairn/gsd/` neste plano e nenhum caminho entrou no registro.
- `bats tests/` inteiro → ver nota de execução abaixo.
- Os 4 verbos de init num fixture cru (`git init` + `.planning/config.json`
  vazio), fora do bats: `init.debug`, `init.autonomous`, `init.quick` e
  `init.verify-work 34` respondem `has("section_manifest") and
  .section_manifest == null`.
- `git status --porcelain` limpo em `cairn/` e `tests/`.

## Desvios do plano

1. **Quatro checks `<automated>` substituídos** (tabela acima). O caso mais
   grave é o T1 `grep -c … -eq 6`, que colide com a `<action>` do próprio plano:
   ou o comentário-decisão existe e nomeia o campo, ou o check fecha. Escolhido
   o comentário — a truth nº 1 do plano exige que *"o motivo medido fique
   registrado no código"* —, e o check foi trocado por um que conta sítios de
   emissão. Um check que quebra quando alguém documenta o campo é o check errado.
2. **O comentário D-03 ficou no topo da família init**, imediatamente acima do
   primeiro sítio (`handle_init_autonomous`), em vez de dentro da função. O
   plano diz "ao lado do primeiro sítio"; um bloco de 21 linhas dentro de uma
   função de 5 linhas seria pior, e no topo ele é referenciável pelos outros 5
   sítios, que apontam para ele com `# null — D-03, topo da família`.
3. **Entre o commit GREEN da Task 1 e o commit da Task 2 a suíte de goldens fica
   vermelha por construção** (o binário já emite `null`, os goldens ainda dizem
   `[]`). É a ordenação que o plano especifica; registrado por honestidade de
   histórico.

## Commits

- `2b3ccd7` test(36-02): a tabela do tipo de section_manifest — 6 verbos null, 1 ausente
- `5445480` feat(36-02): os 6 sitios de init emitem null, com D-03 escrita ao lado
- `9f2bc44` feat(36-02): os 6 goldens editados por substring e a divergencia reescrita

## A ressalva do cético, que continua inteira de pé

**Que `[]` FAÇA os 21 steps serem pulados continua sendo inferência, não
medição.** O gate é prosa lida por um modelo (`If section_manifest is null or
"<id>" is in its included list`), e um modelo pode muito bem ler `[]` como
ausência e ler tudo assim mesmo. Nada aqui mediu comportamento de leitura.

O que se corrigiu foi o **tipo**, e o tipo estava errado dos dois jeitos: `[]`
não é `null` (o valor degradado) nem objeto com `.included` (o valor computado),
`debug.md:31` declara textualmente que os dois não são a mesma coisa, e a
medição no clone da tag mostrou que nem o binário de referência produz lista em
lugar nenhum. Corrigir custou ~6 linhas.

O ganho de contexto de verdade — preencher `included`/`excluded` — **não foi
feito e não deve ser confundido com isto**: dos 21 marcadores, 10 dependem de
flags que o handler já parseia e descarta, 5 de estado já computado, e 3 são
predicados sem fonte. É incremento medido de outra fase, e misturá-lo com a
correção de tipo mataria a prova de qualquer um dos dois.

## Pendências

- **Nenhum caminho novo no registro de adaptações.** Este plano não escreveu sob
  `cairn/gsd/`; os planos 03-07 seguem com a regra do 36-01 intacta (registrar
  na MESMA task que edita).
- **Higiene do worktree, de novo:** `.cairn/journal/*.jsonl` continua fora do
  `.gitignore` e este worktree criou o seu
  (a particao deste worktree, 1 evento `lease_changed`). O nome do arquivo
  carregava o hostname da maquina; corrigido em CairnGo-xclf, e nao reproduzido
  aqui — um documento que cita o valor como evidencia o republica no mesmo
  repositorio que ele existe para limpar.
  Deixado **não rastreado**, como no 36-01. Um `git add -A` numa sessão futura o
  publicaria com o hostname da máquina.
- **`init-plan-phase-pick` e `init-execute-phase-fato-ausente`** ficaram fora
  da tabela de tipo de propósito: o primeiro emite texto cru (`--pick`), o
  segundo sai `exit 1` com stdout vazio. Nenhum dos dois carrega o campo, e
  incluí-los exigiria uma terceira coluna de forma de saída sem ganho de prova.
