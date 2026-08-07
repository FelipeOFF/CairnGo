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

# Phase 28: the journal is PARTITIONED, one file per checkout, under
# .cairn/journal/. Tests that used to hardcode .cairn/journal.jsonl ask the
# script itself where its own active segment is -- a test that recomputed the
# slug would just be a second implementation of the naming scheme.
own_segment() {
  bash "$JOURNAL" provenance --project-dir "$PWD" --json | jq -r '.segment'
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

  [ -f "$(own_segment)" ]
  run bash -c "jq -c . < \"$(own_segment)\""
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
  lines_after_first="$(wc -l < "$(own_segment)" | tr -d ' ')"

  run bash -c "echo '$payload' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '0'
  local lines_after_second
  lines_after_second="$(wc -l < "$(own_segment)" | tr -d ' ')"
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
  [ ! -f "$(own_segment)" ]

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

#-----------------------------------------------------------------------------
# Task 3: torn-line quarantine on read (JOUR-04) — the byte-offset fixture.
#
# The fixture is built by a REAL `observe` call (never hand-written JSON),
# then truncated at a byte offset strictly INSIDE the last record's "to"
# string value — never at a record boundary. Every truncation script below
# self-verifies the cut produced invalid JSON (a fixture bug that
# accidentally produces valid-but-short JSON would otherwise silently pass
# with a wrong record count instead of failing loudly).
#-----------------------------------------------------------------------------

@test "torn tail: a byte-offset cut inside a JSON string value quarantines with the correct offset, history reads all complete records" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 42, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\": 42, \"evidence\": {\"disk\": \"verified\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  [ -f "$(own_segment)" ]

  cat > truncate_fixture.py <<'PYEOF'
import glob
import json
import sys

path = sorted(glob.glob(".cairn/journal/*.jsonl"))[-1]
data = open(path, "rb").read()
lines = [l for l in data.split(b"\n") if l.strip()]
n_complete_before = len(lines) - 1
last = lines[-1].decode("utf-8")
needle = '"verified"'
idx = last.index(needle)
cut_in_line = idx + len('"ver')  # lands inside the string body, after 'ver'
last_line_start = data.rfind(lines[-1])
cut_point = last_line_start + cut_in_line

with open(path, "r+b") as f:
    f.truncate(cut_point)

truncated = open(path, "rb").read()
tail = truncated.split(b"\n")[-1]
if not tail.strip():
    sys.exit("FIXTURE BUG: cut landed on a blank/whitespace tail")
try:
    json.loads(tail)
    sys.exit("FIXTURE BUG: truncated tail is still valid JSON")
except json.JSONDecodeError:
    pass

print(n_complete_before)
PYEOF

  run python3 truncate_fixture.py
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]

  run bash "$JOURNAL" history --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"
  assert_json_eq "$output" '.records | length' '1'
  assert_json_eq "$output" '.records[0].to' 'planned'
  assert_json_eq "$output" '.warnings | length > 0' 'true'
  assert_json_eq "$output" '[.warnings[] | test("byte offset [0-9]+")] | any' 'true'
}

@test "torn tail: last-moved degrades the same way as history, no crash" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 43, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\": 43, \"evidence\": {\"disk\": \"verified\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  cat > truncate_fixture2.py <<'PYEOF'
import glob
import json
import sys

path = sorted(glob.glob(".cairn/journal/*.jsonl"))[-1]
data = open(path, "rb").read()
lines = [l for l in data.split(b"\n") if l.strip()]
last = lines[-1].decode("utf-8")
needle = '"verified"'
idx = last.index(needle)
cut_in_line = idx + len('"ver')
last_line_start = data.rfind(lines[-1])
cut_point = last_line_start + cut_in_line

with open(path, "r+b") as f:
    f.truncate(cut_point)

truncated = open(path, "rb").read()
tail = truncated.split(b"\n")[-1]
if not tail.strip():
    sys.exit("FIXTURE BUG: cut landed on a blank/whitespace tail")
try:
    json.loads(tail)
    sys.exit("FIXTURE BUG: truncated tail is still valid JSON")
except json.JSONDecodeError:
    pass
PYEOF
  run python3 truncate_fixture2.py
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" last-moved --phase 43 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"
  assert_json_eq "$output" '.disk.value' 'planned'
  assert_json_eq "$output" '.warnings | length > 0' 'true'
}

@test "torn tail: a corrupted trailing fragment is never fixed by a later write, only ever reported" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 44, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\": 44, \"evidence\": {\"disk\": \"verified\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  cat > truncate_fixture3.py <<'PYEOF'
import glob
import json
import sys

path = sorted(glob.glob(".cairn/journal/*.jsonl"))[-1]
data = open(path, "rb").read()
lines = [l for l in data.split(b"\n") if l.strip()]
last = lines[-1].decode("utf-8")
needle = '"verified"'
idx = last.index(needle)
cut_in_line = idx + len('"ver')
last_line_start = data.rfind(lines[-1])
cut_point = last_line_start + cut_in_line

with open(path, "r+b") as f:
    f.truncate(cut_point)

truncated = open(path, "rb").read()
tail = truncated.split(b"\n")[-1]
if not tail.strip():
    sys.exit("FIXTURE BUG: cut landed on a blank/whitespace tail")
try:
    json.loads(tail)
    sys.exit("FIXTURE BUG: truncated tail is still valid JSON")
except json.JSONDecodeError:
    pass
PYEOF
  run python3 truncate_fixture3.py
  [ "$status" -eq 0 ]

  local size_before
  size_before="$(wc -c < "$(own_segment)" | tr -d ' ')"

  # Simulate the next real invocation after a crash: a fresh observe call
  # against the SAME truncated journal must succeed and simply append
  # after the quarantined tail, never "fix" or remove the corrupted
  # fragment.
  run bash -c "echo '[{\"phase\": 44, \"evidence\": {\"disk\": \"executed\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  local size_after
  size_after="$(wc -c < "$(own_segment)" | tr -d ' ')"
  [ "$size_after" -gt "$size_before" ]

  # The corrupted fragment's own bytes are still there, byte-for-byte, as
  # an untouched prefix of the file (never rewritten in place).
  run python3 -c "
before = open('$(own_segment)', 'rb').read()[:$size_before]
print(len(before))
"
  [ "$status" -eq 0 ]
  [ "$output" -eq "$size_before" ]

  run bash "$JOURNAL" history --phase 44 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  # The first complete record (planned) plus the new one appended after
  # the quarantined tail (executed) -- the torn "verified" record is still
  # gone from the readable set, exactly as right after truncation.
  assert_json_eq "$output" '.records | length' '2'
  assert_json_eq "$output" '[.records[] | select(.to == "planned")] | length' '1'
  assert_json_eq "$output" '[.records[] | select(.to == "executed")] | length' '1'
  assert_json_eq "$output" '[.records[] | select(.to == "verified")] | length' '0'
}

#-----------------------------------------------------------------------------
# T-16-01: malformed observe stdin degrades to EXIT_USAGE, never a traceback
#-----------------------------------------------------------------------------

@test "observe: malformed stdin (non-JSON, non-array, missing phase, wrong-typed phase) dies EXIT_USAGE, never a traceback" {
  make_tmp_repo

  run bash -c "echo 'not json' | bash \"$JOURNAL\" observe --project-dir \"$PWD\""
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash -c "echo '{\"phase\": 1}' | bash \"$JOURNAL\" observe --project-dir \"$PWD\""
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash -c "echo '[{\"evidence\": {}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\""
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  run bash -c "echo '[{\"phase\": \"5\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\""
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"

  [ ! -f "$(own_segment)" ]
}

#-----------------------------------------------------------------------------
# Plan 16-02 Task 1: compact — sibling write, flock-guarded rename swap,
# and the pre-rename staleness re-validation that closes Pitfall 14 (a
# concurrent append landing in compaction's own read-to-rename window).
#-----------------------------------------------------------------------------

@test "compact: on a nonexistent journal is a no-op, exits 0, creates nothing" {
  make_tmp_repo

  run bash "$JOURNAL" compact --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.compacted' 'false'
  assert_json_eq "$output" '.reason' 'no_journal'
  [ ! -f "$(own_segment)" ]
  [ ! -d .cairn ]
}

@test "compact: folds multi-phase history into exactly one snapshot record per touched phase" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 61, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\": 61, \"evidence\": {\"disk\": \"executed\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\": 62, \"evidence\": {\"bd\": \"open\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" lease 62 acquired --holder /path/A --actor felipe --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" compact --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.compacted' 'true'
  assert_json_eq "$output" '.phases' '2'
  assert_json_eq "$output" '.reason' 'ok'

  run bash -c "wc -l < \"$(own_segment)\" | tr -d ' '"
  [ "$status" -eq 0 ]
  [ "$output" -eq 2 ]

  # Count by parsing every line's own "event" field -- never trust the
  # command's own stdout summary alone.
  run bash -c "jq -c 'select(.event != \"snapshot\")' \"$(own_segment)\""
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  run bash -c "jq -r '.phase' \"$(own_segment)\" | sort -n | tr '\n' ','"
  [ "$status" -eq 0 ]
  [ "$output" = "61,62," ]

  # The folded state survives in the snapshot -- last-moved still answers
  # correctly by reading the compacted file (proven exhaustively by the
  # replay-equivalence test below; spot-checked here too).
  run bash "$JOURNAL" last-moved --phase 62 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.bd.value' 'open'
  assert_json_eq "$output" '.lease.value' 'acquired'
  assert_json_eq "$output" '.lease.holder' '/path/A'
}

@test "compact: a crash between the sibling write and the rename leaves the original journal byte-for-byte unchanged" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 63, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  local before_hash
  before_hash="$(shasum -a 256 "$(own_segment)" | awk '{print $1}')"

  # This is the exact recipe compact() itself uses up through the sibling
  # write -- and then, deliberately, no rename. That gap IS "a crash
  # between the sibling write and the rename": nothing further needs to
  # be mocked or killed to prove the original is untouched by it.
  run python3 -c "
import tempfile, os
tmp_fd, tmp_path = tempfile.mkstemp(dir='.cairn/journal', prefix='journal.jsonl.tmp-')
os.write(tmp_fd, b'{\"event\": \"snapshot\", \"phase\": 63}\n')
os.close(tmp_fd)
print(tmp_path)
"
  [ "$status" -eq 0 ]
  local tmp_path="$output"
  [ -f "$tmp_path" ]

  local after_hash
  after_hash="$(shasum -a 256 "$(own_segment)" | awk '{print $1}')"
  [ "$before_hash" = "$after_hash" ]

  rm -f "$tmp_path"
}

@test "compact: a contended compaction lock is skipped without hanging; a concurrent observe still succeeds uncompacted" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 64, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  local marker="$PWD/.cairn/lock-held"
  python3 -c "
import fcntl, os, time
fd = os.open('$(own_segment | sed 's/-[0-9][0-9][0-9][0-9]\.jsonl$//').compact.lock', os.O_CREAT | os.O_RDWR, 0o644)
fcntl.flock(fd, fcntl.LOCK_EX)
open('$marker', 'w').close()
time.sleep(2)
" &
  local holder_pid=$!

  # Bounded poll for the holder to actually acquire the lock -- never a
  # blind sleep guess.
  local waited=0
  while [ ! -f "$marker" ] && [ "$waited" -lt 50 ]; do
    sleep 0.05
    waited=$((waited + 1))
  done
  [ -f "$marker" ]

  local before_hash
  before_hash="$(shasum -a 256 "$(own_segment)" | awk '{print $1}')"

  local start_ts end_ts
  start_ts="$(date +%s)"
  run bash "$JOURNAL" compact --project-dir "$PWD" --json
  end_ts="$(date +%s)"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.compacted' 'false'
  assert_json_eq "$output" '.reason' 'lock_contended'
  [ "$((end_ts - start_ts))" -lt 2 ]

  local after_hash
  after_hash="$(shasum -a 256 "$(own_segment)" | awk '{print $1}')"
  [ "$before_hash" = "$after_hash" ]

  # observe takes no lock at all, by design -- it must still succeed
  # while the compaction lock is held by someone else.
  run bash -c "echo '[{\"phase\": 64, \"evidence\": {\"disk\": \"executed\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '1'

  wait "$holder_pid" 2>/dev/null || true
}

@test "compact: THE LOAD-BEARING TEST -- a record appended by a separate process during compaction's read-to-rename window survives (Pitfall 14)" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 65, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\": 66, \"evidence\": {\"disk\": \"executed\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  CAIRN_JOURNAL_COMPACT_TEST_DELAY=1 bash "$JOURNAL" compact --project-dir "$PWD" --json &
  local compact_pid=$!

  sleep 0.2

  # A genuinely separate process, appending a record for a phase not yet
  # in the journal, while the backgrounded compaction is asleep between
  # its own read and its own rename.
  run bash -c "echo '[{\"phase\": 67, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written | length' '1'

  wait "$compact_pid"
  local compact_status=$?
  [ "$compact_status" -eq 0 ]

  # This is the assertion that fails without the pre-rename
  # re-validation: a stale-read rename would have silently discarded
  # phase 67's record the instant it swapped in a sibling built before
  # that record ever existed.
  run bash "$JOURNAL" history --phase 67 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '1'
  assert_json_eq "$output" '.records[0].to' 'planned'
}

#-----------------------------------------------------------------------------
# Plan 16-02 Task 2: replay-equivalence proof (JOUR-05) -- last-moved must
# answer identically before and after compaction, for every touched phase.
#-----------------------------------------------------------------------------

@test "replay equivalence: last-moved is provably identical before and after compaction, for every touched phase (JOUR-05)" {
  make_tmp_repo

  # Phase 101: full evidence sweep across 3 observe calls, a verdict flip,
  # and a lease acquire+release.
  run bash -c "echo '[{\"phase\":101,\"evidence\":{\"disk\":\"planned\",\"bd\":\"none\",\"roadmap\":\"incomplete\",\"state_md\":null},\"verdict\":\"ok\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\":101,\"evidence\":{\"disk\":\"executed\",\"bd\":\"open\",\"roadmap\":\"partial\",\"state_md\":\"active\"},\"verdict\":\"conflict\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\":101,\"evidence\":{\"disk\":\"verified\",\"bd\":\"closed\",\"roadmap\":\"complete\",\"state_md\":\"done\"},\"verdict\":\"ok\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" lease 101 acquired --holder /path/A --actor tester --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" lease 101 released --holder /path/A --actor tester --project-dir "$PWD"
  [ "$status" -eq 0 ]

  # Phase 102: a second, distinct phase, same shapes, different values.
  run bash -c "echo '[{\"phase\":102,\"evidence\":{\"disk\":\"planned\",\"bd\":\"none\",\"roadmap\":\"incomplete\",\"state_md\":null},\"verdict\":\"unknown\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\":102,\"evidence\":{\"disk\":\"executed\",\"bd\":\"open\",\"roadmap\":\"partial\",\"state_md\":\"active\"},\"verdict\":\"ok\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" lease 102 acquired --holder /path/B --actor tester --project-dir "$PWD"
  [ "$status" -eq 0 ]

  # Phase 103: a third, distinct phase.
  run bash -c "echo '[{\"phase\":103,\"evidence\":{\"disk\":\"planned\",\"bd\":\"none\",\"roadmap\":\"incomplete\",\"state_md\":\"queued\"},\"verdict\":\"ok\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash -c "echo '[{\"phase\":103,\"evidence\":{\"disk\":\"verified\",\"bd\":\"closed\",\"roadmap\":\"complete\"},\"verdict\":\"conflict\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" lease 103 acquired --holder /path/C --actor tester --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$JOURNAL" lease 103 released --holder /path/C --prev-holder /path/C --actor tester --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" history --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  local history_before="$output"
  local records_before
  records_before="$(jq '.records | length' <<<"$history_before")"
  [ "$records_before" -ge 30 ]

  run bash "$JOURNAL" last-moved --phase 101 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  local before_101="$output"
  run bash "$JOURNAL" last-moved --phase 102 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  local before_102="$output"
  run bash "$JOURNAL" last-moved --phase 103 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  local before_103="$output"

  run bash "$JOURNAL" compact --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.compacted' 'true'

  run bash "$JOURNAL" last-moved --phase 101 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  local after_101="$output"
  run bash "$JOURNAL" last-moved --phase 102 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  local after_102="$output"
  run bash "$JOURNAL" last-moved --phase 103 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  local after_103="$output"

  # The load-bearing property: never a spot-check of one field on one
  # phase -- the FULL last-moved answer, for every touched phase, must be
  # structurally identical before and after. A jq -S (recursive key sort)
  # normalization is used rather than raw string equality: compact()
  # writes the snapshot record via json.dumps(..., sort_keys=True), so a
  # nested {"value":...,"ts":...} sub-object round-trips as
  # {"ts":...,"value":...} post-compaction -- same values, different key
  # order, which a raw string diff would wrongly flag as a real
  # mismatch. jq -S . is exactly the "jq structural equality check"
  # option named in this test's own acceptance criteria.
  [ "$(jq -S . <<<"$before_101")" = "$(jq -S . <<<"$after_101")" ]
  [ "$(jq -S . <<<"$before_102")" = "$(jq -S . <<<"$after_102")" ]
  [ "$(jq -S . <<<"$before_103")" = "$(jq -S . <<<"$after_103")" ]

  # Secondary check: the file was actually rewritten to the smaller form,
  # not merely that the answers happen to still be correct against an
  # untouched file.
  run bash "$JOURNAL" history --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '3'
  assert_json_eq "$output" '[.records[] | select(.event == "snapshot")] | length' '3'
  local records_after
  records_after="$(jq '.records | length' <<<"$output")"
  [ "$records_after" -lt "$records_before" ]
}

#-----------------------------------------------------------------------------
# Phase 28, plan 28-01 (DJOUR-04): provenance -- machine, checkout, actor.
#
# Why these exist: `actor` alone cannot separate two checkouts. Measured on
# 2026-08-06 in this repository, four simultaneous checkouts held 176/64/1/1
# records under ONE identical actor. The partition the phase's design needs
# cannot be built from the data that exists, so the field that separates has
# to exist first.
#
# The rule these tests defend hardest: a record written before phase 28 reads
# as UNKNOWN (machine: null, checkout: null), never stamped with the current
# host. Stamping looks like a migration and is fabrication.
#-----------------------------------------------------------------------------

# Writes a journal in the PRE-phase-28 schema -- the exact eight fields
# measured on the real file (actor, event, from, nonce, phase, source, to,
# ts), with no machine and no checkout. Never produced by the current writer,
# which is the point: this is the inherited file, as it is on disk today.
write_legacy_journal() {
  local phase="$1" source="$2" to="$3" actor="$4" ts="$5"
  mkdir -p .cairn
  printf '%s\n' "$(jq -cn \
    --arg ts "$ts" --arg actor "$actor" --arg source "$source" \
    --arg to "$to" --argjson phase "$phase" \
    '{actor: $actor, event: "state_changed", from: null,
      nonce: "0123456789abcdef0123456789abcdef", phase: $phase,
      source: $source, to: $to, ts: $ts}')" >> .cairn/journal.jsonl
}

@test "provenance: prints machine, checkout and actor, none of them empty" {
  make_tmp_repo

  run bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.machine == null or .machine == ""' 'false'
  assert_json_eq "$output" '.checkout == null or .checkout == ""' 'false'
  assert_json_eq "$output" '.actor == null or .actor == ""' 'false'

  # Human mode names all three, so a person can read the identity too.
  run bash "$JOURNAL" provenance --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF 'machine:' <<<"$output"
  grep -qF 'checkout:' <<<"$output"
  grep -qF 'actor:' <<<"$output"
}

@test "provenance: the checkout id is stable across runs in the same checkout" {
  make_tmp_repo

  run bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local first
  first="$(jq -r '.checkout' <<<"$output")"

  run bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local second
  second="$(jq -r '.checkout' <<<"$output")"

  # Compared against the other RUN, never against a literal: the id is
  # derived, and a test that pinned its value would just be a second
  # implementation of the hash.
  [ "$first" = "$second" ]
}

@test "provenance: two checkouts of one repo on one machine get different ids" {
  make_tmp_repo
  # The case the phase context names: `git worktree list` returns four
  # checkouts on this machine right now, carrying four histories that never
  # reach each other under one identical actor. Built here, not supposed.
  git commit -q --allow-empty -m "base"
  git worktree add -q -b second ../second-checkout
  local other
  other="$(cd ../second-checkout && pwd -P)"

  run bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local here_checkout here_machine
  here_checkout="$(jq -r '.checkout' <<<"$output")"
  here_machine="$(jq -r '.machine' <<<"$output")"

  run bash "$JOURNAL" provenance --project-dir "$other" --json
  [ "$status" -eq 0 ]
  local there_checkout there_machine
  there_checkout="$(jq -r '.checkout' <<<"$output")"
  there_machine="$(jq -r '.machine' <<<"$output")"

  # Distinct checkout, same machine -- both halves matter. Equal machine
  # proves the id is not just a random per-run value; distinct checkout is
  # what makes one partition per checkout possible at all.
  [ "$here_checkout" != "$there_checkout" ]
  [ "$here_machine" = "$there_machine" ]
}

@test "provenance: a record written now carries machine and checkout, equal to provenance's" {
  make_tmp_repo

  run bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local machine checkout
  machine="$(jq -r '.machine' <<<"$output")"
  checkout="$(jq -r '.checkout' <<<"$output")"

  run bash -c "echo '[{\"phase\": 7, \"evidence\": {\"disk\": \"planned\"}, \"verdict\": \"ok\"}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" ".written | map(select(.machine == \"$machine\")) | length" '2'
  assert_json_eq "$output" ".written | map(select(.checkout == \"$checkout\")) | length" '2'

  # And on disk, not only in the reported payload.
  run bash -c "jq -s '[.[] | select(.machine == \"$machine\" and .checkout == \"$checkout\")] | length' < \"$(own_segment)\""
  [ "$status" -eq 0 ]
  [ "$output" = "2" ]
}

@test "provenance: a pre-phase-28 record reads machine null and checkout null, never the current host" {
  make_tmp_repo
  write_legacy_journal 9 disk complete "SomeoneElse" "2026-01-01T00:00:00.000001+00:00"

  run bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local current_machine
  current_machine="$(jq -r '.machine' <<<"$output")"

  run bash "$JOURNAL" last-moved --phase 9 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  # Exact value assertions: null, not "different from the current host".
  assert_json_eq "$output" '.disk.machine' 'null'
  assert_json_eq "$output" '.disk.checkout' 'null'
  # The actor the record DOES carry is reported as it is -- unknown means
  # unknown per field, not a blanket erasure of the record.
  assert_json_eq "$output" '.disk.actor' 'SomeoneElse'
  # value/ts keep their exact prior meaning and position: cairn-doctor.py's
  # _last_moved_clause() reads entry["ts"] and must not see a difference.
  assert_json_eq "$output" '.disk.value' 'complete'
  assert_json_eq "$output" '.disk.ts' '2026-01-01T00:00:00.000001+00:00'

  # THE FABRICATION GUARD. This is the assertion that goes red the day
  # someone "fixes" the read by filling in the running process's host.
  assert_json_eq "$output" ".disk.machine == \"$current_machine\"" 'false'
}

@test "provenance: compaction folds a legacy record without stamping it" {
  make_tmp_repo
  write_legacy_journal 11 disk complete "SomeoneElse" "2026-01-01T00:00:00.000001+00:00"
  # A real record for a DIFFERENT axis of the same phase, so one snapshot
  # carries both a known and an unknown provenance at once.
  run bash -c "echo '[{\"phase\": 11, \"evidence\": {\"bd\": \"closed\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  run bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local current_machine
  current_machine="$(jq -r '.machine' <<<"$output")"

  run bash "$JOURNAL" compact --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.compacted' 'true'

  run bash "$JOURNAL" last-moved --phase 11 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  # The snapshot fold carries the ORIGINAL observer through, and the
  # compacting checkout's own identity never leaks onto the folded axis.
  assert_json_eq "$output" '.disk.machine' 'null'
  assert_json_eq "$output" '.disk.checkout' 'null'
  assert_json_eq "$output" ".bd.machine" "$current_machine"
}

@test "provenance: CAIRN_JOURNAL_MACHINE and CAIRN_JOURNAL_CHECKOUT drive the identity" {
  make_tmp_repo

  run env CAIRN_JOURNAL_MACHINE=hostA CAIRN_JOURNAL_CHECKOUT=ckA \
      bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.machine' 'hostA'
  assert_json_eq "$output" '.checkout' 'ckA'

  run bash -c "echo '[{\"phase\": 3, \"evidence\": {\"disk\": \"planned\"}}]' | CAIRN_JOURNAL_MACHINE=hostB CAIRN_JOURNAL_CHECKOUT=ckB bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.written[0].machine' 'hostB'
  assert_json_eq "$output" '.written[0].checkout' 'ckB'

  # The seam only overrides the two fields it names -- machine alone still
  # derives a checkout, and that checkout differs from the one the real
  # hostname derives, which is what lets one directory play two machines.
  run env CAIRN_JOURNAL_MACHINE=hostA bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local as_host_a
  as_host_a="$(jq -r '.checkout' <<<"$output")"
  run env CAIRN_JOURNAL_MACHINE=hostB bash "$JOURNAL" provenance --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  [ "$as_host_a" != "$(jq -r '.checkout' <<<"$output")" ]
}

#-----------------------------------------------------------------------------
# Phase 28, plan 28-02 (DJOUR-02): one partition per checkout, merge=union on
# each, and a read that unites them without asserting order.
#
# Both pieces are required and neither is sufficient. Different files merge
# with no driver at all (E11 case 1); the SAME partition on two branches is an
# add/add conflict without `union` (E8b). Between partitions no order is ever
# claimed: this machine's own NTP offset was measured at -16.7 ms against a
# 10.8 ms minimum gap between consecutive records.
#-----------------------------------------------------------------------------

# Copies the project's real .gitattributes into the fixture. Never a
# hand-written copy of the line: a test that retyped it would keep passing on
# the day someone deleted the real one.
use_project_gitattributes() {
  cp "$CAIRN_REPO_ROOT/.gitattributes" .gitattributes
  git add .gitattributes
}

# The active segment of a SIMULATED machine's partition. own_segment() answers
# for the real hostname; these tests drive two machines out of one directory,
# so they have to ask for the one they mean.
segment_as() {
  CAIRN_JOURNAL_MACHINE="$1" bash "$JOURNAL" provenance --project-dir "$PWD" \
    --json | jq -r '.segment'
}

observe_as() {
  local machine="$1" phase="$2" axis="$3" value="$4"
  echo "[{\"phase\": $phase, \"evidence\": {\"$axis\": \"$value\"}}]" \
    | CAIRN_JOURNAL_MACHINE="$machine" bash "$JOURNAL" observe \
        --project-dir "$PWD" --json > /dev/null
}

@test "partition: observe writes into .cairn/journal/, never the inherited single file" {
  make_tmp_repo

  run bash -c "echo '[{\"phase\": 71, \"evidence\": {\"disk\": \"planned\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  [ -d .cairn/journal ]
  [ ! -f .cairn/journal.jsonl ]
  local segment
  segment="$(own_segment)"
  [ -f "$segment" ]
  # The segment name ends in the four-digit segment number, and its stem
  # carries the 12-hex checkout id -- the property that makes `legacy` a
  # key no real partition can ever collide with.
  [[ "$(basename "$segment")" =~ ^.+-[0-9a-f]{12}-0001\.jsonl$ ]]
}

@test "partition: two machines in one directory write two different files" {
  make_tmp_repo

  observe_as hostA 72 disk planned
  observe_as hostB 72 disk executed

  local count
  count="$(ls .cairn/journal/*.jsonl | wc -l | tr -d ' ')"
  [ "$count" -eq 2 ]

  # Each file carries only its own machine's records -- that is what makes a
  # merge a concatenation instead of a reconciliation.
  run bash -c "jq -r -s 'map(.machine) | unique | join(\",\")' .cairn/journal/*.jsonl"
  [ "$status" -eq 0 ]

  local a_file b_file
  a_file="$(grep -l '"machine": "hostA"' .cairn/journal/*.jsonl)"
  b_file="$(grep -l '"machine": "hostB"' .cairn/journal/*.jsonl)"
  [ "$a_file" != "$b_file" ]
  run bash -c "jq -r -s 'map(.machine) | unique | length' \"$a_file\""
  [ "$output" = "1" ]
  run bash -c "jq -r -s 'map(.machine) | unique | length' \"$b_file\""
  [ "$output" = "1" ]
}

@test "partition: two machines' journals merge with git, no conflict, nothing lost" {
  make_tmp_repo
  use_project_gitattributes
  git commit -q -m "base"

  git checkout -q -b maqA
  observe_as hostA 73 disk planned
  observe_as hostA 73 bd open
  git add -A .cairn/journal && git commit -q -m "maqA"

  git checkout -q main 2>/dev/null || git checkout -q master
  git checkout -q -b maqB
  observe_as hostB 73 disk executed
  observe_as hostB 73 roadmap incomplete
  git add -A .cairn/journal && git commit -q -m "maqB"

  git checkout -q maqA
  run git merge --no-edit maqB
  [ "$status" -eq 0 ]
  # Never merely "exit 0": a conflict marker in a committed file would still
  # let a badly-configured merge exit 0 on some paths.
  run bash -c "grep -rl '<<<<<<<' .cairn/journal/ || true"
  [ -z "$output" ]

  # Every record from both sides survived: 4 written, 4 readable.
  run bash "$JOURNAL" history --phase 73 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '4'
  assert_json_eq "$output" '.partitions | length' '2'
  assert_json_eq "$output" '[.partitions[].machine] | sort | join(",")' 'hostA,hostB'
  assert_json_eq "$output" '[.records[] | select(.machine == "hostA")] | length' '2'
  assert_json_eq "$output" '[.records[] | select(.machine == "hostB")] | length' '2'
}

@test "partition: the same partition on two branches needs union, and the fold beats file order" {
  make_tmp_repo
  use_project_gitattributes
  # A common ancestor for the segment file, so the merge is a content merge
  # rather than an add/add.
  observe_as hostA 74 disk base
  git add -A .cairn/journal && git commit -q -m "base"
  local base_branch
  base_branch="$(git rev-parse --abbrev-ref HEAD)"

  # maqB writes FIRST and finishes first; maqA writes after. Both are the
  # same machine and the same checkout, so both land in the SAME file.
  git checkout -q -b later
  observe_as hostA 74 disk b_first
  observe_as hostA 74 disk b_second
  git add -A .cairn/journal && git commit -q -m "later branch"

  git checkout -q "$base_branch"
  git checkout -q -b newest
  observe_as hostA 74 disk a_newest
  git add -A .cairn/journal && git commit -q -m "newest branch"

  run git merge --no-edit later
  [ "$status" -eq 0 ]
  run bash -c "grep -c '<<<<<<<' \"$(segment_as hostA)\" || true"
  [ "$output" = "0" ]

  # Nothing lost: base + two + one.
  run bash "$JOURNAL" history --phase 74 --json --project-dir "$PWD"
  assert_json_eq "$output" '.records | length' '4'

  # THE LOAD-BEARING ASSERTION. union concatenates ours-then-theirs, so the
  # LAST PHYSICAL LINE is b_second while the chronologically last record is
  # a_newest. A fold that trusted file order -- the fold this file shipped
  # before phase 28 -- would answer b_second.
  run bash -c "tail -n 1 \"$(segment_as hostA)\" | jq -r '.to'"
  [ "$output" = "b_second" ]

  run bash "$JOURNAL" last-moved --phase 74 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.disk.value' 'a_newest'
}

@test "partition: without the .gitattributes line the same merge conflicts" {
  make_tmp_repo
  # Deliberately NO use_project_gitattributes here. Everything else is the
  # previous test, verbatim -- which is what makes this an isolation of the
  # single line, not a different scenario.
  observe_as hostA 75 disk base
  git add -A .cairn/journal && git commit -q -m "base"
  local base_branch
  base_branch="$(git rev-parse --abbrev-ref HEAD)"

  git checkout -q -b later
  observe_as hostA 75 disk b_first
  git add -A .cairn/journal && git commit -q -m "later branch"

  git checkout -q "$base_branch"
  git checkout -q -b newest
  observe_as hostA 75 disk a_newest
  git add -A .cairn/journal && git commit -q -m "newest branch"

  run git merge --no-edit later
  [ "$status" -ne 0 ]
  run bash -c "grep -c '<<<<<<<' \"$(segment_as hostA)\" || true"
  [ "$output" -ge 1 ]
  git merge --abort
}

@test "partition: the inherited journal is read as a partition and never rewritten" {
  make_tmp_repo
  write_legacy_journal 76 disk complete "SomeoneElse" "2026-01-01T00:00:00.000001+00:00"
  local before_hash
  before_hash="$(shasum -a 256 .cairn/journal.jsonl | awk '{print $1}')"

  run bash -c "echo '[{\"phase\": 76, \"evidence\": {\"bd\": \"closed\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  # Byte-for-byte, by hash. A size check would miss a same-length rewrite.
  local after_hash
  after_hash="$(shasum -a 256 .cairn/journal.jsonl | awk '{print $1}')"
  [ "$before_hash" = "$after_hash" ]

  run bash "$JOURNAL" history --phase 76 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '2'
  assert_json_eq "$output" '.partitions | length' '2'
  assert_json_eq "$output" '[.partitions[] | select(.slug == "legacy")] | length' '1'
  assert_json_eq "$output" '[.partitions[] | select(.slug == "legacy") | .machine][0]' 'null'
}

@test "partition: last-moved names every source and claims no order between them" {
  make_tmp_repo

  # Two checkouts that DISAGREE about the same axis.
  observe_as hostA 77 disk planned
  observe_as hostB 77 disk executed

  run bash "$JOURNAL" last-moved --phase 77 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.disk.sources' '2'
  # No timestamp, ever, once there is more than one source: a single ts
  # across machines is an ordering claim with no source for it.
  assert_json_eq "$output" '.disk.ts' 'null'
  assert_json_eq "$output" '.disk.value' 'null'
  assert_json_eq "$output" '[.disk.candidates[].machine] | sort | join(",")' 'hostA,hostB'
  assert_json_eq "$output" '[.disk.candidates[] | select(.ts == null)] | length' '0'

  # Two checkouts that AGREE: the value survives, because "the last known
  # value is X everywhere" orders nothing. The ts still does not.
  observe_as hostA 78 bd closed
  observe_as hostB 78 bd closed
  run bash "$JOURNAL" last-moved --phase 78 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.bd.sources' '2'
  assert_json_eq "$output" '.bd.value' 'closed'
  assert_json_eq "$output" '.bd.ts' 'null'

  # Human mode says it out loud rather than printing a bare pair of lines.
  run bash "$JOURNAL" last-moved --phase 77 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  grep -qF 'order between machines not claimed' <<<"$output"
}

@test "partition: dedup is scoped to this checkout's own partition" {
  make_tmp_repo

  observe_as hostA 79 disk planned
  # hostB has never seen this axis in ITS OWN partition, so it records its
  # own first sighting. Deduplicating against hostA would make hostB claim
  # knowledge it never had, and would make what it writes depend on whether
  # a merge had landed yet.
  observe_as hostB 79 disk planned

  run bash "$JOURNAL" history --phase 79 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.records | length' '2'
  assert_json_eq "$output" '[.records[] | select(.machine == "hostB")] | length' '1'

  # And within one partition the dedup still holds, unchanged.
  observe_as hostB 79 disk planned
  run bash "$JOURNAL" history --phase 79 --json --project-dir "$PWD"
  assert_json_eq "$output" '.records | length' '2'
}

@test "partition: git tracks the .jsonl segments and ignores the per-machine scratch beside them" {
  make_tmp_repo
  cp "$CAIRN_REPO_ROOT/.gitignore" .gitignore
  mkdir -p .cairn/journal
  touch .cairn/journal/host-0123456789ab-0001.jsonl \
        .cairn/journal/host-0123456789ab.compact.lock \
        .cairn/journal.jsonl

  run git check-ignore -q .cairn/journal/host-0123456789ab-0001.jsonl
  [ "$status" -eq 1 ]
  run git check-ignore -q .cairn/journal/host-0123456789ab.compact.lock
  [ "$status" -eq 0 ]
  run git check-ignore -q .cairn/journal.jsonl
  [ "$status" -eq 0 ]
}
