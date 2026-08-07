#!/usr/bin/env bats
# cairn-command-surfaces.bats — the /cairn:* PROMPTS as a contract.
#
# Every other suite here tests a script. These surfaces have no script: they
# are the files an agent reads before it speaks to the operator, and they age
# in a way nothing catches — a script can be right while the page that
# explains it is a year behind. Measured precedents in this repository, all of
# them the same shape:
#
#   1. docs/commands/doctor.md said "fifteen checks" with sixteen registered
#   2. cairn-doctor.py's docstring said "eighteen checks in total" with
#      nineteen, then "not one of the 17 checks" with nineteen
#   3. docs/commands/doctor.md:449 said "not one of the 18 checks" while line
#      371 of the SAME file said "nineteen" — two hand numbers disagreeing
#      inside one file
#   4. commands/help.md's map listed cairn's own commands by hand and had
#      already dropped /cairn:reconcile (CairnGo-q9l)
#   5. commands/doctor.md taught three status symbols after the script grew a
#      fourth (CairnGo-026)
#
# So the rule these tests enforce is not "the number is right", it is "no
# number is written by hand at all, and every list is derived or addressed".
#
# Assertion style: exact values, never a negation of a value; and a negative
# is `refute_*`, never `! grep` (bash's `!` suppresses errexit, so a failing
# `! grep` would not fail the test).

load 'helpers'

DOCTOR_PY="$CAIRN_SCRIPTS_DIR/cairn-doctor.py"
DOCTOR_PROMPT="$CAIRN_REPO_ROOT/cairn/commands/doctor.md"
# The single routing table the prompt addresses instead of copying.
# Overridable so the coverage assertion can be proved against a deliberately
# broken COPY of the table — the table itself belongs to another workstream in
# this phase and is never edited to run a test.
DOCTOR_ROUTING="${CAIRN_DOCTOR_ROUTING:-$CAIRN_REPO_ROOT/cairn/docs/commands/doctor.md}"

refute_in_file() {
  if grep -qF -- "$1" "$2"; then
    echo "unexpectedly found '$1' in $2" >&2
    return 1
  fi
}

# Every check id the doctor's --json actually reports, one per line.
#
# Derived from a RUN, never from a list written here: a list in the test is
# the same defect the tests below exist to catch, moved one file over. The
# fixture is minimal on purpose — a check with no input still reports itself
# (that is what the fourth status is for), so the id set is complete without
# a populated repo.
doctor_check_ids() {
  local dir="$1"
  python3 "$DOCTOR_PY" --project-dir "$dir" --json \
    | python3 -c 'import json,sys; print("\n".join(c["id"] for c in json.load(sys.stdin)["checks"]))'
}

make_doctor_id_fixture() {
  local dir="$BATS_TEST_TMPDIR/idfix"
  mkdir -p "$dir"
  git init -q "$dir"
  git -C "$dir" config user.email "cairn-tests@example.com"
  git -C "$dir" config user.name "Cairn Tests"
  make_gsd_fixture "$dir"
  ( cd "$dir" && bd init -q --prefix surf --non-interactive >/dev/null 2>&1 )
  printf '%s\n' "$dir"
}

# ---------------------------------------------------------------------------
# CairnGo-026 — the /cairn:doctor PROMPT and the fourth status
# ---------------------------------------------------------------------------

@test "the doctor prompt teaches all four statuses, not three" {
  # MEASURED 2026-08-07 against b9fdfb3: the prompt said
  # `one ✓/⚠/✗ line per check` — three symbols — while cairn-doctor.py:614
  # has carried four since phase 23:
  #   SYMBOL = {"ok": "✓", "not-applicable": "⊘", "warn": "⚠", "fail": "✗"}
  # The operator hears the verdict through this page, so a three-state
  # vocabulary puts the false green back into the conversation after the code
  # stopped printing it.
  local sym
  for sym in "✓" "⊘" "⚠" "✗"; do
    grep -qF -- "$sym" "$DOCTOR_PROMPT"
  done
  local word
  for word in "not-applicable" "no-input" "out-of-scope"; do
    grep -qF -- "$word" "$DOCTOR_PROMPT"
  done
}

@test "the doctor prompt knows the INCOMPLETE verdict and that it exits 0" {
  # cairn-doctor.py:3502-3508 ranks the verdict FAIL > INCOMPLETE > ok, and
  # :3512 exits 0 for INCOMPLETE on purpose: an absent input is friction, not
  # a state inconsistency. A page that only maps exit codes to verdicts would
  # report an incomplete run as clean.
  grep -qF "INCOMPLETE" "$DOCTOR_PROMPT"

  # And it must say how the verdict is DERIVED from --json, because the
  # payload carries no `verdict` key — measured: the top-level keys are
  # ok, failed, applicable, counts, note, active_phase, milestone.
  grep -qF '`failed`' "$DOCTOR_PROMPT"
  grep -qF '`ok`' "$DOCTOR_PROMPT"
}

@test "every check id the doctor reports has an entry in the routing table" {
  require_bd
  local dir; dir="$(make_doctor_id_fixture)"

  local ids; ids="$(doctor_check_ids "$dir")"
  [ -n "$ids" ]

  # The prompt names ONE routing table and every id must have an entry in it.
  # This is the assertion that makes addressing safe: a check added without
  # its remediation turns red here, at the file whose owner added the check.
  local id missing=""
  while IFS= read -r id; do
    [ -n "$id" ] || continue
    grep -qF -- "$id" "$DOCTOR_ROUTING" || missing="$missing $id"
  done <<<"$ids"

  if [ -n "$missing" ]; then
    echo "check id(s) with no entry in $DOCTOR_ROUTING:$missing" >&2
    return 1
  fi
}

@test "the doctor prompt addresses the routing table instead of copying it" {
  # MEASURED 2026-08-07: the prompt routed 9 of the 21 ids the --json
  # reports. Twelve had no treatment at all: bd-version, gsd-capability,
  # phase-corroboration, phase-artifacts, external-ref, lease-stale,
  # release-versions, test-parallel, req-ledger, response-language,
  # phase-landed, plan-counters.
  #
  # The fix is an address, not a second copy: docs/commands/doctor.md already
  # carries one entry per id and ships inside the plugin (verified at
  # ~/.claude/plugins/cache/cairngo/cairn/1.5.0/docs/commands/doctor.md).
  # Copying it here would create the two-hand-lists shape of precedents 1-4.
  grep -qF "docs/commands/doctor.md" "$DOCTOR_PROMPT"
}

@test "no cairn command prompt writes a check count by hand" {
  # The guard against the five measured precedents. The doctor grows checks
  # every other phase — it goes from 21 to 22 in this very phase — so any
  # count written into a prompt is a lie with a delay on it.
  local file hits
  for file in "$CAIRN_REPO_ROOT"/cairn/commands/*.md; do
    # PLURAL only, on purpose: "at least one check failed" is a sentence
    # about a run, not a count of the set. "nineteen checks", "the 21
    # checks", "18 checks in total" are the defect.
    hits="$(grep -niE '\<(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|twenty-one|twenty-two|[0-9]+)[ -]+(doctor )?checks\>' "$file" || true)"
    if [ -n "$hits" ]; then
      echo "a hand-written check count in $file:" >&2
      echo "$hits" >&2
      return 1
    fi
  done
}
