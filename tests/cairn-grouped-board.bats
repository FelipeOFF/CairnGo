#!/usr/bin/env bats
# cairn-grouped-board.bats — the board situates instead of only listing.
#
# Under test: the grouped render that replaces the three-lane kanban on the
# human path (Phase 21). Four properties, one per requirement:
#
#   BOARD-06  the hierarchy on screen is open milestone → phase → task, with
#             work no milestone claims last
#   BOARD-02  every stage symbol is ONE cell, asserted through
#             unicodedata.east_asian_width and never through how it looks,
#             with a one-character ASCII fallback under --ascii
#   BOARD-03  no task title is ever truncated: a row too long for the width
#             wraps into a continuation aligned to the title column
#   BOARD-05  a blocked row names EVERY blocker on the row itself
#
# tests/cairn-board-invariance.bats holds the other half of the proof: the
# committed byte-for-byte references. This file states the properties; that
# file states the bytes.
#
# Assertion style note (same as cairn-status.bats): a failing `[[ ]]` or
# `! cmd` mid-test does NOT fail a bats test on this bash, so every check
# lands on a plain `[ ]` over a run-captured value, or inside a python3
# snippet whose own exit code is what `run` captures.

load 'helpers'

STATUS_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh"
CAIRN_STATUS_PY="$CAIRN_SCRIPTS_DIR/cairn-status.py"

# Load cairn-status.py as a module named cairn_status — not "__main__", so
# its own guard never fires. Same snippet as tests/cairn-group-model.bats.
PY_LOAD="
import importlib.util
spec = importlib.util.spec_from_file_location('cairn_status', '$CAIRN_STATUS_PY')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)
"

# The structural reader every assertion below shares: it splits a render into
# the rows the grouped list actually emitted, and says where the block ended.
#
# A row is recognised by its own shape, which is the shape render_groups()
# builds: a phase row is two spaces then a symbol, a task row is six spaces
# then a symbol, a continuation is a deeper-indented line under a row, and a
# group label is a column-0 line.
#
# The block's END is not guessed from blank lines: a column-0 line that is
# NOT one of the model's own group labels stops the parse and is returned as
# `stop`. That boundary is what keeps the footer and the phase panel out, and
# it also means a group label the render invents (one the model never
# emitted) terminates the block instead of being quietly accepted.
#
# The symbol class the parser matches on is READ OUT OF the script, never
# retyped here. MEASURED while writing these tests: with the ten symbols
# hardcoded, swapping one of them for an east_asian_width=A glyph turned SIX
# tests red instead of one — the parser stopped recognising rows, so every
# test failed for a parsing reason and the width test's failure said nothing
# special. Reading the set keeps the width regression landing on the one
# test that can explain it.
SYMS_ALL="$(env PYTHONIOENCODING=utf-8 python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('cairn_status', '$CAIRN_STATUS_PY')
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)
for a in (False, True):
    s = cs.Style({'ascii': a, 'color': 'never'})
    print(s.s_none + s.s_planned + s.s_doing + s.s_done + s.s_blocked, end='')
")"

PY_ROWS="
import json, re
SYMS = '''$SYMS_ALL'''
ROW = re.compile(r'^(  |      )([' + re.escape(SYMS) + r']) (\S+)  (.*)\$')
def rows(text, labels):
    out, stop = [], None
    lines = text.split('\n')
    for line in lines[1:]:            # line 0 is the counts line
        if not line.strip():
            continue
        m = ROW.match(line)
        if m:
            out.append({'kind': 'phase' if m.group(1) == '  ' else 'issue',
                        'sym': m.group(2), 'key': m.group(3),
                        'body': m.group(4)})
            continue
        if (out and out[-1]['kind'] != 'group'
                and re.match(r'^ {8,}\S', line)):
            out[-1]['body'] += ' ' + line.strip()
            continue
        if not line.startswith(' ') and line in labels:
            out.append({'kind': 'group', 'sym': '', 'key': '', 'body': line})
            continue
        stop = line
        break
    return out, stop
"

# The model's own group labels, as a JSON array — the render is checked
# against what phase_groups() emitted, never against a list retyped here.
model_labels() {
  LABELS="$(bash "$STATUS_SH" --json | python3 -c "
import json, sys
print(json.dumps([g['label'] for g in json.load(sys.stdin)['groups']]))")"
}

# The two populations make_board_fixture deliberately does not carry. Every
# issue in that fixture is rendered into the seven committed reference
# boards, so adding these upstream would force a regeneration of all seven
# for the benefit of one test file (the same decision plan 20-02 recorded).
#
#   brd-201: a genuinely long title — a real sentence with spaces, not a
#            repeated word, so the wrap has something to wrap ON — plus an
#            assignee and an external_ref, so one row exercises the title,
#            the suffixes and the wrap at once.
#   brd-202: blocked by TWO issues, because "names the blocker" is only
#            proved by a row that has more than one to name.
#   brd-203: a title carrying a single token wider than the body column, so
#            the ONE case where a row is allowed past the width is a case
#            the fixture actually contains, not a clause nobody exercises.
setup() {
  require_bd
  make_tmp_repo
  make_board_fixture "$PWD"
  LONG_TITLE="Fill the entire terminal line with a title that has no business being short, so the renderer has to decide what to do with it"
  bd create "$LONG_TITLE" --id brd-201 -t task -p 4 -l phase-4 \
    -a cairn-tests --silent >/dev/null
  bd update brd-201 --status in_progress >/dev/null 2>&1
  bd update brd-201 --external-ref jira-DTP-142 >/dev/null 2>&1
  bd create "Wait on two things at once" --id brd-202 -t task -p 4 \
    -l phase-4 --silent >/dev/null
  bd dep brd-002 --blocks brd-202 >/dev/null
  bd dep brd-003 --blocks brd-202 >/dev/null
  LONG_TOKEN="https://example.invalid/a/path/so/long/that/it/cannot/be/broken/anywhere"
  bd create "Ship the endpoint $LONG_TOKEN today" --id brd-203 -t task -p 4 \
    -l phase-3 --silent >/dev/null
}

# Render into a file and leave the path in $RENDER. Never through a pipe
# into python: --width already forces the board renderer, and a file keeps
# the bytes inspectable when a test fails.
#
# A FRESH path per call, counted, and not $$ — two renders inside one test
# share a pid, so a pid-named file makes the second silently overwrite the
# first and a test comparing them ends up comparing one render with itself.
RENDER_N=0
render() {
  RENDER_N=$((RENDER_N + 1))
  RENDER="$BATS_TEST_TMPDIR/render-$RENDER_N.txt"
  bash "$STATUS_SH" --color=never "$@" > "$RENDER"
}

# ─── BOARD-06: the hierarchy ─────────────────────────────────────────────────

# Breaks this test: emitting the unphased group first (D-01 of phase 20),
# dropping the phase rows, or placing an issue outside the bucket its
# phase-N label names.
@test "the board renders milestone, then phase, then task, with loose work last" {
  model_labels
  render --width 100
  run python3 -c "
$PY_ROWS
labels_in = json.loads('''$LABELS''')
# The model itself, first: the open cycle and the loose bucket, in that
# order. Asserting the render against a model that already drifted would
# prove the two agree about the wrong thing.
assert labels_in == ['v1.1 Surface', 'No milestone'], labels_in
rows, stop = rows(open('$RENDER').read(), labels_in)

labels = [r['body'] for r in rows if r['kind'] == 'group']
assert labels == labels_in, (labels, labels_in)
assert rows[0]['kind'] == 'group', rows[0]
assert labels[-1] == 'No milestone', labels

# The open milestone's own phases, ascending, one row each.
phases = [r['key'] for r in rows if r['kind'] == 'phase']
assert phases == ['3', '4'], phases

# brd-001 carries label phase-3 and must sit under phase 3's row; brd-003
# carries no phase label at all and must sit under 'No milestone'.
def owner(key):
    cur = None
    for r in rows:
        if r['kind'] == 'group':
            cur = r['body']
        elif r['kind'] == 'phase':
            cur = 'phase ' + r['key']
        elif r['key'] == key:
            return cur
    return None
assert owner('brd-001') == 'phase 3', owner('brd-001')
assert owner('brd-004') == 'phase 3', owner('brd-004')
assert owner('brd-002') == 'phase 4', owner('brd-002')
assert owner('brd-003') == 'No milestone', owner('brd-003')

# The block ended where the footer begins, not somewhere inside itself.
assert stop is not None and 'done: ' in stop, repr(stop)
"
  [ "$status" -eq 0 ]
}

# ─── BOARD-02: the symbols ───────────────────────────────────────────────────

# Breaks this test: swapping any of the five for an east_asian_width=A
# glyph (○ U+25CB, ◑ U+25D1, ◆ U+25C6 were the obvious candidates and are
# all A — one cell in a Latin locale, two in a CJK one), or giving the ASCII
# set a two-character member, or reusing a glyph the same output already
# spends on something else.
#
# It reads the symbols OUT OF the script. A literal copied into the test
# would stay green after someone changed the script.
@test "every stage symbol is one cell, measured by unicodedata, not by eye" {
  run env PYTHONIOENCODING=utf-8 python3 -c "
$PY_LOAD
import unicodedata
st = cs.Style({'ascii': False, 'color': 'never'})
assert not st.ascii, 'Style fell back to ascii — stdout encoding is not utf'
syms = [st.s_none, st.s_planned, st.s_doing, st.s_done, st.s_blocked]
assert len(set(syms)) == 5, syms
for ch in syms:
    assert len(ch) == 1, repr(ch)
    w = unicodedata.east_asian_width(ch)
    assert w == 'N', '%r U+%04X is east_asian_width=%s, not N' % (ch, ord(ch), w)
    assert cs.char_width(ch) == 1, repr(ch)

a = cs.Style({'ascii': True, 'color': 'never'})
asc = [a.s_none, a.s_planned, a.s_doing, a.s_done, a.s_blocked]
assert len(set(asc)) == 5, asc
for ch in asc:
    assert len(ch) == 1 and ord(ch) < 128, repr(ch)
# No stage symbol may reuse a glyph this same output already spends: x is
# g_conflict, ! is g_informs, * is g_stale, # is g_card.
taken = {a.g_next, a.g_dep, a.g_who, a.g_stale, a.g_conflict, a.g_informs,
         a.g_card}
assert not (set(asc) & taken), set(asc) & taken
" 3>&-
  [ "$status" -eq 0 ]
}

# ─── BOARD-03: the title ─────────────────────────────────────────────────────

# Breaks this test: putting truncate() back on the task row, or letting any
# suffix be dropped so the row fits. Both would leave the row inside the
# width and both would lose bytes the reader asked for.
#
# The widths start at 64 and not lower ON PURPOSE: below STACK_BELOW the
# render still degrades to the stacked lanes, which plan 21-01 leaves alive
# and which DO truncate. Measured at --width 60: the output is still
# `READY (3)` / `DOING (2)` / `BLOCKED (2)`. Plan 21-02 collapses those
# degrades into this same list and widens this loop; asserting the property
# here at 60 would be asserting it of code this plan did not write.
@test "a genuinely long title is never truncated, at any width that holds a word" {
  model_labels
  for w in 64 80 100 140; do
    render --width "$w"
    run python3 -c "
$PY_ROWS
rows, stop = rows(open('$RENDER').read(), json.loads('''$LABELS'''))
row = [r for r in rows if r['key'] == 'brd-201']
assert len(row) == 1, 'brd-201 rendered %d times' % len(row)
body = row[0]['body']
title = '''$LONG_TITLE'''
assert title in body, 'title came back cut at width $w:\n%r' % body
assert '…' not in body and '...' not in body, body
# The suffixes rode along, none of them shed to make room.
assert 'DTP-142' in body, body
assert 'cairn-tests' in body, body
"
    [ "$status" -eq 0 ]
  done
}

# ─── BOARD-05: the blocker ───────────────────────────────────────────────────

# Breaks this test: naming only as_str_list(blocked_by)[0], which is what
# make_cell() did — the row would carry brd-002 and stay silent about
# brd-003, and finding the second one would need a second command.
@test "a blocked row names every blocker it has, on the row itself" {
  model_labels
  render --width 100
  run python3 -c "
$PY_ROWS
rows, stop = rows(open('$RENDER').read(), json.loads('''$LABELS'''))
row = [r for r in rows if r['key'] == 'brd-202']
assert len(row) == 1, 'brd-202 rendered %d times' % len(row)
body = row[0]['body']
assert 'blocked by' in body, body
named = body.split('blocked by', 1)[1]
for dep in ('brd-002', 'brd-003'):
    assert dep in named, '%s is not named on the row: %r' % (dep, body)
"
  [ "$status" -eq 0 ]
}

# ─── BOARD-02, criterion 3: the two modes close on the same columns ──────────

# Breaks this test: giving any ASCII stage symbol two characters (`->`,
# `[]`, `..`), which is the obvious way to write the fallback and the one
# that silently moves every column right of it in one mode only.
@test "--ascii swaps the symbols and moves no column" {
  model_labels
  render --width 100
  local uni="$RENDER"
  render --width 100 --ascii
  run env PYTHONIOENCODING=utf-8 python3 -c "
$PY_LOAD
$PY_ROWS
labels = json.loads('''$LABELS''')
u = open('$uni').read().split('\n')
a = open('$RENDER').read().split('\n')
ur, ustop = rows(open('$uni').read(), labels)
ar, astop = rows(open('$RENDER').read(), labels)

# Same rows, same order, same keys: --ascii is a glyph decision, never a
# content decision.
assert [(r['kind'], r['key']) for r in ur] == [(r['kind'], r['key'])
                                               for r in ar]

st = cs.Style({'ascii': False, 'color': 'never'})
sa = cs.Style({'ascii': True, 'color': 'never'})
uni_syms = {st.s_none, st.s_planned, st.s_doing, st.s_done, st.s_blocked}
asc_syms = {sa.s_none, sa.s_planned, sa.s_doing, sa.s_done, sa.s_blocked}

# Every row swapped its symbol for the ASCII one at the same position.
pairs = dict(zip([st.s_none, st.s_planned, st.s_doing, st.s_done,
                  st.s_blocked],
                 [sa.s_none, sa.s_planned, sa.s_doing, sa.s_done,
                  sa.s_blocked]))
for ru, ra in zip(ur, ar):
    if ru['kind'] == 'group':
        continue
    assert pairs[ru['sym']] == ra['sym'], (ru['sym'], ra['sym'])

# The block itself: same number of physical lines, and each one the same
# number of CELLS. This is the mechanical form of 'the columns close
# aligned in both modes' — it holds only because every stage symbol is one
# cell in one mode and one character in the other.
ub = u[:u.index(ustop)]
ab = a[:a.index(astop)]
assert len(ub) == len(ab), (len(ub), len(ab))
for i, (lu, la) in enumerate(zip(ub, ab)):
    assert cs.display_width(lu) == cs.display_width(la), (
        i, lu, la, cs.display_width(lu), cs.display_width(la))

# And no glyph leaked the wrong way.
for line in ab:
    assert not (set(line) & uni_syms), line
"
  [ "$status" -eq 0 ]
}

# ─── The row stays inside the width it was given ─────────────────────────────

# Breaks this test: wrapping on character count instead of display cells,
# or forgetting to subtract the prefix from the body budget. Both leave rows
# a few cells past the edge, which is what the old fixed-width lane cell
# existed to prevent and what a wrapping row has to prevent by arithmetic.
#
# It REPLACES tracker-card's "no card is pushed out of its lane, at any
# width" with the stronger property the grouped list can carry: nothing is
# shed to fit, AND nothing overflows — except the single case the code
# documents, a lone token wider than the body column, which brd-203 makes
# real instead of hypothetical.
@test "no row overflows its width, and the one exception is a token that cannot fit" {
  model_labels
  for w in 64 72 100 140; do
    render --width "$w"
    run python3 -c "
$PY_LOAD
$PY_ROWS
text = open('$RENDER').read()
labels = json.loads('''$LABELS''')
rows_, stop = rows(text, labels)
lines = text.split('\n')
block = lines[:lines.index(stop)]
over = [l for l in block if cs.display_width(l) > $w]
# Every overflowing line must be a prefix plus ONE token: the wrap refuses
# to split a token, and that is the documented exception.
for l in over:
    assert len(l.strip().split()) <= 3, 'row past --width $w: %r' % l
    assert 'example.invalid' in l, 'unexpected overflow at --width $w: %r' % l
# The unbreakable token survived whole — split anywhere and this fails.
assert '$LONG_TOKEN' in text.replace('\n', ''), 'the long token was split'
"
    [ "$status" -eq 0 ]
  done
}

# ─── Nothing is lost between the lanes and the screen ────────────────────────

# Breaks this test: dropping a bucket, not emitting the unphased group, or
# a `+k more` that swallows rows without saying so. The multiset comparison
# catches loss AND duplication; 'contains' would catch neither.
@test "every open issue on a lane reaches the screen, exactly once" {
  model_labels
  render --width 100
  run bash -c "bash '$STATUS_SH' --json > '$BATS_TEST_TMPDIR/model.json'"
  [ "$status" -eq 0 ]
  run python3 -c "
$PY_ROWS
labels = json.loads('''$LABELS''')
rows_, stop = rows(open('$RENDER').read(), labels)
on_screen = sorted(r['key'] for r in rows_ if r['kind'] == 'issue')
d = json.load(open('$BATS_TEST_TMPDIR/model.json'))
on_lanes = sorted(i['id'] for lane in ('ready', 'doing', 'blocked')
                  for i in d[lane])
assert on_screen == on_lanes, (
    'only on lanes: %s | only on screen: %s' % (
        sorted(set(on_lanes) - set(on_screen)),
        sorted(set(on_screen) - set(on_lanes))))
"
  [ "$status" -eq 0 ]
}
