#!/usr/bin/env bats
# cairn-phase-model.bats — the shared phase model behind the status surfaces.
#
# Before this model the roadmap parser returned two lists of ints, so a phase
# could only ever render as a number and each surface had to invent anything
# richer for itself. These tests pin the two properties that matter: the model
# reads what a phase actually IS, and all three surfaces render it from that
# one read, so they cannot drift.
#
# Assertion style note (same as cairn-status.bats): a failing `[[ ]]` mid-test
# does NOT fail a bats test on this bash, so substring checks use grep -qF.

load 'helpers'

STATUS_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh"

assert_output_contains() {
  if ! printf '%s\n' "$output" | grep -qF -- "$1"; then
    echo "expected output to contain '$1', got:" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

# Read one field of one phase out of --json.
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

# A roadmap exercising every line shape the parser has to survive.
write_roadmap() {
  mkdir -p .planning
  cat > .planning/ROADMAP.md <<'EOF'
# Roadmap: Model Fixture

## Milestones

- ✅ **v1.0 Foundations** — Phases 1-2
- 🚧 **v1.1 Surface** — Phases 3-4

## Phases

- [x] Phase 1: Signup and login (2/2 plans) — completed 2026-07-01
- [x] **Phase 2: Rate limiting** - the API layer on top
- [ ] Phase 3: Phase model — read what a phase actually is (PANEL-01)
- [ ] Phase 4: Board fills the screen (PANEL-04, PANEL-05)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
| ----- | --------- | -------------- | ------ | --------- |
| 1. Signup and login | v1.0 | 2/2 | Complete | 2026-07-01 |
| 2. Rate limiting | v1.0 | 1/1 | Complete | 2026-07-02 |
| 3. Phase model | v1.1 | 0/? | Not started | — |
| 4. Board fills the screen | v1.1 | 0/? | Not started | — |
EOF
  cat > .planning/STATE.md <<'EOF'
---
milestone: v1.1
active_phase: 3
---

# Project State
EOF
}

setup() {
  require_bd
  make_tmp_repo
  write_roadmap
  bd init -q --prefix pm --non-interactive >/dev/null 2>&1
}

# ─── Reading what a phase is ─────────────────────────────────────────────────

@test "a phase carries its title, not just its number" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 1 title)" = "Signup and login" ]
}

@test "an em dash inside a title survives the completion-suffix strip" {
  # The trap: `— completed <date>` is a suffix carrying its own dash, and
  # titles have dashes of their own. Splitting on the dash truncates the title.
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 3 title)" = \
    "Phase model — read what a phase actually is" ]
}

@test "the bold roadmap shape yields the title, not the description after it" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 2 title)" = "Rate limiting" ]
}

@test "plan progress and the completion date are read off the roadmap line" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 1 plans_done)" = "2" ]
  [ "$(printf '%s' "$output" | phase_field 1 plans_total)" = "2" ]
  [ "$(printf '%s' "$output" | phase_field 1 completed_on)" = "2026-07-01" ]
}

@test "the progress table supplies the milestone and the plan counts" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 2 milestone)" = "v1.0" ]
  [ "$(printf '%s' "$output" | phase_field 2 plans_total)" = "1" ]
  [ "$(printf '%s' "$output" | phase_field 3 milestone)" = "v1.1" ]
}

@test "requirement ids are read, and not mistaken for plan progress" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 4 requirements)" = \
    '["PANEL-04", "PANEL-05"]' ]
}

# ─── State on disk ───────────────────────────────────────────────────────────

@test "disk state climbs none -> planned -> executed -> verified" {
  mkdir -p .planning/phases/03-phase-model
  run bash "$STATUS_SH" --json
  [ "$(printf '%s' "$output" | phase_field 3 disk_state)" = "none" ]

  touch .planning/phases/03-phase-model/03-01-PLAN.md
  run bash "$STATUS_SH" --json
  [ "$(printf '%s' "$output" | phase_field 3 disk_state)" = "planned" ]

  touch .planning/phases/03-phase-model/03-01-SUMMARY.md
  run bash "$STATUS_SH" --json
  [ "$(printf '%s' "$output" | phase_field 3 disk_state)" = "executed" ]

  touch .planning/phases/03-phase-model/03-VERIFICATION.md
  run bash "$STATUS_SH" --json
  [ "$(printf '%s' "$output" | phase_field 3 disk_state)" = "verified" ]
}

@test "the next command follows the state on disk, it is not authored" {
  mkdir -p .planning/phases/03-phase-model
  run bash "$STATUS_SH" --json
  [ "$(printf '%s' "$output" | phase_field 3 next_command)" = "/cairn:plan 3" ]

  touch .planning/phases/03-phase-model/03-01-PLAN.md
  run bash "$STATUS_SH" --json
  [ "$(printf '%s' "$output" | phase_field 3 next_command)" = "/cairn:work 3" ]

  touch .planning/phases/03-phase-model/03-01-SUMMARY.md
  run bash "$STATUS_SH" --json
  [ "$(printf '%s' "$output" | phase_field 3 next_command)" = "/cairn:verify 3" ]
}

@test "a completed phase whose dir was archived is never told to re-plan" {
  # Finishing a milestone moves its phase dirs out of .planning/phases/, so
  # phase 1 has no artifacts on disk at all. Reading disk state alone would
  # cheerfully suggest planning it again.
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 1 disk_state)" = "none" ]
  [ "$(printf '%s' "$output" | phase_field 1 next_command)" = "" ]
}

# ─── Dependencies ────────────────────────────────────────────────────────────

@test "phase dependencies are lifted from bd's own issue edges" {
  # This is the source that exists BEFORE anyone plans a phase — the milestone
  # registers the edges when it creates the issues. PLAN.md frontmatter only
  # appears at planning time, so relying on it alone would report every
  # unplanned phase as independent.
  A="$(bd create "PANEL-01 model" -t task -l phase-3,m-v1.1 --silent)"
  B="$(bd create "PANEL-05 board" -t task -l phase-4,m-v1.1 --silent)"
  bd dep add "$B" "$A" >/dev/null
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 4 depends_on)" = "[3]" ]
  [ "$(printf '%s' "$output" | phase_field 4 blocked_by)" = "[3]" ]
  # ...and the phase it waits on is itself unblocked.
  [ "$(printf '%s' "$output" | phase_field 3 blocked_by)" = "[]" ]
}

@test "a dependency on a completed phase does not count as blocking" {
  A="$(bd create "done work" -t task -l phase-1,m-v1.0 --silent)"
  B="$(bd create "new work" -t task -l phase-3,m-v1.1 --silent)"
  bd dep add "$B" "$A" >/dev/null
  bd close "$A" >/dev/null
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 3 depends_on)" = "[1]" ]
  [ "$(printf '%s' "$output" | phase_field 3 blocked_by)" = "[]" ]
}

@test "PLAN.md depends_on frontmatter is honoured alongside the bd edges" {
  mkdir -p .planning/phases/04-board
  cat > .planning/phases/04-board/04-01-PLAN.md <<'EOF'
---
phase: 04-board
depends_on: ["03-phase-model"]
---
EOF
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 4 depends_on)" = "[3]" ]
}

# ─── One model, three surfaces ───────────────────────────────────────────────

@test "the terminal board, --json and the HTML page report the same title" {
  # The whole point of the model. Each surface is rendered independently and
  # the phase title is compared across all three; any surface that re-derives
  # its own answer shows up here.
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  want="$(printf '%s' "$output" | phase_field 3 title)"
  [ -n "$want" ]

  run bash "$STATUS_SH" --width 100
  [ "$status" -eq 0 ]
  assert_output_contains "$want"

  run bash "$STATUS_SH" --html board.html
  [ "$status" -eq 0 ]
  grep -qF -- "$want" board.html
}

@test "the phase counts are derived from the model, not parsed twice" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
model = d["phases"]
assert d["phase"]["total"] == len(model), (d["phase"]["total"], len(model))
done = [p for p in model if p["complete"]]
assert d["phase"]["completed"] == len(done), (d["phase"]["completed"], len(done))
assert d["phase"]["title"] == [p for p in model if p["number"] == 3][0]["title"]
'
}

# ─── The pending list and the next commands (PANEL-02, PANEL-03) ─────────────

@test "pending phases are described, not listed as bare numbers" {
  run bash "$STATUS_SH" --width 100
  [ "$status" -eq 0 ]
  assert_output_contains "PENDING PHASES"
  assert_output_contains "Phase model — read what a phase actually is"
  assert_output_contains "Board fills the screen"
  assert_output_contains "not planned"
}

@test "completed phases stay out of the pending list" {
  run bash "$STATUS_SH" --width 100
  [ "$status" -eq 0 ]
  # Phases 1 and 2 are complete in the fixture roadmap.
  printf '%s\n' "$output" | sed -n '/PENDING PHASES/,/NEXT COMMANDS/p' \
    > "$BATS_TEST_TMPDIR/pending.txt"
  ! grep -qF "Signup and login" "$BATS_TEST_TMPDIR/pending.txt"
  ! grep -qF "Rate limiting" "$BATS_TEST_TMPDIR/pending.txt"
}

@test "a pending phase says what it waits on" {
  A="$(bd create "model" -t task -l phase-3,m-v1.1 --silent)"
  B="$(bd create "board" -t task -l phase-4,m-v1.1 --silent)"
  bd dep add "$B" "$A" >/dev/null
  run bash "$STATUS_SH" --width 100
  [ "$status" -eq 0 ]
  # The state-column append ("waits on 3") is gone with the table redesign
  # (D-01/D-02) — the blocked phase's row now carries phase 3 in its own
  # `waits` column, and the routing reason ("waits on phase 3") relocated to
  # the PURPOSE list beside that phase's purpose.
  assert_output_contains "waits on phase 3"
}

@test "the next command carries the reason it sits where it does" {
  A="$(bd create "model" -t task -l phase-3,m-v1.1 --silent)"
  B="$(bd create "board" -t task -l phase-4,m-v1.1 --silent)"
  bd dep add "$B" "$A" >/dev/null
  run bash "$STATUS_SH" --width 100
  [ "$status" -eq 0 ]
  # NEXT COMMANDS no longer exists as its own section (D-02) — the command
  # itself is the table's `next` column, and the reason lives in PURPOSE.
  assert_output_contains "/cairn:plan 3"
  assert_output_contains "phase 4 waits on it"
  assert_output_contains "waits on phase 3"
}

@test "order comes from the dependency graph, not the phase number" {
  # Phase 3 is blocked by an open issue in phase 4, so the LATER phase is the
  # one that can actually be run. Sorting by number would invert this and read
  # as an instruction to start with the blocked one.
  A="$(bd create "board first" -t task -l phase-4,m-v1.1 --silent)"
  B="$(bd create "model second" -t task -l phase-3,m-v1.1 --silent)"
  bd dep add "$B" "$A" >/dev/null
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
cmds = json.load(sys.stdin)["next_commands"]
assert cmds[0]["phase"] == 4, cmds
assert cmds[0]["blocked"] is False, cmds
assert cmds[1]["phase"] == 3 and cmds[1]["blocked"] is True, cmds
'
}

@test "the next command follows the phase forward as its artifacts appear" {
  mkdir -p .planning/phases/03-phase-model
  run bash "$STATUS_SH" --width 100
  assert_output_contains "/cairn:plan 3"

  touch .planning/phases/03-phase-model/03-01-PLAN.md
  run bash "$STATUS_SH" --width 100
  assert_output_contains "/cairn:work 3"

  touch .planning/phases/03-phase-model/03-01-SUMMARY.md
  run bash "$STATUS_SH" --width 100
  assert_output_contains "/cairn:verify 3"
}

@test "a milestone with nothing pending is told to ship, then close out" {
  python3 - <<'PY'
import pathlib, re
p = pathlib.Path(".planning/ROADMAP.md")
s = p.read_text()
s = s.replace("- [ ] Phase 3:", "- [x] Phase 3:").replace("- [ ] Phase 4:", "- [x] Phase 4:")
p.write_text(s)
PY
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
cmds = json.load(sys.stdin)["next_commands"]
assert [c["command"] for c in cmds] == ["/cairn:ship", "/cairn:milestone complete"], cmds
assert "v1.1" in cmds[1]["reason"], cmds
'

  # Terminal-side regression coverage (the specific bug this plan exists to
  # close): pending_phases() is empty here, so the old "guard on `pending`"
  # design silently dropped these two commands from the terminal while
  # --json and the HTML page still carried them. Guarding on
  # `pending or global_cmds` instead is what keeps them visible.
  run bash "$STATUS_SH" --width 100
  [ "$status" -eq 0 ]
  assert_output_contains "/cairn:ship"
  assert_output_contains "/cairn:milestone complete"
}

@test "the terminal panel and the HTML page carry the same commands and reasons" {
  A="$(bd create "model" -t task -l phase-3,m-v1.1 --silent)"
  B="$(bd create "board" -t task -l phase-4,m-v1.1 --silent)"
  bd dep add "$B" "$A" >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" > "$BATS_TEST_TMPDIR/j.json"

  run bash "$STATUS_SH" --width 100
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" > "$BATS_TEST_TMPDIR/term.txt"

  run bash "$STATUS_SH" --html board.html
  [ "$status" -eq 0 ]

  python3 - "$BATS_TEST_TMPDIR/j.json" "$BATS_TEST_TMPDIR/term.txt" board.html <<'PY'
import json, sys, pathlib
cmds = json.loads(pathlib.Path(sys.argv[1]).read_text())["next_commands"]
term = pathlib.Path(sys.argv[2]).read_text()
html = pathlib.Path(sys.argv[3]).read_text()
assert cmds, "no commands computed"
for c in cmds:
    for surface, text in (("terminal", term), ("html", html)):
        assert c["command"] in text, (surface, c["command"])
        assert c["reason"] in text, (surface, c["reason"])
PY
}

@test "--json exposes the computed commands for scripting" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert "next_commands" in d, sorted(d)
for c in d["next_commands"]:
    assert set(c) == {"command", "phase", "title", "reason", "blocked"}, c
'
}

# ─── Parallelism, said out loud (PANEL-04) ───────────────────────────────────

@test "two free phases are named as independent, with the split spelled out" {
  # An edge to an already-closed issue, so dependencies count as DECLARED
  # without blocking anything: phases 3 and 4 are then genuinely independent.
  DONE="$(bd create "old" -t task -l phase-1,m-v1.0 --silent)"
  X="$(bd create "model" -t task -l phase-3,m-v1.1 --silent)"
  bd dep add "$X" "$DONE" >/dev/null
  bd close "$DONE" >/dev/null
  bd create "board" -t task -l phase-4,m-v1.1 --silent >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
p = json.load(sys.stdin)["parallelism"]
assert p["runnable"] == [3, 4], p
assert p["declared"] is True, p
assert "independent" in p["note"], p
assert "same time" in p["note"], p
assert "recorded, not a verified ordering" not in p["note"], p
'
}

@test "a single free phase is reported as one, not dressed up as parallel" {
  X="$(bd create "model" -t task -l phase-3,m-v1.1 --silent)"
  Y="$(bd create "board" -t task -l phase-4,m-v1.1 --silent)"
  bd dep add "$Y" "$X" >/dev/null
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
p = json.load(sys.stdin)["parallelism"]
assert p["runnable"] == [3], p
assert p["blocked"] == [4], p
assert "One phase can move" in p["note"], p
assert "independent" not in p["note"], p
'
}

@test "an undeclared graph says so instead of calling everything independent" {
  # No dependency edge anywhere: every phase looks free, but that is a
  # statement about the records, not about the work.
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
p = json.load(sys.stdin)["parallelism"]
assert p["declared"] is False, p
assert "No dependencies are declared" in p["note"], p
assert "not a verified ordering" in p["note"], p
'
}

@test "the parallelism note reaches the terminal panel and the HTML page" {
  X="$(bd create "model" -t task -l phase-3,m-v1.1 --silent)"
  bd create "board" -t task -l phase-4,m-v1.1 --silent >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" > "$BATS_TEST_TMPDIR/j.json"

  run bash "$STATUS_SH" --html board.html
  [ "$status" -eq 0 ]

  # The terminal wraps the sentence, so compare on a distinctive fragment
  # rather than the whole line.
  run bash "$STATUS_SH" --width 100
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" > "$BATS_TEST_TMPDIR/term.txt"

  python3 - "$BATS_TEST_TMPDIR/j.json" "$BATS_TEST_TMPDIR/term.txt" board.html <<'PY'
import json, pathlib, sys, re
note = json.loads(pathlib.Path(sys.argv[1]).read_text())["parallelism"]["note"]
term = re.sub(r"\s+", " ", pathlib.Path(sys.argv[2]).read_text())
html = pathlib.Path(sys.argv[3]).read_text()
assert note, "no note computed"
assert note in html, ("html", note)
# The wrapped terminal keeps the words, so check the opening clause survives.
head = " ".join(note.split()[:6])
assert head in term, ("terminal", head)
PY
}

@test "--json exposes parallelism with a stable shape" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
p = json.load(sys.stdin)["parallelism"]
assert set(p) == {"runnable", "blocked", "declared", "note"}, sorted(p)
assert isinstance(p["runnable"], list) and isinstance(p["blocked"], list), p
assert isinstance(p["declared"], bool) and isinstance(p["note"], str), p
'
}
