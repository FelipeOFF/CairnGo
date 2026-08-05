# /cairn:secure-phase

> Retroactively verify a completed phase's threat mitigations — GSD
> secure-phase, and an unmitigated threat becomes a tracked issue rather than a
> note

## Usage

```text
/cairn:secure-phase [phase number]
```

The phase number may be omitted upstream; when it is, it is resolved from
STATE.md before any label is built.

## Why this wrapper exists

Same shape as [`/cairn:validate-phase`](./validate-phase.md), on a **completed**
phase — plus one thing specific to security work. **An unmitigated threat
recorded only as prose is how security findings die.** Every one of them leaves
this command as a tracked issue with an id someone can be assigned.

**The wrapper never re-opens on its own initiative.**

## What it does

1. **Preflight** — `cairn-wrap.sh preflight secure-phase`. Exit `6` or `5` stops.
2. **Records the closed set.**
3. **Runs `/gsd:secure-phase`.**
4. **Every unmitigated threat becomes an issue**, with the threat named in the
   title rather than "security fix", at raised priority, labelled
   `m-<milestone>,phase-<N>` (unpadded) with the `metadata.gsd` stamp.
5. **If — and only if — the audit re-opened phase work**, the matching issues
   are re-opened, each named with why.
6. **Closes only a mitigation that is verified**, with a reason that says **how**
   it was checked. "Looks fine" is the same silence in different words.
7. **Refreshes and checks the map.**

Next: [/cairn:verify N](./verify.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/` threat artifacts — via `/gsd:secure-phase`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — created, claimed, conditionally re-opened, closed

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
