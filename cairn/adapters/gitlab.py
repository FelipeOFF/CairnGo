#!/usr/bin/env python3
"""GitLab adapter for cairn (REST v4, stdlib only).

config (sync.json):
{
  "base_url": "https://gitlab.com",   # optional (default gitlab.com; set for self-hosted)
  "project": "namespace/project",     # required — numeric id OR URL path
  "token_env": "GITLAB_TOKEN",        # env var holding a Personal/Project Access Token
  "extra_labels": []                  # optional, added to every mirrored issue
}

Auth: PRIVATE-TOKEN header with a token that has `api` scope. Create one at
https://gitlab.com/-/user_settings/personal_access_tokens (or a Project Access
Token). GitLab issues are open/closed natively, so push maps in_progress->open
and pull maps opened->open / closed->closed. The external id stored is the
issue `iid` (project-internal number).
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def token(cfg):
    t = os.environ.get(cfg.get("token_env", "GITLAB_TOKEN"), "")
    if not t:
        print(f"gitlab adapter: missing token env var "
              f"({cfg.get('token_env','GITLAB_TOKEN')})", file=sys.stderr)
        sys.exit(1)
    return t


def pid(cfg):
    return urllib.parse.quote(str(cfg["project"]), safe="")


def api(cfg, method, path, params=None):
    base = cfg.get("base_url", "https://gitlab.com").rstrip("/")
    url = f"{base}/api/v4{path}"
    data = urllib.parse.urlencode(params, doseq=True).encode() if params else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("PRIVATE-TOKEN", token(cfg))
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print(f"gitlab {method} {path} -> {e.code}: {e.read().decode()[:300]}",
              file=sys.stderr)
        sys.exit(1)


def labels_for(event, cfg):
    return ",".join(dict.fromkeys(event.get("labels", []) + cfg.get("extra_labels", [])))


def push(event, cfg):
    ext = event.get("external_id")
    action = event["action"]
    p = pid(cfg)
    if action == "create" or (action == "update" and not ext):
        params = {"title": event["title"], "description": event["body"] or "",
                  "labels": labels_for(event, cfg)}
        d = api(cfg, "POST", f"/projects/{p}/issues", params)
        iid = str(d.get("iid", ""))
        if event["status"] == "closed" and iid:
            api(cfg, "PUT", f"/projects/{p}/issues/{iid}", {"state_event": "close"})
        return iid
    if action == "update":
        params = {"title": event["title"], "description": event["body"] or "",
                  "labels": labels_for(event, cfg)}
        if event["status"] == "closed":
            params["state_event"] = "close"
        api(cfg, "PUT", f"/projects/{p}/issues/{ext}", params)
        return ext
    if action == "close":
        if ext:
            api(cfg, "PUT", f"/projects/{p}/issues/{ext}", {"state_event": "close"})
        return ext or ""
    print(f"unknown action {action}", file=sys.stderr)
    sys.exit(1)


def pull(cfg, items):
    p = pid(cfg)
    out = []
    for it in items:
        ext = it.get("external_id")
        if not ext:
            continue
        try:
            d = api(cfg, "GET", f"/projects/{p}/issues/{ext}")
        except SystemExit:
            continue
        status = "closed" if d.get("state") == "closed" else "open"
        out.append({
            "bd_id": it["bd_id"], "external_id": str(d.get("iid", ext)),
            "title": d.get("title", ""), "body": d.get("description", "") or "",
            "status": status, "updated_at": d.get("updated_at"),
        })
    return out


def main():
    event = json.load(sys.stdin)
    cfg = event.get("config", {})
    if "project" not in cfg:
        print("gitlab adapter: config.project is required", file=sys.stderr)
        sys.exit(1)
    if event["action"] == "pull":
        print(json.dumps(pull(cfg, event.get("items", []))))
    else:
        print(push(event, cfg))


if __name__ == "__main__":
    main()
