#!/usr/bin/env bats
# cairn-trend.bats — exercises the cross-cycle trend reader's CLI contract
# (cairn-trend.py / the cairn-trend.sh wrapper).
#
# What is under test here:
#   cycle states  TREND-01/02 — a cycle whose verification files carry no
#                 frontmatter is `not-applicable` with a NAMED scope, never a
#                 zero. Proved by the break that matters: a not-applicable
#                 cycle must not move any denominator, so the anchor test
#                 asserts the aggregate is identical with and without it.
#   derivation    TREND-02 — the output is a view of the disk. Proved by
#                 ADDING a verification file and asserting the verdict moves
#                 with no prose edited anywhere. A test that compared against
#                 a literal would not prove derivation.
#
# Exit codes under test: 0 ok, 2 usage, 4 insufficient (no series).
#
# Assertion style notes:
#   - every status assertion is on the EXACT value (`-eq 4`), never `-ne 0`:
#     a negation accepts the wrong code and hides a regression.
#   - a failing `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this
#     bash, so substring checks use grep -qF and negatives use refute_output.
#   - no test hard-codes a milestone key or a count taken from this
#     repository's own tree. This repo has three measured precedents of a
#     hand-typed count going stale ("fifteen checks" with sixteen, "17
#     checks" with nineteen, "18 checks" against "nineteen" in one file); a
#     literal in here would be the fourth, wearing a test's clothes.

load 'helpers'

TREND="$CAIRN_SCRIPTS_DIR/cairn-trend.sh"

# --- fixture builders, local to this file -----------------------------------
# helpers.bash is loaded by thirty suites and is not touched for one phase's
# shape; the precedent is make_gsd_surface in cairn-wrap.bats.

# A fresh .planning/ tree, path exported in TREND_PLANNING.
new_planning() {
  local base
  base="$(mktemp -d "${BATS_TEST_TMPDIR:-${TMPDIR:-/tmp}}/trend.XXXXXX")"
  TREND_PLANNING="$base/.planning"
  mkdir -p "$TREND_PLANNING/milestones"
  printf '# Roadmap\n\n## Milestones\n\n' > "$TREND_PLANNING/ROADMAP.md"
}

# archive_cycle KEY — an archived milestone: the <key>-ROADMAP.md that is the
# evidence a cycle closed, plus its phase tree.
archive_cycle() {
  printf '# %s archived roadmap\n' "$1" \
    > "$TREND_PLANNING/milestones/$1-ROADMAP.md"
  mkdir -p "$TREND_PLANNING/milestones/$1-phases"
  printf -- '- shipped **%s**\n' "$1" >> "$TREND_PLANNING/ROADMAP.md"
}

# open_cycle KEY — the in-progress marker the roadmap carries.
open_cycle() {
  printf -- '- 🚧 **%s** — em andamento\n' "$1" >> "$TREND_PLANNING/ROADMAP.md"
  mkdir -p "$TREND_PLANNING/phases"
}

cycle_phases_dir() {
  if [ -d "$TREND_PLANNING/milestones/$1-phases" ]; then
    printf '%s' "$TREND_PLANNING/milestones/$1-phases"
  else
    printf '%s' "$TREND_PLANNING/phases"
  fi
}

# add_verified KEY NN STATUS [extra frontmatter lines...]
add_verified() {
  local key="$1" nn="$2" status="$3"
  shift 3
  local dir line
  dir="$(cycle_phases_dir "$key")/$nn-phase"
  mkdir -p "$dir"
  {
    printf -- '---\n'
    printf 'phase: %s-phase\n' "$nn"
    printf 'verified: 2026-01-01T00:00:00Z\n'
    printf 'status: %s\n' "$status"
    printf 'score: 4/4 must-haves verified\n'
    printf 'overrides_applied: 0\n'
    for line in "$@"; do printf '%s\n' "$line"; done
    printf -- '---\n\n# report\n'
  } > "$dir/$nn-VERIFICATION.md"
}

# add_bare KEY NN — a verification file with no frontmatter at all. This is
# the real shape of v1.2 and v1.3: the input exists, the format does not.
add_bare() {
  local dir
  dir="$(cycle_phases_dir "$1")/$2-phase"
  mkdir -p "$dir"
  printf '# Phase %s Verification\n\nprosa, sem frontmatter.\n' "$2" \
    > "$dir/$2-VERIFICATION.md"
}

# add_unverified KEY NN — a phase directory with no verification file.
add_unverified() {
  mkdir -p "$(cycle_phases_dir "$1")/$2-phase"
}

trend() { run "$TREND" --planning-dir "$TREND_PLANNING" "$@"; }

# jq over the last `trend --json` output.
tjq() { printf '%s' "$output" | jq -r "$1"; }

# --- cycle discovery and the fourth state -----------------------------------

@test "a cycle whose files carry frontmatter is comparable, with its counts" {
  new_planning
  archive_cycle v1.1
  add_verified v1.1 01 passed
  add_verified v1.1 02 passed
  add_verified v1.1 03 gaps_found

  trend --json
  # 4 and not 0: one comparable cycle is fewer than a series needs, so the
  # sufficiency verdict is already in force. Exact value, never a negation.
  [ "$status" -eq 4 ]
  [ "$(tjq '.cycles[0].state')" = "comparable" ]
  [ "$(tjq '.cycles[0].scope')" = "null" ]
  [ "$(tjq '.cycles[0].status_counts.passed')" -eq 2 ]
  [ "$(tjq '.cycles[0].status_counts.gaps_found')" -eq 1 ]
}

@test "files with no frontmatter are not-applicable / no-frontmatter, not zero" {
  new_planning
  archive_cycle v1.2
  add_bare v1.2 07
  add_bare v1.2 08
  add_bare v1.2 09

  trend --json
  [ "$status" -eq 4 ]
  # Exact values on both fields: `no-input` here would be the misreading that
  # erases the fact — the input exists, the format does not.
  [ "$(tjq '.cycles[0].state')" = "not-applicable" ]
  [ "$(tjq '.cycles[0].scope')" = "no-frontmatter" ]
  [ "$(tjq '.cycles[0].verification_files')" -eq 3 ]
  [ "$(tjq '.cycles[0].with_frontmatter')" -eq 0 ]
  # And it is NOT in the comparable set — the whole reason for the state.
  [ "$(tjq '[.comparable[]] | length')" -eq 0 ]
}

@test "a cycle with no verification file at all is not-applicable / no-input" {
  new_planning
  archive_cycle v1.0
  add_unverified v1.0 01

  trend --json
  [ "$status" -eq 4 ]
  [ "$(tjq '.cycles[0].state')" = "not-applicable" ]
  [ "$(tjq '.cycles[0].scope')" = "no-input" ]
}

@test "frontmatter with no status is no-verdict, distinct from no-frontmatter" {
  new_planning
  archive_cycle v1.0
  local dir
  dir="$(cycle_phases_dir v1.0)/01-phase"
  mkdir -p "$dir"
  printf -- '---\nphase: 01-phase\nscore: 2/2 must-haves verified\n---\n' \
    > "$dir/01-VERIFICATION.md"

  trend --json
  [ "$status" -eq 4 ]
  [ "$(tjq '.cycles[0].scope')" = "no-verdict" ]
  [ "$(tjq '.cycles[0].with_frontmatter')" -eq 1 ]
}

@test "ANCHOR: a not-applicable cycle moves no denominator and adds no point" {
  # The defect the roadmap's `**Depende de:**` names: summing "passed" with
  # "nobody checked it that way" measures repo health and tool coverage in
  # one column. Proved by building the same tree twice, once with the
  # no-frontmatter cycle present, and asserting three aggregates are
  # identical. Three, because the contamination has three different shapes
  # and one assertion only sees one of them:
  #   points  — the cycle sneaking into the series as a fourth point. A
  #             sum-of-verdicts assertion is BLIND to this: the intruder
  #             contributes zero verdicts, so the sum never moves. Measured
  #             here by breaking the source (classify() forced to comparable)
  #             and watching only this line go red.
  #   verdicts— its phases counted as phases that did not pass.
  #   files   — its files counted as the denominator instead of its verdicts,
  #             which is the likelier of the two spellings of the same error.
  new_planning
  archive_cycle v1.1
  add_verified v1.1 01 passed
  add_verified v1.1 02 gaps_found
  trend --json
  local points_before verdicts_before files_before
  points_before="$(tjq '.comparable | length')"
  verdicts_before="$(tjq '[.cycles[] | select(.state == "comparable")
                           | .with_verdict] | add')"
  files_before="$(tjq '[.cycles[] | select(.state == "comparable")
                        | .verification_files] | add')"

  archive_cycle v1.2
  add_bare v1.2 07
  add_bare v1.2 08
  add_bare v1.2 09
  trend --json

  [ "$(tjq '.comparable | length')" -eq "$points_before" ]
  [ "$(tjq '[.cycles[] | select(.state == "comparable")
             | .with_verdict] | add')" -eq "$verdicts_before" ]
  [ "$(tjq '[.cycles[] | select(.state == "comparable")
             | .verification_files] | add')" -eq "$files_before" ]
  # The cycle IS in the table, though — declared, never dropped.
  [ "$(tjq '[.cycles[].cycle] | length')" -eq 2 ]
}

@test "the open cycle is marked open and the archived ones are not" {
  new_planning
  archive_cycle v1.4
  add_verified v1.4 13 passed
  open_cycle v1.5
  add_verified v1.5 20 passed

  trend --json
  [ "$status" -eq 4 ]
  [ "$(tjq '.cycles[0].cycle')" = "v1.4" ]
  [ "$(tjq '.cycles[0].open')" = "false" ]
  [ "$(tjq '.cycles[1].cycle')" = "v1.5" ]
  [ "$(tjq '.cycles[1].open')" = "true" ]
}

@test "cycles come back in version order with the open one last" {
  new_planning
  archive_cycle v1.10
  add_verified v1.10 40 passed
  archive_cycle v1.2
  add_verified v1.2 07 passed
  archive_cycle v1.9
  add_verified v1.9 30 passed
  open_cycle v1.11
  add_verified v1.11 50 passed

  trend --json
  [ "$(tjq '[.cycles[].cycle] | join(",")')" = "v1.2,v1.9,v1.10,v1.11" ]
}

@test "no .planning at all exits 0 and says so instead of printing a table" {
  local base
  base="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/trend-empty.XXXXXX")"
  mkdir -p "$base/.planning"
  TREND_PLANNING="$base/.planning"

  trend
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF "nenhum ciclo encontrado"
}

# --- the human table --------------------------------------------------------

@test "the table shows a not-applicable cycle as its scope, never as a zero" {
  new_planning
  archive_cycle v1.1
  add_verified v1.1 01 passed
  archive_cycle v1.2
  add_bare v1.2 07
  add_bare v1.2 08

  trend
  [ "$status" -eq 4 ]
  local na_line
  na_line="$(printf '%s' "$output" | grep -F ' v1.2 ')"
  printf '%s' "$na_line" | grep -qF "not-applicable / no-frontmatter"
  # The break this guards: rendering the cycle as `veredito em 0/2 fases`,
  # a true ratio that reads as "approved nothing".
  if printf '%s' "$na_line" | grep -qE '\b0/'; then
    echo "the not-applicable line rendered a zero ratio: $na_line" >&2
    return 1
  fi
  # The reason survives into the human output, not only the JSON.
  printf '%s' "$output" | grep -qF "o insumo existe, o formato não"
}

@test "the open cycle carries its reason; a tree with none does not" {
  new_planning
  archive_cycle v1.4
  add_verified v1.4 13 passed
  open_cycle v1.5
  add_verified v1.5 20 passed
  trend
  printf '%s' "$output" | grep -qF "está em andamento"

  new_planning
  archive_cycle v1.4
  add_verified v1.4 13 passed
  trend
  if printf '%s' "$output" | grep -qF "está em andamento"; then
    echo "the open-cycle caveat printed with no open cycle" >&2
    return 1
  fi
}

# --- derivation: the output moves when the disk moves ------------------------

@test "ADDING a verification file turns a no-frontmatter cycle comparable" {
  # The proof pattern this cycle has already exercised twice: put a file on
  # disk and assert the verdict changes with NO prose edited anywhere. A test
  # comparing against a literal would not prove derivation.
  new_planning
  archive_cycle v1.2
  add_bare v1.2 07
  add_bare v1.2 08
  trend --json
  [ "$(tjq '.cycles[0].state')" = "not-applicable" ]
  [ "$(tjq '.comparable | length')" -eq 0 ]

  add_verified v1.2 09 passed

  trend --json
  [ "$(tjq '.cycles[0].state')" = "comparable" ]
  [ "$(tjq '.cycles[0].scope')" = "null" ]
  [ "$(tjq '.comparable | length')" -eq 1 ]
}

@test "ADDING a phase directory with no verdict moves coverage, not the verdict" {
  new_planning
  archive_cycle v1.4
  add_verified v1.4 13 passed
  trend --json
  local before
  before="$(tjq '.cycles[0].coverage')"

  add_unverified v1.4 19

  trend --json
  [ "$(tjq '.cycles[0].coverage')" != "$before" ]
  # The unverified phase is NOT a failed phase: the pass count is untouched.
  [ "$(tjq '.cycles[0].status_counts.passed')" -eq 1 ]
}

# --- this repository's own tree ---------------------------------------------
# Nothing below types a milestone key or a count. Both ends of every
# assertion are read from disk inside the test.

@test "real tree: every archived roadmap and the open cycle appear" {
  local planning="$CAIRN_REPO_ROOT/.planning"
  [ -d "$planning/milestones" ] || skip "no archived milestone in this tree"
  run "$TREND" --planning-dir "$planning" --json
  [ "$status" -eq 0 ]

  local key f
  for f in "$planning"/milestones/*-ROADMAP.md; do
    key="$(basename "$f" -ROADMAP.md)"
    printf '%s' "$output" | jq -e --arg k "$key" \
      '[.cycles[].cycle] | index($k) != null' >/dev/null
  done

  local archived total
  archived="$(find "$planning/milestones" -maxdepth 1 -name '*-ROADMAP.md' \
    | wc -l | tr -d ' ')"
  total="$(printf '%s' "$output" | jq -r '.cycles | length')"
  if grep -q '🚧' "$planning/ROADMAP.md"; then
    [ "$total" -eq "$((archived + 1))" ]
  else
    [ "$total" -eq "$archived" ]
  fi
}

@test "real tree: the no-frontmatter cycles are exactly the ones grep finds" {
  local planning="$CAIRN_REPO_ROOT/.planning"
  [ -d "$planning/milestones" ] || skip "no archived milestone in this tree"
  run "$TREND" --planning-dir "$planning" --json
  [ "$status" -eq 0 ]

  # Recompute the expectation from the files themselves: a cycle is
  # no-frontmatter when it has verification files and none of them opens
  # with a `---` fence.
  local key dir f expected reported with_fm found
  expected=""
  for dir in "$planning"/milestones/*-phases; do
    [ -d "$dir" ] || continue
    key="$(basename "$dir" -phases)"
    found=0
    with_fm=0
    while IFS= read -r f; do
      found=$((found + 1))
      [ "$(head -n1 "$f")" = "---" ] && with_fm=$((with_fm + 1))
    done < <(find "$dir" -name '*VERIFICATION.md')
    if [ "$found" -gt 0 ] && [ "$with_fm" -eq 0 ]; then
      expected="$expected $key"
    fi
  done

  reported="$(printf '%s' "$output" | jq -r \
    '[.cycles[] | select(.scope == "no-frontmatter") | .cycle] | join(" ")')"
  [ "$(echo $expected)" = "$reported" ]
}

# --- the intersection decides the axes --------------------------------------

@test "a field every comparable cycle carries becomes an axis" {
  new_planning
  archive_cycle v1.1
  add_verified v1.1 01 passed "gaps:" "  - truth: a"
  archive_cycle v1.2
  add_verified v1.2 07 passed "gaps: []"
  archive_cycle v1.3
  add_verified v1.3 10 gaps_found "gaps:" "  - truth: b" "  - truth: c"

  trend --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | jq -e '.fields.intersection | index("gaps")' >/dev/null
  [ "$(tjq '[.series.axes[].axis] | index("gaps") != null')" = "true" ]
  [ "$(tjq '.series.axes[] | select(.axis == "gaps") | .points_line')" \
    = "1 → 0 → 2" ]
}

@test "a field only one cycle carries is not an axis, and the output says where it is missing" {
  new_planning
  archive_cycle v1.1
  add_verified v1.1 01 passed "gaps:" "  - truth: a"
  archive_cycle v1.2
  add_verified v1.2 07 passed
  archive_cycle v1.3
  add_verified v1.3 10 passed

  trend --json
  # `gaps` is not shared, so it is not in the intersection and not an axis.
  [ "$(tjq '.fields.intersection | index("gaps")')" = "null" ]
  [ "$(tjq '[.series.axes[].axis] | index("gaps")')" = "null" ]
  # And the cycles it is missing from are NAMED, not merely absent.
  [ "$(tjq '.fields.missing_from.gaps | join(",")')" = "v1.2,v1.3" ]
  [ "$(tjq '[.series.unavailable_axes[] | select(.field == "gaps")
             | .missing_from[]] | unique | join(",")')" = "v1.2,v1.3" ]

  trend
  printf '%s' "$output" | grep -qF "não vira série"
}

@test "score aggregates when every cycle counts the same unit" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do
    archive_cycle "$key"
  done
  add_verified v1.1 01 passed
  add_verified v1.2 07 passed
  add_verified v1.3 10 passed

  trend --json
  [ "$status" -eq 0 ]
  [ "$(tjq '.series.score.aggregated')" = "true" ]
  [ "$(tjq '.series.score.distinct_units | length')" -eq 1 ]
  [ "$(tjq '[.series.axes[].axis] | index("score") != null')" = "true" ]
}

@test "score is REFUSED when the denominator's unit differs, naming the units found" {
  # The break this guards is the one that matters: drawing a line between
  # `15/15 must-haves` and `4/4 critérios` is a line between two rulers, the
  # same class of error the phase exists to avoid, one floor down.
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do
    archive_cycle "$key"
  done
  add_verified v1.1 01 passed
  add_verified v1.2 07 passed
  add_verified v1.3 10 passed
  # Rewrite one cycle's score to count something else.
  local f
  f="$(cycle_phases_dir v1.3)/10-phase/10-VERIFICATION.md"
  cp "$f" "$f.orig"
  sed 's|score: 4/4 must-haves verified|score: 4/4 critérios verificados|' \
    "$f.orig" > "$f"
  rm -f "$f.orig"

  trend --json
  [ "$(tjq '.series.score.aggregated')" = "false" ]
  [ "$(tjq '.series.score.distinct_units | length')" -eq 2 ]
  [ "$(tjq '[.series.axes[].axis] | index("score")')" = "null" ]

  trend
  # The units it FOUND, from disk — not a generic complaint.
  printf '%s' "$output" | grep -qF "score não vira série"
  printf '%s' "$output" | grep -qF "must-haves verified"
  printf '%s' "$output" | grep -qF "critérios verificados"
}

@test "direction and monotonicity are reported separately" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  # gaps 1 -> 3 -> 2: ends above where it started, but not monotonically.
  add_verified v1.1 01 passed "gaps:" "  - truth: a"
  add_verified v1.2 07 passed "gaps:" "  - truth: a" "  - truth: b" \
    "  - truth: c"
  add_verified v1.3 10 passed "gaps:" "  - truth: a" "  - truth: b"

  trend --json
  [ "$(tjq '.series.axes[] | select(.axis == "gaps") | .direction')" \
    = "rising" ]
  [ "$(tjq '.series.axes[] | select(.axis == "gaps") | .monotonic')" \
    = "false" ]

  trend
  printf '%s' "$output" | grep -qF "não monotônica"
}

# --- sufficiency and contiguity ---------------------------------------------

@test "REMOVING the third point removes the direction and exits 4" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  add_verified v1.1 01 passed
  add_verified v1.2 07 passed
  add_verified v1.3 10 gaps_found

  trend --json
  [ "$status" -eq 0 ]
  [ "$(tjq '.series.sufficient')" = "true" ]
  [ "$(tjq '.series.axes[] | select(.axis == "first_pass") | .direction')" \
    = "falling" ]

  rm -rf "$(cycle_phases_dir v1.3)/10-phase"

  trend --json
  [ "$status" -eq 4 ]
  [ "$(tjq '.series.sufficient')" = "false" ]
  [ "$(tjq '.series.axes[] | select(.axis == "first_pass") | .direction')" \
    = "null" ]

  trend
  [ "$status" -eq 4 ]
  # It says so, and draws nothing.
  printf '%s' "$output" | grep -qF "nenhuma direção é declarada"
  if printf '%s' "$output" | grep -qF "→"; then
    echo "a direction line was drawn with too few points" >&2
    return 1
  fi
}

@test "ADDING a third point makes the direction appear, with no prose edited" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  add_verified v1.1 01 passed
  add_verified v1.2 07 gaps_found
  add_bare v1.3 10

  trend --json
  [ "$status" -eq 4 ]
  [ "$(tjq '.series.points')" -eq 2 ]
  [ "$(tjq '.series.axes[] | select(.axis == "first_pass") | .direction')" \
    = "null" ]

  # One file on disk. Nothing else.
  add_verified v1.3 11 gaps_found

  trend --json
  [ "$status" -eq 0 ]
  [ "$(tjq '.series.points')" -eq 3 ]
  [ "$(tjq '.series.axes[] | select(.axis == "first_pass") | .direction')" \
    = "falling" ]
}

@test "contiguity distinguishes a solid series from one with a hole in the middle" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  add_verified v1.1 01 passed
  add_verified v1.2 07 passed
  add_verified v1.3 10 passed

  trend --json
  [ "$(tjq '.series.contiguous')" = "true" ]
  [ "$(tjq '.series.holes')" -eq 0 ]
  [ "$(tjq '.series.span')" -eq 3 ]

  # Same three points, two dead cycles wedged into the middle.
  new_planning
  for key in v1.1 v1.2 v1.3 v1.4 v1.5; do archive_cycle "$key"; done
  add_verified v1.1 01 passed
  add_bare v1.2 07
  add_bare v1.3 10
  add_verified v1.4 13 passed
  add_verified v1.5 20 passed

  trend --json
  [ "$(tjq '.series.points')" -eq 3 ]
  [ "$(tjq '.series.contiguous')" = "false" ]
  [ "$(tjq '.series.holes')" -eq 2 ]
  [ "$(tjq '.series.span')" -eq 5 ]

  trend
  printf '%s' "$output" | grep -qF "não contígua"
}

@test "real tree: the series is not contiguous, and the holes are the no-frontmatter cycles" {
  local planning="$CAIRN_REPO_ROOT/.planning"
  [ -d "$planning/milestones" ] || skip "no archived milestone in this tree"
  run "$TREND" --planning-dir "$planning" --json
  [ "$status" -eq 0 ]

  # Both ends read from the command's own output — a literal `2` here would
  # be the fourth hand-typed count in this repository's history.
  local holes na
  holes="$(printf '%s' "$output" | jq -r '.series.holes')"
  na="$(printf '%s' "$output" | jq -r \
    '[.cycles[] | select(.state == "not-applicable")] | length')"
  [ "$holes" -eq "$na" ]
  [ "$(printf '%s' "$output" | jq -r '.series.contiguous')" = "false" ]
}

# --- the ambiguity is derived, not printed ----------------------------------

@test "with no verifier_* key anywhere the verdict is unresolved and the line is declared ambiguous" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  add_verified v1.1 01 passed
  add_verified v1.1 02 passed
  add_verified v1.2 07 passed
  add_verified v1.2 08 gaps_found
  add_verified v1.3 10 gaps_found
  add_verified v1.3 11 gaps_found

  trend --json
  [ "$status" -eq 0 ]
  [ "$(tjq '.disambiguation.verdict')" = "unresolved" ]
  [ "$(tjq '.disambiguation.shared_keys | length')" -eq 0 ]
  [ "$(tjq '.disambiguation.declaration')" != "null" ]

  trend
  printf '%s' "$output" | grep -qF "ambígua na raiz"
  printf '%s' "$output" | grep -qF "escrutínio subindo"
}

@test "ADDING verifier_* to EVERY comparable cycle flips the verdict, no prose edited" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  add_verified v1.1 01 passed
  add_verified v1.2 07 passed
  add_verified v1.3 10 gaps_found
  trend --json
  [ "$(tjq '.disambiguation.verdict')" = "unresolved" ]

  # One key, in every comparable cycle's frontmatter. Nothing else changes.
  add_verified v1.1 01 passed "verifier_rigor: 1"
  add_verified v1.2 07 passed "verifier_rigor: 2"
  add_verified v1.3 10 gaps_found "verifier_rigor: 3"

  trend --json
  [ "$status" -eq 0 ]
  [ "$(tjq '.disambiguation.verdict')" = "resolvable" ]
  [ "$(tjq '.disambiguation.shared_keys | join(",")')" = "verifier_rigor" ]
  # And the ambiguity declaration is gone, because it is no longer true.
  [ "$(tjq '.disambiguation.declaration')" = "null" ]

  trend
  if printf '%s' "$output" | grep -qF "ambígua na raiz"; then
    echo "the ambiguity was still declared after the data could settle it" >&2
    return 1
  fi
}

@test "verifier_* in ONE cycle only does not flip the verdict, and the gap is named" {
  # Without this test, an implementation accepting "the key anywhere" would
  # pass the ADDING test above. A key one cycle carries disambiguates
  # nothing, exactly as a field one cycle carries is not an axis.
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  add_verified v1.1 01 passed "verifier_rigor: 1"
  add_verified v1.2 07 passed
  add_verified v1.3 10 gaps_found

  trend --json
  [ "$(tjq '.disambiguation.verdict')" = "unresolved" ]
  [ "$(tjq '.disambiguation.keys_found."v1.1" | join(",")')" \
    = "verifier_rigor" ]
  [ "$(tjq '.disambiguation.keys_found."v1.2" | length')" -eq 0 ]
  trend
  printf '%s' "$output" | grep -qF "falta em v1.2, v1.3"
}

@test "REMOVING the key from one cycle reverts the verdict to unresolved" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  add_verified v1.1 01 passed "verifier_rigor: 1"
  add_verified v1.2 07 passed "verifier_rigor: 2"
  add_verified v1.3 10 gaps_found "verifier_rigor: 3"
  trend --json
  [ "$(tjq '.disambiguation.verdict')" = "resolvable" ]

  add_verified v1.3 10 gaps_found

  trend --json
  [ "$(tjq '.disambiguation.verdict')" = "unresolved" ]
}

@test "a flat first-pass line carries no ambiguity declaration" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3; do archive_cycle "$key"; done
  add_verified v1.1 01 passed
  add_verified v1.2 07 passed
  add_verified v1.3 10 passed

  trend --json
  [ "$(tjq '.series.axes[] | select(.axis == "first_pass") | .direction')" \
    = "flat" ]
  [ "$(tjq '.disambiguation.verdict')" = "unresolved" ]
  # Unresolved, yes — but there is no moving line to call ambiguous, and a
  # caveat printed unconditionally is decoration.
  [ "$(tjq '.disambiguation.declaration')" = "null" ]

  trend
  if printf '%s' "$output" | grep -qF "ambígua na raiz"; then
    echo "the caveat printed with a flat line" >&2
    return 1
  fi
}

@test "a verifier_* key in a not-applicable cycle counts for nothing" {
  new_planning
  local key
  for key in v1.1 v1.2 v1.3 v1.4; do archive_cycle "$key"; done
  add_verified v1.1 01 passed "verifier_rigor: 1"
  add_verified v1.2 07 passed "verifier_rigor: 2"
  add_verified v1.3 10 gaps_found
  # A cycle that never enters the series cannot settle it. Its file carries
  # frontmatter but no status, so the cycle is not-applicable.
  local dir
  dir="$(cycle_phases_dir v1.4)/13-phase"
  mkdir -p "$dir"
  printf -- '---\nphase: 13\nverifier_rigor: 9\n---\n' \
    > "$dir/13-VERIFICATION.md"

  trend --json
  [ "$(tjq '.cycles[3].state')" = "not-applicable" ]
  [ "$(tjq '.disambiguation.verdict')" = "unresolved" ]
  [ "$(tjq '.disambiguation.keys_found | has("v1.4")')" = "false" ]
}

# --- the guard against the fourth hand-typed count --------------------------

# Numeric tokens present in HUMAN and absent from every scalar value of JSON.
# Empty output means the human text is a view of the data.
numbers_not_in_json() {
  local human="$1" jsonout="$2" tok json_tokens missing=""
  json_tokens="$(printf '%s' "$jsonout" | jq -r '[.. | scalars] | .[]' \
    | grep -oE '[0-9]+' | sort -u)"
  while IFS= read -r tok; do
    [ -z "$tok" ] && continue
    printf '%s\n' "$json_tokens" | grep -qx -- "$tok" || missing="$missing $tok"
  done < <(printf '%s' "$human" | grep -oE '[0-9]+' | sort -u)
  printf '%s' "$missing"
}

@test "GUARD: every number in the human output is a value in the JSON" {
  # TREND-02 is the requirement this phase exists for, and this repository
  # has three measured precedents of a hand-typed count going stale. Saying
  # "no number is typed by hand" is worth nothing; this is the mechanical
  # version, and it is only possible because the renderer computes nothing.
  #
  # Two targets, because one would not prove it: a command that derived on
  # one and stamped on the other would pass a single-target check.
  local planning="$CAIRN_REPO_ROOT/.planning"
  local human json
  human="$("$TREND" --planning-dir "$planning" || true)"
  json="$("$TREND" --planning-dir "$planning" --json || true)"
  local missing
  missing="$(numbers_not_in_json "$human" "$json")"
  if [ -n "$missing" ]; then
    echo "numbers in the prose with no value behind them:$missing" >&2
    return 1
  fi

  new_planning
  local key
  for key in v1.1 v1.2 v1.3 v1.4; do archive_cycle "$key"; done
  add_verified v1.1 01 passed "gaps:" "  - truth: a"
  add_verified v1.2 07 passed "gaps: []"
  add_bare v1.3 10
  add_verified v1.4 13 gaps_found "gaps:" "  - truth: b" "  - truth: c"
  add_unverified v1.4 14
  human="$("$TREND" --planning-dir "$TREND_PLANNING" || true)"
  json="$("$TREND" --planning-dir "$TREND_PLANNING" --json || true)"
  missing="$(numbers_not_in_json "$human" "$json")"
  if [ -n "$missing" ]; then
    echo "numbers in the prose with no value behind them:$missing" >&2
    return 1
  fi
}

@test "GUARD negative control: the check rejects a forged number" {
  # A guard that only ever passes proves nothing — a broken token extraction
  # would stay green forever. This is the liveness half.
  local planning="$CAIRN_REPO_ROOT/.planning"
  local json missing
  json="$("$TREND" --planning-dir "$planning" --json || true)"
  missing="$(numbers_not_in_json "a série tem 987654 pontos" "$json")"
  [ -n "$missing" ]
  printf '%s' "$missing" | grep -qF "987654"
}

@test "GUARD: no live count about the repository lives outside the dated block" {
  # The house convention makes the docstring record MEASURED VERSUS ASSUMED,
  # which means writing measured numbers into prose — and that is exactly how
  # this repository's three stale counts were born. What saves a number is
  # being DATED and labelled as a measurement of one instant. So: counts live
  # inside that block, and nowhere else in either delivered file.
  local py="$CAIRN_SCRIPTS_DIR/cairn-trend.py"
  local sh="$CAIRN_SCRIPTS_DIR/cairn-trend.sh"
  local nouns='ciclos?|cycles?|milestones?|verifica(ção|ções)|verifications?'
  nouns="$nouns"'|fases?|phases?|arquivos?|files?|checks?'
  # `one` and `um` are deliberately absent: in both languages they work as
  # indefinite articles ("at least one verification file"), so including them
  # flags definitions instead of counts. The three precedents this guard is
  # named after were all counts of a SET — "fifteen", "17", "18", "nineteen".
  # The digit 1 stays, because "1 ciclo" is a count and not an article.
  local numerals='[0-9]+|two|three|four|five|six|seven|eight|nine|ten'
  numerals="$numerals"'|eleven|twelve|dois|duas|três|quatro|cinco|seis|sete'
  local pattern="(^|[^A-Za-z_])($numerals) ($nouns)([^A-Za-z]|$)"

  # Everything in the .py BEFORE the dated measurement block.
  local before
  before="$(awk '/^MEASURED VERSUS ASSUMED$/{exit} {print}' "$py")"
  local hit
  hit="$(printf '%s' "$before" | grep -inE "$pattern" || true)"
  if [ -n "$hit" ]; then
    echo "a live count sits outside the dated block in cairn-trend.py:" >&2
    echo "$hit" >&2
    return 1
  fi
  # The .sh header restates the contract and is exactly the kind of place a
  # number moves into and is forgotten.
  hit="$(grep -inE "$pattern" "$sh" || true)"
  if [ -n "$hit" ]; then
    echo "a live count sits in cairn-trend.sh:" >&2
    echo "$hit" >&2
    return 1
  fi
  # Liveness: the pattern must actually match something, or it guards air.
  printf 'this tree has 5 cycles\n' | grep -qiE "$pattern"
  printf 'vanished for two cycles\n' | grep -qiE "$pattern"
}

@test "an unknown flag is a usage error, exit 2" {
  new_planning
  trend --nope
  [ "$status" -eq 2 ]
}

@test "--planning-dir pointing at a non-directory is a usage error" {
  local base
  base="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/trend-file.XXXXXX")"
  printf 'not a dir\n' > "$base/file"
  run "$TREND" --planning-dir "$base/file" --json
  [ "$status" -eq 2 ]
}
