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
  # 4 evidence axes + 1 verdict, all never-observed-before, all appended.
  assert_json_eq "$output" '.written | length' '5'
  assert_json_eq "$output" '[.written[] | select(.event == "state_changed")] | length' '4'
  assert_json_eq "$output" '[.written[] | select(.event == "verdict_changed")] | length' '1'
  assert_json_eq "$output" '[.written[] | select(.ts == "" or .ts == null)] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.nonce == "" or .nonce == null)] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.actor == "" or .actor == null)] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.phase != 5)] | length' '0'
  assert_json_eq "$output" '[.written[] | select(.source == "disk") | .to][0]' 'planned'
  assert_json_eq "$output" '[.written[] | select(.source == "bd") | .to][0]' 'none'
  assert_json_eq "$output" '[.written[] | select(.source == "roadmap") | .to][0]' 'incomplete'
  assert_json_eq "$output" '[.written[] | select(.source == "state_md") | .to][0]' 'null'
  assert_json_eq "$output" '[.written[] | select(.event == "verdict_changed") | .to][0]' 'ok'

  run bash "$JOURNAL" history --phase 5 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '5'
  assert_json_eq "$output" '[.records[] | select(.source == "disk") | .to][0]' 'planned'

  [ -f .cairn/journal.jsonl ]
  run bash -c "jq -c . < .cairn/journal.jsonl"
  [ "$status" -eq 0 ]

  # NOTE: the journal is not yet listed in .gitignore (Plan 16-05 adds that
  # entry) — this test only needs to observe the file was written, not
  # assert anything about its git-tracked status yet.
}

#-----------------------------------------------------------------------------
# Task 2: dedup diff logic in observe, verdict_changed, lease, last-moved
#-----------------------------------------------------------------------------

@test "observe dedup: resubmitting identical evidence+verdict appends zero new lines" {
  make_tmp_repo

  local payload='[{"phase": 7, "evidence": {"disk": "executed", "bd": "closed", "roadmap": "complete", "state_md": "active"}, "verdict": "ok"}]'

  run bash -c "echo '$payload' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '5'
  local lines_after_first
  lines_after_first="$(wc -l < .cairn/journal.jsonl | tr -d ' ')"

  run bash -c "echo '$payload' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '0'
  local lines_after_second
  lines_after_second="$(wc -l < .cairn/journal.jsonl | tr -d ' ')"
  [ "$lines_after_first" -eq "$lines_after_second" ]
}

@test "observe dedup: state_md null-to-null is zero new records, null-to-value is one with from null" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 8, \"evidence\": {\"state_md\": null}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '1'
  assert_json_eq "$output" '.written[0].to' 'null'
  assert_json_eq "$output" '.written[0].from' 'null'

  run bash -c "echo '[{\"phase\": 8, \"evidence\": {\"state_md\": null}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '0'

  run bash -c "echo '[{\"phase\": 8, \"evidence\": {\"state_md\": \"active\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '1'
  assert_json_eq "$output" '.written[0].from' 'null'
  assert_json_eq "$output" '.written[0].to' 'active'
}

@test "observe dedup: verdict change appends exactly one verdict_changed record independent of evidence" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 6, \"evidence\": {}, \"verdict\": \"ok\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '1'
  assert_json_eq "$output" '.written[0].event' 'verdict_changed'
  assert_json_eq "$output" '.written[0].from' 'null'
  assert_json_eq "$output" '.written[0].to' 'ok'

  run bash -c "echo '[{\"phase\": 6, \"evidence\": {}, \"verdict\": \"conflict\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '1'
  assert_json_eq "$output" '.written[0].from' 'ok'
  assert_json_eq "$output" '.written[0].to' 'conflict'

  run bash -c "echo '[{\"phase\": 6, \"evidence\": {}, \"verdict\": \"conflict\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '0'
}

@test "lease subcommand: always appends unconditionally, holder/actor/prev_holder preserved" {
  make_tmp_repo

  run bash "$JOURNAL" lease 9 acquired --holder /path/A --actor felipe --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" history --phase 9 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'
  assert_json_eq "$output" '.records[0].event' 'lease_changed'
  assert_json_eq "$output" '.records[0].action' 'acquired'
  assert_json_eq "$output" '.records[0].holder' '/path/A'
  assert_json_eq "$output" '.records[0].actor' 'felipe'
  assert_json_eq "$output" '.records[0].prev_holder' 'null'

  # Second call with the SAME holder still appends a SECOND record — lease
  # does no dedup itself; that is the caller's job (Plan 16-03/16-04).
  run bash "$JOURNAL" lease 9 acquired --holder /path/A --actor felipe --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" history --phase 9 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '2'

  # released with no --prev-holder given still appends (prev_holder null
  # is valid) -- the caller (Plan 16-03/16-04) decides when to pass it.
  run bash "$JOURNAL" lease 9 released --holder /path/A --actor felipe --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" history --phase 9 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '3'
  assert_json_eq "$output" '[.records[] | select(.action == "released") | .prev_holder][0]' 'null'

  # A released call WITH --prev-holder round-trips it verbatim too.
  run bash "$JOURNAL" lease 10 released --holder /path/B --prev-holder /path/A --actor felipe --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" history --phase 10 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records[0].prev_holder' '/path/A'
}

@test "last-moved: reports last value+ts per axis, or null when never observed" {
  make_tmp_repo

  # No journal file at all yet: every axis null, exit 0, never an error.
  run bash "$JOURNAL" last-moved --phase 999 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.disk' 'null'
  assert_json_eq "$output" '.bd' 'null'
  assert_json_eq "$output" '.roadmap' 'null'
  assert_json_eq "$output" '.state_md' 'null'
  assert_json_eq "$output" '.verdict' 'null'
  assert_json_eq "$output" '.lease' 'null'
  [ ! -f .cairn/journal.jsonl ]

  run bash "$JOURNAL" lease 9 acquired --holder /path/A --actor felipe --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" last-moved --phase 9 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.lease.value' 'acquired'
  assert_json_eq "$output" '.lease.holder' '/path/A'
  assert_json_eq "$output" '.disk' 'null'
  assert_json_eq "$output" '.bd' 'null'
  assert_json_eq "$output" '.roadmap' 'null'
  assert_json_eq "$output" '.state_md' 'null'
  assert_json_eq "$output" '.verdict' 'null'

  # Still no records for an unrelated phase, even though the journal file
  # itself now exists (holding phase 9's record).
  run bash "$JOURNAL" last-moved --phase 999 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.lease' 'null'
}
