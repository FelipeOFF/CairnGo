# Benchmarks

Reproducible measurement of agent workflow cost. What exists here today:
`verify.sh` objectivity (a deterministic pass/fail oracle the agent can never
touch); one live schema-validated `claude -p` measurement path
(`bench-run.py` → one JSONL row per run); three pinned baseline manifests
(`vanilla` / `gsd-only` / `cairn`); full environment isolation of the measured
claude subprocess (disposable HOME, explicit minimal env); pinned plugin
staging (`stage-plugins.py`); and seeded, reproducible interleaved batch
execution (`bench-matrix.py`, stamping `seed`/`run_order_index` into every
row). Explicitly NOT built yet — repetition (N runs per baseline) and
aggregation/medians are Phase 3 scope; nothing in this directory pretends to
do them.

## Zero-cost test suite

```bash
bats tests/bench-verify.bats tests/bench-run.bats \
     tests/stage-plugins.bats tests/bench-matrix.bats
```

Never touches the network. The suite always points `CAIRN_BENCH_CLAUDE_BIN` at
a stub executable that emits canned JSON (schema byte-identical to the real
captured responses in `results/smoke-convert.jsonl` — see "Stub vs. real
schema" below).

## The `CAIRN_BENCH_CLAUDE_BIN` seam

`bench-run.py` resolves the claude binary as: `$CAIRN_BENCH_CLAUDE_BIN` if set,
else the real `claude` on `PATH`. There is no `--live` flag: tests always set
the seam explicitly, so a bare manual invocation IS the live run. That is
precisely how the live runs below were triggered — no special flag existed or
was needed.

## Baselines

Three pinned manifests in `baselines/`, consumed via `bench-run.py
--baseline`:

| manifest | provisioning | what it measures |
|---|---|---|
| `vanilla.json` | no plugins | stock Claude Code — the unassisted control arm |
| `gsd-only.json` | GSD v4.3.1 | GSD's own contribution, before cairn is layered on |
| `cairn.json` | GSD v4.3.1 + context-mode v1.0.169 + cairn (local path) | the full cairn stack — context-mode is a hard dependency of the cairn plugin; excluding it would rig the arm |

`claude_flags` is byte-identical across all three (`bare`, `max_turns: 8`,
`no_session_persistence`, `permission_mode: acceptEdits`), and the manifest
is the sole source of truth for the fully-pinned model id
(`claude-haiku-4-5-20251001`). ONLY `provisioning.plugin_dirs` differs, so
any measured difference between arms is attributable to provisioning alone.

Every measured run is isolated: the claude subprocess receives an explicit
minimal environment — a fresh disposable `HOME`, `PATH`, and
`ANTHROPIC_API_KEY` when present — which REPLACES (never merges with) the
operator's environment. No ambient `~/.claude` config, MCP servers, or hooks
can leak into any arm. The `verify.sh` oracle deliberately keeps the full
inherited environment (it needs PATH-discoverable pytest/bats). With `bare`
set, isolated runs authenticate strictly via `ANTHROPIC_API_KEY` in the
scoped env.

### Staging (`stage-plugins.py`)

Plugin arms never install lazily at run time. `stage-plugins.py --baseline
<manifest>` (or `--all`) materializes every `provisioning.plugin_dirs` entry
BEFORE any measured run: shallow `git clone --branch <ref> --depth 1` of the
pinned tag, the manifest's build commands (`npm ci` / `npm install`), a
`node --check` of every MCP entrypoint the staged plugin declares, then an
atomic rename into `staged_path` with a `.staged-ref` marker making re-runs
idempotent. Staged checkouts live under `plugins/` and are gitignored;
`bench-run.py` fails loud (exit 2) before any spend if a manifest's
`staged_path` is missing.

## Randomized execution order (`bench-matrix.py`)

Running all of one baseline and then all of the next would systematically
favor whichever arm runs while caches are warm. `bench-matrix.py` removes
that bias with a seeded, reproducible interleaving:

```bash
python3 benchmarks/scripts/bench-matrix.py \
  --baselines vanilla,gsd-only,cairn \
  --task benchmarks/tasks/smoke-convert \
  --out benchmarks/results/matrix.jsonl \
  --seed 42
```

- `--seed` is REQUIRED — there is no silent random default. The declared
  baseline names are shuffled with an instance-scoped
  `random.Random(seed)`, so the same seed always reproduces the same
  execution order (auditable and re-runnable by construction).
- Every resolved manifest is validated before ANY run is launched
  (validate-before-spend).
- Every row appended to `--out` carries `seed` and `run_order_index` as
  JSON integers; `run_order_index` values form a contiguous `0..N-1`
  sequence, so each run's exact position within the batch is recorded in
  the data itself.
- A single run's exit code is data about that run, never a batch abort:
  every ordered invocation is always launched, with one report line per
  run and a final summary line.

Both flags are also valid (and optional) on `bench-run.py` directly;
standalone rows carry neither key, keeping single-run and orchestrated rows
distinguishable.

## Live isolation smoke check: PENDING

`ANTHROPIC_API_KEY` was absent from the execution environment when this
phase completed (re-checked live, 2026-07-26), so the one planned live
isolated call was NOT made — deliberately: this check records real cost and
is never silently faked.

The isolation mechanism itself is fully proven at $0: `tests/bench-run.bats`
asserts via an env-observing stub that the claude subprocess sees a
disposable scoped HOME (never the operator's) with planted operator env vars
scrubbed, and `tests/bench-matrix.bats` proves the same holds for every
orchestrated run. The only thing left unproven live is the auth path: that
`bare` + `ANTHROPIC_API_KEY` inside the scoped env completes a real API
round-trip.

When a key becomes available, run exactly:

```bash
python3 benchmarks/scripts/bench-run.py \
  --task benchmarks/tasks/smoke-convert \
  --out benchmarks/results/isolation-smoke.jsonl \
  --baseline benchmarks/baselines/vanilla.json
```

(vanilla only: no plugin dependency, cheapest arm, sufficient to prove the
isolated auth path end-to-end). Then replace this subsection with the
observed `total_cost_usd` / `is_error` / `terminal_reason` (same
client-side-estimate caveat as below), and verify no Anthropic API key
material appears in the committed row before committing it (keys share a
fixed, greppable prefix — scan the row and this file for it).

## The live runs and their observed cost

```bash
python3 benchmarks/scripts/bench-run.py \
  --task benchmarks/tasks/smoke-convert \
  --out benchmarks/results/smoke-convert.jsonl
```

(As invoked on 2026-07-25, before `--baseline` became required; today the
same run additionally needs `--baseline benchmarks/baselines/vanilla.json`.)

Two committed rows in `results/smoke-convert.jsonl`, captured 2026-07-25:

| subtype | is_error | num_turns | total_cost_usd | verify_passed |
|---|---|---|---|---|
| `error_max_turns` (cap 5) | true | 6 | 0.1223481 | **true** |
| `success` (cap 8) | false | 6 | 0.167407 | true |

**Caveat, repeated wherever cost is reported in this repo:** `total_cost_usd`
is Anthropic's own client-side estimate, not authoritative billing data. Use
it for insight and approximate budgeting, never as an invoice.

**Total spend to validate this pipeline: ~$2.88.** Full transparency breakdown:
~$1.29 on direct auth/schema validation from an operator's global environment
(which dragged in ~62k cache-creation tokens of ambient context — living
evidence of the "home-field advantage" contamination that isolated runs must
eliminate); ~$1.30 on a row lost to a missing-output-directory bug (the guard
in `bench-run.py` now fails fast before any spend); $0.1223481 + $0.167407 on
the two committed rows.

## Observed behavior (recorded for future phases)

- **`verify_passed` and `is_error` are independent axes.** The
  `error_max_turns` row carries a fixture the agent had ALREADY solved before
  hitting the turn cap. Cost/outcome metrics must treat "run terminated
  cleanly" and "task actually solved" as separate columns — conflating them
  corrupts any success-rate number built on top.
- **Exit codes:** the `bench-run.py` process exited 0 on both live runs (by
  contract — a run's outcome is a data column, not a harness failure). Both
  live responses, success AND error subtype, were parseable JSON on stdout
  with `usage`/`total_cost_usd` populated, vindicating the
  parse-regardless-of-returncode design.
- **`subtype` is not a success signal.** An unauthenticated call returns
  `subtype:"success"` with `is_error:true`, `terminal_reason:"api_error"`,
  zero cost/usage. Read `is_error`/`terminal_reason`, never `subtype` alone.
- **`--bare` skips claude.ai OAuth.** Verified live: with `--bare`, the CLI
  reports "Not logged in" even on a logged-in machine and requires an API key
  via env/`--settings`. All three baseline manifests now set `bare: true`, so
  isolated runs authenticate strictly via `ANTHROPIC_API_KEY` in the scoped
  env.
- **Model ids must be fully pinned.** The bare alias `claude-haiku` was
  rejected by the API; the baseline manifest carries the full id
  (`claude-haiku-4-5-20251001`) and is the sole source of truth for model
  pinning (`task.json` no longer declares a model).
- **`num_turns` can exceed `--max-turns`** (observed 6 under a cap of 5 — the
  limit-hitting turn is counted).
- **`--permission-mode acceptEdits` gates Bash for real:** both rows carry
  `permission_denials` for the agent's attempted `python -m pytest`/`unittest`
  commands. Edits landed; arbitrary commands did not.

## Stub vs. real schema

The live responses carry many fields absent from the published docs
(`terminal_reason`, `stop_reason`, `uuid`, `modelUsage`, `permission_denials`,
`fast_mode_*`, `ttft_ms`, `ttft_stream_ms`, nested
`usage.cache_creation`/`server_tool_use`/`service_tier`/`iterations`, ...).
Drift WAS found between the pre-live canned stub payloads and the real
responses; `tests/bench-run.bats` was rebuilt so its payloads are key-for-key
identical to the captured rows, and the harness passes every field through
untouched.
