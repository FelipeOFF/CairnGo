# /cairn:validate-phase

> Retroactively fill validation gaps on a completed phase — GSD
> validate-phase, and any issue the audit re-opens is re-opened in bd too

## Usage

```text
/cairn:validate-phase [phase number]
```

The phase number may be omitted upstream; when it is, it is resolved from
STATE.md before any label is built.

## Why this wrapper exists

It works on a **completed** phase, whose issues the ship gate has already
closed. When the audit re-opens work, bd has to follow — otherwise the gate keeps
reading the phase as done while someone is actively fixing it.

**The wrapper never re-opens on its own initiative.** Re-opening asserts that
finished work is unfinished, and that assertion belongs to the audit.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight validate-phase`. Exit `6` or `5`
   stops.
2. **Records the closed set** — the difference after the audit is what step 5
   acts on.
3. **Runs `/gsd:validate-phase`.**
4. **Gaps the audit found become issues**, labelled `m-<milestone>,phase-<N>`
   (unpadded) with the `metadata.gsd` stamp, then claimed.
5. **If — and only if — the audit re-opened phase work**, the matching issues
   are re-opened (`bd update <id> --status open`), each named with why. A phase
   the audit left intact gets no re-opens at all.
6. **Closes what the validation actually completed.** A gap merely recorded is
   not a gap filled; its issue stays open.
7. **Refreshes and checks the map**, so the record shows the re-opened work
   rather than the old clean sheet.

Next: [/cairn:verify N](./verify.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |
| `cairn-map` | `3` | map is stale (`--check`) |
| | `5` | `bd` unavailable — degrade, do not block |

## Files it touches

- `.planning/phases/*/` validation artifacts — via `/gsd:validate-phase`
- `.planning/phases/*/NN-BEADS-MAP.md` — regenerated
- bd issues — created, claimed, conditionally re-opened, closed

## See also

- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
