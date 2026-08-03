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
