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
    cairn-bookkeep.py close <phase-number> [--apply] [--no-tracker] [--json]
                            [--planning-dir <dir>]
    cairn-bookkeep.py reconcile [--apply] [--json] [--planning-dir <dir>]

    --apply           write the planned edits (default: read only)
    --no-tracker      do the file half only: skip the map refresh and the
                      lease release, and say in the report what did not run
    --json            machine-readable output instead of human lines
    --planning-dir    planning dir (default: $CLAUDE_PROJECT_DIR or cwd,
                      plus /.planning). The project root the tracker and the
                      config resolve from is this directory's parent — one
                      flag, not two that can point at different repos.

    CAIRN_NOW         the determinism seam, same shape as the other CAIRN_*
                      seams: unset means the real clock, set means exactly
                      what it says (`2026-08-04` or a full ISO stamp). A
                      value that does not start with YYYY-MM-DD is a usage
                      error rather than a garbage date written into three
                      files.

Reading is the default; writing needs the named --apply flag. That is the
house pattern (cairn-doctor.py's --apply-reconciliation) and it is what keeps
an autonomous loop from writing by accident.

Behavior:

    close <N>   The whole end-of-phase bookkeeping, in one invocation:

                  1. phase N's checkbox line in ROADMAP.md -> `[x]`, plus
                     the `— completed <date>` suffix a closed phase line
                     carries (the form measured on phase 20);
                  2. the checkbox of every requirement all of whose phases
                     are now complete, in REQUIREMENTS.md;
                  3. those requirements' status cell in the coverage table
                     -> `Complete`, and a row for an active requirement that
                     has none — inserted at the end of its phase's group, so
                     the file's existing grouping survives;
                  4. the coverage footer, recounted;
                  5. each `NN-MM-PLAN.md` checkbox whose `NN-MM-SUMMARY.md`
                     is on disk;
                  6. the STATE.md frontmatter counters, and only the keys
                     listed under THE STATE KEYS below;
                  7. the phase's generated map (cairn-map.py <N>) and its
                     lease (cairn-lease.py release <N>), each by INVOKING
                     the script that owns it.

                Without --apply, prints the edits it would make and exits
                EXIT_DISAGREEMENT (3) when there is at least one, EXIT_OK
                (0) when there is none. With --apply, writes and exits 0.
                Running it twice writes nothing the second time — measured
                by sha256 AND mtime, because a byte-identical rewrite is
                still a write.

    reconcile   Read the three planning files and the phase tree and NAME
                every disagreement between them; exits EXIT_DISAGREEMENT
                (3) when it found any, 0 when it did not, and writes
                nothing.

                With --apply, makes edits 2 to 5 above and the counters,
                WITHOUT marking any phase complete: the way to resolve drift
                that already exists without pretending a phase just closed.

IT ONLY EVER MOVES A VIEW TO "DONE" — THE OTHER DIRECTION IS REPORTED
    Marking something complete is corroborated by an artifact that exists: a
    checked phase, a SUMMARY file on disk. Unmarking asserts an ABSENCE, and
    an absence has many causes — a branch not merged yet, a rename, a phase
    split, a file that will land in ten minutes. So a view that is AHEAD of
    its authority (a requirement checked while one of its phases is open, a
    plan checked with no SUMMARY, a row reading Complete under an open
    phase) is reported as `*-ahead` in `unresolved` and left alone. This is
    the one asymmetry in the derivation rule and it is deliberate: a
    bookkeeper that can silently un-complete work is worse than one that
    cannot finish.

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
      derived 4   the coverage footer's `N requisitos, N mapeados.` states
                  TWO quantities: how many requirements are active, and how
                  many of them the table maps.

                  THIS CORRECTS 29-01's RULE 4, which read both numbers as
                  the table's row count. Under that reading the footer is
                  self-consistent with the table by construction — it can
                  never contradict REQUIREMENTS.md, and a number that cannot
                  be wrong is not a check. It would also have this command
                  WRITE `33 requisitos` into a file whose requirements
                  section holds 35, which is the automated version of the
                  defect the phase exists to remove. Read as written, the
                  footer says where the gap is: `35 requisitos, 33
                  mapeados.`;
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

THE FOOTER IS FOUND BY POSITION, AND SEARCHING FOR ITS TEXT DESTROYS THE
PROOF THIS PHASE RESTS ON
    Measured 2026-08-04: `grep -n "requisitos, .*mapeados" ROADMAP.md`
    matches TWO lines. 568 is the footer. 440 is the prose of success
    criterion 5 quoting the wrong footer between quotes and bold, indented
    three spaces inside a list item — the measurement that justifies this
    whole phase, and the acceptance evidence 29-07 reads. A `re.sub` over
    the file rewrites it on the FIRST pass; idempotence saves nothing from
    that, because the damage is done before the second run exists.

    So the footer is located structurally: walk from the `## Cobertura`
    heading to the last consecutive table row, then take the WHOLE-LINE
    match that follows it inside the same section (no indentation, no `**`,
    nothing before the first digit). Line 440 is neither in that interval
    nor a whole-line match. Zero matches means no footer and raises nothing;
    two matches inside the interval is EXIT_USAGE naming both — never "take
    the first", the same posture the phase anchor takes.

A ROW IS NEVER INVENTED FOR A REQUIREMENT WITH NO READABLE CARRIER
    A new coverage row needs a phase for its middle cell, and the only
    readable source of that is the phase's `**Requirements**:` line.
    Measured here: AUTO-05 and AUTO-06 are active, have no row, and appear
    on NO phase's requirements line, because phase 29's is the ellipsis. The
    tempting inference — every other AUTO-* row says Phase 29, so these two
    are Phase 29 — is a pattern, not a source, and it is the same move as
    expanding `AUTO-01 … AUTO-08` into eight ids. So the row is not written:
    `coverage-row-missing` stays in `unresolved` with `blocked_by` naming
    the cause and the phases whose requirements line is unreadable. Write
    the ids out on that line and the row plans itself on the next run.

THE STATE KEYS, EXHAUSTIVELY, AND WHY NO NEW ONE IS EVER CREATED
    Written: current_phase, current_phase_name (close only),
    progress.total_phases, progress.completed_phases, progress.total_plans,
    progress.completed_plans, progress.percent, last_updated,
    last_activity — each by replacing the value of its OWN line, preserving
    indentation, quoting and key order. Every other frontmatter line is
    untouched and the prose body is never read. A key the file does not
    already have is not created; it is named in `skipped`.

    The two timestamps ride along with a real change and never alone. A run
    that changed nothing did not produce activity, and writing them
    unconditionally would make the second --apply of an idempotent command
    write bytes — which is the whole claim.

    `last_activity_desc` and `stopped_at` are NOT written: they are free
    text a person wrote, and rewriting a person's sentence is precisely what
    `state record-session` gets wrong. But the silence about them does not
    stand either — `reconcile` NAMES `state-narrative-stale` with the
    computed numbers beside it, so whoever wrote the sentence can decide. A
    field nobody recalculates and nobody reports is exactly how the coverage
    footer reached 29.

    current_phase vs active_phase (AUTO-08) IS NOT DECIDED HERE. Measured:
    `grep -rn current_phase cairn/` -> ZERO readers, while `active_phase` is
    read by five surfaces (cairn-status.py, cairn-doctor.py, cairn-lease.py,
    cairn-migrate.py, hooks/session-start.sh). The consequence is a measured
    false green: `cairn-doctor.sh --json` reports `claims-stale :: ok ::
    skipped — no active_phase in STATE.md`, a check that has never run in
    this project's life, wearing `ok`. Which dialect wins changes what five
    files read and a wrong migration breaks the lease and the board for
    anyone with a STATE.md already written — that is grooming, tracked as
    CairnGo-rq0, and this command neither decides it nor stays quiet about
    it: it writes the key the file already has, invents none, and a test
    asserts that no `active_phase` key is ever created. The mechanical half
    of AUTO-08 (a check that could not check must stop saying `ok`) lands in
    plan 29-07.

THE TRACKER HALF IS INVOKED, NEVER RE-IMPLEMENTED — AND IT REFUSES EARLY
    `cairn-map.py <N> --json` already refuses a file whose marker block was
    tampered with and is already idempotent; `cairn-lease.py release <N>` is
    already a no-op on a lease nobody holds and already owns the TTL
    arithmetic. Neither is reproduced here. Two implementations of a
    staleness calculation that can disagree is this milestone's disease
    wearing a different hat.

    Because both need `bd`, its availability is checked BEFORE the first
    byte is written: no bd and no --no-tracker means EXIT_NO_BD (5) with the
    three files byte-identical. Writing first and discovering afterwards
    that the lease cannot be released produces exactly the half-done state
    this phase exists to remove. `--no-tracker` is the named way to do the
    file half on purpose, and the report says what did not run.

    THIS IS NOT A GATE. Measured (D-01): the gsd-tools `phase complete 20` —
    the operation a hand actually performs — REFUSED to run and wrote zero
    bytes, because roadmap.cjs:469 requires a passing verification and phase
    20's came back `human_needed`. Here, a missing artifact is a NAMED entry
    in `skipped` or `unresolved`; barring a phase is cairn-gate.py's job and
    it already exits 6.

TWO CONFIG KEYS, READ AT THE POINT OF USE
    bookkeep.auto_commit  true -> after a successful --apply, `git add` of
                          EXACTLY the files this run planned (never -A,
                          never `.`) and one commit. Default false: the
                          files are left written and uncommitted, and the
                          report prints the commit command. A git failure is
                          reported, never fatal — the edits are already on
                          disk and correct.
    ship.pr_scope         becomes the report's `pr_due`: true for "phase",
                          false for "milestone" (the PR comes at the end of
                          the cycle) and false for "none". End of phase is
                          where that decision is answered, so this is where
                          it is asked.

    Both are read by one subprocess call to cairn-config.py, in the
    degrading shape of cairn-status.py's fetch_lease_status(). Neither
    default is copied here: a second home for a default that can drift from
    the schema is the thing this phase removes.

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

    And, only in a write run's `unresolved`, the three AHEAD kinds this
    command reports instead of writing (see the one-way rule above):
    requirement-checkbox-ahead, coverage-row-ahead, plan-checkbox-ahead.

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
    5  EXIT_NO_BD — `bd` is not on PATH and the tracker half was not waived
       with --no-tracker. Returned BEFORE any write, so the three files are
       byte-identical. Never a failed check: barring is cairn-gate.py's 6.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DISAGREEMENT = 3
EXIT_NO_PHASE = 4
EXIT_NO_BD = 5

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
#
# WHOLE LINE, and matched against the UNSTRIPPED content: no indentation, no
# `**` around it, nothing before the first digit. Measured 2026-08-04,
# `grep -n "requisitos, .*mapeados" .planning/ROADMAP.md` matches TWO lines —
# 568, the real footer, and 440, which is the prose of success criterion 5
# quoting the wrong footer between quotes and bold, indented three spaces
# inside a list item. That prose IS the measurement this whole phase rests on
# and 29-07 reads it as its acceptance evidence. A substring search would
# rewrite it on the FIRST pass, and idempotence saves nothing from that.
# Groups 2 and 4 carry the words between and after the numbers so a rewrite
# reproduces the file's own phrasing instead of imposing this script's.
COVERAGE_FOOTER = re.compile(
    r"^(\d+)(\s+(?:requisitos?|requirements?)\s*,\s*)(\d+)"
    r"(\s+(?:mapeados?|mapped)\b.*)$")
# The `— completed <date>` suffix a closed phase line carries (measured on
# phase 20). Detected anywhere in the line: its presence is what makes the
# edit idempotent, so the test is "is it already there", never "where".
COMPLETED_SUFFIX = re.compile(r"\bcompleted\s+\d{4}-\d{2}-\d{2}\b",
                              re.IGNORECASE)
HEAD_PHASE_TITLE = re.compile(r"^#{1,6}\s+Phase\s+0*(\d+)\s*:\s*(.+?)\s*$")
STATE_KEY = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
REQ_SECTION = re.compile(r"^##\s+(.*?)\s*$")
REQ_ITEM = re.compile(
    r"^\s*-\s*(?:\[([ xX])\]\s*)?\*\*([A-Za-z][A-Za-z0-9]*-\d+)\*\*")
PHASE_DIR = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")
# A PLAN and the SUMMARY OF THAT PLAN, matched by SHAPE rather than by suffix.
# MEASURED 2026-08-06, right after the close of phase 22, and still true on
# 2026-08-07 (CairnGo-6bx): scan_phase_tree() globbed `*-SUMMARY.md`, which
# matches `22-01-SUMMARY.md` (a plan's) AND `22-SUMMARY.md` (the phase's),
# while its pair `*-PLAN.md` matches only plans, because a phase has no
# `NN-PLAN.md`. The two globs LOOK symmetric and the naming is not, so
# completed_plans (39 + 8) came out larger than total_plans (39).
#
# `plans` gets the same discipline even though its glob happens to be right
# today: a counter whose correctness rests on the absence of a filename is a
# counter waiting for somebody to create that filename.
PLAN_FILE = re.compile(r"^\d+-\d+-PLAN\.md$")
PLAN_SUMMARY_FILE = re.compile(r"^\d+-\d+-SUMMARY\.md$")
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


def make_edit(path, index, before, after, reason, op="replace"):
    """An edit is one line position plus the reason it is being touched.

    A bookkeeping tool that writes without saying why is the automated
    version of the same problem, so `reason` is not optional.

    op is "replace" (index is the line being replaced) or "insert" (index is
    the position the new line takes, and `before` is None because there was
    no line there). Those are the only two operations: nothing in this script
    deletes a line, and nothing rewrites a file it did not plan an edit for.
    """
    return {"file": str(path), "line": index + 1, "index": index, "op": op,
            "before": before, "after": after, "reason": reason}


def now_stamp():
    """(date, timestamp) — CAIRN_NOW is the determinism seam for the tests.

    Same shape as the other CAIRN_* seams in this repo: unset means the real
    clock, set means exactly what it says. A malformed value is a usage error
    rather than a garbage date written into three files.
    """
    raw = (os.environ.get("CAIRN_NOW") or "").strip()
    if raw:
        if not ISO_DATE.match(raw):
            die(f"CAIRN_NOW must start with YYYY-MM-DD, got {raw!r}",
                EXIT_USAGE)
        date = raw[:10]
        return date, raw if len(raw) > 10 else f"{date}T00:00:00.000Z"
    utc = datetime.datetime.now(datetime.timezone.utc)
    return (utc.strftime("%Y-%m-%d"),
            utc.strftime("%Y-%m-%dT%H:%M:%S.") +
            f"{utc.microsecond // 1000:03d}Z")


def plan_close(path, lines, n, date):
    """Edits that mark phase n complete in ROADMAP.md: the checkbox, and the
    `— completed <date>` suffix a closed phase line carries (measured on
    phase 20). Empty when both are already there."""
    hits = phase_checkbox_hits(lines, n)
    if not hits:
        die(f"no checkbox line for phase {n} in {path}", EXIT_NO_PHASE)
    if len(hits) > 1:
        listed = "\n".join(f"  {path}:{i + 1}: {content}"
                           for i, _s, content, _e, _sp in hits)
        die(f"phase {n} matches {len(hits)} checkbox lines — refusing to "
            f"guess which one is the phase:\n{listed}", EXIT_USAGE)
    index, state, content, _eol, span = hits[0]
    after = content
    why = []
    if state.lower() != "x":
        start, end = span
        after = after[:start] + "x" + after[end:]
        why.append(f"its checkbox still reads '[{state}]'")
    if not COMPLETED_SUFFIX.search(after):
        after = f"{after} — completed {date}"
        why.append("it carries no `— completed <date>` suffix")
    if after == content:
        return []
    return [make_edit(path, index, content, after,
                      f"phase {n} is complete; " + " and ".join(why))]


def apply_edits(sources, edits):
    """Apply every planned edit and write only the files that had one.

    Replacements first, by their ORIGINAL index — they do not move anything.
    Insertions after, in descending index order, so an earlier insertion
    cannot shift a later one's position. Nothing is re-serialized: the list
    of lines that came out of read_lines() is the list that goes back in,
    with the planned positions and nothing else touched.
    """
    by_file = {}
    for edit in edits:
        by_file.setdefault(edit["file"], []).append(edit)
    written = []
    for name in sorted(by_file):
        lines = sources[name]
        group = by_file[name]
        for edit in group:
            if edit["op"] != "replace":
                continue
            _content, eol = split_eol(lines[edit["index"]])
            lines[edit["index"]] = edit["after"] + eol
        # Descending index, and for two insertions at the SAME position the
        # later-planned one first — so the pair comes out in planning order
        # instead of reversed.
        inserts = [(k, e) for k, e in enumerate(group)
                   if e["op"] == "insert"]
        for _k, edit in sorted(inserts,
                               key=lambda t: (-t[1]["index"], -t[0])):
            neighbour = edit["index"] - 1 if edit["index"] else 0
            eol = "\n"
            if lines:
                _content, eol = split_eol(lines[min(neighbour,
                                                    len(lines) - 1)])
                eol = eol or "\n"
            lines.insert(edit["index"], edit["after"] + eol)
        write_lines(Path(name), lines)
        written.append(name)
    return written


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


def sibling(name):
    return str(Path(__file__).resolve().parent / name)


def run_sibling_json(argv):
    """Run a sibling cairn script and parse its --json, degrading to a named
    failure instead of a traceback.

    Same shape as cairn-status.py's fetch_lease_status(): a subprocess that
    will not run, or output that will not parse, is reported — never
    re-implemented here. Two implementations of a TTL calculation that can
    disagree is this milestone's disease with a different hat on.
    """
    try:
        proc = subprocess.run([sys.executable] + argv, capture_output=True,
                              text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc)}
    out = {"ok": proc.returncode == 0, "exit": proc.returncode}
    try:
        out["result"] = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        out["result"] = None
        out["error"] = (proc.stderr or proc.stdout or "").strip()[:400]
    if not out["ok"] and "error" not in out:
        out["error"] = (proc.stderr or "").strip()[:400]
    return out


def config_value(root, key):
    """A config key's effective value, read from cairn-config.py — never
    from a second copy of the schema's default living here."""
    got = run_sibling_json([sibling("cairn-config.py"), "get", key, "--json",
                            "--project-dir", str(root)])
    if not got["ok"] or not isinstance(got.get("result"), dict):
        return None
    return got["result"].get("value")


def git_commit(root, files, message):
    """Stage EXACTLY the files this run planned, and commit those paths.

    Never `git add -A`, never `git add .`: a bookkeeping commit that sweeps
    up whatever else was in the tree is the tool taking work it did not do.
    Both calls carry the same explicit pathspec, so even a dirty index
    cannot widen it.
    """
    rel = [os.path.relpath(f, str(root)) for f in files]
    for argv in (["add", "--"] + rel, ["commit", "-m", message, "--"] + rel):
        try:
            proc = subprocess.run(["git", "-C", str(root)] + argv,
                                  capture_output=True, text=True)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, str(exc)
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout or "").strip()[:400]
    return True, None


def run_tracker(planning, root, phase, wanted, applied):
    """The two pieces of end-of-phase bookkeeping that belong to other
    scripts: the generated map and the phase lease. Invoked, never
    re-implemented."""
    out = {"ran": False, "skipped": None, "map": None, "lease": None}
    if phase is None:
        out["skipped"] = ("reconcile owns no phase: there is no map to "
                          "regenerate and no lease to release")
        return out
    if not wanted:
        out["skipped"] = ("--no-tracker: the phase map was NOT regenerated "
                          "and the phase lease was NOT released")
        return out
    if not applied:
        out["skipped"] = "read mode: the tracker is only touched by --apply"
        return out
    out["ran"] = True
    out["map"] = run_sibling_json([sibling("cairn-map.py"), str(phase),
                                   "--json", "--planning-dir", str(planning)])
    out["lease"] = run_sibling_json([sibling("cairn-lease.py"), "release",
                                     str(phase), "--json", "--project-dir",
                                     str(root)])
    return out


def run_bookkeeping(args, phase):
    """The shared body of `close N` and `reconcile --apply`: plan, write
    behind --apply, report. `close` is this plus the phase's own checkbox
    (edit 1); `reconcile --apply` is this without it."""
    planning = resolve_planning_dir(args.planning_dir)
    root = planning.parent
    date, stamp = now_stamp()
    plan = build_plan(planning, phase, date, stamp)
    edits = plan["edits"]

    # The bd gate fires BEFORE the first byte is written. Bookkeeping that
    # edited three files and then discovered it cannot release the lease is
    # exactly the half-done state this phase exists to remove, and 5 is the
    # house code for "the tool is not there", never for a failed check.
    tracker_wanted = phase is not None and not getattr(args, "no_tracker",
                                                       False)
    if args.apply and tracker_wanted and shutil.which("bd") is None:
        die("bd is not on PATH, so the phase map and the lease cannot be "
            "touched — refusing to write the planning files and leave the "
            "bookkeeping half done. Install beads, or pass --no-tracker to "
            "do the file half deliberately.", EXIT_NO_BD)

    changed = False
    written = []
    if edits and args.apply:
        written = apply_edits(plan["sources"], edits)
        changed = True

    tracker = run_tracker(planning, root, phase, tracker_wanted, args.apply)

    auto_commit = config_value(root, "bookkeep.auto_commit")
    commit = {"configured": auto_commit, "made": False, "note": None}
    if not changed:
        commit["note"] = "nothing was written, so there is nothing to commit"
    elif auto_commit is True:
        message = (f"chore(cairn): bookkeeping fase {phase}" if phase
                   else "chore(cairn): bookkeeping reconcile")
        ok, detail = git_commit(root, written, message)
        commit["made"] = ok
        commit["message"] = message
        # A failed commit is REPORTED, never fatal: the edits are already on
        # disk and correct, and the commit is a convenience on top of them.
        commit["note"] = None if ok else f"git refused the commit: {detail}"
    else:
        paths = " ".join(os.path.relpath(f, str(root)) for f in written)
        commit["note"] = (
            "bookkeep.auto_commit is not true, so the files are written and "
            f"uncommitted. Commit them with: git add -- {paths} && "
            "git commit")

    pr_scope = config_value(root, "ship.pr_scope")
    payload = {
        "phase": phase, "applied": bool(args.apply), "changed": changed,
        "files_written": written,
        "planned": [{k: e[k] for k in ("file", "line", "op", "before",
                                       "after", "reason")} for e in edits],
        "unresolved": plan["unresolved"], "skipped": plan["skipped"],
        "counters": plan["counters"], "tracker": tracker, "commit": commit,
        "pr_scope": pr_scope,
        "pr_due": None if phase is None else (pr_scope == "phase")}

    verb = "wrote" if changed else "would write"
    human = []
    for e in edits:
        human.append(f"{verb} {e['file']}:{e['line']} ({e['op']}): "
                     f"{e['reason']}")
        if e["before"] is not None:
            human.append(f"  - {e['before']}")
        human.append(f"  + {e['after']}")
    if not edits:
        human.append("nothing to change")
    for f in plan["unresolved"]:
        human.append(f"NOT written :: {f['kind']} :: {f['subject']} :: "
                     f"found {f['found']!r} ({f['source']})")
    for s in plan["skipped"]:
        human.append(f"skipped :: {s['what']} :: {s['why']}")
    if tracker["skipped"]:
        human.append(f"tracker :: not run :: {tracker['skipped']}")
    elif tracker["ran"]:
        for name in ("map", "lease"):
            got = tracker[name] or {}
            state = "ok" if got.get("ok") else f"FAILED ({got.get('error')})"
            human.append(f"tracker :: {name} :: {state}")
    if commit["note"]:
        human.append(f"commit :: {commit['note']}")
    elif commit["made"]:
        human.append(f"commit :: made :: {commit['message']}")
    if payload["pr_due"] is not None:
        human.append(f"pr_due :: {payload['pr_due']} "
                     f"(ship.pr_scope = {pr_scope!r})")
    return payload, human, edits


def cmd_close(args):
    payload, human, edits = run_bookkeeping(args, args.phase)
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
    out = {"phases": {}, "phase_reqs": {}, "phase_plans": {}, "titles": {}}
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

        m = HEAD_PHASE_TITLE.match(content)
        if m:
            out["titles"].setdefault(int(m.group(1), 10), m.group(2).strip())

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
                {"line": i + 1, "index": i, "plan": m.group(2),
                 "checked": m.group(1).lower() == "x",
                 "state_span": m.span(1), "raw": content})
    return out


def parse_coverage(lines, path):
    """The requirement -> phase -> status table and its footer, anchored to
    the coverage heading.

    Anchoring is not decoration: unanchored, the footer regex also matched a
    line of PROSE quoting the footer inside a phase's own detail block — the
    phase's evidence about the defect being mistaken for the defect.

    Returns None when this file has no coverage section at all, which is a
    different state from "a section with no rows" and is reported as such.

    THE FOOTER IS FOUND BY POSITION, NEVER BY SEARCHING THE FILE FOR ITS
    TEXT. Walk from the coverage heading to the last consecutive table row,
    and take the whole-line match that follows it inside the same section.
    Measured 2026-08-04: searching the file for `requisitos, .*mapeados`
    matches TWO lines, and the second is the prose of success criterion 5
    quoting the wrong footer — the evidence that justifies this phase. Zero
    or two matches inside the interval is a usage error naming what was
    found; "take the first" is how a tool ends up editing the wrong line
    with confidence.
    """
    head_line, start, end = None, None, len(lines)
    for i, raw in enumerate(lines):
        content, _eol = split_eol(raw)
        if head_line is None:
            if COVERAGE_HEAD.match(content):
                head_line, start = i + 1, i + 1
            continue
        if content.startswith("## "):
            end = i
            break
    if head_line is None:
        return None

    rows, last_row = [], None
    for i in range(start, end):
        content, _eol = split_eol(lines[i])
        m = COVERAGE_ROW.match(content)
        if m:
            rows.append({"file": str(path), "line": i + 1, "index": i,
                         "requirement": m.group(1), "phase": m.group(2),
                         "status": m.group(3), "status_span": m.span(3)})
            last_row = i

    footers = []
    for i in range((last_row + 1) if last_row is not None else start, end):
        content, _eol = split_eol(lines[i])
        m = COVERAGE_FOOTER.match(content)
        if m:
            footers.append({"file": str(path), "line": i + 1, "index": i,
                            "raw": content, "claim": int(m.group(1), 10),
                            "mapped": int(m.group(3), 10)})
    if len(footers) > 1:
        listed = "\n".join(f"  {path}:{f['line']}: {f['raw']}"
                           for f in footers)
        die(f"the coverage section holds {len(footers)} footer lines — "
            f"refusing to guess which one counts the table:\n{listed}",
            EXIT_USAGE)
    return {"file": str(path), "heading_line": head_line, "rows": rows,
            "footer": footers[0] if footers else None,
            "last_row_index": last_row, "section_end_index": end}


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
                "line": i + 1, "index": i, "requirement": m.group(2),
                "checked": bool(state) and state.lower() == "x",
                "has_checkbox": state is not None,
                "state_span": m.span(1) if state is not None else None,
                "raw": content})
    return out


def parse_state_frontmatter_items(lines):
    """The YAML frontmatter of STATE.md, one nesting level deep, with the
    POSITION of every key — dotted for a nested one (`progress.percent`).

    THE BODY IS NEVER READ. Measured cause: `state record-session` took
    `Phase: 18` from the obsolete prose below the frontmatter and rewrote
    `current_phase: 29` backwards to a phase of an archived milestone.

    The position is what lets the write path replace one key's value in
    place, preserving indentation AND key order. Measured cause for that
    one: `state complete-phase` round-trips the frontmatter through a YAML
    serializer and reorders it.
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
        m = STATE_KEY.match(content)
        if not m:
            continue
        indent, key, value = m.group(1), m.group(2), m.group(3).strip()
        item = {"index": i, "line": i + 1, "raw": content, "value": value,
                "value_span": m.span(3)}
        if indent and nested:
            out[f"{nested}.{key}"] = item
        else:
            nested = key if value == "" else None
            if value != "":
                out[key] = item
    return out


def parse_state_frontmatter(lines):
    """Just the values — the shape reconcile's report echoes."""
    return {k: v["value"]
            for k, v in parse_state_frontmatter_items(lines).items()}


def scan_phase_tree(planning):
    """{phase number: {dir, plans: [names], summaries: [names]}} — counted by
    NAME. Nothing in a plan or summary file is ever opened.

    `summaries` is the summaries OF PLANS, never the summary of the phase:
    both end in `-SUMMARY.md` and only one of them is a plan. See
    PLAN_SUMMARY_FILE for the measurement that this asymmetry produced.
    """
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
            "plans": sorted(p.name for p in d.glob("*-PLAN.md")
                            if PLAN_FILE.match(p.name)),
            "summaries": sorted(p.name for p in d.glob("*-SUMMARY.md")
                                if PLAN_SUMMARY_FILE.match(p.name))}
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


# The one-way rule, quoted into every finding it produces so the reason
# travels with the report instead of living only in this file.
ONE_WAY_NOTE = ("this command only ever moves a view from not-done to done. "
                "The reverse — unmarking something the disk does not "
                "corroborate — asserts an ABSENCE, and an absence has many "
                "causes (a branch not merged yet, a rename, a phase split). "
                "Reported, never written.")

# Exhaustively: the only STATE.md frontmatter keys this command ever writes,
# and only when the file already has them. It invents no key.
STATE_KEYS_WRITTEN = ("current_phase", "current_phase_name",
                      "progress.total_phases", "progress.completed_phases",
                      "progress.total_plans", "progress.completed_plans",
                      "progress.percent", "last_updated", "last_activity")


def carriers_of(road):
    """requirement id -> the phases whose `**Requirements**:` line names it.

    ONE implementation, called by the reader and by the writer. Two
    implementations of the same arithmetic that can drift apart is the
    disease this milestone treats; writing it twice here would be the tool
    catching itself.
    """
    carriers = {}
    for n, block in road["phase_reqs"].items():
        for rid in block["ids"]:
            carriers.setdefault(rid, []).append(n)
    return carriers


def derive_complete(carriers, complete_phase):
    """derived 1: a requirement is complete when EVERY phase carrying it
    is."""
    return {rid: all(complete_phase.get(n, False) for n in phases)
            for rid, phases in carriers.items()}


def compute_counters(road, tree, complete_phase, n_active, n_rows):
    """The STATE counters, from the roadmap's checkbox lines and the file
    NAMES under .planning/phases/ — never from the frontmatter that claims
    them, and never from the prose body."""
    in_milestone = sorted(road["phases"])
    total_phases = len(in_milestone)
    completed = sum(1 for n in in_milestone if complete_phase.get(n, False))
    return {
        "total_phases": total_phases,
        "completed_phases": completed,
        "total_plans": sum(len(tree.get(n, {}).get("plans", []))
                           for n in in_milestone),
        "completed_plans": sum(len(tree.get(n, {}).get("summaries", []))
                               for n in in_milestone),
        "percent": (round(100 * completed / total_phases)
                    if total_phases else 0),
        "active_requirements": n_active,
        "coverage_rows": n_rows}


def ellipsis_phases(road):
    """Phases whose requirements line is an ellipsis — the ids it should
    name are unknown, so anything derived from them is unknown too."""
    return sorted(n for n, block in road["phase_reqs"].items()
                  if ELLIPSIS.search(block["raw"]))


def format_state_value(old, value):
    """The new value, wearing the old one's quoting and trailing space."""
    text = str(value)
    body = old.rstrip()
    trail = old[len(body):]
    if len(body) >= 2 and body[0] in "\"'" and body[-1] == body[0]:
        return f"{body[0]}{text}{body[0]}{trail}"
    return f"{text}{trail}"


def insertion_index(coverage, lines, phase):
    """Where a new row for `phase` goes: after the LAST row already mapped
    to that phase, so the file's existing grouping by phase survives; after
    the last row of the table when the phase has no group yet."""
    at = coverage["last_row_index"]
    for row in coverage["rows"]:
        m = re.search(r"\b0*(\d+)\b", row["phase"])
        if m and int(m.group(1), 10) == phase:
            at = row["index"]
    return (at + 1) if at is not None else coverage["heading_line"]


def build_plan(planning, phase, date, stamp):
    """The whole edit plan over the three files — the six edits, the things
    it refuses to write, and the things it could not reach.

    Nothing here writes. It returns the plan; apply_edits() is the only
    thing that touches a file, and only with this list in hand.
    """
    roadmap_path = planning / "ROADMAP.md"
    if not roadmap_path.is_file():
        die(f"ROADMAP.md not found in {planning}", EXIT_USAGE)
    reqs_path = planning / "REQUIREMENTS.md"
    state_path = planning / "STATE.md"

    roadmap_lines = read_lines(roadmap_path)
    sources = {str(roadmap_path): roadmap_lines}
    reqs_lines = None
    state_lines = None
    skipped = []
    if reqs_path.is_file():
        reqs_lines = read_lines(reqs_path)
        sources[str(reqs_path)] = reqs_lines
    else:
        skipped.append({"what": "the requirement checkboxes",
                        "why": f"{reqs_path} does not exist"})
    if state_path.is_file():
        state_lines = read_lines(state_path)
        sources[str(state_path)] = state_lines
    else:
        skipped.append({"what": "the STATE counters",
                        "why": f"{state_path} does not exist"})

    road = parse_roadmap(roadmap_lines)
    tree = scan_phase_tree(planning)
    reqs = (parse_requirements(reqs_lines) if reqs_lines is not None
            else {"active": [], "deferred": [], "out_of_scope": []})
    coverage = parse_coverage(roadmap_lines, roadmap_path)
    if coverage is None and reqs_lines is not None:
        coverage = parse_coverage(reqs_lines, reqs_path)

    edits, unresolved = [], []

    # --- edit 1: the phase's own checkbox (close only) ---------------------
    if phase is not None:
        edits.extend(plan_close(roadmap_path, roadmap_lines, phase, date))

    complete_phase = {n: p["complete"] for n, p in road["phases"].items()}
    if phase is not None:
        complete_phase[phase] = True
    carriers = carriers_of(road)
    derived = derive_complete(carriers, complete_phase)

    active = [r["requirement"] for r in reqs["active"]]
    by_id = {r["requirement"]: r for r in reqs["active"]}

    # --- edit 2: each requirement's checkbox ------------------------------
    for rid in active:
        item = by_id[rid]
        if rid not in derived or not item["has_checkbox"]:
            continue
        if item["checked"] == derived[rid]:
            continue
        if not derived[rid]:
            unresolved.append(finding(
                "requirement-checkbox-ahead", rid, "[x]", "[ ]",
                f"{reqs_path}:{item['line']}",
                {"open_phases": sorted(n for n in carriers[rid]
                                       if not complete_phase.get(n, False)),
                 "note": ONE_WAY_NOTE}))
            continue
        start, end = item["state_span"]
        raw = item["raw"]
        edits.append(make_edit(
            reqs_path, item["index"], raw, raw[:start] + "x" + raw[end:],
            "every phase carrying {0} is complete ({1})".format(
                rid, ", ".join("phase %d" % n
                               for n in sorted(carriers[rid])))))

    # --- edits 3 and 4: the coverage table and its footer ------------------
    rows_after = 0
    if coverage is None:
        if active:
            skipped.append({
                "what": "the coverage table and its footer",
                "why": "no '## Cobertura' section in ROADMAP.md and no "
                       "'## Traceability' section in REQUIREMENTS.md"})
    else:
        cov_path = Path(coverage["file"])
        cov_lines = sources[coverage["file"]]
        rows_by_id = {r["requirement"]: r for r in coverage["rows"]}
        for rid in sorted(rows_by_id):
            row = rows_by_id[rid]
            if rid not in derived:
                continue
            already = row["status"].strip().lower() == "complete"
            if derived[rid] == already:
                continue
            if not derived[rid]:
                unresolved.append(finding(
                    "coverage-row-ahead", rid, row["status"].strip(),
                    "a status matching its phases",
                    f"{row['file']}:{row['line']}",
                    {"open_phases": sorted(n for n in carriers[rid]
                                           if not complete_phase.get(n,
                                                                     False)),
                     "note": ONE_WAY_NOTE}))
                continue
            raw = split_eol(cov_lines[row["index"]])[0]
            start, end = row["status_span"]
            edits.append(make_edit(
                cov_path, row["index"], raw,
                raw[:start] + "Complete" + raw[end:],
                f"every phase carrying {rid} is complete"))

        inserted = 0
        blind = ellipsis_phases(road)
        for rid in active:
            if rid in rows_by_id:
                continue
            if rid not in carriers:
                unresolved.append(finding(
                    "coverage-row-missing", rid, None, "a coverage table row",
                    f"{reqs_path}:{by_id[rid]['line']}",
                    {"blocked_by": "no phase in ROADMAP.md declares it, so "
                                   "the row's phase cell has no readable "
                                   "source",
                     "phases_with_an_unreadable_requirements_line": blind,
                     "note": "NEVER inferred from the id's prefix. That the "
                             "other AUTO-* rows all say Phase 29 is a "
                             "pattern, not a source — writing the row from "
                             "it would be inference wearing the costume of "
                             "reading. Write the ids out on the phase's "
                             "**Requirements**: line and this row plans "
                             "itself."}))
                continue
            n = sorted(carriers[rid])[0]
            status = "Complete" if derived[rid] else "Pending"
            edits.append(make_edit(
                cov_path, insertion_index(coverage, cov_lines, n), None,
                f"| {rid} | Phase {n} | {status} |",
                f"{rid} is active and has no row; phase {n} declares it",
                op="insert"))
            inserted += 1

        rows_after = len(coverage["rows"]) + inserted
        footer = coverage["footer"]
        if footer is not None:
            want = (len(active), rows_after)
            if (footer["claim"], footer["mapped"]) != want:
                raw = split_eol(cov_lines[footer["index"]])[0]
                m = COVERAGE_FOOTER.match(raw)
                edits.append(make_edit(
                    cov_path, footer["index"], raw,
                    f"{want[0]}{m.group(2)}{want[1]}{m.group(4)}",
                    f"{len(active)} active requirement(s) and {rows_after} "
                    f"table row(s); the footer claims "
                    f"{footer['claim']}/{footer['mapped']}"))

    # --- edit 5: each plan's checkbox against its SUMMARY on disk ----------
    for n in sorted(road["phase_plans"]):
        summaries = set(tree.get(n, {}).get("summaries", []))
        for item in road["phase_plans"][n]:
            summary = item["plan"].replace("-PLAN.md", "-SUMMARY.md")
            on_disk = summary in summaries
            if item["checked"] == on_disk:
                continue
            if not on_disk:
                unresolved.append(finding(
                    "plan-checkbox-ahead", item["plan"], "[x]", "[ ]",
                    f"{roadmap_path}:{item['line']}",
                    {"summary": summary, "note": ONE_WAY_NOTE}))
                continue
            start, end = item["state_span"]
            raw = item["raw"]
            edits.append(make_edit(
                roadmap_path, item["index"], raw,
                raw[:start] + "x" + raw[end:],
                f"{summary} is on disk"))

    # --- edit 6: the STATE frontmatter, and ONLY the keys it already has ---
    counters = compute_counters(road, tree, complete_phase, len(active),
                                rows_after)
    if state_lines is not None:
        items = parse_state_frontmatter_items(state_lines)
        wanted = {f"progress.{k}": counters[k] for k in
                  ("total_phases", "completed_phases", "total_plans",
                   "completed_plans", "percent")}
        if phase is not None:
            wanted["current_phase"] = phase
            title = road["titles"].get(phase)
            if title:
                wanted["current_phase_name"] = title
        state_edits = []
        for key in STATE_KEYS_WRITTEN:
            if key not in wanted or key not in items:
                continue
            item = items[key]
            raw = split_eol(state_lines[item["index"]])[0]
            start, end = item["value_span"]
            after = raw[:start] + format_state_value(raw[start:end],
                                                     wanted[key]) + raw[end:]
            if after == raw:
                continue
            state_edits.append(make_edit(
                state_path, item["index"], raw, after,
                f"{key} disagrees with the roadmap and the phase tree"))
        # The two timestamps ride along with a real change and never alone:
        # a run that changed nothing did not produce activity, and writing
        # them unconditionally would make the second --apply of an
        # idempotent command write bytes.
        if edits or state_edits:
            for key, value in (("last_updated", stamp),
                               ("last_activity", date)):
                if key not in items:
                    continue
                item = items[key]
                raw = split_eol(state_lines[item["index"]])[0]
                start, end = item["value_span"]
                after = (raw[:start]
                         + format_state_value(raw[start:end], value)
                         + raw[end:])
                if after != raw:
                    state_edits.append(make_edit(
                        state_path, item["index"], raw, after,
                        f"{key} follows the edits this run made"))
        edits.extend(state_edits)
        absent = [k for k in STATE_KEYS_WRITTEN if k not in items]
        if absent:
            skipped.append({
                "what": "STATE.md keys this command did not create",
                "why": "the file does not have them: " + ", ".join(absent)
                       + " — it writes the key a file already has and "
                         "invents none (see AUTO-08 / CairnGo-rq0)"})

    return {"sources": sources, "edits": edits, "unresolved": unresolved,
            "skipped": skipped, "counters": counters,
            "files": {"roadmap": str(roadmap_path),
                      "requirements": str(reqs_path),
                      "state": str(state_path)}}


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
    complete_phase = {n: p["complete"] for n, p in road["phases"].items()}
    carriers = carriers_of(road)
    derived = derive_complete(carriers, complete_phase)

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

    # --- derived 4: the footer counts requirements AND how many are mapped --
    # No footer at all reports nothing: an absent claim is not a false claim.
    #
    # `N requisitos, N mapeados.` states TWO different quantities, and this
    # is a correction to 29-01's rule 4, which read both as the table's row
    # count. Under that reading the footer is self-consistent with the table
    # by construction: it can never contradict REQUIREMENTS.md, and a number
    # that cannot be wrong is not a check. Read as written — how many
    # requirements exist, how many of them the table maps — the footer says
    # exactly where the gap is: `35 requisitos, 33 mapeados.`
    if cov_footer is not None:
        rows = len(cov_rows)
        if cov_footer["claim"] != len(active) or cov_footer["mapped"] != rows:
            found.append(finding(
                "footer-count-stale", "coverage footer",
                [cov_footer["claim"], cov_footer["mapped"]],
                [len(active), rows],
                f"{cov_footer['file']}:{cov_footer['line']}",
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
    computed = compute_counters(road, tree, complete_phase, len(active),
                                len(cov_rows))
    total_phases = computed["total_phases"]

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
    if args.apply:
        # The same five edits `close` makes, WITHOUT marking any phase
        # complete: the way to resolve drift that already exists rather than
        # pretending a phase just closed.
        payload, human, edits = run_bookkeeping(args, None)
        emit(payload, args.json, human)
        sys.exit(EXIT_OK)
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
    close.add_argument("--no-tracker", action="store_true",
                       help="do the file half only: skip the map refresh "
                            "and the lease release, and say so")
    close.add_argument("--json", action="store_true",
                       help="machine-readable output")
    close.add_argument("--planning-dir", metavar="DIR",
                       help="planning dir (default: $CLAUDE_PROJECT_DIR or "
                            "cwd, plus /.planning)")
    close.set_defaults(func=cmd_close)

    rec = sub.add_parser("reconcile", help="name every disagreement between "
                                           "the planning files and the disk")
    rec.add_argument("--apply", action="store_true",
                     help="resolve what can be resolved without marking any "
                          "phase complete (default: read only)")
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
