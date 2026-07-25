#!/usr/bin/env bats
# cairn-gate.bats — exercises the ship gate's CLI contract (cairn-gate.py /
# the cairn-gate.sh wrapper) and the git pre-push shim cairn-init.sh installs:
#   0 all clear / not applicable, 5 bd unavailable (never blocks a push),
#   6 gate failed (offending issue ids listed, the only code that blocks).
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# Gate fixture on top of make_gsd_fixture (phase 1 complete, phase 2 open):
# two phase-1 issues (closed — phase 1 is DONE) and one open phase-2 issue,
# all carrying the m-v1.0 + phase-N pair labels and the gsd metadata stamp.
make_gate_fixture() {
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  GATE_A1="$(bd create "Signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  GATE_A2="$(bd create "Login flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v1.0"}}' --silent)"
  GATE_P2="$(bd create "Rate limiting" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-01","phase":2,"milestone":"v1.0"}}' --silent)"
  bd close "$GATE_A1" >/dev/null
  bd close "$GATE_A2" >/dev/null
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

@test "gate passes when every completed-phase issue is closed (open phase-2 ignored)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "ok — no open issues" <<<"$output"
  refute_in_output "$GATE_P2"
}

@test "reopened completed-phase issue fails the gate: exit 6, id listed" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  bd update "$GATE_A1" -s open >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 6 ]
  grep -qF "GATE FAILED" <<<"$output"
  # The offending id is the first token of its own line.
  grep -qE "^${GATE_A1}[[:space:]]" <<<"$output"
  # The open phase-2 issue is NOT offending — phase 2 isn't complete.
  refute_in_output "$GATE_P2"
}

@test "milestone scoping: other-milestone issues pass, unlabeled legacy strays fail" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  stamp_state_milestone

  # An open phase-1 issue from ANOTHER milestone must not trip the v1.0 gate.
  local other stray
  other="$(bd create "Future rework" -t task -l phase-1,m-v2.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v2.0"}}' --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  refute_in_output "$other"

  # An open phase-1 issue with NO m-* label is a legacy stray — it counts.
  stray="$(bd create "Legacy leftover" -t task -l phase-1 --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 6 ]
  grep -qE "^${stray}[[:space:]]" <<<"$output"
  refute_in_output "$other"
}

@test "--json prints a machine summary on pass and fail" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  stamp_state_milestone

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.applicable' 'true'
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.milestone' 'v1.0'
  assert_json_eq "$output" '.completed_phases[0]' '1'
  assert_json_eq "$output" '.offending | length' '0'

  bd update "$GATE_A2" -s open >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.offending | length' '1'
  assert_json_eq "$output" '.offending[0].id' "$GATE_A2"
  assert_json_eq "$output" '.offending[0].phase' '1'
}

@test "no .beads/ — gate not applicable, exit 0 with a note" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
}

@test "no .planning/ — gate not applicable, exit 0 with a note" {
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
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

  run env PATH="$stub" "$stub/bash" "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 5 ]
  grep -qF "warning" <<<"$output"
}

#-----------------------------------------------------------------------------
# pre-push shim (installed by cairn-init.sh)
#-----------------------------------------------------------------------------

# Write an executable stub gate that exits CODE, path in $GATE_STUB.
make_gate_stub() {
  GATE_STUB="$BATS_TEST_TMPDIR/gate-stub-$1.sh"
  printf '#!/usr/bin/env bash\necho "stub gate exit %s"\nexit %s\n' "$1" "$1" \
    > "$GATE_STUB"
  chmod +x "$GATE_STUB"
}

@test "cairn-init installs the pre-push shim idempotently" {
  require_bd
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  # A full `bd init` may set core.hooksPath (e.g. .beads/hooks) — the shim
  # follows the ACTIVE hooks dir, so resolve it the same way.
  local hooks_dir
  hooks_dir="$(git rev-parse --git-path hooks)"
  [ -x "$hooks_dir/pre-push" ]
  grep -qF "cairn pre-push gate" "$hooks_dir/pre-push"

  # Re-run: refreshed in place — our own shim is never chained aside to .old.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  [ -x "$hooks_dir/pre-push" ]
  grep -qF "cairn pre-push gate" "$hooks_dir/pre-push"
  if [ -f "$hooks_dir/pre-push.old" ]; then
    if grep -qF "cairn pre-push gate" "$hooks_dir/pre-push.old"; then
      echo "our own shim was wrongly chained aside to pre-push.old" >&2
      return 1
    fi
  fi
}

@test "shim chains a pre-existing foreign pre-push hook (runs it first)" {
  require_bd
  make_tmp_repo
  # bd init sets core.hooksPath (.beads/hooks) and installs bd's own hooks —
  # always resolve the ACTIVE hooks dir instead of assuming .git/hooks.
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  local hooks_dir
  hooks_dir="$(git rev-parse --git-path hooks)"
  mkdir -p "$hooks_dir"
  printf '#!/usr/bin/env bash\ntouch "%s/old-hook-ran"\nexit 0\n' "$PWD" \
    > "$hooks_dir/pre-push"
  chmod +x "$hooks_dir/pre-push"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  [ -x "$hooks_dir/pre-push.old" ]
  grep -qF "cairn pre-push gate" "$hooks_dir/pre-push"

  make_gate_stub 0
  run env CAIRN_GATE="$GATE_STUB" "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 0 ]
  [ -f old-hook-ran ]
}

@test "shim blocks only on gate exit 6; 5 and 0 let the push through" {
  require_bd
  make_tmp_repo
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  local hooks_dir
  hooks_dir="$(git rev-parse --git-path hooks)"
  # Isolate the shim's exit-code contract from whatever hook got chained
  # aside (test 'shim chains...' covers the chain path).
  rm -f "$hooks_dir/pre-push.old"

  make_gate_stub 6
  run env CAIRN_GATE="$GATE_STUB" "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 6 ]
  grep -qF "PUSH BLOCKED" <<<"$output"

  make_gate_stub 5
  run env CAIRN_GATE="$GATE_STUB" "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 0 ]
  grep -qF "bd unavailable" <<<"$output"

  make_gate_stub 0
  run env CAIRN_GATE="$GATE_STUB" "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 0 ]
}

@test "end to end: git push blocked while a completed-phase issue is open, allowed after close" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]

  local remote="$BATS_TEST_TMPDIR/remote.git"
  git init -q --bare "$remote"
  git remote add origin "$remote"
  git add -A >/dev/null
  git commit -qm "fixture"

  bd update "$GATE_A1" -s open >/dev/null
  run git push origin HEAD
  [ "$status" -ne 0 ]
  grep -qF "PUSH BLOCKED" <<<"$output"

  bd close "$GATE_A1" >/dev/null
  run git push origin HEAD
  [ "$status" -eq 0 ]
}
