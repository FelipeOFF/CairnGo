---
phase: 23-not-applicable-as-a-check-state
plan: "02"
subsystem: infra
tags: [python, bats, cli, stdlib, doctor, false-green, annotations]
requires:
  - "23-01: o status not-applicable, o campo scope e a contagem por balde"
provides:
  - "as quatro checagens que diziam a palavra em prosa agora a dizem no campo"
  - "test-parallel sem bats deixa de ser aviso e vira lacuna nomeada"
  - "as oito anotações que citavam a fase 23 quitadas"
affects:
  - "cairn/scripts/cairn-doctor.py"
  - "cairn/docs/commands/doctor.md"
  - "tests/cairn-doctor.bats"
tech-stack:
  added: []
  patterns:
    - "a mesma condição que decide a guarda de aplicabilidade decide a família"
key-files:
  created: []
  modified:
    - "cairn/scripts/cairn-doctor.py"
    - "cairn/docs/commands/doctor.md"
    - "tests/cairn-doctor.bats"
decisions:
  - "os quatro ramos de guarda são out-of-scope; só o ramo sem bats é no-input"
  - "manter nenhuma vista de cobertura é escolha de método, não lacuna"
status: complete
---

# Phase 23 Plan 02: A promoção mecânica e a quitação das anotações — Summary

Os cinco ramos que já diziam "not applicable" em prosa (ou "cannot check" em
aviso) passaram a dizê-lo no campo `status`, com a família certa; as oito
anotações que o `cairn-doctor.py` carregava prometendo esta fase saíram do
arquivo usando o estado.

## Os cinco ramos, com os números de linha reconferidos

Reconferidos na árvore **depois** das edições do plano 01 (que deslocou tudo em
~80 linhas). A coluna "T-08" traz o número que o plano previu.

| checagem | condição | linha do `return` (T-08) | linha real na execução | status antes | família travada |
|---|---|---|---|---|---|
| `release-versions` | sem `cairn/.claude-plugin/plugin.json` | 1729-1734 | 1817 | `ok` + prosa | `out-of-scope` |
| `test-parallel` | idem | 1813-1818 | 1911 | `ok` + prosa | `out-of-scope` |
| `test-parallel` | bats fora do PATH | 1846-1852 | 1944 | `warn` | **`no-input`** |
| `req-ledger` | `.planning/` sem `REQUIREMENTS.md` | 2067-2072 | 2178 | `ok` + prosa | `out-of-scope` |
| `req-ledger` | roadmap sem vista de cobertura | 2099-2105 | 2212 | `ok` + prosa | `out-of-scope` |

A tabela T-08 estava correta em conteúdo e família; só os números de linha
mudaram, como o próprio plano avisou que mudariam.

### A poda de redundância

O plano autoriza aparar a repetição quando o `detail` começa dizendo o que
agora vive no campo. Aplicado nos quatro: `"not applicable — no …"` virou
`"no …"`. Nenhum nome de arquivo, id ou rota foi tocado. O ramo sem bats não
tinha a redundância (ele diz `"bats is not on PATH — …"`), então ficou intacto.

## As oito anotações, e o que cada uma passou a dizer

As cinco que a D-05 nomeia, mais as três que a varredura de T-10 encontrou.
Números de linha do **antes** (medição do plano) e do **depois**.

| sítio | onde | quem quitou | o que passou a dizer |
|---|---|---|---|
| 242-244 | docstring do módulo, checagem 15 | este plano | `not-applicable / out-of-scope`, com o motivo de os carriers serem do cairn |
| 264 | docstring do módulo, checagem 16, ramo sem bats | este plano | `NOT-APPLICABLE / no-input`, e por que é lacuna e não escopo |
| 311 | docstring do módulo, checagem 17 | este plano | `NOT-APPLICABLE / out-of-scope`, e que manter nenhuma vista é escolha de método |
| 988, 991 | docstring de `check_claims_stale` | plano 01 | "PHASE 23 ARRIVED, AND THIS BRANCH IS `not-applicable` / `no-input`" |
| 1717-1721 | docstring de `check_release_versions` | este plano | a família e o motivo de o relatório continuar completo |
| 1808 | docstring de `check_test_parallel` | este plano | as duas famílias do mesmo check, separadas |
| 1923-1927 | comentário de `REQ_LEDGER_VOID_KIND` | este plano | por que é escopo, e que a semântica "0 = ok, ou não aplicável" continua verdadeira (T-11) |
| ladder de status de `check_req_ledger` | docstring da função | este plano | o degrau "no coverage view" passa de `"ok", not applicable` para `not-applicable / out-of-scope` |

O último não estava na lista de T-10 — é um nono sítio que a varredura do plano
não pegou porque não cita a fase pelo nome, mas descrevia o veredito antigo e
ficaria mentindo. Incluído.

**Gate mecânico:** `grep -n -i 'phase 23' cairn-doctor.py | grep -i 'is
introducing|once it lands|owns the state|owns it'` devolve vazio. As sete
menções remanescentes à fase são todas em tempo passado ("phase 23 landed",
"phase 23 gave that sentence its own status").

## Testes: cada um com a quebra que o deixa vermelho

| teste | quebra nomeada |
|---|---|
| `release-versions: a repo without cairn's plugin manifests is out-of-scope…` | marcar como `no-input` — os manifests **nunca** vão existir num repo cabeado, e chamar isso de lacuna deixaria todo repositório de usuário `INCOMPLETE` para sempre |
| `test-parallel: a repo without cairn's plugin manifest is out-of-scope…` | a mesma quebra, uma checagem adiante |
| `test-parallel: no bats at all is not-applicable/no-input…` | manter o `warn` que o 29-06 deixou como marcador — "vai ser lento" afirma um fato que a checagem nunca estabeleceu |
| `req-ledger: a roadmap with no coverage view is out-of-scope…` | chamar de lacuna uma escolha de método do projeto |
| `req-ledger: a .planning/ with no REQUIREMENTS.md is out-of-scope…` | **teste novo** — converter a guarda e deixá-la sem prova; antes deste plano nenhum teste tocava esse ramo |
| `healthy wired fixture` | tolerar valores extras no conjunto de status em vez de afirmar o conjunto ordenado; e, sobretudo, deixar de afirmar que **nenhum** dos ⊘ do fixture é lacuna |

Todas as asserções são sobre o valor exato. Os três testes de guarda que antes
afirmavam apenas sobre a prosa (`grep -qF "not applicable"`) passariam com o
status errado; agora afirmam `status` **e** `scope`.

## A saída do fixture saudável depois da conversão

O fixture é um repositório de usuário (sem os manifests do cairn), então ele é
exatamente a prova de que a fase não fabricou vermelho falso:

- `.checks | length` → `18`
- `[.checks[].status] | unique | sort | join(",")` → `not-applicable,ok`
- `.ok` → `true`
- `.failed` → `false`
- `[.checks[] | select(.status=="not-applicable" and .scope=="no-input")] | length` → `0`
- rodapé humano → `[cairn-doctor] ok`, sem nenhum `⚠` e sem nenhum `✗`

Dois `⊘`, os dois de escopo: `release-versions` e `test-parallel`. O
`req-ledger` roda de verdade nesse fixture, porque `make_gsd_fixture` escreve
um `## Traceability` em `REQUIREMENTS.md`.

## Verificação executada

**Método, e por que não foi o do plano.** O `<verify>` de cada task pede
`cairn/scripts/cairn-test.sh` sobre o arquivo inteiro. A máquina está com três
fases irmãs executando em worktrees (21, 24, 26) e carga média entre 14 e 30 em
8 núcleos; uma passada completa custou 45 min na primeira medição e passava de
2h no pico — e, mais grave, **bloqueia toda edição**, porque os testes executam
o `cairn/scripts/cairn-doctor.py` vivo. Duas tentativas de rodar a suíte
completa em segundo plano foram mortas pelo gerenciador de tarefas no meio,
corrompendo o log.

Então: verificação por run **serial dirigido** a todos os testes que tocam as
superfícies alteradas, e **uma** passada completa pelo runner da casa no fim da
fase, cobrindo os quatro planos. O resultado dessa passada está no
`23-SUMMARY.md`.

Run dirigido deste plano — filtro
`release-versions|test-parallel|req-ledger|healthy wired|report footer|claims-stale|status vocabulary`:

```
1..29
ok:     29
not ok: 0        EXIT=0
```

**29 anunciados, 29 executados**, contados com `grep -c` sobre o log inteiro
(`/tmp/t02.log`), nunca sobre saída truncada.

Gates automatizados do plano, todos verdes:

- `[.checks[]|select(.status=="not-applicable" and (.scope|not))]|length == 0`
- a busca por menção à fase 23 em tempo futuro devolve 0
- `**release-versions**`, `**test-parallel**` e `**req-ledger**` presentes na
  página, com `out-of-scope` e `no-input` escritos nela

## Deviations from Plan

### 1. [Rule 2 — cobertura ausente] O ramo sem `REQUIREMENTS.md` não tinha teste

- **Encontrado durante:** Task 1, ao mapear os testes de guarda.
- **Achado:** o plano lista quatro testes de guarda a alterar. São quatro
  ramos com teste e **um sem**: `req-ledger` com `.planning/` sem
  `REQUIREMENTS.md` nunca foi exercitado pela suíte.
- **Ação:** teste novo, com a quebra nomeada. Converter uma guarda e deixá-la
  sem prova é promover algo que ninguém percebe regredir.
- **Commit:** 2b7f72e

### 2. [Rule 2] Um nono sítio de anotação, fora da lista de T-10

- **Achado:** o "status ladder" no docstring de `check_req_ledger` escrevia
  `no coverage view in this repo at all -> "ok", not applicable`. Não cita a
  fase pelo nome, então a varredura de T-10 não o pegou, mas descrevia o
  veredito antigo e ficaria mentindo.
- **Ação:** atualizado junto.

### 3. [Sobreposição de tasks, sem conflito] Os três sítios do docstring do módulo saíram na Task 1

O `read_first` da Task 2 lista `cairn-doctor.py:240-244`, `:264` e `:311` como
trabalho dela. Eles fazem parte da varredura de anotações que a Task 1 manda
quitar "dentro dos mesmos arquivos que a conversão toca", então saíram lá. A
Task 2 ficou só com a página — que era o conteúdo novo de verdade.

## Threat Flags

Nenhuma superfície nova. Nenhum pacote instalado.

## Known Stubs

Nenhum.
