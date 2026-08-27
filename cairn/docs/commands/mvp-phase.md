# /cairn:mvp-phase

> Plan a phase as a vertical MVP slice — the plan recorded on beads, the tracer wave first, and the map reconciled

## Usage

```text
/cairn:mvp-phase <phase-number>
```

## What it does

1. Split `$ARGUMENTS`
2. Read the map and the carrier first
3. Claim
4. Cut the slice, and record it as plan records
5. A slice with no issue gets one
6. Work the MVP defers is released, not closed
7. Refresh and check the map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh plan --phase <N>` (body on stdin), and the record lands on
the phase carrier — one `plan-NN` bead per wave, a child of the carrier (`description` = the plan; `notes` = its summary, on close) (recording the same `NN` rewrites it). A `.planning/` directory, when present,
is a GSD project waiting to be imported, never a place this command writes;
`/cairn:doctor`'s `planning-writes` check names any document written there
after the import.

Each plan record **names the requirement ids it advances** — that name is the link [`/cairn:work`](work.md) resolves to bead ids through the map; there is no `beads:` frontmatter any more.

Read it back:

```bash
bd show <carrier> --json | jq -r '.description, .design, .acceptance_criteria, .notes'
bd list --parent <carrier> --json          # the plan records
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>
```

## Related

- [`/cairn:work`](work.md) — what comes next
- [`/cairn:doctor`](doctor.md) — `planning-writes`, the guard on the old habit
