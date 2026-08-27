# /cairn:jira

> Link this cycle to Jira — Story ↔ milestone, Sub-task ↔ phase, 1:1, written to the bead's external_ref; the only door that talks to the Atlassian MCP

## Usage

```text
/cairn:jira link [KEY] [--milestone vX.Y | --phase N]
/cairn:jira unlink (--milestone vX.Y | --phase N)
/cairn:jira links
/cairn:jira flush
/cairn:jira audit
```

With no verb, `links`.

## The model

| Jira | cairn | where the link lives |
|---|---|---|
| Epic | — (bigger than a cycle) | `metadata.gsd.jira.epic` on the milestone carrier, cached from the story's parent |
| Story | milestone | `external_ref: jira-<KEY>` on the **milestone carrier** |
| Sub-task | phase | `external_ref: jira-<KEY>` on the **phase carrier** |
| — | requirement (`CAT-NN`) | none — the board shows the phase's `⧉` for display only |

One card per bead, one bead per card. `.cairn/id-map.json` is a per-machine
cache that `gbsync` derives from `external_ref` (`gbsync.sh refresh-map`);
the bead always wins over the file.

## What it does

**`link`** resolves the target (flag, else the leased phase, else the open
milestone), detects the key — carrier title/description and branch name are
strong, recent commits are a suggestion, a typed key is accepted — fetches
the card through the Atlassian MCP, **shows** key/type/status/summary/parent,
confirms once, saves the card JSON verbatim under `.cairn/cache/`, and writes
with the script:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-jira.sh" link \
  --from-json <card.json> (--milestone vX.Y | --phase N) [--json]
```

The script decides; exit codes: `0` linked / already linked · `2` the type
does not fit the target (Story ↔ milestone, Sub-task ↔ phase, nothing else) ·
`3` refused — the carrier already carries another `external_ref` (`unlink`
first), or the key is already another bead's (both ids printed) · `4` no
carrier · `5` no bd. A Sub-task under a story that is not the cycle's links
with a warning; the doctor calls it drift.

**Creation is the only Jira write that always asks.** An Epic key lists its
stories and asks which one is the cycle; none → offer a new Story under the
epic. A phase with no Sub-task → offer one under the cycle's story. No MCP
and no token → "create it in Jira and come back with the key".

**`unlink`** clears the ref and the cached epic; Jira is untouched.
**`flush`** sends the mirror writes the scripts queued on beads when no token
was in the shell (`metadata.gsd.mirror.pending`: a close → transition, an
update → title/description, a comment → comment) through the MCP,
automatically, then clears the queue with `cairn-jira.sh pending --clear`.
**`links`** prints story, epic and one sub-task per phase. **`audit`** runs
the doctor and routes its `milestone-carrier` and `jira-links` findings;
`jira-links` is out-of-scope until `.cairn/sync.json` has a `jira` backend.

## The MCP contract

Loaded per session with one `ToolSearch`; the command names `getJiraIssue`,
`searchJiraIssuesUsingJql` and `createJiraIssue` and the fields it reads from
each. Scripts never call the MCP: headless runs read the saved JSON, the REST
adapter (`JIRA_EMAIL` / `JIRA_API_TOKEN` in the shell), or the bead alone.
The card shape the script accepts is a subset of Jira's REST shape — the
fixtures under `tests/fixtures/jira/` are the contract.

## Related

- [`/cairn:sync-config`](sync-config.md) — the `jira` backend in `.cairn/sync.json`
- [`/cairn:doctor`](doctor.md) — `milestone-carrier` and `jira-links`
- [`/cairn:status`](status.md) — the `⧉ KEY` on the cycle and its phases
