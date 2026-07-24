#!/usr/bin/env bats
# smoke.bats — proves the test harness itself works: fixture builders produce
# valid state, and the require_bd skip path behaves. No cairn script is under
# test here.

load 'helpers'

@test "make_tmp_repo creates a git repo and cds into it" {
  make_tmp_repo
  [ -d .git ]
  [ "$(git rev-parse --is-inside-work-tree)" = "true" ]
}

@test "gsd fixture writes the expected .planning tree" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  [ -f .planning/ROADMAP.md ]
  [ -f .planning/REQUIREMENTS.md ]
  [ -f .planning/STATE.md ]
  [ -f .planning/phases/01-auth/01-01-PLAN.md ]
  [ -f .planning/phases/01-auth/01-01-SUMMARY.md ]
  [ -f .planning/phases/01-auth/01-VERIFICATION.md ]
  [ -f .planning/phases/02-api/02-01-PLAN.md ]
  # phase 2 is mid-flight: PLAN but no SUMMARY
  [ ! -e .planning/phases/02-api/02-01-SUMMARY.md ]

  grep -q '^\*\*Depends on\*\*: Phase 1$' .planning/ROADMAP.md
  grep -q '^\*\*Requirements\*\*: \[AUTH-01, AUTH-02\]$' .planning/ROADMAP.md
  grep -q '| API-01 | Phase 2 | Pending |' .planning/REQUIREMENTS.md
}

@test "gsd fixture frontmatter is present and parseable" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  assert_frontmatter_key .planning/STATE.md gsd_state_version
  assert_frontmatter_key .planning/STATE.md active_phase
  assert_frontmatter_key .planning/STATE.md next_action
  assert_frontmatter_key .planning/STATE.md progress

  assert_frontmatter_key .planning/phases/01-auth/01-01-PLAN.md wave
  assert_frontmatter_key .planning/phases/01-auth/01-01-PLAN.md depends_on
  assert_frontmatter_key .planning/phases/01-auth/01-01-PLAN.md requirements
  assert_frontmatter_key .planning/phases/01-auth/01-01-PLAN.md status
  assert_frontmatter_key .planning/phases/02-api/02-01-PLAN.md requirements
  assert_frontmatter_key .planning/phases/01-auth/01-VERIFICATION.md status
  grep -q '^status: passed$' <(extract_frontmatter .planning/phases/01-auth/01-VERIFICATION.md)

  # Full YAML parse when PyYAML is available (structural checks above are the floor).
  if python3 -c 'import yaml' 2>/dev/null; then
    for f in .planning/STATE.md \
             .planning/phases/01-auth/01-01-PLAN.md \
             .planning/phases/01-auth/01-01-SUMMARY.md \
             .planning/phases/01-auth/01-VERIFICATION.md \
             .planning/phases/02-api/02-01-PLAN.md; do
      extract_frontmatter "$f" | python3 -c '
import sys, yaml
data = yaml.safe_load(sys.stdin)
assert isinstance(data, dict) and data, "frontmatter did not parse to a mapping"
'
    done
    extract_frontmatter .planning/phases/01-auth/01-01-PLAN.md | python3 -c '
import sys, yaml
data = yaml.safe_load(sys.stdin)
assert data["requirements"] == ["AUTH-01", "AUTH-02"], data["requirements"]
assert data["wave"] == 1
'
  fi
}

@test "bd fixture round-trips through bd list --json" {
  require_bd
  make_tmp_repo
  make_bd_fixture "$PWD" tst

  [ -n "$BD_EPIC" ] && [ -n "$BD_CHILD_OPEN" ] && [ -n "$BD_CHILD_CLOSED" ] && [ -n "$BD_STANDALONE" ]

  local all_json open_json
  all_json="$(bd list --json --all)"
  open_json="$(bd list --json)"

  assert_json_eq "$all_json" 'length' 4
  assert_json_eq "$open_json" 'length' 3
  assert_json_eq "$all_json" ".[] | select(.id == \"$BD_EPIC\") | .issue_type" epic
  assert_json_eq "$all_json" ".[] | select(.id == \"$BD_CHILD_CLOSED\") | .status" closed
  assert_json_eq "$all_json" ".[] | select(.id == \"$BD_STANDALONE\") | .labels | index(\"cairn-sync\") != null" true
}

@test "require_bd skips the test when bd is not on PATH" {
  # Inside a bats run, `command -v bats` resolves to the libexec entrypoint,
  # which cannot start under a clean environment — use the real wrapper.
  local bats_bin stub
  bats_bin="${BATS_ROOT:-}/bin/bats"
  [ -x "$bats_bin" ] || bats_bin="$(command -v bats)"
  stub="$BATS_TEST_TMPDIR/require-bd-stub.bats"
  cat > "$stub" <<EOF
load '$CAIRN_TESTS_DIR/helpers'

@test "needs bd" {
  require_bd
  false  # must never run when bd is absent
}
EOF
  # env -i drops the outer run's BATS_* variables (they confuse a nested
  # bats); /usr/bin:/bin carries bash and coreutils but never bd.
  run env -i PATH="/usr/bin:/bin" HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" "$bats_bin" --tap "$stub"
  [ "$status" -eq 0 ]
  [[ "$output" == *"# skip"* ]]
  [[ "$output" == *"bd is not on PATH"* ]]
}
