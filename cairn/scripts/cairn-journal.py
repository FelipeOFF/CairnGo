#!/usr/bin/env python3
"""cairn-journal — the single append-only, local, gitignored writer for
cairn's own observed state history (D-02).

What gets journaled, and why (D-01): exactly three categories — phase-state
axis transitions (the four evidence axes cairn-status.py's corroborate()
already computes: disk/bd/roadmap/state_md), phase-lease acquire/release
events, and corroboration verdict changes (ok/conflict/unknown). Rejected:
logging every action cairn takes (issue closes, map regeneration, doctor
runs) — that would turn this into an application log, growing fast and
drowning the one signal that actually matters: WHEN did each side of a
disk/bd/roadmap/state_md disagreement last move. A doctor conflict report
needs exactly that "when did each side last move" answer (JOUR-02), and
that answer is only recoverable if the journal actually SAW the side that
moved — an issue closing or a lease changing hands, neither of which is a
phase-directory-artifact transition by itself, which is why lease and
verdict events are journaled too, not just phase-state.

Record schema — every record is one self-contained JSON object, written as
exactly one physical line, carrying a common envelope:
    ts      str, datetime.now(timezone.utc).isoformat() — microsecond
            precision, matching cairn-lease.py's own acquired_at/
            heartbeat_at format (NOT cairn-migrate.py's second-resolution
            now_utc()) — sub-second ordering resolution is needed even
            though this file is never git-merged (see below).
    nonce   str, uuid.uuid4().hex — a uniqueness tiebreaker for records
            written in the same instant, and future-proofing per
            STACK.md's merge=union collision finding (byte-identical lines
            silently deduplicate under that driver) even though this file
            is never git-tracked.
    actor   str, resolve_actor()'s BEADS_ACTOR / `git config user.name` /
            $USER chain (reimplemented here verbatim per house convention
            — no shared lib, die()-style helpers are duplicated per
            script; see cairn-lease.py's own resolve_actor()).
    phase   int
    event   str — "state_changed", "verdict_changed", or "lease_changed"

Event-specific fields:
    state_changed   source ("disk"|"bd"|"roadmap"|"state_md" — the exact
                    four keys corroborate()'s evidence dict produces),
                    from (str or null), to (str or null). state_md's value
                    is genuinely nullable per corroborate()'s own code, so
                    "never observed before" and "prior value was null" are
                    two DIFFERENT things: internally, "never observed" is
                    represented by a distinct sentinel (_NEVER_OBSERVED,
                    never serialized) and only resolved to a stored
                    `null` at record-build time — never conflated with an
                    axis whose last known value genuinely WAS null.
    verdict_changed from ("ok"|"conflict"|"unknown"|null), to (same)
    lease_changed   action ("acquired"|"released"), holder (str),
                    prev_holder (str or null)

Append atomicity — the whole reason this is a single writer (D-02): every
write funnels through _append_record(), which builds the complete line in
memory first (json.dumps(record, sort_keys=True) + "\n", encoded once),
then opens the file with os.open(O_WRONLY | O_CREAT | O_APPEND) and issues
exactly ONE os.write() of that full line, verifying the returned byte
count. This is deliberately NOT open(path, "a"): a plain buffered
io.TextIOWrapper is not guaranteed to translate one .write() call into
exactly one write(2) syscall — internal buffering/encoding can split it
into several, each individually losing the O_APPEND atomicity guarantee
POSIX defines at the SYSCALL level, not the language-object level (see
.planning/research/STACK.md's "Append-Only Journal" section).
cairn-migrate.py's Applier.journal() uses exactly this open(path, "a")
recipe — it is the precedent for the JOURNAL IDIOM in this codebase (a
resumable JSONL journal is already production-proven here), but NOT for
this atomicity mechanism; this script deliberately does not copy that
part. PIPE_BUF is also the wrong constant to reason about record size
here — it governs pipe/FIFO writes, not regular-file writes, and measures
512 bytes on macOS (verified in STACK.md); the guarantee this recipe
actually relies on is POSIX O_APPEND atomicity on a regular file, which
carries no PIPE_BUF-sized cap.

Location and git status — the journal lives at
<project-dir>/.cairn/journal.jsonl — INSIDE the worktree's own .cairn/,
deliberately UNLIKE the phase lease (rooted at --git-common-dir, shared
across worktrees, per cairn-lease.py). This file is per-machine, per-
worktree forensics, never a cross-worktree coordination primitive (see
.planning/research/SUMMARY.md's "Collision 4"). It is gitignored and never
git-tracked — not because a `merge=union` flat-file strategy was tried
here and then fixed, but because this file was never meant to be shared
across machines or merged at all: a `*.jsonl merge=union` driver reorders
disjoint appends non-chronologically and silently deduplicates
byte-identical lines (STACK.md), which would be a real, live bug for a
git-tracked version of this file. Keeping the journal local and gitignored
sidesteps that question instead of solving it (Plan 16-05 adds the actual
.gitignore entry; this plan only writes the file).

Usage:
    cairn-journal.py observe    [--project-dir DIR] [--json]
                                 (reads a JSON array from stdin)
    cairn-journal.py lease <N> {acquired|released} --holder H
                                 [--prev-holder P] --actor A
                                 [--project-dir DIR] [--json]
    cairn-journal.py history    [--phase N] [--json]
                                 [--project-dir DIR]
    cairn-journal.py last-moved --phase N [--json] [--project-dir DIR]

    --project-dir DIR   project root (default: $CLAUDE_PROJECT_DIR or cwd)
    --json              machine-readable output instead of human lines

Behavior:
    observe       stdin is a JSON array of {"phase": int, "evidence":
                  {"disk": str, "bd": str, "roadmap": str,
                  "state_md": str|null}, "verdict": "ok"|"conflict"|
                  "unknown"} objects — corroborate()'s own evidence dict,
                  passed through near-verbatim by the caller (a later
                  plan). For each phase, each evidence axis whose incoming
                  value differs from what _last_known() reports for that
                  phase+axis (including "never observed" as a kind of
                  difference) appends exactly one state_changed record;
                  axes that match the last known value append nothing.
                  Same dedup rule for `verdict` -> verdict_changed.
                  Resubmitting byte-identical evidence+verdict for an
                  already-observed phase appends zero new records — this
                  dedup IS JOUR-01's "every transition, no non-transition"
                  guarantee in practice. --json prints
                  {"written": [<records actually appended>]}; human mode
                  prints one line per record written, or
                  "[cairn-journal] no changes" if none.
    lease         Unconditional append of one lease_changed record — this
                  subcommand does NO deduplication itself; a caller
                  invoking it on every heartbeat renewal (rather than only
                  on a genuine acquire/release transition) would flood the
                  journal, and guarding against that is the CALLER's job
                  (Plan 16-03/16-04), not this script's.
    history       Prints every journaled record (optionally filtered by
                  --phase), sorted by (ts, nonce) ascending. --json prints
                  {"records": [...], "warnings": [...]}; human mode prints
                  one JSON object per line, with any _read_records()
                  warning (a quarantined torn/malformed line) printed to
                  stderr as "[cairn-journal] warning: ...". A warning
                  never aborts the read.
    last-moved    Prints _last_known()'s per-axis {value, ts} dict
                  (disk/bd/roadmap/state_md/verdict/lease) for one phase,
                  each key null when that axis has never been observed —
                  including for a phase with NO records at all, or no
                  journal file at all. Never an error.

Exit codes:
    0  ok
    2  usage error (malformed stdin, missing/non-numeric phase, unknown
       flag)
    4  a short/failed os.write() during append — extremely rare on a
       local filesystem, but checked per the STACK.md recipe rather than
       trusted blindly.
"""
import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_WRITE_FAILED = 4

USAGE = ("usage: cairn-journal.py {observe|lease N {acquired|released}|"
         "history|last-moved} [--project-dir DIR] [--json]")

EVIDENCE_AXES = ("disk", "bd", "roadmap", "state_md")

# Internal-only sentinel: "this axis has never been observed for this
# phase" — distinct from an axis whose last recorded value genuinely IS
# null (state_md's own value is nullable per corroborate()). Never
# serialized directly; always resolved to `None` (JSON null) at the point
# a record is built.
_NEVER_OBSERVED = object()


def die(msg, code):
    print(f"[cairn-journal] error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# identity + root resolution
# --------------------------------------------------------------------------- #
def resolve_root(project_dir):
    if project_dir:
        return Path(project_dir).resolve()
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()


def resolve_actor(root):
    """Display-only actor label. Same resolution order as cairn-lease.py's
    resolve_actor() (reimplemented here verbatim per house convention — no
    shared lib, die()-style helpers are duplicated per script):
    $BEADS_ACTOR, else `git config user.name`, else $USER."""
    env_actor = os.environ.get("BEADS_ACTOR")
    if env_actor:
        return env_actor
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "config", "user.name"],
            capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except FileNotFoundError:
        pass
    return os.environ.get("USER")


# --------------------------------------------------------------------------- #
# paths
# --------------------------------------------------------------------------- #
def _journal_path(root):
    return root / ".cairn" / "journal.jsonl"


# --------------------------------------------------------------------------- #
# append primitive — the ONE place any subcommand writes the journal file
# --------------------------------------------------------------------------- #
def _append_record(journal_path, record):
    """Build the complete line in memory, then a single os.open(O_APPEND)
    plus a single os.write() of the whole line, verifying the byte count.
    Never open(path, "a") — see the module docstring for why. Never split
    the line and its trailing newline into two writes."""
    line = json.dumps(record, sort_keys=True).encode("utf-8") + b"\n"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(journal_path),
                 os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        n = os.write(fd, line)
    finally:
        os.close(fd)
    if n != len(line):
        die(f"short write to {journal_path}: wrote {n} of {len(line)} "
            "bytes", EXIT_WRITE_FAILED)


# --------------------------------------------------------------------------- #
# read primitive — the ONE place any subcommand reads the journal file.
# Quarantines a torn/malformed trailing line instead of dropping it
# silently or crashing (JOUR-04 / PITFALLS.md Pitfall 10).
# --------------------------------------------------------------------------- #
def _read_records(journal_path):
    """(records, warnings). Missing file -> ([], []), never an error. Each
    non-empty physical line is parsed independently; a line that fails to
    parse is quarantined — skipped, not trusted, not fatal — and reported
    in `warnings` naming the byte OFFSET (never a line number, which would
    be meaningless once the journal has been through compaction) it
    starts at and its byte length. Every OTHER line, including everything
    after a corrupted line, is still read (JOUR-04 does not promise the
    corruption is only ever trailing, only that it is never silently
    dropped)."""
    try:
        data = journal_path.read_bytes()
    except OSError:
        return [], []
    records = []
    warnings = []
    offset = 0
    for raw in data.split(b"\n"):
        length = len(raw)
        if raw.strip():
            try:
                records.append(json.loads(raw.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                warnings.append(
                    f"quarantined malformed record at byte offset "
                    f"{offset} ({length} bytes): {e}")
        offset += length + 1  # +1 for the \n consumed by split()
    return records, warnings


# --------------------------------------------------------------------------- #
# last-known folding — dedup lookup for observe, and last-moved's own read
# surface
# --------------------------------------------------------------------------- #
def _last_known(records, phase):
    """Fold PHASE's records, IN FILE ORDER (this journal is single-writer
    and append-only per D-02 — file order IS chronological order; no
    re-sort needed here, unlike a hypothetically git-merged file), into
    {axis: {"value": ..., "ts": ...} | None} for disk/bd/roadmap/
    state_md/verdict/lease. Each dict key is None until that axis has been
    observed at least once for this phase."""
    known = {axis: None for axis in EVIDENCE_AXES}
    known["verdict"] = None
    known["lease"] = None
    for rec in records:
        if rec.get("phase") != phase:
            continue
        event = rec.get("event")
        ts = rec.get("ts")
        if event == "state_changed":
            source = rec.get("source")
            if source in known:
                known[source] = {"value": rec.get("to"), "ts": ts}
        elif event == "verdict_changed":
            known["verdict"] = {"value": rec.get("to"), "ts": ts}
        elif event == "lease_changed":
            known["lease"] = {"value": rec.get("action"),
                               "holder": rec.get("holder"), "ts": ts}
    return known


def _resolve_last_value(known_entry):
    """A _last_known()[...] entry -> the axis's last recorded value, or
    the _NEVER_OBSERVED sentinel when the axis has no prior record at
    all. Distinct from a prior record whose stored value genuinely was
    None (JSON null)."""
    if known_entry is None:
        return _NEVER_OBSERVED
    return known_entry["value"]


# --------------------------------------------------------------------------- #
# record builders
# --------------------------------------------------------------------------- #
def _envelope(root, phase, event, actor=None):
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "nonce": uuid.uuid4().hex,
        "actor": actor if actor is not None else resolve_actor(root),
        "phase": phase,
        "event": event,
    }


def _state_changed_record(root, phase, source, from_value, to_value):
    rec = _envelope(root, phase, "state_changed")
    rec["source"] = source
    rec["from"] = None if from_value is _NEVER_OBSERVED else from_value
    rec["to"] = to_value
    return rec


def _verdict_changed_record(root, phase, from_value, to_value):
    rec = _envelope(root, phase, "verdict_changed")
    rec["from"] = None if from_value is _NEVER_OBSERVED else from_value
    rec["to"] = to_value
    return rec


def _lease_changed_record(root, phase, action, holder, prev_holder, actor):
    rec = _envelope(root, phase, "lease_changed", actor=actor)
    rec["action"] = action
    rec["holder"] = holder
    rec["prev_holder"] = prev_holder
    return rec


# --------------------------------------------------------------------------- #
# stdin payload parsing for `observe`
# --------------------------------------------------------------------------- #
def _load_observe_payload():
    """A JSON array of {"phase": int, "evidence": {...}, "verdict": ...}
    objects read from stdin. Dies with EXIT_USAGE — never a traceback —
    on non-JSON stdin, a non-array top level, or an element missing (or
    mistyping) `phase`. Read once into memory, never streamed line-by-line
    as executable input (T-16-01)."""
    try:
        raw = sys.stdin.read()
    except OSError as e:
        die(f"failed to read stdin: {e}", EXIT_USAGE)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"stdin is not valid JSON: {e}", EXIT_USAGE)
    if not isinstance(data, list):
        die("stdin must be a JSON array of observation objects", EXIT_USAGE)
    for i, item in enumerate(data):
        if not isinstance(item, dict) or "phase" not in item:
            die(f"element {i} is missing required field 'phase'",
                EXIT_USAGE)
        if not isinstance(item["phase"], int) or isinstance(item["phase"],
                                                              bool):
            die(f"element {i}'s 'phase' must be an integer", EXIT_USAGE)
        evidence = item.get("evidence")
        if evidence is not None and not isinstance(evidence, dict):
            die(f"element {i}'s 'evidence' must be an object", EXIT_USAGE)
    return data


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def cmd_observe(args, root):
    """Task 1 scope: straight-through append — one state_changed record
    per evidence axis present in each payload element, `from` always the
    "never observed" sentinel (resolved to null). No dedup yet; that lands
    in Task 2 on top of this same CLI contract."""
    payload = _load_observe_payload()
    journal_path = _journal_path(root)
    written = []

    for item in payload:
        phase = item["phase"]
        evidence = item.get("evidence") or {}
        for axis in EVIDENCE_AXES:
            if axis not in evidence:
                continue
            rec = _state_changed_record(root, phase, axis, _NEVER_OBSERVED,
                                         evidence[axis])
            _append_record(journal_path, rec)
            written.append(rec)

    if args.json:
        print(json.dumps({"written": written}))
    elif not written:
        print("[cairn-journal] no changes")
    else:
        for rec in written:
            print(f"[cairn-journal] phase {rec['phase']}: "
                  f"{rec['source']} -> {rec['to']}")
    sys.exit(EXIT_OK)


def cmd_history(args, root):
    journal_path = _journal_path(root)
    records, warnings = _read_records(journal_path)
    if args.phase is not None:
        records = [r for r in records if r.get("phase") == args.phase]
    records.sort(key=lambda r: (r.get("ts", ""), r.get("nonce", "")))

    if args.json:
        print(json.dumps({"records": records, "warnings": warnings}))
    else:
        for w in warnings:
            print(f"[cairn-journal] warning: {w}", file=sys.stderr)
        for rec in records:
            print(json.dumps(rec, sort_keys=True))
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairn-journal",
        description="Single append-only writer for cairn's observed "
                     "phase-state, lease, and verdict transition "
                     "history.")
    sub = parser.add_subparsers(dest="command", required=True)

    observe = sub.add_parser("observe", help="append state_changed/"
                              "verdict_changed records for a batch of "
                              "phase observations read from stdin")
    observe.set_defaults(func=cmd_observe)

    history = sub.add_parser("history", help="read journaled records, "
                              "optionally filtered by phase")
    history.add_argument("--phase", type=int, default=None)
    history.set_defaults(func=cmd_history)

    for p in (observe, history):
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
