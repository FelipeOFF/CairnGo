# Phase 36: Workflows, steps e agentes falam bd - Pattern Map

**Mapped:** 2026-08-11 (HEAD 47e9a17, branch feat/v1.6-transplante)
**Files analyzed:** 34 blocos de preâmbulo + 8 workflows raiz + 42 fragments + 8 agentes com shim + 6 sítios do binário + 6 goldens + 1 teste de byte-paridade
**Analogs found:** 4 / 6 famílias de padrão (a substituição em massa sob `cairn/gsd/` e o teste de conteúdo de prompt não têm análogo — ver No Analog Found)

> **Esta fase edita PROMPT, não python.** Todas as fases 33-35 escreveram em
> `cairn/scripts/` com `cairn/gsd/` como árvore congelada. A 36 inverte isso: ela é a
> PRIMEIRA fase do milestone a escrever sob `cairn/gsd/`. Dois invariantes herdados
> foram construídos contra exatamente essa escrita, e ambos precisam mudar
> conscientemente antes da primeira edição (§Armadilhas Estruturais).

---

## File Classification

| Arquivo novo/modificado | Role | Data Flow | Análogo mais próximo | Qualidade |
|---|---|---|---|---|
| 34 blocos de preâmbulo shim (uma linha cada, sob `cairn/gsd/`) | prompt/config de runtime | transform textual uniforme | `cairn-wrap.py` (bloco por marcador + `--check` + write-only-when-changed) | role-match |
| Script de substituição em massa (novo, `cairn/scripts/`) | utility CLI | batch/file-I/O | `cairn-wrap.py:548-599` (replace_block) + `cairn-migrate.py:1858-1882` (do_write_file com append_marker) | role-match |
| Teste bats do novo script | test harness | batch | `tests/bench-publish.bats:109` (byte-identidade na 2ª rodada) + `tests/cairn-capability.bats:314` | exact |
| `tests/cairn-vendoring.bats` (mod — allowlist de adaptados) | test harness (byte-paridade) | batch | ele próprio: `assert_tree_bytes_match:179-194` + `assert_cut_holds:422-448` (oráculo tabular com controle negativo) | exact |
| `cairn/scripts/cairn-gsd-init.py` (mod — 6× `[]`→`null`) | verb-handler | request-response | ele próprio (as 6 linhas são idênticas em forma) | exact |
| 6 goldens `init-*.golden.json` (mod) | fixture | — | os 110 goldens existentes, comparação por FORMA (`cairn-gsd.bats:238-254`) | exact |
| `tests/fixtures/gsd-goldens/divergences.json` (mod) | fixture/registro | — | ele próprio (55 entradas, schema `aspect/cairn/family/reason/upstream/verb`) | exact |
| Sítios de estado nos 8 workflows raiz + 8 agentes | prompt | request-response / doc-read | os sítios que JÁ chamam `gsd_run query state.*` (execute-phase.md:204, discuss-phase.md:480) | exact |

---

## Pattern Assignments

### 1. O preâmbulo shim (onda zero) — 34 blocos, 2 variantes, UMA LINHA cada

**Medido agora** (`grep -rl '_GSD_SHIM_NAME=' cairn/gsd --include='*.md' | wc -l` → 34;
classificação por sha1 da linha):

| Variante | sha1 (8) | bytes | ramos `elif` | arquivos |
|---|---|---|---|---|
| longa | `a2732b0f` | 4513 | 19 | **31** |
| curta | `3a6b66fd` | 883 | 3 | **3** |

**O bloco é UMA LINHA ÚNICA, sempre a primeira linha dentro de um fence ` ```bash `.**
Isso é o que torna a onda zero uma substituição de linha, não de bloco multilinha.
Exemplar da forma (fast.md:74-80):

```
74: ```bash
75: _GSD_SHIM_NAME="gsd-tools.cjs"; _GSD_RUNTIME_ROOT="${RUNTIME_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"; GSD_TOOLS="${_GSD_RUNTIME_ROOT}/gsd-core/bin/${_GSD_SHIM_NAME}"; if [ -f "$GSD_TOOLS" ]; then gsd_run() { node "$GSD_TOOLS" "$@"; }; elif … ; else echo "ERROR: gsd-tools.cjs not found at $GSD_TOOLS and gsd-tools is not on PATH. Run: npx -y @opengsd/gsd-core@latest --claude --local" >&2; exit 1; fi; if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -n "${GSD_TOOLS:-}" ]; then printf "export PATH='%s':\"\$PATH\"\n" "${GSD_TOOLS%/*}" >> "$CLAUDE_ENV_FILE" 2>/dev/null || true; fi
76: # Detect whether STATE.md has a Quick Tasks Completed table
77: if grep -q "Quick Tasks Completed" .planning/STATE.md 2>/dev/null; then
78:   gsd_run quick-tasks-append --task "$TASK" || …
79: fi
80: ```
```

**O que difere entre as duas variantes** (só isto):
- A **longa** tenta, nesta ordem: `${_GSD_RUNTIME_ROOT}/gsd-core/bin`, `…/.claude/…`,
  `…/.codex/…`, `command -v gsd-tools`, depois 16 diretórios de host por env var
  (`CLAUDE_CONFIG_DIR`, `HERMES_HOME`, `CURSOR_CONFIG_DIR`, `CODEX_HOME`,
  `GEMINI_CONFIG_DIR`, `COPILOT_CONFIG_DIR`, `WINDSURF_CONFIG_DIR`, `AUGMENT_CONFIG_DIR`,
  `TRAE_CONFIG_DIR`, `QWEN_CONFIG_DIR`, `CODEBUDDY_CONFIG_DIR`, `CLINE_CONFIG_DIR`,
  `GROK_AGENTS_HOME`, `ANTIGRAVITY_CONFIG_DIR`, `OPENCODE_CONFIG_DIR`, `KILO_CONFIG_DIR`).
  Termina com o `else echo ERROR … exit 1` **e** o append de PATH em `$CLAUDE_ENV_FILE`.
- A **curta** tem 4 ramos (`gsd-core/bin`, `.claude/gsd-core/bin`, `command -v gsd-tools`,
  `$HOME/.claude/gsd-core/bin`), o mesmo `else … exit 1`, e **não** tem o append de
  `$CLAUDE_ENV_FILE`.

**Exemplares com âncora (verificados):**
- longa: `cairn/gsd/gsd-core/workflows/execute-phase.md:83`,
  `cairn/gsd/agents/gsd-executor.md:80`, `cairn/gsd/gsd-core/workflows/fast.md:75`
- curta: `cairn/gsd/commands/gsd/discuss-phase.md:50`,
  `cairn/gsd/skills/gsd-discuss-phase/SKILL.md:50`,
  `cairn/gsd/gsd-core/references/planner-load-graph-context.md:14`

**Os 34 arquivos, agrupados (linha do bloco entre parênteses):**

| Grupo | n | arquivos |
|---|---|---|
| **workflows raiz** | 8 | `autonomous.md`(67), `debug.md`(19), `discuss-phase.md`(118), `execute-phase.md`(83), `fast.md`(75), `plan-phase.md`(69), `quick.md`(42), `verify-work.md`(40) — todos sob `cairn/gsd/gsd-core/workflows/` |
| **steps** | 13 | `autonomous/steps/converge-fail-fast.md`(6); `execute-phase/steps/`: `codebase-drift-gate.md`(9), `executor-isolation-dispatch.md`(13), `gap-closure-artifacts.md`(16), `partial-wave.md`(5), `per-plan-worktree-gate.md`(101), `post-merge-gate.md`(11), `regression-gate-run.md`(11); `plan-phase/steps/`: `chunked-planning-mode.md`(104), `prd-express-path.md`(96), `stall-detection-helpers.md`(68); `quick/steps/worktree-pre-dispatch-commit.md`(8); `verify-work/steps/mvp-uat-framing.md`(11) |
| **modes** | 2 | `discuss-phase/modes/advisor.md`(40), `discuss-phase/modes/chain.md`(28) |
| **agents** | 8 | `gsd-debug-session-manager.md`(96), `gsd-debugger.md`(961), `gsd-executor.md`(80), `gsd-phase-researcher.md`(119), `gsd-plan-checker.md`(707), `gsd-planner.md`(608), `gsd-ui-researcher.md`(294), `gsd-verifier.md`(104) |
| **commands** | 1 | `cairn/gsd/commands/gsd/discuss-phase.md`(50) — **variante curta** |
| **skills** | 1 | `cairn/gsd/skills/gsd-discuss-phase/SKILL.md`(50) — **variante curta** |
| **references** | 1 | `cairn/gsd/gsd-core/references/planner-load-graph-context.md`(14) — **variante curta** |

> **CORREÇÃO AO RESEARCH §1.** O research diz "8 nos workflows raiz, 8 nos agentes, o
> resto em steps/modes". Medido: steps+modes somam **15**, não 18 — os outros **3**
> estão em `commands/`, `skills/` e `references/`, superfícies que o D-02 declarou fora
> do escopo. Se a onda zero cobrir só workflows+agents, **3 blocos ficam apontando
> `gsd-tools.cjs`** — e um deles (`references/planner-load-graph-context.md:14`) é
> carregado pelo `gsd-planner`. O plano precisa decidir explicitamente: ou a onda zero é
> por PADRÃO (todos os 34, independentemente de diretório), ou a lacuna dos 3 vai a
> `divergences.json` com o nome dos arquivos.

**Alvo da resolução — `cairn/scripts/cairn-gsd.sh` (13 linhas, forma inteira):**

```bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-gsd.py" "$@"
```

Exits documentados no cabeçalho (:7-10): 0/1 por contrato do verbo, 2 uso do dispatcher,
4 família não servida. A forma nova do preâmbulo herda esses exits sem tradução.

---

### 2. Substituição textual uniforme em muitos arquivos — **No-Analog na casa**

**Medido:** nenhum script de `cairn/scripts/` reescreve markdown por substituição
uniforme, e **nenhum escreve sob `cairn/gsd/`** exceto o vendor (que copia do cache — ver
armadilha VEND). Os quatro que declaram a árvore congelada, com âncora:

- `cairn/scripts/cairn-gsd.py:62` — "A árvore cairn/gsd/ é SOMENTE-LEITURA para este script"
- `cairn/scripts/cairn-gsd-init.py:23` — idem
- `cairn/scripts/cairn-gsd-state.py:17` — "cairn/gsd/ é SOMENTE-LEITURA"
- `cairn/scripts/cairn-gsd-check.py:18` — idem

`cairn-relabel.py` **não** toca markdown (grep por `write_text|.md|re.sub|replace(` →
vazio). `cairn-migrate.py` lê muito markdown mas escreve só artefatos de `.planning/`.

**Substituto proposto — copiar a forma de dois moldes reais:**

**(a) `cairn/scripts/cairn-wrap.py` — o molde do reescritor idempotente com `--check`:**

```python
# cairn-wrap.py:102-114
EXIT_OK = 0
# 3 = stale, the same meaning cairn-map.py --check already gives it.
EXIT_STALE = 3
...
START_MARKER = "<!-- cairn:generated:start -->"
END_MARKER = "<!-- cairn:generated:end -->"
HEADER_LINE = "Generated by cairn-wrap — do not edit between markers"
```

```python
# cairn-wrap.py:548-556 — o contrato de escrita cirúrgica
"""Replace the marker block, or append a new section carrying it.

Never rewrites the file wholesale: everything outside the markers survives
byte for byte. A file with no markers gains the block under its own …
"""
```

```python
# cairn-wrap.py:596-599 — write-only-when-changed (mtime intacto no no-op)
# A byte-identical rewrite is still a write: only touch the file when the
# content actually differs, so mtime stays put on a no-op run.
if changed:
    doc.write_text(updated, encoding="utf-8")
```

O modo `--check` sai `EXIT_STALE` (3) e imprime `difflib.unified_diff` (:584-590) — é
exatamente o gate "prove que os 34 estão trocados" que a fase precisa, sem inventar
teste novo. Marcadores irmãos: `cairn-map.py:52-53`, `cairn-status.py:3457` (BOARD_START).

**(b) `cairn/scripts/cairn-migrate.py:1858-1882` — idempotência por marcador + recusa nominal:**

```python
def do_write_file(self, p):
    rel = p["path"]
    base = os.path.basename(rel)
    if base in ("PROJECT.md", "CONTEXT.md"):
        raise StepError(f"refusing to write {rel} — cairn-migrate never "
                        "touches PROJECT.md/CONTEXT.md")
    ...
    if marker:
        if marker in text:
            return {}          # já aplicado: no-op silencioso
```

A recusa por nome (:1861-1863) é o molde direto para "este script nunca escreve em
`cairn/gsd/contracts/` nem em `MANIFEST.json`".

**(c) Prova de idempotência em bats — três moldes na casa:**
- `tests/bench-publish.bats:109` — *"running twice with identical --in/--label is
  byte-identical (write-only-when-changed idempoten…)"*
- `tests/cairn-capability.bats:314` — *"repair is idempotent — a clean manifest reports
  and changes nothing"*
- `tests/cairn-init.bats:157` — *"cairn-init re-run is idempotent — no duplicate
  .gitignore entries"*

**(d) Prova de COBERTURA — o molde é o oráculo tabular com controle negativo**
(`tests/cairn-vendoring.bats:422-448` + `465-474`): uma função `assert_*` que recebe a
RAIZ como argumento, roda o mesmo laço contra a árvore real e contra uma árvore forjada,
e nomeia cada residuo em stderr. Para a onda zero: `assert_no_cjs_shim <root>` verde na
árvore real e vermelho numa cópia com um bloco antigo reinjetado.

---

### 3. Como se testa prompt no CairnGo — e a armadilha central

**Existe exatamente UM teste que valida o conteúdo de arquivo `.md` sob `cairn/gsd/`, e
ele afirma o OPOSTO do que a fase 36 vai fazer:**

```bash
# tests/cairn-vendoring.bats:497-507
real_cache_or_skip() {
  REAL_CACHE="$CAIRN_REPO_ROOT/.cairn/cache/gsd-core-v1.10.0"
  [ -d "$REAL_CACHE" ] || \
    skip "cache do clone ausente — rode cairn-inventory.sh uma vez com rede"
}

@test "real tree: every files[] entry is byte-identical to the pinned cache" {
  real_cache_or_skip
  run assert_tree_bytes_match "$VEND_MANIFEST" "$VEND_ROOT" "$REAL_CACHE"
  [ "$status" -eq 0 ]
}
```

O oráculo (`:179-194`) percorre **os 171 caminhos de `files[]`** e faz `cmp -s` de cada um
contra o mesmo caminho relativo no cache do clone da tag v1.10.0:

```bash
assert_tree_bytes_match() {
  local manifest="$1" dest="$2" corpus="$3" fails=0 p
  while IFS= read -r p; do
    ...
    if ! cmp -s "$dest/$p" "$corpus/$p"; then
      echo "vendored bytes diverge from the corpus: $p" >&2
      fails=$((fails + 1))
    fi
  done < <(jq -r '.files[]' "$manifest")
  [ "$fails" -eq 0 ]
}
```

**O que EXATAMENTE quebra quando a 36 editar:** um `fails` por arquivo tocado. Só a onda
zero produz **34 falhas**; com os sítios de estado, chega perto de 50. A mensagem é
`vendored bytes diverge from the corpus: <path>` — nomeada, mas sem noção de "divergência
autorizada".

**O que NÃO quebra** (verificado arquivo a arquivo):
- `:390` presença de cada `files[]` sob `cairn/gsd/` — só nomes.
- `:402` + `assert_tree_set_exact:160-175` — só conjuntos, em ambos os sentidos.
- `:509` closure re-run vs manifest — só conjuntos de arquivo.
- `:527` LICENSE byte-idêntico — não é arquivo adaptado.
- `:487` totals 171/29957 — lê os campos do próprio MANIFEST, não recomputa a árvore.
- `:450`/`:460` o cut (ausência de blocos) — presença/ausência, não bytes.

**Estado de hoje que engana:** `.cairn/cache/` **não existe** neste checkout (é
gitignored — `.gitignore:13`), então o teste `:503` **SKIPA agora**. Uma fase que rodar
`bats tests/cairn-vendoring.bats` local e ver verde NÃO provou nada. Quem tiver o cache
(quem já rodou `cairn-inventory.sh` com rede) verá a suíte vermelha.

**Como o teste precisa evoluir — três formas, na ordem de preferência pela doutrina da casa:**

1. **Allowlist de adaptados, no molde do oráculo com raiz parametrizada.**
   `assert_tree_bytes_match` ganha um quarto argumento (o conjunto de caminhos
   autorizados a divergir) e passa a exigir **byte-igualdade para todo caminho FORA da
   lista** e **divergência OBRIGATÓRIA para todo caminho DENTRO dela** — dois sentidos,
   como `assert_tree_set_exact` já faz para conjuntos. Um arquivo na allowlist que
   voltou a ser byte-idêntico é falha: significa que a adaptação foi perdida (por
   `vendor`, por merge, por revert).
2. **Manifesto de divergência versionado**, no molde de
   `tests/fixtures/gsd-goldens/divergences.json` (55 entradas hoje, schema
   `{aspect, cairn, family, reason, upstream, verb}`, tipo testado em
   `cairn-gsd.bats:861-870`). A entrada `section-manifest-empty` desse arquivo já cita a
   fase 36 nominalmente.
3. **Baseline nova** (re-pin do cache pós-edição): descartada — mata a capacidade de
   provar "nada além do adaptado mudou", que é o valor inteiro do teste.

O controle negativo obrigatório existe pronto como molde em `:465-474`: injetar num
diretório forjado (a) um arquivo NÃO-allowlisted alterado e (b) um arquivo allowlisted
revertido, e provar que o MESMO laço morde os dois.

---

### 4. O invariante de exatidão dois-sentidos: `git status --porcelain cairn/gsd/`

**Medido: esse gate NÃO é um teste bats.** Ele vive apenas nos blocos de verificação dos
planos e summaries das fases 33-35, mais os quatro docstrings de §2. Âncoras:

| Arquivo | Linha | Forma |
|---|---|---|
| `.planning/phases/33-.../33-01-PLAN.md` | 265 | dentro de `<automated>`: `… && test -z "$(git status --porcelain cairn/gsd/)"` |
| `.planning/phases/33-.../33-01-PLAN.md` | 268 | a prosa: "nenhum arquivo novo ou alterado sob cairn/gsd/" |
| `.planning/phases/33-.../33-02-PLAN.md` | 231 | "nada escrito sob cairn/gsd/ — … vazio" |
| `.planning/phases/34-.../34-01-PLAN.md` | 254 | "… vazio — contratos intocados" |
| `.planning/phases/34-.../34-02..05-PLAN.md` | 203 / 191 / 188 / 212 | mesma linha |
| `.planning/phases/35-.../35-CONTEXT.md` | 102 | herdado |
| SUMMARYs 33-01:185, 33-02:165, 33-03:78, 34-01:94, 34-02:72, 34-03:69, 34-04:66, 34-05:81, 35-01:76, 35-02:69 | — | a prova de que o gate foi verde |

**Como precisa mudar:** o gate não é apagado, é **invertido e nomeado**. Para a 36:
`git status --porcelain cairn/gsd/` passa a ser NÃO-vazio por desenho, e a verificação
vira "o conjunto de caminhos modificados sob `cairn/gsd/` é EXATAMENTE o da allowlist da
onda — nada a mais". Forma disponível na casa: o `comm` dois-sentidos de
`assert_tree_set_exact:160-175` aplicado à saída do porcelain contra a allowlist.
`cairn/gsd/contracts/` e `cairn/gsd/MANIFEST.json` permanecem no lado "vazio" do gate.

Os 4 docstrings continuam verdadeiros como estão ("SOMENTE-LEITURA **para este script**")
— nenhum dos quatro scripts passa a escrever. O script novo de substituição é o primeiro
a escrever, e o docstring dele precisa declarar isso em voz alta, no molde do docstring
de rede do `cairn-inventory.py:13-27` ("ESTE SCRIPT FALA COM A REDE… — E SÓ NELA").

---

### 5. Sítios de estado por workflow — os quatro padrões, com exemplos verificados

**Contagem canônica medida agora** (BROAD_RE de `cairn-inventory.py:176`, excluindo a
linha do shim que *define* `gsd_run`):

| Escopo | chamadas |
|---|---|
| workflows raiz (8) | **147** — execute-phase 48, plan-phase 36, verify-work 18, autonomous 17, quick 17, discuss-phase 8, debug 2, fast 1 |
| fragments (42) | **42** |
| agents (16) | **65** |

`.planning/` citado por workflow raiz: execute-phase 14, debug 13, discuss-phase 10,
autonomous 6, quick 5, plan-phase 4, verify-work 3, fast 2.

#### (a) Leitura MECÂNICA de STATE.md → vira consulta ao binário

```
cairn/gsd/gsd-core/workflows/autonomous.md:138   STATE_CONTENT=$(cat .planning/STATE.md 2>/dev/null || true)
cairn/gsd/gsd-core/workflows/autonomous.md:614   STATE_CONTENT=$(cat .planning/STATE.md 2>/dev/null || true)   ← o MESMO padrão, duas vezes
cairn/gsd/gsd-core/workflows/autonomous.md:622   cat .planning/STATE.md                                        ← "Read STATE.md fresh:" (:619)
cairn/gsd/gsd-core/workflows/fast.md:77          if grep -q "Quick Tasks Completed" .planning/STATE.md 2>/dev/null; then
cairn/gsd/gsd-core/workflows/discuss-phase.md:240 cat .planning/STATE.md 2>/dev/null || true
```

Mais duas em prosa (sem comando, mesma semântica de FATO):
`execute-phase.md:41` "Read STATE.md before any operation to load project context.";
`quick.md:589` "Read STATE.md and check for `### Quick Tasks Completed` section."

`fast.md:77` é o caso mais claro: a linha **imediatamente seguinte** (`:78`) já chama
`gsd_run quick-tasks-append` — o workflow pergunta ao markdown para decidir se chama o
binário. O `grep -q` inteiro é substituível por um verbo.

#### (b) Estado por VARIÁVEL — o que `grep 'STATE.md'` não acha

**12 linhas medidas** (padrão `STATE_PATH|{state_path}|state_raw|state_exists|STATE_FILE`
sobre workflows + agents + references). O research §5.1 citou 13 *(laudo)*; a diferença
é escolha de padrão — `state_raw` não ocorre hoje. Uso o meu número medido:

```
plan-phase.md:550     STATE_PATH=$(_gsd_field "$INIT" state_path)
plan-phase.md:652     API_SURFACE_PATH="$(dirname "$STATE_PATH")/intel/API-SURFACE.md"   ← STATE_PATH usado como ÂNCORA DE DIRETÓRIO
plan-phase.md:695     - {state_path} (Project State)                                     ← injetado num prompt de subagente
quick.md:150          STATE_PATH="$(dirname "${quick_dir}")/STATE.md"                    ← derivado, não vem do binário (#2376)
quick.md:313          - ${STATE_PATH} (Project State)
quick.md:431          - ${STATE_PATH} (Project state)
quick/steps/research-phase.md:34  - ${STATE_PATH} (Project state — what's already built)
verify-work.md:709    - {state_path} (Project State)
autonomous.md:101     Parse JSON for: … `state_exists`, `commit_docs`.
autonomous.md:104     **If `state_exists` is false:** Error — "No STATE.md found. …"
execute-phase.md:90   Parse JSON for: … `state_exists`, `roadmap_exists`, `phase_req_ids`, …
execute-phase.md:152  **If `state_exists` is false but `.planning/` exists:** Offer reconstruct or continue.
```

> **Correção medida no plano 36-03 (2026-08-11).** O bloco acima listava 11 linhas
> enquanto o texto dizia 12: faltava `execute-phase.md:90`, acrescentada acima. O
> total de 12 estava certo; a listagem é que estava curta, e a linha que faltava é
> justamente uma das quatro de `state_exists`. A divisão medida é **8 + 4**: oito
> linhas nas quatro grafias `STATE_PATH|{state_path}|STATE_FILE|state_raw` (as que o
> oráculo do 36-03 mede como família B) e quatro linhas de `state_exists`
> (autonomous 2, execute-phase 2), que o oráculo deixa DE FORA por decisão escrita —
> são campo do bundle de init, fato que já vem do binário desde a fase 34.

Três subclasses distintas, e o plano precisa tratá-las separado:
- **:550** — o caminho vem do binário e é usado só para montar outro caminho (:652). É
  transporte, não leitura de fato.
- **:695, :313, :431, :709, research-phase.md:34** — o caminho é **injetado no prompt de
  um subagente**, que então lê o arquivo. A leitura acontece FORA do workflow: a métrica
  de cobertura por grep no workflow declara verde e o subagente continua lendo markdown.

  > **Correção medida no plano 36-04 (2026-08-11).** São **SEIS**, não cinco. O sexto é
  > `execute-phase.md:750` — `- ${PROJECT_ROOT}/.planning/STATE.md (State)` — que a
  > listagem acima não tinha porque ele fica fora das 12 linhas do bloco: não usa nenhuma
  > das quatro grafias de estado, é o **caminho literal** montado sobre outra variável.
  > É o pior dos seis: sem comando de leitura (fora da família A), sem grafia de variável
  > de estado (fora da B) e sem prosa (fora da C) — invisível às três famílias do oráculo
  > do 36-03. Foi o que obrigou a **família D** (a forma de injeção como classe,
  > `tests/cairn-prompt-state.bats`), cuja regex morde exatamente esses três sítios
  > remanescentes (`plan-phase.md:695`, `verify-work.md:709`, `execute-phase.md:750`) e
  > zero falso-positivo na árvore. Consequência para quem planeja: as duas grafias com
  > variável **já casavam** a família B, então "estender B para cobrir a injeção" era
  > no-op; a cobertura nova está toda na terceira grafia.
- **:90/:101/:104/:152** — `state_exists` é predicado sobre a existência do ARQUIVO. Com o
  bd como dono do estado, o predicado muda de significado, não só de fonte. **Decisão do
  36-03:** as quatro ficam fora da família B do oráculo — pô-las dentro obrigaria quatro
  isenções PERMANENTES para descrever comportamento correto, e isenção que nunca morre é
  ruído que treina a ignorar a tabela.

`quick.md:150` é caso à parte: o caminho é **derivado por `dirname`** porque
`init.quick` não emite `state_path` (a nota está em `quick.md:148`, com o issue #2376).
Nenhum grep por nome de verbo acha isso.

#### (c) Escrita em STATE.md → `set-state` / verbo do bd

Já convertidas (o molde a copiar):
```
execute-phase.md:204   gsd_run query state.update last_gate_trip "${PLAN_ID}/${TASK_ID}" || true
discuss-phase.md:480   gsd_run query state.record-session \
fast.md:78             gsd_run quick-tasks-append --task "$TASK" || echo "⚠ fast.md log_to_state: …"
agents/gsd-executor.md:740  gsd_run query state.update-progress
agents/gsd-executor.md:743  gsd_run query state.record-metric \
agents/gsd-executor.md:753  gsd_run query state.record-session \
```

Ainda em PROSA imperativa (o alvo da fase — instrução para o modelo escrever o arquivo):
```
execute-phase.md:323   **Update STATE.md for phase start:**
execute-phase.md:454   - Update STATE.md plan status to complete
discuss-phase.md:477   Update STATE.md with session info:
quick.md:583           **Step 7: Update STATE.md**
quick.md:585           Update STATE.md with quick task completion record.
```

`discuss-phase.md:477` é o par perfeito de antes/depois: a prosa na :477 e o verbo na
:480 no mesmo bloco. `quick.md:627` documenta o equivalente para fora do workflow.

> **Regra do CONTEXT (integration point) que morde aqui:** "nenhum workflow adaptado pode
> passar a escrever em ROADMAP/REQUIREMENTS por outro caminho" — o bookkeep do cairn é o
> dono. Converter `Update STATE.md` para um verbo é correto; converter uma prosa sobre
> ROADMAP para escrita direta é regressão.

#### (d) Leitura LEGÍTIMA de documento — NÃO deve mudar

```
discuss-phase.md:238   cat .planning/PROJECT.md 2>/dev/null || true
discuss-phase.md:239   cat .planning/REQUIREMENTS.md 2>/dev/null || true
discuss-phase.md:243   Read at most **3** prior CONTEXT.md files … se DECISIONS-INDEX.md existir, ler esse
plan-phase.md:1356     `gap-analysis` capability (ADR-857 §53). Reads REQUIREMENTS.md and CONTEXT.md
discuss-phase.md:85    1. Read the phase goal from ROADMAP.md
```

**`discuss-phase.md:238-240` é o bloco-armadilha**: três `cat` consecutivos no MESMO
fence, e só o terceiro (`:240`, STATE.md) é fato. Uma substituição por bloco converte os
três; uma por linha converte um. O plano precisa que a unidade de edição seja a LINHA.

> **Desarmado no plano 36-04 (2026-08-11).** A edição foi por linha: `:238` e `:239`
> seguem byte a byte no diff (aparecem como linhas de contexto) e só `:240` virou
> `gsd_run query state.load`. `quick.md:589` (a outra leitura em prosa citada em §5a)
> também caiu, junto com o Step 7 inteiro. As citações de linha desta seção são de ANTES
> das ondas 3 e 4: confira contra o arquivo antes de usá-las como âncora.

---

### 6. O bug `section_manifest` — 6 sítios, 6 goldens, e o mecanismo de regravação

**Os 6 sítios, todos idênticos em forma** (`grep -n 'section_manifest' cairn/scripts/cairn-gsd-init.py`):

```
574:    result["section_manifest"] = []
583:        "section_manifest": [],
614:        "section_manifest": [],
786:        "section_manifest": [],
823:        "section_manifest": [],
856:        "section_manifest": [],
```

**Os 6 goldens que congelam** (`tests/fixtures/gsd-goldens/`):
`init-autonomous.golden.json`, `init-debug.golden.json`, `init-execute-phase.golden.json`,
`init-plan-phase.golden.json`, `init-quick.golden.json`, `init-verify-work.golden.json`.

**Os quatro fatos que decidem COMO regravar (todos verificados):**

1. **Os 6 são `provenance: "derived-from-contract"`**, `source.commit`
   `68a04ccf8ef74803bdb651e12c3b85b218bbccdf`. Não são `recorded`.
2. **`--record` é a ferramenta ERRADA aqui.** `cairn-gsd-record.py:2-9` grava o golden
   executando *"o gsd-tools.cjs do clone em cache, cenário a cenário"* — ou seja, o
   binário UPSTREAM. **CORRIGIDO no plano 36-02: upstream NÃO emite `[]`** — a suíte
   dele assere o contrário com estas palavras, em
   `tests/section-manifest-init-facts.test.cjs:67`: *"an absent workflow key must
   degrade to null, never []"*, e `src/init.cts:459-470` não tem caminho que produza
   lista. O `[]` era só da reimplementação em python. O recorder segue sendo a
   ferramenta errada, pelos outros dois motivos: trocaria a provenance para `recorded`,
   o que muda a comparação de FORMA para BYTES (`cairn-gsd.bats:216-237` vs `:238-254`),
   e exigiria um build do runtime. (O cache existe neste checkout; a afirmação original
   de que faltavam os três também não se sustentou.)
3. **A comparação de um `derived-from-contract` é por FORMA** (`cairn-gsd.bats:239-247`):
   *"derived-from-contract não promete os bytes do binário real: a comparação é SEMPRE por
   forma — exit exato + stdout normalizado (`jq -S` para json)"*. Logo, regravar =
   **editar o campo `.expect.stdout` à mão** e manter `provenance` e `source.commit`.
4. **`section_manifest` mora DENTRO de uma string JSON escapada.** O golden tem chaves
   `[expect, provenance, scenario, schema_version, source]`; o valor está em
   `.expect.stdout` como texto serializado (`"stdout": "{\n  \"project_root\": …"`), na
   linha 10 do stdout desescapado. **`jq '.expect.stdout.section_manifest = null'` não
   funciona** — é preciso desescapar, editar, re-escapar (ou substituir a substring
   `"section_manifest": []` → `"section_manifest": null` dentro da string). O envelope
   sobrevivente é validado em `cairn-gsd.bats:329-341` e o guard de timestamp em `:344`.

**A entrada de divergência já existe e cita a fase nominalmente**
(`tests/fixtures/gsd-goldens/divergences.json`, 55 entradas, schema
`{aspect, cairn, family, reason, upstream, verb}`):

```json
{"aspect":"section-manifest-empty","family":"init","verb":"*",
 "upstream":"section_manifest lista as seções do workflow renderizadas por runtime",
 "cairn":"section_manifest emitido [] — as seções vivem nos workflows vendorizados; nenhum call site do cairn consome além de presença",
 "reason":"o manifest de seções upstream é renderização multi-runtime; a fase 36 (shims) decide se o preenche"}
```

Corrigir `[]`→`null` **reescreve essa entrada** (ela deixa de descrever o estado), não
adiciona uma nova.

**Os 21 gates literais na camada prompt** (a prosa que consome o campo): a especificação
está em `execute-phase.md:92`; o par null-vs-vazio está declarado em `debug.md:31`. Os
gates: `execute-phase.md:1221, 1278, 1282`; `autonomous.md:74, 98, 122, 356, 374, 386`;
`plan-phase.md:191, 208, 212, 285, 375, 849`; `quick.md:284, 290, 357, 363, 578`;
`verify-work.md:149, 166`. Forma invariável: ``If `section_manifest` is `null` or
`"<id>"` is in its `included` list: read and execute …``.

---

### 7. Os agentes — 8 de 16, e a forma de invocação

**Shim ⟺ chamada, sem exceção** (medido, `grep -c`): os 8 agentes com preâmbulo são
exatamente os 8 que chamam `gsd_run`; os outros 8 têm **zero** de ambos. Nenhum agente
chama `gsd_run` sem carregar o próprio shim, e nenhum carrega shim sem usar.

| Agente | linha do shim | linhas com `gsd_run` |
|---|---|---|
| `gsd-executor.md` | 80 | 17 |
| `gsd-plan-checker.md` | 707 | 12 |
| `gsd-phase-researcher.md` | 119 | 11 |
| `gsd-verifier.md` | 104 | 10 |
| `gsd-planner.md` | 608 | 7 |
| `gsd-debugger.md` | 961 | 3 |
| `gsd-debug-session-manager.md` | 96 | 3 |
| `gsd-ui-researcher.md` | 294 | 1 |

**Sem shim e sem chamada (8):** `gsd-advisor-researcher`, `gsd-code-reviewer`,
`gsd-codebase-mapper`, `gsd-integration-checker`, `gsd-nyquist-auditor`,
`gsd-pattern-mapper`, `gsd-ui-auditor`, `gsd-ui-checker`.

**A forma de invocação é IDÊNTICA à dos workflows** — mesma variante longa do preâmbulo,
mesmo fence, mesma primeira linha, mesmo unwrap de `@file:`. Par lado a lado:

```
# cairn/gsd/agents/gsd-executor.md:79-83
79: ```bash
80: _GSD_SHIM_NAME="gsd-tools.cjs"; …                       ← variante longa, sha1 a2732b0f
81: INIT=$(gsd_run query init.execute-phase "${PHASE}")
82: if [[ "$INIT" == @file:* ]]; then INIT=$(cat "${INIT#@file:}"); fi
83: ```

# cairn/gsd/gsd-core/workflows/execute-phase.md:83-88
83: _GSD_SHIM_NAME="gsd-tools.cjs"; …                       ← MESMA linha, mesmo sha1
84: WAVE_PARAM=""; if [[ "$ARGUMENTS" =~ … --wave … ]]; then WAVE_PARAM="--wave ${BASH_REMATCH[2]}"; fi
85: INIT=$(gsd_run query init.execute-phase "${PHASE_ARG}" $WAVE_PARAM)
86: if [[ "$INIT" == @file:* ]]; then INIT=$(cat "${INIT#@file:}"); fi
87: AGENT_SKILLS=$(gsd_run query agent-skills gsd-executor)
88: ```
```

**Consequência para o plano:** a onda zero é uma substituição SÓ, para 34 sítios; não há
"forma de agente" separada. E o unwrap `@file:` fica inerte —
`grep -rn '@file:' cairn/scripts/*.py` → **vazio**; o binário python nunca emite esse
prefixo. É dívida a registrar, não a corrigir nesta fase.

> **Recontado no plano 36-06 (2026-08-11).** São **16 sítios em 12 arquivos markdown**,
> não "16 em 10": `grep -rln '@file:' cairn/gsd/ --include='*.md'` dá 12 — os 5 agentes
> com shim (`gsd-debugger`, `gsd-executor`, `gsd-phase-researcher`, `gsd-plan-checker`,
> `gsd-planner`) e 7 workflows (`autonomous.md` com 4 linhas, `verify-work.md` com 2, e
> uma cada em `debug.md`, `discuss-phase.md`, `execute-phase.md`, `plan-phase.md`,
> `quick.md`). Quinze estão na forma `if [[ "$X" == @file:* ]]`; a décima sexta é a forma
> inline de `discuss-phase.md:119`, que uma busca pelo `if` não vê. Há ainda uma menção em
> `contracts/init.json` (nota de contrato, não sítio). A dívida entrou em
> `divergences.json` no plano 36-06, sob `desembrulho-at-file-inerte-divida-registrada`.

---

## Shared Patterns

### Falha nomeada com o comando que cria o fato
**Fonte:** `cairn-gsd-state.py:97-99` (`die`) + `:176-178` (`die_missing_dim` — nomeia a
dimensão E o comando); `cairn-inventory.py:302-305` (cache HEAD divergente diz "delete
the cache or pass --refresh"); `cairn-gsd.sh:7-10` (tabela de exits no cabeçalho).
**Aplicar a:** o `else` do preâmbulo novo (hoje `exit 1` mandando
`npx -y @opengsd/gsd-core@latest`, comando que a 37 vai matar) e ao sítio
`resolve-execution` de D-04.

### Escrita cirúrgica: só a região declarada, resto byte a byte
**Fonte:** `cairn-wrap.py:548-556` (docstring do replace_block) + `:596-599`
(write-only-when-changed) + `cairn-migrate.py:1866-1875` (marcador presente → no-op).
**Aplicar a:** o script de substituição da onda zero e a conversão dos sítios de estado.

### Oráculo com raiz parametrizada + controle negativo forjado
**Fonte:** `tests/cairn-vendoring.bats:420-448` (`assert_cut_holds "$root"`) e
`:465-474` (a metade de liveness: mesma função, árvore forjada, exit 1 e nome no stderr).
**Aplicar a:** todo gate novo desta fase — "os 34 blocos trocados", "nenhum `.md`
adaptado voltou ao byte upstream", "nenhum sítio de fato sobrou".

### Divergência consciente vai a JSON versionado, nunca a silêncio
**Fonte:** `tests/fixtures/gsd-goldens/divergences.json` (55 entradas, tipo testado em
`cairn-gsd.bats:861-870`).
**Aplicar a:** os 3 blocos de shim fora de workflows/agents (se ficarem), os 40
`references/` citados, `resolve-execution`, `requirements.revert-phase`, a grafia
`worktree.set-baseref`, os 193 caminhos `$HOME/.claude`, o unwrap `@file:` inerte, e a
correção da entrada `section-manifest-empty`.

### Contagem sai da ferramenta canônica — ou declara por que não
**Fonte:** `cairn-inventory.py:176` (`BROAD_RE`), `:9-11` (a métrica declarada).
**Aplicar a:** todo número do SUMMARY. **Ver a armadilha INV abaixo: hoje ela não
consegue medir a árvore editada sem um seam.**

---

## Armadilhas Estruturais (as que decidem o plano)

**VEND-BYTES — o conflito central.** `tests/cairn-vendoring.bats:503` afirma que os 171
arquivos de `cairn/gsd/` são byte-idênticos ao clone da tag. A fase 36 edita ≥34 deles.
O teste **skipa neste checkout** (`.cairn/cache/` ausente, `.gitignore:13`), então o
vermelho não aparece localmente. **O plano tem de tocar o teste na MESMA onda da primeira
edição** — allowlist dois-sentidos + controle negativo — ou a fase entrega uma suíte que
mente quando o cache existe.

**VEND-REVERT — o comando que desfaz a fase em silêncio.**
`cairn-inventory.py:825-837` (`cmd_vendor`) faz `shutil.copy2(src_path, dst_path)` do
cache sobre `--dest` (default `cairn/gsd`, `:799`) para **todo** caminho de `files[]`, e
`:838-840` confirma zero divergência depois. Um `cairn-inventory.sh vendor` rodado depois
da fase 36 **sobrescreve as 34 adaptações com os bytes do upstream, sem erro nenhum**. O
script precisa passar a recusar quando houver adaptações registradas, ou a allowlist vira
letra morta na primeira re-vendorização.

**INV-ESCOPO — a ferramenta canônica não mede a árvore editada.**
`ensure_corpus:268-312` exige que o corpus seja um clone git cujo `HEAD` == `TAG_COMMIT`,
e mata com exit 6 caso contrário (`:302-305`). `resolve_corpus:629-637` sempre resolve
o corpus para o cache, nunca para `cairn/gsd/`. **O "depois" de qualquer contagem desta
fase é immensurável pela ferramenta canônica como ela está.** O seam já existe e já é
exercitado: `--source <repo git local> --expect-commit <sha> --cache-dir <tmp>`
(`add_corpus_flags:620-626`; `tests/cairn-inventory.bats:37-46` monta exatamente isso com
`git init` + tag). O plano usa esse seam (ou declara por que não, como o CONTEXT manda).

**PORCELAIN — o gate herdado se inverte.** `git status --porcelain cairn/gsd/` vazio é
critério de aceite copiado em 11 planos/summaries das fases 33-35. Não é bats; é
convenção. Copiá-lo para a 36 reprova a fase por desenho. A forma nova: o conjunto de
caminhos sujos é EXATAMENTE a allowlist da onda (`comm` dois-sentidos, molde de
`assert_tree_set_exact:160-175`), com `contracts/` e `MANIFEST.json` do lado vazio.

**NODE-SOBREVIVE — trocar o shim não remove `node` do caminho executado.** Sete sítios
chamam `node -e` fora do preâmbulo: `execute-phase.md:674, 897, 919, 925`;
`plan-phase.md:549` (`_gsd_field`, que parseia TODO o JSON de init do plan-phase);
`gsd-verifier.md:426, 435`. Um teste de ponta a ponta que só valide o preâmbulo declara
verde num caminho que ainda quebra sem node.

> **Correção medida no plano 36-05 (2026-08-11).** Eram **14** no corpus, não sete —
> e são **13** depois desta onda, que fechou um.
> `grep -rn 'node -e' cairn/gsd/` (excluída a linha de preâmbulo, que a onda zero já
> trocou) dava, por arquivo: `execute-phase.md` 4 (`:674, 897, 919, 925`),
> `execute-phase/steps/executor-isolation-dispatch.md` **2** (`:96, 176`),
> `agents/gsd-verifier.md` 2 (`:426, 435`), `plan-phase.md` 1 (`:549` — fechado nesta
> onda), `references/specless-probe-fallback.md` **3** (`:98, 111, 116`) e
> `references/checkpoints.md` **2** (`:477, 512`). A listagem de sete omitia os 2 do
> fragment de isolamento e os 5 de `references/`. **Em escopo da fase são 9** (workflows
> + agents, D-02 deixa `references/` de fora): 1 fechado no 36-05, 2 de decisão escrita
> no 36-06 e 6 do 36-07. Os 5 de `references/` ficam como lacuna registrada, no mesmo
> lote dos 40 arquivos que D-02 adiou. Consequência para quem planeja: um plano que
> declarar "NODE-SOBREVIVE fechada" contando pela lista de sete declara verde com 7
> sítios de pé, e dois deles (`executor-isolation-dispatch.md`) estão dentro do escopo.
>
> **Saldo remedido no plano 36-06 (2026-08-11):** `grep -rn 'node -e' cairn/gsd/` (fora
> do preâmbulo) dá **13** — os mesmos de cima menos o do `plan-phase.md`, fechado no
> 36-05. Os **2 do `gsd-verifier.md`** deixaram de ser pendência: têm decisão escrita ao
> lado de cada um no próprio arquivo e em `divergences.json`
> (`spot-check-node-do-projeto-verificado-permanece`) — o runtime ali é o do PROJETO
> VERIFICADO (uma resposta de API, um export de módulo), não o do GSD, e convertê-los
> adaptaria o projeto sob verificação em vez da camada prompt. Ficam **6 em escopo para
> o 36-07** (4 em `execute-phase.md`, 2 no fragment de isolamento de executor) e **5 fora
> por D-02** (3 em `specless-probe-fallback.md`, 2 em `checkpoints.md`).

**MANIFEST-PROSA — `totals.lines` vira mentira.** `cairn/gsd/MANIFEST.json` carrega
`{files:171, lines:29957}` (`derived_from: {command: "cairn-inventory.sh closure --json",
date: "2026-08-10"}`) e `cairn-vendoring.bats:487` só confere o campo contra si mesmo.
Se a onda zero mudar a contagem de linhas, o número fica obsoleto sem nenhum teste
reclamar.

**SHIM-HOMÔNIMO.** `MANIFEST.json` tem `summary.shim_matches` com 8 entradas
(`autonomous → [commands/gsd/autonomous.md, skills/gsd-autonomous/SKILL.md]`, etc.).
**Isso é outro "shim"** — o par comando↔skill de cada workflow, não o preâmbulo
`_GSD_SHIM_NAME`. Um plano que confundir os dois vai procurar 16 arquivos e achar 34.

---

## No Analog Found

| Padrão | Onde | Motivo | O que usar no lugar |
|---|---|---|---|
| Substituição textual uniforme em N arquivos markdown | onda zero (34 blocos) | nenhum script da casa reescreve `.md` por substituição; `cairn-relabel.py` não toca markdown; os 4 irmãos GSD declaram `cairn/gsd/` SOMENTE-LEITURA | script novo em `cairn/scripts/` na forma de `cairn-wrap.py` (`--check` → `EXIT_STALE=3` + `difflib.unified_diff`; write-only-when-changed `:596-599`; recusa nominal de caminho proibido no molde `cairn-migrate.py:1861-1863`) + bats de idempotência no molde `bench-publish.bats:109` + cobertura no molde `assert_cut_holds:422-448` com o controle negativo `:465-474` |
| Teste que valida CONTEÚDO SEMÂNTICO de prompt | "zero leitura de `.planning/` como fato" | o único teste de conteúdo `.md` sob `cairn/gsd/` é a byte-paridade contra o upstream (`cairn-vendoring.bats:503`) — afirma o inverso; `tests/cairn-inventory.bats` só valida markdown SINTÉTICO de fixture | ENTREGUE no plano 36-03: `tests/cairn-prompt-state.bats`, grep-oráculo tabular com raiz parametrizada e controle negativo forjado, cobrindo TRÊS famílias — **A** leitura mecânica (`cat|grep|head|tail|wc|test -f|[ -f` com o arquivo de estado como argumento, mais `@.planning/STATE.md`), **B** estado por variável (`STATE_PATH`, `{state_path}`, `STATE_FILE`, `state_raw` — **`state_exists` NÃO**, por decisão escrita em §5b), **C** prosa imperativa `Update STATE.md` MAIS a forma passiva `STATE.md updated|read|checked|written|exists` (medida: 8 linhas na árvore, e sem ela `fast.md:108` ficaria de pé com o arquivo declarado verde). A métrica por nome de arquivo sozinha declara cobertura que não existe (12 linhas escapariam) |
| Regravação de golden `derived-from-contract` | os 6 do `section_manifest` | `cairn-gsd-record.py` grava do binário UPSTREAM (que emite `[]`) e troca a provenance para `recorded`, mudando a comparação de forma para bytes | edição do campo `.expect.stdout` (string JSON escapada — substituir a substring `"section_manifest": []`), `provenance` e `source.commit` intactos, `cairn-gsd.bats:329-341` como validador de envelope, entrada `section-manifest-empty` de `divergences.json` reescrita |
| Verbo `resolve-execution` | `references/execute-phase-quota-recovery.md:13` | fora dos 87 do universo; sítio consome o JSON em 5 `jq` sem tolerância | D-04: falha nomeada + prosa de recuperação manual — molde de mensagem em `cairn-gsd-state.py:176-178` |

---

## Metadata

**Analog search scope:** `cairn/gsd/gsd-core/workflows/` (50), `cairn/gsd/agents/` (16),
`cairn/gsd/gsd-core/references/`, `cairn/gsd/commands/`, `cairn/gsd/skills/`,
`cairn/scripts/` (27 py), `tests/` (52 bats), `tests/fixtures/gsd-goldens/`
**Files scanned:** 34 arquivos com shim (classificados por sha1 da linha), 8 workflows
raiz, 16 agentes, 6 scripts python lidos em profundidade (`cairn-inventory.py`,
`cairn-wrap.py`, `cairn-migrate.py`, `cairn-gsd.py`, `cairn-gsd-init.py`,
`cairn-gsd-record.py`), 3 bats (`cairn-vendoring.bats`, `cairn-gsd.bats`,
`cairn-inventory.bats`), 7 goldens + `divergences.json` + `MANIFEST.json`
**Pattern extraction date:** 2026-08-11 (HEAD 47e9a17, branch feat/v1.6-transplante)
**Estado do ambiente na medição:** `.cairn/cache/gsd-core-v1.10.0` **AUSENTE** — todos os
testes `real_cache_or_skip` de `cairn-vendoring.bats` estão skipando neste checkout.

> **Medido de novo no plano 36-03 (worktree `CairnGo-phase-36`, HEAD bb4bbe7):** o cache
> **EXISTE** nesta árvore e nenhum teste de `cairn-vendoring.bats` skipa aqui — os 26
> passam de verdade, incluindo `real tree: … on both senses of the registry` e
> `PORCELAIN invertido`. O aviso acima vale para um checkout sem cache; num worktree que
> o tem, o verde do oráculo de bytes dois-sentidos É prova. Confira qual é o seu caso
> antes de confiar (ou desconfiar) do verde.
