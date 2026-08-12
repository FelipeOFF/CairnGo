---
phase: 38-paridade-e-gate
plan: 03
subsystem: comandos
tags: [paridade, doctor, gate, registro]
requires:
  - 38-02 (o scanner e os verbos servidos)
  - tests/helpers.bash (make_tmp_repo, make_gsd_fixture)
  - seam CAIRN_INSTALLED_PLUGINS (cairn-capability.py)
provides:
  - cairn/gsd-parity.json — a decisão vendorizar-ou-descartar registrada e travada
  - a bateria do repositório novo — ciclo, doctor limpo, gate verde, com controles
affects:
  - cairn/commands/ (9 arquivos)
  - tests/cairn-parity.bats
  - tests/cairn-standalone.bats
tech-stack:
  added: []
  patterns: [allowlist travada nos dois sentidos; todo verde acompanhado do seu vermelho]
key-files:
  created:
    - cairn/gsd-parity.json
    - tests/fixtures/parity/installed_plugins.json
    - tests/fixtures/parity/installed_plugins_with_gsd.json
  modified:
    - cairn/commands/new.md
    - cairn/commands/init.md
    - cairn/commands/ship.md
    - cairn/commands/milestone.md
    - cairn/commands/progress.md
    - cairn/commands/status.md
    - cairn/commands/config.md
    - cairn/commands/migrate.md
    - cairn/commands/help.md
    - tests/cairn-parity.bats
    - tests/cairn-standalone.bats
key-decisions:
  - "D-01 aplicada: descartar, não vendorizar — com o custo medido escrito no registro"
  - "o registro mora em cairn/gsd-parity.json, fora da árvore vendorizada, que é guardada por manifesto"
  - "o oráculo de imutabilidade da 37 mede a JANELA da 37, não ..HEAD"
metrics:
  duration: 58min
  completed: 2026-08-12
status: complete
---

# Phase 38 Plan 03: O repositório novo, e a dívida dos dez comandos Summary

**Um repositório construído do zero, sem `gsd-core` instalado, fecha o ciclo, sai 0 no
doctor sem uma falha nem um aviso, e verde no gate — e os dez passos que mandavam rodar
verbo inexistente pararam de mandar.**

## A decisão da dívida (D-01): descartar, com o custo medido

Os 8 verbos fora do ciclo (`new-project`, `new-milestone`, `complete-milestone`, `ship`,
`onboard`, `ingest-docs`, `progress`, `config`) **não** são vendorizados. Os arquivos de
comando upstream são pequenos (24-143 linhas), mas cada um puxa seu workflow, e os
workflows puxam references, templates e subagentes; o vendor de hoje tem 184 arquivos e
1,9 MB para 8 verbos, e entre os 8 novos estão `new-project` e `onboard`, que abrem seus
próprios subagentes. É ordem de grandeza de dobrar a árvore vendorizada, e cada arquivo
novo é superfície de deriva contra o pin v1.10.0. Isso é um milestone, não o fecho de um.

Descartar produziu três coisas, nenhuma delas silêncio:

1. **Os 10 passos foram reescritos.** Cada um diz agora, na cara, que o cairn não
   vendoriza aquele verbo, e nomeia as duas rotas: `/cairn:gsd <verbo>` para quem tem um
   plugin GSD instalado ao lado, ou o caminho manual. Onde existia comando cairn
   equivalente (`/cairn:config`, `/cairn:progress`, `/cairn:plan`), o passo passou a
   apontá-lo.
2. **As 11 menções que sobraram estão registradas** em `cairn/gsd-parity.json`, com
   disposição de vocabulário fechado, motivo e — para `descartado` — o substituto.
3. **O registro é travado nos dois sentidos:** menção sem entrada reprova, e entrada sem
   menção também. Uma allowlist que só cresce vira silêncio com carimbo.

## O repositório novo (PAR-02/03/04)

Construído do zero e ligado como `/cairn:new` manda — uma issue por requisito com o par
de labels e o carimbo `gsd`, as issues da fase completa fechadas, os mapas gerados. Um
repositório mal ligado sairia sujo por estar mal ligado, e o teste estaria medindo o
fixture.

| Pergunta | Resultado |
|---|---|
| os 4 comandos do ciclo apontam só caminhos que existem no plugin | sim, e nenhum nomeia `/gsd:` |
| os 8 verbos do ciclo respondem ali | sim, na ordem do ciclo |
| doctor | **exit 0** — 19 ok, 5 não-aplicáveis, 0 aviso, 0 falha |
| gate | **exit 0** |

A ordem dos verbos é load-bearing e virou comentário no teste: os bundles `init.*` compõem
o FATO de estado pelo irmão de estado, cujo portador vive no bd e nasce em `begin-phase`.
Antes disso a falha nomeada é propagada (CORE-04) — medido, e está certo que seja.

## Os controles (todo verde acompanhado do seu vermelho)

- **gate:** issue reaberta numa fase completa → **exit 6**, nomeando `par-001`.
- **doctor:** o **mesmo** repositório, o mesmo comando, só a lista de plugins troca →
  **exit 7**, com `an external GSD plugin is still installed` e a prescrição de
  `uninstall`. Sem este par, "limpo sem gsd-core instalado" não teria como ser falso.

## Deviations from Plan

**1. [Rule 1 - Bug] O registro não podia morar em `cairn/gsd/`**

- **Encontrado em:** Task 1, ao rodar `tests/cairn-vendoring.bats`
- **Issue:** `cairn/gsd/` é a árvore vendorizada e é guardada por manifesto nos dois
  sentidos; `parity.json` ali dentro é arquivo que o MANIFEST não conhece
- **Fix:** movido para `cairn/gsd-parity.json`, ao lado de `cairn/gsd-adaptations.json`,
  que é o precedente da casa
- **Commit:** `e98f351`

**2. [Rule 1 - Bug] O oráculo de imutabilidade da fase 37 media até `..HEAD`**

- **Encontrado em:** Task 1, ao rodar `tests/cairn-standalone.bats`
- **Issue:** o teste que prova que a troca de plugin não migrou dado nenhum comparava
  `base..HEAD` e por isso passou a acusar os arquivos da **fase 38** — trabalho que a 37
  nunca prometeu não fazer. A base já era derivada; a ponta não era.
- **Fix:** a ponta passou a ser derivada também — o último commit que tocou o diretório
  da fase 37. A garantia é sobre a troca, então a janela é a da troca.
- **Commit:** `e98f351`

**3. [Rule 2] `help.md` prometia delegação que a fase 37 tinha acabado**

- **Encontrado em:** Task 1, ao classificar as menções
- **Issue:** a página do `/cairn:help` mandava descrever os 13 como "delegating to
  `/gsd:<wraps>`" e dizia que cada um "recusa começar quando o comando GSD não está
  instalado". Desde a 37 nenhum deles delega: cada um é `inline` ou `vendored`. Era
  superfície afirmando o que não tinha como corroborar — o critério de honestidade do
  ciclo, aplicado à própria página de ajuda.
- **Fix:** a prosa passou a descrever os 13 pelo campo `implementation`, e a dizer que
  nenhum recusa por plugin ausente
- **Commit:** `e98f351`

**4. [Rule 2 - dívida com label desta fase] `CairnGo-zzgn` pedia uma DECISÃO da 38**

- **Encontrado em:** no fecho, ao rodar o gate — ele saiu **6**, e o item era uma issue
  aberta com label `phase-38`
- **Issue:** `cairn_gsd_render.py` cresceu de 81 para 1536 linhas e o design da issue
  dizia "duas saídas possíveis, decidir na 38". Medindo mais fundo: o teto D-01 da fase
  34 **nunca teve teste** — vivia como asserção de plano, válida no dia em que foi
  escrita e em nenhum outro. Não era o gate medindo o arquivo errado; era não haver gate.
- **Fix:** decisão tomada (saída (a), registrada em D-07), execução filada como
  `CairnGo-2fyg` no backlog, e o gate que faltava escrito agora: pino por arquivo que só
  desce, mais a lista fechada dos três arquivos já acima de 1500. Controle medido — duas
  linhas a mais em `cairn-gsd-record.py` deixam o pino vermelho nomeando os números.
- **Commit:** ver o commit de fecho da fase

## Verificação

- `tests/cairn-parity.bats` — 13/13
- `tests/cairn-standalone.bats` + `tests/cairn-vendoring.bats` — 42/42
- `tests/cairn-command-surfaces.bats` + `tests/cairn-wrap.bats` — 39/39
- `tests/cairn-init.bats`, `cairn-migrate.bats`, `cairn-config.bats`, `cairn-status.bats`,
  `smoke.bats` — 131/131
- `grep -rn "/gsd:" cairn/commands/` — 11 ocorrências, todas registradas

## Commits

- `d4053ac` test(38-03): os tres guards do registro de paridade, vermelhos
- `e98f351` feat(38-03): os dez passos mortos somem, e a decisao vira registro travado
- `37bd7ae` test(38-03): o repositorio novo fecha o ciclo, sai limpo no doctor e verde no gate
