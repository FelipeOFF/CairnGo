# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-25

### Added

- `/cairn:status` now renders a deterministic kanban board (READY / DOING /
  BLOCKED lanes) via the new `cairn-status.py` script: dual-mode output
  (TTY board, clean `--plain` in pipes, one-line `--json`, 3-line
  `--brief`), width-aware degradation, full color-precedence chain
  (`--color` > `CAIRN_NO_COLOR` > `NO_COLOR` > `TERM=dumb` > isatty),
  `--ascii` fallback, CJK-aware truncation, and a synthesized single next
  action in the footer. 22 bats tests, including adversarial
  control-byte injection. ([#3](https://github.com/FelipeOFF/CairnGo/issues/3),
  [#4](https://github.com/FelipeOFF/CairnGo/pull/4))
- Per-command reference documentation: one page for each of the 22
  commands under `cairn/docs/commands/` plus a grouped index at
  `cairn/docs/commands.md`, linked from both READMEs.

## [1.0.0] - 2026-07-25

First release of the CairnGo fork
([FelipeOFF/CairnGo](https://github.com/FelipeOFF/CairnGo)). The spec behind
this release is
[issue #1](https://github.com/FelipeOFF/CairnGo/issues/1): deep GSD↔beads
unification, automatic migration, and the fork rebrand.

### Added

- **GSD capability fusion** (`cairn/capability/`) — cairn installs into
  `.gsd/capabilities/cairn/` and hooks the sanctioned loop points, so plain
  `/gsd:plan-phase`, `/gsd:execute-phase`, `/gsd:verify-work`, and `/gsd:ship`
  create, claim, close, and gate bd issues without the `/cairn:*` wrappers:
  `plan:post` (frontmatter + map), `execute:wave:pre` (claim),
  `execute:wave:post` (close with a SUMMARY-derived reason), `verify:post`
  (cross-check), and a blocking, deterministic `ship:pre` gate.
- **`/cairn:migrate`** + `scripts/cairn-migrate` — adopt existing repos:
  GSD-only backfill (mode A), beads-only bootstrap (mode B), and
  both-present-but-unwired reconcile (mode C), with state detection (also
  step 0 of `/cairn:init`), a dry-run plan before any mutation, journaled
  resume via `.cairn/migrate-state.json`, and idempotent re-runs.
- **`/cairn:doctor`** + `scripts/cairn-doctor` — nine-check deterministic
  consistency audit (bd minimum version, requirement↔issue coverage,
  `beads:` frontmatter ids, map freshness, superseded plans, orphans,
  label pairs, stale claims, and `bd doctor` delegation) with a
  `--fix-labels` repair.
- **Ship gate + git shim** — `scripts/cairn-gate` fails when a completed
  phase still has non-closed issues; `cairn-init.sh` installs a chainable git
  `pre-push` shim so the gate holds even with no LLM in the loop.
- **Claude Code hooks** (`cairn/hooks/`) — SessionStart context injection and
  migration nudges, PostToolUse mirror push + phase-map refresh after
  `bd create/update/close`, and a Stop warning for stale `in_progress`
  claims.
- **Deterministic script layer** — `cairn-map` (generated `NN-BEADS-MAP.md`
  from bd state) and `cairn-relabel` (milestone label pairing, phase
  renumbering) join the gate, migrate, and doctor engines above; the prose
  commands are thin wrappers over these scripts.
- **New verbs** — `/cairn:milestone new|complete` (rollover and closeout
  without orphaning maps or issues), `/cairn:quick` (tracked side-quests with
  a `discovered-from` dependency), and a bd-ready-driven `/cairn:status`.
- **Test harness + CI** — bats suites under `tests/` run the scripts against
  fixture repos with a real `bd` (skipping cleanly when it is absent), wired
  into GitHub Actions.

### Changed

- Label scheme: every managed issue now carries the pair `m-<milestone>` +
  `phase-<N>`, so phase numbers that repeat across milestones cannot corrupt
  gates or views.
- `NN-BEADS-MAP.md` is now a **generated** artifact rendered from
  `bd list --json` between markers, not a hand-maintained table; manual notes
  outside the markers survive regeneration.
- Every managed issue carries a `{"gsd": {"req", "phase", "milestone",
  "plan"}}` metadata stamp; `(gsd.req, gsd.milestone)` is the dedup key for
  idempotent creation and migration.
- The ship gate blocks on any **non-closed** status (open, in_progress,
  blocked, deferred, …), not just open issues.
- Context-mode documentation (`docs/context.md`, `/cairn:context-config`, the
  `cairn-context` skill) rewritten for the real on-by-default model.
- Fork identity: repository references now point at `FelipeOFF/CairnGo` and
  the marketplace is `cairngo` (`/plugin install cairn@cairngo`). The GSD
  marketplace entry keeps tracking upstream `jnuyens/gsd-plugin`, with
  compatibility pinned by the capability's `engines.gsd`.

### Fixed

- Zero-padded phase-directory glob in the plan flow resolving the wrong (or
  no) phase directory.
- Redundant claim chain: `bd update --claim` already sets `in_progress`; the
  extra `--status` call is gone.
- `gbsync --dry-run` was accepted but silently ignored — now implemented.
- Generated `.cairn/` state files (`id-map.json`, `state.json`,
  `conflicts.json`) are gitignored by `cairn-init.sh`.

### Removed

- npm distribution mirror (`cairn/package.json`, `cairn/.npmignore`) — the
  plugin marketplace is the only install path.
- Opt-in install beacon and stats tooling (`cairn-ping.sh`,
  `cairn-stats.sh`, the init telemetry step, and the beacon sections of
  `PRIVACY.md`). Cairn now collects nothing at all.

## [0.9.3] and earlier

Upstream history as `cairn` in
[eventually-consistent-code/claude-plugins](https://github.com/eventually-consistent-code/claude-plugins)
by John Reed (eventually-consistent-code) — the origin of this fork.
