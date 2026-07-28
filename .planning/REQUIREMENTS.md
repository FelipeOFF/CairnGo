# Requirements

Two milestones. v1.2 moves GSD to its official source and, in doing so, turns
on the fusion that has silently never run. v1.3 turns the status surface from
a row of phase numbers into a panel an operator can act on.

Research backing both: `.planning/research/gsd-core-migration.md` and
`.planning/research/status-phase-panel.md`.

## v1.2 — GSD Core: official source, working fusion

### GSD-01: cairn depends on the official GSD

The marketplace and plugin manifests source GSD from `open-gsd/gsd-core`
instead of `jnuyens/gsd-plugin`. The plugin name changes from `gsd` to
`gsd-core`, and every reference in commands, docs and scripts follows.

**Done when** a clean install of the marketplace pulls gsd-core, and no file
still points at the old source.

### GSD-02: the capability install is proven, not attempted

`/cairn:init` installs the cairn capability against gsd-core and **verifies**
it registered. The current code treats a missing `capability` subcommand as a
shrug (`|| echo "skipped"`), which is how the fusion came to be inactive for
every existing install without anyone noticing.

**Done when** a failed capability install is reported as a failure with what
to do about it, and the official validator runs in CI rather than skipping.

### GSD-03: doctor reports which GSD lineage is installed

`/cairn:doctor` names the installed GSD distribution and states whether the
capability is actually registered, so "the wrappers work but the fusion does
not" is visible instead of silent.

**Done when** doctor distinguishes gsd-core from the 4.x distribution and
fails, not warns, when the capability is absent while `.planning/` exists.

### GSD-04: an upgrade path for people already installed

Plugin dependencies resolve by name, so an existing install does not follow a
rename. The migration keeps the old entry for one release cycle alongside the
new one and documents the switch.

**Done when** a user on the old plugin gets a working path to gsd-core that
does not require deleting their setup, and the deprecation has a stated end.

### GSD-05: decide, one by one, what gsd-core brings

gsd-core ships 71 commands; 24 are unreferenced anywhere in cairn today
(`ns-*`, `onboard`, `phase`, `spec-phase`, `sketch`, `spike`, `thread`,
`workspace`, `workstreams`, `undo`, `graphify`, `mempalace-*` and others).

**Done when** each has an explicit decision recorded: wrapped as `/cairn:*`,
documented as "use the GSD command directly", or deliberately out of scope.
No wholesale wrapping.

## v1.3 — Status: a panel you can act on

### PANEL-01: the phase model carries what a phase is

`roadmap_phases()` returns phase numbers and completion and throws away title,
plan progress, dependencies and on-disk state. One model reads all of it and
feeds the terminal board, `--json` and the HTML board, so the three cannot
drift.

**Done when** a phase is described by title and plan progress everywhere it
appears, and the three surfaces are proven to render from the same model.

### PANEL-02: pending work is a described list

Pending phases stop being a row of ids. Each entry states what the phase is
about and where it stands (planned / executed / verified), so choosing what to
run next is informed rather than a guess at a number.

**Done when** an operator can pick the next phase without opening ROADMAP.md.

### PANEL-03: next commands, in cairn's namespace, with the reason for the order

A section lists the `/cairn:*` commands to run next and why in that order.
The next legal command per phase is derived from state on disk, and the
ordering comes from the roadmap's declared dependencies.

**Done when** the suggestion is computed from state rather than authored, and
the reason for the order is stated rather than implied.

### PANEL-04: what can run in parallel, said out loud

Phases whose dependencies are all satisfied are independent. The panel names
them and describes the split concretely, for example planning one phase while
another executes.

**Done when** the panel identifies independent phases and `/cairn:autonomous`
surfaces the order it chose instead of deciding silently.

### PANEL-05: the HTML board uses the screen it is opened on

The board is opened on a desktop. It fills the space with the material from
PANEL-02, PANEL-03 and PANEL-04 rather than leaving it empty.

**Done when** the board carries the phase list, the next commands and the
parallelism note, and its layout is verified at desktop widths.

## Out of scope, recorded so it is not lost

Pull-request and code-review state, and reconciliation against an external
tracker, both exist in the reference panel this was drawn from. They are not
in these milestones. The phase model should not make them harder to add.
