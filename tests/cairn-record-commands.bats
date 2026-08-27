#!/usr/bin/env bats
# cairn-record-commands.bats — the planning family records on beads (phase 46,
# RECORD-03). One case per command, STATIC over the command's own md: the
# command is prose, and its observable contract is what it tells the session
# to run. Each must name the cairn-record kind it writes, and none may send
# the session to write under .planning/phases/ or to "read and follow" the
# vendored GSD workflow. A command that regressed to a file would fail here
# by name.

load 'helpers'

COMMANDS="$CAIRN_REPO_ROOT/cairn/commands"

# name:kind — the kind each command records with (D-01 of phase 46).
FAMILY="spec-phase:spec discuss-phase:context plan:plan mvp-phase:plan plan-review-convergence:plan ultraplan-phase:plan ui-phase:ui-spec ai-integration-phase:ai-spec secure-phase:review validate-phase:verification work:summary verify:verification"

assert_records_only() {
  local name="$1" kind="$2" file="$COMMANDS/$1.md"
  [ -f "$file" ] || { echo "$file missing" >&2; return 1; }
  grep -qF "cairn-record.sh\" $kind" "$file" \
    || { echo "$name.md never records with cairn-record.sh $kind" >&2; return 1; }
  if grep -qE '\.planning/phases/[^ ]*\.md' "$file"; then
    echo "$name.md still writes (or names) a file under .planning/phases/" >&2
    return 1
  fi
  if grep -qF 'gsd/commands/gsd/' "$file"; then
    echo "$name.md still sends the session to a vendored GSD workflow" >&2
    return 1
  fi
  if grep -qiE 'the deliverable is `\.planning' "$file"; then
    echo "$name.md still declares a file deliverable" >&2
    return 1
  fi
}

@test "every command of the planning family records with its kind and writes no file" {
  local pair name kind
  for pair in $FAMILY; do
    name="${pair%%:*}"; kind="${pair#*:}"
    assert_records_only "$name" "$kind"
  done
}

@test "spec-phase records a spec" { assert_records_only spec-phase spec; }
@test "discuss-phase records a context" { assert_records_only discuss-phase context; }
@test "plan records plan records" { assert_records_only plan plan; }
@test "mvp-phase records plan records" { assert_records_only mvp-phase plan; }
@test "plan-review-convergence rewrites plan records and appends a review" {
  assert_records_only plan-review-convergence plan
  grep -qF 'cairn-record.sh" review' "$COMMANDS/plan-review-convergence.md"
}
@test "ultraplan-phase imports into plan records" { assert_records_only ultraplan-phase plan; }
@test "ui-phase records a ui-spec" { assert_records_only ui-phase ui-spec; }
@test "ai-integration-phase records an ai-spec" { assert_records_only ai-integration-phase ai-spec; }
@test "secure-phase appends a review" { assert_records_only secure-phase review; }
@test "validate-phase records a verification" { assert_records_only validate-phase verification; }
@test "work closes each plan record with its summary" { assert_records_only work summary; }
@test "verify records the verdict" { assert_records_only verify verification; }

@test "the family reads the record back from bd, never from a file" {
  local pair name
  for pair in $FAMILY; do
    name="${pair%%:*}"
    grep -qE 'bd show <(carrier|plan-record)>|cairn-map\.sh' "$COMMANDS/$name.md" \
      || { echo "$name.md never tells the session where to read the record" >&2; return 1; }
  done
}
