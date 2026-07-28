---
description: One-command, soup-to-nuts project setup — ensure GSD + beads, wire git + bd init, then hand off to the interactive GSD project setup
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
  (never run `/gsd:new-project` over an existing `.planning/`).
- **W** — both present and already wired: run steps 1–5 below (capability
  install + hooks wiring only) and **skip step 6** — there is nothing to
  interview.
- **D** — greenfield: continue with all steps below.

Regardless of the state letter: if the detect JSON (`detect --json`) carries
`external.jira` with `detected: true`, the repo already references Jira cards
(`prefixes` lists the issue-key prefixes found). Mention it to the user and
suggest `/cairn:sync-config` — it pre-fills the Jira backend from this
detection and can import the existing cards. Never configure sync or run an
import yourself; only point at it.

## 1. Verify GSD is present

GSD Core ships as a declared dependency of cairn, so it is normally already
installed. Confirm `/gsd:*` commands are available (check `claude plugin list`
for `gsd-core`). If it is missing, install it and tell the user to
`/reload-plugins`:
```bash
claude plugin install gsd-core@cairngo
```

The capability system cairn depends on exists only on the official
`open-gsd/gsd-core` line. An install of the older `gsd` 4.x plugin
(`jnuyens/gsd-plugin`) has no `capability` subcommand at all — step 2 detects
that and says so.

**Watch for a machine that already had GSD.** Installing cairn pulls `gsd-core`
in as a dependency, and it lands *beside* an existing 4.x `gsd` plugin rather
than replacing it. Nothing errors, both provide the same workflow surface, and
only one of them can host the capability — so `/gsd:*` may be answered by the
plugin that cannot, while every check reports green. Step 2 fails on this and
names the plugin to remove:

```bash
claude plugin uninstall gsd@cairngo    # the id step 2 printed
```

then `/reload-plugins`. This is the likeliest shape for anyone who used GSD
before meeting cairn.

## 2. Install the cairn GSD capability (plain `/gsd:*` does beads)

The capability bundle ships with the plugin at `${CLAUDE_PLUGIN_ROOT}/capability`.
Installing it project-scope registers cairn's loop hooks with GSD itself — plain
`/gsd:plan-phase`, `/gsd:execute-phase`, `/gsd:verify-work`, and `/gsd:ship`
then link, claim, close, and gate bd issues without the `/cairn:*` wrappers.
Idempotent: a re-run refreshes the bundle via `capability update`.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-capability.sh" install
rc=$?
mkdir -p .cairn && printf '%s\n' "${CLAUDE_PLUGIN_ROOT}" > .cairn/plugin-root
exit $rc
```

`install` first repairs a defect in gsd-core's own manifest that would otherwise
stop this step mattering at all. gsd-core 1.7.0 and 1.8.0 declare
`"hooks": "./hooks/hooks.json"`, a path Claude Code loads automatically, so the
loader treats it as a duplicate and **refuses the whole plugin** — no `/gsd:*`
commands exist for the fusion to attach to. cairn removes that one line from the
installed copy rather than forking gsd-core.

If the repair ran, tell the user to `/reload-plugins`: Claude Code has already
decided the plugin failed for this session, and only a reload changes that. A
gsd-core update restores the original file, so `/cairn:doctor` re-checks it.

The script installs the bundle and then **verifies it registered** — GSD's own
`capability list` must report cairn as active, and the staged bundle must carry
the scripts its gates reference. Report the result honestly by exit code:

- **0** — the fusion is active. Say so in one line and continue to step 3.
- **7** — the capability is NOT installed. This is a failure, not a footnote:
  print the script's stderr verbatim (it names the cause and the fix) and tell
  the user plainly that `/cairn:*` commands and the cairn skill still work, but
  plain `/gsd:*` will not touch bd issues until it is resolved. Continue with
  the rest of init; do not pretend the fusion is on.
- **5** — no GSD binary found at all. Same handling as 7, with the install
  command from step 1.

Never swallow a non-zero exit here. This step used to end in
`|| echo "capability install skipped"`, which turned every failure into
success — installs went out for months with the wrappers working and the
fusion absent, and nothing ever said a word.

`--scope project` stages the bundle at `.gsd/capabilities/cairn/`;
`.cairn/plugin-root` lets the bundled scripts reuse the plugin's own map
generator instead of shipping a copy. A blocked install (e.g. a
`capabilities.strict_known_registries` lockdown) still exits 7 — report it and
continue, because the cairn skill covers the same conventions conversationally,
but the user must know the fusion is off.

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

`.planning/` is created by GSD, not by cairn — do NOT create it yourself. Launch
the interactive roadmap interview now:
```text
/gsd:new-project
```
After the roadmap exists, follow the `cairn` skill: create one bd issue per
requirement, stamped with the `gsd` metadata and the `m-<milestone>` +
`phase-<N>` label pair; generate each `NN-BEADS-MAP.md` with
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>`. Then the
normal loop — `/gsd:plan-phase 1`, `/gsd:execute-phase 1`, … — runs under the
cairn conventions, which activate automatically once both `.planning/` and
`.beads/` exist.
