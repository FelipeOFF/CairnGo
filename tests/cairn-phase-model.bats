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
