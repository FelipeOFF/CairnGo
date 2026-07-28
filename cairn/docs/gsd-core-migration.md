# Migrating to GSD Core

cairn's GSD dependency moved from the 4.x line (`jnuyens/gsd-plugin`, published
here as `gsd`) to the official **`open-gsd/gsd-core`**, published here as
`gsd-core`.

This is not a URL swap. It is what makes cairn's central feature work for the
first time.

## Why it matters

cairn's whole premise is that plain `/gsd:*` commands quietly create, claim,
close and gate bd issues, so tracking is not a second thing you have to
remember. That happens through a **GSD capability** — a bundle cairn registers
with GSD at `/cairn:init`.

The 4.x line has no capability system at all. Ask it to install one and it
answers `Error: Unknown command: capability`. So on that line the fusion never
existed: `/cairn:*` wrappers worked, the skill applied, and plain `/gsd:*` did
nothing to your issues.

Worse, `/cairn:init` ended that step with `|| echo "capability install
skipped"`, which turned the failure into a success. Nothing ever said a word.
Both halves are fixed: the source now points at a lineage that can host the
capability, and the install verifies itself instead of assuming.

## Do I need to do anything?

**New installs: no.** Installing cairn pulls `gsd-core` automatically.

**Existing installs: yes.** Plugin dependencies resolve by *name*, and the name
changed, so an existing install does not follow the rename on its own.

Check first:

```bash
/cairn:doctor
```

A `✗ gsd-capability` line means the fusion is not active and tells you which of
the two causes applies.

## Migrating

```bash
claude plugin install gsd-core@cairngo
/reload-plugins
/cairn:init          # re-registers the capability against gsd-core
/cairn:doctor        # must show ✓ gsd-capability
```

`/cairn:init` is idempotent — running it on an already-wired repo refreshes the
capability bundle and leaves everything else alone.

You can remove the old plugin once doctor is green:

```bash
claude plugin uninstall gsd@cairngo
```

Nothing in `.planning/` or `.beads/` changes. This is a plugin swap, not a data
migration.

## The deprecation window

The old `gsd` entry stays in this marketplace for **one release cycle** so
existing installs keep resolving while people migrate.

| | |
|---|---|
| Deprecated in | cairn v1.3 |
| **Removed in** | **cairn v1.4** |

After v1.4 the `gsd` entry is gone and an install still pointing at it will fail
to resolve. Migrate before then.

## What changed underneath

- The marketplace sources `open-gsd/gsd-core` **pinned to a release tag**
  (`ref: v1.8.0`). gsd-core's default branch is `next`, a development branch;
  an unpinned entry would ship unreleased code to every install. Bumping the pin
  is a deliberate, reviewable change.
- `/gsd:` stays the command namespace — gsd-core declares
  `"commands": "./commands/gsd/"` — so every `/cairn:*` wrapper that delegates to
  it keeps working, and nothing cairn references disappeared.
- `/cairn:init` now runs `scripts/cairn-capability.sh install`, which installs
  the bundle and then proves it registered: GSD's own `capability list` must
  report cairn `active`, and the staged bundle must carry the scripts its gates
  run. A failure is reported with its cause and fix, never as "skipped".
- `/cairn:doctor` gained a `gsd-capability` check, so a fusion that is off is
  visible on every routine health check rather than only at install time.

## Troubleshooting

**`✗ gsd-capability` right after migrating.** You probably have not re-run
`/cairn:init` since installing gsd-core, or the session has not reloaded
plugins. Run `/reload-plugins`, then `/cairn:init`.

**Doctor says "no GSD binary found" (⚠).** cairn looks for `gsd_run`/`gsd` on
PATH and then in the plugin cache. A ⚠ here means it could not tell either way,
not that the capability is missing. Confirm GSD is installed with
`claude plugin list`.

**The install is refused.** A `capabilities.strict_known_registries` lockdown
will block a third-party bundle. cairn still works through `/cairn:*` and the
skill; the fusion stays off until the policy allows it, and doctor keeps saying
so.
