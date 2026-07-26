# Phase 2: Baseline Isolation + Multi-Baseline Harness - Research

**Researched:** 2026-07-25
**Domain:** Process-level environment isolation for the Claude Code CLI (`$HOME` override, `--bare`, `--plugin-dir` session-scoped plugin loading) + baseline-manifest design for a reproducible multi-arm benchmark
**Confidence:** HIGH (isolation mechanics verified live against the installed `claude` v2.1.220 binary, not just docs; plugin-provisioning mechanics verified against this repo's own marketplace/plugin manifests and the actual GSD plugin cache on disk; baseline-manifest/interleaving design is a synthesis MEDIUM-HIGH, informed by ARCHITECTURE.md's already-HIGH-confidence component split)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase Boundary:** Every benchmark run executes in a fresh, disposable, mechanically-isolated environment with explicit pinned configuration, across three baselines: vanilla Claude Code, GSD-only, and cairn. Requirements: FAIR-01 (isolation), FAIR-02 (baseline manifests), FAIR-03 (order randomization + 4-way cost decomposition). bd issues: CairnGo-60i, CairnGo-gc1, CairnGo-9bb.

**Phase 1 live findings that BIND this phase:**
- `--bare` requires API-key auth: verified live — `--bare` skips claude.ai OAuth and reports "Not logged in". Isolated baselines therefore authenticate via `ANTHROPIC_API_KEY` (env), never the operator's OAuth keychain. The key is read from the environment at run time, NEVER stored in any file this repo commits.
- Home-field overhead is real and measured: the operator's global environment injected 45-62k cache-creation tokens into Phase 1's non-isolated runs. Isolation (fresh `HOME`, `--bare`, explicit flags) is what removes it — this number is the baseline motivation, cite it.
- Model comes from manifests as a full pinned id (already enforced by bench-run.py + task.json).
- Parse stdout regardless of exit code; `is_error` ⊥ `verify_passed` (both proven live).

**Isolation mechanics (FAIR-01):**
- Fresh disposable workdir per run (already exists) PLUS scoped `HOME` override (empty temp HOME per run) so no global CLAUDE.md/MCP/hooks/settings leak into any baseline.
- The cairn/GSD baselines get their plugins provisioned EXPLICITLY inside the isolated environment (that is the baseline's payload), never inherited from the operator.

**Baseline manifests (FAIR-02):**
- `benchmarks/baselines/<name>.json`: pinned model id, claude flags (`--bare`, `--max-turns`, `--no-session-persistence`, permission mode), and the baseline's provisioning recipe (what gets installed into the isolated HOME). Vanilla = empty provisioning.
- Same task prompt, same fixture, same flags across all baselines — only the provisioning differs.

**Randomization + cost decomposition (FAIR-03):**
- Run order across baselines randomized/interleaved (seeded, seed recorded in the row for reproducibility — stdlib `random.Random(seed)`).
- Every row already carries the 4 usage components; the aggregation stays Phase 3 — this phase only guarantees the fields are captured per-baseline and the execution order is recorded.

**Test strategy (stub-first — CI stays $0):**
- ALL mechanics (HOME override, provisioning staging, manifest parsing, order randomization, seed recording) proven via the `CAIRN_BENCH_CLAUDE_BIN` stub in bats. The stub can ASSERT on its inherited env (e.g. print `$HOME` and env leakage markers into its canned output) — that's how isolation is tested at $0.
- Live validation of isolated auth is OPTIONAL in this phase: it requires `ANTHROPIC_API_KEY` in the operator's env. If the key is absent at execution time, deliver the mechanism + stub proofs, document the single pending live check in the SUMMARY (pending key, not a mechanism gap), and do NOT block the phase. If the key IS present, run at most ONE cheap live isolated run (haiku, smoke task) to prove the auth path, and record its cost.

### Claude's Discretion
- Exact manifest schema fields, HOME staging layout, how provisioning recipes are expressed, randomization CLI surface (flag vs manifest), whether bench-run grows `--baseline` flag vs a new orchestrating script (respect ARCHITECTURE.md's component split).

### Deferred Ideas (OUT OF SCOPE)
- N repetitions/aggregation/statistics — Phase 3. Competitor baseline — Phase 4. Corpus growth — Phase 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FAIR-01 | Cada rodada executa em ambiente isolado descartável (worktree fresco + `HOME` override) — zero herança de CLAUDE.md global, MCP servers ou hooks do operador | Live-verified `$HOME` override mechanics (Architecture Patterns Pattern 1, Common Pitfalls 1-2); minimal env-dict pattern for `subprocess.run(env=...)`; empirical proof no trust-dialog/onboarding blocks a scripted run |
| FAIR-02 | Baselines definidas por manifesto JSON explícito: mesmo modelo (id completo pinado), mesmo prompt de tarefa, `--bare` + flags explícitas, mesmas condições entre vanilla / GSD puro / cairn | Baseline manifest schema (Standard Stack, Code Examples); `--plugin-dir` session-scoped provisioning mechanics (Architecture Patterns Pattern 2); GSD plugin's own MCP-server + `node_modules` prerequisite (Common Pitfalls 4) |
| FAIR-03 | Ordem de execução randomizada/intercalada entre baselines e custo decomposto em 4 componentes | Seeded interleaving pattern with `random.Random(seed)` (Code Examples); cost-component fields already flow through per Phase 1 (`usage.*` passthrough proven) |
</phase_requirements>

## Summary

Phase 1 shipped a runner that invokes `claude -p` with the **operator's full, unscoped environment** — `subprocess.run(cmd, cwd=workdir, ...)` passes no `env=` argument, so the child process inherits every ambient var, and `~/.claude/` (personal CLAUDE.md, hooks, MCP servers, plugins) is read from the operator's real `$HOME` because nothing overrides it. This is not a hypothetical risk: it is the exact, already-measured cause of the 45-62k cache-creation-token overhead cited in Phase 1's own README. Phase 2's isolation mechanic is therefore concrete and small in code-surface: build an explicit, minimal `env` dict (`HOME=<fresh disposable dir>`, `PATH=<inherited, unscoped>`, `ANTHROPIC_API_KEY=<inherited if present>`) and pass it to the `claude` subprocess call only — not to the `verify.sh` call, which needs the full environment to run pytest/bats and is not part of what's being measured.

Live testing against the installed `claude` binary (v2.1.220) in a truly empty `$HOME` with an invalid API key confirms the whole isolation chain end-to-end at $0 cost: the trust dialog never appears (it is unconditionally skipped in `-p`/non-interactive mode per the CLI's own `--print` help text — not `--bare`-specific), no onboarding wizard blocks, `--no-session-persistence` genuinely leaves `.claude/sessions/` empty, and the only filesystem writes are a harmless `.claude.json` feature-flag cache and a `.claude/backups/` snapshot of it — both safe to discard with the disposable `$HOME`. `--bare`'s own `--help` text (read live from the installed binary, more current and more precise than the public docs page, which appears to lag the CLI) explicitly enumerates what it skips: hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, CLAUDE.md auto-discovery — and states auth is strictly `ANTHROPIC_API_KEY`/`apiKeyHelper`, confirming Phase 1's live finding rather than merely repeating it.

The provisioning mechanic for FAIR-02 has a much better answer than "install the plugin into the isolated `~/.claude/plugins/`": `claude`'s `--plugin-dir <path>` flag loads a plugin **from any directory or `.zip`, for that single session only** — no marketplace registration, no persistent install, no touching the isolated `$HOME`'s plugin cache at all. This repo's own `.claude-plugin/marketplace.json` shows the exact shape a provisioning recipe needs to pin: `cairn` is a local path (`./cairn`) inside this very repo, while `gsd` is sourced from an external GitHub repo (currently `jnuyens/gsd-plugin`, which `gh repo view` resolves to `buildomator/buildomator`, MIT-licensed, 83 stars, actively pushed) and, critically, **ships its own MCP server** (`node ${CLAUDE_PLUGIN_ROOT}/mcp/server.cjs`) with vendored `node_modules` — meaning a GSD baseline's provisioning recipe is not just "point `--plugin-dir` at a checkout," it must be a **pre-built** checkout (`npm install` already run) or the first benchmarked run silently absorbs a one-time `npm install` cost into its measured numbers (a direct instance of Pitfall 9 in `.planning/research/PITFALLS.md`). `cairn`'s own `plugin.json` declares a dependency on a second MCP-backed plugin, `context-mode`, from a separate marketplace — this must be a deliberate, documented choice about what "the cairn arm" means for this benchmark, not an accident of how `claude plugin install` would resolve dependencies (see Open Questions).

**Primary recommendation:** Extend `bench-run.py` with a `--baseline <baseline.json>` flag (respecting ARCHITECTURE.md's existing runner/baseline separation) that (1) builds a fresh disposable `HOME` per run, (2) builds a minimal explicit `env` dict for the `claude` invocation only, (3) resolves the baseline's `provisioning.plugin_dirs` into `--plugin-dir` flags pointing at pre-staged, pinned, pre-built plugin source copies, and (4) is driven by a small seeded-shuffle orchestration loop (new script or `bench-run.py --baselines a,b,c --seed N`) that records `seed` and the execution position into every JSONL row. Every mechanic is provable at $0 via an enriched `CAIRN_BENCH_CLAUDE_BIN` stub that echoes its own `$HOME`/env markers into the canned JSON payload, which `bench-run.py` already passes through untouched (proven in Phase 1).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `$HOME` override + env scrubbing per run | Runner (`bench-run.py`, local process) | — | This is a subprocess-launch concern local to the harness process; no client/server split exists in this domain |
| Baseline manifest definition (model, flags, provisioning recipe) | Task/Baseline definition (`benchmarks/baselines/<name>.json`, static config) | Runner (consumes it) | Config is data, read by the runner — matches ARCHITECTURE.md's existing Task/Baseline vs Runner split |
| Plugin provisioning (materializing pinned GSD/cairn source into a stageable dir) | Runner, pre-flight staging step | Baseline definition (declares *what* to fetch) | The runner performs the fetch/copy/build side effect; the manifest only declares intent — same "data vs execution" split as the rest of this table |
| `claude` subprocess invocation (the arm under test) | Runner | External: Anthropic API via the `claude` CLI | Unchanged from Phase 1 — this phase only changes the `env`/flags passed into the existing invocation point |
| `verify.sh` invocation (the objective oracle) | Runner | — | Unchanged from Phase 1; deliberately NOT run under the scoped/isolated env — it inspects the resulting workdir, it is not part of the compared arm |
| Execution-order randomization + seed recording | Orchestration layer (new thin loop, either `bench-run.py --baselines` or a sibling script) | Runner (executes each ordered run) | Ordering is a scheduling concern above a single run; keeping it out of the single-run function preserves `bench-run.py`'s existing one-row-per-invocation contract |
| Isolation proof (stub-asserts-environment) | Test layer (`tests/*.bats` + stub) | — | Black-box: bats never inspects runner internals, only the JSON row the stub was allowed to observe about its own launch environment |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `subprocess` (stdlib) | 3.12.1 (installed) | Launches `claude` with an explicit, minimal `env=` dict, replacing (not merging with) the parent process environment | `subprocess.run(..., env={...})` fully replaces `os.environ` for the child when `env` is not `None` — this is the entire mechanism needed for isolation; no third-party sandboxing library required |
| Python `random.Random(seed)` (stdlib) | 3.12.1 | Seeded, reproducible shuffle of the (baseline × rep) execution order | Instance-scoped RNG (not the shared `random` module global state) — deterministic given the same seed and CPython version, and does not collide with anything else in the process using `random.*` |
| `claude` CLI | 2.1.220 (installed; pin the exact version in `manifest.json` per run) | The arm under test — `-p --output-format json` | Already the harness's only integration point since Phase 1; this phase only changes which flags/env reach it |
| `claude --plugin-dir` | Same CLI version | Session-scoped plugin loading with zero persistent install | `[VERIFIED: local --help output]` — "Load a plugin from a directory or .zip for this session only" — exactly the "explicit, pinnable, scriptable" provisioning FAIR-02 requires |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `git` (already a repo dependency) | 2.42.1 (installed) | Vendoring a pinned tag/commit of the GSD plugin source (`jnuyens/gsd-plugin` → resolves to `buildomator/buildomator`) into a staged, pre-built copy | Baseline provisioning for `gsd-only`/`cairn`; do this as a one-time pre-benchmark staging step, never inside a measured run |
| `node` (already on the operator's PATH; v24.13.1 observed) | Whatever the third party has | Runs GSD's own bundled MCP server (`mcp/server.cjs`) when a GSD/cairn `--plugin-dir` session starts it | Required only for `gsd-only`/`cairn` baselines; vanilla needs nothing beyond `claude` itself |
| `jq` | 1.8.1 (installed) | Bats assertions against JSONL rows (already the pattern in `tests/bench-run.bats`) | Test layer only |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `subprocess.run(env={...})` explicit dict | Shell-level `env -i HOME=... PATH=... claude ...` wrapper | Both work (verified live with `env -i` during this research); the Python dict avoids a second process layer and keeps the isolation logic in one testable place (`bench-run.py`), consistent with the existing "logic testable via stub, not shell scripting" house style |
| `--plugin-dir` pointing at a pre-staged pinned copy | `claude plugin install <name>@<marketplace>` inside the isolated `HOME` before each run | `plugin install` requires network + marketplace registration + writes into the isolated `$HOME`'s `~/.claude/plugins/`, adding install latency/cost that must then be excluded from measured numbers (Pitfall 9) and reintroducing exactly the kind of persistent, hard-to-audit state the isolation is meant to eliminate; `--plugin-dir` is a strictly better fit for "explicit, pinnable, scriptable" |
| GSD provisioned from a fresh `git clone` + `npm install` per baseline manifest, pinned to a tag | Reusing the operator's already-installed `~/.claude/plugins/cache/cairngo/gsd/4.3.1/` copy directly | Reusing the operator's cache is NOT reproducible by a third party (violates REPT-04/Pitfall 10's "one-command reproduction"); it is fine as a *fast local dev loop* shortcut but the manifest/provisioning recipe must describe the git-pinned fetch as the source of truth |

**Installation:** No new third-party packages. Everything above is either already installed (git, node, jq, claude) or Python stdlib (`subprocess`, `random`, `json`, `tempfile` — all already imported in `bench-run.py`).

**Version verification:** `claude --version` → `2.1.220` (installed, verified live 2026-07-25); `python3 --version` → `3.12.1`; `git --version` → `2.42.1`; `bats --version` → `1.14.0`; `node --version` → `v24.13.1`; `jq --version` → `1.8.1`. All confirmed via direct shell invocation during this research session, not assumed from training data.

## Package Legitimacy Audit

This phase installs **no packages from a language package registry** (no `npm install`, `pip install`, or `cargo add` in `benchmarks/scripts/` or its tests — Python stdlib only, per the repo's existing zero-dependency house style). The `slopcheck`/registry-verification protocol therefore does not apply in its standard form. The one external-code dependency this phase introduces is a **git-sourced plugin checkout** (GSD, for the `gsd-only`/`cairn` provisioning recipes), which is a different trust surface (a GitHub repo, not a registry package) and is audited below instead.

| Dependency | Source type | Age / activity | Stars | License | Provenance | Disposition |
|------------|-------------|-----------------|-------|---------|------------|-------------|
| GSD plugin (`jnuyens/gsd-plugin`, currently resolving to `buildomator/buildomator`) | git checkout, pinned to a tag (not npm/pip) | Actively pushed (`pushedAt: 2026-07-25T10:30:58Z`, observed live) | 83 (`gh repo view`, observed live) | MIT (observed live) | Already declared as cairn's own production dependency in this repo's `.claude-plugin/marketplace.json` (line 41-43) and already installed/running in the operator's own Claude Code environment (`~/.claude/plugins/cache/cairngo/gsd/4.3.1/`) — this is not a new, unvetted dependency introduced by the benchmark; it is the same dependency CairnGo already ships to end users | Approved — `[VERIFIED: gh repo view, live 2026-07-25]`. **Note:** the repo appears to have been renamed/transferred from `jnuyens/gsd-plugin` to `buildomator/buildomator` at some point before this research date; the baseline manifest must record whichever exact org/repo + tag/commit SHA actually resolves at fetch time, since a moved repo is itself a reproducibility risk worth a one-line note in `manifest.json`. |
| `context-mode` plugin (declared dependency of `cairn`, separate marketplace) | git/plugin-marketplace, not evaluated in this research pass | — | — | — | — | **Not audited this phase** — flagged in Open Questions as a scope decision (include it in the "cairn" arm's provisioning or not) that the plan must resolve before this table can be completed for it |

**Packages removed due to slopcheck `[SLOP]` verdict:** none (no registry packages in scope).
**Packages flagged as suspicious `[SUS]`:** none, but see the `context-mode` scope question above — it is not a legitimacy concern, it is a fairness/methodology scope decision.

## Architecture Patterns

### System Architecture Diagram

```
                    benchmarks/baselines/<name>.json
                    (model, claude_flags, provisioning.plugin_dirs[])
                              │
                              │ read by
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│  bench-run.py  (extended)                                         │
│                                                                    │
│  1. mktemp fresh HOME_dir  ──────────────────┐                    │
│  2. for each provisioning.plugin_dirs entry:  │                    │
│       resolve pinned source → staged, pre-    │  isolation         │
│       built local path (git-pinned checkout   │  boundary          │
│       for gsd; in-repo path for cairn)        │                    │
│  3. build env = {HOME: HOME_dir,              │                    │
│                   PATH: inherited (unscoped), │                    │
│                   ANTHROPIC_API_KEY: inherited-if-present}         │
│  4. cmd = [claude_bin, -p, prompt,                                │
│            --output-format json, --model <pinned>,                │
│            --bare, --max-turns N, --no-session-persistence,       │
│            --permission-mode acceptEdits,                         │
│            --plugin-dir <staged gsd>, --plugin-dir <staged cairn>]│
│  5. subprocess.run(cmd, cwd=task_workdir, env=env, ...)  ─────────┼──▶ claude CLI
│  6. verify.sh <task_workdir>   (full inherited env — not scoped)  │       │
│  7. row = {..., seed, run_order_index, baseline_id, verify_passed}│       │ Anthropic API
│  8. append JSONL                                                  │       ▼
└───────────────────────────────────────────────────────────────────┘  (auth: ANTHROPIC_API_KEY
                              ▲                                          only — --bare never
                              │ ordered by                               reads OAuth/keychain)
┌───────────────────────────────────────────────────────────────────┐
│  Interleaving loop (new, thin)                                    │
│  order = list(product(baselines, range(reps)))                    │
│  random.Random(seed).shuffle(order)                                │
│  for (baseline, rep) in order: bench-run.py --baseline ... --rep ..│
└───────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
benchmarks/
├── baselines/
│   ├── vanilla.json          # provisioning.plugin_dirs: []
│   ├── gsd-only.json         # provisioning.plugin_dirs: [{plugin: gsd, source: {type: git, ...}}]
│   └── cairn.json            # provisioning.plugin_dirs: [gsd, cairn, (context-mode?) — see Open Questions]
├── plugins/                  # NEW — staged, pre-built, pinned plugin source (gitignored; fetched by a
│   │                          #        pre-flight staging step, never fetched mid-benchmark-run)
│   ├── gsd/<pinned-ref>/     # git checkout + npm install already done, matching plugin.json's mcpServers
│   └── (cairn resolves to the in-repo ./cairn path directly — no staging needed, it's already local)
└── scripts/
    ├── bench-run.py           # extended: --baseline <manifest>, isolated env=, --plugin-dir resolution
    └── bench-matrix.py        # NEW (or a mode of bench-run.py) — seeded shuffle + per-row seed/order fields
```

### Pattern 1: Minimal explicit `env` dict replaces, not merges

**What:** `subprocess.run(cmd, cwd=workdir, env={"HOME": fresh_home, "PATH": os.environ.get("PATH", ""), **({"ANTHROPIC_API_KEY": key} if key else {})}, ...)`. Passing any `env=` value to `subprocess.run` makes the child's environment **exactly** that dict — nothing from `os.environ` is merged in automatically.
**When to use:** Only for the `claude` invocation (the arm under test). The `verify.sh` subprocess call keeps the default (`env=None`, full inherited environment) since it is the oracle, not the measured subject, and may legitimately need `PATH`-discoverable tools like `pytest`/`bats` beyond what's in the minimal set.
**Why PATH is preserved, not scrubbed:** GSD's MCP server is a `node` subprocess; cairn's scripts may shell out to `python3`/`bd`; a third party's machine may have any of these on a completely different `PATH` (nvm-managed node, homebrew, asdf, etc.). Scrubbing `PATH` down to a hardcoded minimal set (e.g. `/usr/bin:/bin`) would make the harness fail to reproduce on machines where these tools live elsewhere — a direct hit to REPT-04's "reproduction in 1 command." `PATH` does not carry CLAUDE.md/hooks/MCP config, so preserving it does not reintroduce home-field advantage.

**Example:**
```python
import os

def isolated_claude_env(fresh_home: str) -> dict:
    env = {"HOME": fresh_home, "PATH": os.environ.get("PATH", "")}
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    return env

proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                       timeout=task["timeout_s"], env=isolated_claude_env(fresh_home))
```

### Pattern 2: `--plugin-dir` for session-scoped, no-install provisioning

**What:** Point one `--plugin-dir` flag at each pinned, pre-staged plugin source directory. `[VERIFIED: local --help output, claude 2.1.220]`: *"Load a plugin from a directory or .zip for this session only (repeatable: --plugin-dir A --plugin-dir B.zip)"*. No marketplace, no persistent install into the isolated `$HOME`.
**When to use:** Every `gsd-only`/`cairn` run. Never for `vanilla` (empty `provisioning.plugin_dirs`, i.e. no `--plugin-dir` flags at all).
**Trade-offs:** The plugin source must be *pre-built* before it's pointed to — GSD's `mcp/server.cjs` needs its `node_modules` already installed, or the first invocation eats an `npm install` inside the measured wall-clock (Pitfall 4 below). Staging is therefore a one-time, out-of-band step (`git clone --branch <pinned-tag> ...  && npm install`), not something `bench-run.py` does per-run.

**Example:**
```bash
claude --bare -p "$(cat prompt.md)" \
  --output-format json --model claude-haiku-4-5-20251001 \
  --max-turns 8 --no-session-persistence --permission-mode acceptEdits \
  --plugin-dir benchmarks/plugins/gsd/v4.3.1 \
  --plugin-dir cairn
```

### Pattern 3: Seeded interleaving with a per-row provenance trail

**What:** Build the full `(baseline, repetition)` cross-product as a list, shuffle it once with an instance-scoped `random.Random(seed)` (never the shared `random` module — avoids interfering with anything else using global random state in the same process), execute in that shuffled order, and stamp every JSONL row with `seed` and its `run_order_index` (0-based position in the shuffled sequence).
**When to use:** Any time more than one baseline is being run in the same session/batch — directly satisfies FAIR-03 and closes PITFALLS.md's Pitfall 7 (cache-order bias): interleaved execution means no single baseline systematically benefits from cache-read discounts a same-baseline predecessor just paid for.
**Trade-offs:** None significant — `random.Random(seed).shuffle()` is deterministic for a fixed seed and CPython minor version (Python's own docs make no cross-version determinism guarantee, so the seed alone does not guarantee byte-identical order across Python upgrades; record the `sys.version` alongside the seed in `manifest.json` if that ever needs auditing, though for THIS phase — Phase 2 doesn't yet add real repetition N>1, see CONTEXT.md's Deferred Ideas — a single ordering per invocation batch is enough to prove the mechanism).

**Example:**
```python
import random
from itertools import product

def build_execution_order(baselines: list[str], reps: int, seed: int) -> list[tuple[str, int]]:
    order = list(product(baselines, range(reps)))
    random.Random(seed).shuffle(order)
    return order

for idx, (baseline, rep) in enumerate(build_execution_order(["vanilla", "gsd-only", "cairn"], reps=1, seed=42)):
    row_extra = {"seed": 42, "run_order_index": idx, "baseline_id": baseline, "repetition": rep}
    # ... invoke bench-run.py's per-run logic, merge row_extra into the JSONL row ...
```

### Pattern 4: Stub-asserts-its-environment (isolation proven black-box, $0)

**What:** The `CAIRN_BENCH_CLAUDE_BIN` stub — the exact seam already exercised in `tests/bench-run.bats` — prints its OWN observed `$HOME` and a deliberately-planted "leak marker" env var into the canned JSON payload it emits. Because `bench-run.py` already passes every payload field through untouched (proven in Phase 1: `terminal_reason`, `modelUsage`, etc. all survive verbatim), these `stub_observed_*` keys land directly in the output JSONL row, where bats can assert on them with `jq`/`assert_json_eq` exactly like any other field.
**When to use:** Every bats test that needs to prove the harness computed and passed the *correct* isolated environment to the `claude` subprocess — this is how FAIR-01 is verified without spending API money.
**Trade-offs:** The stub only proves what environment the harness *handed to the subprocess it launched* — it cannot prove what the real `claude` binary does internally with that environment (e.g., whether it genuinely refrains from touching `~/.claude` on the operator's real disk). That gap is closed by the live empirical check already performed in this research session (see Common Pitfalls 1) and by the optional single live smoke run CONTEXT.md already sanctions.

**Example:**
```bash
# tests/helpers.bash addition (or bench-run.bats-local helper)
make_env_asserting_claude_stub() {
  STUB="$BATS_TEST_TMPDIR/claude-env-stub"
  cat > "$STUB" <<'EOF'
#!/usr/bin/env bash
# Prints its OWN $HOME and a leak-marker var into the canned payload so bats
# can assert on the environment bench-run.py actually constructed.
python3 -c "
import json, os
print(json.dumps({
  'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 1,
  'total_cost_usd': 0.0, 'usage': {'input_tokens': 0, 'output_tokens': 0,
    'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0},
  'session_id': 'stub-env-check',
  'stub_observed_home': os.environ.get('HOME', ''),
  'stub_observed_leak_marker': os.environ.get('OPERATOR_ONLY_LEAK_MARKER', ''),
  'stub_observed_api_key_present': bool(os.environ.get('ANTHROPIC_API_KEY')),
}))
"
EOF
  chmod +x "$STUB"
}

@test "bench-run.py builds a scoped HOME and scrubs unrelated operator env vars" {
  make_env_asserting_claude_stub
  export OPERATOR_ONLY_LEAK_MARKER="this-must-not-reach-the-claude-subprocess"
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-run.py" \
      --task "$BENCH_TASKS_DIR/smoke-convert" --baseline "$BENCH_BASELINES_DIR/vanilla.json" \
      --out "$BATS_TEST_TMPDIR/raw.jsonl"
  [ "$status" -eq 0 ]
  row="$(cat "$BATS_TEST_TMPDIR/raw.jsonl")"
  # The stub's own $HOME must NOT equal the bats test's real $HOME.
  observed_home="$(echo "$row" | jq -r '.stub_observed_home')"
  [ "$observed_home" != "$HOME" ]
  # The planted leak marker must have been scrubbed, not inherited.
  assert_json_eq "$row" '.stub_observed_leak_marker' ''
}
```

### Anti-Patterns to Avoid

- **Passing `env=None` (the current Phase 1 default) to the `claude` subprocess call:** this is the literal bug this phase exists to fix — it is exactly how Phase 1's 45-62k-token home-field overhead happened. Any refactor of `bench-run.py` that touches this call site must add an explicit `env=` argument, never leave it implicit.
- **Provisioning by running `claude plugin install` inside the isolated `HOME` at benchmark time:** persistent, network-dependent, writes state into the very `HOME` that's supposed to be disposable, and its install latency/cost would need to be excluded from measured numbers after the fact. Use `--plugin-dir` at pre-staged, pre-built paths instead.
- **Letting the `gsd-only`/`cairn` provisioning step run `npm install` lazily on first use inside a measured run:** silently inflates that arm's wall-clock/turn count for reasons that have nothing to do with the model's actual task-solving efficiency (Pitfall 9, `.planning/research/PITFALLS.md`). Stage and pre-build before any benchmarked invocation.
- **Scrubbing `PATH` down to a minimal hardcoded set:** breaks third-party reproducibility (a different machine's `node`/`git`/`bd` may live anywhere) without buying any additional fairness — `PATH` does not carry configuration/context, only tool discoverability.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scoping a subprocess's visible config/credentials | A custom sandboxing wrapper, a Docker container, or a shell `env -i` wrapper script | `subprocess.run(..., env={...})` with an explicit minimal dict | Verified live during this research: the explicit-dict approach achieves the same result as `env -i HOME=... claude ...` with zero extra process layers, and keeps the isolation logic testable in the same Python module the rest of the harness already lives in |
| Loading a specific plugin version into a session | A custom plugin-loader shim, manual `~/.claude/plugins/` file copying + `installed_plugins.json` editing | `claude --plugin-dir <path>` | This is a first-class, documented CLI flag purpose-built for exactly this ("for this session only") — hand-rolling install-file editing would be fragile against any future change to the plugins cache's internal file format |
| Reproducible shuffled ordering | A custom Fisher-Yates implementation, or numpy's RNG | `random.Random(seed).shuffle(list)` | stdlib, zero-dependency (matches the repo's house style), well-understood determinism properties within a fixed Python version |

**Key insight:** every mechanic this phase needs (env isolation, plugin loading, reproducible shuffling) already has a first-class stdlib or CLI-native answer once you go looking for it — the risk in this phase is not "what do we build," it's "did we correctly discover the native mechanism instead of hand-rolling around a gap that doesn't actually exist" (as this research found for both `env=` and `--plugin-dir`).

## Common Pitfalls

### Pitfall 1: Trusting docs over the installed binary's own `--help`

**What goes wrong:** The publicly fetched `code.claude.com/docs/en/cli-reference` page's description of `--bare` ("skip auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and CLAUDE.md") is measurably staler/thinner than what `claude --help` reports live from the installed v2.1.220 binary ("skip hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, and CLAUDE.md auto-discovery... Anthropic auth is strictly ANTHROPIC_API_KEY or apiKeyHelper via --settings"). A plan built purely from the fetched docs page would under-specify what `--bare` actually does (e.g., miss that keychain reads are explicitly skipped, or that skills still resolve via `/skill-name` even under `--bare`).
**Why it happens:** Docs pages lag CLI releases; the installed binary is ground truth for the exact version being benchmarked.
**How to avoid:** Always cross-check flag semantics against `claude --help`/`claude <subcommand> --help` on the machine that will actually run the benchmark, not just the public docs page. This research did so and used the live output as the higher-confidence source where the two disagreed.
**Warning signs:** A plan step that cites CLI behavior with only a docs-page URL and no confirmation against the installed version's own `--help`.

### Pitfall 2: Assuming a fresh `HOME` alone triggers interactive onboarding/telemetry prompts that would hang a headless run

**What goes wrong:** It's easy to assume a genuinely first-run `$HOME` (no `.claude.json`, no `.claude/`) will surface a telemetry-opt-in dialog, an onboarding wizard, or a trust prompt that blocks a non-interactive script forever.
**Why it happens:** That IS the interactive-mode behavior; it's a reasonable but wrong extrapolation to non-interactive mode.
**How to avoid — empirically verified live in this research session:** ran `claude --bare -p "..." --output-format json` with `HOME` pointed at a genuinely empty, never-before-used directory and an intentionally invalid `ANTHROPIC_API_KEY` (to force a $0, fast, deterministic failure per Phase 1's own finding that unauthenticated calls cost nothing). Result: clean structured JSON on stdout in ~330ms, `api_error_status: 401`, `terminal_reason: "api_error"`, `total_cost_usd: 0`. No hang, no interactive prompt, no stderr noise. The CLI's own `-p`/`--print` help text explains why: *"the workspace trust dialog is skipped when Claude is run in non-interactive mode (via -p, or when stdout is not a TTY)"* — this is unconditional on non-interactivity, not specifically gated by `--bare`. Confirmed the fresh `HOME` only gained: an empty `.claude/sessions/` dir (proving `--no-session-persistence` genuinely wrote nothing there), a `.claude/backups/` dir with one snapshot of `.claude.json`, and a `.claude.json` feature-flag cache (`cachedGrowthBookFeatures`, `firstStartTime`) — all harmless, all discarded when the disposable `HOME` is deleted.
**Warning signs:** A plan step that budgets extra timeout/retry logic "in case of an onboarding prompt" — unnecessary based on this live evidence; do not over-engineer around a risk that empirically does not exist for this invocation shape.

### Pitfall 3: `--plugin-dir` session-scoped loading may not auto-resolve declared plugin dependencies

**What goes wrong:** `cairn`'s own `plugin.json` declares `"dependencies": ["gsd", {"name": "context-mode", "marketplace": "context-mode"}]`. That dependency resolution is a `claude plugin install`-time, marketplace-aware behavior. It is NOT verified in this research whether a `--bare --plugin-dir ./cairn` session (no marketplace context at all) automatically also loads `gsd`'s and `context-mode`'s skills/commands/MCP servers, or whether it loads ONLY what's literally at the given path.
**Why it happens:** `--plugin-dir`'s documented purpose is "load a plugin from a directory for this session" — dependency resolution across marketplaces is a different, install-time concept that may simply not apply outside of `claude plugin install`.
**How to avoid:** Treat this as unverified and design the baseline manifest schema to be **explicit rather than relying on auto-resolution** — the `cairn` baseline's `provisioning.plugin_dirs` list should enumerate every plugin dir needed (gsd's staged copy, cairn's in-repo path, and a deliberate decision on context-mode — see Open Questions) rather than assuming pointing `--plugin-dir` at `cairn/` alone pulls in `gsd`. This is the safe default regardless of how the untested behavior turns out: if dependencies ARE auto-resolved, passing them explicitly too is harmless (idempotent); if they are NOT auto-resolved, explicit enumeration is required for the cairn arm to function at all.
**Warning signs:** A cairn baseline run that behaves identically to vanilla (no `/gsd:*` or `/cairn:*` command showing any effect) would be the live symptom if this assumption is wrong — worth a quick manual smoke check (interactive, not part of the $0 stub suite) before committing to a provisioning recipe.

### Pitfall 4: GSD's plugin ships its own MCP server with vendored `node_modules` — first use must not `npm install` lazily

**What goes wrong:** `~/.claude/plugins/cache/cairngo/gsd/4.3.1/.claude-plugin/plugin.json` declares `"mcpServers": {"gsd": {"type": "stdio", "command": "node", "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/server.cjs"]}}`, and the cached copy carries a 2.7MB `node_modules/` directory. If the benchmark's provisioning step is "git clone the pinned tag" without also running `npm install` before the first measured invocation, the very first `gsd-only`/`cairn` run either fails outright (missing deps) or — if some install-on-demand path exists — silently absorbs install latency into its measured wall-clock/cost, corrupting the comparison (a direct instance of PITFALLS.md Pitfall 9).
**Why it happens:** It's easy to think of "provisioning a plugin" as "get the source code" and forget that a plugin with its own MCP server is really "get the source code AND build it."
**How to avoid:** The provisioning/staging step (out-of-band, before any benchmarked run) must be: `git clone --branch <pinned-tag> ... && (cd staged-copy && npm install)`. Verify success by confirming `node_modules/` exists and `node mcp/server.cjs --help` (or equivalent) doesn't error, BEFORE pointing any `bench-run.py --baseline gsd-only` invocation at it.
**Warning signs:** A `gsd-only`/`cairn` row with anomalously high `wall_clock_ms` or `num_turns` relative to `vanilla` on the identical task/prompt, especially on the very first run of a freshly-staged plugin copy.

### Pitfall 5: `verify.sh` must NOT run under the same scoped/minimal `env` as the `claude` invocation

**What goes wrong:** It's tempting, for consistency, to pass the same minimal `env={"HOME": ..., "PATH": ...}` dict to the `verify.sh` subprocess call too. `verify.sh` may shell out to `pytest`/`bats`/other tools that expect a richer environment (locale vars, `TMPDIR`, `VIRTUAL_ENV`, etc.) that were never in scope for the isolation guarantee (isolation is about the CLAUDE ARM'S config/context, not about the objective pass/fail oracle).
**Why it happens:** "Isolate everything" feels safer than "isolate exactly the one subprocess that's the actual arm under test."
**How to avoid:** Keep `verify.sh`'s `subprocess.run` call exactly as Phase 1 left it — no `env=` argument, full inherited environment. Only the `claude` invocation gets the new minimal `env=` dict.
**Warning signs:** `verify.sh` runs (which shell out to real test frameworks) start failing in ways unrelated to the fixture's actual solved/unsolved state, only inside the benchmark harness and not when run manually.

## Code Examples

### Baseline manifest schema (three concrete files)

```json
// benchmarks/baselines/vanilla.json
{
  "name": "vanilla",
  "description": "Stock Claude Code, no plugins, no ambient config.",
  "model": "claude-haiku-4-5-20251001",
  "claude_flags": {
    "bare": true,
    "max_turns": 8,
    "no_session_persistence": true,
    "permission_mode": "acceptEdits"
  },
  "provisioning": {
    "plugin_dirs": []
  }
}
```

```json
// benchmarks/baselines/gsd-only.json
{
  "name": "gsd-only",
  "description": "Vanilla + GSD plugin only (isolates GSD's own contribution before cairn is layered on).",
  "model": "claude-haiku-4-5-20251001",
  "claude_flags": {
    "bare": true,
    "max_turns": 8,
    "no_session_persistence": true,
    "permission_mode": "acceptEdits"
  },
  "provisioning": {
    "plugin_dirs": [
      {
        "plugin": "gsd",
        "source": { "type": "git", "repo": "buildomator/buildomator", "ref": "v4.3.1" },
        "staged_path": "benchmarks/plugins/gsd/v4.3.1",
        "build": ["npm install"]
      }
    ]
  }
}
```

```json
// benchmarks/baselines/cairn.json
{
  "name": "cairn",
  "description": "GSD + cairn's own commands/skills/hooks. context-mode inclusion is an explicit open decision — see 02-RESEARCH.md Open Questions.",
  "model": "claude-haiku-4-5-20251001",
  "claude_flags": {
    "bare": true,
    "max_turns": 8,
    "no_session_persistence": true,
    "permission_mode": "acceptEdits"
  },
  "provisioning": {
    "plugin_dirs": [
      {
        "plugin": "gsd",
        "source": { "type": "git", "repo": "buildomator/buildomator", "ref": "v4.3.1" },
        "staged_path": "benchmarks/plugins/gsd/v4.3.1",
        "build": ["npm install"]
      },
      {
        "plugin": "cairn",
        "source": { "type": "local_path", "path": "cairn" },
        "staged_path": "cairn",
        "build": []
      }
    ]
  }
}
```

### `manifest.json` addition — recording seed + CLI version per run batch

```json
{
  "run_id": "2026-07-25_isolation-smoke",
  "claude_code_version": "2.1.220",
  "python_version": "3.12.1",
  "seed": 42,
  "baselines_run": ["vanilla", "gsd-only", "cairn"],
  "execution_order": ["cairn", "vanilla", "gsd-only"]
}
```

## State of the Art

| Before Phase 2 | After Phase 2 | Why it changed | Impact |
|-----------------|----------------|------------------|--------|
| `subprocess.run(cmd, cwd=workdir, ...)` — no `env=`, full operator environment inherited by the `claude` child process | Explicit minimal `env={"HOME": fresh_dir, "PATH": inherited, "ANTHROPIC_API_KEY": inherited-if-present}` | Phase 1 live-measured the cost of NOT doing this (45-62k cache-creation tokens of ambient overhead) | Every arm's cost/token numbers become attributable to the model+prompt+baseline, not the operator's personal `~/.claude/` |
| One implicit baseline (whatever `claude` on `PATH` resolves to, with the operator's real config) | Explicit `benchmarks/baselines/*.json` manifests, `--baseline` flag on `bench-run.py` | FAIR-02 | Vanilla/GSD-only/cairn become auditable, reproducible arms instead of one undocumented default |
| Sequential single-run invocation, no ordering concept | Seeded shuffle across (baseline × rep), seed + order recorded per row | FAIR-03 / PITFALLS.md Pitfall 7 | Removes prompt-cache warm-up bias from favoring whichever baseline happens to run consecutively |

**Deprecated/outdated:** Nothing in this phase deprecates prior Phase 1 work — it is a strict extension of `bench-run.py`'s existing single-run function, adding parameters (`env`, `--plugin-dir` list, `--baseline`) rather than replacing the core invoke-parse-verify-append flow.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `--plugin-dir` sessions do NOT auto-resolve a plugin's declared marketplace dependencies (e.g., pointing at `cairn/` alone does not also load `gsd`/`context-mode`) | Common Pitfalls 3, Standard Stack | If wrong (dependencies ARE auto-resolved), the recommended "enumerate every plugin dir explicitly" approach is still safe (redundant, not harmful) — low risk either way, but the *inverse* risk (assuming auto-resolution when it doesn't happen) would silently produce a cairn baseline that behaves like vanilla, a serious fairness bug |
| A2 | Whether to include `context-mode` (cairn's second declared dependency, a separate MCP-backed memory plugin) in the "cairn" baseline's provisioning recipe is an open methodology decision, not yet resolved by CONTEXT.md | Package Legitimacy Audit, Open Questions | If the plan silently includes or excludes it without a deliberate note, a reader could reasonably ask whether "the cairn arm" in the published benchmark matches what a real `claude plugin install cairn@cairngo` user actually gets — a credibility gap (PITFALLS.md Pitfall 10 category) |
| A3 | The GSD plugin's upstream source currently resolves as `jnuyens/gsd-plugin` → `buildomator/buildomator` (an apparent repo rename/transfer) — the exact org/repo to pin in the provisioning recipe should be re-confirmed at plan/build time, not assumed static from this research date | Standard Stack, Package Legitimacy Audit | A stale/wrong repo reference in a committed baseline manifest would break third-party reproduction (REPT-04) |
| A4 | `random.Random(seed).shuffle()`'s exact output sequence is not guaranteed stable across different CPython minor versions (no cross-version determinism guarantee documented in Python's own stdlib docs, not independently re-verified against docs.python.org in this session — inferred from general Python stdlib knowledge) | Architecture Patterns Pattern 3 | Low risk for Phase 2 itself (single ordering per batch, no cross-machine byte-identical requirement yet); becomes relevant if Phase 3's aggregation ever needs to reproduce Phase 2's exact historical ordering on a different Python version |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **Does `cairn`'s "arm" in this benchmark include `context-mode`?**
   - What we know: `cairn/.claude-plugin/plugin.json` declares `context-mode` as a hard dependency (`"dependencies": ["gsd", {"name": "context-mode", "marketplace": "context-mode"}]`), and a real end user running `claude plugin install cairn@cairngo` gets it automatically.
   - What's unclear: whether the benchmark should replicate that (arguing "this is genuinely what installing cairn gives you") or exclude it (arguing "we're isolating cairn's OWN workflow contribution, and context-mode is a separately-attributable, independently-benchmarkable tool").
   - Recommendation: this is a methodology decision for the plan/discuss-phase to make explicitly and document in the baseline manifest's `description` field either way — do not let it be decided implicitly by whichever `--plugin-dir` list happens to get typed first. Leaning toward: include it (matches what a real user experiences when they type `/cairn:init`), but flag the extra MCP-server surface area explicitly in `manifest.json` so a skeptical reader can see exactly what ran.

2. **Does `--plugin-dir ./cairn` (or any single-path invocation) auto-load `cairn`'s declared dependencies, or must every dependency be passed as its own `--plugin-dir`?**
   - What we know: `--plugin-dir`'s help text describes session-scoped loading "from a directory," with no mention of dependency resolution; `claude plugin install` (a different, marketplace-aware code path) is where `plugin.json`'s `dependencies` array is documented to matter.
   - What's unclear: unverified without a live session (this research deliberately avoided a real live `claude` session with actual plugin loading, since it would need to be interactive or spend a >$0 turn to observe tool/skill availability — the current API key situation, see Environment Availability, makes even a cheap check unavailable this session).
   - Recommendation: default to the safe assumption (A1 above — enumerate explicitly), and fold a live-plugin-loading check into the SAME optional single cheap live smoke run CONTEXT.md already sanctions for the auth path, if/when `ANTHROPIC_API_KEY` becomes available during Phase 2's execution.

3. **Exact current org/repo for the GSD plugin source (`jnuyens/gsd-plugin` vs `buildomator/buildomator`).**
   - What we know: `gh repo view jnuyens/gsd-plugin` resolves live to `buildomator/buildomator` (MIT, 83 stars, pushed 2026-07-25) — likely a rename/transfer; the operator's already-installed local cache (`~/.claude/plugins/cache/cairngo/gsd/4.3.1/`) matches this plugin (`author: Jasper Nuyens`, `homepage: buildomator.com`).
   - What's unclear: which identifier this repo's own `.claude-plugin/marketplace.json` should list going forward (it currently says `jnuyens/gsd-plugin`) — that's a cairn/marketplace-maintenance question possibly out of THIS phase's scope, but the Phase 2 baseline manifest's provisioning recipe must use whichever identifier actually resolves at staging time.
   - Recommendation: use `buildomator/buildomator` (the live-resolving identifier) in the new `benchmarks/baselines/*.json` provisioning recipes, and note the discrepancy with the existing `marketplace.json` as a one-line aside in the plan/summary rather than silently "fixing" `marketplace.json` itself (out of scope for this phase).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `claude` CLI | The arm under test, all baselines | ✓ | 2.1.220 | — |
| `python3` | `bench-run.py` and its extensions | ✓ | 3.12.1 | — |
| `git` | Vendoring/pinning the GSD plugin source | ✓ | 2.42.1 | — |
| `node` | GSD's own MCP server (`mcp/server.cjs`), required only for `gsd-only`/`cairn` baselines | ✓ | v24.13.1 | Vanilla baseline needs no fallback (no `node` dependency at all) |
| `bats` | Test suite (stub-based, $0) | ✓ | 1.14.0 | — |
| `jq` | Bats assertions on JSONL rows | ✓ | 1.8.1 | — |
| `ANTHROPIC_API_KEY` | The ONE optional live smoke run CONTEXT.md sanctions (isolated auth path + `--plugin-dir` loading proof) | ✗ (absent in this research session's shell) | — | Mechanism + stub-based bats proofs still deliver FAIR-01/02/03 in full; document the pending live check in the phase SUMMARY as "pending key," per CONTEXT.md's own explicit instruction — this is NOT a blocker |

**Missing dependencies with no fallback:** none — every dependency needed to BUILD and TEST the mechanism (stub-based) is present.

**Missing dependencies with fallback:** `ANTHROPIC_API_KEY` — the single optional live validation step CONTEXT.md already scopes as non-blocking if absent.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V5 Input Validation | yes | Baseline manifest JSON must be validated before use (model id is a non-empty full pinned string per Phase 1's existing `task.json` enforcement pattern; `provisioning.plugin_dirs[].source` fields are typed/allowlisted, not arbitrary shell strings); `cmd` is built as a Python list and passed to `subprocess.run` without `shell=True` — already the existing pattern in `bench-run.py`, must be preserved when adding `--plugin-dir` flags (never string-interpolate a path into a shell command) |
| V6 Stored Cryptography / secrets handling | yes | `ANTHROPIC_API_KEY` is read from the environment at invocation time only, passed through the explicit `env=` dict to the `claude` subprocess, and NEVER written to any file this repo commits — matches CONTEXT.md's explicit locked decision. The stub-asserts-environment bats trick (Pattern 4) must assert the key's *presence as a boolean*, never echo the literal key value into a committed test fixture or bats output |
| V7 Error Handling & Logging | yes | If a `claude` invocation fails auth (as demonstrated live in this research with an intentionally invalid key), the resulting JSONL row's `result`/`errors[]` fields may echo back diagnostic text from the API — verify no raw key material leaks into that text (not observed in this research's live test: the 401 response returned only `"Invalid API key · Fix external API key"`, no key echo) |
| V14 Configuration | yes | This entire phase IS a "secure/minimal configuration by default" exercise — explicit `env=` allowlisting (HOME, PATH, ANTHROPIC_API_KEY only) rather than environment-variable blocklisting is the ASVS-preferred allowlist-over-blocklist pattern |
| V4 Access Control | no | No auth/authz surface introduced by this phase beyond the existing `ANTHROPIC_API_KEY`-gated Anthropic API call |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Command injection via baseline manifest fields (e.g., a `model` or `plugin_dir` path string containing shell metacharacters) | Tampering | Build `cmd` as a Python list (never `shell=True`), validate manifest fields against expected types/patterns before use — already the harness's existing convention, must be extended (not weakened) when adding new manifest-driven flags |
| Secret leakage into committed test fixtures or JSONL rows | Information Disclosure | Stub tests assert on boolean presence of `ANTHROPIC_API_KEY`, never its value; never commit a JSONL row produced against a real (non-stub) invocation without first confirming it contains no raw secret material — Phase 1 already established this discipline for `total_cost_usd`/`usage` fields, extend it to any new fields this phase introduces |
| Untrusted plugin source execution (a `--plugin-dir` pointed at a compromised/malicious git ref) | Tampering / Elevation of Privilege | Pin exact tags/commit SHAs in the provisioning recipe (never a floating branch like `main`), and stage plugin sources from the same trust boundary this repo already relies on in production (`.claude-plugin/marketplace.json`'s existing GSD dependency) rather than an unvetted new source |

## Sources

### Primary (HIGH confidence — verified live against the installed binary/repo during this research session)

- `claude --help`, `claude plugin --help`, `claude plugin install --help`, `claude plugin marketplace --help`, `claude plugin validate --help` — installed v2.1.220, run live 2026-07-25
- Live test: `HOME=<fresh empty dir> claude --bare -p ... --output-format json` with an invalid `ANTHROPIC_API_KEY`, twice against the same fresh `HOME` and once against a brand-new `mktemp -d` `HOME` — proves no trust-dialog/onboarding block, `--no-session-persistence` writes nothing to `.claude/sessions/`, and the only filesystem writes are a harmless `.claude.json` feature-flag cache
- This repo's own `.claude-plugin/marketplace.json` and `cairn/.claude-plugin/plugin.json` — read directly, 2026-07-25
- `~/.claude/plugins/cache/cairngo/gsd/4.3.1/.claude-plugin/plugin.json` (the operator's already-installed GSD plugin copy) — read directly, confirms the `mcpServers` MCP-server declaration and vendored `node_modules`
- `gh repo view jnuyens/gsd-plugin` / `gh repo view buildomator/buildomator` — run live 2026-07-25, confirms MIT license, 83 stars, active push date
- This repo's `.planning/phases/01-verification-core-first-real-run/01-03-SUMMARY.md`, `benchmarks/README.md`, `benchmarks/scripts/bench-run.py`, `tests/bench-run.bats` — read directly, 2026-07-25
- `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md` (Phase 0/1 project research, itself HIGH-confidence-sourced against official Claude Code docs) — read directly, 2026-07-25

### Secondary (MEDIUM confidence — WebFetch of official docs pages, cross-checked against the live binary where they overlapped)

- [code.claude.com/docs/en/env-vars](https://code.claude.com/docs/en/env-vars) — fetched 2026-07-25; confirms no officially documented `CLAUDE_CONFIG_DIR` variable (matches community bug report below); documents `ANTHROPIC_API_KEY` precedence and settings-file `env` block mechanics
- [code.claude.com/docs/en/cli-reference](https://code.claude.com/docs/en/cli-reference) — fetched 2026-07-25; `--bare`/`--plugin-dir`/`--settings`/`--mcp-config` descriptions cross-checked against, and found slightly staler than, the locally installed binary's own `--help` (see Common Pitfalls 1)

### Tertiary (LOW confidence — community source, not independently re-verified)

- [github.com/anthropics/claude-code/issues/3833](https://github.com/anthropics/claude-code/issues/3833) — community bug report describing unclear/buggy `CLAUDE_CONFIG_DIR` behavior; corroborates the decision to rely on `$HOME` override (empirically proven in this research) rather than `CLAUDE_CONFIG_DIR` (undocumented, reportedly unreliable) as the isolation lever

## Metadata

**Confidence breakdown:**
- `$HOME`/env isolation mechanics: HIGH — live-verified against the installed binary with a real (though intentionally-failing) invocation, not just read from docs
- `--plugin-dir` provisioning mechanics: HIGH for the flag's own documented behavior (verified via local `--help`); MEDIUM for the unverified dependency-auto-resolution question (Open Question 2, Assumption A1)
- Baseline manifest schema / seeded interleaving design: MEDIUM-HIGH — a reasoned synthesis built on Phase 1's already-proven JSONL passthrough behavior and ARCHITECTURE.md's HIGH-confidence component split, not itself independently precedented in an external harness this research found
- GSD plugin's MCP-server/build prerequisite: HIGH — read directly from the plugin's own manifest and installed cache on disk

**Research date:** 2026-07-25
**Valid until:** 30 days (the `claude` CLI ships frequent releases per its own `install [target]` command supporting `stable`/`latest`/pinned versions; re-verify `--bare`/`--plugin-dir` semantics against `claude --help` if the pinned CLI version changes before Phase 2 executes)
