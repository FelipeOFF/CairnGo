#!/usr/bin/env python3
"""cairn-relabel — label/metadata maintenance for cairn's bd data model.

Every cairn-managed issue carries BOTH labels (m-<milestone> and phase-<N>)
plus {"gsd": {...}} metadata. This tool repairs and migrates that pairing:

  PAIR      cairn-relabel.py pair --milestone <m> [--phase <N>] [--dry-run]
            For every issue carrying a phase-* label but NO m-* label
            (optionally scoped to phase N): add label m-<m> and merge
            {"gsd": {"milestone": "<m>"}} into its metadata.

  RENAME    cairn-relabel.py rename m-<X> m-<Y> [--apply]
            Move a WHOLE cycle from one milestone label to another: every
            issue carrying m-<X> (open or closed — a cycle includes its
            history) loses m-<X>, gains m-<Y>, and has metadata.gsd.milestone
            rewritten when it already carried one (a phase carrier has no
            gsd and gets none). The milestone carrier's title prefix
            '<X> — …' becomes '<Y> — …'. Refuses (exit 2) when nothing
            carries m-<X>, when X == Y, or when any issue already carries
            m-<Y> (that would merge two cycles). Unlike pair/renumber this
            one is DRY-RUN BY DEFAULT and needs --apply to write: it exists
            for /cairn:milestone complete, where the label chosen at open is
            the intent and the final version is decided at close, and a
            whole-cycle rewrite is not something to fire by omission. Git
            branches, .cairn/id-map.json and the journal are NOT touched —
            the run says so.
  RENUMBER  cairn-relabel.py renumber --from <N> --to <M> [--milestone <m>]
                                      [--force] [--dry-run]
            For every issue with label phase-<N> (AND m-<milestone> when
            given): remove phase-<N>, add phase-<M>, and set
            metadata.gsd.phase to M. Refuses when any target issue already
            carries phase-<M> (ambiguous double-label) unless --force. The
            refusal applies in --dry-run too: a preview of a refused run is
            the refusal itself.

pair and renumber accept --dry-run; rename inverts the default (--apply): print one 'DRY-RUN: <id> <change>' line per
would-be change, write nothing, exit 0. Non-dry runs print one line per
applied change and a final count. --dir <project_dir> runs bd against another
checkout (passed through as bd -C).

Metadata is merged, never clobbered: bd 1.1.0's `bd update --metadata` merges
top-level keys but REPLACES each provided key's value wholesale (verified:
sending {"gsd": {"milestone": ...}} drops a pre-existing gsd.req). So we read
the current metadata via `bd show --json`, deep-merge the gsd object in
Python, and write the full merged metadata back.

Exit codes: 0 ok, 1 partial failure applying changes, 2 usage error or
refusal, 5 bd unavailable (not on PATH, or the initial bd list fails).
"""
import argparse
import json
import re
import subprocess
import sys

PHASE_RE = re.compile(r"^phase-(\d+)$")


def die(msg, code=1):
    print(f"[cairn-relabel] error: {msg}", file=sys.stderr)
    sys.exit(code)


def run_bd(args, project_dir=None):
    """Run bd, returning (stdout, error). Exits 5 when bd is not on PATH."""
    cmd = ["bd"]
    if project_dir:
        cmd += ["-C", project_dir]
    cmd += args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        die("'bd' not found on PATH", 5)
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"exit {proc.returncode}"
    return proc.stdout, None


def list_issues(project_dir):
    out, err = run_bd(["list", "--all", "-n", "0", "--json"], project_dir)
    if err:
        die(f"bd list failed: {err}", 5)
    try:
        issues = json.loads(out) if out.strip() else []
    except json.JSONDecodeError as e:
        die(f"bd list returned invalid JSON: {e}", 5)
    if not isinstance(issues, list):
        issues = issues.get("issues", [])
    for issue in issues:
        issue["labels"] = issue.get("labels") or []
    return sorted(issues, key=lambda i: i.get("id", ""))


def fetch_metadata(bd_id, project_dir):
    """Current metadata dict of one issue, via bd show --json."""
    out, err = run_bd(["show", bd_id, "--json"], project_dir)
    if err:
        return None, err
    data = json.loads(out)
    issue = data[0] if isinstance(data, list) else data
    meta = issue.get("metadata")
    return (meta if isinstance(meta, dict) else {}), None


def merge_gsd(bd_id, gsd_updates, project_dir):
    """Deep-merge keys into metadata.gsd, preserving everything else."""
    meta, err = fetch_metadata(bd_id, project_dir)
    if err:
        return f"bd show: {err}"
    gsd = meta.get("gsd")
    if not isinstance(gsd, dict):
        gsd = {}
    gsd.update(gsd_updates)
    meta["gsd"] = gsd
    _, err = run_bd(["update", bd_id, "--metadata", json.dumps(meta)],
                    project_dir)
    return f"bd update: {err}" if err else None


def phase_labels(issue):
    return [lb for lb in issue["labels"] if PHASE_RE.match(lb)]


def has_milestone_label(issue):
    return any(lb.startswith("m-") for lb in issue["labels"])


# --------------------------------------------------------------------------- #
# pair: add the missing m-<milestone> label + gsd.milestone metadata
# --------------------------------------------------------------------------- #
def do_pair(args):
    candidates = []
    for issue in list_issues(args.dir):
        phases = phase_labels(issue)
        if not phases or has_milestone_label(issue):
            continue
        if args.phase is not None and f"phase-{args.phase}" not in phases:
            continue
        candidates.append(issue)

    label = f"m-{args.milestone}"
    change = f"+{label} gsd.milestone={args.milestone}"
    if args.dry_run:
        for issue in candidates:
            print(f"DRY-RUN: {issue['id']} {change}")
        return 0

    failed = 0
    for issue in candidates:
        bd_id = issue["id"]
        _, err = run_bd(["label", "add", bd_id, label], args.dir)
        if err is None:
            err = merge_gsd(bd_id, {"milestone": args.milestone}, args.dir)
        if err:
            failed += 1
            print(f"[cairn-relabel] FAIL {bd_id}: {err}", file=sys.stderr)
            continue
        print(f"{bd_id} {change}")
    print(f"[cairn-relabel] pair: {len(candidates) - failed} issue(s) updated")
    return 1 if failed else 0


# --------------------------------------------------------------------------- #
# renumber: move phase-<N> -> phase-<M> (labels + gsd.phase)
# --------------------------------------------------------------------------- #
def do_renumber(args):
    if args.from_phase == args.to_phase:
        die("--from and --to are the same phase", 2)
    old, new = f"phase-{args.from_phase}", f"phase-{args.to_phase}"

    targets = []
    for issue in list_issues(args.dir):
        if old not in issue["labels"]:
            continue
        if args.milestone and f"m-{args.milestone}" not in issue["labels"]:
            continue
        targets.append(issue)

    doubled = [i["id"] for i in targets if new in i["labels"]]
    if doubled and not args.force:
        verb = "carry" if len(doubled) > 1 else "carries"
        die(f"refusing: {', '.join(doubled)} already {verb} {new} (ambiguous "
            f"double-label) — rerun with --force to renumber anyway", 2)

    change = f"{old} -> {new}"
    if args.dry_run:
        for issue in targets:
            print(f"DRY-RUN: {issue['id']} {change}")
        return 0

    failed = 0
    for issue in targets:
        bd_id = issue["id"]
        _, err = run_bd(["label", "remove", bd_id, old], args.dir)
        if err is None:
            _, err = run_bd(["label", "add", bd_id, new], args.dir)
        if err is None:
            err = merge_gsd(bd_id, {"phase": args.to_phase}, args.dir)
        if err:
            failed += 1
            print(f"[cairn-relabel] FAIL {bd_id}: {err}", file=sys.stderr)
            continue
        print(f"{bd_id} {change}")
    print(f"[cairn-relabel] renumber: {len(targets) - failed} issue(s) updated")
    return 1 if failed else 0



# --------------------------------------------------------------------------- #
# rename: move a whole cycle m-<X> -> m-<Y> (labels + gsd.milestone + title)
# --------------------------------------------------------------------------- #
def milestone_key(label):
    """'m-v1.0' -> 'v1.0'; a bare 'v1.0' is accepted and normalised."""
    return label[2:] if label.startswith("m-") else label


def is_milestone_carrier(issue):
    """Mirrors cairn_source.is_milestone_carrier: marker label `milestone`,
    an m-* label, and no phase-* label."""
    return ("milestone" in issue["labels"]
            and not phase_labels(issue)
            and has_milestone_label(issue))


def rename_gsd_milestone(bd_id, new_key, project_dir):
    """Rewrite gsd.milestone ONLY where one already exists; a carrier without
    gsd metadata stays without it. Returns (changed, error)."""
    meta, err = fetch_metadata(bd_id, project_dir)
    if err:
        return False, f"bd show: {err}"
    gsd = meta.get("gsd")
    if not isinstance(gsd, dict) or "milestone" not in gsd:
        return False, None
    gsd["milestone"] = new_key
    meta["gsd"] = gsd
    _, err = run_bd(["update", bd_id, "--metadata", json.dumps(meta)],
                    project_dir)
    return (err is None), (f"bd update: {err}" if err else None)


def do_rename(args):
    old_key, new_key = milestone_key(args.old), milestone_key(args.new)
    old, new = f"m-{old_key}", f"m-{new_key}"
    if old == new:
        die("old and new milestone are the same label", 2)
    issues = list_issues(args.dir)
    targets = [i for i in issues if old in i["labels"]]
    if not targets:
        die(f"no issue carries {old} — nothing to rename", 2)
    taken = [i["id"] for i in issues if new in i["labels"]]
    if taken:
        die(f"refusing: {', '.join(taken)} already carr{'y' if len(taken) > 1 else 'ies'} "
            f"{new} — renaming would merge two cycles", 2)
    title_re = re.compile(r"^" + re.escape(old_key) + r"(?=\s|$)")
    plan = []
    for issue in targets:
        gsd = (issue.get("metadata") or {}).get("gsd") \
            if isinstance(issue.get("metadata"), dict) else None
        parts = [f"{old} -> {new}"]
        if isinstance(gsd, dict) and "milestone" in gsd:
            parts.append(f"gsd.milestone={new_key}")
        new_title = None
        if is_milestone_carrier(issue) and title_re.match(issue.get("title") or ""):
            new_title = title_re.sub(new_key, issue["title"], count=1)
            parts.append(f"title '{new_title}'")
        plan.append((issue, " ".join(parts), new_title))
    untouched = ("[cairn-relabel] not touched: git branches, .cairn/id-map.json "
                 f"and the journal — grep them for {old} yourself")
    if not args.apply:
        for issue, change, _ in plan:
            print(f"DRY-RUN: {issue['id']} {change}")
        print(untouched)
        print(f"[cairn-relabel] rename: {len(plan)} issue(s) would change "
              "(dry-run; pass --apply to write)")
        return 0
    failed = 0
    for issue, change, new_title in plan:
        bd_id = issue["id"]
        _, err = run_bd(["label", "remove", bd_id, old], args.dir)
        if err is None:
            _, err = run_bd(["label", "add", bd_id, new], args.dir)
        if err is None:
            _, err = rename_gsd_milestone(bd_id, new_key, args.dir)
        if err is None and new_title is not None:
            _, err = run_bd(["update", bd_id, "--title", new_title], args.dir)
        if err:
            failed += 1
            print(f"[cairn-relabel] FAIL {bd_id}: {err}", file=sys.stderr)
            continue
        print(f"{bd_id} {change}")
    print(untouched)
    print(f"[cairn-relabel] rename: {len(plan) - failed} issue(s) updated")
    return 1 if failed else 0

def main():
    parser = argparse.ArgumentParser(
        prog="cairn-relabel",
        description="Repair/migrate cairn's m-<milestone> + phase-<N> "
                    "label pairing and gsd metadata in bd.")
    sub = parser.add_subparsers(dest="command", required=True)

    pair = sub.add_parser("pair", help="add m-<milestone> to phase-labeled "
                                       "issues that lack any m-* label")
    pair.add_argument("--milestone", required=True, metavar="M",
                      help="milestone name, e.g. v1.0 (label becomes m-v1.0)")
    pair.add_argument("--phase", type=int, metavar="N",
                      help="only issues carrying label phase-N")
    pair.set_defaults(func=do_pair)

    ren = sub.add_parser("renumber",
                         help="move phase-<N> to phase-<M>, labels + metadata")
    ren.add_argument("--from", dest="from_phase", required=True, type=int,
                     metavar="N", help="current phase number")
    ren.add_argument("--to", dest="to_phase", required=True, type=int,
                     metavar="M", help="new phase number")
    ren.add_argument("--milestone", metavar="M",
                     help="only issues also carrying m-<milestone>")
    ren.add_argument("--force", action="store_true",
                     help="proceed even when a target already has phase-<M>")
    ren.set_defaults(func=do_renumber)

    rn = sub.add_parser("rename", help="move a whole cycle m-<X> -> m-<Y>: "
                                       "labels, gsd.milestone, carrier title")
    rn.add_argument("old", metavar="m-<X>", help="current milestone label")
    rn.add_argument("new", metavar="m-<Y>", help="new milestone label")
    rn.add_argument("--apply", action="store_true",
                    help="write the changes (default is a dry run)")
    rn.add_argument("--dir", metavar="DIR",
                    help="project dir for bd discovery (bd -C DIR)")
    rn.set_defaults(func=do_rename)

    for p in (pair, ren):
        p.add_argument("--dry-run", action="store_true",
                       help="print would-be changes, write nothing")
        p.add_argument("--dir", metavar="DIR",
                       help="project dir for bd discovery (bd -C DIR)")

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
