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

#-----------------------------------------------------------------------------
# Task 2: renew, status --all, release --mine, staleness edge cases
#-----------------------------------------------------------------------------

@test "a stale lease (heartbeat older than 4h) is reclaimed by the next acquire, with a fresh acquired_at" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 7 --project-dir "$wt_a" --json
  [ "$status" -eq 0 ]
  local lease_id old_acquired_at
  lease_id="$(jq -r '.id' <<<"$output")"
  old_acquired_at="$(jq -r '.acquired_at' <<<"$output")"

  # Simulate the passage of time by hand-setting heartbeat_at via bd
  # directly, bypassing the script entirely, rather than sleeping 4+ hours.
  local stale_ts
  stale_ts="$(python3 -c "
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) - timedelta(hours=5)).isoformat())
")"
  run bd update "$lease_id" --metadata \
    "{\"cairn\":{\"lease\":{\"phase\":7,\"holder\":\"$wt_a\",\"actor\":\"a\",\"host\":\"h\",\"acquired_at\":\"$old_acquired_at\",\"heartbeat_at\":\"$stale_ts\"}}}"
  [ "$status" -eq 0 ]

  run bash "$LEASE" acquire 7 --project-dir "$wt_b"
  [ "$status" -eq 0 ]
  grep -qF "reclaimed" <<<"$output"
  grep -qF "$wt_a" <<<"$output"

  run bash "$LEASE" status 7 --project-dir "$wt_a" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.holder' "$wt_b"
  local new_acquired_at
  new_acquired_at="$(jq -r '.acquired_at' <<<"$output")"
  [ "$new_acquired_at" != "$old_acquired_at" ]
}

@test "renew from a worktree that does NOT hold the lease writes nothing (status byte-identical) and exits 0" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 9 --project-dir "$wt_a"
  [ "$status" -eq 0 ]

  run bash "$LEASE" status 9 --project-dir "$wt_a" --json
  [ "$status" -eq 0 ]
  local before="$output"

  # wt_b does not hold phase 9's lease.
  run bash "$LEASE" renew 9 --project-dir "$wt_b"
  [ "$status" -eq 0 ]

  run bash "$LEASE" status 9 --project-dir "$wt_a" --json
  [ "$status" -eq 0 ]
  [ "$output" = "$before" ]
}

@test "renew with no phase argument resolves active_phase from STATE.md, and is a silent no-op with no STATE.md" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" acquire 3 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$LEASE" status 3 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local before_heartbeat
  before_heartbeat="$(jq -r '.heartbeat_at' <<<"$output")"

  mkdir -p .planning
  cat > .planning/STATE.md <<'EOF'
---
active_phase: "3"
---
# State
EOF

  run bash "$LEASE" renew --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$LEASE" status 3 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local after_heartbeat
  after_heartbeat="$(jq -r '.heartbeat_at' <<<"$output")"
  [ "$after_heartbeat" != "$before_heartbeat" ]

  # No STATE.md at all: silent no-op, exit 0, no traceback.
  rm -f .planning/STATE.md
  run bash "$LEASE" renew --project-dir "$PWD"
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"
}

@test "status --all reports one entry per phase that ever had a lease, across worktrees" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 11 --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  run bash "$LEASE" acquire 12 --project-dir "$wt_b"
  [ "$status" -eq 0 ]

  run bash "$LEASE" status --all --project-dir "$wt_a" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" 'length' '2'
  assert_json_eq "$output" '[.[] | select(.phase == 11) | .holder][0]' "$wt_a"
  assert_json_eq "$output" '[.[] | select(.phase == 12) | .holder][0]' "$wt_b"
}

@test "status --all on a repo with zero lease issues ever created returns an empty array" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" status --all --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" 'length' '0'
}

@test "release --mine releases only the calling worktree's own lease(s)" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 21 --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  run bash "$LEASE" acquire 22 --project-dir "$wt_b"
  [ "$status" -eq 0 ]

  run bash "$LEASE" release --mine --project-dir "$wt_a"
  [ "$status" -eq 0 ]

  run bash "$LEASE" status 21 --project-dir "$wt_a" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'false'

  run bash "$LEASE" status 22 --project-dir "$wt_b" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'true'
  assert_json_eq "$output" '.holder' "$wt_b"
}

@test "release --mine with zero matches is a no-op, exit 0, no traceback" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" release --mine --project-dir "$PWD"
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"
}

@test "usage errors: non-numeric or missing phase exits 2 with a usage line, never a traceback" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" acquire notanumber --project-dir "$PWD"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash "$LEASE" acquire --project-dir "$PWD"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash "$LEASE" release notanumber --project-dir "$PWD"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash "$LEASE" renew notanumber --project-dir "$PWD"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash "$LEASE" status notanumber --project-dir "$PWD"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  # status/release with neither a phase number nor their --all/--mine flag.
  run bash "$LEASE" status --project-dir "$PWD"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash "$LEASE" release --project-dir "$PWD"
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"
}

@test "bd missing from PATH exits 5 for every subcommand, no traceback" {
  make_tmp_repo

  local stub="$BATS_TEST_TMPDIR/nobd-bin"
  mkdir -p "$stub"
  ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
  ln -s "$(command -v bash)" "$stub/bash"
  ln -s "$(command -v dirname)" "$stub/dirname"

  run env PATH="$stub" "$stub/bash" "$LEASE" acquire 1 --project-dir "$PWD"
  [ "$status" -eq 5 ]
  refute_in_output "Traceback"

  run env PATH="$stub" "$stub/bash" "$LEASE" release 1 --project-dir "$PWD"
  [ "$status" -eq 5 ]
  refute_in_output "Traceback"

  run env PATH="$stub" "$stub/bash" "$LEASE" renew 1 --project-dir "$PWD"
  [ "$status" -eq 5 ]
  refute_in_output "Traceback"

  run env PATH="$stub" "$stub/bash" "$LEASE" status 1 --project-dir "$PWD"
  [ "$status" -eq 5 ]
  refute_in_output "Traceback"
}
