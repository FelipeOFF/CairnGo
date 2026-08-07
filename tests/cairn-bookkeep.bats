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
#
# Why the surgery tests pass --no-tracker: `close --apply` refuses to write
# without `bd`, on purpose (a run that edits three files and then cannot
# release the lease is the half-done state this phase removes). These
# fixtures have no bd database, and the claim they carry is about the LINE
# SURGERY. --no-tracker is the named way to ask for exactly that half. The
# tracker half has its own tests below, and they require_bd.

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

# Assert NEEDLE ($1) does not appear in HAYSTACK ($2), for strings that are
# not the captured $output.
refute_substring() {
  if grep -qF -- "$1" <<<"$2"; then
    echo "unexpectedly found '$1' in: $2" >&2
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

# Nanosecond mtime of FILE, through python3 for the same portability reason
# as file_sha256 (`stat -f %m` on macOS vs `stat -c %Y` on Linux).
file_mtime() {
  python3 -c \
    "import os,sys;print(os.stat(sys.argv[1]).st_mtime_ns)" "$1"
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

# Every date this command writes comes from CAIRN_NOW when it is set — the
# same determinism seam the other CAIRN_* variables are. Fixed here so the
# `— completed <date>` suffix and the two STATE timestamps are literals a
# test can assert instead of a moving target.
setup() {
  make_tmp_repo
  ROADMAP="$PWD/.planning/ROADMAP.md"
  export CAIRN_NOW="2026-08-04T09:00:00.000Z"
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

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
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
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # The ellipsis, the bold run and the em dash survive the edit verbatim, and
  # so does the OTHER phase line and the detail block.
  grep -qF "(AUTO-01 … AUTO-08) — **roda primeiro**" "$ROADMAP"
  grep -qF -- "- [x] Phase 20: Group model (BOARD-01) — completed 2026-08-03" "$ROADMAP"
  grep -qF "**Requirements**: AUTO-01 … AUTO-08" "$ROADMAP"

  # The byte count grows by EXACTLY the completion suffix and nothing else:
  # '[ ]' -> '[x]' is one character for one character, and ' — completed
  # 2026-08-04' is the only addition. (Plan 29-01 deliberately left the
  # suffix out and asserted equal byte counts; 29-02 writes it, so the
  # assertion becomes the suffix's own length rather than zero.)
  local n_before n_after suffix_bytes
  n_before="$(wc -c < "$BATS_TEST_TMPDIR/roadmap.before")"
  n_after="$(wc -c < "$ROADMAP")"
  suffix_bytes="$(printf ' — completed 2026-08-04' | wc -c | tr -d ' ')"
  [ "$n_after" -eq "$((n_before + suffix_bytes))" ]
  grep -qF -- "— **roda primeiro** — completed 2026-08-04" "$ROADMAP"
}

@test "close --apply: the completed suffix is written once, never twice" {
  write_mini_roadmap "$PWD"
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # A second run with a DIFFERENT CAIRN_NOW must still write nothing: the
  # suffix's presence is the idempotence test, never its date. A writer that
  # re-stamps the date would append a second suffix on every autonomous
  # cycle.
  local before
  before="$(file_sha256 "$ROADMAP")"
  CAIRN_NOW="2027-01-01" run bash "$BOOKKEEP" close 29 --apply --no-tracker --json \
    --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.changed' 'false'
  [ "$before" = "$(file_sha256 "$ROADMAP")" ]
  refute_in_file "completed 2027-01-01" "$ROADMAP"
}

@test "close: a malformed CAIRN_NOW is a usage error, not a garbage date" {
  write_mini_roadmap "$PWD"
  local before
  before="$(file_sha256 "$ROADMAP")"
  CAIRN_NOW="ontem" run bash "$BOOKKEEP" close 29 --apply --no-tracker \
    --planning-dir "$PWD/.planning"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "CAIRN_NOW must start with YYYY-MM-DD"
  [ "$before" = "$(file_sha256 "$ROADMAP")" ]
}

@test "close --apply twice: the second run reports changed:false and writes nothing" {
  write_mini_roadmap "$PWD"
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  local after_first
  after_first="$(file_sha256 "$ROADMAP")"

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --json --planning-dir "$PWD/.planning"
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

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
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

  # phases.tsv is the tree those counters disagree with: 3+7 = 10 plans. The
  # fifth column is has_phase_summary — phase 20 carries a 20-SUMMARY.md, and
  # it is not one of the 10.
  grep -qF "20-group-model	3	3	1	1" "$FIXTURE_DIR/phases.tsv"
  grep -qF "29-nothing-mechanical-stays-manual	7	0	0	0" \
    "$FIXTURE_DIR/phases.tsv"
}

@test "make_drift_fixture: rebuilds the tree by name and commits a baseline" {
  make_drift_fixture "$PWD"

  # Counted by SHAPE, because that is the whole distinction: `-SUMMARY.md`
  # alone matches a plan's summary AND the phase's, and conflating the two is
  # what let completed_plans exceed total_plans (CairnGo-6bx). The fixture now
  # carries one of each kind so a counter that cannot tell them apart has
  # somewhere to be caught.
  local plans plan_summaries phase_summaries
  plans="$(find "$PWD/.planning/phases" -name '*-PLAN.md' | wc -l | tr -d ' ')"
  plan_summaries="$(find "$PWD/.planning/phases" -type f \
    | grep -cE '/[0-9]+-[0-9]+-SUMMARY\.md$' | tr -d ' ')"
  phase_summaries="$(find "$PWD/.planning/phases" -type f \
    | grep -cE '/[0-9]+-SUMMARY\.md$' | tr -d ' ')"
  [ "$plans" -eq 10 ]
  [ "$plan_summaries" -eq 3 ]
  [ "$phase_summaries" -eq 1 ]
  [ -f "$PWD/.planning/phases/20-group-model/20-SUMMARY.md" ]
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

  # And it is a real denominator: the edits show up as an exact count, with
  # nothing else riding along. Seven lines in the ROADMAP — the phase
  # checkbox, two row status cells, the footer and three plan checkboxes.
  # The per-edit breakdown is asserted in "the six edits land"; what this
  # one proves is that the baseline commit makes numstat mean something.
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  run git -C "$PWD" diff --numstat -- .planning/ROADMAP.md
  [ "$status" -eq 0 ]
  [ "$output" = "7	7	.planning/ROADMAP.md" ]
}

# ---------------------------------------------------------------------------
# reconcile — reading the frozen drift and naming it
#
# Every expected number here is a literal, for the reason spelled out above
# the fixture guards: the fixture is frozen bytes, so these cannot age, and
# reading them back out of MANIFEST.md would be a tautology. They are also a
# second, independent count of the same files — capture.sh measured them with
# its own counters, and cairn-bookkeep measures them with a different parser.
# The two agreeing is the point; the two disagreeing would be a finding.
# ---------------------------------------------------------------------------

@test "reconcile: separates 35 active requirements from the deferred CORR-09" {
  make_drift_fixture "$PWD"

  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.requirements.active | length' '35'
  assert_json_eq "$output" '.requirements.deferred | join(",")' 'CORR-09'
  assert_json_eq "$output" '.requirements.out_of_scope | length' '0'

  # A naive counter puts CORR-09 among the active ones; the section boundary
  # is what keeps it out, and it is still reported rather than dropped.
  assert_json_eq "$output" \
    '.requirements.active | map(select(. == "CORR-09")) | length' '0'

  # The footer is NOT the source of the row count. A command that trusted it
  # would report footer_claim == rows and find nothing wrong.
  assert_json_eq "$output" '.coverage.rows' '33'
  assert_json_eq "$output" '.coverage.footer_claim' '29'
}

@test "reconcile: names all ten disagreements the fixture carries" {
  make_drift_fixture "$PWD"

  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]

  # A command that presumes consistency returns an empty list over a fixture
  # that provably disagrees with itself.
  assert_json_eq "$output" '.disagreements | length' '10'

  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "coverage-row-missing") | .subject] | sort | join(",")' \
    'AUTO-05,AUTO-06'
  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "requirement-checkbox-stale") | .subject] | join(",")' \
    'BOARD-01'
  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "footer-count-stale")] | length' '1'
  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "state-counter-stale") | .subject] | join(",")' \
    'progress.total_plans'
  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "plan-checkbox-stale") | .subject] | sort | join(",")' \
    '20-01-PLAN.md,20-02-PLAN.md,20-03-PLAN.md'
  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "state-narrative-stale") | .subject] | join(",")' \
    'last_activity_desc'

  # BOARD-01's checkbox is stale because phase 20 is closed — derived, never
  # copied from the coverage table's own "Complete".
  assert_json_eq "$output" \
    '.disagreements[] | select(.subject == "BOARD-01") | .expected' '[x]'

  # CORR-09 is an explained absence, so it is NOT a disagreement.
  assert_json_eq "$output" \
    '[.disagreements[] | select(.subject == "CORR-09")] | length' '0'
}

@test "reconcile: the ellipsis is NAMED, and never expanded into ids" {
  make_drift_fixture "$PWD"

  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]

  # Break 1 — a parser that silences the line: two ids and zero
  # disagreements, which is exactly today's measured behavior and exactly
  # what makes `req-issue` answer ok.
  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "requirements-line-unreadable") | .subject] | join(",")' \
    'Phase 29'
  assert_json_eq "$output" \
    '.disagreements[] | select(.kind == "requirements-line-unreadable") | .detail.ids_parsed | join(",")' \
    'AUTO-01,AUTO-08'
  assert_json_eq "$output" \
    '.disagreements[] | select(.kind == "requirements-line-unreadable") | .detail.raw' \
    '**Requirements**: AUTO-01 … AUTO-08'

  # Break 2 — a parser clever enough to expand the range: eight ids invented
  # out of suffix arithmetic, and it lies with more confidence than the first.
  assert_json_eq "$output" '.phases.detail["29"].requirements | length' '2'
  assert_json_eq "$output" \
    '.phases.detail["29"].requirements | join(",")' 'AUTO-01,AUTO-08'

  # `expected` stays null: what the line SHOULD say is genuinely unknown from
  # the ROADMAP alone. AUTO-05 and AUTO-06 are not even in the coverage
  # table, so no view of this file can reconstruct the missing ids.
  assert_json_eq "$output" \
    '.disagreements[] | select(.kind == "requirements-line-unreadable") | .expected' \
    'null'
}

@test "reconcile: computes the STATE counters from disk, never from the prose" {
  make_drift_fixture "$PWD"

  # The fixture's own prose body says this, and the frontmatter says 29.
  grep -qF "Phase: 18" "$PWD/.planning/STATE.md"

  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.state.computed.total_phases' '10'
  assert_json_eq "$output" '.state.computed.completed_phases' '1'
  assert_json_eq "$output" '.state.computed.percent' '10'
  # From the phase tree, not from the frontmatter that claims 3.
  assert_json_eq "$output" '.state.computed.total_plans' '10'
  assert_json_eq "$output" '.state.computed.completed_plans' '3'
  assert_json_eq "$output" '.state.frontmatter["progress.total_plans"]' '3'

  # The measured corruption is `state record-session` reading 18 out of the
  # prose. Nothing computed here may carry it.
  local computed
  computed="$(jq -c '.state.computed' <<<"$output")"
  refute_substring "18" "$computed"
}

@test "reconcile: a phase's own SUMMARY is not one of its plans" {
  # MEASURED 2026-08-06, right after the close of phase 22, and reconfirmed on
  # this repository 2026-08-07 (CairnGo-6bx, roadmap criterion 6):
  #
  #   .planning/STATE.md          on disk
  #   total_plans:     39         NN-MM-PLAN.md ...... 39
  #   completed_plans: 47   <---  NN-MM-SUMMARY.md ... 39
  #   percent:         91         NN-SUMMARY.md ....... 8      47 = 39 + 8
  #
  # scan_phase_tree() globbed `*-SUMMARY.md`, which matches the summary of a
  # PLAN (22-01-SUMMARY.md) AND the summary of the PHASE (22-SUMMARY.md). Its
  # pair, `*-PLAN.md`, matches only plans, because a phase has no NN-PLAN.md.
  # The two globs look symmetric and the naming is not, so completed_plans
  # counted past its own total.
  #
  # The aggravating half, and the reason this is a criterion rather than a
  # one-line fix: `reconcile` returned `disagreements: []` over that STATE.md
  # while printing both contradictory numbers in the same JSON object. Writer
  # and verifier compute it with the SAME wrong rule, so they agree.
  #
  # This is the exact shape the issue's acceptance asks for: two plans, two
  # plan summaries, one phase summary, and completed_plans == 2.
  make_drift_fixture "$PWD"
  rm -rf "$PWD/.planning/phases"
  mkdir -p "$PWD/.planning/phases/21-the-grouped-board"
  local d="$PWD/.planning/phases/21-the-grouped-board"
  : > "$d/21-01-PLAN.md"
  : > "$d/21-02-PLAN.md"
  : > "$d/21-01-SUMMARY.md"
  : > "$d/21-02-SUMMARY.md"
  : > "$d/21-SUMMARY.md"

  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  assert_json_eq "$output" '.state.computed.total_plans' '2'
  assert_json_eq "$output" '.state.computed.completed_plans' '2'
}

@test "reconcile: read mode does not write one byte" {
  make_drift_fixture "$PWD"

  local before_r before_q before_s mt_r mt_q mt_s
  before_r="$(file_sha256 "$PWD/.planning/ROADMAP.md")"
  before_q="$(file_sha256 "$PWD/.planning/REQUIREMENTS.md")"
  before_s="$(file_sha256 "$PWD/.planning/STATE.md")"
  # sha256 alone only catches a write that CHANGES bytes. A reconcile that
  # "takes the opportunity" and rewrites a file with identical content is
  # still a write, and it passed a sha-only check when I tried it. mtime is
  # what makes "does not write one byte" mean what it says.
  mt_r="$(file_mtime "$PWD/.planning/ROADMAP.md")"
  mt_q="$(file_mtime "$PWD/.planning/REQUIREMENTS.md")"
  mt_s="$(file_mtime "$PWD/.planning/STATE.md")"

  run bash "$BOOKKEEP" reconcile --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  echo "$output" | grep -qF "requirements-line-unreadable"
  echo "$output" | grep -qF "deferred (out of the table by rule"
  # The count itself belongs to the test above; this one is about the file
  # not moving, and coupling it to a number would make it go red for a
  # reason it does not name.
  echo "$output" | grep -qE "[0-9]+ disagreement\(s\)"

  [ "$before_r" = "$(file_sha256 "$PWD/.planning/ROADMAP.md")" ]
  [ "$before_q" = "$(file_sha256 "$PWD/.planning/REQUIREMENTS.md")" ]
  [ "$before_s" = "$(file_sha256 "$PWD/.planning/STATE.md")" ]
  [ "$mt_r" = "$(file_mtime "$PWD/.planning/ROADMAP.md")" ]
  [ "$mt_q" = "$(file_mtime "$PWD/.planning/REQUIREMENTS.md")" ]
  [ "$mt_s" = "$(file_mtime "$PWD/.planning/STATE.md")" ]

  # Nothing anywhere in the tree moved, not just those three files. The
  # baseline commit is what makes this assertion mean something.
  run git -C "$PWD" status --porcelain
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "reconcile --apply marks no phase complete — that is what close is for" {
  make_drift_fixture "$PWD"
  run bash "$BOOKKEEP" reconcile --apply --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # It resolved what it could (BOARD-01, the plan checkboxes, the footer,
  # the counters) …
  grep -qF -- "- [x] **BOARD-01**" "$PWD/.planning/REQUIREMENTS.md"
  grep -qF -- "- [x] 20-01-PLAN.md" "$PWD/.planning/ROADMAP.md"
  grep -qF "35 requisitos, 33 mapeados." "$PWD/.planning/ROADMAP.md"

  # … and marked NOTHING complete. Break: reusing close's edit 1 here, which
  # would let a drift repair silently close a phase nobody finished.
  refute_in_file "- [x] Phase 29" "$PWD/.planning/ROADMAP.md"
  refute_in_file "| AUTO-01 | Phase 29 | Complete |" "$PWD/.planning/ROADMAP.md"
  refute_in_file "- [x] **AUTO-01**" "$PWD/.planning/REQUIREMENTS.md"
}

@test "reconcile: a consistent tree is exit 0 with an empty list" {
  make_gsd_fixture "$PWD"
  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.disagreements | length' '0'
  assert_json_eq "$output" '.requirements.active | length' '3'
  assert_json_eq "$output" '.state.computed.percent' '50'
}

@test "reconcile: reads the coverage table from REQUIREMENTS when that is where it lives" {
  make_gsd_fixture "$PWD"
  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  # The GSD template puts the same three columns under `## Traceability` in
  # REQUIREMENTS.md. Reading only `## Cobertura` in the ROADMAP would report
  # one missing row per requirement over a table that is right there.
  assert_json_eq "$output" '.coverage.rows' '3'
  assert_json_eq "$output" '.coverage.source | endswith("REQUIREMENTS.md")' 'true'
  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "coverage-row-missing")] | length' '0'
}

@test "reconcile: no coverage table anywhere is ONE finding, not one per requirement" {
  make_gsd_fixture "$PWD"
  # Strip both homes of the table.
  python3 - "$PWD/.planning/REQUIREMENTS.md" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text().split("## Traceability")[0])
PY
  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.disagreements | length' '1'
  assert_json_eq "$output" '.disagreements[0].kind' 'coverage-view-missing'
  assert_json_eq "$output" '.coverage.source' 'null'
  # Three active requirements, and NOT three findings.
  assert_json_eq "$output" '.requirements.active | length' '3'
}

# ---------------------------------------------------------------------------
# The write path (plan 29-02) — the whole bookkeeping against the frozen
# drift, one edit at a time and never one line more.
#
# Same rule as above: every expected number is a LITERAL, because the fixture
# is committed bytes and cannot age. The line counts in particular are the
# contrast this milestone is measured by — `roadmap update-plan-progress 20`
# produces +31/-4 to flip three checkboxes, because _normalizeMd reserializes
# every .md the gsd-tools writes.
# ---------------------------------------------------------------------------

# The keys of STATE.md's frontmatter, in file order, as one line.
state_key_order() {
  python3 - "$1" <<'PY'
import re, sys
keys, started = [], False
for i, line in enumerate(open(sys.argv[1], encoding="utf-8")):
    line = line.rstrip("\n")
    if line.strip() == "---":
        if not started and i == 0:
            started = True
            continue
        if started:
            break
    if not started:
        continue
    m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
    if m:
        keys.append(("  " if m.group(1) else "") + m.group(2))
print(" ".join(keys))
PY
}

# Everything BELOW the frontmatter — the prose body this command never reads.
state_body_sha() {
  python3 - "$1" <<'PY'
import hashlib, sys
text = open(sys.argv[1], encoding="utf-8").read()
print(hashlib.sha256(text.split("\n---\n", 1)[1].encode()).hexdigest())
PY
}

@test "close --apply: the six edits land, and the diff is 16 lines for 16" {
  make_drift_fixture "$PWD"
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # 1. the phase, with the suffix phase 20 already carries.
  grep -qF -- "- [x] Phase 29: Nothing mechanical stays manual (AUTO-01 … AUTO-08) — **roda primeiro** — completed 2026-08-04" \
    "$PWD/.planning/ROADMAP.md"
  # 2. its requirements, plus BOARD-01 whose phase was already closed.
  grep -qF -- "- [x] **AUTO-01**" "$PWD/.planning/REQUIREMENTS.md"
  grep -qF -- "- [x] **AUTO-08**" "$PWD/.planning/REQUIREMENTS.md"
  grep -qF -- "- [x] **BOARD-01**" "$PWD/.planning/REQUIREMENTS.md"
  # AUTO-02 has no phase declaring it (the ellipsis), so nothing derives it.
  grep -qF -- "- [ ] **AUTO-02**" "$PWD/.planning/REQUIREMENTS.md"
  # 3. the two rows those requirements own.
  grep -qF "| AUTO-01 | Phase 29 | Complete |" "$PWD/.planning/ROADMAP.md"
  grep -qF "| AUTO-08 | Phase 29 | Complete |" "$PWD/.planning/ROADMAP.md"
  # 4. the footer: 35 active requirements, 33 of them mapped. A command that
  #    counted rows twice would write "33 requisitos" over a file holding 35.
  grep -qF "35 requisitos, 33 mapeados." "$PWD/.planning/ROADMAP.md"
  # 5. the plan checkboxes follow the SUMMARY files on disk — and only them.
  grep -qF -- "- [x] 20-01-PLAN.md" "$PWD/.planning/ROADMAP.md"
  grep -qF -- "- [x] 20-03-PLAN.md" "$PWD/.planning/ROADMAP.md"
  grep -qF -- "- [ ] 29-01-PLAN.md" "$PWD/.planning/ROADMAP.md"
  # 6. the counters, from the tree and the checkbox lines.
  grep -qF "  total_plans: 10" "$PWD/.planning/STATE.md"
  grep -qF "  completed_plans: 3" "$PWD/.planning/STATE.md"
  grep -qF "  completed_phases: 2" "$PWD/.planning/STATE.md"
  grep -qF "  percent: 20" "$PWD/.planning/STATE.md"
  grep -qF 'last_updated: "2026-08-04T09:00:00.000Z"' "$PWD/.planning/STATE.md"
  grep -qF "last_activity: 2026-08-04" "$PWD/.planning/STATE.md"
  # 7. AUTO-10: the key cairn READS, beside the key GSD writes. The sixteenth
  #    line of the diff below is this one, and it is the only INSERTION the
  #    STATE half has ever made.
  grep -qF "current_phase: 29" "$PWD/.planning/STATE.md"
  grep -qF "active_phase: 29" "$PWD/.planning/STATE.md"

  # The whole D-01 claim, in three numbers. Any reserialization, re-wrap or
  # whitespace pass makes these explode. STATE.md reads 6/5 and not 5/5
  # BECAUSE of the insertion above: five values replaced, one key created.
  run git -C "$PWD" diff --numstat
  [ "$status" -eq 0 ]
  echo "$output" | grep -qE '^3	3	\.planning/REQUIREMENTS\.md$'
  echo "$output" | grep -qE '^7	7	\.planning/ROADMAP\.md$'
  echo "$output" | grep -qE '^6	5	\.planning/STATE\.md$'
}

@test "close --apply: the prose quoting the footer comes out byte for byte" {
  make_drift_fixture "$PWD"
  # Measured 2026-08-04: `grep -n "requisitos, .*mapeados"` matches TWO lines
  # in this file. The second is success criterion 5 quoting the WRONG footer,
  # which is the measurement justifying this whole phase and the evidence
  # 29-07 reads. A text search rewrites it on the first pass.
  local quote
  quote='   `AUTO-05` e `AUTO-06`), e o rodapé afirmando **"29 requisitos, 29 mapeados"** —'
  grep -qxF -- "$quote" "$PWD/.planning/ROADMAP.md"

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  grep -qxF -- "$quote" "$PWD/.planning/ROADMAP.md"
  # And the real footer DID move — otherwise this test would pass over a
  # command that simply never touched the footer at all.
  grep -qF "35 requisitos, 33 mapeados." "$PWD/.planning/ROADMAP.md"
}

@test "close --apply: two footer lines in the section is exit 2 naming both" {
  make_drift_fixture "$PWD"
  # A second whole-line footer INSIDE the coverage section. "Take the first"
  # would silently pick one and edit it.
  python3 - "$PWD/.planning/ROADMAP.md" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text().replace(
    "29 requisitos, 29 mapeados.\n",
    "29 requisitos, 29 mapeados.\n\n30 requisitos, 30 mapeados.\n"))
PY
  local before
  before="$(file_sha256 "$PWD/.planning/ROADMAP.md")"

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "2 footer lines"
  echo "$output" | grep -qF "29 requisitos, 29 mapeados."
  echo "$output" | grep -qF "30 requisitos, 30 mapeados."
  [ "$before" = "$(file_sha256 "$PWD/.planning/ROADMAP.md")" ]
}

@test "close --apply twice: the second run writes nothing, by sha AND mtime" {
  make_drift_fixture "$PWD"
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  local n sha_r sha_q sha_s mt_r mt_q mt_s
  sha_r="$(file_sha256 "$PWD/.planning/ROADMAP.md")"
  sha_q="$(file_sha256 "$PWD/.planning/REQUIREMENTS.md")"
  sha_s="$(file_sha256 "$PWD/.planning/STATE.md")"
  mt_r="$(file_mtime "$PWD/.planning/ROADMAP.md")"
  mt_q="$(file_mtime "$PWD/.planning/REQUIREMENTS.md")"
  mt_s="$(file_mtime "$PWD/.planning/STATE.md")"

  # A LATER clock on the second run: the two STATE timestamps must not move
  # on their own. Running twice is the normal case in an autonomous loop, and
  # a timestamp written unconditionally makes every second pass a write.
  CAIRN_NOW="2026-09-09T09:09:09.000Z" run bash "$BOOKKEEP" close 29 --apply --no-tracker \
    --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.changed' 'false'
  assert_json_eq "$output" '.planned | length' '0'
  assert_json_eq "$output" '.files_written | length' '0'

  [ "$sha_r" = "$(file_sha256 "$PWD/.planning/ROADMAP.md")" ]
  [ "$sha_q" = "$(file_sha256 "$PWD/.planning/REQUIREMENTS.md")" ]
  [ "$sha_s" = "$(file_sha256 "$PWD/.planning/STATE.md")" ]
  [ "$mt_r" = "$(file_mtime "$PWD/.planning/ROADMAP.md")" ]
  [ "$mt_q" = "$(file_mtime "$PWD/.planning/REQUIREMENTS.md")" ]
  [ "$mt_s" = "$(file_mtime "$PWD/.planning/STATE.md")" ]
  refute_in_file "2026-09-09" "$PWD/.planning/STATE.md"
}

@test "close --apply: what stays is EXACTLY what the command refused to write" {
  make_drift_fixture "$PWD"
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  # Eight of the ten are gone. The four rows below are the SET that remains,
  # asserted as a set: "empty" would be a lie (the ellipsis is never expanded
  # and a person's sentence is never rewritten), and asserting only a count
  # would pass over a command that resolved the wrong ones.
  assert_json_eq "$output" \
    '[.disagreements[] | "\(.kind)/\(.subject)"] | sort | join(" ")' \
    'coverage-row-missing/AUTO-05 coverage-row-missing/AUTO-06 requirements-line-unreadable/Phase 29 state-narrative-stale/last_activity_desc'
}

@test "close --apply: a row is never invented for a requirement with no carrier" {
  make_drift_fixture "$PWD"
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # AUTO-05 and AUTO-06 are active, have no row, and appear on NO phase's
  # requirements line — phase 29's is the ellipsis. Every other AUTO-* row
  # says Phase 29, which is a PATTERN, not a source. Inferring from it is the
  # same move as expanding the ellipsis into eight ids.
  assert_json_eq "$output" \
    '[.unresolved[] | select(.kind == "coverage-row-missing") | .subject] | sort | join(",")' \
    'AUTO-05,AUTO-06'
  assert_json_eq "$output" \
    '.unresolved[] | select(.subject == "AUTO-05") | .detail.phases_with_an_unreadable_requirements_line | join(",")' \
    '29'
  refute_in_file "| AUTO-05 |" "$PWD/.planning/ROADMAP.md"
  refute_in_file "| AUTO-06 |" "$PWD/.planning/ROADMAP.md"
}

@test "close --apply: with the ids written out, the rows plan themselves" {
  make_drift_fixture "$PWD"
  # The one edit a person has to make — the ellipsis replaced by the ids.
  python3 - "$PWD/.planning/ROADMAP.md" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text().replace(
    "**Requirements**: AUTO-01 … AUTO-08",
    "**Requirements**: AUTO-01, AUTO-02, AUTO-03, AUTO-04, AUTO-05, "
    "AUTO-06, AUTO-07, AUTO-08"))
PY
  run bash "$BOOKKEEP" reconcile --apply --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.unresolved | length' '0'

  # Inserted at the END of Phase 29's group, in planning order, so the file's
  # existing grouping by phase survives. Break: appending both to the bottom
  # of the table, or inserting them reversed.
  run grep -n "| AUTO-0[4-8] | Phase 29 |" "$PWD/.planning/ROADMAP.md"
  [ "$status" -eq 0 ]
  local ids
  ids="$(sed 's/.*| \(AUTO-0[0-9]\) |.*/\1/' <<<"$output" | tr '\n' ' ')"
  [ "$ids" = "AUTO-04 AUTO-07 AUTO-08 AUTO-05 AUTO-06 " ]

  # 35 requirements, and now all 35 mapped.
  grep -qF "35 requisitos, 35 mapeados." "$PWD/.planning/ROADMAP.md"

  # Seven lines in, five out — the four edits this run made (two row status
  # cells stay untouched here, so: the footer, the three 20-* plan
  # checkboxes), the two inserted rows, and the requirements line the test
  # itself rewrote above. The insert did not drag the table's shape along.
  run git -C "$PWD" diff --numstat -- .planning/ROADMAP.md
  [ "$status" -eq 0 ]
  [ "$output" = "7	5	.planning/ROADMAP.md" ]
}

@test "close --apply: the frontmatter keeps its order and its body, and grows EXACTLY one key" {
  make_drift_fixture "$PWD"
  local order_before body_before
  order_before="$(state_key_order "$PWD/.planning/STATE.md")"
  body_before="$(state_body_sha "$PWD/.planning/STATE.md")"
  # The dialect this fixture speaks, and the one every GSD-written STATE.md
  # speaks: the key nothing in cairn reads, and not the key five surfaces do.
  grep -qF "current_phase: 29" "$PWD/.planning/STATE.md"
  refute_in_file "active_phase" "$PWD/.planning/STATE.md"

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # Break: a command that "takes the opportunity" to refresh the prose — or,
  # worse, that READS it. The measured corruption is `state record-session`
  # taking `Phase: 18` out of this body and writing it over current_phase.
  [ "$(state_body_sha "$PWD/.planning/STATE.md")" = "$body_before" ]
  grep -qF "Phase: 18" "$PWD/.planning/STATE.md"

  # AUTO-10, decided 2026-08-06: BOTH keys, same value, reading stays on
  # active_phase. Measured 2026-08-05: `grep -rn current_phase cairn/` finds
  # zero readers while five surfaces read active_phase.
  grep -qF "current_phase: 29" "$PWD/.planning/STATE.md"
  grep -qF "active_phase: 29" "$PWD/.planning/STATE.md"

  # Break, and this is the assertion the whole exception is fenced by: the
  # order is the OLD order with active_phase inserted immediately after its
  # anchor, and nothing else moved. A YAML round-trip (the measured failure
  # of `state complete-phase`) fails this; so does creating the key anywhere
  # else, and so does creating a second one.
  local order_after expected
  order_after="$(state_key_order "$PWD/.planning/STATE.md")"
  expected="${order_before/current_phase/current_phase active_phase}"
  [ "$order_after" = "$expected" ]
}

# The key is CREATED once and MAINTAINED forever after, and those are two
# different code paths — a distinction found by breaking, not by reading.
#
# MEASURED while proving this plan: removing `active_phase` from
# STATE_KEYS_WRITTEN left every other test in this file GREEN, because the
# creation branch asks `"active_phase" in wanted` and never consults the
# tuple. So the tuple governs only the UPDATE of a file that already carries
# the key — the state of every repository from its second close onward — and
# nothing asserted it. Without this test the phase would ship a key that is
# written once and then goes stale, which is a fresh instance of exactly the
# defect state-dialect exists to catch: it would start FAILING the doctor on
# the next phase.
@test "close --apply: an active_phase already in the file is updated, not duplicated" {
  make_drift_fixture "$PWD"
  python3 - "$PWD/.planning/STATE.md" <<'PY'
import re
import sys
from pathlib import Path
p = Path(sys.argv[1])
p.write_text(re.sub(r"^(current_phase: .*)$", r"\1\nactive_phase: 3",
                    p.read_text(), count=1, flags=re.MULTILINE))
PY
  grep -qF "active_phase: 3" "$PWD/.planning/STATE.md"

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  grep -qF "current_phase: 29" "$PWD/.planning/STATE.md"
  grep -qF "active_phase: 29" "$PWD/.planning/STATE.md"
  # Exactly one line, not a second one inserted beside the stale first.
  [ "$(grep -c '^active_phase:' "$PWD/.planning/STATE.md")" -eq 1 ]
}

# The other half of the exception, and the reason it is not "always create":
# the anchor. A STATE.md that speaks about no phase at all grows no key —
# the file has to already carry the dialect for the second word of it to be
# added beside the first.
#
# Break: drop the `"current_phase" in items` condition and this file grows an
# active_phase out of nothing, which is the invention the rest of this
# command exists to refuse.
@test "close --apply: no current_phase in the file means no active_phase either" {
  make_drift_fixture "$PWD"
  python3 - "$PWD/.planning/STATE.md" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
p.write_text(re.sub(r"^current_phase.*\n", "", p.read_text(),
                    flags=re.MULTILINE))
PY
  refute_in_file "current_phase" "$PWD/.planning/STATE.md"

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  refute_in_file "active_phase" "$PWD/.planning/STATE.md"
  # And it says so, rather than staying quiet about the key it did not write.
  run bash "$BOOKKEEP" close 29 --json --no-tracker --planning-dir "$PWD/.planning"
  assert_json_eq "$output" \
    '[.skipped[] | select(.why | test("active_phase"))] | length' '1'
}

@test "close --apply: the two free-text fields are untouched AND still named" {
  make_drift_fixture "$PWD"
  local desc stopped
  desc="$(grep '^last_activity_desc:' "$PWD/.planning/STATE.md")"
  stopped="$(grep '^stopped_at:' "$PWD/.planning/STATE.md")"

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # Break one way: a command that rewrites a person's sentence, which is what
  # `state record-session` gets wrong.
  [ "$(grep '^last_activity_desc:' "$PWD/.planning/STATE.md")" = "$desc" ]
  [ "$(grep '^stopped_at:' "$PWD/.planning/STATE.md")" = "$stopped" ]

  # Break the other way: silence. A number nobody recalculates and nobody
  # reports is exactly how the coverage footer reached 29.
  run bash "$BOOKKEEP" reconcile --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" \
    '[.disagreements[] | select(.kind == "state-narrative-stale") | .subject] | join(",")' \
    'last_activity_desc'
}

@test "close --apply: a view ahead of its authority is reported, never unmarked" {
  make_drift_fixture "$PWD"
  # A plan checked with no SUMMARY on disk, and a requirement checked while
  # the phase carrying it is still open.
  python3 - "$PWD/.planning/ROADMAP.md" "$PWD/.planning/REQUIREMENTS.md" <<'PY'
import pathlib, sys
r = pathlib.Path(sys.argv[1])
r.write_text(r.read_text().replace("- [ ] 29-07-PLAN.md", "- [x] 29-07-PLAN.md"))
q = pathlib.Path(sys.argv[2])
q.write_text(q.read_text().replace("- [ ] **BOARD-06**", "- [x] **BOARD-06**"))
PY
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  assert_json_eq "$output" \
    '[.unresolved[] | select(.kind == "plan-checkbox-ahead") | .subject] | join(",")' \
    '29-07-PLAN.md'
  assert_json_eq "$output" \
    '[.unresolved[] | select(.kind == "requirement-checkbox-ahead") | .subject] | join(",")' \
    'BOARD-06'
  assert_json_eq "$output" \
    '.unresolved[] | select(.subject == "BOARD-06") | .detail.open_phases | join(",")' \
    '21'

  # Still checked. Unmarking asserts an ABSENCE, and a bookkeeper that can
  # silently un-complete someone's work is worse than one that cannot finish.
  grep -qF -- "- [x] 29-07-PLAN.md" "$PWD/.planning/ROADMAP.md"
  grep -qF -- "- [x] **BOARD-06**" "$PWD/.planning/REQUIREMENTS.md"
}

@test "close: read mode over the full plan writes nothing and exits 3" {
  make_drift_fixture "$PWD"
  local sha mt
  sha="$(file_sha256 "$PWD/.planning/STATE.md")"
  mt="$(file_mtime "$PWD/.planning/STATE.md")"

  run bash "$BOOKKEEP" close 29 --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.applied' 'false'
  assert_json_eq "$output" '.changed' 'false'
  assert_json_eq "$output" '.planned | length > 10' 'true'

  [ "$sha" = "$(file_sha256 "$PWD/.planning/STATE.md")" ]
  [ "$mt" = "$(file_mtime "$PWD/.planning/STATE.md")" ]
  run git -C "$PWD" status --porcelain
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "close --apply: a roadmap-only tree writes the roadmap and NAMES the rest" {
  write_mini_roadmap "$PWD"
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.changed' 'true'
  # Break: a silent half-run. A missing file is a named skip, not a pass.
  assert_json_eq "$output" \
    '[.skipped[] | select(.what | contains("STATE"))] | length > 0' 'true'
  assert_json_eq "$output" \
    '[.skipped[] | select(.what | contains("requirement"))] | length > 0' 'true'
}

# ---------------------------------------------------------------------------
# The tracker half, the bd gate, and the two config keys (plan 29-02, task 2)
# ---------------------------------------------------------------------------

@test "close --apply: the map is regenerated and the lease released" {
  require_bd
  make_drift_fixture "$PWD"
  bd init -q --prefix bkp --non-interactive >/dev/null 2>&1
  run bash "$CAIRN_SCRIPTS_DIR/cairn-lease.sh" acquire 29 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$CAIRN_SCRIPTS_DIR/cairn-lease.sh" status 29 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'true'

  run bash "$BOOKKEEP" close 29 --apply --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.tracker.ran' 'true'
  assert_json_eq "$output" '.tracker.skipped' 'null'
  assert_json_eq "$output" '.tracker.map.ok' 'true'
  assert_json_eq "$output" '.tracker.lease.ok' 'true'

  # The lease is vacant and the generated map exists. Break: skipping the
  # shell-out leaves the lease held — the concrete damage a hand-closed
  # phase does, and the reason "one command" has to mean all of it.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-lease.sh" status 29 --json --project-dir "$PWD"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.held' 'false'
  [ -f "$PWD/.planning/phases/29-nothing-mechanical-stays-manual/29-BEADS-MAP.md" ]
}

@test "close --apply without bd: exit 5 BEFORE a single byte is written" {
  make_drift_fixture "$PWD"
  local stub="$BATS_TEST_TMPDIR/nobd-bin"
  mkdir -p "$stub"
  ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
  ln -s "$(command -v bash)" "$stub/bash"
  ln -s "$(command -v dirname)" "$stub/dirname"
  # The setup itself is asserted: a stub that still reached bd would make
  # this test pass for the wrong reason.
  run env PATH="$stub" "$stub/bash" -c 'command -v bd'
  [ "$status" -ne 0 ]

  local sha_r sha_q sha_s
  sha_r="$(file_sha256 "$PWD/.planning/ROADMAP.md")"
  sha_q="$(file_sha256 "$PWD/.planning/REQUIREMENTS.md")"
  sha_s="$(file_sha256 "$PWD/.planning/STATE.md")"

  run env PATH="$stub" "$stub/bash" "$BOOKKEEP" close 29 --apply \
    --planning-dir "$PWD/.planning"
  [ "$status" -eq 5 ]
  echo "$output" | grep -qF "bd is not on PATH"
  echo "$output" | grep -qF "half done"

  # Break: writing first and discovering afterwards.
  [ "$sha_r" = "$(file_sha256 "$PWD/.planning/ROADMAP.md")" ]
  [ "$sha_q" = "$(file_sha256 "$PWD/.planning/REQUIREMENTS.md")" ]
  [ "$sha_s" = "$(file_sha256 "$PWD/.planning/STATE.md")" ]
}

@test "close --apply --no-tracker without bd: exit 0, and it names what it skipped" {
  make_drift_fixture "$PWD"
  local stub="$BATS_TEST_TMPDIR/nobd-bin"
  mkdir -p "$stub"
  ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
  ln -s "$(command -v bash)" "$stub/bash"
  ln -s "$(command -v dirname)" "$stub/dirname"

  run env PATH="$stub" "$stub/bash" "$BOOKKEEP" close 29 --apply \
    --no-tracker --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.changed' 'true'
  assert_json_eq "$output" '.tracker.ran' 'false'
  # Break: a silent skip. Half the bookkeeping done quietly is the state
  # this phase exists to remove; done ON PURPOSE and SAID is a choice.
  assert_json_eq "$output" '.tracker.skipped | contains("--no-tracker")' 'true'
  assert_json_eq "$output" \
    '.tracker.skipped | contains("lease") and contains("map")' 'true'
  grep -qF -- "- [x] Phase 29" "$PWD/.planning/ROADMAP.md"
}

@test "close: read mode never touches the tracker, even with bd right there" {
  make_drift_fixture "$PWD"
  run bash "$BOOKKEEP" close 29 --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.tracker.ran' 'false'
  assert_json_eq "$output" '.tracker.skipped | contains("read mode")' 'true'
  [ ! -f "$PWD/.planning/phases/29-nothing-mechanical-stays-manual/29-BEADS-MAP.md" ]
}

@test "bookkeep.auto_commit: true commits exactly the planned files, false commits nothing" {
  make_drift_fixture "$PWD"
  local base
  base="$(git -C "$PWD" rev-list --count HEAD)"

  # false (the default): written, uncommitted, and the command printed.
  run bash "$BOOKKEEP" close 29 --apply --no-tracker --json \
    --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.commit.made' 'false'
  assert_json_eq "$output" '.commit.note | contains("git add")' 'true'
  [ "$(git -C "$PWD" rev-list --count HEAD)" = "$base" ]
  run git -C "$PWD" status --porcelain
  [ -n "$output" ]

  # Config flipped, and a DIFFERENT open phase so there is real work to do.
  # (Deliberately not `git checkout -- .planning` to rewind: a blanket
  # working-tree reset is the move that destroys uncommitted work, and a
  # test is not the place to teach it.)
  run bash "$CAIRN_SCRIPTS_DIR/cairn-config.sh" set bookkeep.auto_commit true \
    --project-dir "$PWD"
  [ "$status" -eq 0 ]
  git -C "$PWD" add -A && git -C "$PWD" commit -q -m "phase 29 by hand"
  base="$(git -C "$PWD" rev-list --count HEAD)"

  run bash "$BOOKKEEP" close 21 --apply --no-tracker --json \
    --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.commit.made' 'true'
  assert_json_eq "$output" '.commit.message' 'chore(cairn): bookkeeping fase 21'
  [ "$(git -C "$PWD" rev-list --count HEAD)" = "$((base + 1))" ]

  # EXACTLY the three files this run planned — never `git add -A` sweeping
  # up whatever else was in the tree.
  run git -C "$PWD" show --name-only --format= HEAD
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | sort | tr '\n' ' ')" = ".planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/STATE.md " ]
}

@test "bookkeep.auto_commit: an unrelated dirty file is never swept into the commit" {
  make_drift_fixture "$PWD"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-config.sh" set bookkeep.auto_commit true \
    --project-dir "$PWD"
  [ "$status" -eq 0 ]
  git -C "$PWD" add -A && git -C "$PWD" commit -q -m "config"
  echo "work in progress" > "$PWD/unrelated.txt"
  git -C "$PWD" add unrelated.txt

  run bash "$BOOKKEEP" close 29 --apply --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  run git -C "$PWD" show --name-only --format= HEAD
  refute_in_output "unrelated.txt"
  # Still staged, still uncommitted: it was not this command's to take.
  run git -C "$PWD" status --porcelain
  echo "$output" | grep -qF "unrelated.txt"
}

@test "ship.pr_scope decides pr_due, and it is not a constant" {
  make_drift_fixture "$PWD"
  run bash "$BOOKKEEP" close 29 --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  # Schema default is "phase": the PR comes due at the end of a phase.
  assert_json_eq "$output" '.pr_scope' 'phase'
  assert_json_eq "$output" '.pr_due' 'true'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-config.sh" set ship.pr_scope milestone \
    --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$BOOKKEEP" close 29 --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.pr_scope' 'milestone'
  assert_json_eq "$output" '.pr_due' 'false'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-config.sh" set ship.pr_scope none \
    --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$BOOKKEEP" close 29 --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.pr_due' 'false'

  # reconcile owns no phase, so it answers null rather than guessing.
  run bash "$BOOKKEEP" reconcile --apply --json --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.pr_due' 'null'
}

# ---------------------------------------------------------------------------
# The prose: no cairn command instructs a hand edit of the three files
# (plan 29-02, task 3)
#
# What these do NOT prove: that an agent obeys prose. What they prove is that
# the prose does not carry two contradictory instructions at once — which is
# the likely result of a careless edit, and the one an "it mentions the
# script" assertion would happily approve.
#
# The negative assertion is scoped to the STEP and searched one FILE NAME at a
# time, deliberately. Measured before this plan: the three names were split
# across two lines (`.planning/STATE.md`, `.planning/ROADMAP.md` and\n
# `.planning/REQUIREMENTS.md`), so any search for a whole phrase containing
# them matched ZERO occurrences and would have "passed" forever. A sweep that
# finds nothing because it looked wrong is the same false green this phase
# exists to remove, performed by the hand that came to remove it.
# ---------------------------------------------------------------------------

AUTONOMOUS_CMD="$CAIRN_REPO_ROOT/cairn/commands/autonomous.md"
BOOKKEEP_DOC="$CAIRN_REPO_ROOT/cairn/docs/commands/bookkeep.md"

# The completion-marks step only: from its numbered heading to the next one.
completion_step() {
  sed -n '/^3\. \*\*Apply the completion marks/,/^4\. \*\*/p' "$AUTONOMOUS_CMD"
}

@test "autonomous: the completion-marks step invokes the script" {
  # The interval is real before anything is claimed about it — a delimiter
  # that matched nothing would make every assertion below vacuous.
  local step
  step="$(completion_step)"
  [ -n "$step" ]
  [ "$(wc -l <<<"$step" | tr -d ' ')" -gt 5 ]

  grep -qF "cairn-bookkeep.sh" <<<"$step"
  grep -qE 'cairn-bookkeep\.sh" close <N> --apply' <<<"$step"
  # Exit 5 is the one exit code the operator has to act on here.
  grep -qF "Exit 5" <<<"$step"
}

@test "autonomous: no hand edit survives inside that step — one name at a time" {
  local step name hits
  step="$(completion_step)"
  for name in "STATE.md" "ROADMAP.md" "REQUIREMENTS.md"; do
    # Every line inside the step that names this file must be the invocation
    # itself. Break: leaving "update .planning/STATE.md …" next to the new
    # command — two instructions, one of them the defect.
    hits="$(grep -nF -- "$name" <<<"$step" | grep -vF "cairn-bookkeep.sh" || true)"
    if [ -n "$hits" ]; then
      echo "the completion-marks step still names $name outside the invocation:" >&2
      echo "$hits" >&2
      return 1
    fi
  done
}

@test "autonomous: the worktree prohibition is untouched, and lives outside the step" {
  # The script is not permission to write from inside a worktree; it is the
  # HOW of "centrally". Break: reading the new invocation as a relaxation.
  grep -qF -- "- **What it must not write.** \`.planning/STATE.md\`, \`.planning/ROADMAP.md\` and" \
    "$AUTONOMOUS_CMD"
  grep -qF -- "\`.planning/REQUIREMENTS.md\` are forbidden inside the worktree: do not create," \
    "$AUTONOMOUS_CMD"

  # And it is genuinely outside the interval the test above scopes to.
  refute_substring "must not write" "$(completion_step)"
}

@test "no cairn command instructs a hand edit of the three planning files" {
  # The whole sweep, by name, over both prompt trees. A line may READ or
  # FORBID; what it may not do is tell someone to update/edit/write one.
  local name hits
  for name in "STATE.md" "ROADMAP.md" "REQUIREMENTS.md"; do
    hits="$(grep -rniE "(update|edit|rewrite) [^.]*$name|$name[^.]*(by hand|manually)" \
      "$CAIRN_REPO_ROOT/cairn/commands" "$CAIRN_REPO_ROOT/cairn/skills" 2>/dev/null \
      | grep -vF "cairn-bookkeep" || true)"
    if [ -n "$hits" ]; then
      echo "a command still instructs a hand edit of $name:" >&2
      echo "$hits" >&2
      return 1
    fi
  done
}

@test "the command page documents the contract, the exit codes and the refusals" {
  [ -f "$BOOKKEEP_DOC" ]

  # Every exit code the script can return, so a reader never has to open the
  # .py to find out what one means.
  local code
  for code in "| 0 |" "| 2 |" "| 3 |" "| 4 |" "| 5 |"; do
    grep -qF -- "$code" "$BOOKKEEP_DOC"
  done

  # The derivation rule: one authority, five derived views. Without it in
  # writing, the next person repairs the wrong side.
  grep -qF "derived 1" "$BOOKKEEP_DOC"
  grep -qF "derived 5" "$BOOKKEEP_DOC"

  # Every STATE key it writes, named on the page and not only in the
  # docstring.
  local key
  for key in current_phase current_phase_name progress.total_phases \
             progress.completed_phases progress.total_plans \
             progress.completed_plans progress.percent last_updated \
             last_activity; do
    grep -qF "$key" "$BOOKKEEP_DOC"
  done

  # And the section that says what it does NOT do — the half a page like
  # this usually leaves out, and the half that keeps it from being read as a
  # gate.
  grep -qF "## What it does not do" "$BOOKKEEP_DOC"
  grep -qF "It is not a gate" "$BOOKKEEP_DOC"
  grep -qF "cairn-gate.sh" "$BOOKKEEP_DOC"
  grep -qF "never un-marks" "$BOOKKEEP_DOC"
  grep -qF "CairnGo-rq0" "$BOOKKEEP_DOC"
}

@test "help.md registers the command and points at its page" {
  local help="$CAIRN_REPO_ROOT/cairn/commands/help.md"
  grep -qF "cairn-bookkeep.sh close" "$help"
  grep -qF "docs/commands/bookkeep.md" "$help"
}
