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

  IMPORT (tool -> bd)   one-shot adoption of pre-existing external items
        gbsync.py import (--query <q> | --project <KEY>) [--backend <type>]
        Pull only reconciles items already in id-map.json (populated by push),
        so it can never ADOPT work that predates the sync wiring. Import asks
        one adapter (action "import") for the external items matching a
        native query (e.g. JQL) or a project key, mints one bd issue per item
        (title/body/status), and records the bd-id<->ext-id pair in the
        id-map — after which normal push/pull cover them. Items whose
        external id is already mapped are skipped (idempotent re-runs).

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
    IMPORT stdin: {action:"import", config, query, project}
          stdout: JSON array [{external_id, title, body, status, updated_at}]
                  (same normalization as PULL; optional action — jira only today)
    exit 0 on success; nonzero => dispatcher logs and continues.

No secrets are read/written by this dispatcher. Adapters read tokens from env
vars named in their config; a missing credential is the adapter's fail-loud
error (it names the env vars), surfaced verbatim here.

Test seam: CAIRN_ADAPTERS_DIR overrides the adapters directory (house
CAIRN_* env-var seam pattern) so bats can substitute recorder/canned stubs.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ADAPTERS_DIR = Path(os.environ.get("CAIRN_ADAPTERS_DIR")
                    or Path(__file__).resolve().parent.parent / "adapters")
PUSH_ACTIONS = {"create", "update", "close"}
VALID_STATUS = {"open", "in_progress", "closed"}
USAGE = ("usage: gbsync.py <create|update|close> <bd_id> | pull "
         "[--since <iso>] | import (--query <q> | --project <KEY>) "
         "[--backend <type>] [--dir <project_dir>] [--dry-run]")
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


def bd_create(title, body, status):
    """Mint a bd issue from an imported external item.

    The title is EXTERNAL input (a Jira summary), so it goes through
    'bd create --title <title>' and never the positional argument: a card
    titled '--help' (or any '-'-leading string) parsed as a flag makes bd
    exit 0 printing its help, which the old code then stored as the bd id
    in id-map.json — marking the card imported forever while no issue was
    ever created. The returned id is validated as a single whitespace-free
    token for the same reason.

    Returns (bd_id, err). bd_id may be set even when err is — the issue was
    created but the follow-up status update failed; callers should still map
    it so a re-run does not duplicate.
    """
    try:
        bd_id = subprocess.run(["bd", "create", "--title", title,
                                "--body-file", "-", "--silent"],
                               input=body or "", text=True,
                               capture_output=True, check=True).stdout.strip()
    except FileNotFoundError:
        die("'bd' not found on PATH")
    except subprocess.CalledProcessError as e:
        return None, e.stderr.strip() or f"exit {e.returncode}"
    if not bd_id:
        return None, "bd create returned no id"
    if len(bd_id.splitlines()) != 1 or any(c.isspace() for c in bd_id):
        return None, ("bd create returned an unparseable id: "
                      f"{bd_id.splitlines()[0][:60]!r}")
    if status in VALID_STATUS and status != "open":
        try:
            subprocess.run(["bd", "update", bd_id, "--status", status],
                           capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            return bd_id, (f"created {bd_id} but status update failed: "
                           f"{e.stderr.strip() or e.returncode}")
    return bd_id, None


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


# --------------------------------------------------------------------------- #
# IMPORT:  tool -> bd  (adopt pre-existing external items, seed the id-map)
# --------------------------------------------------------------------------- #
def do_import(base, cfg, query, project, backend_type, dry_run=False):
    backends = enabled_backends(cfg)
    if backend_type:
        backends = [b for b in backends if b.get("type") == backend_type]
        if not backends:
            die(f"backend '{backend_type}' is not enabled in sync.json")
    if not backends:
        die("no enabled backends — run /cairn:sync-config first")
    if len(backends) > 1:
        die("multiple enabled backends — pick one with --backend <type>")
    b = backends[0]
    btype = b.get("type", "?")
    adapter = resolve_adapter(b.get("adapter", btype))
    if not adapter:
        die(f"adapter '{b.get('adapter', btype)}' not found")
    scope = f'query "{query}"' if query else f"project {project}"
    if dry_run:
        # Same contract as push/pull: dry-run never invokes the adapter and
        # writes nothing, so we cannot know the item list — describe the call.
        print(f"DRY-RUN: {btype} import {scope} -> bd create + id-map entries")
        return 0
    out, err = run_adapter(adapter, {"action": "import",
                                     "config": b.get("config", {}),
                                     "query": query, "project": project})
    if err:
        die(f"{btype} import failed: {err}", 2)
    try:
        items = json.loads(out) if out else []
    except json.JSONDecodeError as e:
        die(f"{btype} import: bad adapter JSON: {e}", 2)

    idmap = load_json(base / "id-map.json", {})
    mapped = {m[btype] for m in idmap.values() if m.get(btype)}
    created = skipped = failed = 0
    lines = []
    for it in items:
        ext = str(it.get("external_id") or "").strip()
        if not ext:
            failed += 1
            lines.append(("FAIL", "item without external_id — skipped"))
            continue
        if ext in mapped:
            skipped += 1
            lines.append(("skip", f"{ext} already mapped"))
            continue
        title = (it.get("title") or "").strip() or ext
        bd_id, cerr = bd_create(title, it.get("body", ""),
                                it.get("status", "open"))
        if bd_id:
            idmap.setdefault(bd_id, {})[btype] = ext
            mapped.add(ext)
        if cerr:
            failed += 1
            lines.append(("FAIL", f"{ext}: {cerr}"))
        else:
            created += 1
            lines.append(("ok", f"{ext} -> {bd_id}"))
    write_json(base / "id-map.json", idmap)
    print(f"[gbsync] import {btype} ({scope}): "
          f"created={created} skipped={skipped} failed={failed}")
    for state, detail in lines:
        print(f"  {state:8} {detail}")
    return 2 if failed else 0


def take_flag(args, flag, default=None):
    """Pop '<flag> <value>' out of args and return the value.

    A value-taking flag given as the LAST argument is a usage error, never
    an IndexError traceback: 'gbsync.py import --query' must print how to
    call it, like every other bad invocation here.
    """
    if flag not in args:
        return default
    i = args.index(flag)
    if i + 1 >= len(args):
        die(f"{flag} needs a value\n{USAGE}")
    value = args[i + 1]
    del args[i:i + 2]
    return value


def main():
    args = sys.argv[1:]
    project_dir = take_flag(args, "--dir",
                            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    since = take_flag(args, "--since")
    query = take_flag(args, "--query")
    project_key = take_flag(args, "--project")
    backend = take_flag(args, "--backend")
    dry_run = "--dry-run" in args
    if dry_run:
        args.remove("--dry-run")
    if not args:
        die(USAGE)

    base = Path(project_dir) / ".cairn"
    cfg = load_json(base / "sync.json", None)
    if cfg is None:
        die(f"no {base/'sync.json'} — run /cairn:sync-config first")

    action = args[0]
    if action == "pull":
        sys.exit(do_pull(base, cfg, since, dry_run))
    elif action == "import":
        if len(args) != 1:
            die("usage: gbsync.py import (--query <q> | --project <KEY>) "
                "[--backend <type>] [--dry-run]")
        if bool(query) == bool(project_key):
            die("import needs exactly one of --query <q> or --project <KEY>")
        sys.exit(do_import(base, cfg, query, project_key, backend, dry_run))
    elif action in PUSH_ACTIONS:
        if len(args) != 2:
            die(f"usage: gbsync.py {action} <bd_id> [--dry-run]")
        sys.exit(do_push(action, args[1], base, cfg, dry_run))
    else:
        die(f"unknown action '{action}' (use create|update|close|pull|import)")


if __name__ == "__main__":
    main()
