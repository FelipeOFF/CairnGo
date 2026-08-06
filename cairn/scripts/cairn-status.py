#!/usr/bin/env python3
"""cairn-status — render the combined bd + GSD status board.

One deterministic, pipe-safe render of the repo's working state: three lanes
(READY / DOING / BLOCKED) driven by bd, a footer with the GSD roadmap
position, and ONE synthesized next action. Prints top-down and exits — no
alternate screen, no cursor addressing, no animation.

Usage:
    cairn-status.py [--json] [--plain] [--brief] [--width N] [--max-rows N]
                    [--ascii] [--color=always|never] [--planning-dir <dir>]
                    [--html <path>]

Behavior:
    1. Locate the planning dir (default: $CLAUDE_PROJECT_DIR or cwd +
       /.planning). When --planning-dir is given, the repo root is its
       parent, so the board can be pointed at any checkout.
    2. Query bd (pinned to the root with -C): `bd ready --json` (the truly
       claimable list — deps, gates and defer_until respected), `bd list
       --status in_progress --json`, `bd blocked --json`, and `bd list
       --status closed --json` (for the done count). When the root has no
       .beads/, bd is never queried (bd walks UP to find a database, which
       could silently render an ancestor repo's board): the board degrades
       to a GSD-only render with a note — mirroring cairn-gate's
       applicability decision. When the root DOES have a .beads/ but a
       cheap `bd list --limit 1` probe run before the lane queries itself
       fails (bd present on PATH, the query broken — a crashed daemon, a
       corrupted DB), the board degrades the same way — every lane empty,
       a note naming the failure — and `phase_model()`'s `bd_ok` flag turns
       False, so every phase's corroboration `bd` evidence reads "unknown"
       rather than silently agreeing with disk (see 4c).
    3. Read GSD position leniently (regex, no YAML lib — patterns shared
       with cairn-gate, except TABLE_PHASE_ANY which is stricter, see its
       comment): ROADMAP.md phase checkboxes / progress-table rows and the
       🚧 milestone line; STATE.md frontmatter `milestone:`, `active_phase:`
       and `next_action:`. All of it is optional — missing files degrade to
       an issues-only board. `roadmap_phase_rows()` also reads each phase's
       `### Phase N:` detail block for `**Card:**` (or, failing that, the
       first sentence of `**Goal:**`) — per D-03, this is the phase's
       `purpose`, and it is `null` only when the phase has no detail block
       at all.

       Since Phase 22 (BOARD-04) STATE.md's `milestone:` no longer names the
       milestone on any human surface. It is the pointer that keeps aiming at
       the archived cycle (MEASURED 2026-08-03, ten minutes after v1.4 was
       archived: the board still read `v1.4`), so the footer, --brief and the
       HTML head all read `open_milestones` — the `🚧` marker on the
       ROADMAP's own `## Milestones` line, the same source phase_groups()
       has used since Phase 20 — through milestone_label(). `--plain` still
       carries the STATE.md read on its `MILESTONE` row, because PIPE-01
       freezes the machine contract; that asymmetry is deliberate, recorded,
       and tracked as an issue rather than smuggled into a byte change here.
    4. Synthesize ONE next action. In order: an in_progress issue exists →
       continue it; else the highest-priority ready issue labeled
       m-<milestone>,phase-<active>; else STATE.md's next_action; else the
       highest-priority ready issue overall. Rule of thumb (kept from the
       prose command): bd wins for work items, STATE.md wins for workflow
       steps. Ready issues whose phase-N labels ALL point at phases the
       ROADMAP marks complete are excluded from both ready picks — next
       never suggests a delivered phase.
    4b. Cross-check lanes against the roadmap: open issues (any lane) whose
       phase labels are all roadmap-complete stay on the board — data is
       data — but carry a dim ·done-phase marker on their card, a footer
       warning pointing at /cairn:doctor --close-completed, and their ids
       under the JSON key stale_complete.
    4c. Corroborate each phase's state from four independent reads: disk
       (phase_disk_state — file existence only), bd (that phase's own
       phase-N-labeled issues), the ROADMAP checkbox, and STATE.md's
       active_phase pointer. Each `--json` phase row carries additive keys
       `evidence` (the raw per-source reads), `corroboration` (`"ok"` /
       `"conflict"` / `"unknown"`), and `conflicts` (itemized `{severity,
       sources, detail}`, severity `"blocks"` or `"informs"`) — disk_state
       itself is never widened, so it stays exactly the four values it
       always was. A source that could not be read (bd unreachable) is
       reported "unknown", never folded into agreement: an unreadable bd
       never produces "ok" by itself. A phase needing attention (an
       "unknown" verdict, or a "blocks" conflict) is rerouted to
       `/cairn:doctor` instead of its disk-driven next command, both in
       `phases[].next_command` and in `next_commands[]`.
    4d. Each `--json` phase row also carries four additive, purely
       descriptive keys for the phase card: `purpose` (see step 3),
       `research_done` (does the phase directory carry an `NN-RESEARCH.md`),
       `issues_done`/`issues_total` (bd issues matching that phase's own
       `phase-N` label by ANY match — a looser count than bd_state()'s
       ALL-not-ANY corroboration filter, and never used for corroboration),
       and `verify_status` (the literal `status:` value from the phase's
       `NN-VERIFICATION.md` frontmatter, or `null` when absent/unreadable).
       `disk_state` itself is still never widened by any of this.
    4e. `phase_model()` ends with exactly ONE batched call to
       `cairn-journal.py observe` (Phase 16, D-01/D-02), carrying every
       phase's `evidence`+`corroboration` from 4c above as one JSON array
       on stdin — the concrete write path for the journal's "phase state"
       and "corroboration verdict" categories, reached from every surface
       that renders the board. Purely a side effect: the journal is never
       read anywhere in this script, so a missing or broken
       cairn-journal.py degrades to a stderr warning and changes nothing
       else about this run (JOUR-03) — see journal_observe_phases().
    4f. `--json` also carries a top-level `groups` key (never anything
       nested inside `phases[]`): the same model read as the hierarchy
       milestone → phase → issue. Each group is `{type, key, label, items}`
       with `type` `"milestone"` or `"unphased"`, and `items` is always a
       list of `{phase, issues}` buckets — the unphased group has exactly
       one, with `phase` null. Open milestone groups come in the roadmap's
       own order, the unphased group is always last, and a group with no
       buckets is not emitted at all, so no group ever wears the last
       archived name. A roadmap with NO open cycle emits one group carrying
       the pending phases, `key` null and label `No open milestone` (Phase
       22, CairnGo-uz6 — until then it emitted nothing and the list said
       `(no open work)` while the table counted phases). "Open" is the
       marker on the milestone's own `## Milestones` line (`🚧` /
       `(in progress)`), never STATE.md's `milestone:`, which keeps pointing
       at the archived cycle. An issue's
       `phase-N` labels are the ONLY thing that places it (the smallest
       phase it names among the ones some emitted group claims, else the
       unphased group); dependency edges are deliberately never read here,
       because they currently conflate provenance with blocking across
       archived cycles (FIX-04). Nothing is deduplicated, so the multiset of
       ids across every bucket equals the multiset on the lanes. See
       phase_groups() and roadmap_milestones().
    4g. What the group model rests on, measured and presumed. MEASURED
       2026-08-03: this repository's own ROADMAP carries 5 milestones with
       exactly 1 open (`v1.5`, phases 20-29); the phase-model fixture's
       roadmap carries 2 with 1 open (`v1.1`, phases 3-4); make_gsd_fixture
       writes no `## Milestones` section at all and yields 0, which is the
       shape every pre-20 test runs on; and the `## Milestone: v1.5 ... 🚧`
       heading sitting immediately below the list does not reopen the
       section (the heading regex is anchored and plural on purpose).
       MEASURED: without `bd create --id`, two identically built repos
       produce different issue ids, so a render carrying ids is not
       byte-stable — which is why the reference fixture pins every id.
       MEASURED, and the reason placement reads labels and nothing else:
       phase 26 renders as blocked by phase 9, a cycle archived two
       milestones earlier, because a `discovered-from` edge counts as a
       block and an archived phase is never in the completed-phase set
       (FIX-04, phase 25's repair — not this one's). PRESUMED, with no
       formal guarantee anywhere: that every milestone of this project keeps
       writing itself as a list item whose bold span starts with a version
       token. If that shape changes, roadmap_milestones() returns an empty
       list and the model falls silent — zero milestone groups, every issue
       in the unphased group — which is the correct failure mode, and the
       reason the rule is written to fall that way rather than to guess.
    5. Render. TTY: ONE grouped list, at every width. The hierarchy is the
       step-4 `groups` model read straight down — open milestone, then its
       phases in roadmap order, then that phase's tasks, with `unphased`
       last so work nobody routed is visible instead of lost. There is no
       width degrade: three columns did not fit a narrow terminal and one
       column fits any, so the columns/stacked/raw ladder (>= 64 / >= 40 /
       < 40 cols) that stood here until Phase 21 had nothing left to solve
       and went out with the renderers it chose between.

       Row shape. A stage symbol of exactly ONE cell, then the key (phase
       number or issue id) padded to the widest key AMONG THE VISIBLE ROWS,
       then the body. The title is never truncated: it wraps per cell with
       the continuation aligned under the body, and a single token wider
       than the column overflows rather than being split — a cut token is
       a lie about the title, an overflowing one is the terminal's own
       wrap. Below NARROW_BODY cells of body room the row stops trying to
       sit the body beside the key and drops it to its own indented lines
       (MEASURED at --width 30 with an 11-cell id: 9 cells inline versus 22
       stacked; nothing is truncated either way, so this is a legibility
       decision and it carries its own test). Each bucket is capped at
       --max-rows with a dim `+k more`, and the counts line at the top is
       the same text `--brief` prints.

       MEASURED 2026-08-05 (unicodedata.east_asian_width): the five stage
       symbols `◌ ◔ ◕ ✓ ⧗` are all `N` — one cell in every locale. `○`
       U+25CB, `◑` U+25D1 and `◆` U+25C6 were the obvious candidates and
       all three are `A`: one cell in a Latin locale, TWO in a CJK one.
       char_width() returns 2 only for W and F, so an `A` symbol counts 1
       here and draws 2 there, and this script cannot tell the difference
       (it reads no locale, and inventing that read would be inventing a
       source of truth). The defense is to not use `A` at all.

       DECIDED 2026-08-06 (Phase 22, CairnGo-hbo), where Phase 21 had left a
       finding: the `A`-width characters outside the stage symbols are NOT
       going away, and the board's alignment is therefore GUARANTEED IN A
       WESTERN LOCALE AND NOT IN A CJK ONE. That is a boundary, not a
       pending fix. Measured 53 occurrences on a --width 100 render, of
       which 12 are accented letters of the board's own Portuguese prose —
       so choosing different glyphs cannot solve it, and resolving `A` from
       the environment would mean inventing a source of truth this script
       refuses to invent. The full measurement and the argument live in
       char_width()'s docstring, next to the ruler they are about.

       ASSUMED, not proved: that one issue reaches the list at most twice
       (once in_progress, once blocked), because `bd list --status
       in_progress` and `bd blocked` are independent queries. The FIFO in
       group_rows() does not depend on the number — the assumption is only
       about what is observed in practice.

       DELIBERATE: a phase row never carries the blocked symbol. A phase is
       not blocked by the same mechanism an issue is, and FIX-04 (phase
       25's repair) is where "archived phase counted as complete" gets
       fixed; borrowing the blocked glyph here would encode a state this
       model does not actually compute.

       Non-TTY: the SAME renderer, in plain text (Phase 22, PIPE-02). Until
       2026-08-06 a flagless non-TTY run degraded to --plain, so the machine
       format was what a pipe, a redirect and a subprocess all got. It no
       longer does: without a tty the board renders exactly as it does with
       one, minus the two things a tty decides. MEASURED 2026-08-06: Style
       resolves color to False because _color_enabled() ends at
       isatty(stdout), so the output carries zero escape bytes; and
       terminal_cols() returns 80, because shutil.get_terminal_size falls
       back to (80, 24) when stdout is a pipe and $COLUMNS is unset — the
       same width a terminal without $COLUMNS gets. --width N and
       --color=always no longer select a renderer, because there is nothing
       left to select: they are width and color, and that is all.

       THE BOUNDARY THIS CREATES, and it is the one thing to read here: a
       script doing `cairn-status > file` and expecting TSV now receives the
       board. The fix is to write --plain, which is the only door to the
       machine format and is byte-for-byte what it always was (PIPE-01,
       pinned in tests/fixtures/machine-contract/nontty-pre-split.txt).

       All bd/STATE.md text is passed through clean(), which strips C0/C1
       control bytes — titles from remote trackers can't inject escape
       sequences or forge rows.
    5b. Below the grouped list, `phase_panel_lines()` prints a
       PENDING PHASES table (`#`, `phase`, `state`, `rsch`, `plans`, `issues`,
       `verify`, `waits`, `next` — the same step-4d/4c fields the HTML page
       renders) and a PURPOSE list keyed by phase number, each line pairing
       that phase's purpose with the reason `next_commands()` ordered it
       where it did. There is no separate NEXT COMMANDS section: the command
       itself is the table's `next` column, and the reason lives in PURPOSE
       instead. PURPOSE is the one place text wraps rather than truncates —
       a phase's purpose is never cut. When every phase is complete
       (`pending_phases()` empty), PURPOSE still renders: `next_commands()`'s
       `phase: None` pair (`/cairn:ship`, `/cairn:milestone complete`) prints
       there with no phase-number prefix, so the terminal never shows less
       than `--json` or the HTML page.

       An unresolved tension, recorded rather than papered over (D-08 of
       the Phase 21 context): step 5 promises a task title is never cut,
       and this table still cuts a PHASE title — at --width 50 the `phase`
       column comes out as a bare `…`. The table is fixed-width by design
       and MEASURED 2026-08-05 it has a floor of 92 cells, so it overflows
       at EVERY width from 64 to 90 as well — including widths that were
       already on the wide path before Phase 21, which is what makes this a
       pre-existing defect of this function rather than a cost of the
       grouped list. No criterion of Phase 21 reaches it; it has an issue.
    6. When .cairn/sync.json exists, append a sync-staleness line from the
       last-pull watermarks in .cairn/state.json (missing or older than 24h
       → suggest /cairn:sync-pull).
    6b. When the active phase's lease (Plan 15-01) is actively held and
       fresh, append one footer line naming who holds it and since when
       (D-05) — computed once from data["lease"] and shared verbatim by
       the terminal footer, --plain and the HTML foot, so the three can
       never disagree. A vacant or stale hold renders nothing here (a
       stale hold is /cairn:doctor's story to tell, not the footer's).
    7. --html <path> renders the SAME data as a standalone HTML board (no
       network of any kind: styles, texture and the profile are inline, no
       font/script/image is loaded from anywhere). The page is a generated
       VIEW: everything between <!-- cairn:generated:board:start --> and
       <!-- cairn:generated:board:end --> is owned by this script, every byte
       outside them is the user's and survives regeneration byte for byte —
       the same marker mechanics as cairn-map.py and bench-publish.py. A path
       that does not exist yet is seeded from templates/status-board.html; a
       file without the marker pair gets the block appended, never destroyed.
       Its signature is a topographic profile of the roadmap: one terrain
       segment per phase, elevation = that phase's issue count (open AND
       closed), ground filled up to the active phase, a drawn cairn standing
       on it, and a thin ridge line for the climb ahead. Without roadmap
       phases the band degrades to a flat horizon carrying the counts — it
       never invents relief. All bd/GSD text goes through esc() = clean() +
       HTML escaping, so a title carrying markup renders as text.

    --json      one machine line: {ready, doing, blocked, counts, milestone,
                open_milestones, phase, phases, next_commands, parallelism,
                groups, next, sync, stale_complete, note, lease} (+ html:
                {file, changed} when --html also ran). `milestone` is the
                STATE.md-first read it always was; `open_milestones` is what
                the ROADMAP marks open, and is what every human surface
                names (Phase 22, BOARD-04)
    --plain     the machine contract, and ONLY the flag reaches it (Phase
                22): tab-separated rows (LANE, ID, PRIORITY, TITLE, EXTRA)
                plus PHASE/MILESTONE/DONE/NEXT/SYNC/NOTE meta rows; no color,
                no truncation. No condition of the environment selects it
    --brief     three lines: position, counts, next action
    --width N   render the board at N columns (overrides terminal size)
    --max-rows N  cap rows per bucket (default 15); overflow shows "+k more".
                Per BUCKET since Phase 21, not per lane: the cap follows the
                thing the list actually groups by
    --ascii     one-character stage symbols and "..." (also automatic on
                non-UTF-8 stdout). The +-| border set it used to swap in
                went out with the box-drawing renderer
    --color     always|never; default: auto. Precedence: --color >
                CAIRN_NO_COLOR > NO_COLOR (present and non-empty, even "0")
                > TERM=dumb > isatty(stdout). Color only: since Phase 22 a
                piped run already renders the board, so there is no renderer
                for this flag to opt into (see 5)
    --html P    write/refresh the HTML board at P and print one confirmation
                line. Composes with --planning-dir and --json (which reports
                the write instead of the line); rejected with --plain /
                --brief, which are stdout render modes (exit 2). The page has
                no row cap, so --max-rows / --width / --ascii / --color do
                not apply to it.

Exit codes:
    0 ok    2 usage (bad flag, or an unusable --html target/template)
    5 bd unavailable — not on PATH, or the pre-lane-query probe failed
      (bd present but the query itself broke). Can now happen on ANY
      render path (--json, --html, or the terminal/plain/brief default),
      always after this run's real output on stdout, never a silent,
      empty exit.
"""
import html
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BD = 5

# Test/override seam for the journal companion script (mirrors the existing
# CAIRN_GBSYNC/CAIRN_MAP/CAIRN_GATE env-seam convention and cairn-lease.py's
# identical CAIRN_JOURNAL seam — see CONVENTIONS.md's "Environment variable
# seams" note). Default: the sibling cairn-journal.py next to this script.
# phase_model()'s own observe call (Phase 16, D-01/D-02) shells out through
# this seam, resiliently — see journal_observe_phases().
CAIRN_JOURNAL = os.environ.get(
    "CAIRN_JOURNAL",
    str(Path(__file__).resolve().parent / "cairn-journal.py"))

USAGE = ("usage: cairn-status.py [--json] [--plain] [--brief] [--width N] "
         "[--max-rows N] [--ascii] [--color=always|never] "
         "[--planning-dir <dir>] [--html <path>]")

# MIN_INNER / MAX_INNER / N_LANES / STACK_BELOW / RAW_BELOW lived here until
# Phase 21. They sized a three-column kanban and the two width degrades it
# needed (columns >= 64 -> stacked lanes >= 40 -> raw list), all of which
# existed for one reason: three columns do not fit in a narrow terminal. One
# column fits in any terminal, so the degrades had nothing left to solve and
# went out with the constants.
SYNC_STALE_SECONDS = 24 * 3600
DEFAULT_MAX_ROWS = 15

# 4-bit SGR codes only — the terminal's own palette decides the hues.
SGR_BOLD = "1"
SGR_DIM = "2"
SGR_RED = "31"
SGR_GREEN = "32"
SGR_YELLOW = "33"
SGR_BORDER = "90"

# (name, lane color) — READY stays dim/default, DOING yellow, BLOCKED red.
LANES = (("READY", SGR_DIM), ("DOING", SGR_YELLOW), ("BLOCKED", SGR_RED))

VERSION_TOKEN = re.compile(r"\bv\d+(?:\.\d+)*\b")
CHECKED_PHASE = re.compile(r"^\s*-\s*\[[xX]\]\s.*?\bPhase\s+0*(\d+)\b")
ANY_PHASE = re.compile(r"^\s*-\s*\[[ xX]\]\s.*?\bPhase\s+0*(\d+)\b")
TABLE_PHASE_DONE = re.compile(
    r"^\s*\|\s*0*(\d+)[.)\s][^|]*\|.*\|\s*Complete\s*\|", re.IGNORECASE)
# Stricter than cairn-gate's TABLE_PHASE (which always demands `| Complete |`
# and so has no false-positive problem): a row only counts toward the phase
# TOTAL when its first cell actually reads like a phase — `Phase 3`,
# `3. Name`, `3) Name`. A bare leading number (`| 1 | User can sign up |`,
# success-criteria or traceability tables) is NOT a phase row.
TABLE_PHASE_ANY = re.compile(
    r"^\s*\|\s*(?:Phase\s+0*(\d+)\b[^|]*|0*(\d+)[.)][^|]*)\|",
    re.IGNORECASE)

# Phase-model parsing. A phase directory may carry an optional project-code
# prefix (myproj-03-auth), the same shape cairn-map resolves.
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")
PLAN_FILE = re.compile(r"^\d+-(\d+)-PLAN\.md$")
SUMMARY_FILE = re.compile(r"^\d+-(\d+)-SUMMARY\.md$")
# `— completed 2026-07-26` / `- completed 2026-07-26`, stripped by shape.
# Never split a roadmap line on the dash: titles carry their own em dashes
# ("Phase model — read what a phase actually is").
ROADMAP_COMPLETED = re.compile(
    r"\s*[—–-]?\s*completed\s+(\d{4}-\d{2}-\d{2})\s*$", re.IGNORECASE)
ROADMAP_TRAILING_PAREN = re.compile(r"\s*\(([^()]*)\)\s*$")
ROADMAP_PLANS = re.compile(r"^(\d+)\s*/\s*(\d+)\s+plans?$", re.IGNORECASE)
REQ_ID = re.compile(r"^[A-Z][A-Z0-9]*-\d+(?:\s*,\s*[A-Z][A-Z0-9]*-\d+)*$")

# The `## Milestones` list (roadmap_milestones(), phase 20). The heading match
# is anchored and plural on purpose: this repo's own ROADMAP carries a
# `## Milestone: v1.5 Legible State 🚧` heading immediately BELOW the list, and
# a looser pattern would open the section a second time on it and read the
# phase checkboxes that follow as milestone items.
MILESTONES_HEADING = re.compile(r"^##\s+Milestones\s*$", re.IGNORECASE)
ANY_H2 = re.compile(r"^##\s+")
MILESTONE_ITEM = re.compile(r"^\s*[-*]\s+(.+)$")
MILESTONE_BOLD = re.compile(r"\*\*([^*]+)\*\*")
# `Phases 20-29`, `Phases 3 - 4`, `Phase 7` — read from the text AFTER the
# bold span, never from inside it, so a milestone NAMED after a phase cannot
# be mistaken for a range.
MILESTONE_RANGE = re.compile(r"\bPhases?\s+0*(\d+)(?:\s*[-–—]\s*0*(\d+))?",
                             re.IGNORECASE)
# The SAME two markers roadmap_milestone() accepts, deliberately: two readers
# of "which cycle is open" that disagree would be the defect this phase exists
# to avoid, wearing a different name.
MILESTONE_IN_PROGRESS = re.compile(r"\(in progress\)", re.IGNORECASE)

# Label of the group holding work that belongs to no emitted milestone group.
# A module constant, not a literal at the emit site: phase 21 owns how this
# reads on the board and needs one place to change it. English like every
# other string this CLI prints (READY, PENDING PHASES, PURPOSE).
UNPHASED_KEY = "unphased"
UNPHASED_LABEL = "No milestone"
# Deliberately close to UNPHASED_LABEL, and they can share a screen. They say
# different things: this one is "the ROADMAP declares no open cycle", that one
# is "this issue names no phase any emitted group claims". The pair is
# exercised together by a test in tests/cairn-group-model.bats precisely so
# the closeness stays checked instead of assumed.
NO_OPEN_MILESTONE_LABEL = "No open milestone"

# "## Detalhe das fases" prose blocks (Phase 14): a THIRD phase-reference
# shape, an H3 heading, distinct in form from ANY_PHASE's checkbox line and
# TABLE_PHASE_ANY's table row — it can never collide with either.
DETAIL_PHASE_HEADING = re.compile(r"^###\s+Phase\s+0*(\d+)\b")
CARD_LABEL = re.compile(r"^\*\*Card:\*\*\s*(.*)$")
GOAL_LABEL = re.compile(r"^\*\*Goal:\*\*\s*(.*)$")
# The external tracker key of a whole phase, same block, same single pass.
# The label is `Tracker`, not `Card`: `**Card:**` already means the phase's
# one-sentence purpose in this roadmap, and reusing the word inside the same
# block would make the parser and the reader disagree about which one a line
# is.
TRACKER_LABEL = re.compile(r"^\*\*Tracker:\*\*\s*(.*)$")
# Recognizes ANY bold label line, both the colon-inside shape (`**Card:**`)
# and the colon-outside shape used by `**Requirements**:` elsewhere in the
# same blocks. Used only to know when to STOP collecting continuation text
# for a Card/Goal block, never to start it.
#
# The colon is REQUIRED, in one position or the other. It used to be optional
# (`\*\*:?`), which made every emphasized word at the start of a wrapped line
# look like a new label: phase 17's real Goal wraps onto a line beginning
# `**propõe** uma reconciliação`, so the purpose was flushed early and rendered
# as a sentence fragment with no closing period. Prose emphasis carries no
# colon; a label always does.
BOLD_LABEL = re.compile(r"^\*\*[^*]+\*\*:|^\*\*[^*]+:\*\*")

# Inline **bold** / __bold__ / *italic* / _italic_ inside a Card or Goal, with
# the marked words kept. Applied only to the purpose text, never to a label.
INLINE_EMPHASIS = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*|_([^_]+)_")

# Backend half of an `external_ref`, as cairn's own writers emit it:
# cairn-doctor.py --link-refs writes `gh-<number>`, a Jira sync writes
# `jira-<KEY>`. Stripped for DISPLAY only — see tracker_key().
TRACKER_BACKEND_PREFIX = re.compile(r"^(?:jira|gh|github|gl|gitlab|linear)-",
                                    re.IGNORECASE)


def die(msg, code):
    print(f"[cairn-status] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    opts = {"json": False, "plain": False, "brief": False, "width": None,
            "max_rows": DEFAULT_MAX_ROWS, "ascii": False, "color": "auto",
            "planning_dir": None, "html": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            opts["json"] = True
            i += 1
        elif arg == "--plain":
            opts["plain"] = True
            i += 1
        elif arg == "--brief":
            opts["brief"] = True
            i += 1
        elif arg == "--ascii":
            opts["ascii"] = True
            i += 1
        elif arg == "--width" or arg == "--max-rows":
            if i + 1 >= len(argv):
                die(f"{arg} needs a value\n{USAGE}", EXIT_USAGE)
            val = argv[i + 1]
            if not re.fullmatch(r"\d+", val) or int(val) < 1:
                die(f"{arg} must be a positive integer, got '{val}'\n{USAGE}",
                    EXIT_USAGE)
            opts["width" if arg == "--width" else "max_rows"] = int(val)
            i += 2
        elif arg == "--color" or arg.startswith("--color="):
            if arg == "--color":
                if i + 1 >= len(argv):
                    die(f"--color needs a value\n{USAGE}", EXIT_USAGE)
                val = argv[i + 1]
                i += 2
            else:
                val = arg.split("=", 1)[1]
                i += 1
            if val not in ("always", "never"):
                die(f"--color must be always or never, got '{val}'\n{USAGE}",
                    EXIT_USAGE)
            opts["color"] = val
        elif arg == "--planning-dir" or arg == "--html":
            if i + 1 >= len(argv):
                die(f"{arg} needs a value\n{USAGE}", EXIT_USAGE)
            opts["planning_dir" if arg == "--planning-dir" else "html"] = \
                argv[i + 1]
            i += 2
        else:
            die(f"unknown argument '{arg}'\n{USAGE}", EXIT_USAGE)
    if opts["json"] + opts["plain"] + opts["brief"] > 1:
        die(f"choose one of --json / --plain / --brief\n{USAGE}", EXIT_USAGE)
    if opts["html"] is not None and (opts["plain"] or opts["brief"]):
        # --html is a file render target, --plain/--brief are stdout render
        # modes: combining them would silently drop one. --json composes
        # (it reports the write under an "html" key).
        die("--html cannot be combined with --plain / --brief "
            f"(--json composes)\n{USAGE}", EXIT_USAGE)
    return opts


# ---------------------------------------------------------------- bd queries

def run_bd(args, root):
    cmd = ["bd", "-C", str(root)] + args + ["--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"bd {args[0]} failed: {proc.stderr.strip()}", EXIT_NO_BD)
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        die(f"bd {args[0]} returned invalid JSON: {e}", EXIT_NO_BD)
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def issue_priority(iss):
    p = iss.get("priority", 2)
    if isinstance(p, str):
        p = p.lstrip("Pp") or "2"
    try:
        return int(p)
    except (TypeError, ValueError):
        return 2


def as_str_list(val):
    """Defensive shape for bd list fields (labels, blocked_by): always a
    list of strings. A bare string becomes a one-item list (never iterated
    char by char), {id: ...} objects collapse to their id, None drops out,
    anything else is stringified."""
    if isinstance(val, str):
        val = [val]
    if not isinstance(val, list):
        return []
    out = []
    for x in val:
        if isinstance(x, dict):
            x = x.get("id")
        if x is not None:
            out.append(str(x))
    return out


PHASE_LABEL = re.compile(r"^phase-0*(\d+)$")


def issue_phase_ns(iss):
    """Phase numbers from an issue's phase-N labels (leading zeros
    tolerated — the same leniency cairn-gate applies to its regexes)."""
    out = set()
    for lab in as_str_list(iss.get("labels")):
        m = PHASE_LABEL.match(lab.strip())
        if m:
            out.add(int(m.group(1)))
    return out


def is_lease_issue(iss):
    """True when this is the phase-lease bookkeeping issue (Plan 15-01):
    a real bd issue, carrying the `lease` label, that is never tracked
    work — it must never show up as a phantom card in READY/DOING/BLOCKED,
    or inflate the done count, alongside issues that actually are (D-05).
    Mirrors NO_PHASE_EXEMPT's `lease` entry in cairn-doctor.py."""
    return "lease" in as_str_list(iss.get("labels"))


def in_done_phase(iss, done_set):
    """True when the issue is phase-labeled and EVERY phase label points at
    a roadmap-complete phase — an open issue the roadmap says was already
    delivered. A cross-phase issue stays live while any of its phases is
    still open, and an unlabeled issue is never stale."""
    ns = issue_phase_ns(iss)
    return bool(ns) and ns <= done_set


def trim_issue(iss):
    """Stable, minimal issue dict for the JSON summary.

    `external_ref` is bd's own field, carried RAW — prefix included, exactly
    the bytes `bd update --external-ref` stored (`cairn-doctor.py --link-refs`
    already writes it in production, as `gh-<n>`). The board strips the
    backend prefix for display via tracker_key(); this dict never does. A
    consumer that reads the JSON gets the datum, not a rendering of it.
    """
    return {"id": str(iss.get("id") or "?"),
            "title": iss.get("title", ""),
            "priority": issue_priority(iss),
            "assignee": iss.get("assignee") or None,
            "external_ref": iss.get("external_ref") or None,
            "labels": as_str_list(iss.get("labels")),
            "blocked_by": as_str_list(iss.get("blocked_by"))}


def fetch_lanes(root):
    """(ready, doing, blocked, closed) issue lists. The closed issues are
    kept whole, not counted: --html reads their phase-N labels to give each
    roadmap phase its real elevation. Every other renderer uses len()."""
    ready = run_bd(["ready", "-n", "0"], root)
    doing = run_bd(["list", "--status", "in_progress", "--limit", "0"], root)
    blocked = run_bd(["blocked"], root)
    closed = run_bd(["list", "--status", "closed", "--limit", "0"], root)
    # str() on the id: an explicit null must not TypeError the sort.
    key = lambda i: (issue_priority(i), str(i.get("id") or ""))  # noqa: E731
    return (sorted(ready, key=key), sorted(doing, key=key),
            sorted(blocked, key=key), closed)


def fetch_lease_status(root, active_phase, bd_ok):
    """data["lease"]: the active phase's lease status (Plan 15-01), or
    None when there is no active phase to ask about or bd itself could not
    be read.

    One subprocess call to `cairn-lease.py status <active_phase> --json`,
    mirroring cairn-doctor.py's check_phase_corroboration()/
    check_lease_stale() shell-out-and-parse-defensively shape: a
    subprocess failure or unparsable JSON degrades to None, never a
    crash. No TTL/staleness math is re-derived here — cairn-lease.py
    status --json is the single source for that.
    """
    if active_phase is None or not bd_ok:
        return None
    lease_script = Path(__file__).resolve().parent / "cairn-lease.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(lease_script), "status", str(active_phase),
             "--json", "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------- GSD reading

def read_lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def phase_dirs(planning_dir):
    """{phase number: dir} under <planning>/phases/, newest name wins ties."""
    out = {}
    root = planning_dir / "phases"
    if not root.is_dir():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        m = PHASE_DIR_PREFIX.match(d.name)
        if m:
            out.setdefault(int(m.group(1)), d)
    return out


def phase_disk_state(pdir):
    """How far a phase has actually got on disk: none/planned/executed/verified.

    Read from artifacts rather than from the roadmap checkbox, because the two
    disagree exactly when it matters — a phase can be planned and executed with
    nobody having ticked the box, and a box can be ticked over a phase whose
    SUMMARY was never written.
    """
    if pdir is None or not pdir.is_dir():
        return "none"
    names = [p.name for p in pdir.iterdir() if p.is_file()]
    has = lambda suffix: any(n.endswith(suffix) for n in names)  # noqa: E731
    if has("-VERIFICATION.md"):
        return "verified"
    if has("-SUMMARY.md"):
        return "executed"
    if has("-PLAN.md"):
        return "planned"
    return "none"


def bd_state(issues, n, roadmap_done_set):
    """bd's own verdict on phase n: none/closed/in_progress/open.

    Only issues whose phase-label set is entirely covered by phase n plus
    already-roadmap-complete phases count as evidence for n — an issue that
    also carries an undone OTHER phase's label is genuinely live work for
    THAT phase, not evidence against n. This mirrors in_done_phase's
    ALL-not-ANY discipline, so a legitimate cross-phase issue can never
    fabricate a false conflict for a phase it isn't really about.
    """
    allowed = roadmap_done_set | {n}
    qualifying = [iss for iss in issues
                  if n in issue_phase_ns(iss) and issue_phase_ns(iss) <= allowed]
    if not qualifying:
        return "none"
    statuses = [iss.get("status") for iss in qualifying]
    if all(s == "closed" for s in statuses):
        return "closed"
    if any(s == "in_progress" for s in statuses):
        return "in_progress"
    return "open"


def corroborate(n, disk_state, roadmap_complete, bd_val, bd_ok,
                state_md_active_phase):
    """(verdict, evidence, conflicts) for phase n from four independent
    reads: disk, bd, the roadmap checkbox, and STATE.md's active_phase
    pointer.

    Two severities only (D-09), each rule carrying its own justification for
    the one it gets:
      R1 blocks, disk vs bd — both are direct, artifact-backed reads of real
         work state; a disagreement between them is exactly what ROADMAP SC2
         and D-05 ("disk vs bd invalidates") describe.
      R2 blocks, roadmap vs disk — a checked box with nothing built is at
         least as dangerous as R1, and it fires independent of whether bd
         has any opinion at all. The reverse (disk verified, box unticked)
         is the existing, accepted lag phase_model() already documents and
         must NOT fire here.
      R3 informs, state_md vs disk — STATE.md's active_phase is a workflow
         POINTER, not a work-completion signal (D-05): it must never
         invalidate /cairn:work N on its own, so it can never outrank R1/R2.

    Verdict is "conflict" whenever conflicts is non-empty, else "unknown"
    when bd could not be read, else "ok". An unreadable bd (bd_ok False)
    never fabricates agreement (D-07) — its axis simply casts no vote, so R2
    and R3 can still fire and produce "conflict" without it, since neither
    needs bd to disagree. Two readable sources disagreeing is already a
    conflict: no majority, no tiebreak (D-06).

    Pure and silent by construction: no prompting, no blocking on input, no
    AskUserQuestion anywhere in this call graph (D-02) — this only reports,
    structured and deterministic; the prose in cairn/commands/*.md is what
    later offers the human options.
    """
    evidence = {
        "disk": disk_state,
        "bd": bd_val if bd_ok else "unknown",
        "roadmap": "complete" if roadmap_complete else "incomplete",
        "state_md": "active" if state_md_active_phase == n else None,
    }
    conflicts = []

    if bd_ok and bd_val != "none":
        disk_done = disk_state in ("executed", "verified")
        bd_done = bd_val == "closed"
        if disk_done != bd_done:
            conflicts.append({
                "severity": "blocks", "sources": ["disk", "bd"],
                "detail": (f"disk reports phase {n} {disk_state}, bd "
                          f"reports its issues {bd_val}"),
            })

    if roadmap_complete and disk_state not in ("executed", "verified"):
        conflicts.append({
            "severity": "blocks", "sources": ["roadmap", "disk"],
            "detail": (f"roadmap marks phase {n} complete, disk reports "
                      f"{disk_state}"),
        })

    if state_md_active_phase == n and disk_state in ("executed", "verified"):
        conflicts.append({
            "severity": "informs", "sources": ["state_md", "disk"],
            "detail": (f"STATE.md still points at phase {n}, disk already "
                      f"reports {disk_state}"),
        })

    if conflicts:
        verdict = "conflict"
    elif not bd_ok:
        verdict = "unknown"
    else:
        verdict = "ok"
    return verdict, evidence, conflicts


def phase_plan_counts(pdir):
    """(plans with a SUMMARY, total non-superseded plans) on disk, or None."""
    if pdir is None or not pdir.is_dir():
        return None, None
    plans, summaries = set(), set()
    for p in pdir.iterdir():
        if not p.is_file():
            continue
        m = PLAN_FILE.match(p.name)
        if m:
            plans.add(m.group(1))
            continue
        m = SUMMARY_FILE.match(p.name)
        if m:
            summaries.add(m.group(1))
    if not plans:
        return None, None
    return len(summaries & plans), len(plans)


def phase_has_research(pdir):
    """Whether this phase directory carries at least one `*-RESEARCH.md`
    file — the same suffix-match shape phase_disk_state() already uses for
    its own four suffixes: existence only, never mtime- or content-sensitive.
    """
    if pdir is None or not pdir.is_dir():
        return False
    return any(p.name.endswith("-RESEARCH.md") for p in pdir.iterdir()
              if p.is_file())


def phase_issue_counts(issues, n):
    """(done, total) bd issues carrying phase n's own `phase-N` label, by ANY
    match.

    Deliberately looser than bd_state()'s ALL-not-ANY qualifying filter: an
    issue that also carries an undone OTHER phase's label is still counted
    here. This is a raw completion tally for the phase card, not a
    corroboration read that must avoid fabricating a false conflict — do not
    reuse this count for corroboration, and do not reuse bd_state()'s
    qualifying list here. The two answer different questions.
    """
    done = total = 0
    for iss in issues:
        if n in issue_phase_ns(iss):
            total += 1
            if iss.get("status") == "closed":
                done += 1
    return done, total


def verification_status(pdir):
    """The literal `status:` value from a phase's `NN-VERIFICATION.md`
    frontmatter, or None when the file is absent, unreadable, or the field
    is missing/empty. Mirrors state_frontmatter()'s lenient
    regex-and-strip shape rather than a YAML lib.
    """
    if pdir is None or not pdir.is_dir():
        return None
    candidates = sorted(p for p in pdir.iterdir()
                        if p.is_file() and p.name.endswith("-VERIFICATION.md"))
    if not candidates:
        return None
    lines = read_lines(candidates[0])
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^status\s*:\s*(.+?)\s*$", line)
        if m:
            val = m.group(1).split("#", 1)[0].strip().strip("'\"").strip()
            return val or None
    return None


def plan_depends_on(pdir, dir_to_number):
    """Phase numbers this phase's plans declare in `depends_on:` frontmatter.

    The roadmap does not carry dependencies, but PLAN.md does, and that is
    what makes 'these two can run at the same time' computable rather than
    guessed. Entries may be phase dir names or bare numbers.
    """
    if pdir is None or not pdir.is_dir():
        return []
    deps = set()
    for p in sorted(pdir.iterdir()):
        if not (p.is_file() and PLAN_FILE.match(p.name)):
            continue
        lines = read_lines(p)
        if not lines or lines[0].strip() != "---":
            continue
        for line in lines[1:]:
            if line.strip() == "---":
                break
            m = re.match(r"^depends_on\s*:\s*\[(.*)\]\s*$", line)
            if not m:
                continue
            for raw in m.group(1).split(","):
                tok = raw.strip().strip("'\"").strip()
                if not tok:
                    continue
                if tok.isdigit():
                    deps.add(int(tok))
                    continue
                hit = dir_to_number.get(tok)
                if hit is None:
                    dm = PHASE_DIR_PREFIX.match(tok)
                    hit = int(dm.group(1)) if dm else None
                if hit is not None:
                    deps.add(hit)
    return sorted(deps)


def _split_roadmap_rest(rest):
    """(title, plans_done, plans_total, requirements, completed_on) from the
    text after `Phase N:` on a roadmap checkbox line.

    Order matters. The completion suffix carries its own em dash, and titles
    contain em dashes of their own ("Phase model — read what a phase actually
    is"), so the suffix is stripped by shape and never by splitting on the
    dash.
    """
    completed_on = None
    m = ROADMAP_COMPLETED.search(rest)
    if m:
        completed_on = m.group(1)
        rest = rest[:m.start()]
    plans_done = plans_total = None
    reqs = []
    m = ROADMAP_TRAILING_PAREN.search(rest)
    if m:
        inner = m.group(1).strip()
        pm = ROADMAP_PLANS.match(inner)
        if pm:
            plans_done, plans_total = int(pm.group(1)), int(pm.group(2))
            rest = rest[:m.start()]
        elif REQ_ID.match(inner):
            reqs = [t.strip() for t in inner.split(",") if t.strip()]
            rest = rest[:m.start()]
    # `- [x] **Phase 1: Auth** - Signup and login flows` is as common a shape
    # as the plain one. The bold span delimits the title; what follows it is a
    # description, not part of the name.
    close = rest.find("**")
    if close > 0:
        rest = rest[:close]
    title = rest.replace("**", "").replace("__", "").strip()
    title = title.strip("—–-").strip() or None
    return title, plans_done, plans_total, reqs, completed_on


def roadmap_phase_rows(planning_dir):
    """{n: partial phase dict} from ROADMAP.md.

    Two sources, merged: the checkbox lines carry the title, the requirement
    ids and the completion date; the milestone progress table carries the
    milestone and the plan counts. Neither alone is complete, which is why the
    board could only ever show a number.
    """
    rows = {}

    def slot(n):
        return rows.setdefault(n, {
            "number": n, "title": None, "milestone": None, "complete": False,
            "completed_on": None, "plans_done": None, "plans_total": None,
            "requirements": [], "purpose": None, "tracker": None,
        })

    # State machine for the "## Detalhe das fases" prose blocks, tracked
    # across the same single pass below (no second file read): detail_phase
    # is the `### Phase N:` block currently open (or None), collecting is
    # None/"card"/"goal"/"tracker" naming which label is being gathered,
    # buffer holds its continuation lines so far. card_text/goal_text/
    # tracker_text are resolved once after the loop, per phase number.
    detail_phase = None
    collecting = None
    buffer = []
    card_text, goal_text, tracker_text = {}, {}, {}

    def flush():
        # Joins the buffered continuation lines into one cleaned string and
        # files it under the label ("card"/"goal"/"tracker") currently being
        # collected, keyed by the detail block it belongs to. A no-op when
        # nothing is being collected.
        nonlocal collecting, buffer
        if collecting is not None:
            text = " ".join(b for b in buffer if b).strip()
            # Prose emphasis is markup for a markdown reader, not for a
            # terminal column — `**propõe**` in phase 17's Goal would reach
            # the board as four literal asterisks. Strip the bold/italic
            # markers and keep the words. Backticks are deliberately left
            # alone: in this project's prose they mark real identifiers, and
            # that distinction is worth carrying into the card.
            text = INLINE_EMPHASIS.sub(
                lambda m: next(g for g in m.groups() if g is not None), text)
            target = {"card": card_text, "goal": goal_text,
                      "tracker": tracker_text}[collecting]
            target[detail_phase] = text
        collecting = None
        buffer = []

    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = DETAIL_PHASE_HEADING.match(line)
        if m:
            flush()
            detail_phase = int(m.group(1))
            slot(detail_phase)
            continue

        if detail_phase is not None:
            m = CARD_LABEL.match(line)
            if m:
                flush()
                collecting = "card"
                buffer = [m.group(1).strip()]
                continue
            m = GOAL_LABEL.match(line)
            if m:
                flush()
                collecting = "goal"
                buffer = [m.group(1).strip()]
                continue
            m = TRACKER_LABEL.match(line)
            if m:
                # Same machine, same pass, same flush() — a third label, not
                # a second read of the file.
                flush()
                collecting = "tracker"
                buffer = [m.group(1).strip()]
                continue
            if collecting is not None:
                stripped = line.strip()
                if not stripped or BOLD_LABEL.match(line) or stripped == "---":
                    flush()
                    if stripped == "---":
                        # The `---` rule separates one phase's detail block
                        # from the next, per the file's own structure.
                        detail_phase = None
                    continue
                buffer.append(stripped)
                continue

        m = ANY_PHASE.match(line)
        if m:
            n = int(m.group(1))
            row = slot(n)
            if CHECKED_PHASE.match(line):
                row["complete"] = True
            after = line.split(f"Phase {m.group(1)}", 1)[-1]
            after = re.sub(r"^\s*0*\d*\s*[:.)]?\s*", "", after, count=1)
            title, pd, pt, reqs, done_on = _split_roadmap_rest(after)
            if title and not row["title"]:
                row["title"] = clean(title)
            if pt is not None:
                row["plans_done"], row["plans_total"] = pd, pt
            if reqs and not row["requirements"]:
                row["requirements"] = reqs
            if done_on and not row["completed_on"]:
                row["completed_on"] = done_on
            continue

        m = TABLE_PHASE_ANY.match(line)
        if not m:
            continue
        n = int(m.group(1) or m.group(2))
        row = slot(n)
        if TABLE_PHASE_DONE.match(line):
            row["complete"] = True
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells:
            head = re.sub(r"^(?:Phase\s+)?0*\d+\s*[.)]?\s*", "", cells[0],
                          count=1).strip()
            if head and not row["title"]:
                row["title"] = clean(head)
        for cell in cells[1:]:
            vm = re.match(r"^v\d+(?:\.\d+)*$", cell)
            if vm and not row["milestone"]:
                row["milestone"] = cell
                continue
            pm = re.match(r"^(\d+)\s*/\s*(\d+)$", cell)
            if pm and row["plans_total"] is None:
                row["plans_done"] = int(pm.group(1))
                row["plans_total"] = int(pm.group(2))
                continue
            dm = re.match(r"^(\d{4}-\d{2}-\d{2})$", cell)
            if dm and not row["completed_on"]:
                row["completed_on"] = cell
    flush()  # a Card/Goal block running to EOF with no trailing `---`

    for n in set(card_text) | set(goal_text) | set(tracker_text):
        slot(n)
        card, goal = card_text.get(n), goal_text.get(n)
        if card:
            purpose = card
        elif goal:
            # First sentence only (up to and including the first period);
            # the whole Goal text when no period exists.
            sm = re.search(r"^(.*?\.)(?:\s|$)", goal)
            purpose = sm.group(1) if sm else goal
        else:
            purpose = None
        rows[n]["purpose"] = clean(purpose) if purpose else None
        # A phase with a Tracker and no Card/Goal joins the union above and
        # gets `purpose = None` — which is what slot() already gave it, so
        # nothing that existed before this label moves.
        tracker = tracker_text.get(n)
        rows[n]["tracker"] = (clean(tracker) or None) if tracker else None

    return rows


def dep_target_ids(iss):
    """Ids this issue depends on, from either shape bd reports.

    The lane queries disagree about how they say it, and the disagreement is
    silent: `bd list` and `bd ready` return a `dependencies` array of
    {issue_id, depends_on_id}, while `bd blocked` returns a flat `blocked_by`
    list of ids and no `dependencies` at all. Reading only the first shape
    loses every edge whose target is still open — which is exactly the set the
    parallelism answer is about.
    """
    out = []
    for dep in iss.get("dependencies") or []:
        if isinstance(dep, dict):
            tid = str(dep.get("depends_on_id") or "").strip()
            if tid:
                out.append(tid)
    for raw in as_str_list(iss.get("blocked_by")):
        tid = raw.strip()
        if tid:
            out.append(tid)
    return out


def issue_phase_deps(issues):
    """{phase: {phases it depends on}} lifted from bd's own dependency edges.

    This is the dependency source that exists BEFORE a phase is planned. The
    PLAN.md `depends_on:` frontmatter only appears once someone has planned the
    phase, so relying on it alone would report every unplanned phase as
    independent — which is precisely the claim the parallelism section must not
    get wrong.
    """
    phases_of = {}
    for iss in issues:
        iid = str(iss.get("id") or "")
        if iid:
            phases_of[iid] = issue_phase_ns(iss)
    edges = {}
    for iss in issues:
        mine = phases_of.get(str(iss.get("id") or ""), set())
        if not mine:
            continue
        for tid in dep_target_ids(iss):
            for a in mine:
                for b in phases_of.get(tid, set()):
                    if a != b:
                        edges.setdefault(a, set()).add(b)
    return edges


def journal_observe_phases(root, phases):
    """Best-effort, single batched append of every phase's already-computed
    evidence/corroboration into cairn-journal.py's `observe` subcommand
    (Phase 16, D-01/D-02) — the concrete write path for JOUR-01's "phase
    state" and "corroboration verdict" categories. Exactly ONE subprocess
    call per phase_model() invocation, carrying every phase's own
    `{"phase", "evidence", "verdict"}` as one JSON array on stdin; never one
    call per phase.

    Purely a side effect appended AFTER corroborate() has already produced
    every value in the payload (see phase_model()'s own call site) —
    nothing here can feed back into corroboration itself, and nothing here
    is read by anything else in this module (JOUR-03: the journal is never
    consulted as a source of "current state"). On ANY failure — a nonzero
    exit, a missing script (FileNotFoundError), any other
    subprocess.SubprocessError, or output that is not valid JSON — prints a
    single `[cairn-status] warning: could not record journal observation:
    ...` line to stderr and returns. NEVER raises, NEVER calls die():
    recording history is bookkeeping, rendering the board is the real work
    (mirrors fetch_lease_status()'s and cairn-lease.py's
    journal_lease_event()'s identical resilience posture)."""
    payload = [{"phase": p["number"], "evidence": p["evidence"],
                "verdict": p["corroboration"]} for p in phases]
    cmd = [sys.executable, CAIRN_JOURNAL, "observe",
           "--project-dir", str(root), "--json"]
    try:
        proc = subprocess.run(cmd, input=json.dumps(payload),
                               capture_output=True, text=True)
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"[cairn-status] warning: could not record journal "
              f"observation: {e}", file=sys.stderr)
        return
    if proc.returncode != 0:
        detail = proc.stderr.strip() or f"exit {proc.returncode}"
        print(f"[cairn-status] warning: could not record journal "
              f"observation: {detail}", file=sys.stderr)
        return
    try:
        json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        print(f"[cairn-status] warning: could not record journal "
              f"observation: unparsable output ({e})", file=sys.stderr)


def phase_model(planning_dir, issues=None, bd_ok=True):
    """Every phase, described once, for all three surfaces to render from.

    The board, `--json` and the HTML page previously each re-derived what they
    needed from `(all, done)` int lists; anything richer had to be invented per
    surface, so the three could disagree. This is the single read: roadmap text
    merged with what is actually on disk, plus the dependency edges that make
    parallelism computable.

    Each row also carries additive corroboration keys — `evidence`,
    `corroboration`, `conflicts`, `needs_doctor` — computed by corroborate()
    from disk/bd/roadmap/STATE.md without ever widening `disk_state` itself.
    `bd_ok` (default True, unchanged behavior for every existing caller) says
    whether `issues` is a trustworthy read of bd; when False (bd unreachable)
    the bd axis reports "unknown" rather than fabricating agreement.

    Once every phase's evidence/corroboration below is computed, this
    function ends with exactly ONE batched call to journal_observe_phases()
    (Phase 16, D-01/D-02) — a pure, best-effort side effect appended AFTER
    corroborate() has already produced its answer for every phase. The
    journal is never read anywhere in this call graph and never feeds back
    into any value computed here, so a missing or broken journal changes
    zero bytes of this function's return value, only a stderr warning
    (JOUR-03).
    """
    rows = roadmap_phase_rows(planning_dir)
    dirs = phase_dirs(planning_dir)
    for n in dirs:
        rows.setdefault(n, {
            "number": n, "title": None, "milestone": None, "complete": False,
            "completed_on": None, "plans_done": None, "plans_total": None,
            "requirements": [], "purpose": None, "tracker": None,
        })
    dir_to_number = {d.name: n for n, d in dirs.items()}
    bd_edges = issue_phase_deps(issues or [])

    # Independent evidence corroborate() needs, read once — not the
    # disk-aware done_set below, which corroborate() must be free to
    # disagree with (a checked box with nothing on disk is exactly the
    # conflict R2 exists to catch).
    roadmap_done_set = {n for n, row in rows.items() if row.get("complete")}
    active_raw = normalize_phase(state_frontmatter(planning_dir)["active_phase"])
    active_phase_n = (int(active_raw) if active_raw is not None
                      and str(active_raw).isdigit() else None)
    # Project root: the same resolution main() already applies (planning_dir
    # is always root / ".planning", whichever branch resolved it) — reused
    # here rather than invented a second way, both for row["dir"] below and
    # for the observe call's --project-dir at the end of this function.
    root = planning_dir.parent

    out = []
    for n in sorted(rows):
        row = dict(rows[n])
        pdir = dirs.get(n)
        row["dir"] = str(pdir.relative_to(root)) if pdir else None
        row["disk_state"] = phase_disk_state(pdir)
        row["research_done"] = phase_has_research(pdir)
        row["issues_done"], row["issues_total"] = phase_issue_counts(
            issues or [], n)
        row["verify_status"] = verification_status(pdir)
        bd_val = bd_state(issues or [], n, roadmap_done_set)
        verdict, evidence, conflicts = corroborate(
            n, row["disk_state"], row["complete"], bd_val, bd_ok,
            active_phase_n)
        row["evidence"] = evidence
        row["corroboration"] = verdict
        row["conflicts"] = conflicts
        # The single, shared "route this phase to /cairn:doctor" predicate —
        # computed exactly once, here, and only ever READ by
        # phase_next_command()'s guard and next_commands()'s sort/blocked
        # fold below. Neither of them recomputes this condition.
        row["needs_doctor"] = (
            verdict == "unknown"
            or (verdict == "conflict"
                and any(c["severity"] == "blocks" for c in conflicts)))
        if row["plans_total"] is None:
            done, total = phase_plan_counts(pdir)
            row["plans_done"], row["plans_total"] = done, total
        deps = set(plan_depends_on(pdir, dir_to_number)) | bd_edges.get(n, set())
        row["depends_on"] = sorted(d for d in deps if d != n)
        out.append(row)

    # A dependency is satisfied by the WORK being done, not by the checkbox
    # being ticked. A phase verified on disk whose roadmap box nobody has
    # updated yet would otherwise keep every phase behind it reading "waits on
    # 10" long after 10 was finished.
    done_set = {p["number"] for p in out
                if p["complete"] or p["disk_state"] == "verified"}
    for p in out:
        p["blocked_by"] = [d for d in p["depends_on"] if d not in done_set]
        p["next_command"] = phase_next_command(p)
    # Every phase's evidence/corroboration is fully computed above — this is
    # the ONE place in the whole module where the batch gets observed into
    # the journal, resiliently (see journal_observe_phases()).
    journal_observe_phases(root, out)
    return out


def phase_next_command(p):
    """The next legal /cairn:* command for a phase, from its state on disk.

    Computed, never authored — which is the difference between a suggestion
    that stays true and one that rots the first time someone runs a command out
    of band.

    A phase the roadmap calls complete gets no command, whatever the disk says.
    Finished milestones have their phase dirs archived out of .planning/phases/,
    so reading disk state alone would tell the operator to go and plan phase 1
    again. When the checkbox and the artifacts genuinely disagree, that is
    /cairn:doctor's report to make, not a suggestion to act on.

    A needs_doctor phase (an "unknown" corroboration verdict, or a "blocks"
    conflict) is routed to /cairn:doctor instead of its disk-driven command —
    the one shared field computed once in phase_model(), never recomputed
    here.
    """
    if p["complete"]:
        # Deliberately unconditional and deliberately BEFORE the needs_doctor
        # guard below — a roadmap-complete phase keeps returning None whatever
        # corroboration says. A complete-but-conflicting phase is not "next
        # work to do"; it is a done phase that might be WRONG, and auditing
        # that is the ship gate's (13-04) and doctor's (13-03) job, never
        # next-command routing's. Do not reorder this check after the guard.
        return None
    if p.get("needs_doctor"):
        return "/cairn:doctor"
    return {
        "none": f"/cairn:plan {p['number']}",
        "planned": f"/cairn:work {p['number']}",
        "executed": f"/cairn:verify {p['number']}",
        "verified": None,
    }[p["disk_state"]]


def roadmap_phases(planning_dir, model=None):
    """(total, completed) phase numbers — derived from phase_model so the
    counts and the described list can never disagree."""
    model = phase_model(planning_dir) if model is None else model
    return ([p["number"] for p in model],
            [p["number"] for p in model if p["complete"]])


def find_phase(model, number):
    """The modelled phase with this number, or None. Accepts '02'/2/'2'."""
    n = normalize_phase(number)
    if n is None or not str(n).isdigit():
        return None
    n = int(n)
    for p in model:
        if p["number"] == n:
            return p
    return None


def active_phase_title(model, active_phase):
    """Title of the phase STATE.md points at — the one string that turns a
    footer reading `phase 10/12` into one that says what phase 10 IS."""
    p = find_phase(model, active_phase)
    return p["title"] if p else None


def phase_progress_text(p):
    """`2/3 plans` when the counts are known, else '' — one spelling, shared
    by every surface, so plan progress cannot read differently in two places."""
    if not p or p.get("plans_total") in (None, 0):
        return ""
    done = p.get("plans_done")
    done = 0 if done is None else done
    return f"{done}/{p['plans_total']} plans"


def phase_purpose_text(p):
    """What a phase IS, in one sentence — Plan 14-01's resolved `purpose`
    (Card verbatim, or the first sentence of Goal), with the same
    never-blank fallback shape `title` already uses elsewhere on this
    board. Shared by the terminal PURPOSE list and the HTML purpose
    paragraph so the two can only ever repeat the same sentence (D-04)."""
    return p.get("purpose") or p.get("title") or "(no purpose recorded)"


def phase_research_text(p):
    """`yes`/`—` — whether an `NN-RESEARCH.md` exists for this phase."""
    return "yes" if p.get("research_done") else "—"


def phase_issues_text(p):
    """`done/total`, or `—` when this phase has no bd issues mapped to it at
    all. Distinct from `0/N`, real information (issues exist, none closed
    yet) that must never collapse to a dash — only the true absence of any
    issue does."""
    total = p.get("issues_total")
    if not total:
        return "—"
    return f"{p['issues_done']}/{total}"


def phase_verify_text(p):
    """The verification verdict: the literal `status:` value from
    `NN-VERIFICATION.md` when one exists; `pending` when a SUMMARY exists but
    no VERIFICATION.md yet (`disk_state == "executed"`); else `—`."""
    if p.get("verify_status"):
        return p["verify_status"]
    if p.get("disk_state") == "executed":
        return "pending"
    return "—"


DISK_STATE_LABEL = {
    "none": "not planned",
    "planned": "planned",
    "executed": "executed",
    "verified": "verified",
}


def phase_state_text(p):
    """Where a phase stands, in words — the half of 'what should I run next?'
    that a phase number cannot answer."""
    if p.get("complete"):
        return "complete"
    return DISK_STATE_LABEL.get(p.get("disk_state"), "unknown")


def conflict_summary_text(p):
    """`word — detail` for a "conflict" verdict phase (D-03's one-line
    rendering): `conflict` when the phase carries a "blocks" item, else
    `diverges` when only "informs" items exist. The detail is that item's
    own `detail` string, already naming both sources (built by corroborate()
    in Plan 13-01) — never re-derived here, so the terminal panel and the
    HTML page can only ever repeat the exact same claim, not each
    independently summarize it (D-04)."""
    conflicts = p.get("conflicts") or []
    blocks = [c for c in conflicts if c["severity"] == "blocks"]
    item = blocks[0] if blocks else conflicts[0]
    word = "conflict" if blocks else "diverges"
    return f"{word} — {item['detail']}"


def conflict_marker(p, style):
    """(glyph, sgr) naming a phase's corroboration verdict — computed once so
    the terminal panel and the HTML CSS class can never point at a different
    severity for the same phase (D-04). "unknown" (bd unreachable, no
    conflicts computed) gets the same quiet g_stale/SGR_DIM treatment as a
    stale marker elsewhere on the board; a "blocks" item outranks "informs"
    within a "conflict" verdict, matching conflict_summary_text()'s pick."""
    if p.get("corroboration") == "unknown":
        return (style.g_stale, SGR_DIM)
    if any(c["severity"] == "blocks" for c in (p.get("conflicts") or [])):
        return (style.g_conflict, SGR_RED)
    return (style.g_informs, SGR_YELLOW)


def pending_phases(model):
    """Phases still to do, in roadmap order. Complete ones drop out."""
    return [p for p in model if not p["complete"]]


def phase_dependents(model, number):
    """Pending phases that wait on this one."""
    return [p["number"] for p in model
            if not p["complete"] and number in p["depends_on"]]


def join_numbers(ns):
    """`10`, `10 and 11`, `10, 11 and 12` — read as a sentence, not a list."""
    ns = [str(n) for n in ns]
    if not ns:
        return ""
    if len(ns) == 1:
        return ns[0]
    return f"{', '.join(ns[:-1])} and {ns[-1]}"


def parallelism(model):
    """What can proceed at the same time, right now, and how honest that is.

    Returns {runnable, blocked, note, declared}. `runnable` is every pending
    phase nothing still open blocks; two or more of those are independent of
    each other by construction, because a dependency between them would have
    blocked the later one.

    `declared` is the honesty flag. Independence is only as good as what is
    written down: a roadmap where nobody registered a dependency reports every
    phase as free, which is a statement about the records rather than about the
    work. The note says so instead of implying the graph was checked.
    """
    pending = pending_phases(model)
    runnable = [p for p in pending if not p["blocked_by"] and p["next_command"]]
    blocked = [p for p in pending if p["blocked_by"]]
    declared = any(p["depends_on"] for p in model)

    if not pending:
        note = "Nothing pending — the milestone is ready to ship."
    elif not runnable:
        note = ("Everything pending is waiting on something else. Finish "
                f"phase {join_numbers(sorted({d for p in blocked for d in p['blocked_by']}))} "
                "to open the next one up.")
    elif len(runnable) == 1:
        p = runnable[0]
        rest = f" Phase {join_numbers([b['number'] for b in blocked])} waits." \
            if blocked else ""
        note = (f"One phase can move: {p['next_command']}."
                + rest)
    else:
        # "alongside", never "then": the whole claim is that these do not have
        # to be sequenced, and a comma-then reads as an order.
        pair = " alongside ".join(p["next_command"] for p in runnable[:2])
        more = "" if len(runnable) < 3 else \
            f", and {len(runnable) - 2} more the same way"
        note = (f"Phases {join_numbers([p['number'] for p in runnable])} are "
                "independent — nothing still open blocks any of them, so they "
                f"can run at the same time rather than in sequence: {pair}"
                f"{more}. One agent per phase, or one worktree each.")
    if not declared and pending:
        note += (" No dependencies are declared anywhere in this roadmap, so "
                 "this reflects what is recorded, not a verified ordering.")
    return {"runnable": [p["number"] for p in runnable],
            "blocked": [p["number"] for p in blocked],
            "declared": declared, "note": note}


def next_commands(model, milestone=None):
    """The `/cairn:*` commands to run next, in order, each with its reason.

    Two things this is NOT. It is not authored: every command comes from the
    phase's own state on disk, so it cannot claim a phase needs planning when
    someone already planned it. And it is not ordered by phase number: the
    order comes from the dependency graph, so a later phase that is free
    outranks an earlier one that is waiting.

    Returns [{command, phase, title, reason, blocked}], unblocked first.

    A needs_doctor phase (the same stored field phase_next_command() reads —
    never recomputed here) reroutes both its reason and its blocked flag: an
    "unknown" verdict and a "blocks" conflict are both deprioritized behind
    every runnable phase, not just the conflict half — the self-contained
    ROADMAP SC4 guarantee (see 13-01's Objective for the doctor pre-flight's
    complementary half).
    """
    out = []
    for p in pending_phases(model):
        cmd = p["next_command"]
        if not cmd:
            continue
        needs_doctor = p.get("needs_doctor", False)
        if needs_doctor:
            # Takes priority over the blocked_by/waiting branches below: a
            # corroboration/doctor routing is not a dependency wait, so it
            # gets its own distinct message rather than borrowing theirs.
            reason = ("corroboration conflict — resolve via /cairn:doctor "
                      "before continuing")
        else:
            waiting = phase_dependents(model, p["number"])
            if p["blocked_by"]:
                reason = f"waits on phase {join_numbers(p['blocked_by'])}"
            elif waiting:
                reason = (f"nothing blocks it, and phase "
                          f"{join_numbers(waiting)} waits on it")
            else:
                reason = "nothing blocks it"
        out.append({"command": cmd, "phase": p["number"],
                    "title": p["title"], "reason": reason,
                    "blocked": bool(p["blocked_by"]) or needs_doctor})
    # Free work first, then by phase number. Sorting by number alone would put
    # a blocked phase 11 above a free phase 12 and read as an instruction.
    out.sort(key=lambda c: (c["blocked"], c["phase"]))

    if not out and model:
        ms = f" {milestone}" if milestone else ""
        out.append({"command": "/cairn:ship", "phase": None, "title": None,
                    "reason": "every phase is complete", "blocked": False})
        out.append({"command": "/cairn:milestone complete", "phase": None,
                    "title": None,
                    "reason": f"closes out{ms} once the gate passes",
                    "blocked": False})
    return out


def phase_groups(model, milestones, issues):
    """The hierarchy milestone → phase → issue, as a list of groups.

    A pure derivation of `model` + the roadmap's milestone list + the open
    issues, in the line of parallelism(model) and next_commands(model): no
    I/O, no bd, testable on its own, and a TOP-LEVEL key of the model rather
    than anything nested inside `phases[]` (D-02) — a consumer reading
    `phases[]` today reads exactly the same rows tomorrow.

    Each group is `{type, key, label, items}`, `type` being `"milestone"` or
    `"unphased"`. `items` is homogeneous across both types: always a list of
    `{phase, issues}` buckets, the unphased group carrying exactly one bucket
    whose `phase` is None. A consumer iterating `items` never has to know
    which kind of group it is holding. No group and no bucket carries a
    count: a count is len(), and a second spelling of the same number is a
    second thing that can disagree — which is the whole reason this file
    exists.

    A phase belongs to a milestone by, in this order: its own `milestone`
    cell from the roadmap's `## Progress` table (explicit and per-phase, so
    it wins), else the milestone line's `first..last` range (the only path in
    a roadmap that has no progress table, like this repository's own). Only
    phases that EXIST in `model` become buckets: inventing a phase out of a
    range is the same class of lie as naming an archived cycle. Groups come
    out in the roadmap's own order, filtered to the open ones (D-03: a
    milestone with no buckets is not emitted at all, so no group ever wears
    the last archived name); buckets inside a group come out by ascending
    phase number; the unphased group is always last.

    When NO milestone is open, ONE group is emitted carrying the PENDING
    phases, labelled NO_OPEN_MILESTONE_LABEL with `key` None (Phase 22,
    CairnGo-uz6). Until then that case produced zero groups and the board
    contradicted itself on one screen: `(no open work)` in the list while the
    footer and the table counted phases. The D-03 promise that mattered is
    intact and is now stronger — no group wears an archived name, AND the
    absence of an open cycle is stated positively instead of by silence.

    Issue placement reads ONE thing: `issue_phase_ns()`, the issue's own
    `phase-N` labels. An issue goes to the bucket of the SMALLEST phase it
    names among those some emitted group claims, and to the unphased group
    when it names none of them.

    This function deliberately does NOT read `dependencies`, `blocked_by`,
    `depends_on` or `dep_target_ids()`. Measured 2026-08-03: phase 26 renders
    as blocked by phase 9 — a cycle archived two milestones earlier — because
    dep_target_ids() counts every edge without looking at its type (a
    `discovered-from` edge, which /cairn:quick documents as provenance and
    not as a block, counts as a block) and because the pending filter tests
    against a completed-phase set an archived phase is never part of. That is
    FIX-04, phase 25's repair. Grouping by edge would import the whole
    confusion into the group model, so placement rests on labels alone.

    Only OPEN issues are passed in (main() calls with ready + doing +
    blocked): a group describes work still to do, and the lease bookkeeping
    issue was already filtered out upstream (Phase 15, D-05). Inside a
    bucket, issues keep the order the lanes deliver them in (READY, then
    DOING, then BLOCKED) — the model introduces no second ordering.

    No deduplication, and that is part of the contract: `doing` and
    `blocked` are independent bd queries, so one issue can legitimately
    arrive twice. Placement is per INPUT OCCURRENCE, so the multiset of ids
    across every bucket is exactly the multiset of ids on the lanes — which
    is what makes "nothing was lost and nothing was doubled" checkable by
    comparing the two sorted lists.
    """
    by_number = {p["number"]: p for p in model}
    explicit = {}
    for p in model:
        key = p.get("milestone")
        if key:
            explicit.setdefault(key, set()).add(p["number"])

    groups = []
    buckets = {}
    for ms in milestones:
        if not ms["open"]:
            continue
        numbers = set(explicit.get(ms["key"], ()))
        if ms["first"] is not None:
            # Range only for phases the progress table left unassigned: an
            # explicit cell naming another milestone is never overridden by
            # a range that happens to span this phase.
            numbers.update(n for n, p in by_number.items()
                           if not p.get("milestone")
                           and ms["first"] <= n <= ms["last"])
        items = []
        for n in sorted(numbers):
            if n not in by_number or n in buckets:
                continue
            bucket = {"phase": n, "issues": []}
            buckets[n] = bucket
            items.append(bucket)
        if not items:
            continue
        groups.append({"type": "milestone", "key": ms["key"],
                       "label": ms["label"], "items": items})

    if not any(ms["open"] for ms in milestones):
        # NO OPEN CYCLE (Phase 22, CairnGo-uz6). Without this, a roadmap that
        # declares no open milestone produced no phase bucket at all, and the
        # board contradicted itself on one screen — MEASURED 2026-08-06 on a
        # one-phase roadmap with no `## Milestones` section:
        #
        #     (no open work)          <- this list
        #   phase 1/1 Alpha           <- the footer
        #   PENDING PHASES  1         <- the table
        #
        # Three surfaces, two answers. With an issue carrying `phase-1` the
        # second symptom showed instead: the issue rendered under the loose
        # group and the phase line vanished, label and all.
        #
        # `type` stays "milestone" and `key` is None. A third type value would
        # make every `if group["type"] == "milestone"` already written stop
        # seeing this group; the group IS the grouping-by-milestone, it simply
        # has no milestone to name, and `key: None` says that in the model
        # while the label says it in words.
        #
        # PENDING phases only, not all of them: with no cycle to bound the
        # scope, "every phase since the project started" is a list that only
        # grows. Pending is exactly the set `PENDING PHASES` counts, and
        # making those two agree IS the fix.
        #
        # The condition is "no open cycle", never "no group was emitted". An
        # open cycle that claims no existing phase is a case nobody measured,
        # and inventing behaviour for it would be guessing; it falls through
        # to the old shape on purpose.
        items = []
        for p in pending_phases(model):
            n = p["number"]
            if n in buckets:
                continue
            bucket = {"phase": n, "issues": []}
            buckets[n] = bucket
            items.append(bucket)
        if items:
            groups.append({"type": "milestone", "key": None,
                           "label": NO_OPEN_MILESTONE_LABEL, "items": items})

    loose = {"phase": None, "issues": []}
    for iss in issues:
        named = sorted(n for n in issue_phase_ns(iss) if n in buckets)
        target = buckets[named[0]] if named else loose
        target["issues"].append(str(iss.get("id") or "?"))
    if loose["issues"]:
        groups.append({"type": "unphased", "key": UNPHASED_KEY,
                       "label": UNPHASED_LABEL, "items": [loose]})
    return groups


def state_frontmatter(planning_dir):
    """{milestone, active_phase, next_action} from STATE.md's YAML
    frontmatter, parsed by regex (no YAML lib) — missing keys are None."""
    out = {"milestone": None, "active_phase": None, "next_action": None}
    lines = read_lines(planning_dir / "STATE.md")
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^(milestone|active_phase|next_action)\s*:\s*(.+?)\s*$",
                     line)
        if m:
            val = m.group(2).split("#", 1)[0].strip().strip("'\"").strip()
            if val:
                out[m.group(1)] = val
    return out


def roadmap_milestone(planning_dir):
    """Milestone marked in progress in ROADMAP.md (🚧 / '(in progress)' line
    carrying a vN[.N...] token), or None."""
    for line in read_lines(planning_dir / "ROADMAP.md"):
        if "🚧" in line or MILESTONE_IN_PROGRESS.search(line):
            m = VERSION_TOKEN.search(line)
            if m:
                return m.group(0)
    return None


def roadmap_milestones(planning_dir):
    """[{key, label, open, first, last}] from the `## Milestones` list.

    The list, and only the list: the section opens at a `## Milestones`
    heading and closes at the next `## ` heading. Each list item carrying a
    bold span that STARTS with a version token is a milestone — the token is
    the key (`v1.1`), the whole bold span cleaned is the label
    (`v1.1 Surface`), and the `Phases A-B` (or lone `Phase A`, with
    `last == first`) read from the text AFTER the bold span is the range.
    A milestone whose line declares no range gets `first = last = None`.

    `open` is the marker on the milestone's OWN line — `🚧`, or
    `(in progress)` in any case, the same two roadmap_milestone() accepts.
    Everything else (`✅`, `shipped`, an archive link, no marker at all) is
    closed. Deliberately conservative: nothing infers openness from position
    in the list, from recency, or from STATE.md, because a group announcing
    an archived cycle is exactly the measured defect (2026-08-03, ten minutes
    after v1.4 was archived, the board still read `MILESTONE v1.4`) that this
    phase must not reproduce under a new key.

    Measured 2026-08-03: 5 milestones and exactly 1 open (`v1.5`, phases
    20-29) in this repository's own ROADMAP; 2 and 1 open (`v1.1`, phases
    3-4) in the test fixtures' roadmap; 0 in a roadmap with no such section.
    """
    out = []
    in_section = False
    for line in read_lines(planning_dir / "ROADMAP.md"):
        if MILESTONES_HEADING.match(line):
            in_section = True
            continue
        if not in_section:
            continue
        if ANY_H2.match(line):
            break
        m = MILESTONE_ITEM.match(line)
        if not m:
            continue
        item = m.group(1)
        bold = MILESTONE_BOLD.search(item)
        if not bold:
            continue
        text = bold.group(1).strip()
        token = VERSION_TOKEN.match(text)
        if not token:
            continue
        first = last = None
        rng = MILESTONE_RANGE.search(item[bold.end():])
        if rng:
            first = int(rng.group(1))
            last = int(rng.group(2)) if rng.group(2) else first
        out.append({
            "key": token.group(0),
            "label": clean(text),
            "open": "🚧" in line or bool(MILESTONE_IN_PROGRESS.search(line)),
            "first": first,
            "last": last,
        })
    return out


# ------------------------------------------------------------ sync staleness

def parse_ts(s):
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def humanize_age(seconds):
    if seconds >= 86400:
        return f"{int(seconds // 86400)}d"
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h"
    return f"{max(1, int(seconds // 60))}m"


def sync_status(root):
    """{configured, stale, detail, last_pull} from .cairn/sync.json +
    .cairn/state.json watermarks. stale = no pull yet, or oldest watermark
    older than 24h."""
    base = root / ".cairn"
    if not (base / "sync.json").is_file():
        return {"configured": False, "stale": None, "detail": None,
                "last_pull": None}
    try:
        state = json.loads((base / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    # The sync line is best-effort: a corrupt state.json (wrong JSON shape,
    # not just invalid JSON) degrades to "never pulled", never a traceback.
    if not isinstance(state, dict):
        state = {}
    last_pull = state.get("last_pull") or {}
    if not isinstance(last_pull, dict):
        last_pull = {}
    if not last_pull:
        return {"configured": True, "stale": True, "detail": "never pulled",
                "last_pull": {}}
    oldest_backend, oldest_dt = None, None
    for backend, ts in sorted(last_pull.items()):
        dt = parse_ts(ts)
        if dt is not None and (oldest_dt is None or dt < oldest_dt):
            oldest_backend, oldest_dt = backend, dt
    if oldest_dt is None:
        return {"configured": True, "stale": True, "detail": "never pulled",
                "last_pull": last_pull}
    age = (datetime.now(timezone.utc) - oldest_dt).total_seconds()
    stale = age > SYNC_STALE_SECONDS
    detail = f"last pull {humanize_age(age)} ago ({oldest_backend})"
    return {"configured": True, "stale": stale, "detail": detail,
            "last_pull": last_pull}


# ------------------------------------------------------------ next synthesis

def normalize_phase(value):
    """Canonical phase number: `active_phase: "02"` must build the label
    `phase-2`, not `phase-02` (cairn-gate tolerates leading zeros in all of
    its regexes — mirror that here). Non-numeric values pass through."""
    if value is None:
        return None
    s = str(value).strip()
    return str(int(s)) if s.isdigit() else s


def synthesize_next(ready, doing, milestone, active_phase, next_action,
                    done_phases=()):
    """ONE suggested next action.

    Rule kept from the prose command: bd wins for work items, STATE.md wins
    for workflow steps — an in-flight or phase-labeled ready issue is the
    work to do, but when no phase issue is ready the workflow step
    (STATE.md's next_action) outranks unrelated ready issues.
    Ready issues whose phase labels are all in done_phases (roadmap-complete)
    are never suggested — a stale open issue is /cairn:doctor's job, not the
    next action (an in_progress issue still wins: started work continues).
    Returns {kind, id, text, state_next}.
    """
    done_set = set(done_phases)
    ready = [i for i in ready if not in_done_phase(i, done_set)]
    # Every text below goes through clean(): a title with \n or \t would
    # otherwise forge extra rows in --plain / --brief / the board footer.
    out = {"kind": "none", "id": None, "text": "", "state_next": next_action}
    if doing:
        iss = doing[0]
        out.update(kind="continue", id=iss.get("id"),
                   text=clean(f"continue {iss.get('id')} — "
                              f"{iss.get('title', '')}"))
        return out
    if ready and active_phase:
        # Pair label m-<milestone>,phase-<active>; legacy repos without m-*
        # labels filter on the bare phase label (same leniency as cairn-gate).
        wanted = {f"phase-{active_phase}"}
        if milestone:
            wanted.add(f"m-{milestone}")
        in_phase = [i for i in ready
                    if wanted <= set(as_str_list(i.get("labels")))]
        if in_phase:
            iss = in_phase[0]
            out.update(kind="ready", id=iss.get("id"),
                       text=clean(f"start {iss.get('id')} — "
                                  f"{iss.get('title', '')}"))
            return out
    if next_action:
        text = clean(next_action)
        if active_phase:
            text += f" (phase {active_phase})"
        out.update(kind="workflow", id=None, text=clean(text))
        return out
    if ready:
        iss = ready[0]
        out.update(kind="ready", id=iss.get("id"),
                   text=clean(f"start {iss.get('id')} — "
                              f"{iss.get('title', '')}"))
        return out
    out["text"] = "nothing tracked — plan the next phase or run /cairn:doctor"
    return out


# ------------------------------------------------------- width and truncation

def char_width(ch):
    """Terminal cells one character occupies: 2 for W and F, 0 for combining
    marks / ZWJ / variation selectors, 1 for everything else.

    THE BOUNDARY THIS DRAWS, decided in Phase 22 (CairnGo-hbo) and written
    here because here is where the ruler lives:

        The board's column alignment is guaranteed in a WESTERN locale.
        It is NOT guaranteed in a CJK locale.

    east_asian_width returns `A` (ambiguous) for a large set of characters
    that occupy ONE cell in a Latin locale and TWO in a CJK one. This
    function counts them as 1, which is right in the first case and wrong in
    the second, and the script cannot tell which it is in.

    MEASURED 2026-08-06 on a --width 100 render of this repository: 53
    occurrences of `A`-width characters, 9 distinct —

        —  EM DASH        28      …  ELLIPSIS       8
        ·  MIDDLE DOT      4      ▶                 1
        á ê ó í é         12  ← accented letters, in the board's own prose

    Those 12 are the number that decides it. Swapping `—` for `-` and `…` for
    `...` would remove 36 of the 53 and fix NOTHING: this project's prose is
    Portuguese, and every accented letter is `A`. Choosing different glyphs
    cannot solve a problem the language itself creates.

    The alternative was resolving `A` from the environment, and it is
    refused for the reason this file already refuses it once, in Phase 21's
    choice of stage symbols: it would mean reading LANG/LC_CTYPE and deciding
    by heuristic what only the terminal emulator actually knows — "inventing
    that read would be inventing a source of truth". Solving half of it (the
    symbols) and guessing the other half (the prose) is worse than one honest
    boundary.

    What the Phase 21 defence still buys: the five stage symbols are all `N`,
    so the LIST's own columns hold in either locale. What remains exposed is
    the punctuation and the prose around them.
    """
    if ch == "‍" or "︀" <= ch <= "️":
        return 0                       # ZWJ / variation selectors
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def display_width(s):
    return sum(char_width(ch) for ch in s)


def truncate(s, width, ell):
    """Cut s to at most `width` display cells, appending `ell` when cut."""
    if width <= 0:
        return ""
    if display_width(s) <= width:
        return s
    budget = width - display_width(ell)
    if budget < 0:
        # Narrower than the ellipsis itself ("..." into 1-2 cells): degrade
        # to its head instead of returning something wider than width.
        return ell[:width]
    out, used = [], 0
    for ch in s:
        w = char_width(ch)
        if used + w > budget:
            break
        out.append(ch)
        used += w
    return "".join(out).rstrip() + ell


def wrap_spans(spans, width):
    """Greedy wrap of styled spans at `width` DISPLAY CELLS.

    The grouped list (Phase 21) never truncates a title, so it needs the
    other answer to "the text is longer than the room": a continuation line.
    textwrap cannot give it — textwrap counts characters, and this module
    measures everything with display_width(). Using two rulers in one file is
    how a CJK title silently overflows a column that says it fits.

    Breaks on whitespace only. A single token wider than `width` OVERFLOWS on
    a line of its own rather than being split: cutting an id or a URL in half
    is a form of truncation, and BOARD-03 excludes exactly the case where the
    line cannot fit. Leading whitespace is dropped from every continuation
    line and trailing whitespace from every line, so a wrapped line never
    carries padding it did not ask for.

    Returns a list of span lists (always at least one), each element having
    the same (text, sgr) shape render_spans() consumes — the styling of the
    dim tracker key and the dim done-phase marker survives the wrap.
    """
    if width <= 0:
        return [list(spans)]
    tokens = []
    for text, sgr in spans:
        for part in re.split(r"(\s+)", text):
            if part:
                tokens.append((part, sgr))
    lines, cur, used = [], [], 0
    for tok, sgr in tokens:
        w = display_width(tok)
        if tok.isspace():
            if cur:                       # never open a line with a space
                cur.append((tok, sgr))
                used += w
            continue
        if cur and used + w > width:
            while cur and cur[-1][0].isspace():
                cur.pop()
            lines.append(cur)
            cur, used = [], 0
        cur.append((tok, sgr))
        used += w
    while cur and cur[-1][0].isspace():
        cur.pop()
    if cur:
        lines.append(cur)
    return lines or [[("", None)]]


# C0 (minus \t and \n, which the whitespace collapse turns into spaces),
# DEL, and C1 — ESC, CSI, OSC and friends. Titles can come from remote
# trackers via sync-pull, so control bytes are attacker-reachable.
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def clean(text):
    """One safe display line: strip control bytes, collapse whitespace."""
    return re.sub(r"\s+", " ", CONTROL_CHARS.sub("", str(text))).strip()


def tracker_key(ref):
    """The human half of an `external_ref`, for display on the board.

    `jira-DTP-142` is two things joined: a backend name nobody quotes and the
    key everybody does. The board shows the second. A ref that is already bare
    (`DTP-142`) shows as it is.

    DELIBERATE DEVIATION from 29-05-PLAN.md, which lists `gh-` among the
    prefixes to strip unconditionally. MEASURED: cairn-doctor.py --link-refs
    writes `gh-<number>` in production, so the most common real ref in this
    repository is `gh-42`, and stripping it leaves `42` — a bare digit sitting
    next to an issue id on a fixed-width board, naming nothing. So the prefix
    comes off only when what survives still identifies the issue on its own,
    which a pure number does not: `jira-DTP-142` -> `DTP-142`, while `gh-42`
    keeps its prefix.

    Display only. The stored ref is never rewritten — `--json` carries it raw,
    prefix included, so nothing downstream has to guess what was cut.
    """
    ref = clean(ref)
    if not ref:
        return ""
    stripped = TRACKER_BACKEND_PREFIX.sub("", ref, count=1)
    if stripped and not stripped.isdigit():
        return stripped
    return ref


# ------------------------------------------------------------------ rendering

class Style:
    """Color + glyph decisions, resolved once."""

    def __init__(self, opts):
        enc = (getattr(sys.stdout, "encoding", None) or "").lower()
        self.ascii = opts["ascii"] or "utf" not in enc
        self.color = self._color_enabled(opts)
        if self.ascii:
            # The box-drawing vocabulary (tl/tm/tr, bl/bm/br, h, v) lived
            # here until Phase 21. Its only reader was render_board, and the
            # AST says nothing else in this file — not render_plain, not the
            # phase panel, not the HTML — ever read one. Write-only state is
            # worse than absent state: it tells the next reader a grid still
            # exists somewhere.
            self.ell, self.sep = "...", " | "
            self.g_next, self.g_dep, self.g_who = ">", "<-", "@"
            self.g_stale = "*"
            self.g_conflict, self.g_informs = "x", "!"
            self.g_card = "#"
            # Stage symbols, ASCII fallback: exactly ONE character each, which
            # is what makes "the columns close aligned in both modes" a
            # mechanical claim — every column of the grouped block lands on
            # the same cell as its Unicode counterpart, because 1 cell == 1
            # char. `x`, `!`, `*` and `#` were rejected not on taste but on
            # collision inside the same output: they already are g_conflict,
            # g_informs, g_stale and g_card.
            self.s_none, self.s_planned, self.s_doing = ".", "o", "O"
            self.s_done, self.s_blocked = "v", "~"
        else:
            self.ell, self.sep = "…", " · "
            self.g_next, self.g_dep, self.g_who = "▶", "⧗", "◆"
            self.g_stale = "·"
            self.g_conflict, self.g_informs = "✗", "⚠"
            # External tracker card. U+29C9 is east-asian-width N, like the
            # ⧗ already used for dependencies — one cell everywhere, so it
            # can never widen a lane on a CJK terminal.
            self.g_card = "⧉"
            # Stage symbols (Phase 21, BOARD-02). MEASURED 2026-08-05 with
            # unicodedata.east_asian_width: all five are `N`, i.e. one cell
            # everywhere. `○` U+25CB, `◑` U+25D1 and `◆` U+25C6 were the
            # obvious candidates and all three are `A` — one cell in a Latin
            # locale, TWO in a CJK one. char_width() above returns 2 only for
            # W and F, so an `A` symbol counts 1 here and draws 2 there, and
            # nothing in this script can detect the difference (it reads no
            # locale, and inventing that read would be inventing a source of
            # truth). The defense is to not use `A` at all, which is why
            # tests/cairn-grouped-board.bats asserts the property through
            # unicodedata and never through how the glyph looks.
            self.s_none, self.s_planned, self.s_doing = "◌", "◔", "◕"
            self.s_done, self.s_blocked = "✓", "⧗"

    def asciify(self, text):
        """Downgrade the punctuation this script itself injects. Issue titles
        keep their own characters (the final print falls back to
        errors='replace' on a non-Unicode stdout)."""
        if not self.ascii:
            return text
        return text.replace("—", "-").replace("·", "|").replace("…", "...")

    @staticmethod
    def _color_enabled(opts):
        # Precedence: --color > CAIRN_NO_COLOR > NO_COLOR (present and
        # non-empty, even "0" — no-color.org) > TERM=dumb > isatty(stdout).
        if opts["color"] == "always":
            return True
        if opts["color"] == "never":
            return False
        if os.environ.get("CAIRN_NO_COLOR"):
            return False
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("TERM") == "dumb":
            return False
        return sys.stdout.isatty()

    def paint(self, text, sgr):
        if self.color and sgr and text:
            return f"\x1b[{sgr}m{text}\x1b[0m"
        return text


def render_spans(spans, style):
    # Color is applied AFTER truncation/padding: spans carry plain text that
    # was measured and padded first, and every span closes with a reset, so
    # no style ever leaks into a border.
    return "".join(style.paint(text, sgr) for text, sgr in spans)


# --------------------------------------------------------- the grouped list
#
# Phase 21 replaces the three-lane kanban on the human render path. The lanes
# spent the terminal's width divided by three and cut every title at ~28
# cells; with 40 tasks READY became 40 rows and the other two lanes stood
# empty. What goes in its place is ONE list, grouped by the model Phase 20
# built (open milestone -> phase -> task), each row carrying its stage in a
# single-cell symbol and its title whole.

GROUP_INDENT = ""
PHASE_INDENT = "  "
ISSUE_INDENT = "      "
NO_WORK_TEXT = "(no open work)"
# Below this many cells left for the body, the row stops trying to put the
# title beside the id and drops it to its own indented lines. MEASURED at
# --width 30 with an 11-cell id: the inline budget is 9 cells, so every word
# lands on a line of its own — nothing truncated, and nothing readable
# either. The stacked form gives the same row 22 cells. 24 is the smallest
# budget that still holds a short phrase per line.
NARROW_BODY = 24


def stage_symbol(kind, obj, style):
    """The stage of one row, as (symbol, sgr). ONE decision point.

    A phase row reads its own disk state: complete or `verified` -> done,
    `executed` -> in progress, `planned` -> planned, `none` -> not planned.

    A task row reads the LANE it arrived on: BLOCKED -> blocked, DOING -> in
    progress, READY -> planned.

    A phase row DELIBERATELY never renders the blocked symbol, even when
    `blocked_by` is non-empty. MEASURED 2026-08-03 and still true: phase 26
    renders as blocked by phase 9, a cycle archived two milestones earlier,
    because dep_target_ids() counts every edge without looking at its type
    and the pending filter tests against a completed-phase set an archived
    phase is never part of (FIX-04, phase 25's repair). phase_groups()
    refused to read edges for exactly this reason — its own docstring says
    so — and painting a phase blocked from the same data would import the
    whole confusion into a new surface. A phase symbol describes progress on
    disk and nothing else; the `waits` column of the phase panel keeps
    telling the other story where it is already understood.
    """
    if kind == "phase":
        if obj.get("complete") or obj.get("disk_state") == "verified":
            return style.s_done, SGR_GREEN
        return ({"executed": style.s_doing,
                 "planned": style.s_planned}.get(obj.get("disk_state"),
                                                 style.s_none), SGR_DIM)
    lane_sgr = dict(LANES).get(kind)
    return ({"BLOCKED": style.s_blocked,
             "DOING": style.s_doing}.get(kind, style.s_planned), lane_sgr)


def group_rows(data, max_rows):
    """The grouped list as rows, with no width and no color decided yet.

    Structure comes from `data["groups"]` — the Phase 20 model — and is never
    re-derived here: open milestones in the roadmap's order, buckets by
    ascending phase, `unphased` last. Each row is one of:

        {"kind": "group", "label": str}
        {"kind": "phase", "number": int, "phase": <model row>}
        {"kind": "issue", "lane": str,   "issue": <raw bd dict>}
        {"kind": "more",  "count": int}

    An id is resolved to its issue through a FIFO queue per id, filled from
    `data["_lanes"]` in (READY, DOING, BLOCKED) order. That is not
    bookkeeping fussiness, it is phase_groups()' documented contract: it
    places PER INPUT OCCURRENCE and does not deduplicate, because
    `bd list --status in_progress` and `bd blocked` are independent queries
    and one issue can legitimately arrive twice. Consuming a per-id queue in
    the order the ids appear reproduces the exact (occurrence, lane) pairing
    without inventing a second placement — which is the one thing this file
    exists to prevent. An id with no queue left (unreachable today:
    phase_groups() is only ever handed what the lanes produced) still renders,
    on the READY lane, from a minimal dict — never dropped in silence.

    `max_rows` caps issues PER BUCKET, with the same `+k more` row the lanes
    used. A lane was the container; a bucket is the container now. Group and
    phase rows are never capped: they are the structure, not the content.
    """
    queues = {}
    for (lane, _), items in zip(LANES, data.get("_lanes") or []):
        for iss in items:
            queues.setdefault(str(iss.get("id") or "?"), []).append(
                (lane, iss))

    by_number = {p["number"]: p for p in (data.get("phases") or [])}
    rows = []
    for group in data.get("groups") or []:
        rows.append({"kind": "group", "label": group["label"]})
        for bucket in group["items"]:
            n = bucket["phase"]
            if n is not None and n in by_number:
                rows.append({"kind": "phase", "number": n,
                             "phase": by_number[n]})
            ids = bucket["issues"]
            for iid in ids[:max_rows]:
                queue = queues.get(iid)
                lane, iss = queue.pop(0) if queue else ("READY", {"id": iid})
                rows.append({"kind": "issue", "lane": lane, "issue": iss})
            if len(ids) > max_rows:
                rows.append({"kind": "more", "count": len(ids) - max_rows})
    return rows


def counts_parts(data, style):
    """`ready N · doing N · blocked N · done N` as spans.

    ONE spelling, two surfaces: --brief has printed this line since Phase 10,
    and the grouped list needs it because the lane headers that used to carry
    the four numbers (`READY (3)`) are gone. Extracted rather than copied —
    a second copy is a second thing that can drift.
    """
    c = data["counts"]
    return [("ready ", None), (str(c["ready"]), None), (style.sep, SGR_DIM),
            ("doing ", None), (str(c["doing"]), SGR_YELLOW),
            (style.sep, SGR_DIM),
            ("blocked ", None), (str(c["blocked"]), SGR_RED),
            (style.sep, SGR_DIM),
            ("done ", None), (str(c["closed"]), SGR_GREEN)]


def issue_body_spans(lane, iss, style):
    """A task row's text after the id: the title, then its suffixes.

    Everything here WRAPS and nothing here is ever dropped. The lane cell was
    a fixed width, so make_cell() had to rank its suffixes and shed them
    (the tracker key first, then the rest, the title always winning); a row
    that wraps has nothing to rank. The property that replaces that
    precedence is stronger: at every width, every suffix is on the line.

    A blocked row names EVERY blocker, not just the first, and names them in
    words rather than reusing the hourglass the stage symbol already spent —
    success criterion 4 is that the row says who blocks it without a second
    command, and `blocked by brd-001, brd-007` says it.
    """
    spans = [(clean(iss.get("title", "")), None)]
    if lane == "BLOCKED" and as_str_list(iss.get("blocked_by")):
        names = ", ".join(clean(b)
                          for b in as_str_list(iss.get("blocked_by")))
        spans += [("  ", None), (f"blocked by {names}", SGR_RED)]
    elif lane == "DOING" and iss.get("assignee"):
        spans += [("  ", None), (style.g_who, SGR_YELLOW),
                  (" " + clean(iss["assignee"]), None)]
    if iss.get("_stale"):
        spans += [("  ", None), (style.g_stale + "done-phase", SGR_DIM)]
    if iss.get("external_ref"):
        key = tracker_key(iss["external_ref"])
        if key:
            spans += [("  ", None), (style.g_card, SGR_DIM),
                      (" " + key, SGR_DIM)]
    return spans


def render_groups(data, width, max_rows, style):
    """The grouped list: counts, then open milestone -> phase -> task.

    Column widths are computed once over every row that will actually print,
    so every title starts on the same cell whatever the id lengths are. The
    prefix (indent + symbol + id/number) is fixed width; the body wraps into
    what is left with wrap_spans(), and each continuation line is indented to
    the body column. Nothing is truncated at any width — that is BOARD-03,
    and it is why `truncate()` no longer appears on this path even though it
    still serves the phase panel and the footer.

    No count is printed on a group or phase row. A count is len(), and the
    numbers are already spelled once at the top and once in the phase panel;
    a third spelling is a third thing that can disagree, which is the reason
    phase_groups() refused to store one in the first place.
    """
    rows = group_rows(data, max_rows)
    lines = [render_spans(counts_parts(data, style), style)]
    if not rows:
        lines.append("")
        lines.append(render_spans([(PHASE_INDENT + NO_WORK_TEXT, SGR_DIM)],
                                  style))
        lines.append("")
        return lines

    ids = [clean(str(r["issue"].get("id") or "?"))
           for r in rows if r["kind"] == "issue"]
    id_w = max((display_width(i) for i in ids), default=0)
    num_w = max((len(str(r["number"])) for r in rows if r["kind"] == "phase"),
                default=1)

    for row in rows:
        if row["kind"] == "group":
            lines.append("")
            lines.append(render_spans(
                [(GROUP_INDENT + style.asciify(clean(row["label"])),
                  SGR_BOLD)], style))
            continue
        if row["kind"] == "more":
            lines.append(render_spans(
                [(ISSUE_INDENT + f"+{row['count']} more", SGR_DIM)], style))
            continue
        if row["kind"] == "phase":
            p = row["phase"]
            glyph, sgr = stage_symbol("phase", p, style)
            indent = PHASE_INDENT
            prefix = [(indent, None), (glyph, sgr), (" ", None),
                      (str(row["number"]).rjust(num_w), None), ("  ", None)]
            body = [(style.asciify(clean(p.get("title") or "(untitled)")),
                     None)]
        else:
            iss = row["issue"]
            glyph, sgr = stage_symbol(row["lane"], iss, style)
            iid = clean(str(iss.get("id") or "?"))
            indent = ISSUE_INDENT
            prefix = [(indent, None), (glyph, sgr), (" ", None),
                      (iid.ljust(id_w + len(iid) - display_width(iid)),
                       SGR_BOLD if issue_priority(iss) <= 1 else None),
                      ("  ", None)]
            body = issue_body_spans(row["lane"], iss, style)
        prefix_w = sum(display_width(t) for t, _ in prefix)
        if width - prefix_w < NARROW_BODY:
            # Too narrow to sit the body beside the id: the id keeps its own
            # line and the body drops below it, hanging two cells past this
            # row's own indent. Nothing is lost either way — these are the
            # same bytes in a shape a 30-column terminal can actually read.
            # The hang is deliberately 2 past the row indent and not the
            # body column: at these widths the body column IS most of the
            # line, so aligning to it would leave nowhere to wrap into.
            lines.append(render_spans(prefix, style).rstrip())
            hang = indent + "  "
            hang_w = display_width(hang)
            for cont in wrap_spans(body, width - hang_w):
                lines.append(render_spans([(hang, None)] + cont,
                                          style).rstrip())
            continue
        wrapped = wrap_spans(body, width - prefix_w)
        lines.append(render_spans(prefix + wrapped[0], style).rstrip())
        for cont in wrapped[1:]:
            lines.append(render_spans([(" " * prefix_w, None)] + cont,
                                      style).rstrip())
    lines.append("")
    return lines


def meta_parts(data, style, include_done=True):
    """`phase X/Y title · milestone · done: N` as spans (segments drop out
    when unknown).

    The title comes from the shared phase model. `phase 10/12` alone says
    where you are on a count and nothing about what you are doing.

    The milestone segment is milestone_label() since Phase 22 (BOARD-04): the
    cycle the ROADMAP marks open, or `no open milestone` in words. It is
    printed whenever there IS a roadmap position to speak of, and skipped
    entirely when there is not — announcing "no open milestone" about a repo
    with no roadmap at all answers a question nobody asked, and the
    `(no roadmap position)` fallback below is already the right answer there.
    """
    parts = []
    phase = data["phase"]
    has_roadmap = phase["active"] is not None and phase["total"]
    if has_roadmap:
        head = [(f"phase {phase['active']}/{phase['total']}", None)]
        if phase.get("title"):
            head.append((f" {style.asciify(phase['title'])}", SGR_DIM))
        parts.append(head)
    if has_roadmap or data.get("open_milestones"):
        parts.append([(style.asciify(milestone_label(data)), None)])
    if include_done:
        parts.append([("done: ", None),
                      (str(data["counts"]["closed"]), SGR_GREEN)])
    if not parts:
        parts.append([("(no roadmap position)", SGR_DIM)])
    spans = []
    for i, part in enumerate(parts):
        if i:
            spans.append((style.sep, SGR_DIM))
        spans += part
    return spans


PHASE_TABLE_FLOOR = 18       # target minimum for the `phase` column
STATE_TABLE_FLOOR = 16       # enough for "x conflict -" (12 cells) plus a
                              # margin under both --ascii (3-cell ellipsis)
                              # and unicode (1-cell ellipsis)
RSCH_W, PLANS_W, ISSUES_W = 5, 6, 7
VERIFY_W, WAITS_W, NEXT_W = 16, 7, 16   # 16: fits "needs-revision" (14) whole

# The hard minimums, used only when the comfortable FLOORs above do not fit
# (Phase 22, CairnGo-cdx). MEASURED 2026-08-06 against the real strings:
# `not planned` is 11 cells and is the longest of the four state labels, so
# 11 is where `state` stops before it starts cutting a word it could have
# shown whole; 8 is what the `phase` column already gets at --width 100,
# which makes it a value the board has always rendered rather than one
# invented here.
PHASE_TABLE_MIN = 8
STATE_TABLE_MIN = 11

# The optional columns, in VISUAL order (this is the order they print in),
# each with its natural width and its floor.
#
# THE FLOOR RULE, and it is one rule: a column never shrinks below its own
# HEADER. A column whose title renders as `issu…` is worse than a column that
# is absent and named — the first lies about being there, the second says it
# left. `verify` is the one floor above its header (6): `verified` and
# `pending` are 8 and 7 cells, and a verdict column that cannot show its own
# most common verdicts is not carrying information, it is carrying an
# ellipsis.
PANEL_COLUMNS = (("rsch", RSCH_W, 4), ("plans", PLANS_W, 5),
                 ("issues", ISSUES_W, 6), ("verify", VERIFY_W, 8),
                 ("waits", WAITS_W, 5))

# SACRIFICE ORDER — shrink in this order, then drop in this order. Each
# position has a reason, because an order without one is taste:
#   waits   the same fact is spelled out in words in PURPOSE below
#   rsch    a yes/— signal that rarely decides anything on its own
#   verify  only ever speaks about a phase that already executed
#   issues  \ the two that answer "how far has it got", kept longest
#   plans   /
# `#`, `phase`, `state` and `next` are the core and never leave: without them
# the table answers neither "which phase" nor "what do I do with it".
PANEL_SACRIFICE = ("waits", "rsch", "verify", "issues", "plans")
# Cells the phase TITLE must keep before a `**Tracker:**` key is allowed to
# reserve room beside it. 12 is a readable abbreviation ("Phase model…");
# below it the key falls out and the title takes the whole column back.
TRACKER_TITLE_FLOOR = 12


def panel_note_lines(text, width, style):
    """One dim, indented, WRAPPED note under the table.

    Wrapped and not truncated, for a reason specific to what these notes say:
    both of them are about something not fitting, and a message about not
    fitting that itself runs off the edge is the exact joke CairnGo-cdx was.
    `width - 2` is the two-cell indent every line of this section carries.
    """
    out = []
    for chunk in textwrap.wrap(style.asciify(text), max(20, width - 2)) or [""]:
        out.append(render_spans([("  ", None), (chunk, SGR_DIM)], style))
    return out


def panel_columns(width, num_w):
    """Which optional columns the table can afford at `width`, and how wide.

    Returns `(present, widths, dropped, available)`: the optional columns
    still printing in visual order, their resolved widths, the names that had
    to go, and the cells left over for `phase` + `state`. An `available`
    below PHASE_TABLE_MIN + STATE_TABLE_MIN means not even the core fits and
    the table must not print at all.

    WHY THIS FUNCTION EXISTS (CairnGo-cdx). The six optional widths used to be
    summed unconditionally, so the table had a FLOOR it silently exceeded:
    MEASURED 2026-08-06, `76 + num_w - 1 + len(next)` cells — 90 in the test
    fixture, 92 in this repository — meaning it overflowed at EVERY width from
    30 to 89, with `phase` collapsed to a single `…` and the other six columns
    not giving up one character. It was already a defect; Phase 22 made it
    urgent, because PIPE-02 sends a flagless non-TTY run through this table at
    80 columns.

    The order is shrink-then-drop, both in PANEL_SACRIFICE order. Shrinking
    first is what keeps a column on screen when it is one cell short of
    fitting; dropping second is what stops a column from shrinking into an
    ellipsis. A column that shrank does NOT grow back when a later column is
    dropped: re-solving after every drop would be a better packing and a
    worse contract, because the width a column ends up with would depend on
    what happened to a column somewhere else.
    """
    widths = {n: w for n, w, _ in PANEL_COLUMNS}
    floors = {n: f for n, _, f in PANEL_COLUMNS}
    present = [n for n, _, _ in PANEL_COLUMNS]

    def available():
        # margin(2) + `#` + every present column + `next`, with a 2-cell
        # gutter between each pair. Columns = 1 + 1 + 1 + len(present) + 1,
        # so gutters = len(present) + 3.
        return width - (2 + num_w + sum(widths[n] for n in present)
                        + NEXT_W + 2 * (len(present) + 3))

    need = PHASE_TABLE_MIN + STATE_TABLE_MIN
    for name in PANEL_SACRIFICE:
        if available() >= need:
            break
        widths[name] = max(floors[name], widths[name] - (need - available()))
    dropped = []
    for name in PANEL_SACRIFICE:
        if available() >= need:
            break
        present.remove(name)
        dropped.append(name)
    return present, widths, dropped, available()


def phase_panel_lines(data, width, style):
    """The pending phases, what each one IS and has done, and what comes
    next for it.

    The lanes above answer "what tracked work exists". This block answers
    "which phase should I run, why that one, and what has it actually done" —
    a table for the vertical scan (read `issues` down every row at once),
    plus a PURPOSE list below carrying what a fixed-width column cannot:
    each phase's purpose in full (D-01), and the next-command routing reason
    beside it (D-02 — `NEXT COMMANDS` no longer exists as its own section).
    Both render from the shared model, so they cannot disagree with the
    footer or with the HTML page.
    """
    phases = data.get("phases") or []
    pending = pending_phases(phases)
    cmds = data.get("next_commands") or []
    if not pending and not cmds:
        return []

    lines = [""]
    # Shared by the table above and the PURPOSE list below, so a phase
    # number lines up under the same width in both — and so this still
    # works when `pending` is empty (the all-complete case: PURPOSE is
    # carried entirely by `global_cmds`, computed below).
    num_w = max((len(str(p["number"])) for p in pending), default=1)

    cols, col_w, dropped, available = panel_columns(width, num_w)
    # The table prints only when the core still fits. PURPOSE below is NOT
    # gated on this: it carries every pending phase, its number, its purpose
    # and its routing reason, WRAPPED, at any width — which is why "print no
    # table here" loses nothing, and would not be a legitimate answer for the
    # grouped list above.
    show_table = bool(pending) and available >= PHASE_TABLE_MIN + STATE_TABLE_MIN

    if pending:
        lines.append(render_spans(
            [("PENDING PHASES", SGR_BOLD),
             (f"  {len(pending)}", SGR_DIM)], style))
    if pending and not show_table:
        # It does not print a row wider than the board was asked for — that
        # was CairnGo-cdx — and it does not print a mangled one either. It
        # says how much room it needs and where the same facts still are.
        short_by = PHASE_TABLE_MIN + STATE_TABLE_MIN - available
        lines += panel_note_lines(
            f"table needs {width + short_by} columns — "
            f"see PURPOSE below, or --json", width, style)

    if show_table:
        # Pass 1: gather each row's raw (untruncated) content. The `state`
        # column's width is only known once every row's real need is known
        # (a conflict/unknown verdict's marker+detail can run to ~70-80
        # cells; a plain "not planned" needs far less) — computing it
        # requires a full pass before anything is truncated or printed.
        rows = []
        n_blocks = n_informs = 0
        for p in pending:
            corrob = p.get("corroboration")
            if corrob == "conflict":
                # One phase, one line (D-03, inherited unchanged from Phase
                # 13): the marker + reason REPLACES the normal state text
                # entirely, it never sits alongside it. This plan only
                # narrows the column the marker lives in.
                if any(c["severity"] == "blocks" for c in p["conflicts"]):
                    n_blocks += 1
                else:
                    n_informs += 1
                glyph, sgr = conflict_marker(p, style)
                state_raw = f"{glyph} {conflict_summary_text(p)}"
            elif corrob == "unknown":
                glyph, sgr = conflict_marker(p, style)
                state_raw = f"{glyph} corroboration unknown"
            else:
                sgr = SGR_DIM
                state_raw = phase_state_text(p)
            blocked = bool(p["blocked_by"]) or p.get("needs_doctor", False)
            rows.append({
                "p": p, "state_raw": state_raw, "state_sgr": sgr,
                "title": style.asciify(p["title"] or "(untitled)"),
                # Rendered into the `phase` column below, never as a column
                # of its own: a new column prints its header and its empty
                # cells on EVERY board, which would move the committed
                # reference renders for phases that carry no tracker at all.
                "tracker": tracker_key(p["tracker"]) if p.get("tracker")
                else None,
                "rsch": phase_research_text(p),
                "plans": phase_progress_text(p) or "—",
                "issues": phase_issues_text(p),
                "verify": phase_verify_text(p),
                "waits": join_numbers(p["blocked_by"]) or "—",
                "next": p["next_command"] or "—",
                "next_sgr": SGR_DIM if blocked else SGR_GREEN,
            })

        # Widths: `state` gets exactly what its widest row needs, capped so
        # `phase` never collapses; `phase` gets whatever `state` doesn't
        # need. This is what lets a plain "not planned" render at its full
        # width while a ~76-cell conflict detail also renders whole at a
        # wide terminal, from the same formula, with no special-casing.
        #
        # `available` now comes from panel_columns() (Phase 22), which has
        # already shrunk or dropped whatever the width could not hold — so
        # the two FLOORs below still describe comfort at a wide terminal, and
        # the MINs they fall back to describe survival at a narrow one.
        natural_state = max((display_width(r["state_raw"]) for r in rows),
                            default=STATE_TABLE_FLOOR)
        state_floor = min(STATE_TABLE_FLOOR,
                          max(STATE_TABLE_MIN, available - PHASE_TABLE_MIN))
        cap = max(state_floor, available - PHASE_TABLE_FLOOR)
        state_w = max(state_floor, min(natural_state, cap))
        phase_w = max(PHASE_TABLE_MIN, available - state_w)

        # Header sub-row, built from the SAME width variables as the data
        # rows below, so header and data always line up — including which
        # optional columns exist at all.
        header = [
            ("  ", None), ("#".rjust(num_w), SGR_DIM), ("  ", None),
            ("phase".ljust(phase_w), SGR_DIM), ("  ", None),
            ("state".ljust(state_w), SGR_DIM),
        ]
        for name in cols:
            header += [("  ", None), (name.ljust(col_w[name]), SGR_DIM)]
        header += [("  ", None), ("next", SGR_DIM)]
        lines.append(render_spans(header, style))

        for r in rows:
            p = r["p"]
            state_text = style.asciify(
                truncate(r["state_raw"], state_w, style.ell))
            # The tracker key rides beside the title, which is what already
            # identifies the phase. Unlike make_cell()'s card suffix, here
            # the key gets its budget RESERVED and the title truncates around
            # it, because MEASURED: `phase` is a squeezed column (8 cells at
            # --width 100, 50 at 140), the title is already truncated in it
            # at every ordinary terminal size, and a suffix that only fits
            # when nothing else needs the room shows up above ~160 columns
            # and nowhere else — a feature nobody would ever see. The key is
            # short and fixed; the title is long and already cut. Reserving
            # for the short one costs a few characters of a name that is
            # abbreviated anyway.
            #
            # The floor is what stops that from going absurd: below
            # TRACKER_TITLE_FLOOR cells left for the title, the key falls out
            # instead, so a narrow board never renders `Ph…  ⧉ DTP-777`.
            phase_cell = r["title"]
            if r["tracker"]:
                key = f"  {style.g_card} {r['tracker']}"
                key_w = display_width(key)
                if phase_w - key_w >= TRACKER_TITLE_FLOOR:
                    phase_cell = truncate(r["title"], phase_w - key_w,
                                          style.ell) + key
            spans = [
                ("  ", None),
                (str(p["number"]).rjust(num_w), None),
                ("  ", None),
                (truncate(phase_cell, phase_w, style.ell).ljust(phase_w),
                 None),
                ("  ", None),
                (state_text.ljust(state_w), r["state_sgr"]),
            ]
            for name in cols:
                w = col_w[name]
                spans += [("  ", None),
                          (truncate(r[name], w, style.ell).ljust(w), SGR_DIM)]
            spans += [("  ", None),
                      (truncate(r["next"], NEXT_W, style.ell), r["next_sgr"])]
            lines.append(render_spans(spans, style))

        if dropped:
            # A column that vanished without a word is the same class of lie
            # as a title cut without an ellipsis. Name them, and say where
            # the same facts are still whole. Through panel_note_lines(),
            # because a message ABOUT not fitting that does not itself fit is
            # the joke this whole plan exists to stop telling.
            lines += panel_note_lines(
                f"hidden at this width: {', '.join(dropped)} — widen, or "
                "/cairn:status --json", width, style)

        if n_blocks or n_informs:
            # The itemized per-source detail lives in /cairn:doctor and
            # --json only — this line counts, it never dumps a second line
            # per phase onto the board itself.
            lines.append("")
            spans = [("  ", None)]
            if n_blocks:
                spans.append((f"{style.g_conflict} {n_blocks} blocks",
                              SGR_RED))
            if n_blocks and n_informs:
                spans.append((style.sep, SGR_DIM))
            if n_informs:
                spans.append((f"{style.g_informs} {n_informs} informs",
                              SGR_YELLOW))
            spans.append((style.asciify(" — /cairn:doctor for the itemized "
                                        "report"), SGR_DIM))
            # Wrapped, not printed flat: MEASURED 2026-08-06 this line is 52
            # cells and ran off a --width 50 board — the same overflow as
            # CairnGo-cdx, in the same section, on a line nobody had counted.
            # wrap_spans keeps the red/yellow markers coloured across the
            # break; textwrap would flatten them to plain text.
            for i, cont in enumerate(wrap_spans(spans[1:], max(20, width - 2))):
                lines.append(render_spans([("  ", None)] + cont, style))

    # PURPOSE: the routing reason moves here from the deleted NEXT COMMANDS
    # section (D-02). This is the ONE place text wraps instead of truncating
    # (D-01 — a phase's purpose is never cut), and it is also the only
    # section left standing when every phase is complete: `pending` is then
    # empty and the per-phase loop below contributes nothing, but
    # `global_cmds` (the /cairn:ship + /cairn:milestone complete pair
    # next_commands() emits with `phase: None`) still carries its reasons
    # into the terminal here — the fix for the bug this plan exists to
    # close (the terminal silently dropping those two commands while --json
    # and the HTML page still had them).
    phase_cmds = [c for c in cmds if c["phase"] is not None]
    global_cmds = [c for c in cmds if c["phase"] is None]
    reason_by_phase = {c["phase"]: c["reason"] for c in phase_cmds}

    if pending or global_cmds:
        lines.append("")
        lines.append(render_spans([("PURPOSE", SGR_BOLD)], style))
        # `max(30, ...)` until 2026-08-06, which overrode the width it was
        # given: MEASURED at --width 30, PURPOSE wrapped its text at 30 cells
        # and then indented it by num_w + 4, producing 35-36 cell lines on a
        # 30-cell board. Same defect as CairnGo-cdx, on the block directly
        # under the table. The floor is now low enough to never fight the
        # subtraction, and the subtraction is what makes the indent fit.
        wrap_w = max(10, width - num_w - 4)
        for p in pending:
            text = phase_purpose_text(p)
            reason = reason_by_phase.get(p["number"])
            if reason:
                text = f"{text} — {reason}"
            wrapped = textwrap.wrap(style.asciify(text), wrap_w) or [""]
            lines.append(render_spans([
                ("  ", None), (str(p["number"]).rjust(num_w), None),
                ("  ", None), (wrapped[0], None),
            ], style))
            for cont in wrapped[1:]:
                lines.append(render_spans(
                    [(" " * (num_w + 4), None), (cont, None)], style))
        for c in global_cmds:
            # No phase number and no purpose prefix — a global command is
            # not attached to any one phase.
            text = c["command"]
            if c.get("reason"):
                text = f"{text} — {c['reason']}"
            wrapped = textwrap.wrap(style.asciify(text), wrap_w) or [""]
            for cont in wrapped:
                lines.append(render_spans([("  ", None), (cont, None)],
                                          style))

    par = data.get("parallelism") or {}
    if par.get("note"):
        lines.append("")
        # Wrapped rather than truncated: this one is a sentence, and a
        # sentence cut at the terminal edge loses the half that qualifies it.
        # Same correction as PURPOSE above: the floor no longer overrides the
        # width, so the two-cell indent stays inside the board.
        for i, chunk in enumerate(textwrap.wrap(style.asciify(par["note"]),
                                                max(10, width - 2))):
            lines.append(render_spans(
                [("  " if i else "  ", None), (chunk, SGR_DIM)], style))
    return lines


def active_lease(data):
    """The active phase's lease dict when it is actively held and fresh
    (D-05), else None — the single held/stale gate every renderer shares,
    so a stale hold (doctor's story to tell, not the footer's — Plan
    15-03) or a vacant lease can never render on one surface and not
    another."""
    lease = data.get("lease")
    if lease and lease.get("held") and not lease.get("stale"):
        return lease
    return None


def lease_line_text(data):
    """`phase N in use by HOLDER since ACQUIRED_AT` for an actively-held,
    fresh lease, or None. The terminal footer and the HTML foot both
    render this exact sentence (asciified / esc()-escaped respectively);
    --plain carries the same three values as separate LEASE\\t... fields
    instead, per its own row convention — one read of data["lease"], no
    renderer re-derives it independently (mirrors 13-01's D-04)."""
    lease = active_lease(data)
    if lease is None:
        return None
    return (f"phase {data['phase']['active']} in use by "
            f"{clean(lease.get('holder') or '')} since "
            f"{clean(lease.get('acquired_at') or '')}")


def milestone_label(data):
    """What the HUMAN surfaces call the current milestone (BOARD-04).

    The open cycles of `data["open_milestones"]`, which come from the marker
    on the ROADMAP's own `## Milestones` line (`🚧` / `(in progress)`) and
    never from STATE.md's `milestone:` — that pointer keeps naming the
    archived cycle, which is the measured defect (2026-08-03, ten minutes
    after v1.4 was archived, the board still read `v1.4`).

    One open cycle: its label, the SAME string the group row prints, so the
    header and the list cannot spell the same milestone two ways. More than
    one: the first plus ` +N`, because omitting the others in silence is the
    thing this function exists to stop. None: `no open milestone`, in words —
    BOARD-04 asks the board to say so, not to fall quiet and let the reader
    assume.

    One read, shared by the terminal footer, --brief and the HTML foot, in
    the line of lease_line_text() (13-01, D-04). `--plain` deliberately does
    NOT use it: it carries data["milestone"] as it always has, because
    PIPE-01 freezes the machine contract byte for byte.
    """
    open_ms = data.get("open_milestones") or []
    if not open_ms:
        return "no open milestone"
    label = clean(open_ms[0]["label"] or open_ms[0]["key"] or "")
    if len(open_ms) > 1:
        return f"{label} +{len(open_ms) - 1}"
    return label


def footer_lines(data, width, style):
    lines = [render_spans(meta_parts(data, style), style)]
    nxt = style.asciify(data["next"]["text"])
    lines.append(render_spans(
        [(style.g_next, SGR_GREEN), (" next: ", SGR_BOLD),
         (truncate(nxt, max(20, width - 10), style.ell), None)], style))
    sync = data["sync"]
    if sync["configured"] and sync["stale"]:
        lines.append(render_spans(
            [("sync: ", SGR_DIM),
             (style.asciify(f"{sync['detail']} — run /cairn:sync-pull"),
              None)], style))
    lease_text = lease_line_text(data)
    if lease_text:
        lines.append(render_spans(
            [(style.g_who, SGR_YELLOW), (" ", None),
             (style.asciify(lease_text), None)], style))
    if data["note"]:
        lines.append(render_spans(
            [("note: ", SGR_DIM), (style.asciify(data["note"]), None)],
            style))
    return lines


def render_plain(data):
    """Tab-separated, escape-free, untruncated — the machine default."""
    lines = []
    for (name, _), items in zip(LANES, data["_lanes"]):
        for iss in items:
            if name == "DOING":
                extra = clean(iss.get("assignee") or "")
            elif name == "BLOCKED":
                extra = ",".join(clean(b)
                                 for b in as_str_list(iss.get("blocked_by")))
            else:
                extra = ""
            lines.append("\t".join([name, clean(iss.get("id", "?")),
                                    str(issue_priority(iss)),
                                    clean(iss.get("title", "")), extra]))
    phase = data["phase"]
    if phase["active"] is not None and phase["total"]:
        lines.append(f"PHASE\t{phase['active']}/{phase['total']}")
    if data["milestone"]:
        lines.append(f"MILESTONE\t{data['milestone']}")
    lines.append(f"DONE\t{data['counts']['closed']}")
    lines.append(f"NEXT\t{data['next']['text']}")
    lease = active_lease(data)
    if lease:
        lines.append(f"LEASE\t{data['phase']['active']}\t"
                      f"{clean(lease.get('holder') or '')}\t"
                      f"{clean(lease.get('acquired_at') or '')}")
    sync = data["sync"]
    if sync["configured"]:
        state = "stale" if sync["stale"] else "fresh"
        lines.append(f"SYNC\t{state}\t{sync['detail']}")
    if data["note"]:
        lines.append(f"NOTE\t{data['note']}")
    return lines


def render_brief(data, style):
    head = render_spans([("[cairn-status] ", None)] +
                        meta_parts(data, style, include_done=False), style)
    if data["sync"]["configured"] and data["sync"]["stale"]:
        head += render_spans([(style.sep, SGR_DIM), ("sync stale", SGR_RED)],
                             style)
    if data["note"]:
        # Brief stays exactly three lines — the note collapses to a marker
        # matching its cause (missing .beads vs roadmap-complete stragglers).
        marker = ("no .beads" if "no .beads" in data["note"]
                  else "stale phases")
        head += render_spans([(style.sep, SGR_DIM), (marker, SGR_RED)],
                             style)
    # The same spans the grouped list prints at its top — one spelling of the
    # four numbers, shared, so the two surfaces cannot disagree.
    counts = render_spans(counts_parts(data, style), style)
    nxt = render_spans([(style.g_next, SGR_GREEN), (" next: ", SGR_BOLD),
                        (style.asciify(data["next"]["text"]), None)], style)
    return [head, counts, nxt]


# ------------------------------------------------------------ html rendering
#
# The HTML board is a fourth renderer over the SAME `data` dict the terminal,
# --plain and --json renderers read: no extra bd query, no second source of
# truth. Its signature element is a topographic profile of the roadmap, and
# every number in it comes from real state (issues per phase, lane counts,
# roadmap position) — the page never invents relief it does not have.

BOARD_START = "<!-- cairn:generated:board:start -->"
BOARD_END = "<!-- cairn:generated:board:end -->"
TEMPLATE_PATH = (Path(__file__).resolve().parent.parent / "templates" /
                 "status-board.html")

# Profile geometry, in viewBox units (the SVG scales with the page, so these
# are proportions, not pixels).
VB_W, VB_H = 1000.0, 220.0
BASE_Y = 196.0                 # elevation datum: relief is measured up from it
# Relief starts at zero so elevation stays PROPORTIONAL to the count: a
# non-zero floor here would be a compressed axis, the truncated axis's twin,
# and the caption makes a quantitative promise the geometry has to honour.
# Two phases at 1 and 4 issues must differ 4x, not 2.3x. The drawing floor
# lives in the clamp inside terrain_ridge (BASE_Y - 8), which keeps a flat
# phase visible without touching the ratio between phases that carry data.
MIN_RELIEF, MAX_RELIEF = 0.0, 124.0
PEAK_Y = BASE_Y - MAX_RELIEF   # 72: the highest a ridge can reach
SKY_Y = PEAK_Y - 6.0           # sampling ceiling, so a spline overshoot on a
#                                steep face can never crowd the marker
STRATA_MAX_BANDS = 12          # above this the one-band-per-issue scale would
#                                crowd into texture, so it is dropped instead
#                                (see svg_profile)
RIDGE_ROUGHNESS = 2.6          # drawn texture BETWEEN nodes only (see
#                                catmull_rom): every peak keeps its exact,
#                                data-given elevation
# Unmapped ground carried on each side of the roadmap so the profile can run
# to the page edges and off them: the trail existed before phase one and
# keeps going after the last. The band bleeds past the text column in the
# stylesheet, and .ticks pads itself by exactly TRAIL_BLEED / TRAIL_SPAN so
# every tick stays dead-centre under its own segment. Change one, change the
# other (the CSS carries the same two numbers in a comment).
TRAIL_BLEED = 70.0
TRAIL_SPAN = VB_W + 2 * TRAIL_BLEED
SKY_PAD = 6.0                  # air kept above the highest thing in the box
CUT_FADE = 48.0                # horizontal run over which walked ground
#                                dissolves into the climb ahead, so the two
#                                meet in a hand-off rather than a shear
GROUND_FADE = 0.26             # bottom share of the box the ground dissolves
#                                over, so the cross-section has no hard edge
#                                against the page under it
MAX_TICK_LABELS = 16           # numbers the scale can hold on a phone before
#                                they collide (see tick_label_indices)

# The marker: five stones, base at (0,0), stacked upward. Faceted irregular
# silhouettes drawn vertex by vertex — a cairn is struck rock stacked by
# hand, and circles would read as a chart legend.
# Each stone is offset against the one below it (left, right, left, right)
# and the taper is deliberately not monotonic — stone three overhangs stone
# two. A perfectly centred, evenly tapering stack reads as a pagoda; a
# cairn is balanced by hand and leans.
CAIRN_STONES = (
    ((-15.6, -2.0), (-13.2, -8.2), (-6.0, -10.6), (3.2, -10.8), (10.6, -9.0),
     (14.4, -5.2), (13.8, -0.6), (8.4, 2.0), (-9.8, 2.2), (-14.6, 0.4)),
    ((-8.4, -12.4), (-6.0, -17.6), (-0.6, -19.4), (6.0, -18.8), (10.4, -16.2),
     (11.2, -12.0), (7.2, -10.2), (-4.6, -10.4)),
    ((-13.0, -21.4), (-10.6, -24.4), (-4.4, -25.4), (3.4, -24.8), (8.0, -22.6),
     (8.6, -20.4), (3.0, -19.0), (-8.6, -19.4)),
    ((-5.0, -27.0), (-2.6, -31.0), (1.6, -32.4), (5.8, -31.2), (8.4, -28.2),
     (7.0, -25.6), (2.6, -25.0), (-3.0, -25.4)),
    ((-6.6, -34.0), (-4.6, -37.2), (-1.4, -38.6), (1.4, -36.6), (2.6, -33.6),
     (0.8, -31.8), (-2.8, -31.8), (-5.4, -32.6)),
)
# Real extent of the stack around its base, half the 0.9 stroke included. The
# marker is clamped inside the viewBox with these, so a cairn standing on the
# first or the last phase of a long roadmap keeps every stone whole.
STACK_L = -min(x for s in CAIRN_STONES for x, _ in s) + 0.5   # 16.1
STACK_R = max(x for s in CAIRN_STONES for x, _ in s) + 0.5    # 14.9
STACK_H = -min(y for s in CAIRN_STONES for _, y in s)         # 38.6

PEBBLE = ('<svg class="mark" viewBox="0 0 12 10" aria-hidden="true">'
          '<use href="#pebble"></use></svg>')


def esc(text):
    """The single gate every bd/GSD string passes before reaching the page.

    clean() first (control bytes stripped, whitespace collapsed — titles can
    arrive from a remote tracker via sync-pull), then HTML escaping of
    & < > " ' so a title like `<script>x&y</script>` renders as text and can
    neither execute nor break out of an attribute.
    """
    return html.escape(clean(text), quote=True)


def n2(x):
    """Compact fixed-point for SVG coordinates."""
    return f"{x:.1f}"


def split_markers(text, start_marker, end_marker):
    """Locate the generated region.

    Returns (prefix incl. start marker, inner, suffix from end marker) for a
    well-formed pair, the string "absent" when the file carries NEITHER
    marker, or the string "damaged" for anything else: one marker without
    its partner, the pair out of order, or a marker appearing more than once.

    The three-way answer is the point. Treating "one marker present" as
    "no region here" and appending a fresh block is what turns a damaged
    page into a destroyed one: the appended block supplies the partner the
    file was missing, and the NEXT run splices between the orphan and the
    newcomer, eating every byte in between. A page carrying only the start
    marker lost its closing tags on the second run that way, and one
    carrying only the end marker grew an extra board every run, forever.
    A file we cannot read confidently is one we must not rewrite.
    """
    starts, ends = text.count(start_marker), text.count(end_marker)
    if starts == 0 and ends == 0:
        return "absent"
    if starts != 1 or ends != 1:
        return "damaged"
    s, e = text.find(start_marker), text.find(end_marker)
    if e < s + len(start_marker):
        return "damaged"
    return (text[:s + len(start_marker)],
            text[s + len(start_marker):e].strip("\n"),
            text[e:])


def splice_board(text, inner):
    """(changed, full_text) or the string "damaged".

    Replaces ONLY the content between the board markers, preserving every
    other byte exactly. A file carrying neither marker gets the block
    appended, never destroyed. A file whose markers are broken is refused
    outright and left untouched, which the caller reports as a usage error:
    the alternative is guessing where a region starts in a page somebody
    hand-edited, and a wrong guess deletes their work.
    """
    parts = split_markers(text, BOARD_START, BOARD_END)
    if parts == "damaged":
        return "damaged"
    if parts == "absent":
        sep = "" if text.endswith("\n") else "\n"
        return True, f"{text}{sep}\n{BOARD_START}\n{inner}\n{BOARD_END}\n"
    if parts[1] == inner:
        return False, text
    return True, f"{parts[0]}\n{inner}\n{parts[2]}"


# ------------------------------------------------------- the roadmap terrain

def terrain_model(data):
    """Per-phase elevation model, or None when the roadmap has no phases.

    Elevation is the issue count of each phase — every issue carrying a
    phase-N label, open or closed, so a delivered phase keeps the ground it
    earned. The phase you stand in is STATE.md's active_phase; when that is
    missing or points off the roadmap, it falls back to the first phase the
    roadmap has not marked complete (the summit when all of them are).
    """
    phases = data["_phases"]["all"]
    if not phases:
        return None
    done = set(data["_phases"]["done"])
    counts = {n: 0 for n in phases}
    tracked = placed = 0
    for iss in (data["_lanes"][0] + data["_lanes"][1] + data["_lanes"][2] +
                data["_closed"]):
        tracked += 1
        on_roadmap = False
        for n in issue_phase_ns(iss):
            if n in counts:
                counts[n] += 1
                on_roadmap = True
        placed += 1 if on_roadmap else 0
    try:
        active = int(str(data["phase"]["active"]))
    except (TypeError, ValueError):
        active = None
    if active not in counts:
        ahead = [n for n in phases if n not in done]
        active = ahead[0] if ahead else phases[-1]
    # Issues with no phase label are real work the terrain cannot show. The
    # caption reports the shortfall rather than letting the profile quietly
    # under-report the board it sits on.
    return {"phases": phases, "counts": counts, "done": done,
            "active": active, "placed": placed, "tracked": tracked}


def catmull_rom(nodes, per_span):
    """Points sampled along a Catmull-Rom spline through `nodes`.

    The nodes sit at a constant x pitch (trailhead, peak, saddle, peak, …),
    and a Catmull-Rom reproduces linear data exactly, so x stays monotonic
    and the ridge can never fold back on itself.

    Between two nodes the crest also picks up a little rock roughness. It is
    weighted by sin(pi*t), which is ZERO at both ends of every span, so each
    node — every peak, every saddle — keeps exactly the elevation the data
    gave it. The roughness is drawing, never data.
    """
    out = []
    last = len(nodes) - 1
    for i in range(last):
        p0 = nodes[max(0, i - 1)]
        p1, p2 = nodes[i], nodes[i + 1]
        p3 = nodes[min(last, i + 2)]
        for s in range(per_span):
            t = s / per_span
            t2, t3 = t * t, t * t * t
            x, y = (0.5 * (2 * a1 + (-a0 + a2) * t +
                           (2 * a0 - 5 * a1 + 4 * a2 - a3) * t2 +
                           (-a0 + 3 * a1 - 3 * a2 + a3) * t3)
                    for a0, a1, a2, a3 in zip(p0, p1, p2, p3))
            grain = math.sin(x * 0.21) * 0.6 + math.sin(x * 0.53) * 0.4
            rough = RIDGE_ROUGHNESS * math.sin(math.pi * t) * grain
            out.append((x, y - rough))
    out.append(nodes[last])
    return out


def terrain_ridge(model):
    """(ridge_points, cut_index, peak_xy) for the profile.

    cut_index splits the ridge into ground already walked (filled, stratified)
    and the climb ahead (a thin line). The split sits exactly on the active
    phase's peak, so the marker stands where the solid ground ends.
    """
    phases, counts = model["phases"], model["counts"]
    span = VB_W / len(phases)
    top = max(counts.values()) if counts else 0
    relief = [MIN_RELIEF if top <= 0 else
              MIN_RELIEF + (counts[n] / top) * (MAX_RELIEF - MIN_RELIEF)
              for n in phases]

    # A pass between two phases drops to 42% of the lower neighbour, which is
    # what keeps distinct summits instead of one rolling wave.
    # The first and last nodes sit OUTSIDE the roadmap, in the unmapped
    # ground: the ridge arrives from off the page and leaves the same way.
    nodes = [(-TRAIL_BLEED, BASE_Y - relief[0] * 0.16),
             (0.0, BASE_Y - relief[0] * 0.44)]
    peaks = []
    for i, h in enumerate(relief):
        if i:
            saddle = min(relief[i - 1], h) * 0.42
            nodes.append((span * i, BASE_Y - saddle))
        peak = (span * (i + 0.5), BASE_Y - h)
        nodes.append(peak)
        peaks.append(peak)
    nodes.append((VB_W, BASE_Y - relief[-1] * 0.74))
    nodes.append((VB_W + TRAIL_BLEED, BASE_Y - relief[-1] * 0.34))

    per_span = max(4, min(14, int(180 / max(1, len(nodes) - 1))))
    pts = [(x, min(BASE_Y - 8.0, max(SKY_Y, y)))
           for x, y in catmull_rom(nodes, per_span)]

    here = peaks[phases.index(model["active"])]
    cut = max(i for i, (x, _) in enumerate(pts) if x <= here[0] + 0.01)
    return pts, cut, here


def poly_len(points):
    """Length of a polyline in viewBox units (drives the walk highlight)."""
    return sum(math.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(points, points[1:]))


def ground_fade(ident, top, bottom=VB_H, cut_x=None):
    """Defs that dissolve the ground into the page at both open edges.

    A cross-section that stops on a hard rule reads as a chart pasted onto
    the page. The last fifth of the ground fades out at the bottom, and the
    page under it carries the same falloff in CSS, so the two read as one
    surface rather than two sections meeting at a seam.

    `cut_x` is where the walked ground ends mid-roadmap. Closing the mass
    there with a vertical edge left a guillotine down the middle of the
    page - the ground simply stopped, sheared. The same treatment is applied
    sideways: the last stretch before the cut dissolves, so walked ground
    hands off to the dotted climb instead of being sliced from it. When the
    roadmap is finished there is no cut, the ground runs off the page, and
    this second fade is not drawn at all.
    """
    height = bottom - top
    box = (f'x="{n2(-TRAIL_BLEED)}" y="{n2(top)}" '
           f'width="{n2(TRAIL_SPAN)}" height="{n2(height)}"')
    defs = (f'<linearGradient id="{ident}-fade" gradientUnits="userSpaceOnUse"'
            f' x1="0" y1="{n2(bottom - height * GROUND_FADE)}" x2="0" '
            f'y2="{n2(bottom)}"><stop offset="0" stop-color="#fff"></stop>'
            f'<stop offset="1" stop-color="#fff" stop-opacity="0"></stop>'
            f'</linearGradient>')
    edge = ""
    if cut_x is not None:
        x0 = cut_x - CUT_FADE
        defs += (f'<linearGradient id="{ident}-cut" '
                 f'gradientUnits="userSpaceOnUse" x1="{n2(x0)}" y1="0" '
                 f'x2="{n2(cut_x)}" y2="0">'
                 f'<stop offset="0" stop-color="#000" stop-opacity="0">'
                 f'</stop><stop offset="1" stop-color="#000"></stop>'
                 f'</linearGradient>')
        edge = (f'<rect x="{n2(x0)}" y="{n2(top)}" width="{n2(CUT_FADE)}" '
                f'height="{n2(height)}" fill="url(#{ident}-cut)"></rect>')
    return (defs
            + f'<mask id="{ident}" maskUnits="userSpaceOnUse" {box}>'
            + f'<rect {box} fill="url(#{ident}-fade)"></rect>{edge}</mask>')


def svg_profile(data, model):
    """The signature: the roadmap read as a terrain cross-section."""
    pts, cut, here = terrain_ridge(model)
    # A roadmap with every phase delivered has nothing left to climb. Drawing
    # the dotted trail there would assert remaining work that does not exist,
    # so the solid ground runs to the edge and off it instead: the summit is
    # the end of the walk, not a waypoint before more of it.
    finished = not (set(model["phases"]) - model["done"])
    if finished:
        walked, ahead = pts, []
    else:
        walked, ahead = pts[:cut + 1], pts[cut:]
    # Where the walked ground stops: the marker's peak, or the page edge once
    # there is nothing after it.
    edge = pts[-1][0] if finished else here[0]

    def poly(points):
        return " ".join(f"{n2(x)},{n2(y)}" for x, y in points)

    # The marker is clamped inside the box: a cairn standing on the first or
    # the last phase of a long roadmap leans off its peak by a unit or two
    # (invisible) rather than losing a stone to the viewport edge (not).
    stack_x = min(max(here[0], -TRAIL_BLEED + STACK_L),
                  VB_W + TRAIL_BLEED - STACK_R)
    stack_y = here[1] + 1.2
    # The box is cropped to what the terrain actually needs, so a roadmap
    # carrying no issues yet draws a low ridge in a low band instead of
    # reserving three quarters of a chart for elevation it does not have.
    top = min(min(y for _, y in pts), stack_y - STACK_H) - SKY_PAD
    mass = poly([(-TRAIL_BLEED, VB_H)] + walked + [(edge, VB_H)])
    # Elevation bands, clipped to the walked ground: deeper ground shows more
    # of them, so the strata count reads as height. They live inside the
    # profile only - a grid behind the page would just be graph paper.
    # One band per issue, measured up from the datum, so counting bands is a
    # real reading of the height. A fixed spacing would have been decoration
    # wearing a scale's costume: its worth in issues would drift with the
    # data. Above STRATA_MAX_BANDS the lines would crowd into a texture, and
    # a scale nobody can count is worse than none, so they are simply left
    # out rather than regrouped into a silent, different unit.
    busiest = max(model["counts"].values()) if model["counts"] else 0
    strata = ""
    if 0 < busiest <= STRATA_MAX_BANDS:
        step = (MAX_RELIEF - MIN_RELIEF) / busiest
        strata = "".join(
            f'<line x1="{n2(-TRAIL_BLEED)}" y1="{n2(y)}" x2="{n2(edge)}" '
            f'y2="{n2(y)}"></line>'
            for y in [BASE_Y - k * step for k in range(1, busiest + 1)]
            if PEAK_Y - 0.01 <= y < VB_H)
    # The light crosses at ONE speed whatever the board, so the length of the
    # beat is itself a reading: a long walked trail takes longer to travel
    # than a short one. Bounded so phase one is not a flicker and a finished
    # roadmap is not a wait.
    walk_len = poly_len(walked)
    walk_ms = round(min(1500.0, max(450.0, walk_len * 1.15)))
    stones = "".join(
        '<path{} d="{}"></path>'.format(
            ' class="is-crown"' if i == len(CAIRN_STONES) - 1 else "",
            "M" + " ".join(f"{n2(x)} {n2(y)}" for x, y in stone) + "Z")
        for i, stone in enumerate(CAIRN_STONES))
    label = esc(f"roadmap profile: {len(model['phases'])} phases, "
                f"standing at phase {model['active']}")
    return (
        f'<svg class="profile" viewBox="{n2(-TRAIL_BLEED)} {n2(top)} '
        f'{n2(TRAIL_SPAN)} {n2(VB_H - top)}" '
        f'role="img" aria-label="{label}">'
        f'<clipPath id="cairn-walked"><polygon points="{mass}"></polygon>'
        f'</clipPath>'
        f'{ground_fade("cairn-ground", top, cut_x=None if finished else edge)}'
        f'<g mask="url(#cairn-ground)">'
        f'<polygon class="terrain-mass" points="{mass}"></polygon>'
        f'<g class="terrain-strata" clip-path="url(#cairn-walked)">'
        f'{strata}</g></g>'
        + (f'<polyline class="terrain-ahead" points="{poly(ahead)}">'
           '</polyline>' if ahead else '') +
        f'<polyline class="terrain-crest" points="{poly(walked)}"></polyline>'
        f'<polyline class="terrain-walk" '
        f'style="--walk-len:{n2(walk_len)}px;--walk-ms:{walk_ms}ms" '
        f'points="{poly(walked)}"></polyline>'
        f'<g class="cairn-stack" transform="translate({n2(stack_x)},'
        f'{n2(stack_y)})"><g class="cairn-scale">{stones}</g></g>'
        f'</svg>')


def tick_label_indices(phases, active):
    """Which phases keep a number under the profile.

    A scale of equal columns has no floor: 24 phases on a phone leave 14px a
    column, and two-digit numbers 14.5px wide, so every label collides with
    its neighbour and the row renders as one smear. Past MAX_TICK_LABELS the
    scale labels index phases only — every 2nd, 5th, 10th — the way a contour
    map labels index lines, plus the phase you are standing in, which is
    never dropped. The rest keep their place as a plain tick.

    Index labels never land in the outermost column (they would sit under the
    very rim of the page); the active phase does, because losing the one
    label that matters would be worse.
    """
    n = len(phases)
    step = next((s for s in (1, 2, 5, 10, 25)
                 if math.ceil(n / s) <= MAX_TICK_LABELS), 50)
    if step == 1:
        return set(range(n))
    keep = {phases.index(active)} if active in phases else set()
    for i, p in enumerate(phases):
        # Selected by POSITION on the scale, not by the phase's number.
        # `step` is an index budget derived from how many phases there are,
        # so testing the number against it only worked while the numbering
        # happened to be contiguous from 1. A roadmap numbered 1, 3, 5, ...
        # has no phase divisible by 2, and the scale rendered exactly one
        # label: the active phase, alone on an empty ruler.
        if i % step or not 0 < i < n - 1:
            continue
        if all(abs(i - j) >= step for j in keep):
            keep.add(i)
    return keep


def html_band(data):
    """The profile band: terrain, the phase scale under it, and one caption
    naming what the elevation encodes. Without a roadmap it degrades to a
    flat horizon carrying the counts: no invented relief."""
    model = terrain_model(data)
    if model is None:
        c = data["counts"]
        openn = c["ready"] + c["doing"] + c["blocked"]
        edge, span = n2(-TRAIL_BLEED), n2(TRAIL_SPAN)
        far = n2(VB_W + TRAIL_BLEED)
        return (
            '<section class="band" aria-label="tracked work">'
            f'<svg class="horizon" viewBox="{edge} 0 {span} 64" '
            'role="img" aria-label="no roadmap phases">'
            f'{ground_fade("cairn-flat", 0.0, 64.0)}'
            f'<g mask="url(#cairn-flat)">'
            f'<polygon class="terrain-mass" points="{edge},64 {edge},24 '
            f'{far},24 {far},64"></polygon>'
            f'<g class="terrain-strata"><line x1="{edge}" y1="43" x2="{far}" '
            f'y2="43"></line><line x1="{edge}" y1="60" x2="{far}" y2="60">'
            '</line></g></g>'
            # Same crest treatment as the profile, held dead level: the
            # ground is real, the relief is simply unmapped.
            f'<polyline class="terrain-crest" points="{edge},24 {far},24">'
            '</polyline></svg>'
            f'<p class="band-counts"><span><span class="n">{openn}</span> '
            f'open</span><span><span class="n">{c["closed"]}</span> done'
            '</span></p>'
            '<p class="caption">no roadmap phases. counts only.</p>'
            '</section>')

    labelled = tick_label_indices(model["phases"], model["active"])
    ticks = []
    for i, n in enumerate(model["phases"]):
        cls = "tick"
        if n in model["done"]:
            cls += " is-done"
        if n == model["active"]:
            cls += " is-here"
        count = model["counts"][n]
        body = (f'<span class="tick-n">{n:02d}</span>'
                f'<span class="tick-c">{count}</span>' if i in labelled
                else '<span class="tick-mark"></span>')
        ticks.append(f'<span class="{cls}">{body}</span>')
    top = max(model["counts"].values()) if model["counts"] else 0
    legend = ['elevation: issues per phase']
    if 0 < top <= STRATA_MAX_BANDS:
        legend.append('one band each')
    legend.append('solid ground: already walked')
    # An honest caption names its own blind spot: work with no phase label
    # exists on the board but cannot exist in the terrain.
    if model["placed"] < model["tracked"]:
        legend.append(f'{model["placed"]} of {model["tracked"]} issues '
                      'carry a phase')
    return ('<section class="band" aria-label="roadmap profile">'
            + svg_profile(data, model)
            # The scale's inset IS the unmapped ground the profile carries on
            # each side, so it is emitted from the same constant the geometry
            # uses. Duplicating the number in the stylesheet is what let the
            # ticks drift 74px away from their own peaks once already.
            + f'<div class="ticks" style="--trail-pad: '
              f'{TRAIL_BLEED / TRAIL_SPAN:.6%}">' + "".join(ticks) + '</div>'
            f'<p class="caption">{" &middot; ".join(legend)}</p></section>')


# ------------------------------------------------------------- page sections

def html_head(data):
    phase = data["phase"]
    bits = []
    if phase["active"] is not None and phase["total"] or data.get(
            "open_milestones"):
        # A milestone is a name, so it is set in the page's own voice. Mono
        # is kept for the things that are actually data: the phase numbers.
        # milestone_label() since Phase 22 (BOARD-04) — the third human
        # surface reading the one spelling, so the page can never announce a
        # cycle the terminal already stopped naming.
        bits.append(f'<span class="m">{esc(milestone_label(data))}</span>')
    if phase["active"] is not None and phase["total"]:
        bits.append(f'phase <span class="n">{esc(phase["active"])}</span> of '
                    f'<span class="n">{phase["total"]}</span>')
    pos = " &middot; ".join(bits) or "no roadmap position"
    # The phase's own name, from the shared model — the page said which
    # numbered phase you were in and never what it was.
    sub = ""
    active = find_phase(data.get("phases") or [], phase["active"])
    if active and active.get("title"):
        detail = esc(active["title"])
        prog = phase_progress_text(active)
        if prog:
            detail += f' <span class="n">{esc(prog)}</span>'
        sub = f'<p class="pos-title">{detail}</p>'
    return ('<header class="head"><h1 class="wordmark">cairn</h1>'
            f'<p class="pos">{pos}</p>{sub}</header>')


def html_next(data):
    """The one thing to pick up, and the only other place amber is spent:
    on the id you are meant to act on."""
    nxt = data["next"]
    by_id = {str(i.get("id")): i for i in
             data["_lanes"][0] + data["_lanes"][1] + data["_lanes"][2]}
    verb = title = mark = ""
    if nxt["kind"] in ("continue", "ready") and nxt["id"] is not None:
        verb = "continue" if nxt["kind"] == "continue" else "start"
        mark = esc(nxt["id"])
        title = esc(by_id.get(str(nxt["id"]), {}).get("title", ""))
    elif nxt["kind"] == "workflow":
        mark = esc(nxt["state_next"] or "")
        if data["phase"]["active"] is not None:
            title = f'in phase {esc(data["phase"]["active"])}'
    else:
        title = "nothing tracked. plan a phase, or run a health check."
    # The lead-in rides the statement's own baseline ("next: continue cg-12")
    # instead of standing as a small label above a big line.
    body = ['<span class="next-lead">next:</span>']
    if verb:
        body.append(f'<span class="next-verb">{verb}</span>')
    if mark:
        body.append(f'<span class="next-id">{mark}</span>')
    # The title is repeated from the card only when there is no card to look
    # at. Printing the same sentence twice, 130px apart, costs a re-read and
    # buys nothing: the lane already carries it, and the card is marked.
    if title and str(nxt["id"]) not in by_id:
        body.append(f'<span class="next-title">{title}</span>')
    out = f'<p class="next-body">{"".join(body)}</p>'
    # Ready work needs claiming before anything else happens, and that is a
    # literal command, so the board prints it instead of stopping one step
    # short of the act. Work already in flight has no such single next verb,
    # so nothing is invented for it.
    if nxt["kind"] == "ready" and nxt["id"] is not None:
        out += (f'<p class="next-cmd">bd update {esc(nxt["id"])} --claim</p>')
    return f'<section class="next" aria-label="next action">{out}</section>'


def html_phases(data):
    """The two blocks that turn the page from a snapshot into something to act
    on: what is still pending, what it is (purpose, research, plans, issues,
    verify), and which commands come next in which order, with the reason for
    that order.

    Same `phase_purpose_text()`/`phase_research_text()`/`phase_issues_text()`/
    `phase_verify_text()` helpers the terminal table calls (CARD-03), and the
    same wording, so a page open on a second screen cannot quietly disagree
    with the shell that produced it. The HTML side does not mirror the
    terminal's table-plus-PURPOSE-list split (D-01 leaves that layout choice
    to the terminal only) — this column stays a single per-phase list, with
    the purpose paragraph and the research/issues/verify meta spans folded
    into the same `<li>`.
    """
    phases = data.get("phases") or []
    pending = pending_phases(phases)
    cmds = data.get("next_commands") or []
    if not pending and not cmds:
        return ""

    out = ['<section class="panel">']

    if pending:
        out.append('<div class="panel-col">')
        out.append('<h2 class="panel-h">pending phases '
                   f'<span class="panel-n">{len(pending)}</span></h2>')
        out.append('<ol class="phase-list">')
        for p in pending:
            # Same D-04 helpers as the terminal panel — meta[0] is never
            # re-derived here, so the two surfaces cannot independently
            # summarize the same conflict differently.
            corrob = p.get("corroboration")
            conflict_cls = ""
            if corrob == "conflict":
                meta = [esc(conflict_summary_text(p))]
                has_blocks = any(c["severity"] == "blocks"
                                 for c in p["conflicts"])
                conflict_cls = " phase-conflict" if has_blocks \
                    else " phase-informs"
            elif corrob == "unknown":
                meta = [esc("corroboration unknown")]
                conflict_cls = " phase-unknown"
            else:
                meta = [esc(phase_state_text(p))]
            prog = phase_progress_text(p)
            if prog:
                meta.append(f'<span class="n">{esc(prog)}</span>')
            # Same D-04 helpers as the terminal table's rsch/issues/verify
            # columns — never re-derived here, so the two surfaces cannot
            # independently summarize the same phase differently (CARD-03).
            meta.append(f'<span class="n">{esc(phase_research_text(p))}</span>')
            meta.append(f'<span class="n">{esc(phase_issues_text(p))}</span>')
            meta.append(f'<span class="n">{esc(phase_verify_text(p))}</span>')
            if p["blocked_by"]:
                meta.append('waits on phase '
                            f'<span class="n">'
                            f'{esc(join_numbers(p["blocked_by"]))}</span>')
            reqs = ""
            if p.get("requirements"):
                reqs = ('<span class="phase-req">'
                        f'{esc(", ".join(p["requirements"]))}</span>')
            blocked = " is-waiting" if p["blocked_by"] else ""
            out.append(
                f'<li class="phase{blocked}{conflict_cls}">'
                f'<span class="phase-n">{p["number"]}</span>'
                '<span class="phase-body">'
                f'<span class="phase-title">{esc(p["title"] or "(untitled)")}'
                '</span>'
                f'<span class="phase-purpose">{esc(phase_purpose_text(p))}'
                '</span>'
                f'{reqs}'
                f'<span class="phase-meta">{" &middot; ".join(meta)}</span>'
                '</span></li>')
        out.append("</ol></div>")

    if cmds:
        out.append('<div class="panel-col">')
        out.append('<h2 class="panel-h">next commands</h2>')
        out.append('<ol class="cmd-list">')
        for c in cmds:
            cls = "cmd is-waiting" if c["blocked"] else "cmd"
            out.append(
                f'<li class="{cls}">'
                f'<code class="cmd-name">{esc(c["command"])}</code>'
                f'<span class="cmd-why">{esc(c["reason"])}</span></li>')
        out.append("</ol>")
        par = data.get("parallelism") or {}
        if par.get("note"):
            # Said out loud rather than left to be inferred from the graph.
            # `is-split` is only for the case that actually offers a choice.
            split = " is-split" if len(par.get("runnable") or []) > 1 else ""
            out.append(f'<p class="panel-par{split}">{esc(par["note"])}</p>')
        out.append('<p class="panel-foot">Order comes from the dependency '
                   'graph, not the phase number. Each command is derived from '
                   'that phase&rsquo;s own state on disk.</p>')
        out.append("</div>")

    out.append("</section>")
    return "".join(out)


def html_card(lane, iss, next_id=None):
    cls = "card"
    if next_id is not None and str(iss.get("id")) == str(next_id):
        # The card the next-action line points at. Marking it here is what
        # lets that line drop the duplicated title: the eye is sent to a
        # specific card instead of being handed the sentence twice.
        cls += " is-next"
    meta = [f'<span class="card-id">{esc(iss.get("id", "?"))}</span>']
    if issue_priority(iss) <= 1:
        meta.append(f'<span class="card-pri">p{issue_priority(iss)}</span>')
    if lane == "doing" and iss.get("assignee"):
        meta.append(f'<span>claimed by {esc(iss["assignee"])}</span>')
    deps = as_str_list(iss.get("blocked_by"))
    if lane == "blocked" and deps:
        meta.append(f'<span class="card-wait">{PEBBLE} waiting on '
                    f'{esc(deps[0])}</span>')
    if iss.get("_stale"):
        meta.append(f'<span class="card-stale">{PEBBLE} delivered phase'
                    '</span>')
    return (f'<li class="{cls}"><p class="card-title">'
            f'{esc(iss.get("title", ""))}</p>'
            f'<p class="card-meta">{"".join(meta)}</p></li>')


# (lane key, heading, empty-state copy) — the three lanes, in the order the
# terminal board renders them.
HTML_LANES = (("ready", "no work ready. plan a phase."),
              ("doing", "nothing in flight."),
              ("blocked", "nothing blocked."))


def html_lanes(data):
    """The three lanes, sized by whether they carry anything.

    Every lane keeps its section and its heading whatever the counts: a lane
    that vanished when it emptied would make "nothing blocked" indistinguish-
    able from "blocked was never checked". What an empty lane does NOT keep
    is an equal share of the width. Holding a third of the row for a zero,
    while the one populated lane wraps its titles inside a narrow column, is
    the ragged-comparison-grid failure with the roles reversed.
    """
    next_id = (data["next"] or {}).get("id")
    filled = [bool(items) for items in data["_lanes"]]
    sole = ' is-sole' if sum(filled) == 1 else ''
    out = []
    for (name, empty), items in zip(HTML_LANES, data["_lanes"]):
        zero = ' is-zero' if not items else ''
        body = (f'<ul class="cards">'
                f'{"".join(html_card(name, i, next_id) for i in items)}</ul>'
                if items else f'<p class="lane-empty">{empty}</p>')
        out.append(
            f'<section class="lane lane-{name}'
            f'{" is-empty" if not items else sole}" '
            f'aria-labelledby="lane-{name}-name"><header class="lane-head">'
            f'<p class="lane-n{zero}">{len(items)}</p>'
            f'<h2 class="lane-name" id="lane-{name}-name">{name}</h2>'
            f'</header>{body}</section>')
    # Populated lanes take twice the share of an empty one; with nothing on
    # the board at all the three stay even, because then the emptiness IS
    # the message and lopsided columns would just look broken.
    tracks = (" ".join("minmax(0, 2fr)" if f else "minmax(0, 1fr)"
                       for f in filled)
              if any(filled) else "repeat(3, minmax(0, 1fr))")
    return (f'<div class="lanes" style="--lane-tracks: {tracks}">'
            f'{"".join(out)}</div>')


def html_foot(data):
    phase = data["phase"]
    lines = []
    tally = [f'<span class="n done-n">{data["counts"]["closed"]}</span> done']
    if phase["total"]:
        tally.append(f'<span class="n">{phase["total"]}</span> phases on the '
                     'roadmap')
    lines.append(f'<p class="foot-line">{" &middot; ".join(tally)}</p>')
    lease_text = lease_line_text(data)
    if lease_text:
        lines.append(f'<p class="foot-line has-mark">{PEBBLE}'
                     f'<span class="foot-text">{esc(lease_text)}</span></p>')
    if data["note"]:
        lines.append(f'<p class="foot-line has-mark foot-note">{PEBBLE}'
                     f'<span class="foot-text">{esc(data["note"])}</span></p>')
    sync = data["sync"]
    if sync["configured"] and sync["stale"]:
        lines.append(f'<p class="foot-line has-mark">{PEBBLE}'
                     '<span class="foot-text">sync '
                     f'{esc(sync["detail"] or "stale")}. run '
                     '<span class="n">/cairn:sync-pull</span></span></p>')
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    lines.append(f'<p class="foot-line">generated <span class="n">{esc(stamp)}'
                 '</span> by <span class="n">cairn-status --html</span></p>')
    return f'<footer class="foot">{"".join(lines)}</footer>'


def render_html_inner(data):
    """Everything between the board markers, one block per line so a diff of
    two generations reads section by section."""
    # The terrain resolves the active phase when STATE.md leaves it out or
    # points off the roadmap. The header used to read the raw value and print
    # nothing, so the page could say where you stand in its SVG label and
    # stay silent in the line meant to tell you. One resolution, both places.
    model = terrain_model(data)
    if model:
        data = dict(data, phase=dict(data["phase"], active=model["active"]))
    return "\n".join([html_head(data), html_band(data), html_next(data),
                      html_phases(data), html_lanes(data), html_foot(data)])


def write_html_board(path, data):
    """{file, changed}: regenerate the board region of an HTML page.

    A path that does not exist yet is seeded from the shipped template and
    then spliced; an existing path keeps every byte outside the markers, so
    a user's own CSS, notes or wrapper markup survive regeneration. The
    generated region carries a timestamp, so consecutive runs do differ.
    """
    if path.is_dir():
        die(f"--html target is a directory: {path}", EXIT_USAGE)
    parent = path.parent
    if not parent.is_dir():
        die(f"--html directory does not exist: {parent} (create it first)",
            EXIT_USAGE)
    fresh = not path.is_file()
    source = TEMPLATE_PATH if fresh else path
    if fresh and not TEMPLATE_PATH.is_file():
        die(f"board template missing: {TEMPLATE_PATH}", EXIT_USAGE)
    try:
        old_text = source.read_text(encoding="utf-8")
    except OSError as e:
        die(f"cannot read {source}: {e}", EXIT_USAGE)
    except ValueError as e:
        # UnicodeDecodeError is a ValueError, not an OSError: an existing
        # target that is not UTF-8 text used to escape as a traceback and
        # exit 1, against the documented contract for an unusable target.
        die(f"cannot read {source} as UTF-8 text: {e}", EXIT_USAGE)
    spliced = splice_board(old_text, render_html_inner(data))
    if spliced == "damaged":
        die(f"{path} carries broken board markers (a lone marker, a "
            f"duplicate, or the end before the start). Nothing was written. "
            f"Repair the pair, or delete the file to regenerate it.",
            EXIT_USAGE)
    changed, new_text = spliced
    if changed or fresh:
        # Write to a sibling temp file and rename over the target, so an
        # interrupted run leaves the previous page intact instead of a
        # truncated one. os.replace is atomic within a filesystem, and the
        # temp file is a sibling precisely to stay on the same one.
        # The temp file is created 0600 by design, and os.replace carries
        # that mode onto the target. A board is a page somebody opens in a
        # browser or serves from a second machine, so it keeps the mode an
        # ordinary create would have given it: the existing file's own mode
        # when regenerating (the reader may have chosen it), otherwise
        # 0666 masked by the process umask, which is what write_text did.
        try:
            keep_mode = path.stat().st_mode & 0o777 if path.is_file() else None
        except OSError:
            keep_mode = None
        if keep_mode is None:
            umask = os.umask(0)
            os.umask(umask)
            keep_mode = 0o666 & ~umask
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                    "w", encoding="utf-8", dir=str(parent),
                    prefix=f".{path.name}.", suffix=".tmp",
                    delete=False) as fh:
                tmp = Path(fh.name)
                fh.write(new_text)
            os.chmod(str(tmp), keep_mode)
            os.replace(str(tmp), str(path))
        except OSError as e:
            if tmp is not None and tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            die(f"cannot write {path}: {e}", EXIT_USAGE)
    return {"file": str(path.resolve()), "changed": changed or fresh}


# ----------------------------------------------------------------------- main

def terminal_cols():
    # shutil.get_terminal_size already prefers $COLUMNS, then the tty ioctl,
    # then the (80, 24) fallback.
    return shutil.get_terminal_size((80, 24)).columns


def main():
    # Pipe-safety: a consumer that closes the pipe early (`cairn-status |
    # head -1`) must not produce a BrokenPipeError traceback — restore the
    # default SIGPIPE disposition Python masks (no-op where unavailable).
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    opts = parse_args(sys.argv[1:])
    if opts["planning_dir"]:
        planning_dir = Path(opts["planning_dir"]).resolve()
        root = planning_dir.parent
    else:
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
        planning_dir = root / ".planning"

    if shutil.which("bd") is None:
        die("'bd' not found on PATH — the board needs beads "
            "(consumers fall back on exit 5, never block)", EXIT_NO_BD)

    note = None
    if (root / ".beads").is_dir():
        # A cheap probe before the real lane queries: bd can be present on
        # PATH and still fail the call itself (crashed daemon, corrupted
        # DB) — that must degrade to "unknown" everywhere, not die via
        # fetch_lanes()/run_bd()'s die() before any output is produced.
        probe_cmd = ["bd", "-C", str(root), "list", "--limit", "1", "--json"]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True)
        if probe.returncode != 0:
            bd_ok = False
            ready, doing, blocked, closed, n_closed = [], [], [], [], 0
            note = (f"bd query failed at {root}: "
                    f"{probe.stderr.strip() or 'unknown error'} — "
                    "run /cairn:doctor")
        else:
            ready, doing, blocked, closed = fetch_lanes(root)
            # The lease bookkeeping issue (Plan 15-01) is real bd state —
            # a genuine claimed, in_progress issue — but never tracked
            # work. Exclude it before phase_model(), the stale-marker
            # cross-check, or the data dict ever sees it, so it can never
            # appear on any lane or inflate the done count (D-05).
            ready = [i for i in ready if not is_lease_issue(i)]
            doing = [i for i in doing if not is_lease_issue(i)]
            blocked = [i for i in blocked if not is_lease_issue(i)]
            closed = [i for i in closed if not is_lease_issue(i)]
            n_closed = len(closed)
            bd_ok = True
    else:
        # bd resolves its database by walking UP from the root, so querying
        # it here could silently render an ANCESTOR repo's board. Mirror
        # cairn-gate's applicability decision instead: skip bd and degrade
        # to a GSD-only board, saying so. This is "no bd usage here", not
        # "bd failed" — every phase's bd axis reads "none", never "unknown".
        ready, doing, blocked, closed, n_closed = [], [], [], [], 0
        note = f"no .beads/ at {root}: GSD-only board (bd lanes skipped)"
        bd_ok = True
    # ONE phase model, built once. Every surface below renders from this list
    # rather than re-deriving what it needs, so the terminal board, --json and
    # the HTML page cannot describe the same phase differently.
    phases = phase_model(planning_dir, ready + doing + blocked + closed, bd_ok=bd_ok)
    all_phases, done_phases = roadmap_phases(planning_dir, phases)
    # Cross-check (docstring step 4b): open issues whose phase labels are
    # all roadmap-complete keep their lane but get flagged. _stale drives
    # the card marker only — trim_issue never copies it into the JSON.
    done_set = set(done_phases)
    stale_ids = []
    for iss in ready + doing + blocked:
        if in_done_phase(iss, done_set):
            iss["_stale"] = True
            stale_ids.append(str(iss.get("id") or "?"))
    if stale_ids:
        # Mutually exclusive with the no-.beads note above: no .beads means
        # empty lanes, so stale_ids can only be non-empty when note is None.
        note = (f"{len(stale_ids)} open issue(s) belong to roadmap-complete "
                "phases. run /cairn:doctor --close-completed")
    fm = state_frontmatter(planning_dir)
    # DELIBERATELY UNCHANGED (Phase 22, BOARD-04). This still reads STATE.md
    # first, which is exactly the source that keeps pointing at the archived
    # cycle — and render_plain() prints it verbatim on its `MILESTONE\t...`
    # row. PIPE-01 forbids moving the TSV by one byte, so the machine contract
    # keeps publishing what it always published. The human surfaces stopped
    # following it: see open_milestones below and milestone_label(). The
    # tension is real and is tracked as an issue, not fixed in silence here.
    milestone = fm["milestone"] or roadmap_milestone(planning_dir)
    milestone = clean(milestone) if milestone else None
    # ONE read of the milestone list, shared with phase_groups() below: two
    # reads of the same file are two things that can disagree.
    milestones = roadmap_milestones(planning_dir)
    active_phase = normalize_phase(fm["active_phase"])
    nxt = synthesize_next(ready, doing, milestone, active_phase,
                          fm["next_action"], done_phases)
    sync = sync_status(root)
    # Additive: the active phase's lease status (Plan 15-01), for the
    # footer line D-05 adds — never re-derived by any renderer below, one
    # read shared by the terminal footer, --plain and the HTML foot.
    lease = fetch_lease_status(root, active_phase, bd_ok)

    data = {
        "ready": [trim_issue(i) for i in ready],
        "doing": [trim_issue(i) for i in doing],
        "blocked": [trim_issue(i) for i in blocked],
        "counts": {"ready": len(ready), "doing": len(doing),
                   "blocked": len(blocked), "closed": n_closed},
        "milestone": milestone,
        # Additive (Phase 22, BOARD-04): the cycles the ROADMAP itself marks
        # open, in roadmap order — the same source phase_groups() reads, and
        # never STATE.md. A LIST, not a scalar: a scalar would force this to
        # pick one in silence when a roadmap declares two open cycles, and
        # picking in silence is the family of defect BOARD-04 exists to end.
        # Empty means the roadmap declares no open cycle, which is a fact the
        # board states out loud rather than papering over — see
        # milestone_label().
        "open_milestones": [{"key": ms["key"], "label": ms["label"]}
                            for ms in milestones if ms["open"]],
        "phase": {"active": active_phase,
                  "total": len(all_phases) or None,
                  "completed": len(done_phases),
                  "title": active_phase_title(phases, active_phase)},
        # The described model, public in --json. Every phase carries what it
        # is, how far it has got, what it waits on and the next legal command.
        "phases": phases,
        # Computed from that model, not authored: which /cairn:* commands to
        # run next, in dependency order, each carrying why it sits there.
        "next_commands": next_commands(phases, milestone),
        # What can proceed at the same time — the input for splitting work
        # across agents, and for /cairn:autonomous to state the order it chose.
        "parallelism": parallelism(phases),
        # The same model seen as a hierarchy: open milestone → phase → issue,
        # plus one last group for work no emitted group claims.
        "groups": phase_groups(phases, milestones, ready + doing + blocked),
        "next": nxt,
        "sync": {k: sync[k] for k in ("configured", "stale", "detail",
                                      "last_pull")},
        "stale_complete": stale_ids,
        "note": note,
        "lease": lease,
        # Underscore keys are renderer-private: the --json summary filters
        # them out, so the machine contract stays exactly as documented.
        "_lanes": [ready, doing, blocked],
        "_closed": closed,
        "_phases": {"all": all_phases, "done": done_phases},
    }
    # EXIT_NO_BD (5) is the documented "bd unavailable" contract — a query
    # that failed after bd was found on PATH degrades exactly the same way
    # as bd missing entirely: real output first, on every render path below,
    # then this exit code rather than a silent EXIT_OK.
    exit_code = EXIT_OK if bd_ok else EXIT_NO_BD

    html_info = None
    if opts["html"] is not None:
        html_info = write_html_board(Path(opts["html"]), data)

    if opts["json"]:
        out = {k: v for k, v in data.items() if not k.startswith("_")}
        if html_info is not None:
            out["html"] = html_info
        print(json.dumps(out))
        sys.exit(exit_code)

    if html_info is not None:
        c = data["counts"]
        # "unchanged" is reachable: two runs inside the same minute with no
        # state change regenerate an identical region (the stamp is minute
        # resolution), and an identical region is never rewritten.
        state = "wrote" if html_info["changed"] else "unchanged"
        print(f"[cairn-status] {state} {html_info['file']} — "
              f"{c['ready']} ready, {c['doing']} doing, "
              f"{c['blocked']} blocked")
        sys.exit(exit_code)

    style = Style(opts)
    if opts["brief"]:
        lines = render_brief(data, style)
    elif opts["plain"]:
        # THE FLAG, AND ONLY THE FLAG (Phase 22, PIPE-02). Until 2026-08-06
        # this branch also fired whenever stdout was not a tty, so --plain did
        # two incompatible jobs: the TSV scripts consume, and the automatic
        # fallback for anyone without a terminal. That is how the machine
        # format ended up on the screen of someone who only wanted to look at
        # the board.
        #
        # A non-TTY run now takes the SAME human branch a terminal takes, and
        # the two differences are decided where they always were: Style turns
        # color off because isatty() is False (the precedence at the end of
        # _color_enabled), and terminal_cols() returns 80 (MEASURED
        # 2026-08-06: shutil.get_terminal_size falls back to (80, 24) with
        # stdout on a pipe and no $COLUMNS) — the same width a terminal
        # without $COLUMNS gets. No condition of the environment selects the
        # machine format any more.
        #
        # The coupling was a deliberate decision once: it kept box-drawing out
        # of pipes. Phase 21 removed the last box-drawing glyph from this
        # file, so the reason died before this line did.
        lines = render_plain(data)
    else:
        # ONE human renderer, every width. The two width degrades this branch
        # used to pick between existed because three columns do not fit in a
        # narrow terminal; a single grouped list fits everywhere and simply
        # wraps sooner.
        cols = opts["width"] if opts["width"] is not None else terminal_cols()
        lines = render_groups(data, cols, opts["max_rows"], style)
        lines += footer_lines(data, cols, style)
        lines += phase_panel_lines(data, cols, style)
    out = "\n".join(lines)
    try:
        print(out)
    except UnicodeEncodeError:
        # Non-Unicode stdout (C locale) with Unicode issue titles: degrade
        # the offending characters instead of crashing.
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        sys.stdout.buffer.write(out.encode(enc, errors="replace") + b"\n")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
