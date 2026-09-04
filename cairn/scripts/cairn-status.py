#!/usr/bin/env python3
"""cairn-status — READY / DOING / BLOCKED from bd.

v5 board: lanes from beads. READY is `bd ready` ∩ `ready-for-agent` when
that label is in use on any open issue; otherwise `bd ready`. Optional
`m-vX.Y` labels group the list. No GSD, no .planning/, no journal.

Usage:
    cairn-status.py [--json] [--plain] [--brief] [--width N] [--max-rows N]
                    [--ascii] [--color=always|never]
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BD = 5
DEFAULT_MAX_ROWS = 15
USAGE = ("usage: cairn-status.py [--json] [--plain] [--brief] [--width N] "
         "[--max-rows N] [--ascii] [--color=always|never]")
SGR_BOLD, SGR_DIM, SGR_YELLOW, SGR_RED = "1", "2", "33", "31"
M_LABEL = re.compile(r"^m-(v?\d+(?:\.\d+)*)$")


def die(msg, code):
    print(f"[cairn-status] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    opts = {"json": False, "plain": False, "brief": False, "width": None,
            "max_rows": DEFAULT_MAX_ROWS, "ascii": False, "color": "auto"}
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
        elif arg in ("--width", "--max-rows"):
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
        else:
            die(f"unknown argument '{arg}'\n{USAGE}", EXIT_USAGE)
    if opts["json"] + opts["plain"] + opts["brief"] > 1:
        die(f"choose one of --json / --plain / --brief\n{USAGE}", EXIT_USAGE)
    return opts


def parse_bd_json(stdout):
    out = (stdout or "").strip()
    starts = [i for i in (out.find("["), out.find("{")) if i >= 0]
    if not starts:
        return []
    data = json.loads(out[min(starts):])
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def run_bd(args, root):
    cmd = ["bd", "-C", str(root)] + args + ["--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"bd {args[0]} failed: {proc.stderr.strip()}", EXIT_NO_BD)
    try:
        return parse_bd_json(proc.stdout)
    except json.JSONDecodeError as e:
        die(f"bd {args[0]} returned invalid JSON: {e}", EXIT_NO_BD)


def issue_priority(iss):
    p = iss.get("priority", 2)
    if isinstance(p, str):
        p = p.lstrip("Pp") or "2"
    try:
        return int(p)
    except (TypeError, ValueError):
        return 2


def as_str_list(val):
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


def labels_of(iss):
    return as_str_list(iss.get("labels"))


def milestoned(iss):
    """m-vX.Y labels → [{key, label}]."""
    out = []
    for lab in labels_of(iss):
        m = M_LABEL.match(lab.strip())
        if m:
            out.append({"key": m.group(1), "label": lab.strip()})
    return out


def trim_issue(iss):
    return {
        "id": str(iss.get("id") or "?"),
        "title": iss.get("title", ""),
        "priority": issue_priority(iss),
        "assignee": iss.get("assignee") or None,
        "external_ref": iss.get("external_ref") or None,
        "labels": labels_of(iss),
        "blocked_by": as_str_list(iss.get("blocked_by")),
    }


def fetch_lanes(root):
    ready = run_bd(["ready", "-n", "0"], root)
    doing = run_bd(["list", "--status", "in_progress", "--limit", "0"], root)
    blocked = run_bd(["blocked"], root)
    closed = run_bd(["list", "--status", "closed", "--limit", "0"], root)
    key = lambda i: (issue_priority(i), str(i.get("id") or ""))  # noqa: E731
    return (sorted(ready, key=key), sorted(doing, key=key),
            sorted(blocked, key=key), closed)


def filter_ready(ready, doing, blocked):
    open_issues = ready + doing + blocked
    if any("ready-for-agent" in labels_of(i) for i in open_issues):
        return [i for i in ready if "ready-for-agent" in labels_of(i)]
    return ready


def synthesize_next(ready, doing):
    out = {"kind": "none", "id": None, "text": ""}
    if doing:
        iss = doing[0]
        out.update(kind="continue", id=iss.get("id"),
                   text=iss.get("title") or "")
        return out
    if ready:
        iss = ready[0]
        out.update(kind="ready", id=iss.get("id"),
                   text=iss.get("title") or "")
    return out


def open_milestones(ready, doing, blocked):
    seen = {}
    for iss in ready + doing + blocked:
        for ms in milestoned(iss):
            seen.setdefault(ms["key"], ms)
    return [seen[k] for k in sorted(seen)]


def color_on(opts):
    if opts["color"] == "always":
        return True
    if opts["color"] == "never":
        return False
    return sys.stdout.isatty()


def sgr(codes, on):
    if not on or not codes:
        return "", ""
    return f"\033[{codes}m", "\033[0m"


def glyph(opts, fancy, plain):
    return plain if opts["ascii"] else fancy


def render_brief(data):
    c = data["counts"]
    lines = [f"ready {c['ready']} · doing {c['doing']} · "
             f"blocked {c['blocked']} · done {c['closed']}"]
    ms = data["open_milestones"]
    lines.append("")
    header = ", ".join(m["label"] for m in ms) if ms else "No milestone"
    lines.append(header)
    shown = 0
    cap = data["_max_rows"]
    for iss in data["_ready"]:
        if shown >= cap:
            break
        lines.append(f"      {glyph(data['_opts'], '◔', 'o')} "
                     f"{iss.get('id')}  {iss.get('title', '')}")
        shown += 1
    nxt = data["next"]
    if nxt["kind"] in ("continue", "ready") and nxt["id"]:
        verb = "continue" if nxt["kind"] == "continue" else "start"
        lines.append(f"▶ next: {verb} {nxt['id']} — {nxt['text']}")
    elif not (data["_ready"] or data["_doing"] or data["_blocked"]):
        lines.append("▶ next: nothing ready")
    return lines


def render_plain(data):
    lines = []
    c = data["counts"]
    lines.append(f"COUNTS\t{c['ready']}\t{c['doing']}\t{c['blocked']}\t{c['closed']}")
    ms = data["open_milestones"]
    lines.append("MILESTONE\t" + (",".join(m["key"] for m in ms) if ms else ""))
    for lane, items in (("READY", data["_ready"]),
                        ("DOING", data["_doing"]),
                        ("BLOCKED", data["_blocked"])):
        for iss in items:
            lines.append(f"{lane}\t{iss.get('id')}\t{iss.get('title', '')}")
    nxt = data["next"]
    if nxt["id"]:
        lines.append(f"NEXT\t{nxt['kind']}\t{nxt['id']}\t{nxt['text']}")
    else:
        lines.append("NEXT\tnone\t\t")
    return lines


def render_board(data):
    opts = data["_opts"]
    on = color_on(opts)
    width = opts["width"] or shutil.get_terminal_size((80, 24)).columns
    c = data["counts"]
    bold, un = sgr(SGR_BOLD, on)
    dim, _ = sgr(SGR_DIM, on)
    yel, _ = sgr(SGR_YELLOW, on)
    red, _ = sgr(SGR_RED, on)
    lines = [f"{bold}ready {c['ready']} · doing {c['doing']} · "
             f"blocked {c['blocked']} · done {c['closed']}{un}"]
    ms = data["open_milestones"]
    lines.append("")
    lines.append(ms[0]["label"] if len(ms) == 1 else (
        ", ".join(m["label"] for m in ms) if ms else f"{dim}No milestone{un}"))
    cap = data["_max_rows"]
    shown = 0

    def add_lane(name, items, color):
        nonlocal shown
        if not items:
            return
        on_c, off_c = sgr(color, on)
        lines.append(f"{on_c}{name}{off_c}")
        for iss in items:
            if shown >= cap:
                left = len(items) - items.index(iss)
                lines.append(f"{dim}      +{left} more{un}")
                break
            mark = glyph(opts, "●", "*") if name == "DOING" else (
                glyph(opts, "✗", "x") if name == "BLOCKED" else
                glyph(opts, "◔", "o"))
            title = iss.get("title") or ""
            row = f"      {mark} {iss.get('id')}  {title}"
            if len(row) > width:
                row = row[: max(0, width - 1)] + "…"
            lines.append(row)
            shown += 1

    add_lane("READY", data["_ready"], SGR_DIM)
    add_lane("DOING", data["_doing"], SGR_YELLOW)
    add_lane("BLOCKED", data["_blocked"], SGR_RED)
    nxt = data["next"]
    if nxt["kind"] in ("continue", "ready") and nxt["id"]:
        verb = "continue" if nxt["kind"] == "continue" else "start"
        lines.append(f"{bold}▶ next:{un} {verb} {nxt['id']} — {nxt['text']}")
    return lines


def main():
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    opts = parse_args(sys.argv[1:])
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR",
                               os.environ.get("GROK_PROJECT_DIR", os.getcwd())))
    if shutil.which("bd") is None:
        die("'bd' not found on PATH — the board needs beads "
            "(consumers fall back on exit 5, never block)", EXIT_NO_BD)

    note = None
    if not (root / ".beads").is_dir():
        ready, doing, blocked, closed = [], [], [], []
        n_closed = 0
        note = f"no .beads/ at {root}: empty board"
        bd_ok = True
    else:
        probe = subprocess.run(
            ["bd", "-C", str(root), "list", "--limit", "1", "--json"],
            capture_output=True, text=True)
        if probe.returncode != 0:
            ready, doing, blocked, closed = [], [], [], []
            n_closed = 0
            note = (f"bd query failed at {root}: "
                    f"{probe.stderr.strip() or 'unknown error'}")
            bd_ok = False
        else:
            ready, doing, blocked, closed = fetch_lanes(root)
            ready = filter_ready(ready, doing, blocked)
            n_closed = len(closed)
            bd_ok = True

    nxt = synthesize_next(ready, doing)
    ms = open_milestones(ready, doing, blocked)
    data = {
        "ready": [trim_issue(i) for i in ready],
        "doing": [trim_issue(i) for i in doing],
        "blocked": [trim_issue(i) for i in blocked],
        "counts": {"ready": len(ready), "doing": len(doing),
                   "blocked": len(blocked), "closed": n_closed},
        "open_milestones": ms,
        "next": nxt,
        "note": note,
        "_ready": ready,
        "_doing": doing,
        "_blocked": blocked,
        "_opts": opts,
        "_max_rows": opts["max_rows"],
    }
    exit_code = EXIT_OK if bd_ok else EXIT_NO_BD
    if opts["json"]:
        out = {k: v for k, v in data.items() if not k.startswith("_")}
        print(json.dumps(out))
        sys.exit(exit_code)
    if opts["plain"]:
        lines = render_plain(data)
    elif opts["brief"]:
        lines = render_brief(data)
    else:
        lines = render_board(data)
    sys.stdout.write("\n".join(lines) + "\n")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
