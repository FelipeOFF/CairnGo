# Migration to the official GSD: open-gsd/gsd-core

Findings from a direct inspection of `https://github.com/open-gsd/gsd-core`
at v1.8.0, compared against what cairn ships and what it currently depends on.
Everything below was checked against a clone, not inferred from docs.

## The three names problem

| | plugin name | plugin version | package.json |
|---|---|---|---|
| current dependency | `gsd` | 4.3.1 | `gsd-plugin` 2.45.0 |
| official | `gsd-core` | 1.8.0 | `gsd-core` |

The marketplace entry sources `jnuyens/gsd-plugin`. The official project is a
different lineage with its own versioning, not a newer release of the same
package.

## cairn was already written against the official one

`cairn/capability/capability.json` declares `engines: {gsd: ">=1.8.0"}`, which
matches gsd-core's numbering and not the 4.x line it is installed against.
The capability's `fragments/` are named for gsd-core's hook points and match
one-for-one:

    plan-post.md · execute-wave-pre.md · execute-wave-post.md · verify-post.md

gsd-core carries 20 capabilities with `role: feature`, the same shape cairn
uses, plus 19 with `role: runtime` (host adapters: cline, cursor, copilot,
windsurf, codex, gemini and friends). None of the 39 touches beads, so cairn's
niche is unoccupied.

**Verified, not assumed:** `tests/capability.bats` already contains a
`gsd-core validateCapability` test that skips when the validator is absent.
Run against a built checkout it passes:

    GSD_CORE_DIR=/path/to/gsd-core bats tests/capability.bats -f validateCapability

(The clone needs `npm install && npm run build:lib` first; without it the CLI
reports the runtime library is not built.)

## The finding that outranks the migration

`gsd-tools` in the 4.3.1 distribution has **no `capability` command**. Its
command list ends at `workstream`/`worktree`; there is no `capability install`.

So `/cairn:init`'s capability install has been taking its own fallback branch
(`|| echo "capability install skipped"`) on every run. Anyone who installed
the marketplace has the `/cairn:*` wrappers working but **not** the fusion the
plugin is built around, where plain `/gsd:*` claims, closes and gates bd
issues.

Pointing at the official repo is not source hygiene. It is what makes the
central feature exist for the first time.

## Commands

gsd-core ships 71 commands under `commands/gsd/`, so the namespace stays
`/gsd:` and every `/cairn:*` wrapper that delegates to it stays valid. Nothing
cairn references has disappeared. Commands present in the official tree and
not currently mentioned anywhere in cairn's docs or wrappers include:

    ns-context ns-ideate ns-manage ns-project ns-review ns-workflow
    onboard phase plan-review-convergence pr-branch profile-user
    spec-phase sketch spike surface thread ultraplan-phase undo
    workspace workstreams graphify mempalace-capture mempalace-recall

These are candidates for new `/cairn:*` wrappers or for explicit "use the GSD
command directly" notes, decided one by one rather than wrapped wholesale.

## Upgrade path for people who already installed

The dependency resolves by plugin **name**, and the name changes from `gsd` to
`gsd-core`. An existing install therefore does not update transparently. This
needs a deliberate path, not a URL swap: most likely keeping the old entry for
one release cycle alongside the new one, with a migration note, and a check in
`/cairn:doctor` that reports which GSD lineage is installed and whether the
capability actually registered.

Open question for that phase: whether `/cairn:init` should detect the 4.x
distribution and tell the user the fusion is inactive, since today it says
nothing and the failure is silent.
