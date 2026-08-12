#!/usr/bin/env python3
"""GitHub adapter for cairn (uses the `gh` CLI — reuses its auth).

config (sync.json):
{
  "repo": "owner/name",          # required
  "extra_labels": []             # optional, added to every mirrored issue
}

GitHub Issues have only open/closed natively, so push maps in_progress->open
(issue stays open) and pull maps OPEN->open, CLOSED->closed. (Project-board
"In progress" mirroring is intentionally out of scope here; do it in a
project-specific CLAUDE.md if needed.)

Requires: `gh` authenticated (`gh auth status`).
"""
import json
import subprocess
import sys


def gh(args, check=True, want_json=False):
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        print(p.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return json.loads(p.stdout) if want_json and p.stdout.strip() else p.stdout.strip()


def labels_for(event, cfg):
    return list(dict.fromkeys(event.get("labels", []) + cfg.get("extra_labels", [])))


def push(event, cfg):
    repo = cfg["repo"]
    ext = event.get("external_id")
    action = event["action"]
    if action == "create" or (action == "update" and not ext):
        args = ["issue", "create", "--repo", repo,
                "--title", event["title"], "--body", event["body"] or ""]
        for lb in labels_for(event, cfg):
            args += ["--label", lb]
        url = gh(args)                       # prints the new issue URL
        return url.rstrip("/").split("/")[-1]
    if action == "update":
        args = ["issue", "edit", ext, "--repo", repo,
                "--title", event["title"], "--body", event["body"] or ""]
        for lb in labels_for(event, cfg):
            args += ["--add-label", lb]
        gh(args)
        if event["status"] == "closed":
            gh(["issue", "close", ext, "--repo", repo, "--reason", "completed"], check=False)
        return ext
    if action == "close":
        if ext:
            gh(["issue", "close", ext, "--repo", repo, "--reason", "completed"], check=False)
        return ext or ""
    print(f"unknown action {action}", file=sys.stderr)
    sys.exit(1)


def pull(cfg, items):
    repo = cfg["repo"]
    out = []
    for it in items:
        ext = it.get("external_id")
        if not ext:
            continue
        data = gh(["issue", "view", ext, "--repo", repo,
                   "--json", "number,title,body,state,updatedAt"],
                  check=False, want_json=True)
        if not data:
            continue
        status = "closed" if str(data.get("state", "")).upper() == "CLOSED" else "open"
        out.append({
            "bd_id": it["bd_id"], "external_id": str(data.get("number", ext)),
            "title": data.get("title", ""), "body": data.get("body", "") or "",
            "status": status, "updated_at": data.get("updatedAt"),
        })
    return out


def main():
    event = json.load(sys.stdin)
    cfg = event.get("config", {})
    if "repo" not in cfg:
        print("github adapter: config.repo is required", file=sys.stderr)
        sys.exit(1)
    if event["action"] == "pull":
        print(json.dumps(pull(cfg, event.get("items", []))))
    else:
        print(push(event, cfg))


if __name__ == "__main__":
    main()
