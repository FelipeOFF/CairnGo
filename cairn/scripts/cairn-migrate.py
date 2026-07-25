#!/usr/bin/env python3
"""cairn-migrate — deterministic migration engine for wiring GSD (.planning/)
and beads (.beads/) together. The /cairn:migrate prose command mediates user
confirmations; this script is the deterministic core with a plan-file
handshake.

Subcommands:

  detect [--project-dir D] [--json]
      Classify the repo. Prints the state letter on the first stdout line:
        A  .planning present, .beads absent        (GSD-only backfill)
        B  .beads present, .planning absent        (beads-only bootstrap)
        C  both present, unwired (no *-BEADS-MAP.md anywhere AND no 'beads:'
           frontmatter in any *-PLAN.md)           (wire-up/reconcile)
        W  both present and already wired          (nothing to migrate)
        D  neither present                          (greenfield)
      Exit 0 always.

  plan [--mode A|B|C] [--milestone M] [--force] [--project-dir D]
      Read-only inventory pass. Writes .cairn/migrate-plan.json and prints a
      human dry-run summary of every create/close/label/file-write it would
      do, grouped by kind. Mode defaults to the detected state.
      Exit 0 plan written, 2 usage or wrong mode for the repo state,
      5 bd unavailable (only when the mode needs bd at plan time: B and C
      always; A only when .beads/ already exists, for the dedup query).

  apply [--plan FILE] [--yes] [--project-dir D]
      Execute the plan, journaling each completed step id to
      .cairn/migrate-state.json (JSONL: one header line with the plan's
      created_at, then one line per completed step). Re-runs skip completed
      steps — RESUME semantics — and every write handler is additionally
      idempotent against live bd state, so a half-truncated journal never
      produces duplicates. Steps with status pending_confirmation are
      SKIPPED unless their params carry "confirmed": true (the prose command
      flips them after asking the user).
      Exit 0 done, 2 no/invalid plan (or user abort), 5 bd unavailable,
      8 partial failure (the journal says where it stopped).

Bulk creation note (empirically verified against bd 1.1.0): `bd create
--graph` exists, but its node `metadata` field is a map[string]string — a
nested {"gsd": {...}} object is stored as a JSON *string*, which breaks the
cairn convention that `metadata.gsd` is a queryable dict (the dedup key and
cairn-map both read metadata.gsd.req). Sequential `bd create --metadata`
stores a proper nested dict, so this engine ships SEQUENTIAL creates:
correctness beats one-transaction elegance.

Plan file shape (version 1):
  {"version": 1, "mode": "A", "milestone": "v1.0",
   "created_at": "2026-07-24T12:00:00Z", "project_dir": "...",
   "steps": [{"id": "s001", "kind": "...", "params": {...},
              "status": "pending" | "pending_confirmation"}],
   "orphans": [{"id": "...", "title": "...", "action": "report"}],
   "warnings": [...], "notes": [...]}

Orphan actions (mode C, editable per-orphan in the plan file):
  "report" (default, no-op — they surface in the map's Gaps section),
  "attach-to-phase-<N>" (pair labels + gsd.phase stamp),
  "label-backlog" (bd label add backlog).

Safety: apply never runs /gsd:new-project and never touches PROJECT.md or
CONTEXT.md; the only .planning/ writes are the ones the plan declares (maps,
frontmatter appends, and in mode B the generated REQUIREMENTS/ROADMAP/STATE
docs + MILESTONES.md). If .cairn/sync.json exists, apply ends with a
reminder to run /cairn:sync-pull.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_BD = 5
EXIT_PARTIAL = 8

SCRIPT_DIR = Path(__file__).resolve().parent

REQ_ID = re.compile(r"\b[A-Za-z][A-Za-z0-9]*-\d+\b")
VERSION_TOKEN = re.compile(r"\bv\d+(?:\.\d+)*\b")
CHECKBOX_PHASE = re.compile(
    r"^\s*-\s*\[([ xX])\]\s*\*\*Phase\s+0*(\d+)\s*:\s*([^*]+?)\*\*")
TABLE_PHASE = re.compile(
    r"^\s*\|\s*0*(\d+)[.)\s][^|]*\|.*\|\s*Complete\s*\|", re.IGNORECASE)
HEAD_PHASE = re.compile(r"^#{1,6}\s+Phase\s+0*(\d+)\s*:\s*(.*?)\s*$")
ANY_HEAD = re.compile(r"^#{1,6}\s")
REQ_ITEM = re.compile(
    r"^\s*-\s*(?:\[[ xX]\]\s*)?\*\*([A-Za-z][A-Za-z0-9]*-\d+)\*\*\s*:?\s*(.*)$")
PHASE_DIR = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")
ATTACH_ACTION = re.compile(r"^attach-to-phase-(\d+)$")

STATE_DESCRIPTIONS = {
    "A": ".planning present, .beads absent -> GSD-only backfill (plan --mode A)",
    "B": ".beads present, .planning absent -> beads-only bootstrap (plan --mode B)",
    "C": "both present, unwired -> wire-up/reconcile (plan --mode C)",
    "W": "both present and already wired -> nothing to migrate",
    "D": "neither present -> greenfield (/gsd:new-project, then /cairn:init)",
}


def die(msg, code):
    print(f"[cairn-migrate] error: {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg):
    print(f"[cairn-migrate] warning: {msg}", file=sys.stderr)


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# bd plumbing (gbsync/relabel pattern: bd -C <project-dir> ...)
# --------------------------------------------------------------------------- #
def bd_available():
    return shutil.which("bd") is not None


def run_bd(args, project_dir):
    cmd = ["bd", "-C", str(project_dir)] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        die("'bd' not found on PATH", EXIT_NO_BD)
    if proc.returncode != 0:
        return None, (proc.stderr.strip() or proc.stdout.strip()
                      or f"exit {proc.returncode}")
    return proc.stdout, None


def list_issues(project_dir):
    out, err = run_bd(["list", "--all", "-n", "0", "--json"], project_dir)
    if err:
        die(f"bd list failed: {err}", EXIT_NO_BD)
    try:
        data = json.loads(out) if out.strip() else []
    except json.JSONDecodeError as e:
        die(f"bd list returned invalid JSON: {e}", EXIT_NO_BD)
    if data is None:
        data = []
    if not isinstance(data, list):
        data = data.get("issues", [])
    for issue in data:
        issue["labels"] = issue.get("labels") or []
    return sorted(data, key=lambda i: i.get("id", ""))


def issue_gsd(issue):
    """The metadata.gsd dict of a bd issue, tolerating string encodings."""
    md = issue.get("metadata")
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except json.JSONDecodeError:
            md = None
    gsd = md.get("gsd") if isinstance(md, dict) else None
    if isinstance(gsd, str):
        try:
            gsd = json.loads(gsd)
        except json.JSONDecodeError:
            gsd = None
    return gsd if isinstance(gsd, dict) else {}


def fetch_metadata(bd_id, project_dir):
    out, err = run_bd(["show", bd_id, "--json"], project_dir)
    if err:
        return None, err
    data = json.loads(out)
    issue = data[0] if isinstance(data, list) else data
    meta = issue.get("metadata")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}
    return (meta if isinstance(meta, dict) else {}), None


def merge_gsd(bd_id, gsd_updates, project_dir):
    """Deep-merge keys into metadata.gsd (bd update --metadata REPLACES each
    provided top-level key wholesale, so read-modify-write — same approach
    as cairn-relabel)."""
    meta, err = fetch_metadata(bd_id, project_dir)
    if err:
        return f"bd show: {err}"
    gsd = meta.get("gsd")
    if not isinstance(gsd, dict):
        gsd = {}
    gsd.update(gsd_updates)
    meta["gsd"] = gsd
    _, err = run_bd(["update", bd_id, "--metadata", json.dumps(meta)],
                    project_dir)
    return f"bd update: {err}" if err else None


# --------------------------------------------------------------------------- #
# .planning parsers (lenient — same spirit as cairn-gate / cairn-map)
# --------------------------------------------------------------------------- #
def read_lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def frontmatter(path):
    """Lenient top-level YAML-ish frontmatter: {key: raw string value}."""
    lines = read_lines(path)
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def parse_inline_list(raw):
    """Tokens of an inline YAML list like '[a, b]  # comment'."""
    raw = raw.split("#", 1)[0].strip()
    raw = raw.strip("[]")
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


def parse_roadmap(planning_dir):
    """{n: {name, completed, requirements: [CAT-NN], depends_on: [int]}}."""
    phases = {}

    def ensure(n):
        return phases.setdefault(
            n, {"name": None, "completed": False,
                "requirements": [], "depends_on": []})

    current = None
    for line in read_lines(planning_dir / "ROADMAP.md"):
        m = CHECKBOX_PHASE.match(line)
        if m:
            ph = ensure(int(m.group(2)))
            if ph["name"] is None:
                ph["name"] = m.group(3).strip()
            if m.group(1).lower() == "x":
                ph["completed"] = True
            continue
        m = TABLE_PHASE.match(line)
        if m:
            ensure(int(m.group(1)))["completed"] = True
            continue
        m = HEAD_PHASE.match(line)
        if m:
            current = int(m.group(1))
            ph = ensure(current)
            name = m.group(2).strip().rstrip(":").strip()
            if name:
                ph["name"] = name
            continue
        if ANY_HEAD.match(line):
            current = None
            continue
        if current is not None:
            stripped = line.strip()
            m = re.match(r"^\*\*Requirements\*\*\s*:(.*)$", stripped)
            if m:
                phases[current]["requirements"] = REQ_ID.findall(m.group(1))
                continue
            m = re.match(r"^\*\*Depends on\*\*\s*:(.*)$", stripped)
            if m:
                phases[current]["depends_on"] = sorted(
                    {int(x) for x in
                     re.findall(r"Phase\s+0*(\d+)", m.group(1))})
    for n, ph in phases.items():
        if ph["name"] is None:
            ph["name"] = f"Phase {n}"
    return phases


def parse_requirements_md(path):
    """{CAT-NN: {"title": str, "body": str}} — body runs until next item or
    heading."""
    items = {}
    current = None
    body = []

    def flush():
        nonlocal current, body
        if current is not None:
            text = "\n".join(body).strip()
            items[current[0]] = {"title": current[1], "body": text}
        current, body = None, []

    for line in read_lines(path):
        m = REQ_ITEM.match(line)
        if m:
            flush()
            current = (m.group(1), m.group(2).strip() or m.group(1))
            continue
        if ANY_HEAD.match(line):
            flush()
            continue
        if current is not None:
            body.append(line.rstrip())
    flush()
    return items


def state_active_phase(planning_dir):
    val = frontmatter(planning_dir / "STATE.md").get("active_phase", "")
    m = re.search(r"\d+", val)
    return int(m.group(0)) if m else None


def state_milestone(planning_dir):
    val = frontmatter(planning_dir / "STATE.md").get("milestone", "")
    val = val.split("#", 1)[0].strip().strip("'\"").strip()
    return val or None


def roadmap_milestone(planning_dir):
    """Milestone marked in progress in ROADMAP.md (same lenient rule as
    cairn-gate: a 🚧 / '(in progress)' line carrying a vN[.N] token)."""
    for line in read_lines(planning_dir / "ROADMAP.md"):
        if "🚧" in line or re.search(r"\(in progress\)", line, re.IGNORECASE):
            m = VERSION_TOKEN.search(line)
            if m:
                return m.group(0)
    return None


def resolve_milestone(opt, planning_dir, mode):
    if opt:
        return opt
    if mode in ("A", "C") and planning_dir.is_dir():
        found = state_milestone(planning_dir) or roadmap_milestone(planning_dir)
        if found:
            return found
    warn("could not infer the milestone (no STATE.md 'milestone:' key, no "
         "in-progress ROADMAP milestone header) — defaulting to 'v1.0'; "
         "pass --milestone to override")
    return "v1.0"


def phase_dirs(planning_dir):
    """{n: Path} for every .planning/phases/<prefix?>NN-<slug> directory."""
    out = {}
    phases = planning_dir / "phases"
    if not phases.is_dir():
        return out
    for d in sorted(phases.iterdir(), key=lambda p: p.name):
        if not d.is_dir():
            continue
        m = PHASE_DIR.match(d.name)
        if m:
            out.setdefault(int(m.group(1)), d)
    return out


def plan_files(phase_dir):
    """Sorted *-PLAN.md paths in a phase dir."""
    return sorted(phase_dir.glob("*-PLAN.md"))


def phase_is_complete(phase_dir):
    """Every non-superseded PLAN has a SUMMARY + a VERIFICATION with
    status: passed. Requires at least one non-superseded plan."""
    if phase_dir is None:
        return False
    plans = [p for p in plan_files(phase_dir)
             if frontmatter(p).get("status", "") != "superseded"]
    if not plans:
        return False
    for p in plans:
        summary = p.with_name(p.name.replace("-PLAN.md", "-SUMMARY.md"))
        if not summary.is_file():
            return False
    return any(frontmatter(v).get("status", "") == "passed"
               for v in phase_dir.glob("*-VERIFICATION.md"))


def pending_todos(planning_dir):
    """[(title, description, filename)] from .planning/todos/pending/*."""
    todos = []
    pend = planning_dir / "todos" / "pending"
    if not pend.is_dir():
        return todos
    for f in sorted(pend.iterdir(), key=lambda p: p.name):
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        title = None
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("#"):
                title = s.lstrip("#").strip()
                break
        if not title:
            title = f.stem.replace("-", " ").replace("_", " ").strip() or f.name
        todos.append((title, text.strip(), f.name))
    return todos


# --------------------------------------------------------------------------- #
# detect
# --------------------------------------------------------------------------- #
def wired_signals(planning_dir):
    maps = [p for p in planning_dir.rglob("*-BEADS-MAP.md")]
    plans_with_beads = [p for p in planning_dir.rglob("*-PLAN.md")
                        if "beads" in frontmatter(p)]
    return maps, plans_with_beads


def classify(project_dir):
    planning = project_dir / ".planning"
    beads = project_dir / ".beads"
    has_p, has_b = planning.is_dir(), beads.is_dir()
    info = {"planning": has_p, "beads": has_b, "wired": None,
            "maps_found": 0, "plans_with_beads": 0}
    if has_p and not has_b:
        info["state"] = "A"
    elif has_b and not has_p:
        info["state"] = "B"
    elif not has_p and not has_b:
        info["state"] = "D"
    else:
        maps, wired_plans = wired_signals(planning)
        info["maps_found"] = len(maps)
        info["plans_with_beads"] = len(wired_plans)
        info["wired"] = bool(maps or wired_plans)
        info["state"] = "W" if info["wired"] else "C"
    return info


def cmd_detect(args):
    project = Path(args.project_dir or
                   os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    info = classify(project)
    if args.json:
        print(json.dumps(info))
    else:
        print(info["state"])
        print(STATE_DESCRIPTIONS[info["state"]])
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# issue indexes (dedup keys)
# --------------------------------------------------------------------------- #
class IssueIndex:
    def __init__(self, issues, milestone):
        self.milestone = milestone
        self.by_id = {}
        self.by_req = {}
        self.epic_by_phase = {}
        self.todo_titles = set()
        for iss in issues:
            self.add(iss)

    def add(self, iss):
        self.by_id[iss.get("id", "")] = iss
        gsd = issue_gsd(iss)
        req, ms = gsd.get("req"), gsd.get("milestone")
        if req and ms:
            self.by_req.setdefault((str(req), str(ms)), iss)
        if (iss.get("issue_type") == "epic" and ms
                and gsd.get("phase") is not None):
            try:
                self.epic_by_phase.setdefault(
                    (int(gsd["phase"]), str(ms)), iss)
            except (TypeError, ValueError):
                pass
        if "migrated-todo" in (iss.get("labels") or []):
            self.todo_titles.add(iss.get("title", ""))

    def req_issue(self, req):
        return self.by_req.get((req, self.milestone))

    def epic(self, phase):
        return self.epic_by_phase.get((phase, self.milestone))


def pair_labels(phase, milestone):
    return [f"m-{milestone}", f"phase-{phase}"]


def missing_labels(issue, want):
    have = set(issue.get("labels") or [])
    return [lb for lb in want if lb not in have]


def gsd_needs(issue, want):
    have = issue_gsd(issue)
    return {k: v for k, v in want.items() if have.get(k) != v}


def dep_exists(issue, blocker_id):
    for d in issue.get("dependencies") or []:
        if (d.get("depends_on_id") == blocker_id
                and d.get("type") in ("blocks", None)):
            return True
    return False


# --------------------------------------------------------------------------- #
# plan builders
# --------------------------------------------------------------------------- #
class StepList:
    def __init__(self):
        self.steps = []

    def add(self, kind, params, status="pending"):
        sid = f"s{len(self.steps) + 1:03d}"
        self.steps.append({"id": sid, "kind": kind, "params": params,
                           "status": status})
        return sid


def derive_prefix(project_dir):
    base = re.sub(r"[^a-z0-9]", "", project_dir.name.lower())
    return base[:10] or "proj"


def build_plan_a(project, planning, milestone, index, notes):
    """GSD-only backfill: epics per phase, one child issue per requirement,
    closes for completed phases, frontmatter appends, todos, maps."""
    steps = StepList()
    roadmap = parse_roadmap(planning)
    reqs_md = parse_requirements_md(planning / "REQUIREMENTS.md")
    dirs = phase_dirs(planning)
    if not roadmap:
        notes.append("no phases found in ROADMAP.md — nothing to backfill")

    if not (project / ".beads").is_dir():
        steps.add("bd_init", {"prefix": derive_prefix(project)})

    phase_nums = sorted(roadmap)
    epic_ref = {}   # n -> {"key": ...} or {"id": ...}

    # (1) one epic per phase
    for n in phase_nums:
        ph = roadmap[n]
        title = f"Phase {n:02d} — {ph['name']}"
        gsd = {"phase": n, "milestone": milestone}
        existing = index.epic(n) if index else None
        if existing is not None:
            epic_ref[n] = {"id": existing["id"]}
            need_l = missing_labels(existing, pair_labels(n, milestone))
            need_g = gsd_needs(existing, gsd)
            if need_l or need_g:
                steps.add("update_issue",
                          {"id": existing["id"], "labels": need_l,
                           "gsd": need_g,
                           "why": f"complete epic pairing for phase {n}"})
        else:
            epic_ref[n] = {"key": f"epic:{n}"}
            steps.add("create_epic",
                      {"key": f"epic:{n}", "phase": n, "title": title,
                       "labels": pair_labels(n, milestone), "gsd": gsd,
                       "priority": 1})

    # (2) phase deps: phase N depends on phase M -> bd dep add epicN epicM
    for n in phase_nums:
        for m in roadmap[n]["depends_on"]:
            if m not in epic_ref:
                notes.append(f"phase {n} depends on unknown phase {m} — "
                             "dependency skipped")
                continue
            a, b = epic_ref[n], epic_ref[m]
            if "id" in a and "id" in b and index:
                iss = index.by_id.get(a["id"])
                if iss is not None and dep_exists(iss, b["id"]):
                    continue
            params = {}
            params["from_id" if "id" in a else "from_key"] = a.get("id") or a.get("key")
            params["to_id" if "id" in b else "to_key"] = b.get("id") or b.get("key")
            steps.add("dep_add", params)

    # (3) one child issue per requirement
    req_phase = {}
    req_ref = {}
    seen_reqs = set()
    for n in phase_nums:
        for req in roadmap[n]["requirements"]:
            if req in seen_reqs:
                continue
            seen_reqs.add(req)
            req_phase[req] = n
            info = reqs_md.get(req, {"title": req, "body": ""})
            gsd = {"req": req, "phase": n, "milestone": milestone}
            existing = index.req_issue(req) if index else None
            if existing is not None:
                req_ref[req] = {"id": existing["id"]}
                need_l = missing_labels(existing, pair_labels(n, milestone))
                need_g = gsd_needs(existing, gsd)
                if need_l or need_g:
                    steps.add("update_issue",
                              {"id": existing["id"], "labels": need_l,
                               "gsd": need_g,
                               "why": f"complete stamp for {req}"})
            else:
                req_ref[req] = {"key": f"req:{req}"}
                desc = info["title"]
                if info["body"]:
                    desc += "\n\n" + info["body"]
                desc += f"\n\nMigrated from .planning (phase {n:02d})"
                params = {"key": f"req:{req}", "req": req, "phase": n,
                          "title": f"{req}: {info['title']}",
                          "description": desc,
                          "labels": pair_labels(n, milestone), "gsd": gsd}
                params.update({"parent_" + k: v
                               for k, v in epic_ref[n].items()})
                steps.add("create_issue", params)
    unassigned = sorted(set(reqs_md) - seen_reqs)
    if unassigned:
        notes.append("requirements present in REQUIREMENTS.md but mapped to "
                     f"no ROADMAP phase (skipped): {', '.join(unassigned)}")

    # (4) completed phases: close children, then the epic
    for n in phase_nums:
        if not phase_is_complete(dirs.get(n)):
            continue
        reason = f"migrated: completed in phase {n:02d} (see SUMMARIES)"
        for req in roadmap[n]["requirements"]:
            ref = req_ref.get(req)
            if ref is None:
                continue
            if "id" in ref and index:
                iss = index.by_id.get(ref["id"])
                if iss is not None and iss.get("status") == "closed":
                    continue
            steps.add("close_issue", dict(ref, reason=reason))
        eref = epic_ref[n]
        if "id" in eref and index:
            iss = index.by_id.get(eref["id"])
            if iss is not None and iss.get("status") == "closed":
                continue
        steps.add("close_issue", dict(eref, reason=reason))

    # (5) beads: frontmatter appends per non-superseded plan
    add_frontmatter_steps(steps, planning, project, index, milestone, notes)

    # (6) pending todos
    for title, text, fname in pending_todos(planning):
        if index and title in index.todo_titles:
            continue
        steps.add("create_todo",
                  {"key": f"todo:{fname}", "title": title,
                   "description": text + "\n\nMigrated from "
                                  f".planning/todos/pending/{fname}",
                   "labels": ["migrated-todo"]})

    # (7) regenerate every phase map
    for n in phase_nums:
        if dirs.get(n) is not None:
            steps.add("gen_map", {"phase": n, "milestone": milestone})
        else:
            notes.append(f"phase {n} has no .planning/phases/ dir — "
                         "map generation skipped")
    return steps


def add_frontmatter_steps(steps, planning, project, index, milestone, notes):
    """beads: frontmatter appends for every non-superseded PLAN.md with a
    requirements: list. Skips plans whose beads: list already carries every
    resolvable id (so a fully-applied plan replans to zero work)."""
    for n, d in sorted(phase_dirs(planning).items()):
        for p in plan_files(d):
            fm = frontmatter(p)
            if fm.get("status", "") == "superseded":
                continue
            reqs = REQ_ID.findall(fm.get("requirements", ""))
            if not reqs:
                continue
            have = set(parse_inline_list(fm.get("beads", "")))
            resolvable = []
            unresolved = False
            for r in reqs:
                iss = index.req_issue(r) if index else None
                if iss is None:
                    unresolved = True
                else:
                    resolvable.append(iss["id"])
            if not unresolved and resolvable and set(resolvable) <= have:
                continue
            steps.add("frontmatter_beads",
                      {"file": str(p.relative_to(project)), "reqs": reqs})


def slugify(name, fallback):
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug[:32] or fallback


def topo_order(nodes, blockers_of):
    """Kahn topological order (ties by id); cycles appended sorted."""
    ids = [n for n in nodes]
    pending = {i: set(b for b in blockers_of(i) if b in ids) for i in ids}
    out = []
    while pending:
        ready = sorted(i for i, blk in pending.items() if not blk)
        if not ready:
            out.extend(sorted(pending))
            break
        for i in ready:
            out.append(i)
            del pending[i]
        for blk in pending.values():
            blk.difference_update(ready)
    return out


def cat_prefix(issues, epic_title, used_fallback="REQ"):
    labels = Counter()
    for iss in issues:
        for lb in iss.get("labels") or []:
            if lb.startswith(("m-", "phase-", "cairn-")):
                continue
            labels[lb] += 1
    if labels:
        best = labels.most_common(1)[0][0]
        pref = re.sub(r"[^A-Za-z0-9]", "", best).upper()[:8]
        if pref:
            return pref
    if epic_title:
        m = re.search(r"[A-Za-z0-9]+", epic_title)
        if m:
            return m.group(0).upper()[:8]
    return used_fallback


def build_plan_b(project, planning, milestone, force, notes):
    """beads-only bootstrap: group issues into phases, generate the three
    GSD docs + MILESTONES.md, stamp labels/metadata, generate maps.
    Never fabricates PLAN.md; never writes PROJECT.md."""
    steps = StepList()
    issues = list_issues(project)
    by_id = {i["id"]: i for i in issues}
    epics = [i for i in issues if i.get("issue_type") == "epic"]

    def children_of(epic):
        eid = epic["id"]
        return [i for i in issues if i is not epic
                and (i.get("parent") == eid
                     or str(i.get("id", "")).startswith(eid + "."))]

    phases = []   # [{"n", "name", "epic": iss|None, "issues": [iss]}]
    if epics:
        def epic_blockers(eid):
            iss = by_id[eid]
            return [d.get("depends_on_id") for d in iss.get("dependencies")
                    or [] if d.get("type") == "blocks"]
        order = topo_order([e["id"] for e in epics], epic_blockers)
        assigned = set()
        for n, eid in enumerate(order, start=1):
            epic = by_id[eid]
            kids = children_of(epic)
            assigned.add(eid)
            assigned.update(k["id"] for k in kids)
            phases.append({"n": n, "name": epic.get("title", f"Phase {n}"),
                           "epic": epic, "issues": kids})
        strays = [i for i in issues if i["id"] not in assigned
                  and i.get("status") != "closed"]
        if strays:
            phases.append({"n": len(phases) + 1, "name": "Unscoped work",
                           "epic": None, "issues": strays})
    else:
        open_issues = [i for i in issues if i.get("status") != "closed"]

        def blockers(iid):
            iss = by_id[iid]
            return [d.get("depends_on_id") for d in iss.get("dependencies")
                    or [] if d.get("type") == "blocks"]
        order = topo_order([i["id"] for i in open_issues], blockers)
        layers = []
        placed = {}
        for iid in order:
            layer = 0
            for b in blockers(iid):
                if b in placed:
                    layer = max(layer, placed[b] + 1)
            placed[iid] = layer
            while len(layers) <= layer:
                layers.append([])
            layers[layer].append(by_id[iid])
        for n, layer in enumerate(layers, start=1):
            phases.append({"n": n, "name": f"Stage {n}", "epic": None,
                           "issues": layer})

    if not phases:
        notes.append("no groupable issues found in bd — only the docs "
                     "skeleton would be written")

    # Assign CAT-NN requirement ids (deterministic: phase order, then id)
    counters = {}
    for ph in phases:
        pref = cat_prefix(ph["issues"], (ph["epic"] or {}).get("title"))
        ph["prefix"] = pref
        ph["reqs"] = []
        for iss in sorted(ph["issues"], key=lambda i: i.get("id", "")):
            counters[pref] = counters.get(pref, 0) + 1
            ph["reqs"].append((f"{pref}-{counters[pref]:02d}", iss))

    # Phase deps from epic-level blocks deps
    epic_phase = {ph["epic"]["id"]: ph["n"] for ph in phases if ph["epic"]}
    for ph in phases:
        deps = set()
        if ph["epic"]:
            for d in ph["epic"].get("dependencies") or []:
                if d.get("type") == "blocks" and d.get("depends_on_id") in epic_phase:
                    deps.add(epic_phase[d["depends_on_id"]])
        ph["depends_on"] = sorted(deps - {ph["n"]})

    closed_issues = [i for i in issues if i.get("status") == "closed"]
    active = next((ph["n"] for ph in phases for i in ph["issues"]
                   if i.get("status") == "in_progress"), 1)

    name = project.name
    today = now_utc().split("T")[0]
    banner = f"_Bootstrapped from beads by cairn-migrate on {today}._"

    def phase_done(ph):
        allc = ph["issues"] + ([ph["epic"]] if ph["epic"] else [])
        return bool(allc) and all(i.get("status") == "closed" for i in allc)

    # --- REQUIREMENTS.md
    lines = [f"# Requirements: {name}", "", banner, "",
             f"**Defined:** {today}", "", "## Requirements", ""]
    for ph in phases:
        lines += [f"### Phase {ph['n']}: {ph['name']}", ""]
        for req, iss in ph["reqs"]:
            box = "x" if iss.get("status") == "closed" else " "
            lines.append(f"- [{box}] **{req}**: {iss.get('title', '')} "
                         f"(bd: {iss['id']})")
        lines.append("")
    lines += ["## Traceability", "",
              "| Requirement | Phase | Issue | Status |",
              "|-------------|-------|-------|--------|"]
    for ph in phases:
        for req, iss in ph["reqs"]:
            status = ("Complete" if iss.get("status") == "closed"
                      else "Pending")
            lines.append(f"| {req} | Phase {ph['n']} | {iss['id']} "
                         f"| {status} |")
    requirements_doc = "\n".join(lines) + "\n"

    # --- ROADMAP.md
    lines = [f"# Roadmap: {name}", "", banner, "", "## Phases", ""]
    for ph in phases:
        box = "x" if phase_done(ph) else " "
        lines.append(f"- [{box}] **Phase {ph['n']}: {ph['name']}**")
    lines += ["", "## Phase Details", ""]
    for ph in phases:
        lines += [f"### Phase {ph['n']}: {ph['name']}"]
        goal = ((ph["epic"] or {}).get("description") or "").strip()
        goal = goal.splitlines()[0] if goal else ph["name"]
        lines.append(f"**Goal**: {goal}")
        if ph["depends_on"]:
            dep_txt = ", ".join(f"Phase {d}" for d in ph["depends_on"])
        else:
            dep_txt = "Nothing"
        lines.append(f"**Depends on**: {dep_txt}")
        reqs = ", ".join(req for req, _ in ph["reqs"])
        lines.append(f"**Requirements**: [{reqs}]")
        lines.append("")
    roadmap_doc = "\n".join(lines) + "\n"

    # --- STATE.md
    state_doc = "\n".join([
        "---",
        "gsd_state_version: '1.0'",
        "status: executing",
        f'active_phase: "{active}"',
        f"milestone: {milestone}",
        "next_action: plan-phase",
        "---",
        "",
        "# Project State",
        "",
        banner,
        "",
        f"Phase: {active} of {len(phases)}",
        "Status: bootstrapped from the beads backlog — run /cairn:plan "
        "to produce the first PLAN.md",
        ""])

    # --- MILESTONES.md pre-cairn section
    ml = ["## Completed pre-cairn", "",
          f"Issues closed before cairn migration ({today}):", ""]
    for iss in sorted(closed_issues, key=lambda i: i.get("id", "")):
        reason = iss.get("close_reason") or ""
        suffix = f" — {reason}" if reason else ""
        ml.append(f"- {iss['id']} — {iss.get('title', '')}{suffix}")
    ml.append("")
    milestones_section = "\n".join(ml)
    milestones_doc = f"# Milestones\n\n{milestones_section}"

    def write_step(rel, content, append_marker=None):
        path = project / rel
        if append_marker is None and path.is_file() and not force:
            notes.append(f"{rel} already exists — skipped (use --force on "
                         "plan to overwrite)")
            return
        params = {"path": rel, "content": content, "overwrite": force}
        if append_marker:
            params["append_marker"] = append_marker
        steps.add("write_file", params)

    write_step(".planning/REQUIREMENTS.md", requirements_doc)
    write_step(".planning/ROADMAP.md", roadmap_doc)
    write_step(".planning/STATE.md", state_doc)
    if closed_issues:
        mfile = project / ".planning/MILESTONES.md"
        if (not mfile.is_file()
                or "## Completed pre-cairn" not in
                mfile.read_text(encoding="utf-8", errors="replace")):
            steps.add("write_file",
                      {"path": ".planning/MILESTONES.md",
                       "content": milestones_doc,
                       "append_content": "\n" + milestones_section,
                       "append_marker": "## Completed pre-cairn",
                       "overwrite": False})

    # --- label + stamp every phase-assigned issue
    for ph in phases:
        n = ph["n"]
        targets = []
        if ph["epic"]:
            targets.append((None, ph["epic"]))
        targets.extend(ph["reqs"])
        for req, iss in targets:
            gsd = {"phase": n, "milestone": milestone}
            if req:
                gsd["req"] = req
            need_l = missing_labels(iss, pair_labels(n, milestone))
            need_g = gsd_needs(iss, gsd)
            if not need_l and not need_g:
                continue
            steps.add("link_issue",
                      {"id": iss["id"], "req": req, "phase": n,
                       "labels": pair_labels(n, milestone), "gsd": gsd})

    # --- maps (phase dirs are created by the gen_map handler; the dir with
    #     only a generated map inside is NOT a fabricated PLAN.md)
    for ph in phases:
        fallback = "phase-%d" % ph["n"]
        dirname = "%02d-%s" % (ph["n"], slugify(ph["name"], fallback))
        steps.add("gen_map", {"phase": ph["n"], "milestone": milestone,
                              "dir": dirname})
    return steps


def build_plan_c(project, planning, milestone, index, notes, plan_extra):
    """Both present, unwired: match requirements to issues (exact CAT token
    auto-links; fuzzy >= 0.6 becomes a pending_confirmation candidate),
    create the unmatched, report orphans + divergence, then frontmatter
    backfill and maps like mode A."""
    steps = StepList()
    roadmap = parse_roadmap(planning)
    reqs_md = parse_requirements_md(planning / "REQUIREMENTS.md")
    dirs = phase_dirs(planning)
    issues = [index.by_id[i] for i in sorted(index.by_id)]

    req_phase = {}
    for n in sorted(roadmap):
        for req in roadmap[n]["requirements"]:
            req_phase.setdefault(req, n)
    for req in reqs_md:
        if req not in req_phase:
            notes.append(f"{req} is in REQUIREMENTS.md but mapped to no "
                         "ROADMAP phase — left unmatched")

    # epics per phase, when they exist (mode C creates no epics)
    epic_for = {}
    for iss in issues:
        if iss.get("issue_type") != "epic":
            continue
        gsd = issue_gsd(iss)
        n = gsd.get("phase")
        if n is None:
            m = re.match(r"^Phase\s+0*(\d+)\b", iss.get("title", ""))
            n = int(m.group(1)) if m else None
        try:
            n = int(n) if n is not None else None
        except (TypeError, ValueError):
            n = None
        if n is not None:
            epic_for.setdefault(n, iss)

    matched_issue_by_req = {}
    matched_ids = set()

    # pre-wired issues count as matched
    for req, n in req_phase.items():
        iss = index.req_issue(req)
        if iss is not None:
            matched_issue_by_req[req] = iss
            matched_ids.add(iss["id"])

    # exact pass: the CAT-NN token appears in the issue title
    for req, n in req_phase.items():
        if req in matched_issue_by_req:
            continue
        tok = re.compile(rf"\b{re.escape(req)}\b")
        hits = [i for i in issues if i["id"] not in matched_ids
                and i.get("issue_type") != "epic"
                and tok.search(i.get("title", ""))]
        if not hits:
            continue
        iss = hits[0]
        matched_issue_by_req[req] = iss
        matched_ids.add(iss["id"])
        gsd = {"req": req, "phase": n, "milestone": milestone}
        need_l = missing_labels(iss, pair_labels(n, milestone))
        need_g = gsd_needs(iss, gsd)
        if need_l or need_g:
            steps.add("link_issue",
                      {"id": iss["id"], "req": req, "phase": n,
                       "labels": pair_labels(n, milestone), "gsd": gsd})

    # fuzzy pass: difflib ratio >= 0.6 -> pending_confirmation candidate
    candidate_ids = set()
    for req, n in sorted(req_phase.items()):
        if req in matched_issue_by_req:
            continue
        title = reqs_md.get(req, {}).get("title", req)
        best, best_score = None, 0.0
        for iss in issues:
            if iss["id"] in matched_ids or iss["id"] in candidate_ids:
                continue
            if iss.get("issue_type") == "epic":
                continue
            score = difflib.SequenceMatcher(
                None, title.lower(), iss.get("title", "").lower()).ratio()
            if score > best_score:
                best, best_score = iss, score
        if best is not None and best_score >= 0.6:
            candidate_ids.add(best["id"])
            gsd = {"req": req, "phase": n, "milestone": milestone}
            steps.add("link_candidate",
                      {"id": best["id"], "req": req, "phase": n,
                       "labels": pair_labels(n, milestone), "gsd": gsd,
                       "issue_title": best.get("title", ""),
                       "requirement_title": title,
                       "score": round(best_score, 3), "confirmed": False},
                      status="pending_confirmation")
        else:
            # unmatched requirement -> create (mode-A style)
            info = reqs_md.get(req, {"title": req, "body": ""})
            desc = info["title"]
            if info["body"]:
                desc += "\n\n" + info["body"]
            desc += f"\n\nMigrated from .planning (phase {n:02d})"
            gsd = {"req": req, "phase": n, "milestone": milestone}
            params = {"key": f"req:{req}", "req": req, "phase": n,
                      "title": f"{req}: {info['title']}",
                      "description": desc,
                      "labels": pair_labels(n, milestone), "gsd": gsd}
            if n in epic_for:
                params["parent_id"] = epic_for[n]["id"]
            steps.add("create_issue", params)

    # orphans: open-ish issues with no phase label and no match
    orphans = []
    for iss in issues:
        if iss.get("status") == "closed":
            continue
        if iss["id"] in matched_ids or iss["id"] in candidate_ids:
            continue
        if any(lb.startswith("phase-") for lb in iss.get("labels") or []):
            continue
        orphans.append({"id": iss["id"], "title": iss.get("title", ""),
                        "action": "report"})
    plan_extra["orphans"] = orphans

    # divergence: complete phases with open matched issues -> offer close
    # (pending_confirmation: pre-existing issues may be externally mirrored)
    warnings = []
    for n in sorted(roadmap):
        complete = phase_is_complete(dirs.get(n))
        for req in roadmap[n]["requirements"]:
            iss = matched_issue_by_req.get(req)
            if iss is None:
                continue
            if complete and iss.get("status") != "closed":
                steps.add("close_issue",
                          {"id": iss["id"],
                           "reason": f"migrated: completed in phase {n:02d} "
                                     "(see SUMMARIES)",
                           "confirmed": False},
                          status="pending_confirmation")
            if not complete and iss.get("status") == "closed":
                warnings.append(
                    f"{iss['id']} is closed but phase {n:02d} has no passed "
                    f"VERIFICATION — review ({req})")
    plan_extra["warnings"] = warnings

    add_frontmatter_steps(steps, planning, project, index, milestone, notes)
    for n in sorted(roadmap):
        if dirs.get(n) is not None:
            steps.add("gen_map", {"phase": n, "milestone": milestone})
    return steps


# --------------------------------------------------------------------------- #
# plan command
# --------------------------------------------------------------------------- #
def step_summary_line(step):
    p = step["params"]
    k = step["kind"]
    if k == "bd_init":
        return f"bd init (prefix {p['prefix']})"
    if k == "create_epic":
        return f"create epic: {p['title']}"
    if k == "create_issue":
        return f"create issue: {p['title']}"
    if k == "update_issue":
        return f"update {p['id']}: {p.get('why', 'labels/metadata')}"
    if k == "link_issue":
        return f"link {p['id']} -> {p.get('req') or 'phase ' + str(p['phase'])}"
    if k == "link_candidate":
        return (f"CANDIDATE {p['id']} -> {p['req']} (score {p['score']}, "
                "pending confirmation)")
    if k == "dep_add":
        frm = p.get("from_id") or p.get("from_key")
        to = p.get("to_id") or p.get("to_key")
        return f"dep: {frm} depends on {to}"
    if k == "close_issue":
        tgt = p.get("id") or p.get("key")
        tail = " (pending confirmation)" if p.get("confirmed") is False else ""
        return f"close {tgt}: {p['reason']}{tail}"
    if k == "create_todo":
        return f"create todo issue: {p['title']} [migrated-todo]"
    if k == "frontmatter_beads":
        return f"append beads: frontmatter -> {p['file']}"
    if k == "write_file":
        return f"write {p['path']}"
    if k == "gen_map":
        return f"regenerate map for phase {p['phase']:02d}"
    return k


def print_plan_summary(plan, plan_path):
    steps = plan["steps"]
    print(f"[cairn-migrate] plan (mode {plan['mode']}, milestone "
          f"{plan['milestone']}) — {len(steps)} step(s) -> {plan_path}")
    by_kind = {}
    for s in steps:
        by_kind.setdefault(s["kind"], []).append(s)
    for kind in sorted(by_kind):
        group = by_kind[kind]
        print(f"  {kind} ({len(group)}):")
        for s in group:
            print(f"    {s['id']}  {step_summary_line(s)}")
    for o in plan.get("orphans", []):
        print(f"  orphan: {o['id']}  {o['title']}  [action: {o['action']}]")
    for w in plan.get("warnings", []):
        print(f"  warning: {w}")
    for note in plan.get("notes", []):
        print(f"  note: {note}")
    if not steps:
        print("  nothing to do — the repo is already migrated")


def cmd_plan(args):
    project = Path(args.project_dir or
                   os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    planning = project / ".planning"
    info = classify(project)
    mode = args.mode or info["state"]
    if mode not in ("A", "B", "C"):
        die(f"detected state {info['state']} "
            f"({STATE_DESCRIPTIONS[info['state']]}) — nothing to plan; "
            "pass --mode A|B|C to override", EXIT_USAGE)
    if mode in ("A", "C") and not planning.is_dir():
        die(f"mode {mode} needs .planning/ and {planning} is absent",
            EXIT_USAGE)
    if mode in ("B", "C") and not (project / ".beads").is_dir():
        die(f"mode {mode} needs .beads/ and it is absent under {project}",
            EXIT_USAGE)

    needs_bd = mode in ("B", "C") or (project / ".beads").is_dir()
    if needs_bd and not bd_available():
        die("'bd' not found on PATH — required to plan this mode",
            EXIT_NO_BD)

    milestone = resolve_milestone(args.milestone, planning, mode)
    notes = []
    plan_extra = {}
    index = None
    if needs_bd:
        index = IssueIndex(list_issues(project), milestone)

    if mode == "A":
        steps = build_plan_a(project, planning, milestone, index, notes)
    elif mode == "B":
        steps = build_plan_b(project, planning, milestone, args.force, notes)
    else:
        steps = build_plan_c(project, planning, milestone, index, notes,
                             plan_extra)

    plan = {"version": 1, "mode": mode, "milestone": milestone,
            "created_at": now_utc(), "project_dir": str(project),
            "steps": steps.steps, "orphans": plan_extra.get("orphans", []),
            "warnings": plan_extra.get("warnings", []), "notes": notes}

    cairn_dir = project / ".cairn"
    cairn_dir.mkdir(parents=True, exist_ok=True)
    plan_path = cairn_dir / "migrate-plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    print_plan_summary(plan, plan_path)
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# apply
# --------------------------------------------------------------------------- #
class StepError(Exception):
    pass


class Applier:
    def __init__(self, project, plan, journal_path):
        self.project = project
        self.planning = project / ".planning"
        self.plan = plan
        self.milestone = plan["milestone"]
        self.journal_path = journal_path
        self.ids = {}
        self.completed = set()
        self.index = None

    # ---- journal -----------------------------------------------------------
    def load_journal(self):
        created = self.plan.get("created_at")
        if self.journal_path.is_file():
            lines = self.journal_path.read_text(
                encoding="utf-8").splitlines()
            header_ok = False
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not header_ok:
                    if rec.get("plan_created_at") == created:
                        header_ok = True
                        continue
                    break
                sid = rec.get("step")
                if sid:
                    self.completed.add(sid)
                    self.ids.update(rec.get("ids") or {})
            if header_ok:
                return
        # missing or stale journal: start fresh
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self.journal_path.write_text(
            json.dumps({"plan_created_at": created,
                        "plan_file": str(self.plan.get("_path", ""))}) + "\n",
            encoding="utf-8")

    def journal(self, step_id, new_ids=None):
        self.completed.add(step_id)
        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"step": step_id, "ids": new_ids or {},
                                 "ts": now_utc()}) + "\n")

    # ---- shared ------------------------------------------------------------
    def refresh_index(self):
        self.index = IssueIndex(list_issues(self.project), self.milestone)

    def resolve(self, params, key_field="key", id_field="id"):
        if params.get(id_field):
            return params[id_field]
        key = params.get(key_field)
        if key and key in self.ids:
            return self.ids[key]
        if key:
            if key.startswith("req:"):
                iss = self.index.req_issue(key[4:])
                if iss is not None:
                    return iss["id"]
            if key.startswith("epic:"):
                try:
                    iss = self.index.epic(int(key[5:]))
                except ValueError:
                    iss = None
                if iss is not None:
                    return iss["id"]
        raise StepError(f"cannot resolve issue reference "
                        f"{params.get(id_field) or key!r}")

    def ensure_pairing(self, bd_id, labels, gsd):
        iss = self.index.by_id.get(bd_id)
        need_l = missing_labels(iss, labels) if iss is not None else labels
        need_g = gsd_needs(iss, gsd) if iss is not None else gsd
        for lb in need_l:
            _, err = run_bd(["label", "add", bd_id, lb], self.project)
            if err:
                raise StepError(f"bd label add {lb}: {err}")
            if iss is not None:
                iss.setdefault("labels", []).append(lb)
        if need_g:
            err = merge_gsd(bd_id, need_g, self.project)
            if err:
                raise StepError(err)
            if iss is not None:
                md = iss.get("metadata")
                if not isinstance(md, dict):
                    md = {}
                cur = issue_gsd(iss)
                cur.update(need_g)
                md["gsd"] = cur
                iss["metadata"] = md
                # re-index so same-run lookups see the new (req, milestone)
                # / (phase, milestone) keys
                self.index.add(iss)

    def create(self, title, itype, labels, gsd, description=None,
               parent=None, priority=None):
        args = ["create", title, "-t", itype, "--silent"]
        if labels:
            args += ["-l", ",".join(labels)]
        if gsd:
            args += ["--metadata", json.dumps({"gsd": gsd})]
        if description:
            args += ["-d", description]
        if parent:
            args += ["--parent", parent]
        if priority is not None:
            args += ["-p", str(priority)]
        out, err = run_bd(args, self.project)
        if err:
            raise StepError(f"bd create: {err}")
        out_lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        if not out_lines:
            raise StepError("bd create returned no id")
        bd_id = out_lines[-1]
        record = {"id": bd_id, "title": title, "status": "open",
                  "issue_type": itype, "labels": list(labels or []),
                  "metadata": {"gsd": dict(gsd)} if gsd else {},
                  "parent": parent, "dependencies": []}
        self.index.add(record)
        return bd_id

    # ---- handlers ----------------------------------------------------------
    def do_bd_init(self, p):
        if (self.project / ".beads").is_dir():
            return {}
        # NOTE: `bd -C <dir> init` refuses to run when <dir> has no beads
        # project yet ("cannot use -C directory ... no beads project found",
        # verified on bd 1.1.0), so init runs with cwd=project instead.
        # --skip-agents keeps apply's writes confined to what the plan
        # declares (no AGENTS.md/CLAUDE.md side effects); --init-if-missing
        # makes a resumed step a no-op.
        cmd = ["bd", "init", "-q", "--prefix", p["prefix"],
               "--non-interactive", "--skip-agents", "--init-if-missing"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  cwd=str(self.project))
        except FileNotFoundError:
            die("'bd' not found on PATH", EXIT_NO_BD)
        if proc.returncode != 0:
            raise StepError(f"bd init: {proc.stderr.strip() or proc.stdout.strip() or f'exit {proc.returncode}'}")
        return {}

    def do_create_epic(self, p):
        existing = self.index.epic(p["phase"])
        if existing is not None:
            self.ensure_pairing(existing["id"], p["labels"], p["gsd"])
            self.ids[p["key"]] = existing["id"]
            return {p["key"]: existing["id"]}
        bd_id = self.create(p["title"], "epic", p["labels"], p["gsd"],
                            priority=p.get("priority"))
        self.ids[p["key"]] = bd_id
        return {p["key"]: bd_id}

    def do_create_issue(self, p):
        existing = self.index.req_issue(p["req"])
        if existing is not None:
            self.ensure_pairing(existing["id"], p["labels"], p["gsd"])
            self.ids[p["key"]] = existing["id"]
            return {p["key"]: existing["id"]}
        parent = None
        if p.get("parent_id") or p.get("parent_key"):
            parent = self.resolve(p, key_field="parent_key",
                                  id_field="parent_id")
        bd_id = self.create(p["title"], "task", p["labels"], p["gsd"],
                            description=p.get("description"), parent=parent)
        self.ids[p["key"]] = bd_id
        return {p["key"]: bd_id}

    def do_update_issue(self, p):
        self.ensure_pairing(p["id"], p.get("labels") or [],
                            p.get("gsd") or {})
        return {}

    do_link_issue = do_update_issue
    do_link_candidate = do_update_issue

    def do_dep_add(self, p):
        frm = self.resolve(p, key_field="from_key", id_field="from_id")
        to = self.resolve(p, key_field="to_key", id_field="to_id")
        iss = self.index.by_id.get(frm)
        if iss is not None and dep_exists(iss, to):
            return {}
        _, err = run_bd(["dep", "add", frm, to], self.project)
        if err:
            raise StepError(f"bd dep add {frm} {to}: {err}")
        if iss is not None:
            iss.setdefault("dependencies", []).append(
                {"issue_id": frm, "depends_on_id": to, "type": "blocks"})
        return {}

    def do_close_issue(self, p):
        bd_id = self.resolve(p)
        iss = self.index.by_id.get(bd_id)
        if iss is not None and iss.get("status") == "closed":
            return {}
        _, err = run_bd(["close", bd_id, "--reason", p["reason"]],
                        self.project)
        if err:
            raise StepError(f"bd close {bd_id}: {err}")
        if iss is not None:
            iss["status"] = "closed"
        return {}

    def do_create_todo(self, p):
        if p["title"] in self.index.todo_titles:
            return {}
        bd_id = self.create(p["title"], "task", p.get("labels") or
                            ["migrated-todo"], None,
                            description=p.get("description"))
        self.ids[p["key"]] = bd_id
        return {p["key"]: bd_id}

    def do_frontmatter_beads(self, p):
        path = self.project / p["file"]
        resolved = []
        for req in p["reqs"]:
            iss = self.index.req_issue(req)
            bd_id = self.ids.get(f"req:{req}") or (iss and iss["id"])
            if bd_id:
                resolved.append(bd_id)
            else:
                warn(f"{p['file']}: no issue found for {req} — left out of "
                     "beads: frontmatter")
        if not resolved:
            # Not a failure: every req may map to a rejected fuzzy candidate
            # (mode C) or an issue that simply doesn't exist yet. Failing here
            # would make apply exit 8 forever on a plan the user legitimately
            # trimmed; warn and skip instead — a later plan run picks it up.
            warn(f"{p['file']}: no requirement resolved to an issue id — "
                 "beads: frontmatter left unchanged")
            return {}
        merge_beads_frontmatter(path, resolved)
        return {}

    def do_write_file(self, p):
        rel = p["path"]
        base = os.path.basename(rel)
        if base in ("PROJECT.md", "CONTEXT.md"):
            raise StepError(f"refusing to write {rel} — cairn-migrate never "
                            "touches PROJECT.md/CONTEXT.md")
        path = self.project / rel
        marker = p.get("append_marker")
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            if marker:
                if marker in text:
                    return {}
                sep = "" if text.endswith("\n") else "\n"
                path.write_text(text + sep +
                                p.get("append_content", p["content"]),
                                encoding="utf-8")
                return {}
            if not p.get("overwrite"):
                print(f"[cairn-migrate] skip existing {rel} "
                      "(--force on plan to overwrite)")
                return {}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(p["content"], encoding="utf-8")
        return {}

    def do_gen_map(self, p):
        if p.get("dir"):
            (self.planning / "phases" / p["dir"]).mkdir(parents=True,
                                                        exist_ok=True)
        cmd = [sys.executable, str(SCRIPT_DIR / "cairn-map.py"),
               str(p["phase"]), "--planning-dir", str(self.planning)]
        if p.get("milestone"):
            cmd += ["--milestone", p["milestone"]]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              cwd=str(self.project))
        if proc.returncode != 0:
            raise StepError(f"cairn-map phase {p['phase']}: "
                            f"{proc.stderr.strip() or proc.stdout.strip()}")
        return {}

    def do_orphan(self, orphan):
        action = orphan.get("action", "report")
        if action == "report":
            return
        bd_id = orphan["id"]
        m = ATTACH_ACTION.match(action)
        if m:
            n = int(m.group(1))
            self.ensure_pairing(bd_id, pair_labels(n, self.milestone),
                                {"phase": n, "milestone": self.milestone})
            return
        if action == "label-backlog":
            _, err = run_bd(["label", "add", bd_id, "backlog"], self.project)
            if err:
                raise StepError(f"bd label add backlog: {err}")
            return
        raise StepError(f"unknown orphan action {action!r} for {bd_id}")


def merge_beads_frontmatter(path, new_ids):
    """Merge ids into the PLAN.md beads: frontmatter list (never duplicate,
    never clobber the rest of the frontmatter)."""
    if not path.is_file():
        raise StepError(f"{path} does not exist")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise StepError(f"{path} has no YAML frontmatter")
    end = None
    beads_line = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        if re.match(r"^beads\s*:", lines[i]):
            beads_line = i
    if end is None:
        raise StepError(f"{path} frontmatter never closes")
    if beads_line is not None:
        raw = lines[beads_line].split(":", 1)[1]
        comment = ""
        if "#" in raw:
            raw, comment = raw.split("#", 1)
            comment = "   # " + comment.strip()
        block_end = beads_line + 1
        if raw.strip():
            existing = parse_inline_list(raw)
        else:
            # Block form ('beads:' + indented '- id' items — the same shape
            # cairn-doctor's parse_plan_frontmatter accepts): consume the
            # item lines so the flow-style rewrite REPLACES them instead of
            # leaving duplicated ids stranded under the new inline list.
            existing = []
            while block_end < end:
                mi = re.match(r"^\s*-\s*(.+?)\s*$", lines[block_end])
                if not mi:
                    break
                existing.append(mi.group(1).strip("'\""))
                block_end += 1
        merged = existing + [i for i in new_ids if i not in existing]
        if merged == existing:
            return
        lines[beads_line:block_end] = \
            [f"beads: [{', '.join(merged)}]{comment}"]
    else:
        lines.insert(end, f"beads: [{', '.join(new_ids)}]")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_apply(args):
    project = Path(args.project_dir or
                   os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    plan_path = Path(args.plan) if args.plan else (
        project / ".cairn" / "migrate-plan.json")
    if not plan_path.is_file():
        die(f"no plan at {plan_path} — run 'plan' first", EXIT_USAGE)
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"invalid plan JSON at {plan_path}: {e}", EXIT_USAGE)
    if (not isinstance(plan, dict) or plan.get("version") != 1
            or plan.get("mode") not in ("A", "B", "C")
            or not isinstance(plan.get("steps"), list)):
        die(f"invalid plan at {plan_path} (need version 1, mode A|B|C, "
            "steps list)", EXIT_USAGE)
    plan["_path"] = str(plan_path)

    if not bd_available():
        die("'bd' not found on PATH — apply needs bd", EXIT_NO_BD)

    runnable = [s for s in plan["steps"]
                if s.get("status") != "pending_confirmation"
                or s.get("params", {}).get("confirmed")]
    if not args.yes:
        if not sys.stdin.isatty():
            die("refusing to apply without --yes (stdin is not a TTY; the "
                "prose command passes --yes after user confirmation)",
                EXIT_USAGE)
        resp = input(f"Apply {len(runnable)} step(s) from {plan_path}? "
                     "[y/N] ")
        if resp.strip().lower() not in ("y", "yes"):
            print("[cairn-migrate] aborted")
            sys.exit(EXIT_USAGE)

    applier = Applier(project, plan,
                      project / ".cairn" / "migrate-state.json")
    applier.load_journal()
    if (project / ".beads").is_dir():
        applier.refresh_index()
    else:
        applier.index = IssueIndex([], plan["milestone"])

    executed = skipped_done = skipped_unconfirmed = 0
    failures = []
    for step in plan["steps"]:
        sid = step["id"]
        if (sid in applier.completed
                and step["kind"] not in ("gen_map", "frontmatter_beads")):
            # gen_map and frontmatter_beads are exempt from journal
            # skipping: their output is a view of live bd state, so a map
            # or beads: list journaled during a partial run (or before a
            # link_candidate was confirmed) would stay stale/incomplete.
            # Both handlers are cheap and idempotent (merge, no dupes), and
            # a journaled frontmatter step always re-resolves at least the
            # ids it resolved before (bd issues are never deleted here).
            skipped_done += 1
            continue
        if (step.get("status") == "pending_confirmation"
                and not step.get("params", {}).get("confirmed")):
            skipped_unconfirmed += 1
            continue
        handler = getattr(applier, f"do_{step['kind']}", None)
        if handler is None:
            failures.append((sid, f"unknown step kind {step['kind']!r}"))
            print(f"[cairn-migrate] FAIL {sid}: unknown step kind "
                  f"{step['kind']!r}", file=sys.stderr)
            continue
        try:
            new_ids = handler(step["params"])
        except (StepError, OSError) as e:
            # OSError covers filesystem failures in do_write_file /
            # merge_beads_frontmatter (unwritable path, path component is a
            # file, ...) — a raw traceback here would break the documented
            # 0/2/5/8 exit contract and skip the resume guidance.
            failures.append((sid, str(e)))
            print(f"[cairn-migrate] FAIL {sid} ({step['kind']}): {e}",
                  file=sys.stderr)
            continue
        applier.journal(sid, new_ids)
        executed += 1
        print(f"[cairn-migrate] done {sid}  {step_summary_line(step)}")

    for orphan in plan.get("orphans", []):
        oid = f"orphan:{orphan['id']}"
        if oid in applier.completed or orphan.get("action", "report") == "report":
            continue
        try:
            applier.do_orphan(orphan)
        except (StepError, OSError) as e:
            failures.append((oid, str(e)))
            print(f"[cairn-migrate] FAIL {oid}: {e}", file=sys.stderr)
            continue
        applier.journal(oid)
        executed += 1
        print(f"[cairn-migrate] done {oid} ({orphan['action']})")

    print(f"[cairn-migrate] apply: {executed} executed, {skipped_done} "
          f"already done (journal), {skipped_unconfirmed} awaiting "
          f"confirmation, {len(failures)} failed")
    if (project / ".cairn" / "sync.json").is_file():
        print("[cairn-migrate] reminder: .cairn/sync.json exists — run "
              "/cairn:sync-pull to reconcile external mirrors")
    if failures:
        print(f"[cairn-migrate] partial failure — resume by re-running "
              f"apply; the journal at {applier.journal_path} records what "
              "completed", file=sys.stderr)
        sys.exit(EXIT_PARTIAL)
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(
        prog="cairn-migrate",
        description="Deterministic GSD <-> beads migration engine "
                    "(detect / plan / apply with a plan-file handshake).")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("detect", help="classify the repo (A/B/C/W/D)")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_detect)

    pl = sub.add_parser("plan", help="read-only inventory -> "
                                     ".cairn/migrate-plan.json + dry-run "
                                     "summary")
    pl.add_argument("--mode", choices=["A", "B", "C"],
                    help="override the detected mode")
    pl.add_argument("--milestone", metavar="M",
                    help="milestone (default: inferred, else v1.0)")
    pl.add_argument("--force", action="store_true",
                    help="mode B: overwrite existing generated docs")
    pl.set_defaults(func=cmd_plan)

    ap = sub.add_parser("apply", help="execute the plan with resume "
                                      "journaling")
    ap.add_argument("--plan", metavar="FILE",
                    help="plan file (default .cairn/migrate-plan.json)")
    ap.add_argument("--yes", action="store_true",
                    help="skip the interactive confirmation")
    ap.set_defaults(func=cmd_apply)

    for p in (d, pl, ap):
        p.add_argument("--project-dir", metavar="D",
                       help="project root (default $CLAUDE_PROJECT_DIR "
                            "or cwd)")

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
