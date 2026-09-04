#!/usr/bin/env python3
"""Jira Cloud adapter for cairn (REST v3, stdlib only).

config (sync.json):
{
  "base_url": "https://yourorg.atlassian.net",   # required
  "project_key": "CHN",                          # required
  "issue_type": "Task",                          # optional (default Task)
  "email_env": "JIRA_EMAIL",                     # env var holding the account email
  "token_env": "JIRA_API_TOKEN",                 # env var holding the API token
  "transitions": { "in_progress": "In Progress", "closed": "Done" }
}

Auth: HTTP Basic with <email>:<api_token> (Atlassian Cloud). Create a token at
https://id.atlassian.com/manage-profile/security/api-tokens and export both env
vars before syncing. Status normalization on pull uses Jira's statusCategory
(new->open, indeterminate->in_progress, done->closed), which is robust across
workflow configs.

Actions: push (create/update/close), pull, and import.

IMPORT — one-shot adoption of existing Jira cards:
  stdin : {action:"import", config, query, project}
          query   = raw JQL (wins when set)
          project = project key, validated against ^[A-Z][A-Z0-9_]{1,30}$
                    (rejected loud otherwise — it is interpolated into the
                    JQL, and arbitrary JQL belongs in --query); default is
                    'project = <key> ORDER BY created ASC'
                    (falls back to config.project_key when both are null)
  stdout: JSON array [{external_id, title, body, status, updated_at}]
          normalized exactly like pull (statusCategory mapping, ADF -> text).
Search is GET /rest/api/3/search/jql, paginated via nextPageToken in pages of
100, capped at IMPORT_MAX (200) items — refine the JQL to import a larger
backlog in slices. Auth/env-var handling identical to push/pull (fail-loud
when the env vars named in config are unset).

Every request carries an explicit TIMEOUT (30s) and every transport failure
(HTTP status, DNS/refused, timeout, non-JSON body) exits 1 with a one-line
reason on stderr — never a traceback, and never a hang.
"""
import base64
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

CAT = {"new": "open", "indeterminate": "in_progress", "done": "closed"}
IMPORT_MAX = 200      # documented ceiling per import run
PAGE_SIZE = 100
# Seconds per request; a hung socket must not hang gbsync forever. Test
# seam (house CAIRN_* env-var pattern): CAIRN_JIRA_TIMEOUT shortens it so a
# bats test can prove the hang is bounded without waiting 30s.
try:
    TIMEOUT = float(os.environ.get("CAIRN_JIRA_TIMEOUT") or 30)
except ValueError:
    TIMEOUT = 30
# Jira project keys: uppercase, digits and underscore after the first letter.
# Anything else (spaces, JQL operators) is refused rather than interpolated.
PROJECT_KEY = re.compile(r"^[A-Z][A-Z0-9_]{1,30}$")
DEFAULT_LEVEL_TYPES = {"spec": "Epic", "ticket": "Story"}


def cfg_auth(cfg):
    email = os.environ.get(cfg.get("email_env", "JIRA_EMAIL"), "")
    token = os.environ.get(cfg.get("token_env", "JIRA_API_TOKEN"), "")
    if not email or not token:
        print("jira adapter: missing email/token env vars "
              f"({cfg.get('email_env','JIRA_EMAIL')} / {cfg.get('token_env','JIRA_API_TOKEN')})",
              file=sys.stderr)
        sys.exit(1)
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()


def api(cfg, method, path, body=None):
    url = cfg["base_url"].rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", cfg_auth(cfg))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    # Every failure mode exits 1 with a one-line reason (the adapter
    # contract's fail-loud): a bare traceback here would surface as garbage
    # on the dispatcher's stderr, and no timeout at all hangs 'gbsync
    # import' (up to 3 sequential requests per run) forever on a dead socket.
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print(f"jira {method} {path} -> {e.code}: {e.read().decode()[:300]}",
              file=sys.stderr)
        sys.exit(1)
    except (socket.timeout, TimeoutError):
        print(f"jira {method} {path} -> timed out after {TIMEOUT:g}s",
              file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        reason = e.reason
        detail = (f"timed out after {TIMEOUT:g}s"
                  if isinstance(reason, (socket.timeout, TimeoutError))
                  else reason)
        print(f"jira {method} {path} -> connection failed: {detail}",
              file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"jira {method} {path} -> response is not JSON: {e}",
              file=sys.stderr)
        sys.exit(1)


def adf(text):
    return {"type": "doc", "version": 1,
            "content": [{"type": "paragraph",
                         "content": [{"type": "text", "text": text or " "}]}]}


def adf_to_text(node):
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    return "".join(adf_to_text(c) for c in node.get("content", []))


def transition(cfg, key, target_name):
    if not target_name:
        return
    ts = api(cfg, "GET", f"/rest/api/3/issue/{key}/transitions").get("transitions", [])
    for t in ts:
        if t.get("to", {}).get("name", "").lower() == target_name.lower() \
                or t.get("name", "").lower() == target_name.lower():
            api(cfg, "POST", f"/rest/api/3/issue/{key}/transitions",
                {"transition": {"id": t["id"]}})
            return


def push(event, cfg):
    ext = event.get("external_id")
    action = event["action"]
    trans = cfg.get("transitions", {})
    if action == "create" or (action == "update" and not ext):
        # v5 hierarchy: dispatcher sets level spec|ticket; cfg.issue_types
        # maps those to this site's type names. Flat model: one type.
        level = event.get("level")
        if level:
            types = dict(DEFAULT_LEVEL_TYPES)
            types.update(cfg.get("issue_types") or {})
            issuetype = types.get(level) or cfg.get("issue_type", "Task")
        else:
            issuetype = cfg.get("issue_type", "Task")
        fields = {
            "project": {"key": cfg["project_key"]},
            "summary": event["title"],
            "description": adf(event["body"]),
            "issuetype": {"name": issuetype},
        }
        if event.get("parent"):
            fields["parent"] = {"key": event["parent"]}
        versions = event.get("fix_versions") or []
        if versions:
            fields["fixVersions"] = [{"name": v} for v in versions]
        body = {"fields": fields}
        key = api(cfg, "POST", "/rest/api/3/issue", body).get("key", "")
        if event["status"] == "in_progress":
            transition(cfg, key, trans.get("in_progress"))
        for blocker in event.get("blocked_by") or []:
            if not blocker or not key:
                continue
            api(cfg, "POST", "/rest/api/3/issueLink", {
                "type": {"name": "Blocks"},
                "inwardIssue": {"key": key},
                "outwardIssue": {"key": blocker},
            })
        return key
    if action == "update":
        api(cfg, "PUT", f"/rest/api/3/issue/{ext}",
            {"fields": {"summary": event["title"], "description": adf(event["body"])}})
        if event["status"] == "in_progress":
            transition(cfg, ext, trans.get("in_progress"))
        elif event["status"] == "closed":
            transition(cfg, ext, trans.get("closed"))
        return ext
    if action == "close":
        if ext:
            transition(cfg, ext, trans.get("closed", "Done"))
        return ext or ""
    if action == "comment":
        if not ext:
            print("jira adapter: comment needs a linked card", file=sys.stderr)
            sys.exit(1)
        api(cfg, "POST", f"/rest/api/3/issue/{ext}/comment",
            {"body": adf(event.get("text") or "")})
        return ext
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
                    f"/rest/api/3/issue/{ext}?fields=summary,description,status,updated")
        except SystemExit:
            continue
        f = d.get("fields", {})
        cat = f.get("status", {}).get("statusCategory", {}).get("key", "new")
        out.append({
            "bd_id": it["bd_id"], "external_id": d.get("key", ext),
            "title": f.get("summary", ""),
            "body": adf_to_text(f.get("description")) if f.get("description") else "",
            "status": CAT.get(cat, "open"),
            "updated_at": f.get("updated"),
        })
    return out


def do_import(cfg, query, project):
    """Fetch up to IMPORT_MAX issues by JQL, normalized like pull().

    A --project key is interpolated into the JQL, so it is validated
    against PROJECT_KEY first and refused loud otherwise: 'CHN OR assignee
    is not EMPTY' must not silently widen the search. Raw JQL belongs in
    --query, where it is the declared input."""
    if query:
        jql = query
    else:
        key = project or cfg.get("project_key")
        if not key:
            print("jira adapter: import needs --project <KEY>, --query "
                  "<jql>, or config.project_key", file=sys.stderr)
            sys.exit(1)
        if not PROJECT_KEY.match(str(key)):
            print(f"jira adapter: invalid project key {key!r} (expected "
                  r"^[A-Z][A-Z0-9_]{1,30}$) — pass raw JQL with --query "
                  "instead", file=sys.stderr)
            sys.exit(1)
        jql = f"project = {key} ORDER BY created ASC"
    out, token = [], None
    while len(out) < IMPORT_MAX:
        path = ("/rest/api/3/search/jql?jql=" + urllib.parse.quote(jql)
                + f"&maxResults={PAGE_SIZE}"
                + "&fields=summary,description,status,updated")
        if token:
            path += "&nextPageToken=" + urllib.parse.quote(token)
        d = api(cfg, "GET", path)
        issues = d.get("issues", [])
        if not issues:
            break
        for issue in issues:
            f = issue.get("fields", {})
            cat = f.get("status", {}).get("statusCategory", {}).get("key", "new")
            out.append({
                "external_id": issue.get("key", ""),
                "title": f.get("summary", ""),
                "body": adf_to_text(f.get("description")) if f.get("description") else "",
                "status": CAT.get(cat, "open"),
                "updated_at": f.get("updated"),
            })
            if len(out) >= IMPORT_MAX:
                break
        token = d.get("nextPageToken")
        if not token or d.get("isLast"):
            break
    return out


def main():
    event = json.load(sys.stdin)
    cfg = event.get("config", {})
    for req in ("base_url", "project_key"):
        if req not in cfg:
            print(f"jira adapter: config.{req} is required", file=sys.stderr)
            sys.exit(1)
    if event["action"] == "pull":
        print(json.dumps(pull(cfg, event.get("items", []))))
    elif event["action"] == "import":
        print(json.dumps(do_import(cfg, event.get("query"),
                                   event.get("project"))))
    else:
        print(push(event, cfg))


if __name__ == "__main__":
    main()
