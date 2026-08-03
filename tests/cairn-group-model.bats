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
