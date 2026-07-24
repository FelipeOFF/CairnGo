#!/usr/bin/env bats
# gbsync.bats — exercises the gbsync dispatcher's --dry-run contract through
# the real CLI (gbsync.py / the gbsync.sh wrapper): it walks the push/pull
# decision logic, prints one 'DRY-RUN:' line per would-be operation, exits 0,
# and never calls an adapter or writes id-map.json / state.json /
# conflicts.json under .cairn/.

load 'helpers'

# Write a minimal .cairn/sync.json (github backend enabled) into the current
# repo. GH_TOKEN is a dummy on purpose: dry-run must never reach the gh CLI
# or the network, so a fake token must be harmless.
make_sync_config() {
  mkdir -p .cairn
  cat > .cairn/sync.json <<'EOF'
{
  "backends": [
    { "type": "github", "enabled": true, "adapter": "github",
      "config": { "repo": "example/fixture", "extra_labels": [] } }
  ]
}
EOF
  export GH_TOKEN="dummy-not-a-real-token"
}

@test "gbsync push --dry-run prints DRY-RUN lines, exits 0, writes no state" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_sync_config

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" create "$BD_EPIC" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ "$output" = "DRY-RUN: github create $BD_EPIC -> (new)" ]

  [ ! -e .cairn/id-map.json ]
  [ ! -e .cairn/state.json ]
  [ ! -e .cairn/conflicts.json ]
}

@test "gbsync push --dry-run emits only DRY-RUN-prefixed lines" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_sync_config

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" update "$BD_STANDALONE" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ -n "$output" ]
  local line
  while IFS= read -r line; do
    [[ "$line" == DRY-RUN:* ]]
  done <<< "$output"
}

@test "gbsync pull --dry-run lists mapped items and advances no watermark" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_sync_config
  printf '{ "%s": { "github": "42" } }\n' "$BD_EPIC" > .cairn/id-map.json
  local before
  before="$(cat .cairn/id-map.json)"

  run python3 "$CAIRN_SCRIPTS_DIR/gbsync.py" pull --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [ "$output" = "DRY-RUN: github pull $BD_EPIC <- 42 (since 1970-01-01T00:00:00Z)" ]

  # No watermark, no conflicts log, and the id-map is byte-identical.
  [ ! -e .cairn/state.json ]
  [ ! -e .cairn/conflicts.json ]
  [ "$(cat .cairn/id-map.json)" = "$before" ]
}

@test "gbsync.sh wrapper forwards --dry-run to the dispatcher" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst
  make_sync_config

  run bash "$CAIRN_SCRIPTS_DIR/gbsync.sh" update "$BD_EPIC" --dir "$PWD" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == DRY-RUN:* ]]

  [ ! -e .cairn/id-map.json ]
  [ ! -e .cairn/state.json ]
  [ ! -e .cairn/conflicts.json ]
}
