# Privacy Policy — Cairn

_Last updated: 2026-07-05_

Cairn is an open-source Claude Code plugin. It runs **entirely on your own
machine**. The author operates no servers and, by default, collects nothing. The
one exception is a single **opt-in install beacon** that is **off unless you
turn it on** — and even then the author receives only an anonymous running total,
never your IP, your repository, or any identifier (see
[Telemetry](#telemetry-opt-in-off-by-default)).

## What the plugin does with data

- **Runs locally.** All logic (the dispatcher, hooks, and adapters) executes on
  your machine within your own repository. There is no "cairn service."
- **No collection by the author, by default.** With telemetry off (the default),
  the plugin sends nothing to the author or any author-controlled endpoint — no
  analytics, no tracking. The only thing that ever reaches the author is the
  opt-in install beacon described below, and only if you enable it.

## Telemetry (opt-in, off by default)

Cairn can send a single **install beacon** so the author can tell whether the
plugin is actually being used. It is **disabled by default** and only turns on if
you explicitly opt in during `/cairn:init` (which writes `"enabled": true` to
`.cairn/telemetry.json`).

- **How it works.** When enabled, cairn does **one anonymous HTTPS GET** of a
  tiny "beacon" file published as a GitHub release asset. GitHub increments that
  asset's public `download_count`. There is no author-run server.
- **What the author receives.** Only that aggregate integer — a count. The author
  never sees your IP address, your repository, your username, timestamps, or any
  per-event record. (GitHub, as the file host, sees the request the same way it
  sees any download; the author does not.)
- **How often.** Once per project, guarded by a local `.cairn/.beacon-sent`
  marker. It does not fire on every session.
- **Turning it off.** Set `"enabled": false` in `.cairn/telemetry.json` (delete
  `.cairn/.beacon-sent` for a clean slate). With it off, cairn sends nothing.

This is deliberately the least-invasive mechanism available: no server, no
identifiers, no personal data — just a bump on a public counter you chose to
allow.

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

The optional context-mode integration (`.cairn/context.json`,
`cairn-context` skill) sends **no data anywhere**. It only adds labels to,
and runs searches against, the local knowledge base owned by the separate
[context-mode](https://github.com/mksglu/context-mode) plugin — all on your
machine. It transmits nothing to the author or any third party, and it is
**non-destructive**: it never deletes that knowledge base (it never calls
`ctx_purge`); any wipe is a manual action you take yourself. context-mode is a
separate plugin governed by **its own** behavior and policy; review that project
for how it stores data locally. `context.json` (committed) holds only switches
and a numeric threshold — no secrets.

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
`context.json` are meant to be committed and whether to commit the rest is your
choice.

## Changes

This policy may change as the plugin evolves. Material changes will be reflected
in this file in the repository, with an updated date above.

## Contact

Questions or concerns: open an issue at
<https://github.com/eventually-consistent-code/claude-plugins/issues>.
