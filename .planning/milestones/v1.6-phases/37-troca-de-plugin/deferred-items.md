# Fase 37 — itens fora de escopo, encontrados durante a execução

Achados que a onda que os encontrou NÃO consertou, por estarem fora do escopo do
plano dela. Cada um traz a medição que o sustenta.

## 1. Dez comandos ainda nomeiam verbos GSD que o plugin não carrega (onda 1)

**Medido 2026-08-12**, depois da conversão dos 13 e do retarget do ciclo central:

| Comando | Verbos externos que ainda nomeia |
|---|---|
| `new` | `new-project` |
| `milestone` | `new-milestone`, `complete-milestone`, `plan-phase`¹ |
| `ship` | `ship` |
| `migrate` | `new-project`, `new-milestone`, `onboard`, `ingest-docs` |
| `progress`, `status` | `progress` |
| `config`, `sync-config` | `config` |
| `help` | `/gsd:` genérico |
| `gsd` | `/gsd:` — **é o passthrough, e é intencional** (D-05) |

¹ `plan-phase` É vendorizado; a menção em `milestone.md` é prosa, não passo.

O fecho da fase 32 cortou o runtime em **8 verbos** (`ls cairn/gsd/commands/gsd/`
→ 8 arquivos). Nenhum dos verbos da tabela — exceto `plan-phase` — está entre
eles, e depois desta fase nenhum deles resolve numa instalação limpa.

**Por que não foi consertado aqui:** PLUG-01 nomeou **os 13 wrappers formais**
(frontmatter `wraps:`), e nenhum destes carrega essa chave. A onda 1 já
estendeu o escopo uma vez, por Rule 2, para `plan`/`work`/`verify`/
`autonomous`/`quick` — sem isso o card da própria fase ("máquina nova instala só
o cairn e **fecha um ciclo**") seria falso. Estender uma segunda vez, para 10
comandos e 8 contratos novos, é reabrir a fase, não fechá-la.

**Ação:** é a decisão que o research já previu — "a decisão sobre os 54 comandos
não-wrapped vira decisão de vendorizar ou descartar, nunca silêncio". A fase 38
mede paridade ponta a ponta num repositório limpo e é lá que a lacuna aparece
com dado. `cairn/docs/gsd-core-commands.md` carrega a nota de premissa que a
antecipa.

`init.md` aparece na medição bruta mas **não** nesta tabela: ele é reescrito
pelo plano 37-02 (PLUG-03).

## 2. Remoção física de `cairn/capability/` (onda 2, D-04)

O bundle é arquivado, não deletado. Removê-lo cascatearia em quatro frentes,
medidas antes da decisão: `cairn-capability.py` (721 linhas), o check 15
`release-versions` (que lê `cairn/capability/capability.json` como eixo semver
próprio), `tests/capability.bats` e `tests/cairn-capability.bats`.

**Ação:** candidata a fase posterior, depois que a fase 38 provar que nada mais
lê o bundle em runtime.

## 3. Profundidade dos 12 contratos inline (onda 1, D-01)

Os 12 contratos escritos nos comandos são mais finos que os workflows upstream
que substituem. É regressão de profundidade de prompt, aceita conscientemente
para fechar a janela de coexistência.

**Ação:** o gate de paridade da fase 38 mede; aprofundar é trabalho com dado,
não com impressão.

## 4. Dívida herdada da fase 36 que já estava fechada (onda 1)

O item 3 de `36/deferred-items.md` (rota de `export-identity` ausente em
`cairn/docs/commands/doctor.md`, teste 54 vermelho) **já estava resolvido** ao
início desta fase: `grep -c export-identity cairn/docs/commands/doctor.md` → 1 e
`tests/cairn-command-surfaces.bats` sai 0. Registrado para que o plano 03 não
"conserte" o que já está de pé.
