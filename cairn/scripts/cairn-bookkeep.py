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

    MEASURED (2026-08-03, .planning/ROADMAP.md at 3863d73):
      - the ten phase checkbox lines are `- [ ] Phase <N>: <title> (<reqs>)`,
        one of them already `- [x] ... — completed 2026-08-03` (phase 20);
      - the whole-file lenient scan matches those ten lines and no others;
      - `git diff --quiet HEAD -- .planning/{ROADMAP,REQUIREMENTS,STATE}.md`
        exits 0, so the fixture captured from them is a committed state.

    ASSUMED (not measured here, and deliberately not relied on):
      - that other GSD projects use the same checkbox wording. The regex is
        lenient precisely because that is an assumption; the phase NUMBER is
        the only thing it treats as load-bearing.
      - that a planning file might arrive with CRLF endings. No such file was
        seen in this repo; the newline="" handling costs nothing and removes
        the assumption instead of resting on it.

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
    return parser


def main(argv):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
