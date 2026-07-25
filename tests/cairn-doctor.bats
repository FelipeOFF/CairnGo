#!/usr/bin/env bats
# cairn-doctor.bats — exercises the consistency doctor's CLI contract
# (cairn-doctor.py / the cairn-doctor.sh wrapper):
#   0 all ok or warnings only (warnings never change the exit code) or not
#   applicable, 2 usage / refused --fix-labels, 5 bd unavailable, 7 any
#   check failed.
#
# Each test starts from the HEALTHY wired fixture (all eight checks ✓) and
# breaks exactly one check, asserting on that check's reported status.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail
# a bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# Insert `beads: [IDS]` into a PLAN.md's frontmatter (right after the
# opening ---).
add_plan_beads() {
  python3 - "$1" "$2" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
lines = p.read_text().splitlines(keepends=True)
lines.insert(1, f"beads: [{sys.argv[2]}]\n")
p.write_text("".join(lines))
PY
}

# Insert `milestone: v1.0` into the fixture STATE.md frontmatter.
stamp_state_milestone() {
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/STATE.md")
lines = p.read_text().splitlines(keepends=True)
lines.insert(1, "milestone: 'v1.0'\n")   # right after the opening ---
p.write_text("".join(lines))
PY
}

# Healthy wired fixture on top of make_gsd_fixture (phase 1 complete,
# phase 2 active): one issue per ROADMAP requirement with the pair labels
# and gsd metadata stamp, plan frontmatter pointing at them, maps fresh.
make_doctor_fixture() {
  bd init -q --prefix doc --non-interactive >/dev/null 2>&1
  DOC_A1="$(bd create "AUTH-01: Signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  DOC_A2="$(bd create "AUTH-02: Login flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v1.0"}}' --silent)"
  DOC_P2="$(bd create "API-01: Rate limiting" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-01","phase":2,"milestone":"v1.0"}}' --silent)"
  bd close "$DOC_A1" >/dev/null
  bd close "$DOC_A2" >/dev/null
  add_plan_beads .planning/phases/01-auth/01-01-PLAN.md "$DOC_A1, $DOC_A2"
  add_plan_beads .planning/phases/02-api/02-01-PLAN.md "$DOC_P2"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
}

@test "healthy wired fixture: exit 0, every check ✓" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "[cairn-doctor] ok" <<<"$output"
  refute_in_output "⚠"
  refute_in_output "✗"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.applicable' 'true'
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.checks | length' '8'
  assert_json_eq "$output" '[.checks[].status] | unique | join(",")' 'ok'
}

@test "check 1 req-issue: requirement without a gsd.req issue fails, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Wipe gsd.req off AUTH-01's issue (--metadata replaces the gsd key
  # wholesale) and regenerate the map so ONLY check 1 breaks.
  bd update "$DOC_A1" --metadata '{"gsd":{"phase":1,"milestone":"v1.0"}}' >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.checks[] | select(.id=="req-issue") | .status' 'fail'
  assert_json_eq "$output" '.checks[] | select(.id=="req-issue") | .items | length' '1'
  grep -qF "AUTH-01" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ req-issue" <<<"$output"
  grep -qF "[cairn-doctor] FAIL" <<<"$output"
}

@test "check 2 frontmatter-ids: dangling id in PLAN beads fails, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/phases/02-api/02-01-PLAN.md")
p.write_text(p.read_text().replace("beads: [", "beads: [doc-zzz, ", 1))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="frontmatter-ids") | .status' 'fail'
  assert_json_eq "$output" '.checks[] | select(.id=="frontmatter-ids") | .items | length' '1'
  grep -qF "doc-zzz not found in bd" <<<"$output"
}

@test "check 2 frontmatter-ids: bead without the plan's phase label fails" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # DOC_P2 is referenced by the phase-2 plan — moving its label to phase-1
  # makes the frontmatter reference wrong (regen maps to keep check 3 ok).
  bd label remove "$DOC_P2" phase-2 >/dev/null
  bd label add "$DOC_P2" phase-1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="frontmatter-ids") | .status' 'fail'
  grep -qF "lacks label phase-2" <<<"$output"
}

@test "check 3 maps-fresh: close without regenerating the map warns, exit 0" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  bd close "$DOC_P2" >/dev/null   # map 2 NOT regenerated

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # warnings alone never change the exit code
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.checks[] | select(.id=="maps-fresh") | .status' 'warn'
  grep -qF "stale map 02-BEADS-MAP.md" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⚠ maps-fresh" <<<"$output"

  # Regenerate -> clean again.
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  refute_in_output "⚠"
}

@test "check 4 superseded-released: superseded plan holding a live bead warns" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # A superseded plan still pointing at the OPEN phase-2 issue.
  cat > .planning/phases/02-api/02-02-PLAN.md <<EOF
---
phase: 02-api
plan: "02"
status: superseded
beads: [$DOC_P2]
---

Superseded draft plan.
EOF

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="superseded-released") | .status' 'warn'
  # Superseded plans are excluded from check 2 — its ids are not "dangling".
  assert_json_eq "$output" '.checks[] | select(.id=="frontmatter-ids") | .status' 'ok'
  grep -qF "still open" <<<"$output"
}

@test "check 5 orphans: unknown phase label and phase-less issue warn; migrated-todo exempt" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local ghost loose todo
  ghost="$(bd create "Ghost of a phase" -t task -l phase-9,m-v1.0 --silent)"
  loose="$(bd create "Loose end" -t task --silent)"
  todo="$(bd create "Parked todo" -t task -l migrated-todo --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .items | length' '2'
  grep -qF "$ghost" <<<"$output"
  grep -qF "$loose" <<<"$output"
  refute_in_output "$todo"
}

@test "check 6 label-pairs: phase-only label warns, --fix-labels repairs, re-run clean" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  stamp_state_milestone
  local stray
  stray="$(bd create "Stray unpaired task" -t task -l phase-2 --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.milestone' 'v1.0'
  assert_json_eq "$output" '.checks[] | select(.id=="label-pairs") | .status' 'warn'
  grep -qF "$stray" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --fix-labels
  [ "$status" -eq 0 ]
  grep -qF "fixed 1 via cairn-relabel pair" <<<"$output"
  refute_in_output "⚠ label-pairs"

  # The pair label and gsd.milestone actually landed in bd.
  run bd show "$stray" --json
  assert_json_eq "$output" '.[0].labels | sort | join(",")' 'm-v1.0,phase-2'
  assert_json_eq "$output" '.[0].metadata.gsd.milestone' 'v1.0'

  # Refresh the phase-2 map (the stray is a new row) -> fully clean re-run.
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  refute_in_output "⚠"
  refute_in_output "✗"
}

@test "check 6 --fix-labels refuses when the milestone is unresolvable, exit 2" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # no milestone in STATE.md or ROADMAP.md
  make_doctor_fixture
  bd create "Stray unpaired task" -t task -l phase-2 --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --fix-labels
  [ "$status" -eq 2 ]
  grep -qF "milestone unresolvable" <<<"$output"
}

@test "check 7 claims-stale: assigned in_progress issue outside the active phase warns" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # STATE.md active_phase: 2
  make_doctor_fixture
  local claimed
  claimed="$(bd create "AUTH-03: Password reset" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-03","phase":1,"milestone":"v1.0"}}' --silent)"
  bd update "$claimed" --claim >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null   # keep check 3 ok

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.active_phase' '2'
  assert_json_eq "$output" '.checks[] | select(.id=="claims-stale") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="claims-stale") | .items | length' '1'
  grep -qF "$claimed" <<<"$output"
  grep -qF "stale claim" <<<"$output"
}

@test "check 8 bd-doctor: summary line captured in the report" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="bd-doctor") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="bd-doctor") | .detail | startswith("exit 0:")' 'true'
}

@test "no .planning/ — not applicable, exit 0, suggests /cairn:migrate" {
  require_bd
  make_tmp_repo
  bd init -q --prefix doc --non-interactive >/dev/null 2>&1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
  grep -qF "/cairn:migrate" <<<"$output"
}

@test "no .beads/ — not applicable, exit 0, suggests /cairn:migrate" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
  grep -qF "/cairn:migrate" <<<"$output"
}

@test "neither .planning/ nor .beads/ — not applicable, no migrate hint" {
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
  refute_in_output "/cairn:migrate"
}

@test "bd missing from PATH exits 5 with a warning" {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  mkdir .beads   # applicable, but bd is unreachable
  local stub="$BATS_TEST_TMPDIR/nobd-bin"
  mkdir -p "$stub"
  # Link the real interpreter (not a version-manager shim needing PATH).
  ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
  ln -s "$(command -v bash)" "$stub/bash"
  ln -s "$(command -v dirname)" "$stub/dirname"

  run env PATH="$stub" "$stub/bash" "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 5 ]
  grep -qF "warning" <<<"$output"
}

@test "unknown flag is a usage error, exit 2" {
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --frobnicate
  [ "$status" -eq 2 ]
}
