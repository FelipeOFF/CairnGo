#!/usr/bin/env bash
# cairn-map.sh (capability bundle shim) — locate the cairn plugin's map
# generator (scripts/cairn-map.py) and delegate to it, so the bundle does not
# ship a second copy of the generator logic.
#
# Usage: identical to the plugin's cairn-map.sh:
#   cairn-map.sh <phase-number> [--milestone <m>] [--planning-dir <dir>]
#                [--check] [--json]
#
# Resolution order for the plugin root (first hit with scripts/cairn-map.py
# wins):
#   1. $CAIRN_PLUGIN_ROOT              explicit override
#   2. <project>/.cairn/plugin-root    pointer written by /cairn:init
#   3. $CLAUDE_PLUGIN_ROOT             when running inside a cairn command
#   4. <bundle>/../..                  dev checkout (cairn/capability/ next to
#                                      cairn/scripts/)
#
# No-op contract (exit 0, silent): the working directory has no .beads/, or
# cairn.enabled=false in .planning/config.json. An unresolvable plugin root
# warns to stderr and exits 0 — a missing generator must never break GSD.
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
  if [ -n "$root" ] && [ -f "$root/scripts/cairn-map.py" ]; then
    exec python3 "$root/scripts/cairn-map.py" "$@"
  fi
done

echo "[cairn] warning: could not locate the cairn plugin's cairn-map.py" \
     "(set CAIRN_PLUGIN_ROOT or re-run /cairn:init) — skipping map refresh" >&2
exit 0
