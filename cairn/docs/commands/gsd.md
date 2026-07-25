# /cairn:gsd

> Run any GSD command directly — raw passthrough

## Usage

```text
/cairn:gsd <gsd-command> [args…]
```

The first token is the GSD command name; the rest are its arguments.

## What it does

Raw GSD passthrough — **no cairn orchestration**. It invokes:

```text
/gsd:$ARGUMENTS
```

So `/cairn:gsd debug` runs `/gsd:debug`, `/cairn:gsd new-milestone` runs
`/gsd:new-milestone`, and so on. That is the entire flow — cairn adds nothing
on top.

This is the escape hatch for the long tail of GSD commands the cairn workflow
verbs don't wrap (debugging, settings, stats, threads, spikes, …). The cairn
verbs wrap only the core loop: [`/cairn:new`](new.md) wraps `new-project`,
[`/cairn:plan`](plan.md) wraps `plan-phase`, [`/cairn:work`](work.md) wraps
`execute-phase`, [`/cairn:verify`](verify.md) wraps `verify-work`,
[`/cairn:ship`](ship.md) wraps `ship`, [`/cairn:milestone`](milestone.md)
wraps `new-milestone` / `complete-milestone`, and
[`/cairn:progress`](progress.md) wraps `progress`.

### Beads bookkeeping

There is **no additional beads bookkeeping** beyond what the installed cairn
capability already does on its own. The capability hooks the core GSD verbs
(e.g. claim/close around `/gsd:execute-phase`), so those behave the same
whether invoked directly or through this passthrough. Everything else runs as
plain GSD.

Prefer the cairn verb when one exists — it layers the beads conventions
(label pair, metadata stamp, gates, map refresh) that the raw GSD command
alone does not guarantee. In particular, never run `new-project` or
`new-milestone` through this passthrough on a repo with an existing
`.planning/` — that path belongs to [`/cairn:migrate`](migrate.md).

## Flags & arguments

| Argument | Meaning |
|---|---|
| `<gsd-command>` | Positional, required. The GSD command name, without the `/gsd:` prefix. |
| `[args…]` | Passed through as the GSD command's own arguments. |

## Examples

```text
/cairn:gsd debug
```

→ runs `/gsd:debug` — systematic debugging with persistent state; no cairn
wrapper exists for it.

```text
/cairn:gsd help
```

→ runs `/gsd:help` and prints the GSD command guide (distinct from
[`/cairn:help`](help.md), which prints the cairn map).

```text
/cairn:gsd stats
```

→ runs `/gsd:stats` for project statistics from `.planning/`.

## Files touched

- Whatever the invoked GSD command touches — typically `.planning/`
  (STATE.md, ROADMAP.md, phase dirs). The passthrough itself adds no reads or
  writes; any beads writes come only from the installed capability's own
  hooks on the core verbs.

## Related

- [`/cairn:bd`](bd.md) — the same escape hatch for beads commands
- [`/cairn:ctx`](ctx.md) — the same escape hatch for context-mode operations
- [`/cairn:help`](help.md) — the cairn command map (which verbs wrap what)
- [`/cairn:migrate`](migrate.md) — the safe path for repos with existing `.planning/`
