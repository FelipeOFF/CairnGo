#!/usr/bin/env python3
"""cairn-reconcile — the deterministic, provably write-free collector and
citation checker for cairn's semantic escalation pipeline (D-01's first
layer, phase 17).

Layered architecture (17-CONTEXT.md, D-01): this script is the COLLECTOR
only. It gathers the evidence a later, tool-restricted investigation
subagent (Plan 17-02) reads and proposes a reconciliation from, and it
mechanically re-checks that subagent's own proposal's citations against
the files they claim to quote. It never interprets, never proposes, and
never applies — interpretation is the subagent (a harness-level tool
restriction), application is a human running cairn-doctor's own
--apply-reconciliation flag (Plan 17-03). This script's own guarantee is
narrower and load-bearing precisely because it IS code, not a harness
policy: a grep over its source finds no bd write verb (never
create/update/close/reopen as a bd argument, and never a
cairn-journal.py/.sh call with observe, lease, or append as its
subcommand — this file only ever shells to cairn-status.py, cairn-journal.py
last-moved/history (both read subcommands), and git log/git rev-parse
(both read-only git invocations)), and a bats test runs `collect` against
a real fixture and proves nothing mutated — neither bd state nor the git
working tree — not merely that the source text looks clean today.

Usage:
    cairn-reconcile.py collect <N> [--json] [--out PATH]
                                    [--project-dir DIR]
    cairn-reconcile.py verify <N>  [--file PATH] [--json]
                                    [--project-dir DIR]

    --project-dir DIR   project root (default: $CLAUDE_PROJECT_DIR or cwd)
    --json              machine-readable output instead of human lines

Behavior:
    collect   Refuses to gather or write anything unless phase N's own
              corroboration verdict — read from `cairn-status.py --json
              --planning-dir <planning>`'s phases[] row for N (the same
              subprocess pattern cairn-doctor.py's check_phase_corroboration
              already uses) — reads exactly "conflict" (ESC-04). A verdict
              of "ok" or "unknown" refuses: nothing is written, any stale
              evidence bundle left over from a PRIOR run for a DIFFERENT
              phase number is deleted (a bundle that no longer matches what
              was just checked must never be mistaken for current), and the
              command exits EXIT_NOT_CONFLICTED. A phase number absent from
              the model exits EXIT_USAGE.

              When the verdict IS "conflict", gathers four kinds of
              evidence and writes them to a single bundle (schema below):
              corroboration (that same phases[] row's own evidence/
              conflicts, verbatim), journal (cairn-journal.py's
              last-moved/history reads for N — D-01's "história", the
              third consumer of Phase 16's journal), git_log (up to 50
              commits touching the phase's own files, from its PLAN.md
              frontmatter `files_modified:` lists, falling back to the
              phase directory path — D-01's "código", capped per T-17-03,
              never unbounded), and text (what the phase says it is —
              its own ROADMAP.md section while a roadmap is still on disk,
              its bd phase carrier's title and description once there is
              not — plus its NN-CONTEXT.md, when one exists). A failure
              gathering ANY one of these degrades that piece to null/empty
              — collect never aborts partway for a soft-read failure; the
              only hard refusal is the corroboration gate itself.

              The bundle's evidence_hash (D-04) covers ONLY the sources
              this specific conflict's bundle actually gathered — never a
              whole-repo tree hash, which a commit anywhere else in the
              repo would invalidate for no reason. It is computed BEFORE
              generated_at/evidence_hash are added to the dict that gets
              hashed, which is what makes two immediate, unchanged re-runs
              produce an identical hash.

    verify    Mechanically re-checks a proposal's citations (schema below)
              against the files they claim to quote — D-03. Reads the
              proposal from `.cairn/conflicts.json` by default (`--file`
              overrides, making this testable without a real subagent ever
              running) and asserts its own `phase` field matches N.
              Flattens every claims[].citations[] entry across the whole
              proposal and, for each one, re-opens citation["file"]
              (resolved against --project-dir/cwd) and compares its
              1-indexed citation["line"] against citation["text"] EXACTLY
              — no whitespace normalization, no hashing (D-03 rejected
              both: a hash is unreadable to the human who reads the
              proposal, and normalization is blind to the exact thing a
              citation exists to prove). A missing file, an out-of-range
              line, or a text mismatch are all "this citation failed" —
              no partial credit. The proposal is empty of anything to
              verify when its own claims list is missing, empty, or
              carries zero citations across every claim — that, too, is
              treated as invalid, never as vacuously valid (an empty
              proposal is not evidence of agreement).

              The moment ANY single citation fails, the WHOLE proposal is
              rejected — never "N of M claims verified". This is D-03's
              explicit rule: a proposal with one false citation is not a
              proposal with an error, it is a proposal that cannot be
              trusted.

Evidence bundle schema (written to .cairn/reconcile-evidence.json, or
--out PATH):
    {
      "phase": <int>,
      "generated_at": <iso8601>,
      "evidence_hash": "sha256:<hex>",
      "corroboration": {"verdict": "conflict", "evidence": {...},
                         "conflicts": [...]},
      "journal": {"last_moved": {...} | null, "history": [...]},
      "git_log": [{"hash":..., "date":..., "author":..., "subject":...}],
      "git_shallow": <bool>,
      "roadmap_excerpt": <str> | null,   # roadmap section, or carrier
      "context_excerpt": <str> | null
    }

Proposal schema (read from .cairn/conflicts.json by verify; written by
Plan 17-02's subagent, fixed here so both plans agree on one shape):
    {
      "phase": <int>,
      "generated_at": <iso8601>,
      "evidence_hash": "sha256:<hex>",
      "claims": [
        {
          "statement": <str>,
          "citations": [{"file": <repo-relative path>, "line": <int>,
                          "text": <exact literal line text>}],
          "recommended_action": {"type": "bd_close"|"bd_reopen"|
                                  "manual_review", "issue": <bd id>|null,
                                  "reason"|"note": <str>}
        }
      ]
    }
    verify only ever reads `phase` and `claims[].citations[]` — it never
    needs recommended_action to run its own check.

Exit codes:
    0  ok — collect wrote a bundle, or verify's proposal is valid.
    2  usage error (bad flags, project directory does not exist, phase not
       in the model, proposal's own phase field does not match the
       requested N, proposal file unreadable or not valid JSON).
    3  EXIT_NOT_CONFLICTED — collect's own ESC-04 gate: phase N's
       corroboration verdict was not "conflict" at read time.
    4  EXIT_INVALID_PROPOSAL — verify rejected the proposal: at least one
       citation failed, or the proposal carried no claims/citations to
       check at all.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cairn_source  # noqa: E402

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_CONFLICTED = 3
EXIT_INVALID_PROPOSAL = 4

SCRIPTS_DIR = Path(__file__).resolve().parent

# Test/override seam for the last-moved/history calls below — the SAME env
# var name cairn-lease.py, cairn-status.py, and cairn-doctor.py already use
# for their own calls into this identical script (CONVENTIONS.md's
# "Environment variable seams" note: CAIRN_* prefix, upper case). Default:
# the sibling cairn-journal.py next to this script.
CAIRN_JOURNAL = os.environ.get(
    "CAIRN_JOURNAL", str(SCRIPTS_DIR / "cairn-journal.py"))

# Phase directory numeric-prefix matching — verbatim reimplementation of
# cairn-gate.py's PHASE_DIR_PREFIX / cairn-doctor.py's DIR_PREFIX (house
# convention: no shared lib, each script carries its own copy).
PHASE_DIR_PREFIX = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")

# The ROADMAP.md phase-detail heading this module excerpts between — same
# shape as cairn-status.py's DETAIL_PHASE_HEADING / cairn-doctor.py's
# PHASE_HEAD, reimplemented here per house convention.
PHASE_SECTION_HEAD = re.compile(r"^###\s+Phase\s+0*(\d+)\b")


def die(msg, code):
    print(f"[cairn-reconcile] error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# identity + root resolution
# --------------------------------------------------------------------------- #
def resolve_root(project_dir):
    if project_dir:
        return Path(project_dir).resolve()
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()


def read_lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


# --------------------------------------------------------------------------- #
# phase directory + PLAN.md frontmatter helpers — verbatim reimplementations
# of cairn-doctor.py's phase_dirs()/parse_plan_frontmatter()/
# parse_plan_files_modified(), trimmed to only what collect() needs (house
# convention: no shared lib, each script carries its own copy).
# --------------------------------------------------------------------------- #
def phase_dir_for(planning_dir, n):
    """Directory under <planning>/phases/ whose numeric prefix matches N,
    or None."""
    root = planning_dir / "phases"
    if not root.is_dir():
        return None
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        m = PHASE_DIR_PREFIX.match(d.name)
        if m and int(m.group(1)) == n:
            return d
    return None


def _plan_status(path):
    """'status:' field from a PLAN.md's YAML frontmatter, or None."""
    lines = read_lines(path)
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^status\s*:\s*(.+?)\s*$", line)
        if m:
            return m.group(1).split("#", 1)[0].strip().strip("'\"")
    return None


def _plan_files_modified(path):
    """`files_modified:` paths from a PLAN.md's YAML frontmatter, leniently:
    a flow list ('files_modified: [a, b]', trailing comment tolerated) or
    an indented '- path' block list."""
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


def phase_pathspec(root, pdir):
    """files_modified paths across PDIR's non-superseded *-PLAN.md files,
    de-duplicated in first-seen order; falls back to the phase directory's
    own repo-relative path when no files_modified is known anywhere. []
    when PDIR itself is None — collect() skips the git log gather entirely
    in that case rather than querying with no path restriction at all."""
    if pdir is None:
        return []
    files = []
    for f in sorted(pdir.glob("*-PLAN.md")):
        if _plan_status(f) == "superseded":
            continue
        files.extend(_plan_files_modified(f))
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    if out:
        return out
    return [str(pdir.relative_to(root))]


# --------------------------------------------------------------------------- #
# git evidence — verbatim-in-spirit reimplementations of cairn-doctor.py's
# git_is_shallow() and link_ref_candidate()'s git-log-narrowed-by-pathspec
# pattern, capped rather than unbounded (T-17-03).
# --------------------------------------------------------------------------- #
def git_is_shallow(root):
    """True when root is a shallow git clone (STACK.md: a shallow clone
    makes some git queries silently incomplete at the boundary commit) —
    collect() never skips gathering because of this, only flags it in the
    bundle for whoever reads it."""
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-shallow-repository"],
        capture_output=True, text=True)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def git_log_evidence(root, pathspec):
    """Up to 50 commits touching PATHSPEC, newest first, as
    {"hash","date","author","subject"} dicts. Degrades to [] on any git
    failure — never aborts collect. split(sep, 3) (not a bare split on
    "|") keeps a "|" that happens to appear inside a commit subject from
    corrupting the fields around it."""
    cmd = ["git", "-C", str(root), "log", "--max-count=50",
           "--format=%H|%ai|%an|%s", "--", *pathspec]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    entries = []
    for line in proc.stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        h, date, author, subject = parts
        entries.append({"hash": h, "date": date, "author": author,
                         "subject": subject})
    return entries


# --------------------------------------------------------------------------- #
# journal evidence — verbatim-in-spirit reimplementation of
# cairn-doctor.py's journal_last_moved() shell-out-and-degrade shape, one
# level down: a failure here degrades only this bundle's own journal
# section to null/[], never aborts collect.
# --------------------------------------------------------------------------- #
def journal_last_moved(root, phase):
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


def journal_history(root, phase):
    """Same shell-out-and-degrade shape as journal_last_moved(), for the
    `history --phase N --json` read. Returns [] (never None — history's
    own contract is a list) on any failure."""
    try:
        proc = subprocess.run(
            [sys.executable, CAIRN_JOURNAL, "history",
             "--phase", str(phase), "--json", "--project-dir", str(root)],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return []
    return data.get("records") or []


# --------------------------------------------------------------------------- #
# text evidence — what the phase SAYS it is, plus its NN-CONTEXT.md
# --------------------------------------------------------------------------- #
def roadmap_excerpt(planning_dir, n):
    """The phase's own '### Phase N: ...' section from ROADMAP.md, from its
    heading line up to (not including) the next '###' heading or a bare
    '---' line — the same detail-block shape cairn-status.py's
    DETAIL_PHASE_HEADING/roadmap_phase_rows() already parses. None when the
    phase has no detail block at all."""
    lines = read_lines(planning_dir / "ROADMAP.md")
    start = None
    for i, line in enumerate(lines):
        m = PHASE_SECTION_HEAD.match(line)
        if m and int(m.group(1)) == n:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("###") or lines[j].strip() == "---":
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def carrier_excerpt(root, n):
    """The phase as its CARRIER declares it: the bead's title, and the
    description that says what the phase promises. None when the phase has
    no carrier — an absence is reported, never filled in with a
    requirement's title.

    Deliberately NOT shaped like a `### Phase N` heading. The reader of this
    bundle answers in citations of file and line, and text that looked like
    a roadmap section would invite a citation of a file that does not exist
    in this repository — which `verify` would then reject wholesale, for a
    fabrication this function had handed it.
    """
    name = cairn_source.phase_name(root, n)
    if name is None:
        return None
    carrier = cairn_source.phase_carrier(root, n)
    head = f"Phase {n}: {name} [bd {carrier.get('id')}]"
    goal = (cairn_source.phase_goal(root, n) or "").strip()
    return f"{head}\n\n{goal}" if goal else head


def phase_excerpt(planning_dir, root, n):
    """The phase's own text evidence, from the ROADMAP on disk when there is
    one and from the tracker when there is not.

    Same two-source rule cairn-doctor.py and cairn-gate.py already hold: a
    `.planning/ROADMAP.md` still waiting to be imported IS the input, and
    while it exists it is what the phase says about itself — including when
    it says nothing, which is a `None` this must not paper over with the
    tracker. Once imported the file is gone, and the carrier answers.
    """
    if (planning_dir / "ROADMAP.md").is_file():
        return roadmap_excerpt(planning_dir, n)
    return carrier_excerpt(root, n)


def context_excerpt(pdir):
    """Full text of PDIR's own *-CONTEXT.md, or None when PDIR is absent or
    carries no such file."""
    if pdir is None:
        return None
    matches = sorted(pdir.glob("*-CONTEXT.md"))
    if not matches:
        return None
    try:
        return matches[0].read_text(encoding="utf-8")
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# stale-bundle cleanup
# --------------------------------------------------------------------------- #
def _clean_stale_bundle(out_path, n):
    """Delete OUT_PATH when it holds an evidence bundle for a DIFFERENT
    phase than N — a bundle that no longer matches what was just checked
    must never be left behind for a later reader to mistake for current.
    A bundle for the SAME phase N, or an unreadable/unparsable file, is
    left in place: unreadable content is not this function's problem to
    solve, and a same-phase bundle is still the last real evidence
    gathered for N."""
    if not out_path.exists():
        return
    try:
        existing = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(existing, dict) and existing.get("phase") != n:
        try:
            out_path.unlink()
        except OSError:
            pass


def _atomic_write_json(path, data):
    """Write-to-temp then os.replace — an atomic swap, mirroring
    cairn-journal.py's own care around atomicity (see that module's
    docstring). This bundle is regenerated whole on every invocation, so a
    torn write here is a smaller concern than the journal's append case,
    but the temp+replace recipe is cheap and already the house pattern."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".tmp-")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, sort_keys=True, indent=2) + "\n")
        os.replace(str(tmp_path), str(path))
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------- #
# collect
# --------------------------------------------------------------------------- #
def cmd_collect(args, root):
    if not root.is_dir():
        die(f"project directory does not exist: {root}", EXIT_USAGE)
    n = args.phase
    planning_dir = root / ".planning"
    out_path = Path(args.out) if args.out else (
        root / ".cairn" / "reconcile-evidence.json")

    status_script = SCRIPTS_DIR / "cairn-status.py"
    proc = subprocess.run(
        [sys.executable, str(status_script), "--json",
         "--planning-dir", str(planning_dir)],
        capture_output=True, text=True, cwd=str(root))
    # 0 (every phase corroborated) and 5 (cairn-status.py's own bd probe
    # failed — a documented degrade that still emits valid JSON with every
    # affected phase's bd axis reading "unknown") are the two exit codes
    # cairn-status.py --json is documented to pair with real output —
    # exactly the same contract cairn-doctor.py's check_phase_corroboration
    # already relies on.
    if proc.returncode not in (0, 5):
        text = proc.stderr.strip() or proc.stdout.strip()
        first = text.splitlines()[0] if text else "(no output)"
        die(f"cairn-status.py --json exited {proc.returncode}: {first}",
            EXIT_USAGE)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        die(f"cairn-status.py --json returned invalid JSON: {e}",
            EXIT_USAGE)

    row = None
    for p in data.get("phases") or []:
        if p.get("number") == n:
            row = p
            break
    if row is None:
        die(f"phase {n} does not exist in the model", EXIT_USAGE)

    verdict = row.get("corroboration")
    if verdict != "conflict":
        _clean_stale_bundle(out_path, n)
        msg = f"phase {n} corroboration is '{verdict}' — nothing to investigate"
        if args.json:
            print(json.dumps({"phase": n, "corroboration": verdict,
                               "collected": False, "reason": msg}))
        else:
            print(f"[cairn-reconcile] {msg}")
        sys.exit(EXIT_NOT_CONFLICTED)

    pdir = phase_dir_for(planning_dir, n)
    pathspec = phase_pathspec(root, pdir)
    bundle = {
        "phase": n,
        "corroboration": {
            "verdict": verdict,
            "evidence": row.get("evidence") or {},
            "conflicts": row.get("conflicts") or [],
        },
        "journal": {
            "last_moved": journal_last_moved(root, n),
            "history": journal_history(root, n),
        },
        "git_log": git_log_evidence(root, pathspec) if pathspec else [],
        "git_shallow": git_is_shallow(root),
        "roadmap_excerpt": phase_excerpt(planning_dir, root, n),
        "context_excerpt": context_excerpt(pdir),
    }
    # D-04: hash computed over exactly the dict above — BEFORE
    # generated_at/evidence_hash are added below — so it covers only the
    # sources this conflict's own bundle actually gathered, and so two
    # immediate, unchanged re-runs produce an identical hash.
    evidence_hash = "sha256:" + hashlib.sha256(
        json.dumps(bundle, sort_keys=True).encode("utf-8")).hexdigest()
    bundle["generated_at"] = datetime.now(timezone.utc).isoformat()
    bundle["evidence_hash"] = evidence_hash

    _atomic_write_json(out_path, bundle)

    n_conflicts = len(bundle["corroboration"]["conflicts"])
    n_journal = len(bundle["journal"]["history"])
    n_commits = len(bundle["git_log"])
    if args.json:
        print(json.dumps(bundle))
    else:
        print(f"[cairn-reconcile] phase {n}: gathered evidence — "
              f"{n_conflicts} conflict(s), {n_journal} journal record(s), "
              f"{n_commits} commit(s) -> {out_path}")
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #
def _load_proposal(path, n):
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        die(f"cannot read proposal {path}: {e}", EXIT_USAGE)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}", EXIT_USAGE)
    if not isinstance(data, dict):
        die(f"{path} must be a JSON object", EXIT_USAGE)
    if data.get("phase") != n:
        die(f"proposal's phase ({data.get('phase')!r}) does not match "
            f"the requested phase {n}", EXIT_USAGE)
    return data


def _check_one_citation(project_dir, file_field, line_no, expected):
    """A single citation -> a failure dict, or None when it passes. A
    missing file, an out-of-range line, or a text mismatch are all
    treated identically — one failure entry, no partial credit."""
    if not file_field or not isinstance(line_no, int) or isinstance(
            line_no, bool):
        return {"file": file_field, "line": line_no, "expected": expected,
                "error": "malformed citation (missing file or "
                         "non-integer line)"}
    path = Path(file_field)
    if not path.is_absolute():
        path = project_dir / path
    try:
        # splitlines() already excludes the line terminator (\n, \r\n, or
        # \r) — the comparison below needs no further stripping to land on
        # the exact literal text D-03 requires.
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return {"file": file_field, "line": line_no, "expected": expected,
                "error": f"cannot read file: {e}"}
    if line_no < 1 or line_no > len(lines):
        return {"file": file_field, "line": line_no, "expected": expected,
                "error": f"line {line_no} out of range "
                         f"({len(lines)} lines)"}
    actual = lines[line_no - 1]
    if actual != expected:
        return {"file": file_field, "line": line_no, "expected": expected,
                "actual": actual, "error": "text mismatch"}
    return None


def _verify_citations(project_dir, claims):
    """Flattened per-citation check across every claims[].citations[]
    entry. Returns a list of failure dicts (empty when every citation
    passes) — never partial credit, D-03."""
    failures = []
    for claim in claims:
        statement = claim.get("statement")
        for citation in claim.get("citations") or []:
            failure = _check_one_citation(
                project_dir, citation.get("file"), citation.get("line"),
                citation.get("text"))
            if failure is not None:
                failure["statement"] = statement
                failures.append(failure)
    return failures


def cmd_verify(args, root):
    if not root.is_dir():
        die(f"project directory does not exist: {root}", EXIT_USAGE)
    n = args.phase
    if args.file:
        proposal_path = Path(args.file)
        if not proposal_path.is_absolute():
            proposal_path = Path.cwd() / proposal_path
    else:
        proposal_path = root / ".cairn" / "conflicts.json"
    proposal = _load_proposal(proposal_path, n)

    claims = proposal.get("claims")
    if not isinstance(claims, list) or not claims:
        failures = [{"error": "proposal has no claims to verify"}]
    else:
        failures = _verify_citations(root, claims)
        if not failures:
            total_citations = sum(len(c.get("citations") or [])
                                   for c in claims)
            if total_citations == 0:
                failures = [{"error": "proposal has no citations to "
                                       "verify"}]

    valid = not failures
    if args.json:
        print(json.dumps({"valid": valid, "phase": n,
                           "failed_citations": failures}))
    elif valid:
        total_citations = sum(len(c.get("citations") or []) for c in claims)
        print(f"[cairn-reconcile] {total_citations} citation(s) verified, "
              f"proposal valid")
    else:
        for f in failures:
            loc = f"{f.get('file')}:{f.get('line')}" if f.get("file") \
                else "(no citations)"
            if f.get("error") == "text mismatch":
                print(f"[cairn-reconcile] citation failed ({loc}): "
                      f"expected {f.get('expected')!r}, found "
                      f"{f.get('actual')!r}")
            else:
                print(f"[cairn-reconcile] citation failed ({loc}): "
                      f"{f.get('error')}")
        print(f"[cairn-reconcile] {len(failures)} citation(s) failed — "
              f"proposal rejected")
    sys.exit(EXIT_OK if valid else EXIT_INVALID_PROPOSAL)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairn-reconcile",
        description="Deterministic, write-free collector and citation "
                     "checker for cairn's semantic escalation pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="gather evidence for a "
                              "conflicted phase into an evidence bundle — "
                              "refuses when the phase is not conflicted")
    collect.add_argument("phase", type=int, help="phase number")
    collect.add_argument("--out", metavar="PATH", default=None,
                          help="evidence bundle destination (default: "
                               "<project>/.cairn/reconcile-evidence.json)")
    collect.set_defaults(func=cmd_collect)

    verify = sub.add_parser("verify", help="mechanically re-check a "
                             "proposal's citations against the files they "
                             "claim to quote — one bad citation invalidates "
                             "the whole proposal")
    verify.add_argument("phase", type=int, help="phase number")
    verify.add_argument("--file", metavar="PATH", default=None,
                         help="proposal file (default: "
                              "<project>/.cairn/conflicts.json)")
    verify.set_defaults(func=cmd_verify)

    for p in (collect, verify):
        p.add_argument("--project-dir", metavar="DIR",
                        help="project root (default: $CLAUDE_PROJECT_DIR "
                             "or cwd)")
        p.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    root = resolve_root(args.project_dir)
    args.func(args, root)


if __name__ == "__main__":
    main()
