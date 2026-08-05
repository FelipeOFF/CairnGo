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
# ─────────────────────────────────────────────────────────────────────────────
# THE ABSENCE OF NETWORK: what is MEASURED and what is ASSUMED
#
# "The board makes no network call" is worth nothing as a sentence. It is
# worth something only if something goes red when somebody makes one. This
# file arms two independent tripwires, because ONE of them does not cover the
# case that will actually happen.
#
# MEASURED (reproduced offline by the layer-2 liveness test below): with the
# socket tripwire installed, `subprocess.run(["curl", ...])` inside the SAME
# process raises nothing at all. A child process does not inherit a patched
# `socket` module. The plan measured the same thing against the real internet
# and got HTTP 200 back; the version here proves the identical blind spot
# without needing a network. cairn-status.py shells out in four places, so a
# live tracker fetch written later as a subprocess — a `curl`, a new client, a
# `bd` that learned to talk to a server — would sail straight past a
# socket-only test.
#
#   Layer 1, inside the process: a `sitecustomize` that raises on
#     socket.connect / connect_ex. Catches urllib, http.client, raw sockets.
#     Its liveness control: a one-line python that opens a connection under
#     the same PYTHONPATH and MUST fail.
#   Layer 2, outside the process: a PATH holding ONLY bd / git / python3 / jq
#     plus a trapped curl and wget that log their own argv and exit 1. The
#     assertion is that the log stays empty. Its liveness control: a one-line
#     python that runs curl under the same PATH and MUST show up in the log —
#     the exact path layer 1 is blind to.
#   Layer 3, before either runs: a structural inventory of every
#     subprocess.run in cairn-status.py, asserting each one invokes an
#     allowlisted binary. This is the layer that catches a new call site the
#     day it is WRITTEN, months before anyone renders a board with it. Its
#     liveness control: a synthetic source carrying a curl call, which the
#     same inventory MUST reject.
#
# ASSUMED, and out of reach of all three: what `bd` does inside its own
# process. It is a third-party Go binary sitting on the allowlist. What is
# proved here is that THIS script opens no socket and invokes no network tool.
# What is not proved is bd own behaviour, and no test in this file pretends
# otherwise.
# ─────────────────────────────────────────────────────────────────────────────
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

# Append a `## Detalhe das fases` block giving phase N an external tracker.
# The label is `Tracker`, not `Card`: `**Card:**` already means the phase
# purpose in this roadmap grammar (tests/cairn-phase-card.bats owns that one).
add_phase_tracker() {
  cat >> .planning/ROADMAP.md <<EOF

## Detalhe das fases

### Phase $1: detail block

**Tracker:** $2

---
EOF
}

# Build both runtime tripwires under BATS_TEST_TMPDIR and set TRIP_SITE
# (PYTHONPATH for layer 1), TRIP_BIN (PATH for layer 2) and TRIP_LOG (where a
# trapped network tool records that it was called).
arm_tripwires() {
  TRIP_SITE="$BATS_TEST_TMPDIR/tripwire-site"
  TRIP_BIN="$BATS_TEST_TMPDIR/tripwire-bin"
  TRIP_LOG="$BATS_TEST_TMPDIR/network-tools.log"
  mkdir -p "$TRIP_SITE" "$TRIP_BIN"
  : > "$TRIP_LOG"

  cat > "$TRIP_SITE/sitecustomize.py" <<'PY'
"""Layer 1: no socket leaves this interpreter.

Imported automatically by `site` for every python started with this
directory on PYTHONPATH, which is how it reaches cairn-status.py AND the
cairn-lease.py / cairn-journal.py children it starts with sys.executable.
"""
import socket


def _refuse(self, address, *rest):
    raise RuntimeError(
        "CAIRN-NET-TRIPWIRE: this process tried to open a socket to %r"
        % (address,))


socket.socket.connect = _refuse
socket.socket.connect_ex = _refuse
PY

  # The REAL interpreter, not whatever `command -v python3` resolves to.
  # MEASURED on this machine: `python3` is an asdf shim written in bash, so a
  # PATH holding only the allowlist made it exit 127 with `env: bash: No such
  # file or directory` — the allowlist was accidentally testing the version
  # manager instead of the renderer.
  local real
  real="$(python3 -c 'import sys; print(sys.executable)')"
  printf '#!/bin/sh\nexec %s "$@"\n' "$real" > "$TRIP_BIN/python3"
  chmod +x "$TRIP_BIN/python3"

  local tool
  for tool in bd git jq; do
    real="$(command -v "$tool" || true)"
    [ -n "$real" ] || continue
    printf '#!/bin/sh\nexec %s "$@"\n' "$real" > "$TRIP_BIN/$tool"
    chmod +x "$TRIP_BIN/$tool"
  done

  # Present and trapped, not merely absent: an absent binary proves only that
  # the call failed, a trapped one records that the call was ATTEMPTED and by
  # whom. Exit 1 so a caller that ignores the log still sees a failure.
  for tool in curl wget; do
    cat > "$TRIP_BIN/$tool" <<'SH'
#!/bin/sh
printf '%s %s\n' "$0" "$*" >> "$CAIRN_NET_LOG"
exit 1
SH
    chmod +x "$TRIP_BIN/$tool"
  done
}

# Write layer 3 — the structural inventory — and set INVENTORY to its path.
write_inventory() {
  INVENTORY="$BATS_TEST_TMPDIR/subprocess-inventory.py"
  cat > "$INVENTORY" <<'PY'
"""Layer 3: every subprocess.run in a script invokes an allowlisted binary.

A runtime tripwire only catches a path that actually executes. This one reads
the source, so it goes red the day a network tool is WRITTEN into the file,
which is long before anybody renders a board with it.
"""
import ast
import sys

ALLOWED_BINARIES = {"bd", "git", "jq"}
path = sys.argv[1]
tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)


def head(node, assigns, depth=0):
    """First element of an argv expression, resolved through one list concat
    and through a local name bound to a list literal."""
    if depth > 4:
        return None
    if isinstance(node, ast.List) and node.elts:
        return node.elts[0]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return head(node.left, assigns, depth + 1)
    if isinstance(node, ast.Name) and node.id in assigns:
        return head(assigns[node.id], assigns, depth + 1)
    return None


def describe(h):
    if isinstance(h, ast.Constant) and isinstance(h.value, str):
        return h.value
    # sys.executable is this very interpreter, already inside layer 1, and it
    # is never resolved through PATH.
    if isinstance(h, ast.Attribute) and h.attr == "executable":
        return "<sys.executable>"
    return None


def scan(scope, assigns):
    """subprocess.run sites in ONE scope, resolved against that scope only.

    MEASURED, and the reason this is per-function: resolving names
    module-wide collapsed two different `cmd` variables into one and reported
    the journal call as `bd`. A green that names the wrong binary is worse
    than no inventory at all.
    """
    out = []
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    assigns[t.id] = node.value
    for node in ast.walk(scope):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr == "run"
                and isinstance(f.value, ast.Name)
                and f.value.id == "subprocess"):
            continue
        argv = node.args[0] if node.args else None
        name = describe(head(argv, assigns)) if argv is not None else None
        out.append((node.lineno, name))
    return out


module_assigns = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                module_assigns[t.id] = node.value

sites = []
for fn in ast.walk(tree):
    if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        sites += scan(fn, dict(module_assigns))

assert sites, "no subprocess.run found - the inventory read the wrong file"
for lineno, name in sorted(sites):
    print("line %-5d %s" % (lineno, name))
bad = [(ln, nm) for ln, nm in sites
       if nm is None
       or (nm != "<sys.executable>" and nm not in ALLOWED_BINARIES)]
assert not bad, "subprocess.run invoking something off the allowlist: %r" % bad
print("ok: %d subprocess.run sites, all on the allowlist" % len(sites))
PY
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

# REWRITTEN 2026-08-05 (Phase 21). The old claim was "the line keeps its
# width — the suffix eats padding", which only makes sense inside a cell of
# fixed width. The grouped row has no padding to eat: the card makes the row
# genuinely longer, and the property that matters is the one underneath —
# a suffix that display_width() does not count pushes the row past --width.
# That is asserted directly now, over the row this test always owned.
@test "the marked card lengthens its row and never passes --width" {
  local before="$BATS_TEST_TMPDIR/before.txt"
  local after="$BATS_TEST_TMPDIR/after.txt"
  bash "$STATUS_SH" --width 100 --color=never > "$before"
  mark_ref brd-001 jira-DTP-142
  bash "$STATUS_SH" --width 100 --color=never > "$after"
  run python3 -c '
import sys, unicodedata
def cw(ch):
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
def row(path):
    for line in open(path, encoding="utf-8"):
        if line.startswith("      ") and "brd-001" in line:
            return line.rstrip("\n")
    raise AssertionError("brd-001 is not a task row in %s" % path)
b, a = row(sys.argv[1]), row(sys.argv[2])
assert "DTP-142" not in b, "the key was already there before the mark: %r" % b
assert "⧉ DTP-142" in a, "the mark did not render: %r" % a
assert sum(cw(c) for c in a) <= 100, "the row ran past --width 100: %r" % a
# The key is what grew the row, and only the key.
assert a.replace("  ⧉ DTP-142", "") == b, (b, a)
print("ok %d -> %d" % (sum(cw(c) for c in b), sum(cw(c) for c in a)))
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
# REWRITTEN 2026-08-05 (Phase 21). Two things changed here.
#
# 1. The board region is no longer only grid lines. At and above
#    STACK_BELOW it is the grouped list, whose task rows start with six
#    spaces; below it the stacked and raw degrades are still alive (plan
#    21-02 collapses them), so the grid characters stay in the filter.
# 2. The old filter was `line[:1] not in "┌│└+|"`, and in Python an EMPTY
#    string is a substring of every string — so a blank line counted as a
#    board line. MEASURED: with the grid gone, that alone kept this test
#    green at every width above 64 while it inspected nothing at all. The
#    filter now rejects the empty line explicitly.
def is_board_line(line):
    if not line:
        return False
    return line[0] in "┌│└+|" or line.startswith("      ")
seen = 0
for i, line in enumerate(sys.stdin.read().splitlines(), 1):
    if not is_board_line(line):
        continue
    seen += 1
    got = sum(cw(c) for c in line)
    assert got <= limit, "board line %d is %d cells wide at --width %d: %r" % (
        i, got, limit, line)
# The exemption `limit < 64` that stood here until 2026-08-05 is GONE with
# the degrades plan 21-02 removed: one list serves every width, so a board
# line exists at every width and a filter that matched nothing is always a
# bug in the filter.
assert seen > 0, "no board line found at --width %d" % limit
print("ok %d board lines" % seen)
' "$w" <<<"$output"
    [ "$status" -eq 0 ]
  done
}

# REWRITTEN 2026-08-05 (Phase 21), and this one REPLACES a property with a
# STRONGER one rather than restating it — so an audit reading this later does
# not count it as coverage lost.
#
# It used to be "when the lane is too narrow the card falls out and the title
# stays", and it pinned make_cell()'s precedence: the tracker key was shed
# first, then the rest, the title always winning. That precedence existed
# because the lane cell was a fixed width and something HAD to go. A row that
# wraps has nothing to rank, so the rule it enforced is now: nothing goes.
# The same render still carries the proof that the feature is alive (the key
# renders), and now also that the row it competed with keeps everything.
@test "no suffix falls out to make room: the row wraps instead" {
  mark_ref brd-001 jira-DTP-142
  mark_ref brd-004 jira-DTP-142
  run bash "$STATUS_SH" --width 100 --color=never
  [ "$status" -eq 0 ]

  run python3 -c '
import sys
rows = {}
for line in sys.stdin.read().splitlines():
    if not line.startswith("      "):
        continue
    for iid in ("brd-001", "brd-004"):
        # startswith on the stripped row, not `in`: a blocked row names
        # brd-001 as its blocker, and a substring match would read that row
        # as the row OF brd-001 (no apostrophe here on purpose — this block
        # is inside a single-quoted bash argument).
        body = line.strip()
        if body[2:].startswith(iid):
            rows[iid] = body
ready, doing = rows.get("brd-001"), rows.get("brd-004")
assert ready and doing, "both rows must be on the board: %r" % rows
assert "⧉ DTP-142" in ready, "the plain row lost its key: %r" % ready
assert "⧉ DTP-142" in doing, "the key fell out of the busy row: %r" % doing
assert "cairn-tests" in doing, "the assignee was dropped: %r" % doing
assert "Hold the lease while executing" in doing, (
    "the title was cut to fit a suffix: %r" % doing)
print("ok")
' <<<"$output"
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]
}

# ─── The other half of AUTO-03: a card attached to a PHASE ───────────────────

@test "a phase with a Tracker line shows its key beside the title" {
  add_phase_tracker 3 jira-DTP-777
  run bash "$STATUS_SH" --width 140 --color=never
  [ "$status" -eq 0 ]
  # Breaks by: not reading the label at all, or reading it in a second pass
  # that never runs.
  assert_output_has "⧉ DTP-777"
}

@test "a phase without a Tracker line changes nothing on the board" {
  local before="$BATS_TEST_TMPDIR/before.txt"
  local after="$BATS_TEST_TMPDIR/after.txt"
  bash "$STATUS_SH" --width 140 --color=never > "$before"
  add_phase_tracker 3 jira-DTP-777
  bash "$STATUS_SH" --width 140 --color=never > "$after"

  # Exactly one line moved, and it is phase 3 own table row. Phase 4 has no
  # Tracker line, and neither the header, the column widths, the footer nor
  # the PURPOSE list may shift because phase 3 grew one.
  run python3 -c '
import sys
b = open(sys.argv[1], encoding="utf-8").read().splitlines()
a = open(sys.argv[2], encoding="utf-8").read().splitlines()
assert len(b) == len(a), "the render gained or lost lines: %d -> %d" % (
    len(b), len(a))
moved = [i for i, (x, y) in enumerate(zip(b, a), 1) if x != y]
assert moved, "the Tracker label rendered nothing at all"
assert len(moved) == 1, "more than the phase 3 row moved: lines %r" % moved
row = a[moved[0] - 1]
assert row.lstrip().startswith("3 "), "the line that moved is not the phase 3 row: %r" % row
assert "⧉ DTP-777" in row, "phase 3 row moved without gaining the key: %r" % row
print("ok")
' "$before" "$after"
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]
}

@test "--json carries the phase tracker raw, prefix and all" {
  add_phase_tracker 3 jira-DTP-777
  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.phases[] | select(.number==3) | .tracker' \
    "jira-DTP-777"
  # And a phase that has no Tracker line reports null, on every row — the
  # key is additive for ALL phases, not only the ones that carry a value.
  assert_json_eq "$output" '.phases[] | select(.number==4) | .tracker' "null"
  assert_json_eq "$output" \
    '[.phases[] | has("tracker")] | unique | join(",")' "true"
}

# ─── The absence of network, proved at both boundaries ───────────────────────

@test "the whole render runs under both tripwires and still prints the card" {
  mark_ref brd-001 jira-DTP-142
  add_phase_tracker 3 jira-DTP-777
  arm_tripwires

  # `python3` deliberately unqualified: it has to resolve out of the
  # allowlisted PATH, or the layer being tested is not the one in force.
  run env PATH="$TRIP_BIN" PYTHONPATH="$TRIP_SITE" CAIRN_NET_LOG="$TRIP_LOG" \
    python3 "$STATUS_PY" --width 140 --color=never
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]

  # It rendered the feature, not a degraded board that happens to exit 0.
  assert_output_has "⧉ DTP-142"
  assert_output_has "⧉ DTP-777"

  # Layer 2 assertion: no trapped network tool was invoked, by the renderer
  # or by any child it started.
  if [ -s "$TRIP_LOG" ]; then
    echo "a network tool was invoked during the render:" >&2
    cat "$TRIP_LOG" >&2
    return 1
  fi
}

@test "layer 1 is alive: an in-process socket raises under the same PYTHONPATH" {
  arm_tripwires
  # 127.0.0.1:9 (discard) — the tripwire fires on connect(), before anything
  # is sent, so this needs no network and no listener.
  run env PATH="$TRIP_BIN" PYTHONPATH="$TRIP_SITE" CAIRN_NET_LOG="$TRIP_LOG" \
    python3 -c 'import socket; socket.create_connection(("127.0.0.1", 9))'
  [ "$status" -ne 0 ]
  # Named, not merely nonzero: a python that failed to start also exits
  # nonzero, and would leave the test green with the tripwire never loaded.
  assert_output_has "CAIRN-NET-TRIPWIRE"
}

@test "layer 2 is alive exactly where layer 1 is blind" {
  arm_tripwires
  # THE MEASUREMENT, reproduced offline. Both layers armed. curl is started
  # as a CHILD, so it never sees the patched socket module: layer 1 raises
  # nothing and the call succeeds in reaching the tool. What catches it is
  # layer 2, and the proof is the log. Without this control there is no
  # evidence that layer 2 sees the one path a live fetch would take.
  run env PATH="$TRIP_BIN" PYTHONPATH="$TRIP_SITE" CAIRN_NET_LOG="$TRIP_LOG" \
    python3 -c 'import subprocess
p = subprocess.run(["curl", "-s", "https://example.com"])
print("curl was reached, layer 1 raised nothing, rc=%d" % p.returncode)'
  [ "$status" -eq 0 ]
  assert_output_has "layer 1 raised nothing"
  assert_output_lacks "CAIRN-NET-TRIPWIRE"

  if [ ! -s "$TRIP_LOG" ]; then
    echo "layer 2 did not record the curl call — the allowlisted PATH is" \
      "not in force, and the previous test is the only thing standing" >&2
    return 1
  fi
  grep -qF "https://example.com" "$TRIP_LOG"
}

@test "every subprocess.run in the renderer invokes an allowlisted binary" {
  write_inventory
  run python3 "$INVENTORY" "$STATUS_PY"
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
  fi
  [ "$status" -eq 0 ]
  # MEASURED at the time of writing: four sites — two `bd`, two
  # `sys.executable` (cairn-lease.py, cairn-journal.py). The count is
  # asserted so that a site DELETED by a refactor is noticed too; a
  # legitimate fifth site updates this number and stays on the allowlist.
  assert_output_has "ok: 4 subprocess.run sites"
}

@test "layer 3 is alive: a synthetic curl call site is rejected" {
  write_inventory
  # What a live fetch would plausibly look like when somebody adds it later.
  cat > "$BATS_TEST_TMPDIR/fake-fetch.py" <<'PY'
import subprocess


def fetch_card(key):
    cmd = ["curl", "-s", "https://jira.example.com/rest/api/2/issue/" + key]
    return subprocess.run(cmd, capture_output=True)
PY
  run python3 "$INVENTORY" "$BATS_TEST_TMPDIR/fake-fetch.py"
  [ "$status" -ne 0 ]
  assert_output_has "off the allowlist"
  assert_output_has "curl"
}

@test "a narrow panel drops the phase key and gives the title its column" {
  # MEASURED on this fixture: the `phase` column is 8 cells at --width 100
  # and ~30 at 110 — below TRACKER_TITLE_FLOOR + the key, so the key goes
  # and the title takes the whole column back. At 140 it is back. Without
  # the second half, this test would pass against a label that never renders.
  add_phase_tracker 3 jira-DTP-777
  run bash "$STATUS_SH" --width 110 --color=never
  [ "$status" -eq 0 ]
  assert_output_lacks "DTP-777"
  assert_output_has "Phase model"

  run bash "$STATUS_SH" --width 140 --color=never
  [ "$status" -eq 0 ]
  assert_output_has "⧉ DTP-777"
}
