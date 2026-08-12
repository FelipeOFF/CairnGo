# Migrating GSD lineages

Two migrations, in order. **v1.4** moved cairn's GSD dependency from the 4.x
line (`jnuyens/gsd-plugin`, published here as `gsd`) to the official
`open-gsd/gsd-core`. **v1.6** removed the dependency altogether and vendored the
runtime inside cairn — [jump to that chapter](#v16-the-plugin-dependency-is-gone-the-runtime-is-inside-cairn).

Everything above that heading describes the v1.4 move and is kept as written:
it is the precedent the v1.6 removal follows, and rewriting a precedent is
erasing it.

## v1.4: from the 4.x line to GSD Core

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

## The old `gsd` entry is gone

**As of cairn v1.4 the `gsd` marketplace entry no longer exists.** Nothing in
this marketplace publishes the 4.x line any more.

What that means in practice:

- **An install you already have keeps working.** Claude Code holds the plugin
  in its own cache, so a machine that installed `gsd@cairngo` before v1.4 still
  has it, still runs `/gsd:*`, and still has no capability system — the fusion
  was never active on that line.
- **`claude plugin install gsd@cairngo` no longer resolves**, and neither does
  a marketplace refresh that tries to re-fetch it. If you are on the old plugin
  and reinstall, or set up a new machine, that name is not there.

Either way the fix is the same migration below, and it leaves `.planning/` and
`.beads/` untouched. Run `/cairn:doctor` — a `✗ gsd-capability` line tells you
whether you still need to.

---

# v1.6: the plugin dependency is gone, the runtime is inside cairn

**As of cairn v1.6 the `gsd-core` marketplace entry no longer exists either,
and cairn declares no GSD plugin dependency at all.** The GSD planning runtime
is **vendored inside the plugin**, at `cairn/gsd/`.

This is the second time this marketplace has retired a GSD entry, and the
precedent is the chapter above: **the `gsd` 4.x entry was removed in v1.4**, by
this same path — the entry disappears, an install already on disk keeps working
from Claude Code's own cache, and `claude plugin install` stops resolving the
name. What was true then is true now, with one difference that matters: in v1.4
the answer was to install a *different* plugin. Now there is nothing to install.

## Why

cairn's premise was always that plain planning commands quietly create, claim,
close and gate bd issues. Until v1.6 that ran through a **GSD capability** — a
bundle cairn registered with an external `gsd-core`. Two plugins, one bridge.

The bridge was the problem. Two plugins version independently, and a machine
could end up with an old `/gsd:*` answering from a cached markdown-era release
while a new `/cairn:*` answered from bd. That window is the defect class the
entire v1.5 cycle chased. Removing the dependency removes the window: there is
one runtime, it ships with cairn, and it talks to bd directly.

## Do I need to do anything?

**New installs: no.** Installing cairn installs everything cairn needs.

**Existing installs: yes, and this is the half that is easy to skip.** Removing
the marketplace entry does not uninstall anything: your `gsd-core` is still on
disk, still answering `/gsd:*`, and now answering it with workflows that know
nothing about bd — beside a `/cairn:*` that does. Leaving it installed is worse
than useless.

Check first:

```bash
/cairn:doctor
```

A `✗ gsd-capability` line now means **an external GSD is still installed**, and
it names which. That check inverted in this release: it used to tell you to
install `gsd-core@cairngo`, and it now tells you to uninstall it.

## Migrating

```bash
claude plugin uninstall gsd-core@cairngo   # the id doctor named
claude plugin uninstall gsd@cairngo        # only if you still have the 4.x one
/reload-plugins
/cairn:doctor                              # must show ✓ gsd-capability
```

Doctor may then report a ⚠ for leftover capability state — `.gsd/capabilities/
cairn/` and `.gsd-capabilities.json`, staged by a `/cairn:init` from before this
release. Nothing reads those files any more. Remove exactly what it names:

```bash
rm -rf .gsd/capabilities/cairn .gsd-capabilities.json
```

It is a warning and not a failure on purpose: leftover files are friction, not a
broken repo, and cairn never deletes them for you.

**Nothing in `.planning/` or `.beads/` changes.** This is a plugin swap, not a
data migration — the same guarantee the v1.4 migration made, and this time it is
asserted by a test rather than promised in prose
(`tests/cairn-standalone.bats`, "a troca não move nada em .planning/ fora da
própria fase, nem em .beads/").

## The capability is archived

The bundle at `cairn/capability/` is no longer installed by `/cairn:init` and no
longer required by `/cairn:doctor`. It stays in the repository, with
`cairn/capability/ARCHIVED.md` recording why, what replaced each of its five
contributions, and what its physical removal would touch.

The one piece of it that never depended on a plugin host — the blocking ship
gate — is unchanged: it runs from git's own `pre-push` hook.

## What changed underneath

- `.claude-plugin/marketplace.json` publishes one plugin, `cairn`.
  `cairn/.claude-plugin/plugin.json` lists one dependency, `context-mode`.
- `cairn/gsd/` carries the runtime closure phase 32 derived from
  `open-gsd/gsd-core@v1.10.0` — 8 workflows and their transitive references,
  with `cairn/gsd/LICENSE` carrying upstream's MIT intact and
  `cairn/gsd/MANIFEST.json` listing every file, derived by
  `cairn-inventory.sh closure --json` rather than typed.
- The thirteen `/cairn:*` commands that used to wrap a `/gsd:*` command stopped
  wrapping. One (`discuss-phase`) delegates to the vendored workflow; the other
  twelve carry their deliverable contract in the command file itself. Each
  declares which in its `implementation:` frontmatter. See
  [what gsd-core brings](./gsd-core-commands.md) for the split and its known
  ceiling.
- `/cairn:gsd` survives as a passthrough for anyone who keeps an external GSD
  installed for their own reasons. On a clean cairn install `/gsd:*` does not
  resolve and it has nothing to reach.

## Troubleshooting (v1.6)

**`✗ gsd-capability` says the vendored runtime is incomplete.** That is a defect
of the cairn install, not of your machine, and no external plugin can supply it:
`claude plugin install cairn@cairngo`, then `/reload-plugins`.

**`/gsd:*` stopped working after uninstalling.** Expected. The `/cairn:*`
namespace is the whole loop now: `/cairn:new`, `/cairn:plan N`, `/cairn:work N`,
`/cairn:verify N`, `/cairn:ship`. `/cairn:help` lists them.

**The gsd-core manifest defect below no longer applies to you** once gsd-core is
uninstalled — cairn does not ship, load, or patch that plugin any more. The
section is kept because it documents a real upstream defect and the reasoning
that produced the repair, and `cairn-capability.sh repair-manifest` still exists
for anyone running gsd-core on their own.

---

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

**`claude plugin list` reports a hook error on gsd-core.** You will probably
see this after installing gsd-core 1.8.0:

```
gsd-core@gsd-core
  Error: Hook load failed: Duplicate hooks file detected:
  ./hooks/hooks.json resolves to already-loaded file …/hooks/hooks.json.
```

**cairn repairs this for you, and you should not see it.** `/cairn:init` clears
the defect before installing the capability, and `/cairn:doctor` re-checks it. If
you do see it, run:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-capability.sh" repair-manifest
```

then `/reload-plugins` — Claude Code has already decided the plugin failed for
this session, and only a reload changes that.

### What the defect actually is

gsd-core's `plugin.json` declares `"hooks": "./hooks/hooks.json"`, and Claude
Code loads that standard path automatically. The declaration is therefore a
duplicate, and the loader does not merely skip the hooks — it **refuses the whole
plugin**:

```
Status: ✘ failed to load
```

So the severity is higher than the message suggests: **there are no `/gsd:*`
commands at all**. What hides it is that the `gsd-tools` CLI keeps working, so
cairn's capability still installs and registers happily against a plugin Claude
Code will not load. Measured both ways on the same install: with the line,
`✘ failed to load`; without it, `✔ enabled`.

### Why cairn patches instead of forking

The repair removes exactly one line from the copy already on your disk. You keep
receiving genuine upstream code — cairn does not fork, vendor or re-publish
gsd-core, and there is no 41 MB tree to rebase against a weekly release cadence.
It is narrow by design: it only removes a declaration that names the *standard*
path. A manifest pointing at *additional* hook files is using the field
correctly and is never touched.

A gsd-core update restores the original file, so the defect can come back; that
is why `/cairn:doctor` checks it on every run rather than trusting a one-time
fix.

### Upstream

The one-line fix already exists as
[open-gsd/gsd-core#2077](https://github.com/open-gsd/gsd-core/pull/2077). It was
closed twelve seconds after opening, by automation rather than on merit: the
project requires a maintainer-approved issue before any PR, and no such issue
exists. The declaration is still present on `main`, `next` and `v1.8.0`.

When it lands, this repair becomes a no-op on its own — the field it looks for
will not be there — and cairn can drop the code.
