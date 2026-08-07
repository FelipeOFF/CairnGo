# Phase 26: The cairn wrappers - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning
**Source:** Modo autônomo. Toda gray area vira Claude's Discretion por escrito,
e nenhuma decisão abaixo é palpite: cada uma cita a medição que a produziu, ou
diz que não foi medida.

<domain>
## Phase Boundary

Os 13 wrappers `/cairn:*` decididos no GSD-05 passam a existir, cada um
carregando o bookkeeping bd da casa; um wrapper cujo `/gsd:*` correspondente
não existe falha nomeando o que falta; e a lista deles na documentação é
derivada do disco, nunca digitada.

Requisitos: WRAP-01, WRAP-02, WRAP-03. Issues bd: `CairnGo-9xy` (WRAP-01),
`CairnGo-38j` (WRAP-02), `CairnGo-5mu` (WRAP-03) — ver `26-BEADS-MAP.md`.

**Fora de escopo, por escrito:** os 39 comandos decididos como "use o GSD
direto" e os 2 fora de escopo por princípio (`pr-branch`, `graphify`). O
GSD-05 já decidiu cada um; esta fase constrói o que ele mandou construir e não
reabre a triagem. Reabrir seria refazer a decisão, não executá-la.

</domain>

<decisions>
## O bloqueio anunciado desta fase é falso, e foi medido

O `/cairn:status` reporta a fase 26 como *"waits on phase 9"*. **Medido agora,
nesta worktree: `bd blocked` devolve vazio** (`✨ No blocked issues`). O
`ROADMAP.md` § Phase 26 diz, na íntegra, `**Depende de:** nada`.

A mecânica do falso positivo está localizada e é o defeito **FIX-04**, conserto
já enfileirado para a fase 25:

- `bd show CairnGo-9xy` traz `DISCOVERED FROM ◊ ✓ CairnGo-k21`. A aresta é
  `discovered-from`, que o próprio `/cairn:quick` documenta como procedência
  **que não bloqueia** (`commands/quick.md:28`: *"records provenance without
  blocking"*).
- `cairn-status.py:1002` `dep_target_ids()` coleta `depends_on_id` de toda
  aresta em `dependencies` **sem olhar o tipo**. `discovered-from` entra junto
  com `blocks`.
- `CairnGo-k21` é da fase 9, milestone **v1.2, arquivado**. O filtro de
  "já concluída" roda contra o conjunto de fases feitas do ciclo corrente, do
  qual uma fase arquivada nunca faz parte — então a aresta nunca é descartada.

As duas metades do FIX-04, exatamente como o REQUIREMENTS.md o enuncia, e as
duas incidindo sobre a mesma aresta desta fase.

**Prossegui.** Esta fase não conserta o FIX-04 — é da fase 25 e mexer no
`cairn-status.py` aqui colidiria com ela. O registro fica aqui porque o próximo
a ler o board vai ver a mesma mentira.

## Implementation Decisions

### D-01: os 13 são os do GSD-05, lidos na decisão original, e os 13 existem hoje

A lista não foi reinventada. Foi lida em
`.planning/milestones/v1.2-phases/09-adopt-gsd-core-commands/09-01-SUMMARY.md:18-24`
e em `cairn/docs/gsd-core-commands.md` § *Wrapped as `/cairn:*` — 13*:

`phase`, `discuss-phase`, `spec-phase`, `mvp-phase`, `ui-phase`,
`ai-integration-phase`, `ultraplan-phase`, `plan-review-convergence`,
`validate-phase`, `secure-phase`, `cleanup`, `review-backlog`,
`audit-milestone`.

**O item de research que o ROADMAP pediu está respondido, e medido.** Contra o
gsd-core que esta máquina de fato carrega
(`~/.claude/plugins/cache/cairngo/gsd-core/1.8.0`, confirmado como `installPath`
em `installed_plugins.json`): **71 comandos** em `commands/gsd/*.md`, e os
**13 estão presentes, um a um**. Nenhum sumiu, nenhum foi renomeado entre
2026-07-28 e hoje.

Medido também: **nenhum dos 13 colide** com os 25 comandos que `cairn/commands/`
já tem. Não há renome a negociar.

**Assumido, não medido:** que 1.8.0 é a versão que todo usuário do cairn tem. É
exatamente por isso que o WRAP-02 existe — a checagem é sobre a máquina de quem
roda, não sobre a minha.

### D-02: o par `.py`/`.sh` novo é UM script com subcomandos — `cairn-wrap`

Padrão da casa (`cairn-bookkeep.py close|reconcile`,
`cairn-capability.py detect|install`). Três subcomandos, um por requisito:

| subcomando | requisito | o que faz |
|---|---|---|
| `preflight <cmd>` | WRAP-02 | o `/gsd:<cmd>` está instalado? |
| `list [--json]` | WRAP-01/03 | enumera os wrappers **do disco** |
| `docs [--check]` | WRAP-03 | regenera o bloco derivado na documentação |

`tests/cairn-wrap.bats` próprio, `cairn-wrap.sh` fino ao lado.

### D-03: WRAP-02 — quem checa é script, não prosa, e são dois códigos distintos

Um `commands/*.md` é prosa: não tem código de saída, não pode "falhar". A
checagem tem que ser um passo determinístico que a prosa **invoca**, e é a
primeira linha de cada um dos 13:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight <gsd-command>
```

Contrato de saída, seguindo a tabela do `CONVENTIONS.md` § Exit Code:

| código | significado |
|---|---|
| 0 | o comando está instalado |
| 2 | uso |
| 3 | `docs --check` desatualizado (mesmo 3 = *stale* do `cairn-map`) |
| 5 | **não deu para olhar** — nenhum diretório de comandos GSD encontrado |
| 6 | **olhou e não está lá** — o comando não existe onde o GSD instalado vive |

Os dois são falha para o wrapper e os dois nomeiam o que falta; a diferença é
diagnóstica, não de bloqueio, e está escrita no docstring. Deliberadamente
**não** herdo aqui o "callers must NOT block on 5" que vale para o `bd` no
pre-push shim: ali o 5 é uma checagem opcional degradando; aqui o comando
delegado **é o trabalho todo**, e seguir em frente seria o exit-0-em-silêncio
que o requisito proíbe.

### D-04: WRAP-02 — a prova exige esconder o comando, e por que o feliz não serve

Um teste que só roda o caminho feliz passaria com a checagem **deletada**. Então
o teste do WRAP-02 monta um diretório-fixture de comandos GSD, **remove um
arquivo**, e afirma **o valor exato** do código (`6`) e a mensagem nomeando o
`/gsd:<cmd>` ausente e onde se procurou.

A quebra que o deixa vermelho, nomeada: apagar a checagem de existência do
`preflight` faz o `status` virar `0` e a asserção `[ "$status" -eq 6 ]` falha.
Sem `[ "$status" -ne 0 ]` em lugar nenhum — asserção é sobre o valor exato.

O seam para isso é `CAIRN_GSD_COMMANDS_DIR`, `UPPER_CASE` com prefixo do
`CONVENTIONS.md` e mesma família de `CAIRN_GSD_BIN`, que o
`cairn-capability.py:324` já criou pelo mesmo motivo declarado: *"this check
reads GLOBAL state ... sem um seam, o veredito dependeria do cache de plugins do
desenvolvedor"*.

### D-05: WRAP-03 — a lista é derivada de frontmatter, e o repositório já provou por que

**Este é o coração da fase e a armadilha.** Escrever a lista à mão no `.md`
satisfaz a leitura casual e falha o requisito.

**A prova de que documentação escrita à mão envelhece está neste repositório,
duas vezes, e a segunda é de anteontem:**

1. `cairn/docs/commands/doctor.md` afirmava `fifteen checks in total` com
   **dezesseis** registradas, e não tinha entrada para `release-versions` nem
   para `test-parallel`. Corrigido à mão em `8d3db19` (fase 29-07) para
   *"eighteen"* — e hoje o `cairn-doctor.py` tem 18 `def check_*`, então está
   certo **até a próxima checagem que alguém acrescentar**.

2. **Medido agora, e ainda quebrado:** `cairn/docs/commands.md` diz
   `22 in total`, linka **23** páginas, e `cairn/commands/` tem **25**
   comandos. `/cairn:config` e `/cairn:reconcile` existem, funcionam, e **não
   aparecem em lugar nenhum** da página que existe para listá-los. Sobra ainda
   `docs/commands/bookkeep.md`, página para o que não é comando.

Acrescentar 13 linhas à mão numa página já errada em três é repetir o defeito no
mesmo commit que o requisito manda consertar.

**A decisão:** cada um dos 13 carrega `wraps: <gsd-command>` no frontmatter, e
`cairn-wrap.py docs` deriva a tabela varrendo `cairn/commands/*.md`, dentro dos
marcadores `<!-- cairn:generated:start -->` / `<!-- cairn:generated:end -->` que
o `cairn-map.py` já estabeleceu como o idioma da casa para bloco gerado.

Medido que isso é seguro: o gsd-core usa 8 chaves distintas de frontmatter nos
seus 71 comandos (`name`, `allowed-tools`, `requires`, `effort`, `type`,
`argument-instructions`, além de `description`/`argument-hint`), enquanto o cairn
usa 2. Chave desconhecida é tolerada pelo carregador — o precedente é do próprio
upstream, não uma aposta minha.

### D-06: WRAP-03 — a prova exige acrescentar um wrapper, e a fase inteira é a demonstração

O teste monta um diretório-fixture com N wrappers, gera, afirma que os N
aparecem; então **escreve um arquivo de wrapper novo**, regenera, e afirma que o
novo aparece **sem uma linha de prosa editada**. E `docs --check` sai `3` com
diff quando o disco e a página discordam.

A quebra nomeada: trocar a derivação por lista literal faz o wrapper novo não
aparecer e a asserção falha.

**Mais forte que o fixture:** a ordem dos planos torna a fase inteira a
demonstração em campo. O gerador nasce quando existe **um** wrapper; os outros
**doze** chegam depois. Se a página ganhar as doze linhas sem ninguém escrever
prosa, o WRAP-03 está provado em produção, não só em fixture.

### D-07: o bookkeeping é uniforme no núcleo e explícito por família

O brief da casa é `claim → in_progress → close`, par de rótulos
`m-<milestone>` + `phase-<N>` (não padronizado — `phase-3`, nunca `phase-03`) e
carimbo `metadata.gsd`. Isso é o núcleo dos 13.

Mas os 13 não são homogêneos, e fingir que são produziria prosa errada em três
deles. Três famílias, declaradas em `wrap-family:` no frontmatter, derivadas do
que o próprio `gsd-core-commands.md` diz que cada um faz:

| família | comandos | forma |
|---|---|---|
| `phase` | discuss-phase, spec-phase, mvp-phase, ui-phase, ai-integration-phase, ultraplan-phase, plan-review-convergence, validate-phase, secure-phase | recebe `<N>`, claim das issues da fase, roda o GSD, refresca o mapa |
| `structural` | phase | CRUD renumera/remove fases e **órfã todo issue com o rótulo `phase-<N>`** — o caso mais forte da lista inteira, e o único que precisa de relabel |
| `milestone` | cleanup, review-backlog, audit-milestone | escopo `m-<milestone>`, não `phase-<N>` |

**Claude's Discretion, e assumido:** que o `validate-phase` e o `secure-phase`
precisam **reabrir** issue fechada é o que a tabela do GSD-05 afirma; não medi o
comportamento deles ao vivo. A prosa vai dizer "reabra se o GSD reabrir a fase",
não vai reabrir por conta própria.

### D-08: um teste de contrato uniforme sobre os 13, mecânico

Treze arquivos de prosa escritos à mão divergem. Então um teste varre
`cairn-wrap.sh list --json` e, para **cada** wrapper, afirma que o arquivo:
nomeia a chamada do `preflight`, nomeia o `/gsd:<seu comando>`, nomeia
`bd update <id> --claim`, e nomeia o par de rótulos.

A quebra nomeada: apagar a linha do `--claim` de **qualquer um** dos 13 deixa o
teste vermelho, nomeando qual.

### Claude's Discretion (registrado, não escondido)

- **O nome `cairn-wrap`** e a forma dos três subcomandos.
- **Consertar os três defeitos medidos do `commands.md`** (contagem 22→derivada,
  `config` e `reconcile` ausentes) dentro desta fase. É o defeito que o WRAP-03
  existe para matar, medido na página que a fase tem que editar de qualquer
  jeito; deixá-lo para depois seria acrescentar 13 linhas certas a uma página
  que continua mentindo em três.
- **O `docs --check` entra na suíte**, para a página não poder envelhecer de
  novo em silêncio.
- **Onde o bloco derivado mora:** `cairn/docs/commands.md`, num grupo próprio,
  em vez de página nova. Uma segunda página seria uma segunda lista para manter
  em sincronia — o defeito, de novo.

</decisions>

<risks>
- **A ordem dos planos é a prova do WRAP-03 e por isso não é negociável.** Se os
  13 wrappers nascerem antes do gerador, a página ganha 13 linhas escritas à mão
  e a demonstração em campo se perde; sobra só o fixture.
- **`CLAUDE_PLUGIN_ROOT` não existe fora de uma sessão de plugin.** A descoberta
  precisa cair para o cache de plugins e para o `installed_plugins.json`, como o
  `cairn-capability.py` já faz. Não medi o comportamento do `preflight` dentro
  de uma sessão real do Claude Code — só via o seam e via os caminhos do disco.
- **Colisão com a fase 25 (FIX-04).** Esta fase **não** toca `cairn-status.py`.
- **Volume.** É a maior fase do ciclo em número de arquivos (13 comandos + 13
  páginas de doc + script + testes). O risco é prosa repetida divergindo — é o
  que o D-08 existe para pegar.
</risks>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### A decisão que fixou os 13
- `.planning/milestones/v1.2-phases/09-adopt-gsd-core-commands/09-CONTEXT.md` —
  o viés de triagem escolhido pelo operador e o critério de "ganha wrapper"
- `.planning/milestones/v1.2-phases/09-adopt-gsd-core-commands/09-01-SUMMARY.md:18-24`
  — a lista dos 13, nominal
- `cairn/docs/gsd-core-commands.md` § *Wrapped as `/cairn:*` — 13* — a tabela
  com o **porquê** de cada um, que é a fonte da coluna "família" do D-07

### Código
- `cairn/commands/work.md` — o bookkeeping de fase da casa (claim, close, rótulo
  não padronizado, refresh do mapa) e o comentário que explica por que
  `${CLAUDE_PLUGIN_ROOT}` está certo num comando cairn
- `cairn/commands/quick.md:28` — `discovered-from` "records provenance without
  blocking", a frase que o FIX-04 contradiz
- `cairn/scripts/cairn-map.py` — o idioma do bloco gerado por marcadores e o
  `--check` com exit 3 + diff
- `cairn/scripts/cairn-capability.py:209-339` — descoberta de plugin GSD
  instalado, e o seam `CAIRN_GSD_BIN` com o motivo declarado
- `cairn/scripts/cairn-status.py:1002` — `dep_target_ids()`, o FIX-04 (**não
  mexer nesta fase**)
- `.planning/codebase/CONVENTIONS.md` — stdlib only, sem type hints, par
  `.py`/`.sh`, `EXIT_*`, docstring como spec

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cairn-map.py`: marcadores, preservação do que está fora deles, `--check` com
  diff e exit 3. O gerador do WRAP-03 é o mesmo formato.
- `cairn-capability.py`: `_plugin_cache_roots()`, `installed_plugin_roots()`,
  `_discovery_key()` — a descoberta do GSD instalado já está resolvida e medida
  (inclusive o caso das duas linhagens na mesma máquina).
- `cairn-relabel.py`: já existe, e é o que o wrapper `structural` (`phase`)
  chama quando o CRUD renumera uma fase.
- `helpers.bash`: `make_tmp_repo`, `make_gsd_fixture`, `require_bd`,
  `refute_in_file` (o idioma para negativa que de fato falha o teste).

### Established Patterns
- Escrita atrás de flag nomeada; leitura por default.
- `EXIT_*` nomeados, nunca inteiro solto.
- Docstring de módulo é a spec canônica, e registra **medido versus assumido**.
- Um teste que passaria com a feature removida não é prova.
- Asserção de status é sobre o valor exato, nunca sobre a negação.

### Integration Points
- `cairn/commands/*.md` — 13 arquivos novos, `wraps:` + `wrap-family:` no
  frontmatter.
- `cairn/docs/commands.md` — ganha o bloco derivado e perde os três defeitos
  medidos.
- `cairn/docs/gsd-core-commands.md` — o *"Status: decided, not yet built"*
  deixa de ser verdade e tem que mudar junto.
- `cairn/docs/commands/*.md` — página por wrapper.

</code_context>

<specifics>
## Specific Ideas

- **A fase carrega a prova do próprio requisito no repositório que a hospeda.**
  O WRAP-03 não precisa de argumento hipotético: `commands.md` diz 22, linka 23,
  e existem 25. O gerador nasce com um teste que fica **vermelho contra o estado
  atual do repositório** e verde depois do conserto — red→green medido, não
  sintético.

- **O `phase` é o caso mais forte e deve ser a fatia vertical.** É o único dos
  13 cujo dano é irreversível sem trabalho: renumerar uma fase órfã todo issue
  com o rótulo antigo, e o GSD-05 o registrou nesses termos. Se um wrapper só
  puder existir, é esse.

- **O bloqueio falso desta fase e o defeito que ela conserta são o mesmo
  animal.** O board mente porque uma lista foi derivada errado; a documentação
  mente porque uma lista não foi derivada. As duas metades do mesmo princípio da
  casa.

</specifics>

<deferred>
## Deferred Ideas

- Consertar o FIX-04 no `cairn-status.py` — é da fase 25, e mexer aqui colide.
- Rever a triagem do GSD-05 (13 wrap / 39 direto / 2 fora) contra um gsd-core
  mais novo que 1.8.0 — a re-derivação já está documentada em
  `gsd-core-commands.md`; rodá-la é outra fase, quando o upstream subir.
- Página de doc para `/cairn:bookkeep` versus a página órfã
  `docs/commands/bookkeep.md`: decidir se `bookkeep` vira comando ou se a página
  vira outra coisa. Fora de escopo aqui; o gerador vai **nomear** a sobra em vez
  de escondê-la.

</deferred>

---

*Phase: 26-The cairn wrappers*
*Context gathered: 2026-08-05*
