# Benchmarks

Reproducible measurement of agent workflow cost. What exists here today:
`verify.sh` objectivity (a deterministic pass/fail oracle the agent can never
touch) and one live schema-validated `claude -p` measurement path
(`bench-run.py` → one JSONL row per run). Explicitly NOT built yet — baselines,
environment isolation (HOME override, worktrees), repetition, and aggregation
are Phase 2/3 scope; nothing in this directory pretends to do them.

## Zero-cost test suite

```bash
bats tests/bench-verify.bats tests/bench-run.bats
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

## The live runs and their observed cost

```bash
python3 benchmarks/scripts/bench-run.py \
  --task benchmarks/tasks/smoke-convert \
  --out benchmarks/results/smoke-convert.jsonl
```

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
  via env/`--settings`. `bench-run.py` therefore omits it; any future isolated
  baseline that wants `--bare` must provide `ANTHROPIC_API_KEY`.
- **Model ids must be fully pinned.** The bare alias `claude-haiku` was
  rejected by the API; `task.json` now requires a full id
  (`claude-haiku-4-5-20251001`).
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
