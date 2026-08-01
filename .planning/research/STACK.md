# Stack Research

**Domain:** Local-first CLI state corroboration, cooperative advisory locking, and an append-only audit log — stdlib-only Python3 + `git`/`bd` CLIs
**Researched:** 2026-07-29
**Confidence:** HIGH for all git/OS-syscall claims (reproduced live in this repo/sandbox below); MEDIUM for the two claims sourced from documentation rather than a local repro (NFS `flock`/`O_APPEND` caveats, `actions/checkout` default depth) — both cross-checked against an authoritative primary source.

No new package is being recommended anywhere in this document. Every capability below is a stdlib module, a `git` plumbing/porcelain command, or a `bd` CLI flag that already exists. The research question was never "what library" — it was "which stdlib primitive is actually correct," and several of the intuitive answers turned out to be wrong in ways that were only visible by running them.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `subprocess` | stdlib | Shell out to `git` and `bd` | Already the house pattern (`cairn-status.py:run_bd`, `capture_output=True, text=True`, explicit `.returncode` check). Reuse it verbatim for the new `git log`/`git rev-parse` calls — no new subprocess wrapper needed. |
| `os` (`O_CREAT\|O_EXCL`, `O_APPEND`, `mkdir`, `link`, `kill`) | stdlib | Atomic lease acquisition, atomic journal append, crash-liveness probe | The three real POSIX atomicity primitives available without `fcntl`. Verified below — `os.rename` is **not** one of them. |
| `fcntl` | stdlib (POSIX only — no Windows, not a target platform per `.planning/codebase/STACK.md`) | Opportunistic same-host crash-safety layer on top of the lease file | Kernel releases the lock automatically when the holding process dies, even via `SIGKILL` — verified below. Useful as a *secondary* liveness check, not the primary lease mechanism (see Lease section — the reason is process-lifetime, not correctness). |
| `git` (CLI, already required) | ≥ 2.31 for `--path-format=absolute` | Commit-evidence queries (`log --grep`, `-S`, `-G`, pathspec, `--since`, `%(trailers:...)`), shared-across-worktrees path resolution (`rev-parse --git-common-dir`) | This repo runs 2.42.1 (`git --version`, verified below), well past the 2.31 floor. No version bump needed. |
| `bd` (CLI, already required, ≥1.1.0) | 1.1.0+ installed | Issue status per `phase-<N>` label, and (new) `--external-ref` as an optional PR-number join key | `bd update --help` on this machine shows `--external-ref string  External reference (e.g., 'gh-9', 'jira-ABC', Linear URL)` — already exists, unused today, directly useful (see Corroboration §3). |
| `json`, `hashlib`/`uuid`, `socket`, `time`/`datetime` | stdlib | Journal record shape, per-line uniqueness nonce, hostname for lease/journal identity, timestamps | `json.dumps(obj, sort_keys=True) + "\n"` already matches `CONVENTIONS.md`'s `write_json` pattern — reuse it for journal *lines* too (one object per line, not one array). |

### Supporting Techniques (not libraries — verified command/call recipes)

| Technique | Purpose | When to Use |
|-----------|---------|-------------|
| `git log --grep=<pattern> [--all-match --grep=<p2>] [-- <pathspec>] [--since=<iso>]` | Cheap first-pass search over commit **messages only** | Primary corroboration query — O(commits in range), no diff computed. Always try this before `-S`/`-G`. |
| `git log -S<string>` / `-G<regex>` | Search commit **diff content** ("pickaxe") | Only when message-grep is insufficient (e.g. confirming a function was actually added, not just mentioned). ~4x slower than `--grep` on identical range (measured below) because a diff is computed per candidate commit. |
| `git log --format='%(trailers:key=<K>,valueonly)'` + `git interpret-trailers --parse` | Read/validate structured trailers (e.g. a future `Bd-Issue:` trailer) | Reliable, delimiter-safe alternative to regexing free text out of commit bodies. |
| `os.open(path, O_WRONLY\|O_CREAT\|O_EXCL, 0o644)` | Atomic "create-or-fail" | Primary lease-acquire primitive. |
| `os.mkdir(path)` | Atomic "create-or-fail," directory form | Alternative to `O_EXCL` file create — some teams prefer it because directory-creation atomicity is the most universally-relied-upon POSIX guarantee across filesystem implementations (it's what NFS-hardened lockers reach for first). Functionally equivalent to `O_EXCL` here; pick one, don't mix. |
| `tempfile.mkstemp()` + `os.link(tmp, target)` | Atomic "publish fully-written content, or fail if it already exists" | Superior to bare `O_EXCL` when the lease/lock file's *content* must be written before it becomes visible (avoids a reader seeing a half-written lease file). Classic maildir-style idiom. **Caveat:** requires `tmp` and `target` on the same filesystem, and hard-link semantics are the one primitive in this list with the weakest cross-network-filesystem track record — prefer `O_EXCL`/`mkdir` when the repo might live on a network mount. |
| `os.kill(pid, 0)` | Liveness probe for a same-host PID (no signal sent, raises if dead/inaccessible) | Verified below: `ProcessLookupError` for a dead PID, no exception for the caller's own live PID. **Known limitation:** PID reuse — a dead PID can be reassigned to an unrelated process before the check runs. Treat as a fast-path optimization, not a proof; combine with the TTL heartbeat fallback (below), never rely on it alone. |
| `git rev-parse --path-format=absolute --git-common-dir` | Resolve the path shared by every `git worktree` of one repo | **Load-bearing for the lease design** — see "Placement" below. |
| `os.open(path, O_WRONLY\|O_CREAT\|O_APPEND)` + one `os.write(fd, line_bytes)` per record | Atomic single-syscall append | The only stdlib recipe that actually gets POSIX's `O_APPEND` atomicity guarantee — see Journal section for why `open(path, "a")` does *not* reliably get it. |
| `.gitattributes` → `*.jsonl merge=union` | Make concurrent appends merge without a conflict | Zero-config git built-in (verified below — no `merge.union.driver` entry needed anywhere). |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pip install filelock` / `fasteners` / `portalocker` | Pulls in a third-party dependency — hard violation of the stdlib-only constraint, even though these libraries correctly implement most of what's below | Hand-roll the ~40 lines of `os`/`fcntl` logic documented here. It's a solved, small problem once the primitives are chosen correctly. |
| `GitPython` / `pygit2` / `dulwich` | Third-party dependency; also `pygit2`/`dulwich` re-implement git's object model in a way that can silently diverge from the installed `git` CLI's actual behavior (squash-merge/trailer parsing edge cases especially) | `subprocess` calling the real `git` binary — the existing `run_bd()` pattern in `cairn-status.py` is the template to copy. |
| `multiprocessing.Lock` / `threading.Lock` | Wrong process model entirely — these only coordinate threads/processes that share a common Python parent process. Every `/cairn:*` invocation is a **separate, short-lived `python3 cairn-*.py` process**; there is no shared parent to hold a `multiprocessing.Lock` in | The file-based lease described below, which coordinates across unrelated OS processes by design. |
| Bare `os.rename(tmp, lockfile)` as the lease-acquire step | **Verified below: `os.rename` silently overwrites an existing destination on POSIX — it never raises, so it cannot detect "someone else already holds this."** This is the single most likely mistake to make by analogy with cairn's own atomic-write convention elsewhere (`cairn-map.py`'s generated-block writes use rename-into-place, which is correct for "publish this file" but wrong for "acquire exclusivity"). | `os.link` (fails if dest exists) or `O_EXCL` create — see table above. |
| `sqlite3` as a lock/journal store | Tempting because it's stdlib and transactional, but it adds a *second* embedded-database format to a project that already has one (`bd`'s Dolt store) and doesn't solve anything `O_EXCL`+JSONL doesn't — plus SQLite's own file-locking has the exact same NFS caveats as `flock`, so it buys nothing on the hard case | Plain files, as above. |
| `git notes` for the journal | A tempting "structured metadata attached to commits" primitive, but notes live on their own ref (`refs/notes/commits`), require an explicit `git push refs/notes/*`/fetch dance most contributors never set up, and note-content merge conflicts are a *harder*, less-documented problem than the JSONL `merge=union` case below | A plain tracked `*.jsonl` file with `.gitattributes` `merge=union`, as documented below. |
| Relying on `git log --grep`/`-S` for bd-id matches as a **required**, always-present signal | **Verified below: as of today, zero commits in this repo's entire history mention a `CairnGo-xxx` id, anywhere — not in a subject, not in a body, not in a trailer.** Squash-merging (this repo's actual practice) also discards the original branch commits' messages entirely; the squash body is hand/AI-written prose, not GitHub's default bullet-list-of-commits. Treating this signal's *absence* as evidence against a phase would flag the project's entire shipped history as `conflict` on day one. | Treat signal (c) as **corroborating only, never contradicting** — its absence is "no data," not "no work." See Corroboration §3 for what to do about it going forward. |
| Storing the lease file inside `.planning/` or `.cairn/` (repo-root, per-worktree paths) | **Verified below: these paths are physically different files in each `git worktree` of the same repo**, even though all worktrees share one `.git`. A lease placed there would never be visible to a second agent working the same phase from a different worktree — exactly the scenario the feature exists to catch, and it would fail silently. | `<git-common-dir>/cairn/leases/` (see Placement, below). |

## Corroboration — git as an evidence source

### 1. Verified command behavior (this repo, 239 commits, `git 2.42.1`)

```
$ time git log --all --grep='phase_disk_state' --oneline | head -5
...
real 0.030s   # message-only search: cheap

$ time git log --all -S'phase_disk_state' --oneline | head -10
16815bb docs: start milestone v1.4 Honest State
f7526be feat(v1.3): a status board that says which phase to run, why...  (#14)
c95dcbd feat(status): read what a phase actually is, once, for every surface
real 0.130s   # pickaxe: ~4x slower on the same range — diff computed per commit

$ git log --all --grep='phase' --grep='status' --all-match --oneline | head -5
# --all-match turns multiple --grep into AND; omitting it is OR (verified: 46 hits without --all-match vs a handful with it)

$ git log --all --grep='status board' -- cairn/scripts/cairn-status.py --oneline
# pathspec + --grep compose as AND — "mentions X" AND "touched this path"

$ git log --since="2026-07-27" --oneline | wc -l
14   # date-bounding narrows the range before either grep or pickaxe runs
```

**Recommendation:** tier the query. First pass is always `--grep` (cheap, message-only). Escalate to `-S`/`-G` only when message-grep found nothing and the check is worth the cost. Always narrow with a pathspec (the files the phase's `PLAN.md` names) and, where a start timestamp is known (bd issue `created_at`), `--since` — this bounds cost independent of total repo size, which matters because `-S`/`-G` cost scales with commits *examined*, not commits matched.

At 239 commits this repo is too small to demonstrate "thousands of commits" performance directly — that claim is extrapolated from the *mechanism*, not measured at scale: `--grep` reads commit-message strings only (cost ∝ commits in range, independent of blob/diff size), while `-S`/`-G` must materialize a tree diff per candidate commit (cost ∝ commits in range × average diff size). The 4x gap measured here on identical ranges is consistent with that mechanism and should widen, not narrow, on a larger repo with bigger diffs per commit.

### 2. Squash-merge: what survives, what is destroyed (verified concretely)

This repo squash-merges every recent PR (confirmed: `git log --format='%H %P'` on the 5 most recent history-visible commits shows single-parent chains despite `(#18)`/`(#19)`/`(#20)` in the subjects — no merge commits at all in recent history, even though **older** history in the same repo (`ec417a5`, `1d7e99c`, `0891939`...) genuinely does contain two-parent merge commits, meaning the project switched practices partway through its life. A corroboration script cannot assume one shape for the whole history).

**Survives a squash merge:**
- The squash commit's own subject + body, entirely under the merger's control (in this repo: hand/AI-written prose, `(#N)` PR number always in the subject, `Co-authored-by:` trailer always present — verified via `git log -1 --format=%B` on three recent squash commits).
- The **complete** diff of the whole PR, as a single commit against its single parent — so `-S`/`-G` and pathspec filtering find squash commits correctly (verified: `-S'phase_disk_state'` correctly surfaced `f7526be`, a squash-merged commit; pathspec-filtered log on `cairn-status.py` correctly returned 11 commits including squash merges).
- GitHub's own PR object and its "Closes #N" linkage — but this lives on GitHub's server, not in git. Querying it requires the `gh` CLI (already a cairn dependency per `STACK.md`), not `git log`.

**Destroyed by a squash merge, verified concretely:**
- Every intermediate commit hash from the feature branch — `git log --all` on a normal clone never sees them (they're not on `refs/heads/*` or `refs/tags/*`; GitHub keeps `refs/pull/N/head` server-side, but that's not fetched by a default clone). Confirmed independently: rewriting a commit locally with `git commit --amend`, then `git reflog expire --expire=now --all && git gc --prune=now`, made the original commit's `git cat-file -e <sha>` fail (exit 1) — the same fate a squashed-away commit meets once GitHub's own retention window passes.
- Any bd-id mention that existed **only** in an intermediate commit's message and was not hand-carried into the final squash body — and in this repo, **zero** such mentions exist anywhere, confirmed by grepping the full history (`git log --all --format='%H%n%B' | grep -oE 'CairnGo-[a-z0-9]+'` → no matches).
- Fine-grained per-original-commit attribution (`git blame` on a squash-merged repo attributes every changed line to the single squash commit).

**Concrete conclusion for the requirements step:** signal (c) as literally specified ("git commits that reference those bd ids") returns **empty for this repo's entire history today**. This is not a corner case to handle — it is the current, 100%-of-the-time state. The corroboration design must treat this signal as *optional supporting evidence with a distinct "not adopted" state*, never as a peer-weighted vote alongside the other three. Flipping this signal on as a hard requirement would immediately mark the whole shipped project `conflict`.

### 3. What replaces per-commit bd-id linkage, concretely

Two independent, buildable options — not mutually exclusive:

- **`bd update <id> --external-ref gh-<PR#>`** (flag verified present in `bd update --help` on the installed 1.1.0 binary, currently unused by cairn). PR numbers are reliably present in every recent squash-commit subject (`(#18)`, `(#19)`, `(#20)` — 100% of the last 10 commits checked). Populating `--external-ref` at close time (a natural extension of the existing `post-bd-write.sh` hook, which already fires on `bd close`) creates a `bd-issue → PR-number` join key that works **today**, on this repo's actual squash-merge convention, without touching git history at all: `git log --grep='(#18)'` finds the exact squash commit.
- **A new structured trailer, going forward only** (e.g. `Bd-Issue: CairnGo-xxx[, CairnGo-yyy]`), stamped automatically — verified that `git log --format='%(trailers:key=Bd-Issue,valueonly)'` and `git interpret-trailers --parse` reliably extract a trailer of this shape (proven against the existing `Co-authored-by:` trailer already on every commit). This is additive to, not a replacement for, the `--external-ref` approach: `--external-ref` recovers *existing* history, a trailer prevents the gap from recurring.

Neither is a stack decision to make in this document — flagging both as concretely buildable is the point; the roadmap should pick one or both.

### 4. Correctness caveats, verified

- **Shallow clones silently corrupt both `--grep` and `-S`/`-G`, with no error.** Reproduced: `git clone --depth 5` of this repo, then `git rev-parse --is-shallow-repository` → `true`; `git log --all --grep='phase_disk_state'` → zero hits (should have 3); `git log --all -S'phase_disk_state'` → **two** hits, one of which (`842933b`) is a false positive artifact of the shallow boundary — git computes that grafted commit's diff against an empty tree, so pre-existing content at the boundary reads as "added." **This is worse than a silent miss; it is a silent wrong answer.** Any corroboration script must call `git rev-parse --is-shallow-repository` first and degrade signal (c) to an explicit "unknown (shallow clone)" state rather than trusting a `-S`/`-G` result from one.
- **`actions/checkout@v4` defaults to `fetch-depth: 1`** (confirmed against the official action's own documentation), and this repo's `.github/workflows/ci.yml` does not override it. If the corroboration check is ever wired into CI as currently configured, it runs against a 1-commit shallow checkout and signal (c) is unconditionally unusable there — either add `fetch-depth: 0` to the workflow step that needs it, or scope the corroboration check to local/interactive use only, and make the shallow-clone detection above fail loud rather than fail quiet in CI specifically.
- **Rewritten/rebased history becomes genuinely unreachable, not just hard to find** (verified above via amend + reflog-expire + gc). Any design that *caches* a commit SHA as stored evidence (e.g. a journal record recording `"evidence": {"commit": "<sha>"}`) must treat a later "commit not found" as "can no longer confirm," not as an error or as proof the event never happened — re-derive evidence fresh at read time rather than trusting a cached pointer forever.

## Phase Lease — cooperative advisory lock

### Placement (verified, load-bearing)

`git rev-parse --path-format=absolute --git-common-dir` returns the **same** absolute path from every `git worktree` of one repository — verified by creating a real worktree of this repo (`git worktree add`) and comparing: the worktree's own `--git-dir` differs (`.git/worktrees/<name>`), but `--git-common-dir` resolves to the same `.../CairnGo/.git` in both. `--path-format=absolute` requires git ≥ 2.31 (this repo: 2.42.1, well past the floor).

This matters because the user's own stated workflow convention (see global instructions) is one git worktree per concurrent agent — exactly the scenario a phase lease exists to catch. A lease rooted at `.planning/` or `.cairn/` (both inside the per-worktree working tree) would be invisible across worktrees and silently fail at the one thing it's for. **Root the lease at `<git-common-dir>/cairn/leases/phase-<N>.json`** — outside any worktree's working tree, therefore shared, and never subject to git tracking/merge/`.gitignore` at all (it isn't inside a working tree to begin with).

Avoid rooting it under a cloud-synced path (iCloud Drive, Dropbox) if the repo happens to live under one — verified concern, not tested here: cloud-sync file providers can dematerialize files and interpose their own I/O layer between the app and the real filesystem, which is exactly the kind of "unusual filesystem" `O_EXCL`/`flock` correctness assumptions are least tested against. `.git/` is not typically cloud-synced by default, which is an incidental point in its favor.

### Acquire primitive (verified)

```python
fd = os.open(str(lease_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
os.write(fd, metadata_json_bytes)   # single write — see Journal section for why
os.close(fd)
```

Verified concretely in this environment (macOS/Darwin, APFS):
- A second `os.open(..., O_EXCL, ...)` on the same path raises `FileExistsError` — correct exclusive-create semantics.
- `os.rename(tmp, lease_path)` does **not** raise when `lease_path` already exists — it silently overwrites (verified: content became the *renamed-in* file's content, the original was clobbered with no exception). **Do not use bare `rename` for lease acquisition** — this is the mistake most likely to be made here specifically because cairn already uses rename-into-place correctly elsewhere for "publish this file" (`cairn-map.py`).
- `os.link(tmp, lease_path)` raises `FileExistsError` if `lease_path` exists (verified) — this is the "write full content first, then atomically publish-or-fail" idiom, strictly better than `O_EXCL` when the lease file's content matters (no reader ever sees a half-written lease), at the cost of requiring same-filesystem `tmp`/target and being the weakest of the three primitives on some network filesystems.
- `os.mkdir(lease_dir)` raises `FileExistsError` if it exists (verified) — functionally equivalent to `O_EXCL`, some teams prefer it for its stronger track record on non-local filesystems.

Any of the three ( `O_EXCL`, `link`-swap, `mkdir`) is correct on local macOS APFS and Linux ext4/xfs. Pick `O_EXCL` for simplicity (matches the existing `die()`/exception-driven error style already used throughout `cairn/scripts/`) unless the lease is ever expected to live on a network filesystem, in which case prefer `mkdir`.

### Staleness — verified, and why the obvious "just use flock" design is wrong here

`fcntl.flock` was tested directly on this machine and has two verified properties:

1. **It is per-open-file-description, not per-process.** Two independent `open()` calls of the *same file*, by the *same process*, contend against each other — the second `flock(LOCK_EX|LOCK_NB)` raised `OSError`/`EAGAIN`. A naive "the same script calls the lease module twice" bug would deadlock against itself.
2. **The kernel releases the lock automatically the instant the holding process dies — even via `SIGKILL`, with zero cleanup code.** Verified by forking a child that acquires the lock and is then `SIGKILL`ed with no handler; the parent's very next `flock(LOCK_EX|LOCK_NB)` succeeded immediately.

Property 2 is the reason `flock` is the standard answer to "advisory lock with automatic crash recovery, no daemon." **It is still the wrong primary mechanism for a phase lease specifically**, because every `/cairn:*` invocation in this codebase is a **separate, short-lived `python3 cairn-*.py` process that exits after doing its one thing** (there is no single process alive for the whole duration of a phase — plan, work, and verify are three separate invocations, possibly minutes to hours apart). `flock`'s auto-release fires the moment the *acquiring* process exits — which for cairn's process model is almost immediately, defeating the entire purpose. `flock` is well suited to guarding a single short critical section *within* one invocation (e.g., protecting `cairn-map.py`'s generated-block write from a second concurrent invocation); it is not suited to "hold this for the duration of an agent's engagement with a phase."

**Recommendation — the mechanism that actually matches this process model:**

- Staleness is decided by a **heartbeat TTL in the metadata file**, not by process liveness: `now - heartbeat_at > TTL` → reclaimable. TTL should be generous (hours, not minutes) to tolerate long human-review/thinking gaps without false reclamation.
- Renew/release the heartbeat from the **existing session hooks**, not a new daemon — `cairn/hooks/session-start.sh` and `cairn/hooks/session-stop.sh` already exist and already follow the "fire-and-forget, never fail the caller" contract documented in `CONVENTIONS.md`. Extending `session-start.sh` to touch/renew a heartbeat for any lease this session holds, and `session-stop.sh` to best-effort release it, ties lease lifetime to Claude Code's own session lifecycle — which is the actual unit of "an agent is working on this," not any single script's process.
- `os.kill(pid, 0)` liveness (verified: `ProcessLookupError` for a dead PID) is worth recording as a **secondary, same-host-only fast path** — record the PID of the invoking session's process if it can be discovered, and if a same-hostname check finds that PID dead, the lease is *certainly* stale (skip waiting out the TTL). But do not depend on it: PID reuse is a real, if rare, race, and it says nothing when the recorded host differs from the checking host. TTL is the only fallback that works in every case, so design TTL as the source of truth and PID-liveness as a same-host optimization on top of it, not the reverse.
- **Identity ("who holds this"):** no session-id primitive currently exists anywhere in cairn's hook surface (verified — grepped `cairn/hooks/` and `cairn/scripts/` for `SESSION`/`session_id`: no hits). Rather than invent a new one, reuse `bd`'s own actor-resolution convention, already documented in `bd`'s own `--help` (`--actor string   Actor name for audit trail (default: $BEADS_ACTOR, git user.name, $USER)`) — `$BEADS_ACTOR` → `git config user.name` → `$USER`, in that order, for the lease's human-readable "who" field, plus hostname + PID for the machine-readable staleness fields. This is a genuine open question for the requirements step, not a solved one — flagging it precisely so it isn't silently glossed over.

### Cross-platform notes

- `O_EXCL`, `os.link`, `os.mkdir`, `os.kill(pid, 0)` and `fcntl.flock` are all verified working on macOS/Darwin/APFS in this environment; all five are standard POSIX and behave identically on Linux ext4/xfs.
- `fcntl` does not exist on Windows — not a concern per `.planning/codebase/STACK.md`'s stated platform requirement (macOS or Linux only), but worth a one-line guard/comment at the import site so a future contributor understands why, rather than rediscovering it via an `ImportError`.
- `flock` over NFS is documented (not tested here — no NFS mount available in this sandbox) as supported since Linux 2.6.12 via NLM emulation, but multiple independent sources describe it as unreliable in practice with "no way to properly detect whether locking works on a specific NFS mount" — treat any network-filesystem deployment of the lease as out of the verified-safe zone regardless of which primitive is chosen, and prefer `mkdir`/`O_EXCL` (namespace operations, not lock-table operations) if a network filesystem is ever a real target.

## Append-Only Journal

### Concurrent-append safety (verified + one important correction to the question's framing)

The question asks whether "a single `write()` under `PIPE_BUF`" makes concurrent appends safe. **`PIPE_BUF` is the wrong constant for this** — POSIX's `PIPE_BUF` atomicity guarantee applies specifically to writes on **pipes/FIFOs**, not to `write()` calls on regular files. Verified on this machine: `select.PIPE_BUF` / `os.fpathconf(fd, 'PC_PIPE_BUF')` both report **512 bytes** on macOS (Darwin) — notably smaller than Linux's typical 4096 — which would make any journal line design built around that constant fail immediately for any record carrying a description string, since 512 bytes is easy to exceed.

The guarantee that actually applies to a regular file is **`O_APPEND` atomicity**: when a file descriptor is opened with `O_APPEND`, POSIX requires the seek-to-end and the `write()` to happen as a single atomic step with respect to other `O_APPEND` writers of the same file, with **no size cap tied to `PIPE_BUF`**. This is documented directly in the Linux `open(2)` man page. It holds on local filesystems (APFS, ext4, xfs) and is explicitly **not** guaranteed on NFS — the same man page's NOTES section states the NFS protocol has no atomic append operation, so the client kernel must simulate it via a separate stat-then-write, which reintroduces the exact race `O_APPEND` exists to prevent, for multi-client writers.

**The recipe that actually gets the guarantee, verified correct against the mechanism (not benchmarked under real contention here — the atomicity claim is POSIX/documented, not something a single-process test can prove or disprove):**

```python
line = json.dumps(record, sort_keys=True).encode("utf-8") + b"\n"
fd = os.open(str(journal_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
n = os.write(fd, line)
if n != len(line):
    raise OSError(f"short write: {n}/{len(line)} bytes")   # extremely rare locally, but check it
os.close(fd)
```

**Two things this recipe deliberately avoids, and why:**
- A plain `open(path, "a")` Python file object (`io.TextIOWrapper`) is **not** guaranteed to translate one `.write()` call into exactly one `write(2)` syscall — internal buffering/encoding can split it into several, each individually losing the atomicity guarantee, which is defined at the syscall level. Go through `os.open`/`os.write` directly.
- Never split a record's body and its trailing `\n` into two separate `os.write()` calls — that reintroduces a window where another writer's line could land between them.

### `.gitattributes merge=union` (verified — zero-config, and verified to have real failure modes)

```
*.jsonl merge=union
```

Verified in a scratch repo, with **no** corresponding `merge.union.driver` entry in any config file anywhere: `union` is one of git's built-in low-level merge drivers, confirmed via `man gitattributes`:

> **union** — Run 3-way file level merge for text files, but take lines from both versions, instead of leaving conflict markers. This tends to leave the added lines in the resulting file in random order and the user should verify the result. Do not use this if you do not understand the implications.

That warning is not boilerplate — both halves were reproduced concretely:

1. **Disjoint appends merge cleanly, in an order that is not chronological.** Two branches each appending one distinct line, merged: the result contains both lines, but in an order determined by merge side ("ours" before "theirs"), not by wall-clock time. **Ordering must be recovered from a field inside each record (a timestamp, or a monotonic sequence number), never from line position in the file.**
2. **Two failure modes that must shape the design, both verified:**
   - **Byte-identical lines silently deduplicate.** Two branches independently appending the exact same line (e.g. two agents each recording `{"phase":3,"event":"claimed"}` with second-resolution timestamps and no other differentiator) merge down to **one** line, not two — a real event silently vanishes from the record. **Every journal line must carry something that guarantees global uniqueness independent of its semantic content** — a UUID, or a `(hostname, pid, monotonic counter)` tuple, is sufficient; a timestamp alone at second resolution is not.
   - **The union driver never reports a conflict, even for genuinely conflicting edits to the same pre-existing line.** Reproduced by having two branches each rewrite line 1 of the same file differently and merging: `git merge` returned `exit 0` with no `CONFLICT` reported anywhere, and the file ended up containing **both** contradictory versions of "line 1" as two separate lines. This is safe *only* under the invariant that nothing ever rewrites or deletes an existing line — which must hold for an append-only journal by construction, but it means any future compaction/rotation script that touches this file in place reintroduces exactly this silent-double-write bug, with no warning from git at all. Compaction must happen through a mechanism that is conflict-sensitive (a normal 3-way-merged file, or a separate rewrite step gated behind the phase lease so only one process can be doing it), never as an in-place edit to the `merge=union` file itself.
3. **The file must be true JSONL — one complete, self-parseable JSON object per physical line, never a pretty-printed multi-line record.** `merge=union` operates at line granularity; a record that spans multiple lines can be shuffled away from its siblings by the union algorithm and become truncated or invalid JSON. This isn't a hypothetical — it follows directly from "random order" in git's own documentation of the driver.

### Recovering order after a union merge

Because line position is meaningless post-merge, every record needs an embedded ordering field, and every *reader* of the journal must sort by it before drawing any conclusion — never assume file order. A high-resolution timestamp (not second-resolution) plus the uniqueness nonce above covers both problems with one field if structured as, e.g., `{"ts": "2026-07-29T14:03:11.482931Z", "nonce": "<uuid4>", ...}` — sort by `ts`, break ties (if any) by `nonce` for a fully deterministic replay order.

## Installation

Nothing to install. Every module above ships with Python 3's standard library on macOS and Linux; `git` and `bd` are already required dependencies at the versions already pinned in `.planning/codebase/STACK.md`. The only version floor introduced by this research is `git ≥ 2.31` (for `--path-format=absolute`), and this repo already runs 2.42.1.

## Version Compatibility

| Requirement | Needed For | Status in This Repo |
|-------------|-----------|----------------------|
| `git ≥ 2.31` | `rev-parse --path-format=absolute --git-common-dir` (lease placement) | Satisfied — 2.42.1 installed, verified via `git --version` |
| `bd ≥ 1.1.0` | `--external-ref` flag (optional corroboration join key) | Already the pinned floor per `.planning/codebase/STACK.md`; `--external-ref` confirmed present in the installed 1.1.0 binary's `bd update --help` |
| Python `fcntl` | Opportunistic same-host lease liveness check | POSIX-only; already implied by the macOS/Linux-only platform requirement |

## Stack Patterns by Variant

**If a lease must coordinate across `git worktree`s of the same repo (the expected case, given this user's stated worktree-per-agent workflow):**
- Root it at `git rev-parse --path-format=absolute --git-common-dir`, never inside `.planning/` or `.cairn/`.

**If the corroboration check might ever run against a shallow clone (CI, or a shallow `git clone --depth N`):**
- Call `git rev-parse --is-shallow-repository` first. Degrade signal (c) to an explicit "unknown (shallow)" state — never silently trust a `-S`/`-G` result from one; the boundary-commit false-positive verified above makes a shallow `-S` result actively misleading, not merely incomplete.

**If a phase predates any bd-id-in-commit convention (true for 100% of this repo's history today):**
- Signal (c) contributes corroborating evidence only when present; its absence must never downgrade an otherwise-agreeing corroboration from the other three signals into `conflict`.

**If the journal file is ever rotated/compacted:**
- Never rewrite the `merge=union` file in place — route compaction through the phase lease (so only one writer can be mid-compaction) and treat the result as a new file/normal (non-union) merge, not an edit to the live union-merged file.

## Sources

- This repository, live commands (`git log`, `git rev-parse`, `git clone --depth`, `git worktree add`, `bd --help`, `bd orphans --help`, `bd show --json`) — HIGH confidence, directly reproduced above with real output, not recalled.
- Scratch repos built and merged in this session (`/private/tmp/.../scratchpad/union-test`, `union-nodrv`, `rebase-test`, `wt-test`, `shallow-test`, `lock_test.py`, `flock_test.py`, `flock_crash_test.py`) — HIGH confidence, same reason.
- `man gitattributes` (local, git 2.42.1) — HIGH confidence, primary/official source, quoted verbatim above.
- [`actions/checkout` GitHub Marketplace / repo docs](https://github.com/actions/checkout) — MEDIUM confidence (web-sourced, cross-checked against the action's own official documentation, not independently reproduced in a live CI run here); confirms `fetch-depth: 1` default.
- [`open(2)` — Linux manual page, man7.org](https://man7.org/linux/man-pages/man2/open.2.html) — MEDIUM confidence (web-sourced, but an authoritative primary kernel-interface reference); source for the `O_APPEND`/NFS race-condition NOTES text quoted above.
- [`flock(2)` — Linux manual page, man7.org](https://man7.org/linux/man-pages/man2/flock.2.html) and [Lennart Poettering, "On the Brokenness of File Locking"](https://0pointer.de/blog/projects/locking.html) — MEDIUM confidence (web-sourced, cross-referenced across multiple independent sources converging on the same conclusion); source for the `flock`-over-NFS reliability caveat.

---
*Stack research for: cairn v1.4 "Honest State" — corroboration, phase lease, append-only journal*
*Researched: 2026-07-29*
