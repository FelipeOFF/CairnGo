# /cairn:spec-phase

> Clarify WHAT a phase delivers, with ambiguity scoring — the SPEC recorded on the phase carrier, and every requirement it names a stamped issue

## Usage

```text
/cairn:spec-phase <phase> [--auto]
```

## What it does

1. Split `$ARGUMENTS`
2. Read what is tracked
3. Write the SPEC and record it
4. Turn the SPEC's requirements into issues
5. Refresh and check the map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh spec --phase <N>` (body on stdin), and the record lands on
the phase carrier — `design`, section `## SPEC` (context stays). A `.planning/` directory, when present,
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

- [`/cairn:discuss-phase`](discuss-phase.md) — what comes next
- [`/cairn:doctor`](doctor.md) — `planning-writes`, the guard on the old habit
