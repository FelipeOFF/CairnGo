#!/usr/bin/env python3
"""cairn-loop-gate — deterministic loop checks for the cairn GSD capability.

Ships inside the capability bundle (installed at .gsd/capabilities/cairn/)
so the GSD loop can run it from the project root without the Claude plugin
on PATH.

Usage:
    cairn-loop-gate.py ship-gate    [--phase N] [--milestone M] [--project-dir DIR]
    cairn-loop-gate.py verify-cross <phase>    [--milestone M] [--project-dir DIR]

ship-gate
    Blocking ship:pre check. Every completed phase (checked '[x]' entries in
    ROADMAP.md's phase checklist, plus --phase when given) must have ZERO
    non-closed bd issues labeled phase-<N> (AND m-<M> when --milestone is
    given). Exit 0 = pass or clean no-op; exit 1 = block, with a report on
    stdout; exit 2 = usage. A present-but-failing bd also exits 1 (fail
    closed — never ship on an ambiguous tracker, mirroring the security
    ship gate's strict-equality contract).

    SECOND, independent block reason (CORR-05 / D-10): a completed phase
    whose directory never reached "executed" on disk — no file ending
    -SUMMARY.md or -VERIFICATION.md — blocks even when bd reports zero open
    issues for it. Identical rule to cairn/scripts/cairn-gate.py's twin
    check, duplicated here (not imported) per this bundle's self-contained
    convention, so both ship-gate entry points agree in lockstep.

verify-cross
    Advisory verify:post report. Cross-checks bd state for the phase against
    the phase's *-VERIFICATION.md status and prints mismatches. Always exits
    0 (2 on usage) — the surrounding contribution surfaces the text.

No-op contract (both subcommands, silent exit 0): .planning/ missing,
.beads/ missing, cairn.enabled=false in .planning/config.json, or bd not on
PATH (a warning goes to stderr). GSD must behave untouched in repos without
beads.
"""
import json
import re
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_BLOCK = 1
EXIT_USAGE = 2

USAGE = ("usage: cairn-loop-gate.py ship-gate [--phase N] [--milestone M] "
         "[--project-dir DIR] | verify-cross <phase> [--milestone M] "
         "[--project-dir DIR]")

NON_CLOSED = ("closed",)  # anything NOT in here counts as open work


def die(msg, code):
    print(f"[cairn-loop-gate] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    if not argv or argv[0] in ("-h", "--help"):
        die(USAGE, EXIT_USAGE)
    opts = {"cmd": argv[0], "phase": None, "milestone": None,
            "project_dir": None}
    if opts["cmd"] not in ("ship-gate", "verify-cross"):
        die(f"unknown subcommand '{opts['cmd']}'\n{USAGE}", EXIT_USAGE)
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("--phase", "--milestone", "--project-dir"):
            if i + 1 >= len(argv):
                die(f"{arg} needs a value\n{USAGE}", EXIT_USAGE)
            key = arg.lstrip("-").replace("-", "_")
            opts[key] = argv[i + 1]
            i += 2
        elif arg.startswith("-"):
            die(f"unknown option '{arg}'\n{USAGE}", EXIT_USAGE)
        elif opts["cmd"] == "verify-cross" and opts["phase"] is None:
            opts["phase"] = arg
            i += 1
        else:
            die(f"unexpected argument '{arg}'\n{USAGE}", EXIT_USAGE)
    # The ${PHASE_NUMBER} placeholder interpolates to "" when the workflow
    # has no phase in scope — treat empty as absent, not as a usage error.
    if opts["phase"] is not None and opts["phase"].strip() == "":
        opts["phase"] = None
    if opts["phase"] is not None and not re.fullmatch(r"\d+", opts["phase"]):
        die(f"phase must be a number, got '{opts['phase']}'", EXIT_USAGE)
    if opts["cmd"] == "verify-cross" and opts["phase"] is None:
        die(f"verify-cross needs a <phase>\n{USAGE}", EXIT_USAGE)
    return opts


def cairn_enabled(planning_dir):
    """False only when .planning/config.json explicitly disables cairn.
    Accepts the nested form {"cairn": {"enabled": false}} and the flat
    dotted form {"cairn.enabled": false}."""
    cfg_path = planning_dir / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(cfg, dict):
        return True
    nested = cfg.get("cairn")
    if isinstance(nested, dict) and nested.get("enabled") is False:
        return False
    if cfg.get("cairn.enabled") is False:
        return False
    return True


def noop_guard(project_dir):
    """Exit 0 silently when this repo is not a cairn repo (or cairn is off).
    Returns only when the check should actually run."""
    planning = project_dir / ".planning"
    if not planning.is_dir():
        sys.exit(EXIT_OK)
    if not (project_dir / ".beads").is_dir():
        sys.exit(EXIT_OK)
    if not cairn_enabled(planning):
        sys.exit(EXIT_OK)
    if shutil.which("bd") is None:
        print("[cairn-loop-gate] warning: .beads/ exists but 'bd' is not on PATH "
              "— skipping check", file=sys.stderr)
        sys.exit(EXIT_OK)


def bd_list(labels, cwd):
    """bd list -l <labels-ANDed> --all --limit 0 --json, parsed.
    Returns (issues, error-string-or-None)."""
    cmd = ["bd", "list", "-l", ",".join(labels),
           "--all", "--limit", "0", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if proc.returncode != 0:
        return None, f"bd list failed: {proc.stderr.strip()}"
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        return None, f"bd list returned invalid JSON: {e}"
    return (data if isinstance(data, list) else [data]), None


def completed_phases(planning_dir):
    """Phase numbers checked '[x]' in ROADMAP.md's phase checklist."""
    path = planning_dir / "ROADMAP.md"
    if not path.is_file():
        return []
    pat = re.compile(r"^\s*-\s*\[x\]\s*\*\*Phase\s+(\d+)", re.IGNORECASE)
    nums = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = pat.match(line)
        if m:
            nums.append(int(m.group(1), 10))
    return sorted(set(nums))


def non_closed(issues):
    return [i for i in issues
            if str(i.get("status", "")).lower() not in NON_CLOSED]


def issue_line(issue):
    return (f"  {issue.get('id', '?')} ({issue.get('status', '?')}) "
            f"{str(issue.get('title', '')).strip()}")


def cmd_ship_gate(opts, project_dir):
    planning = project_dir / ".planning"
    phases = completed_phases(planning)
    if opts["phase"] is not None:
        n = int(opts["phase"], 10)
        if n not in phases:
            phases.append(n)
    if not phases:
        sys.exit(EXIT_OK)

    blockers = {}
    no_artifacts = set()
    for n in sorted(phases):
        labels = [f"phase-{n}"]
        if opts["milestone"]:
            labels.append(f"m-{opts['milestone']}")
        issues, err = bd_list(labels, project_dir)
        if err:
            # Fail closed: a present-but-broken tracker is ambiguous state,
            # and a blocking ship gate never passes on ambiguity.
            print(f"[cairn-loop-gate] ship gate: cannot verify phase {n} — {err}")
            sys.exit(EXIT_BLOCK)
        open_issues = non_closed(issues)
        if open_issues:
            blockers[n] = open_issues
        # SECOND, independent block reason (CORR-05 / D-10): a completed
        # phase whose disk never reached "executed" blocks even when bd
        # reports zero open issues for it — force it into the report even
        # though the bd-issue loop above only populates `blockers` for
        # phases WITH non-closed issues.
        if not disk_reached_executed(resolve_phase_dir(planning, n)):
            no_artifacts.add(n)

    if not blockers and not no_artifacts:
        sys.exit(EXIT_OK)
    pair = f",m-{opts['milestone']}" if opts["milestone"] else ""
    print("[cairn-loop-gate] ship gate BLOCKED — completed phases still have "
          "non-closed bd issues or no artifacts on disk:")
    for n in sorted(set(blockers) | no_artifacts):
        if n in blockers:
            # --all, not --status open: the gate blocks on ANY non-closed
            # status (open, in_progress, blocked, ...), so the hint must
            # list every offender the gate saw.
            print(f"phase {n} (non-closed; bd list -l phase-{n}{pair} --all):")
            for issue in blockers[n]:
                print(issue_line(issue))
        if n in no_artifacts:
            # Mirrors cairn-gate.py's "no artifacts" phrasing so an operator
            # reading either gate's output recognizes the same failure class.
            print(f"phase {n}: no artifacts on disk (no -SUMMARY.md or "
                  "-VERIFICATION.md) even though ROADMAP.md marks it "
                  "complete.")
    if blockers:
        print("Close them (bd close <id> --reason \"...\") or defer them out of "
              "the phase, then re-run /gsd:ship.")
    if no_artifacts:
        print("Build the phase (SUMMARY/VERIFICATION) or uncheck it in "
              "ROADMAP.md, then re-run /gsd:ship.")
    sys.exit(EXIT_BLOCK)


def resolve_phase_dir(planning_dir, n):
    """Same matching semantics as cairn-map.py / commands/plan.md: numeric
    prefix with optional zero padding and optional project-code prefix."""
    phases = planning_dir / "phases"
    if not phases.is_dir():
        return None
    pat = re.compile(rf"^(?:[A-Za-z0-9]+-)?0*{n}-")
    hits = sorted((d for d in phases.iterdir()
                   if d.is_dir() and pat.match(d.name)),
                  key=lambda d: d.name)
    return hits[0] if hits else None


def disk_reached_executed(pdir):
    """True when the phase directory holds at least one -SUMMARY.md or
    -VERIFICATION.md file. Identical behavior to cairn-gate.py's twin
    helper of the same name — duplicated here (not imported) per this
    bundle's self-contained convention."""
    if pdir is None or not pdir.is_dir():
        return False
    names = [p.name for p in pdir.iterdir() if p.is_file()]
    return any(n.endswith("-SUMMARY.md") or n.endswith("-VERIFICATION.md")
               for n in names)


def verification_status(phase_dir):
    """status: value from the frontmatter of the phase's *-VERIFICATION.md,
    or None when no report exists."""
    if phase_dir is None:
        return None
    reports = sorted(phase_dir.glob("*-VERIFICATION.md"))
    if not reports:
        return None
    in_fm = False
    for idx, line in enumerate(
            reports[0].read_text(encoding="utf-8").splitlines()):
        if idx == 0:
            if line.strip() != "---":
                return None
            in_fm = True
            continue
        if in_fm and line.strip() == "---":
            return None
        if in_fm:
            m = re.match(r"^status:\s*(\S+)", line)
            if m:
                return m.group(1).strip("'\"")
    return None


def cmd_verify_cross(opts, project_dir):
    planning = project_dir / ".planning"
    n = int(opts["phase"], 10)
    labels = [f"phase-{n}"]
    if opts["milestone"]:
        labels.append(f"m-{opts['milestone']}")
    issues, err = bd_list(labels, project_dir)
    if err:
        print(f"[cairn-loop-gate] verify cross-check (phase {n}): skipped — {err}")
        sys.exit(EXIT_OK)

    status = verification_status(resolve_phase_dir(planning, n))
    open_issues = non_closed(issues)
    head = f"[cairn-loop-gate] verify cross-check (phase {n})"
    mismatches = []
    if status in ("passed", "complete") and open_issues:
        mismatches.append(
            f"MISMATCH: VERIFICATION status is '{status}' but "
            f"{len(open_issues)} bd issue(s) are not closed:\n"
            + "\n".join(issue_line(i) for i in open_issues)
            + "\n  -> close them (bd close <id> --reason \"...\") or "
              "reopen the verification.")
    if status is None and issues and not open_issues:
        mismatches.append(
            f"MISMATCH: all {len(issues)} bd issue(s) for phase {n} are "
            "closed but no VERIFICATION report exists — record verification "
            "or reopen the unfinished work (bd reopen <id>).")
    if status not in (None, "passed", "complete") and issues \
            and not open_issues:
        mismatches.append(
            f"MISMATCH: VERIFICATION status is '{status}' but every bd "
            f"issue for phase {n} is already closed — reopen the ids the "
            "failed items map to (bd reopen <id>).")

    if mismatches:
        print(head + ":")
        for m in mismatches:
            print(m)
    else:
        print(f"{head}: OK — bd state and VERIFICATION agree "
              f"({len(issues)} issue(s), {len(open_issues)} non-closed, "
              f"verification: {status or 'none'}).")
    sys.exit(EXIT_OK)


def main(argv):
    opts = parse_args(argv)
    project_dir = Path(opts["project_dir"]
                       or os.environ.get("CLAUDE_PROJECT_DIR")
                       or os.getcwd())
    noop_guard(project_dir)
    if opts["cmd"] == "ship-gate":
        cmd_ship_gate(opts, project_dir)
    else:
        cmd_verify_cross(opts, project_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
