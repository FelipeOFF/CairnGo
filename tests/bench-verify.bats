#!/usr/bin/env bats
# bench-verify.bats — exercises verify.sh's exit-code contract for the
# smoke-convert fixture: proves HARN-01's "exit code = pass/fail, never agent
# self-report" property with zero agent or API involvement. verify.sh lives at
# the task-dir root, receives the workdir path as its sole argument, and is
# never staged inside the workdir it checks.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so substring checks use grep -qF and file-absence
# checks use an explicit `[ ! -f ... ]`.

load 'helpers'

BENCH_TASKS_DIR="$CAIRN_REPO_ROOT/benchmarks/tasks"

@test "verify.sh fails against the unsolved fixture, zero agent involvement" {
  cp -r "$BENCH_TASKS_DIR/smoke-convert/fixture" "$BATS_TEST_TMPDIR/unsolved"
  run bash "$BENCH_TASKS_DIR/smoke-convert/verify.sh" "$BATS_TEST_TMPDIR/unsolved"
  [ "$status" -ne 0 ]
}

@test "verify.sh passes against a hand-solved fixture" {
  cp -r "$BENCH_TASKS_DIR/smoke-convert/fixture" "$BATS_TEST_TMPDIR/solved"
  cat > "$BATS_TEST_TMPDIR/solved/convert.py" <<'EOF'
"""Temperature conversion utilities."""


def celsius_to_fahrenheit(c):
    return c * 9 / 5 + 32
EOF
  run bash "$BENCH_TASKS_DIR/smoke-convert/verify.sh" "$BATS_TEST_TMPDIR/solved"
  [ "$status" -eq 0 ]
}

@test "verify.sh is never staged inside the workdir it checks" {
  cp -r "$BENCH_TASKS_DIR/smoke-convert/fixture" "$BATS_TEST_TMPDIR/workdir"
  run bash "$BENCH_TASKS_DIR/smoke-convert/verify.sh" "$BATS_TEST_TMPDIR/workdir"
  [ ! -f "$BATS_TEST_TMPDIR/workdir/verify.sh" ]
}
