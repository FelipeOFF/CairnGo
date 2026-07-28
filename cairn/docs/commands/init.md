# /cairn:init

> One-command, soup-to-nuts project setup — ensure GSD + beads, wire git + bd
> init, then hand off to the interactive GSD project setup

## Usage

```text
/cairn:init
```

No arguments. Run it from the directory you want to set up. Step 0 classifies
the repo; steps 1–2 and 4–5 are non-interactive wiring; step 3 asks once
before installing bd, and the only interview happens at the hand-off.

## What it does

- **Step 0 — detect existing state.** Runs
  `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-migrate.sh" detect` and routes on
  the state letter (line 1 of the output):
  - **A / B / C** — the repo already has `.planning/` and/or `.beads/` history
    that isn't wired yet. Init **stops here** and hands off to
    [/cairn:migrate](./migrate.md). It never runs `/gsd:new-project` over an
    existing `.planning/`.
  - **W** — both present and already wired: only the wiring steps (1–5) run,
    and step 6 is skipped — there is nothing to interview.
  - **D** — greenfield: all steps run.

  Whatever the state letter: when the detect JSON (`detect --json`) carries
  `external.jira` with `detected: true`, the repo already references Jira
  cards (`prefixes` lists the issue-key prefixes found). The user is told and
  pointed at [/cairn:sync-config](./sync-config.md), which pre-fills the Jira
  backend from this detection and can import the existing cards — init never
  configures sync or runs an import by itself.
- **Step 1 — verify GSD Core.** It ships as a declared dependency of cairn, so
  it is normally already installed. If missing:
  `claude plugin install gsd-core@cairngo`, then `/reload-plugins`. The
  capability system cairn needs exists only on the official
  `open-gsd/gsd-core` line; the older `gsd` 4.x plugin has no `capability`
  subcommand.
- **Step 2 — install the cairn GSD capability** at project scope, via
  `scripts/cairn-capability.sh install`. It installs the bundle
  (`capability install …`, falling back to `capability update cairn` on a
  re-run) and then **verifies the result**: GSD's own `capability list` must
  report cairn as `active`, and the staged bundle must carry the scripts its
  gates reference. Registration makes plain `/gsd:plan-phase`,
  `/gsd:execute-phase`, `/gsd:verify-work` and `/gsd:ship` link, claim, close
  and gate bd issues without the `/cairn:*` wrappers. Idempotent.

  Exit 7 means the capability is **not** installed — a blocked install (e.g. a
  `capabilities.strict_known_registries` lockdown) or a 4.x lineage that cannot
  host it. Setup continues and the cairn skill still covers the conventions
  conversationally, but the failure is reported with its cause and fix instead
  of being swallowed. See [/cairn:doctor](./doctor.md) to re-check later.
- **Step 3 — ensure beads (`bd`).** If the binary is on PATH, continue. If
  missing, the user is asked **before** anything is installed
  (`brew install beads` / `npm install -g @beads/bd` / curl installer), then
  verified with `bd version`. If the user declines, an empty marker
  `$CLAUDE_PLUGIN_DATA/bd-install.skip` is created (so the session-start hook
  stops nagging) and setup **stops** — the rest needs bd.
- **Step 4 — wire git + beads.** Runs
  `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-init.sh" "$PWD"` (idempotent):
  ensures the directory is a git repo and runs `bd init` if `.beads/` is
  missing, then reports what it did.
- **Step 5 — memory is already on.** context-mode ships as a cairn
  dependency, so intent-aware memory ([/cairn:remember](./remember.md),
  [/cairn:recall](./recall.md)) works out of the box.
  [/cairn:context-config](./context-config.md) is only for tuning and is not
  run unprompted.
- **Step 6 — hand off** to `/gsd:new-project` for the interactive roadmap
  interview. `.planning/` is created by GSD, never by cairn. After the
  roadmap exists, the cairn skill takes over: one stamped bd issue per
  requirement (label pair `m-<milestone>` + `phase-<N>` and the
  `metadata.gsd` stamp), and each phase's `NN-BEADS-MAP.md` generated with
  `cairn-map.sh <N>`. The normal loop then runs under the cairn conventions,
  which activate automatically once both `.planning/` and `.beads/` exist.

### Side effects

- `.gsd/capabilities/cairn/` — the capability bundle, staged at project scope.
- `.cairn/plugin-root` — records `${CLAUDE_PLUGIN_ROOT}` so the bundled
  scripts reuse the plugin's own map generator instead of shipping a copy.
- git **pre-push shim** + `.cairn` entries in `.gitignore` (via
  `cairn-init.sh`). The shim re-runs the ship gate outside any LLM — see
  [/cairn:ship](./ship.md).
- `.beads/` created by `bd init` when absent.
- `$CLAUDE_PLUGIN_DATA/bd-install.skip` when the user declines the bd install.

## Flags & arguments

None.

## Examples

```text
/cairn:init          # in an empty repo
→ detect: D (greenfield) · GSD present · capability installed (project scope)
→ bd found on PATH · cairn-init: git repo ok, bd init created .beads/
→ handing off to /gsd:new-project …
```

```text
/cairn:init          # in a repo that already has .planning/
→ detect: A — GSD history present but unwired. Stopping init;
  run /cairn:migrate to adopt this repo without redoing anything.
```

## Files touched

- **Reads:** repo state (`.planning/`, `.beads/` presence, git status).
- **Writes:** `.cairn/plugin-root`, `.gsd/capabilities/cairn/`,
  `.git/hooks/pre-push` (shim), `.gitignore` (`.cairn` generated files),
  `.beads/` (via `bd init`), `$CLAUDE_PLUGIN_DATA/bd-install.skip` (only on
  decline). `.planning/` is written by GSD at the hand-off, not by cairn.

## Related

- [/cairn:migrate](./migrate.md) — where states A/B/C are routed
- [/cairn:new](./new.md) — the project-creation flow init hands off to
- [/cairn:doctor](./doctor.md) — health-check the wiring afterwards
- [/cairn:context-config](./context-config.md) — tune the memory integration
