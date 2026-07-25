#!/usr/bin/env bats
# cairn-migrate.bats — exercises the detect/plan/apply contract of
# cairn-migrate.py (and the cairn-migrate.sh wrapper) against real fixture
# repos and a real bd database:
#   - detect classifies all five repo states (A/B/C/W/D), exit 0 always;
#   - mode A backfills epics + requirement issues (pair labels + gsd
#     stamps), closes completed phases with the migrated reason, appends
#     beads: frontmatter, migrates pending todos, generates maps — and a
#     replan after apply contains zero create/close steps;
#   - apply resumes from a truncated journal without duplicating work;
#   - mode B bootstraps REQUIREMENTS/ROADMAP/STATE (+ MILESTONES pre-cairn
#     section) from bd, stamps labels+metadata, fabricates no PLAN.md, and
#     never overwrites an existing doc without --force;
#   - mode C auto-links exact CAT-NN title matches, holds fuzzy matches as
#     pending_confirmation candidates that apply skips until the plan file
#     flips confirmed=true, and creates the unmatched requirements.
#
# Assertion style note: substring checks use grep -qF and exact checks use
# `[ ]` (a failing `[[ ]]` mid-test does not fail a bats test on this bash).

load 'helpers'

MIGRATE() { bash "$CAIRN_SCRIPTS_DIR/cairn-migrate.sh" "$@"; }

# jq over `bd list --all -n 0 --json`
bd_json() { bd list --all -n 0 --json; }

issue_count() { bd_json | jq 'length'; }

# id of the issue whose metadata.gsd.req is $1 (empty when absent)
id_for_req() {
  bd_json | jq -r --arg r "$1" \
    '.[] | select((.metadata.gsd.req // "") == $r) | .id'
}

# id of the epic stamped with metadata.gsd.phase == $1
id_for_epic() {
  bd_json | jq -r --argjson n "$1" \
    '.[] | select(.issue_type == "epic" and (.metadata.gsd.phase // -1) == $n) | .id'
}

refute_contains() {
  if grep -qF -- "$1" <<<"$2"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

@test "detect classifies all five repo states, exit 0 always" {
  require_bd
  make_tmp_repo

  # D: neither .planning/ nor .beads/
  run MIGRATE detect
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "D" ]

  # A: .planning/ only
  make_gsd_fixture "$CAIRN_TMP_REPO"
  run MIGRATE detect
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "A" ]

  # C: both present, no map files, no beads: frontmatter
  bd init -q --prefix det --non-interactive >/dev/null 2>&1
  run MIGRATE detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.state' "C"
  assert_json_eq "$output" '.wired' "false"

  # W via a *-BEADS-MAP.md anywhere under .planning/
  touch .planning/phases/01-auth/01-BEADS-MAP.md
  run MIGRATE detect
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "W" ]
  rm .planning/phases/01-auth/01-BEADS-MAP.md

  # W via beads: frontmatter in a PLAN.md
  sed -i.bak 's/^status: complete$/status: complete\nbeads: [det-000]/' \
    .planning/phases/01-auth/01-01-PLAN.md
  run MIGRATE detect
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "W" ]

  # B: .beads/ only
  rm -rf .planning
  run MIGRATE detect
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "B" ]
}

@test "plan rejects a wrong mode for the repo state; apply rejects a missing plan" {
  make_tmp_repo

  # empty repo: mode C needs both dirs
  run MIGRATE plan --mode C
  [ "$status" -eq 2 ]

  # mode B without .beads/
  run MIGRATE plan --mode B
  [ "$status" -eq 2 ]

  # state D with no --mode: nothing to plan
  run MIGRATE plan
  [ "$status" -eq 2 ]

  # apply with no plan file
  run MIGRATE apply --yes
  [ "$status" -eq 2 ]

  # apply with invalid plan JSON
  mkdir -p .cairn
  echo "not json" > .cairn/migrate-plan.json
  run MIGRATE apply --yes
  [ "$status" -eq 2 ]
}

@test "mode A backfills epics, issues, closes, frontmatter, todos and maps" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  mkdir -p .planning/todos/pending
  printf '# Fix the README\n\nUpdate the install steps.\n' \
    > .planning/todos/pending/fix-readme.md
  bd init -q --prefix mga --non-interactive >/dev/null 2>&1

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  [ -f .cairn/migrate-plan.json ]
  assert_json_eq "$(cat .cairn/migrate-plan.json)" '.mode' "A"
  assert_json_eq "$(cat .cairn/migrate-plan.json)" '.milestone' "v1.0"

  run MIGRATE apply --yes
  [ "$status" -eq 0 ]

  # epics: pair labels + gsd stamp
  local epic1 epic2
  epic1="$(id_for_epic 1)"
  epic2="$(id_for_epic 2)"
  [ -n "$epic1" ] && [ -n "$epic2" ]
  assert_json_eq "$(bd show "$epic1" --json)" \
    '.[0].labels | sort | join(",")' "m-v1.0,phase-1"
  assert_json_eq "$(bd show "$epic1" --json)" '.[0].title' "Phase 01 — Auth"
  assert_json_eq "$(bd show "$epic2" --json)" '.[0].title' "Phase 02 — API"
  assert_json_eq "$(bd show "$epic1" --json)" \
    '.[0].metadata.gsd.milestone' "v1.0"

  # phase dep: epic2 depends on (is blocked by) epic1
  assert_json_eq "$(bd show "$epic2" --json)" \
    ".[0].dependencies | map(select(.dependency_type == \"blocks\") | .id) | join(\",\")" \
    "$epic1"

  # children: one per requirement, pair labels + full gsd stamp, parented
  local a1 a2 api
  a1="$(id_for_req AUTH-01)"
  a2="$(id_for_req AUTH-02)"
  api="$(id_for_req API-01)"
  [ -n "$a1" ] && [ -n "$a2" ] && [ -n "$api" ]
  assert_json_eq "$(bd show "$a1" --json)" '.[0].parent' "$epic1"
  assert_json_eq "$(bd show "$api" --json)" '.[0].parent' "$epic2"
  assert_json_eq "$(bd show "$a1" --json)" \
    '.[0].labels | sort | join(",")' "m-v1.0,phase-1"
  assert_json_eq "$(bd show "$api" --json)" \
    '.[0].labels | sort | join(",")' "m-v1.0,phase-2"
  assert_json_eq "$(bd show "$a2" --json)" '.[0].metadata.gsd.req' "AUTH-02"
  assert_json_eq "$(bd show "$a2" --json)" '.[0].metadata.gsd.phase' "1"
  grep -qF "Migrated from .planning (phase 01)" \
    <<<"$(bd show "$a1" --json | jq -r '.[0].description')"

  # phase 1 (complete + verified) closed with the migrated reason; 2 open
  assert_json_eq "$(bd show "$a1" --json)" '.[0].status' "closed"
  assert_json_eq "$(bd show "$a2" --json)" '.[0].status' "closed"
  assert_json_eq "$(bd show "$epic1" --json)" '.[0].status' "closed"
  grep -qF "migrated: completed in phase 01" \
    <<<"$(bd show "$epic1" --json | jq -r '.[0].close_reason')"
  assert_json_eq "$(bd show "$epic2" --json)" '.[0].status' "open"
  assert_json_eq "$(bd show "$api" --json)" '.[0].status' "open"

  # maps generated with requirement rows
  [ -f .planning/phases/01-auth/01-BEADS-MAP.md ]
  [ -f .planning/phases/02-api/02-BEADS-MAP.md ]
  grep -qF "| AUTH-01 | $a1 |" .planning/phases/01-auth/01-BEADS-MAP.md
  grep -qF "| API-01 | $api |" .planning/phases/02-api/02-BEADS-MAP.md

  # beads: frontmatter appended to both plans, with the resolved ids
  assert_frontmatter_key .planning/phases/01-auth/01-01-PLAN.md beads
  assert_frontmatter_key .planning/phases/02-api/02-01-PLAN.md beads
  grep -qF "$a1" .planning/phases/01-auth/01-01-PLAN.md
  grep -qF "$a2" .planning/phases/01-auth/01-01-PLAN.md
  grep -qF "$api" .planning/phases/02-api/02-01-PLAN.md

  # pending todo migrated with the migrated-todo label and no phase label
  local todo_json
  todo_json="$(bd_json | jq '[.[] | select((.labels // []) | index("migrated-todo"))]')"
  assert_json_eq "$todo_json" 'length' "1"
  assert_json_eq "$todo_json" '.[0].title' "Fix the README"
  assert_json_eq "$todo_json" \
    '[.[0].labels[] | select(startswith("phase-"))] | length' "0"
}

@test "mode A replan after apply contains zero create/close steps" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  bd init -q --prefix mgr --non-interactive >/dev/null 2>&1

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  local plan
  plan="$(cat .cairn/migrate-plan.json)"
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind | startswith("create"))] | length' "0"
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "close_issue")] | length' "0"
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "update_issue")] | length' "0"
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "dep_add")] | length' "0"
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "frontmatter_beads")] | length' "0"
}

@test "apply resumes from a truncated journal without duplicating work" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  bd init -q --prefix mgs --non-interactive >/dev/null 2>&1

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]
  local n_before
  n_before="$(issue_count)"

  # keep the journal header plus half of the completed-step lines
  local total keep
  total="$(wc -l < .cairn/migrate-state.json | tr -d ' ')"
  keep=$(( (total - 1) / 2 + 1 ))
  head -n "$keep" .cairn/migrate-state.json > .cairn/journal.tmp
  mv .cairn/journal.tmp .cairn/migrate-state.json

  run MIGRATE apply --yes
  [ "$status" -eq 0 ]
  grep -qF "already done (journal)" <<<"$output"

  # nothing duplicated: same issue count, one issue per requirement
  [ "$(issue_count)" = "$n_before" ]
  assert_json_eq "$(bd_json)" \
    '[.[] | select((.metadata.gsd.req // "") == "AUTH-01")] | length' "1"
  assert_json_eq "$(bd_json)" \
    '[.[] | select((.metadata.gsd.req // "") == "AUTH-02")] | length' "1"
  assert_json_eq "$(bd_json)" \
    '[.[] | select((.metadata.gsd.req // "") == "API-01")] | length' "1"
  # frontmatter merge did not duplicate ids
  local beads_line
  beads_line="$(grep '^beads:' .planning/phases/01-auth/01-01-PLAN.md)"
  [ "$(tr ',' '\n' <<<"$beads_line" | grep -c "$(id_for_req AUTH-01)")" = "1" ]
}

@test "mode B bootstraps planning docs from bd without fabricating PLAN.md" {
  require_bd
  make_tmp_repo
  bd init -q --prefix mgb --non-interactive >/dev/null 2>&1
  local epic c1 c2 standalone
  epic="$(bd create "Auth epic" -t epic -p 1 --silent)"
  c1="$(bd create "Implement login flow" -t task --parent "$epic" --silent)"
  c2="$(bd create "Scaffold auth module" -t task --parent "$epic" --silent)"
  bd close "$c2" --reason "done early" >/dev/null
  standalone="$(bd create "Old spike issue" -t task --silent)"
  bd close "$standalone" --reason "spike done" >/dev/null
  bd update "$c1" --claim >/dev/null 2>&1

  run MIGRATE plan --mode B --milestone v1.0
  [ "$status" -eq 0 ]
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]

  # the three generated docs exist; PROJECT.md is NOT written
  [ -f .planning/REQUIREMENTS.md ]
  [ -f .planning/ROADMAP.md ]
  [ -f .planning/STATE.md ]
  [ ! -e .planning/PROJECT.md ]

  # roadmap: one phase per epic, with a requirements list
  grep -qF "**Phase 1: Auth epic**" .planning/ROADMAP.md
  grep -qF "**Requirements**: [AUTH-01, AUTH-02]" .planning/ROADMAP.md
  grep -qF "**AUTH-01**: Implement login flow (bd: $c1)" .planning/REQUIREMENTS.md
  grep -qF "**AUTH-02**: Scaffold auth module (bd: $c2)" .planning/REQUIREMENTS.md
  assert_frontmatter_key .planning/STATE.md active_phase
  grep -qF 'active_phase: "1"' .planning/STATE.md

  # closed issues recorded in the pre-cairn milestone section
  grep -qF "## Completed pre-cairn" .planning/MILESTONES.md
  grep -qF "$standalone" .planning/MILESTONES.md
  grep -qF "$c2" .planning/MILESTONES.md

  # labels + metadata stamped on the epic and its children
  assert_json_eq "$(bd show "$epic" --json)" \
    '.[0].labels | sort | join(",")' "m-v1.0,phase-1"
  assert_json_eq "$(bd show "$epic" --json)" '.[0].metadata.gsd.phase' "1"
  assert_json_eq "$(bd show "$c1" --json)" '.[0].metadata.gsd.req' "AUTH-01"
  assert_json_eq "$(bd show "$c2" --json)" '.[0].metadata.gsd.req' "AUTH-02"
  # the closed standalone got no phase pairing (pre-cairn history only)
  assert_json_eq "$(bd show "$standalone" --json)" \
    '[(.[0].labels // [])[] | select(startswith("phase-"))] | length' "0"

  # map generated inside the created phase dir; no PLAN.md fabricated
  ls .planning/phases/01-*/01-BEADS-MAP.md >/dev/null
  grep -qF "| AUTH-01 | $c1 |" .planning/phases/01-*/01-BEADS-MAP.md
  [ "$(find .planning -name '*PLAN.md' | wc -l | tr -d ' ')" = "0" ]

  # replan after apply: no more writes or links, only map regeneration
  run MIGRATE plan --mode B --milestone v1.0
  [ "$status" -eq 0 ]
  assert_json_eq "$(cat .cairn/migrate-plan.json)" \
    '[.steps[] | select(.kind == "write_file" or .kind == "link_issue")] | length' \
    "0"
}

@test "mode B never overwrites an existing doc without --force" {
  require_bd
  make_tmp_repo
  bd init -q --prefix mgo --non-interactive >/dev/null 2>&1
  bd create "Solo task" -t task --silent >/dev/null
  mkdir -p .planning
  echo "SENTINEL: hand-written requirements" > .planning/REQUIREMENTS.md

  run MIGRATE plan --mode B --milestone v1.0
  [ "$status" -eq 0 ]
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]
  grep -qF "SENTINEL: hand-written requirements" .planning/REQUIREMENTS.md
  [ -f .planning/ROADMAP.md ]   # absent docs are still generated

  run MIGRATE plan --mode B --milestone v1.0 --force
  [ "$status" -eq 0 ]
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]
  refute_contains "SENTINEL" "$(cat .planning/REQUIREMENTS.md)"
  grep -qF "Bootstrapped from beads" .planning/REQUIREMENTS.md
}

@test "mode C links exact matches, defers fuzzy candidates, creates the rest" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  bd init -q --prefix mgc --non-interactive >/dev/null 2>&1
  local exact fuzzy orphan
  exact="$(bd create "AUTH-01: user signup handler" -t task --silent)"
  fuzzy="$(bd create "User can log in with valid credential" -t task --silent)"
  orphan="$(bd create "Upgrade CI runners" -t chore --silent)"

  run MIGRATE plan --milestone v1.0   # detected state C, no --mode needed
  [ "$status" -eq 0 ]
  local plan
  plan="$(cat .cairn/migrate-plan.json)"
  assert_json_eq "$plan" '.mode' "C"
  # exact CAT token in the title -> auto-link step
  assert_json_eq "$plan" \
    "[.steps[] | select(.kind == \"link_issue\" and .params.id == \"$exact\")] | length" \
    "1"
  # fuzzy similarity -> pending_confirmation candidate with a score
  assert_json_eq "$plan" \
    "[.steps[] | select(.kind == \"link_candidate\")] | length" "1"
  assert_json_eq "$plan" \
    ".steps[] | select(.kind == \"link_candidate\") | .params.id" "$fuzzy"
  assert_json_eq "$plan" \
    ".steps[] | select(.kind == \"link_candidate\") | .status" \
    "pending_confirmation"
  # unmatched requirement -> mode-A style create
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "create_issue") | .params.req] | join(",")' \
    "API-01"
  # unmatched unlabeled issue -> orphan, default action report
  assert_json_eq "$plan" \
    ".orphans[] | select(.id == \"$orphan\") | .action" "report"
  # SUMMARY-complete phase with an open matched issue -> close offer that
  # also awaits confirmation
  assert_json_eq "$plan" \
    "[.steps[] | select(.kind == \"close_issue\" and .params.id == \"$exact\")] | .[0].status" \
    "pending_confirmation"

  run MIGRATE apply --yes
  [ "$status" -eq 0 ]
  grep -qF "awaiting confirmation" <<<"$output"

  # exact match linked: pair labels + gsd stamp
  assert_json_eq "$(bd show "$exact" --json)" \
    '.[0].labels | sort | join(",")' "m-v1.0,phase-1"
  assert_json_eq "$(bd show "$exact" --json)" '.[0].metadata.gsd.req' "AUTH-01"
  # unconfirmed close offer skipped: the exact match is still open
  assert_json_eq "$(bd show "$exact" --json)" '.[0].status' "open"
  # unconfirmed candidate skipped: untouched
  assert_json_eq "$(bd show "$fuzzy" --json)" \
    '[(.[0].labels // [])[] | select(startswith("m-"))] | length' "0"
  # unmatched requirement created
  [ -n "$(id_for_req API-01)" ]

  # the prose command confirms the candidate in the plan file; apply links it
  python3 - <<'PYEOF'
import json
path = ".cairn/migrate-plan.json"
plan = json.load(open(path))
for step in plan["steps"]:
    if step["kind"] == "link_candidate":
        step["params"]["confirmed"] = True
json.dump(plan, open(path, "w"), indent=2)
PYEOF
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]
  assert_json_eq "$(bd show "$fuzzy" --json)" \
    '.[0].labels | sort | join(",")' "m-v1.0,phase-1"
  assert_json_eq "$(bd show "$fuzzy" --json)" '.[0].metadata.gsd.req' "AUTH-02"
}
