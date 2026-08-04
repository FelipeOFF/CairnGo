#!/usr/bin/env python3
"""cairn-bookkeep — read the planning files, NAME every disagreement, and
edit only the lines that have to change.

Why this exists: the three planning files (.planning/ROADMAP.md,
REQUIREMENTS.md, STATE.md) hold several numbers that are pure arithmetic over
each other and over the phase tree on disk. Every one of them is maintained by
hand today, and every one of them has drifted. The drift is not hypothetical:
it is committed in this repository and frozen byte for byte under
tests/fixtures/bookkeep-drift/, which is this script's test input.

Usage:
    cairn-bookkeep.py close <phase-number> [--apply] [--json]
                            [--planning-dir <dir>]
    cairn-bookkeep.py reconcile [--json] [--planning-dir <dir>]

    --apply           write the planned edits (default: read only)
    --json            machine-readable output instead of human lines
    --planning-dir    planning dir (default: $CLAUDE_PROJECT_DIR or cwd,
                      plus /.planning)

Reading is the default; writing needs the named --apply flag. That is the
house pattern (cairn-doctor.py's --apply-reconciliation) and it is what keeps
an autonomous loop from writing by accident.

Behavior:

    close <N>   Mark phase N's checkbox line in ROADMAP.md as complete.
                Without --apply, prints the edit it would make and exits
                EXIT_DISAGREEMENT (3) when there is one, EXIT_OK (0) when
                the checkbox is already marked. With --apply, writes and
                exits 0. Running it twice writes nothing the second time.

                The `— completed <date>` suffix that closed phases carry
                (measured on phase 20) is NOT written here; it belongs to
                the full write path (plan 29-02). This subcommand changes
                one character inside one bracket, and nothing else.

    reconcile   Read the three planning files and the phase tree, and NAME
                every disagreement between them. Writes NOTHING — this
                subcommand has no --apply at all; resolving is plan 29-02.
                Exits EXIT_DISAGREEMENT (3) when it found any, 0 when it
                did not.

THE DERIVATION RULE (the spec, not a description of the code)
    One authority, five derived views. Every disagreement `reconcile` names
    is a derived view contradicting the authority.

      authority   the phase's checkbox line in ROADMAP.md says whether the
                  phase is complete;
      the phase's requirements come from the `**Requirements**:` line of its
                  `### Phase N:` block — the SAME dialect cairn-map.py's
                  roadmap_requirements() already reads. Not a second parser,
                  and never the parenthesis of the checkbox line;
      derived 1   a requirement is complete when EVERY phase carrying it is
                  complete;
      derived 2   the requirement's checkbox in REQUIREMENTS.md reflects
                  derived 1;
      derived 3   its row in the coverage table reflects derived 1;
      derived 4   the coverage footer's `N requisitos, N mapeados.` counts
                  the table's rows;
      derived 5   each `NN-MM-PLAN.md` checkbox in a phase block's `Plans:`
                  list reflects whether `NN-MM-SUMMARY.md` exists on disk.

    Active requirements are the ones under the milestone's own requirements
    heading. `## Deferred (v2)` and `## Out of Scope` are outside the table
    BY RULE, and they are still reported (requirements.deferred /
    .out_of_scope) rather than dropped: an unexplained absence is how the
    original defect got in, and silencing it in the other direction repeats
    it. Measured corroboration of the section boundary: in this repo every
    active item carries a `- [ ]` checkbox and the deferred one does not.

A REQUIREMENTS LINE CAN BE UNREADABLE, AND TODAY ONE IS
    Measured 2026-08-03, ROADMAP.md:400 reads

        **Requirements**: AUTO-01 … AUTO-08

    and roadmap_requirements(.planning, 29) returns ['AUTO-01', 'AUTO-08'] —
    two ids, not eight. The ellipsis is prose, not a separator. There is no
    readable source of phase 29's requirements inside the ROADMAP.

    This is not a parser subtlety, it is two false greens, both measured:
    `cairn-doctor.sh --json` reports `req-issue :: ok :: 29 requirement(s)
    mapped to issues` (27 from the other nine phases plus 2 from this one;
    the right number is 35), and `cairn-map.py 29 --check` exits 0 with the
    map asserting `None — every phase requirement is mapped` — true only
    because AUTO-01 and AUTO-08 happen to have issues, while AUTO-02 through
    AUTO-07 never enter the gap count at all. Note the coincidence, because
    it is how this kind of thing survives: that 29 equals the coverage
    footer's wrong 29 from a completely unrelated cause. Two wrong numbers
    meeting by accident, each wearing a green check. It is the cleanest
    example this repository owns of a surface answering without knowing what
    it is answering about.

    So `reconcile` does exactly three things with such a line, in order:

      1. DETECTS it — the line carries an ellipsis (`…` or `...`) between two
         ids, or the coverage table maps more ids to that phase than the line
         yields;
      2. NAMES it — kind `requirements-line-unreadable`, carrying the phase
         number, the raw line, the ids actually extracted, and which signals
         fired;
      3. NEVER EXPANDS it. Turning `AUTO-01 … AUTO-08` into eight ids assumes
         contiguity and assumes nothing was removed in between. That is
         inference wearing the costume of reading, and this phase's rule is
         that measured and assumed stay separate. The fix is writing the ids
         out, by a hand or by 29-02's --apply using the requirements section
         as its source — never by arithmetic over a suffix.

THE STATE COUNTERS COME FROM DISK, AND THE PROSE BODY IS NEVER READ
    total_phases is the phase checkbox lines of the open milestone;
    completed_phases counts the marked ones; total_plans and completed_plans
    count `*-PLAN.md` and `*-SUMMARY.md` files in those phases' directories;
    percent = round(100 * completed_phases / total_phases).

    Nothing below STATE.md's frontmatter is ever read — not for the phase,
    not for the milestone, not for anything. Measured cause (29-CONTEXT.md,
    D-01): `state record-session` read `Phase: 18` out of the obsolete prose
    body and rewrote the frontmatter's `current_phase: 29` backwards to 18,
    naming a phase of an ARCHIVED milestone. A test asserts that 18 appears
    nowhere in this command's computed output while running against a fixture
    whose body says exactly that.

    The table itself has two measured homes: this repo writes it under
    `## Cobertura` in ROADMAP.md, and the GSD requirements template writes
    the same three columns under `## Traceability` in REQUIREMENTS.md. Both
    are read, ROADMAP first. A table living in the other supported place is
    NOT an absent table — reporting one missing row per requirement over it
    would be this same command answering without knowing what it is
    answering about. When neither exists, that is ONE finding
    (coverage-view-missing), not one per requirement.

DISAGREEMENT KINDS
    coverage-row-missing         active requirement with no table row
    coverage-view-missing        no coverage table anywhere (reported once)
    coverage-row-orphan          table row for a requirement that is not
                                 active (reported, not assumed to be junk)
    requirement-checkbox-stale   checkbox contradicting its phases' state
    footer-count-stale           footer count contradicting the table
    state-counter-stale          a frontmatter counter contradicting disk
    state-narrative-stale        free-text frontmatter whose numbers
                                 contradict the computed ones, reported
                                 WITHOUT this command proposing to rewrite it
    plan-checkbox-stale          plan with a SUMMARY on disk still `- [ ]`
    requirements-line-unreadable the case above

THE SURGERY, AND WHY IT IS NOT A SERIALIZER
    Every write goes: read the file with newline="" (so a CRLF file stays
    CRLF), split with splitlines(keepends=True), replace ONE position of that
    list with a new string, and join it back. There is no reserialization
    step: no markdown parser, no re-wrap, no whitespace normalization, no
    touching a line that is not in the planned edit list.

    Measured, and this is the whole reason the script exists instead of a
    gsd-tools call: `roadmap update-plan-progress 20` produces +31/-4 — 35
    diff lines to flip 3 checkboxes — because _normalizeMd runs over every
    .md the gsd-tools writes (shell-command-projection.cjs:631). The risk is
    of any writer that reserializes, not of one verb.

THE PHASE ANCHOR
    A phase's checkbox line is found STRUCTURALLY, by phase number, with a
    lenient regex of the same family as cairn-migrate.py's
    CHECKBOX_PHASE_LENIENT — never by a literal of the line's text. Measured
    reason: between this phase being planned and being executed, phase 29's
    own line changed from `AUTO-01 … AUTO-07` to `AUTO-01 … AUTO-08`. A
    literal would already be stale.

    The scan covers the WHOLE file, not just the `## Phases` section, and a
    phase number matching two lines is a usage error (exit 2) that names both
    lines — never "take the first". Measured: on this repo's ROADMAP.md the
    whole-file scan finds exactly the ten phase lines of the open milestone
    and nothing else.

MEASURED vs ASSUMED
    This phase's rule is that the docstring separates what was measured in
    this repository from what is merely assumed. For this subcommand:

    MEASURED (2026-08-03, .planning/ at 3863d73, frozen under
    tests/fixtures/bookkeep-drift/ and re-measured independently by its
    capture.sh):
      - the ten phase checkbox lines are `- [ ] Phase <N>: <title> (<reqs>)`,
        one of them already `- [x] ... — completed 2026-08-03` (phase 20);
      - the whole-file lenient scan matches those ten lines and no others;
      - `git diff --quiet HEAD -- .planning/{ROADMAP,REQUIREMENTS,STATE}.md`
        exits 0, so the fixture captured from them is a committed state;
      - 35 active requirements, 0 of them checked; 33 coverage rows; AUTO-05
        and AUTO-06 with no row at all; footer claiming 29;
      - roadmap_requirements(.planning, 29) -> ['AUTO-01', 'AUTO-08'], and
        the ten phases' parsed ids sum to 29 — the same 29 the footer claims,
        by coincidence;
      - progress.total_plans: 3 against 10 `*-PLAN.md` on disk, while the
        phase pair (1/10, percent 10) still agrees. That agreeing half is
        the only arithmetic D-01 keeps from the gsd-tools.

    ASSUMED (not measured here, and deliberately not relied on):
      - that other GSD projects use the same checkbox wording. The regex is
        lenient precisely because that is an assumption; the phase NUMBER is
        the only thing it treats as load-bearing.
      - that a planning file might arrive with CRLF endings. No such file was
        seen in this repo; the newline="" handling costs nothing and removes
        the assumption instead of resting on it.
      - that a coverage footer might be written in English (`N requirements,
        N mapped`). Only the pt-BR form was measured in this repo; the
        English alternative is accepted by the regex and is ASSUMED, not
        observed. A file with no footer at all reports footer_claim: null and
        raises nothing — an absent claim is not a false claim.
      - that `last_activity_desc` states its counts as `<n> fases` and
        `<n> requisitos`. That is the measured form here; any other phrasing
        simply yields no state-narrative-stale finding, never a wrong one.

Exit codes:
    0  EXIT_OK — done, or nothing to change.
    2  EXIT_USAGE — bad flags/arguments, or an ambiguous phase number.
    3  EXIT_DISAGREEMENT — read mode found something to change. Mirrors
       cairn-map.py's exit 3 ("stale") on purpose.
    4  EXIT_NO_PHASE — no checkbox line for that phase number.
    5  RESERVED for "bd unavailable", the house meaning of 5. This script
       does not talk to bd yet (the tracker path is plan 29-02), so it never
       returns 5 today. It is listed so 29-02 cannot spend the number on
       something else — a declared code with no producer is exactly the
       defect this phase exists to remove, and naming it as reserved is the
       difference between a promise and a lie.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DISAGREEMENT = 3
EXIT_NO_PHASE = 4

TAG = "[cairn-bookkeep]"

# Same family as cairn-migrate.py's CHECKBOX_PHASE_LENIENT: the phase NUMBER
# is the anchor, everything around it is tolerated. Two dialects disagreeing
# about what a complete phase looks like is the disease this milestone treats,
# so this one deliberately does not invent a third.
CHECKBOX_PHASE_LENIENT = re.compile(
    r"^\s*-\s*\[([ xX])\]\s.*?\bPhase\s+0*(\d+)\b")

REQ_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*-\d+")
ANY_HEAD = re.compile(r"^#{1,6}\s")
HEAD_PHASE = re.compile(r"^#{1,6}\s+Phase\s+0*(\d+)\b")
# The same shape roadmap_requirements() matches in cairn-map.py.
REQ_LINE = re.compile(r"^\*\*Requirements\*\*\s*:(.*)$")
PLAN_CHECKBOX = re.compile(r"^\s*-\s*\[([ xX])\]\s*(\d+-\d+-PLAN\.md)\b")
# The requirement -> phase -> status table has two measured homes: this
# repo's ROADMAP.md writes it under `## Cobertura`, and the GSD requirements
# template writes the same three columns under `## Traceability` in
# REQUIREMENTS.md (tests/helpers.bash's make_gsd_fixture is that shape). Both
# are read, ROADMAP first — a table living in the OTHER supported place is
# not an absent table, and reporting one missing row per requirement over it
# would be the tool answering without knowing what it is answering about.
COVERAGE_HEAD = re.compile(
    r"^##\s+(Cobertura|Coverage|Traceability|Rastreabilidade)\b",
    re.IGNORECASE)
COVERAGE_ROW = re.compile(
    r"^\|\s*([A-Za-z][A-Za-z0-9]*-\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
# Measured form is pt-BR; the English alternative is ASSUMED (see docstring).
COVERAGE_FOOTER = re.compile(
    r"^(\d+)\s+(?:requisitos?|requirements?)\s*,\s*(\d+)\s+"
    r"(?:mapeados?|mapped)")
REQ_SECTION = re.compile(r"^##\s+(.*?)\s*$")
REQ_ITEM = re.compile(
    r"^\s*-\s*(?:\[([ xX])\]\s*)?\*\*([A-Za-z][A-Za-z0-9]*-\d+)\*\*")
PHASE_DIR = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")
ELLIPSIS = re.compile(r"[A-Za-z0-9]\s*(?:…|\.\.\.)\s*[A-Za-z]")
NARRATIVE_COUNT = re.compile(r"(\d+)\s+(fases?|requisitos?)")


def die(msg, code):
    print(f"{TAG} error: {msg}", file=sys.stderr)
    sys.exit(code)


def split_eol(line):
    """(content, line ending) — the ending is preserved verbatim on write."""
    for eol in ("\r\n", "\n", "\r"):
        if line.endswith(eol):
            return line[:-len(eol)], eol
    return line, ""


def read_lines(path):
    """Lines with endings kept, and endings NOT translated.

    newline="" is load-bearing: Path.read_text() would fold CRLF into LF and
    the next write would silently rewrite every line of the file — the exact
    class of damage this script exists to avoid.
    """
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read().splitlines(keepends=True)


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("".join(lines))


def phase_checkbox_hits(lines, n):
    """[(index, state_char, content, eol)] for every checkbox line naming
    phase n."""
    hits = []
    for i, raw in enumerate(lines):
        content, eol = split_eol(raw)
        m = CHECKBOX_PHASE_LENIENT.match(content)
        if m and int(m.group(2), 10) == n:
            hits.append((i, m.group(1), content, eol, m.span(1)))
    return hits


def make_edit(path, index, before, after, reason):
    """An edit is a line replacement plus the reason it is being made.

    A bookkeeping tool that writes without saying why is the automated
    version of the same problem, so `reason` is not optional.
    """
    return {"file": str(path), "line": index + 1, "index": index,
            "before": before, "after": after, "reason": reason}


def plan_close(path, lines, n):
    """Edits that mark phase n complete in ROADMAP.md. Empty when already
    marked."""
    hits = phase_checkbox_hits(lines, n)
    if not hits:
        die(f"no checkbox line for phase {n} in {path}", EXIT_NO_PHASE)
    if len(hits) > 1:
        listed = "\n".join(f"  {path}:{i + 1}: {content}"
                           for i, _s, content, _e, _sp in hits)
        die(f"phase {n} matches {len(hits)} checkbox lines — refusing to "
            f"guess which one is the phase:\n{listed}", EXIT_USAGE)
    index, state, content, _eol, span = hits[0]
    if state.lower() == "x":
        return []
    start, end = span
    after = content[:start] + "x" + content[end:]
    return [make_edit(path, index, content, after,
                      f"phase {n} is complete; its checkbox still reads "
                      f"'[{state}]'")]


def apply_edits(path, lines, edits):
    for edit in edits:
        _content, eol = split_eol(lines[edit["index"]])
        lines[edit["index"]] = edit["after"] + eol
    write_lines(path, lines)


def emit(payload, as_json, human_lines):
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for line in human_lines:
            print(f"{TAG} {line}")


def resolve_planning_dir(arg):
    if arg:
        planning = Path(arg)
    else:
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
        planning = root / ".planning"
    if not planning.is_dir():
        die(f"planning dir not found: {planning}", EXIT_USAGE)
    return planning


def cmd_close(args):
    planning = resolve_planning_dir(args.planning_dir)
    roadmap = planning / "ROADMAP.md"
    if not roadmap.is_file():
        die(f"ROADMAP.md not found in {planning}", EXIT_USAGE)
    lines = read_lines(roadmap)
    edits = plan_close(roadmap, lines, args.phase)
    changed = False
    if edits and args.apply:
        apply_edits(roadmap, lines, edits)
        changed = True
    payload = {"phase": args.phase, "applied": bool(args.apply),
               "changed": changed,
               "planned": [{k: e[k] for k in
                            ("file", "line", "before", "after", "reason")}
                           for e in edits]}
    if edits:
        verb = "wrote" if changed else "would write"
        human = [f"{verb} {e['file']}:{e['line']}: {e['reason']}"
                 for e in edits]
        human += [f"  - {e['before']}" for e in edits]
        human += [f"  + {e['after']}" for e in edits]
    else:
        human = [f"phase {args.phase}: nothing to change"]
    emit(payload, args.json, human)
    if edits and not args.apply:
        sys.exit(EXIT_DISAGREEMENT)
    sys.exit(EXIT_OK)


def parse_roadmap(lines):
    """Everything reconcile reads out of ROADMAP.md, in one pass.

    Returns phases (checkbox authority), per-phase requirement lines and plan
    checkboxes, and the coverage table with its footer. Line numbers are kept
    on every item so a finding can cite where it came from — and so 29-02's
    write path has the position it needs without re-parsing.
    """
    out = {"phases": {}, "phase_reqs": {}, "phase_plans": {}}
    current = None
    for i, raw in enumerate(lines):
        content, _eol = split_eol(raw)
        stripped = content.strip()

        m = CHECKBOX_PHASE_LENIENT.match(content)
        if m:
            n = int(m.group(2), 10)
            entry = out["phases"].setdefault(
                n, {"complete": False, "line": i + 1, "raw": content})
            if m.group(1).lower() == "x":
                entry["complete"] = True

        m = HEAD_PHASE.match(content)
        if m:
            current = int(m.group(1), 10)
            continue
        if ANY_HEAD.match(content):
            current = None
        if current is None:
            continue

        m = REQ_LINE.match(stripped)
        if m and current not in out["phase_reqs"]:
            out["phase_reqs"][current] = {
                "line": i + 1, "raw": stripped,
                "ids": REQ_ID.findall(m.group(1))}
            continue
        m = PLAN_CHECKBOX.match(content)
        if m:
            out["phase_plans"].setdefault(current, []).append(
                {"line": i + 1, "plan": m.group(2),
                 "checked": m.group(1).lower() == "x"})
    return out


def parse_coverage(lines, path):
    """The requirement -> phase -> status table and its footer, anchored to
    the coverage heading.

    Anchoring is not decoration: unanchored, the footer regex also matched a
    line of PROSE quoting the footer inside a phase's own detail block — the
    phase's evidence about the defect being mistaken for the defect.

    Returns None when this file has no coverage section at all, which is a
    different state from "a section with no rows" and is reported as such.
    """
    inside = False
    rows, footer, head_line = [], None, None
    for i, raw in enumerate(lines):
        content, _eol = split_eol(raw)
        if COVERAGE_HEAD.match(content):
            inside = True
            head_line = i + 1
            continue
        if inside and content.startswith("## "):
            break
        if not inside:
            continue
        m = COVERAGE_ROW.match(content)
        if m:
            rows.append({"file": str(path), "line": i + 1,
                         "requirement": m.group(1), "phase": m.group(2),
                         "status": m.group(3)})
            continue
        m = COVERAGE_FOOTER.match(content.strip())
        if m and footer is None:
            footer = {"file": str(path), "line": i + 1,
                      "raw": content.strip(), "claim": int(m.group(1), 10),
                      "mapped": int(m.group(2), 10)}
    if head_line is None:
        return None
    return {"file": str(path), "heading_line": head_line, "rows": rows,
            "footer": footer}


def parse_requirements(lines):
    """Requirement ids by section: the milestone's own heading is active,
    `Deferred*` and `Out of Scope*` are the two named exclusions."""
    out = {"active": [], "deferred": [], "out_of_scope": []}
    bucket = None
    for i, raw in enumerate(lines):
        content, _eol = split_eol(raw)
        m = REQ_SECTION.match(content)
        if m:
            title = m.group(1).strip().lower()
            if title.endswith("requirements"):
                bucket = "active"
            elif title.startswith("deferred"):
                bucket = "deferred"
            elif title.startswith("out of scope"):
                bucket = "out_of_scope"
            else:
                bucket = None
            continue
        if bucket is None:
            continue
        m = REQ_ITEM.match(content)
        if m:
            state = m.group(1)
            out[bucket].append({
                "line": i + 1, "requirement": m.group(2),
                "checked": bool(state) and state.lower() == "x",
                "has_checkbox": state is not None})
    return out


def parse_state_frontmatter(lines):
    """The YAML frontmatter of STATE.md, one nesting level deep.

    THE BODY IS NEVER READ. Measured cause: `state record-session` took
    `Phase: 18` from the obsolete prose below the frontmatter and rewrote
    `current_phase: 29` backwards to a phase of an archived milestone.
    """
    out = {}
    started = False
    nested = None
    for i, raw in enumerate(lines):
        content, _eol = split_eol(raw)
        if content.strip() == "---":
            if not started and i == 0:
                started = True
                continue
            if started:
                break
        if not started:
            continue
        m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", content)
        if not m:
            continue
        indent, key, value = m.group(1), m.group(2), m.group(3).strip()
        if indent and nested:
            out[f"{nested}.{key}"] = value
        else:
            nested = key if value == "" else None
            if value != "":
                out[key] = value
    return out


def scan_phase_tree(planning):
    """{phase number: {dir, plans: [names], summaries: [names]}} — counted by
    NAME. Nothing in a plan or summary file is ever opened."""
    tree = {}
    phases = planning / "phases"
    if not phases.is_dir():
        return tree
    for d in sorted(phases.iterdir()):
        if not d.is_dir():
            continue
        m = PHASE_DIR.match(d.name)
        if not m:
            continue
        tree[int(m.group(1), 10)] = {
            "dir": d.name,
            "plans": sorted(p.name for p in d.glob("*-PLAN.md")),
            "summaries": sorted(p.name for p in d.glob("*-SUMMARY.md"))}
    return tree


def finding(kind, subject, found, expected, source, detail=None):
    item = {"kind": kind, "subject": subject, "found": found,
            "expected": expected, "source": source}
    if detail is not None:
        item["detail"] = detail
    return item


def as_int(value):
    try:
        return int(str(value).strip(), 10)
    except (TypeError, ValueError):
        return None


def reconcile(planning):
    """Read the three files and the phase tree; name every disagreement.

    Not one byte is written anywhere in this function or anything it calls.
    """
    roadmap_path = planning / "ROADMAP.md"
    reqs_path = planning / "REQUIREMENTS.md"
    state_path = planning / "STATE.md"
    for path in (roadmap_path, reqs_path, state_path):
        if not path.is_file():
            die(f"{path.name} not found in {planning}", EXIT_USAGE)

    roadmap_lines = read_lines(roadmap_path)
    reqs_lines = read_lines(reqs_path)
    road = parse_roadmap(roadmap_lines)
    reqs = parse_requirements(reqs_lines)
    frontmatter = parse_state_frontmatter(read_lines(state_path))
    tree = scan_phase_tree(planning)
    coverage = (parse_coverage(roadmap_lines, roadmap_path)
                or parse_coverage(reqs_lines, reqs_path))

    rm = str(roadmap_path)
    rq = str(reqs_path)
    st = str(state_path)
    found = []

    active = [r["requirement"] for r in reqs["active"]]
    active_set = set(active)
    checked = {r["requirement"]: r["checked"] for r in reqs["active"]}
    req_line_no = {r["requirement"]: r["line"] for r in reqs["active"]}

    # derived 1: a requirement is complete when every phase carrying it is.
    carriers = {}
    for n, block in road["phase_reqs"].items():
        for rid in block["ids"]:
            carriers.setdefault(rid, []).append(n)
    complete_phase = {n: p["complete"] for n, p in road["phases"].items()}
    derived = {}
    for rid, phases in carriers.items():
        derived[rid] = all(complete_phase.get(n, False) for n in phases)

    cov_rows = coverage["rows"] if coverage else []
    cov_footer = coverage["footer"] if coverage else None

    # --- the unreadable requirements line -----------------------------------
    table_by_phase = {}
    for row in cov_rows:
        m = re.search(r"\b0*(\d+)\b", row["phase"])
        if m:
            table_by_phase.setdefault(int(m.group(1), 10), set()).add(
                row["requirement"])
    for n in sorted(road["phase_reqs"]):
        block = road["phase_reqs"][n]
        signals = []
        if ELLIPSIS.search(block["raw"]):
            signals.append("ellipsis-between-ids")
        unseen = sorted(table_by_phase.get(n, set()) - set(block["ids"]))
        if unseen:
            signals.append("coverage-table-maps-more-ids")
        if not signals:
            continue
        found.append(finding(
            "requirements-line-unreadable", f"Phase {n}",
            block["ids"],
            None,  # never invented: the ids that SHOULD be there are unknown
            f"{rm}:{block['line']}",
            {"raw": block["raw"], "signals": signals,
             "ids_parsed": block["ids"],
             "ids_the_table_maps_here": unseen,
             "note": "reported, never expanded — turning an ellipsis into a "
                     "range assumes contiguity and assumes nothing was "
                     "removed in between"}))

    # --- derived 3: a row per active requirement ----------------------------
    row_ids = [r["requirement"] for r in cov_rows]
    row_src = {r["requirement"]: f"{r['file']}:{r['line']}" for r in cov_rows}
    if coverage is None:
        # One finding, not one per requirement. A file with no coverage
        # section anywhere does not have 35 missing rows; it has no table,
        # and saying it 35 times is the tool answering without knowing what
        # it is answering about.
        found.append(finding(
            "coverage-view-missing", "coverage table", None,
            "a '## Cobertura' section in ROADMAP.md or a '## Traceability' "
            "section in REQUIREMENTS.md", rm,
            {"active_requirements": len(active)}))
    else:
        for rid in active:
            if rid not in row_ids:
                found.append(finding(
                    "coverage-row-missing", rid, None, "a coverage table row",
                    f"{rq}:{req_line_no[rid]}"))
        for rid in row_ids:
            if rid not in active_set:
                found.append(finding(
                    "coverage-row-orphan", rid, "a coverage table row",
                    "an active requirement carrying it", row_src[rid]))

    # --- derived 2: the requirement checkbox --------------------------------
    for rid in active:
        if rid not in derived:
            continue
        if checked[rid] != derived[rid]:
            found.append(finding(
                "requirement-checkbox-stale", rid,
                "[x]" if checked[rid] else "[ ]",
                "[x]" if derived[rid] else "[ ]",
                f"{rq}:{req_line_no[rid]}",
                {"phases": sorted(carriers[rid]),
                 "phases_complete": derived[rid]}))

    # --- derived 4: the footer counts the table -----------------------------
    # No footer at all reports nothing: an absent claim is not a false claim.
    if cov_footer is not None:
        rows = len(cov_rows)
        if cov_footer["claim"] != rows or cov_footer["mapped"] != rows:
            found.append(finding(
                "footer-count-stale", "coverage footer",
                [cov_footer["claim"], cov_footer["mapped"]],
                [rows, rows], f"{cov_footer['file']}:{cov_footer['line']}",
                {"raw": cov_footer["raw"],
                 "active_requirements": len(active)}))

    # --- derived 5: a plan checkbox reflects its SUMMARY on disk ------------
    for n in sorted(road["phase_plans"]):
        summaries = set(tree.get(n, {}).get("summaries", []))
        for item in road["phase_plans"][n]:
            summary = item["plan"].replace("-PLAN.md", "-SUMMARY.md")
            on_disk = summary in summaries
            if item["checked"] != on_disk:
                found.append(finding(
                    "plan-checkbox-stale", item["plan"],
                    "[x]" if item["checked"] else "[ ]",
                    "[x]" if on_disk else "[ ]",
                    f"{rm}:{item['line']}",
                    {"summary": summary, "summary_on_disk": on_disk}))

    # --- the STATE counters, computed from disk and the roadmap only --------
    in_milestone = sorted(road["phases"])
    total_phases = len(in_milestone)
    completed_phases = sum(1 for n in in_milestone if complete_phase[n])
    total_plans = sum(len(tree.get(n, {}).get("plans", []))
                      for n in in_milestone)
    completed_plans = sum(len(tree.get(n, {}).get("summaries", []))
                          for n in in_milestone)
    computed = {
        "total_phases": total_phases,
        "completed_phases": completed_phases,
        "total_plans": total_plans,
        "completed_plans": completed_plans,
        "percent": (round(100 * completed_phases / total_phases)
                    if total_phases else 0),
        "active_requirements": len(active),
        "coverage_rows": len(cov_rows)}

    for key in ("total_phases", "completed_phases", "total_plans",
                "completed_plans", "percent"):
        declared = as_int(frontmatter.get(f"progress.{key}"))
        if declared is None or declared == computed[key]:
            continue
        found.append(finding(
            "state-counter-stale", f"progress.{key}", declared,
            computed[key], st,
            {"computed_from": "the phase checkbox lines and the file names "
                              "under .planning/phases/"}))

    desc = frontmatter.get("last_activity_desc")
    if desc:
        stated = {unit.rstrip("s"): int(num, 10)
                  for num, unit in NARRATIVE_COUNT.findall(desc)}
        expected = {"fase": total_phases, "requisito": len(active)}
        wrong = {k: v for k, v in stated.items()
                 if k in expected and v != expected[k]}
        if wrong:
            found.append(finding(
                "state-narrative-stale", "last_activity_desc", desc,
                {k: expected[k] for k in wrong}, st,
                {"note": "free text nobody recalculates — reported, and this "
                         "command does not propose to rewrite it"}))

    return {
        "requirements": {
            "active": active,
            "deferred": [r["requirement"] for r in reqs["deferred"]],
            "out_of_scope": [r["requirement"] for r in reqs["out_of_scope"]]},
        "coverage": {
            "rows": len(cov_rows),
            "source": coverage["file"] if coverage else None,
            "footer_claim": cov_footer["claim"] if cov_footer else None},
        "phases": {
            "complete": [n for n in in_milestone if complete_phase[n]],
            "open": [n for n in in_milestone if not complete_phase[n]],
            "detail": {
                str(n): {
                    "complete": complete_phase[n],
                    "requirements": road["phase_reqs"].get(
                        n, {}).get("ids", []),
                    "plans": len(tree.get(n, {}).get("plans", [])),
                    "summaries": len(tree.get(n, {}).get("summaries", []))}
                for n in in_milestone}},
        "state": {"frontmatter": frontmatter, "computed": computed},
        "disagreements": found}


def cmd_reconcile(args):
    planning = resolve_planning_dir(args.planning_dir)
    result = reconcile(planning)
    found = result["disagreements"]
    human = [f"{f['kind']} :: {f['subject']} :: found {f['found']!r}, "
             f"expected {f['expected']!r} ({f['source']})" for f in found]
    if result["requirements"]["deferred"]:
        human.append("deferred (out of the table by rule, not a "
                     "disagreement): "
                     + ", ".join(result["requirements"]["deferred"]))
    human.append(f"{len(found)} disagreement(s)")
    emit(result, args.json, human)
    sys.exit(EXIT_DISAGREEMENT if found else EXIT_OK)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairn-bookkeep.py",
        description="read the planning files, name every disagreement, and "
                    "edit only the lines that have to change")
    sub = parser.add_subparsers(dest="command", required=True)

    close = sub.add_parser("close", help="mark a phase's ROADMAP checkbox "
                                         "complete")
    close.add_argument("phase", type=int, help="phase number")
    close.add_argument("--apply", action="store_true",
                       help="write the planned edits (default: read only)")
    close.add_argument("--json", action="store_true",
                       help="machine-readable output")
    close.add_argument("--planning-dir", metavar="DIR",
                       help="planning dir (default: $CLAUDE_PROJECT_DIR or "
                            "cwd, plus /.planning)")
    close.set_defaults(func=cmd_close)

    # No --apply here, deliberately: reconcile in this plan reads and names.
    # Resolving is plan 29-02, and a flag that exists before its behavior
    # does is the defect this phase removes.
    rec = sub.add_parser("reconcile", help="name every disagreement between "
                                           "the planning files and the disk")
    rec.add_argument("--json", action="store_true",
                     help="machine-readable output")
    rec.add_argument("--planning-dir", metavar="DIR",
                     help="planning dir (default: $CLAUDE_PROJECT_DIR or "
                          "cwd, plus /.planning)")
    rec.set_defaults(func=cmd_reconcile)
    return parser


def main(argv):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
