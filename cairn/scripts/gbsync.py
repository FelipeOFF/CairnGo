#!/usr/bin/env python3
"""gbsync — hub-and-spoke, pull-on-demand sync dispatcher for cairn.

bd (beads) is the HUB / source of truth. Every external tool syncs to bd; tools
never sync to each other. Two directions:

  PUSH  (bd -> tools)   fired on a bd lifecycle event
        gbsync.py <create|update|close> <bd_id>
        Fans a normalized event to each enabled adapter; records bd-id<->ext-id.

  PULL  (tools -> bd)   reconcile-on-demand
        gbsync.py pull [--since <iso>]
        Asks each adapter for the current state of its mapped items, then
        reconciles into bd with last-writer-wins by timestamp. Genuine
        both-sides-changed cases are written to .cairn/conflicts.json.

Both directions accept --dry-run: walk the same decision logic but only print
the would-be operations (issue ids + operations, one per line, prefixed
'DRY-RUN:') without invoking any adapter or writing id-map/state/conflicts.

State files (all under <project>/.cairn/):
    sync.json       backends config (committed; contains ENV VAR NAMES, no secrets)
    id-map.json     { bd_id: { backend_type: external_id } }
    state.json      { last_pull: { backend_type: iso8601 } }  (sync watermarks)
    conflicts.json  append-only log of both-sides-changed reconciliations

Adapter contract (../adapters/<adapter>):
    PUSH  stdin : {action, bd_id, title, body, status, labels, external_id, config}
          stdout: external id (string)
    PULL  stdin : {action:"pull", config, items:[{bd_id, external_id}]}
          stdout: JSON array [{bd_id, external_id, title, body, status, updated_at}]
                  status normalized to open|in_progress|closed; updated_at ISO8601
    exit 0 on success; nonzero => dispatcher logs and continues.

No secrets are read/written by this dispatcher. Adapters read tokens from env
vars named in their config.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ADAPTERS_DIR = Path(__file__).resolve().parent.parent / "adapters"
PUSH_ACTIONS = {"create", "update", "close"}
VALID_STATUS = {"open", "in_progress", "closed"}
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def die(msg, code=1):
    print(f"[gbsync] error: {msg}", file=sys.stderr)
    sys.exit(code)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s):
    if not s:
        return EPOCH
    s = str(s).strip().replace("Z", "+00:00")
    # Normalize a trailing numeric offset without a colon (e.g. +0000 -> +00:00),
    # which older datetime.fromisoformat rejects. Jira returns this form.
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return EPOCH


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}")


def write_json(path, obj):
    Path(path).parent.mkdir(exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def bd_fetch(bd_id):
    try:
        out = subprocess.run(["bd", "show", bd_id, "--json"],
                             capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        die("'bd' not found on PATH")
    except subprocess.CalledProcessError as e:
        die(f"bd show {bd_id} failed: {e.stderr.strip()}")
    data = json.loads(out)
    issue = data[0] if isinstance(data, list) else data
    status = issue.get("status", "open")
    if status not in VALID_STATUS:
        status = "open"
    body = issue.get("description", "") or ""
    notes = issue.get("notes")
    if notes:
        body = f"{body}\n\n---\n_bd notes:_ {notes}".strip()
    return {
        "bd_id": issue.get("id", bd_id),
        "title": issue.get("title", bd_id),
        "body": body,
        "status": status,
        "labels": issue.get("labels", []) or [],
        "updated_at": parse_ts(issue.get("updated_at")),
    }


def bd_apply(bd_id, title, body, status):
    """Reconcile an external state into bd (external won LWW)."""
    cmd = ["bd", "update", bd_id, "--title", title, "--body-file", "-"]
    if status in VALID_STATUS:
        cmd += ["--status", status]
    try:
        subprocess.run(cmd, input=body or "", text=True,
                       capture_output=True, check=True)
        return None
    except subprocess.CalledProcessError as e:
        return e.stderr.strip() or f"exit {e.returncode}"


def resolve_adapter(name):
    for cand in (name, f"{name}.py", f"{name}.sh"):
        p = ADAPTERS_DIR / cand
        if p.exists():
            return p
    return None


def run_adapter(adapter_path, event):
    if adapter_path.suffix == ".py":
        cmd = [sys.executable, str(adapter_path)]
    elif adapter_path.suffix == ".sh":
        cmd = ["bash", str(adapter_path)]
    else:
        cmd = [str(adapter_path)]
    proc = subprocess.run(cmd, input=json.dumps(event),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"exit {proc.returncode}"
    return proc.stdout.strip(), None


def enabled_backends(cfg):
    return [b for b in cfg.get("backends", []) if b.get("enabled")]


# --------------------------------------------------------------------------- #
# PUSH:  bd -> tools
# --------------------------------------------------------------------------- #
def do_push(action, bd_id, base, cfg, dry_run=False):
    backends = enabled_backends(cfg)
    if not backends:
        print("[gbsync] no enabled backends — nothing to mirror")
        return 0
    issue = bd_fetch(bd_id)
    idmap = load_json(base / "id-map.json", {})
    entry = idmap.setdefault(bd_id, {})
    if dry_run:
        for b in backends:
            btype = b.get("type", "?")
            adapter = resolve_adapter(b.get("adapter", btype))
            if not adapter:
                print(f"DRY-RUN: {btype} skip {bd_id} "
                      f"(adapter '{b.get('adapter', btype)}' not found)")
                continue
            ext = entry.get(btype)
            print(f"DRY-RUN: {btype} {action} {bd_id} -> {ext or '(new)'}")
        return 0
    results = []
    for b in backends:
        btype = b.get("type", "?")
        adapter = resolve_adapter(b.get("adapter", btype))
        if not adapter:
            results.append((btype, "skip", f"adapter '{b.get('adapter', btype)}' not found"))
            continue
        event = {
            "action": action, "bd_id": issue["bd_id"], "title": issue["title"],
            "body": issue["body"], "status": issue["status"],
            "labels": issue["labels"], "external_id": entry.get(btype),
            "config": b.get("config", {}),
        }
        ext, err = run_adapter(adapter, event)
        if err:
            results.append((btype, "FAIL", err))
            continue
        if ext:
            entry[btype] = ext
        results.append((btype, "ok", f"{action} -> {ext or entry.get(btype, '?')}"))
    write_json(base / "id-map.json", idmap)
    print(f"[gbsync] push {action} {bd_id}:")
    for btype, state, detail in results:
        print(f"  {state:8} {btype:14} {detail}")
    return 2 if any(s == "FAIL" for _, s, _ in results) else 0


# --------------------------------------------------------------------------- #
# PULL:  tools -> bd  (reconcile, last-writer-wins)
# --------------------------------------------------------------------------- #
def do_pull(base, cfg, since_override, dry_run=False):
    backends = enabled_backends(cfg)
    if not backends:
        print("[gbsync] no enabled backends — nothing to pull")
        return 0
    idmap = load_json(base / "id-map.json", {})
    state = load_json(base / "state.json", {})
    last_pull = state.setdefault("last_pull", {})
    conflicts = load_json(base / "conflicts.json", [])
    started = now_iso()
    results = []

    for b in backends:
        btype = b.get("type", "?")
        adapter = resolve_adapter(b.get("adapter", btype))
        if not adapter:
            if dry_run:
                print(f"DRY-RUN: {btype} skip (adapter not found)")
            else:
                results.append((btype, "skip", "adapter not found"))
            continue
        items = [{"bd_id": bid, "external_id": m[btype]}
                 for bid, m in idmap.items() if m.get(btype)]
        if not items:
            if dry_run:
                print(f"DRY-RUN: {btype} skip (no mapped items)")
            else:
                results.append((btype, "skip", "no mapped items"))
            continue
        watermark = parse_ts(since_override or last_pull.get(btype))
        if dry_run:
            wm = watermark.strftime("%Y-%m-%dT%H:%M:%SZ")
            for it in items:
                print(f"DRY-RUN: {btype} pull {it['bd_id']} "
                      f"<- {it['external_id']} (since {wm})")
            continue
        out, err = run_adapter(adapter, {"action": "pull",
                                         "config": b.get("config", {}),
                                         "items": items})
        if err:
            results.append((btype, "FAIL", err))
            continue
        try:
            ext_states = json.loads(out) if out else []
        except json.JSONDecodeError as e:
            results.append((btype, "FAIL", f"bad adapter JSON: {e}"))
            continue

        applied = skipped = conflicted = 0
        for ext in ext_states:
            bid = ext.get("bd_id")
            if not bid:
                continue
            bd = bd_fetch(bid)
            ext_ts = parse_ts(ext.get("updated_at"))
            ext_changed = ext_ts > watermark
            bd_changed = bd["updated_at"] > watermark
            if not ext_changed:
                skipped += 1
                continue
            if ext_changed and bd_changed:
                conflicted += 1
                conflicts.append({
                    "at": started, "backend": btype, "bd_id": bid,
                    "external_id": ext.get("external_id"),
                    "resolution": "external" if ext_ts > bd["updated_at"] else "bd",
                    "bd_updated_at": bd["updated_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "ext_updated_at": ext.get("updated_at"),
                })
                if ext_ts <= bd["updated_at"]:
                    continue  # bd wins; push path will propagate
            # external wins -> apply to bd
            aerr = bd_apply(bid, ext.get("title", bd["title"]),
                            ext.get("body", bd["body"]),
                            ext.get("status", bd["status"]))
            if aerr:
                results.append((btype, "FAIL", f"{bid}: bd update: {aerr}"))
            else:
                applied += 1
        last_pull[btype] = started
        results.append((btype, "ok",
                        f"applied={applied} conflicts={conflicted} skipped={skipped}"))

    if dry_run:
        return 0
    write_json(base / "state.json", state)
    if conflicts:
        write_json(base / "conflicts.json", conflicts)
    print("[gbsync] pull (tools -> bd):")
    for btype, st, detail in results:
        print(f"  {st:8} {btype:14} {detail}")
    return 2 if any(s == "FAIL" for _, s, _ in results) else 0


def main():
    args = sys.argv[1:]
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    if "--dir" in args:
        i = args.index("--dir"); project_dir = args[i + 1]; del args[i:i + 2]
    since = None
    if "--since" in args:
        i = args.index("--since"); since = args[i + 1]; del args[i:i + 2]
    dry_run = "--dry-run" in args
    if dry_run:
        args.remove("--dry-run")
    if not args:
        die("usage: gbsync.py <create|update|close> <bd_id> | pull [--since <iso>] "
            "[--dir <project_dir>] [--dry-run]")

    base = Path(project_dir) / ".cairn"
    cfg = load_json(base / "sync.json", None)
    if cfg is None:
        die(f"no {base/'sync.json'} — run /cairn:sync-config first")

    action = args[0]
    if action == "pull":
        sys.exit(do_pull(base, cfg, since, dry_run))
    elif action in PUSH_ACTIONS:
        if len(args) != 2:
            die(f"usage: gbsync.py {action} <bd_id> [--dry-run]")
        sys.exit(do_push(action, args[1], base, cfg, dry_run))
    else:
        die(f"unknown action '{action}' (use create|update|close|pull)")


if __name__ == "__main__":
    main()
