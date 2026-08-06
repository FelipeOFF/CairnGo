# /cairn:status

> One combined view driven by `bd ready` — a grouped list of the open work (milestone → phase → task), GSD roadmap position, and one suggested next action.

## Usage

```
/cairn:status [--brief] [--json] [--plain] [--html <path>]
```

Flags typed by the user are passed through to the renderer (full set in the
table below). The command runs the deterministic renderer and presents its
output verbatim:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-status.sh" [flags]
```

## What it does

1. Runs `cairn-status.sh` (a thin wrapper over `cairn-status.py`, zero-dependency
   Python 3). The script gathers everything itself.

   First, three bd queries. They are called **lanes** because a lane is where
   a row comes FROM — each row's stage symbol is read off the lane it arrived
   on — and not because anything on screen is arranged in lanes:
   - **READY** — `bd ready --json`: the truly claimable list. Dependencies,
     gates, and `defer_until` are respected; in_progress and blocked issues are
     excluded. Renders with `◔`.
   - **DOING** — `bd list --status in_progress --json`. Renders with `◕`, and
     the assignee after a `◆` marker.
   - **BLOCKED** — `bd blocked --json`. Renders with `⧗`, and names **every**
     blocker in words on the row itself (`blocked by brd-001, brd-007`).
   - **Roadmap position** — ROADMAP.md and STATE.md parsed leniently (completed
     phases, `active_phase` frontmatter). The **open milestone** comes from the
     `🚧` marker on its own line in ROADMAP.md's `## Milestones` list, never
     from STATE.md's `milestone:` — that pointer keeps naming the archived
     cycle after a milestone is completed, which is how the board used to
     announce a milestone that had shipped ten minutes earlier.
   - **External tracker cards** — read from two places that are already local,
     with no network call of any kind (see
     [The board never touches the network](#the-board-never-touches-the-network)):
     - per issue, from bd's own `external_ref` field (`bd update <id>
       --external-ref jira-DTP-142`, which `/cairn:doctor --link-refs` already
       writes as `gh-<n>`). It renders as a `⧉ <key>` suffix on the card;
     - per phase, from an optional `**Tracker:**` line inside that phase's
       `### Phase N:` block in ROADMAP.md, beside `**Card:**` and `**Goal:**`
       (see [What the board reads from ROADMAP.md](#what-the-board-reads-from-roadmapmd)).
   - **Sync staleness** — when `.cairn/sync.json` exists, checked against the
     last-pull watermark in `.cairn/state.json`.
2. Renders **one grouped list**, at every width: the four counts
   (`ready N · doing N · blocked N · done N`), then the open milestone, then
   its phases in roadmap order, then each phase's tasks, with work no phase
   claims last. Every row carries its stage in a single-cell symbol
   (`◌` not planned · `◔` planned · `◕` in progress · `✓` done · `⧗` blocked),
   and **a task title is never truncated** — a row too long for the width
   wraps into a continuation aligned under the title.

   There is no width degrade and no kanban grid. Three lanes did not fit a
   narrow terminal and one list fits any, so the columns/stacked/raw ladder
   went out with the renderers it chose between.

   When the roadmap declares no open milestone, the list still shows the
   pending phases under a group that says so by name. It never falls silent
   while the footer and the table below it count phases.
3. Prints a footer below the list: `phase X/Y <title> · <milestone> ·
   done: N` — or `no open milestone` where the name would be — then
   `▶ next: <one action>`, then a sync-staleness line when relevant (stale or
   missing watermark → suggests `/cairn:sync-pull`).
3b. Prints the **phase panel** below the footer — the part that answers which
   phase to run rather than what work exists:
   - **PENDING PHASES** — a table, one row per unfinished phase: number,
     title, where it stands (`not planned` / `planned` / `executed` /
     `verified`), whether research exists, plan progress, issue progress, the
     verification verdict, what it waits on, and the next legal command. The
     point is choosing the next phase without opening ROADMAP.md.

     **It fits the width it was given.** A column that does not fit shrinks to
     its floor, and then leaves — and a column that left is named, on a line
     under the table (`hidden at this width: waits, rsch — widen, or
     /cairn:status --json`). A column is never squeezed until its own header
     reads `issu…`. Below the width its core needs, the table steps aside and
     says how many columns it wants; PURPOSE, below, still carries every phase.
   - **PURPOSE** — each phase's purpose in full, paired with the reason the
     next command sits where it does. This is the one block that **wraps**
     rather than truncates: a phase's purpose is never cut. The command comes
     from that phase's own state on disk (`no PLAN → /cairn:plan`,
     `PLAN → /cairn:work`, `SUMMARY → /cairn:verify`), so it cannot claim a
     phase needs planning after someone planned it. The **order comes from the
     dependency graph**, not the phase number — free work first, so a blocked
     earlier phase is never listed above a later one that can actually run. A
     milestone with nothing pending gets `/cairn:ship`, then
     `/cairn:milestone complete`.
   - **The parallelism note** — what could proceed at the same time, and the
     concrete split. When no dependency is declared anywhere in the roadmap it
     says so, rather than reporting every phase as independent and letting
     that read as a verified ordering.

   Dependencies are read from bd's own issue edges first (they exist from the
   moment the milestone creates the issues) and from `PLAN.md`'s `depends_on:`
   frontmatter second. A dependency counts as satisfied when the phase is
   complete **or** verified on disk — the work being done is what matters, not
   the roadmap checkbox catching up.
4. **Synthesizes ONE next action**, in order: an in_progress issue exists →
   continue it; else the highest-priority ready issue of the active phase
   (filtered by the `m-<milestone>,phase-<active>` label pair); else the next
   GSD step from STATE.md. When bd and STATE.md disagree, the rule is stated
   explicitly: **bd wins for work items, STATE.md wins for workflow steps** —
   neither overrides the other.
5. Fits the width it has. One renderer at every width: rows wrap instead of
   being cut, and the phase panel gives up columns instead of running off the
   edge. The only thing allowed past the margin is a single token wider than
   the column itself (a long URL in a title) — splitting it would be a form
   of truncation, and letting it overflow is the terminal's own wrap.
6. When stdout is **not a TTY** (pipes, redirects), prints **the same board**
   in plain text: no ANSI escapes (color already ends at `isatty`) and 80
   columns (the `shutil.get_terminal_size` fallback, the same width a
   terminal without `$COLUMNS` gets).

   > **If you have a script reading this output, read this.** Until this
   > change, a flagless non-TTY run silently switched to `--plain`, so a pipe
   > or a redirect got the tab-separated machine format. It now gets the human
   > board. **The fix is to write `--plain`,** which is byte-for-byte the
   > format it always was and is the only door to it — no condition of the
   > environment selects it any more.
7. With `--html <path>`, renders the same data as a standalone HTML board
   instead (see [The HTML board](#the-html-board)).

The skill presents the board verbatim (in a code fence, never paraphrased).
On exit 5 it falls back to a minimal prose view via `/gsd:progress`.

## Flags & arguments

| Flag | Effect |
| --- | --- |
| `--json` | Single-line machine-readable JSON (stable dict shape); gains an `html` key when `--html` also ran |
| `--plain` | **The machine contract**, and the only way to reach it: tab-separated rows, no color, nothing truncated. Byte-for-byte what it has always been — pinned by two committed references, `tests/fixtures/board-render/plain.txt` and `tests/fixtures/machine-contract/nontty-pre-split.txt` |
| `--brief` | Three lines only: header, counts, next action |
| `--html <path>` | Write/refresh a standalone HTML board at `<path>`, print one confirmation line. Composes with `--json` and `--planning-dir`; refused with `--plain` / `--brief` |
| `--width N` | Render at N columns instead of the detected terminal width (deterministic output) |
| `--max-rows N` | Rows per **bucket** before a `+k more` row (default 15). Per bucket, not per lane: the cap follows the thing the list groups by |
| `--ascii` | One-character stage symbols (`. o O v ~`) and `...` instead of the Unicode set. There are no borders to swap — the box-drawing went out with the kanban |
| `--color=always\|never` | Force color on or off. Color only: a piped run renders the board either way, so there is no renderer for this flag to opt into |
| `--planning-dir <dir>` | Use an alternate planning dir (default `.planning/`) |

Color precedence: `--color` > `CAIRN_NO_COLOR` > `NO_COLOR` > `TERM=dumb` >
`isatty(stdout)`. Colors are 4-bit only: DOING yellow, BLOCKED red, done
green in the footer; color on the stage symbol, the counts and high-priority
ids, never on a whole row.

**Alignment and locale.** Column alignment is guaranteed in a Western locale
and **is not guaranteed in a CJK one**. A large set of characters
(`east_asian_width=A`) takes one cell in a Latin locale and two in a CJK one,
and this board's own prose is Portuguese, where every accented letter is in
that set — so choosing different glyphs cannot fix it, and reading the locale
would mean guessing what only the terminal emulator knows. The measurement and
the full argument are in `char_width()`'s docstring in `cairn-status.py`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Board rendered |
| `2` | Usage error (unknown flag, bad value, or an unusable `--html` target/template) |
| `5` | `bd` not on PATH — fall back to the GSD-only prose view (`/gsd:progress`) |

## The HTML board

```
$ bash cairn/scripts/cairn-status.sh --html status.html
[cairn-status] wrote /repo/status.html — 5 ready, 1 doing, 1 blocked
```

A page for the second monitor: the same data as the terminal board, laid out
to answer *where are we* and *what do I pick up now* at a glance.

**A generated view, like `NN-BEADS-MAP.md`.** Everything between
`<!-- cairn:generated:board:start -->` and `<!-- cairn:generated:board:end -->`
belongs to the renderer. Every byte outside those markers is preserved exactly
— restyle the CSS, retitle the page, add your own notes around the board and
they all survive regeneration. A path that does not exist yet is seeded from
`templates/status-board.html`; a file that exists but has lost its markers
gets the block appended, never destroyed. (Same marker mechanics as
`cairn-map.py` and `benchmarks/scripts/bench-publish.py`.)

**The roadmap as terrain.** The signature element is a topographic profile
read from real state, not decoration:

| What you see | What it means |
| --- | --- |
| One terrain segment per phase | The phases in `ROADMAP.md`, in order |
| Its elevation | How many issues carry that `phase-N` label, open **and** closed |
| Filled, stratified ground | The ground already walked, up to the active phase |
| A dotted trail | The climb still ahead — no ground drawn under it |
| The cairn | Where you stand (`active_phase`, or the first phase the roadmap has not completed) |
| Phase number in green / white / grey | Delivered / you are here / ahead |

The terrain runs past the text column and off both page edges: the ground on
either side of the roadmap is unmapped trail, drawn so the phases stay
centred under their own tick marks. On a long roadmap the scale stops
numbering every phase and labels index phases only (every 2nd, 5th or 10th,
plus the one you are standing in), the way a contour map labels index lines;
the phases in between keep their place as a plain tick.

With no roadmap phases the band degrades to a flat horizon carrying the
counts. It never invents relief it cannot read from the data.

**Zero network.** Styles, texture and the profile are all inline: no CDN, no
webfont, no script, no image request. The page renders identically offline,
from a `file://` URL, or inside a locked-down viewer. All issue text is
HTML-escaped on top of the existing control-byte sanitising, so a title
carrying markup renders as text.

**It is a snapshot.** Nothing watches the repo — re-run the command to
refresh. The page carries the timestamp it was generated at.

## Examples

> Every block below is a **captured run**, not a drawing. Source: the
> deterministic `make_board_fixture` from `tests/helpers.bash` (fixed issue
> ids, so the output is reproducible), rendered with `--color=never`, on
> 2026-08-06. To re-capture, build that fixture in a scratch repo and run the
> command shown. The previous example on this page was hand-drawn, which is
> exactly how it went on describing a kanban board for a year after the kanban
> was deleted.

Full board in a terminal:

```
$ bash cairn/scripts/cairn-status.sh --width 100
ready 3 · doing 1 · blocked 1 · done 1

v1.1 Surface
  ◔ 3  Phase model — read what a phase actually is
      ◔ brd-001  Read the roadmap into a phase model
      ◕ brd-004  Hold the lease while executing  ◆ cairn-tests
  ◌ 4  Board fills the screen
      ◔ brd-002  Fill the screen at any width
      ⧗ brd-005  Wait on the phase model  blocked by brd-001

No milestone
      ◔ brd-003  Sweep the backlog

phase 3/4 Phase model — read what a phase actually is · v1.1 Surface · done: 1
▶ next: continue brd-004 — Hold the lease while executing

PENDING PHASES  2
  #  phase     state             rsch   plans   issues   verify            waits    next
  3  Phase m…  planned           —      0/1 p…  0/2      —                 —        /cairn:work 3
  4  Board f…  not planned       —      —       0/2      —                 3        /cairn:plan 4

PURPOSE
  3  Phase model — read what a phase actually is — nothing blocks it, and phase 4 waits on it
  4  Board fills the screen — waits on phase 3

  One phase can move: /cairn:work 3. Phase 4 waits.
```

Note the fixture's own trap, visible in that output: `STATE.md` names `v1.0`,
the archived cycle, while the footer reads `v1.1 Surface`. The header follows
the roadmap's `🚧` marker, not the stale pointer.

Three-line summary:

```
$ bash cairn/scripts/cairn-status.sh --brief
[cairn-status] phase 3/4 Phase model — read what a phase actually is · v1.1 Surface
ready 3 · doing 1 · blocked 1 · done 1
▶ next: continue brd-004 — Hold the lease while executing
```

**Through a pipe, the two surfaces side by side.** No flag gets the board in
plain text; `--plain` gets the machine contract:

```
$ bash cairn/scripts/cairn-status.sh | head -6
ready 3 · doing 1 · blocked 1 · done 1

v1.1 Surface
  ◔ 3  Phase model — read what a phase actually is
      ◔ brd-001  Read the roadmap into a phase model
      ◕ brd-004  Hold the lease while executing  ◆ cairn-tests

$ bash cairn/scripts/cairn-status.sh --plain | head -3
READY	brd-001	0	Read the roadmap into a phase model	
READY	brd-002	1	Fill the screen at any width	
READY	brd-003	2	Sweep the backlog	
```

Those `--plain` rows end in a **trailing tab**, and it is not stray: an issue
row is always five fields — `LANE`, `ID`, `PRIORITY`, `TITLE`, `EXTRA` — and
`EXTRA` is empty on the READY lane (it carries the assignee on DOING and the
blockers on BLOCKED). A fixed field count is what lets `cut -f4` mean the same
thing on every row. The meta rows below them (`PHASE`, `MILESTONE`, `DONE`,
`NEXT`, `LEASE`, `SYNC`, `NOTE`) carry their own field counts.

Machine consumption:

```
$ bash cairn/scripts/cairn-status.sh --json | jq .ready
```

The phase panel is machine-readable too, which is what lets other commands
stop re-deriving it:

```
# every pending phase, described
$ bash cairn/scripts/cairn-status.sh --json \
    | jq '.phases[] | select(.complete | not)
          | {number, title, disk_state, blocked_by, next_command}'

# the order, and the reason for it
$ bash cairn/scripts/cairn-status.sh --json | jq -r '.next_commands[]
    | "\(.command)\t\(.reason)"'

# what could run at the same time
$ bash cairn/scripts/cairn-status.sh --json | jq -r .parallelism.note
```

| Key | Shape |
|---|---|
| `ready[] / doing[] / blocked[]` | `{id, title, priority, assignee, external_ref, labels[], blocked_by[]}` — `external_ref` is bd's own field, carried **raw** (backend prefix included); the board strips the prefix for display only |
| `phases[]` | `{number, title, milestone, complete, completed_on, plans_done, plans_total, requirements[], purpose, tracker, dir, disk_state, depends_on[], blocked_by[], next_command}` — `tracker` is the `**Tracker:**` line, also raw |
| `next_commands[]` | `{command, phase, title, reason, blocked}`, ordered — unblocked first |
| `parallelism` | `{runnable[], blocked[], declared, note}`; `declared` is false when no dependency is recorded anywhere, and the note says so |

`/cairn:autonomous` reads exactly these keys to resolve and **announce** the
order it runs phases in, instead of deciding silently.

## What the board reads from ROADMAP.md

Inside a phase block (`### Phase N: <title>`), three bold labels are read, all
in the same single pass over the file:

| Label | Meaning | Where it shows |
| --- | --- | --- |
| `**Card:**` | The phase purpose, one sentence, verbatim | The PURPOSE list |
| `**Goal:**` | Fallback purpose when there is no `Card` — first sentence only | The PURPOSE list |
| `**Tracker:**` | The external tracker key of the whole phase (`DTP-142`, `jira-DTP-142`) | Beside the phase title in PENDING PHASES, as `⧉ <key>` |

```markdown
### Phase 7: Billing

**Card:** invoices reconcile against the ledger without a human.
**Tracker:** jira-DTP-142
```

The label is `Tracker` and not `Card` because `**Card:**` already means the
phase purpose in this grammar — reusing the word inside the same block would
make the parser and the reader disagree about which one a line is.

A phase with no `**Tracker:**` line renders exactly as it did before the label
existed. The key rides beside the title and takes its room from it; when the
`phase` column is too narrow to leave the title 12 readable cells, the key is
dropped and the title takes the column back.

## The board never touches the network

Every row on the board comes from data that is already on the machine: bd's
local database and `ROADMAP.md`. Nothing is fetched — not a title, not a
status, not an avatar.

That is not a promise, it is a test. `tests/cairn-tracker-card.bats` renders
the whole board under two independent tripwires and asserts what each one
covers:

| Layer | What it catches | Its negative control |
| --- | --- | --- |
| A `sitecustomize` that raises on `socket.connect` | Any `urllib` / `http.client` / raw socket opened **inside** the renderer | A one-line `python3` that opens a connection under the same `PYTHONPATH` and must fail |
| A `PATH` holding only `bd`, `git`, `python3`, `jq`, plus a trapped `curl`/`wget` that log their argv | Any network tool run **outside** the process, in a child that does not inherit the socket patch | A one-line `python3` that runs `curl` under the same `PATH` and must appear in the log |

The second layer exists because the first one does not cover the case that
matters. MEASURED: with the socket tripwire installed, `subprocess.run(['curl',
…])` in the same process returns **200** — a child process does not inherit
a patched `socket` module, and `cairn-status.py` shells out in four places. A
live fetch added later as a subprocess would sail past a socket-only test.

**ASSUMED, and out of reach of both layers:** what `bd` itself does inside its
own process. It is a third-party Go binary on the allowlist; what is proved is
that *this script* opens no socket and invokes no network tool.

## Files touched

- **Reads:** beads state via `bd` (`ready`, `list`, `blocked`),
  `.planning/ROADMAP.md`, `.planning/STATE.md`, `.cairn/sync.json`,
  `.cairn/state.json` (sync watermark); `templates/status-board.html` when
  `--html` seeds a new page
- **Writes:** nothing — read-only, except the `--html` target, and there only
  the region between the board markers

## Related

- [/cairn:progress](progress.md) — GSD-only roadmap view (no beads)
- [/cairn:issues](issues.md) — flat issue listing, optionally per phase
- [/cairn:sync-pull](sync-pull.md) — refresh when the sync line reports stale
- [/cairn:quick](quick.md) — released quick issues reappear in the READY lane
