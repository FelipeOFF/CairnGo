#!/usr/bin/env bats
# bench-run.bats — exercises bench-run.py / bench-run.sh's CLI contract:
# fixture staging, claude subprocess invocation via the CAIRN_BENCH_CLAUDE_BIN
# stub seam, one JSONL row per run wired to the real smoke-convert verify.sh,
# zero API cost. Never invokes the real claude binary.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so positive substring checks use grep -qF and
# negative checks use refute_in_output.

load 'helpers'

BENCH_SCRIPTS_DIR="$CAIRN_REPO_ROOT/benchmarks/scripts"
BENCH_TASKS_DIR="$CAIRN_REPO_ROOT/benchmarks/tasks"

# Canned claude payloads, byte-identical in field names/shape to the verified
# `claude -p --output-format json` result schema (usage + total_cost_usd are
# present on BOTH success and error subtypes).
SUCCESS_JSON='{"type":"result","subtype":"success","duration_ms":1200,"duration_api_ms":900,"is_error":false,"num_turns":2,"result":"done","session_id":"stub-session-0000","total_cost_usd":0.0031,"usage":{"input_tokens":812,"output_tokens":140,"cache_creation_input_tokens":0,"cache_read_input_tokens":0}}'
ERROR_JSON='{"type":"result","subtype":"error_max_turns","duration_ms":5000,"duration_api_ms":4500,"is_error":true,"num_turns":5,"session_id":"stub-session-0001","total_cost_usd":0.0102,"usage":{"input_tokens":2048,"output_tokens":512,"cache_creation_input_tokens":0,"cache_read_input_tokens":0}}'

# make_claude_stub NAME JSON_BODY EXIT_CODE — write an executable stub to
# $BATS_TEST_TMPDIR/$NAME that emits JSON_BODY on stdout then exits EXIT_CODE.
make_claude_stub() {
  local name="$1" json_body="$2" exit_code="$3"
  STUB="$BATS_TEST_TMPDIR/$name"
  {
    printf '#!/usr/bin/env bash\n'
    printf "cat <<'JSON'\n"
    printf '%s\n' "$json_body"
    printf 'JSON\n'
    printf 'exit %s\n' "$exit_code"
  } > "$STUB"
  chmod +x "$STUB"
}

@test "writes one JSONL row wired to the real verify.sh; verify_passed reflects the unsolved fixture" {
  make_claude_stub claude-success "$SUCCESS_JSON" 0
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    bash "$BENCH_SCRIPTS_DIR/bench-run.sh" \
      --task "$BENCH_TASKS_DIR/smoke-convert" --out "$BATS_TEST_TMPDIR/raw1.jsonl"
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$BATS_TEST_TMPDIR/raw1.jsonl")" -eq 1 ]
  row="$(cat "$BATS_TEST_TMPDIR/raw1.jsonl")"
  assert_json_eq "$row" '.task_id' 'smoke-convert'
  assert_json_eq "$row" '.total_cost_usd' '0.0031'
  # The stub never actually edits convert.py, so the real verify.sh genuinely
  # fails: verify_passed is wired to a REAL check, not hardcoded.
  assert_json_eq "$row" '.verify_passed' 'false'
  run jq -e 'has("wall_clock_ms")' "$BATS_TEST_TMPDIR/raw1.jsonl"
  [ "$status" -eq 0 ]
}

@test "error-subtype JSON is parsed even though the stub exits non-zero" {
  make_claude_stub claude-error "$ERROR_JSON" 1
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    bash "$BENCH_SCRIPTS_DIR/bench-run.sh" \
      --task "$BENCH_TASKS_DIR/smoke-convert" --out "$BATS_TEST_TMPDIR/raw2.jsonl"
  [ "$status" -eq 0 ]
  row="$(cat "$BATS_TEST_TMPDIR/raw2.jsonl")"
  assert_json_eq "$row" '.is_error' 'true'
  # Cost/usage must survive an error subtype: JSON parsing is never gated on
  # the subprocess return code.
  run jq -e 'has("usage") and has("total_cost_usd") and has("wall_clock_ms")' \
    "$BATS_TEST_TMPDIR/raw2.jsonl"
  [ "$status" -eq 0 ]
}

# wall_clock_ms is the one intentionally-excluded field below: an inherently
# non-deterministic external timing measurement — HARN-02 still requires it
# present in every row (proven by the two tests above), but by its very nature
# it cannot be part of a byte-identical comparison.
@test "running twice against identical stub input yields byte-identical JSONL, wall-clock excluded" {
  make_claude_stub claude-success "$SUCCESS_JSON" 0
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    bash "$BENCH_SCRIPTS_DIR/bench-run.sh" \
      --task "$BENCH_TASKS_DIR/smoke-convert" --out "$BATS_TEST_TMPDIR/raw_a.jsonl"
  [ "$status" -eq 0 ]
  run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    bash "$BENCH_SCRIPTS_DIR/bench-run.sh" \
      --task "$BENCH_TASKS_DIR/smoke-convert" --out "$BATS_TEST_TMPDIR/raw_b.jsonl"
  [ "$status" -eq 0 ]
  run diff \
    <(jq -S 'del(.wall_clock_ms)' "$BATS_TEST_TMPDIR/raw_a.jsonl") \
    <(jq -S 'del(.wall_clock_ms)' "$BATS_TEST_TMPDIR/raw_b.jsonl")
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
