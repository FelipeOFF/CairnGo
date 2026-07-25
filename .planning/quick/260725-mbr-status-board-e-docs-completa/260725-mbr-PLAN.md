---
quick_id: 260725-mbr
bd_issue: CairnGo-4ju
mode: quick-full
must_haves:
  truths:
    - "/cairn:status renderiza board kanban em colunas via script determinístico"
    - "Board degrada graciosamente: colunas → empilhado → lista crua conforme largura"
    - "Pipe/--json nunca recebem box-drawing nem escapes ANSI"
    - "Todos os 22 comandos têm doc individual em cairn/docs/commands/"
    - "Índice cairn/docs/commands.md linka os 22 e está linkado do cairn/README.md"
  artifacts:
    - cairn/scripts/cairn-status.py
    - cairn/scripts/cairn-status.sh
    - tests/cairn-status.bats
    - cairn/commands/status.md (rewrite)
    - cairn/docs/commands/*.md (22 arquivos)
    - cairn/docs/commands.md (índice)
  key_links:
    - cairn/commands/status.md → cairn/scripts/cairn-status.sh
    - cairn/docs/commands.md → cairn/docs/commands/<cmd>.md
    - cairn/README.md → cairn/docs/commands.md
---

# Quick Task 260725-mbr: Status board + documentação completa — PLAN

Fontes: `260725-mbr-CONTEXT.md` (decisões travadas), `260725-mbr-inventory.json` (22 comandos), `260725-mbr-research-cli-design.json`, `260725-mbr-research-house-style.json`.

## Task 1 — Renderer `cairn-status` (script + wrapper + testes + rewiring do comando)

**Files:** `cairn/scripts/cairn-status.py`, `cairn/scripts/cairn-status.sh`, `tests/cairn-status.bats`, `cairn/commands/status.md`, `cairn/commands/help.md` (1 linha), `cairn/README.md` (linha do status no mapa)

**Action — spec do script (seguir house style à risca; ver research-house-style.json):**

1. `cairn-status.py` python3 zero-dependências, shebang `#!/usr/bin/env python3`, docstring-contrato com Usage/Behavior/Exit codes. Constantes `EXIT_OK=0`, `EXIT_USAGE=2`, `EXIT_NO_BD=5`. Helper `die(msg, code)` → `[cairn-status] error: {msg}` em stderr.
2. Wrapper `cairn-status.sh` idêntico ao molde dos outros 6 (comentário "Thin wrapper", `set -euo pipefail`, `exec python3 "$HERE/cairn-status.py" "$@"`).
3. **Flags:** `--json` (uma linha `json.dumps` com dict estável), `--plain` (tabular TSV-like, sem cor/box), `--brief` (3 linhas: header, counts, next), `--width N` (override de largura — essencial pros bats determinísticos), `--max-rows N` (default 15, rodapé `+k more`), `--ascii`, `--color=always|never`, `--planning-dir <dir>`.
4. **Dados:** `shutil.which("bd")` ausente → exit 5 (nunca trava consumidor). `bd -C <root> ready --json`, `bd -C <root> list --status in_progress --json`, `bd -C <root> blocked --json` (builder confirma flags exatas contra `bd help` do bd 1.1.0 instalado). ROADMAP.md/STATE.md via regex leniente — REUSAR os padrões de `cairn-gate.py:62-125` (fases completas, milestone 🚧, frontmatter `active_phase`/`milestone`). Sync staleness de `.cairn/sync.json` + watermark `.cairn/state.json`.
5. **Board (modo TTY):** 3 lanes `READY` / `DOING` / `BLOCKED` em colunas box-drawing light (┌┬┐├┼┤└┴┘─│), UMA grade compartilhada (nunca caixa por card). Header de lane `NOME (count)`. Célula: `id  título-truncado` (+ `⧗ dep-id` na BLOCKED, `◆ assignee` na DOING). Rodapé fora da grade: `fase X/Y · milestone · done: N` + `▶ next: <ação única>` + linha de sync se stale.
6. **Síntese do next (portar da prosa atual):** in_progress existe → continuar; senão ready de maior prioridade filtrado por `m-<milestone>,phase-<ativa>`; senão next action do STATE.md. Regra "bd wins for work items, STATE.md wins for workflow steps" vira comentário no código + comportamento.
7. **Largura:** `shutil.get_terminal_size()` (fallback env COLUMNS, fallback 80); `--width` vence tudo. `inner = clamp(floor((cols-(n+1))/n)-2, 18, 40)`. Degradação: `cols < 3*(18+2)+4` (~64) → lanes empilhadas verticalmente (header + itens 1/linha); `cols < 40` → lista crua `LANE  id  título`. Nunca deixar o terminal quebrar linha da grade; só espaços, jamais `\t` dentro do board.
8. **Truncamento:** por display width via `unicodedata.east_asian_width` (W/F=2, resto 1 — implementação local ~10 linhas, zero deps), corte + `…` (ASCII: `...`). Cor aplicada DEPOIS de truncar/pad. Reset `\x1b[0m` antes de cada borda.
9. **Cor (4-bit apenas):** precedência `--color` > `CAIRN_NO_COLOR` > `NO_COLOR` (presente e não-vazio, mesmo "0") > `TERM=dumb` > `isatty(stdout)`. Semântica: READY dim/default, DOING amarelo(33), BLOCKED vermelho(31), done verde(32) no rodapé; cor no header/count/glifo, NUNCA no card inteiro nem background; bordas em dim(2)/bright-black(90).
10. **Não-TTY sem flags = `--plain` automático** (modelo gh CLI): tabular limpo, zero bytes de escape, sem truncar títulos.
11. `tests/cairn-status.bats` no padrão de `cairn-map.bats`: `load 'helpers'`, `make_tmp_repo`+`make_gsd_fixture`+`make_bd_fixture`, invocação sempre pelo wrapper `run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --width 100`. Casos: happy path board, `--json` com `assert_json_eq`, `--brief`, `--plain`, degradação `--width 50` e `--width 30`, truncamento de título longo, `NO_COLOR=1` (sem `\x1b`), `--ascii`, exit 2 usage, exit 5 via PATH-stub (técnica de cairn-map.bats:219-231), isolamento `--planning-dir`.
12. Rewrite de `cairn/commands/status.md` no modelo doctor.md: rodar `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-status.sh"`, apresentar o board VERBATIM (fence, sem parafrasear), explicar exit codes (5 → bd ausente: cair de volta pra visão prosa mínima com `/gsd:progress`), `--brief` quando o usuário só quer 3 linhas, e a regra bd-vs-STATE preservada. Atualizar description do frontmatter. Atualizar a linha do status em `help.md` (seção VIEW) e ESPELHAR em `cairn/README.md` (mapa duplicado — gotcha documentado).

**Verify:** `bats tests/cairn-status.bats` verde; `bash cairn/scripts/cairn-status.sh --width 100` roda no PRÓPRIO repo (bd vivo com CairnGo-4ju in_progress) e mostra board coerente; `... | cat` sem escapes ANSI.

**Done:** board renderiza determinístico, testes verdes, comando rewired, help/README espelhados.

## Task 2 — Documentação dos 22 comandos

**Files:** `cairn/docs/commands/<cmd>.md` × 22 (bd, context-config, ctx, doctor, gsd, help, init, issues, migrate, milestone, new, plan, progress, quick, recall, remember, ship, status, sync-config, sync-pull, verify, work)

**Action:** Em INGLÊS (idioma do repo). Fonte primária: o próprio `cairn/commands/<cmd>.md` (LER o arquivo real; inventory.json é guia, não fonte). Estrutura fixa por doc:

```markdown
# /cairn:<cmd>

> <description do frontmatter>

## Usage        — invocação + argument-hint
## What it does — fluxo em passos, side effects (commits, hooks, gates) explícitos
## Flags & arguments
## Exit codes   — só quando o comando envolve script com contrato de exit codes
## Examples     — 1-3 exemplos realistas com output esperado resumido
## Files touched — o que lê/escreve (.cairn/, .planning/, .beads/)
## Related      — links relativos pros docs dos comandos vizinhos
```

Gotchas do inventário (unpadded labels, purge destrutivo, precedência de milestone, exit codes) DEVEM aparecer nos docs respectivos. Doc do `status` documenta o board NOVO da Task 1.

**Split em 3 builders paralelos (arquivos disjuntos):**
- Grupo B (lifecycle): init, new, migrate, plan, work, verify, ship
- Grupo C (view/health): status, progress, issues, doctor, milestone, quick, help
- Grupo D (memory/sync/escape): remember, recall, ctx, context-config, sync-config, sync-pull, bd, gsd

**Verify:** 22 arquivos existem, nenhum <30 linhas, flags citadas batem com os command files reais.

**Done:** 22 docs completos e fiéis.

## Task 3 — Índice + integração

**Files:** `cairn/docs/commands.md` (índice: tabela nome → description → link, agrupada como o help: SETUP/LOOP/VIEW/MIGRATE & HEALTH/MEMORY/SYNC/ESCAPE HATCHES), `cairn/README.md` (adicionar linha na tabela de docs), `README.md` raiz (linha na tabela de docs, seção existente linha 81).

**Depends on:** Tasks 1-2 (índice referencia docs prontos; linha do status no README já mexida pela Task 1 — Task 3 NÃO toca a linha do mapa, só a tabela de docs).

**Verify:** todos os 22 links do índice resolvem; README(s) linkam o índice.

**Done:** navegação completa: README → índice → doc por comando.

## Execução

- Branch: `feat/status-board-e-docs` (já criada). Builders NÃO commitam nem tocam git — commits atômicos ficam com o orquestrador (1 commit script+testes+comando, 1 commit docs, 1 commit índice+artefatos).
- Pós-execução: verifier (bats + execução real + checagem dos 22 docs) e code review do python.
- Entrega: GitHub issue descrevendo as duas frentes + PR de `feat/status-board-e-docs` → `main` fechando a issue. `bd close CairnGo-4ju` no fim.

## Riscos

- Flags do bd 1.1.0 podem diferir (`bd blocked --json`?) — builder confirma com `bd help` antes de fixar; fallback documentado no script.
- Alinhamento com emoji em títulos de issue: mitigado por truncamento display-width e prefixo fixo de glifo; imperfeição residual aceita (research: "inatingível em todos os terminais").
- `cairn/README.md` tocado por Task 1 (linha do mapa) e Task 3 (tabela docs) — regiões distintas, sequenciado (Task 3 depois).
