# Technology Stack

**Analysis Date:** 2026-07-25

## Languages

**Primary:**
- Bash (POSIX-ish, `bash`-specific — `#!/usr/bin/env bash`, `set -euo pipefail`) - Claude Code hooks (`cairn/hooks/*.sh`), thin script wrappers (`cairn/scripts/*.sh`, `cairn/capability/scripts/*.sh`), and the bootstrap script `cairn/scripts/cairn-init.sh`
- Python 3 (stdlib only, no third-party packages) - the actual implementation logic behind every `.sh` wrapper (`cairn/scripts/*.py`, `cairn/capability/scripts/cairn-loop-gate.py`, `cairn/adapters/*.py`)
- Markdown - Claude Code slash-command definitions (`cairn/commands/*.md`), skills (`cairn/skills/*/SKILL.md`), capability prompt fragments (`cairn/capability/fragments/*.md`), and all docs

**Secondary:**
- Bats (Bash Automated Testing System) - test suite (`tests/*.bats`)
- YAML - `.beads/config.yaml` (beads/bd configuration)
- JSON - plugin manifests, capability manifest, config templates (`cairn/.claude-plugin/plugin.json`, `cairn/capability/capability.json`, `cairn/hooks/hooks.json`, `cairn/templates/*.json.example`)

## Runtime

**Environment:**
- Claude Code (plugin runtime — hooks, slash commands, capability contributions are Claude-Code-specific; the repo explicitly notes "other GSD runtimes get the conventions without the enforcement")
- Bash ≥ whatever ships `set -euo pipefail` + array support (no `declare -A`/`local -n` used — kept portable across macOS's older bash 3.2 and Linux bash)
- Python 3 (any modern 3.x — stdlib-only by design, see `CONTRIBUTING.md`: "Python: stdlib only (the sync layer must run anywhere Claude Code runs)")

**Package Manager:**
- None (no `package.json`, `requirements.txt`, `pyproject.toml`, or `Cargo.toml` at the repo root or in `cairn/`) — this is a script/plugin repo, not an installable package
- No lockfile — dependencies are external CLI tools, not language-level packages

## Frameworks

**Core:**
- None (no application framework) — the repo *is* a Claude Code plugin: `cairn/.claude-plugin/plugin.json` declares the plugin, `.claude-plugin/marketplace.json` declares the marketplace that distributes it

**Testing:**
- bats-core - shell test framework, invoked as `bats tests/` (installed via `npm install -g bats` in CI, or `brew install bats-core` per `tests/README.md`)
- `jq` - required by several `.bats` files for JSON assertions (`tests/cairn-map.bats`, `tests/cairn-migrate.bats`, `tests/capability.bats`)

**Build/Dev:**
- No build step or bundler — scripts run directly (`bash script.sh`, `python3 script.py`)
- `python3 -m py_compile` used in CI as a lightweight Python syntax lint (`.github/workflows/ci.yml`)
- `shellcheck` referenced as a style requirement in `CONTRIBUTING.md` ("Shell: bash, `set -euo pipefail`, shellcheck-clean") but not wired into CI

## Key Dependencies

**Critical (external CLI binaries, not language packages):**
- `bd` (beads) ≥ 1.1.0 - git-native issue tracker; the hub/source-of-truth CLI that nearly every cairn script shells out to (`bd list --json`, `bd create`, `bd update --claim`, `bd close`, etc.). Installed via `brew install beads`, `npm install -g @beads/bd`, or the upstream install script. Pinned minimum version checked in `cairn/scripts/cairn-init.sh`.
- `git` - required for the GSD `.planning/` + beads `.beads/` git-native model; also used for the `pre-push` ship-gate shim
- `gh` (GitHub CLI) - used exclusively by `cairn/adapters/github.py`, which shells out to `gh issue create/edit/close` and reuses `gh`'s own auth (`gh auth status`) rather than handling GitHub tokens itself

**Infrastructure:**
- GSD ("Get Shit Done", `jnuyens/gsd-plugin`) ≥ 1.8.0 - the planning/execution/verification workflow (`/gsd:*`) that cairn wires into via a capability contribution model (`plan:post`, `execute:wave:pre`, `execute:wave:post`, `verify:post`, `ship:pre` gate). Declared as a plugin dependency in `cairn/.claude-plugin/plugin.json` and version-pinned via `engines.gsd` in `cairn/capability/capability.json`.
- context-mode (`mksglu/context-mode`) - optional cross-marketplace dependency providing the `ctx_*` MCP tools for compressed memory; cairn's `cairn-context` skill and `cairn/templates/context.json.example` make it intent-aware (scoped by bd issue + GSD phase) but never required
- Dolt (embedded) - the storage engine underneath `bd`/beads itself (`.beads/metadata.json`: `"database": "dolt", "dolt_mode": "embedded"`); cairn does not talk to Dolt directly, only through the `bd` CLI

## Configuration

**Environment:**
- No `.env` file present in the repo
- Secrets for sync adapters are read from named environment variables at runtime, never written to disk: `GITLAB_TOKEN`, `JIRA_EMAIL` / `JIRA_API_TOKEN`, `ASANA_TOKEN`, `AZURE_DEVOPS_PAT` (variable names themselves are configurable per-project in `.cairn/sync.json`, see `token_env`/`pat_env`/`email_env` keys)
- `CLAUDE_PROJECT_DIR` - read by `cairn/scripts/gbsync.py` to resolve the active project root
- `CLAUDE_PLUGIN_ROOT` - used throughout `cairn/hooks/hooks.json` to locate hook scripts relative to the installed plugin
- `GSD_HOME` - consulted by the `ship:pre` gate predicate in `cairn/capability/capability.json` to locate the bundled `cairn-loop-gate.sh`

**Build:**
- `.beads/config.yaml` - per-repo beads/bd configuration (issue prefix, no-db mode, backup settings, Dolt remote sync URL)
- `cairn/templates/sync.json.example` - template for the committed `.cairn/sync.json` (external-tracker mirroring config; only variable *names*, never secrets)
- `cairn/templates/context.json.example` - template for `.cairn/context.json` (context-mode scoping config)
- `.claude/settings.json` - local Claude Code settings for this repo checkout

## Platform Requirements

**Development:**
- macOS or Linux with `bash`, `python3`, `git`
- `bd` (beads) binary on `PATH`, version ≥ 1.1.0
- `bats-core` and `jq` for running the test suite
- Claude Code CLI to actually exercise the plugin's hooks/commands/capability end to end

**Production:**
- No deployed service — this ships as a Claude Code plugin distributed through a plugin marketplace (`.claude-plugin/marketplace.json`), installed per-project via `/plugin marketplace add FelipeOFF/CairnGo` + `/plugin install cairn@cairngo`
- CI target: `ubuntu-latest` (GitHub Actions, `.github/workflows/ci.yml`)

---

*Stack analysis: 2026-07-25*
