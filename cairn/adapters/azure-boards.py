#!/usr/bin/env python3
"""Azure DevOps Boards adapter for cairn (Work Items REST, stdlib only).

config (sync.json):
{
  "org_url": "https://dev.azure.com/yourorg",   # required
  "project": "ChainVote",                        # required
  "work_item_type": "Issue",                     # optional (Issue|Task|User Story|Bug)
  "pat_env": "AZURE_DEVOPS_PAT",                 # env var holding a PAT (Boards read/write)
  "api_version": "7.0",                           # optional
  "states": { "in_progress": "Active", "closed": "Closed" }
}

Auth: HTTP Basic with an empty username and a Personal Access Token as the
password. Create a PAT at https://dev.azure.com/<org>/_usersSettings/tokens with
"Work Items (Read & Write)". State NAMES depend on the project's process
template (Basic: To Do/Doing/Done; Agile: New/Active/Resolved/Closed) — set the
`states` map accordingly. Pull normalizes via the State Category when available,
falling back to the `states` map.

Every request carries an explicit TIMEOUT (30s) and every transport failure
(HTTP status, DNS/refused, timeout, non-JSON body) exits 1 with a one-line
reason on stderr — never a traceback, and never a hang.
"""
import base64
import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

# Seconds per request; a hung socket must not hang gbsync forever. Test seam
# (house CAIRN_* env-var pattern): CAIRN_AZURE_TIMEOUT shortens it so a bats
# test can prove the hang is bounded without waiting 30s.
try:
    TIMEOUT = float(os.environ.get("CAIRN_AZURE_TIMEOUT") or 30)
except ValueError:
    TIMEOUT = 30


def auth(cfg):
    pat = os.environ.get(cfg.get("pat_env", "AZURE_DEVOPS_PAT"), "")
    if not pat:
        print(f"azure-boards adapter: missing PAT env var "
              f"({cfg.get('pat_env','AZURE_DEVOPS_PAT')})", file=sys.stderr)
        sys.exit(1)
    return "Basic " + base64.b64encode((":" + pat).encode()).decode()


def api(cfg, method, path, body=None, content_type="application/json"):
    url = cfg["org_url"].rstrip("/") + path
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}api-version={cfg.get('api_version', '7.0')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", auth(cfg))
    req.add_header("Content-Type", content_type)
    req.add_header("Accept", "application/json")
    # Every failure mode exits 1 with a one-line reason (the adapter
    # contract's fail-loud): a bare traceback here would surface as garbage on
    # the dispatcher's stderr, and no timeout at all hangs gbsync — and the
    # prose command that called it — forever on a dead socket.
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print(f"azure {method} {path} -> {e.code}: {e.read().decode()[:300]}",
              file=sys.stderr)
        sys.exit(1)
    except (socket.timeout, TimeoutError):
        print(f"azure {method} {path} -> timed out after {TIMEOUT:g}s",
              file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        reason = e.reason
        detail = (f"timed out after {TIMEOUT:g}s"
                  if isinstance(reason, (socket.timeout, TimeoutError))
                  else reason)
        print(f"azure {method} {path} -> connection failed: {detail}",
              file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"azure {method} {path} -> response is not JSON: {e}",
              file=sys.stderr)
        sys.exit(1)


def patch_ops(event, cfg, include_state=True):
    ops = [
        {"op": "add", "path": "/fields/System.Title", "value": event["title"]},
        {"op": "add", "path": "/fields/System.Description", "value": event["body"] or ""},
    ]
    if include_state:
        states = cfg.get("states", {})
        if event["status"] == "in_progress" and states.get("in_progress"):
            ops.append({"op": "add", "path": "/fields/System.State",
                        "value": states["in_progress"]})
        elif event["status"] == "closed" and states.get("closed"):
            ops.append({"op": "add", "path": "/fields/System.State",
                        "value": states["closed"]})
    return ops


def push(event, cfg):
    ext = event.get("external_id")
    action = event["action"]
    proj = urllib.parse.quote(cfg["project"])
    ct = "application/json-patch+json"
    if action == "create" or (action == "update" and not ext):
        wtype = urllib.parse.quote("$" + cfg.get("work_item_type", "Issue"))
        d = api(cfg, "POST", f"/{proj}/_apis/wit/workitems/{wtype}",
                patch_ops(event, cfg), content_type=ct)
        return str(d.get("id", ""))
    if action == "update":
        api(cfg, "PATCH", f"/{proj}/_apis/wit/workitems/{ext}",
            patch_ops(event, cfg), content_type=ct)
        return ext
    if action == "close":
        if ext:
            close_state = cfg.get("states", {}).get("closed", "Closed")
            api(cfg, "PATCH", f"/{proj}/_apis/wit/workitems/{ext}",
                [{"op": "add", "path": "/fields/System.State", "value": close_state}],
                content_type=ct)
        return ext or ""
    print(f"unknown action {action}", file=sys.stderr)
    sys.exit(1)


def normalize_state(cfg, state, category):
    if category:
        c = category.lower()
        if c in ("completed", "removed"):
            return "closed"
        if c in ("inprogress", "resolved"):
            return "in_progress"
        if c == "proposed":
            return "open"
    states = cfg.get("states", {})
    if state == states.get("closed"):
        return "closed"
    if state == states.get("in_progress"):
        return "in_progress"
    return "open"


def pull(cfg, items):
    proj = urllib.parse.quote(cfg["project"])
    out = []
    for it in items:
        ext = it.get("external_id")
        if not ext:
            continue
        try:
            d = api(cfg, "GET", f"/{proj}/_apis/wit/workitems/{ext}")
        except SystemExit:
            continue
        f = d.get("fields", {})
        out.append({
            "bd_id": it["bd_id"], "external_id": str(d.get("id", ext)),
            "title": f.get("System.Title", ""),
            "body": f.get("System.Description", "") or "",
            "status": normalize_state(cfg, f.get("System.State"),
                                      f.get("System.StateCategory")),
            "updated_at": f.get("System.ChangedDate"),
        })
    return out


def main():
    event = json.load(sys.stdin)
    cfg = event.get("config", {})
    for req in ("org_url", "project"):
        if req not in cfg:
            print(f"azure-boards adapter: config.{req} is required", file=sys.stderr)
            sys.exit(1)
    if event["action"] == "pull":
        print(json.dumps(pull(cfg, event.get("items", []))))
    else:
        print(push(event, cfg))


if __name__ == "__main__":
    main()
