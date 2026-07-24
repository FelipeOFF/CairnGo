#!/usr/bin/env bats
# cairn-relabel.bats — exercises the pair/renumber contract of
# cairn-relabel.py (and the cairn-relabel.sh wrapper) against a real bd
# database: pair adds the missing m-<milestone> label and merges
# gsd.milestone into metadata WITHOUT clobbering pre-existing metadata keys;
# renumber moves phase-<N> -> phase-<M> in both labels and metadata.gsd.phase,
# refusing on an ambiguous double-label unless --force.
#
# Assertion style note: a failing `[[ ]]` mid-test does NOT fail a bats test
# on this bash, so substring checks use grep -qF and exact checks use `[ ]`.

load 'helpers'

# bd init + the relabel fixture issues (ids exported for assertions):
#   RL_PLAIN     phase-1 only, no metadata          (pair candidate)
#   RL_META      phase-1 only, unrelated metadata   (pair candidate; the
#                pre-existing "custom" key must survive the merge)
#   RL_PAIRED    phase-1 + m-v1.0                   (already paired; pair
#                must leave it untouched)
#   RL_PHASE2    phase-2 only                       (renumber target)
# Callers must require_bd and cd into a repo (make_tmp_repo) first.
make_relabel_fixture() {
  bd init -q --prefix rlb --non-interactive >/dev/null 2>&1
  RL_PLAIN="$(bd create "Plain phase-1 issue" -t task -l phase-1 --silent)"
  RL_META="$(bd create "Phase-1 issue with metadata" -t task -l phase-1 \
    --metadata '{"custom":{"keep":"yes"}}' --silent)"
  RL_PAIRED="$(bd create "Already paired issue" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  RL_PHASE2="$(bd create "Phase-2 issue" -t task -l phase-2 \
    --metadata '{"gsd":{"req":"API-01","phase":2}}' --silent)"
}

show_json() { bd show "$1" --json; }

# Assert NEEDLE does not appear in HAYSTACK. (`! grep` cannot be used inline:
# bash's `!` suppresses errexit, so its failure would never fail the test.)
refute_contains() {
  if grep -qF -- "$1" <<<"$2"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

@test "pair --dry-run lists exactly the two candidates and changes nothing" {
  require_bd
  make_tmp_repo
  make_relabel_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-relabel.sh" pair --milestone v1.0 \
    --phase 1 --dry-run
  [ "$status" -eq 0 ]
  # Exactly the two unpaired phase-1 issues, one DRY-RUN line each, in
  # sorted-id order. The paired issue and the phase-2 issue are not listed.
  local expected
  expected="$(printf 'DRY-RUN: %s +m-v1.0 gsd.milestone=v1.0\n' \
    "$RL_PLAIN" "$RL_META" | LC_ALL=C sort)"
  [ "$output" = "$expected" ]

  # Unscoped, the phase-2 issue is a candidate too (no m-* label either).
  run bash "$CAIRN_SCRIPTS_DIR/cairn-relabel.sh" pair --milestone v1.0 --dry-run
  [ "$status" -eq 0 ]
  [ "$(wc -l <<<"$output" | tr -d ' ')" = "3" ]
  grep -qF "DRY-RUN: $RL_PHASE2 " <<<"$output"

  # Nothing was written: labels and metadata are as the fixture created them.
  assert_json_eq "$(show_json "$RL_PLAIN")" '.[0].labels | join(",")' "phase-1"
  assert_json_eq "$(show_json "$RL_META")" '.[0].labels | join(",")' "phase-1"
  assert_json_eq "$(show_json "$RL_META")" '.[0].metadata | keys | join(",")' "custom"
}

@test "pair adds m-label and merges gsd.milestone, preserving prior metadata" {
  require_bd
  make_tmp_repo
  make_relabel_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-relabel.sh" pair --milestone v1.0 --phase 1
  [ "$status" -eq 0 ]
  grep -qF "$RL_PLAIN +m-v1.0 gsd.milestone=v1.0" <<<"$output"
  grep -qF "$RL_META +m-v1.0 gsd.milestone=v1.0" <<<"$output"
  grep -qF "pair: 2 issue(s) updated" <<<"$output"

  # Both candidates now carry the milestone label and gsd.milestone.
  assert_json_eq "$(show_json "$RL_PLAIN")" \
    '.[0].labels | sort | join(",")' "m-v1.0,phase-1"
  assert_json_eq "$(show_json "$RL_PLAIN")" \
    '.[0].metadata.gsd.milestone' "v1.0"
  # The pre-existing unrelated metadata key survived the merge.
  assert_json_eq "$(show_json "$RL_META")" \
    '.[0].metadata.custom.keep' "yes"
  assert_json_eq "$(show_json "$RL_META")" \
    '.[0].metadata.gsd.milestone' "v1.0"

  # The already-paired issue was not touched (not even re-listed).
  refute_contains "$RL_PAIRED" "$output"
  assert_json_eq "$(show_json "$RL_PAIRED")" \
    '.[0].labels | sort | join(",")' "m-v1.0,phase-1"
  assert_json_eq "$(show_json "$RL_PAIRED")" \
    '.[0].metadata.gsd.req' "AUTH-01"

  # The phase-2 issue was outside the --phase 1 scope.
  refute_contains "$RL_PHASE2" "$output"
  assert_json_eq "$(show_json "$RL_PHASE2")" '.[0].labels | join(",")' "phase-2"
}

@test "renumber moves phase-2 to phase-3 in labels and metadata.gsd.phase" {
  require_bd
  make_tmp_repo
  make_relabel_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-relabel.sh" renumber --from 2 --to 3
  [ "$status" -eq 0 ]
  grep -qF "$RL_PHASE2 phase-2 -> phase-3" <<<"$output"
  grep -qF "renumber: 1 issue(s) updated" <<<"$output"

  assert_json_eq "$(show_json "$RL_PHASE2")" \
    '.[0].labels | join(",")' "phase-3"
  assert_json_eq "$(show_json "$RL_PHASE2")" \
    '.[0].metadata.gsd.phase' "3"
  # The gsd.req sibling key survived the phase merge.
  assert_json_eq "$(show_json "$RL_PHASE2")" \
    '.[0].metadata.gsd.req' "API-01"

  # phase-1 issues were out of scope.
  assert_json_eq "$(show_json "$RL_PLAIN")" '.[0].labels | join(",")' "phase-1"
}

@test "renumber refuses a double-labeled target without --force (exit 2)" {
  require_bd
  make_tmp_repo
  make_relabel_fixture
  local doubled
  doubled="$(bd create "Ambiguous double-label" -t task -l phase-2,phase-3 --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-relabel.sh" renumber --from 2 --to 3
  [ "$status" -eq 2 ]
  grep -qF "$doubled" <<<"$output"
  grep -qF -- "--force" <<<"$output"

  # Refusal wrote nothing: the clean phase-2 target is unchanged.
  assert_json_eq "$(show_json "$RL_PHASE2")" '.[0].labels | join(",")' "phase-2"
  assert_json_eq "$(show_json "$RL_PHASE2")" '.[0].metadata.gsd.phase' "2"
}
