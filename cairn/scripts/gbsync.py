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
USAGE = ("usage: gbsync.py <create|update|close> <bd_id> | comment <bd_id> "
         "--text <t> | pull "
         "[--since <iso>] | import (--query <q> | --project <KEY>) "
         "[--backend <type>] | refresh-map [--dir <project_dir>] [--dry-run]")
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def die(msg, code=1):
    print(f"[gbsync] error: {msg}", file=sys.stderr)
    sys.exit(code)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s, default=EPOCH):
    if not s:
        return default
    s = str(s).strip().replace("Z", "+00:00")
    # Normalize a trailing numeric offset without a colon (e.g. +0000 -> +00:00),
    # which older datetime.fromisoformat rejects. Jira returns this form.
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return default


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
# external_ref prefix -> backend type, as cairn's own writers spell them.
REF_BACKENDS = {"jira": "jira", "gh": "github", "github": "github",
                "gl": "gitlab", "gitlab": "gitlab", "linear": "linear"}
# ...and the prefix a backend's key is written with, when this dispatcher
# is the one writing it (a card it just created for a carrier).
REF_PREFIX = {"jira": "jira", "github": "gh", "gitlab": "gl", "linear": "linear"}


def source():
    """cairn_source, imported on first use — still used to invalidate the
    issue cache after a write. Classification itself is v5 cairn.kind."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cairn_source
    return cairn_source


def hierarchical(backend):
    """A backend with `"model": "hierarchy"` mirrors specs and tickets
    (v5 spoke map). Flat backends keep the one-type-for-everything mirror."""
    return backend.get("model") == "hierarchy"


def _parse_json(stdout):
    out = (stdout or "").strip()
    starts = [i for i in (out.find("["), out.find("{")) if i >= 0]
    if not starts:
        return []
    data = json.loads(out[min(starts):])
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def _bd_show(root, bd_id):
    try:
        out = subprocess.run(
            ["bd", "-C", str(root), "show", bd_id, "--json"],
            capture_output=True, text=True, check=True).stdout
        rows = _parse_json(out)
        return rows[0] if rows else None
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        return None


def cairn_kind(issue):
    meta = issue.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            meta = {}
    cairn = (meta or {}).get("cairn") if isinstance(meta, dict) else {}
    kind = (cairn or {}).get("kind")
    if kind:
        return kind
    t = str(issue.get("issue_type") or issue.get("type") or "").lower()
    if t == "epic":
        return "spec"
    return None


def parent_bd_id(issue):
    p = issue.get("parent")
    if isinstance(p, dict):
        p = p.get("id")
    if p:
        return str(p)
    iid = str(issue.get("id") or "")
    if "." in iid:
        return iid.rsplit(".", 1)[0]
    return None


def ref_for(issue, btype):
    ref = str(issue.get("external_ref") or "")
    prefix, _, key = ref.partition("-")
    if key and REF_BACKENDS.get(prefix) == btype:
        return key
    return None


def fix_versions(issue):
    out = []
    for lab in issue.get("labels") or []:
        lab = str(lab)
        if lab.startswith("m-") and len(lab) > 2:
            out.append(lab[2:])
    return out


def _blocker_id_from_dep_row(row, bd_id):
    """Id of the bead that blocks `bd_id`, from a dep-list or show JSON row.

    bd 1.1.0 hydrates `bd dep list --json` as the blocker issue (`id` +
    `dependency_type`). Storage/edge shape uses `depends_on_id`. Parent-child
    must not count: on 1.2.2 `bd show` puts the spec parent in
    `dependencies` and leaves `blocked_by` empty, so `x or y` would pick the
    Epic key (CI 33815460444).
    """
    if row is None:
        return None
    if not isinstance(row, dict):
        val = str(row)
        return val if val and val != str(bd_id) else None
    dtype = str(row.get("dependency_type") or row.get("type") or "")
    if dtype in ("parent-child", "parent", "child", "discovered-from",
                 "related", "relates_to", "tracks"):
        return None
    if row.get("depends_on_id"):
        return str(row["depends_on_id"])
    rid = row.get("id")
    if rid and str(rid) != str(bd_id):
        return str(rid)
    return None


def blocker_keys(root, issue, btype, idmap):
    """Spoke keys of beads that block this one (`bd dep` → Jira Blocks)."""
    bd_id = str(issue.get("id") or "")
    ids = []
    try:
        proc = subprocess.run(
            ["bd", "-C", str(root), "dep", "list", bd_id,
             "--type", "blocks", "--json"],
            capture_output=True, text=True)
        if proc.returncode == 0:
            for row in _parse_json(proc.stdout):
                bid = _blocker_id_from_dep_row(row, bd_id)
                if bid and bid not in ids:
                    ids.append(bid)
    except (FileNotFoundError, ValueError):
        pass
    if not ids:
        parent = parent_bd_id(issue)
        for key in ("blocked_by", "depends_on", "dependencies"):
            raw = issue.get(key)
            if raw is None:
                continue
            if not isinstance(raw, list):
                raw = [raw]
            for item in raw:
                bid = _blocker_id_from_dep_row(item, bd_id)
                if bid and bid != parent and bid not in ids:
                    ids.append(bid)
    keys = []
    for dep_id in ids:
        mapped = (idmap.get(dep_id) or {}).get(btype)
        if mapped:
            keys.append(mapped)
            continue
        other = _bd_show(root, dep_id)
        if other is not None:
            ref = ref_for(other, btype)
            if ref:
                keys.append(ref)
    return keys


def classify(root, bd_id, btype):
    """(level, parent_key, issue) for a hierarchy push.

    spec → level 'spec', no parent. ticket → level 'ticket', parent = the
    spec's spoke key for this backend. Anything else is skipped."""
    issue = _bd_show(root, bd_id)
    if issue is None:
        return None, None, None
    kind = cairn_kind(issue)
    if kind == "spec":
        return "spec", None, issue
    if kind == "ticket":
        parent_key = None
        pid = parent_bd_id(issue)
        if pid:
            parent = _bd_show(root, pid)
            if parent is not None:
                parent_key = ref_for(parent, btype)
        return "ticket", parent_key, issue
    return None, None, issue


def credentials_missing(cfg):
    """The env var NAMES a backend declares (email_env / token_env /
    pat_env) that are not set in this shell — the reason a hierarchy write
    is queued on the bead instead of attempted (phase 45, D-02/C-04). A
    backend that declares none is assumed reachable."""
    names = [cfg.get(k) for k in ("email_env", "token_env", "pat_env")
             if cfg.get(k)]
    return [n for n in names if not os.environ.get(n)]


def enqueue_pending(root, bd_id, btype, action, extra=None):
    """Append one write to metadata.gsd.mirror.pending on the bead, by
    read-modify-write (bd replaces a provided top-level key wholesale). The
    queue is what /cairn:jira flush applies in a session, and what the
    doctor shows meanwhile."""
    try:
        out = subprocess.run(["bd", "-C", str(root), "show", bd_id, "--json"],
                             capture_output=True, text=True, check=True).stdout
        data = json.loads(out or "[]")
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return False
    issue = data[0] if isinstance(data, list) else data
    meta = issue.get("metadata") if isinstance(issue.get("metadata"), dict) else {}
    gsd = meta.get("gsd") if isinstance(meta.get("gsd"), dict) else {}
    mirror = gsd.get("mirror") if isinstance(gsd.get("mirror"), dict) else {}
    pending = mirror.get("pending") if isinstance(mirror.get("pending"), list) else []
    entry = {"backend": btype, "action": action, "at": now_iso()}
    entry.update(extra or {})
    pending.append(entry)
    mirror["pending"] = pending
    gsd["mirror"] = mirror
    meta["gsd"] = gsd
    proc = subprocess.run(["bd", "-C", str(root), "update", bd_id,
                           "--metadata", json.dumps(meta)],
                          capture_output=True, text=True)
    source().invalidate(root)
    return proc.returncode == 0


def record_ref(root, bd_id, btype, ext):
    """A card this dispatcher just created is a link, and the link lives in
    the bead: write external_ref <prefix>-<key> when the bead has none."""
    prefix = REF_PREFIX.get(btype)
    if not prefix:
        return
    subprocess.run(["bd", "-C", str(root), "update", bd_id,
                    "--external-ref", f"{prefix}-{ext}"],
                   capture_output=True, text=True)
    source().invalidate(root)


def derive_idmap(idmap, cfg):
    """Fold bd's own `external_ref` into the id-map (phase 44 / LINK-02).

    The link lives in the bead — `jira-DTP-142` on a carrier — and travels
    with Dolt; the id-map is a per-machine cache that used to be the only
    record and is now DERIVED: for every issue whose external_ref prefix
    names an enabled backend, entry[backend] = key, and the bead wins over
    whatever the file said. Called on every push and pull, and by
    `refresh-map` on its own. One bd list, never one per issue."""
    wanted = {b.get("type") for b in enabled_backends(cfg)}
    try:
        out = subprocess.run(["bd", "list", "--all", "--limit", "0", "--json"],
                             capture_output=True, text=True, check=True).stdout
        issues = json.loads(out or "[]")
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        return idmap, 0
    if not isinstance(issues, list):
        issues = issues.get("issues", []) if isinstance(issues, dict) else []
    changed = 0
    for issue in issues:
        ref = str(issue.get("external_ref") or "").strip()
        prefix, _, key = ref.partition("-")
        btype = REF_BACKENDS.get(prefix)
        if not key or btype not in wanted:
            continue
        entry = idmap.setdefault(issue.get("id"), {})
        if entry.get(btype) != key:
            entry[btype] = key
            changed += 1
    return idmap, changed


def do_refresh_map(base, cfg, dry_run=False):
    idmap = load_json(base / "id-map.json", {})
    before = json.dumps(idmap, sort_keys=True)
    idmap, changed = derive_idmap(idmap, cfg)
    if dry_run:
        print(f"DRY-RUN: refresh-map would rewrite {changed} entr"
              f"{'y' if changed == 1 else 'ies'} from external_ref")
        return 0
    if json.dumps(idmap, sort_keys=True) != before:
        write_json(base / "id-map.json", idmap)
    print(f"[gbsync] refresh-map: {changed} entr{'y' if changed == 1 else 'ies'} "
          f"derived from external_ref ({len(idmap)} bd id(s) mapped)")
    return 0


def do_push(action, bd_id, base, cfg, dry_run=False, text=None):
    backends = enabled_backends(cfg)
    if not backends:
        print("[gbsync] no enabled backends — nothing to mirror")
        return 0
    issue = bd_fetch(bd_id)
    idmap, _ = derive_idmap(load_json(base / "id-map.json", {}), cfg)
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
            if hierarchical(b):
                level, parent, raw = classify(base.parent, bd_id, btype)
                if level is None:
                    print(f"DRY-RUN: {btype} skip {bd_id} (not a spec or ticket)")
                    continue
                queued = " (queued: no credentials)" \
                    if credentials_missing(b.get("config", {})) else ""
                fv = ",".join(fix_versions(raw or {}))
                extra = f", fix {fv}" if fv else ""
                print(f"DRY-RUN: {btype} {action} {bd_id} -> {ext or '(new)'} "
                      f"[{level}, parent {parent or '(none)'}{extra}]{queued}")
                continue
            if action == "comment":
                print(f"DRY-RUN: {btype} skip {bd_id} (comment needs the "
                      "hierarchy model)")
                continue
            print(f"DRY-RUN: {btype} {action} {bd_id} -> {ext or '(new)'}")
        return 0
    results = []
    root = base.parent
    for b in backends:
        btype = b.get("type", "?")
        adapter = resolve_adapter(b.get("adapter", btype))
        if not adapter:
            results.append((btype, "skip", f"adapter '{b.get('adapter', btype)}' not found"))
            continue
        if action == "comment" and not hierarchical(b):
            results.append((btype, "skip", "comment needs the hierarchy model"))
            continue
        event = {
            "action": action, "bd_id": issue["bd_id"], "title": issue["title"],
            "body": issue["body"], "status": issue["status"],
            "labels": issue["labels"], "external_id": entry.get(btype),
            "config": b.get("config", {}),
        }
        if hierarchical(b):
            level, parent, raw = classify(root, bd_id, btype)
            if level is None:
                results.append((btype, "skip", "not a spec or ticket"))
                continue
            if level == "ticket" and not parent and not entry.get(btype):
                results.append((btype, "FAIL", "ticket with no parent: "
                                "link the spec first"))
                continue
            event.update({"level": level, "parent": parent,
                          "external_key": entry.get(btype),
                          "fix_versions": fix_versions(raw or {}),
                          "blocked_by": blocker_keys(
                              root, raw or {}, btype, idmap)})
            if action == "comment" and not entry.get(btype):
                results.append((btype, "skip", "not linked — nothing to "
                                "comment on"))
                continue
            missing = credentials_missing(b.get("config", {}))
            if missing:
                # No road to the tracker: queue, never fail, never forget.
                extra = {"key": entry.get(btype)}
                if text is not None:
                    extra["text"] = text
                ok = enqueue_pending(root, bd_id, btype, action, extra)
                results.append((btype, "queued" if ok else "FAIL",
                                f"{action} queued on the bead (no "
                                f"{'/'.join(missing)} in the shell) — "
                                "/cairn:jira flush applies it"
                                if ok else "could not queue on the bead"))
                continue
            if text is not None:
                event["text"] = text
        ext, err = run_adapter(adapter, event)
        if err:
            results.append((btype, "FAIL", err))
            continue
        if ext:
            if hierarchical(b) and not entry.get(btype):
                record_ref(root, bd_id, btype, ext)
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
    idmap, _ = derive_idmap(load_json(base / "id-map.json", {}), cfg)
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
        if hierarchical(b):
            # Read only (phase 45 / MIRROR-04): the tracker's status is
            # RECORDED under state.json.seen and the doctor names the
            # divergence; nothing here closes, reopens or rewrites a bead,
            # and nothing is a conflict — the bead is the source.
            if dry_run:
                for it in items:
                    print(f"DRY-RUN: {btype} pull {it['bd_id']} "
                          f"<- {it['external_id']} (read only: seen)")
                continue
            missing = credentials_missing(b.get("config", {}))
            if missing:
                results.append((btype, "skip", f"no {'/'.join(missing)} in "
                                "the shell — in a session, /cairn-sync-pull "
                                "reads through the MCP and records with "
                                "cairn-jira.py seen"))
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
            seen = state.setdefault("seen", {}).setdefault(btype, {})
            for ext in ext_states:
                key = ext.get("external_id")
                if not key:
                    continue
                seen[key] = {"bd_id": ext.get("bd_id"),
                             "status": ext.get("status"),
                             "title": ext.get("title"),
                             "updated_at": ext.get("updated_at"),
                             "at": started}
            last_pull[btype] = started
            results.append((btype, "ok", f"seen={len(ext_states)} (read only; "
                            "the doctor names any divergence)"))
            continue
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
        die("no enabled backends — run /cairn-sync-config first")
    if len(backends) > 1:
        die("multiple enabled backends — pick one with --backend <type>")
    b = backends[0]
    btype = b.get("type", "?")
    if hierarchical(b):
        die(f"{btype} runs the hierarchy model: a card does not become a bead, "
            "it LINKS to an existing spec/ticket — set external_ref on the "
            "bead (jira-<KEY>) or /cairn-implement the spoke key", 2)
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
    try:
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
                # Persisted per item, not once at the end. An import that
                # died halfway used to leave every issue it had just created
                # unmapped, so the re-run the user was told was safe created
                # all of them a second time. The map is small and the write
                # is cheap next to a bd create; correctness wins here.
                write_json(base / "id-map.json", idmap)
            if cerr:
                failed += 1
                lines.append(("FAIL", f"{ext}: {cerr}"))
            else:
                created += 1
                lines.append(("ok", f"{ext} -> {bd_id}"))
    finally:
        # Also on the way out of an interrupt or an unexpected error: what
        # was created stays mapped, so nothing is orphaned.
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
    call it, like every other bad invocation here. A next token that itself
    starts with '--' is the same class of error: `pull --since --dry-run`
    must not swallow --dry-run as a timestamp.
    """
    if flag not in args:
        return default
    i = args.index(flag)
    if i + 1 >= len(args):
        die(f"{flag} needs a value\n{USAGE}")
    value = args[i + 1]
    if value.startswith("--"):
        die(f"{flag} needs a value, got the flag {value!r}\n{USAGE}")
    del args[i:i + 2]
    return value


def main():
    args = sys.argv[1:]
    project_dir = take_flag(args, "--dir",
                            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    since = take_flag(args, "--since")
    query = take_flag(args, "--query")
    project_key = take_flag(args, "--project")
    text = take_flag(args, "--text")
    backend = take_flag(args, "--backend")
    dry_run = "--dry-run" in args
    if dry_run:
        args.remove("--dry-run")
    if not args:
        die(USAGE)
    if since and parse_ts(since, default=None) is None:
        die(f"--since needs an ISO8601 timestamp, got {since!r}\n{USAGE}")

    base = Path(project_dir) / ".cairn"
    cfg = load_json(base / "sync.json", None)
    if cfg is None:
        die(f"no {base/'sync.json'} — run /cairn-sync-config first")

    action = args[0]
    if action == "refresh-map":
        if len(args) != 1:
            die("usage: gbsync.py refresh-map [--dry-run]")
        sys.exit(do_refresh_map(base, cfg, dry_run))
    if action == "pull":
        if len(args) != 1:
            die("usage: gbsync.py pull [--since <iso>] [--dry-run]")
        sys.exit(do_pull(base, cfg, since, dry_run))
    elif action == "import":
        if len(args) != 1:
            die("usage: gbsync.py import (--query <q> | --project <KEY>) "
                "[--backend <type>] [--dry-run]")
        if bool(query) == bool(project_key):
            die("import needs exactly one of --query <q> or --project <KEY>")
        sys.exit(do_import(base, cfg, query, project_key, backend, dry_run))
    elif action == "comment":
        if len(args) != 2 or not (text or "").strip():
            die("usage: gbsync.py comment <bd_id> --text <text> [--dry-run]")
        sys.exit(do_push("comment", args[1], base, cfg, dry_run, text=text))
    elif action in PUSH_ACTIONS:
        if len(args) != 2:
            die(f"usage: gbsync.py {action} <bd_id> [--dry-run]")
        sys.exit(do_push(action, args[1], base, cfg, dry_run))
    else:
        die(f"unknown action '{action}' (use create|update|close|comment|pull|import|refresh-map)")


if __name__ == "__main__":
    main()
