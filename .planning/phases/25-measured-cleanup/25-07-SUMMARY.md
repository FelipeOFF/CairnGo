---
phase: 25-measured-cleanup
plan: "07"
beads: [CairnGo-026]
status: complete
---

# Fase 25 Plano 07 — resumo

## O que mudou

`cairn/commands/doctor.md` — o prompt que o agente lê para explicar o
`/cairn:doctor` — passa a conhecer os **quatro** estados do relatório, as duas
famílias de `not-applicable`, o veredito `INCOMPLETE` e a razão de ele sair com
`0`. O roteamento por checagem deixa de ser uma cópia parcial e passa a
endereçar a única tabela completa que existe. Arquivo de teste novo,
`tests/cairn-command-surfaces.bats`, para as superfícies de prompt — que não
têm par `.py` e por isso não cabiam em nenhum `tests/<basename>.bats`.

## O defeito, e a asserção que o fecha

| Defeito | Medição (2026-08-07, contra `b9fdfb3`) | Teste |
|---|---|---|
| O prompt ensinava três símbolos | `one ✓/⚠/✗ line per check` na linha 25, contra `SYMBOL` de quatro chaves em `cairn-doctor.py:614` | `the doctor prompt teaches all four statuses, not three` |
| `INCOMPLETE` não existia no prompt | `grep -c INCOMPLETE` → `0`; o script imprime o veredito em `cairn-doctor.py:3506` | `the doctor prompt knows the INCOMPLETE verdict and that it exits 0` |
| 12 dos 21 ids sem tratamento nenhum | cruzamento do `--json` contra o texto: `bd-version, gsd-capability, phase-corroboration, phase-artifacts, external-ref, lease-stale, release-versions, test-parallel, req-ledger, response-language, phase-landed, plan-counters` | `the doctor prompt addresses the routing table instead of copying it` + `every check id the doctor reports has an entry in the routing table` |
| Risco de nascer o sexto número à mão | cinco precedentes medidos no repositório | `no cairn command prompt writes a check count by hand` |

Cinco testes, quatro deles vermelhos contra o `b9fdfb3` antes do conserto.

## A decisão que vale registrar: endereço em vez de cópia

O critério pedia "todo id tem tratamento na página". Havia duas saídas, e a
escolha foi a segunda:

1. copiar as 21 entradas de remediação para dentro do prompt;
2. o prompt endereçar a tabela que já é completa.

Medido: `cairn/docs/commands/doctor.md` já carrega **21 de 21** ids, com
símbolo, família de `⊘` e ação — e é um superconjunto do que o prompt
carregava (a linha `bd create` do `req-issue`, por exemplo, está lá inteira).
Medido também que o plugin instalado embarca a página:
`~/.claude/plugins/cache/cairngo/cairn/1.5.0/docs/commands/doctor.md` existe,
então `${CLAUDE_PLUGIN_ROOT}/docs/commands/doctor.md` é endereço válido em
runtime, não só no repositório.

A saída 1 criaria duas listas à mão que precisam concordar — a forma exata dos
cinco precedentes. E ela nasceria errada neste ciclo: a outra frente está
acrescentando a 22ª checagem agora. Com o endereço, o teste de cobertura passa
a cobrar a entrada **no arquivo de quem acrescentou a checagem**, que é onde a
cobrança pertence.

O prompt não escreve número de checagem em lugar nenhum, e o teste 5 varre
`cairn/commands/*.md` inteiro para que nenhum outro escreva.

## As quebras guardadas, e a asserção que cada uma derrubou

| Quebra | Onde | Asserção vermelha |
|---|---|---|
| A tabela de roteamento perde a entrada de um id (`plan-counters`) | **cópia** da tabela, via a seam `CAIRN_DOCTOR_ROUTING` | `every check id the doctor reports has an entry in the routing table` — `check id(s) with no entry (…): plan-counters` |
| O prompt perde o quarto símbolo (`⊘` → `-`) | `cairn/commands/doctor.md`, restaurado de `cp` | `the doctor prompt teaches all four statuses, not three` |

A primeira quebra rodou sobre uma **cópia** porque
`cairn/docs/commands/doctor.md` é da outra frente nesta fase: a seam
`CAIRN_DOCTOR_ROUTING` foi criada exatamente para provar a asserção sem tocar
no arquivo dela. A segunda foi quebra real no fonte, restaurada de cópia `cp`
— nunca `git checkout <arquivo>`.

## Premissas que a medição contradisse

1. **A issue diz "roteia so 9 das 19 checagens".** São **21** hoje, não 19 — a
   `phase-landed` e a `plan-counters` entraram depois de a issue ser aberta.
   O número na issue já tinha envelhecido, que é o próprio defeito que ela
   descreve, uma superfície acima.
2. **A issue pede que a página "roteie as 19 checagens".** A página que já as
   roteia todas existe e não é essa: `cairn/docs/commands/doctor.md` cobre
   21/21. A lacuna não era falta de roteamento no projeto, era um prompt com
   uma cópia parcial ao lado da tabela boa.
3. **O `--json` não carrega veredito.** As chaves do topo são `ok`, `failed`,
   `applicable`, `counts`, `note`, `active_phase`, `milestone`. Quem lê o JSON
   precisa **derivar** FAIL/INCOMPLETE/ok de dois booleanos, e nenhuma
   superfície dizia isso — o prompt agora diz.

## Fora de escopo, e por quê

`cairn/docs/commands/doctor.md` não foi tocado: pertence à outra frente desta
fase, que está acrescentando uma checagem a ele agora.
