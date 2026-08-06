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


def field_survey(cycles):
    """Which frontmatter keys every comparable cycle carries, and which ones
    only some do.

    The intersection is over CYCLES, not over files: `gaps` is in two of
    v1.1's six files, and that is enough — the cycle knows how to record
    gaps. A key present in one cycle only is not a trend, it is a dialect,
    and this is the survey that says which is which. Nothing here is written
    down: it is recomputed from disk on every run.
    """
    per_cycle = {}
    for c in cycles:
        if c["state"] != COMPARABLE:
            continue
        keys = set()
        for e in c["entries"]:
            keys.update(e["keys"])
        per_cycle[c["cycle"]] = keys
    if not per_cycle:
        return {"intersection": [], "missing_from": {}, "per_cycle": {}}
    inter = set.intersection(*per_cycle.values())
    union = set().union(*per_cycle.values())
    missing = {}
    for k in sorted(union - inter):
        missing[k] = sorted((cy for cy, ks in per_cycle.items()
                             if k not in ks), key=version_sort_key)
    return {
        "intersection": sorted(inter),
        "missing_from": missing,
        "per_cycle": {k: sorted(v) for k, v in per_cycle.items()},
    }


# How to aggregate a field, NOT which fields exist. Which fields exist is the
# intersection, recomputed from disk; an axis whose field is missing from it
# is not computed at all and the output says where it is missing.
AXIS_SPECS = (
    ("first_pass", "status", "primeira aprovação"),
    ("gaps", "gaps", "lacunas registradas"),
    ("gap_density", "gaps", "lacunas por fase"),
    ("overrides", "overrides_applied", "overrides aplicados"),
    # Computed only when score_survey() finds one unit across every
    # comparable cycle. Otherwise it is refused, with the units it found.
    ("score", "score", "score"),
)


def axis_point(axis_id, cycle):
    """(value, formatted) for one cycle on one axis, or None when the cycle
    carries nothing to compute it from."""
    entries = [e for e in cycle["entries"] if e["status"]]
    denom = len(entries)
    if axis_id == "first_pass":
        if not denom:
            return None
        value = sum(1 for e in entries if e["status"] == "passed") / denom
        return value, f"{round(value * 100)}%"
    if axis_id in ("gaps", "gap_density"):
        counted = [e["gaps"] for e in entries if e["gaps"] is not None]
        if not counted:
            return None
        total = sum(counted)
        if axis_id == "gaps":
            return total, str(total)
        return total / denom, f"{total / denom:.2f}"
    if axis_id == "overrides":
        counted = [e["overrides_applied"] for e in entries
                   if e["overrides_applied"] is not None]
        if not counted:
            return None
        return sum(counted), str(sum(counted))
    if axis_id == "score":
        ratios = [e["score_ratio"] for e in entries if e["score_ratio"]]
        if not ratios:
            return None
        num = sum(r[0] for r in ratios)
        den = sum(r[1] for r in ratios)
        if not den:
            return None
        return num / den, f"{num}/{den}"
    return None


def direction_of(values):
    """(direction, monotonic). Both, because an axis that falls, rises and
    falls again is not the same shape as one that only falls, and a single
    word would erase the difference. Monotonic here is non-strict: every step
    goes the same way or stands still."""
    if len(values) < 2:
        return "flat", True
    first, last = values[0], values[-1]
    direction = "flat"
    if last > first:
        direction = "rising"
    elif last < first:
        direction = "falling"
    deltas = [b - a for a, b in zip(values, values[1:])]
    monotonic = all(d >= 0 for d in deltas) or all(d <= 0 for d in deltas)
    return direction, monotonic


DIRECTION_LABEL = {"rising": "sobe", "falling": "desce", "flat": "constante"}


def score_survey(cycles):
    """Whether `score` may be aggregated, and the measured reason when it may
    not.

    `score` is in the intersection — every file carrying frontmatter has one,
    which makes it look ready to plot. It is not: the denominator's UNIT
    changes between cycles and, in v1.4, inside one cycle. Plotting it would
    draw a line between two different rulers, which is the same class of
    error this whole phase exists to avoid, one floor down.

    The refusal is data and not prose: it carries the distinct units it FOUND
    on disk, so the day every cycle counts the same thing the refusal lifts
    on its own.
    """
    per_cycle = {}
    for c in cycles:
        if c["state"] != COMPARABLE:
            continue
        units = sorted({e["score_unit"] for e in c["entries"]
                        if e["score_unit"]})
        if units:
            per_cycle[c["cycle"]] = units
    distinct = sorted({u for units in per_cycle.values() for u in units})
    survey = {
        "units_by_cycle": per_cycle,
        "distinct_units": distinct,
        "units_line": " · ".join(
            f"{cy}: {', '.join(us)}"
            for cy, us in sorted(per_cycle.items(),
                                 key=lambda kv: version_sort_key(kv[0]))),
    }
    if len(distinct) <= 1:
        survey["aggregated"] = True
        survey["reason"] = ("uma unidade só em todos os ciclos comparáveis — "
                            "as frações se comparam")
    else:
        survey["aggregated"] = False
        survey["reason"] = ("as unidades do denominador diferem entre os "
                            "ciclos comparáveis — as frações não se comparam")
    return survey


def build_series(cycles, survey, score):
    """The series proper: shape, sufficiency, contiguity, and one entry per
    axis the intersection actually supports."""
    comparable = [c for c in cycles if c["state"] == COMPARABLE]
    keys = [c["cycle"] for c in comparable]
    span, holes, contiguous = 0, 0, True
    if comparable:
        idx = [i for i, c in enumerate(cycles) if c["state"] == COMPARABLE]
        span = idx[-1] - idx[0] + 1
        holes = span - len(idx)
        contiguous = holes == 0
    sufficient = len(comparable) >= MIN_SERIES_POINTS
    axes, unavailable = [], []
    for axis_id, field, label in AXIS_SPECS:
        if field not in survey["intersection"]:
            unavailable.append({
                "axis": axis_id,
                "field": field,
                "label": label,
                "missing_from": survey["missing_from"].get(field, []),
            })
            continue
        if axis_id == "score" and not score["aggregated"]:
            continue
        points = [axis_point(axis_id, c) for c in comparable]
        if any(p is None for p in points):
            unavailable.append({
                "axis": axis_id,
                "field": field,
                "label": label,
                "missing_from": [k for k, p in zip(keys, points)
                                 if p is None],
            })
            continue
        values = [p[0] for p in points]
        formatted = [p[1] for p in points]
        direction, monotonic = direction_of(values)
        axes.append({
            "axis": axis_id,
            "field": field,
            "label": label,
            "cycles": keys,
            "values": values,
            "formatted": formatted,
            "points_line": " → ".join(formatted),
            "direction": direction if sufficient else None,
            "direction_label": DIRECTION_LABEL[direction] if sufficient
            else None,
            "monotonic": monotonic if sufficient else None,
        })
    shape = (f"{len(comparable)} pontos comparáveis em {span} ciclos, "
             f"{holes} vãos — "
             f"{'contígua' if contiguous else 'não contígua'}")
    if not comparable:
        shape = "nenhum ciclo comparável"
    return {
        "points": len(comparable),
        "min_points": MIN_SERIES_POINTS,
        "span": span,
        "holes": holes,
        "contiguous": contiguous,
        "sufficient": sufficient,
        "shape_line": shape,
        "axes": axes,
        "unavailable_axes": unavailable,
        "score": score,
    }


def build_model(planning_dir):
    """Everything the renderer will ever need, INCLUDING the formatted
    strings.

    The renderer computes nothing — not a division, not a rounding, not a
    count. That is not fastidiousness: it is what makes "no number in the
    prose was typed by hand" a mechanically checkable claim, since every
    token the human output prints can then be found as a value in --json.
    TREND-02 is the reason this phase exists, and an unprovable claim about
    it would be the fourth hand-typed count in this repository's history.
    """
    cycles = [classify(scan_cycle(c)) for c in discover_cycles(planning_dir)]
    for c in cycles:
        c["status_counts"] = status_counts(c)
        c["coverage"] = f"{c['with_verdict']}/{c['phase_dirs']}"
        c["status_line"] = " · ".join(
            f"{k} {v}" for k, v in sorted(c["status_counts"].items()))
        c.pop("phases_dir", None)
    survey = field_survey(cycles)
    score = score_survey(cycles)
    return {
        "planning_dir": str(planning_dir),
        "cycles": cycles,
        "comparable": [c["cycle"] for c in cycles if c["state"] == COMPARABLE],
        "open_cycle": next((c["cycle"] for c in cycles if c["open"]), None),
        "fields": survey,
        "series": build_series(cycles, survey, score),
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
    # No cycle at all is a repository that has not closed one — the
    # convention's genuine "this repo doesn't need this check", exit 0. A
    # repository WITH cycles but too few comparable ones is the roadmap's
    # criterion 3, and gets its own code so a caller can branch on it.
    if model["cycles"] and not model["series"]["sufficient"]:
        sys.exit(EXIT_INSUFFICIENT)
    sys.exit(EXIT_OK)


def render(model):
    """Position strings the model already produced. Widths are layout, not
    data — no value printed here is computed here."""
    lines = [f"{TAG} discordância entre ciclos — {model['planning_dir']}"]
    if not model["cycles"]:
        lines.append(f"{TAG} {SYMBOL[NOT_APPLICABLE]} nenhum ciclo "
                     f"encontrado — nem milestone arquivado nem ciclo "
                     f"corrente no ROADMAP")
        return lines
    width = max(len(c["cycle"]) for c in model["cycles"])
    lines.append(TAG)
    for c in model["cycles"]:
        key = c["cycle"].ljust(width)
        mark = SYMBOL[c["state"]]
        if c["state"] == COMPARABLE:
            # Coverage AND the per-status breakdown, so nothing has to be
            # inferred from a single ratio.
            lines.append(f"{TAG} {mark} {key}  veredito em {c['coverage']} "
                         f"fases   {c['status_line']}")
        else:
            # Never a zero, never an empty cell, never a dash that reads as
            # "approved nothing": the scope IS the value here, and the
            # difference between "did not pass" and "was not checked that
            # way" has to be legible without opening the JSON.
            lines.append(f"{TAG} {mark} {key}  {NOT_APPLICABLE} / {c['scope']}")
            lines.append(f"{TAG}   {' ' * width}  {c['detail']}")
    if model["open_cycle"]:
        lines.append(TAG)
        lines.append(f"{TAG} ! {model['open_cycle']} está em andamento: a "
                     f"cobertura dele conta fases que ainda não começaram, "
                     f"então não se compara com a de um ciclo fechado.")
    lines.extend(render_series(model))
    return lines


def render_series(model):
    series = model["series"]
    lines = [TAG, f"{TAG} ▸ série: {series['shape_line']}"]
    if not series["sufficient"]:
        # Roadmap success criterion 3: say so, and do NOT draw a line. Two
        # points define a line every time, so a direction over fewer than
        # MIN_SERIES_POINTS cannot tell a trend from a pair of values.
        lines.append(f"{TAG} ! menos de {series['min_points']} pontos "
                     f"comparáveis: nenhuma direção é declarada.")
        for c in model["cycles"]:
            if c["state"] != COMPARABLE:
                lines.append(f"{TAG}   {c['cycle']} não entra na série: "
                             f"{c['scope']} — {c['detail']}")
        return lines
    width = max((len(a["label"]) for a in series["axes"]), default=0)
    for axis in series["axes"]:
        mark = "" if axis["monotonic"] else "  (não monotônica)"
        lines.append(f"{TAG} ▸ {axis['label'].ljust(width)}  "
                     f"{axis['points_line']}   "
                     f"{axis['direction_label']}{mark}")
    for miss in series["unavailable_axes"]:
        lines.append(f"{TAG} {SYMBOL[NOT_APPLICABLE]} {miss['label']} não "
                     f"vira série: `{miss['field']}` falta em "
                     f"{', '.join(miss['missing_from'])}")
    score = series["score"]
    if not score["aggregated"]:
        lines.append(f"{TAG} {SYMBOL[NOT_APPLICABLE]} score não vira série: "
                     f"{score['reason']}")
        lines.append(f"{TAG}   {score['units_line']}")
    return lines


if __name__ == "__main__":
    main()
