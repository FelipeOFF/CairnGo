# Matt skills on beads

Cairn orchestrates grill-with-docs → to-spec → to-tickets → implement-spec.
Those skills must **publish to bd**. They must **not** write planning files.

Grill questions go through the harness Ask tool (Claude Code: `AskUserQuestion`;
Grok: `ask_user_question`). A markdown `❓ Q1` block in chat is not the interview.

## Tracker

Read `docs/agents/issue-tracker.md` if present (written by `/cairn-init`).
Otherwise use this page.

- Create a spec: `bd create --title="..." --type=epic --labels=enhancement,ready-for-agent --metadata '{"cairn":{"kind":"spec"}}'` and put the spec body in `--description` (or `--body-file`). Glossary/ADRs go in `--design`.
- Create a ticket: `bd create --title="..." --type=task --parent=<spec-id> --labels=ready-for-agent --metadata '{"cairn":{"kind":"ticket"}}' --deps <blocker-ids>`.
- Fetch: `bd show <id>`. List frontier: `bd ready` and keep rows labelled `ready-for-agent`.
- Claim: `bd update <id> --claim`. Close: `bd close <id> --reason="..."`.
- Block: `bd dep add <issue> <depends-on>`.

Do **not** call `gh issue create` unless the spoke is GitHub **and** you are only mirroring — the hub write is always `bd`.

## CONTEXT.md is an error

If a Matt skill (or domain-modeling) tries to create or edit `CONTEXT.md` or `docs/adr/*.md`:

1. Do not write the file.
2. Append the glossary term or ADR to the spec bead: `bd update <spec> --design` (read-modify-write the existing `design`, keep `## GLOSSARY` / `## ADR` sections).
3. Tell the user the prose landed on the bead, not on disk.

## Triage

Apply beads labels, not GitHub labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`, `bug`, `enhancement`.

## After each bd write

If `.cairn/sync.json` has an enabled backend, run the matching `gbsync.sh create|update|close <id>`.
