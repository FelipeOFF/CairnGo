# Tests

Run: `bats tests/` (needs [bats-core](https://github.com/bats-core/bats-core), `jq`, and `bd` on PATH — bd-dependent tests skip cleanly when it is missing).

## The seam

Deterministic behavior lives in CLI scripts under `cairn/scripts/`. Tests invoke
those scripts against temp fixture repos and assert on resulting files, exit
codes, and bd state via `bd list --json` — never on script internals. If a
behavior can't be asserted through a script's CLI contract, move the behavior
into a script first.

## Assertion style

A failing `[[ ]]` or `! cmd` mid-test does NOT fail a bats test on this bash
(bash's `!` suppresses errexit). So: substring checks use plain `grep -qF`,
negative checks go through a `refute_in_output`-style helper that explicitly
`return 1`s, and computed comparisons use `[ ... ]` as the last command or a
helper. Never rely on an inline `! grep` or `[[ ]]` to fail a test.

## Fixture helpers (`tests/helpers.bash`)

- `require_bd` — skip the test when `bd` is not installed
- `make_tmp_repo` — throwaway git repo, auto-cleaned by bats
- `make_gsd_fixture <dir>` — minimal, structurally faithful GSD `.planning/` tree
- `make_bd_fixture <dir> [prefix]` — bd db with epic + children + dep + label (IDs in `BD_*` globals)
- `make_board_fixture <dir>` — the deterministic board fixture: every roadmap shape plus six bd issues at **fixed** ids (`brd-001`…`brd-006`, needs bd >= 1.1.0 for `bd create --id`). Two builds of it render the same bytes; without the fixed ids and the literal `--prefix` they do not.
- `extract_frontmatter` / `assert_frontmatter_key` / `assert_json_eq` — assertion utilities

## The board render reference (`tests/fixtures/board-render/`)

Seven committed files, one per render mode of `cairn-status.sh`, captured
from `make_board_fixture`. `tests/cairn-board-invariance.bats` compares the
live render against them byte for byte — that is how a phase can claim it
changed the model and moved nothing on screen.

Regenerate them **only** when a render change is intentional and reviewed:

```
bash tests/fixtures/board-render/regenerate.sh
```

It is the only writer of those files, no test ever calls it, and it ends by
printing the diff it produced. **Read that diff before committing it.** A red
invariance test is not a reason to regenerate; it is a reason to find out
what moved. Regenerating by reflex turns the proof into a rubber stamp.
