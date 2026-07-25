# Architecture Research

**Domain:** Reproducible LLM-agent benchmark harness, embedded inside an existing Python-stdlib/bash/bats plugin repo (CairnGo v1.1 — "Metrics & Benchmarks")
**Researched:** 2026-07-25
**Confidence:** MEDIUM-HIGH (Claude Code headless flags and JSON result schema are HIGH confidence, sourced from current official docs; the harness component decomposition itself is a synthesis of two closely analogous public repos — SWE-bench/terminal-bench-style task+verify design and a Claude-Code-specific token-benchmark repo — adapted to this repo's own constraints, so mark that synthesis MEDIUM until validated by building task #1)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  benchmarks/tasks/<id>/            benchmarks/baselines/<id>/             │
│  task.json + prompt.md + fixture/  baseline.json + settings.json          │
│  verify.sh (objective pass/fail)   (plugin-dir/plugin-url list, pinned)   │
└───────────────────────┬───────────────────────────┬───────────────────────┘
                         │ read by                    │ read by
                         ▼                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  bench-run.py  (runner + collector, one process)                         │
│  for each (task, baseline, repetition):                                  │
│    1. fresh isolated worktree from task fixture                         │
│    2. stage baseline's --bare + --plugin-dir/--settings/--model flags   │
│    3. exec `claude -p "$(cat prompt.md)" --output-format json …`         │
│    4. run task's verify.sh against the resulting worktree → pass/fail   │
│    5. append one row to raw/<task>__<baseline>.jsonl                    │
└───────────────────────┬────────────────────────────────────────────────┘
                         │ raw JSONL rows (1 row = 1 run)
                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  bench-aggregate.py                                                      │
│  group by (task, baseline) → N, pass-rate, mean/median/stdev tokens,     │
│  geometric-mean cost_usd, mean turns, mean wall-clock                    │
└───────────────────────┬────────────────────────────────────────────────┘
                         │ results/<run-id>/aggregated.json
                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  bench-report.py                                                         │
│  aggregated.json → REPORT.md (comparison table) + charts/*.svg           │
│  (hand-rolled SVG bar charts — no matplotlib, stays zero-dep)            │
└───────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  bench-publish.py                                                         │
│  embeds latest REPORT.md table + chart links into root README.md         │
│  between generated markers — same convention as cairn-map.py             │
└──────────────────────────────────────────────────────────────────────────┘
```

**Deliberate scope decision:** the brief's proposed 6-component split (task defs,
runner, collector, aggregator, reporter, publication) collapses to 5 real
components here. `claude -p --output-format json` already returns
`total_cost_usd`, full token `usage`, `num_turns`, `duration_ms`, and
`is_error` in one payload (confirmed against current Agent SDK docs — see
Sources). A separate "collector" that scrapes session logs after the fact
would duplicate that payload for no benefit; the runner writes the JSONL row
directly from the CLI's own JSON result. Keep collection *inside* the runner
process, one row per invocation.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|-------------------------|
| Task definition | Fixed, versioned unit of work: seed repo state + exact prompt text + objective completion check | `benchmarks/tasks/<id>/{task.json,prompt.md,fixture/,verify.sh}` |
| Baseline definition | Exactly which Claude Code configuration is under test (vanilla / GSD-only / cairn / competitor) | `benchmarks/baselines/<id>/{baseline.json,settings.json}` |
| Runner + collector | Executes N repetitions of (task × baseline), isolates each in a throwaway worktree, invokes `claude -p`, runs `verify.sh`, appends the raw result row | `benchmarks/scripts/bench-run.py` + `.sh` wrapper |
| Aggregator | Turns many raw JSONL rows into one stable statistics artifact per (task, baseline) | `benchmarks/scripts/bench-aggregate.py` + `.sh` wrapper |
| Reporter | Renders the aggregated artifact as a markdown table and SVG bar charts | `benchmarks/scripts/bench-report.py` + `.sh` wrapper |
| Publisher | Regenerates the README's embedded benchmark section from the latest run, using the same generated-marker convention as `cairn-map.py` | `benchmarks/scripts/bench-publish.py` + `.sh` wrapper |
| Results archive | Append-only, per-run directory (`manifest.json` + raw + aggregated + report + charts) that is the audit trail behind any public claim | `benchmarks/results/<run-id>/` |

## Recommended Project Structure

```
benchmarks/                          # top-level, sibling to cairn/ and tests/ — NOT shipped in the plugin
├── README.md                        # how to run, cost estimate table, methodology, "what counts as a pass"
├── tasks/
│   └── <task-id>/
│       ├── task.json                # id, description, difficulty, timeout_s, max_turns, fixture ref
│       ├── prompt.md                 # the exact, baseline-agnostic prompt text
│       ├── fixture/                  # seed repo tree copied fresh into every run's worktree
│       └── verify.sh                 # objective pass/fail; exit 0 = task solved (may shell out to bats/pytest)
├── baselines/
│   └── <baseline-id>/                # vanilla | gsd-only | cairn | <competitor>
│       ├── baseline.json             # description, plugin-dir/plugin-url list, pinned versions, notes
│       └── settings.json             # passed verbatim to `claude --settings`
├── scripts/
│   ├── bench-run.py / .sh            # runner+collector
│   ├── bench-aggregate.py / .sh      # raw JSONL(s) -> aggregated.json
│   ├── bench-report.py / .sh         # aggregated.json -> REPORT.md + charts/*.svg
│   └── bench-publish.py / .sh        # embed latest report into root README.md
└── results/
    └── <run-id>/                     # e.g. 2026-07-25_claude-sonnet-5  (append-only, never overwritten)
        ├── manifest.json             # every pinned version + timing — the reproducibility contract
        ├── raw/<task>__<baseline>.jsonl
        ├── aggregated.json
        ├── REPORT.md
        └── charts/*.svg

tests/                                # existing flat suite — new files added here, NOT under benchmarks/
├── bench-run.bats                    # orchestration tested via a `claude` stub on PATH — no real API cost
├── bench-aggregate.bats              # tested against synthetic raw JSONL fixtures
├── bench-report.bats                 # tested against synthetic aggregated.json — proves markdown/SVG shape
└── bench-publish.bats                # proves generated-marker regeneration + idempotence
```

### Structure Rationale

- **`benchmarks/` lives at repo root, not under `cairn/`:** it is not part of
  what `/plugin install cairn@cairngo` ships to a user — it is
  repo-development tooling that produces the evidence behind a README claim,
  the same category as CI config, not a plugin feature. Putting it under
  `cairn/` would ship benchmark fixtures (and eventually gigabytes of
  `results/` history) inside every user's plugin install.
- **`tasks/` and `baselines/` are separated, not nested:** every baseline
  must run the identical task set with the identical prompt text — nesting
  baselines under tasks (or vice versa) invites someone to fork a prompt
  "just for this one baseline," which is exactly the fairness violation
  PROJECT.md's constraints warn against. Two flat, orthogonal directories
  make the runner's `for task × for baseline` double loop the only place
  they combine.
- **Task manifests are JSON, not YAML**, deliberately diverging from the
  SWE-bench/terminal-bench convention (`task.yaml`). PROJECT.md's house-style
  constraint is "python3 zero-dependências" — `cairn/scripts/*.py` and (per
  the same constraint) the benchmark harness must stay stdlib-only. Python's
  stdlib has no YAML parser; `json` does. This is a deliberate, documented
  deviation from ecosystem convention, not an oversight.
- **`verify.sh` per task, not a shared test runner:** tasks vary in what
  "done" means (a passing test suite, a file existing with certain content, a
  git diff matching a shape). A thin per-task `verify.sh` that can itself
  shell out to `bats`, `pytest`, or a hand-rolled check keeps the contract
  uniform (exit 0 = pass) while letting each task pick the right verification
  tool — mirrors terminal-bench's "tests/ folder + oracle solution" pattern
  and this repo's own "exit code is the entire contract" convention already
  used by `cairn-gate.py`.
- **New bats files land in the existing flat `tests/` directory**, not a
  parallel `benchmarks/tests/`. CI already runs `bats tests/` with no
  discovery configuration; a second test directory would need its own CI
  wiring for no benefit, and it breaks the repo's existing 1:1
  script-to-`.bats` naming convention documented in `TESTING.md`.
- **`results/<run-id>/` is append-only and committed.** PROJECT.md scoped
  "Dashboard/página web" and "telemetria contínua" as explicitly out — the
  credibility strategy is a fixed, reproducible suite whose history lives in
  git. Every run directory is immutable once written; a bad run is superseded
  by a new run directory, never edited in place.

## Architectural Patterns

### Pattern 1: Fresh isolated worktree per run

**What:** Every single `(task, baseline, repetition)` invocation gets a brand
new throwaway git worktree (or `mktemp -d` + `git init`) seeded only from
`fixture/`, run once, then discarded — never reused across repetitions or
baselines.
**When to use:** Always, for every run without exception.
**Trade-offs:** Costs a few seconds of setup per run versus a shared/reused
workspace, but a reused workspace silently leaks state between repetitions
(stale files, git history, a warm model-side cache) and would invalidate the
"reproducível" and "mesmas condições" requirements outright. This is the same
principle `tests/helpers.bash`'s `make_tmp_repo` already applies to every
bats test in this repo — the benchmark runner should follow the identical
discipline, just against a real `claude` invocation instead of a cairn
script.

**Example:**
```python
def run_once(task, baseline, rep_index, results_path):
    workdir = tempfile.mkdtemp(prefix=f"cairn-bench-{task.id}-")
    try:
        stage_fixture(task.fixture_dir, workdir)
        cmd = build_claude_cmd(task, baseline, workdir)
        result = subprocess.run(cmd, cwd=workdir, capture_output=True,
                                 timeout=task.timeout_s, text=True)
        payload = json.loads(result.stdout)          # claude -p --output-format json
        passed = run_verify(task.verify_script, workdir) == 0
        write_jsonl_row(results_path, task, baseline, rep_index, payload, passed)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
```

### Pattern 2: `--bare` + explicit flags, never ambient config

**What:** Every `claude -p` invocation passes `--bare` (skips
auto-discovery of hooks, skills, plugins, MCP servers, auto-memory, and
CLAUDE.md) and then re-adds *only* what the baseline under test declares
(`--plugin-dir`/`--plugin-url` for the vanilla/GSD/cairn/competitor plugin
set, `--settings <baseline settings.json>`, a pinned `--model <full id>`, a
uniform `--max-turns`/`--max-budget-usd` ceiling, `--no-session-persistence`).
**When to use:** Every single run, no exceptions — this is the mechanism
that makes "same conditions" true rather than aspirational.
**Trade-offs:** More flags to get right up front, but the alternative
(letting each machine's `~/.claude/` and installed plugins leak in) makes the
whole benchmark non-reproducible by a third party running it on their own
machine — directly the failure mode PROJECT.md's "Honestidade metodológica"
constraint calls out. Official docs recommend `--bare` explicitly "for CI and
scripts where you need the same result on every machine" (Sources).

**Example:**
```bash
claude --bare -p "$(cat "$TASK_DIR/prompt.md")" \
  --model claude-sonnet-5 \
  --plugin-dir "$BASELINE_DIR/plugins/cairn" \
  --settings "$BASELINE_DIR/settings.json" \
  --allowedTools "Bash,Read,Edit,Write" \
  --permission-mode bypassPermissions \
  --max-turns 40 \
  --max-budget-usd 2.00 \
  --no-session-persistence \
  --output-format json
```

### Pattern 3: Stub seam for testing the harness itself (no live API cost)

**What:** `bench-run.py` resolves the `claude` binary through an
overridable seam (`CAIRN_BENCH_CLAUDE_BIN`, mirroring the existing
`CAIRN_GBSYNC`/`CAIRN_MAP`/`CAIRN_GATE` env-var seams documented in
`TESTING.md`). Bats tests point that seam at a recorder stub that prints a
canned `--output-format json` payload and exits, so the harness's own logic
(fixture staging, JSONL row shape, cleanup, verify-script invocation,
timeout handling) is exercised by the existing black-box, CLI-contract bats
style — with zero real Anthropic API spend.
**When to use:** For every bats test of `bench-run.py`/`bench-aggregate.py`/
`bench-report.py`. Reserve actual `claude` invocations for a separate,
manually or CI-scheduled, cost-bounded job — never run them as part of the
normal `bats tests/` suite that runs on every push/PR (see CI note below).
**Trade-offs:** Stub-based tests cannot catch a real CLI flag regression
(e.g., Anthropic renaming a JSON field) — accept that risk the same way
`gbsync.bats`'s `--dry-run` tests accept never touching the real network;
pair it with periodic smoke runs against the live API, gated by cost.

**Example (mirrors the existing recorder-stub pattern in `tests/helpers.bash`):**
```bash
make_claude_stub() {
  STUB="$BATS_TEST_TMPDIR/claude-stub"
  cat > "$STUB" <<'EOF'
#!/usr/bin/env bash
cat <<'JSON'
{"total_cost_usd":0.0421,"num_turns":6,"duration_ms":18234,
 "usage":{"input_tokens":9120,"output_tokens":812,
          "cache_creation_input_tokens":4000,"cache_read_input_tokens":15000},
 "is_error":false,"session_id":"stub-session"}
JSON
EOF
  chmod +x "$STUB"
}

@test "bench-run writes one JSONL row per repetition" {
  make_claude_stub
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-run.py" \
      --task smoke-task --baseline vanilla --reps 3 --out "$BATS_TEST_TMPDIR/raw.jsonl"
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$BATS_TEST_TMPDIR/raw.jsonl")" -eq 3 ]
}
```

### Pattern 4: Generated artifact regeneration for the README embed

**What:** `bench-publish.py` rewrites only the content between
`<!-- cairn-bench:generated:start -->` / `<!-- cairn-bench:generated:end -->`
markers in the root `README.md`, exactly the mechanism `cairn-map.py` already
uses for `NN-BEADS-MAP.md`.
**When to use:** Every publish step; never hand-edit inside the markers.
**Trade-offs:** None significant — this reuses a pattern already proven in
this repo, both in implementation and in the existing anti-pattern
documentation ("Hand-editing a generated block") that this new script should
extend rather than duplicate.

## Data Flow

### Benchmark run flow

```
task.json + prompt.md + fixture/  ┐
                                    ├─→ bench-run.py (per task × baseline × rep)
baseline.json + settings.json     ┘        │
                                            ├─ 1. fresh isolated worktree
                                            ├─ 2. claude -p … --output-format json
                                            ├─ 3. verify.sh <worktree> → exit code
                                            └─ 4. append JSONL row
                                                    ↓
                              raw/<task>__<baseline>.jsonl (append-only, one line per run)
                                                    ↓
                                    bench-aggregate.py (group by task × baseline)
                                                    ↓
                                    results/<run-id>/aggregated.json
                                                    ↓
                                    bench-report.py
                                          ├─→ REPORT.md (comparison table)
                                          └─→ charts/*.svg (hand-rolled, stdlib)
                                                    ↓
                                    bench-publish.py → README.md (generated-marker embed)
```

### Raw JSONL row shape (one line = one `claude -p` invocation)

```json
{
  "task_id": "add-endpoint-with-tests",
  "baseline_id": "cairn",
  "repetition": 3,
  "model": "claude-sonnet-5",
  "started_at": "2026-07-25T14:02:11Z",
  "duration_ms": 41822,
  "duration_api_ms": 38010,
  "num_turns": 9,
  "total_cost_usd": 0.1187,
  "usage": {
    "input_tokens": 21044,
    "output_tokens": 1830,
    "cache_creation_input_tokens": 8200,
    "cache_read_input_tokens": 61500
  },
  "is_error": false,
  "session_id": "…",
  "verify_passed": true,
  "verify_output": "3 passed, 0 failed",
  "harness_git_sha": "6a39e3d…"
}
```

Every field above except `task_id`/`baseline_id`/`repetition`/`started_at`/
`verify_passed`/`verify_output`/`harness_git_sha` comes straight from `claude
-p --output-format json`'s own result payload — no post-hoc log scraping
needed (confirmed field-by-field against the current Agent SDK
`SDKResultMessage` schema; see Sources).

### `manifest.json` — the reproducibility contract (one per run directory)

```json
{
  "run_id": "2026-07-25_claude-sonnet-5",
  "claude_code_version": "2.1.214",
  "model": "claude-sonnet-5",
  "baselines": {
    "vanilla": {"plugins": []},
    "gsd-only": {"plugins": ["gsd@1.42.2"]},
    "cairn": {"plugins": ["gsd@1.42.2", "cairn@1.0.0"]},
    "<competitor>": {"plugins": ["<competitor>@<version>"]}
  },
  "task_set_git_sha": "…",
  "repetitions_per_task": 5,
  "started_at": "…", "finished_at": "…"
}
```

Without this file, a reader has no way to verify that "cairn uses fewer
tokens" was measured against the same model/version/task set as the other
baselines — this is the single artifact that makes the "honestidade
metodológica" constraint checkable rather than asserted.

## Scaling Considerations

A benchmark suite does not scale to "users" — it scales along three axes:
number of tasks, number of baselines, and repetitions per (task, baseline).
Cost is the real constraint (PROJECT.md: "custo previsível e documentado"),
not throughput.

| Scale | Approach |
|-------|----------|
| Smoke run (1 task × 1 baseline × 1 rep) | Used to develop and bats-test the pipeline itself with the stub seam (Pattern 3); zero live API cost, runs on every PR touching `benchmarks/`. |
| Full suite (few tasks × 3-4 baselines × 5-10 reps) | The actual published comparison. Cost = `tasks × baselines × reps × avg_cost_per_task`; `benchmarks/README.md` must state this number before anyone runs it, per the cost-predictability constraint. Run manually or on a scheduled/tagged CI job — never on every push. |
| Growth over time (new tasks, new model releases, historical trend) | Each run is its own immutable `results/<run-id>/` directory; a trend view is a future `bench-report.py --compare <run-id-1> <run-id-2>` mode reading multiple `aggregated.json` files — no change to the storage model needed, just an additional reporter mode. Do not build this until at least two real runs exist. |

### Scaling priorities

1. **First real constraint: API cost, not code.** Every task/baseline/rep
   triple is a paid Anthropic API call. Keep the task count small and the
   tasks short (terminal-bench and THOL both explicitly restrict scope —
   terminal-bench per-task, THOL to "sessions where vanilla burns
   >200k tokens" — deliberately, not by accident). Size CairnGo's own task
   set to what is affordable to re-run on every cairn/GSD minor version
   bump, since that re-run is the credibility mechanism.
2. **Second constraint: variance, not volume.** Token counts and cost are
   right-skewed (a single long tool-call retry loop can blow up one run's
   total). Reporting only an arithmetic mean, as most naive comparisons do,
   overstates the effect of outliers. Aggregate cost/tokens with a geometric
   mean (THOL's explicit methodology, cited below) and always report N and a
   spread (stdev or min/max), never a bare point estimate — this is also a
   direct requirement of PROJECT.md's "variância reportada" constraint.

## Anti-Patterns

### Anti-Pattern 1: LLM self-report as the completion criterion

**What people do:** Trust the agent's own final message ("I've completed the
task") or a rough heuristic like "did any file change" as pass/fail.
**Why it's wrong:** An agent can claim success on a broken implementation, or
under-report turns/cost if it self-summarizes. It also makes the criterion
unauditable by a third party without re-running the LLM.
**Do this instead:** Every task ships an independent, deterministic
`verify.sh` (can shell out to `bats`/`pytest`/a plain assertion script) that
inspects the *resulting filesystem state*, exactly the SWE-bench/
terminal-bench convention ("tests/ folder housing deterministic pytest
scripts... checks the end state of the environment, not the agent's
transcript" — Sources). `verify.sh`'s exit code, not the model's prose, is
`verify_passed` in the JSONL row.

### Anti-Pattern 2: Comparing baselines that don't share task, prompt, and model

**What people do:** Let each baseline use a slightly different phrasing
("optimized for that tool"), a different `--model` alias that silently
resolves to different dated snapshots on different days, or skip `--bare`
so one baseline picks up an extra ambient plugin nobody accounted for.
**Why it's wrong:** Any of these invalidates the comparison — you're no
longer measuring the baseline, you're measuring an uncontrolled variable.
This is precisely the "vale só se a metodologia aguentar escrutínio público"
risk named in PROJECT.md.
**Do this instead:** One `prompt.md` per task, read verbatim by every
baseline; one pinned full model id (not an alias) per run, recorded in
`manifest.json`; `--bare` always, with only the baseline's declared
plugins/settings re-added explicitly.

### Anti-Pattern 3: Reusing or warm-starting workspaces across repetitions

**What people do:** Run repetition 2 in the same directory as repetition 1
"to save setup time," or reuse a long-lived container across the whole
matrix.
**Why it's wrong:** Leftover files, git history, or filesystem cache state
leak between runs and silently bias later repetitions — usually toward
*better* numbers, since later runs benefit from state the first run had to
build from scratch.
**Do this instead:** Fresh `mktemp -d` (or a fresh git worktree) seeded only
from `fixture/` for every single run; delete it after; never reuse (Pattern 1
above).

### Anti-Pattern 4: Publishing an average with no visible spread

**What people do:** Ship "cairn uses 30% fewer tokens" as a single number.
**Why it's wrong:** Without N and a spread, a reader cannot tell a real
effect from run-to-run noise, and the claim cannot be falsified.
**Do this instead:** `aggregated.json` always carries `n`, a geometric mean
(for cost/tokens), and a dispersion measure per (task, baseline);
`bench-report.py`'s markdown table renders at least mean ± spread, and the
raw JSONL stays committed in `results/<run-id>/raw/` so anyone can
recompute the statistic independently.

### Anti-Pattern 5: Testing the harness's deterministic logic with real API calls

**What people do:** Write the harness's own CI tests (JSONL shape,
aggregation math, chart rendering) as tests that shell out to a real `claude
-p` call "to keep it honest."
**Why it's wrong:** Makes every PR touching `benchmarks/scripts/` cost real
money and become flaky/slow/non-deterministic — the opposite of what this
repo's whole bats philosophy (`tests/README.md`) exists to prevent.
**Do this instead:** Stub the `claude` binary (Pattern 3) for every bats
test; keep real, costed runs as a separate, deliberately-triggered job.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Anthropic API via the `claude` CLI (`claude -p`) | Subprocess invocation from `bench-run.py`; `--output-format json` gives the full result payload (`total_cost_usd`, `usage.*`, `num_turns`, `duration_ms`, `is_error`) in one call — HIGH confidence, current official docs. | Pin the full model id via `--model` (not an alias like `sonnet`, which can silently move). Use `--max-budget-usd` as a hard per-run safety cap and `--max-turns` as a fairness cap applied identically across baselines. `--bare` is explicitly recommended by Anthropic "for CI and scripts where you need the same result on every machine." |
| Competitor workflow plugin (baseline #4) | Staged the same way as cairn/GSD — `--plugin-dir`/`--plugin-url` pointed at a pinned copy/version, described in its own `baselines/<competitor>/baseline.json`. | Open question, flag for phase-specific research: not all third-party Claude Code plugins are guaranteed to have documented headless-mode support or a pinnable version reference — verify per-competitor before committing to it as a baseline; if a competitor has no reliable headless story, that itself is a legitimate (and reportable) finding rather than a blocker. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `benchmarks/scripts/*.py` ↔ `tests/*.bats` | bats `load '../tests/helpers'` reuses `make_tmp_repo` from the existing shared helper file; a new local helper (either appended to `tests/helpers.bash` or a small benchmark-scoped helper loaded alongside it) adds `make_bench_task_fixture`/`make_bench_raw_jsonl_fixture` following the existing "local fixture helpers layer on top of shared ones" convention. | Do not fork a parallel fixture system — the existing `make_tmp_repo` primitive (throwaway git repo under `BATS_TEST_TMPDIR`, auto-cleaned) is exactly what a benchmark task's worktree needs too. |
| `bench-run.py` ↔ real `claude` binary | `subprocess.run([...], capture_output=True, timeout=…)`, resolved through the `CAIRN_BENCH_CLAUDE_BIN` env-var seam so tests can swap in a stub (Pattern 3). | Mirrors the existing `CAIRN_GBSYNC`/`CAIRN_MAP`/`CAIRN_GATE` seam pattern already documented in `TESTING.md` — do not invent a different override mechanism. |
| `bench-publish.py` ↔ root `README.md` | Regenerates only the content inside `<!-- cairn-bench:generated:start/end -->` markers. | Same idempotent-regeneration contract as `cairn-map.py`'s `<!-- cairn:generated:start/end -->` blocks; extend the existing "Hand-editing a generated block" anti-pattern doc to cover this new marker pair. |
| `.github/workflows/ci.yml` ↔ `benchmarks/scripts/*.py` | The existing `python3 -m py_compile cairn/scripts/*.py cairn/adapters/*.py cairn/capability/scripts/*.py` lint step needs `benchmarks/scripts/*.py` added to its glob; `bats tests/` already picks up new `.bats` files automatically. | No new CI job is required for the stub-based harness tests (they run in the normal, fast, free suite). A **separate**, manually or schedule-triggered workflow is the right place for real, costed `claude -p` runs — never wire real API calls into the default push/PR pipeline. |

## Recommended Build Order

1. **One task's `verify.sh`, proven without any agent involved.** Hand-craft
   a fixture in both a "solved" and an "unsolved" state and assert
   `verify.sh` returns 0/nonzero correctly. This is fully bats-testable today
   and de-risks the one part of the design that determines whether the whole
   benchmark's pass/fail numbers mean anything.
2. **`bench-run.py` against a single baseline (vanilla), single task, single
   repetition — first with the stub seam (bats-tested), then once with a
   real `claude -p` call to validate the JSON schema assumptions against the
   live CLI.** This is the highest-uncertainty integration point (external
   binary, real cost, non-determinism) — validate it early, not last, so any
   surprise in the real JSON payload shape is caught before baselines and
   aggregation are built on top of a wrong assumption.
3. **Extend to multiple baselines** (add `gsd-only`, `cairn`, then the
   competitor) against the same single task — this is where the `--bare` +
   explicit-flags fairness discipline (Pattern 2) gets exercised for real for
   the first time.
4. **Add the repetition loop + `bench-aggregate.py`** once single-run
   collection across all baselines is proven — geometric mean, spread, pass
   rate, all bats-testable against synthetic JSONL fixtures with no live API
   cost.
5. **`bench-report.py` markdown table** — pure function of `aggregated.json`,
   fully bats-testable offline; build and test this before charts since the
   table alone is already a usable, honest artifact.
6. **`bench-report.py` SVG charts** — last, and lowest-risk: rendering is a
   pure function of the same `aggregated.json`, easily developed and tested
   against synthetic data with zero dependency on any live run.
7. **`bench-publish.py` README embed** — final integration step; reuses the
   already-proven generated-marker regeneration pattern from `cairn-map.py`,
   so this is largely wiring, not new design.
8. **Scale the task set** — only after the full pipeline is proven on one
   task, add more tasks (2-4 realistic development tasks spanning the kinds
   of work cairn's workflow actually targets) to make the published
   comparison meaningful rather than anecdotal.

This order deliberately front-loads the two riskiest, hardest-to-fake pieces
— the objective verify contract (step 1) and a real, live `claude -p`
invocation (step 2) — before any statistics or presentation layer is built,
so later phases are refining a design that has already been proven against
reality rather than against assumptions.

## Sources

- [Run Claude Code programmatically — headless mode, `-p`/`--print`, `--bare`, `--output-format json/stream-json`](https://code.claude.com/docs/en/headless) — HIGH confidence, official docs, confirms `--bare` recommendation for CI/scripts, `total_cost_usd` + per-model cost breakdown in JSON output.
- [Claude Code CLI reference — full flag table](https://code.claude.com/docs/en/cli-reference) — HIGH confidence, official docs; confirmed `--max-turns`, `--max-budget-usd`, `--model` (full id pinning), `--plugin-dir`/`--plugin-url`, `--settings`, `--permission-mode`, `--no-session-persistence`, `--session-id`.
- [Agent SDK TypeScript reference — `SDKResultMessage` schema](https://code.claude.com/docs/en/agent-sdk/typescript) — HIGH confidence, official docs; confirmed exact JSON result fields (`duration_ms`, `duration_api_ms`, `num_turns`, `total_cost_usd`, `usage.{input_tokens,output_tokens,cache_creation_input_tokens,cache_read_input_tokens}`, `is_error`, `subtype`, `session_id`).
- [SWE-bench harness reference](https://www.swebench.com/SWE-bench/reference/harness/) and [SWE-bench GitHub](https://github.com/swe-bench/SWE-bench) — MEDIUM-HIGH confidence; Docker-isolated task instances, patch-apply-then-test evaluation, "hidden test suite" as objective pass/fail — pattern basis for `verify.sh`.
- [Terminal-Bench 2.0 / Harbor framework](https://www.harborframework.com/docs/tutorials/running-terminal-bench) and [terminal-bench GitHub](https://github.com/harbor-framework/terminal-bench) — MEDIUM-HIGH confidence; `task.yaml` + Dockerfile + `tests/` (pytest) + `solution.sh` oracle structure — direct analogue for this repo's `task.json`+`fixture/`+`verify.sh` (adapted to JSON per the zero-dep constraint and to no-Docker per this repo's "runs anywhere Claude Code runs" constraint).
- [testing-claude-agent (GitHub, adam-s)](https://github.com/adam-s/testing-claude-agent) — MEDIUM confidence (single community repo, not an official reference); closest direct analogue found — multiple `.claude/` configs as the independent variable (= this design's "baselines"), isolated git worktrees per run, JSON results, separate `report.py`/`analyze.py` aggregation scripts.
- [Token-Harness Optimizer Leaderboard (THOL)](https://pi-infected.github.io/token-harness-optimizer-leaderboard/) — MEDIUM confidence (community benchmark site, methodology stated but not independently audited here); source for the geometric-mean-aggregation-for-cost recommendation, "publish raw results including unfavorable ones," and N=10 repetitions per task as a real-world precedent for repetition count.
- This repo's own `.planning/codebase/TESTING.md` and `.planning/codebase/ARCHITECTURE.md` (generated 2026-07-25) — HIGH confidence, primary source; basis for every "mirrors the existing X pattern" claim above (script/wrapper pairing, exit-code contracts, env-var stub seams, generated-marker regeneration, flat `tests/*.bats` convention, Python-stdlib-only constraint).

---
*Architecture research for: reproducible benchmark harness (CairnGo v1.1)*
*Researched: 2026-07-25*
