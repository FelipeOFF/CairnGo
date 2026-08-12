#!/usr/bin/env bats
# bench-aggregate.bats — exercises the deterministic JSONL -> aggregated.json
# statistics layer: required-field/malformed-line rejection (counted in the
# artifact, never a crash), belt-and-braces success gating (verify_passed AND
# NOT is_error), modelUsage-preferred 4-way token decomposition with flat-usage
# fallback, multi-file order-independence, byte-identical double-run
# determinism, and CLI usage errors — all against static fixtures, zero API
# cost. Never invokes the claude binary at all.
#
# Assertion style note (same as bench-run.bats): a failing `[[ ]]` or `! cmd`
# mid-test does NOT fail a bats test on this bash, so positive checks use
# `run jq -e` / grep -qF and negative checks assert via jq predicates.

load 'helpers'

BENCH_SCRIPTS_DIR="$CAIRN_REPO_ROOT/benchmarks/scripts"
FIXTURES_DIR="$CAIRN_REPO_ROOT/tests/fixtures"

@test "rejects real historical rows missing baseline_id, and malformed/incomplete synthetic rows — all counted, never a crash" {
  # The two committed real rows predate baseline_id stamping — they ARE the
  # required-field rejection fixture, used unmodified.
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$CAIRN_REPO_ROOT/benchmarks/results/smoke-convert.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-real.json"
  [ "$status" -eq 0 ]
  run jq -e '.rejected_rows == 2 and (.cells | length) == 0' \
    "$BATS_TEST_TMPDIR/agg-real.json"
  [ "$status" -eq 0 ]
  # Synthetic mix: 1 well-formed row + 1 non-JSON garbage line + 1 row missing
  # baseline_id — the garbage line must not abort the well-formed row's load.
  cat > "$BATS_TEST_TMPDIR/broken.jsonl" <<'EOF'
{"task_id": "smoke-convert", "baseline_id": "alpha", "verify_passed": true, "is_error": false, "total_cost_usd": 0.10, "usage": {"input_tokens": 1, "cache_creation_input_tokens": 2, "cache_read_input_tokens": 3, "output_tokens": 4}}
this is not json at all {{{
{"task_id": "smoke-convert", "verify_passed": true, "is_error": false, "total_cost_usd": 0.11, "usage": {"input_tokens": 5, "cache_creation_input_tokens": 6, "cache_read_input_tokens": 7, "output_tokens": 8}}
EOF
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$BATS_TEST_TMPDIR/broken.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-broken.json"
  [ "$status" -eq 0 ]
  run jq -e '.rejected_rows == 2 and (.cells | length) == 1' \
    "$BATS_TEST_TMPDIR/agg-broken.json"
  [ "$status" -eq 0 ]
}

@test "success-gated 4-way decomposition: belt-and-braces gating, pass_rate-zero cell, modelUsage-preferred with usage fallback — exact values" {
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$FIXTURES_DIR/aggregate-gating-a.jsonl" \
    --in "$FIXTURES_DIR/aggregate-gating-b.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-gating.json"
  [ "$status" -eq 0 ]
  run jq -e '
    .rejected_rows == 0
    and (.cells | length) == 3
    and .cells["smoke-convert::alpha"].n_total == 5 and .cells["smoke-convert::alpha"].n_passed == 4
    and .cells["smoke-convert::alpha"].pass_rate == 0.8
    and .cells["smoke-convert::alpha"].cost_median == 0.13 and .cells["smoke-convert::alpha"].cost_min == 0.1 and .cells["smoke-convert::alpha"].cost_max == 0.16
    and .cells["smoke-convert::alpha"].cost_iqr == 0.030000000000000027
    and .cells["smoke-convert::alpha"].tokens.input_sum == 52 and .cells["smoke-convert::alpha"].tokens.input_median == 13
    and .cells["smoke-convert::alpha"].tokens.cache_creation_sum == 460 and .cells["smoke-convert::alpha"].tokens.cache_creation_median == 115
    and .cells["smoke-convert::alpha"].tokens.cache_read_sum == 860 and .cells["smoke-convert::alpha"].tokens.cache_read_median == 215
    and .cells["smoke-convert::alpha"].tokens.output_sum == 230 and .cells["smoke-convert::alpha"].tokens.output_median == 57.5
    and .cells["smoke-convert::beta"].n_total == 3 and .cells["smoke-convert::beta"].n_passed == 1
    and .cells["smoke-convert::beta"].pass_rate == (1/3)
    and .cells["smoke-convert::beta"].cost_median == 0.25 and .cells["smoke-convert::beta"].cost_iqr == null
    and .cells["smoke-convert::beta"].tokens.input_sum == 20 and .cells["smoke-convert::beta"].tokens.cache_creation_sum == 150
    and .cells["smoke-convert::gamma"].n_total == 2 and .cells["smoke-convert::gamma"].n_passed == 0
    and .cells["smoke-convert::gamma"].pass_rate == 0
    and .cells["smoke-convert::gamma"].cost_median == null and .cells["smoke-convert::gamma"].tokens.input_median == null
  ' "$BATS_TEST_TMPDIR/agg-gating.json"
  [ "$status" -eq 0 ]
}

@test "multiple --in files combine identically regardless of argument order" {
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$FIXTURES_DIR/aggregate-gating-a.jsonl" \
    --in "$FIXTURES_DIR/aggregate-gating-b.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-ab.json"
  [ "$status" -eq 0 ]
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$FIXTURES_DIR/aggregate-gating-b.jsonl" \
    --in "$FIXTURES_DIR/aggregate-gating-a.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-ba.json"
  [ "$status" -eq 0 ]
  run diff "$BATS_TEST_TMPDIR/agg-ab.json" "$BATS_TEST_TMPDIR/agg-ba.json"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "running twice against identical input yields byte-identical aggregated.json" {
  # A TRUE byte-for-byte diff — no jq -S normalization: the aggregator itself
  # must emit sort_keys + fixed separators, with no timestamps anywhere.
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$FIXTURES_DIR/aggregate-gating-a.jsonl" \
    --in "$FIXTURES_DIR/aggregate-gating-b.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-run1.json"
  [ "$status" -eq 0 ]
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$FIXTURES_DIR/aggregate-gating-a.jsonl" \
    --in "$FIXTURES_DIR/aggregate-gating-b.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-run2.json"
  [ "$status" -eq 0 ]
  run diff "$BATS_TEST_TMPDIR/agg-run1.json" "$BATS_TEST_TMPDIR/agg-run2.json"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "mixing real historical rows with synthetic rows: real rows rejected, synthetic cells unaffected" {
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$FIXTURES_DIR/aggregate-gating-a.jsonl" \
    --in "$FIXTURES_DIR/aggregate-gating-b.jsonl" \
    --in "$CAIRN_REPO_ROOT/benchmarks/results/smoke-convert.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-mixed.json"
  [ "$status" -eq 0 ]
  run jq -e '.rejected_rows == 2 and (.cells | length) == 3
             and .cells["smoke-convert::alpha"].cost_median == 0.13' \
    "$BATS_TEST_TMPDIR/agg-mixed.json"
  [ "$status" -eq 0 ]
}

@test "missing --in or --out dies EXIT_USAGE naming the flag" {
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --out "$BATS_TEST_TMPDIR/agg-no-in.json"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--in'
  [ ! -e "$BATS_TEST_TMPDIR/agg-no-in.json" ]
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$FIXTURES_DIR/aggregate-gating-a.jsonl"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--out'
}

@test "aggregated cells surface the source task's category, null when rows carry none" {
  cat > "$BATS_TEST_TMPDIR/category.jsonl" <<'EOF'
{"task_id": "microedit-greet", "baseline_id": "alpha", "category": "honest-non-win", "verify_passed": true, "is_error": false, "total_cost_usd": 0.05, "usage": {"input_tokens": 1, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 1}}
{"task_id": "smoke-convert", "baseline_id": "alpha", "verify_passed": true, "is_error": false, "total_cost_usd": 0.12, "usage": {"input_tokens": 1, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 1}}
EOF
  run bash "$BENCH_SCRIPTS_DIR/bench-aggregate.sh" \
    --in "$BATS_TEST_TMPDIR/category.jsonl" \
    --out "$BATS_TEST_TMPDIR/agg-category.json"
  [ "$status" -eq 0 ]
  run jq -e '.cells["microedit-greet::alpha"].category == "honest-non-win"
             and .cells["smoke-convert::alpha"].category == null' \
    "$BATS_TEST_TMPDIR/agg-category.json"
  [ "$status" -eq 0 ]
}
