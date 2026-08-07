# /cairn:reconcile

> Investigate a detected phase conflict and propose a cited reconciliation —
> proposes only, never applies

## Usage

```text
/cairn:reconcile <phase-number>
```

## The guarantee

This command **never touches bd state**. It writes exactly one file — a
proposal — for a separate, human-invoked step to act on. Applying anything is
[`/cairn:doctor --apply-reconciliation N`](./doctor.md), by a person, later.

## What it does

1. **Gate — only a real conflict is worth investigating.**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-status.sh" --json --planning-dir .planning
   ```
   The phase's `corroboration` key must read exactly `"conflict"`. Anything
   else and the command says there is nothing to investigate and **stops**.
   This gate is enforced twice: here, and mechanically inside the evidence
   gatherer itself — the bats-proven half, since a test cannot spawn the Task
   tool to prove a live run respects prose.
2. **Cache check — reuse a still-valid proposal.**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-reconcile.sh" collect <N> --json
   ```
   When a prior proposal's `evidence_hash` matches this run's, nothing the
   conflict cites has changed: the prior proposal is presented as-is, with zero
   new subagent spend.
3. **Investigates** by spawning the `reconcile-investigator` subagent, which
   holds **no** `Write`, `Edit`, `Bash` or `NotebookEdit` tool — it cannot
   write `.cairn/conflicts.json`, or anything else. It returns a JSON
   `{"claims": [...]}` and nothing more. See
   `cairn/agents/reconcile-investigator.md` for the full tool grant.
4. **Writes the proposal** — this command's own deterministic action, from
   values it already knows, never from anything the subagent said about them.
   The `evidence_hash` stamped is the one captured in step 2, never one read
   back from the subagent. A parse failure is a failed investigation: the raw
   text is reported and **nothing is written**.
5. **Verifies before anyone sees it.**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-reconcile.sh" verify <N>
   ```
   Exit `4` means at least one citation failed re-checking against the file it
   claims to quote — the failing citations are named and the command **stops**.
   An unverified proposal is never presented as trustworthy.
6. **Presents** each claim, its citations and its recommended action in plain
   language — never raw JSON — and names the apply command as the next step.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Proposal written and verified, or nothing to investigate |
| `2` | Usage |
| `3` | Not conflicted — nothing to investigate |
| `4` | A citation failed re-checking against the file it quotes |
| `5` | `bd` unavailable |

## Files it touches

- `.cairn/reconcile-evidence.json` — the collected evidence bundle
- `.cairn/conflicts.json` — the proposal, the one file this command writes

## See also

- [`/cairn:doctor`](./doctor.md) — `--apply-reconciliation N`, the separate,
  human-invoked step that acts on the proposal
- [`/cairn:status`](./status.md) — where a phase's `corroboration` verdict
  comes from
- [Command reference](../commands.md) — every `/cairn:` command
