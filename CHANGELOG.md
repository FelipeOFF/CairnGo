# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **cairn detects a machine that already had GSD.** Installing cairn pulls
  `gsd-core` in as a dependency, and on a machine already running the 4.x `gsd`
  plugin it lands *beside* it rather than replacing it. Nothing errors, both
  provide the same workflow surface, and only one of them can host the
  capability — so `/gsd:*` can be answered by the plugin that cannot, while the
  capability is registered against the one that can and every check reports
  green. That is the same silent-success shape this line of work exists to
  remove.

  `/cairn:init` and `/cairn:doctor` now fail on it and name the plugin to
  uninstall. Absent or unparseable plugin state is never read as a collision:
  a machine whose state cairn cannot parse must not be told it has two GSDs.

## [1.4.1] - 2026-07-28

### Fixed

- **gsd-core would not load at all, so v1.4.0 shipped a migration into a dead
  dependency.** gsd-core 1.7.0 and 1.8.0 declare `"hooks": "./hooks/hooks.json"`
  in their own manifest — the standard path Claude Code already loads
  automatically. The loader treats it as a duplicate and refuses the **whole
  plugin** (`Status: ✘ failed to load`), so a user who followed cairn's own
  migration guide ended up with no `/gsd:*` commands.

  What hid it: the `gsd-tools` CLI keeps working, so the capability installs and
  registers happily against a plugin Claude Code will not load. The v1.4.0
  migration guide said the error "does not affect the fusion" — that was wrong,
  and is corrected.

  `/cairn:init` now removes that one line from the installed copy before
  installing the capability, `/cairn:doctor` re-checks it on every run (a
  gsd-core update restores the original file), and
  `cairn-capability.sh repair-manifest` does it on demand. The repair is narrow:
  it only removes a declaration naming the *standard* path, never one pointing
  at additional hook files.

  cairn patches rather than forks — you keep receiving genuine upstream code,
  with no vendored tree to rebase against a weekly release cadence. Upstream has
  the same one-line fix in
  [open-gsd/gsd-core#2077](https://github.com/open-gsd/gsd-core/pull/2077),
  closed twelve seconds after opening by automation requiring a pre-approved
  issue. When it lands, this repair becomes a no-op and the code can go.

## [1.4.0] - 2026-07-28

### Added

- **`/cairn:status` answers which phase to run, not just what work exists.**
  The board gained a phase panel: every pending phase described by title,
  requirement ids, where it stands (`not planned` / `planned` / `executed` /
  `verified`), plan progress and what it waits on — so choosing the next phase
  no longer means opening ROADMAP.md. Below it, the `/cairn:*` commands to run
  next, each with the reason it sits where it does. The command comes from that
  phase's own state on disk and the **order comes from the dependency graph**,
  so a blocked earlier phase is never listed above a later one that can
  actually run.
- **The board says what can proceed at the same time**, and describes the split
  in real commands ("`/cairn:plan 2` alongside `/cairn:plan 3`. One agent per
  phase, or one worktree each."). When no dependency is recorded anywhere it
  says so, rather than reporting every phase as independent and letting that
  read as a verified ordering.
- `/cairn:autonomous` resolves its phase order from the status model and
  **announces** it — the order, the reason for each position, and the
  concurrency available but unused — instead of deciding silently.
- `--json` exposes the whole model: `phases[]`, `next_commands[]` and
  `parallelism`, so other commands can stop re-deriving it.

### Changed

- The status surfaces read one shared phase model. The roadmap parser used to
  return two lists of phase numbers, which is why a phase could only render as
  `10` and why the HTML board had space it could not fill. Title, plan
  progress, milestone, requirement ids, dependencies and on-disk state are now
  read once and rendered by the terminal board, `--json` and the HTML page
  alike, so the three cannot drift.
- The HTML board uses the desktop it is opened on: the grid grows to 1440px on
  a wide screen instead of sitting in a fixed 1024px column, while prose keeps
  its own measure so the sentences stay readable.

- **cairn now depends on the official GSD, `open-gsd/gsd-core`**, pinned to a
  release tag. The previous dependency was the 4.x line
  (`jnuyens/gsd-plugin`), which has no capability system — so the beads fusion
  cairn is built around could never run on it. `/cairn:init`'s capability step
  was failing on every install and reporting success. Both halves are fixed.
  Existing installs do not follow a plugin rename: see
  [Migrating to GSD Core](cairn/docs/gsd-core-migration.md).

### Added

- `/cairn:init` installs the capability through `cairn-capability.sh`, which
  **verifies** the result instead of assuming it. GSD's own `capability list`
  must report cairn active, and the staged bundle must carry the scripts its
  gates run — a bundle staged without them leaves a ship gate that passes
  without checking anything. Failures name their cause and their fix.
- `/cairn:doctor` gained a `gsd-capability` check reporting which GSD lineage
  is installed and whether the capability actually registered. It fails rather
  than warns: a soft signal is how the original failure stayed invisible.
- CI runs gsd-core's own `validateCapability` against a pinned checkout on
  every pull request. A missing validator in CI now fails the run instead of
  skipping it.

### Removed

- **The `gsd` marketplace entry (the 4.x line).** Nothing in this marketplace
  publishes it any more. An install made before v1.4 keeps working from Claude
  Code's own plugin cache, but `claude plugin install gsd@cairngo` no longer
  resolves and neither does a marketplace refresh that tries to re-fetch it.
  Migrate with [the guide](cairn/docs/gsd-core-migration.md) — it leaves
  `.planning/` and `.beads/` untouched — and check with `/cairn:doctor`.

  This is a shorter path than GSD-04 planned for. That requirement asked for the
  old entry to survive one release cycle; the decision to drop it in the same
  release that introduces the migration was taken deliberately, with the cost
  understood. The documented migration path is unchanged and still works.

## [1.3.0] - 2026-07-27

### Fixed

- `/cairn:migrate` closes phases the roadmap marks complete even when
  `SUMMARY.md` and `VERIFICATION.md` are absent from disk. A repository that
  delivered its phases before adopting cairn previously came out of migration
  with every one of those phases open, and the dependency edges between them
  blocked the phases that followed. Failed steps are now retried once,
  journaled, and replayed on the next run; `apply` exits 8 when anything
  failed instead of reporting success.
- `/cairn:status` warns when open issues belong to phases the roadmap calls
  complete, and its suggested next action skips them.

### Added

- `/cairn:doctor` gained a `phase-complete-open` check and a
  `--close-completed` repair for databases already migrated by an older
  version. Closes run in repeated passes so a whole dependency chain drains in
  one invocation, and anything bd refuses is reported with its reason and
  exits 7.
- `gbsync import` brings existing Jira issues into bd by JQL or project key.
  `detect` reports whether a repository looks like it tracks work in Jira, and
  `/cairn:init` and `/cairn:migrate` surface that without configuring anything.
- Published benchmark results: 120 runs across four arms, with the finding
  that no arm is measurably cheaper on the current corpus. See BENCHMARKS.md.

### Changed

- Every command's argument hint, body and reference page now lists the flags
  it actually accepts. `/cairn:quick --full` was accepted but undocumented.

## [1.2.0] - 2026-07-25

### Added

- `/cairn:autonomous [start-phase]` — run every remaining phase hands-off
  through the full cairn loop (map → plan → claim → execute → close →
  verify per phase), with `cairn-doctor` checkpoints between phases,
  explicit stop rules (doctor failure, unrecoverable execution, unclosable
  verification gap, bd unavailable, ship gate blocked) and a resume path
  that skips completed phases. Stops at the ship gate — the push stays a
  human decision. The beads-aware counterpart of `/gsd:autonomous`.

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
