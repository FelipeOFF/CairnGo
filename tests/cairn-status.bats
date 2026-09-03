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

@test "--json exits 0 with v5 keys and no GSD phase model" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD" >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  echo "$output" | grep -qv 'could not record journal'
  python3 -c '
import json,sys
raw=sys.stdin.read()
start=min(i for i in (raw.find("{"), raw.find("[")) if i>=0)
d=json.loads(raw[start:])
assert "ready" in d and "doing" in d and "blocked" in d
assert "counts" in d and "next" in d
assert "phases" not in d
assert "lease" not in d
assert "stale_complete" not in d
' <<<"$output"
}

@test "READY is bd ready intersect ready-for-agent when that label is in use" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD" >/dev/null
  bd create --title="agent work" --type=task --labels=ready-for-agent --silent >/dev/null
  bd create --title="human work" --type=task --labels=ready-for-human --silent >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  python3 -c '
import json,sys
raw=sys.stdin.read()
start=min(i for i in (raw.find("{"),) if i>=0)
d=json.loads(raw[start:])
titles=[i["title"] for i in d["ready"]]
assert "agent work" in titles
assert "human work" not in titles
' <<<"$output"
}

@test "--brief names the m-v cycle and does not mention journal" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD" >/dev/null
  bd create --title="cycle work" --type=task --labels=ready-for-agent,m-v5.1 --silent >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --brief
  [ "$status" -eq 0 ]
  grep -qF "m-v5.1" <<<"$output"
  grep -qv "journal" <<<"$output"
  grep -qv "/cairn:milestone" <<<"$output"
}

@test "--plain is TSV with COUNTS and NEXT" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD" >/dev/null
  bd create --title="ready work" --type=task --labels=ready-for-agent --silent >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --plain
  [ "$status" -eq 0 ]
  grep -q "^COUNTS" <<<"$output"
  grep -q "^READY" <<<"$output"
  grep -q "^NEXT" <<<"$output"
}
