#!/usr/bin/env bats
# cairn-doctor.bats — exercises the consistency doctor's CLI contract
# (cairn-doctor.py / the cairn-doctor.sh wrapper):
#   0 all ok or warnings only (warnings never change the exit code) or not
#   applicable, 2 usage / refused --fix-labels, 5 bd unavailable, 7 any
#   check failed.
#
# Each test starts from the HEALTHY wired fixture (all ten checks ✓) and
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
  wire_capability_ok
}

# The gsd-capability check reads GLOBAL state — which GSD is installed on the
# machine — so without a seam every doctor test would inherit the developer's
# plugin cache and pass or fail by accident. CAIRN_GSD_BIN pins it to a stub.
# $1 = lineage: "core" (default, cairn registered) or "legacy".
wire_capability_ok() {
  local mode="${1:-core}" stub="$PWD/.gsd-stub"
  cat > "$stub" <<EOF
#!/usr/bin/env sh
mode="$mode"
EOF
  cat >> "$stub" <<'EOF'
[ "$1" = "capability" ] || { echo "unexpected: $*" >&2; exit 1; }
if [ "$mode" = "legacy" ]; then
  echo "Error: Unknown command: capability" >&2; exit 1
fi
echo '[{"id":"cairn","status":"active","version":"1.0.0","scope":"project"}]'
EOF
  chmod +x "$stub"
  export CAIRN_GSD_BIN="$stub"
  if [ "$mode" = "core" ]; then
    mkdir -p .gsd/capabilities/cairn/scripts
    cp "$CAIRN_REPO_ROOT/cairn/capability/capability.json" \
       .gsd/capabilities/cairn/capability.json
    cp "$CAIRN_REPO_ROOT/cairn/capability/scripts/cairn-loop-gate.sh" \
       .gsd/capabilities/cairn/scripts/
  fi
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
  assert_json_eq "$output" '.checks | length' '11'
  assert_json_eq "$output" '[.checks[].status] | unique | join(",")' 'ok'
}

@test "gsd-capability: the 4.x lineage fails the doctor, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  wire_capability_ok legacy

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "gsd-capability" <<<"$output"
  grep -qF "claude plugin install gsd-core@cairngo" <<<"$output"
}

@test "gsd-capability: gsd-core without a registered capability fails, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # gsd-core answers, but the registry does not list cairn.
  cat > "$PWD/.gsd-stub" <<'EOF'
#!/usr/bin/env sh
[ "$1" = "capability" ] || exit 1
echo '[{"id":"ai-integration","status":"active"}]'
EOF
  chmod +x "$PWD/.gsd-stub"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "gsd-capability" <<<"$output"
}

@test "gsd-capability: a staged bundle missing its gate script fails, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The ship-gate predicate no-ops when this file is absent, so a bundle
  # staged without it leaves a gate that passes without checking anything.
  rm -f .gsd/capabilities/cairn/scripts/cairn-loop-gate.sh

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "gsd-capability" <<<"$output"
}

@test "gsd-capability: no GSD binary at all warns, it does not fail" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Not evidence either way — a warn, so the exit code stays 0.
  #
  # Cutting every GSD discovery route means a HOME with no plugin cache under
  # it, which also moves any version-manager shims (asdf/mise put python3 on
  # PATH via $HOME). So PATH is rebuilt from the system dirs plus bd's own,
  # which the doctor needs — leaving a real python3 at /usr/bin and no
  # gsd_run/gsd anywhere.
  mkdir -p "$PWD/nohome"
  run env -u CAIRN_GSD_BIN -u CLAUDE_PLUGIN_ROOT HOME="$PWD/nohome" \
    PATH="/usr/bin:/bin:$(dirname "$(command -v bd)")" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "no GSD binary found" <<<"$output"
}

@test "req-issue: requirement without a gsd.req issue fails, exit 7" {
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

@test "frontmatter-ids: dangling id in PLAN beads fails, exit 7" {
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

@test "frontmatter-ids: bead without the plan's phase label fails" {
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

@test "maps-fresh: close without regenerating the map warns, exit 0" {
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

@test "superseded-released: superseded plan holding a live bead warns" {
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

@test "phase-complete-open: open issue in a completed phase warns; --close-completed closes; re-run clean" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 checked off in ROADMAP.md
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null   # keep check 3 ok

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # WARN, never fail
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '1'
  grep -qF "$straggler" <<<"$output"
  # Phase 1's disk artifacts agree (PLAN has its SUMMARY) — no divergence note.
  refute_in_output "artifacts disagree"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  grep -qF "closed $straggler" <<<"$output"
  refute_in_output "⚠ phase-complete-open"

  # Actually closed in bd.
  run bd show "$straggler" --json
  assert_json_eq "$output" '.[0].status' 'closed'

  # Idempotent: a second run has nothing left to close.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  refute_in_output "closed $straggler"

  # Refresh the phase-1 map (the close changed a row) -> fully clean re-run.
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  refute_in_output "⚠"
  refute_in_output "✗"
}

@test "phase-complete-open: absent when completed phases hold nothing open" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture   # phase-1 issues closed, open issue only in phase 2

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '0'
}

@test "phase-complete-open: a cross-phase issue with one live phase is never flagged or closed" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 complete, phase 2 active
  make_doctor_fixture
  # phase-1 (complete) AND phase-2 (live): ALL, not any. cairn-status keeps
  # this issue out of stale_complete and offers it as the next action, and
  # its footer sends the user to --close-completed — which must not then
  # kill the very issue the board just recommended.
  local cross
  cross="$(bd create "API-02: Spans two phases" -t task -l phase-1,phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-02","phase":2,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '0'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  refute_in_output "closed $cross"
  run bd show "$cross" --json
  assert_json_eq "$output" '.[0].status' 'open'

  # cairn-status agrees: not stale, and still the pick.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.stale_complete | length' '0'

  # A single-label phase-1 straggler in the same board IS still swept, so
  # the ALL predicate narrows the target set without disabling the flag.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  grep -qF "closed $straggler" <<<"$output"
  refute_in_output "closed $cross"
  run bd show "$cross" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "phase-complete-open: --close-completed prints the divergence note BEFORE closing" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  rm .planning/phases/01-auth/01-01-SUMMARY.md   # disk now disagrees

  # The warning must reach the operator in the SAME run that closes: after
  # the close the issues leave check 5's scope and the note is unreachable.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  grep -qF "artifacts disagree" <<<"$output"
  grep -qF "confirm the phase is really done before closing" <<<"$output"
  grep -qF "closed $straggler" <<<"$output"
  # ...and it is ordered before the close line, not after it.
  local warn_line close_line
  warn_line="$(grep -nF "artifacts disagree" <<<"$output" | head -1 | cut -d: -f1)"
  close_line="$(grep -nF "closed $straggler" <<<"$output" | head -1 | cut -d: -f1)"
  [ "$warn_line" -lt "$close_line" ]

  # --json stays ONE machine line (the note never leaks onto stdout/stderr)
  # and still carries the divergence note inside the report.
  local straggler2
  straggler2="$(bd create "AUTH-05: Another follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-05","phase":1,"milestone":"v1.0"}}' --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json --close-completed
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.applicable' 'true'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-complete-open") | .items[] | select(test("artifacts disagree"))] | length' '1'
}

@test "phase-complete-open: notes when ROADMAP checkbox and disk artifacts diverge" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  rm .planning/phases/01-auth/01-01-SUMMARY.md   # disk now disagrees

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '2'
  grep -qF "$straggler" <<<"$output"
  grep -qF "artifacts disagree" <<<"$output"
}

@test "phase-complete-open: the divergence note names the real on-disk gap" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' \
    --silent >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  # Gap 1: the PLAN is there, its SUMMARY is not.
  rm .planning/phases/01-auth/01-01-SUMMARY.md
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  grep -qF "01-01-PLAN.md lacks its SUMMARY" <<<"$output"

  # Gap 2: no phase directory at all — the note used to blame a missing
  # SUMMARY for a phase that has no PLAN to lack one.
  rm -rf .planning/phases/01-auth
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  grep -qF "no phase directory on disk" <<<"$output"
  refute_in_output "lacks its SUMMARY"
}

@test "phase-complete-open: --close-completed drains an epic<-epic<-epic chain in ONE run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Both phases complete, on the ROADMAP checkbox AND on disk, so the whole
  # chain below is in scope and no divergence note fires.
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/ROADMAP.md")
p.write_text(p.read_text().replace("- [ ] **Phase 2: API**",
                                   "- [x] **Phase 2: API**"))
PY
  cp .planning/phases/01-auth/01-01-SUMMARY.md \
     .planning/phases/02-api/02-01-SUMMARY.md
  bd close "$DOC_P2" >/dev/null   # keep the sweep's scope to the chain

  # The shape that broke the bulk close in the field: epics chained by
  # blocks edges, each holding an open task child. bd refuses to close an
  # epic with an open child AND an issue with an open blocker, so NO single
  # ordered pass closes all six — only a fixpoint drains it.
  local e1 t1 e2 t2 e3 t3
  e1="$(bd create "Phase 1 epic" -t epic -l phase-1,m-v1.0 --silent)"
  t1="$(bd create "REQ-A: child of the phase 1 epic" -t task \
    -l phase-1,m-v1.0 --parent "$e1" --silent)"
  e2="$(bd create "Phase 2 epic" -t epic -l phase-2,m-v1.0 --silent)"
  t2="$(bd create "REQ-B: child of the phase 2 epic" -t task \
    -l phase-2,m-v1.0 --parent "$e2" --silent)"
  e3="$(bd create "Phase 2 follow-up epic" -t epic -l phase-2,m-v1.0 --silent)"
  t3="$(bd create "REQ-C: child of the follow-up epic" -t task \
    -l phase-2,m-v1.0 --parent "$e3" --silent)"
  bd dep add "$e2" "$e1" >/dev/null   # e2 blocked by e1
  bd dep add "$e3" "$e2" >/dev/null   # e3 blocked by e2
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  local id
  for id in "$e1" "$t1" "$e2" "$t2" "$e3" "$t3"; do
    if ! grep -qF "closed $id —" <<<"$output"; then
      echo "id $id was never closed. output:" >&2
      echo "$output" >&2
      return 1
    fi
  done
  grep -qF "closed 6 via --close-completed" <<<"$output"

  # bd agrees: one invocation left nothing open anywhere.
  run bd list --all --json
  assert_json_eq "$output" '[.[] | select(.status != "closed")] | length' '0'

  # Re-run is clean and idempotent.
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  refute_in_output "[cairn-doctor] closed"
  refute_in_output "⚠"
  refute_in_output "✗"
}

@test "phase-complete-open: a close bd refuses fails the check, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 complete, phase 2 still open
  make_doctor_fixture
  # An epic in the COMPLETE phase 1 whose only child lives in the still-open
  # phase 2. The child is not a target (its phase is live) and --force is
  # not on the table, so bd refuses the epic on every pass: the fixpoint
  # cannot drain it and the run must say so instead of exiting 0.
  local epic child
  epic="$(bd create "AUTH-06: Phase 1 epic" -t epic -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-06","phase":1,"milestone":"v1.0"}}' --silent)"
  child="$(bd create "API-02: live child in phase 2" -t task \
    -l phase-2,m-v1.0 --parent "$epic" \
    --metadata '{"gsd":{"req":"API-02","phase":2,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json --close-completed
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-complete-open") | .status' 'fail'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-complete-open") | .items[] | select(test("could not close"))] | length' '1'
  grep -qF "$epic" <<<"$output"
  grep -qF "open child" <<<"$output"   # bd's own refusal reason is relayed

  # Nothing was forced: the epic and its live child are both still open.
  run bd show "$epic" --json
  assert_json_eq "$output" '.[0].status' 'open'
  run bd show "$child" --json
  assert_json_eq "$output" '.[0].status' 'open'

  # Same verdict in the human report.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 7 ]
  grep -qF "✗ phase-complete-open" <<<"$output"
  grep -qF "[cairn-doctor] FAIL" <<<"$output"
}

@test "orphans: unknown phase label and phase-less issue warn; migrated-todo exempt" {
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

@test "label-pairs: phase-only label warns, --fix-labels repairs, re-run clean" {
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

@test "--fix-labels refuses when the milestone is unresolvable, exit 2" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # no milestone in STATE.md or ROADMAP.md
  make_doctor_fixture
  bd create "Stray unpaired task" -t task -l phase-2 --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --fix-labels
  [ "$status" -eq 2 ]
  grep -qF "milestone unresolvable" <<<"$output"
}

@test "claims-stale: assigned in_progress issue outside the active phase warns" {
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

@test "bd-doctor: summary line captured in the report" {
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

@test "gsd-capability: an unloadable gsd-core manifest fails and outranks registration" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # A stub install whose manifest carries the upstream defect: it declares the
  # standard hooks path, so Claude Code refuses the whole plugin. The capability
  # itself is registered and staged — the point is that this outranks it,
  # because a plugin that will not load exposes no /gsd:* commands.
  root="$PWD/plug"
  mkdir -p "$root/.claude-plugin" "$root/hooks" "$root/gsd-core/bin"
  printf '{"hooks":[]}\n' > "$root/hooks/hooks.json"
  printf '{"name":"gsd-core","hooks":"./hooks/hooks.json"}\n' \
    > "$root/.claude-plugin/plugin.json"
  cp "$PWD/.gsd-stub" "$root/gsd-core/bin/gsd_run"
  chmod +x "$root/gsd-core/bin/gsd_run"
  export CAIRN_GSD_BIN="$root/gsd-core/bin/gsd_run"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "will NOT load" <<<"$output"
  grep -qF "repair-manifest" <<<"$output"
}

@test "gsd-capability: two GSD lineages installed at once fails the doctor" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The capability itself is fine — registered and staged. The point is that a
  # second GSD can be the one answering /gsd:*, so every other signal being
  # green is exactly the problem.
  home="$PWD/fakehome"
  mkdir -p "$home/.claude/plugins"
  cat > "$home/.claude/plugins/installed_plugins.json" <<'EOF'
{"plugins": {"gsd@cairngo": [{"scope": "user"}],
             "gsd-core@cairngo": [{"scope": "user"}]}}
EOF
  # HOME moves version-manager shims off PATH, so rebuild PATH with a real
  # python3 plus bd's own directory (same trap as the no-GSD-binary test).
  run env HOME="$home" PATH="/usr/bin:/bin:$(dirname "$(command -v bd)")" \
    CAIRN_GSD_BIN="$CAIRN_GSD_BIN" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "two GSD lineages installed" <<<"$output"
  grep -qF "claude plugin uninstall gsd@cairngo" <<<"$output"
}
