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
  write_mini_roadmap "$PWD"
  ROADMAP="$PWD/.planning/ROADMAP.md"
}

@test "close: read mode names the edit, exits 3, and writes nothing" {
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
  run bash "$BOOKKEEP" close 20 --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.planned | length' '0'
  assert_json_eq "$output" '.changed' 'false'
}

@test "close --json: the planned edit carries file, line, before, after and a reason" {
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
  run bash "$BOOKKEEP" close 77 --planning-dir "$PWD/.planning"
  [ "$status" -eq 4 ]
  echo "$output" | grep -qF "no checkbox line for phase 77"
}

@test "close: a phase number matching two lines is exit 2 naming both" {
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
  run bash "$BOOKKEEP" close 29 --planning-dir "$PWD/nope"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "planning dir not found"
  refute_in_output "Traceback"
}
