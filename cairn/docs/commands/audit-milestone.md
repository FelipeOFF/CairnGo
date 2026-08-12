# /cairn:audit-milestone

> Audit a milestone against its original intent before archiving — GSD
> audit-milestone, reported against the same gate /cairn:milestone complete
> enforces

## Usage

```text
/cairn:audit-milestone [version]
```

Without an argument the milestone is resolved from ROADMAP.md's current
milestone header, or STATE.md.

## Why this wrapper exists

The audit's verdict has to be read next to what bd says, because
[`/cairn:milestone complete`](./milestone.md) **already refuses to archive over
a non-closed issue**. This wrapper points at that gate rather than
re-implementing it: two gates for one thing is the disease this project treats,
and a second one would drift from the first.

## What it does

1. **Preflight** — `cairn-wrap.sh preflight audit-milestone`. Exit `6` or `5`
   stops the command and prints the script's message verbatim.
2. **Resolves the milestone.**
3. **Reads the tracker's own view first**
   (`bd list -l m-<milestone> --all --limit 0 --json`), noting what is still
   open and under which `phase-<N>` label — so the audit is *compared against*
   it rather than believed on its own.
4. **Claims** the audit's own issue, when one exists.
5. **Runs `/gsd:audit-milestone`.**
6. **Reconciles the two verdicts and names every disagreement:**
   - the audit says a phase is incomplete while its issues are all closed;
   - the audit says the milestone is done while bd still has open issues.

   Neither is resolved by picking a side here. Both are reported with ids and
   phase numbers, and routed: the gate is
   [`/cairn:milestone complete`](./milestone.md), and drift between the planning
   files themselves is [`/cairn:doctor`](./doctor.md).
7. **A gap the audit found becomes an issue** — never a paragraph in a report
   nobody assigns — labelled `m-<milestone>,phase-<N>` with the **unpadded**
   number and the `metadata.gsd` stamp.
8. **Closes the audit's own issue with the verdict.** The gaps it found stay
   **open**: they are the work, not the audit of it. Nothing here closes a
   phase's issues; that is the gate's job.

Next: [/cairn:milestone complete](./milestone.md).

## Exit codes

| Source | Code | Meaning |
| --- | --- | --- |
| `cairn-wrap preflight` | `0` / `5` / `6` | installed / could not look / not there |

## Files it touches

- the milestone audit artifact — via `/gsd:audit-milestone`
- bd issues — read (both verdicts), gaps created, the audit's own issue closed

## See also

- [`/cairn:milestone`](./milestone.md) — the gate this reports against
- [`/cairn:doctor`](./doctor.md) — where planning-file drift is routed
- [Command reference](../commands.md) · [gsd-core commands](../gsd-core-commands.md)
