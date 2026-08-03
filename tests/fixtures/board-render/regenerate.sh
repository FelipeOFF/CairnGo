#!/usr/bin/env bash
# regenerate.sh — the ONLY writer of tests/fixtures/board-render/*.txt.
#
# Those files are the byte-for-byte reference render of make_board_fixture,
# captured from cairn-status.py before phase 20 changed the model underneath
# it. tests/cairn-board-invariance.bats reads them and never writes them: a
# test that regenerates its own reference before comparing proves nothing.
#
# Run this ONLY when a render change is INTENTIONAL and reviewed. It ends by
# printing `git diff --stat` of what it rewrote — that diff is the point.
# Read it, and commit it as its own visible act. A red invariance test is not
# a reason to run this script; it is a reason to find out what moved.
#
# Needs bd (>= 1.1.0, for `bd create --id`) on PATH.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$(dirname "$HERE")")"
REPO_ROOT="$(dirname "$TESTS_DIR")"

# shellcheck source=/dev/null
source "$TESTS_DIR/helpers.bash"
CAIRN_TMP_DIRS=()

if ! command -v bd >/dev/null 2>&1; then
  echo "regenerate.sh: bd is not on PATH — install beads first" >&2
  exit 1
fi

STATUS_SH="$REPO_ROOT/cairn/scripts/cairn-status.sh"

# NAME then the flags for that mode. --color=never is added to every one:
# escape bytes belong to a terminal, never to a committed reference.
render() {
  local name="$1"
  shift
  bash "$STATUS_SH" "$@" --color=never > "$HERE/$name.txt"
  echo "  wrote $name.txt ($(wc -c < "$HERE/$name.txt" | tr -d ' ') bytes)"
}

make_tmp_repo
make_board_fixture "$PWD"

echo "regenerating tests/fixtures/board-render/ from make_board_fixture:"
render w100     --width 100
render w50      --width 50
render w38      --width 38
render ascii100 --width 100 --ascii
render maxrows  --width 100 --max-rows 2
render plain    --plain
render brief    --brief

cd "$REPO_ROOT"
cleanup_tmp_repos

echo
echo "review this diff before committing it:"
git -C "$REPO_ROOT" diff --stat -- tests/fixtures/board-render/
# `diff --stat` says nothing about a file git has never seen, so a brand-new
# mode would regenerate into total silence. List those separately.
git -C "$REPO_ROOT" ls-files --others --exclude-standard \
  -- tests/fixtures/board-render/ | sed 's/^/ untracked  /'
