#!/usr/bin/env python3
"""cairn-stop — the flag a running loop respects (phase 50 / STOP-01).

There is no signal to send: the board does not know the pid of a Claude
session, and killing one mid-merge would be the failure this phase exists
to avoid. So the request is a FILE, `.cairn/stop` (gitignored), and the
loops — /cairn:autonomous, /cairn:implement — read it at every boundary
they already have (before planning a phase, before reading the frontier,
before every merge) and stop clean: claims released, position reported,
nothing half-merged.

    request [--phase N | --phase bead:<id>] [--reason TEXT] [--actor A]
                write the flag: {ts, actor, phase|null, reason}. A phase
                narrows the request to one front; null means everything.
    check   [--phase N] [--json]
                exit 3 when a request applies (global, or for this phase),
                0 otherwise; --json prints the flag, or {"requested": false}.
    clear       remove the flag (a loop that honoured it, or a session that
                starts after it — see hooks/session-start.sh).

One reader: cairn-lease.py status and cairn-parallel.py batch print
`stop_requested` by calling stop_requested() below, never by re-reading
the file their own way.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_USAGE, EXIT_REQUESTED = 0, 2, 3
TAG = "[cairn-stop]"


def resolve_root(project_dir):
    return Path(project_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def flag_path(root):
    return Path(root) / ".cairn" / "stop"


def read_flag(root):
    try:
        data = json.loads(flag_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def stop_requested(root, phase=None):
    """The flag when it applies to `phase` (None = any request applies;
    a request with phase null applies to everything), else None."""
    flag = read_flag(root)
    if not flag:
        return None
    target = flag.get("phase")
    if target is None or phase is None or str(target) == str(phase):
        return flag
    return None


def resolve_actor():
    return (os.environ.get("BEADS_ACTOR") or os.environ.get("USER") or "unknown")


def cmd_request(args, root):
    flag = {"ts": datetime.now(timezone.utc).isoformat(),
            "actor": args.actor or resolve_actor(),
            "phase": args.phase, "reason": args.reason or ""}
    path = flag_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(flag, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(dict(flag, requested=True)))
    else:
        where = f"phase {args.phase}" if args.phase else "everything"
        print(f"{TAG} stop requested for {where} by {flag['actor']} — the "
              "loop stops at its next boundary")
    sys.exit(EXIT_OK)


def cmd_check(args, root):
    flag = stop_requested(root, args.phase)
    if args.json:
        print(json.dumps(dict(flag, requested=True) if flag
                         else {"requested": False}))
    elif flag:
        print(f"{TAG} stop requested by {flag.get('actor')} at {flag.get('ts')}"
              f" for {'phase ' + str(flag.get('phase')) if flag.get('phase') else 'everything'}"
              f"{' — ' + flag['reason'] if flag.get('reason') else ''}")
    else:
        print(f"{TAG} no stop requested")
    sys.exit(EXIT_REQUESTED if flag else EXIT_OK)


def cmd_clear(args, root):
    existed = flag_path(root).is_file()
    try:
        flag_path(root).unlink()
    except OSError:
        pass
    if args.json:
        print(json.dumps({"cleared": existed}))
    else:
        print(f"{TAG} {'cleared' if existed else 'nothing to clear'}")
    sys.exit(EXIT_OK)


def build_parser():
    p = argparse.ArgumentParser(prog="cairn-stop")
    sub = p.add_subparsers(dest="command", required=True)
    rq = sub.add_parser("request", help="write the stop flag")
    rq.add_argument("--phase", help="N or bead:<id>; omit for everything")
    rq.add_argument("--reason", default="")
    rq.add_argument("--actor")
    rq.set_defaults(func=cmd_request)
    ck = sub.add_parser("check", help="exit 3 when a stop applies")
    ck.add_argument("--phase", help="N or bead:<id>")
    ck.set_defaults(func=cmd_check)
    cl = sub.add_parser("clear", help="remove the flag")
    cl.set_defaults(func=cmd_clear)
    for s in (rq, ck, cl):
        s.add_argument("--project-dir", metavar="DIR")
        s.add_argument("--json", action="store_true")
    return p


def main():
    args = build_parser().parse_args()
    args.func(args, resolve_root(args.project_dir))


if __name__ == "__main__":
    main()
