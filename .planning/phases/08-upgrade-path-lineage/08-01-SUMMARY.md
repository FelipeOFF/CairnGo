---
phase: 08-upgrade-path-lineage
plan: "01"
status: complete
requirements: [GSD-03, GSD-04]
beads: [CairnGo-xcc, CairnGo-wlc]
---

# Phase 8 Plan 01 — Summary

The state of the fusion is now visible on every routine health check, and people
already installed have a documented way across.

## What shipped

**GSD-03 — doctor reports the lineage.** `cairn-doctor` gained an eleventh check,
`gsd-capability`, which delegates to `cairn-capability.py detect --json` so the
lineage rules and the two registration checks are defined once:

| Situation | Status |
|---|---|
| gsd-core, cairn registered and completely staged | ✓ ok |
| GSD 4.x lineage — no `capability` subcommand | ✗ fail, with `claude plugin install gsd-core@cairngo` |
| gsd-core, but the registry does not list cairn | ✗ fail, routed to `/cairn:init` |
| Registered, but the bundle is staged without its gate script | ✗ fail — the ship gate would pass without checking |
| No GSD binary discoverable at all | ⚠ warn — "cannot tell" is a different claim |

A ✗ rather than a ⚠ is the point. The capability install failed silently for
months precisely because nothing hard ever said no.

**GSD-04 — the upgrade path.** The `gsd` marketplace entry is back alongside
`gsd-core`, carrying its own deprecation: the description states that the fusion
cannot run on that line and that the entry is removed in **v1.4** (the operator's
chosen window — one minor release). New guide at
`cairn/docs/gsd-core-migration.md` covers why the switch matters, how to check with
`/cairn:doctor`, the four commands to migrate, what changed underneath, and the
three failure shapes actually observed. Nothing in `.planning/` or `.beads/`
changes — it is a plugin swap, not a data migration.

## What the work turned up

**The new check reads global state, and that nearly made it untestable.** Every
other doctor check reads the repo; this one reads which GSD is installed on the
machine. Left alone it made the doctor's own test fixture non-hermetic — the
"healthy fixture, every check ✓" test started failing because the *developer's*
plugin cache has a 4.x GSD in it, and CI would have disagreed with local runs for
reasons invisible in the output. `CAIRN_GSD_BIN` pins the discovery step so the
verdict is reproducible; the doctor fixture now wires a stub, which also gets the
ok path under test rather than only the failures.

A second environment trap showed up while testing the "no GSD anywhere" path:
scrubbing `HOME` to hide the plugin cache also moves the version manager's shims,
so `python3` stopped resolving and the doctor could not start. The test now
rebuilds `PATH` from the system directories plus bd's own, which leaves a real
`/usr/bin/python3` and no `gsd_run` anywhere.

**Attribution note.** The `CAIRN_GSD_BIN` seam is planned here but was committed
with phase 7 (it was written while that commit was being assembled). Recorded
rather than rewritten.

## Verification

- `bats tests/cairn-doctor.bats` — 28 tests green, including the healthy fixture
  now asserting eleven checks all `ok`, plus four new tests: legacy fails,
  unregistered fails, a bundle missing its gate script fails, no binary warns.
- `cairn-doctor` on this repo reports `✗ gsd-capability — GSD 4.x lineage …` and
  exits 7. That is the true state of this machine, and it is the first time the
  tooling has ever said so.

## Consequence the operator needs to decide

Because this repo's GSD is the 4.x line, `cairn-doctor` is now **red here** — and
doctor failure is a stop rule for `/cairn:autonomous`. The local install cannot
move to gsd-core until this branch merges and the marketplace is refreshed, so the
red is expected in the interim. Raised rather than worked around.
