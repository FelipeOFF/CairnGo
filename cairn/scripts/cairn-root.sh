#!/usr/bin/env bash
# Print the cairn plugin root. First hit with scripts/cairn-root.sh (this file)
# or scripts/cairn-status.sh wins:
#   1. CAIRN_PLUGIN_ROOT
#   2. GROK_PLUGIN_ROOT
#   3. CLAUDE_PLUGIN_ROOT
#   4. .cairn/plugin-root (written by init / SessionStart)
#   5. this script's parent directory
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
is_root() { [ -n "${1:-}" ] && [ -d "$1/scripts" ] && [ -f "$1/scripts/cairn-root.sh" ]; }
for c in "${CAIRN_PLUGIN_ROOT:-}" "${GROK_PLUGIN_ROOT:-}" "${CLAUDE_PLUGIN_ROOT:-}"; do
  if is_root "$c"; then
    printf '%s\n' "$(cd "$c" && pwd)"
    exit 0
  fi
done
if [ -f .cairn/plugin-root ]; then
  ptr="$(head -1 .cairn/plugin-root 2>/dev/null || true)"
  if is_root "$ptr"; then
    printf '%s\n' "$(cd "$ptr" && pwd)"
    exit 0
  fi
fi
printf '%s\n' "$(cd "$HERE/.." && pwd)"
