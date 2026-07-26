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

# Canned claude payloads, byte-identical in field names/nesting to the REAL
# `claude -p --output-format json` responses captured live 2026-07-25 (see
# benchmarks/results/smoke-convert.jsonl). The live schema carries many fields
# beyond the published docs (terminal_reason, stop_reason, uuid, modelUsage,
# permission_denials, fast_mode_*, usage.cache_creation, usage.server_tool_use,
# usage.service_tier, usage.iterations, ...); the harness must pass all of them
# through untouched. Field asymmetry mirrors the live capture: `result`,
# `api_error_status` and `time_to_request_ms` appear only on success; `errors`
# only on error subtypes. usage + total_cost_usd are present on BOTH.
# Caveat proven live: `subtype` alone is NOT a success signal — an auth-failure
# api_error emits subtype:"success" WITH is_error:true; read is_error /
# terminal_reason instead.
SUCCESS_JSON='{"type":"result","subtype":"success","api_error_status":null,"duration_ms":1200,"duration_api_ms":900,"time_to_request_ms":50,"ttft_ms":300,"ttft_stream_ms":150,"is_error":false,"num_turns":2,"result":"done","session_id":"stub-session-0000","uuid":"stub-uuid-0000","stop_reason":"end_turn","terminal_reason":"completed","total_cost_usd":0.0031,"fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","permission_denials":[],"modelUsage":{"claude-haiku-4-5-20251001":{"inputTokens":812,"outputTokens":140,"cacheReadInputTokens":0,"cacheCreationInputTokens":0,"webSearchRequests":0,"costUSD":0.0031,"contextWindow":200000,"maxOutputTokens":32000,"canonicalModel":"claude-haiku-4-5","provider":"firstParty"}},"usage":{"input_tokens":812,"output_tokens":140,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"server_tool_use":{"web_fetch_requests":0,"web_search_requests":0},"service_tier":"standard","speed":"standard","inference_geo":"not_available","iterations":[]}}'
ERROR_JSON='{"type":"result","subtype":"error_max_turns","duration_ms":5000,"duration_api_ms":4500,"is_error":true,"num_turns":5,"errors":["Reached maximum number of turns (5)"],"session_id":"stub-session-0001","uuid":"stub-uuid-0001","stop_reason":"tool_use","terminal_reason":"max_turns","total_cost_usd":0.0102,"fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","permission_denials":[],"modelUsage":{"claude-haiku-4-5-20251001":{"inputTokens":2048,"outputTokens":512,"cacheReadInputTokens":0,"cacheCreationInputTokens":0,"webSearchRequests":0,"costUSD":0.0102,"contextWindow":200000,"maxOutputTokens":32000,"canonicalModel":"claude-haiku-4-5","provider":"firstParty"}},"usage":{"input_tokens":2048,"output_tokens":512,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"server_tool_use":{"web_fetch_requests":0,"web_search_requests":0},"service_tier":"standard","speed":"standard","inference_geo":"not_available","iterations":[]}}'

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
  # Live-schema fields absent from the published docs must flow through
  # untouched (schema captured live, benchmarks/results/smoke-convert.jsonl).
  assert_json_eq "$row" '.terminal_reason' 'completed'
  run jq -e 'has("wall_clock_ms") and has("modelUsage") and (.usage | has("cache_creation"))' \
    "$BATS_TEST_TMPDIR/raw1.jsonl"
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
  # Error-only live fields (errors[], terminal_reason) also pass through.
  run jq -e 'has("errors") and .terminal_reason == "max_turns"' \
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
