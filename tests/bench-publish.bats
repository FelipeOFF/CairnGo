#!/usr/bin/env bats
# bench-publish.bats — proves bench-publish.py's marker-scoped regeneration
# contract against tests/fixtures/publish-aggregate.json: only the content
# between the generated markers changes; every byte outside them survives
# byte-identical; a double run with identical inputs is byte-identical
# (idempotent, write-only-when-changed); a target without markers gets the
# block appended, never destroyed; --check detects staleness (exit 3 + diff)
# without writing. All tests run against TEMP COPIES under $BATS_TEST_TMPDIR:
# the real repo-root BENCHMARKS.md and README.md are never written to.
# Zero API cost; never invokes the claude binary at all.
#
# Assertion style note (same as bench-run.bats): a failing `[[ ]]` or `! cmd`
# mid-test does NOT fail a bats test on this bash, so positive checks use
# `run` + `[ "$status" -eq N ]`, plain `[ ]` brackets, and grep via `run`
# or a piped `grep -qF` whose failure is a plain command failure.

load 'helpers'

BENCH_SCRIPTS_DIR="$CAIRN_REPO_ROOT/benchmarks/scripts"
FIXTURES_DIR="$CAIRN_REPO_ROOT/tests/fixtures"
PUBLISH="$BENCH_SCRIPTS_DIR/bench-publish.py"

# Copy the real committed publication surfaces into the test tmpdir; every
# test runs bench-publish.py against these copies, never the repo files.
copy_real_targets() {
  cp "$CAIRN_REPO_ROOT/BENCHMARKS.md" "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  cp "$CAIRN_REPO_ROOT/README.md" "$BATS_TEST_TMPDIR/README.md"
}

# Everything OUTSIDE the benchmarks marker block (block itself deleted), so
# a pre/post diff proves the surrounding prose survived byte-identical.
outside_benchmarks() {
  sed '/<!-- cairn:generated:benchmarks:start -->/,/<!-- cairn:generated:benchmarks:end -->/d' "$1"
}

# Same, for the README teaser marker block.
outside_teaser() {
  sed '/<!-- cairn:generated:benchmarks-teaser:start -->/,/<!-- cairn:generated:benchmarks-teaser:end -->/d' "$1"
}

@test "missing --in, nonexistent --in, malformed --in, missing cells key, and missing --benchmarks target all die EXIT_USAGE naming the flag" {
  copy_real_targets
  run python3 "$PUBLISH" --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--in'
  run python3 "$PUBLISH" --in "$BATS_TEST_TMPDIR/does-not-exist.json" \
    --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--in'
  echo 'this is not json {{{' > "$BATS_TEST_TMPDIR/bad.json"
  run python3 "$PUBLISH" --in "$BATS_TEST_TMPDIR/bad.json" \
    --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--in'
  printf '{"rejected_rows":0}\n' > "$BATS_TEST_TMPDIR/nocells.json"
  run python3 "$PUBLISH" --in "$BATS_TEST_TMPDIR/nocells.json" \
    --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF 'cells'
  run python3 "$PUBLISH" --in "$FIXTURES_DIR/publish-aggregate.json" \
    --benchmarks "$BATS_TEST_TMPDIR/no-such-file.md"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--benchmarks'
}

@test "table correctness: exact fixture values in sorted cell-key order inside the markers, every byte outside byte-identical" {
  copy_real_targets
  outside_benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md" \
    > "$BATS_TEST_TMPDIR/outside-before.txt"
  run python3 "$PUBLISH" --in "$FIXTURES_DIR/publish-aggregate.json" \
    --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md" --label "fixture run"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF 'wrote'
  run grep -qF '| smoke-convert | cairn | smoke | 5/5 (100%) | $0.1618 |' \
    "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 0 ]
  run grep -qF '| smoke-convert | vanilla | smoke | 4/5 (80%) | $0.1223 |' \
    "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 0 ]
  run grep -qF '| microedit-greet | cairn | honest-non-win | 0/5 (0%) | n/a |' \
    "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 0 ]
  # Sorted "task_id::baseline_id" key order: microedit-greet row comes first
  # (3rd pipe-line inside the block, after header + separator).
  run bash -c "sed -n '/<!-- cairn:generated:benchmarks:start -->/,/<!-- cairn:generated:benchmarks:end -->/p' '$BATS_TEST_TMPDIR/BENCHMARKS.md' | grep '^|' | sed -n 3p"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF 'microedit-greet'
  outside_benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md" \
    > "$BATS_TEST_TMPDIR/outside-after.txt"
  run diff "$BATS_TEST_TMPDIR/outside-before.txt" \
    "$BATS_TEST_TMPDIR/outside-after.txt"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "empty cells renders the explicit pending line, never a bare or headerless table" {
  copy_real_targets
  printf '{"cells":{},"rejected_rows":0}\n' > "$BATS_TEST_TMPDIR/empty.json"
  run python3 "$PUBLISH" --in "$BATS_TEST_TMPDIR/empty.json" \
    --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md" --label "empty run"
  [ "$status" -eq 0 ]
  run grep -qF '_No cells in aggregated.json — pending first collection._' \
    "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 0 ]
  run grep -qF '| Task | Baseline |' "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 1 ]
}

@test "running twice with identical --in/--label is byte-identical (write-only-when-changed idempotence)" {
  copy_real_targets
  run python3 "$PUBLISH" --in "$FIXTURES_DIR/publish-aggregate.json" \
    --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md" --label "fixture run"
  [ "$status" -eq 0 ]
  cp "$BATS_TEST_TMPDIR/BENCHMARKS.md" "$BATS_TEST_TMPDIR/after-run1.md"
  run python3 "$PUBLISH" --in "$FIXTURES_DIR/publish-aggregate.json" \
    --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md" --label "fixture run"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF 'unchanged'
  run diff "$BATS_TEST_TMPDIR/after-run1.md" "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
