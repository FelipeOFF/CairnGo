---
description: Show the cairn unified command interface (one namespace for GSD + beads)
group: view
---

Print the map — `/cairn:` is the single interface for the whole GSD↔beads
workflow. Show it to the user, then offer the obvious next step for their repo
(no `.planning/` and no `.beads/` → `/cairn:new`; `.beads/` but no
`.planning/` — or the reverse — → `/cairn:migrate`; both present →
`/cairn:status`).

## The map is derived from what is installed — no half of it is typed here

One call answers what exists:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" list --json
```

- `.commands` is every installed command; `.wrappers[]` are the ones that
  delegate to a `/gsd:*` command. **Cairn's own commands are `.commands` minus
  the `.wrappers[].command` names** — a set difference computed at run time,
  never a list kept on this page.
- Each own command's own file answers the rest: read the frontmatter of
  `${CLAUDE_PLUGIN_ROOT}/commands/<name>.md` — `description:` is the one line
  to print, `group:` is the heading it prints under.
- A file carrying no `group:` prints under `OTHER`, and a `group:` value with
  no heading below prints under a heading of its own name, at the end. A
  command may land in the wrong place; it may never be missing.
- Exit `2` (no commands directory found) is worth one line saying so. It is
  not worth guessing the list.

Print cairn's own commands first, one line per command — `/cairn:<name>`
followed by its description — under these headings, in this order:

| `group:` | Heading | What sits there |
|---|---|---|
| `setup` | `SETUP` | wiring a repo up for the first time |
| `loop` | `LOOP` | the per-phase cycle: plan → work → verify → ship |
| `view` | `VIEW` | read-only renders of where the project stands |
| `health` | `MIGRATE & HEALTH` | adopting a repo, and keeping the wiring honest |
| `config` | `CONFIG` | cairn's own knobs |
| `memory` | `MEMORY (context-mode — on by default)` | intent-scoped memory |
| `sync` | `SYNC (optional)` | mirroring bd to an external tracker |
| `escape` | `ESCAPE HATCHES (raw passthrough)` | reach anything the verbs don't wrap |

Then the wrappers, under a `WRAPPED GSD COMMANDS` heading, in the same shape:
one line per `.wrappers[]` entry, `/cairn:<command>` delegating to
`/gsd:<wraps>`. Every one of them claims the phase's beads, runs the GSD
command, and closes — and refuses to start when that GSD command is not
installed, naming what is missing.

**Do not transcribe either half into this page.** A hand-written list of
commands is how this page starts lying, and it already did: `cairn/docs/commands.md`
once claimed 22 commands while 25 were installed, with two of them reachable
and documented nowhere; and after the wrapper half of this map became derived,
the half still typed here had already dropped a whole command — `reconcile`,
which exists, has a page, has a row in the reference, and was invisible in the
map users read most.
Deriving one half and keeping the other by hand is the worst of the two: the
derived half reads as proof that the whole page is honest.

## What the map does not list, because it is not a command

The end-of-phase bookkeeping is a script, not a `/cairn:` verb — it is invoked
by the commands above, and run by hand when a phase was closed outside them:

```bash
bash "${CLAUDE_PLUGIN_ROOT}"/scripts/cairn-bookkeep.sh close <N> --apply
```

It marks the phase and its requirements, moves the coverage table, the footer,
the plan checkboxes and the STATE counters, regenerates the map, and releases
the lease. Reading is the default — drop `--apply` to see the edits first.
Full contract: `docs/commands/bookkeep.md`.

## The three config files, told apart

Three commands write three files, and they do not overlap. Name all three when
the user asks where a setting lives:

- `/cairn:config` → `.cairn/config.json` — cairn's own knobs: auto-commit, PR
  scope, the ceilings on an autonomous run, test jobs.
- `/cairn:sync-config` → `.cairn/sync.json` — which backends bd mirrors to
  (GitHub / GitLab / Jira / Asana / Azure Boards). Jira is detected first: it
  shows the key it found and where, asks once, and writes the backend from
  your yes — you never type a key or a credential. No signal means no
  question, and a no is recorded (`jira.link` in `.cairn/config.json`) so it
  stays no.
- `/cairn:context-config` → `.cairn/context.json` — the context-mode scope
  template and capacity threshold.

Each writes a file you can also edit by hand, and `/cairn:config` ends by
naming all three plus GSD's own `cairn.enabled` — one place to look.
