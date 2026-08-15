# The vendored GSD runtime — one dispatcher, three siblings, three shared modules

> Eight thousand lines under `cairn/scripts/` exist to answer the GSD planning
> runtime's own verbs, in Python, with no `node` in the path. This document
> explains that mechanism: how a `/cairn:*` command reaches it, how one entry
> point routes ninety-odd verbs across four files, and — the part that matters
> most — how fidelity to the original binary is *measured* rather than claimed.
> Read this before changing any of those files. For the surface question of
> which GSD commands cairn carries at all, see
> [gsd-core commands](./gsd-core-commands.md).

## The one-sentence model

**The vendored prompt layer under `cairn/gsd/` calls one shell function,
`gsd_run`; `gsd_run` is `cairn-gsd.py`; and `cairn-gsd.py` either answers the
verb itself or `os.execv`s the sibling that owns it — with the canonical verb
already resolved into `argv[1]`, so no sibling ever parses a spelling.**

## Why any of this exists

Since v1.6 the GSD planning runtime ships **inside** the cairn plugin, under
`cairn/gsd/`. That decision is documented in
[GSD Core migration](./gsd-core-migration.md), and its consequence is this
directory: a vendored prompt layer is a set of markdown workflows that expect a
runtime to answer verbs like `query config-get` or `state.load`. Vendoring the
markdown without vendoring the runtime would leave 430 call sites across 57
files talking to a binary that may or may not be installed, at whatever version
the machine happened to have.

So the runtime is reimplemented in Python, in this repo, pinned to one upstream
tag. `cairn-preamble.py` is what wires the two halves together: it rewrites the
runtime-resolution line at the top of each vendored `bash` fence so `gsd_run`
points at `cairn-gsd.py`. It is the **only** script in the house that writes
under `cairn/gsd/`, it writes exactly one line per file, and only in paths
registered in `cairn/gsd-adaptations.json` — never under `contracts/`, never
`MANIFEST.json`, and never when the rewrite would be byte-identical.

## The mechanism

`cairn-gsd.py` is the single entry point. Three things happen in `main()`:

1. **Spelling → verb.** `build_routes()` reads
   `cairn/gsd/contracts/contracts.json` and each per-family contract file, and
   builds a `spelling → (verb, family)` map. 89 verbs carry 91 spellings.
   Routing is longest-match-first over the argv words, so `state.load` and
   `query config-get` both resolve without the caller knowing which is which.
   **This table exists in exactly one place.** No sibling carries a parallel
   copy, which is the whole reason a sibling receives the *canonical verb* and
   never the spelling that produced it.
2. **In-process, or exec.** If a handler for the verb is registered in this
   file, it runs and the process exits with the handler's status. Otherwise
   `script_for()` names the sibling and the process is *replaced*:
   `os.execv(sys.executable, [python, sibling, verb, *rest])`. Replacement, not
   a subprocess — stdout, stderr and exit code are the sibling's own, with
   nothing in between to translate them. That preserves the semantics of the
   `cairn-gsd.sh` wrapper it grew out of, which is likewise an `exec`.
3. **Nothing else.** A verb outside the contract universe dies exit 2 with
   `verbo desconhecido (fora do universo do contrato)` and an empty stdout. A
   verb whose family has no sibling on disk dies exit 4 naming the family. The
   universe is closed on purpose: a call site that invents a verb gets a loud
   failure, not an invented envelope.

Where the 89 verbs land, derived by replaying the routing logic over
`contracts.json`:

| Answers | File | Lines | Verbs | Families |
|---|---|---|---|---|
| in-process | `cairn-gsd.py` | 2100 | 10 | `commit`, `config`, `dispatch-model`, `loop-hooks`, `skills` |
| exec'd | `cairn-gsd-init.py` | 1365 | 33 | `init`, `worktree`, generic `misc` |
| exec'd | `cairn-gsd-state.py` | 1560 | 30 | `estado`, `roadmap-phase`, planning-docs `misc` |
| exec'd | `cairn-gsd-check.py` | 1491 | 16 | `checagem`, the five `misc` ex-orphans |

Two of those rows are not a family split but a **verb** split. The `misc`
family has 30 verbs and no natural home, so it routes by verb into three
destinations: eight planning-document verbs go to the state sibling, five go to
the check sibling (`MISC_CHECK_VERBS`), and the remaining seventeen fall
through to init. The two frozensets encoding that live next to each other at
the top of `cairn-gsd.py`, with the phase that decided each one named in the
comment above it.

The siblings are **not commands**. There is no `/cairn:gsd-state`, and there
will not be one: they are reachable only by `os.execv` from `cairn-gsd.py`, and
`tests/cairn-command-surfaces.bats` records that fact as a written reason
rather than letting it pass as silence.

## Parity is measured, not asserted

This is the interesting half. The Python runtime is a reimplementation, and a
reimplementation that merely *claims* fidelity decays the first time someone
refactors it. So fidelity here is a test that runs.

**The differential harness.** `tests/fixtures/gsd-goldens/scenarios.json`
declares 153 scenarios — each an `argv`, a declarative fixture repo, a `verb`,
a comparison mode and an optional mask. The bats runner builds the fixture,
runs the Python binary, and compares its output against the golden file for
that scenario. 127 scenarios compare parsed JSON, 26 compare raw bytes. Masks
exist only for values that cannot be deterministic (a `scanned_at` timestamp
becomes `<masked>` on both sides, and a mask whose regex fails to match is
itself a failure — a mask can hide a value, never a mismatch).

**Where a golden comes from is recorded on the golden.** Of the 156 files in
that directory, 154 carry a `source` pin of `open-gsd/gsd-core` `v1.10.0` at
commit `68a04cc`, and each declares its `provenance`:

- `recorded` (39) — the bytes were captured from the **real** binary. That is
  what `cairn-gsd-record.py` does: it verifies the cached clone's HEAD against
  the expected commit, requires `node`, probes and if necessary builds the
  runtime, then re-records scenario by scenario. It never clones, and it
  refuses outright on an unverified corpus. A `recorded` golden makes the
  comparison literal equality against the original.
- `derived-from-contract` (114) — the shape comes from the contract, because
  recording it is meaningless. The clearest case: verbs that answer from `bd`.
  The upstream binary reads `STATE.md`; there is nothing to record from it that
  would say anything about a verb whose fact lives in the issue tracker.

**And the differences are declared, one by one, with a reason.**
`tests/fixtures/gsd-goldens/divergences.json` holds **67 entries**. Each names
a `verb`, a `family`, an `aspect`, what `upstream` does, what `cairn` does
instead, and *why*. The reasons are not decoration — they are the argument, and
they fall into recognizable classes:

- **Single host.** Cairn runs on Claude only, so multi-runtime layers
  (`persona-fallback-2454`, `static-host-table`, `manager-render-reduced`) are
  dead code here. Porting half of a mechanism is worse than declaring it
  absent.
- **Not reachable without `node`.** The upstream capability registry is a 7k
  line `.cjs` module the Python binary cannot execute. Anything downstream of
  it (`valid-keys-domain`, `native-hook-table`) is reduced, and the reduction
  is written down.
- **Fact lives in bd now.** `source-of-truth-state-load` is the sharpest of
  these: upstream's `state.load` *never fails* — a missing `STATE.md` yields
  `state_exists: false`. Cairn's fails, named, exit 1. Two sources of fact is
  the disease the milestone exists to kill, so degrading to markdown is
  precisely the behavior that had to change.
- **Determinism.** No golden carries a timestamp. `phase-complete-date-omitted`
  and `windows-no-timestamp` drop time fields because the temporal fact already
  has an owner in `bd`.
- **Debt, registered rather than forgotten.** Several entries record what a
  phase decided *not* to fix, with the measurement that made it safe — the
  `@file:` unwrap that is inert in 12 files because the Python binary never
  emits that prefix; the `worktree.set-baseref` spelling mismatch whose call
  site already swallows failure. Writing down a deferral is what separates a
  decision from an oversight.

22 scenarios are additionally flagged `divergent_from_real`, meaning the
re-recording step is skipped for them by declaration — the house shape is
knowingly not the binary's shape there.

**What this buys.** A refactor that changes behavior fails a golden. A
behavior change that is *intended* cannot be merged quietly: it must either
move a golden or add a `divergences.json` entry, and both are visible in
review. The file is the contract between "we reimplemented this" and "we know
exactly where we stopped."

`tests/cairn-parity.bats` closes the loop from the other side: every verb the
binary serves must have executable coverage, every `gsd_run` call in the
vendored tree must resolve to a verb the binary actually serves, and a
from-scratch repo with no gsd-core installed must come out clean.

## The D-01 ceiling, and the gate that holds it

Phase 34 set a ceiling: no file of the Python binary passes ~1500 lines. For a
long while that was an assertion in a plan, which is to say it was true on the
day it was written and unverified every day after. Measured in August 2026,
three of six files were already over it.

`tests/cairn-gsd.bats` now enforces it in two halves, and the split is the
point:

1. **A per-file pin that only descends.** Every file has a recorded line count;
   growing past it fails. Nothing creeps. Raising a pin is a visible edit in a
   review, not an accident.
2. **A closed exception list.** Only `cairn-gsd.py` and `cairn-gsd-state.py`
   may exceed 1500, each with a tracked issue. Any *other* file over the
   ceiling fails — a new exception cannot be added silently, only declared.

The gate globs `cairn-gsd*.py` **and** `cairn_gsd_*.py`, so files added to
either naming convention are covered without anyone remembering to register
them.

The failure this gate was built from is worth keeping: the check sibling was
brought under the ceiling by moving its overflow into a shared module — and the
shared module then grew to 1536 lines. The number people were watching had
become the number of the wrong file.

## The three shared modules

That incident is what the 3.0.0 partition answered. The rule of the cut is
narrow and mechanical:

> **Shared by two or more siblings goes in the envelope. Everything else stays
> where it is used.**

| Module | Lines | Owns |
|---|---|---|
| `cairn_gsd_render.py` | 91 | the measured output envelope — `js_string`, `stringify`, `emit`, `output_like_binary`, the argv splitter, and the `_UNDEFINED` sentinel that models JavaScript's `undefined` (distinct from `None`, which is JSON `null` and survives into the output) |
| `cairn_gsd_parse.py` | 656 | document input: heading sections, task blocks, frontmatter — the markdown substrate |
| `cairn_gsd_fact.py` | 837 | fact: git, subprocess, audit trails |

The render module went from 1536 lines to 91 and left the exception list
entirely. The two new modules entered the gate automatically through the glob.
Note the direction of dependency: `cairn_gsd_fact` imports from
`cairn_gsd_parse`; nothing imports upward into the siblings.

## `cairn_source.py` — the roadmap, derived from bd

Adjacent to the dispatcher and load-bearing for everything around it. It is
416 lines, imported by 7 scripts (`cairn-doctor`, `cairn-gate`, `cairn-lease`,
`cairn-map`, `cairn-reconcile`, `cairn-status`, `cairn-trend`), and it exists
to enforce one sentence: **a question about a phase is a question for `bd`.**

Before it, the project's roadmap — which phases exist, what each promises,
which requirements they carry, which milestone is running — was read out of
`ROADMAP.md` by roughly 25 parsers spread across 8 scripts, each with its own
private grammar of markdown. Once the repository stopped *writing* markdown,
those parsers went blind, and blind is not green: the doctor started printing
`⊘ nothing to compare` across six checks at once. The fix was not to reopen the
markdown; it was to send the question to a different address.

What that address looks like today, measured over `cairn/scripts/`:
`ROADMAP.md` appears on 132 lines across 14 scripts, but only **12** of those
lines touch a path at all, and only **two** read its contents. Everything else
is prose in docstrings explaining why the parser is gone. The mapping
`cairn_source` reads instead is the convention cairn already stamps on every
issue: phase is the label `phase-N` (unpadded), milestone is `m-vX.Y`, a
requirement is a bead carrying `gsd.req` metadata, a plan is `plan-NN`, and
completion is the bead's status and nothing else.

**One read per process.** `bd list --all --limit 0 --json` costs about half a
second on a repo of this size, and the doctor asks the roadmap dozens of
questions in a single run — thirty calls would be fifteen seconds of doctor.
So the read happens once per `(root, process)` into `_CACHE`, and every query
derives from that list in memory. A process that needs to re-read calls
`invalidate()`. No new database: `bd` *is* the database, and what was missing
was simply not querying it in a loop.

**The module never writes.** Not a bead, not a status, not a convention fix.
Writing belongs to `cairn-record` and `cairn-migrate`. A reader that also
writes is how the doctor becomes the thing it was supposed to be measuring.
Nor does it read `.planning/` — not even to cross-check, because a fallback to
markdown is exactly how markdown becomes the source of truth again through the
back door.

### `None` means *no* cycle, not *every* cycle

The one trap in this module, and it is worth a paragraph because it cost two
releases.

Every scoped query takes a `milestone_key`, and it is **mandatory**. That
parameter accepts three values:

| Value | Meaning |
|---|---|
| `"m-v3.2"` | that cycle |
| `ALL_MILESTONES` | every cycle `bd` knows about |
| `None` | **no** cycle — returns empty, always |

`None` used to mean "all", and that default produced two separate incidents.
The cause was never a careless caller: `milestone(root)` returns `None`
*legitimately* when no cycle is open, and every reader that forwarded its
result unchanged silently widened its own scope from one cycle to the entire
history of the repository. Empty is the safe answer to "which phases are in the
cycle that isn't running"; "all of them" is not. Callers that genuinely want
every cycle now say `ALL_MILESTONES` in as many words.

For the same reason `open_cycle(root)` returns the pair `(key, bool)`: two
different situations return `None` from `milestone()` and they need different
handling, so the module answers both rather than letting each consumer invent
its own test.

## Where these numbers came from

Everything above is measured on this tree, not carried over from a plan.

```bash
wc -l cairn/scripts/cairn-gsd*.py cairn/scripts/cairn_gsd_*.py \
      cairn/scripts/cairn_source.py       # the line counts and the pins
jq '.verbs | length' cairn/gsd/contracts/contracts.json          # 89
jq '.scenarios | length' tests/fixtures/gsd-goldens/scenarios.json  # 153
jq '.divergences | length' tests/fixtures/gsd-goldens/divergences.json  # 67
grep -rn 'gsd_run' cairn/gsd/ | wc -l                            # 430 call sites
grep -rl 'import cairn_source' cairn/scripts/ | wc -l            # 7
```

The dispatcher and its siblings are 6,516 lines; with the three shared modules,
8,100. The verb-to-sibling split in the table is produced by replaying
`script_for()` over `contracts.json` rather than by reading the comments.

One number is deliberately not restated here: `tests/cairn-parity.bats` speaks
of an 87-verb universe, while `contracts.json` carries 89 today — the universe
grew by the two `references_extension` verbs phase 38 added. If you are
touching either file, reconcile them there, not here.
