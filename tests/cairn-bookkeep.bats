#!/usr/bin/env bats
# cairn-bookkeep.bats — exercises the planning bookkeeper's CLI contract
# (cairn-bookkeep.py / the cairn-bookkeep.sh wrapper): the read-by-default /
# write-behind---apply seam, the line surgery that must not reflow anything,
# and the documented exit codes (0 ok, 2 usage/ambiguity, 3 read mode found
# something to change, 4 no such phase).
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so substring checks use grep -qF, negative checks go
# through refute_in_file / refute_in_output, and computed comparisons are a
# plain `[ ... ]` over a `run`-captured $status/$output.

load 'helpers'

BOOKKEEP="$CAIRN_SCRIPTS_DIR/cairn-bookkeep.sh"

# Assert NEEDLE does not appear in FILE. (`! grep` cannot be used inline:
# bash's `!` suppresses errexit, so its failure would never fail the test.)
refute_in_file() {
  if grep -qF -- "$1" "$2"; then
    echo "unexpectedly found '$1' in $2" >&2
    return 1
  fi
}

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# sha256 of FILE, computed through python3 so the digest format is identical
# on macOS (shasum) and Linux (sha256sum) hosts and identical to the one
# capture.sh writes into the fixture manifest.
file_sha256() {
  python3 -c \
    "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" \
    "$1"
}

# A minimal ROADMAP carrying two phase checkbox lines, one already complete.
# Deliberately NOT the drift fixture: this task's proof is about the surgery,
# and a small file makes "exactly one line changed" a readable claim.
write_mini_roadmap() {
  local dir="$1"
  mkdir -p "$dir/.planning"
  cat > "$dir/.planning/ROADMAP.md" <<'EOF'
# Roadmap: Mini

## Phases

- [x] Phase 20: Group model (BOARD-01) — completed 2026-08-03
- [ ] Phase 29: Nothing mechanical stays manual (AUTO-01 … AUTO-08) — **roda primeiro**

## Detalhe das fases

### Phase 29: Nothing mechanical stays manual

**Requirements**: AUTO-01 … AUTO-08
EOF
}

setup() {
  make_tmp_repo
  ROADMAP="$PWD/.planning/ROADMAP.md"
}

@test "close: read mode names the edit, exits 3, and writes nothing" {
  write_mini_roadmap "$PWD"
  local before after
  before="$(file_sha256 "$ROADMAP")"

  run bash "$BOOKKEEP" close 29 --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  echo "$output" | grep -qF "would write"
  echo "$output" | grep -qF "ROADMAP.md:6"
  echo "$output" | grep -qF "Nothing mechanical stays manual"

  after="$(file_sha256 "$ROADMAP")"
  [ "$before" = "$after" ]
  refute_in_file "- [x] Phase 29" "$ROADMAP"
}

@test "close --apply: flips the checkbox and changes exactly one line" {
  write_mini_roadmap "$PWD"
  cp "$ROADMAP" "$BATS_TEST_TMPDIR/roadmap.before"

  run bash "$BOOKKEEP" close 29 --apply --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  grep -qF -- "- [x] Phase 29: Nothing mechanical stays manual (AUTO-01 … AUTO-08) — **roda primeiro**" "$ROADMAP"

  # The whole D-01 claim in one number: the measured gsd-tools contrast is
  # +31/-4 to flip three checkboxes. One flip here must be one line out, one
  # line in — a reflow or a reserialization pass makes this count explode.
  run diff "$BATS_TEST_TMPDIR/roadmap.before" "$ROADMAP"
  [ "$status" -eq 1 ]
  local changed
  changed="$(grep -c '^[<>]' <<<"$output")"
  [ "$changed" -eq 2 ]
}

@test "close --apply preserves every other byte of the line and the file" {
  write_mini_roadmap "$PWD"
  cp "$ROADMAP" "$BATS_TEST_TMPDIR/roadmap.before"
  run bash "$BOOKKEEP" close 29 --apply --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # The ellipsis, the bold run and the em dash survive the edit verbatim, and
  # so does the OTHER phase line and the detail block.
  grep -qF "(AUTO-01 … AUTO-08) — **roda primeiro**" "$ROADMAP"
  grep -qF -- "- [x] Phase 20: Group model (BOARD-01) — completed 2026-08-03" "$ROADMAP"
  grep -qF "**Requirements**: AUTO-01 … AUTO-08" "$ROADMAP"

  # Same byte count in, same byte count out: '[ ]' -> '[x]' is one character
  # for one character.
  local n_before n_after
  n_before="$(wc -c < "$BATS_TEST_TMPDIR/roadmap.before")"
  n_after="$(wc -c < "$ROADMAP")"
  [ "$n_before" -eq "$n_after" ]
}

@test "close --apply twice: the second run reports changed:false and writes nothing" {
  write_mini_roadmap "$PWD"
  run bash "$BOOKKEEP" close 29 --apply --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  local after_first
  after_first="$(file_sha256 "$ROADMAP")"

  run bash "$BOOKKEEP" close 29 --apply --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.changed' 'false'
  assert_json_eq "$output" '.planned | length' '0'

  local after_second
  after_second="$(file_sha256 "$ROADMAP")"
  [ "$after_first" = "$after_second" ]
}

@test "close: an already-complete phase is exit 0 with an empty plan, not an edit" {
  write_mini_roadmap "$PWD"
  run bash "$BOOKKEEP" close 20 --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.planned | length' '0'
  assert_json_eq "$output" '.changed' 'false'
}

@test "close --json: the planned edit carries file, line, before, after and a reason" {
  write_mini_roadmap "$PWD"
  run bash "$BOOKKEEP" close 29 --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.planned | length' '1'
  assert_json_eq "$output" '.planned[0].line' '6'
  assert_json_eq "$output" '.applied' 'false'
  assert_json_eq "$output" '.planned[0].before | startswith("- [ ] Phase 29")' 'true'
  assert_json_eq "$output" '.planned[0].after | startswith("- [x] Phase 29")' 'true'
  # A write without a stated reason is the automated version of the same
  # problem this phase exists to remove.
  assert_json_eq "$output" '.planned[0].reason | length > 0' 'true'
}

@test "close: an unknown phase number is exit 4, never a silent no-op" {
  write_mini_roadmap "$PWD"
  run bash "$BOOKKEEP" close 77 --planning-dir "$PWD/.planning"
  [ "$status" -eq 4 ]
  echo "$output" | grep -qF "no checkbox line for phase 77"
}

@test "close: a phase number matching two lines is exit 2 naming both" {
  write_mini_roadmap "$PWD"
  cat >> "$PWD/.planning/ROADMAP.md" <<'EOF'

## Ordem de dependência

- [ ] Phase 29: duplicated by a careless hand
EOF
  local before
  before="$(file_sha256 "$ROADMAP")"

  run bash "$BOOKKEEP" close 29 --apply --planning-dir "$PWD/.planning"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "matches 2 checkbox lines"
  echo "$output" | grep -qF "duplicated by a careless hand"
  echo "$output" | grep -qF "roda primeiro"

  # Ambiguity refuses BEFORE writing: --apply was passed and nothing moved.
  local after
  after="$(file_sha256 "$ROADMAP")"
  [ "$before" = "$after" ]
}

@test "close: a missing planning dir is a usage error, not a traceback" {
  write_mini_roadmap "$PWD"
  run bash "$BOOKKEEP" close 29 --planning-dir "$PWD/nope"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "planning dir not found"
  refute_in_output "Traceback"
}

# ---------------------------------------------------------------------------
# The frozen fixture (tests/fixtures/bookkeep-drift/)
#
# Every expected number below is a LITERAL in this file, deliberately. The
# obvious alternative — reading them back out of MANIFEST.md — is a
# tautology: capture.sh writes the fixture AND the manifest in the same run,
# so a recapture taken after someone tidied .planning/ would move both
# together and these guards would stay green over an empty proof. A literal
# cannot be moved by capture.sh. It can only be moved by a hand, in a diff,
# on purpose.
#
# The numbers are constants because the fixture is frozen bytes: unlike
# .planning/, which moved three times while this phase was being planned
# (33 -> 34 -> 35 active requirements), a committed copy cannot age.
# ---------------------------------------------------------------------------

FIXTURE_DIR="$CAIRN_TESTS_DIR/fixtures/bookkeep-drift"

@test "fixture: the frozen files still hash to what the manifest recorded" {
  local name digest
  for name in ROADMAP REQUIREMENTS STATE; do
    digest="$(file_sha256 "$FIXTURE_DIR/$name.md")"
    # The manifest row is `| \`NAME.md\` | bytes | \`sha256\` |`.
    run grep -F "$digest" "$FIXTURE_DIR/MANIFEST.md"
    [ "$status" -eq 0 ]
    echo "$output" | grep -qF "$name.md"
  done
}

@test "fixture: the frozen ROADMAP still carries the disease it was frozen for" {
  # 1. the footer's own wrong claim, verbatim.
  grep -qF "29 requisitos, 29 mapeados." "$FIXTURE_DIR/ROADMAP.md"

  # 2. thirty-three coverage rows — not the 29 the footer claims, and not
  #    the 35 requirements that actually exist.
  local rows
  rows="$(grep -cE '^\| [A-Z]+-[0-9]+ \| Phase [0-9]+ \|' \
    "$FIXTURE_DIR/ROADMAP.md")"
  [ "$rows" -eq 33 ]

  # 3. AUTO-05 and AUTO-06 have no row at all.
  refute_in_file "| AUTO-05 |" "$FIXTURE_DIR/ROADMAP.md"
  refute_in_file "| AUTO-06 |" "$FIXTURE_DIR/ROADMAP.md"

  # 4. the ellipsis that blinded two tools, still unreadable.
  grep -qF "**Requirements**: AUTO-01 … AUTO-08" "$FIXTURE_DIR/ROADMAP.md"

  # 5. phase 20 is checked off while its three plans are not.
  grep -qF -- "- [x] Phase 20: Group model (BOARD-01)" "$FIXTURE_DIR/ROADMAP.md"
  grep -qF -- "- [ ] 20-01-PLAN.md" "$FIXTURE_DIR/ROADMAP.md"
}

@test "fixture: the frozen REQUIREMENTS still carries 35 unchecked active ids" {
  local active checked
  active="$(grep -cE '^- \[[ x]\] \*\*[A-Z]+-[0-9]+\*\*' \
    "$FIXTURE_DIR/REQUIREMENTS.md")"
  # Exactly 35, and every checkbox item in the file is an active one: the
  # deferred entry below carries NO checkbox, which is the corroboration the
  # section boundary gets for free.
  [ "$active" -eq 35 ]

  checked="$(grep -cE '^- \[x\] \*\*[A-Z]+-[0-9]+\*\*' \
    "$FIXTURE_DIR/REQUIREMENTS.md" || true)"
  [ "$checked" -eq 0 ]

  # BOARD-01 unchecked here while the coverage table calls it Complete: the
  # requirement checkbox and the table disagree, and the phase that carries
  # it is already closed.
  grep -qF -- "- [ ] **BOARD-01**" "$FIXTURE_DIR/REQUIREMENTS.md"
  grep -qF "| BOARD-01 | Phase 20 | Complete |" "$FIXTURE_DIR/ROADMAP.md"

  # CORR-09 is deferred, which is an explained absence, not drift — and it
  # is written WITHOUT a checkbox, unlike every active id above it.
  grep -qF "## Deferred (v2)" "$FIXTURE_DIR/REQUIREMENTS.md"
  grep -qF -- "- **CORR-09**" "$FIXTURE_DIR/REQUIREMENTS.md"
  refute_in_file "- [ ] **CORR-09**" "$FIXTURE_DIR/REQUIREMENTS.md"
}

@test "fixture: the frozen STATE still counts 3 plans against a 10-plan tree" {
  grep -qF "  total_plans: 3" "$FIXTURE_DIR/STATE.md"
  grep -qF "  completed_plans: 3" "$FIXTURE_DIR/STATE.md"
  grep -qF "  total_phases: 10" "$FIXTURE_DIR/STATE.md"
  grep -qF "last_activity_desc: Milestone v1.5 Legible State aberto (9 fases, 24 requisitos)" \
    "$FIXTURE_DIR/STATE.md"

  # The prose body still contradicts the frontmatter — the measured source of
  # the `current_phase: 29 -> 18` corruption. reconcile must never read it.
  grep -qF "current_phase: 29" "$FIXTURE_DIR/STATE.md"
  grep -qF "Phase: 18" "$FIXTURE_DIR/STATE.md"

  # phases.tsv is the tree those counters disagree with: 3+7 = 10 plans.
  grep -qF "20-group-model	3	3	1" "$FIXTURE_DIR/phases.tsv"
  grep -qF "29-nothing-mechanical-stays-manual	7	0	0" "$FIXTURE_DIR/phases.tsv"
}

@test "make_drift_fixture: rebuilds the tree by name and commits a baseline" {
  make_drift_fixture "$PWD"

  local plans summaries
  plans="$(find "$PWD/.planning/phases" -name '*-PLAN.md' | wc -l | tr -d ' ')"
  summaries="$(find "$PWD/.planning/phases" -name '*-SUMMARY.md' | wc -l | tr -d ' ')"
  [ "$plans" -eq 10 ]
  [ "$summaries" -eq 3 ]
  [ -f "$PWD/.planning/phases/20-group-model/20-03-SUMMARY.md" ]
  [ -f "$PWD/.planning/phases/20-group-model/20-VERIFICATION.md" ]
  [ -f "$PWD/.planning/phases/29-nothing-mechanical-stays-manual/29-07-PLAN.md" ]
  [ ! -f "$PWD/.planning/phases/29-nothing-mechanical-stays-manual/29-01-SUMMARY.md" ]

  # The .md files are byte copies, not reconstructions.
  local a b
  a="$(file_sha256 "$FIXTURE_DIR/ROADMAP.md")"
  b="$(file_sha256 "$PWD/.planning/ROADMAP.md")"
  [ "$a" = "$b" ]

  # The baseline commit is the denominator of every "only the planned lines
  # moved" diff. Without it `git diff` has nothing to compare against and
  # would approve a full-file reflow.
  run git -C "$PWD" rev-parse HEAD
  [ "$status" -eq 0 ]
  run git -C "$PWD" status --porcelain
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  # And it is a real denominator: a one-line edit shows up as exactly one.
  run bash "$BOOKKEEP" close 29 --apply --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  run git -C "$PWD" diff --numstat -- .planning/ROADMAP.md
  [ "$status" -eq 0 ]
  [ "$output" = "1	1	.planning/ROADMAP.md" ]
}
