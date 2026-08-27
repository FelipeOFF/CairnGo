# /cairn:plan

> Plan a phase — context, research and one plan record per wave, all on beads

## Usage

```text
/cairn:plan <phase-number> [--research|--skip-research] [--tdd]
```

## What it does

1. Split `$ARGUMENTS`
2. Read what is already tracked
3. Context first, when there is none
4. Research what the plan depends on
5. Claim
6. Cut the phase into waves, one plan record each
7. Reconcile
8. Refresh and check the map

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
