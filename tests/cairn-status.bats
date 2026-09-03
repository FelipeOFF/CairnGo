#!/usr/bin/env bats
load 'helpers'

@test "usage errors exit 2" {
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --not-a-flag
  [ "$status" -eq 2 ]
}

@test "bd missing from PATH exits 5" {
  make_tmp_repo
  PATH="/usr/bin:/bin" run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --brief
  [ "$status" -eq 5 ]
}

@test "--brief prints lanes from bd ready" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD" >/dev/null
  bd create --title="ready work" --type=task --labels=ready-for-agent >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --brief
  [ "$status" -eq 0 ]
  [[ "$output" == *"ready"* ]] || [[ "$output" == *"READY"* ]] || [[ "$output" == *"next"* ]]
}

@test "--json exits 0" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD" >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
}
