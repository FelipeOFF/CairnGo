#!/usr/bin/env bats
# bench-chart.bats — exercises the deterministic aggregated.json -> SVG chart
# layer (bench-chart.py): CLI usage errors that write nothing, byte-identical
# double-run determinism, exact value correctness (every rendered number
# traces to a fixture cell — no rounding drift, no invented numbers), the
# null-median honesty rule (no fabricated zero-value bars; an explicit
# "no data" marker still paired with its real pass-rate text), XML escaping
# of hostile task/baseline ids proven by a well-formedness parse, verbatim
# --label captions, the empty-cells edge case, and the phase's
# zero-SVG-committed repo-hygiene rule — all against static synthetic
# fixtures, zero API cost. Never invokes the claude binary at all.
#
# Assertion style note (same as bench-aggregate.bats): a failing `[[ ]]` or
# `! cmd` mid-test does NOT fail a bats test on this bash, so positive checks
# use `run` + status asserts / `grep -qF` pipelines, and negative checks use
# `run bash -c "grep -c ... || true"` asserting the literal count "0".

load 'helpers'

BENCH_SCRIPTS_DIR="$CAIRN_REPO_ROOT/benchmarks/scripts"
FIXTURES_DIR="$CAIRN_REPO_ROOT/tests/fixtures"
CHART_PY="$BENCH_SCRIPTS_DIR/bench-chart.py"
CHART_FIXTURE="$FIXTURES_DIR/chart-aggregate.json"
LABEL="claude-haiku-4-5-20251001 - 2026-07-26"
SLUG="claude-haiku-4-5-20251001-2026-07-26"

# Generate both charts from the committed fixture into out-dir $1, assert
# exit 0. Leaves $BATS_TEST_TMPDIR-scoped SVGs behind for the caller.
gen_charts() {
  run python3 "$CHART_PY" \
    --in "$CHART_FIXTURE" --out-dir "$1" --label "$LABEL"
  [ "$status" -eq 0 ]
}

@test "missing --in / --out-dir / --label and a nonexistent --in each die EXIT_USAGE naming the flag, writing no SVG" {
  run python3 "$CHART_PY" --out-dir "$BATS_TEST_TMPDIR/out" --label "$LABEL"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--in'
  run python3 "$CHART_PY" --in "$CHART_FIXTURE" --label "$LABEL"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--out-dir'
  run python3 "$CHART_PY" --in "$CHART_FIXTURE" --out-dir "$BATS_TEST_TMPDIR/out"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--label'
  run python3 "$CHART_PY" --in "$BATS_TEST_TMPDIR/does-not-exist.json" \
    --out-dir "$BATS_TEST_TMPDIR/out" --label "$LABEL"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF -- '--in'
  # None of the failed invocations above may have written any SVG anywhere.
  run bash -c "find \"$BATS_TEST_TMPDIR\" -name '*.svg' | wc -l | tr -d ' '"
  [ "$status" -eq 0 ]
  [ "$output" = "0" ]
}

@test "running twice with identical --in and --label yields byte-identical cost.svg and tokens.svg" {
  gen_charts "$BATS_TEST_TMPDIR/run1"
  gen_charts "$BATS_TEST_TMPDIR/run2"
  # Slugified --label drives both filenames.
  [ -f "$BATS_TEST_TMPDIR/run1/$SLUG-cost.svg" ]
  [ -f "$BATS_TEST_TMPDIR/run1/$SLUG-tokens.svg" ]
  run diff "$BATS_TEST_TMPDIR/run1/$SLUG-cost.svg" \
           "$BATS_TEST_TMPDIR/run2/$SLUG-cost.svg"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  run diff "$BATS_TEST_TMPDIR/run1/$SLUG-tokens.svg" \
           "$BATS_TEST_TMPDIR/run2/$SLUG-tokens.svg"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "every rendered value matches its fixture cell exactly — cost \$X.XXXX, pass-rate N/M (P%), integer token medians" {
  gen_charts "$BATS_TEST_TMPDIR/vals"
  COST="$BATS_TEST_TMPDIR/vals/$SLUG-cost.svg"
  TOK="$BATS_TEST_TMPDIR/vals/$SLUG-tokens.svg"
  # Cost medians, formatted $X.XXXX — one bar-value text per non-null cell.
  run grep -c 'class="bar-value"' "$COST"
  [ "$output" = "3" ]
  grep -qF -- '>$0.1234<' "$COST"
  grep -qF -- '>$0.2000<' "$COST"
  grep -qF -- '>$0.3500<' "$COST"
  # Pass rates, formatted N/M (P%) — one per cell, no exceptions (4 cells).
  run grep -c 'class="bar-passrate"' "$COST"
  [ "$output" = "4" ]
  grep -qF -- '>4/5 (80%)<' "$COST"
  grep -qF -- '>0/3 (0%)<' "$COST"
  grep -qF -- '>5/5 (100%)<' "$COST"
  grep -qF -- '>2/3 (67%)<' "$COST"
  # Token medians, integer-rounded, class-scoped to the fixed 4-segment
  # order — microedit-greet::alpha's exact fixture values (57.5 -> 58).
  run grep -qE 'class="token-seg-input"[^>]*>13</text>' "$TOK"
  [ "$status" -eq 0 ]
  run grep -qE 'class="token-seg-cache_creation"[^>]*>115</text>' "$TOK"
  [ "$status" -eq 0 ]
  run grep -qE 'class="token-seg-cache_read"[^>]*>215</text>' "$TOK"
  [ "$status" -eq 0 ]
  run grep -qE 'class="token-seg-output"[^>]*>58</text>' "$TOK"
  [ "$status" -eq 0 ]
  # Spot-check the other two non-null cells' segments.
  run grep -qE 'class="token-seg-cache_read"[^>]*>300</text>' "$TOK"
  [ "$status" -eq 0 ]
  run grep -qE 'class="token-seg-cache_read"[^>]*>400</text>' "$TOK"
  [ "$status" -eq 0 ]
}

@test "null-median honesty: no fabricated bar, an explicit 'no data' marker, pass-rate text still real" {
  gen_charts "$BATS_TEST_TMPDIR/honesty"
  COST="$BATS_TEST_TMPDIR/honesty/$SLUG-cost.svg"
  TOK="$BATS_TEST_TMPDIR/honesty/$SLUG-tokens.svg"
  # Exactly one no-data marker per chart (the microedit-greet::beta cell),
  # reading exactly "no data".
  run grep -c 'class="bar-nodata"' "$COST"
  [ "$output" = "1" ]
  run grep -c 'class="bar-nodata"' "$TOK"
  [ "$output" = "1" ]
  grep -qF -- '>no data<' "$COST"
  grep -qF -- '>no data<' "$TOK"
  # The null cell renders NO bar-value and NO token segments: 3 bar-value
  # texts (not 4), and 6 token-seg-input hits (3 rects + 3 texts, not 8).
  run grep -c 'class="bar-value"' "$COST"
  [ "$output" = "3" ]
  run grep -c 'class="token-seg-input"' "$TOK"
  [ "$output" = "6" ]
  # ... while its pass-rate text is still present and real: 0/3 (0%).
  grep -qF -- '>0/3 (0%)<' "$COST"
}

@test "XML-hostile ids are escaped, never raw, and both SVGs stay well-formed" {
  gen_charts "$BATS_TEST_TMPDIR/escape"
  COST="$BATS_TEST_TMPDIR/escape/$SLUG-cost.svg"
  TOK="$BATS_TEST_TMPDIR/escape/$SLUG-tokens.svg"
  # The raw unescaped id substring must never appear in either document.
  run bash -c "grep -cF 'smoke&convert<x>' \"$COST\" || true"
  [ "$output" = "0" ]
  run bash -c "grep -cF 'smoke&convert<x>' \"$TOK\" || true"
  [ "$output" = "0" ]
  # The escaped form does.
  grep -qF -- 'smoke&amp;convert&lt;x&gt;' "$COST"
  grep -qF -- 'smoke&amp;convert&lt;x&gt;' "$TOK"
  # Well-formedness proof: a strict XML parser accepts both documents.
  run python3 -c "import xml.dom.minidom, sys; xml.dom.minidom.parse(sys.argv[1])" "$COST"
  [ "$status" -eq 0 ]
  run python3 -c "import xml.dom.minidom, sys; xml.dom.minidom.parse(sys.argv[1])" "$TOK"
  [ "$status" -eq 0 ]
}

@test "the --label caption appears verbatim in a chart-caption text element in both SVGs" {
  gen_charts "$BATS_TEST_TMPDIR/caption"
  COST="$BATS_TEST_TMPDIR/caption/$SLUG-cost.svg"
  TOK="$BATS_TEST_TMPDIR/caption/$SLUG-tokens.svg"
  run grep -qE "class=\"chart-caption\"[^>]*>$LABEL</text>" "$COST"
  [ "$status" -eq 0 ]
  run grep -qE "class=\"chart-caption\"[^>]*>$LABEL</text>" "$TOK"
  [ "$status" -eq 0 ]
}

@test "an empty cells object still writes two valid SVGs carrying the caption and a 'no data collected yet' text" {
  printf '{"cells":{},"rejected_rows":0}\n' > "$BATS_TEST_TMPDIR/empty.json"
  run python3 "$CHART_PY" --in "$BATS_TEST_TMPDIR/empty.json" \
    --out-dir "$BATS_TEST_TMPDIR/empty-out" --label "$LABEL"
  [ "$status" -eq 0 ]
  COST="$BATS_TEST_TMPDIR/empty-out/$SLUG-cost.svg"
  TOK="$BATS_TEST_TMPDIR/empty-out/$SLUG-tokens.svg"
  [ -f "$COST" ]
  [ -f "$TOK" ]
  grep -qF -- 'no data collected yet' "$COST"
  grep -qF -- 'no data collected yet' "$TOK"
  grep -qF -- 'class="chart-caption"' "$COST"
  grep -qF -- 'class="chart-caption"' "$TOK"
  run python3 -c "import xml.dom.minidom, sys; xml.dom.minidom.parse(sys.argv[1])" "$COST"
  [ "$status" -eq 0 ]
  run python3 -c "import xml.dom.minidom, sys; xml.dom.minidom.parse(sys.argv[1])" "$TOK"
  [ "$status" -eq 0 ]
}

@test "repo hygiene: every committed chart is backed by committed real data (honesty rule)" {
  # The rule this guards is "no chart made of synthetic numbers", not "no
  # chart". Before the first collection the directory was empty and that was
  # the whole check. Now that real runs exist, the rule is checked directly:
  # a committed SVG requires a committed aggregation, which in turn requires
  # the raw JSONL it was derived from.
  run bash -c "git -C \"$CAIRN_REPO_ROOT\" ls-files -- benchmarks/charts | grep -c '\\.svg\$' || true"
  charts="$output"

  if [ "$charts" = "0" ]; then
    skip "no committed charts yet; the rule has nothing to check"
  fi

  # An aggregation must be committed alongside them.
  run bash -c "git -C \"$CAIRN_REPO_ROOT\" ls-files -- benchmarks/results | grep -c 'aggregated\\.json\$' || true"
  [ "$output" != "0" ]

  # And raw rows must back that aggregation: at least one committed matrix
  # JSONL carrying a real cost field, never a hand-written stub.
  run bash -c "git -C \"$CAIRN_REPO_ROOT\" ls-files -- benchmarks/results | grep -c 'matrix.*\\.jsonl\$' || true"
  [ "$output" != "0" ]

  run bash -c "grep -l 'total_cost_usd' \"$CAIRN_REPO_ROOT\"/benchmarks/results/matrix*.jsonl | wc -l | tr -d ' '"
  [ "$output" != "0" ]
}
