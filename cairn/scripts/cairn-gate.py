#!/usr/bin/env python3
"""cairn-gate — the ship gate: fail when a COMPLETED GSD phase still has
open bd issues.

Usage:
    cairn-gate.py [--planning-dir <dir>] [--json]

Behavior:
    1. Locate the planning dir (default: $CLAUDE_PROJECT_DIR or cwd +
       /.planning). When --planning-dir is given, the repo root is taken to
       be its parent so the gate can be pointed at any checkout.
    2. Applicability: no .planning/ or no .beads/ at the root -> the gate
       does not apply; print a note and exit 0.
    3. Enumerate COMPLETED phases from ROADMAP.md, parsed leniently:
       checkbox lines ('- [x] **Phase N: ...**') plus milestone-grouped
       progress-table rows ('| N. Name | vX.Y | ... | Complete | ...').
    4. Resolve the ACTIVE milestone leniently: STATE.md frontmatter
       'milestone:' key first, else the ROADMAP.md milestone marked in
       progress (a line with the 🚧 emoji or '(in progress)' carrying a
       vN[.N...] token), else None (single-milestone or legacy repo).
    5. For each completed phase N, query the tracker. Semantically this is
       'every NON-CLOSED bd issue labeled m-<milestone>,phase-<N>' with a
       fallback to the bare 'phase-<N>' label when issues carry no m-*
       labels (legacy repos, per the cairn skill). It is implemented as
       ONE bare query per phase — bd list -l phase-<N> --all --limit 0
       --json — filtered client-side to status != closed, then:
         - milestone known:   offending = non-closed issues labeled
                              m-<milestone> PLUS non-closed issues with no
                              m-* label at all (legacy strays);
         - milestone unknown: offending = every non-closed phase-<N> issue.
       Any status other than 'closed' blocks (open, in_progress, blocked,
       deferred, …) — a completed phase with an in-flight issue is as
       incoherent as one with an open issue. Same semantics as the
       capability bundle's cairn-loop-gate ship-gate.

Exit codes:
    0  all clear — or gate NOT APPLICABLE (.planning/ or .beads/ absent, or
       no completed phases); a note says which.
    2  usage error.
    5  bd unavailable (not on PATH, or bd list failed). A WARNING is
       printed. IMPORTANT: the pre-push shim MUST NOT block the push on
       exit 5 — an availability failure is not a gate failure. Only exit 6
       may block a push.
    6  GATE FAILED — offending issue ids are listed one per line (the id is
       the first whitespace-delimited token of each line).
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BD = 5
EXIT_GATE_FAILED = 6

USAGE = "usage: cairn-gate.py [--planning-dir <dir>] [--json]"

VERSION_TOKEN = re.compile(r"\bv\d+(?:\.\d+)*\b")
CHECKED_PHASE = re.compile(r"^\s*-\s*\[[xX]\]\s.*?\bPhase\s+0*(\d+)\b")
TABLE_PHASE = re.compile(r"^\s*\|\s*0*(\d+)[.)\s][^|]*\|.*\|\s*Complete\s*\|",
                         re.IGNORECASE)


def die(msg, code):
    print(f"[cairn-gate] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    opts = {"planning_dir": None, "json": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--planning-dir":
            if i + 1 >= len(argv):
                die(f"--planning-dir needs a value\n{USAGE}", EXIT_USAGE)
            opts["planning_dir"] = argv[i + 1]
            i += 2
        elif arg == "--json":
            opts["json"] = True
            i += 1
        else:
            die(f"unknown argument '{arg}'\n{USAGE}", EXIT_USAGE)
    return opts


def read_lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def completed_phases(planning_dir):
    """Phase numbers ROADMAP.md marks complete (checkbox or progress table)."""
    done = set()
    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = CHECKED_PHASE.match(line)
        if m:
            done.add(int(m.group(1)))
            continue
        m = TABLE_PHASE.match(line)
        if m:
            done.add(int(m.group(1)))
    return sorted(done)


def state_milestone(planning_dir):
    """'milestone:' key from STATE.md YAML frontmatter, or None."""
    lines = read_lines(planning_dir / "STATE.md")
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^milestone\s*:\s*(.+?)\s*$", line)
        if m:
            val = m.group(1).split("#", 1)[0].strip().strip("'\"").strip()
            if val:
                return val
    return None


def roadmap_milestone(planning_dir):
    """Milestone marked in progress in ROADMAP.md (🚧 / '(in progress)'
    line carrying a vN[.N...] token), or None."""
    for line in read_lines(planning_dir / "ROADMAP.md"):
        if "🚧" in line or re.search(r"\(in progress\)", line, re.IGNORECASE):
            m = VERSION_TOKEN.search(line)
            if m:
                return m.group(0)
    return None


def bd_open_issues(root, phase):
    """Non-closed issues carrying the bare phase-<N> label.

    Queries with --all and filters status != closed client-side: a completed
    phase with an in_progress or blocked issue is just as incoherent as one
    with an open issue, and this matches the capability bundle's
    cairn-loop-gate ship-gate semantics (non-closed blocks)."""
    cmd = ["bd", "-C", str(root), "list", "-l", f"phase-{phase}",
           "--all", "--limit", "0", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"bd list failed: {proc.stderr.strip()} — gate cannot run "
            "(exit 5; the pre-push shim does not block on this)", EXIT_NO_BD)
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        die(f"bd list returned invalid JSON: {e} — gate cannot run "
            "(exit 5; the pre-push shim does not block on this)", EXIT_NO_BD)
    if data is None:
        return []
    issues = data if isinstance(data, list) else [data]
    return [i for i in issues if i.get("status") != "closed"]


def offending_for(issues, milestone):
    """Issues that belong to the active milestone (or are legacy strays)."""
    out = []
    for iss in issues:
        labels = iss.get("labels") or []
        m_labels = [l for l in labels if l.startswith("m-")]
        if milestone is None or not m_labels or f"m-{milestone}" in m_labels:
            out.append(iss)
    return out


def emit(opts, summary, human_lines):
    if opts["json"]:
        print(json.dumps(summary))
    else:
        for line in human_lines:
            print(line)


def main():
    opts = parse_args(sys.argv[1:])
    if opts["planning_dir"]:
        planning_dir = Path(opts["planning_dir"]).resolve()
        root = planning_dir.parent
    else:
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
        planning_dir = root / ".planning"

    summary = {"applicable": False, "ok": True, "milestone": None,
               "completed_phases": [], "offending": [], "note": None}

    if not planning_dir.is_dir():
        summary["note"] = f"no .planning/ at {planning_dir} — gate not applicable"
        emit(opts, summary, [f"[cairn-gate] note: {summary['note']}"])
        sys.exit(EXIT_OK)
    if not (root / ".beads").is_dir():
        summary["note"] = "no .beads/ — gate not applicable (nothing tracked)"
        emit(opts, summary, [f"[cairn-gate] note: {summary['note']}"])
        sys.exit(EXIT_OK)

    summary["applicable"] = True
    phases = completed_phases(planning_dir)
    summary["completed_phases"] = phases
    if not phases:
        summary["note"] = "no completed phases in ROADMAP.md — nothing to gate"
        emit(opts, summary, [f"[cairn-gate] ok: {summary['note']}"])
        sys.exit(EXIT_OK)

    if shutil.which("bd") is None:
        print("[cairn-gate] warning: 'bd' not on PATH — gate cannot run "
              "(exit 5). Availability failure is NOT a gate failure; the "
              "pre-push shim does not block on this.", file=sys.stderr)
        sys.exit(EXIT_NO_BD)

    milestone = state_milestone(planning_dir) or roadmap_milestone(planning_dir)
    summary["milestone"] = milestone

    offending = []
    for n in phases:
        for iss in offending_for(bd_open_issues(root, n), milestone):
            offending.append({"id": iss.get("id", "?"), "phase": n,
                              "status": iss.get("status", "open"),
                              "title": iss.get("title", "")})

    if offending:
        summary["ok"] = False
        summary["offending"] = offending
        scope = f"milestone {milestone}" if milestone else "all milestones"
        lines = [f"[cairn-gate] GATE FAILED — {len(offending)} non-closed "
                 f"issue(s) in completed phase(s) ({scope}):"]
        lines += [f"{o['id']}  phase-{o['phase']}  {o['title']}"
                  for o in offending]
        lines.append("[cairn-gate] close them (bd close <id> --reason=...) "
                     "before shipping.")
        emit(opts, summary, lines)
        sys.exit(EXIT_GATE_FAILED)

    scope = f"milestone {milestone}" if milestone else "all issues"
    emit(opts, summary,
         [f"[cairn-gate] ok — no open issues in completed phase(s) "
          f"{', '.join(str(p) for p in phases)} ({scope})"])
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
