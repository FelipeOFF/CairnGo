# /cairn:status

> One combined view driven by `bd ready` — a kanban status board (actionable, in-flight, blocked), GSD roadmap position, and one suggested next action.

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
   Python 3). The script gathers everything itself:
   - **READY** lane — `bd ready --json`: the truly claimable list. Dependencies,
     gates, and `defer_until` are respected; in_progress and blocked issues are
     excluded.
   - **DOING** lane — `bd list --status in_progress --json` (assignees shown
     with a `◆` marker).
   - **BLOCKED** lane — `bd blocked --json` (blocking dependency shown with a
     `⧗ <dep-id>` marker).
   - **Roadmap position** — ROADMAP.md and STATE.md parsed leniently (completed
     phases, 🚧 milestone marker, `active_phase` / `milestone` frontmatter).
   - **Sync staleness** — when `.cairn/sync.json` exists, checked against the
     last-pull watermark in `.cairn/state.json`.
2. Renders a three-lane kanban board on one shared box-drawing grid (never a
   box per card), with lane headers like `READY (3)`.
3. Prints a footer **outside** the grid: `phase X/Y · <milestone> · done: N`,
   then `▶ next: <one action>`, then a sync-staleness line when relevant
   (stale or missing watermark → suggests `/cairn:sync-pull`).
4. **Synthesizes ONE next action**, in order: an in_progress issue exists →
   continue it; else the highest-priority ready issue of the active phase
   (filtered by the `m-<milestone>,phase-<active>` label pair); else the next
   GSD step from STATE.md. When bd and STATE.md disagree, the rule is stated
   explicitly: **bd wins for work items, STATE.md wins for workflow steps** —
   neither overrides the other.
5. Degrades gracefully by width: full columns → vertically stacked lanes
   (below ~64 columns) → raw `LANE  id  title` list (below 40 columns). The
   grid never wraps.
6. When stdout is **not a TTY** (pipes, redirects) and no output flag was
   given, the script automatically switches to `--plain`: clean tabular
   output, zero ANSI escapes, zero box-drawing, titles untruncated.
7. With `--html <path>`, renders the same data as a standalone HTML board
   instead (see [The HTML board](#the-html-board)).

The skill presents the board verbatim (in a code fence, never paraphrased).
On exit 5 it falls back to a minimal prose view via `/gsd:progress`.

## Flags & arguments

| Flag | Effect |
| --- | --- |
| `--json` | Single-line machine-readable JSON (stable dict shape); gains an `html` key when `--html` also ran |
| `--plain` | Tabular TSV-like output, no color, no box-drawing |
| `--brief` | Three lines only: header, counts, next action |
| `--html <path>` | Write/refresh a standalone HTML board at `<path>`, print one confirmation line. Composes with `--json` and `--planning-dir`; refused with `--plain` / `--brief` |
| `--width N` | Override detected terminal width (deterministic output) |
| `--max-rows N` | Rows per lane before a `+k more` footer (default 15) |
| `--ascii` | ASCII borders and `...` truncation instead of Unicode |
| `--color=always\|never` | Force color on or off |
| `--planning-dir <dir>` | Use an alternate planning dir (default `.planning/`) |

Color precedence: `--color` > `CAIRN_NO_COLOR` > `NO_COLOR` > `TERM=dumb` >
`isatty(stdout)`. Colors are 4-bit only: DOING yellow, BLOCKED red, done
green in the footer; color on headers/counts/glyphs, never on whole cards.

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

Full board in a terminal:

```
$ bash cairn/scripts/cairn-status.sh --width 100
┌──────────────────────┬──────────────────────┬──────────────────────┐
│ READY (2)            │ DOING (1)            │ BLOCKED (1)          │
├──────────────────────┼──────────────────────┼──────────────────────┤
│ app-12  Add auth …   │ app-9  Status boa…   │ app-14  Deploy pi…   │
│ app-13  Fix flaky…   │        ◆ felipe      │         ⧗ app-12     │
└──────────────────────┴──────────────────────┴──────────────────────┘
phase 3/5 · v1.0 · done: 7
▶ next: continue app-9 (Status board renderer)
```

Three-line summary:

```
$ bash cairn/scripts/cairn-status.sh --brief
```

Machine consumption (also what pipes get, minus the JSON shape):

```
$ bash cairn/scripts/cairn-status.sh --json | jq .ready
```

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
