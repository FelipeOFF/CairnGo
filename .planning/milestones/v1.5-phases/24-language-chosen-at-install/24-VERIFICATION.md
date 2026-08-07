---
phase: 24-language-chosen-at-install
verified: 2026-08-06T21:43:31Z
status: gaps_found
score: 2/3 critérios verificados, 2/2 requisitos entregues
behavior_unverified: 1
behavior_unverified_items:
  - truth: "Critério 3 do roadmap — rodar `/cairn:init` de novo num projeto que já respondeu não pergunta e não escreve"
    test: "Num projeto com `.cairn/config.json:agents.response_language` já setado, executar `/cairn:init` uma segunda vez e observar o passo 3.5"
    expected: "Nenhuma pergunta é feita; nenhum arquivo de config é escrito; o comando diz em uma linha qual escolha já existe e segue"
    why_human: "O ramo é condicional e é executado pelo modelo, não por script: o teste que existe (`tests/cairn-init.bats:97-111`) prova que a instrução está escrita no arquivo de comando, não que o ramo foi tomado. Nenhum bats spawna `/cairn:init`"
human_verification: []
overrides_applied: 0
gaps:
  - truth: "O registro de fechamento da fase afirma sobre a diretiva do GSD o que é mensuravelmente falso"
    status: failed
    reason: "`24-SUMMARY.md` diz, em dois lugares, que a diretiva padrão do GSD manda *não* repassar `response_language` ao subagente, citando *\"subagent prompts stay in English\"* como se fosse isso. Medido por mim nesta máquina: dos 47 arquivos de `~/.claude/gsd-core/workflows/` que mencionam `response_language`, 43 carregam essa cláusula — e ela é sobre o TEXTO do prompt, nunca sobre o valor; 2 arquivos (`references/execute-phase-response-language.md`, `workflows/plan-phase.md`) mandam explicitamente *\"Pass `response_language: {value}` into every spawned subagent prompt\"*; ZERO arquivos dizem para não repassar o valor. A premissa é a viga que sustenta o veredito 'LANG-02 parcial' do próprio SUMMARY, e a correção já está registrada na `bd show CairnGo-4ia` desde 2026-08-05"
    artifacts:
      - path: .planning/phases/24-language-chosen-at-install/24-SUMMARY.md
        issue: "L35-37 ('Na maioria dos pontos de spawn, a regra escrita era **não** repassar') e L221 ('a diretiva padrão do GSD manda literalmente *não* repassar')"
      - path: .planning/phases/24-language-chosen-at-install/24-CONTEXT.md
        issue: "L44-49 — a origem da leitura invertida, citada como medição"
    missing:
      - "Corrigir as duas frases do `24-SUMMARY.md` para o que a diretiva diz lida inteira, com a citação de `references/execute-phase-response-language.md:3`"
      - "Registrar no `24-SUMMARY.md` a medição que a substitui (43 arquivos com a cláusula sobre o texto do prompt, 2 mandando repassar o valor, 0 proibindo)"
  - truth: "O SUMMARY da fase é o único artefato que ainda declara LANG-02 incompleta"
    status: failed
    reason: "O frontmatter do `24-SUMMARY.md` diz `LANG-02: partial` e o corpo diz 'LANG-02 — parcial, e a issue `CairnGo-4ia` fica aberta'. Medido agora: `CairnGo-4ia` está CLOSED (2026-08-05), com o critério reescopado no motivo de fechamento; `.planning/REQUIREMENTS.md:36` marca LANG-02 `[x]` com o texto reescopado (commit `d8f1ba5`, 'docs(24): LANG-02 reescopado para o lifecycle do cairn'); e `.planning/ROADMAP.md:39` marca a fase completa. Quem abrir a pasta da fase lê que ela não entregou o que entregou"
    artifacts:
      - path: .planning/phases/24-language-chosen-at-install/24-SUMMARY.md
        issue: "L16 (`LANG-02: partial`) e L196-222 (a seção 'parcial', escrita contra o critério antigo)"
    missing:
      - "Atualizar `requirements_status.LANG-02` para `complete` no frontmatter do SUMMARY"
      - "Reescrever a seção de requisitos contra o critério vigente do `REQUIREMENTS.md`, preservando — porque continua verdadeiro e é o que dá honestidade ao registro — que os dois pontos de spawn do cairn têm provas de força diferente"
---

# Fase 24: Language chosen at install — Relatório de verificação

**Card:** a linguagem de resposta deixa de ser algo que alguém descobre no meio de
um ciclo.
**Verificado:** 2026-08-06T21:43:31Z
**Veredito:** gaps_found
**Re-verificação:** não — verificação inicial (não havia `24-VERIFICATION.md`)

O veredito não vem do SUMMARY. Vem de quatro medições feitas nesta árvore: os dois
arquivos de teste da fase rodados com log inteiro em disco, uma reprodução
independente da precedência lida na saída do processo, uma chamada direta às três
saídas do check do doctor, e uma contagem sobre os arquivos do GSD instalados nesta
máquina.

**O código entrega o que a fase prometeu.** As duas lacunas abaixo são do registro
escrito da fase, não do mecanismo: o `24-SUMMARY.md` sustenta uma premissa que é
mensuravelmente falsa e conclui, a partir dela, que LANG-02 ficou parcial — quando o
critério vigente, a issue e o `REQUIREMENTS.md` dizem o contrário desde 2026-08-05.

## Verdades observáveis

| # | Verdade (critério do ROADMAP) | Estado | Evidência |
|---|---|---|---|
| 1 | `/cairn:init` pergunta a linguagem e grava a escolha, com inglês como default explícito — nunca um default implícito por omissão | ✓ VERIFICADO | `cairn/commands/init.md:134-176` é o passo 3.5, e ele está **antes** do hand-off (`init.md:195`, `## 6. Hand off`) — comparação de números de linha em `tests/cairn-init.bats:82`, verde. "English is the default, and it is pre-selected" é asserção de string (`cairn-init.bats:98`). O default é explícito **no mecanismo**, não só na prosa: medido por mim, `get agents.response_language --json` num diretório limpo devolve `{"value": "English", "source": "default"}` — uma chave ausente e uma escolha por inglês não são indistinguíveis |
| 2 | Um teste lê o valor **no ponto de entrega ao subagente**, não na config | ✓ VERIFICADO | `tests/cairn-parallel.bats:231-313` **executa** `bash "$PARALLEL" prepare 2 --json` e assere sobre `$output` — a saída do processo — em quatro estados. Ver a auditoria abaixo, que é o ponto que decide a fase. Testes 6, 7, 8 e 9 do arquivo, verdes |
| 3 | Um projeto já instalado não é alterado sem pedido; rodar o init de novo é idempotente e não sobrescreve escolha existente | ⚠️ PRESENTE, COMPORTAMENTO NÃO PROVADO | O mecanismo está presente e ligado: `init.md:148-152` decide pelo `source` do `get --json` (`file`/`planning` ⇒ "do not ask, and do not write anything"), e `cairn-config.sh set` é idempotente por construção (teste 17, "a second set replaces GSD's value instead of duplicating the key", verde; reproduzi: a chave do GSD fica com uma ocorrência só). A metade de script é provada em comportamento (`cairn-init.sh` re-executado: testes 35, 39, 40, verdes). A metade da língua é um **ramo condicional executado pelo modelo**: o teste prova que a instrução está no arquivo, não que o ramo foi tomado |

**Score:** 2/3 critérios verificados (1 presente sem prova de comportamento).

## A auditoria do critério 2 — o ponto que decide a fase

O requisito existe para distinguir um teste que lê a config de um teste que lê a
entrega. Um que lesse a config ficaria verde nos quatro estados e não provaria nada,
porque o defeito do v1.4 aconteceu **com a chave presente e correta**. Então
conferi a cadeia inteira, e não a alegação.

**O teste executa o script.** `tests/cairn-parallel.bats:241`, `:265`, `:279`,
`:296`: `run bash "$PARALLEL" prepare 2 --project-dir "$MAIN_ROOT" --json`. O que os
testes escrevem em `.cairn/config.json` e `.planning/config.json` antes disso é
**setup**, não asserção.

**A asserção é sobre `$output`.** `assert_json_eq` (`tests/helpers.bash:580-588`)
faz `jq -r "$filter" <<<"$json"` sobre a **string passada**, e a string passada é
`$output` do bats — stdout do processo. Não há nenhum `assert_json_eq` sobre um
caminho de arquivo nesses quatro testes. A render humana é conferida do mesmo jeito:
`grep -qF "response language: Portuguese" <<<"$output"` (`:254`) e
`grep -qF "response language: unavailable" <<<"$output"` (`:312`).

**O payload é o que o montador do prompt lê.** `cairn-parallel.py:1004-1005` põe
`response_language` e `response_language_source` na saída de `prepare`;
`cairn/commands/autonomous.md:216-222`, dentro do bloco delimitado
`SUBAGENT-PROMPT-BEGIN/END`, manda copiar o valor **daquela saída** —
"copied literally — read from the output, never remembered and never inferred from
the repository" — e trata `null` mandando declarar em vez de adivinhar.

**Reprodução independente**, feita por mim num diretório temporário, sem os fixtures
do bats, chamando o mesmo resolvedor que `prepare` chama:

```
vazio            → {"value": "English",    "source": "default"}
só cairn         → {"value": "Portuguese", "source": "file"}    propagated: false (planning-config-absent)
GSD por cima     → {"value": "Japanese",   "source": "planning"}
set com .planning/config.json existente → propagated: true, e o arquivo sai
                   {"a": 1, "response_language": "Korean"} — a chave "a" continua na frente
```

Duas coisas caem junto com essa medição: a precedência é a declarada, e a
propagação **não cria** `.planning/` (no estado "só cairn" o diretório não existia e
continuou não existindo — tive de criá-lo à mão para chegar ao terceiro estado), que
é a proibição que `init.md:153` e as medições M-1/M-2 do CONTEXT sustentam.

**Conclusão:** a alegação da fase resiste. O teste lê o valor na saída do processo.

## LANG-02 com o critério vigente

O texto que vale é o do `REQUIREMENTS.md:36`, reescopado no commit `d8f1ba5`: a
escolha alcança todo subagente spawnado pelo lifecycle **do cairn**, provado por
teste que lê o valor na saída do processo; o repasse dentro dos workflows do GSD é
dependência externa e está fora do escopo.

**O inventário, remedido por mim** (`grep -rln "subagent\|[Ss]pawn"` sobre
`cairn/commands/`, `cairn/skills/`, `cairn/capability/fragments/`): quatro arquivos —
`autonomous.md`, `reconcile.md`, `config.md`, `init.md`. Conferi as ocorrências dos
dois últimos uma a uma: são prosa descrevendo a chave (`config.md:63,74`;
`init.md:134,137,139,140,157,211`), nenhuma spawna. Pontos de spawn reais: **dois**.

| ponto de spawn | onde o valor é entregue | teste que lê essa saída | força |
|---|---|---|---|
| `autonomous.md` passo 3 | stdout de `cairn-parallel.py prepare --json` | `tests/cairn-parallel.bats:231-313`, quatro estados de precedência + a render humana | alta — o valor é lido na saída, e `tests/cairn-parallel-autonomous.bats:172-209` assere sobre a **região** do bloco do prompt (não sobre o arquivo) que ele é copiado de lá |
| `reconcile.md:59` | stdout de `cairn-config.sh get agents.response_language` | `tests/cairn-config.bats:222-330` executa exatamente esse comando e assere sobre `$output` nos estados default/file/planning e nos degradados | média — a saída é provada, mas por um teste que não é daquele caminho; o que é daquele caminho (`tests/cairn-reconcile-agent.bats:180`) assere **ordem de linhas** no `.md` |

Nos dois casos a última perna — o modelo colar o valor no prompt do Task tool — não
é testável por bats, e nenhum teste da fase afirma o contrário. Isso está escrito no
`CHANGELOG.md:43-46` e no cabeçalho de `tests/cairn-parallel.bats:212-227`, o que é
o comportamento correto.

**Veredito do requisito:** entregue. E vale dizer o que o registro da fase não diz:
o caminho do `reconcile` satisfaz o critério porque o processo que ele lê é o mesmo
`cairn-config.sh get` cuja saída `tests/cairn-config.bats` assere — não porque
alguém tenha desenhado a prova assim. A força das duas provas é diferente, e um
teste que executasse o `get` de dentro do arquivo do reconcile fecharia a diferença.

## Cobertura de requisitos

| Requisito | Plano | Estado | Evidência |
|---|---|---|---|
| **LANG-01** — `/cairn:init` pergunta a linguagem e grava a escolha na config local, com inglês como default | 24-02 | ✓ ENTREGUE | Passo 3.5 antes do hand-off, com posição provada por comparação de linhas; inglês pré-selecionado e nomeado; escrita só por `cairn-config.sh set` (asserção de contagem exata zero para `config-set response_language`, `cairn-init.bats:112-126`). Issue `CairnGo-0rk` fechada |
| **LANG-02** — a escolha alcança todo subagente do lifecycle do cairn, provado na saída do processo | 24-01, 24-03 | ✓ ENTREGUE | Ver a seção acima. Issue `CairnGo-4ia` fechada em 2026-08-05 com o critério reescopado |

Nenhum requisito órfão: `REQUIREMENTS.md` mapeia LANG-01 e LANG-02 à fase 24, e os
dois aparecem nos planos.

## A rede: o check do doctor

Fora do escopo de execução que me foi dado (`tests/cairn-doctor.bats` não foi
rodado — e o próprio SUMMARY declara aquele arquivo **não medido**, o que é honesto),
então chamei `check_response_language()` diretamente, três estados:

```
concordam    → ok    "'Korean' in both .cairn/config.json and .planning/config.json"
divergem     → warn  "the two disagree: .planning says 'Japanese', .cairn says 'Korean'.
                      GSD's key governs, so every subagent answers in 'Japanese'"
nunca chegou → warn  "'Korean' was chosen at install but never reached
                      .planning/config.json:response_language"
```

`warn` e nunca `fail`, com o comando exato de fechamento nos `items` — como o plano
24-03 declarou. Ligado em `cairn-doctor.py:3068`.

## Suíte executada

Somente os arquivos da fase, uma invocação por linha, log inteiro em disco, contado
com `grep -c` sobre o arquivo completo e com a marca de fim conferida. Nenhum
`Executed N instead of expected M` em nenhum dos dois.

| invocação | anunciado | `ok` | `not ok` | `EXIT=` |
|---|---|---|---|---|
| `cairn-test.sh --jobs 3 tests/cairn-config.bats tests/cairn-init.bats` | `1..40` | 40 | 0 | 0 |
| `cairn-test.sh --jobs 3 tests/cairn-parallel.bats` | `1..41` | 41 | 0 | 0 |

Os 40 da primeira invocação se dividem exatamente como o SUMMARY diz — 29 do
`cairn-config.bats` (`ok 1`..`ok 29`) e 11 do `cairn-init.bats` (`ok 30`..`ok 40`),
conferido contra `grep -c '^@test'` nos dois arquivos: 29 e 11. Escrevi 28 + 12 numa
primeira leitura, olhando um trecho do log em vez do log inteiro, e a contagem por
arquivo desmentiu. Fica registrado porque é o erro de método que a regra desta
verificação existe para evitar.

Os testes da fase, nominalmente verdes: `cairn-config.bats` 9-21 (a chave, a
precedência, a validação, a propagação e a preservação de ordem),
`cairn-init.bats` 30-33 (posição, default explícito, idempotência escrita, a página
de doc), `cairn-parallel.bats` 6-9 (os quatro estados no ponto de entrega).

## Anti-padrões

Varredura sobre as linhas **acrescentadas** pelos 11 commits da fase
(`git diff c2cf776~1 2402e18`) nos sete arquivos de código e comando:
`TODO`, `FIXME`, `XXX`, `TBD`, `HACK`, `PLACEHOLDER`, "not yet implemented" —
**zero ocorrências**. Nenhum retorno vazio decorativo: os quatro `return` do
degradado em `config_language()` (`cairn-parallel.py:1096-1126`) são o estado
`unavailable` que o teste 9 assere, não stub.

## Lacunas

Duas, ambas no registro escrito da fase, ambas com o mesmo pai.

**1. A premissa invertida sobre a diretiva do GSD.** O `24-SUMMARY.md` afirma
(L35-37 e L221) que a diretiva padrão do GSD manda *não* repassar o
`response_language`, citando *"subagent prompts stay in English"*. Medi:

```
arquivos de ~/.claude/gsd-core/workflows/ que mencionam response_language   47
  … que carregam "subagent prompts stay in English"                         43
arquivos do gsd-core que mandam "Pass `response_language: {value}` …"         2
  (references/execute-phase-response-language.md, workflows/plan-phase.md)
arquivos que dizem para NÃO repassar o valor                                  0
```

A cláusula é sobre o **texto** do prompt — a mesma linha 3 do
`execute-phase-response-language.md` que a contém termina mandando *"Pass
`response_language: {value}` into every spawned subagent prompt"*. As duas coisas
convivem porque falam de coisas diferentes: o prompt é escrito em inglês, e o valor
é passado dentro dele. Ler "não repassar" ali é inverter a diretiva, e é dela que
sai o veredito "LANG-02 parcial" do SUMMARY. A correção já está escrita na
`bd show CairnGo-4ia` desde 2026-08-05; o SUMMARY não a incorporou.

**2. O SUMMARY é o único artefato que ainda diz que LANG-02 não fechou.** Frontmatter
`LANG-02: partial` (L16) e seção "LANG-02 — parcial, e a issue `CairnGo-4ia` fica
aberta" (L196). Contra: `CairnGo-4ia` CLOSED, `REQUIREMENTS.md:36` com `[x]` e o
texto reescopado, `ROADMAP.md:39` com a fase completa. O SUMMARY foi escrito contra
o critério antigo e ficou parado ali.

Nenhuma das duas toca o mecanismo. Quem executar o código pega a língua certa; quem
ler a pasta da fase é informado errado sobre por quê.

## O que não consegui verificar

- **A idempotência do init em execução real** (critério 3). É ramo condicional
  executado pelo modelo; nenhum bats spawna `/cairn:init`. Está registrado em
  `behavior_unverified_items` com o que testar.
- **`tests/cairn-doctor.bats`, `tests/cairn-parallel-autonomous.bats`,
  `tests/cairn-reconcile-agent.bats` e `tests/cairn-reconcile.bats`** — fora do
  escopo de execução desta verificação (três fases rodando em paralelo nesta
  máquina de 8 núcleos). Li os três estaticamente e chamei o check do doctor
  diretamente, mas **não** estou chamando aqueles arquivos de verdes.
- **O modelo colar o valor no prompt do Task tool**, nos dois pontos de spawn. É a
  fronteira que a própria fase declara, e ela está declarada corretamente.

Uma imprecisão menor, sem peso de lacuna: a citação `tests/cairn-parallel.bats:231-305`
que aparece no SUMMARY e na issue corta o quarto teste no meio — o bloco vai até a
linha 313.

---

_Verificado: 2026-08-06T21:43:31Z_
_Verificador: Claude (gsd-verifier)_
