# /cairn:ui-phase

> Generate the UI design contract (UI-SPEC.md) for a frontend phase — GSD
> ui-phase, with its requirements tracked as stamped issues

## Usage

```text
/cairn:ui-phase [phase]
```

The phase number may be omitted upstream; when it is, the active phase is
resolved from STATE.md before any label is built.

## Why this wrapper exists

A UI-SPEC is a phase artifact with requirements in it — screens, states,
acceptance criteria — and those need issues like any other requirement. A design
contract nobody tracked is a contract nobody ships against.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight ui-phase`. Exit `6` or `5` stops.
2. **Claims** the phase's ids.
3. **Runs `/gsd:ui-phase`.**
4. **Every UI-SPEC requirement becomes an issue**, labelled
   `m-<milestone>,phase-<N>` (unpadded) with the `metadata.gsd` stamp.
5. **Closes what the contract settled**; releases and leaves open what it
   deferred — a screen postponed is not a screen finished.
6. **Refreshes and checks the map.**

Next: [/cairn:plan N](./plan.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/NN-UI-SPEC.md` — via `/gsd:ui-phase`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — claimed, created, closed or released

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
