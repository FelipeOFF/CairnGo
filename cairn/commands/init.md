---
description: One-command, soup-to-nuts project setup — ensure GSD + beads, wire git + bd init, then hand off to the interactive GSD project setup
---

Set up the current working directory for the full cairn workflow, end to end.
Run these steps in order. Step 0 classifies the repo; steps 1–2 and 4–5 are
non-interactive wiring; step 3 asks once before installing bd, step 6 asks
about telemetry, and the interview happens only at the hand-off.

## 0. Detect existing state

Before anything else, classify the repo:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-migrate.sh" detect
```

Route on the state letter (line 1 of the output):

- **A / B / C** — the repo already has `.planning/` and/or `.beads/` history
  that isn't wired yet. **Stop init here** and hand off to `/cairn:migrate`
  (never run `/gsd:new-project` over an existing `.planning/`).
- **W** — both present and already wired: run steps 1–6 below (capability
  install + hooks wiring only) and **skip step 7** — there is nothing to
  interview.
- **D** — greenfield: continue with all steps below.

## 1. Verify GSD is present

GSD ships as a declared dependency of cairn, so it is normally already installed.
Confirm `/gsd:*` commands are available (check `claude plugin list` for `gsd`).
If GSD is missing, install it and tell the user to `/reload-plugins`:
```bash
claude plugin install gsd@eventually-consistent-code
```

## 2. Install the cairn GSD capability (plain `/gsd:*` does beads)

The capability bundle ships with the plugin at `${CLAUDE_PLUGIN_ROOT}/capability`.
Installing it project-scope registers cairn's loop hooks with GSD itself — plain
`/gsd:plan-phase`, `/gsd:execute-phase`, `/gsd:verify-work`, and `/gsd:ship`
then link, claim, close, and gate bd issues without the `/cairn:*` wrappers.
Idempotent: a re-run refreshes the bundle via `capability update`.

```bash
GSD_BIN="$(command -v gsd_run || command -v gsd || true)"
if [ -n "$GSD_BIN" ]; then
  "$GSD_BIN" capability install "${CLAUDE_PLUGIN_ROOT}/capability" --scope project --yes \
    || "$GSD_BIN" capability update cairn --scope project --yes \
    || echo "capability install skipped — /cairn:* commands and the cairn skill still work"
  mkdir -p .cairn && printf '%s\n' "${CLAUDE_PLUGIN_ROOT}" > .cairn/plugin-root
else
  echo "gsd_run not on PATH — skipping capability install (the cairn skill still applies)"
fi
```

`--scope project` stages the bundle at `.gsd/capabilities/cairn/`;
`.cairn/plugin-root` lets the bundled scripts reuse the plugin's own map
generator instead of shipping a copy. If the install is blocked (e.g. a
`capabilities.strict_known_registries` lockdown), continue — the cairn skill
covers the same conventions conversationally.

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

## 6. Opt-in install ping (off by default)

Ask once, plainly, and take **no** as the default:

> "Send an anonymous install ping so the author can see cairn is actually being
> used? It's **off** unless you say yes. If you opt in, cairn does a single
> anonymous download of a beacon file on GitHub — the author sees only a running
> total, never your IP, your repo, or any identifier. You can turn it off anytime."

Write the choice to `.cairn/telemetry.json` (create `.cairn/` if missing) — use
`"enabled": true` only if the user opts in, otherwise `false`:
```json
{ "enabled": false }
```
Then run the ping helper (it's a no-op unless `enabled` is true):
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-ping.sh" "$PWD"
```
To stop later: set `"enabled": false` in `.cairn/telemetry.json` (and delete
`.cairn/.beacon-sent` for a clean slate). See `PRIVACY.md` for exactly what the
beacon does and doesn't send.

## 7. Hand off to the interactive project setup

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
