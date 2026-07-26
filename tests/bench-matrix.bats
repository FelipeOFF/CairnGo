#!/usr/bin/env bats
# bench-matrix.bats — exercises the seeded interleaving contract: bench-run.py's
# optional --seed/--run-order-index row-provenance stamps, and bench-matrix.py's
# deterministic shuffled orchestration of declared baseline names — all at zero
# API cost via the CAIRN_BENCH_CLAUDE_BIN stub seam. Never invokes the real
# claude binary.
#
# Assertion style note (same as bench-run.bats): a failing `[[ ]]` or `! cmd`
# mid-test does NOT fail a bats test on this bash, so positive checks use
# `run jq -e` / grep -qF and negative checks assert via jq predicates.

load 'helpers'

BENCH_SCRIPTS_DIR="$CAIRN_REPO_ROOT/benchmarks/scripts"
BENCH_TASKS_DIR="$CAIRN_REPO_ROOT/benchmarks/tasks"
BENCH_BASELINES_DIR="$CAIRN_REPO_ROOT/benchmarks/baselines"

# make_fixture_baselines — write alpha/beta/gamma.json test-only manifests into
# $BATS_TEST_TMPDIR/baselines. claude_flags mirrors vanilla.json byte-for-byte;
# only "name" differs; provisioning is empty. These fixtures live and die with
# the test — the committed benchmarks/baselines/ stays exactly Plan 02-01's
# three real manifests.
make_fixture_baselines() {
  FIXTURE_BASELINES_DIR="$BATS_TEST_TMPDIR/baselines"
  mkdir -p "$FIXTURE_BASELINES_DIR"
  local name
  for name in alpha beta gamma; do
    cat > "$FIXTURE_BASELINES_DIR/$name.json" <<EOF
{
  "name": "$name",
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
EOF
  done
}

@test "bench-run.py stamps --seed/--run-order-index into the row as JSON integers" {
  make_env_asserting_claude_stub
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-run.py" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --baseline "$BENCH_BASELINES_DIR/vanilla.json" \
      --out "$BATS_TEST_TMPDIR/raw-seeded.jsonl" \
      --seed 42 --run-order-index 3
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$BATS_TEST_TMPDIR/raw-seeded.jsonl")" -eq 1 ]
  # Integers, not strings: jq's == is type-strict only across scalars, so the
  # explicit type checks prove "42"/"3" (strings) would fail here.
  run jq -e '(.seed == 42) and ((.seed | type) == "number")
             and (.run_order_index == 3)
             and ((.run_order_index | type) == "number")' \
    "$BATS_TEST_TMPDIR/raw-seeded.jsonl"
  [ "$status" -eq 0 ]
}

@test "bench-run.py without --seed/--run-order-index emits a row with neither key" {
  # Regression guard for every Plan 02-01 invocation shape: the new flags are
  # strictly optional and absent flags leave the row schema untouched.
  make_env_asserting_claude_stub
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-run.py" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --baseline "$BENCH_BASELINES_DIR/vanilla.json" \
      --out "$BATS_TEST_TMPDIR/raw-unseeded.jsonl"
  [ "$status" -eq 0 ]
  run jq -e '(has("seed") | not) and (has("run_order_index") | not)' \
    "$BATS_TEST_TMPDIR/raw-unseeded.jsonl"
  [ "$status" -eq 0 ]
}

@test "bench-matrix.py runs each declared baseline exactly once with seed stamped and contiguous run_order_index" {
  make_env_asserting_claude_stub
  make_fixture_baselines
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-matrix.py" \
      --baselines alpha,beta,gamma \
      --baselines-dir "$FIXTURE_BASELINES_DIR" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --out "$BATS_TEST_TMPDIR/matrix.jsonl" \
      --seed 7 --reps 1
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$BATS_TEST_TMPDIR/matrix.jsonl")" -eq 3 ]
  # run_order_index values are exactly the set {0,1,2}: contiguous, no gaps,
  # no duplicates.
  run jq -s -e 'map(.run_order_index) | sort == [0, 1, 2]' \
    "$BATS_TEST_TMPDIR/matrix.jsonl"
  [ "$status" -eq 0 ]
  # Every row carries seed 7, and each baseline appears exactly once.
  run jq -s -e '(map(.seed) | unique == [7])
                and (map(.baseline_id) | sort == ["alpha", "beta", "gamma"])' \
    "$BATS_TEST_TMPDIR/matrix.jsonl"
  [ "$status" -eq 0 ]
}

@test "the same seed yields a byte-identical baseline_id order across two invocations" {
  make_env_asserting_claude_stub
  make_fixture_baselines
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-matrix.py" \
      --baselines alpha,beta,gamma \
      --baselines-dir "$FIXTURE_BASELINES_DIR" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --out "$BATS_TEST_TMPDIR/order_a.jsonl" \
      --seed 20260726 --reps 1
  [ "$status" -eq 0 ]
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-matrix.py" \
      --baselines alpha,beta,gamma \
      --baselines-dir "$FIXTURE_BASELINES_DIR" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --out "$BATS_TEST_TMPDIR/order_b.jsonl" \
      --seed 20260726 --reps 1
  [ "$status" -eq 0 ]
  run diff \
    <(jq -r '.baseline_id' "$BATS_TEST_TMPDIR/order_a.jsonl") \
    <(jq -r '.baseline_id' "$BATS_TEST_TMPDIR/order_b.jsonl")
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "bench-matrix.py --reps 5 interleaves the full baseline x rep cross-product, stamping rep_index and preserving run_order_index contiguity" {
  make_env_asserting_claude_stub
  make_fixture_baselines
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-matrix.py" \
      --baselines alpha,beta,gamma \
      --baselines-dir "$FIXTURE_BASELINES_DIR" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --out "$BATS_TEST_TMPDIR/matrix-reps.jsonl" \
      --seed 7 --reps 5
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$BATS_TEST_TMPDIR/matrix-reps.jsonl")" -eq 15 ]
  # run_order_index spans the full cross-product contiguously: exactly the
  # set {0..14}, no gaps, no duplicates.
  run jq -s -e 'map(.run_order_index) | sort ==
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]' \
    "$BATS_TEST_TMPDIR/matrix-reps.jsonl"
  [ "$status" -eq 0 ]
  # Every baseline received exactly reps {0,1,2,3,4}, each stamped once.
  run jq -s -e 'group_by(.baseline_id)
                | all(.[]; (map(.rep_index) | sort) == [0, 1, 2, 3, 4])' \
    "$BATS_TEST_TMPDIR/matrix-reps.jsonl"
  [ "$status" -eq 0 ]
  # Genuine interleaving: a baseline whose 5 run positions span exactly 4
  # would be a fully contiguous block of 5 — must be false for every
  # baseline at seed 7 (verified positions: alpha [0,5,9,10,13],
  # beta [3,7,8,12,14], gamma [1,2,4,6,11]).
  run jq -s -e 'group_by(.baseline_id)
                | all(.[]; (map(.run_order_index) | (max - min)) != 4)' \
    "$BATS_TEST_TMPDIR/matrix-reps.jsonl"
  [ "$status" -eq 0 ]
}

@test "bench-matrix.py omits --reps and still defaults to 5" {
  # The default must be live (METR-01's N=5), not merely accepted by argparse.
  make_env_asserting_claude_stub
  make_fixture_baselines
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-matrix.py" \
      --baselines alpha,beta,gamma \
      --baselines-dir "$FIXTURE_BASELINES_DIR" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --out "$BATS_TEST_TMPDIR/matrix-default.jsonl" \
      --seed 7
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$BATS_TEST_TMPDIR/matrix-default.jsonl")" -eq 15 ]
}

@test "orchestrated runs preserve per-run isolation against the real vanilla/gsd-only manifests" {
  if [ ! -d "$CAIRN_REPO_ROOT/benchmarks/plugins/gsd/v4.3.1" ]; then
    skip "benchmarks/plugins/gsd/v4.3.1 not staged"
  fi
  make_env_asserting_claude_stub
  # gsd-only.json's staged_path is repo-root-relative: pin the cwd so it
  # resolves regardless of where bats was invoked from.
  cd "$CAIRN_REPO_ROOT"
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    python3 "$BENCH_SCRIPTS_DIR/bench-matrix.py" \
      --baselines vanilla,gsd-only \
      --baselines-dir "$BENCH_BASELINES_DIR" \
      --task "$BENCH_TASKS_DIR/smoke-convert" \
      --out "$BATS_TEST_TMPDIR/matrix-real.jsonl" \
      --seed 1 --reps 1
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$BATS_TEST_TMPDIR/matrix-real.jsonl")" -eq 2 ]
  # The same isolation contract Plan 02-01 proved for a single run holds for
  # BOTH orchestrated rows: each stub observed a disposable scoped HOME, never
  # the operator's real one.
  run jq -s -e --arg home "$HOME" \
    'all(.[]; .stub_observed_home != $home
              and (.stub_observed_home | contains("cairn-bench-home-")))' \
    "$BATS_TEST_TMPDIR/matrix-real.jsonl"
  [ "$status" -eq 0 ]
}
