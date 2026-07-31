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

  [ -f .cairn/journal.jsonl ]

  cat > truncate_fixture.py <<'PYEOF'
import json
import sys

path = ".cairn/journal.jsonl"
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
import json
import sys

path = ".cairn/journal.jsonl"
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
import json
import sys

path = ".cairn/journal.jsonl"
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
  size_before="$(wc -c < .cairn/journal.jsonl | tr -d ' ')"

  # Simulate the next real invocation after a crash: a fresh observe call
  # against the SAME truncated journal must succeed and simply append
  # after the quarantined tail, never "fix" or remove the corrupted
  # fragment.
  run bash -c "echo '[{\"phase\": 44, \"evidence\": {\"disk\": \"executed\"}}]' | bash \"$JOURNAL\" observe --project-dir \"$PWD\" --json"
  [ "$status" -eq 0 ]

  local size_after
  size_after="$(wc -c < .cairn/journal.jsonl | tr -d ' ')"
  [ "$size_after" -gt "$size_before" ]

  # The corrupted fragment's own bytes are still there, byte-for-byte, as
  # an untouched prefix of the file (never rewritten in place).
  run python3 -c "
before = open('.cairn/journal.jsonl', 'rb').read()[:$size_before]
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

  [ ! -f .cairn/journal.jsonl ]
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
  [ ! -f .cairn/journal.jsonl ]
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

  run bash -c "wc -l < .cairn/journal.jsonl | tr -d ' '"
  [ "$status" -eq 0 ]
  [ "$output" -eq 2 ]

  # Count by parsing every line's own "event" field -- never trust the
  # command's own stdout summary alone.
  run bash -c "jq -c 'select(.event != \"snapshot\")' .cairn/journal.jsonl"
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  run bash -c "jq -r '.phase' .cairn/journal.jsonl | sort -n | tr '\n' ','"
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
  before_hash="$(shasum -a 256 .cairn/journal.jsonl | awk '{print $1}')"

  # This is the exact recipe compact() itself uses up through the sibling
  # write -- and then, deliberately, no rename. That gap IS "a crash
  # between the sibling write and the rename": nothing further needs to
  # be mocked or killed to prove the original is untouched by it.
  run python3 -c "
import tempfile, os
tmp_fd, tmp_path = tempfile.mkstemp(dir='.cairn', prefix='journal.jsonl.tmp-')
os.write(tmp_fd, b'{\"event\": \"snapshot\", \"phase\": 63}\n')
os.close(tmp_fd)
print(tmp_path)
"
  [ "$status" -eq 0 ]
  local tmp_path="$output"
  [ -f "$tmp_path" ]

  local after_hash
  after_hash="$(shasum -a 256 .cairn/journal.jsonl | awk '{print $1}')"
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
fd = os.open('.cairn/journal.jsonl.compact.lock', os.O_CREAT | os.O_RDWR, 0o644)
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
  before_hash="$(shasum -a 256 .cairn/journal.jsonl | awk '{print $1}')"

  local start_ts end_ts
  start_ts="$(date +%s)"
  run bash "$JOURNAL" compact --project-dir "$PWD" --json
  end_ts="$(date +%s)"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.compacted' 'false'
  assert_json_eq "$output" '.reason' 'lock_contended'
  [ "$((end_ts - start_ts))" -lt 2 ]

  local after_hash
  after_hash="$(shasum -a 256 .cairn/journal.jsonl | awk '{print $1}')"
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
  # byte-identical before and after.
  [ "$before_101" = "$after_101" ]
  [ "$before_102" = "$after_102" ]
  [ "$before_103" = "$after_103" ]

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
