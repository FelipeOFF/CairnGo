<!-- refreshed: 2026-07-25 -->
# Architecture

**Analysis Date:** 2026-07-25

## System Overview

CairnGo is not an application with a runtime process — it is a **Claude Code
plugin marketplace repo** whose product is prose (slash commands, skills) plus
a set of deterministic CLI scripts that those prose commands and Claude Code
hooks invoke. There is no server, no build step, no compiled artifact. The
"architecture" is the wiring between three external tools (GSD, `bd`/beads,
context-mode) plus the enforcement layers cairn adds on top.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                     Claude Code session (the agent)                      │
├────────────────────────────┬──────────────────────────┬─────────────────┤
│  /cairn:* slash commands    │   `cairn` + `cairn-sync`  │  GSD capability │
│  `cairn/commands/*.md`      │   + `cairn-context` skills│  contributions  │
│  (prose, thin wrappers)     │   `cairn/skills/*/SKILL.md`│ `cairn/capability/`│
└──────────────┬──────────────┴──────────────┬─────────────┴────────┬──────┘
               │ invokes                     │ conventions           │ injected at
               ▼                             │ (no code)             │ plan/execute/
┌──────────────────────────────────────────┐ │                       │ verify/ship
│   Deterministic CLI scripts (tested)      │ │                       │ loop points
│   `cairn/scripts/*.sh` -> `*.py`          │◄┘                       ▼
│   cairn-init, cairn-gate, cairn-map,      │            ┌────────────────────────┐
│   cairn-migrate, cairn-doctor, cairn-     │            │ capability bundle       │
│   relabel, gbsync                         │            │ `cairn/capability/`     │
└───────────────┬────────────────────────────┘            │ fragments/*.md (prose   │
                │ shells out to `bd --json`                │ injected into planner/  │
                ▼                                           │ executor/orchestrator) │
┌──────────────────────────────────────────┐               │ scripts/cairn-loop-     │
│  beads (`bd`) — external binary           │               │ gate.py (ship gate)     │
│  `.beads/` (never read directly)          │               └────────────────────────┘
└───────────────┬────────────────────────────┘
                │ mirrored via
                ▼
┌──────────────────────────────────────────┐
│  cairn/adapters/*.py (hub-and-spoke sync) │
│  GitHub · GitLab · Jira · Asana · Azure   │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  Claude Code hooks (`cairn/hooks/`)  — the layer that runs without a     │
│  prompt: SessionStart (nudge/inject), PostToolUse on Bash (mirror push + │
│  map refresh after `bd` writes), Stop (in_progress warning)              │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  git `pre-push` shim (installed by cairn-init.sh) — re-runs cairn-gate   │
│  outside any LLM, blocks a push only on gate exit 6                      │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Slash commands | Prose entry points the user/agent types (`/cairn:init`, `/cairn:ship`, …); thin wrappers that shell out to scripts or delegate to skills | `cairn/commands/*.md` |
| Skills | Conventions the agent follows when no code enforces them (label pairs, metadata stamps, precedence rules) | `cairn/skills/cairn/SKILL.md`, `cairn/skills/cairn-sync/SKILL.md`, `cairn/skills/cairn-context/SKILL.md` |
| GSD capability bundle | Registers cairn at GSD's loop points (`plan:post`, `execute:wave:pre`, `execute:wave:post`, `verify:post`, `ship:pre`) so plain `/gsd:*` does beads bookkeeping | `cairn/capability/capability.json`, `cairn/capability/fragments/*.md` |
| Bundled loop-gate script | Self-contained copy of the ship gate the capability bundle runs (no dependency on the plugin's own scripts dir once staged) | `cairn/capability/scripts/cairn-loop-gate.py`, `cairn-loop-gate.sh` |
| Deterministic scripts | The tested surface — init, gate, map generation, migration, doctor, relabel, sync dispatch | `cairn/scripts/*.py` (paired with thin `.sh` wrappers) |
| Sync adapters | One executable per external tracker; HTTP happens here, never in the dispatcher | `cairn/adapters/*.py`, contract in `cairn/adapters/_contract.md` |
| Claude Code hooks | Code that runs automatically around the session lifecycle, not on user request | `cairn/hooks/hooks.json`, `session-start.sh`, `post-bd-write.sh`, `session-stop.sh` |
| git pre-push shim | Generated (not committed) shell script installed into `.git/hooks/pre-push`, re-runs the gate outside Claude Code entirely | written by `cairn/scripts/cairn-init.sh` |
| beads (`bd`) | External binary; sole owner and source of truth for work items | `.beads/` (opaque; always accessed via `bd … --json`) |
| GSD | External plugin dependency; sole owner of the plan (roadmap/phases/requirements) | `.planning/*.md` (parsed leniently, never written except generated maps) |
| context-mode | External plugin dependency; sole owner of compressed session memory | reached only through `ctx_*` tools |

## Pattern Overview

**Overall:** Integration/glue-layer architecture — a **hub-and-spoke bridge**
between three independently-owned systems, expressed as (1) prose that an LLM
agent reads and follows, and (2) small, single-purpose CLI scripts that do the
one thing prose cannot be trusted to do deterministically. There is no
persistent process, no database, no framework; the plugin is discovered and
loaded by Claude Code's plugin marketplace mechanism at session start.

**Key Characteristics:**
- **Enforcement is layered by strength**, documented explicitly in
  `cairn/docs/architecture.md` — GSD capability code > Claude Code hooks > git
  pre-push shim > prose convention. New behavior is expected to justify
  landing below layer 2 rather than being added as prose only.
- **Everything deterministic is a script with a CLI contract**, tested by
  bats against fixture repos; prose commands are "thin wrappers" that are
  explicitly *not* tested directly (see `tests/README.md`).
- **`.sh` files are exec-only wrappers.** Every meaningful script is Python
  (`cairn/scripts/*.py`, stdlib only); the matching `.sh` file just resolves
  its own directory and `exec python3 that.py "$@"`. Hooks (`cairn/hooks/*.sh`)
  are the exception — those are real bash because they parse the Claude Code
  hook JSON payload and shell out.
- **Nothing is a source of truth except the external tool that owns it.**
  Generated files (`NN-BEADS-MAP.md`, `.cairn/id-map.json`) are always
  regenerable from `bd … --json` and are treated as views, never edited by
  hand inside their generated-marker blocks.
- **Hub-and-spoke, never spoke-to-spoke.** External trackers (GitHub, GitLab,
  Jira, Asana, Azure Boards) only ever talk to `bd`; two external trackers
  never talk to each other.
- **No-op by design in non-beads repos.** Every bundled script checks for
  `.beads/`/`.planning/` and the `cairn.enabled` config key first and exits 0
  silently if the integration does not apply — GSD (and this repo's other
  tooling) behaves exactly as it would without cairn installed.

## Layers

**Prose layer (commands + skills):**
- Purpose: human/agent-facing entry points and conventions with no
  deterministic guarantee
- Location: `cairn/commands/*.md`, `cairn/skills/*/SKILL.md`
- Contains: markdown with YAML frontmatter (`description`, sometimes
  `argument-hint`), imperative instructions, embedded bash snippets the agent
  is told to run
- Depends on: the scripts layer (nearly every command's real work is `bash
  "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh" …`)
- Used by: the user (typed `/cairn:*`) and the agent (reads skills as
  standing conventions when both `.planning/` and `.beads/` are present)

**Capability layer (GSD extension point):**
- Purpose: make plain `/gsd:*` commands do beads bookkeeping without the user
  ever typing `/cairn:*`
- Location: `cairn/capability/` (manifest `capability.json`, prose
  `fragments/*.md` injected into GSD's planner/executor/orchestrator at named
  loop points, plus a bundled copy of the gate script under
  `capability/scripts/`)
- Depends on: GSD's capability contract (`plan:post`, `execute:wave:pre`,
  `execute:wave:post`, `verify:post`, `ship:pre`) and `engines.gsd >=1.8.0`
  pinning
- Used by: `/cairn:init` step 2, which stages the bundle at
  `.gsd/capabilities/cairn/` via `gsd capability install`

**Scripts layer (the tested surface):**
- Purpose: everything that must be correct and idempotent — init wiring, the
  ship gate, map generation, migration, health checks, relabeling, sync
  dispatch
- Location: `cairn/scripts/*.py` (+ `.sh` wrapper of the same base name)
- Depends on: Python stdlib only ("the sync layer must run anywhere Claude
  Code runs" — `CONTRIBUTING.md`), the `bd` CLI via `subprocess`, and
  `.planning/*.md` read as plain text
- Used by: prose commands, Claude Code hooks, the capability bundle, the git
  pre-push shim, and bats tests directly

**Adapter layer (external tracker sync):**
- Purpose: isolate the one thing that talks HTTP to a third party
- Location: `cairn/adapters/*.py`, one file per backend (`github.py`,
  `gitlab.py`, `jira.py`, `asana.py`, `azure-boards.py`), contract documented
  in `cairn/adapters/_contract.md`
- Depends on: a JSON object on stdin / JSON (or bare string) on stdout — no
  shared code with the dispatcher beyond that contract
- Used by: `cairn/scripts/gbsync.py`, the dispatcher, which is the only
  caller and never inspects an adapter's internals

**Hooks layer (ambient automation):**
- Purpose: run without any explicit user/agent action, around the Claude
  Code session lifecycle
- Location: `cairn/hooks/hooks.json` (registration) + `session-start.sh`,
  `post-bd-write.sh`, `session-stop.sh`
- Depends on: Claude Code's hook JSON payload on stdin (`PostToolUse`) or
  plain execution (`SessionStart`, `Stop`); shells out to `cairn/scripts/`
- Used by: Claude Code itself, matched by event name (`SessionStart`,
  `PostToolUse` on the `Bash` tool, `Stop`)

**git layer (outside-the-agent enforcement):**
- Purpose: hold the ship gate even when nobody is inside a Claude Code
  session (a bare `git push`)
- Location: generated into `.git/hooks/pre-push` by
  `cairn/scripts/cairn-init.sh` (not a tracked file — templated inline in the
  init script)
- Depends on: `cairn/scripts/cairn-gate.sh`/`cairn-gate.py`
- Used by: git itself on every `push`

## Data Flow

### Primary lifecycle: plan -> execute -> verify -> ship

1. `/gsd:plan-phase N` runs; the GSD planner reaches the `plan:post` loop
   point, which injects `cairn/capability/fragments/plan-post.md`: resolve
   `PLAN.md` requirements against `bd list -l m-<milestone>,phase-<N>`,
   `bd create` any unmapped requirement (dedup key `(gsd.req,
   gsd.milestone)`), write `beads:` frontmatter on `PLAN.md`, then regenerate
   `<NN>-BEADS-MAP.md` via `cairn-map.sh <N>` (`cairn/capability/fragments/plan-post.md:11-39`).
2. `/gsd:execute-phase N` dispatches a wave; at `execute:wave:pre` the
   `execute-wave-pre.md` fragment claims every id in the plan's `beads:`
   frontmatter with `bd update <id> --claim` (`cairn/capability/fragments/execute-wave-pre.md:12-17`).
3. Every `bd create|update|close|reopen` the agent runs is a `Bash` tool
   call, which fires the `PostToolUse` hook `cairn/hooks/post-bd-write.sh`
   (`cairn/hooks/hooks.json:16-27`). The hook parses the command from stdin
   JSON, extracts the verb/issue id/phase, and — always exiting 0, never
   failing the tool call — backgrounds (a) a mirror push via
   `gbsync.sh <verb> <id>` when `.cairn/sync.json` has an enabled backend,
   and (b) a `cairn-map.sh <phase>` refresh when the command string mentions
   `phase-<N>` (`cairn/hooks/post-bd-write.sh:1-150`).
4. At `execute:wave:post` the fragment closes each claimed id with
   `bd close --reason "<one-line SUMMARY digest>"`, then refreshes the map
   again.
5. `/gsd:verify-work` reaches `verify:post`, which cross-checks `bd` open
   state against the VERIFICATION report.
6. `/gsd:ship` reaches the **blocking** `ship:pre` gate: a
   `command-exit-zero` predicate that runs
   `cairn-loop-gate.sh ship-gate --phase <N>` — the bundled, self-contained
   copy of the gate logic staged under `.gsd/capabilities/cairn/scripts/`
   (`cairn/capability/capability.json:108-122`). Semantics: fail if any
   completed phase (per `ROADMAP.md`) has a non-closed `bd` issue labeled
   `phase-<N>` for the active milestone (`cairn/scripts/cairn-gate.py:1-46`,
   the standalone twin of the bundled script).
7. Independently of any of the above, a bare `git push` re-runs the same
   gate logic via the `pre-push` shim installed by `cairn-init.sh`; it blocks
   **only** on gate exit 6 (open issues) and warns-but-allows on exit 5 (`bd`
   unavailable) (`cairn/scripts/cairn-init.sh:79-142`).

### Secondary flow: sync mirror push (bd -> external tracker)

1. A `bd` lifecycle write triggers `post-bd-write.sh` (see step 3 above).
2. `cairn/scripts/gbsync.py` (dispatcher) reads `.cairn/sync.json` for
   enabled backends, looks up the issue's `external_id` in
   `.cairn/id-map.json`, and calls the matching adapter under
   `cairn/adapters/` with one JSON object on stdin
   (`cairn/adapters/_contract.md:11-41`).
3. The adapter does the HTTP call and prints the external id as a bare
   string on stdout; the dispatcher persists it back into
   `.cairn/id-map.json`.
4. Sync is strictly hub-and-spoke: adapters never call each other, and `bd`
   is always the source of truth being pushed outward.

### Secondary flow: migration (adopting an existing repo)

1. `/cairn:init` step 0 runs `cairn-migrate.sh detect`, which classifies the
   repo into one of five states (A/B/C/W/D — see `cairn/docs/architecture.md`
   "Migration modes").
2. `cairn-migrate.py` (the largest script in the repo at ~1,750 lines) walks
   `detect -> plan -> confirm -> apply`: `plan` is read-only (writes only
   `.cairn/migrate-plan.json`), sensitive steps are held as
   `pending_confirmation` until the user approves, and a JSONL journal in
   `.cairn/migrate-state.json` makes the whole run resumable without
   duplicating writes.
3. Issue creation during migration is sequential `bd create` calls, never
   `bd create --graph` (a version quirk in `bd` 1.1.0 flattens nested
   `--metadata`, which would corrupt the queryable `gsd` stamp).

**State Management:**
There is no application state beyond files on disk: `.planning/*.md` (GSD,
read leniently, never hand-written by cairn except generated map blocks),
`.beads/` (opaque, only touched via the `bd` CLI), and `.cairn/` (cairn's own
local state — `sync.json` is the only committed file; `id-map.json`,
`state.json`, `conflicts.json`, and `migrate-*.json` are per-machine and
gitignored by `cairn-init.sh`). Every generated artifact is idempotently
regenerable from its source of truth, which is the mechanism that lets the
whole system have no long-lived process or cache to go stale.

## Key Abstractions

**Loop-point contribution (GSD capability):**
- Purpose: inject prose into GSD's own workflow at a named point without
  forking GSD
- Examples: `cairn/capability/fragments/{plan-post,execute-wave-pre,execute-wave-post,verify-post}.md`
- Pattern: each fragment declares (in `capability.json`) the `point` it
  attaches to, `into` which GSD role, a `when` gate (`cairn.enabled`), and
  `onError: skip` so a broken fragment never blocks the host loop

**Gate (blocking predicate):**
- Purpose: a deterministic yes/no check GSD or git can enforce without an
  LLM in the loop
- Examples: `cairn/scripts/cairn-gate.py` (standalone), `cairn/capability/scripts/cairn-loop-gate.py` (bundled copy used by the capability)
- Pattern: `command-exit-zero` predicate — exit code is the entire contract
  (0 = pass, nonzero = specific documented meaning); the capability manifest
  and the git shim both branch only on exit code, never on stdout

**Generated view (never a source of truth):**
- Purpose: give humans a readable artifact without creating a second place
  that can drift from `bd`
- Examples: `NN-BEADS-MAP.md` (regenerated by `cairn-map.py` between
  `<!-- cairn:generated:start -->`/`<!-- cairn:generated:end -->` markers),
  `.cairn/id-map.json`
- Pattern: idempotent regeneration; content outside the markers (or files
  entirely outside the generated set) is preserved

**Adapter (uniform external-system boundary):**
- Purpose: let five unrelated tracker APIs plug into one dispatcher with zero
  shared code
- Examples: `cairn/adapters/github.py`, `gitlab.py`, `jira.py`, `asana.py`,
  `azure-boards.py`
- Pattern: stdin JSON in, stdout (string or JSON array) out, exit 0/nonzero;
  language-agnostic by contract (`.py`/`.sh`/extensionless all auto-detected)

**Script/wrapper pair:**
- Purpose: give every script both a stable, dependency-free shell entry point
  and a real implementation
- Examples: `cairn-gate.sh` -> `cairn-gate.py`, `cairn-map.sh` -> `cairn-map.py`, `cairn-migrate.sh` -> `cairn-migrate.py`, `cairn-doctor.sh` -> `cairn-doctor.py`, `cairn-relabel.sh` -> `cairn-relabel.py`, `gbsync.sh` -> `gbsync.py`
- Pattern: the `.sh` file is ~7-10 lines, resolves `$HERE` from
  `BASH_SOURCE[0]`, and does `exec python3 "$HERE/<name>.py" "$@"` — nothing
  else lives in the wrapper

## Entry Points

**Slash commands (`/cairn:*`):**
- Location: `cairn/commands/*.md` — one file per command
  (`init`, `migrate`, `doctor`, `status`, `progress`, `plan`, `work`, `verify`,
  `ship`, `new`, `quick`, `milestone`, `issues`, `bd`, `gsd`, `help`,
  `remember`, `recall`, `context-config`, `sync-config`, `sync-pull`, `ctx`)
- Triggers: the user (or agent on their behalf) typing the command in a
  Claude Code session
- Responsibilities: orchestrate scripts and skills in prose; `cairn/commands/bd.md`
  is the raw passthrough (`bd $ARGUMENTS`) for anything the curated verbs
  don't cover

**GSD capability contributions:**
- Location: `cairn/capability/capability.json` (manifest) +
  `cairn/capability/fragments/*.md` (injected prose) +
  `cairn/capability/scripts/cairn-loop-gate.{sh,py}` (bundled gate)
- Triggers: GSD's own loop reaching `plan:post`, `execute:wave:pre`,
  `execute:wave:post`, `verify:post`, or `ship:pre` in a repo where the
  bundle is installed and `cairn.enabled` is true
- Responsibilities: everything a plain `/gsd:*` command needs to also do
  beads bookkeeping, with no `/cairn:*` verb typed at all

**Claude Code hooks:**
- Location: `cairn/hooks/hooks.json` (registration), `session-start.sh`,
  `post-bd-write.sh`, `session-stop.sh`
- Triggers: `SessionStart` (`startup|clear|compact`), `PostToolUse` matched
  on the `Bash` tool, `Stop`
- Responsibilities: first-run bootstrap nudges, migration nudges, the
  cairn-conventions reminder injected as session context, background mirror
  push + map refresh after `bd` writes, and an end-of-session warning about
  issues still claimed by the current actor

**git `pre-push` hook:**
- Location: templated and written into `.git/hooks/pre-push` by
  `cairn/scripts/cairn-init.sh` (not itself a tracked file)
- Triggers: `git push` from anywhere, including outside any Claude Code
  session
- Responsibilities: chain any pre-existing hook first, then run
  `cairn-gate.sh --planning-dir <repo>/.planning` and block only on exit 6

**Codex-runtime hooks (parallel, non-Claude-Code):**
- Location: `.codex/hooks.json`, `.codex/config.toml`
- Triggers: `PostCompact`, `PreCompact`, `SessionStart`, `UserPromptSubmit`
  inside a Codex CLI session
- Responsibilities: delegate to `bd codex-hook <event>` — a separate, beads
  ("bd") owned integration path for agent runtimes other than Claude Code;
  not part of the cairn plugin itself, but present so this repo's own
  development loop (which is dogfooded on beads) works under Codex too

## Architectural Constraints

- **No shared process / no in-memory state.** Every script is a short-lived
  CLI invocation; all coordination happens through files (`.planning/`,
  `.beads/` via `bd`, `.cairn/`) or subprocess exit codes. There is nothing
  resembling a server, a job queue, or a long-running daemon.
- **Backgrounding via `nohup … &`, not a task runner.** `post-bd-write.sh`
  explicitly backgrounds its two jobs (mirror push, map refresh) so the
  `PostToolUse` hook returns immediately; there is no retry queue — a failed
  background job is only visible in its own process's exit code, unobserved
  by the hook.
- **Version pin surface is narrow and explicit.** The only real
  cross-plugin version guarantee is `engines.gsd: ">=1.8.0"` in
  `cairn/capability/capability.json`; `bd` compatibility is a soft runtime
  check (`cairn-init.sh` compares `bd version` against `BD_MIN_VERSION` and
  only warns).
- **Python stdlib only.** `CONTRIBUTING.md` mandates this for
  `cairn/scripts/*.py` and `cairn/adapters/*.py` — "the sync layer must run
  anywhere Claude Code runs" — so there is no `requirements.txt`, no venv,
  no pip install step anywhere in the repo.
- **`.beads/` internals are never a read/write surface.** Every access to
  beads state goes through `bd … --json`; grepping for direct
  `.beads/` file reads outside of existence checks (`[ -d .beads ]`) is a
  correctness bug by the architecture's own rules.
- **Dual command surface, single mechanism.** `/cairn:*` and plain `/gsd:*`
  (with the capability installed) are meant to produce identical bd
  bookkeeping — the capability fragments and the `/cairn:*` command prose
  describe the same conventions from two entry points, so a change to one
  convention (label pair, metadata stamp, dedup key) must be mirrored in
  both `cairn/skills/cairn/SKILL.md` and the relevant `cairn/capability/fragments/*.md`.

## Anti-Patterns

### Hand-editing a generated block

**What happens:** Someone edits text between
`<!-- cairn:generated:start -->` and `<!-- cairn:generated:end -->` inside an
`NN-BEADS-MAP.md`.
**Why it's wrong:** The next `cairn-map.sh <N>` run (fired automatically by
`post-bd-write.sh` on the next `bd` write mentioning that phase) silently
overwrites the edit — there is no diff/merge step, only full regeneration.
**Do this instead:** Put manual notes outside the marker block (they survive
regeneration), or change the underlying `bd` issue/metadata and let the next
regeneration pick it up.

### Reading `.beads/` files directly

**What happens:** A script or command reaches into `.beads/*.jsonl` or
similar instead of calling `bd … --json`.
**Why it's wrong:** `.beads/` internals are explicitly not an integration
surface (`cairn/docs/architecture.md` "Version compatibility") — the on-disk
format is beads' own concern and can change between `bd` versions without
notice; only the CLI's `--json` output is a contract.
**Do this instead:** Shell out to `bd <verb> … --json` and parse stdout, the
same way every script in `cairn/scripts/` and `cairn/adapters/` already does.

### Landing new deterministic behavior as prose only

**What happens:** A new rule ("always do X before Y") gets added only to a
`SKILL.md` or a command's `.md` file, with no backing script.
**Why it's wrong:** `CONTRIBUTING.md` calls this out directly — "Scripts over
prose... If a SKILL.md sentence can be a script check, make it one" — because
prose-only rules are unenforceable and untestable (bats only exercises
script CLIs, never prose).
**Do this instead:** Implement the check/behavior as a script under
`cairn/scripts/` (or the capability bundle's `capability/scripts/`) with its
own `.bats` file, then have the prose command/skill call it.

## Error Handling

**Strategy:** Exit codes are the entire contract for every deterministic
script; each script's module docstring enumerates every exit code and its
exact meaning (see `cairn-gate.py`, `cairn-map.py` docstrings). Hooks are the
one place that deliberately swallow errors: `post-bd-write.sh` always exits 0
so a hook failure never blocks the user's actual `Bash` tool call.

**Patterns:**
- `die(msg, code)` helper in every gate/map/relabel script — prints to
  stderr prefixed with the script's own name (`[cairn-gate] error: …`), then
  `sys.exit(code)`.
- Availability failures (e.g. `bd` not on PATH) are a distinct exit code
  (5) from logical gate failures (6) everywhere the distinction matters, so
  callers like the pre-push shim can choose to warn-and-allow versus block.
- Adapter and hook failures are isolated: `gbsync.py` logs a nonzero adapter
  exit and continues with the remaining backends rather than aborting the
  whole sync; capability contributions declare `onError: skip` so one broken
  fragment never blocks the GSD loop it's injected into.

## Cross-Cutting Concerns

**Logging:** No structured logging framework. Scripts print human-readable
lines to stdout/stderr (optionally JSON via a `--json` flag on
gate/map/doctor scripts for machine consumption); hooks print at most one
short line to stdout, which Claude Code surfaces as session context.

**Validation:** Input validation is manual argv parsing per script
(`parse_args` functions with a `die()` on bad usage) — no CLI framework
(argparse is deliberately avoided in favor of hand-rolled loops in most
scripts, keeping stdlib-only and dependency-free).

**Authentication:** Only relevant for the sync adapters — each adapter reads
its API token from an environment variable *named* in `.cairn/sync.json`
(`"token_env": "JIRA_API_TOKEN"`); secrets are never written to disk by any
cairn code (`cairn/adapters/_contract.md` "Secrets").

---

*Architecture analysis: 2026-07-25*
