#!/usr/bin/env bats
# cairn-init.bats — exercises cairn/scripts/cairn-init.sh against throwaway
# repos: git + bd bootstrap, the .gitignore entries promised by docs/sync.md §4,
# and idempotent re-runs (no duplicate lines).

load 'helpers'

# The four entries cairn-init must gitignore (docs/sync.md §4).
CAIRN_GITIGNORE_ENTRIES=(
  '.cairn/.beacon-sent'
  '.cairn/id-map.json'
  '.cairn/state.json'
  '.cairn/conflicts.json'
)

@test "cairn-init bootstraps git + bd and gitignores the .cairn state files" {
  require_bd
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]

  [ -d .git ]
  [ -d .beads ]
  local entry
  for entry in "${CAIRN_GITIGNORE_ENTRIES[@]}"; do
    grep -qxF "$entry" .gitignore
  done
}

@test "cairn-init re-run is idempotent — no duplicate .gitignore entries" {
  require_bd
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  [[ "$output" == *".cairn state files already gitignored"* ]]

  local entry
  for entry in "${CAIRN_GITIGNORE_ENTRIES[@]}"; do
    [ "$(grep -cxF "$entry" .gitignore)" -eq 1 ]
  done
}

@test "cairn-init completes a legacy .gitignore that only has .beacon-sent" {
  require_bd
  make_tmp_repo
  printf '.cairn/.beacon-sent\n' > .gitignore

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]

  # The pre-existing entry stays single; the missing three are appended once.
  local entry
  for entry in "${CAIRN_GITIGNORE_ENTRIES[@]}"; do
    [ "$(grep -cxF "$entry" .gitignore)" -eq 1 ]
  done
}
