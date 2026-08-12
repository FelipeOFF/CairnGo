#!/usr/bin/env bash
# Thin wrapper around the record boundary. See cairn-record.py for the contract.
# Usage: cairn-record.sh <kind> --phase <N> [--plan <P>] [--issue <ID>]
#        [--milestone <M>] [--title <T>] [--project-dir <D>] [--json]
# O corpo do registro vem sempre por stdin.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cairn-record.py" "$@"
