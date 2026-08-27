#!/usr/bin/env bats
# cairn-stop.bats — the flag a running loop respects (phase 50 / STOP-01).

load 'helpers'

STOP="$CAIRN_SCRIPTS_DIR/cairn-stop.sh"
LEASE="$CAIRN_SCRIPTS_DIR/cairn-lease.sh"

@test "request writes the flag, check exits 3 where it applies and 0 where it does not, clear removes it" {
  make_tmp_repo
  run bash "$STOP" check --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "no stop requested" <<<"$output"

  run bash "$STOP" request --phase 7 --reason "enough" --actor board --project-dir "$PWD"
  [ "$status" -eq 0 ]
  [ -f .cairn/stop ]
  run jq -r '.phase + " " + .actor + " " + .reason' .cairn/stop
  [ "$output" = "7 board enough" ]

  run bash "$STOP" check --phase 7 --project-dir "$PWD"
  [ "$status" -eq 3 ]
  grep -qF "stop requested by board" <<<"$output"
  run bash "$STOP" check --phase 8 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.requested' 'false'
  # A check with no phase asks "any request?" — a per-phase one applies.
  run bash "$STOP" check --project-dir "$PWD"
  [ "$status" -eq 3 ]

  run bash "$STOP" clear --project-dir "$PWD" --json
  assert_json_eq "$output" '.cleared' 'true'
  [ ! -f .cairn/stop ]

  # A global request applies to every phase.
  bash "$STOP" request --project-dir "$PWD" >/dev/null
  run bash "$STOP" check --phase 8 --project-dir "$PWD"
  [ "$status" -eq 3 ]
}

@test "the lease status and the batch carry stop_requested from the same reader" {
  require_bd
  make_tmp_repo
  bd init -q --prefix stp --non-interactive >/dev/null 2>&1
  bash "$LEASE" acquire 4 --project-dir "$PWD" >/dev/null
  run bash "$LEASE" status 4 --project-dir "$PWD" --json
  assert_json_eq "$output" '.stop_requested' 'false'

  bash "$STOP" request --phase 4 --project-dir "$PWD" >/dev/null
  run bash "$LEASE" status 4 --project-dir "$PWD" --json
  assert_json_eq "$output" '.stop_requested' 'true'
  run bash "$LEASE" status --all --project-dir "$PWD" --json
  assert_json_eq "$output" '.[0].stop_requested' 'true'
  # A per-phase request is not the run's: batch says false; a global one, true.
  make_gsd_fixture "$PWD"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-parallel.sh" batch --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.stop_requested' 'false'
  bash "$STOP" request --project-dir "$PWD" >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-parallel.sh" batch --json --project-dir "$PWD"
  assert_json_eq "$output" '.stop_requested' 'true'
}
