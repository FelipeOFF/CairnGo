# This capability bundle is archived

**Since:** cairn v1.6 (phase 37, PLUG-04), 2026-08-12.
**Status:** on disk, not installed, not loaded, not read at runtime.

## Why

The cairn GSD capability existed to fuse two loops that lived in two plugins.
With it registered against an installed `gsd-core`, plain `/gsd:plan-phase`,
`/gsd:execute-phase`, `/gsd:verify-work` and `/gsd:ship` linked, claimed, closed
and gated bd issues through four contributions and one blocking `ship:pre` gate.

v1.6 removed the other plugin. The GSD runtime is now vendored inside cairn
(`cairn/gsd/`), and phase 36 adapted its 129 state sites and 189 verb sites to
talk to bd directly. The fusion the capability provided is no longer a bridge
between two things — it is how the one remaining runtime already works.

So the bundle has **no host**. `.gsd/capabilities/cairn/` and
`.gsd-capabilities.json` on a machine that ran `/cairn:init` before v1.6 are
leftover files that nothing reads; `/cairn:doctor` check 10 reports them as a
WARN with a named cleanup (`rm -rf`), and never deletes them itself.

## Why it is still on disk

Deleting it is a separate change with a measured blast radius, and v1.6 is not
the release to spend it in:

- `cairn/scripts/cairn-capability.py` (721 lines) installs and verifies it, and
  still owns the lineage rules `/cairn:doctor` delegates to;
- doctor check 15 (`release-versions`) reads `capability.json` as its **own**
  semver axis, deliberately separate from the plugin version (decision D-02);
- `tests/capability.bats` and `tests/cairn-capability.bats` assert against the
  bundle's contents.

Archiving is therefore: `/cairn:init` stopped installing it, `/cairn:doctor`
stopped requiring it and started reporting its residue, and this file states
that the directory is history rather than a live component. The physical
removal is recorded in the phase's `deferred-items.md` and belongs after phase
38 proves nothing reads the bundle at runtime.

## What replaced it

| The capability did | What does it now |
|---|---|
| `plan:post` — write `beads:` frontmatter, regenerate the map | `/cairn:plan`, plus the vendored plan-phase workflow |
| `execute:wave:pre` — claim | `/cairn:work`, plus the vendored execute-phase workflow |
| `execute:wave:post` — close with a SUMMARY-derived reason | the same |
| `verify:post` — cross-check | `/cairn:verify`, plus the vendored verify-work workflow |
| `ship:pre` — blocking, deterministic gate | `cairn-gate` in the pre-push shim `/cairn:init` installs |

The ship gate is the one to note: it never depended on the capability host. It
runs from git's own `pre-push` hook, and it kept working through the whole
transplant.
