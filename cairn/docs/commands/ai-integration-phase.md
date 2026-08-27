# /cairn:ai-integration-phase

> Record the AI design contract for a phase that builds an AI system — the AI-SPEC on the phase carrier, with its requirements and evals tracked

## Usage

```text
/cairn:ai-integration-phase [phase number]
```

## What it does

1. Split `$ARGUMENTS`
2. Read the map and the carrier
3. Write the AI-SPEC and record it
4. Every AI-SPEC requirement gets an issue
5. Refresh and check the map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh ai-spec --phase <N>` (body on stdin), and the record lands on
the phase carrier — `design`, section `## AI-SPEC` (the other sections stay). A `.planning/` directory, when present,
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
