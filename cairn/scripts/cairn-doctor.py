#!/usr/bin/env python3
"""cairn-doctor v5 — spec/ticket graph, triage labels, claims, spoke config.

Exit: 0 ok or warnings only, 2 usage, 5 bd unavailable, 7 at least one fail.
Missing phase-N is not a failure.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_OK, EXIT_USAGE, EXIT_BD, EXIT_FAIL = 0, 2, 5, 7


def die(msg, code):
    print(f"[cairn-doctor] {msg}", file=sys.stderr)
    sys.exit(code)


def bd_json(root, args):
    proc = subprocess.run(
        ["bd", "-C", str(root), *args, "--json"],
        capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        return None, proc.stderr
    out = (proc.stdout or "").strip()
    start = min([i for i in (out.find("["), out.find("{")) if i >= 0] or [-1])
    if start < 0:
        return [], None
    data = json.loads(out[start:])
    return (data if isinstance(data, list) else [data]), None


def cairn_meta(issue):
    meta = issue.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return {}
    return (meta or {}).get("cairn") or {}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project-dir", default=".")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    root = Path(args.project_dir).resolve()
    checks = []

    def add(cid, status, detail):
        checks.append({"id": cid, "status": status, "detail": detail})

    if not shutil.which("bd"):
        die("bd not on PATH", EXIT_BD)
    if not (root / ".beads").is_dir():
        add("beads", "fail", "no .beads/ — run /cairn-init")
    else:
        add("beads", "ok", str(root / ".beads"))
        issues, err = bd_json(root, ["list", "--all", "--limit", "0"])
        if issues is None:
            die(f"bd list failed: {err}", EXIT_BD)
        specs = [i for i in issues if cairn_meta(i).get("kind") == "spec"
                 or i.get("type") == "epic"]
        tickets = [i for i in issues if cairn_meta(i).get("kind") == "ticket"]
        open_specs = [i for i in specs if i.get("status") != "closed"]
        add("specs", "ok" if specs else "warn",
            f"{len(specs)} spec(s), {len(open_specs)} open")
        hollow = []
        for s in open_specs:
            kids = [t for t in issues
                    if str(t.get("id", "")).startswith(str(s.get("id")) + ".")]
            if not kids and not (s.get("description") or "").strip():
                hollow.append(s.get("id"))
        if hollow:
            add("spec-body", "warn",
                "hollow specs (no body): " + ", ".join(hollow[:8]))
        else:
            add("spec-body", "ok", "open specs have body or tickets")
        add("tickets", "ok" if tickets or not open_specs else "warn",
            f"{len(tickets)} ticket(s)")
        inprog = [i for i in issues if i.get("status") == "in_progress"]
        add("claims", "ok", f"{len(inprog)} in_progress")

    sync = root / ".cairn" / "sync.json"
    if sync.is_file():
        try:
            cfg = json.loads(sync.read_text(encoding="utf-8"))
            backends = cfg.get("backends") or cfg
            enabled = 0
            if isinstance(backends, dict):
                enabled = sum(1 for v in backends.values()
                              if isinstance(v, dict) and v.get("enabled"))
            add("spoke", "ok", f"sync.json present, {enabled} enabled backend(s)")
        except (OSError, ValueError) as e:
            add("spoke", "fail", f"sync.json unreadable: {e}")
    else:
        add("spoke", "not-applicable", "no .cairn/sync.json")

    ptr = root / ".cairn" / "plugin-root"
    if ptr.is_file() and ptr.read_text().strip():
        add("plugin-root", "ok", ptr.read_text().strip().splitlines()[0])
    else:
        add("plugin-root", "warn", "missing .cairn/plugin-root — run /cairn-init")

    failed = [c for c in checks if c["status"] == "fail"]
    if args.json:
        json.dump({"ok": not failed, "checks": checks}, sys.stdout)
        print()
    else:
        sym = {"ok": "✓", "warn": "⚠", "fail": "✗", "not-applicable": "⊘"}
        for c in checks:
            print(f"{sym.get(c['status'], '?')} {c['id']}: {c['detail']}")
        print("FAIL" if failed else "OK")
    sys.exit(EXIT_FAIL if failed else EXIT_OK)


if __name__ == "__main__":
    main()
