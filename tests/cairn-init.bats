#!/usr/bin/env bats
load 'helpers'

CAIRN_GITIGNORE_ENTRIES=(
  '.cairn/id-map.json'
  '.cairn/state.json'
  '.cairn/conflicts.json'
  '.cairn/journal.jsonl*'
  '.cairn/journal/*'
  '!.cairn/journal/*.jsonl'
  '.cairn/reconcile-evidence.json'
  '.cairn/hook.log'
  '.cairn/migrate-plan.json'
  '.cairn/migrate-state.json'
  '.cairn/plugin-root'
)

make_cairn_generated_files() {
  mkdir -p .cairn
  local f
  for f in id-map.json state.json conflicts.json journal.jsonl \
           journal.jsonl.tmp-abc123 journal.jsonl.compact.lock \
           reconcile-evidence.json hook.log migrate-plan.json \
           migrate-state.json plugin-root; do
    printf 'generated\n' > ".cairn/$f"
  done
}

make_cairn_committable_files() {
  mkdir -p .cairn
  printf '{"backends":{}}\n' > .cairn/sync.json
}

cairn_untracked() {
  git status --porcelain -uall | sed -n 's/^?? //p' | grep '^\.cairn/' || true
}

@test "cairn-init bootstraps git + bd and gitignores the .cairn state files" {
  make_tmp_repo
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  [ -d .git ]
  [ -d .beads ]
  local e
  for e in "${CAIRN_GITIGNORE_ENTRIES[@]}"; do
    grep -qxF "$e" .gitignore
  done
}

@test "cairn-init re-run is idempotent — no duplicate .gitignore entries" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  local e
  for e in "${CAIRN_GITIGNORE_ENTRIES[@]}"; do
    [ "$(grep -cxF "$e" .gitignore)" = "1" ]
  done
}

@test "after cairn-init no generated .cairn file shows up as untracked" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  make_cairn_generated_files
  run bash -c 'git status --porcelain -uall | grep "^\?\? .cairn/" | grep -v sync.json || true'
  [ -z "$output" ]
}

@test "cairn-init leaves the committable .cairn config files visible to git" {
  make_tmp_repo
  bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  make_cairn_committable_files
  git status --porcelain -uall | grep -q 'sync.json'
}

@test "cairn-init points at /cairn-implement not /gsd:" {
  grep -q '/cairn-implement' "$CAIRN_SCRIPTS_DIR/cairn-init.sh"
  run grep -F '/gsd:' "$CAIRN_SCRIPTS_DIR/cairn-init.sh"
  [ "$status" -ne 0 ]
}
