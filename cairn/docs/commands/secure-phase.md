# /cairn:secure-phase

> Retroactively verify a completed phase's threat mitigations — the security review recorded on the carrier, and an unmitigated threat a tracked issue rather than a note

## Usage

```text
/cairn:secure-phase [phase number]
```

## What it does

1. Split `$ARGUMENTS`
2. Record the closed set
3. Write the security review and record it
4. Every unmitigated threat becomes an issue
5. If — and only if — the audit re-opened phase work
6. Close only a mitigation that is verified
7. Refresh and check the map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh review --phase <N>` (body on stdin), and the record lands on
the phase carrier — `notes`, appended and dated (audits accumulate). A `.planning/` directory, when present,
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
