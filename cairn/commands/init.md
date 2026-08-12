---
description: One-command, soup-to-nuts project setup — ensure GSD + beads, wire git + bd init, then hand off to the interactive GSD project setup
group: setup
---

Set up the current working directory for the full cairn workflow, end to end.
Run these steps in order. Step 0 classifies the repo; steps 1–2 and 4–5 are
non-interactive wiring; step 3 asks once before installing bd, and the
interview happens only at the hand-off.

## 0. Detect existing state

Before anything else, classify the repo:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-migrate.sh" detect
```

Route on the state letter (line 1 of the output):

- **A / B / C** — the repo already has `.planning/` and/or `.beads/` history
  that isn't wired yet. **Stop init here** and hand off to `/cairn:migrate`
  (never run a project-creation interview over an existing `.planning/`).
- **W** — both present and already wired: run steps 1–5 below (cleanup
  install + hooks wiring only) and **skip step 6** — there is nothing to
  interview.
- **D** — greenfield: continue with all steps below.

Regardless of the state letter: if the detect JSON (`detect --json`) carries
`external.jira` with `detected: true`, the repo already references Jira cards
(`prefixes` lists the issue-key prefixes found). Mention it to the user and
suggest `/cairn:sync-config` — it pre-fills the Jira backend from this
detection and can import the existing cards. Never configure sync or run an
import yourself; only point at it.

## 1. Verify the vendored GSD runtime

Since v1.6 cairn **carries its own GSD runtime** at
`${CLAUDE_PLUGIN_ROOT}/gsd/`. There is no `gsd-core` plugin to install, no
plugin dependency to resolve, and no lineage to choose between. Confirm the
runtime arrived intact:

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/gsd/MANIFEST.json" && \
  test -d "${CLAUDE_PLUGIN_ROOT}/gsd/commands" && echo ok
```

Anything other than `ok` means **this cairn install is incomplete** — a defect
of the install, not of the machine, and no external plugin can supply it. Tell
the user to reinstall (`claude plugin install cairn@cairngo`) and
`/reload-plugins`, then stop: the rest of setup assumes the runtime is there.

**Watch for a machine that used cairn before v1.6.** It still has `gsd-core`
installed — cairn used to pull it in as a dependency — and possibly an older
4.x `gsd` beside it. Neither is needed now, and leaving one installed is worse
than useless: it answers `/gsd:*` with the pre-bd workflows while `/cairn:*`
answers with bd, which is exactly the two-lineage window the vendoring closed.
Tell the user to remove what `/cairn:doctor` names:

```bash
claude plugin uninstall gsd-core@cairngo    # the id doctor printed
```

then `/reload-plugins`. `/cairn:doctor` check 10 reports this, and step 2 below
is where the leftovers from that era get cleaned up.

## 2. Clean up pre-v1.6 capability state

cairn used to register a **GSD capability** here, so that plain `/gsd:*` would
drive bd through an external plugin's hook points. That bundle was **archived
in v1.6** (see `cairn/capability/ARCHIVED.md`): the vendored runtime talks to
bd directly, so there is no host for the contributions and nothing reads the
staged files.

This step no longer installs anything. On a repo that was wired before v1.6,
leftover state may still exist — `/cairn:doctor` reports it as a ⚠ with the
exact paths. Show the user what it named and let them remove it:

```bash
rm -rf .gsd/capabilities/cairn .gsd-capabilities.json   # only what doctor named
```

Never delete these on the user's behalf without showing what is going, and
never treat their presence as an error: leftover files are friction, not a
broken repo.

The one thing this step still does is record the plugin root, so the bundled
scripts can find the plugin's own map generator instead of shipping a copy:

```bash
mkdir -p .cairn && printf '%s\n' "${CLAUDE_PLUGIN_ROOT}" > .cairn/plugin-root
```

## 3. Ensure beads (`bd`) — prompt, then install

beads is a binary, not a plugin, so it can't be a dependency. Check `command -v bd`.

If `bd` is **already on PATH**, say so and continue.

If `bd` is **missing**, ask the user to confirm before installing — show them
what will run and let them pick. On their OK, run the first installer that fits
their machine, then verify with `bd version`:
- macOS / Linux (recommended): `brew install beads`
- Node.js users: `npm install -g @beads/bd`
- portable fallback: `curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash`

If the user **declines**, create an empty marker so the session-start hook stops
nagging, then stop (the rest of setup needs bd):
```bash
mkdir -p "$CLAUDE_PLUGIN_DATA" && touch "$CLAUDE_PLUGIN_DATA/bd-install.skip"
```

## 3.5. Ask the response language — before anything spawns a subagent

The position of this step is the decision, not a detail. Step 6 hands off to
`/gsd:new-project`, which **spawns its own subagents** (researcher, synthesizer,
roadmapper). Asking after that hand-off is asking after the project's first
subagents already answered in the wrong language. "Chosen at install" means
before the first subagent, and that is here.

Read the current state from the script, never from memory:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" get agents.response_language --json
```

**If `source` is already `file` or `planning`**, a choice exists. Say which one,
in one line, and move on — **do not ask, and do not write anything**. An
installed project is not changed without being asked, and the mechanism for
that is exactly this: the only door that writes is the question, and the
question does not open.

**If `source` is `default`**, ask once with `AskUserQuestion`.
**English is the default, and it is pre-selected and named as such** — never
offered as merely the first item of a list. Describe the effect rather than the
key: it is the language every subagent writes its user-facing output in —
reports, SUMMARY files, the questions it asks you — while code, identifiers,
file paths and commands stay as they are. Offer the common languages and make
clear that any language name is accepted; GSD's own schema takes any
(`references/planning-config.md`: "Any language name").

Then write it:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" set agents.response_language "<the answer>"
```

The script propagates the value into `.planning/config.json:response_language`
by itself, and only if that file already exists. At this point in a greenfield
run it does not, so the output will say `planning-config-absent` — that is
expected, and step 6 is where the same command is run again. **Never write
`.planning/config.json` yourself here**: `gsd-tools query config-set` creates
`.planning/` when it is absent, and a `.planning/` holding only `config.json`
makes step 0's `detect` answer **A** instead of **D**, which would make the
next run of this very command stop and divert to `/cairn:migrate`.

## 4. Wire git + beads

Run the bootstrap script (idempotent — safe to re-run):
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-init.sh" "$PWD"
```
It ensures the directory is a git repo and runs `bd init` if `.beads/` is missing,
and reports what it did.

## 5. Intent-aware memory (already on)

context-mode ships as a cairn dependency, so intent-aware memory is active by
default — `/cairn:remember` and `/cairn:recall` work out of the box, scoping
memory to the active bd issue + phase. Mention `/cairn:context-config` only if
the user wants to tune the scope template or capacity threshold; don't run it
unprompted.

## 6. Hand off to the interactive project setup

`.planning/` holds the roadmap interview's output, and **cairn does not vendor
project creation**: v1.6 vendored the four cycle verbs (discuss, plan, execute,
verify) and nothing else, so there is no `new-project` inside this plugin.
Take the first route that applies and tell the user which one it was:

- a GSD plugin installed alongside cairn — run the interview through the
  declared passthrough:
  ```text
  /cairn:gsd new-project
  ```
- no GSD plugin — write `.planning/PROJECT.md`, `.planning/ROADMAP.md` and
  `.planning/REQUIREMENTS.md` from a short interview you run yourself (what is
  this project, why does it exist, what has to be true for v1). Keep it to 4-5
  questions; `/cairn:plan <N>` fills in the rest, phase by phase.

**As soon as it returns, re-run the language write from step 3.5, unchanged:**

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" set agents.response_language "<the same answer>"
```

`.planning/config.json` exists now, so this time the propagation fires and
GSD's own `response_language` carries the choice — that key is what GSD's
workflows read when they spawn their subagents. Same command, same value:
idempotent by construction, and running it when the value is already there
changes nothing. If this step is ever skipped, `/cairn:doctor` reports it and
names this exact command; it is not left to memory.

After the roadmap exists, follow the `cairn` skill: create one bd issue per
requirement, stamped with the `gsd` metadata and the `m-<milestone>` +
`phase-<N>` label pair. Inspect a phase any time with
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>`, which prints its
requirement↔issue table straight from bd. Then the
normal loop — `/cairn:plan 1`, `/cairn:work 1`, `/cairn:verify 1`, … — runs
under the cairn conventions, which activate automatically once both
`.planning/` and `.beads/` exist.
