# Phase 1: Verification Core + First Real Run - Research

**Researched:** 2026-07-25
**Domain:** Objective task-verification contract (`verify.sh`) + a single live, schema-validating `claude -p --output-format json` invocation, inside an existing Python-stdlib/bash/bats plugin repo
**Confidence:** HIGH (CLI flags, JSON result schema, and house-style patterns all directly verified against official docs and the repo's own source in this session); MEDIUM on the exit-code↔`is_error` mapping (not in an official table, corroborated by multiple secondary sources) and on `--max-budget-usd` (present in CLI but not re-fetched from the primary reference page this session)

## Summary

This phase builds exactly two things and proves them work before anything else in the roadmap depends on them: an objective, agent-unwritable `verify.sh` contract per task fixture, and one real, live `claude -p --output-format json` call that validates the harness's schema assumptions against the actual CLI. Everything else — baselines, isolation, repetition, aggregation, charts — is explicitly out of scope and must not be built ahead of schedule (CONTEXT.md `<deferred>`).

The house style is already fully specified by the existing repo: every deterministic script is Python-stdlib-only with a thin bash wrapper of the same basename, a docstring documenting Usage/Behavior/Exit codes, a `die(msg, code)` helper, `EXIT_*` constants, and JSON I/O via stdlib `json`. Testability uses **CLI-contract bats tests** exclusively — no internal unit tests, no mocking of the script's own logic — with binary unavailability/behavior swapped via one of two seams already proven in this repo: an env-var override (`CAIRN_GBSYNC`-style, for a *recorder or canned-output stub*) or a minimal stub `$PATH` directory (for simulating *binary absence*). `bench-run.py` should resolve the `claude` binary through a new env-var seam, `CAIRN_BENCH_CLAUDE_BIN`, following the existing naming convention (`CAIRN_` prefix, per `CONVENTIONS.md`) rather than the bare `BENCH_CLAUDE_BIN` used only as an illustrative example in CONTEXT.md.

The `claude -p --output-format json` result schema is confirmed directly against current official docs (fetched live this session): a `result` message carries `type`, `subtype` (`success` | `error_max_turns` | `error_during_execution`), `duration_ms`, `duration_api_ms`, `is_error`, `num_turns`, `result` (string, success only), `session_id`, `total_cost_usd`, and a `usage` object (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`) — all confirmed present on **both success and error results** (the cost-tracking doc explicitly states "Both success and error result messages include `usage` and `total_cost_usd`"). The process exit code is not documented in an official table; treat "non-zero exit on any error subtype, 0 on success" as a reasonable but **unverified-by-primary-source** assumption and defensively parse the JSON on stdout regardless of exit code, falling back to a synthetic error row if `stdout` is not valid JSON.

**Primary recommendation:** Build the fixture task's `verify.sh` first, prove it green/red against a hand-built solved/unsolved pair with zero agent involvement (bats-only), then build `bench-run.py` against the `CAIRN_BENCH_CLAUDE_BIN` stub seam (bats-tested, zero cost), and only then run it once for real with `--bare --model claude-haiku --max-turns 5 --permission-mode acceptEdits --no-session-persistence --output-format json` against the same fixture, from inside a disposable `mktemp -d` copy of the fixture — never against the live repo working tree.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**House style**
- python3 **stdlib-only** + thin bash wrapper, exactly like `cairn/scripts/` (shebang, docstring-contract with Usage/Behavior/Exit codes, `die()` helper, `--json` flag convention).
- Manifests/config are **JSON, not YAML** (stdlib has no YAML parser — deliberate deviation from SWE-bench's task.yaml).

**Verification (HARN-01)**
- Per-task `verify.sh`: exit code = pass/fail. Never LLM self-report. The agent under test must not be able to rewrite it (it lives outside the agent's working tree; staged in read-only or copied fresh per run).
- Task fixture = disposable repo tree + task prompt + `verify.sh`, bats-testable with zero API cost.

**Runner (HARN-02)**
- `claude -p --output-format json` is the primary measurement source: `total_cost_usd`, `usage.{input,output,cache_creation,cache_read}_tokens`, `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`, `session_id` (verified against official docs in STACK.md).
- One raw JSONL row per run appended to a results file; external wall-clock measured by the runner itself (python `time.time()`).
- Exactly **one real `claude -p` call** happens in this phase, at the end, to validate the schema live — smallest possible task, cost documented in the SUMMARY. Everything else runs against the stub.

**Testability (HARN-03)**
- `claude` binary reached through an env-var seam (e.g. `BENCH_CLAUDE_BIN`, mirroring the existing `CAIRN_GBSYNC`-style stub seams) — bats stubs it; CI never pays API.

**Layout**
- New top-level `benchmarks/` directory (tasks/, harness scripts follow house naming `bench-*.py` + `.sh` wrappers); tests in `tests/` as `bench-*.bats` reusing `tests/helpers.bash`.

### Claude's Discretion
- Exact `benchmarks/` subtree layout, JSONL field order, the content of the first fixture task, stub output shape, and how the single live validation run is triggered (flag vs separate script).

### Deferred Ideas (OUT OF SCOPE)
- Multi-baseline manifests, isolation (HOME override, worktrees) — Phase 2.
- Repetition/aggregation — Phase 3. Never build ahead of the current phase.

**Phase boundary (verbatim):** Prove the harness's two riskiest primitives before anything is built on top of them: (1) an objective, agent-unwritable pass/fail check per benchmark task (`verify.sh`, exit code is the verdict), and (2) one real `claude -p --output-format json` invocation validating the result-JSON schema assumptions. Deliverables map to HARN-01, HARN-02, HARN-03. bd issues: CairnGo-bur (HARN-01), CairnGo-9f5 (HARN-02), CairnGo-pgp (HARN-03).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARN-01 | Task fixture com critério objetivo de conclusão: `verify.sh` por tarefa (exit code = pass/fail), nunca auto-relato do agente; formato bats-testável sem custo de API | "verify.sh Design" pattern below (out-of-worktree invocation, solved/unsolved pair, SWE-bench FAIL_TO_PASS/PASS_TO_PASS analogue); Code Examples section gives a concrete minimal fixture |
| HARN-02 | Runner (`bench-run.py`) invoca `claude -p --output-format json` headless e grava por rodada o resultado bruto em JSONL: `total_cost_usd`, `usage` completo, `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`, wall-clock externo | "Verified JSON Result Schema" section (live-fetched, HIGH confidence); "Flags for the Single Live Validation Run" section; Code Examples give the exact subprocess + JSONL-row pattern |
| HARN-03 | Lógica determinística do harness testável em bats via stub do binário `claude` (seam por env-var, padrão do repo) — CI nunca paga API; runs reais são job separado e deliberado | "Stub Seam Mechanics" section (exact `CAIRN_GBSYNC` pattern read from `tests/hooks.bats`/`tests/helpers.bash`/`TESTING.md` this session); Code Examples give the exact stub script + bats test |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Task fixture + `verify.sh` | Filesystem / disposable fixture tree | — | Pure filesystem state + exit code; no network, no API |
| `bench-run.py` orchestration | CLI harness (Python subprocess layer) | — | Owns fixture staging, `claude` subprocess invocation, JSONL write |
| `claude -p` invocation | External process (Anthropic API via CLI) | — | Out-of-process boundary; harness treats it as an opaque subprocess with a JSON contract |
| Stub seam (`CAIRN_BENCH_CLAUDE_BIN`) | Test double / CLI harness | — | Same tier as the harness itself — an env-var-resolved executable, not a separate service |
| bats tests | Test harness (bash) | — | Black-box CLI-contract tests against the real `bench-run.sh`/`bench-run.py` |

This phase has no browser, server, or database tier — it is a single-process CLI harness invoking another CLI as a subprocess. The only "external service" is the Anthropic API, reached exclusively through the `claude` binary, never called directly.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `claude` CLI (`claude -p --output-format json`) | 2.1.220 confirmed installed locally this session (`claude --version`); pin whatever version is present when the live run happens and record it in the JSONL row / SUMMARY | The one real measurement source for HARN-02 | Anthropic's own documented headless interface — `[VERIFIED: code.claude.com/docs/en/headless, code.claude.com/docs/en/cli-reference, code.claude.com/docs/en/agent-sdk/cost-tracking, fetched live this session]` |
| Python 3 stdlib (`subprocess`, `json`, `time`, `tempfile`, `shutil`, `sys`, `os`) | 3.12.1 confirmed installed locally (`python3 --version`); repo policy is "any modern 3.x" | `bench-run.py` implementation | Matches repo's zero-dependency house style; no new packages needed for this phase — `[VERIFIED: python3 --version + existing CONVENTIONS.md constraint]` |
| bats-core | 1.14.0 confirmed installed locally (`bats --version`); CI installs latest via `npm install -g bats`, unpinned | `tests/bench-run.bats`, `tests/bench-verify.bats` (or equivalent) | Existing project test runner — no alternative considered, this is a hard house-style constraint, not a choice — `[VERIFIED: bats --version + TESTING.md]` |
| `jq` | 1.8.1 confirmed installed locally | Optional sanity-check extraction of `claude -p` JSON fields in bash wrappers or bats assertions | Already a repo test dependency (`assert_json_eq` in `tests/helpers.bash` uses it) — `[VERIFIED: jq --version + tests/helpers.bash]` |

**No new external packages are introduced by this phase.** Every tool above is either Python stdlib (nothing to install) or already an existing, verified project dependency (`bd`, `bats`, `jq`, `claude`). See "Package Legitimacy Audit" below for why the gate is not applicable here.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `git` (for `git init` in fixture tests, mirroring `make_tmp_repo`) | Whatever version CI/dev machine has | Optional — only if the fixture task's `verify.sh` needs to diff against a git baseline | Not needed for the "smallest possible" first fixture task (a plain file-content check needs no git at all); keep the first task git-free unless the task specifically needs a diff-based check |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `CAIRN_BENCH_CLAUDE_BIN` env-var seam | `--plugin-dir`/`PATH`-only stubbing (no env var) | Rejected: the repo's own `CONVENTIONS.md` states env-var seams are "preferred, used by hooks" specifically because they don't require mutating `$PATH` globally per test; PATH-replacement is reserved in this repo for simulating *binary absence* (see `cairn-map.bats:219-231`), a different test case (not applicable here since HARN-03 needs canned-output stubbing, not absence-simulation) |
| Invoking `verify.sh` with the worktree path as an argument (verify.sh stays outside the tree) | Copying a read-only (`chmod 444`) `verify.sh` into the worktree itself | The "outside the tree, path as argument" pattern is strictly safer — the agent never even sees the file to attempt tampering, vs. a `chmod 444` copy which is still visible/enumerable and depends on the agent's own tool permissions never including a chmod/rm. Use the copied-read-only variant only if a specific task's checker genuinely must run with the worktree as its cwd (e.g., relies on relative-path test discovery) |
| `--permission-mode acceptEdits` for the one live run | `--dangerously-skip-permissions` / `--permission-mode bypassPermissions` | STACK.md (project research, already committed) explicitly flags unsandboxed `--dangerously-skip-permissions` on a real machine as discouraged by Anthropic's own guidance (intended for a network-restricted devcontainer). Since Phase 1's live run happens on a developer machine, not a devcontainer, `acceptEdits` (auto-approves file writes/edits + common fs commands, still prompts for anything else) is the safer default for a task that only needs to write/edit files. Use `bypassPermissions` only inside an actual sandboxed container, which is out of scope for Phase 1 |

## Package Legitimacy Audit

**Not applicable this phase.** No new external packages (pip, npm, cargo, or otherwise) are introduced. Every tool used is either Python stdlib (ships with the interpreter) or an existing, already-vetted project dependency confirmed present in this environment:

| Tool | Registry/Source | Status this session | Disposition |
|------|------------------|----------------------|-------------|
| `claude` CLI | Anthropic (native binary, not a package registry) | `claude --version` → `2.1.220` confirmed installed | Pre-existing dependency, not newly introduced |
| `bats-core` | Already a project dependency (`CONTRIBUTING.md`, `tests/README.md`) | `bats --version` → `Bats 1.14.0` confirmed installed | Pre-existing, unpinned in CI (`npm install -g bats`), unchanged by this phase |
| `jq` | Already a project test dependency | `jq --version` → `jq-1.8.1` confirmed installed | Pre-existing, unchanged |
| Python 3 stdlib | Ships with `python3` | `python3 --version` → `3.12.1` confirmed installed | No install step; stdlib only |

No `pip install`, `npm install`, or `cargo add` commands are needed to complete HARN-01/02/03. If a future phase (2+) needs a new package, run the full Package Legitimacy Gate then — not here.

## Architecture Patterns

### System Architecture Diagram

```
benchmarks/tasks/<smoke-task-id>/
  task.json         (id, description, timeout_s, max_turns)
  prompt.md          (exact prompt text handed to claude -p)
  fixture/           (starting repo state, copied fresh per run)
  verify.sh          (lives HERE, never copied into the worktree)
        │
        │ read by
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ benchmarks/scripts/bench-run.py                                 │
│                                                                   │
│  1. workdir = mktemp -d                                          │
│  2. copy fixture/ contents into workdir                           │
│  3. claude_bin = os.environ.get("CAIRN_BENCH_CLAUDE_BIN")         │
│                   or shutil.which("claude")                      │
│  4. subprocess.run([claude_bin, "-p", prompt, --bare,             │
│       --output-format json, --max-turns N, --model M,             │
│       --permission-mode acceptEdits, --no-session-persistence],   │
│       cwd=workdir, capture_output=True, timeout=task.timeout_s)   │
│  5. parse stdout as JSON -> payload (defensive: catch JSONDecodeError)│
│  6. run_verify: subprocess.run(["bash", verify_sh_path, workdir]) │
│  7. append one JSONL row: task/rep/model/payload fields/verify_passed│
│  8. rmtree(workdir)                                               │
└──────────────────────────┬────────────────────────────────────────┘
                           │ one line per run
                           ▼
              benchmarks/results/<run-id>/raw/<task>.jsonl
                    (Phase 3 will aggregate this — not built yet)
```

Two invocation paths through the SAME script:
- **bats path (default in CI):** `CAIRN_BENCH_CLAUDE_BIN` set to a canned-output recorder stub → zero API cost, deterministic.
- **live path (manual, once, at the end of this phase):** `CAIRN_BENCH_CLAUDE_BIN` unset → resolves to the real `claude` on `$PATH` → the one real, costed, documented call.

### Recommended Project Structure

```
benchmarks/
├── README.md                    # how to run, cost of the one live smoke run, what verify.sh proves
├── tasks/
│   └── smoke-<slug>/            # the ONE fixture task built in this phase
│       ├── task.json            # {"id": "...", "timeout_s": 60, "max_turns": 5, "prompt_file": "prompt.md"}
│       ├── prompt.md            # exact prompt text, baseline-agnostic
│       ├── fixture/             # starting file tree, copied fresh into every workdir
│       └── verify.sh            # exit 0 = pass; never copied into the workdir
├── scripts/
│   ├── bench-run.py             # HARN-02: stage fixture, invoke claude -p, run verify.sh, append JSONL row
│   └── bench-run.sh             # thin wrapper, exec's the .py, same contract as cairn/scripts/*.sh
└── results/
    └── .gitkeep                 # or the one committed JSONL row from the live run (per CONTEXT specifics)

tests/
└── bench-run.bats               # stub-based CLI-contract tests, zero API cost
```

### Structure Rationale

- **`verify.sh` lives inside `tasks/<id>/`, never staged into the workdir.** `bench-run.py` invokes it as `bash "$TASK_DIR/verify.sh" "$WORKDIR"` — the checker receives the worktree path as an argument and inspects it from outside. This is the strongest form of "the agent under test must not be able to rewrite it" (CONTEXT.md, HARN-01): the file is never in the agent's visible filesystem at all, not merely read-only within it.
- **One task, one script, no `--baseline` flag yet.** CONTEXT.md defers "multi-baseline manifests, isolation" explicitly to Phase 2 (FAIR-01/02). `bench-run.py`'s CLI surface for this phase needs only `--task <dir>` and `--out <jsonl-path>`; do not add a `baselines/` directory, a `--baseline` flag, or `--bare`'s counterpart (loading a specific plugin set) — that machinery belongs to Phase 2's FAIR requirements, and building it now violates the phase's own "Never build ahead" constraint. If a `baseline_id` field is wanted in the JSONL row for future compatibility with the Phase 2/3 schema (see project ARCHITECTURE.md's row shape), hardcode it to a constant like `"dev"` rather than building a parameterization system around it.
- **`results/` starts effectively empty except the one live run's row.** CONTEXT.md's `<specifics>` section states the single live run's JSONL row "gets committed as the first real data point" — so `benchmarks/results/` should exist with exactly one committed row from the real invocation, not a `results/<run-id>/` directory tree (that structure, with `manifest.json`/`aggregated.json`/`REPORT.md`, is Phase 3+ scope per the project ARCHITECTURE.md build order).
- **New tests land in the existing flat `tests/` directory**, named `bench-run.bats` (mirrors the `<script-basename>.bats` convention in `CONVENTIONS.md`/`TESTING.md`), loading `tests/helpers.bash` for `make_tmp_repo`/`require_bd` if the fixture task happens to need a git repo (it doesn't have to for the smallest possible task).

### Pattern 1: `verify.sh` design — smallest possible, deterministic, unambiguous

**What:** A task fixture is judged solved/unsolved purely by `verify.sh`'s exit code, checked against the resulting worktree filesystem state — never the agent's own transcript or self-report.

**Concrete recipe for the smallest possible first task** (synthesizing SWE-bench's `FAIL_TO_PASS`/`PASS_TO_PASS` concept — `[CITED: swebench.com/SWE-bench/reference/harness, github.com/swe-bench/SWE-bench]` — and terminal-bench's "tests folder + oracle solution" pattern — `[CITED: harborframework.com/docs/tutorials/running-terminal-bench, github.com/harbor-framework/terminal-bench]` — down to what this repo can build with zero dependencies):

1. `fixture/` contains a small Python module with ONE missing/broken function and an accompanying test file that currently **fails** (the FAIL_TO_PASS analogue — proves the agent actually did the work, not that the test was already green).
2. `prompt.md` states the task in one or two sentences ("Implement `celsius_to_fahrenheit(c)` in `convert.py` so the tests pass.").
3. `verify.sh` is a two-line script: `cd "$1" && python3 -m pytest tests/test_convert.py -q`. Exit code of `pytest` IS the exit code of `verify.sh` (no wrapping logic needed — pytest already returns 0/non-zero correctly).
4. Prove `verify.sh` against BOTH states by hand, with zero agent/API involvement, in a bats test:
   - Copy `fixture/` (unsolved) into a tmp dir → run `verify.sh` → assert non-zero.
   - Copy `fixture/` but manually apply the "solved" edit → run `verify.sh` → assert zero.
   - This is exactly the project ARCHITECTURE.md's prescribed Build Order step 1: "Hand-craft a fixture in both a 'solved' and an 'unsolved' state and assert `verify.sh` returns 0/nonzero correctly... fully bats-testable today."

**When to use:** For every task fixture, always — this is the harness's single most important correctness property (project PITFALLS.md Pitfall 6: "fewer tokens because the task wasn't actually finished" — a headline number that doesn't gate on correctness is worse than no benchmark at all).

**Why deterministic + seconds-to-verify matters for THIS first task specifically:** the fixture built in this phase is not yet part of a real comparison suite — its only job is to prove the `verify.sh` contract and (later) the live schema. A test that takes minutes or depends on network/timing would slow down every bats run in CI going forward; keep it sub-second.

**Trade-offs:** A trivially small task (one function, one test) does not yet exercise multi-file changes, exploration, or realistic agent behavior — that's fine for Phase 1 (CONTEXT.md scope is "prove the primitive," not "build a representative task corpus," which is Phase 5's CORP-01/02).

### Pattern 2: Stub seam for `bench-run.py` — exact mechanics from this repo

**What:** `bench-run.py` resolves the `claude` binary path through an env-var seam:

```python
import os
import shutil

CLAUDE_BIN = os.environ.get("CAIRN_BENCH_CLAUDE_BIN") or shutil.which("claude") or "claude"
```

This mirrors the exact pattern read from `cairn/hooks/post-bd-write.sh` this session:
```bash
GBSYNC="${CAIRN_GBSYNC:-$PLUGIN_ROOT/scripts/gbsync.sh}"
CAIRN_MAP="${CAIRN_MAP:-$PLUGIN_ROOT/scripts/cairn-map.sh}"
```
— an env var, defaulting to the real resolved binary/script when unset. `[VERIFIED: cairn/hooks/post-bd-write.sh, this repo, read directly this session]`

**Naming:** Use `CAIRN_BENCH_CLAUDE_BIN`, not the bare `BENCH_CLAUDE_BIN` given as an illustrative example in CONTEXT.md — `.planning/codebase/CONVENTIONS.md` states plainly: "Environment variable seams (test/override points) are always `UPPER_CASE` with a `CAIRN_` prefix — `CAIRN_GBSYNC`, `CAIRN_MAP`, `CAIRN_GATE`..." `[VERIFIED: .planning/codebase/CONVENTIONS.md, read this session]`. CONTEXT.md's own phrasing ("e.g. `BENCH_CLAUDE_BIN`") reads as an illustrative example, not a locked literal name; following house convention takes precedence.

**Bats stub — the recorder/canned-output pattern**, adapted exactly from `tests/hooks.bats`'s `make_recorders()`:

```bash
make_claude_stub() {
  STUB="$BATS_TEST_TMPDIR/claude-stub"
  cat > "$STUB" <<'EOF'
#!/usr/bin/env bash
cat <<'JSON'
{"type":"result","subtype":"success","is_error":false,"duration_ms":1200,
 "duration_api_ms":900,"num_turns":2,"result":"done",
 "session_id":"stub-session-0000",
 "total_cost_usd":0.0031,
 "usage":{"input_tokens":812,"output_tokens":140,
          "cache_creation_input_tokens":0,"cache_read_input_tokens":0}}
JSON
EOF
  chmod +x "$STUB"
}

@test "bench-run writes one JSONL row with the stubbed claude output" {
  make_claude_stub
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-run.py" \
      --task "$BENCH_TASKS_DIR/smoke-convert" --out "$BATS_TEST_TMPDIR/raw.jsonl"
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$BATS_TEST_TMPDIR/raw.jsonl")" -eq 1 ]
  assert_json_eq "$(cat "$BATS_TEST_TMPDIR/raw.jsonl")" '.total_cost_usd' '0.0031'
}
```

**PATH-replacement variant is NOT the right tool here.** This repo reserves `PATH`-stubbing (`cairn-map.bats:219-231`, the "bd missing from PATH" test) for proving *absence* of a binary — a stub `bin/` dir deliberately excluding the tool, asserting the script's own "unavailable" exit code (5, in that case). HARN-03 needs the opposite: a *present*, canned-output double. Use the env-var seam for that; reserve a `PATH`-stub test only if `bench-run.py` needs its own "claude missing" exit-code test (a reasonable *additional* test, but a different scenario from the main HARN-03 ask).

**When to use:** Every bats test of `bench-run.py`'s deterministic logic (fixture staging, JSONL row shape, verify.sh invocation, error/timeout handling). Never invoke the real `claude` binary from a test that runs on every push/PR.

### Pattern 3: The one live run — triggering mechanism

**Claude's Discretion per CONTEXT.md** — recommendation: **no special flag needed.** Because the seam already defaults to the real binary when `CAIRN_BENCH_CLAUDE_BIN` is unset, the "live" invocation is simply:

```bash
# Run once, manually, deliberately — NOT part of `bats tests/`:
python3 benchmarks/scripts/bench-run.py \
  --task benchmarks/tasks/smoke-convert \
  --out benchmarks/results/smoke-convert.jsonl
```

No `--live` flag, no separate script, no environment-variable gate to remember to unset — the bats suite always sets `CAIRN_BENCH_CLAUDE_BIN` to a stub explicitly; a bare manual invocation naturally resolves to the real `claude` on `$PATH`. This is simpler than the alternative (a `--live`/`--dry-run` flag pair) and mirrors the zero-extra-flag `CAIRN_GBSYNC` pattern exactly — that seam has no "live mode" flag either. Document this invocation, its cost, and its resulting JSONL row in `benchmarks/README.md` and the phase SUMMARY, per CONTEXT.md's `<specifics>`.

### Anti-Patterns to Avoid

- **Running `verify.sh` from inside the agent's own working tree with the file present in it.** Even `chmod 444` doesn't fully close the loop if the agent's own toolset includes chmod/rm; keep the checker out of the tree entirely (Pattern 1).
- **Making the stub's canned JSON diverge from the real schema's field names/types.** If the stub payload uses different key names/casing than what `code.claude.com/docs` documents, the bats tests prove nothing about the real integration — keep the stub's JSON keys byte-identical to the verified schema (see "Verified JSON Result Schema" below), updating both together if Anthropic changes the schema.
- **Building `--baseline`, `HOME` override, or worktree isolation now.** Explicitly deferred to Phase 2 (FAIR-01/02) by CONTEXT.md; adding it here duplicates work and risks conflicting with how Phase 2 designs it with fuller context.
- **Trusting exit code alone without also parsing stdout as JSON.** Because the exit-code↔`is_error` mapping is not primary-source-documented (see Assumptions Log), `bench-run.py` must attempt `json.loads(stdout)` regardless of the subprocess's returncode, and only fall back to a synthetic `is_error: true` row if stdout fails to parse — never assume "non-zero exit ⇒ no usable JSON."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON parsing of `claude -p` output | A custom regex/text scraper of `claude`'s stdout | `json.loads(proc.stdout)` directly on the `--output-format json` result | The CLI already emits one well-formed JSON object per invocation; scraping human-readable/`text` output would be strictly worse and fragile across CLI versions |
| Detecting task success | An LLM-based "did it look done" check, or a heuristic like "did any file change" | A deterministic `verify.sh` (can shell out to `pytest`) | Project PITFALLS.md Pitfall 6 names this as the single most damaging shortcut in the whole benchmark effort — self-report or heuristics make the pass/fail number meaningless and unauditable |
| Stubbing the `claude` binary for tests | A Python-level mock/monkeypatch of `subprocess.run` | A tiny stub executable resolved through `CAIRN_BENCH_CLAUDE_BIN`, invoked via a real `subprocess.run` call | Matches the repo's explicit "tests are black-box CLI-contract tests... never mock script internals" philosophy (`TESTING.md`); a Python-level mock would test the mock, not the actual subprocess invocation path (argv construction, cwd, timeout, capture) |
| Wall-clock timing | Bash `$EPOCHREALTIME` or `date +%N` | `python3`'s `time.time()` around the `subprocess.run` call | Already documented and decided in the committed project STACK.md — macOS ships bash 3.2 (no `$EPOCHREALTIME`) and BSD `date` lacks `%N`; `time.time()` is portable across the whole target matrix |

**Key insight:** every "don't hand-roll" item above already has a working, tested precedent inside this exact repo (`cairn-gate.py`'s exit-code contract, `tests/hooks.bats`'s recorder-stub pattern, the committed STACK.md's timing decision) — the discipline for this phase is *reuse those patterns*, not invent new ones.

## Verified JSON Result Schema

Fetched live this session from `code.claude.com/docs/en/headless`, `code.claude.com/docs/en/cli-reference`, and `code.claude.com/docs/en/agent-sdk/cost-tracking` — `[VERIFIED: official docs, fetched 2026-07-25]`:

```json
// subtype: "success"
{
  "type": "result",
  "subtype": "success",
  "duration_ms": 0,
  "duration_api_ms": 0,
  "is_error": false,
  "num_turns": 0,
  "result": "string — the final text response",
  "session_id": "uuid string",
  "total_cost_usd": 0.0,
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0
  }
}
```

```json
// subtype: "error_max_turns" | "error_during_execution"
{
  "type": "result",
  "subtype": "error_max_turns",
  "duration_ms": 0,
  "duration_api_ms": 0,
  "is_error": true,
  "num_turns": 0,
  "session_id": "uuid string",
  "total_cost_usd": 0.0,
  "usage": { "...": "same 4 fields, still populated — confirmed by cost-tracking docs" }
}
```

Key facts confirmed directly this session:
- **`usage` and `total_cost_usd` are present on BOTH success and error results** — `[VERIFIED, quoted]`: "Both success and error result messages include `usage` and `total_cost_usd`... Always read cost data from the result message regardless of its `subtype`." (`agent-sdk/cost-tracking`)
- **`result` (the text field) is absent on error subtypes** — only present on `success` (confirmed by the schema difference cited in WebSearch corroboration of the TypeScript `SDKResultMessage` union; `result` string is success-only).
- **A separate `modelUsage`/`model_usage` breakdown exists** on the result message, keyed by model name, with `costUSD`, `inputTokens`, `outputTokens`, `cacheReadInputTokens`, `cacheCreationInputTokens` per model — useful if a later phase runs subagents, but the flat `usage` object is sufficient for Phase 1's single-turn smoke task. **Not needed for HARN-02's minimum field list.**
- **`total_cost_usd` is an explicit client-side ESTIMATE**, not authoritative billing — `[VERIFIED, quoted]`: "The `total_cost_usd` and `costUSD` fields are client-side estimates, not authoritative billing data... Use these fields for development insight and approximate budgeting." Document this caveat in `benchmarks/README.md` wherever `total_cost_usd` is reported, since the project's whole credibility premise (PITFALLS.md Pitfall 10) depends on methodological honesty.
- **`--max-turns` reaching its limit exits with an error and yields `subtype: "error_max_turns"`** — `[VERIFIED: cli-reference: "Exits with an error when the limit is reached"; CITED/MEDIUM: search-corroborated subtype name from SDK docs/community sources, not independently re-fetched from a single canonical schema table this session]`.
- **`--no-session-persistence` exists and is print-mode-only** — `[VERIFIED: cli-reference, fetched this session]`: "Disable session persistence so sessions are not saved to disk and cannot be resumed. Print mode only." Use this on the one live run so it leaves no session file behind.
- **`--bare` is explicitly Anthropic's own recommended mode for scripted/SDK calls** — `[VERIFIED, quoted]`: "`--bare` is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release." Use it on the live run even though full FAIR-01 isolation (HOME override, worktrees) is Phase 2 scope — `--bare` itself is a single, free flag, not an isolation *system*.
- **Exit code ↔ `is_error` mapping is NOT in an official table.** `code.claude.com/docs/en/errors` does not document a general exit-code table for `-p` mode (confirmed by direct fetch this session — the page covers installer/wrapper errors, not the print-mode result contract). Community/GitHub-issue evidence (`error_during_execution` correlating with process exit 1) is consistent but **MEDIUM confidence only** — treat this as an assumption requiring confirmation once the live run actually happens (see Assumptions Log).

## Flags for the Single Live Validation Run

Recommended invocation, combining verified flags from `cli-reference` (fetched this session) with the project's own committed STACK.md guidance:

```bash
claude --bare -p "$(cat benchmarks/tasks/smoke-convert/prompt.md)" \
  --model claude-haiku \
  --max-turns 5 \
  --permission-mode acceptEdits \
  --no-session-persistence \
  --output-format json
```

Rationale per flag:
- `--bare`: skip ambient hooks/skills/plugins/MCP/CLAUDE.md — Anthropic's own recommended default for scripted calls, and this phase's task doesn't need any of cairn's own capabilities to solve a trivial fixture. `[VERIFIED]`
- `--model claude-haiku`: cheapest available model alias for a task whose sole purpose is to validate the JSON *schema*, not to measure any baseline's real capability (that comparison is Phase 2+ and will pin a specific full model id per FAIR-02, not an alias). `[CITED: cli-reference aliases table — sonnet/opus/haiku/fable — fetched this session]` Using a full pinned model id instead of the `haiku` alias is also acceptable and slightly more reproducible; either is fine for a one-off schema-validation call since FAIR-02's "pin the exact full model id" discipline is a Phase 2 baseline-fairness requirement, not a Phase 1 one.
- `--max-turns 5`: the fixture task (implement one function) should resolve in 1-2 turns; 5 is a safety ceiling that still triggers `error_max_turns` cleanly if something goes wrong, without needing a long timeout.
- `--permission-mode acceptEdits`: auto-approves file writes/edits and common fs commands without prompting, but still gates arbitrary Bash/network — safer than `bypassPermissions`/`--dangerously-skip-permissions` on a real (non-sandboxed) developer machine, matching the project's own committed "What NOT to Use" guidance in STACK.md. `[VERIFIED flag values; CITED risk framing from STACK.md + code.claude.com/docs/en/devcontainer]`
- `--no-session-persistence`: no session file left behind after a one-off validation call. `[VERIFIED]`
- `--output-format json`: the schema under test. `[VERIFIED]`
- **Not used:** `--max-budget-usd` — exists per multiple secondary sources (`[CITED, MEDIUM confidence — not re-fetched from the primary cli-reference page this session, but consistent with the already-committed project STACK.md/ARCHITECTURE.md which independently arrived at the same flag]`) but is unnecessary for a `haiku`-tier, `max-turns 5`, single-function task where the cost ceiling is already near-zero; add it in Phase 2 once real multi-baseline runs are at stake.
- Run from a `mktemp -d` copy of `fixture/`, never the repo's own working tree — this is basic hygiene independent of Phase 2's fuller isolation system.

## Common Pitfalls

### Pitfall 1: Trusting exit code over parsed JSON

**What goes wrong:** `bench-run.py` branches on the subprocess's returncode to decide whether a JSON payload exists, and skips parsing stdout when returncode is non-zero — but the docs show `usage`/`total_cost_usd` are present on error results too, and the exit-code contract itself is undocumented.
**Why it happens:** It's tempting to treat "non-zero exit" as "nothing useful to parse," mirroring how most CLI tools behave.
**How to avoid:** Always attempt `json.loads(proc.stdout)` first, regardless of returncode; only synthesize a fallback error row if parsing itself fails (empty stdout, truncated output, a non-JSON error string on stderr instead).
**Warning signs:** A test that only exercises the success path and never feeds the stub an `error_max_turns` payload.

### Pitfall 2: Stub JSON drifting from the real schema

**What goes wrong:** The bats recorder stub's canned JSON uses field names or a shape that doesn't match what `claude -p --output-format json` actually returns (e.g., forgetting `duration_api_ms`, or nesting `usage` incorrectly).
**Why it happens:** The stub is hand-written once and never re-diffed against a real response.
**How to avoid:** The one live run in this phase is the reference point — after running it for real, diff its raw JSON output against the stub's canned payload and correct any drift before calling HARN-03 done. Keep both in the same file/fixture location so they're easy to compare side by side.
**Warning signs:** bats tests all green, but the live run's real JSON has a field the JSONL-row writer silently drops (e.g., `.get("field", None)` masking a typo in the key name).

### Pitfall 3: `verify.sh` accidentally verifiable by the agent inspecting its own prompt

**What goes wrong:** If `prompt.md` contains a hint like "make sure `test_convert.py` passes" and the agent can `find` or `grep` its way to `verify.sh` anyway (e.g., it's staged inside the workdir under a name the agent can discover), the checker's independence is compromised even if it isn't literally rewritten.
**Why it happens:** Convenience — staging everything the harness needs in one place.
**How to avoid:** Physically keep `verify.sh` outside the workdir tree entirely (Pattern 1); the harness invokes it with the workdir path as an argument, never copies it in.
**Warning signs:** `ls -la` inside the workdir (as the agent would see it) reveals a `verify.sh` file.

### Pitfall 4: Building Phase 2/3 machinery early

**What goes wrong:** While implementing `bench-run.py`, it's tempting to add a `--baseline` flag, a `HOME` override, or a repetition loop "since it's basically free to add now."
**Why it happens:** The full project ARCHITECTURE.md (already committed) describes the eventual full pipeline, and it's natural to want to lay groundwork.
**How to avoid:** CONTEXT.md's `<deferred>` section is explicit and should be treated as a hard boundary for this phase's scope, exactly like a locked decision — Phase 2 will design isolation/baselines with fuller context (competitor plugin shape, etc.) than is available now.
**Warning signs:** `bench-run.py`'s CLI surface grows beyond `--task`/`--out` before Phase 2 starts.

## Code Examples

### `verify.sh` skeleton (Pattern 1)

```bash
#!/usr/bin/env bash
# verify.sh <workdir> — exit 0 = task solved, non-zero = not solved.
# Never staged inside <workdir>; invoked with its path as an argument.
set -euo pipefail
WORKDIR="$1"
cd "$WORKDIR"
exec python3 -m pytest tests/test_convert.py -q
```

### `bench-run.py` skeleton (HARN-02, house-style docstring contract)

```python
#!/usr/bin/env python3
"""bench-run — invoke claude -p headless against one task fixture, write one
raw JSONL row per run.

Usage:
    bench-run.py --task <task-dir> --out <jsonl-path>

Behavior:
    1. Read <task-dir>/task.json (prompt_file, timeout_s, max_turns) and
       <task-dir>/prompt.md.
    2. Stage a fresh mktemp workdir from <task-dir>/fixture/.
    3. Resolve the claude binary via CAIRN_BENCH_CLAUDE_BIN, falling back to
       the real `claude` on PATH.
    4. Invoke `claude -p <prompt> --bare --output-format json --max-turns N
       --no-session-persistence`, cwd=workdir, capture_output=True,
       timeout=timeout_s.
    5. Parse stdout as JSON regardless of returncode; on parse failure,
       synthesize {"is_error": true, "parse_error": "..."}.
    6. Invoke <task-dir>/verify.sh <workdir>; verify_passed = (returncode==0).
    7. Append one JSON line to --out: task_id, started_at, payload fields,
       verify_passed, harness_git_sha.
    8. rmtree(workdir).

Exit codes:
    0  run completed (regardless of verify_passed — that's a data column,
       not a harness failure)
    2  usage error
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2


def die(msg, code):
    print(f"[bench-run] error: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_claude_bin():
    return os.environ.get("CAIRN_BENCH_CLAUDE_BIN") or shutil.which("claude") or "claude"


def main():
    # ... parse_args, load task.json/prompt.md ...
    workdir = tempfile.mkdtemp(prefix="cairn-bench-")
    try:
        shutil.copytree(task_dir / "fixture", workdir, dirs_exist_ok=True)
        cmd = [resolve_claude_bin(), "-p", prompt_text,
               "--bare", "--output-format", "json",
               "--max-turns", str(max_turns),
               "--no-session-persistence"]
        start = time.time()
        proc = subprocess.run(cmd, cwd=workdir, capture_output=True,
                               text=True, timeout=timeout_s)
        wall_ms = int((time.time() - start) * 1000)
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            payload = {"is_error": True, "parse_error": str(e),
                       "raw_stdout": proc.stdout[:2000]}
        verify = subprocess.run(["bash", str(task_dir / "verify.sh"), workdir])
        row = {"task_id": task_id, "wall_clock_ms": wall_ms,
               **payload, "verify_passed": verify.returncode == 0}
        with open(out_path, "a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
```

## State of the Art

| Old Approach (SWE-bench/terminal-bench convention) | Current Approach (this repo, Phase 1) | When Changed | Impact |
|--------------------------------------------------|----------------------------------------|---------------|--------|
| `task.yaml` manifest | `task.json` manifest | Deliberate, this phase | Python stdlib has no YAML parser; documented deviation, not an oversight (already decided in committed ARCHITECTURE.md) |
| Docker-isolated task execution (SWE-bench, terminal-bench) | Plain `mktemp -d` + fixture copy, no container | This phase (and likely permanently, per repo's "runs anywhere Claude Code runs" constraint) | Simpler, zero-dependency, but weaker isolation than Docker — acceptable for Phase 1's single-task, single-run scope; full HOME-override isolation is still Phase 2, not Docker |
| `--print`/`-p` without `--bare` (implicit ambient config) | `--bare` explicitly, on every scripted call | Anthropic doc update (confirmed live this session): "`--bare` is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release" | A future `claude` version may make `--bare` the default — the harness should keep passing it explicitly regardless, since relying on a future default silently changes behavior on upgrade otherwise |

**Deprecated/outdated:** None specific to this phase — the flags and schema fields verified this session are all current as of `claude` 2.1.220 (confirmed installed locally).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Process exit code is non-zero for `subtype: error_max_turns`/`error_during_execution` and 0 for `subtype: success` | "Verified JSON Result Schema", Pitfall 1 | LOW — mitigated by design: `bench-run.py` parses stdout as JSON regardless of exit code, so an incorrect assumption about exit codes doesn't corrupt the JSONL row; only affects any code path that branches on returncode alone (avoid writing one) |
| A2 | `--max-budget-usd` exists and is print-mode-only, accepting a float ceiling | "Flags for the Single Live Validation Run" | LOW — this phase's recommended invocation doesn't use it; if absent/renamed in the installed CLI version, the flag simply isn't passed, no functional dependency on it here |
| A3 | `claude-haiku` is a valid, currently-resolvable model alias distinct from a full pinned model id | "Flags for the Single Live Validation Run" | LOW-MEDIUM — if the alias doesn't resolve on the installed CLI version, the live run fails fast with a clear CLI error before any cost is incurred; substitute any valid model id/alias confirmed by `claude --model <x> -p "hi" --output-format json` as a pre-flight check before the real fixture run |
| A4 | House convention favors `CAIRN_BENCH_CLAUDE_BIN` over CONTEXT.md's illustrative `BENCH_CLAUDE_BIN` | "Pattern 2: Stub seam" | LOW — purely a naming choice; either works functionally, but `CAIRN_BENCH_CLAUDE_BIN` matches the repo's own documented convention (`CONVENTIONS.md`) and should be preferred unless the planner/user explicitly wants the bare name |

**If this table is empty:** N/A — see rows above. All other factual claims in this document are tagged `[VERIFIED]`/`[CITED]` inline with their source.

## Open Questions (RESOLVED)

1. **Does the installed `claude` 2.1.220 actually emit exit code 0/non-zero matching A1's assumption?** (RESOLVED)
   - What we know: cli-reference confirms `--max-turns` "exits with an error" at the limit; community/issue sources describe `error_during_execution` correlating with exit 1.
   - What's unclear: no official exit-code table exists (confirmed by direct fetch of `code.claude.com/docs/en/errors` this session, which does not cover this).
   - Recommendation: the one live run in this phase is itself the empirical answer — record the actual `$?` alongside the JSON payload when it happens, and note the observed mapping in the phase SUMMARY for future phases to rely on with HIGH confidence instead of MEDIUM.
   - RESOLVED: (live runs 2026-07-25, rows committed in `benchmarks/results/smoke-convert.jsonl`) Both live results — `subtype:"error_max_turns"` and `subtype:"success"` — emitted fully-parseable JSON on stdout with `usage`/`total_cost_usd` populated; `bench-run.py` exited 0 on both runs by contract, and the row deliberately does not record the inner claude returncode (nothing branches on it). Empirically observed: the reliable error signals are `is_error` + `terminal_reason` (`"max_turns"`, `"completed"`, `"api_error"`), never exit code or `subtype` alone — an unauthenticated call returns `subtype:"success"` WITH `is_error:true` and `terminal_reason:"api_error"`. A1's mitigation (parse stdout regardless of returncode) is validated live; confidence upgraded MEDIUM → HIGH.

2. **Is a plain function-implementation task (no git, no multi-file) too trivial to catch real edge cases in `bench-run.py` (e.g., `verify.sh` invoked from the wrong cwd)?** (RESOLVED)
   - What we know: ARCHITECTURE.md's Build Order explicitly wants the smallest task for de-risking, not realism.
   - What's unclear: whether a second, deliberately-git-based fixture should also exist in this phase to exercise a diff-based `verify.sh` variant.
   - Recommendation: keep Phase 1 to exactly one fixture task (matches CONTEXT.md scope: "Claude's Discretion" over "the content of the first fixture task," singular) — defer task diversity to Phase 5 (CORP-01).
   - RESOLVED: resolved as the Recommendation stands — Phase 1 kept exactly one fixture task (smoke-convert), and the single fixture proved sufficient: both live rows validated the full schema, the verify.sh wiring, and even surfaced real edge findings (out-dir guard, `--bare`×OAuth, model-id pinning, `num_turns` exceeding the cap) without any second fixture. Task diversity is deferred to Phase 5 (CORP-01).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `claude` CLI | HARN-02 (the one live run) | ✓ | 2.1.220 | — |
| `python3` | HARN-01, HARN-02 (harness + verify.sh's pytest call) | ✓ | 3.12.1 | — |
| `bats-core` | HARN-03 (test suite) | ✓ | 1.14.0 | — |
| `jq` | Optional bash-level JSON sanity checks / `assert_json_eq` in bats | ✓ | 1.8.1 | — |
| `git` | Only if a git-based fixture variant is added (not needed for the recommended first task) | ✓ (repo itself is git) | n/a (system git) | Skip — first task is git-free by design |

**Missing dependencies with no fallback:** None — every dependency needed for this phase is already installed and confirmed in this environment.
**Missing dependencies with fallback:** None applicable.

## Security Domain

`security_enforcement` is absent from `.planning/config.json` (treated as enabled per default policy). This phase's tech stack is a local CLI harness with no auth, no session management, no network-facing surface, and no user-supplied untrusted input beyond the fixture's own repo-controlled prompt text — most ASVS categories don't apply, but the ones that do matter here are specific to subprocess/agent-execution safety, not web-app security.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | No auth surface — the harness is a local CLI, not a service |
| V3 Session Management | No | `--no-session-persistence` explicitly avoids creating session state at all |
| V4 Access Control | No | Single-user local tool |
| V5 Input Validation | Yes | `subprocess.run([...], shell=False)` with an argv list (never `shell=True`/string interpolation) — the task prompt text is repo-controlled, not user-uploaded, but treat it as untrusted input to the subprocess boundary anyway; never build the `claude` command line via string concatenation |
| V6 Cryptography | No | Not applicable — no crypto operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Command/argument injection via prompt text or task.json fields fed into a shell string | Tampering | Always pass `subprocess.run` a list (argv), never `shell=True` with interpolated strings; this is already the repo's existing convention (`gbsync.py`'s `subprocess.run(..., capture_output=True, text=True)` pattern) |
| `ANTHROPIC_API_KEY` (or other credentials) leaking into JSONL rows or bats logs | Information Disclosure | Never log `os.environ` wholesale; the JSONL row schema (Verified JSON Result Schema section) contains no credential fields by design — only write the documented result-object fields plus harness-added metadata |
| An agent under test escaping its intended fixture directory (e.g., via `--add-dir`, absolute paths in tool calls, or a prompt injection in fixture content) | Elevation of Privilege | Do not pass `--add-dir` on the live run (default scope is the workdir's cwd only); `--permission-mode acceptEdits` still gates arbitrary Bash, limiting blast radius versus `bypassPermissions` |
| `verify.sh` itself being tampered with if inadvertently staged inside the workdir | Tampering | Pattern 1 — keep `verify.sh` outside the workdir at all times, invoked with the workdir path as an argument |

## Sources

### Primary (HIGH confidence)
- `code.claude.com/docs/en/headless` — fetched live this session; `--bare` recommendation, `--output-format json/stream-json` behavior, background-task exit grace period, stdin cap
- `code.claude.com/docs/en/cli-reference` — fetched live this session; exact current flag list/values for `--output-format`, `--max-turns`, `--model`, `--permission-mode`, `--no-session-persistence`, `--bare`, `--settings`, `--plugin-dir`, `--dangerously-skip-permissions`, `--add-dir`, `--session-id`
- `code.claude.com/docs/en/agent-sdk/cost-tracking` — fetched live this session; exact `usage`/`total_cost_usd`/`modelUsage` field semantics, confirmation that both success and error results carry cost/usage data, the "estimate, not billing" caveat
- `code.claude.com/docs/en/errors` — fetched live this session; confirms NO official exit-code table exists for `-p` mode (a negative-claim verification, not just an assumption)
- This repo's own `cairn/hooks/post-bd-write.sh`, `tests/hooks.bats`, `tests/helpers.bash`, `.planning/codebase/TESTING.md`, `.planning/codebase/CONVENTIONS.md`, `cairn/scripts/cairn-gate.py`, `cairn/scripts/cairn-map.py`, `tests/cairn-map.bats` — all read directly this session; source of every "house style"/"stub seam" claim
- Local environment probes this session: `claude --version` (2.1.220), `python3 --version` (3.12.1), `bats --version` (1.14.0), `jq --version` (1.8.1)

### Secondary (MEDIUM confidence)
- WebSearch corroboration (multiple independent sources, cross-referenced) — `SDKResultMessage`/`ResultMessage` subtype values (`success`, `error_max_turns`, `error_during_execution`), exit-code-1 correlation with `error_during_execution`, `--max-budget-usd` flag existence and print-mode-only scope
- `swebench.com/SWE-bench/reference/harness`, `github.com/swe-bench/SWE-bench` — `FAIL_TO_PASS`/`PASS_TO_PASS` concept, adapted (not copied) into the `verify.sh` recipe
- `harborframework.com/docs/tutorials/running-terminal-bench` — confirmed oracle-solution concept exists, but the fetch did not surface concrete `task.yaml`/`tests/` file-level detail this session (page content was thin); treated as directional confirmation only, not a detailed template

### Tertiary (LOW confidence)
- None specifically load-bearing in this document — the one MEDIUM-confidence gap (exit-code mapping) is explicitly flagged in the Assumptions Log with a mitigation (parse JSON regardless of exit code) rather than left as an unverified hard dependency.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, every tool version-confirmed installed locally this session
- Architecture (verify.sh design, stub seam): HIGH — patterns lifted directly from this repo's own existing, working code, read this session, not inferred
- JSON schema / flags: HIGH on field names and flag behavior (official docs, fetched live), MEDIUM on the exit-code↔is_error mapping specifically (no official table found)
- Pitfalls: HIGH — sourced from the project's own already-committed, multiply-cross-referenced PITFALLS.md (Pitfall 6 is the direct match for this phase's scope)

**Research date:** 2026-07-25
**Valid until:** 30 days for the house-style/repo-pattern claims (stable, internal); ~14 days for the `claude` CLI flag/schema claims specifically, since the docs themselves note version-gated behavior changes across recent 2.1.x releases (e.g., stream-drain wait changed in 2.1.214, stdin fix in 2.1.211) — re-verify against `code.claude.com/docs` if the installed `claude` version changes before this phase executes.
