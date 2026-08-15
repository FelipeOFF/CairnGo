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

Every `gh` invocation carries an explicit TIMEOUT (30s) and every transport
failure (the CLI missing, the CLI hanging on a dead forge, a non-JSON answer)
exits 1 with a one-line reason on stderr — never a traceback, and never a
hang. `gh` reaches the network on our behalf, so an unbounded call here is an
unbounded network call: it hangs gbsync and the prose command that called it.
"""
import json
import os
import subprocess
import sys

# Seconds per `gh` invocation. Test seam (house CAIRN_* env-var pattern):
# CAIRN_GITHUB_TIMEOUT shortens it so a bats test can prove the hang is
# bounded without waiting 30s.
try:
    TIMEOUT = float(os.environ.get("CAIRN_GITHUB_TIMEOUT") or 30)
except ValueError:
    TIMEOUT = 30


def gh(args, check=True, want_json=False):
    # `check` governs only the CLI's exit code — a transport failure exits
    # regardless, because "gh never came back" is not an answer any caller can
    # treat as "no such issue".
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True,
                           timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f"github gh {' '.join(args[:2])} -> timed out after "
              f"{TIMEOUT:g}s", file=sys.stderr)
        sys.exit(1)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"github: could not run gh: {e}", file=sys.stderr)
        sys.exit(1)
    if check and p.returncode != 0:
        print(p.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    if not (want_json and p.stdout.strip()):
        return p.stdout.strip()
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as e:
        print(f"github gh {' '.join(args[:2])} -> response is not JSON: {e}",
              file=sys.stderr)
        sys.exit(1)


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
