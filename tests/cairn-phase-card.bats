#!/usr/bin/env bats
# cairn-phase-card.bats — Plan 14-01's data-layer additions to
# phase_model(): four additive per-phase --json keys the phase card (Plan
# 14-02) renders from — `purpose`, `research_done`, `issues_done`/
# `issues_total`, `verify_status`. This plan is data-layer only: every
# assertion here reads `--json`, never the terminal or HTML renderers
# (unchanged by this plan).
#
# Assertion style note (same as cairn-phase-model.bats and
# cairn-corroboration.bats): a failing `[[ ]]` mid-test does NOT fail a bats
# test on this bash, so substring checks use grep -qF; structural JSON
# assertions run as bare `python3 -c` pipelines (a raised AssertionError
# fails the bats test the same way `set -e` would).

load 'helpers'

STATUS_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh"

# Read one field of one phase out of --json (copied from
# tests/cairn-phase-model.bats — same helper, same contract).
phase_field() {
  python3 -c '
import json, sys
doc = json.load(sys.stdin)
n, key = int(sys.argv[1]), sys.argv[2]
for p in doc["phases"]:
    if p["number"] == n:
        v = p[key]
        print(json.dumps(v) if isinstance(v, (list, dict)) else ("" if v is None else v))
        sys.exit(0)
sys.exit("phase %d not in model" % n)
' "$1" "$2"
}

# A ROADMAP.md "## Detalhe das fases" section exercising every purpose-
# resolution shape (D-03): Phase 1 has both **Card:** (multi-line, like the
# real Phase 18 entry) and a distracting **Goal:** that must be ignored;
# Phase 2 has only a multi-sentence **Goal:**, whose SECOND sentence must
# never surface; Phase 3 has no detail block at all (its directory exists on
# disk, so it still appears in the model).
write_card_roadmap() {
  mkdir -p .planning .planning/phases/03-neither
  cat > .planning/ROADMAP.md <<'EOF'
# Roadmap: Card Fixture

## Detalhe das fases

### Phase 1: Card wins

**Card:** the card text spans two lines and must win over the goal below,
even though the goal sits right beside it.

**Goal:** the goal names DISTRACTINGWORD, which must never surface as the
purpose when a Card is present.

---

### Phase 2: Goal fallback only

**Goal:** the first sentence stands alone and must resolve as the purpose.
The second sentence carries SECONDSENTENCEMARKER and must never appear.

---
EOF
}

setup() {
  require_bd
  make_tmp_repo
  write_card_roadmap
  bd init -q --prefix pc --non-interactive >/dev/null 2>&1
}

# ─── purpose: Card / Goal-fallback / neither (D-03) ─────────────────────────

@test "a Card line wins verbatim over a distracting Goal in the same block" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  purpose="$(printf '%s' "$output" | phase_field 1 purpose)"
  [ "$purpose" = "the card text spans two lines and must win over the goal below, even though the goal sits right beside it." ]
  ! grep -qF "DISTRACTINGWORD" <<<"$purpose"
}

@test "a Goal-only block falls back to the first sentence, dropping the second" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  purpose="$(printf '%s' "$output" | phase_field 2 purpose)"
  [ "$purpose" = "the first sentence stands alone and must resolve as the purpose." ]
  ! grep -qF "SECONDSENTENCEMARKER" <<<"$purpose"
}

@test "a phase with neither Card nor Goal reads purpose as null, not a fabricated string" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
p = [x for x in d["phases"] if x["number"] == 3][0]
assert p["purpose"] is None, p["purpose"]
'
}

@test "every phases[] entry carries a purpose key, even phases with no detail block and no roadmap row" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for p in d["phases"]:
    assert "purpose" in p, p
'
}

# ─── research_done ────────────────────────────────────────────────────────

@test "research_done is true for a phase directory carrying an NN-RESEARCH.md file, false for one without" {
  mkdir -p .planning/phases/01-card
  touch .planning/phases/01-card/01-RESEARCH.md
  # Phase 3's directory (.planning/phases/03-neither, from write_card_roadmap)
  # already exists with no RESEARCH.md — the sibling "false" case, reused
  # rather than invented.

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 1 research_done)" = "True" ]
  [ "$(printf '%s' "$output" | phase_field 3 research_done)" = "False" ]
}

# ─── issues_done / issues_total: ANY-match, not bd_state()'s ALL-not-ANY ───

@test "issues_done/issues_total count phase-N issues by ANY match, including one that also carries an undone other phase's label" {
  bd create "phase 1 open work" -t task -l phase-1 --silent >/dev/null
  CLOSED="$(bd create "phase 1 closed work" -t task -l phase-1 --silent)"
  bd close "$CLOSED" >/dev/null
  # Cross-phase: carries phase-1 AND phase-2 (phase 2 is not roadmap-complete
  # here). bd_state()'s ALL-not-ANY corroboration filter would exclude this
  # issue from phase 1's evidence; phase_issue_counts() must NOT — it counts
  # by ANY match, and this is the proof.
  bd create "cross-phase follow-up" -t task -l phase-1,phase-2 --silent >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 1 issues_done)" = "1" ]
  [ "$(printf '%s' "$output" | phase_field 1 issues_total)" = "3" ]
  # ...and the cross-phase issue counts for phase 2 too — the ANY-match tally
  # is symmetric, not a one-sided exception carved out for phase 1.
  [ "$(printf '%s' "$output" | phase_field 2 issues_done)" = "0" ]
  [ "$(printf '%s' "$output" | phase_field 2 issues_total)" = "1" ]
}

# ─── verify_status ───────────────────────────────────────────────────────

@test "verify_status carries the literal status: value from NN-VERIFICATION.md, null when the file is absent" {
  make_gsd_fixture "$PWD"
  # Phase 1 (01-auth) ships 01-VERIFICATION.md with `status: passed`; phase 2
  # (02-api) has a PLAN but no VERIFICATION.md at all.

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 1 verify_status)" = "passed" ]
  [ "$(printf '%s' "$output" | phase_field 2 verify_status)" = "" ]
}

# ─── Cross-surface parity: terminal ≡ HTML (Plan 14-02, CARD-03) ───────────
#
# The terminal table and the HTML page must render `purpose`/research/
# issues/verify from the SAME phase_*_text() helpers — never re-derive their
# own wording. Proven by extracting the raw --json scalars and recomputing
# the expected display strings in THIS test, then grepping both rendered
# surfaces for them — never by calling the shared functions under test to
# build the expectation (that could only ever agree with itself).

write_parity_roadmap() {
  mkdir -p .planning .planning/phases/07-parity
  cat > .planning/ROADMAP.md <<'EOF'
# Roadmap: Parity Fixture

## Phases

- [ ] Phase 7: Parity check

## Detalhe das fases

### Phase 7: Parity check

**Card:** cross-surface fields must read identically from one model.

---
EOF
}

@test "purpose/research/issues/verify render identically across --json, the terminal panel and the HTML page" {
  write_parity_roadmap
  touch .planning/phases/07-parity/07-RESEARCH.md
  cat > .planning/phases/07-parity/07-VERIFICATION.md <<'EOF'
---
phase: 07-parity
verified: 2026-07-31T00:00:00Z
status: needs-revision
---

# Phase 7 Verification Report
EOF
  # bd is already initialized by setup() (prefix "pc") — no second bd init.
  bd create "parity open 1" -t task -l phase-7 --silent >/dev/null
  bd create "parity open 2" -t task -l phase-7 --silent >/dev/null
  CLOSED="$(bd create "parity closed" -t task -l phase-7 --silent)"
  bd close "$CLOSED" >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" > "$BATS_TEST_TMPDIR/j.json"

  # A wide render so nothing this test cares about is a truncation casualty
  # — the terminal table's own column-width budgeting is Task 1's concern,
  # not this test's.
  run bash "$STATUS_SH" --width 200
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" > "$BATS_TEST_TMPDIR/term.txt"

  run bash "$STATUS_SH" --html board.html
  [ "$status" -eq 0 ]

  python3 - "$BATS_TEST_TMPDIR/j.json" "$BATS_TEST_TMPDIR/term.txt" board.html <<'PY'
import json, sys, pathlib
doc = json.loads(pathlib.Path(sys.argv[1]).read_text())
term = pathlib.Path(sys.argv[2]).read_text()
html = pathlib.Path(sys.argv[3]).read_text()
p = [x for x in doc["phases"] if x["number"] == 7][0]

# Sanity on the fixture itself, so a broken fixture fails loudly here
# instead of the parity assertions below silently passing on garbage.
assert p["research_done"] is True, p
assert p["issues_done"] == 1 and p["issues_total"] == 3, p
assert p["verify_status"] == "needs-revision", p
assert p["purpose"], p

# Every expected string is built HERE, from the raw --json scalars, by
# literal string formatting — this script never imports cairn-status.py,
# so there is no way to call phase_research_text()/phase_issues_text()/
# phase_verify_text() even by accident. A bug inside one of those shared
# functions would make both surfaces agree on the same wrong value;
# recomputing independently is what actually catches that.
expected = {
    "purpose": p["purpose"],
    "research": "yes" if p["research_done"] else "—",
    "issues": f"{p['issues_done']}/{p['issues_total']}",
    "verify": p["verify_status"],
}
for label, text in expected.items():
    for surface, blob in (("terminal", term), ("html", html)):
        assert text in blob, (label, surface, text)
PY
  grep -qF 'class="phase-purpose"' board.html
}
