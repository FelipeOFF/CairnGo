---
description: Link this cycle to Jira — Story ↔ milestone, Sub-task ↔ phase, 1:1, written to the bead's external_ref; the only door that talks to the Atlassian MCP
argument-hint: <link [KEY] [--milestone vX.Y | --phase N] | unlink (--milestone vX.Y | --phase N) | links | audit>
group: sync
---

Link cairn's cycle to Jira under the `cairn` conventions. `$ARGUMENTS` picks
the verb; with none, run `links`.

**The link IS the bead.** A milestone carrier linked to a Story carries
`external_ref: jira-<KEY>`; a phase carrier linked to a Sub-task carries the
same field. That field travels with Dolt, the board renders it as `⧉ KEY`,
the doctor audits it, and `.cairn/id-map.json` is a per-machine cache gbsync
derives from it. Nothing else records a link — not a document, not a config
file. The hierarchy is fixed: **Epic > Story ↔ milestone > Sub-task ↔ phase**,
one card per bead and one bead per card. Requirement beads (`CAT-NN`) have no
card of their own; the board shows them their phase's `⧉` for display only.

**This command is the only place that talks to the Atlassian MCP**, and only
because it runs in a session. Every script under `scripts/` is headless: it
reads the card from a JSON file this command saved, or from the REST adapter
with a token, or from the bead alone. Never make a script call the MCP.

## The MCP contract

Before the first MCP call, load the tools with one `ToolSearch`
(`select:` the names below, comma-separated) — the Atlassian server is
deferred and its tools have no schema until fetched. If the search returns
only `authenticate` / `complete_authentication`, the server is declared but
not signed in: say so and take the **no MCP** route below. Do not guess at
tool names beyond these; when the server renames one, the search result is
the truth and this table is what to update.

| Need | Tool | Fields read |
|---|---|---|
| one card by key | `getJiraIssue` (`issueIdOrKey`) | `key`, `fields.summary`, `fields.status.name`, `fields.issuetype.name`, `fields.issuetype.subtask`, `fields.parent.key`, `fields.parent.fields.issuetype.name` |
| the stories of an epic | `searchJiraIssuesUsingJql` (`jql: parent = <EPIC> AND issuetype = Story`) | per issue: the same fields |
| a missing card | `createJiraIssue` (`projectKey`, `issueTypeName`, `summary`, `description`, `parent`) | `key` of the created issue |

Both site and project come from `.cairn/sync.json` when it has a `jira`
backend (`/cairn:sync-config`); without one, the site is whichever the MCP is
signed into, and the key's own prefix names the project. Save what the MCP
returns **verbatim**, as a subset of Jira's REST shape, to a file under
`.cairn/cache/jira-<KEY>.json` — that file is what the script reads, and the
bats fixtures under `tests/fixtures/jira/` are examples of exactly that shape.

## `link [KEY] [--milestone vX.Y | --phase N]`

1. **Resolve the target.** `--milestone` or `--phase` when given; otherwise
   the phase whose lease this checkout holds
   (`cairn-lease.sh status --json`), else the open milestone
   (`cairn-status.sh --json` → `milestone`). Say which one you picked.
2. **Detect the key — do not ask for it first.** Four signals, in this
   precedence, and the first two are the strong ones:
   - the target carrier's **title or description** (`bd show <carrier>
     --json`) — a `PROJ-123` token there was put there on purpose;
   - the **branch name** (`git branch --show-current`) — strong for the phase
     being executed, since `feat/DTP-142/...` names its card;
   - **recent commits** (`git log -20 --format=%s`) — weak: a key seen there
     is a *suggestion*, never a pick;
   - the **argument** `KEY` when the user typed one.
   One key across the strong signals → propose it. Strong signals that
   disagree, or only weak ones → put the candidates to the user with
   `AskUserQuestion`, each with where it was seen. No signal at all → ask for
   the key, or offer to create the card (step 5).
3. **Show the evidence before writing anything.** Fetch the card
   (`getJiraIssue`) and print what it is: key, type, status, summary, and its
   parent (an Epic for a Story, a Story for a Sub-task). Then confirm
   **once** (`AskUserQuestion`: link / pick another / cancel). Never write on
   the strength of a detection alone — a wrong link is a wrong card moved to
   Done later, by automation, in someone else's tracker.
4. **Write with the script, never by hand:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-jira.sh" link \
     --from-json .cairn/cache/jira-<KEY>.json (--milestone vX.Y | --phase N)
   ```
   The script is the one that decides. Read its exit code and relay its
   line, verbatim:
   - `0` — linked (or already linked, idempotent). A Story's Epic is cached on
     the milestone carrier (`metadata.gsd.jira.epic`). A Sub-task hanging
     under a story that is not the cycle's prints a **warning** — it is
     linked anyway, and `/cairn:doctor` will call it drift.
   - `2` — **the type does not fit**: a Story on a phase, a Sub-task on a
     milestone, a Task or Bug anywhere. Say the type the script read and
     stop; the fix is in Jira (or a different card), not here.
   - `3` — **refused**: the carrier already carries a different
     `external_ref` (another `jira-KEY`, or a `gh-N` the doctor's
     `--link-refs` wrote) → offer `unlink` then `link`, as two explicit
     writes; or the key is **already linked to another bead** → the script
     names both ids. Put that to the user: *which bead is this card really
     about?* Keep that one, and offer to create another card (step 5) for the
     other — a 1:1 that is violated is resolved by adding a card, never by
     sharing one.
   - `4` — no carrier to write on: a phase without one, or a cycle without
     exactly one (`/cairn:doctor`'s `milestone-carrier` check says which).
   - `5` — bd unavailable; nothing was written.
5. **A card that does not exist yet is created only on confirmation.** This
   is the one Jira write that always asks; transitions, comments and titles
   (phase 45) are automatic, creation never is.
   - **The key is an Epic** (`fields.issuetype.name == "Epic"`): a milestone
     is a Story, so list the epic's stories (`searchJiraIssuesUsingJql`) and
     ask which one *is* this cycle. None fits → offer to create a Story under
     the epic, titled with the milestone carrier's title and described with
     its promise. On yes, `createJiraIssue`, save the result, and link the
     new key.
   - **A phase with no Sub-task**: offer to create one under the cycle's
     story (the milestone must be linked first — say so if it is not), titled
     with the phase carrier's title. On yes, create, save, link.
   - **No MCP and no token** (`JIRA_API_TOKEN` unset in the shell): say
     exactly that, and ask the user to create the card in Jira and come back
     with the key — this command then links from the key alone, reading the
     card through the REST adapter only if a token appears, and otherwise
     recording nothing but `external_ref` (type unchecked, and said so).

## `unlink (--milestone vX.Y | --phase N)`

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-jira.sh" unlink (--milestone vX.Y | --phase N)
```

Clears the carrier's `external_ref` and, on a milestone, the cached epic.
Nothing in Jira changes. Say what was cleared (the script prints the old
ref) — and that the next `link` starts from a clean bead.

## `links`

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-jira.sh" links [--milestone vX.Y]
```

The whole cycle in one read: the milestone's story and epic, then one line
per phase with its sub-task or `(unlinked)`. Present the script's lines as
they are; `--json` gives the same model for anything that needs it.

## `audit`

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-doctor.sh" --json
```

Read only the link checks off `.checks[]` — `milestone-carrier` and
`jira-links` — and route each per `/cairn:doctor`. The `jira-links` check is
`⊘ out-of-scope` until `.cairn/sync.json` carries a `jira` backend; say that
rather than reading silence as clean. Its **key does not exist** item is
answered by REST when a token is in the shell; without one, and only here in
a session, fetch the key through the MCP and say what you found — the script
will have said `skipped`, and this is the one place that can close that gap.

Next: `/cairn:status` shows the `⧉` on the cycle and its phases;
`/cairn:doctor` keeps the links honest.
