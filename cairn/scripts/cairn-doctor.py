#!/usr/bin/env python3
"""cairn-doctor — consistency doctor for a repo wired with GSD + beads.

Cross-checks the two sources of truth (.planning/ and the bd tracker) and
reports drift. Read-only except for --fix-labels, which delegates to
cairn-relabel.py pair, --close-completed, which bulk-closes via
'bd close', and --link-refs, which backfills bd's --external-ref field
via 'bd update'.

Usage:
    cairn-doctor.py [--project-dir <dir>] [--json] [--fix-labels]
                    [--close-completed] [--link-refs]
                    [--apply-reconciliation N]

Checks (each reported as {id, status: ok|warn|fail, detail, items[]}):
    0. bd-version       the bd binary meets the minimum version cairn
                        relies on (--claim, --all, label add/remove,
                        nested --metadata). Older -> FAIL, unparsable
                        version output -> WARN. Runs first — sixteen
                        checks in total.
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
    10. gsd-capability  which GSD lineage is installed and whether the
                        cairn capability actually registered against it
                        (see check_gsd_capability()'s own docstring for
                        the full routing — an unloadable manifest, two
                        lineages at once, the 4.x lineage, or an
                        unregistered/partly-staged bundle -> FAIL; no GSD
                        binary found at all -> WARN, not evidence either
                        way).
    11. phase-corroboration  reads Plan 13-01's phase_model() verdict for
                        every phase (shells to 'cairn-status.py --json',
                        the same subprocess pattern check 3 already uses
                        for cairn-map.py --check) and itemizes every
                        phase whose corroboration != "ok": a "conflict"
                        verdict lists each entry in that phase's
                        conflicts[] as '<n>: <detail> (<severity>) —
                        <recommendation> — <source> last moved <ts>, ...',
                        the recommendation being the FIRST, most-likely
                        fix (D-01) and differing by the conflict's source
                        pair (disk/bd -> close the bd issue or run
                        /cairn:work; roadmap/disk -> confirm before
                        leaving the checkbox ticked; state_md/disk -> the
                        pointer is merely stale, no action needed); the
                        trailing "last moved" clause (Phase 16, JOUR-02)
                        names when EACH of that conflict's cited sources
                        last moved, pulled from 'cairn-journal.py
                        last-moved --phase N --json' (called at most ONCE
                        per phase, cached, never once per conflict item),
                        "never observed" for a source the journal has
                        never seen — a broken/missing journal degrades
                        that one clause to nothing, never this check's
                        own status. An "unknown" verdict (bd unreadable
                        for that phase) gets one item saying so, no
                        last-moved clause. A "blocks"-severity conflict ->
                        FAIL (reuses EXIT_FAILED, no new exit code);
                        "informs"-only or "unknown" -> WARN, never fails
                        the run (D-10 applied to doctor's own exit code).
                        A subprocess/JSON failure degrades to WARN rather
                        than crashing the whole doctor run over this one
                        check.
    12. phase-artifacts CARD-02/D-04: names which artifact is missing for a
                        phase whose board row would otherwise be a bare
                        dash. Reuses main()'s already-computed
                        disk_incomplete_reasons() (no duplicate frontmatter
                        parser) plus 'cairn-status.py --json' (same
                        subprocess pattern as check 11) for disk_state /
                        verify_status. Two WARN-only shapes: a phase whose
                        disk_state has already reached "verified" (an
                        NN-VERIFICATION.md exists) while one of its
                        PLAN.md files still lacks its own SUMMARY.md,
                        named by filename; and a "verified" phase whose
                        NN-VERIFICATION.md carries no readable 'status:'
                        field. The missing-SUMMARY half is gated on
                        disk_state == "verified" ON PURPOSE — an ungated
                        version fired on every plans-without-summary gap,
                        which is the state of any phase mid-flight between
                        waves, and a plan-checker caught that as noise; a
                        phase someone ran /cairn:verify on despite an
                        unsummarized plan is a genuine anomaly, ordinary
                        in-progress work is not. Known accepted gap: a
                        phase stuck at "executed" that never reaches
                        "verified" — its SUMMARY-less plan never gets
                        flagged here either, the false negative the
                        narrowed gate trades for removing the mid-flight
                        false positive. NEVER fails the run (see
                        check_phase_artifacts()'s own docstring for why);
                        a subprocess/JSON failure against cairn-status.py
                        degrades to a single WARN item rather than falling
                        back to the ungated dump.
    13. external-ref    CORR-08/D-11 backfill: every CLOSED issue lacking
                        bd's own 'external_ref' field, resolved to its
                        phase and that phase's plan(s) 'files_modified:',
                        cross-referenced against 'git log' in a +/-2 day
                        window around the issue's closed_at for a commit
                        subject carrying a single, unambiguous '(#N)'
                        token (zero or multiple distinct numbers found ->
                        never a candidate, never guessed). Read-only by
                        default: reports each unambiguous candidate as
                        '<id> -> gh-N', writes nothing. --link-refs backs
                        it: runs 'bd update <id> --external-ref gh-N' for
                        each candidate, itemizes what it linked, and is
                        idempotent (an issue already carrying an
                        external_ref is excluded from consideration up
                        front). A shallow clone's git match can be
                        silently WRONG at the boundary commit, not merely
                        incomplete (D-08, reproduced in STACK.md) — a
                        single 'git rev-parse --is-shallow-repository'
                        check skips the whole check for the run rather
                        than trusting it. WARN only when an unambiguous,
                        actionable candidate is waiting (never merely
                        because history predates the convention — that is
                        the expected, unremarkable case per STACK.md).
    14. lease-stale     cairn-lease.py status --all --json (Plan 15-01)
                        itemized for every phase whose lease is currently
                        held AND stale (heartbeat older than the 4h TTL
                        cairn-lease.py enforces): phase, holder, actor,
                        acquired_at, heartbeat_at, and the reclaim path
                        ("reclaimable — the next /cairn:work N takes it
                        automatically, or run cairn-lease.sh release N to
                        clear it now") -> WARN, one item per stale lease;
                        no stale lease -> ok. Never FAIL — mirrors check 8
                        (claims-stale)'s own discipline one level up
                        (D-04/LEASE-05): a stale lease is reclaimable, not
                        itself a doctor failure. A non-zero cairn-lease.py
                        exit or unparsable JSON degrades to WARN with an
                        explanatory detail rather than crashing the whole
                        doctor run over this one check (same degrade
                        shape as check_phase_corroboration()).
    15. release-versions  cairn-release.py check --json (Plan 19-01,
                        REL-02) run through the CAIRN_RELEASE env seam:
                        the plugin version's carriers must agree —
                        cairn/.claude-plugin/plugin.json's `version`,
                        .claude-plugin/marketplace.json's NESTED
                        `metadata.version`, the first released CHANGELOG
                        heading, and the v<version> git tag — while
                        cairn/capability/capability.json keeps its own
                        axis and need only be valid semver (D-02). A
                        finding -> FAIL (exit 7): a version inconsistency
                        blocks a release, and the marketplace carrier went
                        unnoticed across three of them precisely because
                        nothing failed. APPLIES ONLY when
                        cairn/.claude-plugin/plugin.json exists under the
                        project root — the doctor runs in USERS' repos,
                        which carry none of these manifests, and a naive
                        version of this check would report `missing` and
                        drive every one of them to exit 7. Elsewhere it
                        reports ok with a "not applicable" detail, the
                        same "0 = ok, or not applicable" semantics the
                        exit-code table below already documents. A
                        non-zero-and-not-6 cairn-release.py exit or
                        unparsable JSON degrades to WARN rather than
                        crashing the whole doctor run over this one check
                        (same degrade shape as check_lease_stale()).

--apply-reconciliation N  (ESC-03, Phase 17 Plan 3) the human-invoked,
                    separate command that APPLIES a verified semantic-
                    escalation reconciliation proposal for phase N. Not one
                    of the 16 checks above — a fixer, the same category as
                    --close-completed/--fix-labels/--link-refs, but the only
                    one of the four that always exits on its own rather
                    than falling through to the ordinary report, since its
                    own exit-code contract (below) does not track check
                    pass/fail. Reads .cairn/conflicts.json (written by
                    /cairn:reconcile's own deterministic step, Plan 17-02)
                    and refuses the WHOLE apply, fail-closed, on any of:
                    no proposal for phase N (or its own 'phase' field
                    doesn't match N); phase N's corroboration verdict is no
                    longer "conflict" at apply-time (a real 're-collect',
                    never the proposal's own stale self-claim) — not a
                    failure, nothing to apply; the freshly re-collected
                    evidence_hash no longer matches the proposal's own
                    stored one (the tree moved between proposal and apply,
                    D-04's cache key re-validated); any citation fails a
                    real re-verification run (D-03); any
                    recommended_action.type falls outside the closed
                    {bd_close, bd_reopen, manual_review} vocabulary; or any
                    bd_close/bd_reopen claim's recommended_action.issue
                    names a bd id that carries no phase-N label (the
                    issue-provenance check — correct citations elsewhere in
                    the same proposal never excuse a claim that targets an
                    unrelated issue). Only once every one of those passes
                    does anything print: EVERY claim is enumerated
                    (statement, recommended_action, what will happen —
                    manual_review claims listed as skipped) BEFORE the
                    first bd subprocess call ever runs, then bd_close/
                    bd_reopen claims are applied one at a time; manual_review
                    claims never touch bd. A close/reopen bd itself refuses
                    is reported by id and reason and fails the run — never
                    silent, the same "asked for it and did not get it"
                    discipline check_phase_complete_open's close_failures
                    already applies one level up.

Active milestone is resolved leniently like cairn-gate: STATE.md
frontmatter 'milestone:' first, else the ROADMAP.md milestone marked in
progress, else None (single-milestone / legacy repo — milestone scoping is
then a no-op).

Exit codes:
    0  all checks ok, or ok + warnings (warnings are printed but never
       change the exit code), or doctor NOT APPLICABLE: .planning/ or
       .beads/ absent — the doctor is for wired repos. When exactly one
       side exists the note suggests /cairn:migrate. ALSO:
       --apply-reconciliation's own "phase N is no longer in conflict"
       refusal — nothing left to apply is not a failure.
    2  usage error, or --fix-labels refused (milestone unresolvable), or
       --apply-reconciliation found no proposal for phase N (missing
       .cairn/conflicts.json, or its own 'phase' field doesn't match N).
    5  bd unavailable (not on PATH, or bd list failed).
    7  at least one check FAILED — including --close-completed leaving a
       target unclosed (bd refused it and the fixpoint could not drain it),
       which fails check 5 rather than exiting silently 0, and including a
       "blocks"-severity phase-corroboration conflict (check 11). ALSO:
       --apply-reconciliation refusing a stale proposal, a bad citation, an
       unrecognized recommended_action.type, an issue-provenance mismatch,
       or bd itself refusing a close/reopen it was asked to apply.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BD = 5
EXIT_FAILED = 7

SYMBOL = {"ok": "✓", "warn": "⚠", "fail": "✗"}

SCRIPTS_DIR = Path(__file__).resolve().parent

# Test/override seam for check_phase_corroboration()'s journal_last_moved()
# call (Phase 16, D-01/D-02) — the SAME env var name cairn-lease.py and
# cairn-status.py already use for their own calls into this identical
# script (CONVENTIONS.md's "Environment variable seams" note: CAIRN_*
# prefix, upper case). Default: the sibling cairn-journal.py next to this
# script.
CAIRN_JOURNAL = os.environ.get(
    "CAIRN_JOURNAL", str(SCRIPTS_DIR / "cairn-journal.py"))

# Test/override seam for check_release_versions() (Phase 19, Plan 19-01) —
# the same CAIRN_* convention as CAIRN_JOURNAL above and CAIRN_GBSYNC/
# CAIRN_MAP/CAIRN_GATE elsewhere (CONVENTIONS.md's "Environment variable
# seams" note). Default: the sibling cairn-release.py next to this script.
# The doctor never reimplements the manifest reads; it calls the script that
# owns them.
CAIRN_RELEASE = os.environ.get(
    "CAIRN_RELEASE", str(SCRIPTS_DIR / "cairn-release.py"))

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
PR_NUMBER = re.compile(r"\(#(\d+)\)")

# Labels that legitimately carry no phase-* label (migration parking lots,
# unphased /cairn:quick side-quests, plus the phase-lease bookkeeping issue
# — cairn-lease.py's module docstring explains why it never carries a
# phase-<N> label: it would make the lease look like real phase work to
# this doctor's own phase-complete-open check, phase-corroboration, and
# work.md's done-check).
NO_PHASE_EXEMPT = {"migrated-todo", "backlog", "quick", "lease"}


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
# check 11 — phase-corroboration (CORR-06)
# --------------------------------------------------------------------------- #
CORROBORATION_RECOMMENDATION = {
    ("disk", "bd"): "close the open bd issue(s) if the work is done, or "
                    "run /cairn:work N if it is not",
    ("roadmap", "disk"): "confirm the phase is really done before leaving "
                         "the checkbox ticked, or re-plan it",
    ("state_md", "disk"): "STATE.md's active_phase looks stale — no action "
                          "needed unless you are actually still working "
                          "phase N",
}


def corroboration_recommendation(sources):
    """The first, most-likely fix for a conflict's source pair (D-01: the
    likely-correct option presented first, never a bare list of options)."""
    return CORROBORATION_RECOMMENDATION.get(
        tuple(sources), "see /cairn:doctor for details")


def journal_last_moved(root, phase):
    """cairn-journal.py's `last-moved --phase N --json` for one PHASE, or
    None on ANY failure (missing/broken script, nonzero exit, unparsable
    JSON) — mirroring check_lease_stale()'s shell-out-and-degrade shape
    exactly, one level down: a failure HERE degrades only the calling
    conflict item's enrichment text (see _last_moved_clause()), never
    check_phase_corroboration()'s own status/severity computation (T-16-09
    — that verdict is already fully decided by corroborate()'s own
    "severity" field by the time this is ever called). Shells through the
    CAIRN_JOURNAL env seam (default: the sibling cairn-journal.py), the
    same test/override convention cairn-lease.py and cairn-status.py
    already use for this identical script."""
    try:
        proc = subprocess.run(
            [sys.executable, CAIRN_JOURNAL, "last-moved",
             "--phase", str(phase), "--json", "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None


def _last_moved_clause(last_moved, sources):
    """'<source> last moved <ts>, ...' — one clause per SOURCES key
    (a conflict's own ["disk","bd"]-shaped list), pulled from
    journal_last_moved()'s per-axis {"value":..., "ts":...} dict. A
    source with no prior record (the axis key is None/missing) renders
    the literal phrase "never observed", per JOUR-02's own wording — never
    a blank, never a fabricated timestamp. Returns "" (append nothing)
    when LAST_MOVED itself is None — the journal call failed or was never
    attempted, and the item's EXISTING (pre-Plan-16-05) text is left
    completely untouched in that case."""
    if last_moved is None:
        return ""
    clauses = []
    for source in sources:
        entry = last_moved.get(source)
        if entry:
            clauses.append(f"{source} last moved {entry.get('ts')}")
        else:
            clauses.append(f"{source} last moved never observed")
    return ", ".join(clauses)


def check_phase_corroboration(root, planning_dir):
    """Check 11, id "phase-corroboration" (CORR-06) — reads Plan 13-01's
    phase_model() corroboration verdict for every phase (shells to
    'cairn-status.py --json', the same subprocess pattern check_maps_fresh()
    already uses for cairn-map.py --check) and routes each non-"ok" phase to
    a recommended fix.

    Two severities only (D-09), each carrying corroborate()'s own written
    justification (see cairn-status.py): a "blocks" conflict FAILS the
    doctor run (reuses EXIT_FAILED, no new exit code); an "informs"
    conflict or an "unknown" verdict (bd unreadable for that phase) WARNs
    without failing — D-10's "the ship gate bars only the blockers" posture,
    applied here to doctor's own exit code too. A subprocess/parse failure
    degrades to WARN rather than crashing the whole doctor run over one
    check — corroboration is additive, never a new way for doctor itself to
    become unusable.

    Each "conflict" item ALSO cites when each of that conflict's cited
    sources last moved (Phase 16, JOUR-02 — D-04's "dentro do relatório de
    conflito", the ONLY place this history surfaces by design), via
    journal_last_moved(): one cairn-journal.py `last-moved` call per phase
    that has at least one conflict — cached in last_moved_cache, never
    once per conflict item, even when a phase carries several (e.g. both
    a ["disk","bd"] and a ["roadmap","disk"] conflict at once). This is
    PURELY additive text appended to an item whose status/severity was
    already fully decided above — a broken or missing journal degrades
    that one item's trailing clause to nothing (no clause at all), never
    the item's severity, never this check's own status/exit code.
    """
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "cairn-status.py"), "--json",
         "--planning-dir", str(planning_dir)],
        capture_output=True, text=True, cwd=str(root))
    # 0 (every phase corroborated) and 5 (cairn-status.py's own bd probe
    # failed — a normal, documented degrade that still emits valid JSON
    # with every affected phase's bd axis reading "unknown") are the two
    # exit codes cairn-status.py --json is documented to pair with real
    # output; anything else is unexpected.
    if proc.returncode not in (0, 5):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return {"id": "phase-corroboration", "status": "warn",
                "detail": f"cairn-status.py --json exited "
                          f"{proc.returncode}, corroboration could not be "
                          f"computed: {first}",
                "items": []}
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        return {"id": "phase-corroboration", "status": "warn",
                "detail": "cairn-status.py --json returned invalid JSON, "
                          f"corroboration could not be computed: {e}",
                "items": []}

    items = []
    any_blocks = False
    n_phases = 0
    last_moved_cache = {}
    for p in data.get("phases") or []:
        verdict = p.get("corroboration")
        if verdict in (None, "ok"):
            continue
        n_phases += 1
        n = p.get("number")
        if verdict == "conflict":
            conflicts = p.get("conflicts") or []
            if conflicts and n not in last_moved_cache:
                last_moved_cache[n] = journal_last_moved(root, n)
            last_moved = last_moved_cache.get(n)
            for c in conflicts:
                sev = c.get("severity")
                sources = c.get("sources") or []
                rec = corroboration_recommendation(sources)
                line = f"{n}: {c.get('detail', '')} ({sev}) — {rec}"
                clause = _last_moved_clause(last_moved, sources)
                if clause:
                    line = f"{line} — {clause}"
                items.append(line)
                if sev == "blocks":
                    any_blocks = True
        elif verdict == "unknown":
            items.append(f"{n}: bd could not be read for this phase — "
                         f"re-run once bd is reachable")
    detail = (f"{len(items)} corroboration item(s) across {n_phases} "
              "phase(s)" if items else "every phase's corroboration is ok")
    status = "fail" if any_blocks else ("warn" if items else "ok")
    return {"id": "phase-corroboration", "status": status,
            "detail": detail, "items": items}


# --------------------------------------------------------------------------- #
# check 12 — phase-artifacts (CARD-02, D-04)
# --------------------------------------------------------------------------- #
def check_phase_artifacts(root, planning_dir, disk_reasons):
    """Check 12, id "phase-artifacts" (CARD-02/D-04) — names which artifact
    is missing when a phase's board row would otherwise show only a bare
    dash: a PLAN.md still lacking its own SUMMARY.md in a phase that has
    already reached disk_state "verified", or an NN-VERIFICATION.md with
    no readable 'status:' verdict in its frontmatter. This is the doctor
    half of D-04's narrowing of the phase card's missing-artifact story —
    the board says "not planned" or renders a dash; naming the concrete
    gap by filename is doctor's job, the same division of labor phase 13
    already established for per-source conflict detail (check 11, above).

    The missing-SUMMARY half is gated on disk_state == "verified"
    DELIBERATELY, not on every plans/summary gap
    disk_incomplete_reasons() (already computed once in main() as
    disk_reasons, reused here rather than recomputed — no duplicate
    frontmatter parser in this file) reports. An earlier draft fired on
    ANY phase with an unsummarized plan regardless of state; a
    plan-checker caught that this fires on completely ordinary mid-flight
    work (a phase between waves always has some plans without summaries
    yet) and is noise, not signal. A phase someone ran /cairn:verify on
    despite one of its plans never having been summarized is a genuine
    anomaly; a phase still being worked is not.

    Known, accepted residual gap — written down rather than left as a
    silent trap: a phase stuck at disk_state "executed" (its SUMMARY-less
    plan sits there, nobody ever runs /cairn:verify on it, so it never
    reaches "verified") never fires this check either. The narrowed gate
    trades that false negative for the mid-flight false positive it was
    built to remove; check 5 (phase-complete-open) independently covers
    the ROADMAP-checkbox-complete flavor of the same on-disk gap.

    Shells to 'cairn-status.py --json' exactly the way
    check_phase_corroboration() already does, reading phase_model()'s
    disk_state and verify_status for every phase in the same subprocess
    call. On a returncode outside (0, 5) or a JSON-decode failure, this
    check cannot determine disk_state for its gate, so it degrades to a
    single WARN item rather than falling back to the ungated disk_reasons
    dump — that fallback would silently reintroduce the exact mid-flight
    noise this check's narrowed gate exists to remove.

    Status is ALWAYS "warn" (items present) or "ok" (none), NEVER "fail" —
    a deliberate choice distinct from phase-corroboration's blocks/fail
    behavior, because a missing SUMMARY or an unreadable verdict is a
    record-hygiene gap, not contradictory evidence about what actually
    happened (D-01's "cairn never stops the flow", applied here to
    hygiene rather than correctness findings).
    """
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "cairn-status.py"), "--json",
         "--planning-dir", str(planning_dir)],
        capture_output=True, text=True, cwd=str(root))
    if proc.returncode not in (0, 5):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return {"id": "phase-artifacts", "status": "warn",
                "detail": f"cairn-status.py --json exited "
                          f"{proc.returncode}, phase-artifacts could not "
                          f"run: {first}",
                "items": []}
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        return {"id": "phase-artifacts", "status": "warn",
                "detail": "cairn-status.py --json returned invalid JSON, "
                          f"phase-artifacts could not run: {e}",
                "items": []}

    phases = data.get("phases") or []
    state_by_n = {p.get("number"): p.get("disk_state") for p in phases}
    verify_by_n = {p.get("number"): p.get("verify_status") for p in phases}

    items = []
    # First pass: a PLAN.md missing its SUMMARY.md, but ONLY for phases
    # that have already reached disk_state "verified" — the narrowed gate
    # this check exists to enforce (see docstring above).
    for n, reason in sorted((disk_reasons or {}).items()):
        if state_by_n.get(n) == "verified":
            items.append(f"phase {n}: {reason}")
    # Second pass: a "verified" phase whose NN-VERIFICATION.md carries no
    # readable 'status:' field.
    for n, ds in sorted(state_by_n.items()):
        if ds == "verified" and not verify_by_n.get(n):
            items.append(f"phase {n}: has a VERIFICATION.md but no "
                         f"readable 'status:' field in its frontmatter")

    detail = (f"{len(items)} phase(s) with an unexpected missing/unreadable "
              "artifact" if items
              else "every phase's artifacts are complete and readable")
    return {"id": "phase-artifacts", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


# --------------------------------------------------------------------------- #
# check 13 — external-ref backfill (CORR-08, D-11)
# --------------------------------------------------------------------------- #
def parse_plan_files_modified(path):
    """`files_modified:` paths from a PLAN.md's YAML frontmatter, the same
    lenient flow-list-or-block-list shape parse_plan_frontmatter() already
    reads for `beads:` — a sibling parser, so that function's (status,
    beads) return contract never changes."""
    lines = read_lines(path)
    if not lines or lines[0].strip() != "---":
        return []
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    for i, line in enumerate(body):
        m = re.match(r"^files_modified\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1)
        if "[" in rest:
            inner = rest[rest.index("[") + 1:]
            if "]" in inner:
                inner = inner[:inner.index("]")]
            return [t.strip().strip("'\"") for t in inner.split(",")
                    if t.strip().strip("'\"")]
        files = []
        for cont in body[i + 1:]:
            mi = re.match(r"^\s*-\s*(.+?)\s*$", cont)
            if not mi:
                break
            files.append(mi.group(1).strip("'\""))
        return files
    return []


def phase_files_modified(planning_dir, n):
    """Every files_modified path across phase n's non-superseded plans,
    de-duplicated in first-seen order — the pathspec link_ref_candidate()
    narrows its git query to."""
    files = []
    for num, d in phase_dirs(planning_dir):
        if num != n:
            continue
        for f in sorted(d.glob("*-PLAN.md")):
            status, _ = parse_plan_frontmatter(f)
            if status == "superseded":
                continue
            files.extend(parse_plan_files_modified(f))
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def git_is_shallow(root):
    """True when root is a shallow git clone — verified live (STACK.md) to
    make -S/-G/--grep results silently WRONG at the boundary commit, not
    merely incomplete (D-08); check_external_ref must never trust a git
    match from one."""
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-shallow-repository"],
        capture_output=True, text=True)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def closed_window(closed_at, pad_days=2):
    """(since, until) ISO8601 strings +/-pad_days around a bd closed_at
    timestamp, or (None, None) when it is missing/unparsable."""
    if not closed_at:
        return None, None
    s = str(closed_at).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None, None
    delta = timedelta(days=pad_days)
    return (dt - delta).isoformat(), (dt + delta).isoformat()


def link_ref_candidate(root, planning_dir, iss):
    """The single unambiguous PR number for a closed issue, or None.

    Resolves the issue's phase from its phase-<N> label(s) (the lowest
    numbered one when it carries several), narrows a 'git log' query to
    that phase's files_modified (falling back to the phase directory path
    when no files_modified is known) within +/-2 days of the issue's
    closed_at, and scans matching commit subjects for a '(#N)' token.
    Exactly one distinct PR number among the matches is the candidate;
    zero or multiple distinct numbers is never a candidate — this never
    guesses (T-13-07: a crafted '(#N)' misattributing a PR is bounded to
    'nothing written', never a wrong link silently accepted).
    """
    nums = phase_nums(iss)
    if not nums:
        return None
    n = min(nums)
    since, until = closed_window(iss.get("closed_at"))
    if since is None:
        return None
    pathspec = phase_files_modified(planning_dir, n)
    if not pathspec:
        d = dict(phase_dirs(planning_dir)).get(n)
        if d is None:
            return None
        pathspec = [str(d.relative_to(root))]
    proc = subprocess.run(
        ["git", "-C", str(root), "log", f"--since={since}",
         f"--until={until}", "--format=%H|%s", "--", *pathspec],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    prs = set()
    for line in proc.stdout.splitlines():
        if "|" not in line:
            continue
        subject = line.split("|", 1)[1]
        m = PR_NUMBER.search(subject)
        if m:
            prs.add(int(m.group(1)))
    if len(prs) == 1:
        return next(iter(prs))
    return None


def check_external_ref(root, planning_dir, issues, do_write):
    """Check 12, id "external-ref" (CORR-08, D-11) — backfills the
    bd-issue-to-PR linkage on already-closed issues from this repo's own
    git history. See link_ref_candidate() for the exact match rule.

    Read-only by default: reports each unambiguous candidate as
    '<id> -> gh-N', writes nothing. do_write (--link-refs) writes 'bd
    update <id> --external-ref gh-N' for each candidate and itemizes what
    it linked — naturally idempotent, since an issue that already carries
    an external_ref is excluded from `lacking` up front, so a second run
    (a fresh process reading fresh bd state) has nothing left to
    (re)write.

    D-08: a shallow clone's git match can be silently WRONG at the
    boundary commit, not merely incomplete (verified live in STACK.md) —
    checked once before any query and reported as a single item rather
    than trusted.

    WARN only when an unambiguous, actionable candidate is waiting — never
    merely because closed issues predate the --external-ref convention.
    Per STACK.md, that is the expected, unremarkable state of this
    repo's entire history today; flagging it unconditionally would be
    exactly the vacuous-check failure mode this milestone exists to avoid.
    """
    if git_is_shallow(root):
        return {"id": "external-ref", "status": "warn",
                "detail": "shallow clone — git history cannot be trusted "
                          "for --link-refs (D-08); run against a full "
                          "clone (git fetch --unshallow)",
                "items": ["shallow clone: --link-refs skipped entirely "
                          "this run"]}

    closed = [i for i in issues if i.get("status") == "closed"]
    lacking = [i for i in closed
               if not str(i.get("external_ref") or "").strip()]
    candidates = []
    for iss in lacking:
        pr = link_ref_candidate(root, planning_dir, iss)
        if pr is not None:
            candidates.append((iss.get("id"), pr))

    linked = []
    if do_write:
        for iid, pr in candidates:
            proc = subprocess.run(
                ["bd", "-C", str(root), "update", iid, "--external-ref",
                 f"gh-{pr}"], capture_output=True, text=True)
            if proc.returncode == 0:
                linked.append(iid)

    remaining_lacking = len(lacking) - len(linked)
    remaining_candidates = len(candidates) - len(linked)
    items = [f"linked {iid} -> gh-{pr}" if iid in linked
             else f"{iid} -> gh-{pr}" for iid, pr in candidates]
    detail = (f"{remaining_lacking} closed issue(s) lack an external ref, "
              f"{remaining_candidates} have an unambiguous git match "
              f"(run --link-refs to backfill)")
    if linked:
        detail += f" — linked {len(linked)} via --link-refs"
    return {"id": "external-ref",
            "status": "warn" if remaining_candidates else "ok",
            "detail": detail, "items": items}


# --------------------------------------------------------------------------- #
# check 13 — lease-stale (LEASE-05)
# --------------------------------------------------------------------------- #
def check_lease_stale(root):
    """Check 13, id "lease-stale" (LEASE-05) — a stale phase lease reported
    with the same WARN-only discipline check 8 (claims-stale) already
    applies to a stale issue claim, one level up: shells to
    'cairn-lease.py status --all --json' (Plan 15-01), the same
    shell-out-to-a-sibling-script pattern check_maps_fresh() already uses
    for cairn-map.py --check and check_phase_corroboration() uses for
    cairn-status.py --json — no TTL/staleness math is re-derived here.

    Itemizes every phase whose lease is currently held AND stale (past the
    4h TTL cairn-lease.py enforces) by phase, holder, actor, acquired_at,
    heartbeat_at, and the reclaim path. Never FAILS: a stale lease is
    reclaimable — the next acquire takes it automatically, or a human runs
    'cairn-lease.sh release N' — exactly the "reclaimable, not a bug" case
    D-03/LEASE-04 describe, matching claims-stale's own never-fails
    posture exactly.

    A non-zero cairn-lease.py exit or unparsable JSON degrades to WARN
    with an explanatory detail rather than crashing the whole doctor run
    over this one check (same degrade shape as
    check_phase_corroboration()).
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "cairn-lease.py"), "status",
             "--all", "--json", "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"id": "lease-stale", "status": "warn",
                "detail": f"could not run cairn-lease.py: {exc}",
                "items": []}
    if proc.returncode != 0:
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return {"id": "lease-stale", "status": "warn",
                "detail": f"cairn-lease.py status --all exited "
                          f"{proc.returncode}, lease staleness could not "
                          f"be computed: {first}",
                "items": []}
    try:
        entries = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        return {"id": "lease-stale", "status": "warn",
                "detail": "cairn-lease.py status --all returned invalid "
                          f"JSON, lease staleness could not be computed: "
                          f"{e}",
                "items": []}
    if not isinstance(entries, list):
        entries = []

    items = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("held") and entry.get("stale"):
            phase = entry.get("phase")
            items.append(
                f"phase {phase}: held by {entry.get('holder')} (actor: "
                f"{entry.get('actor')}) since {entry.get('acquired_at')}, "
                f"last renewed {entry.get('heartbeat_at')} — reclaimable "
                f"— the next /cairn:work {phase} takes it automatically, "
                f"or run cairn-lease.sh release {phase} to clear it now")
    detail = (f"{len(items)} stale phase lease(s)" if items
              else "no stale phase leases")
    return {"id": "lease-stale", "status": "warn" if items else "ok",
            "detail": detail, "items": items}


# --------------------------------------------------------------------------- #
# check 15 — release-versions (REL-02)
# --------------------------------------------------------------------------- #
RELEASE_PLUGIN_MANIFEST = Path("cairn") / ".claude-plugin" / "plugin.json"


def check_release_versions(root):
    """Check 15, id "release-versions" (REL-02) — the plugin version's
    carriers must agree, verified by shelling out to cairn-release.py
    through the CAIRN_RELEASE env seam, the same
    shell-out-to-a-sibling-script pattern check_maps_fresh() uses for
    cairn-map.py --check and check_lease_stale() uses for cairn-lease.py.
    No manifest reading is re-derived here: cairn-release.py owns the three
    (different!) JSON key paths and the CHANGELOG heading, and this check
    only routes its verdict.

    A command nobody remembers to run would not have caught the third
    carrier. That is why this lives in the doctor at all:
    .claude-plugin/marketplace.json carries the version at
    `metadata.version` and drifted unnoticed across three releases while
    every human check said "the two files match".

    APPLICABILITY — the trap this check has to dodge. The doctor runs in
    USERS' repos, which have a .planning/ and a .beads/ but none of cairn's
    own plugin manifests. A naive version of this check would report
    `missing: cairn/.claude-plugin/plugin.json does not exist` and drive
    every user's doctor to exit 7 over a file that has no business being
    there. So it applies ONLY when cairn/.claude-plugin/plugin.json exists
    under the project root; everywhere else it reports "ok" with a "not
    applicable" detail — the same "0 = ok, or not applicable" semantics the
    module docstring's exit-code table already documents for the doctor as
    a whole.

    Inside THIS repo a divergence is "fail", not "warn": it is an
    inconsistency that blocks a release, and only "fail" reaches exit 7.
    An unexpected cairn-release.py exit (anything but its documented 0/6)
    or unparsable JSON degrades to WARN rather than crashing the whole
    doctor run over this one check.
    """
    if not (root / RELEASE_PLUGIN_MANIFEST).is_file():
        return {"id": "release-versions", "status": "ok",
                "detail": f"not applicable — no {RELEASE_PLUGIN_MANIFEST} "
                          "under this root (the version carriers are "
                          "cairn's own, not a wired repo's)",
                "items": []}
    try:
        proc = subprocess.run(
            [sys.executable, CAIRN_RELEASE, "check", "--json",
             "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"id": "release-versions", "status": "warn",
                "detail": f"could not run cairn-release.py: {exc}",
                "items": []}
    # 0 (every carrier agrees) and 6 (findings) are the two exit codes
    # cairn-release.py check --json is documented to pair with real output;
    # anything else is unexpected and degrades rather than failing.
    if proc.returncode not in (0, 6):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        return {"id": "release-versions", "status": "warn",
                "detail": f"cairn-release.py check exited "
                          f"{proc.returncode}, version consistency could "
                          f"not be computed: {first}",
                "items": []}
    try:
        report = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        return {"id": "release-versions", "status": "warn",
                "detail": "cairn-release.py check returned invalid JSON, "
                          f"version consistency could not be computed: {e}",
                "items": []}

    findings = report.get("findings") or []
    if findings:
        return {"id": "release-versions", "status": "fail",
                "detail": f"{len(findings)} version carrier finding(s) — "
                          "run cairn-release.sh check",
                "items": list(findings)}
    version = report.get("version")
    tag = next((c for c in report.get("carriers") or []
                if c.get("name") == "tag"), {})
    tag_note = {"ok": f", git tag {tag.get('key')} present",
                "pending": f", git tag {tag.get('key')} pending"}.get(
                    tag.get("status"), "")
    return {"id": "release-versions", "status": "ok",
            "detail": f"every version carrier agrees on {version}"
                      f"{tag_note}",
            "items": []}


# --------------------------------------------------------------------------- #
# --apply-reconciliation (ESC-03, Phase 17 Plan 3) — the human-invoked,
# separate apply command for a verified semantic-escalation reconciliation
# proposal. See the module docstring's own --apply-reconciliation entry for
# the full refusal-path rationale.
# --------------------------------------------------------------------------- #
RECONCILE_SCRIPT = SCRIPTS_DIR / "cairn-reconcile.py"
RECONCILE_ACTION_VOCAB = ("bd_close", "bd_reopen", "manual_review")


def run_apply_reconciliation(root, n, issues, as_json):
    """--apply-reconciliation N — reads .cairn/conflicts.json (written by
    /cairn:reconcile's own deterministic step, Plan 17-02), re-verifies it
    is STILL trustworthy at apply-time (never trusting anything about the
    proposal's own self-description), enumerates every change it is about
    to make, and only then executes the closed bd_close/bd_reopen action
    vocabulary. This is the ONLY place in the whole phase 17 pipeline where
    a real bd write happens, and it always runs because a human explicitly
    asked it to — never automatically.

    Fail-closed refusal paths, each refusing the WHOLE apply (never a
    per-claim partial result) — a proposal is only ever as trustworthy as
    its LAST verification, and time may have passed since /cairn:reconcile
    wrote it:
      1. no .cairn/conflicts.json for phase N, or its own 'phase' field
         does not match N -> EXIT_USAGE, nothing written.
      2. phase N's corroboration verdict is no longer "conflict", re-read
         via a REAL 'cairn-reconcile.py collect N --json' run at
         apply-time -> EXIT_OK, nothing to apply, not a failure.
      3. the freshly re-collected evidence_hash no longer matches the
         proposal's own stored one (D-04's cache key re-validated) ->
         EXIT_FAILED.
      4. any citation fails a real 'cairn-reconcile.py verify N' run
         (D-03) -> EXIT_FAILED.
      5. any recommended_action.type falls outside the closed
         {bd_close, bd_reopen, manual_review} vocabulary -> EXIT_FAILED,
         checked over EVERY claim in one pre-flight pass, before anything
         is even enumerated.
      6. any bd_close/bd_reopen claim's recommended_action.issue names a bd
         id carrying no phase-N label (issue provenance — correct
         citations elsewhere in the same proposal never excuse a claim
         that targets an unrelated issue) -> EXIT_FAILED, checked in the
         SAME pre-flight pass as 5, also before any enumeration prints.

    Only once every one of those passes does anything print: EVERY claim
    is enumerated (statement, recommended_action, what will happen —
    manual_review claims listed as "skipped") BEFORE the first bd
    subprocess call ever runs — the operator sees the full plan while it
    can still be stopped. bd_close/bd_reopen claims are then applied one
    at a time; a close/reopen bd itself refuses is reported by id and
    reason and fails the run (EXIT_FAILED) — never silent, the same
    "asked for it and did not get it" discipline
    check_phase_complete_open's close_failures already applies one level
    up.
    """
    proposal_path = root / ".cairn" / "conflicts.json"
    proposal = None
    if proposal_path.is_file():
        try:
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            proposal = None
    if not isinstance(proposal, dict) or proposal.get("phase") != n:
        die(f"no proposal for phase {n} — run /cairn:reconcile {n} first",
            EXIT_USAGE)

    # Step 2 (freshness, re-validating D-04's cache key at apply-time): a
    # REAL, current 'collect' run — the tree may have moved between
    # proposal generation and this invocation, so the proposal's own
    # evidence_hash is never trusted on its own say-so.
    proc = subprocess.run(
        [sys.executable, str(RECONCILE_SCRIPT), "collect", str(n), "--json",
         "--project-dir", str(root)],
        capture_output=True, text=True, cwd=str(root))
    if proc.returncode == 3:  # cairn-reconcile.py's EXIT_NOT_CONFLICTED
        msg = f"phase {n} is no longer in conflict; this proposal is moot"
        if as_json:
            print(json.dumps({"phase": n, "applied": False,
                              "reason": "not_conflicted", "detail": msg}))
        else:
            print(f"[cairn-doctor] {msg}")
        sys.exit(EXIT_OK)
    if proc.returncode != 0:
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        die(f"could not re-collect evidence for phase {n}: {first}",
            EXIT_FAILED)
    try:
        fresh = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        die(f"could not re-collect evidence for phase {n}: cairn-reconcile "
            f"collect returned invalid JSON: {e}", EXIT_FAILED)
    if fresh.get("evidence_hash") != proposal.get("evidence_hash"):
        die("proposal is stale (evidence has changed since it was "
            f"generated) — re-run /cairn:reconcile {n}", EXIT_FAILED)

    # Step 3 (citation re-check, D-03): a single bad citation invalidates
    # the WHOLE proposal, never per-claim partial credit.
    vproc = subprocess.run(
        [sys.executable, str(RECONCILE_SCRIPT), "verify", str(n),
         "--project-dir", str(root)],
        capture_output=True, text=True, cwd=str(root))
    if vproc.returncode != 0:
        text = (vproc.stdout.strip() or vproc.stderr.strip()
                or "(no output)")
        die(f"proposal failed citation verification: {text}", EXIT_FAILED)

    claims = proposal.get("claims") or []

    # Step 4 (pre-flight, BEFORE any enumeration is even printed): the
    # closed action vocabulary AND issue provenance, checked over EVERY
    # claim. Either failure refuses the ENTIRE apply, fail-closed, the same
    # posture as a stale hash or a bad citation above — a rejected
    # proposal never gets as far as looking plausible on screen.
    phase_n_ids = {iss.get("id") for iss in issues if n in phase_nums(iss)}
    for claim in claims:
        action = claim.get("recommended_action") or {}
        atype = action.get("type")
        if atype not in RECONCILE_ACTION_VOCAB:
            die("proposal names an unrecognized recommended_action.type "
                f"{atype!r} — refusing the whole apply (closed vocabulary: "
                "bd_close, bd_reopen, manual_review)", EXIT_FAILED)
        if atype in ("bd_close", "bd_reopen"):
            iid = action.get("issue")
            if iid not in phase_n_ids:
                die(f"proposal's claim targets {iid!r}, which carries no "
                    f"phase-{n} label — refusing the whole apply "
                    "(issue-provenance check: correct citations elsewhere "
                    "in the proposal do not excuse a claim targeting an "
                    "unrelated issue)", EXIT_FAILED)

    # Step 5 (enumerate): the FULL plan, printed before anything executes.
    header = (f"[cairn-doctor] apply-reconciliation: phase {n} — "
              f"{len(claims)} claim(s)")
    enum_lines = [header]
    for i, claim in enumerate(claims, 1):
        action = claim.get("recommended_action") or {}
        atype = action.get("type")
        stmt = claim.get("statement", "")
        if atype == "manual_review":
            what = "skipped (manual review, no automated action)"
        elif atype == "bd_close":
            what = f"will close {action.get('issue')}"
        else:
            what = f"will reopen {action.get('issue')}"
        enum_lines.append(f"  {i}. {stmt} -> {what}")
    if not as_json:
        for line in enum_lines:
            print(line)

    # Step 6 (apply): only bd_close/bd_reopen ever touch bd — manual_review
    # was already enumerated above and is never executed.
    results = []
    any_refused = False
    for claim in claims:
        action = claim.get("recommended_action") or {}
        atype = action.get("type")
        iid = action.get("issue")
        stmt = claim.get("statement", "")
        if atype == "manual_review":
            results.append({"statement": stmt, "issue": iid, "type": atype,
                            "outcome": "skipped-manual-review"})
            continue
        if atype == "bd_close":
            reason = (action.get("reason") or action.get("note")
                      or f"cairn-doctor: apply-reconciliation phase {n}")
            cmd = ["bd", "-C", str(root), "close", iid, "--reason", reason]
        else:  # bd_reopen
            cmd = ["bd", "-C", str(root), "update", iid, "--status", "open",
                   "--assignee", ""]
        bproc = subprocess.run(cmd, capture_output=True, text=True)
        if bproc.returncode == 0:
            results.append({"statement": stmt, "issue": iid, "type": atype,
                            "outcome": "applied"})
            verb = "closed" if atype == "bd_close" else "reopened"
            if not as_json:
                print(f"[cairn-doctor] {verb} {iid} — applied via "
                      "--apply-reconciliation")
        else:
            any_refused = True
            why = (bproc.stderr.strip() or bproc.stdout.strip()
                   or f"bd exited {bproc.returncode}")
            results.append({"statement": stmt, "issue": iid, "type": atype,
                            "outcome": "refused-by-bd", "detail": why})
            if not as_json:
                print(f"[cairn-doctor] {iid}: {atype} refused by bd — {why}")

    n_applied = sum(1 for r in results if r["outcome"] == "applied")
    n_skipped = sum(1 for r in results
                    if r["outcome"] == "skipped-manual-review")
    n_refused = sum(1 for r in results if r["outcome"] == "refused-by-bd")
    if as_json:
        print(json.dumps({"phase": n, "applied": not any_refused,
                          "claims": len(claims), "applied_n": n_applied,
                          "skipped_n": n_skipped, "refused_n": n_refused,
                          "results": results}))
    else:
        print(f"[cairn-doctor] apply-reconciliation phase {n}: "
              f"{n_applied} applied, {n_skipped} skipped (manual review), "
              f"{n_refused} refused by bd")
    sys.exit(EXIT_FAILED if any_refused else EXIT_OK)


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
    parser.add_argument("--link-refs", action="store_true",
                        help="backfill closed issues lacking bd's "
                             "external_ref field from an unambiguous git "
                             "match (bd update --external-ref), read-only "
                             "without this flag")
    parser.add_argument("--apply-reconciliation", metavar="N", type=int,
                        default=None,
                        help="apply a verified semantic-escalation "
                             "reconciliation proposal for phase N "
                             "(.cairn/conflicts.json): re-verifies "
                             "freshness and citations, enumerates every "
                             "change before making any of them, then "
                             "executes only the closed bd_close/bd_reopen "
                             "vocabulary — refuses the whole apply on any "
                             "staleness, bad citation, unrecognized action "
                             "type, or an issue lacking a phase-N label")
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

    # --apply-reconciliation (ESC-03) is mutually orthogonal to the two
    # fixers above (no shared state) — simple sequencing after them is
    # enough. Unlike them it is a distinct, human-invoked command whose own
    # exit-code contract does not track check pass/fail, so it always exits
    # on its own rather than falling through to the report below.
    if args.apply_reconciliation is not None:
        run_apply_reconciliation(root, args.apply_reconciliation, issues,
                                 args.json)

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
        check_phase_corroboration(root, planning_dir),
        check_phase_artifacts(root, planning_dir, disk_reasons),
        check_external_ref(root, planning_dir, issues, args.link_refs),
        check_lease_stale(root),
        check_release_versions(root),
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
