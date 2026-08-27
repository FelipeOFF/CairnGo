# /cairn:ultraplan-phase

> Offload planning to the ultraplan cloud and import it back — the imported plan lands as plan records that name the requirements they advance

## Usage

```text
/cairn:ultraplan-phase [phase-number]
```

## What it does

1. Split `$ARGUMENTS`
2. Record the phase's ids before the round trip
3. Claim
4. A plan the cloud invented with no issue behind it gets one
5. Close only what the planning genuinely finished
6. Refresh and check the map

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
