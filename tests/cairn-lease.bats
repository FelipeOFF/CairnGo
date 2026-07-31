#!/usr/bin/env bats
# cairn-lease.bats — exercises the phase-lease CLI contract (cairn-lease.py /
# the cairn-lease.sh wrapper): acquire/release/renew/status, backed by a
# dedicated `lease`-labelled bd issue per phase (never a phase-<N> label —
# see the module docstring for why).
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'

LEASE="$CAIRN_SCRIPTS_DIR/cairn-lease.sh"

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

#-----------------------------------------------------------------------------
# Task 1: acquire / release / status for a single phase, cross-worktree
#-----------------------------------------------------------------------------

@test "the tracer: lease acquired in worktree A is visible from a real second worktree B" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  # Canonicalized via git itself (not raw $PWD): on macOS TMPDIR resolves
  # through a /var -> /private/var symlink, and `git rev-parse
  # --show-toplevel` (what cairn-lease.py uses for identity) returns the
  # PHYSICAL path, so the assertion must compare against the same
  # canonicalization the script performs internally, not bash's logical $PWD.
  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch

  run bash "$LEASE" acquire 15 --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  grep -qF "acquired phase 15 lease" <<<"$output"

  run bash "$LEASE" status 15 --project-dir "$wt_b" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'true'
  assert_json_eq "$output" '.holder' "$wt_a"
}

@test "acquire on a live-held phase writes nothing, exits 3, names the holder and since-when" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch

  run bash "$LEASE" acquire 15 --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  run bash "$LEASE" status 15 --project-dir "$wt_a" --json
  local acquired_at
  acquired_at="$(jq -r '.acquired_at' <<<"$output")"

  run bash "$LEASE" acquire 15 --project-dir "$wt_b"
  [ "$status" -eq 3 ]
  grep -qF "$wt_a" <<<"$output"
  grep -qF "$acquired_at" <<<"$output"

  # Nothing was written: worktree A is still the holder, acquired_at unchanged.
  run bash "$LEASE" status 15 --project-dir "$wt_a" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.holder' "$wt_a"
  assert_json_eq "$output" '.acquired_at' "$acquired_at"
}

@test "the lease issue carries only the lease label, never phase-<N>" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" acquire 15 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local lease_id
  lease_id="$(jq -r '.id' <<<"$output")"

  run bd show "$lease_id" --json
  [ "$status" -eq 0 ]
  # The title legitimately contains the substring "phase-15" ("phase-15
  # lease") — the load-bearing assertion is the LABELS array, checked
  # exhaustively: exactly one label, and it is "lease", never "phase-15".
  assert_json_eq "$output" '.[0].labels | length' '1'
  assert_json_eq "$output" '.[0].labels[0]' 'lease'
  assert_json_eq "$output" '(.[0].labels | index("phase-15")) // "absent"' 'absent'
}

@test "release clears the lease; a second release on the now-vacant lease is a no-op" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" acquire 15 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$LEASE" acquire 15 --project-dir "$PWD" --json
  local lease_id
  lease_id="$(jq -r '.id' <<<"$output")"

  run bash "$LEASE" release 15 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  # Assert against raw bd state, not just our own script's status output —
  # a stub echoing static held:false JSON would pass a self-referential
  # check trivially.
  run bd show "$lease_id" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.[0].status' 'open'
  assert_json_eq "$output" '(.[0].assignee // "") ' ''
  assert_json_eq "$output" '(.[0].metadata.cairn.lease.holder // "absent")' 'absent'

  run bash "$LEASE" status 15 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'false'
  assert_json_eq "$output" '.holder' 'null'

  # Second release: no-op, exit 0, no traceback, and bd state unchanged.
  run bash "$LEASE" release 15 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"
  run bd show "$lease_id" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "release on a phase whose lease issue was never created is a no-op, exit 0, and creates no issue" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" release 999 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"

  run bd list -l lease --all --limit 0 --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" 'length' '0'
}

@test "acquire creates exactly one lease issue; a second immediate acquire from the same worktree reuses it" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" acquire 15 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$LEASE" acquire 15 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "already yours" <<<"$output"

  run bd list -l lease --all --limit 0 --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" 'length' '1'
}

@test "status on a phase that never had a lease reports held=false with null identity fields, and creates nothing" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" status 42 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'false'
  assert_json_eq "$output" '.id' 'null'
  assert_json_eq "$output" '.holder' 'null'
  assert_json_eq "$output" '.acquired_at' 'null'
  assert_json_eq "$output" '.heartbeat_at' 'null'

  run bd list -l lease --all --limit 0 --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" 'length' '0'
}
