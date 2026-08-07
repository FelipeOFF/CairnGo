---
phase: 25-measured-cleanup
verified: 2026-08-07T13:20:00Z
status: passed
score: 9/9 critérios verificados, 6/6 requisitos entregues
behavior_unverified: 2
behavior_unverified_items:
  - behavior: "A liberação de lease e a remoção de worktree num repositório que NÃO é este — outro layout de caminho, outro remoto, outro dono de branch"
    why: "Os dois verbos novos (`cairn-lease retire`, `cairn-parallel cleanup --phase`) foram provados em fixture e depois ao vivo aqui, onde o worktree canônico é `<raiz>-phase-N` e o dono do bd é o mesmo usuário do git. Um repositório com convenção de caminho diferente, ou com dois atores no bd, não foi construído"
  - behavior: "O `cairn-init` regenerando o hook de pre-push depois do conserto do artefato"
    why: "O artefato deste repositório foi consertado (87646cd) e o gerador não — `cairn-init.sh:156` interpola `$SCRIPTS_DIR` do momento da instalação e volta a assar um caminho absoluto. Registrado como `CairnGo-pg9`. Rodar o init aqui sobrescreveria o conserto, e isso não foi exercido"
human_verification:
  - test: "Rodar `cairn-parallel.sh cleanup --apply` num repositório com um worktree de fase que journalizou, e conferir que ele é removido"
    expected: "O worktree sai; `.cairn/journal/` não o retém"
    why_human: "A exclusão do journal da checagem de trabalho não commitado (D-05) foi provada aqui removendo cinco worktrees de uma vez, mas os três antigos eram anteriores à fase 28 e não tinham partição. O caso exato — worktree COM partição — foi construído em fixture, não observado em produção"
  - test: "Fazer um `git push` neste repositório e observar qual gate roda"
    expected: "`<repo>/cairn/scripts/cairn-gate.sh`, nunca uma cópia do cache de plugin"
    why_human: "O hook foi exercido por invocação direta (`bash .beads/hooks/pre-push`), que é o mesmo caminho de código, mas o disparo real pelo git no fluxo de push ainda não aconteceu — acontece no push desta milestone"
overrides_applied: 0
gaps:
  - truth: "Três verbos novos — `bookkeep plan`, `lease retire`, `cleanup --phase` — não têm página em `cairn/docs/commands/`"
    status: open
  - truth: "A segunda metade do `CairnGo-66o` não foi entregue: a porta cirúrgica por plano existe e está provada, mas nada ainda a chama no lugar do gsd-tools"
    status: partial
---

# Fase 25 — Verificação

**Verificada em 2026-08-07**, contra a árvore em `5151dba` mais o fechamento, com
as duas metades já mescladas em `main` (`6fc5ffa`, `3f594fe`).

## Os nove critérios

| # | Critério | Veredito | Prova |
|---|---|---|---|
| 1 | Teste que reproduz o defeito **antes** do conserto, com a medição citada | ✓ | 68 testes novos ao todo. 31 quebras aplicadas ao fonte, cada uma restaurada de cópia `cp` |
| 2 | O `status` do `cairn-release --json` significa "está correto", ou é renomeado | ✓ | `mismatch` sai do vocabulário; a comparação vira `agrees_with_reference`, `null` quando não houve comparação, e a régua é nomeada em `reference` |
| 3 | Nenhum conserto muda o código de saída de caminho hoje verde | ✓ | Conferido no `tuh` (texto humano e exit idênticos; `check_release_versions` devolve o mesmo objeto) e nos sete renders da fase 20, que seguem byte a byte |
| 4 | FIX-04: `discovered-from` não bloqueia, fase arquivada não bloqueia para sempre | ✓ | fase 26: `depends_on [9]` → `[]`; `NON_BLOCKING_DEP_TYPES` conferido contra as 50 arestas reais (`{blocks: 42, discovered-from: 8}`) |
| 5 | AUTO-10: um dialeto só, e a divergência vira checagem | ✓ | **Provado ao vivo, não em fixture** — ver abaixo |
| 6 | A cadeia de planos ganha leitor independente | ✓ | Checagem `plan-counters`, que **compara** em vez de recomputar. Ela reprovou este repositório no ato de nascer: `47 completed de 39 total` |
| 7 | `cairn.sync_push` sai da declaração | ✓ | Ausente de `cairn/capability/capability.json`. As menções restantes são prosa **sobre a remoção**, não declaração |
| 8 | O fechamento de fase desmonta o que o `prepare` montou | ✓ | `lease retire` e `cleanup --phase`, invocados pelo `close`. Cinco worktrees removidos ao vivo |
| 9 | Superfície nova sem porta de entrada | ✓ | `/cairn:land` e `/cairn:review` com prompt, página, linha na referência e bloco derivado regenerado (38/25 → 40/27) |

## O critério 5 se provou no repositório real

Não é asserção de fixture. Foi medido antes e depois do `cairn-bookkeep close 25`
desta mesma fase:

```
antes    claims-stale   not-applicable    state-dialect  not-applicable
         (STATE.md carregava só current_phase, e o cairn lê active_phase)

depois   claims-stale   ok                state-dialect  ok

.planning/STATE.md:5   current_phase: 25
.planning/STATE.md:6   active_phase: 25      <- inserido AO LADO, não no lugar
```

Duas checagens saíram de "não consegui checar" para "checado", e a chave nasceu do
próprio comando que a fase consertou. O `state-dialect` **compara** as duas e nunca
recomputa nenhuma — que é a diferença entre uma checagem e um segundo escritor.

## O que a medição contradisse: 37 premissas

Três agentes rodaram esta fase e cada um foi instruído a reportar toda premissa que a
medição derrubasse. Somaram **37**: nove na primeira metade, onze nas superfícies,
dezessete nas ferramentas. As quatro que mudam o entendimento do defeito:

- **O `php` não era "deixou de liberar a partir da fase 20".** Não existe um único
  `bd close` no `cairn-lease.py`, e o ramo de vacância passa `--status open` de
  propósito. As leases 18 e 19 foram fechadas **à mão**, a um segundo uma da outra,
  com razão em prosa que nenhuma ferramenta daqui gera. A capacidade nunca existiu —
  a issue descrevia uma regressão que nunca houve.
- **O `ce3`: os três worktrees já eram `removable`.** Limpos, mesclados. Faltava a
  chamada, não a capacidade. E a mesma medição expôs que um `cleanup --apply` global
  naquele momento teria apagado os dois worktrees das frentes vivas.
- **O quarto defeito da família, achado dentro do diff herdado e sem issue**
  (`CairnGo-4p1`): `plan_depends_on()` lia todo dígito do frontmatter de um `PLAN.md`
  como **número de fase**, mas o GSD escreve `depends_on:` ali para ordenar as
  **ondas** da fase. `22-02-PLAN.md` dizia `depends_on: ["01"]` querendo dizer "a onda
  anterior", e o modelo leu "as fases 1 a 4" — de um milestone arquivado, que nunca
  entra em `done_set` e portanto bloqueia para sempre. Dois defeitos somando-se.
- **A `gbu` dizia que `sync_push` vive em três lugares. Vive em nove**, e um deles
  (`tests/cairn-config.bats:726`) **exige** a string dentro de `cairn/commands/config.md`
  — então "apagar a declaração" nunca podia ser "apagar todas as menções".

## Três quebras saíram verdes, e os três verdes são o achado

A disciplina da casa manda aplicar uma quebra real por guarda e registrar a asserção
vermelha. Três não ficaram vermelhas, e cada uma expôs um teste que não media nada:

1. **Remover só a fixture nova não derrubava nada.** A prova tinha de ser combinada, e
   foi medida: *glob quebrado + fixture antiga → o teste passa* (`rc = 0`). É a cegueira
   literal que a issue do contador descreve.
2. **Uma asserção vazia**, escrita para guardar o ramo "sem `.planning/`" — o doctor
   registra zero checagens nesse repositório, então o guarda não guardava coisa alguma.
   Removida, e o ramo documentado como defensivo.
3. **`STATE_KEYS_WRITTEN` não governa a criação da chave, só a atualização.** Sem o
   teste novo, a fase teria entregue uma chave que envelhece e passaria a **reprovar** o
   doctor na fase seguinte — o conserto do AUTO-10 criando o defeito que o AUTO-10
   existe para remover.

## Estado do doctor ao fim

```
22 checagens · 0 falhas
warn  orphans              2 issues órfãs (+61 fechadas de milestone arquivado, isentas)
warn  phase-corroboration  1 item
warn  phase-landed         11 fases completas ainda não alcançaram a branch de controle
```

Os três são verdade sobre o repositório, não defeito da ferramenta: o `phase-landed`
em particular é a fase 30 fazendo exatamente o que foi construída para fazer, e ele se
resolve quando esta milestone entrar na branch de controle.

---

*Phase: 25-Measured cleanup*
*Verified: 2026-08-07*
