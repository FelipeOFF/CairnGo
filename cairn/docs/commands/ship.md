# /cairn:ship

> Ship — verify every completed phase's beads are closed, then GSD ship / push

## Usage

```text
/cairn:ship
```

No arguments. A deterministic pre-ship gate, then the actual ship.

## What it does

1. **Run the deterministic gate first:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-gate.sh"
   ```
   - Exit `6` — **blocked**: the gate lists the offending issue ids. Stop and
     report; do not push.
   - Exit `5` — bd unavailable: warn, then check manually (below).
   - If the script itself is unavailable, check by hand: for each completed
     phase `N`, `bd list -l m-<milestone>,phase-<N> --all` must show no
     non-closed issue (milestone from ROADMAP.md's current milestone header;
     **any status other than `closed`** — open, in_progress, blocked,
     deferred — blocks). If anything is non-closed, **stop** and report it —
     do not push.
2. **Ship.** When all completed phases are clean, run `/gsd:ship` to finalize
   — it handles the push. If the project doesn't use `/gsd:ship`, push the
   branch directly.

The invariant: **never push with non-closed issues on a phase marked done.**

### Enforcement beyond this command

The same gate is enforced at two other layers, so it holds even when this
command is skipped:

- The **git pre-push shim** installed by [/cairn:init](./init.md) re-runs
  `cairn-gate.sh` outside any LLM. It blocks **only** on gate exit 6; exit 5
  (bd unavailable) warns and lets the push through, because an availability
  failure is not a gate failure.
- The installed GSD capability applies the same blocking check at `ship:pre`
  when plain `/gsd:ship` is used.

### Side effects

- None of its own: the gate is read-only, and the push (plus anything else —
  PR creation, tags) belongs to `/gsd:ship` or to the direct `git push`.

## Flags & arguments

None.

## Exit codes

These belong to `cairn-gate.sh`:

| Code | Meaning |
|---|---|
| `0` | gate clean — every completed phase's issues are closed |
| `5` | bd unavailable — warn, then check manually (the pre-push shim lets the push through on this code) |
| `6` | **blocked** — non-closed issues on a completed phase; ids are listed |

## Examples

```text
/cairn:ship
→ cairn-gate.sh: OK (phases 1–3 complete, all issues closed)
→ /gsd:ship … pushed
```

```text
/cairn:ship
→ cairn-gate.sh exited 6 — blocked:
    phase-2: app-9 (in_progress), app-11 (open)
→ stopping: close or carry these before shipping (see /cairn:work,
  /cairn:milestone complete for carry-over)
```

## Files touched

- **Reads:** ROADMAP.md (completed phases, current milestone header), bd
  state via `bd list … --json`.
- **Writes:** nothing directly — the push is delegated to `/gsd:ship` or git.

## Related

- [/cairn:work](./work.md) — closes the issues this gate requires
- [/cairn:verify](./verify.md) — reconcile mismatches before gating
- [/cairn:milestone](./milestone.md) — `complete` runs this same gate first
- [/cairn:init](./init.md) — installs the pre-push shim that mirrors the gate
