#!/usr/bin/env python3
"""cairn-journal — the single append-only writer for cairn's own observed
state history (D-02), partitioned one file per checkout and versioned
(phase 28, DJOUR-02).

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
            now_utc()) — sub-second ordering resolution is what the
            per-partition fold sorts on once git CAN merge a partition
            file (see "Location and git status" below).
    nonce   str, uuid.uuid4().hex — a uniqueness tiebreaker for records
            written in the same instant, and future-proofing per
            STACK.md's merge=union collision finding: byte-identical
            lines silently deduplicate under that driver, and this nonce
            is what makes two real records never byte-identical. Written
            since phase 16 as future-proofing; load-bearing since phase
            28, which is when the file became git-tracked.
    actor   str, resolve_actor()'s BEADS_ACTOR / `git config user.name` /
            $USER chain (reimplemented here verbatim per house convention
            — no shared lib, die()-style helpers are duplicated per
            script; see cairn-lease.py's own resolve_actor()).
    machine str or null (phase 28, DJOUR-04) — resolve_machine()'s
            CAIRN_JOURNAL_MACHINE / socket.gethostname() chain.
    checkout str or null (phase 28, DJOUR-04) — resolve_checkout()'s
            CAIRN_JOURNAL_CHECKOUT / sha256(machine + NUL + root)[:12]
            chain. See those two functions for why identity is DERIVED,
            never stored, and why `machine` is folded into the checkout
            hash.
    phase   int
    event   str — "state_changed", "verdict_changed", or "lease_changed"

Provenance and the records written before it existed (phase 28, DJOUR-04)
— `actor` alone cannot tell two checkouts apart: it is the git user, and
it was measured IDENTICAL across all four simultaneous checkouts of this
repository (176/64/1/1 records, one actor). `machine`/`checkout` are the
fields that separate them, and they only exist from phase 28 onward. A
record written before that carries neither and NEVER will: it is read as
UNKNOWN — `machine: null`, `checkout: null` — and never stamped with the
current host and checkout. Stamping would look like a migration and would
be fabrication: nobody knows where an inherited journal came from, and the
file may have been copied. record_provenance() is the single read point
for this, and it deliberately never calls resolve_machine().

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
    snapshot        written only by compact() (Plan 16-02, D-03; phase 28
                    D-06 moved it to the head of the NEXT segment instead
                    of over the old one) — folds a phase's ENTIRE prior
                    history within THIS PARTITION into one record: state
                    (dict of the four evidence axes, each {"value":...,
                    "ts":...} or null), verdict ({"value":...,"ts":...}
                    or null), lease ({"value":...,"holder":...,"ts":...}
                    or null), and compacted_through_ts (the ts of the
                    latest real event folded into this phase's snapshot —
                    phase 28 made this field LOAD-BEARING: _last_known()
                    folds snapshots by it and then applies only the events
                    that came after it, which is what keeps a
                    union-merged, interleaved partition readable. It used
                    to be provenance only).

Append atomicity — the whole reason this is a single writer (D-02): every
write funnels through _append_record(), which builds the complete line in
memory first (json.dumps(record, sort_keys=True) + "\n", encoded once),
then opens the file with os.open(O_WRONLY | O_CREAT | O_APPEND) and issues
exactly ONE os.write() of that full payload, verifying the returned byte
count. This is deliberately NOT open(path, "a"): a plain buffered
io.TextIOWrapper is not guaranteed to translate one .write() call into
exactly one write(2) syscall — internal buffering/encoding can split it
into several, each individually losing the O_APPEND atomicity guarantee
POSIX defines at the SYSCALL level, not the language-object level (see
.planning/research/STACK.md's "Append-Only Journal" section).
_append_record() also guards a case Task 3's own torn-tail fixture
surfaced: a prior crash can leave the file NOT ending in a newline (JOUR-04
— a torn write). Appending blindly onto that tail would concatenate this
NEW record onto the old garbage, corrupting BOTH into one unparseable
line, making the new record unrecoverable too. A read-only pre-check (a
separate, ordinary file open — the O_WRONLY write fd cannot itself be
read from) inspects the current last byte; if it is not already a newline
(or the file does not exist yet), a leading "\n" is folded into the SAME
single os.write() payload, so the whole thing — separator plus record —
still lands in one atomic syscall.
cairn-migrate.py's Applier.journal() uses exactly this open(path, "a")
recipe — it is the precedent for the JOURNAL IDIOM in this codebase (a
resumable JSONL journal is already production-proven here), but NOT for
this atomicity mechanism; this script deliberately does not copy that
part. PIPE_BUF is also the wrong constant to reason about record size
here — it governs pipe/FIFO writes, not regular-file writes, and measures
512 bytes on macOS (verified in STACK.md); the guarantee this recipe
actually relies on is POSIX O_APPEND atomicity on a regular file, which
carries no PIPE_BUF-sized cap.

Location and git status (REDESIGNED in phase 28, DJOUR-02) — the journal
lives at <project-dir>/.cairn/journal/<slug>-NNNN.jsonl: ONE PARTITION PER
CHECKOUT, each partition a numbered run of segments, all of it VERSIONED.
This is deliberately UNLIKE the phase lease (rooted at --git-common-dir,
shared across worktrees, per cairn-lease.py): partitions are never shared,
they are merged.

What changed and why. Until phase 28 this was one local, gitignored file,
on the stated ground that it "was never meant to be shared across machines
or merged at all". That ground was removed by a decision, not by a
preference: cairn runs on more than one machine and in more than one
session, so the single-writer invariant the old design rested on is false
today, not hypothetically — this repository was measured carrying four
simultaneous checkouts with 176/64/1/1 records under one identical `actor`.
A single shared file would have to be merged, and `merge=union` on a shared
file reorders disjoint appends non-chronologically. Partitioning removes
the question instead of answering it: two checkouts never write the same
file, so a merge only ever concatenates.

Both pieces are required and neither is sufficient, both measured:
different files merge with no driver at all (E11 case 1), but the SAME
partition on two branches of one checkout is an add/add conflict without
`merge=union` (E8b). The driver is the BUILT-IN union and never a custom
one: a custom `merge.<name>.driver` lives in .git/config, which git never
clones, so a machine that skipped the out-of-band setup falls back to the
default merge and conflicts with markers, in silence (E17).

The inherited .cairn/journal.jsonl is still read, as a partition of UNKNOWN
provenance, and is never written, rewritten or deleted (D-04). It is still
covered by .gitignore's `.cairn/journal.jsonl*`; the partition directory is
covered by a whitelist (`.cairn/journal/*` then `!.cairn/journal/*.jsonl`)
so its segments are versioned and the per-machine scratch beside them —
the compaction locks — is not.

Compaction (D-03, Plan 16-02; REDESIGNED in phase 28, D-06) — the journal
is scoped to a project's entire lifetime with no natural discard point
(unlike cairn-migrate.py's per-run resumable journal), so left unbounded
every history/last-moved read gets slower every month (PITFALLS.md Pitfall
8). Compacting now means SEAL THE ACTIVE SEGMENT AND OPEN THE NEXT ONE,
whose first lines are one `snapshot` record per phase. It never rewrites a
segment, never deletes one, and never touches a partition other than this
checkout's own. Three measurements forced each of those three rules
(28-RESEARCH.md):
    - Rewriting is out. The pre-phase-28 recipe built a sibling and
      os.rename'd it over the live journal. On a git-versioned, union-
      merged file that RESURRECTS what was folded — the other branch still
      carries the original lines and union concatenates them back in (E5:
      6 lines where a human expected 2).
    - Deleting is out. Removing a sealed segment turns the next merge into
      modify/delete (E10), which is worse to resolve than a content
      conflict.
    - Crossing partitions is out, and this is the one that matters most.
      E13: two machines compacting the same shared journal left a VALID
      two-line JSONL with one machine's entire history gone — no conflict,
      no error, no signal. Scoping compaction to the partition that owns it
      makes that impossible by construction instead of by care.
The honest trade, accepted with eyes open: compacting a VERSIONED file
saves nothing durable, because every version stays in git history forever.
The win is read time, and a sealed segment delivers exactly that win
without rewriting a byte.
    - JOURNAL_COMPACT_THRESHOLD_BYTES (below) is the auto-trigger
      threshold, measured against the ACTIVE SEGMENT: observe/lease each
      check that size, in-process, before opening it for their own append,
      and call compact() first when over threshold — never as a background
      process (every /cairn:* invocation is already a single short-lived
      process; a background compactor would just be a second process
      racing this one for no benefit).
    - Concurrency, and what is left of it. Two compactions of the SAME
      partition are still serialized by a non-blocking
      `fcntl.flock(LOCK_EX | LOCK_NB)` on that partition's own
      `<slug>.compact.lock`; a contended compaction is SKIPPED for that
      invocation (exit 0, no error). The next segment is created with
      O_CREAT | O_EXCL, which covers what the flock cannot: a segment of
      that number already on disk because a clone compacted first and the
      file arrived through git. Overwriting it would delete somebody
      else's sealed head.
    - Pitfall 14 is GONE, structurally. It was: a record appended by
      observe/lease — which take NO lock at all, correctly, by design —
      landing on the live journal after compact()'s read but before its
      rename, and being silently discarded by that rename. With no rename
      there is no discard. The concurrent record stays in the sealed
      segment, and because its `ts` is later than the snapshot's
      `compacted_through_ts`, _last_known() applies it right on top.
      [SUPOSTO] this assumes the clock does not step backwards within one
      machine between the read and that append — the same assumption the
      per-partition fold already makes, and one no ordering scheme
      available here could remove.
    - CAIRN_JOURNAL_COMPACT_TEST_DELAY (float, seconds): a test-only seam
      (mirrors this codebase's existing CAIRN_GBSYNC/CAIRN_MAP/CAIRN_GATE
      env-seam convention). When set, compact() sleeps for that long
      immediately after its own read/fold, before writing the next
      segment — giving a test a deterministic window in which to run a
      real, separate observe/lease process against the same partition.
      Before phase 28 that window was a data-loss race; it is now the
      window in which nothing can be lost, and the test asserts exactly
      that.

Usage:
    cairn-journal.py observe    [--project-dir DIR] [--json]
                                 (reads a JSON array from stdin)
    cairn-journal.py lease <N> {acquired|released} --holder H
                                 [--prev-holder P] --actor A
                                 [--project-dir DIR] [--json]
    cairn-journal.py history    [--phase N] [--json]
                                 [--project-dir DIR]
    cairn-journal.py last-moved --phase N [--json] [--project-dir DIR]
    cairn-journal.py compact    [--project-dir DIR] [--json]
    cairn-journal.py provenance [--project-dir DIR] [--json]

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
    last-moved    Prints _last_known()'s per-axis {value, ts, machine,
                  checkout, actor} dict (disk/bd/roadmap/state_md/verdict/
                  lease) for one phase, each key null when that axis has
                  never been observed — including for a phase with NO
                  records at all, or no journal file at all. Never an
                  error. `value` and `ts` keep their exact prior meaning
                  and position: cairn-doctor.py's _last_moved_clause()
                  reads entry["ts"] and must not be able to tell the
                  difference. machine/checkout are null for an axis whose
                  last record predates phase 28 — unknown, never the
                  current host.
    provenance    Prints THIS checkout's {machine, checkout, actor}
                  without writing anything. Exists so the identity that
                  partitions the journal is verifiable from outside, and
                  so a test can prove it is stable across runs and
                  distinct across checkouts on one machine.
    compact       SEALS this checkout's active segment and opens the next
                  one, whose first lines are one `snapshot` record per
                  phase (phase 28, D-06). Never rewrites a segment, never
                  deletes one, and never reads or writes any partition
                  but its own. A no-op (exit 0) when this partition has
                  no segment yet, when its active segment is already
                  nothing but snapshots, when the next segment number is
                  already on disk (it arrived through git), or when
                  another compaction of the same partition holds the
                  lock. --json prints {"compacted": bool, "phases": int,
                  "reason": "ok"|"no_journal"|"lock_contended"|
                  "already_compacted"|"segment_exists"}. observe and
                  lease both auto-trigger this, in-process, before their
                  own append, whenever the ACTIVE SEGMENT's byte size is
                  at or past JOURNAL_COMPACT_THRESHOLD_BYTES.

Exit codes:
    0  ok — includes every compact() outcome (no journal, compacted,
       lock-contended skip, aborted-stale-read defer): none of those are
       treated as errors, per the module docstring's "Compaction"
       section.
    2  usage error (malformed stdin, missing/non-numeric phase, unknown
       flag)
    4  a short/failed os.write() during append — extremely rare on a
       local filesystem, but checked per the STACK.md recipe rather than
       trusted blindly.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_WRITE_FAILED = 4

USAGE = ("usage: cairn-journal.py {observe|lease N {acquired|released}|"
         "history|last-moved|compact|provenance} [--project-dir DIR] "
         "[--json]")

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


def resolve_machine():
    """This machine's provenance label (phase 28, DJOUR-04), or None when
    it cannot be measured. Order: $CAIRN_JOURNAL_MACHINE (the house
    CAIRN_* env-seam convention this codebase already uses for
    CAIRN_JOURNAL/CAIRN_GBSYNC/CAIRN_MAP — it is what lets a test drive
    two simulated machines out of one directory), else
    socket.gethostname().

    An empty hostname returns None, never an invented string: a
    provenance field that could not be measured is UNKNOWN, and unknown
    has its own representation (JSON null). This is the same rule that
    governs a pre-phase-28 record — see record_provenance()."""
    env_machine = os.environ.get("CAIRN_JOURNAL_MACHINE")
    if env_machine:
        return env_machine
    try:
        name = socket.gethostname()
    except OSError:
        return None
    return name or None


def resolve_checkout(root, machine):
    """This checkout's stable id (phase 28, DJOUR-04). Order:
    $CAIRN_JOURNAL_CHECKOUT, else the first 12 hex of
    sha256(machine + NUL + resolved-root-path).

    Three properties, and the phase's whole partitioning depends on all
    three:
      1. STABLE across runs in the same checkout — the only inputs are the
         resolved path and the host. No clock, no pid, no random, and
         nothing read from or written to disk.
      2. DISTINCT between checkouts on the same machine — measured, not
         assumed: this repository has four simultaneous checkouts (one
         worktree per in-flight phase) at four distinct paths, carrying
         four histories that never reach each other under one identical
         `actor`.
      3. COLLISION-FREE between machines that happen to share a path —
         /Users/x/Projects/CairnGo is the same string on a laptop and a
         desktop, so `machine` is folded INTO the hash rather than only
         sitting beside it. Consequence, and it belongs in every reader:
         the checkout id is already machine-scoped, so the partition key
         is the PAIR (machine, checkout), never `checkout` alone.

    Nothing is written to disk to remember this. A stored id file would be
    one more piece of per-machine state under .cairn/, needing its own
    ignore rule and its own recovery path. The cost accepted instead, with
    eyes open: renaming the checkout directory (or the hostname changing)
    yields a NEW partition. That is safe by construction — a new partition
    file never conflicts with an old one — and it fragments history. A
    fragmented history that always merges cleanly beats a stored id that
    can go missing."""
    env_checkout = os.environ.get("CAIRN_JOURNAL_CHECKOUT")
    if env_checkout:
        return env_checkout
    digest = hashlib.sha256()
    digest.update((machine or "").encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(root).encode("utf-8"))
    return digest.hexdigest()[:12]


def record_provenance(rec):
    """{"machine","checkout","actor"} read OUT of a record, each key None
    when the record does not carry it (phase 28, DJOUR-04).

    This function deliberately never calls resolve_machine() or
    resolve_checkout(). A record written before phase 28 has neither
    field and never will; filling those in from the current process would
    look like a migration and would be fabrication — the inherited
    journal may have been copied from somewhere else, and nobody knows
    where its records came from. Unknown reads as null."""
    return {
        "machine": rec.get("machine"),
        "checkout": rec.get("checkout"),
        "actor": rec.get("actor"),
    }


# --------------------------------------------------------------------------- #
# paths — one PARTITION per checkout, under .cairn/journal/ (phase 28,
# DJOUR-02). See the module docstring's "Partitions" section for the two
# pieces that are both required and neither sufficient.
# --------------------------------------------------------------------------- #
LEGACY_PARTITION = "legacy"

# Segment filenames are "<slug>-NNNN.jsonl". The slug always ends in the
# 12-hex checkout id, so it can never collide with LEGACY_PARTITION above —
# that is a property of the naming scheme, not a hope.
_SEGMENT_NAME = re.compile(r"^(?P<slug>.+)-(?P<segment>\d{4})\.jsonl$")

_SLUG_UNSAFE = re.compile(r"[^a-z0-9]+")

# How much of the (sanitized) machine name goes into a filename. A cap is
# needed because a hostname has no length bound and a path does; the
# checkout id that follows it is what actually distinguishes partitions,
# so truncating the human-readable half costs nothing but readability.
_SLUG_MACHINE_MAX = 24


def _legacy_journal_path(root):
    """The pre-phase-28 single journal, .cairn/journal.jsonl. Still read —
    as a partition of UNKNOWN provenance — and NEVER written, never
    rewritten, never deleted (D-04/D-06). Its records carry no machine and
    no checkout, and that is exactly how they are reported."""
    return root / ".cairn" / "journal.jsonl"


def _partition_dir(root):
    return root / ".cairn" / "journal"


def _partition_slug(machine, checkout):
    """The filename half of a partition identity: a sanitized, truncated
    machine name followed by the full 12-hex checkout id.

    The sanitized machine name is a FILENAME, never data. The record
    carries the machine as measured; this carries a version of it that
    survives a filesystem. Two hostnames can sanitize to the same string,
    which is exactly why the checkout id — which folds the RAW machine
    name into its hash (see resolve_checkout) — is appended in full and
    is what actually separates two partitions."""
    safe = _SLUG_UNSAFE.sub("-", (machine or "").lower()).strip("-")
    safe = safe[:_SLUG_MACHINE_MAX].strip("-")
    if not safe:
        safe = "host"
    return f"{safe}-{checkout}"


def _own_slug(root):
    machine = resolve_machine()
    return _partition_slug(machine, resolve_checkout(root, machine))


def _segment_paths(root, slug):
    """Every existing segment of SLUG's partition, in ascending segment
    order. Ordering is by the numeric segment, never by mtime: a git
    checkout rewrites mtimes wholesale and would reorder a partition's
    own history for no reason at all."""
    directory = _partition_dir(root)
    found = []
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []
    for path in entries:
        match = _SEGMENT_NAME.match(path.name)
        if match and match.group("slug") == slug:
            found.append((int(match.group("segment")), path))
    found.sort(key=lambda pair: pair[0])
    return [path for _number, path in found]


def _active_segment_path(root, slug):
    """The segment this checkout appends to: the highest-numbered one that
    exists, or segment 0001 when the partition is brand new. Compaction
    (28-03) is the only thing that ever moves this forward, by SEALING the
    current segment and opening the next — a sealed segment is never
    rewritten and never deleted (E5: rewriting makes `union` resurrect
    what was folded; E10: deleting gives modify/delete)."""
    existing = _segment_paths(root, slug)
    if existing:
        return existing[-1]
    return _partition_dir(root) / f"{slug}-0001.jsonl"


def _journal_path(root):
    """This checkout's own active segment — the ONE file observe/lease
    append to. Two checkouts never resolve this to the same path, which is
    what makes a merge a concatenation instead of a reconciliation (E11
    case 1: different files merge with no driver at all)."""
    return _active_segment_path(root, _own_slug(root))


def _own_partition_records(root):
    """(records, warnings) for THIS checkout's partition only — every one
    of its segments, in ascending segment order. This is the input to
    observe's dedup and to compaction: both are scoped to the partition
    that owns them, and neither may read another checkout's history."""
    records = []
    warnings = []
    for path in _segment_paths(root, _own_slug(root)):
        part_records, part_warnings = _read_records(path)
        records.extend(part_records)
        warnings.extend(part_warnings)
    return records, warnings


# --------------------------------------------------------------------------- #
# append primitive — the ONE place any subcommand writes the journal file
# --------------------------------------------------------------------------- #
def _append_record(journal_path, record):
    """Build the complete line in memory, then a single os.open(O_APPEND)
    plus a single os.write() of the whole payload, verifying the byte
    count. Never open(path, "a") — see the module docstring for why.
    Never split a record's own line and its trailing newline into two
    writes.

    One additional guard, discovered by Task 3's own torn-tail fixture: a
    prior crash can leave the file NOT ending in a newline (a torn write,
    JOUR-04). Appending straight onto that tail would silently
    concatenate this NEW record onto the old torn fragment, corrupting
    both into one unparseable line — making the new record unrecoverable
    too, not just the old one. So this function checks the current
    end-of-file byte and, if it is not already a newline (file empty/new
    counts as "no separator needed"), prepends one — still inside this
    SAME os.write() call, so the whole payload (leading separator
    included) lands in one atomic syscall, never a second write."""
    line = json.dumps(record, sort_keys=True).encode("utf-8") + b"\n"
    journal_path.parent.mkdir(parents=True, exist_ok=True)

    # Read-only pre-check, entirely separate from the write fd below (the
    # write fd is O_WRONLY per the STACK.md recipe and cannot be read
    # from). Missing file counts as "no separator needed" — the very
    # first record never gets a leading blank line.
    needs_separator = False
    try:
        with open(journal_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() > 0:
                f.seek(-1, os.SEEK_END)
                needs_separator = f.read(1) != b"\n"
    except FileNotFoundError:
        pass

    payload = (b"\n" if needs_separator else b"") + line
    fd = os.open(str(journal_path),
                 os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        n = os.write(fd, payload)
    finally:
        os.close(fd)
    if n != len(payload):
        die(f"short write to {journal_path}: wrote {n} of {len(payload)} "
            "bytes", EXIT_WRITE_FAILED)


# --------------------------------------------------------------------------- #
# read primitive — the ONE place any subcommand reads the journal file.
# Quarantines a torn/malformed trailing line instead of dropping it
# silently or crashing (JOUR-04 / PITFALLS.md Pitfall 10).
# --------------------------------------------------------------------------- #
def _parse_records(raw):
    """(records, warnings) parsed from RAW bytes already in memory. Split
    out of _read_records() so compact() (Plan 16-02) can derive its
    pre-rename `size_at_read` from the EXACT bytes that were parsed and
    folded — never from a separate stat() call taken after the fact,
    which would reopen the identical TOCTOU gap one level up (an append
    landing between the read and that later stat would inflate
    size_at_read past what was actually folded). Each non-empty physical
    line is parsed independently; a line that fails to parse is
    quarantined — skipped, not trusted, not fatal — and reported in
    `warnings` naming the byte OFFSET (never a line number, which would
    be meaningless once the journal has been through compaction) it
    starts at and its byte length. Every OTHER line, including everything
    after a corrupted line, is still read (JOUR-04 does not promise the
    corruption is only ever trailing, only that it is never silently
    dropped)."""
    records = []
    warnings = []
    offset = 0
    for line in raw.split(b"\n"):
        length = len(line)
        if line.strip():
            try:
                records.append(json.loads(line.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                warnings.append(
                    f"quarantined malformed record at byte offset "
                    f"{offset} ({length} bytes): {e}")
        offset += length + 1  # +1 for the \n consumed by split()
    return records, warnings


def _read_records(journal_path):
    """(records, warnings). Missing file -> ([], []), never an error. Thin
    wrapper around _parse_records() — see that function for the
    quarantine contract."""
    try:
        data = journal_path.read_bytes()
    except OSError:
        return [], []
    return _parse_records(data)


def _read_partitions(root):
    """(partitions, warnings) — every partition this project can see.

    A partition is a dict:
        slug      str, the partition key (LEGACY_PARTITION for the
                  inherited .cairn/journal.jsonl)
        machine   str or None — read from the partition's own records,
                  never resolved from this process. None for `legacy`,
                  whose records predate the field.
        checkout  str or None — same rule.
        paths     [Path] the segments read, in ascending segment order
        records   [dict] their records, concatenated in that order

    The inherited single journal is read as its own partition of UNKNOWN
    provenance (D-04): it is never merged into this checkout's partition,
    because nobody knows where it came from — the file may have been
    copied from another machine. It is never written and never rewritten.

    Partitions come back sorted by slug. That is a DISPLAY order and
    nothing more: no ordering claim is ever made between partitions (E14 —
    a well-synced machine's own NTP offset, −16.7 ms, is larger than the
    10.8 ms minimum gap measured between consecutive journal records, so
    the resolution a cross-machine timeline would need is finer than the
    clock agreement available)."""
    partitions = []
    warnings = []

    legacy_path = _legacy_journal_path(root)
    if legacy_path.exists():
        records, legacy_warnings = _read_records(legacy_path)
        warnings.extend(legacy_warnings)
        partitions.append({
            "slug": LEGACY_PARTITION,
            "machine": None,
            "checkout": None,
            "paths": [legacy_path],
            "records": records,
        })

    by_slug = {}
    directory = _partition_dir(root)
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        entries = []
    for path in entries:
        match = _SEGMENT_NAME.match(path.name)
        if not match:
            continue
        by_slug.setdefault(match.group("slug"), []).append(
            (int(match.group("segment")), path))

    for slug in sorted(by_slug):
        segments = sorted(by_slug[slug], key=lambda pair: pair[0])
        records = []
        paths = []
        for _number, path in segments:
            part_records, part_warnings = _read_records(path)
            records.extend(part_records)
            warnings.extend(part_warnings)
            paths.append(path)
        machine = None
        checkout = None
        for rec in records:
            if rec.get("machine") is not None or rec.get("checkout") is not None:
                machine = rec.get("machine")
                checkout = rec.get("checkout")
                break
        partitions.append({
            "slug": slug,
            "machine": machine,
            "checkout": checkout,
            "paths": paths,
            "records": records,
        })

    return partitions, warnings


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
    observed at least once for this phase.

    Also folds `snapshot` records (Plan 16-02, D-03, compact()'s own
    output) exactly like a real event: a snapshot's `state`/`verdict`/
    `lease` sub-fields overwrite `known` the same way a state_changed/
    verdict_changed/lease_changed record would. This is what makes
    compaction provably lossless for JOUR-05's own truth — a compacted
    file always has its snapshot record(s) earliest in file order (they
    are written once, at compaction time; every subsequent real event is
    necessarily appended AFTER, since observe/lease only ever append), so
    folding a snapshot first and then any later real events over it
    reconstructs exactly the same answer a full, uncompacted replay
    would. Without this branch, last-moved/observe's own dedup lookup
    would see a freshly-compacted journal as "nothing was ever observed"
    for every phase — silently wrong, and the reason this branch was
    added as part of Task 1 rather than left for a later plan to
    discover.

    Every entry also carries the PROVENANCE of the record that set it
    (phase 28, DJOUR-04): machine/checkout/actor, each null when that
    record predates the fields. `value` and `ts` keep their exact prior
    meaning and position — cairn-doctor.py's _last_moved_clause() reads
    entry["ts"] and must not be able to tell that anything changed. The
    snapshot branch copies state/verdict/lease entries through unchanged,
    so a compacted history still reports the ORIGINAL observer, never the
    checkout that ran the compaction.

    ORDERING, and why it is NOT a plain sort (phase 28, DJOUR-02). File
    order stopped being chronological order the moment a partition file
    became git-mergeable: `merge=union` concatenates one branch's block
    then the other's, so two runs of the SAME checkout on two branches
    interleave in time but not in the file (E2). The fix is NOT
    records.sort(key=(ts, nonce)) — that repairs E2 and BREAKS E9,
    because a snapshot's own `ts` is later than everything it folded, so
    a bare sort folds the snapshot LAST and lets it overwrite a real
    later event. What this does instead (E12, measured to work):
      1. Fold every `snapshot` first, in `compacted_through_ts` order,
         tracking the furthest point already folded.
      2. Then fold only the real events whose `ts` is AFTER that point,
         those sorted by (ts, nonce).
    Within one partition every record was written by one checkout on one
    machine, so its own `ts` values are comparable to each other. Between
    partitions they are not, which is why this function is per-partition
    and _merge_last_known() is what unites them."""
    known = {axis: None for axis in EVIDENCE_AXES}
    known["verdict"] = None
    known["lease"] = None

    phase_records = [r for r in records if r.get("phase") == phase]
    snapshots = [r for r in phase_records if r.get("event") == "snapshot"]
    events = [r for r in phase_records if r.get("event") != "snapshot"]

    snapshots.sort(key=lambda r: (r.get("compacted_through_ts") or "",
                                   r.get("ts") or "", r.get("nonce") or ""))
    folded_through = ""
    for rec in snapshots:
        state = rec.get("state") or {}
        for axis in EVIDENCE_AXES:
            if axis in state:
                known[axis] = state[axis]
        if "verdict" in rec:
            known["verdict"] = rec["verdict"]
        if "lease" in rec:
            known["lease"] = rec["lease"]
        through = rec.get("compacted_through_ts") or ""
        if through > folded_through:
            folded_through = through

    events = [r for r in events if (r.get("ts") or "") > folded_through]
    events.sort(key=lambda r: (r.get("ts") or "", r.get("nonce") or ""))
    for rec in events:
        event = rec.get("event")
        ts = rec.get("ts")
        prov = record_provenance(rec)
        if event == "state_changed":
            source = rec.get("source")
            if source in known:
                entry = {"value": rec.get("to"), "ts": ts}
                entry.update(prov)
                known[source] = entry
        elif event == "verdict_changed":
            entry = {"value": rec.get("to"), "ts": ts}
            entry.update(prov)
            known["verdict"] = entry
        elif event == "lease_changed":
            entry = {"value": rec.get("action"),
                     "holder": rec.get("holder"), "ts": ts}
            entry.update(prov)
            known["lease"] = entry
    return known


AXES = EVIDENCE_AXES + ("verdict", "lease")


def _merge_last_known(partitions, phase):
    """Unite every partition's own _last_known() fold for PHASE, WITHOUT
    asserting any order between partitions (phase 28, DJOUR-02, D-08).

    Per axis:
      no partition observed it  -> None, exactly as before partitioning
      exactly one did          -> that partition's entry, unchanged
      two or more did          -> {"value": the agreed value, or null when
                                   they disagree,
                                   "ts": null, "machine": null,
                                   "checkout": null, "actor": null,
                                   "sources": N, "candidates": [...]}

    `ts` is null the moment there is more than one source, and that is the
    whole point: a single timestamp would be an ORDERING CLAIM, and there
    is no source for one. Measured (E14): this machine's own NTP offset is
    −16.7 ms ± 7.9, while the minimum gap between two consecutive journal
    records is 10.8 ms and the median 17.7 ms. Two machines can disagree
    by ~33 ms — two or three positions in a sort. A cross-machine timeline
    ordered by `ts` looks authoritative and is not.

    `value` DOES survive when every source agrees, because "the last known
    value is `complete` everywhere" orders nothing. `candidates` is sorted
    by (machine, checkout, slug) — a DISPLAY order, stated here so nobody
    later reads it as chronology."""
    per_partition = []
    for part in partitions:
        per_partition.append(
            (part, _last_known(part["records"], phase)))

    merged = {}
    for axis in AXES:
        found = []
        for part, known in per_partition:
            entry = known.get(axis)
            if entry is not None:
                candidate = dict(entry)
                candidate["partition"] = part["slug"]
                found.append(candidate)
        if not found:
            merged[axis] = None
            continue
        if len(found) == 1:
            merged[axis] = found[0]
            continue
        found.sort(key=lambda c: (c.get("machine") or "",
                                   c.get("checkout") or "",
                                   c.get("partition") or ""))
        values = [c.get("value") for c in found]
        agreed = values[0] if all(v == values[0] for v in values) else None
        merged[axis] = {
            "value": agreed,
            "ts": None,
            "machine": None,
            "checkout": None,
            "actor": None,
            "sources": len(found),
            "candidates": found,
        }
    return merged


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
    """The ONE place any record is born — which is why phase 28's
    machine/checkout provenance is added here and nowhere else: it lands
    on state_changed, verdict_changed, lease_changed and snapshot at
    once, with no fourth builder able to forget it."""
    machine = resolve_machine()
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "nonce": uuid.uuid4().hex,
        "actor": actor if actor is not None else resolve_actor(root),
        "machine": machine,
        "checkout": resolve_checkout(root, machine),
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


def _build_snapshot_record(root, records, phase):
    """One `snapshot` record folding PHASE's full history, via
    _last_known() (already built, and already the shared source of truth
    for last-moved/observe's own dedup lookup — reusing it here, rather
    than re-deriving state some other way, is exactly what makes a
    snapshot's answer provably identical to a full replay). Carries the
    common envelope (ts/nonce/actor/phase/event) plus state (the four
    evidence axes), verdict, lease, and compacted_through_ts — the latest
    real event's ts folded into this phase's snapshot. compacted_through_ts
    is provenance/debugging only: _last_known() never reads it back, it
    re-derives everything it needs from state/verdict/lease directly."""
    known = _last_known(records, phase)
    phase_ts = [r.get("ts") for r in records
                if r.get("phase") == phase and r.get("ts")]
    rec = _envelope(root, phase, "snapshot")
    rec["state"] = {axis: known[axis] for axis in EVIDENCE_AXES}
    rec["verdict"] = known["verdict"]
    rec["lease"] = known["lease"]
    rec["compacted_through_ts"] = max(phase_ts) if phase_ts else None
    return rec


# --------------------------------------------------------------------------- #
# compaction (D-03, Plan 16-02; REDESIGNED in phase 28, D-06) — seals this
# checkout's active segment and opens the next one, whose first lines are one
# `snapshot` record per phase. Never rewrites, never deletes, never leaves
# this partition. See the module docstring's "Compaction" section for the
# three measurements that force each of those three rules, and for the
# CAIRN_JOURNAL_COMPACT_TEST_DELAY test seam.
# --------------------------------------------------------------------------- #

# Size threshold (bytes) at which observe/lease auto-trigger a compaction
# before their own append. Picked in the low hundreds of KB: small enough
# that this module's own bats tests can drive it directly via the manual
# `compact` subcommand rather than padding a multi-megabyte fixture to
# reach it naturally, large enough that routine day-to-day phase work (a
# handful of observe/lease calls per session) does not compact every few
# appends.
JOURNAL_COMPACT_THRESHOLD_BYTES = 200 * 1024  # 200 KiB


def _compact_lock_path(journal_path):
    """One lock PER PARTITION, next to that partition's segments. Two
    checkouts compacting at the same time must not serialize against each
    other: they touch disjoint files by construction, and a shared lock
    would make one of them skip for no reason (phase 28, DJOUR-02). The
    lock file is per-machine scratch and is never versioned — the
    .gitignore rule for .cairn/journal/ whitelists *.jsonl and nothing
    else."""
    match = _SEGMENT_NAME.match(journal_path.name)
    slug = match.group("slug") if match else journal_path.stem
    return journal_path.parent / f"{slug}.compact.lock"


def _next_segment_path(root, slug, current):
    """The path of the segment that follows CURRENT in SLUG's partition."""
    match = _SEGMENT_NAME.match(current.name)
    number = int(match.group("segment")) if match else 0
    return _partition_dir(root) / f"{slug}-{number + 1:04d}.jsonl"


def compact(root):
    """SEAL this checkout's active segment and open the next one, whose
    first lines are one `snapshot` record per phase (phase 28, D-06).
    Returns {"compacted": bool, "phases": int, "reason": "ok"|"no_journal"|
    "lock_contended"|"already_compacted"|"segment_exists"}. Never raises
    for any of its own no-op paths — every one of those is a normal,
    exit-0 outcome, not an error.

    What changed from the pre-phase-28 recipe, and why every piece of it
    had to (all three measured in 28-RESEARCH.md):

      - NOTHING IS REWRITTEN. Compaction used to build a sibling and
        os.rename it over the live journal. On a git-versioned, union-
        merged file that RESURRECTS what was folded: the other branch
        still carries the original lines, and union concatenates them back
        in (E5 produced 6 lines where a human expected 2). Sealing the
        current segment and opening the next one gives the same read-time
        win with no rewrite at all.
      - NOTHING IS DELETED. Removing a sealed segment turns the next merge
        into modify/delete (E10), which is worse to resolve than a content
        conflict.
      - ONLY THIS CHECKOUT'S OWN PARTITION IS READ OR WRITTEN. This is the
        one that matters most. E13: two machines compacting the shared
        single journal left a VALID two-line JSONL with one machine's
        entire history gone — no conflict, no error, no signal at all.
        Scoping compaction to the partition that owns it makes that
        impossible by construction rather than by care.

    The honest trade this accepts: compacting a VERSIONED file saves
    nothing durable, because every version stays in git history forever.
    The win is read time, and a sealed segment delivers exactly that win
    without rewriting a byte.

    `aborted_stale_read` is gone, and structurally so. It existed for
    Pitfall 14 — a separate process's append landing between this
    function's read and its rename, and being discarded by the rename.
    With no rename there is no discard: the concurrent record stays in the
    sealed segment, and because its `ts` is later than the snapshot's
    `compacted_through_ts`, _last_known() applies it right on top.
    [SUPOSTO] that assumes the clock does not step backwards within one
    machine between the read and that append — the same assumption the
    per-partition fold already makes, and one no ordering scheme available
    here could remove."""
    slug = _own_slug(root)
    segments = _segment_paths(root, slug)
    if not segments:
        return {"compacted": False, "phases": 0, "reason": "no_journal"}

    active = segments[-1]
    lock_path = _compact_lock_path(active)
    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Another compaction of THIS partition already holds this. The
            # caller's own append (if this was an auto-trigger check from
            # observe/lease) still proceeds against the still-live,
            # unsealed segment immediately afterward, which is always
            # correct, just not yet compacted.
            return {"compacted": False, "phases": 0,
                    "reason": "lock_contended"}

        return _compact_locked(root, slug, segments)
    finally:
        # Closing the fd releases any flock held through it (POSIX) —
        # no separate explicit LOCK_UN needed.
        os.close(lock_fd)


def _compact_locked(root, slug, segments):
    """The compaction critical section: read this partition's own
    segments, fold, and write the NEXT segment. Only ever called while the
    caller already holds this partition's non-blocking compaction flock;
    split out of compact() purely for readability, not a separate lock
    boundary."""
    records = []
    for path in segments:
        part_records, _warnings = _read_records(path)
        records.extend(part_records)

    active = segments[-1]
    active_records, _active_warnings = _read_records(active)
    if active_records and all(r.get("event") == "snapshot"
                              for r in active_records):
        # The active segment is already nothing but a freshly-opened
        # compaction head. Without this guard, running compact twice in a
        # row would chain segments of pure snapshots forever.
        return {"compacted": False, "phases": 0,
                "reason": "already_compacted"}

    test_delay = os.environ.get("CAIRN_JOURNAL_COMPACT_TEST_DELAY")
    if test_delay:
        # Test-only seam (mirrors this codebase's existing CAIRN_GBSYNC/
        # CAIRN_MAP/CAIRN_GATE env-seam convention): a deterministic
        # window, right here between the read/fold and the write, in which
        # a test can run a real, separate observe/lease process against
        # this same partition. Before phase 28 this window was a data-loss
        # race (Pitfall 14); it is now the window in which nothing can be
        # lost, and the test asserts exactly that.
        time.sleep(float(test_delay))

    phases = sorted({r.get("phase") for r in records
                      if r.get("phase") is not None})
    snapshots = [_build_snapshot_record(root, records, phase)
                 for phase in phases]

    target = _next_segment_path(root, slug, active)
    payload = b"".join(
        json.dumps(snap, sort_keys=True).encode("utf-8") + b"\n"
        for snap in snapshots)
    try:
        # O_EXCL, not a plain create: the flock only serializes compactions
        # on THIS machine, and the next segment number can already be on
        # disk because a clone compacted first and the file arrived through
        # git. Overwriting it would delete somebody's sealed head.
        fd = os.open(str(target),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return {"compacted": False, "phases": 0, "reason": "segment_exists"}
    try:
        written = os.write(fd, payload)
    finally:
        os.close(fd)
    if written != len(payload):
        die(f"short write to {target}: wrote {written} of {len(payload)} "
            "bytes", EXIT_WRITE_FAILED)

    return {"compacted": True, "phases": len(snapshots), "reason": "ok"}


def _maybe_auto_compact(root, journal_path):
    """Called by observe/lease, in-process, before they open the journal
    for their own append — never as a background process (each
    /cairn:* invocation is already a single short-lived process per this
    codebase's existing model; a background compactor would just be a
    second process racing this one for no benefit). A no-op when the
    journal doesn't exist yet or is still under
    JOURNAL_COMPACT_THRESHOLD_BYTES.

    The size measured is the ACTIVE SEGMENT's, not the whole partition's:
    sealing only shortens the active segment, so the threshold has to
    speak about the thing the seal shortens. The sealed ones stay on disk
    forever by design and would make the trigger fire every single time."""
    try:
        size = journal_path.stat().st_size
    except OSError:
        return
    if size >= JOURNAL_COMPACT_THRESHOLD_BYTES:
        compact(root)


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
        die(f"stdin is not valid JSON: {e}\n{USAGE}", EXIT_USAGE)
    if not isinstance(data, list):
        die(f"stdin must be a JSON array of observation objects\n{USAGE}",
            EXIT_USAGE)
    for i, item in enumerate(data):
        if not isinstance(item, dict) or "phase" not in item:
            die(f"element {i} is missing required field 'phase'\n{USAGE}",
                EXIT_USAGE)
        if not isinstance(item["phase"], int) or isinstance(item["phase"],
                                                              bool):
            die(f"element {i}'s 'phase' must be an integer\n{USAGE}",
                EXIT_USAGE)
        evidence = item.get("evidence")
        if evidence is not None and not isinstance(evidence, dict):
            die(f"element {i}'s 'evidence' must be an object\n{USAGE}",
                EXIT_USAGE)
    return data


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def cmd_observe(args, root):
    """Diff-then-append: for each phase in the batch, each evidence axis
    (and the verdict) whose incoming value differs from what
    _last_known() reports for that phase+axis appends exactly one record;
    axes/verdicts that match the last known value append nothing. This IS
    JOUR-01's "every transition, no non-transition" guarantee. `known` is
    recomputed per item against `existing_records`, which is itself
    appended to as records are written — so two elements in the SAME
    batch for the same phase also dedup against each other, not just
    against what was already on disk before this call."""
    payload = _load_observe_payload()
    _maybe_auto_compact(root, _journal_path(root))
    # Re-resolved AFTER the auto-compaction check: compaction seals the
    # current segment and opens the next one (28-03), so the path this
    # append belongs in can differ from the path that was measured.
    journal_path = _journal_path(root)
    # Dedup is against THIS CHECKOUT'S OWN partition, never the union of
    # all of them (phase 28, DJOUR-02). Deduplicating against another
    # checkout's records would make this one silently skip a transition it
    # genuinely observed, and would make what it writes depend on whether
    # a merge had landed yet. The accepted cost, stated plainly: each
    # checkout records its own first sighting of each axis, so the total
    # record count grows with the number of checkouts. That is the price
    # of every partition being a complete history on its own.
    existing_records, _warnings = _own_partition_records(root)
    written = []

    for item in payload:
        phase = item["phase"]
        evidence = item.get("evidence") or {}
        verdict = item.get("verdict")
        known = _last_known(existing_records, phase)

        for axis in EVIDENCE_AXES:
            if axis not in evidence:
                continue
            to_value = evidence[axis]
            from_value = _resolve_last_value(known[axis])
            if from_value is _NEVER_OBSERVED or from_value != to_value:
                rec = _state_changed_record(root, phase, axis, from_value,
                                             to_value)
                _append_record(journal_path, rec)
                existing_records.append(rec)
                written.append(rec)
                entry = {"value": to_value, "ts": rec["ts"]}
                entry.update(record_provenance(rec))
                known[axis] = entry

        if verdict is not None:
            from_value = _resolve_last_value(known["verdict"])
            if from_value is _NEVER_OBSERVED or from_value != verdict:
                rec = _verdict_changed_record(root, phase, from_value,
                                               verdict)
                _append_record(journal_path, rec)
                existing_records.append(rec)
                written.append(rec)
                entry = {"value": verdict, "ts": rec["ts"]}
                entry.update(record_provenance(rec))
                known["verdict"] = entry

    if args.json:
        print(json.dumps({"written": written}))
    elif not written:
        print("[cairn-journal] no changes")
    else:
        for rec in written:
            if rec["event"] == "state_changed":
                print(f"[cairn-journal] phase {rec['phase']}: "
                      f"{rec['source']} -> {rec['to']}")
            else:
                print(f"[cairn-journal] phase {rec['phase']}: verdict -> "
                      f"{rec['to']}")
    sys.exit(EXIT_OK)


def cmd_lease(args, root):
    """Unconditional append of one lease_changed record — no dedup here;
    see the module docstring's `lease` behavior entry for why."""
    journal_path = _journal_path(root)
    _maybe_auto_compact(root, journal_path)
    rec = _lease_changed_record(root, args.phase, args.action, args.holder,
                                 args.prev_holder, args.actor)
    _append_record(journal_path, rec)
    if args.json:
        print(json.dumps({"written": [rec]}))
    else:
        print(f"[cairn-journal] phase {args.phase}: lease {args.action} "
              f"by {args.holder}")
    sys.exit(EXIT_OK)


def cmd_last_moved(args, root):
    partitions, warnings = _read_partitions(root)
    known = _merge_last_known(partitions, args.phase)
    if args.json:
        out = dict(known)
        out["warnings"] = warnings
        print(json.dumps(out))
    else:
        for w in warnings:
            print(f"[cairn-journal] warning: {w}", file=sys.stderr)
        for axis, val in known.items():
            if val is None:
                print(f"[cairn-journal] phase {args.phase}: {axis} never "
                      "observed")
            elif val.get("candidates"):
                # More than one partition observed this axis. Each is named
                # by its own machine, and no order is claimed between them.
                for cand in val["candidates"]:
                    print(f"[cairn-journal] phase {args.phase}: {axis} = "
                          f"{cand.get('value')} (last moved {cand.get('ts')} "
                          f"on {cand.get('machine')}) — order between "
                          "machines not claimed")
            else:
                print(f"[cairn-journal] phase {args.phase}: {axis} = "
                      f"{val.get('value')} (last moved {val['ts']})")
    sys.exit(EXIT_OK)


def cmd_history(args, root):
    """Records partition by partition, each block sorted by (ts, nonce)
    inside itself — never one global sort across partitions, which is
    exactly the cross-machine timeline E14 measured to be unbuildable
    (−16.7 ms clock offset against a 10.8 ms minimum record gap). The
    partition order is a display order, and the records carry their own
    machine/checkout so a reader never has to infer where a line came
    from."""
    partitions, warnings = _read_partitions(root)
    records = []
    summary = []
    for part in partitions:
        block = part["records"]
        if args.phase is not None:
            block = [r for r in block if r.get("phase") == args.phase]
        block = sorted(block, key=lambda r: (r.get("ts", ""),
                                              r.get("nonce", "")))
        records.extend(block)
        summary.append({
            "slug": part["slug"],
            "machine": part["machine"],
            "checkout": part["checkout"],
            "records": len(block),
            "segments": [p.name for p in part["paths"]],
        })

    if args.json:
        print(json.dumps({"records": records, "warnings": warnings,
                          "partitions": summary}))
    else:
        for w in warnings:
            print(f"[cairn-journal] warning: {w}", file=sys.stderr)
        for rec in records:
            print(json.dumps(rec, sort_keys=True))
    sys.exit(EXIT_OK)


def cmd_provenance(args, root):
    """This checkout's own {machine, checkout, actor} — resolved, never
    read back from any record, and never written anywhere. The identity
    that partitions the journal has to be inspectable from outside, or a
    test cannot prove it is stable across runs and distinct across
    checkouts on one machine (phase 28, DJOUR-04)."""
    machine = resolve_machine()
    checkout = resolve_checkout(root, machine)
    slug = _partition_slug(machine, checkout)
    out = {
        "machine": machine,
        "checkout": checkout,
        "actor": resolve_actor(root),
        "partition": slug,
        "segment": str(_active_segment_path(root, slug)),
    }
    if args.json:
        print(json.dumps(out, sort_keys=True))
    else:
        print(f"[cairn-journal] machine: {out['machine']}")
        print(f"[cairn-journal] checkout: {out['checkout']}")
        print(f"[cairn-journal] actor: {out['actor']}")
        print(f"[cairn-journal] partition: {out['partition']}")
        print(f"[cairn-journal] segment: {out['segment']}")
    sys.exit(EXIT_OK)


def cmd_compact(args, root):
    """Manual/on-demand compaction — also what this module's own bats
    tests use to trigger compaction deterministically, without growing a
    fixture to JOURNAL_COMPACT_THRESHOLD_BYTES."""
    result = compact(root)
    if args.json:
        print(json.dumps(result))
    elif result["reason"] == "no_journal":
        print("[cairn-journal] no journal to compact")
    elif result["reason"] == "lock_contended":
        print("[cairn-journal] compaction already in progress, skipped")
    elif result["reason"] == "already_compacted":
        print("[cairn-journal] active segment is already a compaction "
              "head, nothing to seal")
    elif result["reason"] == "segment_exists":
        print("[cairn-journal] the next segment already exists (it "
              "arrived through git), skipped")
    else:
        print(f"[cairn-journal] compacted {result['phases']} phase(s)")
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

    lease = sub.add_parser("lease", help="unconditionally append one "
                            "lease_changed record — no dedup, that is the "
                            "caller's job")
    lease.add_argument("phase", type=int, help="phase number")
    lease.add_argument("action", choices=["acquired", "released"])
    lease.add_argument("--holder", required=True,
                        help="worktree identity involved in this event")
    lease.add_argument("--prev-holder", default=None,
                        help="previous holder, when relevant (optional)")
    lease.add_argument("--actor", required=True,
                        help="display-only actor name (caller-supplied — "
                             "not re-resolved here)")
    lease.set_defaults(func=cmd_lease)

    history = sub.add_parser("history", help="read journaled records, "
                              "optionally filtered by phase")
    history.add_argument("--phase", type=int, default=None)
    history.set_defaults(func=cmd_history)

    last_moved = sub.add_parser("last-moved", help="report each axis's "
                                 "last known value+timestamp for a phase")
    last_moved.add_argument("--phase", type=int, required=True)
    last_moved.set_defaults(func=cmd_last_moved)

    compact_cmd = sub.add_parser("compact", help="fold each phase's full "
                                  "history into one snapshot record, "
                                  "replacing the journal via a flock-"
                                  "guarded atomic rename swap (D-03)")
    compact_cmd.set_defaults(func=cmd_compact)

    provenance = sub.add_parser("provenance", help="print this checkout's "
                                 "machine/checkout/actor identity without "
                                 "writing anything")
    provenance.set_defaults(func=cmd_provenance)

    for p in (observe, lease, history, last_moved, compact_cmd, provenance):
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
