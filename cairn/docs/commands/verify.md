# /cairn:verify

> Verify a phase's work — GSD verify-work cross-checked against beads

## Usage

```text
/cairn:verify [phase-number]
```

Labels use the **unpadded** phase number (`phase-3`, never `phase-03`) — any
leading zero is stripped from the argument before building the label.

## What it does

1. **Run `/gsd:verify-work <N>`** — the conversational GSD verification flow.
2. **Cross-check against beads.** Every issue for the phase is listed:
   - `bd list -l m-<milestone>,phase-<N>` when the milestone is known
     (ROADMAP.md's current milestone header),
   - else the fallback `bd list -l phase-<N>` — note that in legacy repos
     without `m-*` labels this can mix phases from different milestones.
   Every issue the work claims done should be **closed**.
3. **Flag and reconcile mismatches, in both directions:**
   - GSD-verified but the bd issue is still open → close the issue;
   - bd closed but GSD is not satisfied → reopen the work.
   Neither source silently overrides the other — the mismatch is surfaced
   and resolved.
4. **Refresh the phase's generated map:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>
   ```

### Side effects

- Any reconciliation touches bd (`bd close`, or status changes when work is
  reopened) — bd writes fire the plugin's PostToolUse hook (mirror push +
  map refresh) as usual.
- `NN-BEADS-MAP.md` refreshed at the end.
- With the capability installed, plain `/gsd:verify-work` triggers the same
  cross-check via the `verify:post` hook.
- No commits are made by the command itself.

## Flags & arguments

| Argument | Meaning |
|---|---|
| `[phase-number]` | positional — the phase to verify |

## Examples

```text
/cairn:verify 3
→ /gsd:verify-work 3 … UAT passed
→ cross-check: bd list -l m-v1.0,phase-3 → app-14 still open but
  GSD-verified → bd close app-14 --reason="verified in phase 3 UAT"
→ cairn-map.sh 3 refreshed · phase 3 consistent
```

```text
/cairn:verify 3      # bd closed, GSD not satisfied
→ mismatch: app-15 is closed in bd but verification failed its acceptance
  criterion → reopening the work; issue stays visible until re-verified
```

## Files touched

- **Reads:** ROADMAP.md (current milestone header), bd state via
  `bd list … --json`, the phase's VERIFICATION output from GSD.
- **Writes:** `.beads/` via `bd close` (reconciliation),
  `.planning/phases/<dir>/*-BEADS-MAP.md` (refresh).

## Related

- [/cairn:work](./work.md) — the execution step this verifies
- [/cairn:ship](./ship.md) — the gate that follows a clean verification
- [/cairn:plan](./plan.md) — where the phase's issue linkage was established
