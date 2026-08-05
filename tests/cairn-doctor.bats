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
  assert_json_eq "$output" '.checks | length' '16'
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
  # A new open issue (not a close) keeps disk/bd corroboration agreeing —
  # phase 2 stays "not done" on both sides — while still making the map
  # stale, which is all this test needs.
  bd create "API-02: Second endpoint" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-02","phase":2,"milestone":"v1.0"}}' \
    --silent >/dev/null   # map 2 NOT regenerated

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
  # phase-complete-open itself only WARNs here, but phase-corroboration
  # (check 11) independently reads the same fact — phase 1 verified on
  # disk, one of its issues still open — as its R1 "blocks" rule (disk vs
  # bd), so the OVERALL run fails until the straggler is closed.
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '1'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
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
  # VERIFICATION.md still exists, so disk still reads "verified" — an open
  # issue in a verified phase is also phase-corroboration's R1 "blocks"
  # conflict (check 11), which is why the run fails overall even though
  # phase-complete-open itself only warns.
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '2'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
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

  # Gap 1: the PLAN is there, its SUMMARY is not. VERIFICATION.md still
  # exists, so disk still reads "verified" to phase-corroboration — an
  # open issue (AUTH-04) in a verified phase is its R1 "blocks" conflict
  # (check 11), so the run fails overall even though phase-complete-open
  # itself only warns.
  rm .planning/phases/01-auth/01-01-SUMMARY.md
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  grep -qF "01-01-PLAN.md lacks its SUMMARY" <<<"$output"
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'

  # Gap 2: no phase directory at all — the note used to blame a missing
  # SUMMARY for a phase that has no PLAN to lack one. disk now reads
  # "none"; roadmap still marks phase 1 complete, which is R2's "blocks"
  # conflict (roadmap vs disk) — still failing, for a different reason.
  rm -rf .planning/phases/01-auth
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  grep -qF "no phase directory on disk" <<<"$output"
  refute_in_output "lacks its SUMMARY"
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
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
  refute_in_output "✗"
  # phase-corroboration (check 11) still reports one "informs" item — this
  # fixture marks phase 2 complete on disk without also moving STATE.md's
  # active_phase off 2, a real (non-blocking) staleness the check exists to
  # surface — so a blanket refute of "⚠" would now fail for a legitimate
  # reason. Assert the specific check is clean AND pin the warning that is
  # expected, so an unexpected SECOND warning from any other check still
  # breaks this test — which is the property the blanket refute was
  # carrying, and the reason not to simply drop it.
  grep -qF "✓ phase-complete-open" <<<"$output"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" '[.checks[] | select(.status=="warn")] | length' '1'
  assert_json_eq "$output" '.checks[] | select(.status=="warn") | .id' 'phase-corroboration'
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
  # claims-stale itself only WARNs, but phase-corroboration (check 11)
  # independently reads the same fact — phase 1 verified on disk, one of
  # its issues in_progress — as its R1 "blocks" conflict (disk vs bd), so
  # the OVERALL run fails until the claim is resolved.
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.active_phase' '2'
  assert_json_eq "$output" '.checks[] | select(.id=="claims-stale") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="claims-stale") | .items | length' '1'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
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

# --------------------------------------------------------------------------- #
# phase-corroboration (check 11, CORR-06) — 13-03
# --------------------------------------------------------------------------- #

# Point STATE.md's active_phase at N (fixture always ships '"2"').
set_state_active_phase() {
  python3 - "$1" <<'PY'
import re
import sys
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(re.sub(r'active_phase: ".*?"', f'active_phase: "{sys.argv[1]}"',
                     p.read_text()))
PY
}

@test "phase-corroboration: clean fixture reports ok with no items" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .items | length' '0'
}

@test "phase-corroboration: disk-vs-bd blocks conflict fails the check and the run, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 verified on disk and roadmap-complete
  make_doctor_fixture
  # Plan 13-01's canonical "blocks" scenario: disk says phase 1 is done
  # (SUMMARY + VERIFICATION exist), bd still has an open issue for it.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(startswith("1:"))] | length' '1'
  grep -qF "disk reports phase 1 verified" <<<"$output"
  grep -qF "close the open bd issue(s) if the work is done" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ phase-corroboration" <<<"$output"
  grep -qF "[cairn-doctor] FAIL" <<<"$output"
}

@test "phase-corroboration: state_md-vs-disk informs conflict warns, never fails the run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 verified, phase 2 active
  make_doctor_fixture
  # Point the workflow pointer at the phase that already shipped — a stale
  # pointer (R3, informs) with nothing else disagreeing.
  set_state_active_phase 1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # informs never fails the run (D-10)
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .items | length' '1'
  grep -qF "STATE.md still points at phase 1, disk already reports verified" <<<"$output"
  grep -qF "STATE.md's active_phase looks stale" <<<"$output"
}

@test "phase-corroboration: recommendation text is routed per conflict source pair" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Both a "blocks" (disk vs bd) AND an "informs" (state_md vs disk)
  # conflict on the SAME phase in the SAME run — the routed recommendation
  # must differ per item, not bleed from one item's text into the other's.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  set_state_active_phase 1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(test("disk reports")) | select(test("close the open bd issue"))] | length' '1'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(test("STATE.md still points")) | select(test("close the open bd issue"))] | length' '0'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(test("STATE.md still points")) | select(test("looks stale"))] | length' '1'
}

# --------------------------------------------------------------------------- #
# phase-corroboration's last-moved enrichment (JOUR-02) — 16-05
# --------------------------------------------------------------------------- #

@test "last-moved: a real conflict item names each cited source's last-moved timestamp, or 'never observed'" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Plan 13-01's canonical "blocks" scenario: disk says phase 1 is done,
  # bd still has an open issue for it.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  # Seed phase 1's disk axis directly (cairn-journal.py observe, NOT
  # through any /cairn:status render), so its last-moved timestamp is a
  # KNOWN value captured straight from the seed call — never guessed.
  local seed_output seeded_ts
  seed_output="$(printf '[{"phase":1,"evidence":{"disk":"verified"}}]' \
    | python3 "$CAIRN_SCRIPTS_DIR/cairn-journal.py" observe --project-dir "$PWD" --json)"
  seeded_ts="$(jq -r '.written[0].ts' <<<"$seed_output")"
  [ -n "$seeded_ts" ]
  [ "$seeded_ts" != "null" ]

  # A CAIRN_JOURNAL stub that blocks ONLY the `observe` subcommand (the
  # exact call cairn-status.py's own internal journal wiring, Plan 16-04,
  # makes as part of computing this very conflict) but execs into the
  # REAL cairn-journal.py for every other subcommand. Without this, bd's
  # first-ever real value would be observed and journaled moments before
  # doctor's own last-moved read — this stub is what keeps bd genuinely
  # "never observed" while disk's earlier seed stays exactly as written.
  local stub="$BATS_TEST_TMPDIR/observe-blocking-journal.py"
  cat > "$stub" <<'PYEOF'
#!/usr/bin/env python3
import os, sys
if sys.argv[1] == "observe":
    sys.exit(1)
os.execv(sys.executable,
         [sys.executable, os.environ["CAIRN_JOURNAL_REAL"]] + sys.argv[1:])
PYEOF
  chmod +x "$stub"

  run env CAIRN_JOURNAL="$stub" \
      CAIRN_JOURNAL_REAL="$CAIRN_SCRIPTS_DIR/cairn-journal.py" \
      bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'

  local item
  item="$(jq -r '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(startswith("1:"))][0]' <<<"$output")"
  [ "$item" != "null" ]
  grep -qF "disk last moved $seeded_ts" <<<"$item"
  grep -qF "bd last moved never observed" <<<"$item"
}

@test "last-moved: a broken CAIRN_JOURNAL leaves status/detail identical to a working journal, only the clause is missing" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  local working_status working_count
  working_status="$(jq -r '.checks[] | select(.id=="phase-corroboration") | .status' <<<"$output")"
  working_count="$(jq -r '.checks[] | select(.id=="phase-corroboration") | .items | length' <<<"$output")"
  grep -qF "last moved" <<<"$output"

  run env CAIRN_JOURNAL=/nonexistent/path bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  local broken_status broken_count
  broken_status="$(jq -r '.checks[] | select(.id=="phase-corroboration") | .status' <<<"$output")"
  broken_count="$(jq -r '.checks[] | select(.id=="phase-corroboration") | .items | length' <<<"$output")"
  [ "$broken_status" = "$working_status" ]
  [ "$broken_count" = "$working_count" ]
  refute_in_output "last moved"
}

@test "last-moved: journal_last_moved() is called at most once per phase, not once per conflict item" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Phase 2 with BOTH a disk-vs-bd AND a roadmap-vs-disk conflict at once
  # (the plan's own example): roadmap ticked, disk still "planned" (a
  # PLAN.md, no SUMMARY yet), bd's only phase-2 issue closed.
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/ROADMAP.md")
p.write_text(p.read_text().replace("- [ ] **Phase 2: API**",
                                   "- [x] **Phase 2: API**"))
PY
  bd close "$DOC_P2" >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  local stub="$BATS_TEST_TMPDIR/counting-journal.py"
  local count_file="$BATS_TEST_TMPDIR/last-moved-call-count"
  cat > "$stub" <<'PYEOF'
#!/usr/bin/env python3
import os, sys
with open(os.environ["CAIRN_JOURNAL_CALL_COUNT_FILE"], "a") as f:
    f.write(sys.argv[1] + "\n")
os.execv(sys.executable,
         [sys.executable, os.environ["CAIRN_JOURNAL_REAL"]] + sys.argv[1:])
PYEOF
  chmod +x "$stub"

  run env CAIRN_JOURNAL="$stub" \
      CAIRN_JOURNAL_CALL_COUNT_FILE="$count_file" \
      CAIRN_JOURNAL_REAL="$CAIRN_SCRIPTS_DIR/cairn-journal.py" \
      bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(startswith("2:"))] | length' '2'

  [ -f "$count_file" ]
  local n_last_moved
  n_last_moved="$(grep -c '^last-moved$' "$count_file" || true)"
  [ "$n_last_moved" -eq 1 ]
}

# --------------------------------------------------------------------------- #
# .gitignore — the journal entry and its compaction siblings (Plan 16-05)
# --------------------------------------------------------------------------- #

@test "gitignore: journal.jsonl and its compaction temp siblings are never staged by git add -A" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The .gitignore under test is the REPO'S OWN — copied into the fixture
  # so this proves the actual entry takes effect, not a fixture stand-in.
  cp "$CAIRN_REPO_ROOT/.gitignore" .gitignore

  # Seed a real conflict (same fixture shape as the last-moved tests
  # above) so the journal carries genuine content, not an empty stub.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  [ -f .cairn/journal.jsonl ]

  # A leftover compaction temp sibling and its lock file — the exact
  # shape compact()'s sibling-write-then-rename recipe (Plan 16-02) can
  # leave behind after a crash, and the flock file it holds during a live
  # compaction.
  : > .cairn/journal.jsonl.tmp-abc123
  : > .cairn/journal.jsonl.compact.lock

  git add -A

  run git status --porcelain
  refute_in_output "journal.jsonl"

  run git diff --cached --name-only
  refute_in_output "journal.jsonl"
}

# --------------------------------------------------------------------------- #
# phase-artifacts (check 12, CARD-02/D-04) — 14-03
# --------------------------------------------------------------------------- #

# Give phase 2's existing 02-01-PLAN.md a SUMMARY.md (so it stops being the
# ordinary mid-flight gap the healthy fixture ships with) and add a second
# plan, 02-02-PLAN.md, deliberately left without one — the "two plans, only
# one summarized" shape check_phase_artifacts' missing-SUMMARY half looks
# for. ROADMAP.md's phase-2 checkbox is left unticked throughout (the
# fixture never ticks it), so any item here is coming from disk_state, not
# from check 5's ROADMAP-complete gate.
make_phase2_two_plans_one_summary() {
  cat > .planning/phases/02-api/02-01-SUMMARY.md <<'EOF'
---
phase: 02-api
plan: "01"
subsystem: api
tags: [python, api]
provides:
  - rate limiting middleware in src/api.py
key-files:
  created: [src/api.py]
  modified: []
key-decisions: []
duration: 8min
completed: 2026-07-21
status: complete
---

# Phase 2: API Summary (Minimal)

**Rate limiting middleware implemented and tested.**
EOF
  cat > .planning/phases/02-api/02-02-PLAN.md <<'EOF'
---
phase: 02-api
plan: "02"
type: execute
wave: 1
depends_on: []
files_modified: [src/api_extra.py]
autonomous: true
requirements: []
must_haves:
  truths: []
  artifacts: []
  key_links: []
---

<objective>
Second plan in phase 2, deliberately left without a SUMMARY.md — the
missing-SUMMARY fixture for phase-artifacts.

Purpose: exercise check_phase_artifacts' missing-SUMMARY half.
Output: src/api_extra.py
</objective>

<tasks>

<task type="auto">
  <name>Task 1: placeholder</name>
  <files>src/api_extra.py</files>
  <action>placeholder</action>
  <verify>true</verify>
  <done>placeholder</done>
</task>

</tasks>
EOF
}

# NN-VERIFICATION.md with a readable status: field — pushes phase 2's
# disk_state to "verified" without itself triggering the unreadable-status
# half.
add_phase2_verification_passed() {
  cat > .planning/phases/02-api/02-VERIFICATION.md <<'EOF'
---
phase: 02-api
verified: 2026-07-25T10:00:00Z
status: passed
score: 1/1 must-haves verified
behavior_unverified: 0
---

# Phase 2: API Verification Report

**Status:** passed
EOF
}

# NN-VERIFICATION.md with a readable frontmatter block but NO status:
# field — the unreadable-verdict fixture.
add_phase2_verification_no_status() {
  cat > .planning/phases/02-api/02-VERIFICATION.md <<'EOF'
---
phase: 02-api
verified: 2026-07-25T10:00:00Z
---

# Phase 2: API Verification Report (status field omitted)
EOF
}

# Pushing phase 2 to disk_state "verified" without this would ALSO trip
# phase-corroboration's own R1/R3 axes (DOC_P2, phase 2's bd issue, is
# still open; STATE.md's active_phase fixture default is "2"), confounding
# the assertions below with a second, unrelated check's findings. Closes
# the issue, regenerates its map (closing changes the map's status column,
# see maps-fresh), and points active_phase somewhere that collides with no
# real phase — isolating these tests to phase-artifacts' own behavior, the
# same way the phase-corroboration tests above build single-conflict
# fixtures on purpose.
neutralize_phase2_corroboration() {
  bd close "$DOC_P2" >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  set_state_active_phase 99
}

@test "phase-artifacts: clean fixture reports ok with no items" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .items | length' '0'
}

@test "phase-artifacts: verified phase with an unsummarized plan warns, names the file, never fails the run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 2's checkbox stays unticked throughout
  make_doctor_fixture
  make_phase2_two_plans_one_summary
  add_phase2_verification_passed
  neutralize_phase2_corroboration

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # a phase-artifacts warn never turns the run exit 7
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .status' 'warn'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-artifacts") | .items[] | select(. == "phase 2: 02-02-PLAN.md lacks its SUMMARY")] | length' '1'
}

@test "phase-artifacts: same two-plan/one-summary phase with NO VERIFICATION.md produces zero items (mid-flight regression)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Identical to the warn case above MINUS add_phase2_verification_passed —
  # this is the exact false positive an earlier, ungated draft produced and
  # a plan-checker caught: a phase between waves, with some plans still
  # unsummarized, disk_state never having reached "verified". It must stay
  # green forever, not just today.
  make_phase2_two_plans_one_summary
  # Adding 02-01-SUMMARY.md alone (with no VERIFICATION.md) already moves
  # phase 2's disk_state from "planned" to "executed" — still short of
  # "verified", so phase-artifacts' own gate is unaffected, but it is
  # ALSO enough to trip phase-corroboration's disk-vs-bd axis against the
  # still-open DOC_P2 (an unrelated confound this test isn't about).
  neutralize_phase2_corroboration

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .status' 'ok'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-artifacts") | .items[] | select(startswith("phase 2:"))] | length' '0'
}

@test "phase-artifacts: verified phase with an unreadable VERIFICATION status warns, never fails the run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Give 02-01 its summary so this scenario isolates the unreadable-status
  # half — no missing-SUMMARY noise mixed into the same item set.
  cat > .planning/phases/02-api/02-01-SUMMARY.md <<'EOF'
---
phase: 02-api
plan: "01"
subsystem: api
tags: [python, api]
provides:
  - rate limiting middleware in src/api.py
key-files:
  created: [src/api.py]
  modified: []
key-decisions: []
duration: 8min
completed: 2026-07-21
status: complete
---

# Phase 2: API Summary (Minimal)

**Rate limiting middleware implemented and tested.**
EOF
  add_phase2_verification_no_status
  neutralize_phase2_corroboration

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .status' 'warn'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-artifacts") | .items[] | select(. == "phase 2: has a VERIFICATION.md but no readable '"'"'status:'"'"' field in its frontmatter")] | length' '1'
}

@test "phase-artifacts: a lone phase-artifacts warn never turns an otherwise-clean run into a failure" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  make_phase2_two_plans_one_summary
  add_phase2_verification_passed
  neutralize_phase2_corroboration

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '[.checks[] | select(.status=="fail")] | length' '0'
  assert_json_eq "$output" '[.checks[] | select(.status=="warn")] | .[0].id' 'phase-artifacts'
  assert_json_eq "$output" '[.checks[] | select(.status=="warn")] | length' '1'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⚠ phase-artifacts" <<<"$output"
  refute_in_output "✗"
  grep -qF "[cairn-doctor] ok" <<<"$output"
}

# --------------------------------------------------------------------------- #
# external-ref (check 13, CORR-08/D-11) — 13-03
# --------------------------------------------------------------------------- #

@test "external-ref: unambiguous git match reported by default, --link-refs backfills, idempotent" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Isolate the scenario to DOC_A1: DOC_A2 already carries an external_ref,
  # so it drops out of `lacking` and stays out of what is asserted here.
  bd update "$DOC_A2" --external-ref gh-1 >/dev/null
  mkdir -p src
  echo "def signup(): pass" >> src/auth.py
  git add src/auth.py
  git commit -qm "feat(auth): add signup handler (#42)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'warn'
  assert_json_eq "$output" \
    "[.checks[] | select(.id==\"external-ref\") | .items[] | select(. == \"$DOC_A1 -> gh-42\")] | length" '1'

  # Nothing written yet — the default run is read-only.
  run bd show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref // "none"' 'none'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --link-refs
  [ "$status" -eq 0 ]
  grep -qF "linked $DOC_A1 -> gh-42" <<<"$output"

  run bd show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref' 'gh-42'

  # Idempotent: a second run (a fresh process reading fresh bd state) has
  # nothing left to link.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json --link-refs
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'ok'
  refute_in_output "linked"
}

@test "external-ref: two different PR numbers in the window is ambiguous, never a candidate" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  bd update "$DOC_A2" --external-ref gh-1 >/dev/null
  mkdir -p src
  echo "one" >> src/auth.py
  git add src/auth.py
  git commit -qm "wip: signup tweak (#10)"
  echo "two" >> src/auth.py
  git add src/auth.py
  git commit -qm "wip: another tweak (#11)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .items | length' '0'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --link-refs
  [ "$status" -eq 0 ]
  run bd show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref // "none"' 'none'
}

@test "external-ref: a real shallow clone skips --link-refs entirely, writes nothing (D-08)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  mkdir -p src
  echo "def signup(): pass" >> src/auth.py
  git add src/auth.py
  git commit -qm "feat(auth): add signup handler (#42)"

  # A REAL shallow clone (git clone --depth 1), per STACK.md's verified
  # recipe — not a simulated flag. bd's actual data lives under a
  # gitignored embeddeddolt/ dir that a plain clone never carries, and
  # .planning/ here was never committed either, so both are copied across
  # the same way an operator would after cloning.
  local src_repo="$PWD"
  local clone_dir="$BATS_TEST_TMPDIR/ext-ref-shallow-clone"
  git clone --depth 1 -q "file://$src_repo" "$clone_dir"
  rm -rf "$clone_dir/.beads"
  cp -r "$src_repo/.beads" "$clone_dir/.beads"
  chmod 700 "$clone_dir/.beads"
  cp -r "$src_repo/.planning" "$clone_dir/.planning"

  run git -C "$clone_dir" rev-parse --is-shallow-repository
  [ "$output" = "true" ]

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --project-dir "$clone_dir" \
    --json --link-refs
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'warn'
  grep -qF "shallow clone" <<<"$output"

  run bd -C "$clone_dir" show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref // "none"' 'none'
}

@test "external-ref: composes with --close-completed in one invocation" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 checked off in ROADMAP.md
  make_doctor_fixture
  bd update "$DOC_A2" --external-ref gh-1 >/dev/null
  mkdir -p src
  echo "def signup(): pass" >> src/auth.py
  git add src/auth.py
  git commit -qm "feat(auth): add signup handler (#42)"
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json --link-refs --close-completed
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'ok'

  run bd show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref' 'gh-42'
  run bd show "$straggler" --json
  assert_json_eq "$output" '.[0].status' 'closed'
}

# --------------------------------------------------------------------------- #
# lease-stale (check 13, LEASE-05) — 15-03
# --------------------------------------------------------------------------- #

LEASE="$CAIRN_SCRIPTS_DIR/cairn-lease.sh"

# Hand-set a lease issue's heartbeat_at to hours-in-the-past via bd update
# directly (same technique as tests/cairn-lease.bats' own staleness
# fixture) — never a real 4-hour sleep.
stale_lease_heartbeat() {
  local lease_id="$1" phase="$2" holder="$3" acquired_at="$4" hours_ago="$5"
  local stale_ts
  stale_ts="$(python3 -c "
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) - timedelta(hours=$hours_ago)).isoformat())
")"
  bd update "$lease_id" --metadata \
    "{\"cairn\":{\"lease\":{\"phase\":$phase,\"holder\":\"$holder\",\"actor\":\"a\",\"host\":\"h\",\"acquired_at\":\"$acquired_at\",\"heartbeat_at\":\"$stale_ts\"}}}" \
    >/dev/null
}

@test "lease-stale: a lease with a heartbeat older than 4h warns, itemized by phase and holder, exit 0" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$LEASE" acquire 2 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local lease_id acquired_at holder
  lease_id="$(jq -r '.id' <<<"$output")"
  acquired_at="$(jq -r '.acquired_at' <<<"$output")"
  holder="$(jq -r '.holder' <<<"$output")"

  stale_lease_heartbeat "$lease_id" 2 "$holder" "$acquired_at" 5

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # WARN never fails the doctor run (D-04/LEASE-05)
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .items | length' '1'
  grep -qF "phase 2" <<<"$output"
  grep -qF "$holder" <<<"$output"
  grep -qF "reclaimable" <<<"$output"
  grep -qF "cairn-lease.sh release 2" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⚠ lease-stale" <<<"$output"
}

@test "lease-stale: a freshly-acquired lease (no stale heartbeat) reads ok, empty items" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$LEASE" acquire 2 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .items | length' '0'
}

@test "lease-stale: the lease bookkeeping issue is exempt from check 6 (orphans) even vacant" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$LEASE" acquire 2 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$LEASE" release 2 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .items | length' '0'
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .status' 'ok'
}

@test "lease-stale: cairn-lease.py itself failing degrades to warn, never crashes the doctor run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  # A bd wrapper that fails ONLY the lease-label lookup cairn-lease.py's
  # status --all makes ('bd ... -l lease ...'), passing every other
  # invocation straight through to the real bd. Same PATH-stub seam as the
  # "bd missing from PATH" test above, narrowed to a single sibling
  # script's own bd call instead of bd being entirely absent — the only
  # way to observe lease-stale actually degrade while the REST of the
  # doctor run completes normally.
  local real_bd
  real_bd="$(command -v bd)"
  local stub="$BATS_TEST_TMPDIR/bd-lease-fail-bin"
  mkdir -p "$stub"
  cat > "$stub/bd" <<EOF
#!/usr/bin/env bash
for a in "\$@"; do
  if [ "\$a" = "lease" ]; then
    echo "bd: simulated lease lookup failure" >&2
    exit 1
  fi
done
exec "$real_bd" "\$@"
EOF
  chmod +x "$stub/bd"

  run env PATH="$stub:$PATH" bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .status' 'warn'
  grep -qF "lease staleness could not be computed" <<<"$output"
  # The failure stayed scoped to lease-stale — nothing else regressed.
  assert_json_eq "$output" \
    '[.checks[] | select(.id != "lease-stale" and .status != "ok")] | length' '0'
}

# --------------------------------------------------------------------------- #
# --apply-reconciliation (ESC-03, Phase 17 Plan 3) — the human-invoked,
# separate command that applies a verified semantic-escalation reconciliation
# proposal. Not a check: a fixer, tested the same way --close-completed and
# --fix-labels are, against a real conflicted fixture and a real bd.
# --------------------------------------------------------------------------- #

RECONCILE="$CAIRN_SCRIPTS_DIR/cairn-reconcile.sh"

# The same disk-vs-bd "blocks" corroboration conflict the phase-corroboration
# tests above build (line ~833): phase 1 verified on disk and roadmap-
# complete, one straggler bd issue for phase 1 still open — the recipe that
# makes `cairn-reconcile.py collect 1` succeed with a "conflict" verdict
# instead of refusing. Exports RECON_STRAGGLER (the open issue's id).
make_conflicted_fixture() {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  RECON_STRAGGLER="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
}

# A fresh, evidence-hash-current reconciliation proposal for PHASE: a
# bd_close claim naming TARGET (any bd id — callers pick one in or out of
# PHASE's own labels) plus a manual_review claim, both citing REAL lines
# from ROADMAP.md so citation verification passes. Calls a real `collect`
# to capture the CURRENT evidence_hash — the same hash
# --apply-reconciliation's own freshness re-check will re-derive and
# compare against, so a proposal built by this helper and applied
# immediately always starts out valid on both axes.
write_valid_proposal() {
  local phase="$1" target="$2"
  local ehash
  ehash="$(bash "$RECONCILE" collect "$phase" --project-dir "$PWD" --json | jq -r '.evidence_hash')"
  local line1
  line1="$(sed -n '1p' .planning/ROADMAP.md)"
  mkdir -p .cairn
  python3 - "$phase" "$ehash" "$target" "$line1" <<'PY'
import json
import sys

phase, ehash, target, line1 = sys.argv[1:5]
proposal = {
    "phase": int(phase),
    "generated_at": "2026-07-31T00:00:00Z",
    "evidence_hash": ehash,
    "claims": [
        {
            "statement": f"{target} is an open straggler in a phase disk "
                         "already reports verified.",
            "citations": [
                {"file": ".planning/ROADMAP.md", "line": 1, "text": line1}
            ],
            "recommended_action": {"type": "bd_close", "issue": target,
                                    "reason": "phase complete, straggler stale"}
        },
        {
            "statement": "A separate, ambiguous finding needs a human look.",
            "citations": [
                {"file": ".planning/ROADMAP.md", "line": 1, "text": line1}
            ],
            "recommended_action": {"type": "manual_review", "issue": None,
                                    "note": "ambiguous, needs a human"}
        }
    ]
}
with open(".cairn/conflicts.json", "w") as f:
    json.dump(proposal, f)
PY
}

@test "apply-reconciliation: no .cairn/conflicts.json -> clean refusal, no crash" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"
  grep -qiF "no proposal" <<<"$output"
}

@test "apply-reconciliation: a stale evidence_hash is refused, bd state unchanged" {
  require_bd
  make_conflicted_fixture
  local bd_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"

  write_valid_proposal 1 "$RECON_STRAGGLER"
  # Corrupt the stored hash to a plausible-looking but wrong one — the
  # tree did not actually move, but the proposal's own claim about its
  # evidence no longer matches what a fresh collect produces.
  python3 - <<'PY'
import json
from pathlib import Path
p = Path(".cairn/conflicts.json")
data = json.loads(p.read_text())
data["evidence_hash"] = "sha256:" + "0" * 64
p.write_text(json.dumps(data))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 7 ]
  grep -qF "proposal is stale" <<<"$output"

  local bd_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  [ "$bd_before" = "$bd_after" ]
  run bd show "$RECON_STRAGGLER" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "apply-reconciliation: a proposal with one wrong citation is refused wholesale, bd state unchanged" {
  require_bd
  make_conflicted_fixture
  local bd_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"

  write_valid_proposal 1 "$RECON_STRAGGLER"
  # Poison ONE citation's text so it no longer matches what is really on
  # line 1 — the other claim's citation is left correct (D-03's trap: one
  # bad citation must still reject the WHOLE proposal).
  python3 - <<'PY'
import json
from pathlib import Path
p = Path(".cairn/conflicts.json")
data = json.loads(p.read_text())
data["claims"][0]["citations"][0]["text"] = \
    "this is definitely not what line 1 of ROADMAP.md says"
p.write_text(json.dumps(data))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 7 ]
  grep -qF "citation verification" <<<"$output"

  local bd_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  [ "$bd_before" = "$bd_after" ]
  run bd show "$RECON_STRAGGLER" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "apply-reconciliation: correct citations do not excuse a claim naming an id outside phase N, bd state unchanged" {
  require_bd
  make_conflicted_fixture
  local bd_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"

  # $DOC_P2 (make_doctor_fixture's phase-2 issue) carries no phase-1 label.
  # Every citation in this proposal is genuinely correct — the ONLY defect
  # is that the bd_close claim targets an issue outside the phase being
  # reconciled.
  write_valid_proposal 1 "$DOC_P2"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 7 ]
  grep -qF "issue-provenance" <<<"$output"
  grep -qF "carries no phase-1 label" <<<"$output"

  local bd_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  [ "$bd_before" = "$bd_after" ]
  run bd show "$DOC_P2" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "apply-reconciliation: every claim is enumerated in output BEFORE the first bd write happens" {
  require_bd
  make_conflicted_fixture
  write_valid_proposal 1 "$RECON_STRAGGLER"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 0 ]
  # Both claims — the bd_close AND the manual_review — appear in the
  # enumeration.
  grep -qF "will close $RECON_STRAGGLER" <<<"$output"
  grep -qF "skipped (manual review" <<<"$output"

  # ...and BOTH enumerated lines precede the first bd 'closed' confirmation
  # line: the FULL plan prints before the first write, never interleaved
  # enumerate-then-apply-then-enumerate-next.
  local enum_line1 enum_line2 close_line
  enum_line1="$(grep -nF "will close $RECON_STRAGGLER" <<<"$output" | head -1 | cut -d: -f1)"
  enum_line2="$(grep -nF "skipped (manual review" <<<"$output" | head -1 | cut -d: -f1)"
  close_line="$(grep -nF "closed $RECON_STRAGGLER —" <<<"$output" | head -1 | cut -d: -f1)"
  [ -n "$close_line" ]
  [ "$enum_line1" -lt "$close_line" ]
  [ "$enum_line2" -lt "$close_line" ]
}

@test "apply-reconciliation: a valid fresh proposal actually closes the bd_close issue; manual_review never touches bd" {
  require_bd
  make_conflicted_fixture
  write_valid_proposal 1 "$RECON_STRAGGLER"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 0 ]
  grep -qF "1 applied, 1 skipped (manual review), 0 refused by bd" <<<"$output"

  run bd show "$RECON_STRAGGLER" --json
  assert_json_eq "$output" '.[0].status' 'closed'
}

@test "apply-reconciliation: an unrecognized recommended_action.type refuses the WHOLE apply, bd state unchanged" {
  require_bd
  make_conflicted_fixture
  local bd_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"

  write_valid_proposal 1 "$RECON_STRAGGLER"
  # Corrupt the SECOND claim's type to something outside the closed
  # vocabulary — the FIRST claim is a perfectly valid bd_close, proving one
  # bad claim refuses the whole proposal, never just its own.
  python3 - <<'PY'
import json
from pathlib import Path
p = Path(".cairn/conflicts.json")
data = json.loads(p.read_text())
data["claims"][1]["recommended_action"]["type"] = "bd_delete"
p.write_text(json.dumps(data))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 7 ]
  grep -qF "unrecognized recommended_action.type" <<<"$output"

  local bd_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  [ "$bd_before" = "$bd_after" ]
  run bd show "$RECON_STRAGGLER" --json
  assert_json_eq "$output" '.[0].status' 'open'
}


#-----------------------------------------------------------------------------
# release-versions (check 15, REL-02) — 19-01
#-----------------------------------------------------------------------------

# Write cairn's own version carriers into the fixture at their REAL paths and
# REAL key paths — plugin.json's top-level `version`, marketplace.json's
# NESTED `metadata.version`, the CHANGELOG's first released heading,
# capability.json's own axis. $1 = lockstep version, $2 = the marketplace
# version (default: the same, i.e. agreement).
write_release_carriers() {
  local version="$1" market="${2:-$1}"
  mkdir -p cairn/.claude-plugin .claude-plugin cairn/capability
  printf '{"name": "cairn", "version": "%s"}\n' "$version" \
    > cairn/.claude-plugin/plugin.json
  printf '{"name": "cairngo", "metadata": {"version": "%s"}, "plugins": []}\n' \
    "$market" > .claude-plugin/marketplace.json
  printf '{"id": "cairn", "version": "1.0.0"}\n' \
    > cairn/capability/capability.json
  cat > CHANGELOG.md <<EOF
# Changelog

## [$version] - 2026-08-01

### Added

- fixture entry
EOF
}

# Break: make the absence of the plugin manifests a failure. Red here — and it
# would have turned every user's doctor red too, since no wired repo carries
# cairn's own manifests.
@test "release-versions: a repo without cairn's plugin manifests reads ok and never fails the doctor" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .items | length' '0'
  grep -qF "not applicable" <<<"$output"
}

# Break: register the check as `warn`, or forget to add it to the `checks`
# list at all — red in both cases (warn never reaches exit 7; an absent check
# never appears in the report).
@test "release-versions: a diverging carrier fails the check and takes the doctor to exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  # First: the carriers agree, so the check is ok and the doctor still exits 0.
  write_release_carriers 1.5.0
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .detail' \
    'every version carrier agrees on 1.5.0, git tag v1.5.0 pending'

  # Then the third carrier drifts — the exact drift that shipped three times.
  write_release_carriers 1.5.0 1.4.2
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .status' 'fail'
  assert_json_eq "$output" '.ok' 'false'
  grep -qF "metadata.version" <<<"$output"
  grep -qF "1.4.2" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ release-versions" <<<"$output"
}

#-----------------------------------------------------------------------------
# test-parallel (check 16, AUTO-04) — 29-06
#
# The environment dimension is controlled through BATS' OWN seam,
# BATS_PARALLEL_BINARY_NAME (bats-exec-suite:8), rather than by rebuilding
# PATH: it is the same variable bats itself reads to decide which binary to
# fan out through, so pointing it at something that exists (or does not) asks
# the check exactly the question bats would ask. Rebuilding PATH would also
# have to keep bd, git and python3 reachable, which is a lot of machinery for
# a question with a one-variable answer.
#
# The two branches that do NOT depend on this machine (no bats at all; the
# report itself unavailable) go through the CAIRN_TEST seam with a stub
# reporter, the same way the release check is driven through CAIRN_RELEASE.
#-----------------------------------------------------------------------------

# Break: drop the applicability guard. Red here — and it would put a warning
# about GNU parallel in front of every user of a wired repo, about a bats
# suite they do not have.
@test "test-parallel: a repo without cairn's plugin manifest reads ok and says not applicable" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .detail | contains("not applicable")' 'true'
}

@test "test-parallel: with the prerequisites present the check is ok and names the job count" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The FULL set of carriers, not just plugin.json: that file is also check
  # 15's applicability marker, so writing it alone turns release-versions on
  # with nothing to agree with and takes the doctor to exit 7 for an
  # unrelated reason.
  write_release_carriers 1.5.0

  # `bash` stands in for the parallel binary: it exists on every machine this
  # suite runs on, so the ok branch is asserted deterministically instead of
  # depending on whether the developer happens to have GNU parallel.
  run env BATS_PARALLEL_BINARY_NAME=bash \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .detail | contains("bats -j")' 'true'
}

@test "test-parallel: a missing parallel binary warns with the fix and the measured cost, and the doctor still exits 0" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The FULL set of carriers, not just plugin.json: that file is also check
  # 15's applicability marker, so writing it alone turns release-versions on
  # with nothing to agree with and takes the doctor to exit 7 for an
  # unrelated reason.
  write_release_carriers 1.5.0

  run env BATS_PARALLEL_BINARY_NAME=this-binary-does-not-exist \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # Break, and it is the expensive one: turning friction into a blockage.
  # A slow suite is not a state inconsistency, and spending exit 7 on it
  # teaches everyone to ignore exit 7.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'warn'
  assert_json_eq "$output" '.ok' 'true'
  # Break: a warning that names neither the cost nor the cure.
  grep -qF "install parallel" <<<"$output"
  grep -qF "64s serial" <<<"$output"

  run env BATS_PARALLEL_BINARY_NAME=this-binary-does-not-exist \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⚠ test-parallel" <<<"$output"
}

@test "test-parallel: no bats at all warns with a different sentence than 'it will be slow'" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The FULL set of carriers, not just plugin.json: that file is also check
  # 15's applicability marker, so writing it alone turns release-versions on
  # with nothing to agree with and takes the doctor to exit 7 for an
  # unrelated reason.
  write_release_carriers 1.5.0

  local stub="$BATS_TEST_TMPDIR/no-bats-report.py"
  cat > "$stub" <<'PY'
import json
print(json.dumps({"bats": None, "jobs": 8, "jobs_source": "cpu count",
                  "parallel_binary": "parallel", "can_parallelize": True,
                  "blockers": [], "measured_cost": "n/a"}))
PY

  run env CAIRN_TEST="$stub" bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'warn'
  # Break: routing "no bats" into the slow-suite branch. can_parallelize is
  # true in this report, so a check that looked at that field first would
  # report ok on a machine that cannot run the suite at all.
  grep -qF "cannot run here at all" <<<"$output"
}

@test "test-parallel: an unusable environment report degrades to warn, never a crash and never a failure" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The FULL set of carriers, not just plugin.json: that file is also check
  # 15's applicability marker, so writing it alone turns release-versions on
  # with nothing to agree with and takes the doctor to exit 7 for an
  # unrelated reason.
  write_release_carriers 1.5.0

  local stub="$BATS_TEST_TMPDIR/broken-report.py"
  printf 'import sys\nsys.stderr.write("boom\\n")\nsys.exit(1)\n' > "$stub"

  run env CAIRN_TEST="$stub" bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # Break: letting one check's subprocess failure take the whole doctor down,
  # or promoting it to fail. The other fifteen checks still have answers.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'warn'
  grep -qF "exited 1" <<<"$output"
}
