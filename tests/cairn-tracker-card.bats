#!/usr/bin/env bats
# cairn-tracker-card.bats — the external tracker card reaches the board from
# data that is ALREADY local, and the board that shows it never touches the
# network.
#
# Under test: `external_ref` (bd's own field, written today by
# cairn-doctor.py --link-refs) carried through trim_issue() into `--json` and
# through make_cell() into the human render, plus the roadmap's optional
# `**Tracker:**` line per phase.
#
# The rule this whole file exists to hold: the suffix is strictly conditional
# on the datum. An issue with no `external_ref` renders the bytes it always
# rendered — which is why tests/cairn-board-invariance.bats, whose fixture
# carries no ref at all, stays green beside this one. That suite is the proof
# for the seven committed reference renders; this one is the proof for the
# feature.
#
# Assertion style note (same as cairn-status.bats and
# cairn-board-invariance.bats): a failing `[[ ]]` or `! cmd` mid-test does NOT
# fail a bats test on this bash, so every check lands on a plain `[ ]` over a
# run-captured `$status`, or on an explicit `if ... return 1` block.

load 'helpers'

STATUS_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh"
STATUS_PY="$CAIRN_SCRIPTS_DIR/cairn-status.py"

setup() {
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
}

# Attach an external ref to a fixture issue — the same `bd update
# --external-ref` call cairn-doctor.py --link-refs already makes in
# production. Nothing here invents a storage location for the link.
mark_ref() {
  bd update "$1" --external-ref "$2" >/dev/null
}

assert_output_has() {
  if ! printf '%s\n' "$output" | grep -qF -- "$1"; then
    echo "expected the render to contain '$1', it does not:" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

assert_output_lacks() {
  if printf '%s\n' "$output" | grep -qF -- "$1"; then
    echo "expected the render NOT to contain '$1', it does:" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}

# ─── The card comes from the local datum ─────────────────────────────────────

@test "an issue with an external_ref shows its tracker key on the board" {
  mark_ref brd-001 jira-DTP-142
  run bash "$STATUS_SH" --width 100 --color=never
  [ "$status" -eq 0 ]
  # Breaks by: dropping the suffix from make_cell(). The most direct test
  # that the feature exists at all.
  assert_output_has "DTP-142"
  assert_output_has "⧉ DTP-142"
}

@test "a bare tracker key is shown exactly as stored" {
  # The second of the two forms the plan names: an external_ref that carries
  # no backend prefix at all is already the human key.
  mark_ref brd-001 DTP-142
  run bash "$STATUS_SH" --width 100 --color=never
  [ "$status" -eq 0 ]
  assert_output_has "⧉ DTP-142"
}

@test "a gh-<number> ref keeps its prefix instead of degrading to a digit" {
  # DELIBERATE DEVIATION from 29-05-PLAN.md, which lists `gh-` among the
  # prefixes stripped unconditionally. MEASURED: cairn-doctor.py --link-refs
  # writes exactly this shape in production, and stripping it would print a
  # bare `42` beside an issue id — a number that identifies nothing. A prefix
  # comes off only when what survives still names the issue.
  mark_ref brd-001 gh-42
  run bash "$STATUS_SH" --width 100 --color=never
  [ "$status" -eq 0 ]
  assert_output_has "⧉ gh-42"
}

@test "the ascii board carries the card with an ascii glyph" {
  mark_ref brd-001 jira-DTP-142
  run bash "$STATUS_SH" --width 100 --ascii --color=never
  [ "$status" -eq 0 ]
  assert_output_has "# DTP-142"
  # Breaks by: leaking U+29C9 into a render that asked for ascii, which is
  # what every other glyph on this board already refuses to do.
  assert_output_lacks "⧉"
}

# ─── No datum, no movement ───────────────────────────────────────────────────

@test "every unmarked card renders the bytes it rendered before the mark" {
  # Captured from THIS fixture before the mark, so the comparison is against
  # the render as it actually was — not against a description of it.
  local before="$BATS_TEST_TMPDIR/before.txt"
  local after="$BATS_TEST_TMPDIR/after.txt"
  bash "$STATUS_SH" --width 100 --color=never > "$before"
  mark_ref brd-001 jira-DTP-142
  bash "$STATUS_SH" --width 100 --color=never > "$after"

  # The mark IS visible: without this, everything below passes trivially on a
  # feature that never rendered anything.
  run diff -q "$before" "$after"
  [ "$status" -ne 0 ]

  # And it is visible in exactly one place. Every line that is not the marked
  # issue's is byte-identical. Breaks by: a suffix that appears with empty
  # data, which would move a line of every board of every user.
  grep -vF brd-001 "$before" > "$before.rest"
  grep -vF brd-001 "$after" > "$after.rest"
  run diff -u "$before.rest" "$after.rest"
  [ "$status" -eq 0 ]
}

@test "the marked card line keeps its width — the suffix eats padding" {
  local before="$BATS_TEST_TMPDIR/before.txt"
  local after="$BATS_TEST_TMPDIR/after.txt"
  bash "$STATUS_SH" --width 100 --color=never > "$before"
  mark_ref brd-001 jira-DTP-142
  bash "$STATUS_SH" --width 100 --color=never > "$after"
  # Character counts of the one changed line, before and after. A suffix that
  # is not counted into display_width() shows up here as a longer line, which
  # is the same defect as a card pushed out of its lane.
  run python3 -c '
import sys
def w(path):
    for line in open(path, encoding="utf-8"):
        if "brd-001" in line:
            return len(line.rstrip("\n"))
    raise AssertionError("brd-001 is not on the board in %s" % path)
b, a = w(sys.argv[1]), w(sys.argv[2])
assert b == a, "line width moved from %d to %d" % (b, a)
print("ok %d" % a)
' "$before" "$after"
  [ "$status" -eq 0 ]
}

# ─── The datum, unrewritten, in --json ───────────────────────────────────────

@test "--json carries the external_ref raw, backend prefix and all" {
  mark_ref brd-001 jira-DTP-142
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  # Breaks by: normalizing on the way out. The board strips the prefix for
  # DISPLAY; the datum a consumer reads is the one bd stored.
  assert_json_eq "$output" \
    '.ready[] | select(.id=="brd-001") | .external_ref' "jira-DTP-142"
}

@test "--json reports null for an issue with no external_ref" {
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  # null, not "" and not a missing key: a consumer distinguishes "no link"
  # from "link is the empty string" without guessing.
  assert_json_eq "$output" \
    '.ready[] | select(.id=="brd-002") | .external_ref' "null"
  assert_json_eq "$output" \
    '[.ready[], .doing[], .blocked[]] | map(has("external_ref")) | unique | join(",")' \
    "true"
}

# ─── Width: the title outranks the card ──────────────────────────────────────

@test "no card is pushed out of its lane, at any width" {
  # A suffix that is not counted into the lane budget pushes the card past
  # the border. Swept rather than sampled: the degrades happen at ~64 and
  # ~40 columns, and a bug that only shows on one side of a boundary is the
  # kind a single width silently misses. All three lanes carry a long ref,
  # because DOING and BLOCKED already have a suffix of their own to compete
  # with and READY does not.
  #
  # Scope note, MEASURED on this fixture before any mark: the footer line
  # (70 cells) and the PENDING PHASES table (85-90 cells) DO run past a
  # narrow --width today, identically with and without a tracker ref. That
  # is a pre-existing defect of other renderers, logged in
  # .planning/phases/29-nothing-mechanical-stays-manual/deferred-items.md
  # and deliberately not fixed here. What this test owns is the lane grid,
  # which is what a card suffix can break — so it asserts over the grid
  # lines only, and says so rather than quietly widening its filter until
  # it passes.
  mark_ref brd-001 jira-DTP-142-A-VERY-LONG-KEY
  mark_ref brd-004 jira-DTP-142-A-VERY-LONG-KEY
  mark_ref brd-005 jira-DTP-142-A-VERY-LONG-KEY
  local w
  for w in 38 40 44 50 58 64 72 80 100 120 200; do
    run bash "$STATUS_SH" --width "$w" --color=never
    [ "$status" -eq 0 ]
    run python3 -c '
import sys, unicodedata
limit = int(sys.argv[1])
def cw(ch):
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
seen = 0
for i, line in enumerate(sys.stdin.read().splitlines(), 1):
    if line[:1] not in "┌│└+|":
        continue
    seen += 1
    got = sum(cw(c) for c in line)
    assert got <= limit, "grid line %d is %d cells wide at --width %d: %r" % (
        i, got, limit, line)
# Below STACK_BELOW the grid does not exist; above it, a filter that matched
# nothing would pass this test forever.
assert limit < 64 or seen > 0, "no grid line found at --width %d" % limit
print("ok %d grid lines" % seen)
' "$w" <<<"$output"
    [ "$status" -eq 0 ]
  done
}

@test "when the lane is too narrow the card falls out and the title stays" {
  # MEASURED, and it is the whole precedence rule in one render at --width
  # 100 (lane inner 30 cells):
  #   brd-001 sits on READY with no suffix of its own — the key fits, and
  #           renders;
  #   brd-004 sits on DOING with `◆ cairn-tests` — both do not fit, so the
  #           key is the one that goes, and the assignee and the title stay.
  # One render carries both the drop and the proof that the feature is alive,
  # so the drop can never be a feature that simply never renders.
  mark_ref brd-001 jira-DTP-142
  mark_ref brd-004 jira-DTP-142
  run bash "$STATUS_SH" --width 100 --color=never
  [ "$status" -eq 0 ]

  # Per CELL, not per line: the three lanes share one row, so a whole-line
  # check would read brd-001's key while asserting about brd-004's card.
  run python3 -c '
import sys
cells = {}
for line in sys.stdin.read().splitlines():
    if line[:1] != "│":
        continue
    for cell in line.strip("│").split("│"):
        for iid in ("brd-001", "brd-004"):
            # startswith, not `in`: BLOCKED renders `⧗ brd-001` as its
            # dependency suffix, and a substring match would read that cell
            # as the card OF brd-001 (no apostrophe here on purpose — this
            # block is inside a single-quoted bash argument).
            if cell.strip().startswith(iid):
                cells[iid] = cell
ready, doing = cells.get("brd-001"), cells.get("brd-004")
assert ready and doing, "both cards must be on the grid: %r" % cells
assert "⧉ DTP-142" in ready, "the unencumbered card lost its key: %r" % ready
assert "⧉" not in doing, "the key did not fall out first: %r" % doing
assert "cairn-tests" in doing, "the assignee was dropped instead: %r" % doing
assert "Hold" in doing, "the title was sacrificed to a suffix: %r" % doing
print("ok")
' <<<"$output"
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]
}
