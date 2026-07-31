#!/usr/bin/env bash
# cairn-lease.sh (capability bundle shim) — locate the cairn plugin's phase
# lease script (scripts/cairn-lease.py) and delegate to it, so the bundle
# does not ship a second copy of the lease/TTL/metadata logic.
#
# Usage: identical to the plugin's cairn-lease.sh:
#   cairn-lease.sh acquire <N>            [--project-dir DIR] [--json]
#   cairn-lease.sh release <N>            [--project-dir DIR] [--json]
#   cairn-lease.sh release --mine         [--project-dir DIR] [--json]
#   cairn-lease.sh renew   [<N>]          [--project-dir DIR] [--json]
#   cairn-lease.sh status  <N>            [--project-dir DIR] [--json]
#   cairn-lease.sh status  --all          [--project-dir DIR] [--json]
#
# Resolution order for the plugin root (first hit with scripts/cairn-lease.py
# wins):
#   1. $CAIRN_PLUGIN_ROOT              explicit override
#   2. <project>/.cairn/plugin-root    pointer written by /cairn:init
#   3. $CLAUDE_PLUGIN_ROOT             when running inside a cairn command
#   4. <bundle>/../..                  dev checkout (cairn/capability/ next to
#                                      cairn/scripts/)
#
# No-op contract (exit 0, silent): the working directory has no .beads/, or
# cairn.enabled=false in .planning/config.json. An unresolvable plugin root
# warns to stderr and exits 0 — a missing lease script must never break the
# calling GSD workflow (D-04: report, never stop the flow).
#
# This shim contains ZERO lease/TTL/metadata logic of its own — it only
# locates and execs the real cairn-lease.py, so that logic has exactly one
# implementation (see cairn-lease.py's own module docstring for the full
# acquire/release/renew/status contract and exit codes).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

# Quiet no-op outside cairn repos (or when the capability is toggled off).
[ -d "$PROJECT_DIR/.beads" ] || exit 0
if [ -f "$PROJECT_DIR/.planning/config.json" ]; then
  enabled="$(python3 - "$PROJECT_DIR/.planning/config.json" <<'PY' 2>/dev/null || echo true
import json, sys
try:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    cfg = {}
nested = cfg.get("cairn") if isinstance(cfg, dict) else None
off = (isinstance(nested, dict) and nested.get("enabled") is False) or \
      (isinstance(cfg, dict) and cfg.get("cairn.enabled") is False)
print("false" if off else "true")
PY
)"
  [ "$enabled" = "false" ] && exit 0
fi

candidates=()
[ -n "${CAIRN_PLUGIN_ROOT:-}" ] && candidates+=("$CAIRN_PLUGIN_ROOT")
if [ -f "$PROJECT_DIR/.cairn/plugin-root" ]; then
  candidates+=("$(head -1 "$PROJECT_DIR/.cairn/plugin-root")")
fi
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && candidates+=("$CLAUDE_PLUGIN_ROOT")
candidates+=("$(cd "$HERE/../.." && pwd)")

for root in "${candidates[@]}"; do
  if [ -n "$root" ] && [ -f "$root/scripts/cairn-lease.py" ]; then
    exec python3 "$root/scripts/cairn-lease.py" "$@"
  fi
done

echo "[cairn] warning: could not locate the cairn plugin's cairn-lease.py" \
     "(set CAIRN_PLUGIN_ROOT or re-run /cairn:init) — skipping lease call" >&2
exit 0
