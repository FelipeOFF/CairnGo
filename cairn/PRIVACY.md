# Privacy Policy — Cairn

_Last updated: 2026-07-25_

Cairn is an open-source Claude Code plugin. It runs **entirely on your own
machine**. The author operates no servers and collects nothing — no telemetry,
no analytics, no install tracking.

## What the plugin does with data

- **Runs locally.** All logic (the dispatcher, hooks, and adapters) executes on
  your machine within your own repository. There is no "cairn service."
- **No collection by the author.** The plugin sends nothing to the author or any
  author-controlled endpoint — no analytics, no tracking, no beacons. The only
  network traffic the plugin ever produces is the third-party issue mirroring
  you explicitly configure, described below.

## Data sent to third parties (only the ones you enable)

When you configure and enable a backend in `.cairn/sync.json`, the plugin
transmits issue data **to that external service, using your own credentials**, so
your `bd` (Beads) issues can be mirrored there. Specifically:

- **What is sent:** the fields needed to create/update/close the mirrored item —
  issue title, description/body, status, labels, and the external item's ID.
- **Where it is sent:** only to the services you explicitly enable, e.g. GitHub,
  GitLab, Jira, Asana, and/or Azure Boards.
- **Pull direction:** when you run a reconcile, the plugin reads the current
  state of mapped items back from those same services.

Each enabled service processes that data under **its own privacy policy and
terms** — GitHub, GitLab, Atlassian (Jira), Asana, and Microsoft (Azure DevOps)
respectively. Review theirs for how they handle the data you mirror.

If you enable **no** backends, the plugin sends no data anywhere.

## Context-mode integration (local memory only)

The context-mode integration (`cairn-context` skill) is **on by default** —
context-mode ships as a cairn plugin dependency — and sends **no data
anywhere**. It only adds labels to, and runs searches against, the local
knowledge base owned by the separate
[context-mode](https://github.com/mksglu/context-mode) plugin — all on your
machine. It transmits nothing to the author or any third party, and it is
**non-destructive**: it never deletes that knowledge base (it never calls
`ctx_purge`); any wipe is a manual action you take yourself. context-mode is a
separate plugin governed by **its own** behavior and policy; review that project
for how it stores data locally. `.cairn/context.json` is **optional tuning**
(defaults apply without it; set `enabled: false` in it to switch the
conventions off); when created it is meant to be committed and holds only
switches and a numeric threshold — no secrets.

## Credentials and secrets

- API tokens are read from **environment variables** whose *names* you put in
  `sync.json`. The plugin never stores token values on disk and never transmits
  them anywhere except, over HTTPS, to the corresponding service's API to
  authenticate your own requests.
- The GitHub adapter uses your existing `gh` CLI authentication.
- `sync.json` (committed) contains configuration and env-var *names* only — no
  secrets. Keep your tokens in your environment / secret manager.

## Local files

The plugin reads and writes files inside your repository: `.beads/`,
`.planning/`, and `.cairn/` (`sync.json`, `context.json`, `id-map.json`,
`state.json`, `conflicts.json`). These stay in your working tree under your
control. The generated state files are gitignored by default; `sync.json` and
`context.json` (both optional) are meant to be committed when you create them,
and whether to commit the rest is your choice.

## Changes

This policy may change as the plugin evolves. Material changes will be reflected
in this file in the repository, with an updated date above.

## Contact

Questions or concerns: open an issue at
<https://github.com/FelipeOFF/CairnGo/issues>.
