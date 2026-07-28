#!/usr/bin/env python3
"""cairn-doctor — consistency doctor for a repo wired with GSD + beads.

Cross-checks the two sources of truth (.planning/ and the bd tracker) and
reports drift. Read-only except for --fix-labels, which delegates to
cairn-relabel.py pair, and --close-completed, which bulk-closes via
'bd close'.

Usage:
    cairn-doctor.py [--project-dir <dir>] [--json] [--fix-labels]
                    [--close-completed]

Checks (each reported as {id, status: ok|warn|fail, detail, items[]}):
    0. bd-version       the bd binary meets the minimum version cairn
                        relies on (--claim, --all, label add/remove,
                        nested --metadata). Older -> FAIL, unparsable
                        version output -> WARN. Runs first — eleven checks
                        in total.
    1. req-issue        every requirement id in ROADMAP.md's
                        '**Requirements**:' lists has >=1 issue whose
                        metadata.gsd.req matches, scoped to the phase's
                        phase-<N> label and to the active milestone
                        (issues from other milestones are ignored;
                        m-*-less legacy issues count, same semantics as
                        cairn-gate). Missing -> FAIL.
    2. frontmatter-ids  every id in a non-superseded PLAN.md's 'beads:'
                        frontmatter exists in bd and carries the plan's
                        phase-<N> label. Dangling id or wrong label -> FAIL.
    3. maps-fresh       cairn-map.py --check per phase dir that has issues
                        or a map (its exit codes reused: 3 stale -> WARN;
                        a missing map where issues exist -> WARN).
    4. superseded-released  PLAN.md with 'status: superseded' whose beads:
                        ids are still open/in_progress -> WARN (release or
                        move them).
    5. phase-complete-open  non-closed issues whose phase-<N> labels ALL
                        point at phases ROADMAP.md marks COMPLETE -> WARN
                        (FAIL only when a --close-completed the operator
                        asked for was refused, see below), listing the
                        ids. ALL, not any: a
                        cross-phase issue stays live while any of its
                        phases is still open, the same predicate as
                        cairn-status's in_done_phase — otherwise the
                        doctor would flag (and --close-completed would
                        kill) the very issue the status board recommends
                        as the next action. 'Complete' is read with
                        the same lenient semantics as cairn-gate:
                        '- [x] ... Phase N' checkboxes plus milestone
                        progress-table rows ending '| Complete |'. When
                        the ROADMAP checkbox and the on-disk artifacts
                        (every non-superseded PLAN has its SUMMARY)
                        disagree about a flagged phase, a note item spells
                        out the divergence and names the concrete gap (no
                        phase directory / no PLAN in it / a PLAN lacking
                        its SUMMARY). --close-completed bulk-closes
                        the flagged issues via 'bd close <id> --reason
                        "doctor: phase N complete in ROADMAP"' BEFORE the
                        checks run (idempotent; the report shows post-fix
                        state). The divergence note is computed and
                        printed BEFORE those closes — after them the
                        issues leave check 5's scope, so the operator
                        would never see the warning in the one run that
                        needed it — and the note is carried into the
                        check's items too.
                        bd refuses to close an epic with an open child and
                        an issue whose blocker is still open, so the bulk
                        close runs as a FIXPOINT: repeated passes over the
                        target set, each closing whatever bd now accepts,
                        stopping when a whole pass closes nothing. That
                        drains any topology (epic<-epic<-epic chains,
                        blocks edges between phases) without modelling the
                        graph and without --force, which would bulldoze a
                        genuinely open child that is NOT in a complete
                        phase. Whatever survives the fixpoint is reported
                        with bd's own refusal reason and turns this check
                        FAIL (exit 7) — a close the operator asked for and
                        did not get is never silent.
    6. orphans          issues labeled phase-<N> where N is not a ROADMAP
                        phase -> WARN; non-closed issues with NO phase-*
                        label at all (excluding migrated-todo/backlog/
                        quick labels) -> WARN.
    7. label-pairs      issues with a phase-* label but no m-* label ->
                        WARN. --fix-labels repairs them via
                        'cairn-relabel.py pair --milestone <active>' BEFORE
                        the checks run (the report shows post-fix state);
                        refused (exit 2) when the active milestone is
                        unresolvable.
    8. claims-stale     in_progress issues with an assignee whose phase-<N>
                        label differs from STATE.md's active_phase -> WARN
                        (possible stale claim). Skipped when active_phase
                        is unresolvable.
    9. bd-doctor        run 'bd doctor'; first line captured as the
                        summary, pass/fail as bd reports it (exit 0 -> ok,
                        else FAIL).

Active milestone is resolved leniently like cairn-gate: STATE.md
frontmatter 'milestone:' first, else the ROADMAP.md milestone marked in
progress, else None (single-milestone / legacy repo — milestone scoping is
then a no-op).

Exit codes:
    0  all checks ok, or ok + warnings (warnings are printed but never
       change the exit code), or doctor NOT APPLICABLE: .planning/ or
       .beads/ absent — the doctor is for wired repos. When exactly one
       side exists the note suggests /cairn:migrate.
    2  usage error, or --fix-labels refused (milestone unresolvable).
    5  bd unavailable (not on PATH, or bd list failed).
    7  at least one check FAILED — including --close-completed leaving a
       target unclosed (bd refused it and the fixpoint could not drain it),
       which fails check 5 rather than exiting silently 0.
"""
import argparse
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
EXIT_FAILED = 7

SYMBOL = {"ok": "✓", "warn": "⚠", "fail": "✗"}

SCRIPTS_DIR = Path(__file__).resolve().parent

PHASE_LABEL = re.compile(r"^phase-(\d+)$")
PHASE_HEAD = re.compile(r"^#{1,6}\s+Phase\s+0*(\d+)\b")
ANY_HEAD = re.compile(r"^#{1,6}\s")
CHECKBOX_PHASE = re.compile(r"^\s*-\s*\[([ xX])\]\s.*?\bPhase\s+0*(\d+)\b")
TABLE_PHASE = re.compile(r"^\s*\|\s*0*(\d+)[.)\s][^|]*\|.*\|\s*Complete\s*\|",
                         re.IGNORECASE)
REQ_LINE = re.compile(r"^\*\*Requirements\*\*\s*:(.*)$")
REQ_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*-\d+")
VERSION_TOKEN = re.compile(r"\bv\d+(?:\.\d+)*\b")
DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")

# Labels that legitimately carry no phase-* label (migration parking lots,
# plus unphased /cairn:quick side-quests).
NO_PHASE_EXEMPT = {"migrated-todo", "backlog", "quick"}


def die(msg, code):
    print(f"[cairn-doctor] error: {msg}", file=sys.stderr)
    sys.exit(code)


def read_lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


# --------------------------------------------------------------------------- #
# lenient .planning/ parsing (same shapes cairn-gate / cairn-map accept)
# --------------------------------------------------------------------------- #
def state_frontmatter(planning_dir):
    """{'milestone': str|None, 'active_phase': int|None} from STATE.md."""
    out = {"milestone": None, "active_phase": None}
    lines = read_lines(planning_dir / "STATE.md")
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^(milestone|active_phase)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        val = m.group(2).split("#", 1)[0].strip().strip("'\"").strip()
        if m.group(1) == "milestone" and val:
            out["milestone"] = val
        elif m.group(1) == "active_phase":
            digits = re.search(r"\d+", val)
            if digits:
                out["active_phase"] = int(digits.group(0))
    return out


def roadmap_milestone(planning_dir):
    """Milestone marked in progress in ROADMAP.md (🚧 / '(in progress)'
    line carrying a vN[.N...] token), or None."""
    for line in read_lines(planning_dir / "ROADMAP.md"):
        if "🚧" in line or re.search(r"\(in progress\)", line, re.IGNORECASE):
            m = VERSION_TOKEN.search(line)
            if m:
                return m.group(0)
    return None


def roadmap_phases_and_reqs(planning_dir):
    """(set of phase numbers, {phase: [req ids]}) parsed leniently from
    ROADMAP.md: 'Phase N' headings and checkbox lines enumerate phases;
    a '**Requirements**:' line inside a phase heading's section maps it."""
    phases, reqs = set(), {}
    current = None
    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = PHASE_HEAD.match(line)
        if m:
            current = int(m.group(1))
            phases.add(current)
            continue
        if ANY_HEAD.match(line):
            current = None
        m = CHECKBOX_PHASE.match(line)
        if m:
            phases.add(int(m.group(2)))
        if current is not None:
            m = REQ_LINE.match(line.strip())
            if m:
                reqs[current] = REQ_ID.findall(m.group(1))
    return phases, reqs


def roadmap_completed_phases(planning_dir):
    """Phase numbers ROADMAP.md marks COMPLETE, with the same lenient
    semantics as cairn-gate: checked '- [x] ... Phase N' checkbox lines
    plus milestone progress-table rows ending '| Complete |'."""
    done = set()
    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = CHECKBOX_PHASE.match(line)
        if m:
            if m.group(1) in ("x", "X"):
                done.add(int(m.group(2)))
            continue
        m = TABLE_PHASE.match(line)
        if m:
            done.add(int(m.group(1)))
    return done


def disk_complete_phases(planning_dir):
    """Phase numbers that look complete ON DISK: the phase dir has >=1
    *-PLAN.md and every non-superseded plan has its sibling *-SUMMARY.md.
    The artifact-based notion of 'complete', held next to the ROADMAP
    checkbox one — phase-complete-open notes when the two diverge."""
    done = set()
    for n, d in phase_dirs(planning_dir):
        plans = sorted(d.glob("*-PLAN.md"))
        if not plans:
            continue
        complete = True
        for f in plans:
            status, _ = parse_plan_frontmatter(f)
            if status == "superseded":
                continue
            summary = f.with_name(f.name[:-len("-PLAN.md")] + "-SUMMARY.md")
            if not summary.is_file():
                complete = False
                break
        if complete:
            done.add(n)
    return done


def disk_incomplete_reasons(planning_dir):
    """{phase number: why it falls short of disk_complete_phases}, for the
    phases that HAVE a directory. The divergence note used to claim 'a
    non-superseded PLAN lacks its SUMMARY' for every gap, including a phase
    with no directory at all — this names the real case instead. A phase
    absent from the mapping has no directory on disk (the caller's
    default); a phase in disk_complete_phases is absent too."""
    reasons = {}
    for n, d in phase_dirs(planning_dir):
        plans = sorted(d.glob("*-PLAN.md"))
        if not plans:
            reasons[n] = f"{d.name}/ holds no PLAN"
            continue
        missing = []
        for f in plans:
            status, _ = parse_plan_frontmatter(f)
            if status == "superseded":
                continue
            summary = f.with_name(f.name[:-len("-PLAN.md")] + "-SUMMARY.md")
            if not summary.is_file():
                missing.append(f.name)
        if missing:
            extra = (f" (+{len(missing) - 1} more)" if len(missing) > 1
                     else "")
            reasons[n] = f"{missing[0]}{extra} lacks its SUMMARY"
    return reasons


def divergence_sentence(n, disk_reasons):
    """The one sentence both the pre-close warning and check 5's note item
    print, carrying the concrete on-disk gap for phase n."""
    why = (disk_reasons or {}).get(n, "no phase directory on disk")
    return (f"phase {n} is checked off in ROADMAP.md but its on-disk "
            f"artifacts disagree ({why}) — confirm the phase is really "
            f"done before closing")


def parse_plan_frontmatter(path):
    """(status, beads ids) from a PLAN.md's YAML frontmatter, leniently:
    'beads: [a, b]' flow style (trailing comment tolerated) or an indented
    '- id' block list."""
    lines = read_lines(path)
    if not lines or lines[0].strip() != "---":
        return None, []
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    status, beads = None, []
    for i, line in enumerate(body):
        m = re.match(r"^status\s*:\s*(.+?)\s*$", line)
        if m:
            status = m.group(1).split("#", 1)[0].strip().strip("'\"")
            continue
        m = re.match(r"^beads\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1)
        if "[" in rest:
            inner = rest[rest.index("[") + 1:]
            if "]" in inner:
                inner = inner[:inner.index("]")]
            beads = [t.strip().strip("'\"") for t in inner.split(",")]
            beads = [b for b in beads if b]
        else:
            for cont in body[i + 1:]:
                mi = re.match(r"^\s*-\s*(.+?)\s*$", cont)
                if not mi:
                    break
                beads.append(mi.group(1).strip("'\""))
    return status, beads


def plan_inventory(planning_dir):
    """[{rel, phase, status, beads}] for every *-PLAN.md under phases/."""
    plans = []
    phases_root = planning_dir / "phases"
    if not phases_root.is_dir():
        return plans
    for d in sorted(p for p in phases_root.iterdir() if p.is_dir()):
        m = DIR_PREFIX.match(d.name)
        if not m:
            continue
        n = int(m.group(1))
        for f in sorted(d.glob("*-PLAN.md")):
            status, beads = parse_plan_frontmatter(f)
            plans.append({"rel": f"{d.name}/{f.name}", "phase": n,
                          "status": status, "beads": beads})
    return plans


def phase_dirs(planning_dir):
    """[(phase number, dir Path)] under <planning>/phases/."""
    out = []
    phases_root = planning_dir / "phases"
    if not phases_root.is_dir():
        return out
    for d in sorted(p for p in phases_root.iterdir() if p.is_dir()):
        m = DIR_PREFIX.match(d.name)
        if m:
            out.append((int(m.group(1)), d))
    return out


# --------------------------------------------------------------------------- #
# bd access
# --------------------------------------------------------------------------- #
def bd_all_issues(root):
    """Every issue (open and closed), labels normalized, exit 5 on failure."""
    cmd = ["bd", "-C", str(root), "list", "--all", "--limit", "0", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"bd list failed: {proc.stderr.strip()}", EXIT_NO_BD)
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        die(f"bd list returned invalid JSON: {e}", EXIT_NO_BD)
    if data is None:
        data = []
    issues = data if isinstance(data, list) else [data]
    for issue in issues:
        issue["labels"] = issue.get("labels") or []
    return sorted(issues, key=lambda i: i.get("id", ""))


def gsd_req(issue):
    """metadata.gsd.req of a bd issue, or None when absent."""
    md = issue.get("metadata")
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except json.JSONDecodeError:
            md = None
    gsd = md.get("gsd") if isinstance(md, dict) else None
    req = gsd.get("req") if isinstance(gsd, dict) else None
    return req.strip() if isinstance(req, str) and req.strip() else None


def phase_nums(issue):
    """Phase numbers from the issue's phase-<N> labels."""
    out = []
    for lb in issue["labels"]:
        m = PHASE_LABEL.match(lb)
        if m:
            out.append(int(m.group(1)))
    return out


def in_done_phase(issue, completed):
    """True when the issue is phase-labeled and EVERY phase label points at
    a ROADMAP-complete phase — an issue the roadmap says was already
    delivered. ALL, not any: a cross-phase issue stays live while any of
    its phases is still open, and an unlabeled issue is never stale. Same
    predicate as cairn-status's in_done_phase, so the board and the doctor
    never disagree about what is deliverable."""
    ns = set(phase_nums(issue))
    return bool(ns) and ns <= set(completed)


def in_milestone(issue, milestone):
    """Same scoping as cairn-gate: the issue counts when no milestone is
    resolved, when it carries m-<milestone>, or when it carries no m-*
    label at all (legacy stray)."""
    m_labels = [lb for lb in issue["labels"] if lb.startswith("m-")]
    return milestone is None or not m_labels or f"m-{milestone}" in m_labels


# --------------------------------------------------------------------------- #
# the checks
# --------------------------------------------------------------------------- #
def check_req_issue(issues, reqs_by_phase, milestone):
    items = []
    total = 0
    scoped = [i for i in issues if in_milestone(i, milestone)]
    for n in sorted(reqs_by_phase):
        for req in reqs_by_phase[n]:
            total += 1
            matching = [i for i in scoped if gsd_req(i) == req]
            if any(n in phase_nums(i) for i in matching):
                continue
            if matching:
                ids = ", ".join(i.get("id", "?") for i in matching)
                items.append(f"{req} (phase {n}): {ids} carry the req but "
                             f"none is labeled phase-{n}")
            else:
                items.append(f"{req} (phase {n}): no issue with "
                             f"metadata.gsd.req == {req}")
    if not total:
        detail = "no '**Requirements**:' lists found in ROADMAP.md"
    elif items:
        detail = f"{len(items)} of {total} requirement(s) unmapped"
    else:
        detail = f"{total} requirement(s) mapped to issues"
    return {"id": "req-issue", "status": "fail" if items else "ok",
            "detail": detail, "items": items}


def check_frontmatter_ids(plans, issues):
    by_id = {i.get("id"): i for i in issues}
    items = []
    checked = 0
    for plan in plans:
        if plan["status"] == "superseded":
            continue
        for bid in plan["beads"]:
            checked += 1
            iss = by_id.get(bid)
            if iss is None:
                items.append(f"{plan['rel']}: {bid} not found in bd")
            elif plan["phase"] not in phase_nums(iss):
                labels = ", ".join(iss["labels"]) or "none"
                items.append(f"{plan['rel']}: {bid} lacks label "
                             f"phase-{plan['phase']} (labels: {labels})")
    detail = (f"{len(items)} of {checked} plan bead id(s) broken" if items
              else f"{checked} plan bead id(s) verified")
    return {"id": "frontmatter-ids", "status": "fail" if items else "ok",
            "detail": detail, "items": items}


def check_maps_fresh(root, planning_dir, issues):
    items = []
    checked = 0
    for n, d in phase_dirs(planning_dir):
        map_path = d / f"{n:02d}-BEADS-MAP.md"
        n_issues = sum(1 for i in issues if n in phase_nums(i))
        if not map_path.is_file():
            if n_issues:
                items.append(f"phase {n}: {n_issues} issue(s) but no "
                             f"{map_path.name} — run cairn-map.sh {n}")
                checked += 1
            continue
        checked += 1
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "cairn-map.py"), str(n),
             "--check", "--planning-dir", str(planning_dir)],
            capture_output=True, text=True, cwd=str(root))
        if proc.returncode == 0:
            continue
        if proc.returncode == 3:
            items.append(f"phase {n}: stale map {map_path.name} — "
                         f"run cairn-map.sh {n}")
        elif proc.returncode == 5:
            die(f"cairn-map --check: bd unavailable: "
                f"{proc.stderr.strip()}", EXIT_NO_BD)
        else:
            text = proc.stderr.strip() or proc.stdout.strip()
            first = text.splitlines()[0] if text else ""
            items.append(f"phase {n}: cairn-map --check exit "
                         f"{proc.returncode}: {first}")
    detail = (f"{len(items)} of {checked} phase map(s) need attention"
              if items else f"{checked} phase map(s) current")
    return {"id": "maps-fresh", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


def check_superseded_released(plans, issues):
    by_id = {i.get("id"): i for i in issues}
    items = []
    n_superseded = 0
    for plan in plans:
        if plan["status"] != "superseded":
            continue
        n_superseded += 1
        for bid in plan["beads"]:
            iss = by_id.get(bid)
            if iss and iss.get("status") in ("open", "in_progress"):
                items.append(f"{plan['rel']}: {bid} still "
                             f"{iss['status']} — release or move it")
    detail = (f"{len(items)} bead(s) still live under superseded plan(s)"
              if items else f"{n_superseded} superseded plan(s), "
                            "no live beads")
    return {"id": "superseded-released", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


def check_phase_complete_open(issues, completed, disk_done, milestone,
                              closed_n, closed_phases=(), disk_reasons=None,
                              close_failures=()):
    """Check 5 — non-closed issues whose phase-<N> labels ALL point at
    phases ROADMAP.md marks complete. WARN by default (the phase's checkbox
    and its tracker disagree; --close-completed bulk-closes, or re-open the
    phase), FAIL only when a --close-completed the operator asked for was
    refused by bd and the fixpoint could not drain it: close_failures
    carries [(id, bd's reason)] and each one replaces that issue's generic
    warn item. A cross-phase issue with one phase still open is NOT flagged
    (in_done_phase — cairn-status's semantics). Appends a note item per
    flagged phase where the ROADMAP checkbox and the on-disk artifacts
    diverge; closed_phases carries the phases --close-completed just
    emptied so their divergence note survives the close that removed the
    issues from scope."""
    items = []
    flagged = set(closed_phases)
    failures = dict(close_failures)
    reported = set()
    scoped = [i for i in issues
              if i.get("status") != "closed" and in_milestone(i, milestone)]
    for iss in scoped:
        if not in_done_phase(iss, completed):
            continue
        done = sorted(set(phase_nums(iss)))
        flagged.update(done)
        phases = ", ".join(str(n) for n in done)
        iid = iss.get("id", "?")
        if iid in failures:
            reported.add(iid)
            items.append(f"{iid}: --close-completed could not close it — "
                         f"{failures[iid]}")
        else:
            items.append(f"{iid}: {iss.get('status')} but phase "
                         f"{phases} is complete in ROADMAP.md — close it "
                         f"(--close-completed bulk-closes) or re-open the "
                         f"phase")
    # A refused close whose issue somehow left scope still gets reported —
    # the operator asked for it and did not get it.
    for iid, why in close_failures:
        if iid not in reported:
            items.append(f"{iid}: --close-completed could not close it — "
                         f"{why}")
    n_flagged = len(items)
    for n in sorted(flagged):
        if n not in disk_done:
            items.append(f"note: {divergence_sentence(n, disk_reasons)}")
    detail = (f"{n_flagged} non-closed issue(s) in completed phase(s)"
              if n_flagged
              else "no non-closed issues in completed phases")
    if closed_n:
        detail += f" (closed {closed_n} via --close-completed)"
    if close_failures:
        detail += (f" — {len(close_failures)} refused by bd, still open")
    status = ("fail" if close_failures
              else "warn" if n_flagged else "ok")
    return {"id": "phase-complete-open", "status": status,
            "detail": detail, "items": items}


def check_orphans(issues, roadmap_phases):
    items = []
    for iss in issues:
        nums = phase_nums(iss)
        if nums:
            if roadmap_phases:
                for n in nums:
                    if n not in roadmap_phases:
                        items.append(f"{iss.get('id', '?')}: labeled "
                                     f"phase-{n} but ROADMAP.md has no "
                                     f"phase {n}")
        elif (iss.get("status") != "closed"
                and not NO_PHASE_EXEMPT.intersection(iss["labels"])):
            items.append(f"{iss.get('id', '?')}: no phase-* label "
                         f"({iss.get('status')}: "
                         f"{iss.get('title', '')})")
    detail = (f"{len(items)} orphan issue(s)" if items
              else f"{len(issues)} issue(s), no orphans")
    return {"id": "orphans", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


def unpaired_issues(issues):
    return [i for i in issues
            if phase_nums(i)
            and not any(lb.startswith("m-") for lb in i["labels"])]


def check_label_pairs(issues, milestone, fixed, fix_error):
    items = []
    for iss in unpaired_issues(issues):
        labels = ", ".join(lb for lb in iss["labels"]
                           if PHASE_LABEL.match(lb))
        hint = (f"cairn-relabel.sh pair --milestone {milestone}"
                if milestone else "cairn-relabel.sh pair --milestone <m>")
        items.append(f"{iss.get('id', '?')}: {labels} but no m-* label "
                     f"— {hint}")
    if fix_error:
        items.insert(0, f"--fix-labels failed: {fix_error}")
        status = "fail"
        detail = "--fix-labels could not repair the pairing"
    else:
        status = "warn" if items else "ok"
        detail = (f"{len(items)} issue(s) missing the m-* pair" if items
                  else "every phase-labeled issue carries an m-* label")
        if fixed:
            detail += f" (fixed {fixed} via cairn-relabel pair)"
    return {"id": "label-pairs", "status": status,
            "detail": detail, "items": items}


def check_claims_stale(issues, milestone, active_phase):
    if active_phase is None:
        return {"id": "claims-stale", "status": "ok",
                "detail": "skipped — no active_phase in STATE.md",
                "items": []}
    items = []
    for iss in issues:
        if iss.get("status") != "in_progress" or not iss.get("assignee"):
            continue
        if not in_milestone(iss, milestone):
            continue
        nums = phase_nums(iss)
        if nums and active_phase not in nums:
            phases = ", ".join(f"phase-{n}" for n in nums)
            items.append(f"{iss.get('id', '?')}: in_progress "
                         f"(assignee {iss['assignee']}) on {phases} but "
                         f"active phase is {active_phase} — stale claim?")
    detail = (f"{len(items)} possible stale claim(s)" if items
              else f"no assigned in_progress issues outside "
                   f"phase {active_phase}")
    return {"id": "claims-stale", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


BD_MIN_VERSION = (1, 1, 0)


def check_bd_version():
    """Check 0 — the bd binary meets the minimum version cairn relies on
    (--claim semantics, --all, label add/remove, nested --metadata)."""
    need = ".".join(map(str, BD_MIN_VERSION))
    proc = subprocess.run(["bd", "version"], capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    if proc.returncode != 0 or not m:
        return {"id": "bd-version", "status": "warn",
                "detail": "could not parse bd version output: "
                          f"{out or proc.stderr.strip() or '(empty)'}",
                "items": []}
    ver = tuple(int(x) for x in m.groups())
    got = ".".join(map(str, ver))
    if ver < BD_MIN_VERSION:
        return {"id": "bd-version", "status": "fail",
                "detail": f"bd {got} < required {need} — upgrade beads "
                          "(brew upgrade beads / npm update -g @beads/bd)",
                "items": []}
    return {"id": "bd-version", "status": "ok",
            "detail": f"bd {got} >= {need}", "items": []}


def check_bd_doctor(root):
    try:
        proc = subprocess.run(["bd", "doctor"], capture_output=True,
                              text=True, cwd=str(root), timeout=60)
    except subprocess.TimeoutExpired:
        return {"id": "bd-doctor", "status": "warn",
                "detail": "bd doctor timed out after 60s", "items": []}
    text = proc.stdout.strip() or proc.stderr.strip()
    summary = text.splitlines()[0].strip() if text else "(no output)"
    status = "ok" if proc.returncode == 0 else "fail"
    return {"id": "bd-doctor", "status": status,
            "detail": f"exit {proc.returncode}: {summary}", "items": []}


def check_gsd_capability(root):
    """Check 10 — which GSD lineage is installed, and whether the cairn
    capability actually registered against it.

    This is the check that would have caught the plugin's longest-lived bug:
    the wrappers worked, the fusion did not, and nothing said so. It is a
    FAIL, not a warn, whenever a repo with .planning/ has no registered
    capability — a soft signal here is exactly how the failure stayed
    invisible.

    Delegates to cairn-capability.py so the lineage rules and the two
    registration checks live in one place. Its exit codes: 0 registered,
    5 no GSD binary found, 7 not registered.
    """
    script = Path(__file__).resolve().parent / "cairn-capability.py"
    if not script.is_file():
        return {"id": "gsd-capability", "status": "warn",
                "detail": "cairn-capability.py not found beside this script",
                "items": []}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "detect",
             "--project-dir", str(root), "--json"],
            capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"id": "gsd-capability", "status": "warn",
                "detail": f"could not run cairn-capability.py: {exc}",
                "items": []}

    try:
        info = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"id": "gsd-capability", "status": "warn",
                "detail": "cairn-capability.py did not return JSON "
                          f"(exit {proc.returncode})", "items": []}

    lineage = info.get("lineage", "unknown")
    if lineage == "absent":
        # No GSD binary is discoverable. That is not proof the capability is
        # missing, so it does not carry the same verdict as a registry that
        # answered and did not list cairn.
        return {"id": "gsd-capability", "status": "warn",
                "detail": "no GSD binary found — cannot tell whether the "
                          "cairn capability is registered", "items": []}

    # Checked before registration, because it outranks it: a plugin Claude Code
    # refuses to load exposes no /gsd:* commands at all, so a perfectly
    # registered capability has nothing to attach to. It is also invisible from
    # inside the capability checks — the gsd-tools CLI keeps working, which is
    # why the install succeeds while the plugin is dead.
    if info.get("manifest_loadable") is False:
        return {"id": "gsd-capability", "status": "fail",
                "detail": "the installed gsd-core will NOT load — "
                          f"{info.get('manifest_detail', 'manifest defect')}",
                "items": [
                    "Fix: bash \"${CLAUDE_PLUGIN_ROOT}/scripts/"
                    "cairn-capability.sh\" repair-manifest, then /reload-plugins",
                    "Upstream: open-gsd/gsd-core#2077 has the one-line fix; a "
                    "plugin update re-introduces the defect until it lands",
                ]}

    # Two GSD lineages at once. cairn's discovery prefers gsd-core, so the
    # capability can be registered and complete while the operator's /gsd:*
    # commands are answered by the 4.x plugin that cannot host it — the fusion
    # absent with every other signal green. The likeliest way to land here is
    # having had GSD before meeting cairn.
    if info.get("both_lineages"):
        inst = info.get("installed_gsd") or {}
        legacy = inst.get("legacy") or []
        return {"id": "gsd-capability", "status": "fail",
                "detail": "two GSD lineages installed — "
                          f"{', '.join(legacy + (inst.get('core') or []))}. "
                          "/gsd:* may be answered by the 4.x plugin, which "
                          "cannot host the capability",
                "items": [
                    f"Fix: claude plugin uninstall {legacy[0]}"
                    if legacy else "Fix: remove the 4.x gsd plugin",
                    "then /reload-plugins",
                ]}

    if info.get("ok"):
        cap = info.get("capability") or {}
        return {"id": "gsd-capability", "status": "ok",
                "detail": f"gsd-core lineage; cairn v{cap.get('version', '?')} "
                          f"registered ({cap.get('scope', '?')} scope)",
                "items": []}

    remedy = (info.get("remedy") or "").splitlines()
    detail = {
        "legacy": "GSD 4.x lineage — it has no 'capability' subcommand, so "
                  "plain /gsd:* does NOT touch bd issues. Install the official "
                  "core: claude plugin install gsd-core@cairngo",
    }.get(lineage)
    if detail is None:
        detail = (remedy[0] if remedy
                  else f"capability not registered (lineage {lineage})")
    return {"id": "gsd-capability", "status": "fail", "detail": detail,
            "items": [ln.strip() for ln in remedy[1:] if ln.strip()]}


# --------------------------------------------------------------------------- #
# output + main
# --------------------------------------------------------------------------- #
def emit(as_json, summary, human_lines):
    if as_json:
        print(json.dumps(summary))
    else:
        for line in human_lines:
            print(line)


def main():
    parser = argparse.ArgumentParser(
        prog="cairn-doctor",
        description="Consistency doctor for a repo wired with GSD + beads.")
    parser.add_argument("--project-dir", metavar="DIR",
                        help="repo root (default: $CLAUDE_PROJECT_DIR or cwd)")
    parser.add_argument("--json", action="store_true",
                        help="print a machine summary instead of the report")
    parser.add_argument("--fix-labels", action="store_true",
                        help="repair phase-* issues lacking an m-* label via "
                             "cairn-relabel pair --milestone <active>")
    parser.add_argument("--close-completed", action="store_true",
                        help="bulk-close non-closed issues whose phase-<N> "
                             "labels ALL point at phases ROADMAP.md marks "
                             "complete (bd close --reason), before the "
                             "checks run; a cross-phase issue with an open "
                             "phase is left alone")
    args = parser.parse_args()

    root = Path(args.project_dir
                or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    planning_dir = root / ".planning"
    has_planning = planning_dir.is_dir()
    has_beads = (root / ".beads").is_dir()

    summary = {"applicable": False, "ok": True, "milestone": None,
               "active_phase": None, "checks": [], "note": None}

    if not has_planning and not has_beads:
        summary["note"] = ("neither .planning/ nor .beads/ — doctor not "
                           "applicable (it checks wired repos)")
        emit(args.json, summary, [f"[cairn-doctor] note: {summary['note']}"])
        sys.exit(EXIT_OK)
    if has_planning != has_beads:
        present = ".planning/" if has_planning else ".beads/"
        absent = ".beads/" if has_planning else ".planning/"
        summary["note"] = (f"{present} exists but {absent} is absent — "
                           "doctor not applicable (it checks wired repos); "
                           "run /cairn:migrate to bootstrap the missing side")
        emit(args.json, summary, [f"[cairn-doctor] note: {summary['note']}"])
        sys.exit(EXIT_OK)

    if shutil.which("bd") is None:
        print("[cairn-doctor] warning: 'bd' not on PATH — doctor cannot "
              "run (exit 5)", file=sys.stderr)
        sys.exit(EXIT_NO_BD)

    summary["applicable"] = True
    issues = bd_all_issues(root)
    state = state_frontmatter(planning_dir)
    milestone = state["milestone"] or roadmap_milestone(planning_dir)
    active_phase = state["active_phase"]
    summary["milestone"] = milestone
    summary["active_phase"] = active_phase

    roadmap_phases, reqs_by_phase = roadmap_phases_and_reqs(planning_dir)
    completed_set = roadmap_completed_phases(planning_dir)
    disk_done = disk_complete_phases(planning_dir)
    disk_reasons = disk_incomplete_reasons(planning_dir)
    plans = plan_inventory(planning_dir)

    # The fixer flags run BEFORE the checks so the report shows post-fix
    # state. --close-completed first: it shrinks the later fixers' inputs.
    closed_n = 0
    closed_phases = set()
    close_failures = []
    if args.close_completed:
        # in_done_phase (ALL, not any) is what keeps this from killing a
        # cross-phase issue that cairn-status still lists as ready.
        targets = [i for i in issues
                   if i.get("status") != "closed"
                   and i.get("id")
                   and in_milestone(i, milestone)
                   and in_done_phase(i, completed_set)]
        closed_phases = {n for i in targets for n in phase_nums(i)}
        # The checkbox<->artifacts divergence note is printed BEFORE the
        # bulk close: the closes empty check 5's scope, so the operator
        # must see "confirm the phase is really done" while it can still
        # change the decision. --json consumers read the same note off
        # check 5's items (closed_phases carries it there).
        if not args.json:
            for n in sorted(closed_phases - disk_done):
                print(f"[cairn-doctor] warning: "
                      f"{divergence_sentence(n, disk_reasons)}")
        # bd refuses to close an epic that still has an open child, and an
        # issue whose blocker is still open. targets is in bd list order,
        # which says nothing about that ordering, so close by FIXPOINT:
        # sweep the pending set, keep whatever bd refused, repeat while a
        # pass still closed something. Any topology drains (an
        # epic<-epic<-epic chain needs one pass per link) with no graph
        # model and no --force — forcing would bulldoze a genuinely open
        # child that is NOT itself in a completed phase.
        pending = list(targets)
        last_error = {}
        while pending:
            stuck, progressed = [], False
            for iss in pending:
                n = min(phase_nums(iss))
                proc = subprocess.run(
                    ["bd", "-C", str(root), "close", iss["id"], "--reason",
                     f"doctor: phase {n} complete in ROADMAP"],
                    capture_output=True, text=True)
                if proc.returncode != 0:
                    last_error[iss["id"]] = (
                        proc.stderr.strip() or proc.stdout.strip()
                        or f"bd close exited {proc.returncode}")
                    stuck.append(iss)
                    continue
                closed_n += 1
                progressed = True
                if not args.json:
                    print(f"[cairn-doctor] closed {iss['id']} — phase {n} "
                          f"complete in ROADMAP ({iss.get('title', '')})")
            pending = stuck
            if not progressed:
                break
        # Survivors are reported (check 5 turns FAIL -> exit 7), never
        # swallowed: an operator who asked for a close and got none of it
        # must not read exit 0.
        close_failures = [(i["id"], last_error.get(i["id"], "unknown error"))
                          for i in pending]
        if closed_n:
            issues = bd_all_issues(root)
            # These closes go through 'bd close' directly, so no
            # post-bd-write hook fires and external mirrors keep showing
            # them open — same reminder cairn-migrate apply prints.
            if not args.json and (root / ".cairn" / "sync.json").is_file():
                print(f"[cairn-doctor] reminder: .cairn/sync.json exists — "
                      f"run /cairn:sync-pull to reconcile external mirrors "
                      f"({closed_n} issue(s) closed here bypassed the push "
                      f"hook)")

    # --fix-labels runs BEFORE the checks so the report shows post-fix state.
    fixed, fix_error = 0, None
    if args.fix_labels:
        candidates = unpaired_issues(issues)
        if candidates:
            if milestone is None:
                die("cannot --fix-labels: active milestone unresolvable "
                    "(no 'milestone:' in STATE.md frontmatter and no "
                    "in-progress milestone in ROADMAP.md)", EXIT_USAGE)
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "cairn-relabel.py"),
                 "pair", "--milestone", milestone, "--dir", str(root)],
                capture_output=True, text=True)
            if proc.returncode == 5:
                die(f"cairn-relabel pair: bd unavailable: "
                    f"{proc.stderr.strip()}", EXIT_NO_BD)
            if proc.returncode != 0:
                fix_error = (proc.stderr.strip() or
                             f"exit {proc.returncode}")
            else:
                fixed = len(candidates)
            issues = bd_all_issues(root)

    checks = [
        check_bd_version(),
        check_req_issue(issues, reqs_by_phase, milestone),
        check_frontmatter_ids(plans, issues),
        check_maps_fresh(root, planning_dir, issues),
        check_superseded_released(plans, issues),
        check_phase_complete_open(issues, completed_set, disk_done,
                                  milestone, closed_n, closed_phases,
                                  disk_reasons, close_failures),
        check_orphans(issues, roadmap_phases),
        check_label_pairs(issues, milestone, fixed, fix_error),
        check_claims_stale(issues, milestone, active_phase),
        check_bd_doctor(root),
        check_gsd_capability(root),
    ]
    summary["checks"] = checks
    n_fail = sum(1 for c in checks if c["status"] == "fail")
    n_warn = sum(1 for c in checks if c["status"] == "warn")
    n_ok = len(checks) - n_fail - n_warn
    summary["ok"] = n_fail == 0

    lines = [f"[cairn-doctor] {root} — milestone: "
             f"{milestone or 'unresolved'}, active phase: "
             f"{active_phase if active_phase is not None else '?'}"]
    for c in checks:
        lines.append(f" {SYMBOL[c['status']]} {c['id']:<20} {c['detail']}")
        lines += [f"     - {item}" for item in c["items"]]
    verdict = "ok" if n_fail == 0 else "FAIL"
    lines.append(f"[cairn-doctor] {verdict} — {n_ok} ok, {n_warn} "
                 f"warning(s), {n_fail} failure(s)")

    emit(args.json, summary, lines)
    sys.exit(EXIT_OK if n_fail == 0 else EXIT_FAILED)


if __name__ == "__main__":
    main()
