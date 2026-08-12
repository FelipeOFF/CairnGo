# Phase 34: O binário python, o núcleo de estado sobre o bd - Pattern Map

**Mapped:** 2026-08-10
**Files analyzed:** 7 (2 scripts novos, 1 dispatcher modificado, harness + goldens estendidos, tabela verbo→dimensão, wrappers .sh)
**Analogs found:** 6 / 7 (o padrão `bd set-state` não tem análogo em código — só as regras medidas do research/CONTEXT)

## File Classification

| Arquivo novo/modificado | Role | Data Flow | Análogo mais próximo | Qualidade |
|---|---|---|---|---|
| `cairn/scripts/cairn-gsd-state.py` (novo) | verb-handler CLI (estado 10 + roadmap-phase 12 verbos) | request-response sobre bd (query + set-state) | `cairn/scripts/cairn-gsd.py` (forma) + `cairn-lease.py` (acesso bd) + `cairn-status.py` (labels) | exact (forma) / role-match (fonte bd) |
| `cairn/scripts/cairn-gsd-init.py` (novo) | verb-handler CLI (init 9 + worktree 6 + misc 29−5 órfãos) | request-response + file-I/O | `cairn-gsd.py` (forma) + `cairn-parallel.py` (worktree) + `cairn-bookkeep.py` (parsers) | role-match |
| `cairn/scripts/cairn-gsd.py` (mod) | dispatcher/roteador | request-response (exec pros irmãos) | ele próprio (PHASE_BY_FAMILY → tabela família→irmão) | exact |
| `tests/cairn-gsd.bats` (mod) | test harness (diferencial + cobertura) | batch | ele próprio — o seam da 33 provado por teste | exact |
| `tests/fixtures/gsd-goldens/scenarios.json` + `*.golden.json` (novos cenários) | fixture | — | cenários e goldens da 33 | exact |
| Tabela verbo→dimensão (discrição: constante no script OU arquivo em `cairn/gsd/contracts/`) | config | — | `PHASE_BY_FAMILY` (cairn-gsd.py:107-114) ou `contracts.json .verbs` + `load_json_strict` | role-match |
| `cairn-gsd-state.sh` / `cairn-gsd-init.sh` (opcionais — ver nota em Pattern Assignments) | wrapper shell | — | `cairn/scripts/cairn-gsd.sh` | exact |

Universo por família (de `cairn/gsd/contracts/*.json`, `.verbs[].verb`):
- **estado (10):** state.add-blocker, state.add-decision, state.advance-plan, state.begin-phase, state.load, state.planned-phase, state.record-metric, state.record-session, state.update, state.update-progress
- **roadmap-phase (12):** find-phase, phase, phase-plan-index, phase.complete, phase.list-artifacts, phase.list-plans, phase.mvp-mode, phases.list, roadmap.analyze, roadmap.annotate-dependencies, roadmap.get-phase, roadmap.update-plan-progress
- **worktree (6):** worktree, worktree.base-check, worktree.cleanup-wave, worktree.create, worktree.reap-orphans, worktree.record-agent
- **init (9):** init.autonomous, init.debug, init.execute-phase, init.manager, init.milestone-op, init.phase-op, init.plan-phase, init.quick, init.verify-work
- **misc (29, dos quais 5 órfãos ficam na 35):** órfãos = `ORPHANS_PHASE_35` de cairn-gsd.py:116-122 (audit-open, review-lane, agent.classify-failure, task.is-behavior-adding, run-with-timeout) — continuam exit 4 nomeando a fase 35. Os 24 restantes: classify-confidence, estimate-check, frontmatter.get/set/validate, git.base-branch, graphify, history-digest, intel, is, learnings.copy/query, normalize-test-command, package-legitimacy, plan.task-structure, quick-tasks-append, requirements.mark-complete, research-plan, research-store, summary-extract, teams-status, todo.match-phase, websearch, windows. A partição exata entre os dois irmãos é decisão do plano (CONTEXT, Claude's Discretion) — o CONTEXT já ancora init+worktree+misc no `cairn-gsd-init.py`.

## Pattern Assignments

### `cairn/scripts/cairn-gsd-state.py` (verb-handler, request-response sobre bd)

**Análogo primário:** `cairn/scripts/cairn-gsd.py` — forma do script, exit codes, die, handlers.

**Cabeçalho e exit codes** (cairn-gsd.py:70-142) — copiar a forma: docstring com Usage/Exit codes/divergências declaradas, constantes de exit, `die` com tag:

```python
EXIT_OK = 0
EXIT_CONTRACT = 1
EXIT_USAGE = 2
EXIT_UNIMPLEMENTED = 4

TAG_PREFIX = "[cairn-gsd]"

def die(msg, code=EXIT_USAGE):
    print(f"{TAG_PREFIX} error: {msg}", file=sys.stderr)
    sys.exit(code)
```

O irmão deve manter o MESMO vocabulário de exits do dispatcher (o wrapper `cairn-gsd.sh` documenta 0/1/2/4) — o exec preserva o exit do irmão como exit do dispatcher.

**Forma de um handler** (cairn-gsd.py:1966-1992, corpo de `handle_resolve_model`) — parse manual de flags sobre `rest`, flag desconhecida ignorada best-effort, `return EXIT_OK`:

```python
    if not agent_type:
        die("agent-type required", EXIT_CONTRACT)
    config = load_scope_config_defensive()
    ...
    result = {"model": model, "profile": profile, "effort": effort}
    if pick:
        emit(js_string(result[pick]) if pick in result else "undefined")
        return EXIT_OK
    output_like_binary(result, raw, model)
    return EXIT_OK
```

A tabela `HANDLERS = {"verbo": handle_x, ...}` (cairn-gsd.py:1995-2005) é o molde da tabela do irmão. O envelope de saída (`output_like_binary` L874, `emit` L336, `stringify`/`js_string` L301-325) reproduz a semântica medida do binário (`--raw` = String(valor); sem `--raw` = JSON.stringify(v, null, 2), sem newline final) — copiar essas funções, não reimplementar de cabeça. A SHAPE de cada payload vem de `cairn/gsd/contracts/estado.json` e `roadmap-phase.json` (campo `output.shape` + `notes` por verbo).

**Acesso ao bd** (cairn-lease.py:287-299) — o molde `run_bd`:

```python
def run_bd(args, root):
    """Run `bd -C <root> <args>`, returning raw stdout. Exits EXIT_NO_BD on
    any failure — bd missing from PATH or a non-zero exit — never lets a
    subprocess failure surface as a traceback."""
    cmd = ["bd", "-C", str(root)] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        die("'bd' not found on PATH", EXIT_NO_BD)
    if proc.returncode != 0:
        die(f"bd {args[0] if args else ''} failed: "
            f"{proc.stderr.strip() or 'unknown error'}", EXIT_NO_BD)
    return proc.stdout
```

Variante com parse de `--json` embutido (cairn-status.py:570-581): apenda `--json` no cmd, `json.loads(proc.stdout or "[]")`, `data if isinstance(data, list) else [data]`, die nomeado em JSON inválido. Guard de presença: `shutil.which("bd") is None` → die cedo (cairn-lease.py:803, cairn-map.py:133).

**Consulta por label projetado — a ÚNICA chave de consulta (D-02)** (cairn-status.py:612-623):

```python
PHASE_LABEL = re.compile(r"^phase-0*(\d+)$")

def issue_phase_ns(iss):
    out = set()
    for lab in as_str_list(iss.get("labels")):
        m = PHASE_LABEL.match(lab.strip())
        if m:
            out.add(int(m.group(1)))
    return out
```

Com `as_str_list` (cairn-status.py:594-609) como shape defensivo dos campos do bd (string vira lista de 1, `{id:...}` colapsa pro id, None cai fora). Consulta por label é `bd list -l <label> --all --limit 0 --json` (cairn-lease.py:315) ou `bd query "label=dim:valor"` (forma do research). **NUNCA consultar por metadata aninhado** — rc 0 silencioso, medido (CONTEXT, Established Patterns).

**Resolução de ator para `--actor`** (cairn-lease.py:266-281) — mesma ordem que o bd documenta:

```python
def resolve_actor(root):
    env_actor = os.environ.get("BEADS_ACTOR")
    if env_actor:
        return env_actor
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "config", "user.name"],
            capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except FileNotFoundError:
        pass
    return os.environ.get("USER")
```

**Semântica de fase/plano — copiar a FORMA, nunca a FONTE.** `resolve_active_phase` (cairn-lease.py:241-263) mostra a leniência de parse (aspas, zeros à esquerda, `re.search(r"\d+")`) — mas lê `.planning/STATE.md`, que é EXATAMENTE o fallback que a 34 proíbe (duas fontes é a doença; CONTEXT, Specific Ideas). O verbo de estado responde do bd ou FALHA nomeado. Os regexes de identificação de plano/fase reutilizáveis: cairn-status.py:385-387 —

```python
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")
PLAN_FILE = re.compile(r"^\d+-(\d+)-PLAN\.md$")
SUMMARY_FILE = re.compile(r"^\d+-(\d+)-SUMMARY\.md$")
```

**Falha nomeada para fato ausente (CORE-04)** — herda a forma do dispatcher (cairn-gsd.py:2034-2038): a mensagem nomeia o que falta E o comando que resolve. Versão do verbo de estado: `die("o bd não tem phase_status para este repo; rode 'cairn-gsd.sh state.begin-phase <N>' para criar o fato", EXIT_CONTRACT)`. Nunca resposta vazia, nunca fallback pra markdown.

**Caso canônico de idempotência (CORE-03):** o replay `current_phase 18` (state.record-metric lendo prosa obsoleta) vira cenário de golden — o verbo relê o fato do bd, não prosa.

---

### `cairn/scripts/cairn-gsd-init.py` (verb-handler, request-response + file-I/O)

Mesma forma de script do irmão de estado (cabeçalho, die, HANDLERS, envelope — ver acima). Análogos específicos por família:

**worktree:** `cairn/scripts/cairn-parallel.py` — a semântica já existe, reaproveitar por cópia de forma:
- `worktree_entries(top)` L745 — parse de `git worktree list --porcelain`
- `is_linked_worktree(top)` L731, `worktree_entry_at(top, path)` L788, `branch_exists` L797
- `phase_slug(top, phase)` L806 e `phase_layout(top, phase)` L831 — convenção de nome/caminho de worktree por fase
- `rollback(top, worktree, branch, created_worktree, created_branch)` L990 — desfazer criação parcial
- `run_git(cwd, args)` L694 — subprocess git com die nomeado

**init (9 bundles):** a estimativa de ~500 linhas foi re-derivada na 31-04 (delta −10; SUMMARYs `31-04/33-*` são leitura obrigatória do CONTEXT). Cada `init.<workflow>` compõe um bundle de contexto — a shape exata por bundle está em `cairn/gsd/contracts/init.json` (`output.shape` por verbo, flag `--pick`). Análogo de composição: `build_agent_skills_block` (cairn-gsd.py:1179-1263) monta bloco a partir de config + filesystem com diagnostics.

**misc — parsers existentes:**
- `frontmatter.get/set/validate` → `parse_state_frontmatter_items` / `parse_state_frontmatter` (cairn-bookkeep.py:1104-1150)
- `git.base-branch` → `run_git` (cairn-gsd.py:784-799, com timeout e die nomeado)
- `summary-extract`, `todo.match-phase` → parsers de roadmap/plan em cairn-bookkeep.py (`parse_roadmap` L958, `plan_id_matches` L1186) e cairn-status.py (bloco de regexes L369-499)

**Chamar irmão sem reimplementar** (cairn-bookkeep.py:720-746) — quando um verbo precisa de fato que outro script da casa já calcula:

```python
def sibling(name):
    return str(Path(__file__).resolve().parent / name)

def run_sibling_json(argv):
    """Run a sibling cairn script and parse its --json, degrading to a named
    failure instead of a traceback. ... Two implementations of a TTL
    calculation that can disagree is this milestone's disease with a
    different hat on."""
    try:
        proc = subprocess.run([sys.executable] + argv, capture_output=True,
                              text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc)}
    out = {"ok": proc.returncode == 0, "exit": proc.returncode}
    ...
```

---

### `cairn/scripts/cairn-gsd.py` (modificado — roteamento por exec)

**O que muda:** `PHASE_BY_FAMILY` (L107-114) hoje mapeia estado/roadmap-phase/worktree/init/misc para "fase 34" (mensagem de exit 4). A 34 troca essas entradas por uma tabela família→script-irmão; `checagem` e os `ORPHANS_PHASE_35` (L116-122) continuam exit 4 nomeando a fase 35.

**O loop de despacho a estender** (cairn-gsd.py:2026-2041):

```python
    routes = build_routes()
    max_words = max(len(s.split()) for s in routes)
    for n in range(min(max_words, len(argv)), 0, -1):
        spelling = " ".join(argv[:n])
        hit = routes.get(spelling)
        if hit is None:
            continue
        verb, family = hit
        handler = HANDLERS.get(verb)
        if handler is None:
            die(f"verbo '{verb}' pertence à família '{family}', entregue "
                f"pela {phase_for(verb, family)} — ainda não implementado "
                f"neste script", EXIT_UNIMPLEMENTED)
        sys.exit(handler(argv[n:]))
```

Ponto de inserção: entre `HANDLERS.get` e o die de EXIT_UNIMPLEMENTED, consultar a tabela família→irmão e fazer exec. **Não há precedente python de exec na casa** — o precedente é shell: `cairn-gsd.sh` termina em `exec python3 "$HERE/cairn-gsd.py" "$@"` (passthrough de stdout/stderr/exit sem processo intermediário). A forma python equivalente:

```python
sibling = Path(__file__).resolve().parent / FAMILY_SCRIPT[family]
os.execv(sys.executable, [sys.executable, str(sibling), verb] + argv[n:])
```

(resolução de caminho pelo molde `sibling()` de cairn-bookkeep.py:720-721; passar o VERBO canônico já resolvido, não o spelling — o roteamento spelling→verbo é responsabilidade única do dispatcher, `build_routes` L161-191, e nenhuma tabela paralela é mantida no irmão.)

**`--list-implemented` (L2015-2022) precisa agregar os irmãos** — o guard de cobertura do bats consome essa enumeração. Ou o dispatcher roda cada irmão com `--list-implemented` e concatena, ou cada irmão expõe a sua e o guard soma; a primeira mantém o contrato de superfície única ("as chaves de HANDLERS, ordenadas", docstring L15-19) e não muda o bats.

**Nota .sh:** a convenção da casa é 1 wrapper .sh por .py (todos os 25 scripts têm). Como toda entrada passa pelo `cairn-gsd.sh` e os irmãos são detalhe de implementação do dispatcher, wrappers próprios são opcionais — se criados, copiar `cairn-gsd.sh` byte a byte trocando o alvo (12 linhas, header de Usage/Exit + `exec python3`).

---

### `tests/cairn-gsd.bats` + `tests/fixtures/gsd-goldens/` (estendidos — o seam da 33)

**O seam de reuso, como documentado no próprio harness** (cairn-gsd.bats:43-53): cenário novo = (1) entrada em `scenarios.json` (id, argv, fixture declarativo, compare, mask) + (2) golden irmão `<id>.golden.json`. O runner diferencial (L259) e os guards de integridade (L284, L350) iteram o manifesto — **nenhuma linha do runner muda para cenário novo**.

**Shape de cenário** (scenarios.json, entrada real):

```json
{
  "argv": ["query", "config-get", "model_profile"],
  "compare": "bytes",
  "expect_stderr": false,
  "fixture": {
    "files": {},
    "git": true,
    "planning_config": {"model_profile": "quality"}
  },
  "id": "config-get-scope-hit",
  "mask": null,
  "verb": "config-get"
}
```

**Shape de golden** (config-get-scope-hit.golden.json):

```json
{
  "expect": {"exit_code": 0, "stderr": null, "stdout": "\"quality\""},
  "provenance": "recorded",
  "scenario": "config-get-scope-hit",
  "schema_version": 1,
  "source": {
    "commit": "68a04ccf8ef74803bdb651e12c3b85b218bbccdf",
    "repo": "open-gsd/gsd-core",
    "tag": "v1.10.0"
  }
}
```

**Provenance dos goldens de estado: `derived-from-contract`, não `recorded`.** O schema já aceita as duas (cairn-gsd.bats:295-297) e o comparador só exige byte-igualdade para `recorded` (L181); para `derived-from-contract` compara FORMA (L194-215). O recorder (`cairn-gsd-record.py`) grava do binário REAL — que lê markdown; um verbo que responde do bd não pode ser gravado dele. Divergência de fonte se declara em `tests/fixtures/gsd-goldens/divergences.json` (molde já existe: entrada `workstream-root-layer` com aspect/family/upstream/cairn/reason), nunca improvisada.

**O fixture builder precisa de extensão bd.** `build_scenario_fixture` (cairn-gsd.bats:75-95) hoje monta `fixture.git`, `fixture.planning_config` e `fixture.files` — cenários de estado precisam de `fixture.bd` (init + fatos semeados). Molde de bd em fixture, usado por 15+ testes da casa (cairn-lease.bats:34, helpers.bash:353):

```bash
bd init -q --prefix lse --non-interactive >/dev/null 2>&1
```

A extensão entra no builder local do cairn-gsd.bats (precedente declarado L65-67: "helpers.bash is loaded by thirty suites and is not touched for one phase's shape"), com seeds via `bd create`/`bd set-state` declarados no cenário.

**O guard de cobertura precisa conhecer as famílias novas.** `trivial_verbs_of` (cairn-gsd.bats:530-536) filtra hardcoded as 5 famílias triviais:

```bash
trivial_verbs_of() {
  jq -r '.verbs | to_entries[]
    | select(.value.family == "config" or .value.family == "commit"
      or .value.family == "skills" or .value.family == "loop-hooks"
      or .value.family == "dispatch-model")
    | .key' "$1" | sort
}
```

A 34 acrescenta estado/roadmap-phase/worktree/init/misc ao filtro (menos os 5 órfãos da 35 — mesmo mecanismo de exclusão nominal) e compara com o `--list-implemented` agregado, mantendo o `comm` vazio nos dois sentidos (teste L538-561) e o controle negativo do verbo forjado (L563+).

**Doutrina de determinismo dos goldens** (cairn-gsd.bats:334-349): serialização da casa (`jq -S` byte-igual + newline final, `house_serialization_ok`) e NENHUMA chave de timestamp em nenhum nível (`free_of_timestamp_keys` — timestamp/recorded_at/generated_at/date/time). Verbos como `state.record-session` que naturalmente carregam tempo precisam de `mask` no cenário (molde `apply_mask_file`, L132-144: valor validado contra regex e trocado por `<masked>`).

---

### Tabela verbo→dimensão (D-02 — fonte única, forma a decidir no plano)

As duas formas aceitas pelo CONTEXT, com análogo cada:
- **Constante no script:** molde `PHASE_BY_FAMILY` (cairn-gsd.py:107-114) — dict comentado, com o racional em comentário.
- **Arquivo em `cairn/gsd/contracts/`:** molde do índice `contracts.json .verbs` (`"verbo" -> {"family": ..., "file": ...}`) lido por `load_json_strict` (cairn-gsd.py:148-158, die nomeado em falta/JSON inválido) e validado na carga como `build_routes` valida (L161-191: entrada sem campo obrigatório é die, não skip).

O vocabulário é o do D-02 (permanente, one-way): dimensões `phase`, `phase_status` (planned/executing/verified/complete), `plan` (NN-MM), `verification` (passed/failed/pending), `session`; label projetado legível (`phase_status:verified`). Os verbos gsd MAPEIAM para essas dimensões — o vocabulário do upstream não vira schema.

## Shared Patterns

### Escrita de estado: SEMPRE `bd set-state`, nunca `bd update` direto
**Fonte:** research §4 + CONTEXT (Reusable Assets) — não há análogo em código; nenhum script da casa chama `set-state` hoje (grep confirmado: zero ocorrências em `cairn/scripts/*.py` e `tests/*.bats`).
**Aplicar a:** todo verbo que transiciona estado nos dois irmãos.

```
bd set-state <id> <dim>=<val> --actor <ator> --reason <motivo>
```

Cria event bead + label projetado; a auditoria SÓ existe por esse caminho (`bd update` direto vira root sem motivo). Executar pelo molde `run_bd` (cairn-lease.py:287); ator pelo molde `resolve_actor` (cairn-lease.py:266). Escrita de metadata que NÃO é transição de estado (ex.: payload de lease) segue o molde `write_lease` (cairn-lease.py:326-332).

### Falha nomeada (die com comando prescrito)
**Fonte:** `cairn-gsd.py:140-142` (die) + L2034-2038 (mensagem que nomeia família e fase).
**Aplicar a:** dispatcher (verbo de família futura), irmãos (fato ausente no bd — nomear o fato E o comando que o cria), acesso ao bd (bd ausente/exit != 0/JSON inválido). Nunca traceback, nunca resposta vazia, nunca fallback pra markdown.

### Subprocess defensivo
**Fonte:** `cairn-lease.py:287-299` (bd), `cairn-gsd.py:784-799` (git com timeout), `cairn-bookkeep.py:724-746` (irmão python).
**Aplicar a:** todo subprocess dos dois irmãos. `capture_output=True, text=True`, FileNotFoundError → die nomeado, returncode != 0 → die com stderr truncado.

### Envelope de saída na semântica medida do binário
**Fonte:** `cairn-gsd.py:874-906` (`output_like_binary`), L292-336 (`js_number_text`/`js_string`/`stringify`/`emit`).
**Aplicar a:** todo verbo dos dois irmãos. `--raw` = String(valor); default = JSON.stringify(v, null, 2); sem newline final. Divergência deliberada → `divergences.json`, nunca improviso.

### Docstring-contrato no topo do script
**Fonte:** `cairn-gsd.py:1-69` e `cairn-gsd-record.py:1-46`.
**Aplicar a:** os dois irmãos. Usage, exit codes um a um, semântica medida com a data da medição, seams de teste declarados (env vars), e a regra "cairn/gsd/ é somente-leitura".

## No Analog Found

| Padrão | Família | Motivo | O que usar no lugar |
|---|---|---|---|
| `bd set-state` (transição com ator/motivo/label projetado) | estado, roadmap-phase | Nenhum script da casa chama set-state hoje | Regras medidas do research §4 + D-02 do CONTEXT, sobre o molde `run_bd` |
| exec python de irmão (substituição de processo) | dispatcher | Nenhum `os.exec*` em `cairn/scripts/*.py` | Precedente shell (`cairn-gsd.sh` L13: `exec python3 ...`); `os.execv` preserva stdout/exit como o exec do shell |
| fixture bd declarativo em cenário de golden | harness | `build_scenario_fixture` só monta git/planning_config/files | Extensão local no builder, molde `bd init -q --prefix X --non-interactive` (cairn-lease.bats:34, helpers.bash:353) |

## Metadata

**Analog search scope:** `cairn/scripts/`, `tests/`, `tests/fixtures/gsd-goldens/`, `cairn/gsd/contracts/`
**Files scanned:** 12 (cairn-gsd.py, cairn-gsd.sh, cairn-gsd-record.py, cairn-lease.py, cairn-status.py, cairn-bookkeep.py, cairn-parallel.py, cairn-map.py, cairn-relabel.py, cairn-gsd.bats, cairn-lease.bats, helpers.bash) + 6 contratos + manifesto/goldens
**Pattern extraction date:** 2026-08-10
