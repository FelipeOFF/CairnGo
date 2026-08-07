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
CLS = '[' + re.escape(SYMS) + ']'
# Two row shapes, because render_groups() has two. The wide one carries the
# body beside the id; below NARROW_BODY cells of room the id keeps its own
# line and the body hangs under it. Continuations sit at 4, 8 or >=11 spaces
# and never at 2 or 6, so a continuation can never be read as a row.
ROW = re.compile(r'^(  |      )(' + CLS + r') (\S+)  (.*)\$')
ROW_NARROW = re.compile(r'^(  |      )(' + CLS + r') (\S+)\$')
def rows(text, labels):
    out, stop = [], None
    lines = text.split('\n')
    for line in lines[1:]:            # line 0 is the counts line
        if not line.strip():
            continue
        m = ROW.match(line) or ROW_NARROW.match(line)
        if m:
            g = m.groups()
            out.append({'kind': 'phase' if g[0] == '  ' else 'issue',
                        'sym': g[1], 'key': g[2],
                        'body': g[3] if len(g) > 3 else ''})
            continue
        if (out and out[-1]['kind'] != 'group'
                and re.match(r'^ {4,}\S', line)):
            out[-1]['body'] = (out[-1]['body'] + ' ' + line.strip()).strip()
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
# into python: a file keeps the bytes inspectable when a test fails. (Said
# "--width already forces the board renderer" until 2026-08-06 — Phase 22
# ended the forcing: a pipe renders the board anyway, and --width is width.)
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

# ─── CairnGo-cdx: the phase panel fits the width it was given ────────────────

# MEASURED 2026-08-06, BEFORE the fix, with real column cells
# (east_asian_width, never len()) and comparing each line with its trailing
# padding stripped — so what is counted is content, not blank space:
#
#   fixture           --width 30/38/50/60/64/70/80  longest line 90  OVERFLOWS
#   this repository   --width 60/70/80/90           longest line 92  OVERFLOWS
#
# The floor was `76 + num_w - 1 + len(next)`: six optional columns summed
# unconditionally while `phase` collapsed to a lone `…`. Already a defect;
# PIPE-02 made it urgent, because a flagless non-TTY run now renders this
# table at 80 columns.
#
# The sweep covers the whole PHASE PANEL — the table, its two notes, PURPOSE
# and the parallelism note — and not the grouped list above it, on purpose:
# the list is ALLOWED past the edge in exactly one case (a single token wider
# than the column overflows rather than being split, BOARD-03), and this
# fixture contains that case in brd-203. Asserting a property the fixture
# deliberately violates would mean weakening it until it proved nothing.
#
# Breaks this test: summing the optional widths unconditionally again,
# printing the table when only the core would fit, or emitting either note
# unwrapped.
@test "the phase panel never renders a line wider than the width it was given" {
  for w in 30 38 44 50 60 64 70 80 90 100 120 140 200; do
    render --width "$w"
    run python3 -c "
import unicodedata
def cw(s):
    return sum(2 if unicodedata.east_asian_width(c) in ('W','F') else 1
               for c in s)
w = $w
lines = open('$RENDER').read().split('\n')
start = next((i for i, l in enumerate(lines)
              if l.startswith('PENDING PHASES')), None)
assert start is not None, 'the phase panel did not render at width %d' % w
bad = [l for l in lines[start:] if cw(l.rstrip()) > w]
assert not bad, (w, [(cw(l.rstrip()), l.rstrip()) for l in bad])
"
    [ "$status" -eq 0 ]
  done
}

# The other half of the same fix: a column that cannot fit is REMOVED and
# NAMED, never squeezed into an ellipsis, and the header never renders
# narrower than its own word. At 100 columns nothing is sacrificed at all,
# which is what keeps the committed w100/ascii100/maxrows references still.
@test "columns that do not fit are dropped and named, never squeezed" {
  render --width 100
  run grep -c 'hidden at this width' "$RENDER"
  [ "$output" = "0" ]
  grep -qF 'waits' "$RENDER"

  render --width 50
  grep -qF 'hidden at this width' "$RENDER"
  # The names of what left, so the reader knows what is missing rather than
  # believing the table is complete.
  grep -qF 'waits' "$RENDER"
  # And the core survives: which phase, where it stands, what to run.
  grep -qF 'PENDING PHASES' "$RENDER"
  grep -qF 'phase' "$RENDER"
  grep -qF 'state' "$RENDER"
  grep -qF 'next' "$RENDER"

  # Below the core's own minimum the table steps aside and says so, and
  # PURPOSE still carries every pending phase.
  render --width 38
  grep -qF 'table needs' "$RENDER"
  grep -qF 'PURPOSE' "$RENDER"
  run grep -c '^  #  phase' "$RENDER"
  [ "$output" = "0" ]
}

# ─── CairnGo-uz6: the screen stops contradicting itself ──────────────────────

# MEASURED 2026-08-06, on a one-phase roadmap with no `## Milestones` section
# and no open issue, all three of these were on screen at once:
#
#     (no open work)          <- this list
#   phase 1/1 Alpha           <- the footer
#   PENDING PHASES  1         <- the table
#
# Three surfaces, two answers. The list only ever built buckets inside an
# OPEN milestone group, so with no open cycle it built none — and a second
# symptom followed from the same cause: an issue carrying `phase-N` rendered
# under the loose group with its phase line gone.
#
# Breaks this test: dropping the unnamed group, filling it with ALL phases
# instead of the pending ones, or letting `(no open work)` print while a
# phase is pending.
@test "with no open cycle the list shows the pending phases, not '(no open work)'" {
  sed -i.bak 's/^- 🚧 \*\*v1.1 Surface\*\*/- ✅ **v1.1 Surface**/' \
    .planning/ROADMAP.md
  rm -f .planning/ROADMAP.md.bak
  run grep -c '🚧' .planning/ROADMAP.md
  [ "$output" = "0" ]

  model_labels
  render --width 100
  run python3 -c "
$PY_LOAD
$PY_ROWS
labels_in = json.loads('''$LABELS''')
assert labels_in == ['No open milestone', 'No milestone'], labels_in
rows_, stop = rows(open('$RENDER').read(), labels_in)

labels = [r['body'] for r in rows_ if r['kind'] == 'group']
assert labels == labels_in, (labels, labels_in)

# The PENDING phases, ascending — phases 1 and 2 are complete here and must
# not be dragged in.
phases = [r['key'] for r in rows_ if r['kind'] == 'phase']
assert phases == ['3', '4'], phases

# The label the whole defect was about must not be on this screen.
text = open('$RENDER').read()
assert cs.NO_WORK_TEXT not in text, cs.NO_WORK_TEXT
# And the group label is the module's own constant, never a retyped string.
assert cs.NO_OPEN_MILESTONE_LABEL in text, cs.NO_OPEN_MILESTONE_LABEL
"
  [ "$status" -eq 0 ]
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
# WIDENED 2026-08-05 (plan 21-02) from `64 80 100 140` down to 30. The loop
# started at 64 because below STACK_BELOW the render degraded to the stacked
# lanes, which DID truncate — measured at --width 60: `READY (3)` /
# `DOING (2)` / `BLOCKED (2)`. Those degrades are gone, so BOARD-03 now holds
# at every width and the loop says so.
@test "a genuinely long title is never truncated, at any width that holds a word" {
  model_labels
  for w in 30 38 50 60 64 80 100 140; do
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
  for w in 30 38 50 64 72 100 140; do
    render --width "$w"
    run python3 -c "
$PY_LOAD
$PY_ROWS
text = open('$RENDER').read()
labels = json.loads('''$LABELS''')
rows_, stop = rows(text, labels)
lines = text.split('\n')
block = lines[:lines.index(stop)]
# ROWS, which is what this test claims: a phase row indents by two, a task
# row by six, and every continuation by four or more. The counts line and
# the group labels start at column zero and are not rows — the counts line
# does run past a 30-column terminal, the same way the footer's own meta
# line has since Phase 13, and both are logged as a pre-existing overflow
# of the non-row renderers rather than quietly folded into this assertion.
rows_lines = [l for l in block if l.startswith('  ')]
assert rows_lines, 'no task or phase row at --width $w'
over = [l for l in rows_lines if cs.display_width(l) > $w]
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

# ─── The edges ───────────────────────────────────────────────────────────────

# Breaks this test: returning [] early from render_groups() when there are no
# rows. MEASURED 2026-08-05 by doing exactly that — the human render loses
# its counts line and its `(no open work)` line and prints the footer with a
# blank space above it, so an empty board becomes indistinguishable from a
# board that failed to render. The three empty lanes used to say "nothing
# here" by being drawn; a list with nothing in it has to SAY it.
#
# The fixture is a fresh repo with bd initialised and zero issues, not the
# setup() fixture with everything closed: `done: N` should be zero here, and
# closing six issues would make it 6 and hide a counts-line bug behind a
# number that happened to look plausible.
@test "a board with no open work says so, and still prints its counts" {
  make_tmp_repo
  bd init -q --prefix emp --non-interactive >/dev/null 2>&1
  render --width 60
  run python3 -c "
$PY_ROWS
rows_, stop = rows(open('$RENDER').read(), [])
text = open('$RENDER').read()
lines = text.split('\n')

assert lines[0] == 'ready 0 · doing 0 · blocked 0 · done 0', repr(lines[0])
assert '(no open work)' in text, text

# Nothing that could be read as a task or phase row. This is the half that
# an early [] would still pass, which is why it is not the whole assertion.
assert rows_ == [], rows_
"
  [ "$status" -eq 0 ]
}

# Breaks this test: deduplicating by id in group_rows(), or resolving an id
# to one issue instead of consuming a per-id FIFO — either one collapses the
# two occurrences into one row, and the reader loses the fact that the thing
# being worked on is also blocked.
#
# MEASURED 2026-08-05 before writing the assertions, because the plan
# required proving the fixture can even produce this case: with dup-002 set
# in_progress AND blocked by dup-001, `bd list --status in_progress` returns
# ['dup-002'] and `bd blocked` returns ['dup-002'] — the same id from two
# independent queries, on THIS machine's bd. The render then carries it
# twice, once with the doing symbol and once with the blocked symbol naming
# dup-001. The assertions below state that measured behaviour and nothing
# beyond it.
@test "an issue that arrives on two lanes is rendered once per arrival" {
  make_tmp_repo
  bd init -q --prefix dup --non-interactive >/dev/null 2>&1
  bd create "blocker task" --id dup-001 -t task -p 2 --silent >/dev/null
  bd create "double duty" --id dup-002 -t task -p 2 --silent >/dev/null
  bd dep dup-001 --blocks dup-002 >/dev/null
  bd update dup-002 --status in_progress >/dev/null 2>&1

  # The premise first. If this machine's bd ever stops returning the id from
  # both queries, this test must fail HERE, naming the changed premise —
  # never further down, where it would look like a renderer regression.
  run bash -c "bash '$STATUS_SH' --json > '$BATS_TEST_TMPDIR/dup.json'"
  [ "$status" -eq 0 ]
  run python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/dup.json'))
doing = [i['id'] for i in d['doing']]
blocked = [i['id'] for i in d['blocked']]
assert doing == ['dup-002'], ('premise changed: doing is %r' % doing)
assert blocked == ['dup-002'], ('premise changed: blocked is %r' % blocked)
"
  [ "$status" -eq 0 ]

  render --width 90
  run python3 -c "
$PY_LOAD
$PY_ROWS
rows_, stop = rows(open('$RENDER').read(), ['No milestone'])
issues = [r for r in rows_ if r['kind'] == 'issue']
keys = [r['key'] for r in issues]
assert keys == ['dup-001', 'dup-002', 'dup-002'], keys

st = cs.Style({'ascii': False, 'color': 'never'})
by_sym = {r['sym']: r for r in issues if r['key'] == 'dup-002'}
assert set(by_sym) == {st.s_doing, st.s_blocked}, sorted(by_sym)
# The FIFO handed each occurrence its OWN lane, which is the whole claim:
# only the blocked arrival names the blocker.
assert 'blocked by dup-001' in by_sym[st.s_blocked]['body'], by_sym
assert 'blocked by' not in by_sym[st.s_doing]['body'], by_sym
"
  [ "$status" -eq 0 ]
}

# Breaks this test: computing id_w over `bucket['issues']` (every id in the
# bucket) instead of over the rows group_rows() actually emitted. An id
# hidden behind `+k more` would then pad the id column of every VISIBLE row,
# so the title column of the whole board would move because of a row nobody
# can see.
#
# The measurement that makes this concrete: brd-9999999999999999 is 20 cells
# against brd-00N's 7, so the wrong denominator moves the title column 13
# cells to the right — not a subtle drift.
@test "an id hidden behind +k more does not widen the id column" {
  # -p 4, not a lower rank: MEASURED 2026-08-05, `bd create -p 9` is
  # rejected outright ("invalid priority \"9\" (expected 0-4 or P0-P4)"), and
  # a fixture line that fails is a test that proves nothing while looking
  # red for the wrong reason. 4 is the bottom of the scale, which is all this
  # row needs — the assertion below states that the long id was cut and
  # fails loudly with the visible keys if it was not.
  bd create "Hidden behind the cut" --id brd-9999999999999999 -t task -p 4 \
    -l phase-3 --silent >/dev/null
  model_labels
  # --max-rows 1: phase 3's bucket holds more than one issue, so exactly one
  # survives the cut and the rest go behind `+k more`.
  render --width 100 --max-rows 1
  run python3 -c "
$PY_ROWS
text = open('$RENDER').read()
rows_, stop = rows(text, json.loads('''$LABELS'''))
keys = [r['key'] for r in rows_ if r['kind'] == 'issue']
assert 'brd-9999999999999999' not in keys, 'the long id was not cut: %r' % keys
assert '+' in text and 'more' in text, 'nothing was cut at all — the fixture ' \
    'stopped overflowing and this test is measuring nothing'

# Where the body starts on every visible task row, measured from the bytes.
starts = set()
for line in text.split('\n'):
    for r in rows_:
        if r['kind'] != 'issue' or not r['body']:
            continue
        marker = '      ' + r['sym'] + ' ' + r['key']
        if line.startswith(marker):
            starts.add(len(line) - len(line[len(marker):].lstrip()))
assert len(starts) == 1, ('the title column is not one column: %r' % starts)
# 6 indent + 1 symbol + 1 space + len(id) + 2 == the body column, IF the
# widest id among the visible rows is what set it. brd-00N is 7.
assert starts.pop() == 6 + 1 + 1 + 7 + 2, starts
"
  [ "$status" -eq 0 ]
}

# Breaks this test: removing NARROW_BODY, i.e. letting a row sit its body
# beside the id at every width. MEASURED 2026-08-05 at --width 30 with an
# 11-cell id: the inline body budget is 9 cells and single words land alone
# on their lines ("de", "com", "—"); with the drop it is 22. Nothing is
# truncated in either shape — this is purely about how much of the title a
# reader gets per line, which is why it needs its own test instead of riding
# along on the BOARD-03 assertions, all of which stay green with NARROW_BODY
# gone.
@test "a narrow width drops the body under the id instead of squeezing it" {
  model_labels
  render --width 30
  run python3 -c "
$PY_LOAD
$PY_ROWS
text = open('$RENDER').read()
rows_, stop = rows(text, json.loads('''$LABELS'''))
issues = [r for r in rows_ if r['kind'] == 'issue']
assert issues, 'no task row at --width 30'

lines = text.split('\n')
end = lines.index(stop)
# In the narrow shape the id line ends AT the id: no body beside it.
bare = [l for l in lines[:end]
        if any(l.rstrip() == '      ' + r['sym'] + ' ' + r['key']
               for r in issues)]
assert len(bare) == len(issues), (
    'only %d of %d task rows dropped their body' % (len(bare), len(issues)))

# And what that buys: every continuation line gets more than the inline
# budget would have left it. The inline budget is 30 - (6 + 1 + 1 + id + 2).
id_w = max(cs.display_width(r['key']) for r in issues)
inline_budget = 30 - (6 + 1 + 1 + id_w + 2)
widest = max(cs.display_width(l.strip()) for l in lines[:end]
             if l.startswith('        ') and l.strip())
assert widest > inline_budget, (
    'the drop bought nothing: widest continuation %d cells vs inline budget '
    '%d' % (widest, inline_budget))
"
  [ "$status" -eq 0 ]
}
