# Tests

Run: `bash cairn/scripts/cairn-test.sh` (or `bats tests/`, which keeps
working). Needs [bats-core](https://github.com/bats-core/bats-core), `jq`, and
`bd` on PATH — bd-dependent tests skip cleanly when it is missing. GNU
`parallel` is optional and worth having.

The runner picks the job count (`--jobs N`, else `test.jobs` in
`.cairn/config.json`, else your core count), checks what `bats -j` actually
requires *before* composing the command, and passes bats' exit code back
untranslated. `cairn-test.sh --print-command` prints the exact command and
runs nothing.

## What the suite costs

Measured 2026-08-04, 8 cores, bats 1.14.0:

| what | number |
|---|---|
| tests announced by `bats tests/` | **646** |
| `grep -h '^@test' tests/*.bats \| wc -l` | 648 — count the announcement, not the grep |
| whole suite at `-j 8` | **20m27s** wall, 209% CPU, ~46 concurrent `bats-exec` processes |
| `tests/cairn-doctor.bats` alone, serial | **19m05s** for 65 tests |
| `tests/cairn-map.bats` | 64s serial against 33s at `-j 6` |

The two-test gap is not drift: `bats --count` per file finds it at
`tests/smoke.bats:100` and `tests/cairn-test.bats:69`, two `@test` lines that
sit inside heredocs writing a throwaway bats file. The grep counts the
characters; only bats counts the tests.

The bottleneck is per-test setup — nearly every test builds a throwaway git
repo and a bd database — so the suite splits across cores well and a job count
above the core count buys nothing.

## Two traps, both paid for

**`bats -j` without GNU parallel does not run serial. It runs nothing.**
Measured on bats 1.14.0 with the parallel binary missing:

```
1..2
bats-exec-suite: line 323: parallel: command not found
# bats warning: Executed 0 instead of expected 2 tests
exit 1
```

Zero tests executed, reported as a failure. bats has a guard for this at
`bats-exec-suite:110` and it can never fire — it is written
`! type -p X && X --version`, whose two clauses cannot both hold. `-j` also
needs `flock` or `shlock` (`lib/bats-core/semaphore.bash:26-33`); without
either, same shape, `exit 1` and zero tests. This is why `cairn-test.sh`
checks both *before* composing the command and drops `-j` rather than passing
it through.

**`bats -f` with a filter that matches nothing exits 1**, with
`ERROR: Found no tests`. So a plan's `<verify>` and a CI command invoke whole
**files**, never `-f` with a test name that might not exist. A typo in a
filter and a genuinely broken suite are the same exit code.

**And do not read a suite result off `| tail`.** A `bats tests/... | tail -15`
whose failure scrolled out of the window was called green in this repo on
2026-08-04; the failing assertion had been red since the commit before. Count
`^not ok`, or read the plan line.

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
- `make_drift_fixture <dir>` — this repo's OWN planning files, frozen while they still disagree (`tests/fixtures/bookkeep-drift/`), plus the phase tree rebuilt from `phases.tsv` and a **baseline commit**. That commit is load-bearing: nothing else here commits, and `git diff` against a tree with no HEAD returns empty, so a write test proving "only the planned lines moved" would pass against a full-file reflow.
- `extract_frontmatter` / `assert_frontmatter_key` / `assert_json_eq` — assertion utilities

## The board render reference (`tests/fixtures/board-render/`)

Seven committed files, one per render mode of `cairn-status.sh`, captured
from `make_board_fixture`. `tests/cairn-board-invariance.bats` compares the
live render against them byte for byte — that is how a phase can claim it
changed the model and moved nothing on screen.

And it cuts the other way too. Phase 21 changed the render on purpose, so
three of the seven had to move; what the reference bought there was that the
change could not happen in silence. The rule that follows is the same rule
from the other side: regenerating is an act you perform after reading the
diff and writing down what moved in each file and why, never a step you take
to make a red test go green.

Regenerate them **only** when a render change is intentional and reviewed:

```
bash tests/fixtures/board-render/regenerate.sh
```

It is the only writer of those files, no test ever calls it, and it ends by
printing the diff it produced. **Read that diff before committing it.** A red
invariance test is not a reason to regenerate; it is a reason to find out
what moved. Regenerating by reflex turns the proof into a rubber stamp.

## The frozen drift fixture (`tests/fixtures/bookkeep-drift/`)

A byte copy of this repository's own `.planning/ROADMAP.md`,
`REQUIREMENTS.md` and `STATE.md`, frozen while they still disagree with each
other, plus `phases.tsv` (the phase tree indexed by name) and `MANIFEST.md`
(sha256s and the inventory of the disagreement). It is the test input for
`cairn-bookkeep.py`: a command that only ever meets consistent files proves
it can write, never that it can resolve drift.

Same contract as `board-render/`: written by `capture.sh`, read by the tests,
never regenerated to make a red test go green. Recapturing after someone
tidies `.planning/` freezes a repo with no disease left in it.

```
bash tests/fixtures/bookkeep-drift/capture.sh
```

Two things guard against that, and only one of them is real:

- `MANIFEST.md` records each file's sha256, which catches a hand-edit of a
  frozen file without a recapture;
- `tests/cairn-bookkeep.bats` **hardcodes** the anchors of the disease — the
  footer's literal wrong claim, the row count, the two missing requirement
  ids, the unreadable ellipsis. Those are literals on purpose. Reading them
  back out of `MANIFEST.md` would be a tautology: `capture.sh` writes the
  fixture and the manifest in the same run, so a late capture moves both
  together and every manifest-derived guard stays green over an empty proof.
  Measured during phase 29: tidying the frozen ROADMAP and realigning the
  manifest leaves the sha256 test green and turns only the hardcoded-anchor
  test red.
