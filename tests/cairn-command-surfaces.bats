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
WRAP="$CAIRN_SCRIPTS_DIR/cairn-wrap.sh"
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

# ---------------------------------------------------------------------------
# CairnGo-q9l — the /cairn:help map derives BOTH halves
# ---------------------------------------------------------------------------

# Every installed command name, one per line — wrappers and cairn's own.
all_command_names() {
  bash "$WRAP" list --commands-dir "$1" --json \
    | jq -r '.commands[]'
}

@test "the help map names no command by hand, beyond the six prose names" {
  # MEASURED 2026-08-06 (CairnGo-q9l): commit aa48bb3 made the WRAPPER half of
  # the map derived and left cairn's own half typed — and that half had
  # already dropped a command:
  #     grep -c 'cairn:reconcile' cairn/commands/help.md  ->  0
  # while /cairn:reconcile existed, had a page, and had a row in the
  # reference. Nothing caught it: `docs --check` only looks at cairn/docs/,
  # and the suite only knew how to reject the opposite direction (a name in
  # the help that is not on disk).
  #
  # The allowlist below is the whole hand-written surface that survives, and
  # each name is there for a reason that is not "a listing":
  #   config, sync-config, context-config — the three-config-files section,
  #     required by name in tests/cairn-config.bats ("the three config
  #     commands are told apart in one place")
  #   new, migrate, status — the next-step routing rule in the opening
  #     paragraph, which is behaviour, not a map
  # Anything else means somebody typed the map back in.
  local help="$CAIRN_REPO_ROOT/cairn/commands/help.md"
  local allowed=" config sync-config context-config new migrate status "

  local name typed=""
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    case "$allowed" in *" $name "*) continue ;; esac
    if grep -qF -- "/cairn:$name" "$help"; then
      typed="$typed $name"
    fi
  done < <(all_command_names "$CAIRN_REPO_ROOT/cairn/commands")

  if [ -n "$typed" ]; then
    echo "the help map transcribes command name(s):$typed" >&2
    return 1
  fi
}

@test "the help map says where BOTH halves come from" {
  local help="$CAIRN_REPO_ROOT/cairn/commands/help.md"

  # The wrapper half (phase 26, aa48bb3) — kept.
  grep -qF 'cairn-wrap.sh" list' "$help"

  # The own half: the set difference, and the per-command fields that make a
  # rendered line possible without a list on this page.
  grep -qF '.wrappers[].command' "$help"
  grep -qF 'group:' "$help"
  grep -qF 'description:' "$help"

  # And the rule that keeps a new command visible even when its author
  # forgets the group key: wrong heading is allowed, missing is not.
  grep -qF 'OTHER' "$help"
}

@test "a command added to the disk appears in the map with no prose edited" {
  # The same proof by ADDITION that phase 26's verification ran for the
  # wrappers, now for cairn's own half: drop a file in, and the derivation
  # the help page reads reports it — with nobody editing help.md.
  local dir="$BATS_TEST_TMPDIR/probe-commands"
  mkdir -p "$dir"
  cp "$CAIRN_REPO_ROOT/cairn/commands/status.md" "$dir/status.md"
  cp "$CAIRN_REPO_ROOT/cairn/commands/phase.md" "$dir/phase.md"   # a wrapper
  cat > "$dir/zzz-probe.md" <<'EOF'
---
description: A probe command that exists only inside this test
group: view
---
body
EOF

  run bash "$WRAP" list --commands-dir "$dir" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.commands[] | select(. == "zzz-probe")] | length' '1'
  assert_json_eq "$output" '[.wrappers[] | select(.command == "zzz-probe")] | length' '0'

  # The two fields the page tells the agent to read are on the file itself.
  assert_frontmatter_key "$dir/zzz-probe.md" "group"
  assert_frontmatter_key "$dir/zzz-probe.md" "description"

  # And a file with NO group is still listed — it renders under OTHER, never
  # nowhere. This is the half that makes "invisible" impossible.
  cat > "$dir/zzz-groupless.md" <<'EOF'
---
description: A probe command whose author forgot the group key
---
body
EOF
  run bash "$WRAP" list --commands-dir "$dir" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.commands[] | select(. == "zzz-groupless")] | length' '1'
}

@test "every command cairn owns declares the group it prints under" {
  # Not required for visibility — a groupless command still renders, under
  # OTHER. Required so that the shipped map reads as designed rather than
  # accumulating an OTHER pile nobody notices.
  local dir="$CAIRN_REPO_ROOT/cairn/commands"
  local listing; listing="$(bash "$WRAP" list --commands-dir "$dir" --json)"

  local name ungrouped=""
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    # Wrappers group by wrap-family, which cairn-wrap.py already enforces.
    if [ "$(jq -r --arg n "$name" \
        '[.wrappers[] | select(.command == $n)] | length' <<<"$listing")" != "0" ]; then
      continue
    fi
    grep -qE '^group: [a-z-]+$' "$dir/$name.md" || ungrouped="$ungrouped $name"
  done < <(jq -r '.commands[]' <<<"$listing")

  if [ -n "$ungrouped" ]; then
    echo "cairn command(s) with no group: key:$ungrouped" >&2
    return 1
  fi
}

# ---------------------------------------------------------------------------
# CairnGo-3w9 — a script with no door is invisible to the derived page
# ---------------------------------------------------------------------------

@test "the two phase-30 scripts have both doors" {
  # MEASURED 2026-08-07: phase 30 shipped cairn-land.py and cairn-review.py
  # with a .sh pair and a bats suite each, and neither had a /cairn:* command
  # or a page. Found while writing a routing string for /cairn:land — which
  # did not exist, so the string had to name the script instead.
  local name
  for name in land review; do
    [ -f "$CAIRN_REPO_ROOT/cairn/scripts/cairn-$name.py" ]
    [ -f "$CAIRN_REPO_ROOT/cairn/commands/$name.md" ]
    [ -f "$CAIRN_REPO_ROOT/cairn/docs/commands/$name.md" ]
    # And the command reaches the script it is a door onto.
    grep -qF "scripts/cairn-$name.sh" "$CAIRN_REPO_ROOT/cairn/commands/$name.md"
  done

  # Both are now in the derived listing, which is the half of WRAP-03 that
  # could not fire before: a script with no command is not listed BY
  # DEFINITION, so the derived page had no way to notice the absence.
  local listing
  listing="$(bash "$WRAP" list --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" --json)"
  assert_json_eq "$listing" '[.commands[] | select(. == "land")] | length' '1'
  assert_json_eq "$listing" '[.commands[] | select(. == "review")] | length' '1'
}

@test "every cairn script is reachable by command, or its absence is written down" {
  # The guard that makes the NEXT phase-30 loud. A script with no /cairn:*
  # command is not a defect by itself — most of these are invoked BY the
  # commands — but an unexamined one is exactly how land and review shipped
  # with no door. So every script is either a command or carries a reason
  # here, and a new script forces that decision instead of inheriting silence.
  # bash 3.2 (the macOS default) has no associative arrays — a case, then.
  # The reason is the payload: an entry with no sentence is not an entry.
  script_has_written_reason() {
    case "$1" in
      bookkeep) echo "the end-of-phase bookkeeping the loop commands invoke; contract at docs/commands/bookkeep.md, and named in the help page" ;;
      capability) echo "install-time plumbing for the GSD capability; invoked by /cairn:init and /cairn:migrate" ;;
      gate) echo "the deterministic milestone gate; invoked by /cairn:ship and /cairn:milestone complete" ;;
      jira) echo "Jira detection; invoked by /cairn:sync-config" ;;
      journal) echo "the append-only resume journal; invoked by /cairn:migrate and the parallel runner" ;;
      lease) echo "the phase lease; invoked by the loop commands and released by bookkeep" ;;
      map) echo "the generated phase-beads map; invoked by /cairn:plan, /cairn:work and bookkeep" ;;
      parallel) echo "the parallel phase runner; invoked by /cairn:autonomous" ;;
      relabel) echo "label maintenance; invoked by /cairn:phase and by the doctor's --fix-labels" ;;
      release) echo "release engineering for cairn's OWN repo; routed by the doctor's release-versions check" ;;
      test) echo "the bats suite runner for cairn's OWN repo; routed by the doctor's test-parallel check" ;;
      trend) echo "first-pass verdict history across cycles; a maintainer report, not a project verb" ;;
      wrap) echo "the derivation tool itself; invoked by /cairn:help and by the docs regeneration" ;;
      *) return 1 ;;
    esac
  }

  local path name undoored=""
  for path in "$CAIRN_REPO_ROOT"/cairn/scripts/cairn-*.py; do
    name="$(basename "$path" .py)"
    name="${name#cairn-}"
    [ -f "$CAIRN_REPO_ROOT/cairn/commands/$name.md" ] && continue
    script_has_written_reason "$name" >/dev/null && continue
    undoored="$undoored $name"
  done

  if [ -n "$undoored" ]; then
    echo "cairn script(s) with no /cairn: command and no written reason:$undoored" >&2
    echo "give it a command + a page, or add it to the table in this test with why" >&2
    return 1
  fi
}

@test "the command reference lists every command, and its block is current" {
  # The two new commands must have reached BOTH derived surfaces, not just the
  # help: a row in the reference and a page behind the link. This is the same
  # pair tests/cairn-wrap.bats guards for the whole page — asserted here too
  # because it is the acceptance of this issue, not a side effect.
  run bash "$WRAP" docs --check --json \
    --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" \
    --doc "$CAIRN_REPO_ROOT/cairn/docs/commands.md" \
    --doc-pages-dir "$CAIRN_REPO_ROOT/cairn/docs/commands"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.undocumented | length' '0'
  assert_json_eq "$output" '.missing_pages | length' '0'
}

# ---------------------------------------------------------------------------
# CairnGo-13t (FIX-01) — a step ordered at a moment it cannot run
# ---------------------------------------------------------------------------

@test "generating a phase map before the phase directory exists fails, exit 4" {
  # The measurement the issue was opened with, reproduced. Verified when v1.4
  # opened: 5 of 5 phases failed this way; confirmed live when v1.5 opened
  # (2026-08-03) with `cairn-map.sh 20` -> "no phase directory matching phase
  # 20", exit 4.
  #
  # The script does not lie — it fails loudly, with a code of its own. The
  # defect is in the prose that ordered it at a moment when no phase directory
  # exists yet, because the directories are born in /gsd:plan-phase.
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix fix01 --non-interactive >/dev/null 2>&1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 20 --planning-dir "$PWD/.planning"
  [ "$status" -eq 4 ]
  grep -qF "no phase directory matching phase 20" <<<"$output"
}

@test "no surface orders a map generation at milestone-new time" {
  # Both surfaces carried it: cairn/commands/milestone.md step 3, and
  # cairn/skills/cairn/SKILL.md in the /gsd:new-milestone block. Fixing one
  # would have left the other giving the impossible order.
  local file
  for file in "$CAIRN_REPO_ROOT/cairn/commands/milestone.md" \
              "$CAIRN_REPO_ROOT/cairn/skills/cairn/SKILL.md"; do
    # The same files legitimately name cairn-map for /cairn:plan, where the
    # directory DOES exist — so this is scoped to the region that opens a
    # milestone, and that region ends at the next section heading or the next
    # top-level bullet.
    local hits
    hits="$(python3 - "$file" <<'PY'
import re, sys
lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
opener = re.compile(r"new[ -]milestone|milestone new|^##\s.*\bnew\b", re.I)
closer = re.compile(r"^##\s|^-\s\*\*")
call = re.compile(r"cairn-map(\.sh|\.py)?[^\w<]{0,3}<?N")
flagged = {}
for i, line in enumerate(lines):
    if not opener.search(line):
        continue
    for j in range(i + 1, len(lines)):
        if closer.match(lines[j]):
            break
        if call.search(lines[j]):
            flagged[j + 1] = lines[j].strip()
for n in sorted(flagged):
    print(f"{n}: {flagged[n]}")
PY
)"
    if [ -n "$hits" ]; then
      echo "$file still orders a map generation next to milestone-new:" >&2
      echo "$hits" >&2
      return 1
    fi
  done

  # And both say where the map is actually born, so the step was moved rather
  # than merely deleted.
  grep -qF "/cairn:plan" "$CAIRN_REPO_ROOT/cairn/commands/milestone.md"
  grep -qF "plan-phase" "$CAIRN_REPO_ROOT/cairn/skills/cairn/SKILL.md"
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
