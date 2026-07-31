#!/usr/bin/env python3
"""cairn-lease — a phase-level coordination lease for cairn, one level above
bd's own per-issue --claim/--assignee.

Why a bd issue (D-01, measured live this session, not assumed): from inside
a freshly created `git worktree` of a repo already wired with bd, `bd list`
returned the MAIN repo's issues with no local database, no daemon, and no
global registry required, and `bd create` from that worktree produced an
issue immediately visible from the main repo. Both the read path AND the
write path share one database across every worktree of a repo. That is what
makes "the lease is a bd issue" viable instead of reaching for a file-based
lock, which would be split per-worktree by the filesystem the same way
`.planning/` and `.cairn/` already are (they live under the worktree's own
checkout, not under `--git-common-dir`).

Identity (D-02): bd's own actor resolution (`BEADS_ACTOR`, else `git config
user.name`, else `$USER`) is the SAME for two agents on one machine — no use
for telling them apart. `git rev-parse --show-toplevel`, run against the
project root this invocation was pointed at, IS distinct per worktree, so
that absolute path is the lease's holder identity. KNOWN, ACCEPTED
LIMITATION: two agents inside the SAME worktree remain indistinguishable by
this scheme — a real scenario (two terminals in one directory), but outside
this phase's target (one worktree per agent) and not solved here.

Staleness (D-03): a 4-hour heartbeat TTL, never a liveness check on a live
process — every `/cairn:*` invocation is its own short-lived process, so
nothing stays alive for the whole span of a phase to be checked against.

Metadata schema — this script owns the ENTIRE `metadata.cairn.lease` object
on the lease issue and always writes it whole. bd 1.1.0's `bd update
--metadata` REPLACES the value of each top-level key it is given (verified
live this session: setting a new value for "cairn" leaves every OTHER
top-level key alone but wipes whatever "cairn" previously held) — so a
partial patch to just one lease field would silently erase its siblings:

    held:
        {"cairn": {"lease": {
            "phase": <int>,
            "holder": "<acquiring worktree's git rev-parse --show-toplevel>",
            "actor": "<display-only, BEADS_ACTOR/git user.name/$USER>",
            "host": "<socket.gethostname()>",
            "acquired_at": "<ISO8601 UTC, set once, preserved across renew>",
            "heartbeat_at": "<ISO8601 UTC, updated by every acquire/renew>"
        }}}
    vacant:
        {"cairn": {"lease": {"phase": <int>}}}

The lease issue carries ONLY the `lease` label — NEVER `phase-<N>`. A
`phase-<N>` label would make this bookkeeping issue look like real project
work for phase N to cairn-status.py's phase corroboration, cairn-doctor.py's
phase-complete-open check, and work.md's own
`bd list -l phase-<N> --status open` done-check, all three of which treat a
non-closed phase-<N>-labelled issue as unfinished phase work.

Usage:
    cairn-lease.py acquire <N>            [--project-dir DIR] [--json]
    cairn-lease.py release <N>            [--project-dir DIR] [--json]
    cairn-lease.py release --mine         [--project-dir DIR] [--json]
    cairn-lease.py renew   [<N>]          [--project-dir DIR] [--json]
    cairn-lease.py status  <N>            [--project-dir DIR] [--json]
    cairn-lease.py status  --all          [--project-dir DIR] [--json]

    --project-dir DIR   project root for bd/git discovery (default:
                        $CLAUDE_PROJECT_DIR or cwd)
    --json               machine-readable status shape instead of a
                        one-line human report

Behavior:
    acquire <N>    Vacant, already held by this worktree, or stale
                   (heartbeat older than the TTL) -> acquire/renew: one `bd
                   update --claim --metadata` call carrying the FULL
                   replacement lease object, exit 0. Held by another
                   worktree with a fresh heartbeat -> write NOTHING, report
                   who holds it and since when, exit EXIT_HELD (3) — a
                   report, never an error that should stop the caller
                   (D-04).
    release <N>    Unconditionally clears the lease
                   ({"cairn": {"lease": {"phase": N}}} plus `--assignee ""
                   --status open`), regardless of who currently holds it.
                   No-op, exit 0, when no lease issue exists yet for N or it
                   is already vacant. Different from `release --mine`
                   below: this verb releases phase N's lease REGARDLESS of
                   who holds it — verify-post.md calls it once per phase,
                   asserting the phase's cycle is over regardless of who
                   ran it.
    release --mine Releases every lease THIS worktree (by holder identity)
                   currently holds, and only those — a lease held by a
                   DIFFERENT worktree, even on the same machine, is left
                   untouched. Zero matches is a no-op, exit 0.
    renew [<N>]    Heartbeats a lease this worktree ALREADY holds:
                   heartbeat_at -> now, acquired_at unchanged, exit 0. When
                   this worktree is NOT the recorded holder (including
                   "nobody holds it"), a SILENT no-op, exit 0, writes
                   nothing. With no <N>, N is read from
                   <project-dir>/.planning/STATE.md's `active_phase:`
                   frontmatter key (lenient parse, same pattern as
                   cairn-doctor.py's state_frontmatter); no STATE.md, or no
                   active_phase key, is also a silent no-op, exit 0.
    status  <N>    Read-only, NEVER creates the lease issue. Reports phase,
                   id (null if never created), held (true whenever a holder
                   is recorded, stale or not), holder, actor, host,
                   acquired_at, heartbeat_at, stale, ttl_hours. A phase
                   with no lease issue yet reports held=false, every other
                   identity field null.
    status  --all  One status entry (same shape) per phase that has EVER
                   had a lease issue created. An issue whose metadata is
                   unreadable/malformed is skipped, never crashes the whole
                   call. Zero lease issues ever created -> empty array,
                   exit 0.

Exit codes:
    0  ok (including "not held" / "no-op" outcomes — those are not errors)
    2  usage error (non-numeric or missing phase where one is required;
       `status`/`release` given neither a phase number nor their
       `--all`/`--mine` flag)
    3  acquire only: held by another worktree with a live (non-stale)
       heartbeat — nothing was written
    5  bd unavailable (not on PATH, or any bd subprocess call failed or
       returned unparsable JSON)
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_HELD = 3
EXIT_NO_BD = 5

LEASE_TTL_SECONDS = 4 * 60 * 60

USAGE = ("usage: cairn-lease.py {acquire N|release N|release --mine|"
         "renew [N]|status N|status --all} [--project-dir DIR] [--json]")


def die(msg, code):
    print(f"[cairn-lease] error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# identity + root resolution
# --------------------------------------------------------------------------- #
def resolve_root(project_dir):
    if project_dir:
        return Path(project_dir).resolve()
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()


def resolve_holder(root):
    """This invocation's lease identity: `git -C <root> rev-parse
    --show-toplevel`, stripped. Falls back to str(root) when root is not
    inside a git repo (or git itself is unavailable) rather than crashing —
    identity must always resolve to SOMETHING (D-02)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True)
    except FileNotFoundError:
        return str(root)
    if proc.returncode != 0:
        return str(root)
    out = proc.stdout.strip()
    return out or str(root)


def resolve_active_phase(root):
    """active_phase from <root>/.planning/STATE.md's YAML frontmatter,
    parsed leniently (same pattern as cairn-doctor.py's state_frontmatter:
    tolerates quotes and leading zeros). None when the file, its
    frontmatter, or the key is absent — the caller (`renew` with no <N>)
    treats that as a silent no-op, never a crash."""
    try:
        lines = (root / ".planning" / "STATE.md").read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^active_phase\s*:\s*(.+?)\s*$", line)
        if m:
            val = m.group(1).split("#", 1)[0].strip().strip("'\"").strip()
            digits = re.search(r"\d+", val)
            if digits:
                return int(digits.group(0))
    return None


def resolve_actor(root):
    """Display-only actor label — NEVER the lease identity (see D-02). Same
    resolution order bd itself documents: $BEADS_ACTOR, else `git config
    user.name`, else $USER."""
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
# bd access
# --------------------------------------------------------------------------- #
def run_bd(args, root):
    """Run `bd -C <root> <args>`, returning raw stdout. Exits EXIT_NO_BD on
    any failure — bd missing from PATH or a non-zero exit — never lets a
    subprocess failure surface as a traceback."""
    cmd = ["bd", "-C", str(root)] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        die("'bd' not found on PATH", EXIT_NO_BD)
    if proc.returncode != 0:
        die(f"bd {args[0] if args else ''} failed: "
            f"{proc.stderr.strip() or 'unknown error'}", EXIT_NO_BD)
    return proc.stdout


def bd_create_lease_issue(root, phase):
    meta = json.dumps({"cairn": {"lease": {"phase": phase}}})
    out = run_bd(["create", f"phase-{phase} lease", "-t", "chore",
                  "-l", "lease", "--metadata", meta, "--silent"], root)
    issue_id = out.strip()
    if not issue_id:
        die(f"bd create returned no issue id for phase {phase} lease",
            EXIT_NO_BD)
    return issue_id


def bd_list_lease_issues(root):
    """Every bd issue carrying the `lease` label (open and closed)."""
    out = run_bd(["list", "-l", "lease", "--all", "--limit", "0", "--json"],
                 root)
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError as e:
        die(f"bd list returned invalid JSON: {e}", EXIT_NO_BD)
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def write_lease(root, issue_id, payload, claim=False, vacate=False):
    args = ["update", issue_id, "--metadata", json.dumps(payload)]
    if claim:
        args.append("--claim")
    if vacate:
        args += ["--assignee", "", "--status", "open"]
    run_bd(args, root)


# --------------------------------------------------------------------------- #
# lease metadata parsing (defensive — mirrors cairn-doctor.py's gsd_req)
# --------------------------------------------------------------------------- #
def lease_metadata(issue):
    """metadata.cairn.lease dict of a bd issue, defensively parsed. None
    when absent or malformed — a crafted/corrupt metadata value degrades to
    'vacant', never a traceback (T-15-01)."""
    md = issue.get("metadata")
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except json.JSONDecodeError:
            md = None
    cairn = md.get("cairn") if isinstance(md, dict) else None
    lease = cairn.get("lease") if isinstance(cairn, dict) else None
    return lease if isinstance(lease, dict) else None


def find_lease_issue(root, phase):
    """(issue id, lease dict) for phase N's lease issue, or (None, None)
    when no lease issue has ever been created for N."""
    for issue in bd_list_lease_issues(root):
        lease = lease_metadata(issue)
        if lease is None:
            continue
        try:
            lease_phase = int(lease.get("phase"))
        except (TypeError, ValueError):
            continue
        if lease_phase == phase:
            return issue.get("id"), lease
    return None, None


def collect_all_statuses(root):
    """[status_entry(...)] for every phase that has EVER had a lease issue
    created. An issue whose lease metadata is missing/malformed, or whose
    `phase` field isn't int-castable, is skipped — never crashes the whole
    call. Sorted by phase for deterministic output."""
    entries = []
    for issue in bd_list_lease_issues(root):
        lease = lease_metadata(issue)
        if lease is None:
            continue
        try:
            phase = int(lease.get("phase"))
        except (TypeError, ValueError):
            continue
        entries.append(status_entry(phase, issue.get("id"), lease))
    entries.sort(key=lambda e: e["phase"])
    return entries


def lease_payload(phase, holder=None, actor=None, host=None,
                   acquired_at=None, heartbeat_at=None):
    """The {"cairn": {"lease": {...}}} object cairn-lease always writes
    WHOLE (see module docstring: bd's --metadata replaces each top-level
    key wholesale, so a partial patch would erase sibling fields). No
    `holder` means vacant — every other identity field is omitted too."""
    lease = {"phase": phase}
    if holder:
        lease.update(holder=holder, actor=actor, host=host,
                      acquired_at=acquired_at, heartbeat_at=heartbeat_at)
    return {"cairn": {"lease": lease}}


# --------------------------------------------------------------------------- #
# staleness
# --------------------------------------------------------------------------- #
def parse_ts(ts):
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def is_stale(heartbeat_at):
    """True when heartbeat_at is older than the TTL, OR unreadable — a
    lease is never a PERMANENT block (T-15-02 / D-04), so a corrupt or
    missing timestamp degrades to reclaimable, never to perpetually live."""
    if not heartbeat_at:
        return True
    try:
        hb = parse_ts(heartbeat_at)
    except (TypeError, ValueError):
        return True
    if hb.tzinfo is None:
        hb = hb.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - hb).total_seconds()
    return age > LEASE_TTL_SECONDS


# --------------------------------------------------------------------------- #
# status shape + human printing
# --------------------------------------------------------------------------- #
def status_entry(phase, issue_id, lease):
    lease = lease or {}
    holder = lease.get("holder")
    held = bool(holder)
    return {
        "phase": phase,
        "id": issue_id,
        "held": held,
        "holder": holder,
        "actor": lease.get("actor"),
        "host": lease.get("host"),
        "acquired_at": lease.get("acquired_at"),
        "heartbeat_at": lease.get("heartbeat_at"),
        "stale": held and is_stale(lease.get("heartbeat_at")),
        "ttl_hours": LEASE_TTL_SECONDS // 3600,
    }


def print_status_human(entry):
    if not entry["held"]:
        note = " (never created)" if entry["id"] is None else ""
        print(f"[cairn-lease] phase {entry['phase']} lease: not held{note}")
        return
    stale_note = " [STALE]" if entry["stale"] else ""
    print(f"[cairn-lease] phase {entry['phase']} lease{stale_note}: held by "
          f"{entry['holder']} (actor: {entry['actor']}) since "
          f"{entry['acquired_at']}, last renewed {entry['heartbeat_at']}")


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def cmd_acquire(args, root):
    phase = args.phase
    holder = resolve_holder(root)
    actor = resolve_actor(root)
    host = socket.gethostname()
    now = datetime.now(timezone.utc).isoformat()

    issue_id, lease = find_lease_issue(root, phase)
    if issue_id is None:
        issue_id = bd_create_lease_issue(root, phase)
        lease = {"phase": phase}

    current_holder = lease.get("holder")
    already_mine = current_holder == holder
    stale = is_stale(lease.get("heartbeat_at")) if current_holder else False

    if current_holder and not already_mine and not stale:
        entry = status_entry(phase, issue_id, lease)
        if args.json:
            print(json.dumps(entry))
        else:
            print(f"[cairn-lease] phase {phase} lease is held by "
                  f"{current_holder} (actor: {lease.get('actor')}) since "
                  f"{lease.get('acquired_at')}, last renewed "
                  f"{lease.get('heartbeat_at')} — not acquired")
        sys.exit(EXIT_HELD)

    reclaimed = bool(current_holder) and not already_mine
    acquired_at = (lease.get("acquired_at")
                   if already_mine and lease.get("acquired_at") else now)

    payload = lease_payload(phase, holder=holder, actor=actor, host=host,
                             acquired_at=acquired_at, heartbeat_at=now)
    write_lease(root, issue_id, payload, claim=True)

    entry = status_entry(phase, issue_id, payload["cairn"]["lease"])
    if args.json:
        print(json.dumps(entry))
    elif reclaimed:
        print(f"[cairn-lease] reclaimed phase {phase} lease (was stale) — "
              f"previously held by {current_holder} since "
              f"{lease.get('acquired_at')}, last renewed "
              f"{lease.get('heartbeat_at')}")
    elif already_mine:
        print(f"[cairn-lease] phase {phase} lease already yours — "
              f"heartbeat renewed")
    else:
        print(f"[cairn-lease] acquired phase {phase} lease for {holder}")
    sys.exit(EXIT_OK)


def release_one(args, root, phase):
    issue_id, _lease = find_lease_issue(root, phase)
    if issue_id is None:
        if args.json:
            print(json.dumps(status_entry(phase, None, None)))
        else:
            print(f"[cairn-lease] phase {phase} lease: nothing to release "
                  f"(no lease issue exists)")
        return

    write_lease(root, issue_id, lease_payload(phase), vacate=True)
    if args.json:
        print(json.dumps(status_entry(phase, issue_id, None)))
    else:
        print(f"[cairn-lease] released phase {phase} lease")


def cmd_release(args, root):
    if args.mine:
        holder = resolve_holder(root)
        mine = [e for e in collect_all_statuses(root)
                if e["held"] and e["holder"] == holder]
        for entry in mine:
            write_lease(root, entry["id"], lease_payload(entry["phase"]),
                        vacate=True)
        if args.json:
            print(json.dumps({"released": len(mine), "holder": holder,
                               "phases": [e["phase"] for e in mine]}))
        else:
            print(f"[cairn-lease] released {len(mine)} lease(s) held by "
                  f"{holder}")
        sys.exit(EXIT_OK)

    if args.phase is None:
        die("release requires a phase number or --mine\n" + USAGE,
            EXIT_USAGE)
    release_one(args, root, args.phase)
    sys.exit(EXIT_OK)


def cmd_renew(args, root):
    phase = args.phase
    if phase is None:
        phase = resolve_active_phase(root)
        if phase is None:
            sys.exit(EXIT_OK)  # no STATE.md / no active_phase -> silent no-op

    issue_id, lease = find_lease_issue(root, phase)
    if issue_id is None:
        sys.exit(EXIT_OK)  # no lease issue for this phase -> silent no-op

    holder = resolve_holder(root)
    current_holder = lease.get("holder")
    if current_holder != holder:
        sys.exit(EXIT_OK)  # not the holder -> silent no-op, writes nothing

    now = datetime.now(timezone.utc).isoformat()
    payload = lease_payload(phase, holder=holder, actor=lease.get("actor"),
                             host=lease.get("host"),
                             acquired_at=lease.get("acquired_at"),
                             heartbeat_at=now)
    write_lease(root, issue_id, payload, claim=True)

    entry = status_entry(phase, issue_id, payload["cairn"]["lease"])
    if args.json:
        print(json.dumps(entry))
    else:
        print(f"[cairn-lease] phase {phase} lease heartbeat renewed")
    sys.exit(EXIT_OK)


def cmd_status(args, root):
    if args.all:
        entries = collect_all_statuses(root)
        if args.json:
            print(json.dumps(entries))
        elif not entries:
            print("[cairn-lease] no phase leases have ever been created")
        else:
            for entry in entries:
                print_status_human(entry)
        sys.exit(EXIT_OK)

    if args.phase is None:
        die("status requires a phase number or --all\n" + USAGE, EXIT_USAGE)

    issue_id, lease = find_lease_issue(root, args.phase)
    entry = status_entry(args.phase, issue_id, lease)
    if args.json:
        print(json.dumps(entry))
    else:
        print_status_human(entry)
    sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairn-lease",
        description="Phase-level coordination lease for cairn, backed by "
                     "one dedicated bd issue per phase.")
    sub = parser.add_subparsers(dest="command", required=True)

    acquire = sub.add_parser("acquire", help="acquire (or renew) this "
                              "worktree's hold on a phase lease")
    acquire.add_argument("phase", type=int, help="phase number")
    acquire.set_defaults(func=cmd_acquire)

    release = sub.add_parser("release", help="release a phase lease "
                              "unconditionally, or --mine (every lease this "
                              "worktree holds)")
    release.add_argument("phase", type=int, nargs="?", help="phase number")
    release.add_argument("--mine", action="store_true",
                          help="release every lease this worktree holds")
    release.set_defaults(func=cmd_release)

    renew = sub.add_parser("renew", help="heartbeat a lease this worktree "
                            "already holds; silent no-op otherwise")
    renew.add_argument("phase", type=int, nargs="?",
                        help="phase number (default: STATE.md's "
                             "active_phase)")
    renew.set_defaults(func=cmd_renew)

    status = sub.add_parser("status", help="report a phase lease's state, "
                             "or --all (every phase that ever had a lease) "
                             "-- read-only, never creates the lease issue")
    status.add_argument("phase", type=int, nargs="?", help="phase number")
    status.add_argument("--all", action="store_true",
                         help="report every phase that ever had a lease")
    status.set_defaults(func=cmd_status)

    for p in (acquire, release, renew, status):
        p.add_argument("--project-dir", metavar="DIR",
                        help="project root for bd/git discovery (default: "
                             "$CLAUDE_PROJECT_DIR or cwd)")
        p.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    root = resolve_root(args.project_dir)
    if shutil.which("bd") is None:
        die("'bd' not found on PATH", EXIT_NO_BD)
    args.func(args, root)


if __name__ == "__main__":
    main()
