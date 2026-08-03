## Am I affected?

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

## What changed

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
