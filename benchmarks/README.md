# Benchmarks

Reproducible measurement of agent workflow cost. What exists here today:
`verify.sh` objectivity (a deterministic pass/fail oracle the agent can never
touch); one live schema-validated `claude -p` measurement path
(`bench-run.py` → one JSONL row per run); four pinned baseline manifests
(`vanilla` / `gsd-only` / `cairn` / `competitor-ralph-specum`); full
environment isolation of the measured
claude subprocess (disposable HOME, explicit minimal env); pinned plugin
staging (`stage-plugins.py`); and seeded, reproducible interleaved batch
execution (`bench-matrix.py`, stamping `seed`/`run_order_index` into every
row); repetition (`--reps`, default 5, shuffled across the full
`baseline × rep` cross-product); and deterministic aggregation
(`bench-aggregate.py` → success-gated per-cell medians and 4-way token
decomposition in `aggregated.json`). Repetition and aggregation were built
and proven entirely at $0 via stub/fixture-driven bats — zero live API calls
were spent on them.

## Zero-cost test suite

```bash
bats tests/bench-verify.bats tests/bench-run.bats \
     tests/stage-plugins.bats tests/bench-matrix.bats \
     tests/bench-aggregate.bats
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

Four pinned manifests in `baselines/`, consumed via `bench-run.py
--baseline`:

| manifest | provisioning | what it measures |
|---|---|---|
| `vanilla.json` | no plugins | stock Claude Code — the unassisted control arm |
| `gsd-only.json` | GSD v4.3.1 | GSD's own contribution, before cairn is layered on |
| `cairn.json` | GSD v4.3.1 + context-mode v1.0.169 + cairn (local path) | the full cairn stack — context-mode is a hard dependency of the cairn plugin; excluding it would rig the arm |
| `competitor-ralph-specum.json` | `tzachbon/smart-ralph@v4.0.0` (subpath `plugins/ralph-specum`) | the strongest non-GSD competitor: spec-driven autonomous execution whose `--quick` mode runs genuinely headless via a `PreToolUse` hook denying `AskUserQuestion`. Chosen over `github/spec-kit` and `bmad-code-org/BMAD-METHOD` (both structurally disqualified — no `--plugin-dir`-loadable plugin manifest) and `obra/superpowers` (far larger adoption, but no non-interactive escape hatch around its design-approval gate). Configured strictly from its own documented defaults — see the manifest's `defaults_source` field for the exact vendor docs |

`claude_flags` is byte-identical across all four (`bare`, `max_turns: 8`,
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

A `plugin_dirs` entry may additionally declare `plugin_dir_subpath`: the
path inside the staged repo where the plugin's `.claude-plugin/plugin.json`
actually lives, for plugins not rooted at the top of their repository
(`competitor-ralph-specum` is the first — `ralph-specum` sits at
`plugins/ralph-specum/` inside the `tzachbon/smart-ralph` clone). The key is
optional and backward-compatible: `bench-run.py` joins it onto `staged_path`
when present (`Path(staged_path) / ""` is a pathlib no-op, so every manifest
that omits it resolves exactly as before), and `stage-plugins.py` itself
needed zero changes — it always stages the full repo at `staged_path`
regardless of where the eventual `--plugin-dir` target sits inside it. A
declared subpath whose joined target does not exist on disk dies loud
(exit 2) before any claude subprocess is launched.

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

### Repetitions (`--reps`)

One run per baseline is an anecdote, not a measurement. `bench-matrix.py
--reps <N>` (default **5**) launches N runs per baseline, and every row is
stamped with `--rep-index` so it carries `rep_index` (a JSON integer,
`0..N-1` within its baseline) alongside `seed`/`run_order_index`. The
shuffle is NOT per-rep-round: the single seeded RNG shuffles the full
`baseline × rep` cross-product in one pass, so no baseline's repetitions
run as a contiguous cache-warm block, and the same seed still reproduces
the same full execution order.

## Competitor plugin load-check

The single worst outcome this benchmark could publish is a misconfigured
competitor arm: a `--plugin-dir` pointing somewhere claude silently ignores
would measure "vanilla with dead weight" and report it as the competitor's
result. The wiring is proven at $0 by three `tests/bench-run.bats` tests:

- *"plugin_dir_subpath resolves --plugin-dir to the nested target, never the
  bare staged_path"* — the stub-observed argv shows claude receives the
  joined `<staged_path>/plugins/<plugin>` path, exactly where
  `ralph-specum`'s `plugin.json` lives.
- *"missing plugin_dir_subpath target dies EXIT_USAGE before any row or
  claude launch"* — a broken nested target can never be silently measured.
- *"competitor-ralph-specum manifest pins v4.0.0 with claude_flags/model
  byte-identical to cairn (FAIR-02)"* — the arm's fairness (pin,
  `defaults_source`, identical flags/model) is asserted mechanically by
  `jq -S` diff, not left to inspection.

### Live load-check: PENDING

`ANTHROPIC_API_KEY` was absent from the execution environment when this
phase completed (re-checked live, 2026-07-26), so the one planned live
load-check call was NOT made — deliberately: this check records real cost
and is never silently faked.

When a key becomes available, run exactly:

```bash
claude -p "/help" \
  --plugin-dir benchmarks/plugins/ralph-specum/v4.0.0/plugins/ralph-specum \
  --model claude-haiku-4-5-20251001 --bare --no-session-persistence \
  --permission-mode acceptEdits --output-format json \
  | grep -o 'ralph-specum:[a-z-]*' | sort -u
# Expected (non-exhaustive): ralph-specum:start, ralph-specum:new,
# ralph-specum:research, ralph-specum:requirements, ralph-specum:design,
# ralph-specum:tasks, ralph-specum:implement, ralph-specum:status,
# ralph-specum:help
```

This is a single short `/help` call — no task fixture, no file edits — cheap
enough to run for real the moment a key exists (the same precedent the live
isolation smoke check sets below). Then replace this subsection with the
actually observed `ralph-specum:*` command list, and verify no Anthropic API
key material appears in the captured output before committing it (keys share
a fixed, greppable prefix — scan the output and this file for it).

## Aggregation (`bench-aggregate.py`)

Turns one or more raw JSONL files into a single deterministic
`aggregated.json` of per-`(task, baseline)` cell statistics:

```bash
python3 benchmarks/scripts/bench-aggregate.py \
  --in benchmarks/results/matrix.jsonl \
  --out benchmarks/results/aggregated.json
```

- **CLI contract:** `--in <jsonl>` is repeatable (at least one required);
  `--out <aggregated.json>` is required. Bad args, a missing `--in` file, or
  a missing `--out` parent directory exit 2 before any work.
- **Success gate (belt and braces):** a row only counts toward `n_passed`
  and cost/token statistics when `verify_passed` is `true` AND `is_error` is
  falsy. `verify_passed` alone is deliberately not enough — the two axes are
  independent (see "Observed behavior" below: the committed
  `error_max_turns` row has `verify_passed: true`), and a run that errored
  must never be reported as a cost saving.
- **4-way token decomposition** (`input` / `cache_creation` / `cache_read` /
  `output`): prefers `modelUsage` (summed across models) over the flat
  `usage` dict, because `modelUsage` is what reconciles with
  `total_cost_usd` on the real captured rows — the flat `usage` dict
  under-reports by roughly 30% against the priced token counts. `usage` is
  the fallback for rows without `modelUsage`.
- **Spread methodology:** median + min/max over passing rows'
  `total_cost_usd` is the primary reported spread at small N, with IQR via
  `statistics.quantiles(method="inclusive")` as a secondary column. A cell
  with zero passing rows reports `null` cost/token medians (never a
  fabricated `0`) while keeping `pass_rate`/`n_total`/`n_passed` visible;
  IQR is additionally `null` when fewer than 2 passing costs exist.
- **Required-field rejection:** a line that is not valid JSON, or a row
  missing any of `usage`/`verify_passed`/`baseline_id`/`task_id`, is counted
  in the artifact's top-level `rejected_rows` and excluded from every cell —
  never silently dropped, never a crash. The output's top-level shape is
  `{"cells": {...}, "rejected_rows": N}`, keyed `"<task_id>::<baseline_id>"`.
- **Determinism:** input paths and cell keys are iterated sorted, JSON is
  emitted with `sort_keys` + fixed separators, and nothing in the file is
  time-dependent — identical input always produces a byte-identical
  `aggregated.json`, regardless of `--in` argument order.

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
