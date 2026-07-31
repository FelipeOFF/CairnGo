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

# The journal-failure tests use `run --separate-stderr` (bats-core >= 1.5.0)
# to assert on stdout and stderr independently.
bats_require_minimum_version 1.5.0

LEASE="$CAIRN_SCRIPTS_DIR/cairn-lease.sh"
JOURNAL="$CAIRN_SCRIPTS_DIR/cairn-journal.sh"

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

#-----------------------------------------------------------------------------
# Phase 16 Plan 03 Task 1: journal wiring — genuine transitions only (D-01).
# The journal is per-worktree local storage (<project-dir>/.cairn/
# journal.jsonl, never shared across worktrees — see cairn-journal.py's
# module docstring), so these tests always read history back through the
# SAME --project-dir the write went through.
#-----------------------------------------------------------------------------

@test "journal: fresh acquire writes one lease_changed record; a same-worktree renewal via acquire, and renew, write zero" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local root
  root="$(git rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 20 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" history --phase 20 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'
  assert_json_eq "$output" '.records[0].event' 'lease_changed'
  assert_json_eq "$output" '.records[0].action' 'acquired'
  assert_json_eq "$output" '.records[0].holder' "$root"
  assert_json_eq "$output" '.records[0].prev_holder' 'null'

  # Same-worktree heartbeat renewal via acquire (already_mine): zero new
  # records — a heartbeat is not a transition (D-01).
  run bash "$LEASE" acquire 20 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "already yours" <<<"$output"
  run bash "$JOURNAL" history --phase 20 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'

  # renew: also zero new records, always.
  run bash "$LEASE" renew 20 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" history --phase 20 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'
}

@test "journal: a reclaim from a stale lease writes one lease_changed record naming the previous holder" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 23 --project-dir "$wt_a" --json
  [ "$status" -eq 0 ]
  local lease_id old_acquired_at
  lease_id="$(jq -r '.id' <<<"$output")"
  old_acquired_at="$(jq -r '.acquired_at' <<<"$output")"

  # wt_a's own journal has exactly the acquire record so far.
  run bash "$JOURNAL" history --phase 23 --json --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'
  assert_json_eq "$output" '.records[0].holder' "$wt_a"
  assert_json_eq "$output" '.records[0].prev_holder' 'null'

  # Simulate the passage of time by hand-setting heartbeat_at via bd
  # directly (bypassing cairn-lease.py, hence never touching either
  # worktree's journal), rather than sleeping 4+ hours.
  local stale_ts
  stale_ts="$(python3 -c "
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) - timedelta(hours=5)).isoformat())
")"
  run bd update "$lease_id" --metadata \
    "{\"cairn\":{\"lease\":{\"phase\":23,\"holder\":\"$wt_a\",\"actor\":\"a\",\"host\":\"h\",\"acquired_at\":\"$old_acquired_at\",\"heartbeat_at\":\"$stale_ts\"}}}"
  [ "$status" -eq 0 ]

  run bash "$LEASE" acquire 23 --project-dir "$wt_b"
  [ "$status" -eq 0 ]
  grep -qF "reclaimed" <<<"$output"

  # wt_a's own journal is UNCHANGED by wt_b's reclaim — the journal is
  # per-worktree, never a cross-worktree coordination primitive.
  run bash "$JOURNAL" history --phase 23 --json --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'

  # wt_b's own journal has exactly one record: the reclaim, naming wt_a as
  # prev_holder.
  run bash "$JOURNAL" history --phase 23 --json --project-dir "$wt_b"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'
  assert_json_eq "$output" '.records[0].event' 'lease_changed'
  assert_json_eq "$output" '.records[0].action' 'acquired'
  assert_json_eq "$output" '.records[0].holder' "$wt_b"
  assert_json_eq "$output" '.records[0].prev_holder' "$wt_a"
}

@test "journal: acquire held-by-another (EXIT_HELD) writes nothing to either worktree's journal" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 24 --project-dir "$wt_a"
  [ "$status" -eq 0 ]

  run bash "$LEASE" acquire 24 --project-dir "$wt_b"
  [ "$status" -eq 3 ]

  run bash "$JOURNAL" history --phase 24 --json --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'

  # wt_b never wrote — held-by-another writes NOTHING to bd or the journal
  # (D-04) — so wt_b's own journal for this phase does not even exist.
  run bash "$JOURNAL" history --phase 24 --json --project-dir "$wt_b"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '0'
}

@test "journal: release writes one lease_changed record; a second release on the now-vacant lease writes zero" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" acquire 25 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$LEASE" release 25 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" history --phase 25 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '2'
  assert_json_eq "$output" '.records[1].event' 'lease_changed'
  assert_json_eq "$output" '.records[1].action' 'released'

  # A second release on the now-vacant lease: no-op, zero new records.
  run bash "$LEASE" release 25 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" history --phase 25 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '2'
}

@test "journal: release on a phase whose lease issue was never created writes zero records" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  run bash "$LEASE" release 998 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" history --phase 998 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '0'
}

@test "journal: release --mine writes one lease_changed record per phase actually released, zero for a phase held by a different worktree" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local wt_a
  wt_a="$(git rev-parse --show-toplevel)"
  local wt_b="$BATS_TEST_TMPDIR/wt-b"
  git worktree add -q "$wt_b" -b wt-b-branch
  wt_b="$(git -C "$wt_b" rev-parse --show-toplevel)"

  run bash "$LEASE" acquire 26 --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  run bash "$LEASE" acquire 27 --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  run bash "$LEASE" acquire 28 --project-dir "$wt_b"
  [ "$status" -eq 0 ]

  run bash "$LEASE" release --mine --project-dir "$wt_a"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" history --phase 26 --json --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '2'
  assert_json_eq "$output" '.records[1].action' 'released'
  assert_json_eq "$output" '.records[1].holder' "$wt_a"

  run bash "$JOURNAL" history --phase 27 --json --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '2'
  assert_json_eq "$output" '.records[1].action' 'released'

  # phase 28 was acquired by wt_b, not wt_a — release --mine from wt_a
  # never touches it. wt_a's OWN journal never even sees phase 28 (the
  # acquire itself was written into wt_b's journal, per-worktree, not
  # shared) — a release --mine call that wrongly matched it would show up
  # here as an unexpected extra record.
  run bash "$JOURNAL" history --phase 28 --json --project-dir "$wt_a"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '0'

  run bash "$JOURNAL" history --phase 28 --json --project-dir "$wt_b"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'
  assert_json_eq "$output" '.records[0].action' 'acquired'
}

#-----------------------------------------------------------------------------
# Phase 16 Plan 03 Task 2: a broken/missing journal never blocks the
# lease's own documented contract (D-02) — the only observable difference
# is a stderr warning; exit codes and bd state are identical to a normal
# working-journal call.
#-----------------------------------------------------------------------------

@test "journal failure: acquire/release/renew succeed identically to normal, with a stderr warning, when CAIRN_JOURNAL points at a nonexistent path" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local root
  root="$(git rev-parse --show-toplevel)"
  local broken="$BATS_TEST_TMPDIR/nowhere/cairn-journal.py"

  run --separate-stderr env CAIRN_JOURNAL="$broken" \
    bash "$LEASE" acquire 40 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  grep -qF "[cairn-lease] warning:" <<<"$stderr"
  grep -qiF "journal" <<<"$stderr"
  local lease_id
  lease_id="$(jq -r '.id' <<<"$output")"

  run bd show "$lease_id" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.[0].metadata.cairn.lease.holder' "$root"

  # renew: never calls the journal in any branch, so it is trivially
  # unaffected — proven here rather than assumed.
  run --separate-stderr env CAIRN_JOURNAL="$broken" \
    bash "$LEASE" renew 40 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run --separate-stderr env CAIRN_JOURNAL="$broken" \
    bash "$LEASE" release 40 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "[cairn-lease] warning:" <<<"$stderr"

  run bd show "$lease_id" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.[0].status' 'open'
  assert_json_eq "$output" '(.[0].metadata.cairn.lease.holder // "absent")' 'absent'
}

@test "journal failure: acquire/release/renew succeed identically to normal, with a stderr warning, when CAIRN_JOURNAL is a stub that always exits 1" {
  require_bd
  make_tmp_repo
  bd init -q --prefix lse --non-interactive >/dev/null 2>&1

  local root
  root="$(git rev-parse --show-toplevel)"
  local stub="$BATS_TEST_TMPDIR/always-fail-journal.py"
  cat > "$stub" <<'PYEOF'
#!/usr/bin/env python3
import sys
sys.exit(1)
PYEOF

  run --separate-stderr env CAIRN_JOURNAL="$stub" \
    bash "$LEASE" acquire 41 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  grep -qF "[cairn-lease] warning:" <<<"$stderr"
  local lease_id
  lease_id="$(jq -r '.id' <<<"$output")"

  run bd show "$lease_id" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.[0].metadata.cairn.lease.holder' "$root"

  run --separate-stderr env CAIRN_JOURNAL="$stub" \
    bash "$LEASE" renew 41 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run --separate-stderr env CAIRN_JOURNAL="$stub" \
    bash "$LEASE" release 41 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "[cairn-lease] warning:" <<<"$stderr"

  run bd show "$lease_id" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.[0].status' 'open'
  assert_json_eq "$output" '(.[0].metadata.cairn.lease.holder // "absent")' 'absent'
}
