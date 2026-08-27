# /cairn:work

> Execute a phase — claim each plan record's beads, do the work, close the record with its summary and the beads with their reason

## Usage

```text
/cairn:work <phase-number> [--wave N] [--tdd]
```

## What it does

1. Acquire this phase's coordination lease before anything else
2. Read the plan off the beads
3. For each open plan record, in order — before starting it
4. Do the wave
5. Done check
6. Refresh the phase's map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh summary --phase <N>` (body on stdin), and the record lands on
the phase carrier — the plan record's `notes`; the record is closed (the bead count does not rise). A `.planning/` directory, when present,
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

- [`/cairn:verify`](verify.md) — what comes next
- [`/cairn:doctor`](doctor.md) — `planning-writes`, the guard on the old habit
