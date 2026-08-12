# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-08-12

First release of CairnGo as a standalone project.

CairnGo is a Claude Code plugin for structured phase planning where the issue
tracker owns the state. You plan and execute with `/cairn:*` commands; every
work item is created, claimed, closed and gated in `bd` — a git-native issue
tracker — without you touching it. The GSD planning runtime ships **inside**
the plugin, so there is one thing to install and no second plugin to keep in
step.

### What ships

- **One plugin, no external runtime.** The GSD runtime is vendored from
  `open-gsd/gsd-core` (MIT) at a pinned tag. The doctor treats a second GSD
  lineage as a finding with an uninstall prescription: two plugins answering
  the same command is a defect, not a configuration.

- **State has exactly one owner.** Workflows, steps and agents do not read
  markdown to learn where the project is; they call a verb and read its exit
  code. Markdown remains what humans read and write — PROJECT, ROADMAP,
  CONTEXT, PLAN, SUMMARY — and nothing consults it to decide anything.

- **A doctor that reports what it did not measure.** Four states, not two:
  `ok`, `not-applicable`, `warn`, `fail`. A check with no input says so
  instead of counting as green, because a surface that answers without
  knowing what it is answering about does not count as done.

- **Closing a phase is one invocation, idempotent.** `cairn-bookkeep close
  <N> --apply` ticks the roadmap and its requirements, moves the counters,
  regenerates the beads map, releases the lease and removes the worktree —
  in the right order, which a hand edit does not warn about getting wrong.

- **Two-way sync, opt-in.** GitHub Issues, GitLab, Jira, Asana and Azure
  Boards, with `bd` as the hub and source of truth.

### Known limits

cairn vendors the four cycle verbs — discuss, plan, execute, verify — and
nothing else. `/cairn:new`, `/cairn:milestone` and `/cairn:ship` name eight
verbs this plugin does not carry; with a GSD plugin installed alongside the
declared passthrough runs them, and without one you do the creation and
archiving steps yourself. Each affected step says so in its own text, and
`cairn/gsd-parity.json` locks the list in both directions.

Planning artifacts are still written as markdown. Making them queryable
records instead of files is the next milestone's goal.

### Upgrading

Nothing to upgrade from — this is the first release of this repository. On a
machine carrying an older GSD lineage from a previous install:

```bash
claude plugin uninstall gsd-core@cairngo   # or: gsd@4.x
/reload-plugins
```

`cairn-doctor` exits 7 until that is done, and names the plugin it found.

### Notes

The development history that produced this release predates this repository.
It is summarized, milestone by milestone, in `.planning/milestones/`.

The suite is 1161 tests across 51 files and runs in CI on every pull request;
`cairn/scripts/cairn-test.sh` is the one door, here and locally.

---

<details>
<summary>Development history before 1.0.0 (not released from this repository)</summary>

## [1.7.0] - 2026-08-12

The GSD runtime lives here now, and it asks the issue tracker instead of reading
markdown. A writer and a verifier that share the same wrong rule agree, and the
agreement reads as health — this cycle spent most of its effort proving that the
things which said "green" had actually looked.

### Added

- **The prompt layer asks the binary for state.** Every workflow, step and agent
  that used to read `.planning/STATE.md` to learn where the project is now calls
  a verb and reads its exit code. The measurement that made this safe is the
  oracle: three families, not a grep for a filename, because 12 measured lines
  reference state without naming the file and would have escaped — declaring a
  coverage that does not exist. A fourth family covers state paths injected into
  subagent prompts, where the read happens outside the workflow and a coverage
  measured inside it reports green while the subagent keeps reading markdown.

  Final measurement across the 66 files in scope: all four families at zero.
  Calls to `node` in the GSD infrastructure went from 14 to 7, with zero left
  under `gsd-core/workflows/`; the 7 that remain are 2 in the verifier (which
  check the user's own application, not this runtime) and 5 in `references/`.

- **Two doctor checks, each born from a measured defect.**
  `issues-recoverable` exists because a clean clone recovered **none** of the 176
  issues while the documentation had been stating in writing, for weeks, that the
  JSONL was a passive export. It was never born, because bd ships `export.auto`
  disabled.

  `export-identity` is its sibling: the first proves the export exists, the
  second proves it is safe to hand to every clone of a public repository. It
  splits findings by author, and that split is the whole design — prose fails
  because a human can clear it, a tool-written value warns because scrubbing it
  by hand is undone by the next run, and a check that spends exit 7 on something
  the user cannot durably clear teaches people to ignore exit 7.

- **A parity gate with the decision written down.** Ten commands still named
  eight verbs outside the closure. Vendoring them would have doubled the vendored
  tree, and every added file is drift against the pinned upstream tag, so they
  are declared unvendored in the step text itself, with both routes named. The
  remaining 11 mentions are locked in `cairn/gsd-parity.json` in both directions:
  a mention with no record fails, and a record with no mention fails too.

### Changed

- **The plugin no longer depends on `gsd-core`.** It leaves `marketplace.json`
  and the plugin's `dependencies`, the commands stop delegating, and preflight
  resolves against the runtime this plugin carries. The doctor's lineage check
  **inverts**: an installed `gsd-core@cairngo` or `gsd 4.x` is now a finding with
  an uninstall prescription, because two lineages answering the same command is
  the defect class the previous cycle spent itself hunting.

  Nothing under `.planning/` or `.beads/` changes. This is a plugin swap, not a
  data migration.

- **`section_manifest` degrades to `null`, never to an empty list.** Twenty-one
  literal gates in the prompt layer read `null` as "degraded, read everything";
  an empty list is neither `null` nor a manifest, and the upstream's own suite
  asserts the distinction in those words. The six golden files were edited by
  substring inside `.expect.stdout` so that `derived-from-contract` provenance
  survives — recording them would have moved the comparison from shape to bytes.

### Fixed

- **Files this repository tracks stop publishing the machine and the user.** The
  journal partitions and the beads export are versioned by design, so whatever a
  writer puts in them reaches every clone, fork and mirror. What those values are
  for is distinguishing, never naming: `machine_id()` turns a hostname into a
  stable digest, `collapse_home()` turns an absolute home path into a `~` prefix,
  and 161 already-written records were scrubbed in the same move.

  This stops new publications. Records already on the default branch are not
  reached by a forward fix.

- **Releasing a lease survives bd's reassignment guard.** bd 1.2.0 refuses to
  reassign an issue claimed by another actor. For a lease that is the ordinary
  case, not the exception — an agent acquires, a hook releases — and the two
  systems disagree about who decides: bd's authority is the assignee, cairn's is
  the holder, already matched before any write. The release now retries with
  `--force` only when the guard names itself, so bd 1.1.0 (which has no such
  flag) keeps working unchanged.

- **Two dead routes in the vendored runtime.** `worktree.set-baseref` and
  `requirements.revert-phase` are called from `references/`, resolved to nothing,
  and were wrapped in `|| true` — the dispatcher died with exit 2 and the error
  vanished. The baseRef reset between waves and the revert of a requirement
  marked complete too early simply never happened. The verb inventory did not
  scan `references/`, which the runtime executes.

### Upgrading

**Uninstall the old lineage.** This release makes the plugin self-contained, and
the doctor now treats a second GSD lineage as a finding rather than a
requirement — two plugins answering the same command is the defect class the
previous cycle spent itself hunting. On a machine that has one:

```bash
claude plugin uninstall gsd-core@cairngo   # or: gsd@4.x
/reload-plugins
```

`cairn-doctor` exits 7 until that is done, and names the plugin it found.

**Nothing under `.planning/` or `.beads/` changes.** This is a plugin swap, not a
data migration: no file moves, no schema changes, no reindex. A repository that
worked on 1.6.0 keeps working.

**One capability is genuinely reduced, and it is worth knowing before you
upgrade.** cairn vendors the four cycle verbs (discuss, plan, execute, verify)
and nothing else. `/cairn:new`, `/cairn:milestone` and `/cairn:ship` name eight
verbs this plugin does not carry; with a GSD plugin installed alongside, the
declared passthrough still runs them, and without one you do the creation and
archiving steps yourself. Each affected step says so in its own text, and
`cairn/gsd-parity.json` locks the list in both directions.

**If you enabled nothing before, enable the export.** `issues-recoverable`
reports `✗` when `.beads/issues.jsonl` is untracked, because a clean clone then
recovers no issues at all:

```bash
bd config set export.auto true
bd export --all -o .beads/issues.jsonl
git add .beads/issues.jsonl && git commit
```

### Notes

The full suite is 1161 tests across 51 files and runs in CI on every pull
request. Running it serially exceeds an hour, so `CLAUDE.md` and `AGENTS.md` now
say what to do instead, and `cairn/scripts/cairn-test.sh` is the one door both
here and locally.

CI installs bd from its default branch and the version is printed rather than
pinned, deliberately: pinning would make CI stop noticing exactly the class of
break that bd 1.2.0 caused here, which is the one worth noticing.

## [1.6.0] - 2026-08-07

A surface that answers without knowing what it is answering about does not count
as done. This cycle takes the success mark off what was never compared, the
truncation off what did not fit the screen, and the hand-editing off what was
already mechanical.

### Added

- **Closing a phase is one invocation, and running it twice writes nothing.**
  `cairn-bookkeep.sh close <N> --apply` ticks the phase and its requirements in
  the roadmap, updates the coverage table and the footer, ticks the plan
  checkboxes, moves the STATE counters, regenerates the beads map, releases the
  lease and removes the phase worktree. Every one of those was a hand edit made
  in the right order, and the wrong order did not warn.

  The difference shows in the diff. The equivalent close through the previous
  tooling moved +43/-7 in `ROADMAP.md`, 29 of those lines blank ones injected by
  normalisation; the close through `cairn-bookkeep` moved +30/-16, adding 2 blank
  lines and removing 1. `cairn-bookkeep.sh plan <NN-MM>` is the same surgical
  door for a single plan, measured at a 1-line diff.

  `cairn-bookkeep.sh reconcile` lists, writing nothing, every way ROADMAP,
  REQUIREMENTS and STATE contradict each other, and it resolves that
  disagreement without marking any phase complete, because marking a phase is a
  different decision. Without bd installed the report names which half did not
  run instead of skipping in silence.

- **The board says whether a phase's work reached the control branch, and which
  PR carried it there.** `cairn-land.sh report` reads the git already on disk,
  with no network: in this repository, 530 commits reachable from HEAD, 385 from
  `origin/main`, and 145 in the set that has not landed. The board gains a `⤒`
  suffix next to the phase, and `--json` carries `landed` on every phase and
  every task with a stable shape: status, branches, commits, reason and pr. In a
  gitflow repository a phase that reached develop but not main reads `partial`,
  with both branches named.

  When local git does not name the PR the answer is `unknown` with the reason
  written, and no surface claims there is no PR. Measured here: 0 PRs are
  discoverable offline, so all 24 locatable phases answer
  `pr unknown :: no-reference`. PR #21, which carried the whole 1.5 milestone,
  became a squash commit that left no reference at all, and it is the test case.

  The doctor stopped being silent about a complete phase that never reached the
  control branch and names each one with its commit count. A phase of an
  **archived** milestone that never landed exits 7; an open cycle only warns.
  Review state is optional and off by default: `git.review_state` takes `off`,
  `gh` or `glab`, and the board says the datum is cached and when.

- **The journal crosses machines and checkouts without anything needing to be
  merged.** Each checkout writes its own partition under `.cairn/journal/`, and
  the reader unions the partitions without depending on clock agreement. Records
  now carry where they came from, machine and checkout, derived from a hash of
  host and path; an older record without those fields reads as unknown and is
  never given an invented value.

  Compaction now seals a segment and opens the next one instead of rewriting in
  place. The defect that forces this was measured, not assumed: with a shared
  file, two machines compacting concurrently leave a valid JSONL with one
  machine's entire history missing, no conflict and no error. Partition per
  checkout makes it impossible by construction.

  The research behind the decision is in the repository. A hash chain was
  measured and rejected twice over: it does not survive a merge, producing two
  heads rather than a broken chain, and a hash chain is the data structure of
  authority, which this artifact is explicitly not. Deleting the journal still
  changes no verdict anywhere.

- **A read-only command shows how disagreement between sources moved across
  cycles.** `cairn-trend.sh` derives the series from archived verification
  artifacts and never from a typed number. It reports 3 comparable points across
  5 cycles with 2 gaps, and it says the series is not contiguous rather than
  drawing through the holes: v1.2 and v1.3 have verification files with no
  frontmatter, so the input exists and the format does not.

  It also refuses to explain the line it draws. First-pass approval reads
  67% → 50% → 43%, and that descent is ambiguous at the root: it moves for
  quality falling and for scrutiny rising, and the number cannot tell them
  apart. The declaration of that ambiguity is not printed prose. The command
  looks on disk for a key shared by every comparable cycle, finds none, and the
  sentence is born of that absence, so adding the key to every cycle turns the
  verdict to `resolvable` and the sentence disappears.

- **The response language is chosen at installation, and it reaches the
  subagents mechanically.** `/cairn:init` now asks once, before it hands off to
  `/gsd:new-project` — the position matters, because that command spawns its own
  subagents, so a question asked after it is a question asked too late. English
  is the default, pre-selected and named as such rather than arriving as the
  silence of an absent key. Re-running the init on a project that already has an
  answer asks nothing and writes nothing.

  The answer is recorded in `.cairn/config.json` as `agents.response_language`
  and propagated into `.planning/config.json:response_language` — the key GSD's
  own workflows read — as soon as that file exists. It is never propagated by
  creating that file: measured, writing GSD's key into an absent `.planning/`
  creates the directory, and a `.planning/` holding only `config.json` makes
  `/cairn:init`'s own state detection answer "existing project" instead of
  "greenfield", which would stop the next run of the command. When the two
  files carry a value, GSD's governs, and `cairn-config.sh get` reports which
  of the two answered.

  `cairn-parallel.sh prepare --json` now carries `response_language` and its
  source, and the subagent prompt of `/cairn:autonomous` copies the value from
  there rather than remembering it. `/cairn:reconcile` hands the same value to
  its investigator, while forbidding any translation of a quoted line — a
  translated citation is not a citation. `/cairn:doctor` gained a
  `response-language` check that warns when the two files disagree, or when the
  install answer never reached GSD's key, and names the exact command that
  closes it.

  Why this was worth a phase: in the 1.4 cycle every subagent the loop spawned
  answered in English against an all-Portuguese plan — **with the key already
  set correctly**. The value existed; the hand-over to the prompt did not.

  What is **not** proven: that the model pastes the value into the prompt it
  builds. The tests read the value out of `prepare`'s own output and assert that
  the delimited prompt block instructs copying it from there; no test in this
  project can spawn a live subagent, and none of them claims to.

- **cairn has its own config, with two doors onto the same bytes.**
  `/cairn:config` asks a batch in three sections with the current value
  preselected, and `.cairn/config.json` takes the same edit by hand. Seven keys,
  each with a named reader: `agents.response_language`, `autonomous.max_cycles`,
  `autonomous.max_parallel`, `bookkeep.auto_commit`, `jira.link`,
  `ship.pr_scope` and `test.jobs`. `cairn-config.sh list --json` shows value,
  default, source, who reads it and what it changes, in one place.

- **Linking a project to Jira stopped asking you to type a key, a project or a
  credential.** `/cairn:sync-config` confirms what `cairn-jira.sh detect` found
  in branches, commits and declared MCP servers. The weight of each signal was
  measured before it became code: a key only in a commit message is 21/21 false
  positives, and a key in a branch name is the signal that detects. On this
  repository detection went from `detected true` with nine prefixes to
  `detected false` with none, because not one of those prefixes was Jira. A
  project with no signal is never asked, and a recorded "no" is as durable as a
  "yes".

- **The board shows the external card's key without a single network call.** A
  `⧉` suffix appears beside the issue and beside the phase title, sourced from
  bd's `external_ref` and the roadmap's `**Tracker:**` line, and `--json`
  publishes the raw `external_ref` with its backend prefix, `null` when there is
  no card. A card with no key renders exactly the bytes it did before. The
  absence of network is not a promise: three independent tripwire layers, each
  with its own negative control, plus an AST inventory of every `subprocess.run`
  site in the renderer.

- **The suite runs in parallel through one door, and cairn says so before
  calling bats when it cannot.** `cairn-test.sh [--jobs N] [--check-env]
  [--print-command]`. bats 1.14.0 without GNU parallel does not fall back to
  serial in silence: it answers "Executed 0 instead of expected 2 tests" and
  exits 1, which is zero tests run wearing the appearance of a suite that ran.
  The `-j` is now withdrawn before the call, with the cost measured beside it
  (`tests/cairn-map.bats` takes 64s serial against 33s at `-j 6`) and the
  install command written out.

- **The thirteen `/cairn:*` wrappers exist**, each delegating to its `/gsd:*`
  counterpart with this project's bd bookkeeping around it. A wrapper whose GSD
  command is missing fails naming what is absent instead of exiting 0 in
  silence, and the documentation lists them from what is installed rather than
  from a hand-written list that ages. `/cairn:land` and `/cairn:review` joined
  them, and a guard now holds the rule open: every `cairn-*.py` either has a
  command or has its absence written down.

### Changed

- **The board groups by milestone, and stopped truncating.** The three
  `READY`/`DOING`/`BLOCKED` lanes are gone. They spent the terminal width
  divided by three and cut every title at about 28 characters, and with 40 tasks
  one lane held all 40 while the other two sat empty. In their place is a list
  grouped milestone → phase → task, with the stage carried in a single symbol.

  The symbols were measured, not eyeballed: `○`, `◑` and `◆` are
  `east_asian_width=A`, which is width 2 in a CJK locale, so they were
  discarded. The set is `◌ ◔ ◕ ✓ ⧗`, all width 1, asserted through
  `unicodedata` rather than by appearance, with an ASCII equivalent under
  `--ascii`. A blocked line names its blocker in place.

- **Running the status outside a terminal gives you the human board again.**
  `--plain` was doing two incompatible jobs: the stable TSV that scripts parse,
  and whatever a pipe happened to receive. It is now only the machine contract,
  byte-for-byte compatible with what it was, and a non-TTY run renders the
  grouped list in plain text with no box drawing and no ANSI. The test that
  asserted the two were identical was not deleted; it was rewritten as two
  separate assertions.

- **The doctor stopped reporting green over what it never checked.** A check
  with nothing to check now reports `not-applicable`, a fourth state distinct
  from `ok`, and the summary counts the two separately. An empty roadmap no
  longer produces a green board: `req-issue`, `maps-fresh` and `orphans` report
  not-applicable instead of approving nothing. The verdict line reads
  `INCOMPLETE` when checks could not run, and it still exits 0, because missing
  input is not a failure.

  `orphans` also stopped flagging closed issues of archived milestones, so the
  count returns to zero at the end of a cycle instead of growing forever.

  The doctor now carries 22 checks. Two assertions in the test file pin that
  number, and they exist because phases 23 and 24 once ran in parallel, each
  added a check without knowing about the other's, and git merged both files
  with no conflict: each branch correct alone, the result wrong.

- **`cairn-release --json` says what it measured.** The per-carrier `status`
  field reported "agrees with the first readable carrier" while reading as "is
  correct" — measured with the changelog already at 1.5.0 and the manifests at
  1.4.2, the marketplace carried the stale version and got `ok` while the
  changelog, the only correct one, got `mismatch`. `mismatch` leaves the
  vocabulary; the comparison becomes `agrees_with_reference`, `null` when no
  comparison happened, and the ruler is named in `reference`.

- **`cairn.sync_push` is gone from the declaration.** It was declared in the
  capability manifest, in three prompt fragments and in a test, and read by
  nothing: the hook decides the push from the existence of `.cairn/sync.json`.
  Implementing the read would have changed behaviour for anyone who already has
  that file, and no default resolves it. Behaviour after this change is
  byte-for-byte what it was, minus a switch that wrote a value the hook ignored.

### Fixed

- **The batch announced as concurrent two phases the roadmap declares
  dependent.** Phase dependencies were read from plan frontmatter and from bd
  edges, and never from the roadmap's own prose, so an unplanned phase came out
  with `depends_on: []` and passed for independent. The roadmap is now the third
  source. Measured on this repository: phase 22 went from
  `depends_on [1, 2, 3, 4, 21]` to `[21]`, and phase 26 from `[9]` to `[]`.

  Two defects were summing. A `discovered-from` edge, documented as provenance
  that does not block, was counted as a blocker; and a dependency on a phase of
  an archived milestone never entered the done set, so it blocked forever. On
  top of those, plan frontmatter's `depends_on: ["01"]` — which GSD writes to
  order the **waves** inside a phase — was being read as phase numbers.

- **STATE.md claimed more completed plans than plans.** The counter globbed
  `*-SUMMARY.md`, which matches both a plan's summary and a phase's, while its
  pair `*-PLAN.md` matches only plans, because a phase has no `NN-PLAN.md`. The
  two globs look symmetric and the naming is not. The fixture was blind to it by
  construction: no fixture in the repository contained a phase-level summary, so
  the defect never came near the test.

  The doctor gained an independent `plan-counters` check that compares rather
  than recomputing with the rule that wrote the number, and it failed this
  repository the moment it existed, at 47 completed out of 39. And
  `reconcile --apply` stopped answering "nothing to change" about a disagreement
  it had just printed in the same JSON object.

- **The cleanup kept forever the worktree it was meant to remove.** Versioning
  the journal made every phase worktree that had journalled read as carrying
  uncommitted work, and the trap closed on both sides: without committing the
  partition, `uncommitted changes`; committing it, `carries commits HEAD lacks`.
  The uncommitted-work check now ignores `.cairn/journal/`, and only it, on the
  grounds that the journal is the one artifact whose loss changes no verdict.

  Phase closing now retires the lease and removes the phase worktree. The lease
  half turned out not to be a regression at all: there is not a single
  `bd close` in the lease script, and the two leases that were closed had been
  closed by hand. The capability never existed. Five worktrees were removed on
  the first live run.

- **Surfaces describing a program that does not exist.** The `/cairn:doctor`
  prompt knew three states and not the fourth, and copied 9 of the check ids
  beside the complete table instead of addressing it. The `/cairn:help` map
  derived the wrappers and kept cairn's own commands by hand, and had already
  drifted. `/cairn:milestone new` ordered a phase map generated before the phase
  directory exists, which cannot succeed. A guard now fails any command prompt
  that writes a check count by hand: this repository aged such a number six
  separate times, including `"eighteen checks in total"` sitting in a docstring
  with nineteen registered.

### Upgrading

**Two things can break a script, and both have a one-line fix. Nothing about
your `.planning/` or your issues changes, and no data is migrated.**

**1. A pipe no longer gives you TSV.** This is the one that bites silently.
Until now, running the status board outside a terminal degraded to the
machine-readable format on its own, so `cairn-status.sh | while read ...`
happened to work. It no longer does: a non-TTY run renders the human list in
plain text, because a pipe is not a request for a different contract. If a
script of yours parses that output, say so explicitly:

```
cairn-status.sh --plain
```

`--plain` is byte-for-byte what it always was. Nothing about the TSV changed;
what changed is that you now have to ask for it. To find the callers:

```
grep -rn 'cairn-status' --include='*.sh' --include='*.py' . | grep -v -- --plain
```

**2. `cairn-release --json` retired one value.** The per-carrier `status` no
longer emits `mismatch`; it now answers only whether that carrier is readable
and well formed. Whether it agrees with the reference moved to a separate
`agrees_with_reference` field, which is `null` when no comparison happened. If
you branch on `status == "mismatch"`, branch on `agrees_with_reference == false`
instead. The old field was reporting "agrees with the first readable carrier"
while reading as "is correct", which is how a stale marketplace version once
passed while the correct changelog was flagged.

**The journal moved, and it is worth one look.** It now lives under
`.cairn/journal/`, one segment per checkout, and those segments are versioned so
the record survives more than one machine. Your existing `.cairn/journal.jsonl`
is read as a partition of unknown provenance: it is never rewritten, never
stamped with a machine it may not have come from, and nothing is lost. The
ignore rules for the new layout arrive the same way the 1.5 ones did:

```
/cairn:init
```

It appends only what is missing and is a no-op on a repository that is already
correct.

**One thing to decide, not to run.** Versioned partitions carry the machine they
came from, and `machine` is the hostname in plain text. In a public repository
that publishes the hostname of everyone who contributes. If that matters for
your repository, keep `.cairn/journal/` out of git until this stores a hash
instead — the checkout half of the identity already does.

**Everything else is additive.** `phases[]` gained `landed`, `in_roadmap` and
`roadmap_depends_on`; no existing key changed name, type or meaning. The doctor
went from 19 checks to 22 and may now answer `not-applicable` and report
`INCOMPLETE`, which still exits 0, because a check that could not run is not a
failure. `/cairn:land` and `/cairn:review` are new; review state stays off until
you set `git.review_state`. If you had `cairn.sync_push` in a config, it was read
by nothing before and is now gone from the declaration: your push behaviour is
unchanged.

## [1.5.0] - 2026-08-01

cairn stops inferring that a phase is done and starts reporting what each of its
sources actually claims — including when they disagree with one another.

### Added

- **A phase's state is no longer a guess made from which files happen to
  exist.** Four sources now state their claim independently — what the phase
  left on disk, what its issues say, what the roadmap has ticked, and which
  phase the project state calls active — and `/cairn:status` reports a verdict
  per phase: agreement, conflict, or unknown. When they disagree both claims are
  named and neither wins; there is no tiebreak, because a tiebreak is one source
  winning in silence. A source cairn could not read is reported as unknown, not
  counted as agreement.

  In practice: a phase whose summary is on disk but whose issues are still open
  now renders as a conflict on the board, in `--json` and on the HTML page,
  instead of a green tick. `/cairn:doctor` fails on the disagreements that block
  work and warns on the ones that only inform.

- **The board says what each phase is for, how far it got, and what to run
  next.** Every pending phase is now described by its purpose, whether its
  research was done, plans finished out of planned, issues closed out of opened,
  and the verification verdict — so choosing what to work on no longer means
  opening the roadmap and reading between the lines. The terminal board and the
  HTML page render those fields from one shared read, so the two cannot drift
  apart. A phase missing an artifact says which one is missing, instead of
  dropping the line and reading as complete.

- **Two agents on the same phase is prevented before the work starts, not
  discovered halfway through it.** `/cairn:work N` on a phase already held by
  another live session reports who holds it and since when, and stops. The hold
  is identified by the worktree that took it, so it is visible from a second
  worktree of the same repository — the exact case it exists for — and
  `/cairn:status` shows it. A hold whose session died never becomes a permanent
  block, and there are two ways it comes back: `/cairn:doctor` reports it stale
  once its four-hour heartbeat lapses, and the cleanup that runs alongside
  concurrent phases spots it without waiting at all, by checking the holder
  against the worktrees that actually exist. Either way it can be released.

- **A local, append-only record of what actually happened, which survives a
  crash.** Every phase transition, hold and verdict is written down with who,
  when, which phase and what happened. A process killed mid-write leaves
  exactly one unreadable line: it is reported with its position, and
  everything before it is still read. Conflict reports draw on it to say when
  each side last moved. Deleting it changes no verdict — it explains history,
  and it is never the authority on the present.

- **When the sources disagree, you can commission an investigation instead of
  picking a side.** `/cairn:reconcile N` runs only on a phase already reported
  as in conflict. It reads code, git history and project memory, and writes a
  proposal that cites the file and line each claim rests on; every citation is
  checked back against the file, and a single mismatch rejects the whole
  proposal. The investigation is handed no write-capable tool at all, so it
  cannot change your project's state even if something tells it to. Proposing
  and applying are separate acts: applying is
  `/cairn:doctor --apply-reconciliation N`, run by a person, and it re-checks
  that the evidence is still current before it touches anything.

- **Independent phases now genuinely run at the same time.**
  `/cairn:autonomous` used to announce which phases could run concurrently and
  then run them one after another anyway. It now runs them concurrently, one
  git worktree each, and says before starting how many are running, why each
  of the others is not, and what ceiling is in force (`--max`, three by
  default; `--sequential` opts out). Edits made in one worktree stay invisible
  to the other until they are brought back together, the hold keeps a second
  run off a phase, and the merge reports what happened rather than picking a
  winner. That includes the case git resolves silently: both branches changing
  the same line to the same value, which merges cleanly and tells nobody. A
  run that fails or is interrupted does not corrupt the other and does not
  leave a hold nobody can release.

### Fixed

- **Files cairn generates for itself sat in your repository as untracked,
  permanently.** 1.4 started writing several new files under `.cairn/` — the
  history record plus its temporary and lock siblings, the evidence an
  investigation collects, the hook log, the migration plan and its resume
  state, and a file holding the absolute path to your plugin install — while
  the ignore rules still covered only the three files that predate them. So
  `git status` never came back clean; a machine-specific absolute path was one
  `git add .` away from being committed and published; and a worktree prepared
  for a parallel run never looked clean enough to be considered removable, so
  nothing ever cleaned it up. `/cairn:init` now covers all of them. The files
  that are meant to be committed — your sync and context configuration — stay
  visible to git, because the rules name each generated file rather than
  ignoring the directory wholesale.

### Upgrading

**Nothing about your project changes, and there is one command worth running.**
Upgrading from any 1.4.x is a plugin update and nothing more: no data migration,
no configuration change, no breaking change. `.planning/` and `.beads/` are
untouched, and every command keeps the arguments it had.

The one thing to check is whether your ignore rules predate the generated files
cairn now writes under `.cairn/`. Run this in the repository:

```
git status --porcelain -uall .cairn
```

Silence means you are unaffected. Anything it lists is a generated file git is
still watching. (`-uall` matters: without it git collapses the whole directory
into a single `?? .cairn/` line, and you cannot see what is inside.)

If it listed something, run

```
/cairn:init
```

again in that repository. It appends only the ignore rules that are missing,
leaves the rest of your `.gitignore` alone, and changes nothing else — on a
repository that is already correct it is a no-op. Anything you had already
committed stays committed; if that includes one of these generated files, drop
it with `git rm --cached` once the rules are in place.

## [1.4.2] - 2026-07-28

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

</details>
