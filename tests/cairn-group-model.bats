#!/usr/bin/env bats
# cairn-group-model.bats — the model knows which group each thing belongs to.
#
# Under test: the top-level `groups` key of `cairn-status.py --json` — the
# hierarchy milestone → phase → issue that the board's grouped render will
# read. Nothing here touches a renderer: this phase promises the board is
# byte for byte what it was, and tests/cairn-board-invariance.bats is where
# that promise is kept.
#
# The one thing these tests exist to pin down is WHERE each fact comes from.
# The label and the key of a milestone group come from the roadmap's own
# `## Milestones` line, never from STATE.md — make_board_fixture makes the
# two disagree on purpose (STATE.md names the ARCHIVED cycle), so a group
# model reading the wrong source announces a dead milestone and these tests
# go red.
#
# Assertion style note (same as cairn-status.bats): a failing `[[ ]]` or
# `! cmd` mid-test does NOT fail a bats test on this bash, so every check
# lands on a plain `[ ]` over a run-captured value.

load 'helpers'

STATUS_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh"
CAIRN_STATUS_PY="$CAIRN_SCRIPTS_DIR/cairn-status.py"

# Load cairn-status.py as a module named cairn_status — not "__main__", so
# its own guard never fires — for the one assertion below that has to read a
# roadmap fact the --json surface deliberately does not expose. Same snippet
# as tests/cairn-corroboration.bats.
PY_LOAD="
import importlib.util
spec = importlib.util.spec_from_file_location('cairn_status', '$CAIRN_STATUS_PY')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)
"

setup() {
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
  # Two populations make_board_fixture deliberately does NOT carry, added
  # here and not there: every issue in that fixture is rendered into the
  # seven committed reference boards, so adding these two upstream would
  # force a regeneration of all of them for the benefit of one test file.
  # Added here they change nothing outside this file.
  #
  # Both take priority 4 — bd's lowest, and the highest it accepts (0-4).
  # fetch_lanes sorts by (priority, id), so they land after the fixture's
  # own READY issues (0, 1, 2) and the id breaks their tie in a fixed
  # order: the bucket assertions below compare exact lists, in lane order.
  #
  #   brd-101: TWO phase labels, so the "smallest phase it names" rule is
  #            exercised rather than presumed.
  #   brd-102: a label naming phase 1, which belongs to the ARCHIVED v1.0
  #            and is therefore claimed by no emitted group. It must stay
  #            visible in the unphased group, never vanish (T-20-06).
  bd create "Span two phases at once" --id brd-101 -t task -p 4 \
    -l phase-3,phase-4 --silent >/dev/null
  bd create "Belong to an archived milestone" --id brd-102 -t task -p 4 \
    -l phase-1 --silent >/dev/null
}

# Render the fixture as JSON into $BOARD_JSON. Kept as a file rather than a
# variable because every assertion below pipes it through jq more than once,
# and re-rendering per query would multiply this file's runtime by its
# assertion count (each render rebuilds nothing, but each bd query costs).
render_json() {
  BOARD_JSON="$BATS_TEST_TMPDIR/board.json"
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" > "$BOARD_JSON"
}

# ─── The groups exist, and carry the milestone's phases ──────────────────────

@test "the open milestone group carries its phases, in ascending order" {
  render_json
  run jq -r '[.groups[] | select(.type=="milestone") | .items[].phase]
             | map(tostring) | join(" ")' "$BOARD_JSON"
  [ "$status" -eq 0 ]
  # Phases 3 and 4 are v1.1's in the fixture's `## Progress` table; 1 and 2
  # belong to the archived v1.0 and must not appear anywhere.
  [ "$output" = "3 4" ]
}

@test "a milestone with no progress table still gets its phases from the range" {
  # The `## Progress` table is the EXPLICIT per-phase source, and it is the
  # one the fixture uses. This repository's own ROADMAP has no such table:
  # there, the only thing tying a phase to a milestone is the `Phases A-B`
  # range on the milestone line. Cut the table out and the range has to
  # carry the group alone.
  #
  # Without this test the "read the range" code would be dead in every
  # fixture — the plan's own break for the test above (remove the range
  # reading) does not redden it, because the table already places 3 and 4.
  python3 - <<'PY'
import re, pathlib
p = pathlib.Path(".planning/ROADMAP.md")
p.write_text(re.sub(r"\n## Progress\n.*$", "\n", p.read_text(), flags=re.S))
PY
  run grep -c '^## Progress' .planning/ROADMAP.md
  [ "$output" = "0" ]
  render_json
  run jq -r '[.groups[] | select(.type=="milestone") | .items[].phase]
             | map(tostring) | join(" ")' "$BOARD_JSON"
  [ "$status" -eq 0 ]
  [ "$output" = "3 4" ]
}

# ─── Where the name comes from ───────────────────────────────────────────────

@test "the group key comes from the roadmap, not from STATE.md" {
  render_json
  # The trap, asserted rather than assumed: STATE.md wins for `milestone`,
  # and it names the archived cycle. If this stops being true the test below
  # proves nothing, so it must fail loudly here first.
  run jq -r '.milestone' "$BOARD_JSON"
  [ "$output" = "v1.0" ]

  run jq -r '[.groups[] | select(.type=="milestone") | .key] | join(" ")' \
    "$BOARD_JSON"
  [ "$status" -eq 0 ]
  [ "$output" = "v1.1" ]

  # Compare the SET of group keys, never a substring search over the whole
  # --json: `v1.0` legitimately appears in phases[].milestone (it is phases 1
  # and 2's cell in the progress table), so a raw grep would go red for a
  # reason that has nothing to do with grouping.
  run jq -r '[.groups[].key] | index("v1.0") | tostring' "$BOARD_JSON"
  [ "$output" = "null" ]
}

# ─── Where each issue lands ──────────────────────────────────────────────────

# The issues of one bucket, joined, in the order the model emits them.
bucket_issues() {
  jq -r --argjson phase "$1" \
    '[.groups[].items[] | select(.phase == $phase) | .issues[]] | join(" ")' \
    "$BOARD_JSON"
}

@test "a labeled issue lands in its phase's bucket, in lane order" {
  render_json
  # brd-001 is READY, brd-101 is READY at a lower priority, brd-004 is
  # DOING: one bucket, and the lanes' own order (READY, DOING, BLOCKED)
  # preserved inside it — the model adds no second ordering.
  run bucket_issues 3
  [ "$status" -eq 0 ]
  [ "$output" = "brd-001 brd-101 brd-004" ]

  run bucket_issues 4
  [ "$status" -eq 0 ]
  [ "$output" = "brd-002 brd-005" ]
}

@test "an issue naming two phases lands in the smallest one it names" {
  render_json
  run jq -r '[.groups[].items[] | select(.issues | index("brd-101"))
             | .phase | tostring] | join(" ")' "$BOARD_JSON"
  [ "$status" -eq 0 ]
  # Exactly one bucket, and it is 3 — not 4, and not both.
  [ "$output" = "3" ]
}

@test "unphased work goes to its own group, and that group is last" {
  render_json
  run jq -r '.groups[-1].type' "$BOARD_JSON"
  [ "$output" = "unphased" ]
  run jq -r '.groups[-1].items | length | tostring' "$BOARD_JSON"
  [ "$output" = "1" ]
  run jq -r '.groups[-1].items[0].phase | tostring' "$BOARD_JSON"
  [ "$output" = "null" ]
  # brd-003 carries no phase label at all; brd-102 carries phase-1, which
  # belongs to the archived v1.0 and so is claimed by no emitted group. Both
  # belong here, and neither may disappear.
  run jq -r '.groups[-1].items[0].issues | join(" ")' "$BOARD_JSON"
  [ "$output" = "brd-003 brd-102" ]
}

# ─── Nothing lost, nothing doubled ───────────────────────────────────────────

@test "every open issue appears exactly once across all groups" {
  render_json
  # sort on BOTH sides, never unique: unique on the group side would erase
  # exactly the half of the failure this test exists to catch — an issue
  # placed in two buckets would dedupe away and the test would go green with
  # the duplicate still in the model. If this ever goes red, find the
  # duplication; do not soften the comparison.
  #
  # The parentheses in the second filter are not style:
  # `[.ready[],.doing[],.blocked[]] | .id` is a jq error, because the pipe
  # applies to the whole array rather than to each element.
  local grouped lanes
  grouped="$(jq -c '[.groups[].items[].issues[]] | sort' "$BOARD_JSON")"
  lanes="$(jq -c '[(.ready[],.doing[],.blocked[]) | .id] | sort' "$BOARD_JSON")"
  [ "$grouped" = "$lanes" ]
  # A comparison of two empty lists would pass and prove nothing.
  run jq -r '[.groups[].items[].issues[]] | length | tostring' "$BOARD_JSON"
  [ "$output" = "7" ]
}

# ─── The honest silence ──────────────────────────────────────────────────────
#
# Two roadmap variants, both mutating the TMP repo's own .planning/ROADMAP.md
# that make_board_fixture just wrote. Never tests/fixtures/, which is the
# committed reference the invariance suite compares against and is not a
# fixture anyone may mutate.
#
# Each mutation asserts that it actually happened. A sed (or replace) that
# silently stops matching — because the fixture's roadmap grammar moved
# upstream — would leave the milestone open, and every test below would go
# green while measuring nothing at all.

# Variant A, "no open cycle": the fixture's one open milestone becomes an
# archived one. This is the repository ten minutes after a
# `/cairn:milestone complete` and before anyone opens the next cycle — the
# exact interval in which the defect was measured on 2026-08-03, when the
# board still read `MILESTONE v1.4` with v1.4 already archived.
archive_the_open_milestone() {
  python3 - <<'PY'
import pathlib
p = pathlib.Path(".planning/ROADMAP.md")
text = p.read_text()
after = text.replace("- 🚧 **v1.1 Surface**", "- ✅ **v1.1 Surface**")
assert after != text, "the open-milestone line no longer matches"
p.write_text(after)
PY
  run grep -c '🚧' .planning/ROADMAP.md
  [ "$output" = "0" ]
}

# Variant B, "an open cycle that names no phase": v1.1 is archived as in
# variant A, and a milestone marked open takes its place whose range spans
# phases that exist nowhere. So an open milestone DOES exist, and there must
# still be no milestone group — which is the other half of D-03, and the half
# the empty-bucket boundary invites you to get backwards.
open_a_milestone_with_no_phases() {
  python3 - <<'PY'
import pathlib
p = pathlib.Path(".planning/ROADMAP.md")
text = p.read_text()
after = text.replace(
    "- 🚧 **v1.1 Surface** — Phases 3-4",
    "- ✅ **v1.1 Surface** — Phases 3-4\n"
    "- 🚧 **v9.9 Far Horizon** — Phases 90-99")
assert after != text, "the open-milestone line no longer matches"
p.write_text(after)
PY
  run grep -c '^- 🚧 \*\*v9.9 Far Horizon\*\* — Phases 90-99$' .planning/ROADMAP.md
  [ "$output" = "1" ]
  # Exactly one open marker in the file, and it is the new one.
  run grep -c '🚧' .planning/ROADMAP.md
  [ "$output" = "1" ]
}

# The ids on the lanes, sorted — what every group must still add up to.
assert_nothing_lost() {
  local grouped lanes
  grouped="$(jq -c '[.groups[].items[].issues[]] | sort' "$BOARD_JSON")"
  lanes="$(jq -c '[(.ready[],.doing[],.blocked[]) | .id] | sort' "$BOARD_JSON")"
  [ "$grouped" = "$lanes" ]
  run jq -r '[.groups[].items[].issues[]] | length | tostring' "$BOARD_JSON"
  [ "$output" = "${1:-7}" ]
}

# REWRITTEN 2026-08-06 (Phase 22, CairnGo-uz6). It used to assert that this
# case yields ZERO milestone groups. That was the letter of D-03, and the
# letter turned out to hide a defect: with no group, the board printed
# `(no open work)` while the footer and the PENDING PHASES table, on the same
# screen, counted phases — three surfaces, two answers. What D-03 was really
# protecting is that no group wears the ARCHIVED name, and that is now
# asserted positively below: one group, `key` null, and a label that says in
# words that there is no open cycle.
@test "variant A: no open milestone yields one unnamed group, never the archived name" {
  archive_the_open_milestone
  render_json
  run jq -r '[.groups[] | select(.type=="milestone")] | length | tostring' \
    "$BOARD_JSON"
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]

  # Unnamed is the whole point: falling back on roadmap_milestone(), on
  # data["milestone"], or on "the last milestone in the list" would each put
  # a key here.
  run jq -r '.groups[0].key | tostring' "$BOARD_JSON"
  [ "$output" = "null" ]
  run jq -r '.groups[0].label' "$BOARD_JSON"
  [ "$output" = "No open milestone" ]

  # PENDING phases only — the same set PENDING PHASES counts. Phases 1 and 2
  # are complete in this fixture and must not be dragged in: with no cycle to
  # bound the scope, "every phase since the project started" is a list that
  # only grows.
  run jq -r '[.groups[0].items[].phase] | map(tostring) | join(" ")' \
    "$BOARD_JSON"
  [ "$output" = "3 4" ]
}

@test "variant A: no group wears the archived cycle's name, and the work stays" {
  local archived_key="v1.1" archived_label="v1.1 Surface" older_key="v1.0"
  archive_the_open_milestone
  render_json

  # Compare extracted SETS, never a substring search over the whole --json:
  # both v1.0 and v1.1 legitimately appear in phases[].milestone, straight
  # from the progress table, so a raw grep would go red for a reason that has
  # nothing to do with grouping.
  local names
  names="$(jq -c '[.groups[].key] + [.groups[].label]' "$BOARD_JSON")"
  run jq -r --arg t "$archived_key" 'index($t) | tostring' <<<"$names"
  [ "$output" = "null" ]
  run jq -r --arg t "$archived_label" 'index($t) | tostring' <<<"$names"
  [ "$output" = "null" ]
  # Nor the cycle before it, which is the one STATE.md still points at.
  run jq -r --arg t "$older_key" 'index($t) | tostring' <<<"$names"
  [ "$output" = "null" ]

  # And the work did not go silent with the group. Two groups since Phase 22:
  # the unnamed one carrying the pending phases, then the unphased one
  # carrying work no phase claims. Naming EITHER after the last known cycle
  # "for context" is the same lie in a friendlier voice, so both labels are
  # pinned — and pinning them together is what keeps the two similar strings
  # from being confused for each other.
  run jq -r '[.groups[].type] | join(" ")' "$BOARD_JSON"
  [ "$output" = "milestone unphased" ]
  run jq -r '[.groups[].label] | join("|")' "$BOARD_JSON"
  [ "$output" = "No open milestone|No milestone" ]
  assert_nothing_lost 7
}

# The two labels above are deliberately close and can share one screen, so
# this test exercises them TOGETHER and says what each one means: the first
# is "the roadmap declares no open cycle", the second is "this issue names no
# phase any emitted group claims". brd-102 carries `phase-1`, which is
# complete here and therefore claimed by no bucket — it is the issue that
# proves the second group is still doing its own job.
@test "variant A: a phase-labelled issue lands on its phase, an unclaimed one stays loose" {
  archive_the_open_milestone
  render_json

  # brd-001 carries phase-3, which IS a pending phase and now has a bucket.
  # Before Phase 22 it fell through to the unphased group with its label
  # ignored — the second symptom of CairnGo-uz6. brd-101 lands here too, and
  # that is the smallest-phase rule working inside the unnamed group exactly
  # as it works inside a named one: it carries phase-3 AND phase-4.
  run jq -r '.groups[0].items[] | select(.phase==3) | .issues | join(" ")' \
    "$BOARD_JSON"
  [ "$output" = "brd-001 brd-101 brd-004" ]

  # brd-102 names phase 1 (complete, claimed by nobody) and brd-003 names no
  # phase at all: both stay visible, in the loose group, never dropped.
  run jq -r '.groups[1].items[0].issues | join(" ")' "$BOARD_JSON"
  [ "$output" = "brd-003 brd-102" ]
}

@test "variant B: an open milestone naming no existing phase is not a group" {
  open_a_milestone_with_no_phases

  # The variant is really a variant: the parser sees exactly one OPEN
  # milestone. Without this, variant B silently degenerates into variant A
  # and the emptiness it proves is the one test 6 already proved. --json
  # never exposes the roadmap's open marker (`.milestone` comes from
  # STATE.md, which names v1.0 here), so this reads the function directly.
  run python3 -c "$PY_LOAD
import pathlib
print(' '.join(m['key'] for m in cs.roadmap_milestones(pathlib.Path('.planning'))
                if m['open']))"
  [ "$status" -eq 0 ]
  [ "$output" = "v9.9" ]

  render_json
  # An open milestone whose every phase is imaginary claims no bucket, and a
  # group with no buckets is not emitted. Emitting it with `items: []` is the
  # backwards reading of D-03 and this is where it goes red.
  run jq -r '[.groups[] | select(.type=="milestone")] | length | tostring' \
    "$BOARD_JSON"
  [ "$output" = "0" ]
  # Nor may the phantom key leak in under any group.
  run jq -r '[.groups[].key] | index("v9.9") | tostring' "$BOARD_JSON"
  [ "$output" = "null" ]
  # Phases 90-99 do not exist: inventing a bucket out of a range would show
  # up here as a group with buckets and no issues.
  run jq -r '[.groups[].items[].phase] | map(tostring) | join(" ")' \
    "$BOARD_JSON"
  [ "$output" = "null" ]

  run jq -r '[.groups[].type] | join(" ")' "$BOARD_JSON"
  [ "$output" = "unphased" ]
  assert_nothing_lost 7
}

# ─── Not inheriting the confusion between the live cycle and an archived one ──

@test "an archived-cycle issue with a discovered-from edge neither groups nor vanishes" {
  # Measured 2026-08-03 in this repository: phase 26 renders as blocked by
  # phase 9, a cycle archived two milestones back, because dep_target_ids()
  # counts every edge without reading its type — so a `discovered-from` edge,
  # which /cairn:quick documents as provenance and explicitly not as a block,
  # counts as a block — and because the pending filter tests against a
  # completed-phase set an archived phase is never part of. That is FIX-04,
  # phase 25's repair; this phase does not fix it. What this test proves is
  # that the group model does not INHERIT it.
  render_json
  local before
  before="$(jq -c '[.groups[] | select(.type=="milestone") | .key]' \
    "$BOARD_JSON")"
  [ "$before" = '["v1.1"]' ]

  # phase-9 exists in no roadmap here — an archived cycle's phase, whose
  # label outlived the cycle in bd. The edge points at brd-001, which lives
  # in the phase-3 bucket of the one emitted group.
  bd create "Filed while executing an archived phase" --id brd-103 -t task \
    -p 4 -l phase-9 --deps "discovered-from:brd-001" --silent >/dev/null
  render_json

  # (a) exactly once in the whole model, and in the unphased group. Placing
  # by edge instead of by label would walk the provenance INTO the phase-3
  # bucket and this count would still be 1 — so the second assertion, the
  # group it landed in, is the one that catches it.
  run jq -r '[.groups[].items[].issues[] | select(. == "brd-103")]
             | length | tostring' "$BOARD_JSON"
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
  run jq -r '[.groups[] | select(.items[].issues | index("brd-103"))
             | .type] | join(" ")' "$BOARD_JSON"
  [ "$output" = "unphased" ]

  # (b) the milestone groups did not move: not created, not renamed, not
  # dropped. Creating a group per label found, without confronting the
  # roadmap's open milestones, births a phantom `phase-9` group right here.
  run jq -c '[.groups[] | select(.type=="milestone") | .key]' "$BOARD_JSON"
  [ "$output" = "$before" ]

  # (c) and no group is named after anything the stray label dragged in:
  # the full key and label sets, exhaustively.
  run jq -r '[.groups[].key] | join(" ")' "$BOARD_JSON"
  [ "$output" = "v1.1 unphased" ]
  # Joined on a pipe, not a space: both labels contain spaces, and a space
  # join would let "v1.1 Surface" / "No milestone" and a single group called
  # "v1.1 Surface No milestone" produce the same string.
  run jq -r '[.groups[].label] | join("|")' "$BOARD_JSON"
  [ "$output" = "v1.1 Surface|No milestone" ]

  # Nothing lost either: the new issue is the eighth.
  assert_nothing_lost 8
}

# ─── The contract, pinned mechanically ───────────────────────────────────────
#
# "The existing suite still passes" does not prove that no key changed name,
# type or meaning: the 83 tests read the keys they each need, never the SET of
# them, and a new key nested in the wrong place passes every one. The three
# tests below are the mechanical version of that claim.
#
# The literals were measured against this code. If one of them goes red, it is
# a contract change asking to be discussed, not a test asking to be updated.

@test "the --json top-level key set is the old one plus groups, exactly" {
  render_json
  run jq -r 'keys_unsorted | sort | join(",")' "$BOARD_JSON"
  [ "$status" -eq 0 ]
  # The 14 pre-existing keys plus `groups` (20-02), `open_milestones`
  # (22-03, BOARD-04) and `landing` (30-01, PR-01 — which branch "delivered"
  # means here, where that answer came from, and whether it could be produced
  # at all). tests/cairn-status.bats pins this same set against a different
  # fixture (make_gsd_fixture + a status fixture); the two literals must agree,
  # and a key that appears under only one fixture would show up as exactly that
  # disagreement.
  [ "$output" = "blocked,counts,doing,groups,landing,lease,milestone,next,next_commands,note,open_milestones,parallelism,phase,phases,ready,stale_complete,sync" ]
}

@test "every phases[] row carries exactly the 24 keys it always did" {
  render_json

  # The aggregation is the point, so the premise gets asserted rather than
  # assumed: .phases[0] here is phase 1, complete, from the ARCHIVED v1.0.
  # The most plausible way to violate D-02 is not adding a key to every
  # phase — it is adding one only to the phases inside an open milestone
  # group, which would leave this row untouched. A single-row sample would
  # then be green with the decision violated.
  run jq -r '.phases[0] | "\(.number) \(.complete)"' "$BOARD_JSON"
  [ "$output" = "1 true" ]

  run jq -r '[.phases[] | keys_unsorted] | add | unique | join(",")' \
    "$BOARD_JSON"
  [ "$status" -eq 0 ]
  # `add | unique` comes out sorted, so the literal is the sorted set. Any
  # group structure nested inside a phases[] row — in one row is enough —
  # adds a key here and this goes red. That is the only mechanical proof of
  # "a new key BESIDE the existing ones, never inside them" (D-02).
  #
  # EDITED by plan 29-05, deliberately and once: `tracker` joins the set as
  # the 23rd key — the phase half of AUTO-03, read from the roadmap's
  # optional `**Tracker:**` line. The literal is edited rather than loosened
  # to a subset, because a subset assertion is exactly the one that stops
  # catching a key renamed out from under it, and catching that is why this
  # test exists. Intent unchanged: this set is a CONTRACT, and a red here is
  # a contract change asking to be discussed.
  #
  # EDITED AGAIN by plan 30-01, deliberately and once: `landed` joins the set
  # as the 24th key — did this phase's work enter the control branch, answered
  # by cairn-land.py from the local git and carried here for every phase, with
  # `status: "unknown"` and a named `reason` when it could not be answered.
  # Additive for ALL rows exactly like `tracker`, which is what the
  # `[.phases[] | keys_unsorted] | add | unique` aggregation above proves and a
  # single-row sample would not.
  [ "$output" = "blocked_by,complete,completed_on,conflicts,corroboration,depends_on,dir,disk_state,evidence,issues_done,issues_total,landed,milestone,needs_doctor,next_command,number,plans_done,plans_total,purpose,requirements,research_done,title,tracker,verify_status" ]
}

@test "disk_state still carries only its four values" {
  render_json
  run jq -r '[.phases[].disk_state] - ["none","planned","executed","verified"]
             | join(",")' "$BOARD_JSON"
  [ "$status" -eq 0 ]
  # Be honest about how little this proves. Measured: this fixture yields
  # only `none`, and this repository yields `executed,none` — a subset
  # assertion over four values passes trivially until something produces a
  # fifth, and the fixture never will. It is NOT what keeps
  # phase_next_command()'s bare dict lookup from raising KeyError; scope is,
  # because nothing in this phase writes disk_state. Cheap tripwire against
  # a future change, and nothing more.
  [ "$output" = "" ]
}
