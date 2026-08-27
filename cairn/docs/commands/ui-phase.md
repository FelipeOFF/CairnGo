# /cairn:ui-phase

> Record the UI design contract for a frontend phase — the UI-SPEC on the phase carrier, with its requirements tracked as stamped issues

## Usage

```text
/cairn:ui-phase [phase]
```

## What it does

1. Split `$ARGUMENTS`
2. Read the map and the carrier
3. Write the UI-SPEC and record it
4. Every UI-SPEC requirement gets an issue
5. Refresh and check the map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh ui-spec --phase <N>` (body on stdin), and the record lands on
the phase carrier — `design`, section `## UI-SPEC` (the other sections stay). A `.planning/` directory, when present,
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
