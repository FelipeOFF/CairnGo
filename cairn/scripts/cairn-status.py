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
                phase, next, sync, stale_complete, note} (+ html: {file,
                changed} when --html also ran)
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
    --html P    write/refresh the HTML board at P and print one confirmation
                line. Composes with --planning-dir and --json (which reports
                the write instead of the line); rejected with --plain /
                --brief, which are stdout render modes (exit 2). The page has
                no row cap, so --max-rows / --width / --ascii / --color do
                not apply to it.

Exit codes:
    0 ok    2 usage (bad flag, or an unusable --html target/template)
    5 bd unavailable (not on PATH, or a bd query failed)
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

USAGE = ("usage: cairn-status.py [--json] [--plain] [--brief] [--width N] "
         "[--max-rows N] [--ascii] [--color=always|never] "
         "[--planning-dir <dir>] [--html <path>]")

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
            "requirements": [],
        })

    for line in read_lines(planning_dir / "ROADMAP.md"):
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


def phase_model(planning_dir, issues=None):
    """Every phase, described once, for all three surfaces to render from.

    The board, `--json` and the HTML page previously each re-derived what they
    needed from `(all, done)` int lists; anything richer had to be invented per
    surface, so the three could disagree. This is the single read: roadmap text
    merged with what is actually on disk, plus the dependency edges that make
    parallelism computable.
    """
    rows = roadmap_phase_rows(planning_dir)
    dirs = phase_dirs(planning_dir)
    for n in dirs:
        rows.setdefault(n, {
            "number": n, "title": None, "milestone": None, "complete": False,
            "completed_on": None, "plans_done": None, "plans_total": None,
            "requirements": [],
        })
    dir_to_number = {d.name: n for n, d in dirs.items()}
    bd_edges = issue_phase_deps(issues or [])

    out = []
    for n in sorted(rows):
        row = dict(rows[n])
        pdir = dirs.get(n)
        row["dir"] = str(pdir.relative_to(planning_dir.parent)) if pdir else None
        row["disk_state"] = phase_disk_state(pdir)
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
    """
    if p["complete"]:
        return None
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
    """
    out = []
    for p in pending_phases(model):
        cmd = p["next_command"]
        if not cmd:
            continue
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
                    "blocked": bool(p["blocked_by"])})
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
    """`phase X/Y title · milestone · done: N` as spans (segments drop out
    when unknown).

    The title comes from the shared phase model. `phase 10/12` alone says
    where you are on a count and nothing about what you are doing.
    """
    parts = []
    phase = data["phase"]
    if phase["active"] is not None and phase["total"]:
        head = [(f"phase {phase['active']}/{phase['total']}", None)]
        if phase.get("title"):
            head.append((f" {style.asciify(phase['title'])}", SGR_DIM))
        parts.append(head)
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


def phase_panel_lines(data, width, style):
    """The pending phases and the commands to run next.

    The lanes above answer "what tracked work exists". These two blocks answer
    "which phase should I run, and why that one" — the question a row of phase
    numbers cannot answer at all. Both render from the shared model, so they
    cannot disagree with the footer or with the HTML page.
    """
    phases = data.get("phases") or []
    pending = pending_phases(phases)
    cmds = data.get("next_commands") or []
    if not pending and not cmds:
        return []

    lines = [""]
    if pending:
        lines.append(render_spans(
            [("PENDING PHASES", SGR_BOLD),
             (f"  {len(pending)}", SGR_DIM)], style))
        # Titles share one column so the states line up and can be read down.
        num_w = max(len(str(p["number"])) for p in pending)
        budget = max(24, width - num_w - 34)
        for p in pending:
            state = phase_state_text(p)
            prog = phase_progress_text(p)
            if prog:
                state = f"{state} {style.sep} {prog}"
            if p["blocked_by"]:
                state = (f"{state} {style.sep} waits on "
                         f"{join_numbers(p['blocked_by'])}")
            title = style.asciify(p["title"] or "(untitled)")
            lines.append(render_spans([
                ("  ", None),
                (str(p["number"]).rjust(num_w), None),
                ("  ", None),
                (truncate(title, budget, style.ell).ljust(budget), None),
                ("  ", None),
                (style.asciify(state), SGR_DIM),
            ], style))

    if cmds:
        lines.append("")
        lines.append(render_spans([("NEXT COMMANDS", SGR_BOLD)], style))
        cmd_w = max(len(c["command"]) for c in cmds)
        for c in cmds:
            lines.append(render_spans([
                ("  ", None),
                (c["command"].ljust(cmd_w), SGR_GREEN if not c["blocked"]
                 else SGR_DIM),
                ("  ", None),
                (style.asciify(truncate(c["reason"],
                                        max(20, width - cmd_w - 4),
                                        style.ell)), SGR_DIM),
            ], style))

    par = data.get("parallelism") or {}
    if par.get("note"):
        lines.append("")
        # Wrapped rather than truncated: this one is a sentence, and a
        # sentence cut at the terminal edge loses the half that qualifies it.
        for i, chunk in enumerate(textwrap.wrap(style.asciify(par["note"]),
                                                max(30, width - 2))):
            lines.append(render_spans(
                [("  " if i else "  ", None), (chunk, SGR_DIM)], style))
    return lines


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
    if data["milestone"]:
        # A milestone is a name, so it is set in the page's own voice. Mono
        # is kept for the things that are actually data: the phase numbers.
        bits.append(f'<span class="m">{esc(data["milestone"])}</span>')
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
    on: what is still pending and what it is, and which commands come next in
    which order, with the reason for that order.

    Same model as the terminal panel and the same wording, so a page open on a
    second screen cannot quietly disagree with the shell that produced it.
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
            meta = [esc(phase_state_text(p))]
            prog = phase_progress_text(p)
            if prog:
                meta.append(f'<span class="n">{esc(prog)}</span>')
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
                f'<li class="phase{blocked}">'
                f'<span class="phase-n">{p["number"]}</span>'
                '<span class="phase-body">'
                f'<span class="phase-title">{esc(p["title"] or "(untitled)")}'
                f'</span>{reqs}'
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
        ready, doing, blocked, closed = fetch_lanes(root)
        n_closed = len(closed)
    else:
        # bd resolves its database by walking UP from the root, so querying
        # it here could silently render an ANCESTOR repo's board. Mirror
        # cairn-gate's applicability decision instead: skip bd and degrade
        # to a GSD-only board, saying so.
        ready, doing, blocked, closed, n_closed = [], [], [], [], 0
        note = f"no .beads/ at {root}: GSD-only board (bd lanes skipped)"
    # ONE phase model, built once. Every surface below renders from this list
    # rather than re-deriving what it needs, so the terminal board, --json and
    # the HTML page cannot describe the same phase differently.
    phases = phase_model(planning_dir, ready + doing + blocked + closed)
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
        "next": nxt,
        "sync": {k: sync[k] for k in ("configured", "stale", "detail",
                                      "last_pull")},
        "stale_complete": stale_ids,
        "note": note,
        # Underscore keys are renderer-private: the --json summary filters
        # them out, so the machine contract stays exactly as documented.
        "_lanes": [ready, doing, blocked],
        "_closed": closed,
        "_phases": {"all": all_phases, "done": done_phases},
    }

    html_info = None
    if opts["html"] is not None:
        html_info = write_html_board(Path(opts["html"]), data)

    if opts["json"]:
        out = {k: v for k, v in data.items() if not k.startswith("_")}
        if html_info is not None:
            out["html"] = html_info
        print(json.dumps(out))
        sys.exit(EXIT_OK)

    if html_info is not None:
        c = data["counts"]
        # "unchanged" is reachable: two runs inside the same minute with no
        # state change regenerate an identical region (the stamp is minute
        # resolution), and an identical region is never rewritten.
        state = "wrote" if html_info["changed"] else "unchanged"
        print(f"[cairn-status] {state} {html_info['file']} — "
              f"{c['ready']} ready, {c['doing']} doing, "
              f"{c['blocked']} blocked")
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
            lines += phase_panel_lines(data, cols, style)
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
