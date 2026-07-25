# Tests

Run: `bats tests/` (needs [bats-core](https://github.com/bats-core/bats-core), `jq`, and `bd` on PATH — bd-dependent tests skip cleanly when it is missing).

## The seam

Deterministic behavior lives in CLI scripts under `cairn/scripts/`. Tests invoke
those scripts against temp fixture repos and assert on resulting files, exit
codes, and bd state via `bd list --json` — never on script internals. If a
behavior can't be asserted through a script's CLI contract, move the behavior
into a script first.

## Fixture helpers (`tests/helpers.bash`)

- `require_bd` — skip the test when `bd` is not installed
- `make_tmp_repo` — throwaway git repo, auto-cleaned by bats
- `make_gsd_fixture <dir>` — minimal, structurally faithful GSD `.planning/` tree
- `make_bd_fixture <dir> [prefix]` — bd db with epic + children + dep + label (IDs in `BD_*` globals)
- `extract_frontmatter` / `assert_frontmatter_key` / `assert_json_eq` — assertion utilities
