# /cairn:plan-review-convergence

> Replan until cross-AI review concerns are resolved — the plan records rewritten, the convergence log on the carrier, the requirement linkage re-resolved after every rewrite

## Usage

```text
/cairn:plan-review-convergence <phase> [--codex] [--gemini] [--claude] [--opencode] [--ollama] [--lm-studio] [--llama-cpp] [--agy] [--all] [--max-cycles N]
```

## What it does

1. Split `$ARGUMENTS`
2. Record the linkage before the first cycle
3. Claim
4. Rewrite until the review closes
5. Re-resolve the requirement linkage on every record that now exists
6. A concern the review raised that no issue covers becomes one
7. Close only what convergence settled
8. Refresh and check the map

## The record

Nothing this command produces is a file. It records through one boundary,
`cairn-record.sh plan --phase <N>` (body on stdin), and the record lands on
the phase carrier — one `plan-NN` bead per wave, a child of the carrier (`description` = the plan; `notes` = its summary, on close) (recording the same `NN` rewrites it). A `.planning/` directory, when present,
is a GSD project waiting to be imported, never a place this command writes;
`/cairn:doctor`'s `planning-writes` check names any document written there
after the import.

It also appends the convergence log to the carrier's `notes` (`cairn-record.sh review`), one row per cycle.

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
