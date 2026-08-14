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
    6. SECOND, independent block reason (CORR-05 / D-10): a completed phase
       whose directory never reached "executed" on disk — no file ending
       -SUMMARY.md or -VERIFICATION.md (a bare -PLAN.md, or no directory at
       all, counts as "not executed") — blocks even when bd reports zero
       open issues for it. This mirrors Plan 13-01's R2 rule
       (disk_state in ("executed", "verified")) and is duplicated,
       independently, in cairn/capability/scripts/cairn-loop-gate.py so both
       ship-gate entry points agree in lockstep.

Exit codes:
    0  all clear — or gate NOT APPLICABLE (.planning/ or .beads/ absent, or
       no completed phases); a note says which.
    2  usage error.
    5  bd unavailable (not on PATH, or bd list failed). A WARNING is
       printed. IMPORTANT: the pre-push shim MUST NOT block the push on
       exit 5 — an availability failure is not a gate failure. Only exit 6
       may block a push.
    6  GATE FAILED — offending entries are listed one per line. A bd-issue
       entry starts with the issue id; a no-artifacts entry (id is null in
       --json) starts with "phase-<N>" instead since there is no issue id.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cairn_source  # noqa: E402

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BD = 5
EXIT_GATE_FAILED = 6

USAGE = "usage: cairn-gate.py [--planning-dir <dir>] [--json]"

VERSION_TOKEN = re.compile(r"\bv\d+(?:\.\d+)*\b")
CHECKED_PHASE = re.compile(r"^\s*-\s*\[[xX]\]\s.*?\bPhase\s+0*(\d+)\b")
TABLE_PHASE = re.compile(r"^\s*\|\s*0*(\d+)[.)\s][^|]*\|.*\|\s*Complete\s*\|",
                         re.IGNORECASE)
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")


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


def disk_completed_phases(planning_dir):
    """Phase numbers ROADMAP.md marks complete (checkbox or progress table).
    Empty when there is no roadmap on disk — this repo has no GSD to import."""
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


def bd_completed_phases(root):
    """Phases the TRACKER marks complete: those whose phase CARRIER is closed.

    THE CARRIER IS WHAT INHERITED THE CHECKBOX. A gate that asked the tracker
    "which phases are done?" the way cairn_source.completed_phases() answers
    it — every issue closed — would be asking a question whose answer makes
    the next one vacuous: a phase where everything is closed can never hold
    an open issue. The carrier is a SINGLE bead, closed by a human act, and
    "the phase was declared done while its work is still open" is exactly the
    divergence the checkbox used to expose.
    """
    done = []
    for n in sorted(cairn_source.phases(root, cairn_source.milestone(root))):
        carrier = cairn_source.phase_carrier(root, n)
        if carrier is not None and carrier.get("status") == "closed":
            done.append(n)
    return done


def completed_phases(planning_dir, root):
    """(phases, source) — from the ROADMAP on disk when there is one, from
    the tracker when there is not.

    Same two-source rule cairn-doctor holds: a `.planning/ROADMAP.md` that is
    still waiting to be imported is the INPUT, and comparing what it claims
    against what bd holds is the coverage the migration has to prove. Once
    imported the file is gone, and the carrier answers instead.
    """
    disk = disk_completed_phases(planning_dir)
    if disk or (planning_dir / "ROADMAP.md").is_file():
        return disk, "roadmap"
    return bd_completed_phases(root), "bd"


def phase_dir_for(planning_dir, n):
    """Directory under <planning>/phases/ whose numeric prefix matches n, or
    None. Mirrors cairn-status.py's phase_dirs() matching (numeric prefix,
    optional project-code prefix, optional zero padding)."""
    root = planning_dir / "phases"
    if not root.is_dir():
        return None
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        m = PHASE_DIR_PREFIX.match(d.name)
        if m and int(m.group(1)) == n:
            return d
    return None


def disk_reached_executed(pdir):
    """True when the phase directory holds at least one -SUMMARY.md or
    -VERIFICATION.md file. Deliberately the SAME two-suffix threshold Plan
    13-01's R2 rule uses (disk_state in ("executed", "verified")), not "any
    artifact" — a phase with only a -PLAN.md on disk is "planned but not yet
    built" and must NOT satisfy this."""
    if pdir is None or not pdir.is_dir():
        return False
    names = [p.name for p in pdir.iterdir() if p.is_file()]
    return any(n.endswith("-SUMMARY.md") or n.endswith("-VERIFICATION.md")
               for n in names)


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


def resolve_milestone(planning_dir, root):
    """STATE.md first, then the roadmap in progress, then the tracker. The
    last one is what makes the gate work in a repo that has no `.planning/`
    at all."""
    return (state_milestone(planning_dir)
            or roadmap_milestone(planning_dir)
            or cairn_source.milestone(root))


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
               "completed_phases": [], "offending": [], "note": None,
               "source": None}

    # `.beads/` IS THE GATE, and `.planning/` no longer is. Requiring the
    # planning directory meant that the moment a repo finished migrating —
    # the moment it became the tracker-owned repo cairn is for — the ship
    # gate silently stopped running and reported "not applicable" forever.
    if not (root / ".beads").is_dir():
        summary["note"] = "no .beads/ — gate not applicable (nothing tracked)"
        emit(opts, summary, [f"[cairn-gate] note: {summary['note']}"])
        sys.exit(EXIT_OK)

    if shutil.which("bd") is None:
        print("[cairn-gate] warning: 'bd' not on PATH — gate cannot run "
              "(exit 5). Availability failure is NOT a gate failure; the "
              "pre-push shim does not block on this.", file=sys.stderr)
        sys.exit(EXIT_NO_BD)

    summary["applicable"] = True
    phases, source = completed_phases(planning_dir, root)
    summary["completed_phases"] = phases
    summary["source"] = source
    if not phases:
        where = ("ROADMAP.md" if source == "roadmap"
                 else "the tracker (no phase carrier is closed)")
        summary["note"] = f"no completed phases in {where} — nothing to gate"
        emit(opts, summary, [f"[cairn-gate] ok: {summary['note']}"])
        sys.exit(EXIT_OK)

    milestone = resolve_milestone(planning_dir, root)
    summary["milestone"] = milestone

    offending = []
    for n in phases:
        for iss in offending_for(bd_open_issues(root, n), milestone):
            offending.append({"id": iss.get("id", "?"), "phase": n,
                              "status": iss.get("status", "open"),
                              "title": iss.get("title", "")})

    # SECOND, independent block reason (CORR-05 / D-10): a completed phase
    # whose disk never reached "executed" — no SUMMARY or VERIFICATION file
    # — blocks even when bd reports zero open issues for it. `id` is None
    # (there is no bd issue behind this reason); the human-readable line
    # branches on that below.
    # It only applies while the roadmap IS the source: it asks whether disk
    # backs up what the document claims. With no document there is no claim
    # to check, and running it anyway would fail every phase of every
    # migrated repo for the absence of files cairn no longer writes.
    if source == "roadmap":
        for n in phases:
            if not disk_reached_executed(phase_dir_for(planning_dir, n)):
                offending.append({
                    "id": None, "phase": n, "status": "no-artifacts",
                    "title": f"phase {n} is checked off in ROADMAP.md but disk "
                             "never reached executed (no SUMMARY or "
                             "VERIFICATION)",
                })

    if offending:
        summary["ok"] = False
        summary["offending"] = offending
        scope = f"milestone {milestone}" if milestone else "all milestones"
        lines = [f"[cairn-gate] GATE FAILED — {len(offending)} blocking "
                 f"item(s) in completed phase(s) ({scope}):"]
        # A bd-issue entry has an id and leads with it; a no-artifacts entry
        # has no bd issue behind it, so it leads with the phase label instead.
        lines += [
            (f"{o['id']}  phase-{o['phase']}  {o['title']}"
             if o.get("id") is not None
             else f"phase-{o['phase']}  {o['title']}")
            for o in offending
        ]
        if any(o.get("id") is not None for o in offending):
            lines.append("[cairn-gate] close them (bd close <id> "
                         "--reason=...) before shipping.")
        if any(o.get("id") is None for o in offending):
            lines.append("[cairn-gate] build the phase (SUMMARY/"
                         "VERIFICATION) or uncheck it in ROADMAP.md before "
                         "shipping.")
        emit(opts, summary, lines)
        sys.exit(EXIT_GATE_FAILED)

    scope = f"milestone {milestone}" if milestone else "all issues"
    emit(opts, summary,
         [f"[cairn-gate] ok — no open issues in completed phase(s) "
          f"{', '.join(str(p) for p in phases)} ({scope})"])
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
