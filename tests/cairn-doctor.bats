#!/usr/bin/env bats
# cairn-doctor.bats — exercises the consistency doctor's CLI contract
# (cairn-doctor.py / the cairn-doctor.sh wrapper):
#   0 all ok or warnings only (warnings never change the exit code) or not
#   applicable, 2 usage / refused --fix-labels, 5 bd unavailable, 7 any
#   check failed.
#
# Each test starts from the HEALTHY wired fixture (all seventeen checks ✓)
# and breaks exactly one check, asserting on that check's reported status.
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

@test "healthy wired fixture: exit 0, nothing warns or fails, and it still reads ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  # `ok`, not INCOMPLETE. This fixture IS a user's repo — it carries none of
  # cairn's own manifests — so 23-02 gave it ⊘ checks. Every one of them is
  # out-of-scope, and the footer must still read ok: this assertion is the
  # mechanical proof that the phase did not trade a permanent false green for
  # a permanent false red in every repo that uses cairn.
  grep -qF "[cairn-doctor] ok" <<<"$output"
  refute_in_output "⚠"
  refute_in_output "✗"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.applicable' 'true'
  assert_json_eq "$output" '.ok' 'true'
  # The count is hardcoded ON PURPOSE: it is the canary for a check that was
  # written and never registered in main()'s `checks` list. 16 -> 17 here
  # came with check 16, test-parallel (29-06); 17 -> 18 with check 17,
  # req-ledger (29-07).
  #
  # It is also the assertion that caught the reporting failure it was built
  # for. It stayed red through a `bats tests/cairn-doctor.bats` whose log was
  # read through `tail -15`, so the failure line scrolled out and the run was
  # called green. The full-suite run through cairn-test.sh is what surfaced
  # it. A number read off the end of a truncated log is not a measurement.
  assert_json_eq "$output" '.checks | length' '18'
  # The exact ordered set, not "unique == ok": after 23-02 this fixture has
  # two ⊘ checks (cairn's own manifests are absent by construction), and an
  # assertion that merely tolerated extra values would stop proving anything.
  assert_json_eq "$output" \
    '[.checks[].status] | unique | sort | join(",")' 'not-applicable,ok'
  # `.failed` is the exact mirror of the exit code, and it is NOT `.ok`'s
  # complement: `.ok` also answers "did every check in scope actually run".
  assert_json_eq "$output" '.failed' 'false'
  # And the load-bearing half: not one of those ⊘ is a gap.
  assert_json_eq "$output" \
    '[.checks[] | select(.status=="not-applicable" and .scope=="no-input")] | length' \
    '0'
}

# Break: derive any counter as `len(checks) - the others`, the shape
# cairn-doctor.py carried before this phase. A fifth status would then land
# in the success bucket in silence — a brand-new false green inside the
# phase that exists to remove them.
@test "report footer: four counters, summing to the check count, none by subtraction" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # One bucket per word of the vocabulary: a status with no symbol has
  # nowhere to be counted, which is the whole point of deriving the buckets
  # from SYMBOL's own keys.
  assert_json_eq "$output" '.counts | length' '4'
  assert_json_eq "$output" \
    '[.counts | to_entries[] | .value] | add' \
    "$(jq -r '.checks | length' <<<"$output")"
  # Recomputed from the check list itself, so the footer's arithmetic is not
  # taken on trust — it has to agree with a number we derived separately.
  assert_json_eq "$output" '.counts.ok' \
    "$(jq -r '[.checks[] | select(.status == "ok")] | length' <<<"$output")"
  assert_json_eq "$output" '.counts["not-applicable"]' \
    "$(jq -r '[.checks[] | select(.status == "not-applicable")] | length' \
        <<<"$output")"
  assert_json_eq "$output" '.counts.warn' \
    "$(jq -r '[.checks[] | select(.status == "warn")] | length' <<<"$output")"
  assert_json_eq "$output" '.counts.fail' \
    "$(jq -r '[.checks[] | select(.status == "fail")] | length' <<<"$output")"
  # Closed vocabulary: subtracting the four leaves nothing behind.
  assert_json_eq "$output" \
    '[.checks[].status] - ["ok","not-applicable","warn","fail"] | length' '0'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qE '^\[cairn-doctor\] ok — [0-9]+ ok, [0-9]+ not-applicable, [0-9]+ warning\(s\), [0-9]+ failure\(s\)$' \
    <<<"$output"
}

# Break: reuse ✓ for the new state, or pick a character that renders two
# columns wide under a CJK locale. The proof is unicodedata, never how the
# glyph looks in this terminal — the same rule phase 21 measured for the
# board's step symbols.
@test "status vocabulary: four symbols, the new one distinct and single-width" {
  make_tmp_repo
  cat > symbol_check.py <<'PY'
import ast
import re
import sys
import unicodedata

src = open(sys.argv[1]).read()
sym = ast.literal_eval(re.search(r"SYMBOL = (\{.*?\})", src, re.S).group(1))
assert set(sym) == {"ok", "not-applicable", "warn", "fail"}, sorted(sym)
na = sym["not-applicable"]
assert na != sym["ok"], f"the new state must not wear the success marker: {na}"
for name, ch in sorted(sym.items()):
    width = unicodedata.east_asian_width(ch)
    assert width == "N", (name, ch, width)
print(f"{na} U+{ord(na):04X} {unicodedata.name(na)}")
PY
  run python3 symbol_check.py "$CAIRN_SCRIPTS_DIR/cairn-doctor.py"
  [ "$status" -eq 0 ]
  grep -qF "U+2298" <<<"$output"
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
  # Marking phase 2 complete moves the derived views with it: API-01's own
  # checkbox and every STATE plan/phase counter. Left stale they are a REAL
  # ledger disagreement that check 17 names and fails on, which would take
  # this test to exit 7 for a reason that has nothing to do with the bulk
  # close it exercises.
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/ROADMAP.md")
p.write_text(p.read_text().replace("- [ ] **Phase 2: API**",
                                   "- [x] **Phase 2: API**"))
r = Path(".planning/REQUIREMENTS.md")
r.write_text(r.read_text().replace("- [ ] **API-01**", "- [x] **API-01**"))
s = Path(".planning/STATE.md")
s.write_text(s.read_text()
             .replace("  completed_phases: 1", "  completed_phases: 2")
             .replace("  completed_plans: 1", "  completed_plans: 2")
             .replace("  percent: 50", "  percent: 100"))
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

# VOID-02 / criterion 2 of the phase's ROADMAP entry, end to end. This is THE
# proof of the phase: a repo whose roadmap lists nothing must not hand back a
# perfectly green board.
#
# Break: any one of the named checks going back to approving the void. Each is
# asserted by id, on the exact value — `!= "ok"` would be satisfied by `warn`,
# and that is how a false green nearly walked past a test written against
# false greens in phase 29.
@test "empty roadmap: the checks that compared nothing say so, and the footer says the report is incomplete" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  make_roadmap_without_phases

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # The verdict moved where it is READ, not where it decides to block.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.failed' 'false'
  assert_json_eq "$output" '.ok' 'false'

  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-issue") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-issue") | .scope' 'no-input'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .scope' 'no-input'

  # MEASURED CORRECTION to the plan: maps-fresh walks the phase DIRECTORIES on
  # disk and never reads ROADMAP.md, so an empty roadmap leaves it with its
  # input intact — it runs for real and reports what it FOUND (the two
  # generated maps went stale the moment the roadmap changed under them).
  # Asserting the exact `warn` is what proves the correction: a check that
  # still has something to compare must keep comparing, not get swept into
  # the promotion because a neighbouring check lost its input.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="maps-fresh") | .status' 'warn'

  # Each one says WHAT was missing, not just that it gave up.
  grep -qF "ROADMAP.md lists no phase" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "[cairn-doctor] INCOMPLETE" <<<"$output"
  refute_in_output "✓ req-issue"
  refute_in_output "✓ orphans"
}

# Break, and it is the expensive one: refusing check_orphans AS A WHOLE when
# the roadmap is empty. That is the tempting, naive version of the promotion,
# and it would hide every finding of the second axis — a phase that exists to
# remove false green would have created new silence instead.
@test "orphans with an empty roadmap: the axis that still works keeps reporting" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  make_roadmap_without_phases
  local loose
  loose="$(bd create "Loose end nobody placed" -t task --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # The exact value: warn, because there IS a finding — not not-applicable.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .status' 'warn'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .items | length' '1'
  grep -qF "$loose" <<<"$output"
  # And the information that the other axis never ran is NOT lost just
  # because there was something to warn about.
  grep -qF "ROADMAP.md lists no phase" <<<"$output"
}

# Break: promote the plan-inventory checks off the wrong axis. Before 23-03
# both of these read `ok` over an empty inventory — "0 plan bead id(s)
# verified" and "0 superseded plan(s), no live beads" are counts of nothing
# announced as a clean bill of health.
@test "plan-inventory checks: no PLAN.md at all is not-applicable/no-input on both axes" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  rm -f .planning/phases/*/*-PLAN.md

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="frontmatter-ids") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="frontmatter-ids") | .scope' 'no-input'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="superseded-released") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="superseded-released") | .scope' 'no-input'
}

# Break: read the `beads:` gap as vacuous truth. A plan with no stamp is
# EXACTLY the gap cairn exists to prevent, so "0 ids verified" over plans that
# are right there is the loudest possible no-input, not a pass.
@test "frontmatter-ids: plans present but none stamped is not-applicable/no-input" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  python3 - <<'PY'
import re
from pathlib import Path
for p in Path(".planning/phases").glob("*/*-PLAN.md"):
    p.write_text(re.sub(r"^beads: .*\n", "", p.read_text(), flags=re.MULTILINE))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="frontmatter-ids") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="frontmatter-ids") | .scope' 'no-input'
  grep -qF "carries a 'beads:'" <<<"$output"
  # Its sibling on the same axis DID sweep every plan and found no superseded
  # one — that is a real answer, and it must stay `ok`.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="superseded-released") | .status' 'ok'
}

# THE PERMANENCE TEST, and it is not decoration: it is what stops a future
# pass from promoting, by reflex, a check that phase 23 deliberately decided
# to leave alone. Each of these four counts zero in the healthy fixture and
# each of those zeroes is a real answer — the check swept its universe and
# found nothing wrong in it.
#
# Break: promote any of them. `lease-stale` with no lease registered has not
# "failed to check"; it looked for a stuck lease, there is none, and there is
# nothing the operator would want to do about that.
@test "phase 23 decided NOT to promote these four: they stay exactly ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-complete-open") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="label-pairs") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="external-ref") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="lease-stale") | .status' 'ok'
}

# Break: wire this promotion to the roadmap. maps-fresh walks
# `.planning/phases/` on disk and never reads ROADMAP.md, so emptying the
# phases tree is the only lever that silences it — a promotion hung off the
# roadmap would never fire here, and would fire in the test above where the
# check still has work to do.
#
# This is also the shape of a project on day one: a roadmap not yet written
# and no phase directories. It must not read as a clean bill of health.
@test "maps-fresh: no phase directory at all is not-applicable/no-input, not '0 maps current'" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  make_roadmap_without_phases
  rm -rf .planning/phases/*

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="maps-fresh") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="maps-fresh") | .scope' 'no-input'
  grep -qF "no phase directory" <<<"$output"
  # The report as a whole says it is incomplete, and still does not block.
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.failed' 'false'
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
  # The fixture adds a plan and a summary to phase 2, so STATE.md's plan
  # counters move with it. Left behind they are a REAL ledger disagreement
  # (check 17 names them), and this fixture is about phase-artifacts — a
  # second finding riding along would make the "exactly one warning" assertion
  # below fail for a reason that has nothing to do with what it tests.
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(p.read_text()
             .replace("  total_plans: 2", "  total_plans: 3")
             .replace("  completed_plans: 1", "  completed_plans: 2"))
PY
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
@test "release-versions: a repo without cairn's plugin manifests is out-of-scope, never a failure and never incomplete" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # Was `ok` with the words "not applicable" buried in the prose; 23-02 moved
  # them into the field. The exact value, never a negation.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .status' 'not-applicable'
  # Break, and it is the one that would hurt every user of cairn: marking this
  # `no-input`. The manifests will NEVER exist in a wired repo, so calling it
  # a gap would leave every user repo permanently INCOMPLETE — a false red
  # traded for a false green, which is the same defect mirrored.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .scope' 'out-of-scope'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .items | length' '0'
  assert_json_eq "$output" '.ok' 'true'
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
@test "test-parallel: a repo without cairn's plugin manifest is out-of-scope, and the report stays complete" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'not-applicable'
  # Same break as check 15's guard: `no-input` here would make every wired
  # repo read INCOMPLETE forever over a bats suite it does not have.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .scope' 'out-of-scope'
  assert_json_eq "$output" '.ok' 'true'
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

@test "test-parallel: no bats at all is not-applicable/no-input, a different sentence than 'it will be slow'" {
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
  # Break: keep the `warn` 29-06 left here with a comment saying this branch
  # belongs to phase 23. Nothing about parallelism was concluded, so `warn`
  # ("it will be slow") states a fact the check never established.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'not-applicable'
  # `no-input`, NOT `out-of-scope`: the manifest guard above already proved we
  # are inside cairn's own tree, where the suite exists and should be runnable.
  # A missing tool is a gap someone can close, so it DOES make the report
  # incomplete — while still never touching the exit code.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .scope' 'no-input'
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.failed' 'false'
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

#-----------------------------------------------------------------------------
# req-ledger (check 17, AUTO-07) — 29-07
#
# The chain nobody was validating: an active requirement has a coverage row,
# the row count is the number the footer claims, each phase's
# `**Requirements**:` line actually yields its ids, and a plan whose SUMMARY
# is on disk has its checkbox ticked.
#
# EVERY status assertion below is on the EXACT value (`fail`, `ok`, `warn`),
# never on "is not ok". The negation is satisfied by `warn`, and `warn` is
# precisely the wrong state this check can fall into by accident: the
# neighbouring defensive shell-out allowlists returncodes (0, 5), and
# cairn-bookkeep.py reconcile spends 3 on the very disagreement this check
# exists to report. Copied unchanged, the central case would land in the
# "tool unavailable" branch, return `warn`, and leave the doctor exiting 0 —
# a check against false green producing false green, passed by a test that
# could not tell.
#
# The ledger itself is never re-parsed here or in the doctor: cairn-bookkeep.py
# owns that reading, and these tests drive it through the CAIRN_BOOKKEEP seam
# the same way the release check is driven through CAIRN_RELEASE.
#-----------------------------------------------------------------------------

# Insert LINE immediately before the first line starting with MARKER.
# Appending to REQUIREMENTS.md instead lands the item under `## Traceability`,
# where it is not an active requirement at all and the fixture proves nothing.
req_insert_before() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
lines = p.read_text().splitlines()
i = next(j for j, l in enumerate(lines) if l.startswith(sys.argv[2]))
lines.insert(i, sys.argv[3])
p.write_text("\n".join(lines) + "\n")
PY
}

# Write `N requirements, M mapped.` as the coverage footer: a WHOLE line
# directly after the last table row. cairn-bookkeep.py locates the footer by
# POSITION, never by searching the file for its text.
add_coverage_footer() {
  python3 - "$1" "$2" <<'PY'
import re
import sys
from pathlib import Path
p = Path(".planning/REQUIREMENTS.md")
lines = p.read_text().splitlines()
last = max(i for i, l in enumerate(lines) if re.match(r"^\|\s*[A-Za-z]", l))
lines.insert(last + 1, f"{sys.argv[1]} requirements, {sys.argv[2]} mapped.")
p.write_text("\n".join(lines) + "\n")
PY
}

# Turn phase 1's readable `**Requirements**: [AUTH-01, AUTH-02]` into the
# ellipsis this repo's ROADMAP.md:400 actually carries.
elide_requirements_line() {
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/ROADMAP.md")
p.write_text(p.read_text().replace(
    "**Requirements**: [AUTH-01, AUTH-02]",
    "**Requirements**: AUTH-01 … AUTH-02"))
PY
}

# Give phase 2 a SUMMARY on disk while its plan checkbox still reads `- [ ]`.
# The GSD fixture writes plan items in the prose dialect (`- [ ] 02-01:
# title`); the derived-5 link reads the filename dialect this repo's own
# ROADMAP uses, the only one that names a file to look for on disk. The
# STATE counter is bumped along with it so the ONE finding under test is the
# checkbox, not a progress number riding on the same edit.
stale_plan_checkbox() {
  python3 - <<'PY'
from pathlib import Path
road = Path(".planning/ROADMAP.md")
road.write_text(road.read_text().replace(
    "- [ ] 02-01: Add rate limiting middleware",
    "- [ ] 02-01-PLAN.md — Add rate limiting middleware"))
state = Path(".planning/STATE.md")
state.write_text(state.read_text().replace(
    "  completed_plans: 1", "  completed_plans: 2"))
Path(".planning/phases/02-api/02-01-SUMMARY.md").write_text(
    "---\nphase: 02-api\nplan: '01'\nstatus: complete\n---\n\nDone.\n")
PY
}

# A stand-in for cairn-bookkeep.py that prints PAYLOAD and exits CODE — the
# only way to ask this check what it does with an exit code the real script
# does not produce today.
#
# The payload rides in a sibling file rather than being quoted into the stub's
# source: embedding JSON in Python in bash needs three levels of escaping to
# agree, and the first version of this helper got it wrong silently.
write_bookkeep_stub() {
  local path="$1" code="$2" payload="$3"
  printf '%s' "$payload" > "$path.payload"
  {
    printf 'import sys\n'
    printf 'sys.stdout.write(open("%s.payload").read())\n' "$path"
    printf 'sys.exit(%s)\n' "$code"
  } > "$path"
}

# Break: skip the first link. Red — AUTO-07's whole point is that an active
# requirement with no row went unnoticed for days.
@test "req-ledger: an active requirement with no coverage row fails and names the id" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  req_insert_before .planning/REQUIREMENTS.md "## Traceability" \
    "- [ ] **API-02**: Public API exposes a health endpoint"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  assert_json_eq "$output" '.ok' 'false'
  grep -qF "API-02" <<<"$output"
  grep -qF "no row in the coverage table" <<<"$output"
  # The finding routes to the command that resolves it.
  grep -qF "cairn-bookkeep.sh reconcile --apply" <<<"$output"
}

# Break: skip the second link — the one nobody thinks to write, because the
# footer "is only prose". It is the line that read 29 while the table held 33.
@test "req-ledger: a footer claiming another number fails and names both numbers" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  add_coverage_footer 9 9

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "9 requirements, 9 mapped." <<<"$output"
  grep -qF "it claims 9 active requirement(s) / 9 coverage row(s)" <<<"$output"
  grep -qF "the ledger holds 3 active requirement(s) / 3 coverage row(s)" \
    <<<"$output"
}

# Break: inherit the blind spot that has check 1 report `ok :: 29
# requirement(s) mapped` against 35 active requirements.
@test "req-ledger: an elided **Requirements**: line fails, naming the phase and the ids parsed" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  elide_requirements_line

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "Phase 1:" <<<"$output"
  grep -qF "ellipsis-between-ids" <<<"$output"
  grep -qF "does not yield the ids the ledger assigns it" <<<"$output"

  # The raw line and the ids the parser actually got, asserted on the HUMAN
  # report: json.dumps escapes the ellipsis to …, so a grep for it
  # against --json passes or fails for a reason that has nothing to do with
  # this check.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ req-ledger" <<<"$output"
  grep -qF "**Requirements**: AUTH-01 … AUTH-02" <<<"$output"
  grep -qF "parsed ['AUTH-01', 'AUTH-02']" <<<"$output"
}

# Break: leave the view 29-02 taught the bookkeeper to WRITE without a reader.
@test "req-ledger: a plan with its SUMMARY on disk and an unticked checkbox fails, naming the plan" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  stale_plan_checkbox

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "02-01-PLAN.md" <<<"$output"
  grep -qF "02-01-SUMMARY.md is on disk" <<<"$output"
}

# Break: a check that fails on everything would "catch" every test above and
# be worth nothing. This is the one that proves it can say yes.
@test "req-ledger: a coherent ledger reads ok and counts what it checked" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .items | length' '0'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .detail' \
    'every requirement-ledger link agrees — 3 active requirement(s) against 3 coverage row(s), 0 excluded by rule (deferred / out of scope)'
}

# Break: count a deferred requirement as a gap. The doctor fills with noise
# about requirements deliberately outside the table, and gets ignored.
@test "req-ledger: a deferred requirement outside the table is ok, and the count is explained" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  printf '\n## Deferred (v2)\n\n- **API-09**: Webhook fanout\n' \
    >> .planning/REQUIREMENTS.md

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'ok'
  grep -qF "1 excluded by rule (deferred / out of scope)" <<<"$output"
}

# Break: the wide `except` that returns ok, AND the `warn` verdict that
# satisfies "is not ok" while leaving the doctor at exit 0. Both are red here.
@test "req-ledger: cairn-bookkeep.py out of place is exactly fail, and the doctor exits 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run env CAIRN_BOOKKEEP="$BATS_TEST_TMPDIR/no-such-bookkeep.py" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "the requirement ledger could not be read" <<<"$output"
}

# Break: copy check 11's allowlist `(0, 5)` unchanged. Exit 3 — the ONLY
# verdict this check exists to report — would land in the unavailable branch
# and the doctor would exit 0 over a ledger it was just told disagrees.
@test "req-ledger: exit 3 with a valid report is a reading, not an unavailability (the (0, 3) allowlist)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-disagrees.py"
  write_bookkeep_stub "$stub" 3 '{"coverage": {"rows": 3}, "requirements": {"active": ["A-01", "A-02", "A-03"], "deferred": [], "out_of_scope": []}, "disagreements": [{"kind": "coverage-row-missing", "subject": "A-03", "found": null, "expected": "a coverage table row", "source": "REQUIREMENTS.md:9"}]}'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "A-03" <<<"$output"
  # The reading happened: the census is a parsed report, not an error string.
  grep -qF "3 active requirement(s) against 3 coverage row(s)" <<<"$output"
  refute_in_output "could not be read"
}

# Break: any defensive branch that returns `warn`. cairn-doctor.py's own
# exit-code table records that a warning never changes the exit code, so a
# warn here is a doctor approving a ledger nobody managed to read.
@test "req-ledger: an exit outside the allowlist is fail, never warn" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-boom.py"
  write_bookkeep_stub "$stub" 4 'boom'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "exited 4" <<<"$output"
}

# Break: return `fail` on unparsable output only when it is empty, or degrade
# to warn the way the checks around it legitimately do.
@test "req-ledger: an unparsable report is fail, and the doctor exits 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-garbage.py"
  write_bookkeep_stub "$stub" 0 'not json at all'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "invalid JSON" <<<"$output"
}

# Break: fail a repo that keeps no coverage view. Every user's roadmap without
# a coverage table would go to exit 7 over a table that has no business being
# there — the trap check 15 documents, one check over.
@test "req-ledger: a roadmap with no coverage view is out-of-scope, never a failure and never incomplete" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-no-view.py"
  write_bookkeep_stub "$stub" 3 '{"coverage": {"rows": 0}, "requirements": {"active": [], "deferred": [], "out_of_scope": []}, "disagreements": [{"kind": "coverage-view-missing", "subject": "coverage table", "found": null, "expected": "a coverage table", "source": "ROADMAP.md"}]}'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'not-applicable'
  # Break: calling this a gap. Keeping no coverage view is a METHOD choice a
  # project is entitled to make — the comment on REQ_LEDGER_VOID_KIND says so
  # — and marking it `no-input` would make every such repo read INCOMPLETE
  # forever over a table it deliberately does not keep.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .scope' 'out-of-scope'
  assert_json_eq "$output" '.ok' 'true'
  grep -qF "no coverage view" <<<"$output"
}

# Break: convert this guard and leave it unproved. It is the branch a repo
# that keeps no REQUIREMENTS.md at all lands on, and before 23-02 no test
# touched it — a promotion nobody proves is a promotion nobody notices
# regressing.
@test "req-ledger: a .planning/ with no REQUIREMENTS.md is out-of-scope, never a failure" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  rm .planning/REQUIREMENTS.md

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .scope' 'out-of-scope'
  # It still names WHAT is missing — the routing survives the promotion.
  grep -qF "REQUIREMENTS.md" <<<"$output"
}

# Break: silently drop a disagreement this check does not claim. An
# unexplained absence is the defect the phase removes; so is spending exit 7
# on `state-narrative-stale`, free text reconcile itself declines to rewrite.
@test "req-ledger: a disagreement outside its links is surfaced as warn, never exit 7 and never dropped" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-aside.py"
  write_bookkeep_stub "$stub" 3 '{"coverage": {"rows": 3}, "requirements": {"active": ["A-01", "A-02", "A-03"], "deferred": [], "out_of_scope": []}, "disagreements": [{"kind": "state-narrative-stale", "subject": "last_activity_desc", "found": "old prose", "expected": {"fase": 2}, "source": "STATE.md"}]}'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'warn'
  grep -qF "last_activity_desc" <<<"$output"
  grep -qF "outside req-ledger's own links" <<<"$output"
}

# Break: write the function and forget to add it to main()'s `checks` list —
# the quietest way for a new check not to exist, and the one no test that
# calls the function directly would ever catch.
@test "req-ledger: the check is registered and reported in --json" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.checks[].id] | index("req-ledger") != null' \
    'true'
}

#-----------------------------------------------------------------------------
# claims-stale with no input (check 8, AUTO-08's mechanical half) — 29-07
#
# The purest specimen of the defect this phase removes, measured 2026-08-04
# in cairn's own repo: `✓ claims-stale  skipped — no active_phase in
# STATE.md` — a check that had never run once in the project's life, wearing
# the success marker. The verdict changes; the DIALECT does not. Which key
# STATE.md should carry (`current_phase`, what GSD writes, or `active_phase`,
# what cairn reads) is a business rule open in CairnGo-rq0, and no test here
# takes a side.
#-----------------------------------------------------------------------------

# Remove the frontmatter key entirely — the state of every repo whose
# STATE.md was written by GSD.
drop_state_active_phase() {
  python3 - <<'PY'
import re
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(re.sub(r'^active_phase: ".*?"\n', "", p.read_text(),
                    flags=re.MULTILINE))
PY
}

# Break (three times over): keep the `ok` — the state of this check before
# 29-07 — or keep the `warn` 29-07 left as a placeholder for this phase, or
# promote a missing input to a blocking failure. This branch is the tracer
# slice: STATE.md IS here, so the key it lacks is a GAP, not a repo the check
# has no business running in — hence no-input, and hence `.ok` false.
@test "claims-stale: no active_phase is not-applicable/no-input, routes, and never blocks" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  drop_state_active_phase

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # A check with no input is friction, not a state inconsistency: exit 7
  # spent on friction stops meaning anything. The verdict moved where it is
  # READ, not where it decides to block.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.failed' 'false'
  # The health key can no longer be true while a check inside the doctor's
  # remit never received its input.
  assert_json_eq "$output" '.ok' 'false'
  # The exact value, never "is not ok": the old verdict WAS ok, then warn,
  # and a negation would also accept a fail that has no business being one.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .scope' 'no-input'
  grep -qF "cannot check" <<<"$output"
  grep -qF "active_phase" <<<"$output"
  grep -qF "CairnGo-rq0" <<<"$output"
  # The finding routes: it names the surfaces that read the key.
  grep -qF "cairn-lease.py" <<<"$output"
  grep -qF "hooks/session-start.sh" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⊘ claims-stale" <<<"$output"
  refute_in_output "✓ claims-stale"
  refute_in_output "⚠ claims-stale"
  # The footer says the report is incomplete without saying anything failed.
  grep -qF "[cairn-doctor] INCOMPLETE" <<<"$output"
  refute_in_output "[cairn-doctor] FAIL"
}

# Break: a branch that never returns ok makes the check lie in the other
# direction. This is the first proof in this project that it approves when it
# actually has something to compare.
@test "claims-stale: with active_phase present the check really runs and returns ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  # The fixture ships active_phase: "2"; DOC_P2 is the phase-2 issue, so an
  # in_progress claim on it is INSIDE the active phase and must not flag.
  bd update "$DOC_P2" --status in_progress --assignee tester >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .detail' \
    'no assigned in_progress issues outside phase 2'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .items | length' '0'
}

# Break: delete the check instead of fixing its verdict — the lazy way out,
# and the one the id list catches.
@test "claims-stale: no verdict change removes a check from the report" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  drop_state_active_phase

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks | length' '18'
  assert_json_eq "$output" '[.checks[].id] | index("claims-stale") != null' \
    'true'
}

# Break: take a side on the dialect. Writing `active_phase` into STATE.md (or
# teaching any cairn surface to read `current_phase`) resolves the symptom by
# deciding a business rule that belongs to grooming, and it silently changes
# what every repo with a STATE.md already on disk means.
@test "claims-stale: the doctor never writes active_phase and never reads current_phase" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  drop_state_active_phase
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/STATE.md")
lines = p.read_text().splitlines(keepends=True)
lines.insert(1, 'current_phase: "2"\n')   # the dialect GSD actually writes
p.write_text("".join(lines))
PY
  cp .planning/STATE.md "$BATS_TEST_TMPDIR/state-before.md"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # current_phase is NOT adopted as a synonym: the check still has no input.
  # The value moved with 23-01 (warn -> not-applicable); the abstention this
  # test protects did not, and the assertion is still on the exact value.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .scope' 'no-input'
  # And STATE.md is byte-identical — the doctor is read-only about this.
  run diff "$BATS_TEST_TMPDIR/state-before.md" .planning/STATE.md
  [ "$status" -eq 0 ]
}
