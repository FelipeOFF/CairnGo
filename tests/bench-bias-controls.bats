#!/usr/bin/env bats
# bench-bias-controls.bats — CI-enforced proof of Phase 5's bias-control
# decisions (05-CONTEXT.md): every corpus task carries a `category`, exactly
# one is labeled "honest-non-win", no prompt favors an arm by name, the
# README's Cost model section cannot silently drift out of sync with the
# corpus (doc-rot guard), the Variance pilot is documented PENDING, and the
# honest-non-win task runs through the harness with no category-based
# special-casing. Zero API cost — static file assertions plus stubbed runs.

load 'helpers'

BENCH_TASKS_DIR="$CAIRN_REPO_ROOT/benchmarks/tasks"
README="$CAIRN_REPO_ROOT/benchmarks/README.md"

# extract_section HEADING FILE — print the text between a `## HEADING` line
# and the next `## ` heading (or EOF).
extract_section() {
  local heading="$1" file="$2"
  awk -v h="## $heading" '
    $0 == h {found=1; next}
    found && /^## / {exit}
    found {print}
  ' "$file"
}

@test "every task.json in the corpus declares a non-empty category" {
  for f in "$BENCH_TASKS_DIR"/*/task.json; do
    run jq -e '.category | type == "string" and length > 0' "$f"
    [ "$status" -eq 0 ]
  done
}

@test "exactly one corpus task is labeled honest-non-win" {
  run bash -c "jq -r '.category' '$BENCH_TASKS_DIR'/*/task.json | grep -cFx 'honest-non-win'"
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]
}

@test "no task prompt favors an arm by name (cairn/gsd/ralph), case-insensitive" {
  for f in "$BENCH_TASKS_DIR"/*/prompt.md; do
    run grep -qiE 'cairn|gsd|ralph' "$f"
    [ "$status" -ne 0 ]
  done
}

@test "README Cost model section names every corpus task id" {
  run grep -qF "## Cost model" "$README"
  [ "$status" -eq 0 ]
  extract_section "Cost model" "$README" > "$BATS_TEST_TMPDIR/cost-section.txt"
  for f in "$BENCH_TASKS_DIR"/*/task.json; do
    task_id="$(jq -r '.id' "$f")"
    run grep -qF "$task_id" "$BATS_TEST_TMPDIR/cost-section.txt"
    [ "$status" -eq 0 ]
  done
}

@test "README Task corpus section documents all 6 categories" {
  extract_section "Task corpus" "$README" > "$BATS_TEST_TMPDIR/corpus-section.txt"
  [ -s "$BATS_TEST_TMPDIR/corpus-section.txt" ]
  for category in smoke bugfix feature refactor honest-non-win long-horizon; do
    run grep -qF "$category" "$BATS_TEST_TMPDIR/corpus-section.txt"
    [ "$status" -eq 0 ]
  done
}

@test "README documents the variance pilot as PENDING" {
  extract_section "Variance pilot (CORP-01)" "$README" > "$BATS_TEST_TMPDIR/pilot-section.txt"
  [ -s "$BATS_TEST_TMPDIR/pilot-section.txt" ]
  run grep -qF "PENDING" "$BATS_TEST_TMPDIR/pilot-section.txt"
  [ "$status" -eq 0 ]
}

@test "the honest-non-win task runs through bench-run.py identically across differently-provisioned baselines (no category special-casing)" {
  make_env_asserting_claude_stub
  mkdir -p "$BATS_TEST_TMPDIR/fake-plugin-dir"
  for name in bare-arm plugin-arm; do
    if [ "$name" = "bare-arm" ]; then
      provisioning='{"plugin_dirs": []}'
    else
      provisioning="{\"plugin_dirs\": [{\"plugin\": \"fake\", \"source\": {\"type\": \"local_path\", \"path\": \"fake\"}, \"staged_path\": \"$BATS_TEST_TMPDIR/fake-plugin-dir\", \"build\": []}]}"
    fi
    cat > "$BATS_TEST_TMPDIR/$name.json" <<EOF
{"name": "$name", "model": "claude-haiku-4-5-20251001",
 "claude_flags": {"bare": true, "max_turns": 8, "no_session_persistence": true, "permission_mode": "acceptEdits"},
 "provisioning": $provisioning}
EOF
    run env CAIRN_BENCH_CLAUDE_BIN="$STUB" \
      python3 "$CAIRN_REPO_ROOT/benchmarks/scripts/bench-run.py" \
        --task "$BENCH_TASKS_DIR/microedit-greet" \
        --baseline "$BATS_TEST_TMPDIR/$name.json" \
        --out "$BATS_TEST_TMPDIR/$name-out.jsonl"
    [ "$status" -eq 0 ]
    run jq -e ".task_id == \"microedit-greet\" and .category == \"honest-non-win\" and .baseline_id == \"$name\"" \
      "$BATS_TEST_TMPDIR/$name-out.jsonl"
    [ "$status" -eq 0 ]
  done
}
