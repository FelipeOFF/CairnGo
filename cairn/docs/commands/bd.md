# /cairn:bd

> Run any beads (bd) command directly — raw passthrough

## Usage

```text
/cairn:bd <bd args…>
```

Everything after the command name is passed verbatim to the `bd` binary.

## What it does

Raw beads passthrough — **no cairn orchestration**. It runs:

```bash
bd $ARGUMENTS
```

and shows the output. That is the whole flow: no validation, no confirmation
layer, no extra bookkeeping.

This is the escape hatch for anything the cairn workflow verbs don't cover:
dependency surgery, priming, inspecting a single issue, ad-hoc queries — any
`bd` subcommand at all.

### What it does NOT do

Because nothing cairn-side wraps the call, **none of the cairn conventions are
applied**:

- no `m-<milestone>,phase-<N>` label pair
- no `gsd` metadata stamp
- no dedup check against existing stamped issues
- no map regeneration afterwards

An issue created through `/cairn:bd create …` is therefore invisible to the
phase maps and will surface as an orphan in [`/cairn:doctor`](doctor.md).
Use the workflow verbs ([`/cairn:plan`](plan.md), [`/cairn:work`](work.md),
[`/cairn:quick`](quick.md), [`/cairn:milestone`](milestone.md)) for anything
they already handle; keep this passthrough for operations they don't.

## Flags & arguments

| Argument | Meaning |
|---|---|
| `<bd args…>` | Positional, required. Passed verbatim to `bd` — subcommand, flags, and all. |

Every flag `bd` itself accepts works here (`--json`, `-l`, `--status`, …);
run `/cairn:bd help` for the full surface.

## Examples

```text
/cairn:bd dep add app-1 app-2
```

→ runs `bd dep add app-1 app-2`; app-1 now blocks on app-2. Dependency edges
are not something the workflow verbs manage ad hoc, so this is the right tool.

```text
/cairn:bd show app-7
```

→ runs `bd show app-7` and prints the issue's full detail (status, labels,
metadata, deps).

```text
/cairn:bd prime
```

→ runs `bd prime` to load the beads working context.

## Files touched

- **Reads/writes:** the bd database under `.beads/`, exactly as the invoked
  `bd` subcommand would. Read-only subcommands (`show`, `list`, `ready`)
  write nothing; mutating ones (`create`, `update`, `close`, `dep add`) write
  to the database with no cairn-side additions.
- Never touches `.planning/` or `.cairn/`.

## Related

- [`/cairn:gsd`](gsd.md) — the same escape hatch for GSD commands
- [`/cairn:ctx`](ctx.md) — the same escape hatch for context-mode operations
- [`/cairn:issues`](issues.md) — curated, phase-scoped issue listing
- [`/cairn:doctor`](doctor.md) — catches unstamped issues created through this passthrough
- [`/cairn:help`](help.md) — the full command map
