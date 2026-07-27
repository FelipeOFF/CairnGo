# /cairn:help

> Show the cairn unified command interface (one namespace for GSD + beads)

## Usage

```
/cairn:help
```

No arguments.

## What it does

1. Prints the full command map — `/cairn:` is the single interface over the
   whole GSD↔beads↔context-mode workflow — grouped exactly as below:
   - **SETUP** — `init`, `new`
   - **LOOP** — `plan <N>`, `work <N>`,
     `quick <desc> [--full/--discuss/--research/--validate]`, `verify <N>`,
     `ship`, `milestone <op>`
   - **VIEW** — `status`, `progress`, `issues [N]`
   - **MIGRATE & HEALTH** — `migrate`, `doctor`
   - **MEMORY** (context-mode, on by default) — `remember`, `recall`,
     `context-config`
   - **SYNC** (optional) — `sync-config`, `sync-pull`
   - **ESCAPE HATCHES** (raw passthrough) — `bd <args…>`, `gsd <cmd>`,
     `ctx <op>`
2. Suggests the obvious next step for the repo's current state:
   - no `.planning/` and no `.beads/` → `/cairn:new`
   - exactly one of the two present → `/cairn:migrate`
   - both present → `/cairn:status`

No scripts run and nothing is written — it is a printed map plus one routing
suggestion.

## Flags & arguments

None.

## Examples

```
/cairn:help
```

```text
SETUP
  /cairn:init             ensure GSD + beads, wire git + bd init, then hand off
  /cairn:new              new project: /gsd:new-project + stamped bd issues + generated maps
LOOP
  /cairn:plan  <N>        plan phase N  (GSD plan-phase + regenerate/reconcile beads map)
  …
Both .planning/ and .beads/ found → try /cairn:status
```

## Files touched

- **Reads:** presence of `.planning/` and `.beads/` (routing only)
- **Writes:** nothing

## Gotchas

- **The map lives in two places.** The printed map is duplicated literally in
  `cairn/README.md` — any change to a command line must be mirrored in both,
  or they drift.

## Related

- [/cairn:new](new.md) — the route for an empty repo
- [/cairn:migrate](migrate.md) — the route for a half-wired repo
- [/cairn:status](status.md) — the route for a fully wired repo
- [/cairn:init](init.md) — one-command setup underneath `new`
