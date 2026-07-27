#!/usr/bin/env bats
# bench-all.bats — proves bench-all.sh's safety contract mechanically, at $0:
#   * --dry-run/--yes are mutually exclusive; --yes without ANTHROPIC_API_KEY
#     dies a usage error before any pipeline step;
#   * the dry-run default invokes ZERO downstream scripts — proven by a
#     tripwire CAIRN_BENCH_SCRIPTS_DIR full of sentinel-touching stubs, not by
#     code inspection;
#   * the full stage -> matrix -> aggregate -> chart -> publish pipeline runs
#     end-to-end against the CAIRN_BENCH_CLAUDE_BIN stub, filling a TEMP COPY
#     of BENCHMARKS.md — the real repo files are never touched;
#   * no GitHub workflow references bench-all.sh (the never-in-CI invariant,
#     same absence-grep style as bench-bias-controls.bats' neutrality check).
#
# Assertion style note (same as bench-run.bats/bench-matrix.bats): a failing
# `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this bash, so
# positive checks use `run` + status / `echo | grep -qF` and negative checks
# assert on `run` status explicitly.

load 'helpers'

BENCH_SCRIPTS_DIR="$CAIRN_REPO_ROOT/benchmarks/scripts"
BENCH_ALL="$BENCH_SCRIPTS_DIR/bench-all.sh"

# make_tripwire_scripts_dir — populate $BATS_TEST_TMPDIR/tripwire-scripts with
# the five downstream script names, each an executable python3 stub that (if
# ever invoked) touches $BATS_TEST_TMPDIR/INVOKED-<name> and exits 1. Any
# sentinel appearing after a dry-run is mechanical proof the zero-invocation
# contract broke.
make_tripwire_scripts_dir() {
  TRIPWIRE_DIR="$BATS_TEST_TMPDIR/tripwire-scripts"
  mkdir -p "$TRIPWIRE_DIR"
  local name
  for name in stage-plugins.py bench-matrix.py bench-aggregate.py \
              bench-chart.py bench-publish.py; do
    cat > "$TRIPWIRE_DIR/$name" <<EOF
#!/usr/bin/env python3
import pathlib, sys
pathlib.Path("$BATS_TEST_TMPDIR/INVOKED-$name").touch()
sys.exit(1)
EOF
    chmod +x "$TRIPWIRE_DIR/$name"
  done
}

@test "--dry-run and --yes together die exit 2 (mutually exclusive)" {
  run env -u ANTHROPIC_API_KEY bash "$BENCH_ALL" --dry-run --yes
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "mutually exclusive"
}

@test "--yes without ANTHROPIC_API_KEY dies exit 2 naming the key, before plan or any pipeline step" {
  run env -u ANTHROPIC_API_KEY bash "$BENCH_ALL" --yes
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "ANTHROPIC_API_KEY"
  printf '%s\n' "$output" > "$BATS_TEST_TMPDIR/yes-nokey.out"
  # Dies BEFORE the plan print and before any step line.
  run grep -F "total_runs" "$BATS_TEST_TMPDIR/yes-nokey.out"
  [ "$status" -ne 0 ]
  run grep -F "step " "$BATS_TEST_TMPDIR/yes-nokey.out"
  [ "$status" -ne 0 ]

  # Empty-but-set key is just as absent as unset.
  run env ANTHROPIC_API_KEY= bash "$BENCH_ALL" --yes
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "ANTHROPIC_API_KEY"
}

@test "tripwire: dry-run (explicit, no-flags default, and no-flags with a key set) invokes zero downstream scripts" {
  make_tripwire_scripts_dir
  cd "$CAIRN_REPO_ROOT"

  run env -u ANTHROPIC_API_KEY CAIRN_BENCH_SCRIPTS_DIR="$TRIPWIRE_DIR" \
    bash "$BENCH_ALL" --dry-run
  [ "$status" -eq 0 ]
  echo "$output" | grep -qE 'total_runs:[[:space:]]+120'
  echo "$output" | grep -qF '$40'
  echo "$output" | grep -qF "DRY-RUN"

  # No flags at all, key unset: the default is dry-run.
  run env -u ANTHROPIC_API_KEY CAIRN_BENCH_SCRIPTS_DIR="$TRIPWIRE_DIR" \
    bash "$BENCH_ALL"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF "DRY-RUN"
  echo "$output" | grep -qF '$40'

  # No flags with a key PRESENT: still dry-run — spend is never inferred
  # from the environment (only an explicit --yes can go live).
  run env ANTHROPIC_API_KEY="tripwire-dummy-key" \
    CAIRN_BENCH_SCRIPTS_DIR="$TRIPWIRE_DIR" bash "$BENCH_ALL"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qF "DRY-RUN"
  echo "$output" | grep -qF "ANTHROPIC_API_KEY present: yes"

  # The mechanical proof: not one sentinel exists — zero scripts invoked.
  run bash -c "ls \"$BATS_TEST_TMPDIR\"/INVOKED-* 2>/dev/null"
  [ "$status" -ne 0 ]
}

@test "full pipeline end-to-end against the claude stub: \$0, temp BENCHMARKS.md Results filled" {
  make_env_asserting_claude_stub
  cp "$CAIRN_REPO_ROOT/BENCHMARKS.md" "$BATS_TEST_TMPDIR/BENCHMARKS.md"
  cp "$CAIRN_REPO_ROOT/README.md" "$BATS_TEST_TMPDIR/README.md"
  cd "$CAIRN_REPO_ROOT"

  run env ANTHROPIC_API_KEY="bench-all-bats-dummy-key" \
    CAIRN_BENCH_CLAUDE_BIN="$STUB" \
    bash "$BENCH_ALL" --yes \
      --tasks "$CAIRN_REPO_ROOT/benchmarks/tasks/smoke-convert" \
      --baselines vanilla \
      --baselines-dir "$CAIRN_REPO_ROOT/benchmarks/baselines" \
      --reps 1 \
      --out "$BATS_TEST_TMPDIR/out" \
      --charts-dir "$BATS_TEST_TMPDIR/charts" \
      --benchmarks "$BATS_TEST_TMPDIR/BENCHMARKS.md" \
      --readme "$BATS_TEST_TMPDIR/README.md"
  [ "$status" -eq 0 ]
  # Plan printed first even on the live path; key value never echoed.
  echo "$output" | grep -qF "LIVE"
  echo "$output" | grep -qF '$40'
  printf '%s\n' "$output" > "$BATS_TEST_TMPDIR/live.out"
  run grep -F "bench-all-bats-dummy-key" "$BATS_TEST_TMPDIR/live.out"
  [ "$status" -ne 0 ]

  # matrix.jsonl: exactly one row (1 task x 1 baseline x 1 rep).
  [ "$(wc -l < "$BATS_TEST_TMPDIR/out/matrix.jsonl")" -eq 1 ]

  # aggregated.json: exactly one cell.
  run jq -e '(.cells | length) == 1' "$BATS_TEST_TMPDIR/out/aggregated.json"
  [ "$status" -eq 0 ]

  # At least one chart SVG rendered.
  run bash -c "ls \"$BATS_TEST_TMPDIR\"/charts/*.svg"
  [ "$status" -eq 0 ]

  # Temp BENCHMARKS.md generated block: smoke-convert/vanilla row present,
  # pending notice gone.
  sed -n '/cairn:generated:benchmarks:start/,/cairn:generated:benchmarks:end/p' \
    "$BATS_TEST_TMPDIR/BENCHMARKS.md" > "$BATS_TEST_TMPDIR/gen-block.txt"
  run grep -F "smoke-convert" "$BATS_TEST_TMPDIR/gen-block.txt"
  [ "$status" -eq 0 ]
  run grep -F "vanilla" "$BATS_TEST_TMPDIR/gen-block.txt"
  [ "$status" -eq 0 ]
  run grep -F "Pending first collection" "$BATS_TEST_TMPDIR/gen-block.txt"
  [ "$status" -ne 0 ]

  # Surrounding prose (Methodology/Raw data/Reproduction/Changelog) is
  # byte-identical to the committed original once the generated region is
  # stripped from both.
  sed '/cairn:generated:benchmarks:start/,/cairn:generated:benchmarks:end/d' \
    "$BATS_TEST_TMPDIR/BENCHMARKS.md" > "$BATS_TEST_TMPDIR/temp-outside.txt"
  sed '/cairn:generated:benchmarks:start/,/cairn:generated:benchmarks:end/d' \
    "$CAIRN_REPO_ROOT/BENCHMARKS.md" > "$BATS_TEST_TMPDIR/real-outside.txt"
  run diff "$BATS_TEST_TMPDIR/temp-outside.txt" "$BATS_TEST_TMPDIR/real-outside.txt"
  [ "$status" -eq 0 ]
}

@test "never-in-CI invariant: no GitHub workflow references bench-all.sh" {
  # Same absence-grep style as the task-prompt neutrality check: bench-all.sh
  # is a deliberately manual, operator-invoked command (its --yes path spends
  # real money) and must never appear in any automated trigger. Any match
  # here is a violation to be consciously reviewed, not silenced.
  run grep -rn "bench-all" "$CAIRN_REPO_ROOT/.github/workflows/"
  [ "$status" -ne 0 ]
}

@test "repo hygiene: real BENCHMARKS.md/README.md/results/charts untouched by this file's tests" {
  run git -C "$CAIRN_REPO_ROOT" status --porcelain -- \
    BENCHMARKS.md README.md benchmarks/results benchmarks/charts
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
