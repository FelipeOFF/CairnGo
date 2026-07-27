#!/usr/bin/env python3
"""cairn-status — render the combined bd + GSD status board.

One deterministic, pipe-safe render of the repo's working state: three lanes
(READY / DOING / BLOCKED) driven by bd, a footer with the GSD roadmap
position, and ONE synthesized next action. Prints top-down and exits — no
alternate screen, no cursor addressing, no animation.

Usage:
    cairn-status.py [--json] [--plain] [--brief] [--width N] [--max-rows N]
                    [--ascii] [--color=always|never] [--planning-dir <dir>]

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
       applicability decision.
    3. Read GSD position leniently (regex, no YAML lib — patterns shared
       with cairn-gate, except TABLE_PHASE_ANY which is stricter, see its
       comment): ROADMAP.md phase checkboxes / progress-table rows and the
       🚧 milestone line; STATE.md frontmatter `milestone:`, `active_phase:`
       and `next_action:`. All of it is optional — missing files degrade to
       an issues-only board.
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
    5. Render. TTY: box-drawing kanban board sized to the terminal, degrading
       gracefully — columns (>= 64 cols) → stacked lanes (>= 40 cols) → raw
       list (< 40 cols). Non-TTY without an output flag: --plain
       automatically (gh model — zero escape bytes, tab-separated,
       untruncated). --width N forces the board renderer at that width
       (deterministic for tests and pipes); --color=always likewise opts
       into the board renderer when piped, so the flag is never silently
       ignored (--ascii alone does not force it). All bd/STATE.md text is
       passed through clean(), which strips C0/C1 control bytes — titles
       from remote trackers can't inject escape sequences or forge rows.
    6. When .cairn/sync.json exists, append a sync-staleness line from the
       last-pull watermarks in .cairn/state.json (missing or older than 24h
       → suggest /cairn:sync-pull).

    --json      one machine line: {ready, doing, blocked, counts, milestone,
                phase, next, sync, stale_complete, note}
    --plain     tab-separated rows (LANE, ID, PRIORITY, TITLE, EXTRA) plus
                PHASE/MILESTONE/DONE/NEXT/SYNC/NOTE meta rows; no color, no
                truncation
    --brief     three lines: position, counts, next action
    --width N   render the board at N columns (overrides terminal size)
    --max-rows N  cap rows per lane (default 15); overflow shows "+k more"
    --ascii     +-| borders and "..." (also automatic on non-UTF-8 stdout)
    --color     always|never; default: auto. Precedence: --color >
                CAIRN_NO_COLOR > NO_COLOR (present and non-empty, even "0")
                > TERM=dumb > isatty(stdout). `always` also opts a piped
                run into the board renderer (see 5)

Exit codes:
    0 ok    2 usage    5 bd unavailable (not on PATH, or a bd query failed)
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BD = 5

USAGE = ("usage: cairn-status.py [--json] [--plain] [--brief] [--width N] "
         "[--max-rows N] [--ascii] [--color=always|never] "
         "[--planning-dir <dir>]")

MIN_INNER = 18          # narrowest readable lane content
MAX_INNER = 40          # widest useful lane content
N_LANES = 3
STACK_BELOW = N_LANES * (MIN_INNER + 2) + (N_LANES + 1)   # 64 cols
RAW_BELOW = 40
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


def die(msg, code):
    print(f"[cairn-status] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    opts = {"json": False, "plain": False, "brief": False, "width": None,
            "max_rows": DEFAULT_MAX_ROWS, "ascii": False, "color": "auto",
            "planning_dir": None}
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
        elif arg == "--planning-dir":
            if i + 1 >= len(argv):
                die(f"--planning-dir needs a value\n{USAGE}", EXIT_USAGE)
            opts["planning_dir"] = argv[i + 1]
            i += 2
        else:
            die(f"unknown argument '{arg}'\n{USAGE}", EXIT_USAGE)
    if opts["json"] + opts["plain"] + opts["brief"] > 1:
        die(f"choose one of --json / --plain / --brief\n{USAGE}", EXIT_USAGE)
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


def in_done_phase(iss, done_set):
    """True when the issue is phase-labeled and EVERY phase label points at
    a roadmap-complete phase — an open issue the roadmap says was already
    delivered. A cross-phase issue stays live while any of its phases is
    still open, and an unlabeled issue is never stale."""
    ns = issue_phase_ns(iss)
    return bool(ns) and ns <= done_set


def trim_issue(iss):
    """Stable, minimal issue dict for the JSON summary."""
    return {"id": str(iss.get("id") or "?"),
            "title": iss.get("title", ""),
            "priority": issue_priority(iss),
            "assignee": iss.get("assignee") or None,
            "labels": as_str_list(iss.get("labels")),
            "blocked_by": as_str_list(iss.get("blocked_by"))}


def fetch_lanes(root):
    ready = run_bd(["ready", "-n", "0"], root)
    doing = run_bd(["list", "--status", "in_progress", "--limit", "0"], root)
    blocked = run_bd(["blocked"], root)
    closed = run_bd(["list", "--status", "closed", "--limit", "0"], root)
    # str() on the id: an explicit null must not TypeError the sort.
    key = lambda i: (issue_priority(i), str(i.get("id") or ""))  # noqa: E731
    return (sorted(ready, key=key), sorted(doing, key=key),
            sorted(blocked, key=key), len(closed))


# --------------------------------------------------------------- GSD reading

def read_lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def roadmap_phases(planning_dir):
    """(total, completed) phase numbers from ROADMAP.md — checkbox lines and
    milestone progress-table rows, parsed with cairn-gate's lenient checkbox
    patterns plus the stricter TABLE_PHASE_ANY (see its comment)."""
    all_ns, done_ns = set(), set()
    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = ANY_PHASE.match(line)
        if m:
            all_ns.add(int(m.group(1)))
            if CHECKED_PHASE.match(line):
                done_ns.add(int(m.group(1)))
            continue
        m = TABLE_PHASE_ANY.match(line)
        if m:
            n = int(m.group(1) or m.group(2))
            all_ns.add(n)
            if TABLE_PHASE_DONE.match(line):
                done_ns.add(n)
    return sorted(all_ns), sorted(done_ns)


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
        if "🚧" in line or re.search(r"\(in progress\)", line, re.IGNORECASE):
            m = VERSION_TOKEN.search(line)
            if m:
                return m.group(0)
    return None


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
    if ch == "\u200d" or "\ufe00" <= ch <= "\ufe0f":
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


# C0 (minus \t and \n, which the whitespace collapse turns into spaces),
# DEL, and C1 — ESC, CSI, OSC and friends. Titles can come from remote
# trackers via sync-pull, so control bytes are attacker-reachable.
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def clean(text):
    """One safe display line: strip control bytes, collapse whitespace."""
    return re.sub(r"\s+", " ", CONTROL_CHARS.sub("", str(text))).strip()


# ------------------------------------------------------------------ rendering

class Style:
    """Color + glyph decisions, resolved once."""

    def __init__(self, opts):
        enc = (getattr(sys.stdout, "encoding", None) or "").lower()
        self.ascii = opts["ascii"] or "utf" not in enc
        self.color = self._color_enabled(opts)
        if self.ascii:
            self.tl, self.tm, self.tr = "+", "+", "+"
            self.bl, self.bm, self.br = "+", "+", "+"
            self.h, self.v = "-", "|"
            self.ell, self.sep = "...", " | "
            self.g_next, self.g_dep, self.g_who = ">", "<-", "@"
            self.g_stale = "*"
        else:
            self.tl, self.tm, self.tr = "┌", "┬", "┐"
            self.bl, self.bm, self.br = "└", "┴", "┘"
            self.h, self.v = "─", "│"
            self.ell, self.sep = "…", " · "
            self.g_next, self.g_dep, self.g_who = "▶", "⧗", "◆"
            self.g_stale = "·"

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


def make_cell(lane, iss, inner, style):
    """One card as spans: `id  title` (+ ⧗ dep on BLOCKED, ◆ assignee on
    DOING). Only glyphs and high-priority ids get color — never the whole
    card. The id is capped at inner - 8 cells so a long bd prefix can never
    push the card past the lane (the title keeps at least a sliver)."""
    iid = truncate(clean(iss.get("id", "?")), max(1, inner - 8), style.ell)
    title = clean(iss.get("title", ""))
    id_sgr = SGR_BOLD if issue_priority(iss) <= 1 else None

    suffix = []
    if lane == "DOING" and iss.get("assignee"):
        who = truncate(clean(iss["assignee"]), 12, style.ell)
        suffix = [("  ", None), (style.g_who, SGR_YELLOW), (" " + who, None)]
    elif lane == "BLOCKED" and as_str_list(iss.get("blocked_by")):
        dep = clean(as_str_list(iss.get("blocked_by"))[0])
        suffix = [("  ", None), (style.g_dep, SGR_RED), (" " + dep, None)]
    if iss.get("_stale"):
        # Discreet roadmap-complete marker (see docstring step 4b) — dim,
        # ASCII-safe under --ascii, dropped like any suffix when too narrow.
        suffix += [("  ", None), (style.g_stale + "done-phase", SGR_DIM)]

    used = display_width(iid) + 2
    suffix_w = sum(display_width(t) for t, _ in suffix)
    if suffix and inner - used - suffix_w < 6:
        suffix, suffix_w = [], 0      # too narrow — the title wins
    title_t = truncate(title, inner - used - suffix_w, style.ell)
    spans = [(iid, id_sgr), ("  ", None), (title_t, None)] + suffix
    pad = inner - sum(display_width(t) for t, _ in spans)
    if pad > 0:
        spans.append((" " * pad, None))
    return spans


def lane_rows(lane, items, inner, max_rows, style):
    """Visible cells for a lane, with a dim `+k more` overflow row."""
    rows = [make_cell(lane, i, inner, style) for i in items[:max_rows]]
    extra = len(items) - max_rows
    if extra > 0:
        text = f"+{extra} more"
        rows.append([(text, SGR_DIM), (" " * (inner - len(text)), None)])
    return rows


def lane_header_text(name, count, seg_w, style):
    text = f"{name} ({count})"
    if display_width(text) > seg_w - 3:
        name_t = truncate(name, seg_w - 3 - display_width(f" ({count})"),
                          style.ell)
        text = f"{name_t} ({count})"
    return text


def render_board(lanes_items, counts, inner, max_rows, style):
    seg_w = inner + 2
    lines = []

    # Top border with embedded lane headers: ┌─ READY (2) ──┬─ DOING (1) ─...
    spans = [(style.tl, SGR_BORDER)]
    for idx, ((name, sgr), items) in enumerate(zip(LANES, lanes_items)):
        text = lane_header_text(name, counts[idx], seg_w, style)
        fill = seg_w - 3 - display_width(text)
        spans += [(style.h + " ", SGR_BORDER), (text, sgr), (" ", None),
                  (style.h * fill, SGR_BORDER)]
        spans.append((style.tm if idx < N_LANES - 1 else style.tr,
                      SGR_BORDER))
    lines.append(render_spans(spans, style))

    per_lane = [lane_rows(name, items, inner, max_rows, style)
                for (name, _), items in zip(LANES, lanes_items)]
    n_rows = max(1, max(len(r) for r in per_lane))
    empty = [(" " * inner, None)]
    for r in range(n_rows):
        spans = [(style.v, SGR_BORDER)]
        for cells in per_lane:
            cell = cells[r] if r < len(cells) else empty
            spans += [(" ", None)] + cell + [(" ", None),
                                             (style.v, SGR_BORDER)]
        lines.append(render_spans(spans, style))

    spans = [(style.bl, SGR_BORDER)]
    for idx in range(N_LANES):
        spans.append((style.h * seg_w, SGR_BORDER))
        spans.append((style.bm if idx < N_LANES - 1 else style.br,
                      SGR_BORDER))
    lines.append(render_spans(spans, style))
    return lines


def meta_parts(data, style, include_done=True):
    """`phase X/Y · milestone · done: N` as spans (segments drop out when
    unknown)."""
    parts = []
    phase = data["phase"]
    if phase["active"] is not None and phase["total"]:
        parts.append([(f"phase {phase['active']}/{phase['total']}", None)])
    if data["milestone"]:
        parts.append([(data["milestone"], None)])
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
    if data["note"]:
        lines.append(render_spans(
            [("note: ", SGR_DIM), (style.asciify(data["note"]), None)],
            style))
    return lines


def render_stacked(data, width, max_rows, style):
    """Lanes stacked vertically for narrow terminals (>= 40 cols)."""
    lines = []
    for (name, sgr), items in zip(LANES, data["_lanes"]):
        lines.append(render_spans(
            [(f"{name} ({len(items)})", sgr)], style))
        for iss in items[:max_rows]:
            cell = make_cell(name, iss, width - 2, style)
            lines.append("  " + render_spans(cell, style).rstrip())
        extra = len(items) - max_rows
        if extra > 0:
            lines.append("  " + render_spans([(f"+{extra} more", SGR_DIM)],
                                             style))
        lines.append("")
    return lines + footer_lines(data, width, style)


def render_raw(data, style):
    """Bare `LANE  id  title` list for very narrow terminals (< 40 cols)."""
    lines = []
    for (name, _), items in zip(LANES, data["_lanes"]):
        for iss in items:
            lines.append(f"{name}  {clean(iss.get('id', '?'))}  "
                         f"{clean(iss.get('title', ''))}")
    return lines + footer_lines(data, 80, style)


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
    sync = data["sync"]
    if sync["configured"]:
        state = "stale" if sync["stale"] else "fresh"
        lines.append(f"SYNC\t{state}\t{sync['detail']}")
    if data["note"]:
        lines.append(f"NOTE\t{data['note']}")
    return lines


def render_brief(data, style):
    c = data["counts"]
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
    counts = render_spans(
        [("ready ", None), (str(c["ready"]), None), (style.sep, SGR_DIM),
         ("doing ", None), (str(c["doing"]), SGR_YELLOW),
         (style.sep, SGR_DIM),
         ("blocked ", None), (str(c["blocked"]), SGR_RED),
         (style.sep, SGR_DIM),
         ("done ", None), (str(c["closed"]), SGR_GREEN)], style)
    nxt = render_spans([(style.g_next, SGR_GREEN), (" next: ", SGR_BOLD),
                        (style.asciify(data["next"]["text"]), None)], style)
    return [head, counts, nxt]


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
        ready, doing, blocked, n_closed = fetch_lanes(root)
    else:
        # bd resolves its database by walking UP from the root, so querying
        # it here could silently render an ANCESTOR repo's board. Mirror
        # cairn-gate's applicability decision instead: skip bd and degrade
        # to a GSD-only board, saying so.
        ready, doing, blocked, n_closed = [], [], [], 0
        note = f"no .beads/ at {root} — GSD-only board (bd lanes skipped)"
    all_phases, done_phases = roadmap_phases(planning_dir)
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
                "phases — run /cairn:doctor --close-completed")
    fm = state_frontmatter(planning_dir)
    milestone = fm["milestone"] or roadmap_milestone(planning_dir)
    milestone = clean(milestone) if milestone else None
    active_phase = normalize_phase(fm["active_phase"])
    nxt = synthesize_next(ready, doing, milestone, active_phase,
                          fm["next_action"], done_phases)
    sync = sync_status(root)

    data = {
        "ready": [trim_issue(i) for i in ready],
        "doing": [trim_issue(i) for i in doing],
        "blocked": [trim_issue(i) for i in blocked],
        "counts": {"ready": len(ready), "doing": len(doing),
                   "blocked": len(blocked), "closed": n_closed},
        "milestone": milestone,
        "phase": {"active": active_phase,
                  "total": len(all_phases) or None,
                  "completed": len(done_phases)},
        "next": nxt,
        "sync": {k: sync[k] for k in ("configured", "stale", "detail",
                                      "last_pull")},
        "stale_complete": stale_ids,
        "note": note,
        "_lanes": [ready, doing, blocked],
    }

    if opts["json"]:
        out = {k: v for k, v in data.items() if not k.startswith("_")}
        print(json.dumps(out))
        sys.exit(EXIT_OK)

    style = Style(opts)
    if opts["brief"]:
        lines = render_brief(data, style)
    elif opts["plain"] or (opts["width"] is None and
                           opts["color"] != "always" and
                           not sys.stdout.isatty()):
        # Non-TTY without flags gets the machine format automatically (the
        # gh model): zero escape bytes, nothing truncated. --color=always
        # opts into the board renderer like --width does — the flag must
        # never be silently ignored.
        lines = render_plain(data)
    else:
        cols = opts["width"] if opts["width"] is not None else terminal_cols()
        if cols < RAW_BELOW:
            lines = render_raw(data, style)
        elif cols < STACK_BELOW:
            lines = render_stacked(data, cols, opts["max_rows"], style)
        else:
            inner = max(MIN_INNER,
                        min(MAX_INNER, (cols - (N_LANES + 1)) // N_LANES - 2))
            counts = [len(ready), len(doing), len(blocked)]
            lines = render_board(data["_lanes"], counts, inner,
                                 opts["max_rows"], style)
            lines += footer_lines(data, cols, style)
    out = "\n".join(lines)
    try:
        print(out)
    except UnicodeEncodeError:
        # Non-Unicode stdout (C locale) with Unicode issue titles: degrade
        # the offending characters instead of crashing.
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        sys.stdout.buffer.write(out.encode(enc, errors="replace") + b"\n")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
