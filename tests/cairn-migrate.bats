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
#     flips confirmed=true, and creates the unmatched requirements;
#   - completion follows the ROADMAP checkbox (GSD's source of truth): a
#     checked phase without SUMMARY/VERIFICATION artifacts still closes
#     (reason + plan note say "closed via roadmap checkbox"), unbolded
#     checkbox lines parse like cairn-gate's lenient regex, dep_add is
#     skipped when the blocker phase is complete (with closes ordered
#     before the surviving deps), and phase-labeled strays outside the
#     requirements list are swept closed;
#   - a failed apply step gets one retry, lands in the journal with status
#     "failed" (directed replay on the next run), and the summary lists
#     the failed ids/kinds;
#   - detect --json sniffs Jira keys from commits/branches behind a
#     frequency guard (>= 3 of the SAME prefix) and a local REQ-prefix
#     exclusion, plus env JIRA_* / atlassian.net remote signals.
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

  # phase 1 is complete, so the epic2 -> epic1 dep is SKIPPED: wiring a
  # dependency on a completed blocker only manufactures blocked issues
  assert_json_eq "$(bd show "$epic2" --json)" \
    '(.[0].dependencies // []) | map(select(.dependency_type == "blocks") | .id) | join(",")' \
    ""

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

@test "apply reports a filesystem failure as FAIL + exit 8, not a traceback" {
  require_bd
  make_tmp_repo

  # A path component that is a FILE makes do_write_file raise OSError —
  # apply must keep the documented exit contract (8 = partial failure with
  # resume guidance), never crash with a raw traceback (exit 1).
  touch blocker
  mkdir -p .cairn
  cat > .cairn/migrate-plan.json <<'PLANEOF'
{"version": 1, "mode": "A", "milestone": "v1.0",
 "created_at": "2026-07-25T00:00:00Z",
 "steps": [{"id": "s001", "kind": "write_file",
            "params": {"path": "blocker/notes.md", "content": "x\n"},
            "status": "pending"}]}
PLANEOF

  run MIGRATE apply --yes
  [ "$status" -eq 8 ]
  grep -qF "FAIL s001" <<<"$output"
  grep -qF "resume by re-running" <<<"$output"
  refute_contains "Traceback" "$output"
}

@test "block-style beads: frontmatter merges into one flow list, no leftover items" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  local plan_md=".planning/phases/02-api/02-01-PLAN.md"
  # The block form cairn-doctor accepts: 'beads:' + indented '- id' items.
  sed -i.bak 's/^status: in_progress$/status: in_progress\nbeads:\n  - mgd-99/' \
    "$plan_md"
  rm -f "$plan_md.bak"

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]

  local api_id
  api_id="$(id_for_req API-01)"
  [ -n "$api_id" ]
  # Merged to a single flow list keeping the pre-existing id first...
  grep -qxF "beads: [mgd-99, $api_id]" "$plan_md"
  # ...with the old block items consumed, not duplicated below the list.
  refute_contains "- mgd-99" "$(cat "$plan_md")"
}

@test "plan notes checked ROADMAP phases closed on checkbox evidence alone" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  # Phase 2 checked in ROADMAP but with no SUMMARY / passed VERIFICATION:
  # the ROADMAP checkbox is the GSD source of truth (the same rule the ship
  # gates apply), so migrate closes its issues anyway — the note must say
  # which phases closed on checkbox evidence alone, and the close steps
  # must carry the matching reason.
  sed -i.bak 's/^- \[ \] \*\*Phase 2: API\*\*/- [x] **Phase 2: API**/' \
    .planning/ROADMAP.md
  rm -f .planning/ROADMAP.md.bak

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  grep -qF "note: ROADMAP marks phase(s) 2 complete" <<<"$output"
  grep -qF "closed via roadmap checkbox" <<<"$output"
  grep -qF "ship gate" <<<"$output"
  # Phase 1 has a SUMMARY + passed VERIFICATION — never flagged.
  refute_contains "phase(s) 1" "$output"
  # The note is persisted in the plan file for the prose command to surface.
  grep -qF "ROADMAP marks phase(s) 2 complete" .cairn/migrate-plan.json
  # phase 2's requirement + epic each get a close step with the checkbox
  # reason (artifact-backed phase 1 keeps the SUMMARIES reason)
  assert_json_eq "$(cat .cairn/migrate-plan.json)" \
    '[.steps[] | select(.kind == "close_issue" and (.params.reason | contains("roadmap checkbox")))] | length' \
    "2"
  assert_json_eq "$(cat .cairn/migrate-plan.json)" \
    '[.steps[] | select(.kind == "close_issue" and (.params.reason | contains("see SUMMARIES")))] | length' \
    "3"
}

@test "mode A apply closes ROADMAP-checked phases without artifacts" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  # Phase 2 checked but with no SUMMARY / passed VERIFICATION on disk —
  # the real-world shape that used to leave open issues + dep chains
  # blocking the whole board while ROADMAP said everything was done.
  sed -i.bak 's/^- \[ \] \*\*Phase 2: API\*\*/- [x] **Phase 2: API**/' \
    .planning/ROADMAP.md
  rm -f .planning/ROADMAP.md.bak
  bd init -q --prefix mgk --non-interactive >/dev/null 2>&1

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  grep -qF "closed via roadmap checkbox" <<<"$output"

  run MIGRATE apply --yes
  [ "$status" -eq 0 ]

  local epic1 epic2 api
  epic1="$(id_for_epic 1)"
  epic2="$(id_for_epic 2)"
  api="$(id_for_req API-01)"
  [ -n "$epic1" ] && [ -n "$epic2" ] && [ -n "$api" ]
  assert_json_eq "$(bd show "$api" --json)" '.[0].status' "closed"
  assert_json_eq "$(bd show "$epic2" --json)" '.[0].status' "closed"
  grep -qF "closed via roadmap checkbox, artifacts missing" \
    <<<"$(bd show "$epic2" --json | jq -r '.[0].close_reason')"
  # the artifact-complete phase keeps the SUMMARIES reason
  grep -qF "see SUMMARIES" \
    <<<"$(bd show "$epic1" --json | jq -r '.[0].close_reason')"
  # no open issue survives: the board tells the same story as ROADMAP
  assert_json_eq "$(bd_json)" '[.[] | select(.status != "closed")] | length' "0"
}

@test "lenient checkbox: unbolded '- [x] Phase N: ...' parses like the gate" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  # cairn-gate accepts any checked line naming Phase N; migrate must parse
  # the same lines or the gate and the board disagree about completion.
  sed -i.bak \
    -e 's/^- \[x\] \*\*Phase 1: Auth\*\* - Signup and login flows$/- [x] Phase 1: Auth/' \
    -e 's/^- \[ \] \*\*Phase 2: API\*\* - Rate-limited public API$/- [ ] Phase 2: API/' \
    .planning/ROADMAP.md
  rm -f .planning/ROADMAP.md.bak

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  local plan
  plan="$(cat .cairn/migrate-plan.json)"
  # both phases parsed with their names intact
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "create_epic") | .params.title] | join(",")' \
    "Phase 01 — Auth,Phase 02 — API"
  # the unbolded [x] still marks phase 1 completed -> its 3 close steps
  # (AUTH-01, AUTH-02, the epic)
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "close_issue")] | length' "3"
  # ...and unchecked phase 2 stays open
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "close_issue" and (.params.reason | contains("phase 02")))] | length' \
    "0"
}

@test "dep_add skipped when the blocker phase is complete; closes precede deps" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  # a third phase depending on the incomplete phase 2 keeps one live dep
  cat >> .planning/ROADMAP.md <<'EOF'

- [ ] **Phase 3: Console**

### Phase 3: Console
**Goal**: Ops console on top of the API
**Depends on**: Phase 2
**Requirements**: []
EOF
  bd init -q --prefix mgp --non-interactive >/dev/null 2>&1

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  local plan last_close first_dep
  plan="$(cat .cairn/migrate-plan.json)"
  # phase2 -> phase1 skipped (phase 1 complete); phase3 -> phase2 survives
  assert_json_eq "$plan" \
    '[.steps[] | select(.kind == "dep_add")] | length' "1"
  assert_json_eq "$plan" \
    '.steps[] | select(.kind == "dep_add") | .params.from_key' "epic:3"
  # every close of a completed phase is ordered before the surviving deps
  last_close="$(jq '[.steps | to_entries[] | select(.value.kind == "close_issue") | .key] | max' <<<"$plan")"
  first_dep="$(jq '[.steps | to_entries[] | select(.value.kind == "dep_add") | .key] | min' <<<"$plan")"
  [ "$last_close" -lt "$first_dep" ]

  run MIGRATE apply --yes
  [ "$status" -eq 0 ]
  local epic2 epic3
  epic2="$(id_for_epic 2)"
  epic3="$(id_for_epic 3)"
  [ -n "$epic2" ] && [ -n "$epic3" ]
  assert_json_eq "$(bd show "$epic3" --json)" \
    '(.[0].dependencies // []) | map(select(.dependency_type == "blocks") | .id) | join(",")' \
    "$epic2"
  assert_json_eq "$(bd show "$epic2" --json)" \
    '(.[0].dependencies // []) | map(select(.dependency_type == "blocks")) | length' \
    "0"
}

@test "mode A sweeps phase-labeled strays so the epic close succeeds" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  bd init -q --prefix mgl --non-interactive >/dev/null 2>&1
  # a child of the completed phase that is NOT in the ROADMAP requirements
  # list — before the sweep it stayed open and broke the epic close
  local stray other
  stray="$(bd create "Follow-up polish" -t task -l phase-1,m-v1.0 --silent)"
  # the same phase label stamped for ANOTHER milestone must be left alone
  other="$(bd create "Other milestone work" -t task -l phase-1,m-v2.0 --silent)"

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]

  assert_json_eq "$(bd show "$stray" --json)" '.[0].status' "closed"
  grep -qF "migrated: completed in phase 01" \
    <<<"$(bd show "$stray" --json | jq -r '.[0].close_reason')"
  assert_json_eq "$(bd show "$other" --json)" '.[0].status' "open"
  assert_json_eq "$(bd show "$(id_for_epic 1)" --json)" '.[0].status' "closed"
}

@test "mode A sweep spares a cross-phase stray and catches a zero-padded label" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  bd init -q --prefix mgx --non-interactive >/dev/null 2>&1
  # phase-1 is complete but phase-2 is still live: ALL, not any — the same
  # predicate cairn-status's in_done_phase and cairn-doctor's
  # --close-completed use, so the sweep never buries live work.
  local cross padded
  cross="$(bd create "Spans both phases" -t task -l phase-1,phase-2,m-v1.0 --silent)"
  # a zero-padded label for the SAME complete phase must still be swept:
  # left open it makes the epic close fail (exit 8), which is what the
  # sweep exists to prevent.
  padded="$(bd create "Padded stray" -t task -l phase-01,m-v1.0 --silent)"

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  run MIGRATE apply --yes
  [ "$status" -eq 0 ]

  assert_json_eq "$(bd show "$cross" --json)" '.[0].status' "open"
  assert_json_eq "$(bd show "$padded" --json)" '.[0].status' "closed"
  grep -qF "migrated: completed in phase 01" \
    <<<"$(bd show "$padded" --json | jq -r '.[0].close_reason')"
  assert_json_eq "$(bd show "$(id_for_epic 1)" --json)" '.[0].status' "closed"
}

@test "a create that fails AFTER the issue landed does not duplicate on retry" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  bd init -q --prefix mgr --non-interactive >/dev/null 2>&1

  # bd stub: the FIRST 'create' really creates the issue and THEN reports
  # failure — the exact window where a blind retry minted a duplicate,
  # because the retry re-read a stale in-memory index.
  local stub_bin real_bd
  real_bd="$(command -v bd)"
  stub_bin="$BATS_TEST_TMPDIR/flaky-bin"
  mkdir -p "$stub_bin"
  cat > "$stub_bin/bd" <<EOF
#!/usr/bin/env bash
REAL="$real_bd"
MARKER="$BATS_TEST_TMPDIR/create-failed-once"
if [ "\$3" = "create" ] && [ ! -e "\$MARKER" ]; then
  : > "\$MARKER"
  "\$REAL" "\$@"
  echo "simulated post-create failure" >&2
  exit 1
fi
exec "\$REAL" "\$@"
EOF
  chmod +x "$stub_bin/bd"

  run MIGRATE plan --mode A --milestone v1.0
  [ "$status" -eq 0 ]
  run env PATH="$stub_bin:$PATH" \
      bash "$CAIRN_SCRIPTS_DIR/cairn-migrate.sh" apply --yes
  [ "$status" -eq 0 ]
  grep -qF "retry" <<<"$output"
  [ -e "$BATS_TEST_TMPDIR/create-failed-once" ]   # the stub really fired

  # One epic per phase: the retry adopted what the failed attempt created.
  [ "$(bd_json | jq '[.[] | select(.issue_type=="epic" and (.metadata.gsd.phase // -1) == 1)] | length')" -eq 1 ]
  [ "$(bd_json | jq '[.[] | select(.issue_type=="epic")] | length')" -eq 2 ]
  # ...and no requirement ended up with two issues either.
  [ "$(bd_json | jq '[.[] | select((.metadata.gsd.req // "") != "") | .metadata.gsd.req] | (length - (unique | length))')" -eq 0 ]
}

@test "a failed step is retried once, journaled as failed, and replayed" {
  require_bd
  make_tmp_repo
  touch blocker
  mkdir -p .cairn
  cat > .cairn/migrate-plan.json <<'PLANEOF'
{"version": 1, "mode": "A", "milestone": "v1.0",
 "created_at": "2026-07-27T00:00:00Z",
 "steps": [{"id": "s001", "kind": "write_file",
            "params": {"path": "blocker/notes.md", "content": "x\n"},
            "status": "pending"}]}
PLANEOF

  run MIGRATE apply --yes
  [ "$status" -eq 8 ]
  # one retry, then the failure lands in the summary with id + kind
  grep -qF "retry s001 (write_file)" <<<"$output"
  grep -qF "1 failed" <<<"$output"
  grep -qF "failed: s001 (write_file)" <<<"$output"
  # ...and in the journal with status failed
  grep -qF '"step": "s001"' .cairn/migrate-state.json
  grep -qF '"status": "failed"' .cairn/migrate-state.json

  # directed replay: the failed record never counts as completed
  run MIGRATE apply --yes
  [ "$status" -eq 8 ]
  grep -qF "FAIL s001" <<<"$output"
  grep -qF "0 already done (journal)" <<<"$output"
}

@test "detect sniffs Jira keys with frequency and REQ-prefix guards" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"

  # no commits yet: nothing to sniff
  run MIGRATE detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.external.jira.prefixes | length' "0"

  # >= 3 occurrences of the SAME prefix across subjects + bodies count;
  # AUTH-* matches the local REQUIREMENTS.md req ids and is excluded; a
  # single ONEOFF-1 stays under the frequency bar
  git commit -q --allow-empty -m "DTP-101: wire the login flow"
  git commit -q --allow-empty -m "chore: bump deps" -m "Relates to DTP-102"
  git commit -q --allow-empty -m "DTP-103 hotfix"
  git commit -q --allow-empty -m "AUTH-01 polish"
  git commit -q --allow-empty -m "AUTH-02 polish"
  git commit -q --allow-empty -m "AUTH-01 again"
  git commit -q --allow-empty -m "ONEOFF-1: below the frequency bar"
  # three branch names carrying one prefix also cross the bar
  git branch OPS-1-fix
  git branch OPS-2-fix
  git branch OPS-3-fix

  run MIGRATE detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.external.jira.detected' "true"
  assert_json_eq "$output" '.external.jira.prefixes | join(",")' "DTP,OPS"
  assert_json_eq "$output" \
    '.external.jira.signals | contains(["git-log", "branches"])' "true"

  # an atlassian.net remote is an independent signal
  git remote add origin https://example.atlassian.net/scm/proj.git
  run MIGRATE detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.external.jira.signals | contains(["remote"])' "true"

  # so is any JIRA_* env var
  run env JIRA_SITE=https://example.atlassian.net \
    bash "$CAIRN_SCRIPTS_DIR/cairn-migrate.sh" detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.external.jira.signals | contains(["env"])' "true"
}
