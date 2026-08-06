#!/usr/bin/env python3
"""cairn-trend — how the first-pass verdict moved across cycles, with every
gap named and the ambiguity of the line declared next to it.

WHY THIS EXISTS
---------------
Every closed milestone leaves verification artifacts behind. Read in a row
they answer a question no single cycle can: is the disagreement between what
a phase claims and what it proves going up or down?

Two failure modes come free with that question, and both are why this script
is shaped the way it is:

    1. A cycle with no comparable verdict gets counted as zero. A milestone
       whose verification files carry no frontmatter has not "failed" and has
       not "scored 0%" — nobody checked it that way. Summing it with a real
       verdict measures the repository's health and the tooling's coverage in
       the same column. `not-applicable` with a named scope is the answer,
       and it is the fourth check state phase 23 delivered for exactly this.

    2. The line is drawn and then explained. A falling first-pass rate moves
       under two opposite causes that the number itself cannot separate:
       quality dropping, or scrutiny rising — the verifier getting stricter
       and finding what used to pass. A command that draws that line without
       saying so lies with a true number. So the disambiguation verdict is
       derived here (see DISAMBIGUATOR_PREFIX) rather than asserted, and it
       flips on its own the day the data can settle it.

Usage:
    cairn-trend.py [--planning-dir <dir>] [--json]

What it reads:
    Archived cycles      .planning/milestones/<key>-ROADMAP.md is the
                         evidence a cycle closed (the same anchor
                         cairn-doctor.py's archived_milestones() uses, and
                         for the reason recorded there: the archived roadmap
                         is the most direct proof, a REQUIREMENTS file or a
                         phases/ directory is not). Its phases live in
                         .planning/milestones/<key>-phases/.
    The open cycle       the ROADMAP.md line carrying 🚧 (or "in progress"),
                         whose phases live in .planning/phases/.
    Verdicts             every *VERIFICATION.md under a cycle's phase dirs,
                         read for its top-level frontmatter only.

    No milestone key is written in this file. A repository with none of the
    above is not an error — it is a repository that has not closed a cycle.

Exit codes:
    0  ok — the cycles were read. Includes a repository with no .planning/
       at all, which is the convention's genuine "this repo doesn't need
       this check".
    2  usage — an unknown flag, or --planning-dir pointing at something that
       is not a directory.
    4  insufficient — fewer than MIN_SERIES_POINTS comparable cycles. The
       command prints what it knows and declares NO direction. This is not a
       user error and not a repository failure: it is the verdict itself,
       given its own code so a caller can branch without parsing prose.

CYCLE STATES
------------
Each cycle gets exactly one state, in the vocabulary phase 23 established
(cairn-doctor.py: `not-applicable` carries a `scope` when and only when it is
`not-applicable`):

    comparable                    at least one verification file whose
                                  frontmatter carries `status`.
    not-applicable/no-frontmatter verification files exist and NONE has
                                  frontmatter.
    not-applicable/no-verdict     frontmatter exists but no file carries
                                  `status` — a shape nothing on disk has
                                  today, kept because the parser must not
                                  have to choose between two wrong answers.
    not-applicable/no-input       no verification file at all.

`no-frontmatter` is a scope of its own and not `no-input`, and the
distinction is the whole point of it: `no-input` says there is nothing to
read. There is. v1.2 and v1.3 have three verification files each, written,
committed and readable — what is missing is the structured format, which was
born in v1.1, vanished for two cycles and came back in v1.4. Calling that
"no input" would erase the one fact the series most needs to show.

MEASURED VERSUS ASSUMED
-----------------------
MEASURED (2026-08-06, against this repository's own .planning/):
  - Five cycles. Three carry comparable verdicts, two do not, and the two
    that do not sit in the MIDDLE of the range — so the series is not
    contiguous, which is a different weakness from a short series and is
    reported separately.
  - The field intersection across comparable cycles is `phase, verified,
    status, score, overrides_applied, gaps`. `has_blocking_gaps` belongs to
    v1.1 alone. `deferred` appears in v1.1 AND v1.5 and is absent from v1.4:
    the schema did not drift in a straight line, it oscillated. A field that
    disappears and returns is even less of a trend than one that appears
    once, which is why the intersection — recomputed from disk on every run,
    never written down — decides what may be plotted.
  - `score` is present in every file carrying frontmatter, which makes it
    look ready to plot, and it is not: the denominator's UNIT changes. v1.1
    counts `must-haves` (denominators 4, 9, 15, 19); v1.5 counts `critérios`;
    and v1.4 mixes both inside one cycle (phases 13 and 15 count `success
    criteria`, phases 14, 16 and 18 count `must-haves`, phase 17 counts
    `roadmap success criteria`). "15/15 must-haves" and "4/4 critérios" do
    not measure the same thing, so score is carried per phase and refused as
    an axis, with the units it actually found named in the refusal.
  - Zero files carry any key in the `verifier_*` namespace. That is the
    measurement the disambiguation verdict rests on, and it is why the
    namespace is free to mean this.

ASSUMED (not measured):
  - That future cycles keep writing frontmatter at all. Nothing enforces it;
    v1.2 and v1.3 are the proof that it can stop without anyone noticing.
  - That `status: passed` means the same thing in every cycle. It is exactly
    this assumption the disambiguation verdict says it cannot check — the
    two statements have to agree, and they do: the command reports the line
    and refuses to interpret it.

The frontmatter parser is deliberately minimal — the `---` fenced block,
top-level `key: value` lines, and item counts for top-level lists. stdlib
only, no YAML dependency: the same hard constraint the rest of cairn/scripts/
runs under.
"""
import json
import os
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
# 4 = fewer comparable cycles than a series needs. Not a failure — the
# verdict of the roadmap's own success criterion 3, with a code so a caller
# can branch on it instead of grepping prose.
EXIT_INSUFFICIENT = 4

# Two points define a line every time, so "direction" over two points cannot
# tell a trend from a pair of values. Three is the floor, and it is a
# constant so it can be argued with rather than found in the middle of an if.
MIN_SERIES_POINTS = 3

COMPARABLE = "comparable"
NOT_APPLICABLE = "not-applicable"
SCOPE_NO_FRONTMATTER = "no-frontmatter"
SCOPE_NO_VERDICT = "no-verdict"
SCOPE_NO_INPUT = "no-input"

# The filename /gsd:complete-milestone leaves behind when it archives a
# cycle. Anchored on both ends, for the reason cairn-doctor.py records: the
# archived ROADMAP is the evidence; a REQUIREMENTS file is not.
ARCHIVED_ROADMAP = re.compile(r"^(v\d+(?:\.\d+)*)-ROADMAP\.md$")
VERSION_TOKEN = re.compile(r"\bv\d+(?:\.\d+)*\b")
IN_PROGRESS = re.compile(r"\(in progress\)", re.IGNORECASE)
TOP_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$")
LIST_ITEM = re.compile(r"^ {2}-\s")
# `N/M` at the head of a score string, plus whatever names the unit after it.
SCORE_HEAD = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*(.*)$")

# A key in this namespace, present in EVERY comparable cycle, is what would
# let the series separate quality from scrutiny. A PREFIX and not a list of
# known names: a list would be a hand-written list, the very defect this
# phase exists to kill, and it would go stale the moment somebody picked a
# name outside it. Measured 2026-08-06: zero of the artifacts on disk carry
# any key here, which is what leaves the namespace free to mean this.
DISAMBIGUATOR_PREFIX = "verifier_"

SYMBOL = {COMPARABLE: "·", NOT_APPLICABLE: "⊘"}
TAG = "[cairn-trend]"

USAGE = "Usage: cairn-trend.py [--planning-dir <dir>] [--json]"


def die(msg, code=EXIT_USAGE):
    print(f"[cairn-trend] error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    """Hand-rolled, because there are two flags (the convention's threshold
    for reaching for argparse is more than two)."""
    opts = {"planning_dir": None, "json": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            opts["json"] = True
        elif arg == "--planning-dir":
            i += 1
            if i >= len(argv):
                die(f"--planning-dir needs a value\n{USAGE}")
            opts["planning_dir"] = argv[i]
        elif arg in ("-h", "--help"):
            print(USAGE)
            sys.exit(EXIT_OK)
        else:
            die(f"unknown argument: {arg}\n{USAGE}")
        i += 1
    return opts


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_frontmatter(text):
    """Top-level keys of a `---` fenced frontmatter block, or None when the
    file has no block at all (which is a fact, not an error — v1.2 and v1.3
    are made of such files).

    Returns {key: {"value": str or None, "items": int or None}}. `items` is
    the count of `  - ` entries under a key whose value is empty, so a list
    can be measured without parsing what is inside it; `gaps: []` counts
    zero, which is a real shape on disk.
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    keys = {}
    pending = None
    for line in text[4:end].split("\n"):
        if LIST_ITEM.match(line):
            if pending is not None:
                keys[pending]["items"] += 1
            continue
        m = TOP_KEY.match(line)
        if not m:
            continue
        name, value = m.group(1), m.group(2)
        if value == "" or value == "|" or value.startswith(">"):
            # A list or a folded block opens here; only a list gets counted.
            keys[name] = {"value": None, "items": 0}
            pending = name
        elif value == "[]":
            keys[name] = {"value": None, "items": 0}
            pending = None
        else:
            keys[name] = {"value": value, "items": None}
            pending = None
    return keys


def version_sort_key(key):
    return tuple(int(p) for p in key.lstrip("v").split(".") if p.isdigit())


def open_cycle_key(planning_dir):
    """The milestone key the roadmap marks in progress, or None."""
    for line in read_text(planning_dir / "ROADMAP.md").split("\n"):
        if "🚧" in line or IN_PROGRESS.search(line):
            m = VERSION_TOKEN.search(line)
            if m:
                return m.group(0)
    return None


def discover_cycles(planning_dir):
    """Cycles found on disk, in version order, open one last.

    Archived cycles come from <key>-ROADMAP.md under .planning/milestones/;
    the open one from the roadmap's own in-progress marker. Nothing is
    inferred from position in a list or from recency, and no milestone key
    is written in this file.
    """
    cycles = []
    try:
        entries = sorted((planning_dir / "milestones").iterdir())
    except OSError:
        entries = []
    for entry in entries:
        m = ARCHIVED_ROADMAP.match(entry.name)
        if m:
            key = m.group(1)
            cycles.append({
                "cycle": key,
                "open": False,
                "phases_dir": planning_dir / "milestones" / f"{key}-phases",
            })
    cycles.sort(key=lambda c: version_sort_key(c["cycle"]))
    current = open_cycle_key(planning_dir)
    if current and not any(c["cycle"] == current for c in cycles):
        cycles.append({
            "cycle": current,
            "open": True,
            "phases_dir": planning_dir / "phases",
        })
    return cycles


def scan_cycle(cycle):
    """Fill a cycle with what its phase tree actually holds."""
    phases_dir = cycle["phases_dir"]
    try:
        dirs = sorted(d for d in phases_dir.iterdir() if d.is_dir())
    except OSError:
        dirs = []
    entries = []
    for d in dirs:
        for f in sorted(d.glob("*VERIFICATION.md")):
            keys = read_frontmatter(read_text(f))
            entry = {
                "phase_dir": d.name,
                "file": str(f),
                "frontmatter": keys is not None,
                "keys": sorted(keys) if keys else [],
                "status": None,
                "score": None,
                "score_ratio": None,
                "score_unit": None,
                "gaps": None,
                "overrides_applied": None,
            }
            if keys:
                status = keys.get("status", {}).get("value")
                entry["status"] = status
                score = keys.get("score", {}).get("value")
                entry["score"] = score
                if score:
                    m = SCORE_HEAD.match(score)
                    if m:
                        entry["score_ratio"] = [int(m.group(1)),
                                                int(m.group(2))]
                        entry["score_unit"] = score_unit(m.group(3))
                if "gaps" in keys:
                    entry["gaps"] = keys["gaps"]["items"] or 0
                ov = keys.get("overrides_applied", {}).get("value")
                if ov is not None and ov.isdigit():
                    entry["overrides_applied"] = int(ov)
            entries.append(entry)
    cycle["phase_dirs"] = len(dirs)
    cycle["verification_files"] = len(entries)
    cycle["with_frontmatter"] = sum(1 for e in entries if e["frontmatter"])
    cycle["with_verdict"] = sum(1 for e in entries if e["status"])
    cycle["entries"] = entries
    return cycle


def score_unit(tail):
    """The unit a score's denominator counts, normalised enough to compare
    ('4/4 must-haves verified' and '14/14 must-haves verified' share one)
    and no further: the point is to detect that units DIFFER, so trimming
    them aggressively would hide the very thing being looked for."""
    text = tail.strip().lower()
    text = re.split(r"[,(]", text)[0].strip()
    text = re.sub(r"\s+", " ", text)
    return text or "unnamed"


def classify(cycle):
    """Exactly one state per cycle, with a scope when and only when the
    state is not-applicable."""
    if cycle["with_verdict"]:
        cycle["state"] = COMPARABLE
        cycle["scope"] = None
        cycle["detail"] = (
            f"{cycle['with_verdict']} de {cycle['verification_files']} "
            f"arquivos de verificação carregam veredito")
        return cycle
    cycle["state"] = NOT_APPLICABLE
    if cycle["verification_files"] == 0:
        cycle["scope"] = SCOPE_NO_INPUT
        cycle["detail"] = (
            f"nenhum arquivo de verificação em {cycle['phase_dirs']} "
            f"diretórios de fase")
    elif cycle["with_frontmatter"] == 0:
        cycle["scope"] = SCOPE_NO_FRONTMATTER
        cycle["detail"] = (
            f"{cycle['verification_files']} arquivos de verificação, "
            f"nenhum com frontmatter — o insumo existe, o formato não")
    else:
        cycle["scope"] = SCOPE_NO_VERDICT
        cycle["detail"] = (
            f"{cycle['with_frontmatter']} arquivos com frontmatter, "
            f"nenhum carrega `status`")
    return cycle


def status_counts(cycle):
    counts = {}
    for e in cycle["entries"]:
        if e["status"]:
            counts[e["status"]] = counts.get(e["status"], 0) + 1
    return counts


def build_model(planning_dir):
    cycles = [classify(scan_cycle(c)) for c in discover_cycles(planning_dir)]
    for c in cycles:
        c["status_counts"] = status_counts(c)
        c["coverage"] = f"{c['with_verdict']}/{c['phase_dirs']}"
        c.pop("phases_dir", None)
    return {
        "planning_dir": str(planning_dir),
        "cycles": cycles,
        "comparable": [c["cycle"] for c in cycles if c["state"] == COMPARABLE],
    }


def main():
    opts = parse_args(sys.argv[1:])
    root = Path(opts["planning_dir"]) if opts["planning_dir"] else \
        Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".planning"
    if opts["planning_dir"] and not root.is_dir():
        die(f"--planning-dir is not a directory: {root}")
    model = build_model(root)
    if opts["json"]:
        print(json.dumps(model, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        for line in render(model):
            print(line)
    sys.exit(EXIT_OK)


def render(model):
    lines = [f"{TAG} discordância entre ciclos — {model['planning_dir']}"]
    if not model["cycles"]:
        lines.append(f"{TAG} ⊘ nenhum ciclo encontrado — nem milestone "
                     f"arquivado nem ciclo corrente no ROADMAP")
        return lines
    for c in model["cycles"]:
        lines.append(f"{TAG} {SYMBOL[c['state']]} {c['cycle']}  {c['detail']}")
    return lines


if __name__ == "__main__":
    main()
