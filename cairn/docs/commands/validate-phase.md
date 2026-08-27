# /cairn:validate-phase

> Retroactively fill validation gaps on a completed phase — the verification recorded on the carrier, and any issue the audit re-opens re-opened in bd too

## Usage

```text
/cairn:validate-phase [phase number]
```

## What it does

1. Split `$ARGUMENTS`
2. Record the closed set
3. Write the validation record and record it
4. Gaps the audit found become issues
5. If — and only if — the audit re-opened phase work
6. Close what the validation actually completed
7. Refresh and check the map

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

- [`/cairn:verify`](verify.md) — what comes next
- [`/cairn:doctor`](doctor.md) — `planning-writes`, the guard on the old habit
