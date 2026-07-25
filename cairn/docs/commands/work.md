# /cairn:work

> Execute a phase — claim its beads, run GSD execute-phase, close on success

## Usage

```text
/cairn:work <phase-number>
```

The phase number is required. Labels use the **unpadded** phase number
(`phase-3`, never `phase-03`) — any leading zero is stripped from the
argument before building the label.

## What it does

1. **Claim before starting.** For each plan in the phase, before it starts:
   every id in that plan's `beads:` frontmatter gets
   `bd update <id> --claim`. `--claim` atomically assigns the issue to you
   **and** sets its status to `in_progress` in one call (no separate
   `--status` needed; idempotent if the issue is already yours).
2. **Run `/gsd:execute-phase <N>`** — the normal GSD execution flow.
3. **Close on verified success.** On a plan's successful completion **and**
   verification, its ids are closed:
   `bd close <id> --reason="<1–2 sentence summary>"`. Never at the end of raw
   execution — only after the work is verified.
4. **Done check.** When the milestone is known (ROADMAP.md's current
   milestone header, or STATE.md), the list is scoped with the label pair:
   `bd list -l m-<milestone>,phase-<N> --status open` — it should be empty
   when the phase is complete; anything still open is reported.
5. **Refresh the map** so it reflects the closes:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>
   ```

Next: [/cairn:verify N](./verify.md) or [/cairn:ship](./ship.md).

### Side effects

- bd claims (`--claim`) at plan start; bd closes with a `--reason` after
  verified success. Both are bd writes, so the plugin's PostToolUse hook
  fires on each (mirror push when sync is configured + phase-map refresh).
- `NN-BEADS-MAP.md` refreshed at the end.
- The plugin's **Stop hook** warns about issues still `in_progress` and
  assigned to the current actor at session end — a claim left dangling is
  surfaced, not lost.
- With the capability installed, plain `/gsd:execute-phase` performs the same
  claim (`execute:wave:pre`) and close (`execute:wave:post`) by itself — the
  duplicated side effect is expected and idempotent.
- No commits are made by the command itself (GSD's execute flow owns its own
  commit behavior).

## Flags & arguments

| Argument | Meaning |
|---|---|
| `<phase-number>` | required positional — the phase to execute |

## Examples

```text
/cairn:work 3
→ plan 03-01: bd update app-12 --claim (assigned + in_progress)
→ /gsd:execute-phase 3 … plan 03-01 complete + verified
→ bd close app-12 --reason="JWT auth middleware landed with tests"
→ done check: bd list -l m-v1.0,phase-3 --status open → empty
→ cairn-map.sh 3 refreshed · next: /cairn:verify 3
```

```text
/cairn:work 03       # leading zero in the argument
→ labels built as phase-3 (unpadded) — phase-03 would match nothing
```

## Files touched

- **Reads:** `PLAN.md` `beads:` frontmatter, ROADMAP.md / STATE.md (active
  milestone), bd state via `bd … --json`.
- **Writes:** `.beads/` via `bd update --claim` / `bd close`,
  `.planning/phases/<dir>/*-BEADS-MAP.md` (refresh).

## Related

- [/cairn:plan](./plan.md) — produces the plans and frontmatter this consumes
- [/cairn:verify](./verify.md) — cross-check GSD verification against beads
- [/cairn:ship](./ship.md) — the gate that requires these closes
- [/cairn:quick](./quick.md) — tracked side-quests discovered mid-phase
