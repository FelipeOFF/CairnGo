#!/usr/bin/env bats
# cairn-test.bats — exercises the suite runner's CLI contract
# (cairn-test.py / the cairn-test.sh wrapper): the job-count precedence, the
# detection that happens BEFORE the command is composed, and the exit code
# that comes back out of bats untranslated.
#
# THE SEAM, AND WHY IT EXISTS. Every test here goes through
# `--print-command` or through a STUB `bats` on a stub PATH. Not one of them
# runs the real suite, because a bats file that runs bats is a trap: the
# nested run inherits this run's own parallelism and the failure mode is a
# silent hang, not an error. `--print-command` is what makes the interesting
# behavior (job count, precedence, whether `-j` was composed at all)
# observable without ever starting a suite.
#
# THE OTHER SEAM. Both prerequisites bats needs for `-j` are PATH lookups
# (the parallel binary, and flock-or-shlock), so a stub directory that is the
# WHOLE PATH controls them exactly. The stub dir lives under
# $BATS_TEST_TMPDIR, which bats makes per test, so a stub can never leak from
# one test into the next.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so every check is a plain `[ ]` against a
# `run`-captured $status/$output, substring checks use grep -qF, and negative
# checks use refute_in_output.
#
# No bd, no network: these tests need only python3 and bash.

load 'helpers'

bats_require_minimum_version 1.5.0

RUNNER="$CAIRN_SCRIPTS_DIR/cairn-test.sh"

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# The `-j` assertions match it as a COMMAND-LINE TOKEN, never as a substring.
# $BATS_TEST_TMPDIR is built from the test's own name, so a test named
# "--jobs 1 ..." puts the characters "-j" inside every path it prints: a
# substring refutation would trip over the path and never look at the flag.
assert_j_flag() {
  grep -qE -- "(^| )-j $1( |\$)" <<<"$output" || {
    echo "no '-j $1' token in: $output" >&2
    return 1
  }
}

refute_j_flag() {
  if grep -qE -- '(^| )-j( |$)' <<<"$output"; then
    echo "unexpectedly found a -j flag in: $output" >&2
    return 1
  fi
}

# A throwaway repo carrying a tests/ directory (so the default target
# resolves) plus a stub bin dir that will BE the whole PATH. Exports ROOT and
# STUB. Nothing that can parallelize is in the stub yet — each test adds
# exactly the prerequisites it wants to exist.
make_runner_fixture() {
  make_tmp_repo
  ROOT="$PWD"
  mkdir -p "$ROOT/tests"
  cat > "$ROOT/tests/probe.bats" <<'PROBE'
#!/usr/bin/env bats
@test "probe" { [ 1 -eq 1 ]; }
PROBE

  STUB="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$STUB"
  ln -sf "$(python3 -c 'import sys; print(sys.executable)')" "$STUB/python3"
  ln -sf "$(command -v bash)" "$STUB/bash"
  ln -sf "$(command -v dirname)" "$STUB/dirname"
}

# A `parallel` and a `flock` that exist and do nothing. Presence is the whole
# contract: the runner asks PATH, exactly as bats does.
stub_parallel_prereqs() {
  printf '#!/usr/bin/env bash\nexit 0\n' > "$STUB/parallel"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$STUB/flock"
  chmod +x "$STUB/parallel" "$STUB/flock"
}

# A `bats` that records that it ran, echoes its argv, and exits with CODE.
stub_bats() {
  local code="$1"
  cat > "$STUB/bats" <<STUBEOF
#!/usr/bin/env bash
echo "stub-bats argv: \$*"
: > "$BATS_TEST_TMPDIR/bats-ran"
exit $code
STUBEOF
  chmod +x "$STUB/bats"
}

#-----------------------------------------------------------------------------
# Task 1 — the composed command, inspectable before it is executed.
#-----------------------------------------------------------------------------

@test "with the parallel prerequisites present, the composed command carries -j at the CPU count" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 0
  # An INDEPENDENT oracle for the core count: getconf, not os.cpu_count().
  # Reading the number back out of the same call that produced it would
  # assert nothing.
  local cores
  cores="$(getconf _NPROCESSORS_ONLN)"

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --print-command \
    --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  # Break: never composing the -j at all — the entire requirement.
  assert_j_flag "$cores"
  echo "$output" | grep -qF "$ROOT/tests"
  # Nothing ran: --print-command composes and stops.
  [ ! -e "$BATS_TEST_TMPDIR/bats-ran" ]
}

@test "without GNU parallel the -j is removed BEFORE bats is invoked, and the warning names the cost and the fix" {
  make_runner_fixture
  # flock exists, the parallel binary does not: exactly one prerequisite
  # missing, so the test cannot pass for the other one's reason.
  printf '#!/usr/bin/env bash\nexit 0\n' > "$STUB/flock"
  chmod +x "$STUB/flock"
  stub_bats 0

  # The composed command is read off STDOUT ALONE. Reading it off the merged
  # output would be a broken assertion rather than a weak one: the warning
  # SAYS the words "`-j 4` was REMOVED", so a refutation over both channels
  # can never pass no matter how correct the composition is. Measured — this
  # is what the first version of this test did, and it failed green-side up.
  run env PATH="$STUB" "$STUB/bash" -c \
    "'$RUNNER' --print-command --jobs 4 --project-dir '$ROOT' 2>/dev/null"
  [ "$status" -eq 0 ]
  # Break: a detection hardcoded to true composes `-j 4` without parallel —
  # and THAT is the measured state this requirement exists to prevent: bats
  # then executes ZERO tests and exits 1, which is a suite that never ran
  # reported as an infrastructure failure.
  refute_j_flag

  # Now the warning itself, on its own channel.
  run env PATH="$STUB" "$STUB/bash" -c \
    "'$RUNNER' --print-command --jobs 4 --project-dir '$ROOT' 2>&1 >/dev/null"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF "GNU parallel"
  # Break: a warning with no fix in it is noise.
  echo "$output" | grep -qF "install parallel"
  # Break: a warning with no number in it is noise too.
  echo "$output" | grep -qF "64s serial"
  echo "$output" | grep -qF "33s at -j 6"
  # The claim the warning is allowed to make is about what THIS RUNNER did.
  echo "$output" | grep -qF "was REMOVED from the command below by this runner"
  # And the claim it is NOT allowed to make, because it is measurably false.
  refute_in_output "bats ignored"
  refute_in_output "silently"
}

@test "the warning lives on stderr, so --print-command's stdout stays exactly one line" {
  make_runner_fixture
  stub_bats 0

  # stderr discarded on purpose: the warning must not be on this channel.
  run env PATH="$STUB" "$STUB/bash" -c \
    "'$RUNNER' --print-command --jobs 4 --project-dir '$ROOT' 2>/dev/null"
  [ "$status" -eq 0 ]
  # Break: putting the warning on stdout — the composed command stops being
  # machine-readable, which is the one thing this flag exists for.
  [ "$(printf '%s\n' "$output" | wc -l | tr -d ' ')" = "1" ]
  echo "$output" | grep -qF "$STUB/bats"
  refute_in_output "cairn-test"
}

@test "flock and shlock both missing also removes the -j: the second thing bats -j needs" {
  make_runner_fixture
  # The parallel binary IS present. Only the locking one is missing, so this
  # test can only pass for that reason.
  printf '#!/usr/bin/env bash\nexit 0\n' > "$STUB/parallel"
  chmod +x "$STUB/parallel"
  stub_bats 0

  # stdout alone, for the same reason as the test above: the warning names
  # the flag it removed.
  run env PATH="$STUB" "$STUB/bash" -c \
    "'$RUNNER' --print-command --jobs 4 --project-dir '$ROOT' 2>/dev/null"
  [ "$status" -eq 0 ]
  # Break: checking only for GNU parallel. Measured: with neither flock nor
  # shlock, bats prints `ERROR: flock/shlock is required for parallelization
  # within files!` and exits 1 having run zero tests — the same failure the
  # parallel check exists to prevent, through a door the plan did not name.
  refute_j_flag

  run env PATH="$STUB" "$STUB/bash" -c \
    "'$RUNNER' --print-command --jobs 4 --project-dir '$ROOT' 2>&1 >/dev/null"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF "flock"
  echo "$output" | grep -qF "shlock"
  echo "$output" | grep -qF "install flock"
}

@test "test.jobs in the config is READ: with no flag at all the command carries -j 4" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 0
  run bash "$CAIRN_SCRIPTS_DIR/cairn-config.sh" set test.jobs 4 \
    --project-dir "$ROOT"
  [ "$status" -eq 0 ]

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --print-command \
    --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  # Break: ignoring the config. `test.jobs` entered the schema in plan 29-03
  # with its reader NAMED and unwritten; this assertion is the moment the
  # name becomes a fact. Without it the key is a second `cairn.sync_push`
  # and the rule says to delete it.
  assert_j_flag 4
}

@test "the flag beats the config: --jobs 2 against test.jobs 4 composes -j 2" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 0
  run bash "$CAIRN_SCRIPTS_DIR/cairn-config.sh" set test.jobs 4 \
    --project-dir "$ROOT"
  [ "$status" -eq 0 ]

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --print-command --jobs 2 \
    --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  # Break: inverted precedence.
  assert_j_flag 2
  refute_in_output "-j 4"
}

@test "--jobs 1 is a legitimate request for serial: no -j, and no warning about it" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 0

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --print-command --jobs 1 \
    --project-dir "$ROOT"
  [ "$status" -eq 0 ]
  # bats skips its whole parallel path at one job (bats-exec-suite:109), so
  # `-j 1` and no flag are the same run and the shorter one is composed.
  refute_j_flag
  # Break: scolding someone for asking for exactly what they asked for.
  refute_in_output "⚠"
}

@test "--jobs 0 is a usage error, decided before bats is invoked" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 0

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --jobs 0 --project-dir "$ROOT"
  [ "$status" -eq 2 ]
  # Break: letting a nonsense job count through to bats, where its answer
  # would be indistinguishable from a test failure.
  [ ! -e "$BATS_TEST_TMPDIR/bats-ran" ]
}

@test "a path that does not exist is exit 2 and bats never runs" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 0

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --project-dir "$ROOT" \
    "$ROOT/tests/no-such-dir"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "no such path"
  # Break: handing the bad path to bats, which answers 1 — the same code a
  # genuine test failure produces.
  [ ! -e "$BATS_TEST_TMPDIR/bats-ran" ]
}

@test "no bats on PATH is exit 5, and nothing is executed" {
  make_runner_fixture
  stub_parallel_prereqs
  # deliberately no stub_bats

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --project-dir "$ROOT"
  # Break: treating an unavailable tool as a failed check. 5 is the house
  # code for "the tool is not here" and callers are entitled to tell the two
  # apart (CONVENTIONS.md, exit-code table).
  [ "$status" -eq 5 ]
  echo "$output" | grep -qF "bats is not on PATH"
  echo "$output" | grep -qF "nothing was run"
}

@test "bats' exit code comes back untranslated: a bats that exits 1 makes the runner exit 1" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 1

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --project-dir "$ROOT"
  # Break: swallowing the code of what it runs. A runner that reports 0 over
  # a red suite is a false green with a different name (T-29-25).
  [ "$status" -eq 1 ]
  [ -e "$BATS_TEST_TMPDIR/bats-ran" ]
}

@test "a bats that exits 5 exits 5 here too, AND the output says the 5 came from bats" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 5

  run env PATH="$STUB" "$STUB/bash" "$RUNNER" --project-dir "$ROOT"
  [ "$status" -eq 5 ]
  # Break: a contract where 5 means two things and nobody can tell which.
  # The other 5 — bats not installed — is asserted two tests up, and the only
  # thing that distinguishes them at the shell is this line.
  echo "$output" | grep -qF "is bats' own exit code"
  echo "$output" | grep -qF "before bats is invoked"
  [ -e "$BATS_TEST_TMPDIR/bats-ran" ]
}

@test "the default target is tests/ under the project root, not under the cwd" {
  make_runner_fixture
  stub_parallel_prereqs
  stub_bats 0
  mkdir -p "$ROOT/sub/dir"

  run env PATH="$STUB" "$STUB/bash" -c \
    "cd '$ROOT/sub/dir' && '$RUNNER' --print-command --project-dir '$ROOT'"
  [ "$status" -eq 0 ]
  # Break: resolving `tests/` against the cwd. Running the suite from inside
  # a subdirectory is ordinary, and it would silently target nothing.
  echo "$output" | grep -qF "$ROOT/tests"
  refute_in_output "sub/dir/tests"
}

@test "with no project-dir at all the runner targets THIS repo's tests/, resolved from the script's own location" {
  # No fixture and no --project-dir: this is the real repository, and the
  # only thing being asserted is which path gets composed.
  run bash "$RUNNER" --print-command
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF "$CAIRN_REPO_ROOT/tests"
}
