# Benchmarks

Public evidence for cairn's cost and outcome claims, methodology first.
Every mechanism that will ever produce a published number here is
documented, tested and committed before any number exists. The full
mechanics live in [benchmarks/README.md](benchmarks/README.md); this
document is the publication surface those mechanics regenerate.

## Methodology

**Harness.** Every measured run is one `bench-run.py` invocation of
`claude -p --output-format json`: one prompt, one schema-validated JSON
response, one appended JSONL row carrying cost, token usage, turn count,
error state and the verification outcome. Batches run through
`bench-matrix.py` with a seeded, reproducible interleaving of the full
`baseline × rep` cross-product, so no arm executes as a contiguous
cache-warm block; see
[randomized execution order](benchmarks/README.md#randomized-execution-order-bench-matrixpy).

**Environment isolation.** The measured claude subprocess never sees the
operator's machine: each run gets a fresh throwaway working copy of the
task fixture and a disposable scoped `HOME` with an explicit minimal
environment that replaces (never merges with) the operator's, and `--bare`
skips claude.ai OAuth so authentication happens strictly via
`ANTHROPIC_API_KEY` inside that scoped environment; see
[Baselines](benchmarks/README.md#baselines).

**Baselines.** Four pinned manifests: `vanilla` (stock Claude Code, the
control arm), `gsd-only`, `cairn` (the full stack), and
`competitor-ralph-specum` (the strongest non-GSD competitor able to run
genuinely headless). `claude_flags` and the fully pinned model id are
byte-identical across all four; ONLY `provisioning.plugin_dirs` differs, so
any measured difference between arms is attributable to provisioning alone;
see [Baselines](benchmarks/README.md#baselines).

**Success gating.** A run counts as a pass only when `verify_passed` is
`true` AND `is_error` is falsy. The two axes are independent on real
captured rows (a run can hit the turn cap with the task already solved), so
a run that errored never counts as a success and never contributes to any
cost statistic; see
[Aggregation](benchmarks/README.md#aggregation-bench-aggregatepy).

**Task corpus.** Six tasks across six pre-declared categories (smoke,
bugfix, feature, refactor, honest-non-win, long-horizon), committed before
any comparative result exists. The `honest-non-win` category
(`microedit-greet`) is deliberate: cairn is expected to lose or tie on a
one-line edit, because a benchmark that shows only wins reads as
cherry-picked; see [Task corpus](benchmarks/README.md#task-corpus). The
default repetition count (5 per cell) is calibrated by the
[variance pilot](benchmarks/README.md#variance-pilot-corp-01) before the
full matrix ever runs.

**Cost.** The full matrix is `6 tasks × 4 arms × 5 reps = 120 runs`.
Summing the per-category upper-bound estimates with ~30% headroom gives the
declared ceiling for one full 120-run matrix pass: ~$40. The per-category
estimates, their derivation from the two real captured rows, and the
standing caveat that `total_cost_usd` is a client-side estimate (never
authoritative billing data) all live in the
[Cost model](benchmarks/README.md#cost-model).

## Raw data

Two rows exist today, captured 2026-07-25 in
[benchmarks/results/smoke-convert.jsonl](benchmarks/results/smoke-convert.jsonl).
They are schema-validation runs, not comparison results, and are never
counted toward any published comparison:

- they predate the `--baseline` flag becoming required, so neither row
  carries a `baseline_id`;
- they cover a single task with no repetition and no other arms, which
  cannot support any comparative statement;
- `bench-aggregate.py` in fact rejects both rows today for the missing
  `baseline_id` (a behavior pinned by `tests/bench-aggregate.bats`).

All future raw JSONL and every `aggregated.json` derived from it land under
`benchmarks/results/` and are committed alongside the results they back.

## Results

<!-- cairn:generated:benchmarks:start -->
**Pending first collection.** No full benchmark run has been executed yet:
collection is blocked on an `ANTHROPIC_API_KEY`, and this repository does
not publish numbers it has not measured. This section is regenerated
automatically by `benchmarks/scripts/bench-publish.py` from
`benchmarks/results/aggregated.json` the moment real data exists; anyone
can reproduce it with the command in Reproduction below.

Shipping the complete harness, corpus and methodology before any result is
the point, not an apology: a benchmark whose mechanics are committed and
testable in advance cannot be quietly re-tuned after the numbers arrive.
<!-- cairn:generated:benchmarks:end -->

## Reproduction

One command reproduces the full matrix:

```bash
benchmarks/scripts/bench-all.sh --yes
```

Without an explicit `--yes` the default is `--dry-run`: an always-safe, $0,
print-only mode that shows exactly what would run, never invokes any
downstream script, and never spends anything. The full 120-run matrix
carries the same declared cost ceiling as the Cost model above: ~$40.
Nothing runs live without explicitly accepting that ceiling first.

## Changelog

Every change to the corpus, the methodology, or the reproduction command
lands here as a dated entry, never as a silent edit after results exist.

- **2026-07-26**: task corpus pre-declared and committed (6 tasks across 6
  categories, including the deliberate honest-non-win task
  `microedit-greet`) before any comparative result exists.
- **2026-07-26**: this document created: methodology, raw-data labeling,
  generated Results section (explicitly pending first collection),
  reproduction command and cost ceiling.
