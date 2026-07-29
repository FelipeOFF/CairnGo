# Phase 7: Official source + proven capability install - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning
**Source:** Interactive autonomous run (`/cairn:autonomous --interactive v1.2`). Three decisions were put to the operator rather than resolved as Claude's Discretion; they are recorded verbatim below.

<domain>
## Phase Boundary

cairn stops depending on a GSD lineage that cannot host it, and the install that was silently failing starts telling the truth. Requirements: GSD-01, GSD-02. bd issues: CairnGo-jge, CairnGo-zb4 — see `07-BEADS-MAP.md`.

Research backing: `.planning/research/gsd-core-migration.md`, extended in this phase with live verification against `open-gsd/gsd-core@v1.8.0` (see Findings).

Out of scope here: the compatibility entry for people already installed and the doctor lineage check (GSD-03, GSD-04 → phase 8), and the per-command decisions about what gsd-core brings (GSD-05 → phase 9).

</domain>

<decisions>
## Operator decisions (asked, not assumed)

### CI validator — "clone pinned + cache"
The gsd-core validator runs on **every** PR against a pinned tag, rather than in a
separate non-blocking job. Implemented as a shallow clone of the tag; the cache half
of the decision turned out to be unnecessary (see Findings — no build is involved).

### Deprecation window — "one minor release (drops in v1.4)"
The old `gsd` marketplace entry lives one cycle alongside `gsd-core` and is removed
in v1.4. *(Applies to phase 8, recorded here so the window is decided once.)* Claude
recommended a date-based window instead, on the grounds that a version-based one is
invisible to users who do not track releases; the operator chose the release-based
window and that is what phase 8 will implement.

### The 24 unreferenced gsd-core commands — "wrap the phase/planning-adjacent ones"
Commands touching phases and planning get `/cairn:*` wrappers; the rest are
documented as "use the GSD command directly". *(Applies to phase 9.)* Claude
recommended documenting by default to keep cairn's surface small; the operator chose
the wider wrapping and that is the bias phase 9 will apply.

## Implementation decisions (locked)

- **Pin the source to a release tag.** `open-gsd/gsd-core`'s default branch is
  `next`, a development branch. An unpinned marketplace entry would ship unreleased
  code to every install. The marketplace schema supports this: the official Anthropic
  marketplace pins its entries by `ref`/`commit`/`sha`.
- **Verification, not the installer's exit code, is the verdict.** `capability install`
  returning 0 is not evidence the capability registered.
- **Two independent registration checks, both required.** GSD's own `capability list`
  must report cairn `active`, AND the staged bundle must carry the scripts its gates
  reference. The second is not redundant: the ship-gate predicate is written
  `test -f <gate script> || exit 0`, so a bundle staged without its scripts leaves a
  gate that passes vacuously. Only a filesystem check catches that.
- **Discovery must not depend on PATH.** `gsd_run` is not on PATH in a normal Claude
  Code session (verified on this machine), which is why the old init block reached its
  `else` branch and skipped the install without ever attempting it. The script searches
  the plugin cache too.
- **Keep the local-dev skip, forbid it in CI.** `CAIRN_REQUIRE_GSD_VALIDATOR=1` turns
  the validator's "absent → skip" into a hard failure; CI sets it.

</decisions>

<findings>
## Live verification (run against real artifacts, not inferred)

1. **`capability` exists on gsd-core and not on the 4.x line.** gsd-core 1.8.0 lists
   `install, update, remove, list, outdated, trust, disable, enable, state, set`.
   The installed `gsd` 4.3.1/4.4.0 answers `Error: Unknown command: capability` and
   exits 1 — so the old `|| echo "capability install skipped"` swallowed a real
   failure and returned 0.
2. **The fusion works against the official core.** Installing this repo's bundle into
   a scratch project registered `cairn v1.0.0`, `scope: project`, `status: active`,
   `surfaced: true`, alongside gsd-core's own 38 capabilities. The bundled gate
   scripts were staged intact.
3. **A bare git clone of gsd-core has a non-functional CLI** ("runtime library is not
   built"), because the compiled `lib/*.cjs` are build artifacts. This is **not** a
   blocker: gsd-core's `ensure-runtime-build.cjs` self-heals. Claude Code runs
   `npm install --ignore-scripts` on plugin install, which puts TypeScript in place,
   and the first CLI call compiles the runtime once (~3s, verified end to end through
   the exact git-tag path a marketplace install takes).
4. **The validator alone needs no build.** gsd-core git-tracks the generated
   `capability-validator.cjs` and its only dependency (`loop-host-contract.cjs`), so a
   shallow clone of the tag is sufficient for CI — no npm install, no tsc.
5. **`@opengsd/gsd-core` is on npm** (1.8.0) and ships the fully prebuilt runtime.
   Not used for CI (the shallow clone is closer to what users receive), but it is the
   cheapest way to get a working CLI for local experiments.

</findings>

<risks>
- The pin (`GSD_CORE_REF`, `ref: v1.8.0`) will go stale. That is deliberate: bumping
  it is a one-line reviewable change rather than a silent drift, and the CI validator
  is what makes a bad bump visible.
- Existing installs do **not** follow a plugin rename. Everyone currently on `gsd`
  keeps a lineage that cannot host the capability until they act. Phase 8 owns that
  path; until it lands, this phase's change only helps new installs.
</risks>
