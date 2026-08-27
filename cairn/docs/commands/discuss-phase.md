# /cairn:discuss-phase

> Gather phase context before planning — the decisions recorded on the phase carrier, and the phase's beads reconciled against them

## Usage

```text
/cairn:discuss-phase <phase> [--auto] [--assumptions]
```

## What it does

1. Split `$ARGUMENTS`
2. Read the phase's beads first
3. Find the facts yourself, then put the decisions to the user
4. Claim what you are about to move
5. Record the context on the carrier
6. Reconcile, and name every divergence
7. Close what the discussion actually settled
8. Refresh the map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh context --phase <N>` (body on stdin), and the record lands on
the phase carrier — `design`, section `## CONTEXT` (the other sections stay). A `.planning/` directory, when present,
is a GSD project waiting to be imported, never a place this command writes;
`/cairn:doctor`'s `planning-writes` check names any document written there
after the import.

Read it back:

```bash
bd show <carrier> --json | jq -r '.description, .design, .acceptance_criteria, .notes'
bd list --parent <carrier> --json          # the plan records
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>
```

## Related

- [`/cairn:plan`](plan.md) — what comes next
- [`/cairn:doctor`](doctor.md) — `planning-writes`, the guard on the old habit
