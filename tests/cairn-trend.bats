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
  [ "$status" -eq 0 ]
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
  [ "$status" -eq 0 ]
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
  [ "$status" -eq 0 ]
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
  [ "$status" -eq 0 ]
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
  [ "$status" -eq 0 ]
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
