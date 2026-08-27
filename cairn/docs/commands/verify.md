# /cairn:verify

> Verify a phase's work — every plan record's summary checked against the code and the beads, the verdict recorded on the carrier

## Usage

```text
/cairn:verify [phase-number]
```

## What it does

1. Read the claim and the evidence
2. Cross-check against beads
3. Record the verdict on the carrier
4. Refresh the phase's map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh verification --phase <N>` (body on stdin), and the record lands on
the phase carrier — `acceptance_criteria` (replaced on every run). A `.planning/` directory, when present,
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

- [`/cairn:ship`](ship.md) — what comes next
- [`/cairn:doctor`](doctor.md) — `planning-writes`, the guard on the old habit
