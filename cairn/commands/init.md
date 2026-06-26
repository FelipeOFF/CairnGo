---
description: One-command, soup-to-nuts project setup — ensure GSD + beads, wire git + bd init, then hand off to the interactive GSD project setup
---

Set up the current working directory for the full cairn workflow, end to end.
Run these steps in order. Everything up to step 4 is non-interactive wiring; the
interview happens only at the hand-off.

## 1. Verify GSD is present

GSD ships as a declared dependency of cairn, so it is normally already installed.
Confirm `/gsd:*` commands are available (check `claude plugin list` for `gsd`).
If GSD is missing, install it and tell the user to `/reload-plugins`:
```bash
claude plugin install gsd@bigjiggity
```

## 2. Ensure beads (`bd`) — prompt, then install

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

## 3. Wire git + beads

Run the bootstrap script (idempotent — safe to re-run):
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-init.sh" "$PWD"
```
It ensures the directory is a git repo and runs `bd init` if `.beads/` is missing,
and reports what it did.

## 4. Intent-aware memory (already on)

context-mode ships as a cairn dependency, so intent-aware memory is active by
default — `/cairn:remember` and `/cairn:recall` work out of the box, scoping
memory to the active bd issue + phase. Mention `/cairn:context-config` only if
the user wants to tune the scope template or capacity threshold; don't run it
unprompted.

## 5. Hand off to the interactive project setup

`.planning/` is created by GSD, not by cairn — do NOT create it yourself. Launch
the interactive roadmap interview now:
```text
/gsd:new-project
```
After the roadmap exists, follow the `cairn` skill: create one bd issue per
requirement, label each `phase-N`, and write each `NN-BEADS-MAP.md`. Then the
normal loop — `/gsd:plan-phase 1`, `/gsd:execute-phase 1`, … — runs under the
cairn conventions, which activate automatically once both `.planning/` and
`.beads/` exist.
