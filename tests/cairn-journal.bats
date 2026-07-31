#!/usr/bin/env bats
# cairn-journal.bats — exercises the transition-journal CLI contract
# (cairn-journal.py / the cairn-journal.sh wrapper): observe (batched,
# diff-then-append), lease (unconditional append), history, and
# last-moved, backed by a local, gitignored, append-only .cairn/
# journal.jsonl (D-01/D-02). These tests exercise the CLI directly — no
# bd required, no other cairn-*.py caller involved (wiring is later
# plans' work).
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail
# a bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'

JOURNAL="$CAIRN_SCRIPTS_DIR/cairn-journal.sh"

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

#-----------------------------------------------------------------------------
# Task 1: the append/read primitives end to end
#-----------------------------------------------------------------------------

@test "tracer: observe appends a state_changed record per evidence axis; history reads it back" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 5, \"evidence\": {\"disk\": \"planned\", \"bd\": \"none\", \"roadmap\": \"incomplete\", \"state_md\": null}, \"verdict\": \"ok\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '4'
  assert_json_eq "$output" '[.written[] | select(.ts == "" or .ts == null)] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.nonce == "" or .nonce == null)] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.actor == "" or .actor == null)] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.phase != 5)] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.event != "state_changed")] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.source == "disk") | .to][0]' 'planned'
  assert_json_eq "$output" '[.written[] | select(.source == "bd") | .to][0]' 'none'
  assert_json_eq "$output" '[.written[] | select(.source == "roadmap") | .to][0]' 'incomplete'
  assert_json_eq "$output" '[.written[] | select(.source == "state_md") | .to][0]' 'null'

  run bash "$JOURNAL" history --phase 5 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '4'
  assert_json_eq "$output" '[.records[] | select(.source == "disk") | .to][0]' 'planned'

  [ -f .cairn/journal.jsonl ]
  run bash -c "jq -c . < .cairn/journal.jsonl"
  [ "$status" -eq 0 ]

  # NOTE: the journal is not yet listed in .gitignore (Plan 16-05 adds that
  # entry) — this test only needs to observe the file was written, not
  # assert anything about its git-tracked status yet.
}
