#!/usr/bin/env python3
"""Asana adapter for cairn (REST 1.0, stdlib only).

config (sync.json):
{
  "project_gid": "1209…",        # required — tasks are created in this project
  "token_env": "ASANA_TOKEN"     # env var holding a Personal Access Token
}

Auth: Bearer Personal Access Token. Create one at
https://app.asana.com/0/my-apps and export it. Asana tasks have no native
"in progress", so push maps in_progress->open (incomplete) and pull maps
completed->closed / incomplete->open.

Every request carries an explicit TIMEOUT (30s) and every transport failure
(HTTP status, DNS/refused, timeout, non-JSON body) exits 1 with a one-line
reason on stderr — never a traceback, and never a hang.
"""
import json
import os
import socket
import sys
import urllib.error
import urllib.request

BASE = "https://app.asana.com/api/1.0"
# Seconds per request; a hung socket must not hang gbsync forever. Test seam
# (house CAIRN_* env-var pattern): CAIRN_ASANA_TIMEOUT shortens it so a bats
# test can prove the hang is bounded without waiting 30s.
try:
    TIMEOUT = float(os.environ.get("CAIRN_ASANA_TIMEOUT") or 30)
except ValueError:
    TIMEOUT = 30


def token(cfg):
    t = os.environ.get(cfg.get("token_env", "ASANA_TOKEN"), "")
    if not t:
        print(f"asana adapter: missing token env var "
              f"({cfg.get('token_env','ASANA_TOKEN')})", file=sys.stderr)
        sys.exit(1)
    return t


def api(cfg, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token(cfg))
    req.add_header("Content-Type", "application/json")
    # Every failure mode exits 1 with a one-line reason (the adapter
    # contract's fail-loud): a bare traceback here would surface as garbage on
    # the dispatcher's stderr, and no timeout at all hangs gbsync — and the
    # prose command that called it — forever on a dead socket.
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode()
            return json.loads(raw).get("data", {}) if raw else {}
    except urllib.error.HTTPError as e:
        print(f"asana {method} {path} -> {e.code}: {e.read().decode()[:300]}",
              file=sys.stderr)
        sys.exit(1)
    except (socket.timeout, TimeoutError):
        print(f"asana {method} {path} -> timed out after {TIMEOUT:g}s",
              file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        reason = e.reason
        detail = (f"timed out after {TIMEOUT:g}s"
                  if isinstance(reason, (socket.timeout, TimeoutError))
                  else reason)
        print(f"asana {method} {path} -> connection failed: {detail}",
              file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"asana {method} {path} -> response is not JSON: {e}",
              file=sys.stderr)
        sys.exit(1)


def push(event, cfg):
    ext = event.get("external_id")
    action = event["action"]
    if action == "create" or (action == "update" and not ext):
        d = api(cfg, "POST", "/tasks", {"data": {
            "name": event["title"], "notes": event["body"] or "",
            "projects": [cfg["project_gid"]],
            "completed": event["status"] == "closed",
        }})
        return str(d.get("gid", ""))
    if action == "update":
        api(cfg, "PUT", f"/tasks/{ext}", {"data": {
            "name": event["title"], "notes": event["body"] or "",
            "completed": event["status"] == "closed",
        }})
        return ext
    if action == "close":
        if ext:
            api(cfg, "PUT", f"/tasks/{ext}", {"data": {"completed": True}})
        return ext or ""
    print(f"unknown action {action}", file=sys.stderr)
    sys.exit(1)


def pull(cfg, items):
    out = []
    for it in items:
        ext = it.get("external_id")
        if not ext:
            continue
        try:
            d = api(cfg, "GET",
                    f"/tasks/{ext}?opt_fields=name,notes,completed,modified_at")
        except SystemExit:
            continue
        out.append({
            "bd_id": it["bd_id"], "external_id": str(d.get("gid", ext)),
            "title": d.get("name", ""), "body": d.get("notes", "") or "",
            "status": "closed" if d.get("completed") else "open",
            "updated_at": d.get("modified_at"),
        })
    return out


def main():
    event = json.load(sys.stdin)
    cfg = event.get("config", {})
    if event["action"] != "pull" and "project_gid" not in cfg:
        print("asana adapter: config.project_gid is required", file=sys.stderr)
        sys.exit(1)
    if event["action"] == "pull":
        print(json.dumps(pull(cfg, event.get("items", []))))
    else:
        print(push(event, cfg))


if __name__ == "__main__":
    main()
