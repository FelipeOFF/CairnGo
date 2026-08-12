#!/usr/bin/env bash
# capture.sh — the ONLY writer of tests/fixtures/machine-contract/*.txt.
#
# What it captures: the bytes `cairn-status.sh` printed when stdout was NOT a
# tty and NO flag was given, taken before Phase 22 split that path in two.
# Until then `--plain` and the flagless non-TTY default were byte-identical
# (measured 2026-08-06, md5 e98d3096656463236c2ed12a12be90e3 on all four of
# `--plain`, `--plain --color=never`, the flagless run, and the committed
# tests/fixtures/board-render/plain.txt).
#
# WHY IT REFUSES TO OVERWRITE. This file is NOT regenerable, not even in
# principle: PIPE-02 makes a flagless non-TTY run render the human board, so
# running this script after the split captures the board, not the machine
# contract — a file that looks like a reference and proves nothing. `--force`
# exists for one case only: a capture taken wrong BEFORE the split. Never
# after.
#
# WHY IT DOES NOT LIVE IN tests/fixtures/board-render/. That directory belongs
# to regenerate.sh, which rewrites all seven files in a single pass. An
# executor who changes the human render and regenerates rewrites plain.txt
# along with six others, inside one commit, and --plain silently loses its
# guard without anyone deciding that. Nothing regenerates this file alongside
# anything else, which is the whole point of the second axis.
#
# Needs bd (>= 1.1.0, for `bd create --id`) on PATH.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$(dirname "$HERE")")"
REPO_ROOT="$(dirname "$TESTS_DIR")"
TARGET="$HERE/nontty-pre-split.txt"

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

if [ -e "$TARGET" ] && [ "$FORCE" -eq 0 ]; then
  echo "capture.sh: $TARGET already exists — refusing to overwrite." >&2
  echo "  This capture is write-once: the code path it recorded no longer" >&2
  echo "  exists after the Phase 22 split, so re-running captures the human" >&2
  echo "  board instead of the machine contract. Pass --force ONLY to redo a" >&2
  echo "  capture taken wrong before the split." >&2
  exit 1
fi

if ! command -v bd >/dev/null 2>&1; then
  echo "capture.sh: bd is not on PATH — install beads first" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "$TESTS_DIR/helpers.bash"
CAIRN_TMP_DIRS=()

STATUS_SH="$REPO_ROOT/cairn/scripts/cairn-status.sh"

make_tmp_repo
make_board_fixture "$PWD"

# NO FLAGS, deliberately — not even --color=never. The absence of flags is
# what makes this file evidence of the non-TTY path rather than of --plain.
# --color=never would not move a byte here (render_plain never consults
# Style), and adding it would quietly turn the capture into something else.
bash "$STATUS_SH" > "$TARGET"

cd "$REPO_ROOT"
cleanup_tmp_repos

echo "captured $TARGET"
echo "  bytes: $(wc -c < "$TARGET" | tr -d ' ')"
echo "  md5:   $(md5 -q "$TARGET" 2>/dev/null || md5sum "$TARGET" | cut -d' ' -f1)"
