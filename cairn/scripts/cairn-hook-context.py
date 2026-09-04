#!/usr/bin/env python3
"""Read a hook envelope and print safely quoted shell context assignments."""
import json
import os
from pathlib import Path
import shlex
import sys


def text(value):
    return value if isinstance(value, str) and "\0" not in value else ""


def main():
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except (ValueError, OSError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    env = os.environ
    # Current payload signatures outrank inherited launcher variables. Grok's
    # camelCase fields are authoritative; Codex also sets CLAUDE_PLUGIN_ROOT.
    if text(payload.get("hookEventName")) in {"session_start", "post_tool_use", "stop"}:
        agent = "grok"
    elif text(payload.get("turn_id")):
        agent = "codex"
    elif any(env.get(key) for key in ("GROK_HOOK_EVENT", "GROK_SESSION_ID",
                                      "GROK_WORKSPACE_ROOT", "GROK_PLUGIN_ROOT")):
        agent = "grok"
    elif env.get("PLUGIN_ROOT") or env.get("CODEX_THREAD_ID"):
        agent = "codex"
    elif env.get("CLAUDECODE"):
        agent = "claude"
    else:
        agent = "unknown"

    project = text(payload.get("cwd"))
    if not project:
        if agent == "grok":
            project = (env.get("GROK_WORKSPACE_ROOT") or env.get("GROK_PROJECT_DIR")
                       or env.get("CLAUDE_PROJECT_DIR"))
        elif agent != "codex":
            project = env.get("CLAUDE_PROJECT_DIR")
    project = project or os.getcwd()
    directory = Path(project).resolve()
    # Stop at the nearest tracker or Git boundary, including linked worktrees.
    # A nested repo without beads must never inherit its enclosing tracker.
    for ancestor in (directory, *directory.parents):
        if (ancestor / ".beads").is_dir() or (ancestor / ".git").exists():
            project = str(ancestor)
            break
    data = env.get("CLAUDE_PLUGIN_DATA", "")
    if agent == "grok":
        data = env.get("GROK_PLUGIN_DATA") or data
    elif agent == "codex":
        data = env.get("PLUGIN_DATA") or data

    tool = payload.get("toolName", payload.get("tool_name", ""))
    tool_input = payload.get("toolInput", payload.get("tool_input"))
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    for key, value in {"CAIRN_HOOK_AGENT": agent, "PROJECT_DIR": project,
                       "DATA_DIR": data, "TOOL_NAME": text(tool),
                       "TOOL_COMMAND": text(command)}.items():
        print(f"{key}={shlex.quote(value)}")


if __name__ == "__main__":
    main()
