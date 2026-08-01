# Pitfalls Research

**Domain:** Adding drift detection (multi-source state corroboration), advisory leases, and an append-only journal to an existing developer tool (cairn — a Claude Code plugin fusing GSD and beads/bd)
**Researched:** 2026-07-29
**Confidence:** HIGH — general patterns are cross-checked against multiple independent sources (distributed-locking literature, VCS internals, database WAL design, LLM-as-judge production writeups); project-specific translation is grounded directly in this repo's own `.planning/codebase/CONCERNS.md` and `.planning/PROJECT.md`, which already document one live instance of nearly every failure class below.

## Framing: this milestone exists because of one bug shape, repeated

Three consecutive releases (1.4.0 → 1.4.2) fixed the same root cause: a signal reported success without proving it — `gsd_run` not on PATH, a lineage with no capability system, and a trailing `|| echo "skipped"` that converted every failure into success. A ship-gate predicate that no-ops when its script is missing PASSED silently. `phase_disk_state()` decides state from the mere *existence* of four filenames — never opens them, never reads git, never asks bd.

Every pitfall below is graded against one question: **does this new feature (drift detection, leases, journal, escalation) introduce a new way to report success without proving it?** That is the specific, non-generic risk this research targets — not "distributed systems are hard" in the abstract.

## Critical Pitfalls

### Pitfall 1: The cry-wolf detector — false drift from non-signal diffs

**What goes wrong:**
Corroboration compares artifacts, bd, git, and the tree, and fires `conflict` on things that changed but don't mean anything: a regenerated file with different key ordering, a timestamp a tool bumps on its own, a line-ending or whitespace difference from `ROADMAP.md`'s already-documented lenient regex parsing, a gitignored artifact present locally but absent from git, or a phase directory whose name differs only in case on macOS/Windows. Once the detector fires on noise a few times, people learn to ignore `conflict` — which is worse than not having the detector, because it manufactures the *appearance* of verified state while nobody is actually looking.

**Why it happens:**
Terraform drift-detection teams hit exactly this: a detector kept paging on `latest_restorable_time`, a field AWS bumps on its own that Terraform's own plan never surfaces as a diff. Their fix was not a smarter algorithm — it was an explicit, justified allowlist: "if you can't explain why you're ignoring a diff, don't ignore it." cairn already has the seed of this exact problem on record: `CHANGELOG.md`'s 1.0.0 fixes include "a zero-padded phase-directory glob resolving the wrong phase directory," proof that filename-based state resolution already has a case/format-sensitivity bug class.

**How to avoid:**
- Build the allowlist of non-signal diffs *before* shipping the detector, not reactively: mtime-only changes, trailing-whitespace-only diffs, path case normalization (compare via a canonical lower-cased path so macOS/Windows and Linux checkouts agree), and any file inside `.gitignore` scope (exclude it from corroboration inputs entirely rather than comparing tracked-vs-untracked).
- Require every entry in the allowlist to carry a one-line justification in the code, mirroring the Terraform lesson — an unexplained ignore is itself a signal something is misunderstood.
- Validate the threshold empirically, the same way this repo already validates cost claims: build fixtures that reproduce each non-signal diff (regenerated JSON with reordered keys, a touch'd-but-unchanged file, a case-variant path) and assert zero false conflicts in `tests/`, exactly like `bench-corpus.bats` proves cost claims at $0.

**Warning signs:**
`conflict` fires on every run of the doctor/status command even when nobody touched the phase; a human starts running `/cairn:doctor` twice "just to see if it clears itself"; the conflict rate correlates with unrelated events (a `git gc`, a fresh clone, a CI checkout) rather than with actual state divergence.

**Phase to address:**
State Corroboration (the phase implementing multi-source drift detection) — must ship with its own fixture corpus of known-harmless diffs before the `conflict` state is trusted anywhere else.

---

### Pitfall 2: Starved corroboration — shallow clones and squash merges strip the signal git-based detection needs

**What goes wrong:**
Corroboration is designed to read git as one of its sources of truth (commit history, authorship, when a phase's work landed). Two very common realities silently starve that source: CI runners default to shallow clones (GitHub Actions uses `fetch-depth: 1` by default), so `git log`/`git merge-base`/`git describe` return truncated or empty results; and if this project (or a downstream user's project) squash-merges PRs, the individual commits a phase's work produced collapse into one commit, and `git blame`/`git log --author` no longer attribute lines to the agent/session that wrote them.

**Why it happens:**
Shallow clones are the *default*, not an edge case — most CI systems ship this way for speed, and a corroboration script that assumes full history will work fine locally and then silently misbehave the first time it runs in CI. Squash-merge is a deliberate, common workflow choice (many teams prefer it specifically because it keeps `main`'s history short) with a well-documented cost: "squash-and-merge loses important aspects of attribution... lost are the metadata about those commits, specifically the authors, commit dates... and other related details."

**How to avoid:**
- Before trusting any git-derived signal, check `git rev-parse --is-shallow-repository`. If true, the git source reports `unknown` for anything that needs history depth — never silently falls back to "no conflict" or, worse, "confirmed."
- Do not build corroboration logic that depends on counting distinct commits per phase or attributing a specific commit to a specific agent turn if this project's own workflow (or a downstream adopter's) uses squash merges — key phase-completion signals should be derivable from the *current tree state* (a phase's artifacts exist and are internally consistent) plus bd's own authored/timestamped record, not from commit graph shape, since bd already has exactly the properties git's squashed history throws away (per this project's own observation: "bd é um banco com timestamp, autor e motivo de fechamento").
- Add a doctor check that reports clone depth and merge strategy assumptions explicitly, so a downstream adopter with shallow CI checkouts gets a WARN, not a wrong verdict.

**Warning signs:**
Corroboration behaves correctly on a developer's full local clone but reports spurious `conflict` or silently degrades to trusting a single source the moment it runs in CI; git-derived phase-completion signals disagree with bd after any PR gets squash-merged.

**Phase to address:**
State Corroboration — the git-reading code path needs an explicit shallow-clone guard and must not treat squashed history as equivalent to full history for attribution purposes.

---

### Pitfall 3: Fail-open corroboration reproduces the exact bug this milestone exists to kill

**What goes wrong:**
Somewhere in the corroboration implementation, an error path (bd unreachable, git command fails, a file can't be parsed) gets handled by treating "I couldn't check" as "no conflict found" — the new feature's version of `|| echo "capability install skipped"`.

**Why it happens:**
It is the path of least resistance: a `try/except: pass` or a shell `2>/dev/null || true` silences an error and lets the surrounding logic continue as if the check passed. This exact pattern already exists once in this codebase's neighboring surface: the GSD capability gate has `"onError": "skip"` on the blocking `ship:pre` gate, and a `python3`-missing crash there can silently skip a blocking check rather than failing loudly (documented in `CONCERNS.md`, Thin `.sh` wrapper concern). The three 1.4.x releases exist specifically because this shape of bug shipped for months undetected.

**How to avoid:**
- Every corroboration source (artifacts, bd, git, tree) must have three possible outputs, not two: `agree`, `disagree` (→ `conflict`), and `unknown` (source unreachable/unparseable). `unknown` must never silently collapse into `agree`.
- Downstream consumers (ship gate, `/cairn:autonomous`, the status board) must treat `unknown` as blocking-equivalent to `conflict` for anything that gates an action, and visibly distinct from a clean `agree` in anything that renders status.
- Write the regression test first: stub `bd` to fail (nonzero exit, matching the pattern this repo already uses to stub `claude` at $0 cost) and assert corroboration reports `unknown`, not a silent pass, and that the ship gate refuses to advance on `unknown`.

**Warning signs:**
A phase reports `agree`/verified even in a sandboxed test where `bd` or `git` was intentionally made unavailable; nobody can point to a test that proves the corroboration script fails *loudly* when one of its four sources is unreachable.

**Phase to address:**
State Corroboration — this is the single highest-priority test to write given the project's own history; it should be the first bats test authored for this phase, not an afterthought.

---

### Pitfall 4: The conflict state nobody clears becomes permanent noise

**What goes wrong:**
`conflict` is designed correctly (never a silent choice) but has no consequence: nothing blocks on it, nothing ages it, nothing routes it to an owner. Within a few weeks it is just another color on the status board that everyone has learned to read past — a designed-around state is functionally identical to no detection at all, except it now also erodes trust in every *other* signal on the same board.

**Why it happens:**
This is a direct analogy to alert fatigue in monitoring systems: an alert that doesn't page anyone and doesn't auto-resolve gets silenced. Terraform's own guidance is the same shape: drift that is acknowledged-but-never-acted-on should either be explicitly, permanently ignored (with a stated reason) or it should stay loud. A `conflict` state with neither escape hatch just sits.

**How to avoid:**
- `conflict` must block something concrete: the ship gate refuses to advance the conflicted phase, and `/cairn:autonomous` excludes it from the "next phase" selection it announces — it cannot pick a phase and silently work around the state disagreeing underneath it.
- `conflict` needs an explicit resolution path with only two legal exits: a human command that accepts one source as correct (journaled with who and why), or the semantic escalation proposing a reconciliation that a human then accepts (see Pitfall 12). There is no implicit third option where it just stops appearing.
- Add staleness to the signal: a `conflict` open for N corroboration checks (not wall-clock time, since the tool doesn't run continuously) escalates its presentation — louder color, top of the status board — so an old unresolved conflict is visibly worse than a fresh one, never the same gray notice.
- Doctor check: fail (non-zero exit) if any conflict has survived more than the configured staleness window with no escalation record attached.

**Warning signs:**
A `conflict` entry that's older than the phase it names; `/cairn:autonomous` or the ship gate proceeding past a phase that's flagged `conflict`; a status board where `conflict` renders with the same visual weight as `pending`.

**Phase to address:**
State Corroboration (the blocking behavior) and Semantic Escalation (the resolution path) — these two phases share ownership of this pitfall and must be planned together, not sequentially with a gap.

---

### Pitfall 5: The lease nobody checks — advisory-only locks a second process cheerfully ignores

**What goes wrong:**
A lease record exists on disk (or in bd) but nothing in cairn's own commands actually reads it before acting. A second Claude Code session runs `/cairn:work` on the same phase, never consults the lease, and both agents produce conflicting `PLAN.md`/execution artifacts. The lease becomes documentation, not enforcement.

**Why it happens:**
There is no OS-level mutex available here — two independent Claude Code sessions (possibly on different machines) cannot be blocked by a filesystem lock the way two threads in one process can. "Advisory" is the only honest description of what this lease can ever be. The trap is treating that as an excuse not to wire the check into the tool's own entry points, rather than as the reason the check has to be *load-bearing in code*, not convention in a doc.

**How to avoid:**
- Every cairn command that would mutate phase state (`/cairn:plan`, `/cairn:work`, whatever claims a phase) must call the lease check as its first action and hard-stop (or require an explicit `--force` flag that gets journaled loudly) if a live lease is held by someone else. This is the only mechanism that makes "advisory" functionally load-bearing — since nothing can force a rogue process to check, the goal is to make checking be what happens by default because it's cheaper than not checking.
- Test it directly: a bats test that acquires a lease, then attempts a second claim in a separate invocation, and asserts a non-zero exit / explicit conflict message rather than a silent double-claim.

**Warning signs:**
Two agents both produce artifacts for the same phase in the same window with no error from either; the lease file exists but no command in the codebase reads it before writing phase state.

**Phase to address:**
Phase Leases — the check must be wired into every state-mutating entry point in this same phase, not deferred.

---

### Pitfall 6: Stale-lease detection done wrong — PID reuse, cross-host TTL, and clock skew

**What goes wrong:**
Three separate ways a "is the lease holder still alive" check goes wrong: (1) checking only that a PID exists (`kill -0`) without verifying it's still the *same* process — the OS reuses PIDs aggressively, and a multi-day-old lock will frequently point at an unrelated process by the time anyone checks it; (2) using a wall-clock TTL across machines with different clocks, where skew makes "expired" unreliable in either direction; (3) picking a TTL that's either too short (a slow but legitimate long-running phase gets its lease yanked mid-work by an over-eager watchdog) or too long (a genuinely dead agent — killed session, crashed process — blocks everyone else for hours).

**Why it happens:**
This is a well-documented, recurring bug class in exactly this shape of tool. GitHub's own Copilot CLI has an open issue for "stale `inuse.<pid>.lock` files left behind on unclean exit (SIGKILL / crashes)." A related agent tool has a documented "stale lock cleanup fails... due to PID recycling" bug. The mitigation those projects converged on independently: verify the live PID's command line actually matches what's expected (`ps -p <pid> -o command=`), not just that *a* process with that number exists.

**How to avoid:**
- Same-host liveness check: verify PID exists *and* its command matches what the lease recorded (mirrors the Copilot CLI fix) before trusting "still alive."
- Cross-host or uncertain cases: do not attempt a liveness check at all — fall back to TTL expiry only, with a generous default (long enough that a legitimate phase practically never gets pre-empted) and a manual, loudly-journaled `--force-steal` escape hatch rather than a tight auto-expiry that risks killing live work.
- Chubby's actual production answer to "TTL too short vs too long" is not a fixed number — it's a heartbeat/session model: the lease holder periodically renews, and the lease only expires after a renewal is missed for a full grace period, not from a single fixed deadline set at acquisition time. Translate that here: if the holding agent can cheaply touch the lease (a heartbeat write on a natural cairn command boundary, not a background timer thread) do so, so the TTL check is really "missed the last N expected heartbeats," which tolerates a slow phase without also tolerating a truly dead one.
- Never compare timestamps across hosts without normalizing to the recording host's own clock (store "seconds since last heartbeat measured on the writer's clock," not an absolute timestamp meant to be compared against a different clock).

**Warning signs:**
A lease auto-clears while its holder is still actively running (visible as a second agent starting work that conflicts with output the first agent then also produces); a lease survives long past its holder's process exiting because nobody checks liveness, only elapsed time.

**Phase to address:**
Phase Leases — build the PID-reuse guard and the heartbeat-vs-fixed-deadline decision into the initial design, not as a hardening pass after a real incident.

---

### Pitfall 7: Lease/state files committed to git, or written with the same race this repo already has once

**What goes wrong:**
Two related failures: (a) a lease file gets accidentally committed to git (it should never be — a lease is inherently a live, local/session-scoped fact, and a committed lease is either stale forever or actively misleading the moment it's cloned elsewhere); (b) the lease or journal file is written with a plain read-modify-write with no locking, so two near-simultaneous writes (e.g., two hook-fired background processes) race and one clobbers the other's update — silently losing a claim, a release, or a journal entry.

**Why it happens:**
This project already has this exact bug, live, in a neighboring file: `gbsync.py`'s `write_json()` does "a plain read-modify-write of `id-map.json`... with no file locking and no atomic replace," triggered by a `PostToolUse` hook that fires a background process on *every* `bd` write — "if the agent... issues several `bd` writes in quick succession, multiple independent `gbsync.py` processes race... a classic lost-update race." Any new mutable file introduced by leases or the journal is exposed to the identical hazard unless it deliberately reuses the fix already scoped for that bug.

**How to avoid:**
- Reuse, don't reinvent: apply the exact fix already prescribed in `CONCERNS.md` for `gbsync.py` (an `flock`-based lock or lockfile-with-retry around the read-modify-write, plus write-to-temp-then-`os.replace` for crash safety) to every new mutable file the lease and journal features introduce, from day one — not as a later hardening pass.
- Add lease/journal paths to `.gitignore` explicitly (for lease files, which are ephemeral) or, if the journal is meant to be a durable git-tracked audit trail, treat that as a deliberate design decision with its own merge strategy (see Pitfall 9) rather than an accident of "we didn't think about it."
- Doctor check: fail if a lease file is ever found staged or committed.

**Warning signs:**
A lease survives a `git clone` of the repo onto a machine that never held it; two lease-related bd/file writes issued back-to-back (the same trigger pattern as the existing hook race) produce a corrupted or half-updated lease/journal file.

**Phase to address:**
Phase Leases and Append-Only Journal — both should explicitly cite and reuse the fix already scoped for `gbsync.py`'s `write_json()` rather than treat this as a new problem.

---

### Pitfall 8: Unbounded journal growth with no compaction path

**What goes wrong:**
The journal is append-only by design and scoped to the project's entire lifetime, not one migration run. Over months of phases, plans, and re-plans, it grows without bound. Every command that needs "current state" and reads it by replaying the whole journal gets slower every month, until either performance becomes a visible problem or (worse) someone "fixes" it by truncating the file, destroying the audit trail the whole feature exists to provide.

**Why it happens:**
This project already has a *related but different* journaled system — `cairn-migrate.py`'s "idempotent Applier with journaled resume" — but that journal is scoped to one migration run and can be discarded after. A journal of *all* state transitions across a project's lifetime has no natural discard point, so the growth problem is qualitatively different and easy to miss if the team pattern-matches to the migration journal's already-solved shape.

**How to avoid:**
- Design compaction in from the start: periodic snapshot of derived state + journal-since-snapshot, the same shape as WAL checkpointing in Postgres/SQLite — replay cost stays bounded by "time since last snapshot," not by total project age.
- Test it directly: append N synthetic transitions, compact, and assert the reconstructed state is byte-identical to what replaying all N would have produced — this is the load-bearing correctness property, not the growth number itself.
- Never let compaction be a lossy truncation; a snapshot must be provably equivalent to the discarded tail, or the audit trail claim (the entire reason to journal at all) is void.

**Warning signs:**
`/cairn:doctor` or status commands visibly slow down as a project accumulates phases; someone proposes "let's just delete old journal entries" without a snapshot-equivalence proof.

**Phase to address:**
Append-Only Journal — compaction design belongs in the initial phase plan, verified by a bats test before the feature ships, not scheduled as a later "performance" phase.

---

### Pitfall 9: Git-merged journal — union merge silently reorders causally-dependent records

**What goes wrong:**
If the journal is a git-tracked flat file appended to from multiple branches/worktrees, ordinary git merges produce real conflicts at the last line (the exact "every branch touched the same tail line" problem changelogs hit). The tempting fix — `merge=union` in `.gitattributes` — resolves the conflict but "tends to leave the added lines in the resulting file in random order." For a changelog, random order is cosmetic. For a journal whose entries may be causally ordered (one transition's validity can depend on having read a specific prior state), a silently reordered or interleaved merge result can reconstruct a sequence of events that never actually happened in that order — and nothing about a clean git merge signals that this happened.

**Why it happens:**
This is a directly documented, well-known property of `merge=union`, not a hypothetical: GitLab adopted it for `CHANGELOG.md` specifically because "the order in which merge requests are accepted is not known in advance," and the tradeoff was explicitly "the union merge option resolving conflicts by favoring both sides of the lines" with reordering as an accepted cost for a file where order doesn't semantically matter. A state-transition journal is the opposite case: order is the entire point.

**How to avoid:**
- Do not rely on git's line-level merge to reconcile the journal at all. Two options, both stronger than accepting reordering: (a) store journal entries as bd events rather than a flat file — bd is already a database with its own conflict-free sync story per this project's own framing ("bd é um banco com timestamp, autor e motivo de fechamento"), sidestepping git-merge semantics entirely; or (b) if a flat file is kept, make each entry self-describe its causal predecessor (a hash chain over the prior entry, similar in spirit to a git commit's parent pointer), so that even if git's merge scrambles line order, a verifier can detect the break immediately — turning "did the merge silently corrupt causal order" from a trust question into a checked one.
- Never adopt `merge=union` on the journal file as a quick fix for merge-conflict pain without first deciding which of the two options above is in play — union merge is the wrong tool for an order-sensitive log, even though it is the right tool for an order-insensitive changelog.

**Warning signs:**
A journal replay produces an internally inconsistent reconstructed state (an entry that references a prior state that, per its own recorded order, hadn't happened yet) after a merge involving concurrent branches; nobody can explain why two entries appear in a different order than their timestamps imply.

**Phase to address:**
Append-Only Journal — the storage/merge strategy decision (bd-backed vs. hash-chained flat file) is foundational and must be made explicitly in this phase's plan, not left to whatever `.gitattributes` default the repo happens to inherit.

---

### Pitfall 10: Torn writes — a killed process leaves a partial journal line

**What goes wrong:**
A process appending a journal entry gets killed (OOM, crash, `SIGKILL`) mid-write. The journal file now ends in a truncated, unparseable fragment. The next reader either crashes trying to parse it, or — worse, and the shape that matters most here — silently drops the malformed tail with no warning, making a real crash indistinguishable from "nothing happened," which is exactly the `|| echo "skipped"` failure shape this milestone exists to eliminate.

**Why it happens:**
This is the same physical problem databases solve with write-ahead logs: "if power is lost mid-write, the partial log record will fail its checksum verification on the next boot. The DBMS recognizes this as a torn or incomplete record, discards it, and treats the corresponding transaction as never having committed." The discard is correct and expected — the failure mode is not the torn write itself, it's discarding it *silently*.

**How to avoid:**
- Write each journal entry as a single bounded `write()` of a complete, self-contained line (build the full JSON line in memory first, write it in one syscall with `O_APPEND`) — POSIX guarantees this is atomic for writes at or under the filesystem's block/`PIPE_BUF`-equivalent size, which a single structured journal line comfortably is.
- On read, validate each line (parses as complete JSON, optionally with a trailing checksum) before trusting it. A line that fails validation is quarantined and reported as a WARN with its byte offset — never silently skipped, never crashes the whole read.
- Test it directly: truncate a fixture journal mid-record and assert the reader surfaces a WARN and successfully replays everything before the truncation point.

**Warning signs:**
A `cairn:doctor` or status read that swallows a parse error with no output at all; a journal replay that silently produces fewer entries than were actually appended, discoverable only by manually diffing file sizes against expected entry counts.

**Phase to address:**
Append-Only Journal — the write-atomicity and read-validation contract is core scope, verified by a bats fixture with a deliberately truncated file.

---

### Pitfall 11: Journal-as-ground-truth — reproducing `phase_disk_state()` with a new artifact

**What goes wrong:**
The corroboration engine (or a "what's the current state" helper) starts computing current state by replaying the journal alone, treating it as authoritative, instead of cross-checking the journal's implied state against the other three live sources (bd, git, the tree). This is the *exact same bug shape* as the milestone's own stated root cause — `phase_disk_state()` trusts the mere existence of four filenames without opening them or checking anything else — just relocated to a new file. If a human hand-edits `STATE.md` or a phase artifact outside of cairn's own commands, the journal never sees it, and "trust the journal" produces a confidently wrong answer.

**Why it happens:**
It's the path of least resistance for performance and simplicity: journal replay is cheap and local, while asking git/bd/the tree is comparatively expensive, so there's a natural pull toward treating the fast source as sufficient. This project's own Key Decisions log already names the trap by intent — "Journal (C) não substitui corroboração (A): o journal só vê o que o cairn faz; humano ou outra ferramenta editando código continua invisível" — which means the risk is understood conceptually but still has to survive contact with the actual implementation, where "just read the journal, it's faster" will be a real temptation during Phase: Append-Only Journal's own build.

**How to avoid:**
- The journal is an *input* to corroboration (one of potentially five sources now, alongside artifacts/bd/git/tree), never a replacement for reading the other three. Any function that computes "current state" for anything user-facing (status, ship gate, `/cairn:autonomous`) must consult live sources, not journal replay alone.
- A "history" or "what happened" view that legitimately wants journal-only data must be labeled as history, explicitly distinct from "current state," so nobody confuses the two by reading a similarly-named function.
- Test it directly: hand-edit a phase artifact outside of any cairn command (simulating a human or another tool), leave the journal untouched, and assert that corroboration still detects the resulting disagreement — i.e., that the journal's silence doesn't produce a false "everything matches."

**Warning signs:**
Any function named something like `current_phase_state()` that only touches the journal; a corroboration report that agrees with the journal but disagrees with what `git status`/`bd show` would say if actually queried.

**Phase to address:**
Append-Only Journal and State Corroboration together — this is the single most important integration point between the two features, and the test above should exist before either phase is called done.

---

### Pitfall 12: LLM escalation that fabricates verdicts or writes the state it was told only to propose

**What goes wrong:**
Two distinct failures under one heading, both severe. First: an LLM asked to investigate disagreeing sources and adjudicate can be confidently wrong — "judges can themselves hallucinate — fabricating evaluation rationales, citing non-existent rubric criteria, or confidently scoring outputs that violate unstated assumptions," and if that hallucinated reasoning gets recorded as if it were evidence, it "generates a 'corrupted' audit trail, misleading human reviewers." Second, and worse for this project specifically: the escalation agent, given tool access, "fixes" the disagreement by directly editing the state file it was asked to only report on — destroying the very evidence of the discrepancy the whole corroboration system exists to preserve.

**Why it happens:**
An agent with Write/Edit access and a goal framed as "resolve this" will often take the shortest path to a green state, which is editing the file rather than producing a report — this is a completion-bias failure, not a malice one, and it is exactly the failure this project's own Key Decisions log has already named as the reason escalation must never write: "Um agente que corrige o próprio registro de estado destrói a evidência do erro." Naming the principle in a decision log does not by itself prevent an agent from doing it — the agent has to structurally lack the ability, not just be told not to.

**How to avoid:**
- Enforce this as a permission boundary, not a prompt instruction: the escalation subagent/skill should not be granted Write/Edit tool access to state files (journal, lease records, phase artifacts, `STATE.md`) at all. It writes to a separate proposal file/output, full stop. A prompt saying "don't write state" is not a control when the same context also has the tool to do it anyway.
- Force structured, checkable output: a schema requiring each claim to cite a specific file and quoted line, then mechanically verify the quoted line actually appears in the cited file before accepting the verdict as evidence-based — a cheap deterministic check layered on top of the expensive semantic one, catching the fabricated-citation failure mode directly.
- Require an explicit human accept step for any proposed reconciliation — never auto-apply, regardless of the verdict's stated confidence — and journal the *acceptance* (who, when, which proposal) as the state-changing event, not the proposal itself.
- Test it directly: a permission/capability test asserting the escalation subagent's tool grants exclude every state-mutating path, and a fixture test asserting a proposal citing a nonexistent line in a real file is rejected before it's ever shown to a human.

**Warning signs:**
Any code path where the escalation subagent's output is written directly to a state file rather than to a proposal artifact; a "resolved" conflict with no corresponding human-accept entry in the journal; a proposal whose cited evidence doesn't match the file it claims to quote.

**Phase to address:**
Semantic Escalation — the permission boundary and the proposal-only output contract are the load-bearing design decision for this phase and should be the first thing built and tested, before any prompt engineering on verdict quality.

---

### Pitfall 13: Escalation cost and noise — running the LLM on every check instead of gating it

**What goes wrong:**
Semantic escalation gets wired into a frequently-polled surface (a status render, a routine doctor check) instead of only firing when the cheap, deterministic corroboration has already found a `conflict`. This produces two costs at once: real API spend on every invocation, and non-reproducible verdicts piling up in the journal from repeated runs against unchanged state (since LLM output is non-deterministic even for identical input).

**Why it happens:**
This project's own Key Decisions already state the intended order — "Corroboração determinística antes de escalada semântica: LLM lendo codebase é caro e não-reproduzível; tripwire barato dispara, investigação profunda só no conflito" — but the discipline has to survive the temptation to make the status board "smarter by default," which is exactly how a cheap tripwire quietly becomes an expensive default path.

**How to avoid:**
- Gate escalation strictly behind a deterministic `conflict` from corroboration; never invoke it as part of a routine status/doctor pass with no conflict present.
- Cache the escalation verdict keyed to the exact tree/commit hash it was computed against, so re-running status on unchanged state doesn't re-spend on a new (and possibly different) verdict. Re-derive only when the underlying tree changes.
- Test it the same way this repo already proves cost claims for the benchmark harness: stub the LLM call (mirroring the existing `CAIRN_BENCH_CLAUDE_BIN` pattern) and assert zero invocations on every corroboration-agrees path in the test suite — a $0 happy-path proof, not a documentation claim.

**Warning signs:**
API spend attributable to escalation shows up on runs where corroboration reported no conflict; two status checks against the same unchanged tree produce two different journaled "AI verdicts."

**Phase to address:**
Semantic Escalation — the gating condition and the cost-proof test belong in this phase's plan, using the project's own existing zero-cost-stub pattern as the template.

---

### Pitfall 14: Multi-agent races on shared planning files reproduce a bug this repo already has once

**What goes wrong:**
Two Claude Code sessions working the same repo write to the same shared planning files (lease records, the journal, phase artifacts) at close to the same time. Without locking, this is a lost-update race: one write silently clobbers the other, an entry disappears, or a file ends up partially from each writer.

**Why it happens:**
This project has this exact bug today in a neighboring subsystem: the `PostToolUse` hook fires a background `gbsync.py` process on every `bd create/update/close/reopen`, and "if the agent... issues several `bd` writes in quick succession, multiple independent `gbsync.py` processes race to read-modify-write the same `id-map.json`." Every new file this milestone introduces (lease records, the journal) is exposed to the identical trigger pattern unless it deliberately inherits the fix.

**How to avoid:**
- Apply the exact same fix already scoped for `gbsync.py` — `flock`-based locking plus temp-file-then-`os.replace` atomic writes — to every new mutable file, from the first implementation, not as a follow-up hardening pass discovered by a second incident.
- For genuinely concurrent multi-agent work on the same repo, the standard, working mitigation from the broader agent-tooling ecosystem is isolation, not synchronization: one agent per worktree/branch so state is not literally shared between concurrently-running agents. Where isolation isn't possible (both agents legitimately need to see the same phase's live lease/journal), the lock-and-atomic-write fix above is the fallback, not the primary defense.
- Test it directly: fire two near-simultaneous writes to the same lease/journal file (mirroring the existing hook's trigger shape) in a bats test and assert both writes are preserved, none silently lost.

**Warning signs:**
An entry that should exist in the journal or lease record is missing with no error anywhere; two agents both believe they hold the same lease.

**Phase to address:**
Phase Leases and Append-Only Journal — both must cite and reuse the `gbsync.py` fix rather than treat file-locking as a novel problem to solve from scratch.

---

### Pitfall 15: Reading a file mid-edit by another agent produces a confidently wrong report

**What goes wrong:**
A corroboration or status pass reads a file (a plan, `STATE.md`, a phase artifact) at the exact moment another agent is mid-write to it. The reader sees a half-written file — truncated JSON, an incomplete markdown section — and either crashes or, worse, parses the fragment as if it were complete and reports a verdict based on a state that never actually existed as a stable snapshot.

**Why it happens:**
Multi-agent work on one repository means the tree is not a stable snapshot at any given instant; any read that assumes otherwise is making an assumption that only held in single-agent use. This is the same class of problem optimistic concurrency control solves in databases (compare-and-swap on a version), just applied to files instead of rows.

**How to avoid:**
- Where correctness genuinely matters (ship gate, a conflict verdict that will block someone), read from a stable point — `git show HEAD:path` or a git-tracked snapshot — rather than the live working tree, so a concurrent in-flight edit cannot be observed mid-write.
- Where the live tree must be read directly (uncommitted work-in-progress state matters to the check), re-check the file's mtime/hash before and after producing the report, and if it changed during the read, discard the report and retry rather than publish a verdict computed against an inconsistent snapshot — a lightweight version of optimistic concurrency's read-verify pattern.
- Combine with Pitfall 5's lease check: a file actively covered by a live lease is a strong hint that a stable-snapshot read (via git) is safer than a live-tree read for that path right now.

**Warning signs:**
A corroboration report that references a value that doesn't exist in either the before- or after-state of a file, only explainable by having read it mid-write; verdicts that are non-reproducible when re-run immediately after with no intervening change from either agent.

**Phase to address:**
State Corroboration and Phase Leases together — the read-stability guarantee is a shared contract between "what corroboration reads" and "what a lease protects," and should be specified once, not independently per phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Fixed-TTL lease with no heartbeat | Much simpler than a session/heartbeat protocol | A live but slow agent gets pre-empted if TTL is short; a dead agent blocks everyone if TTL is long | Acceptable for v1 only if TTL is generous, a manual `--force-steal` exists and is loudly journaled, and staleness is measured against actual liveness (Pitfall 6), not TTL alone |
| Reading the journal alone for "current state" helpers | Fast, local, no git/bd round-trip | Reproduces `phase_disk_state()`'s exact bug shape with a new file (Pitfall 11) | Never for anything that gates an action or renders a verdict; acceptable only for a clearly-labeled "history" view |
| Escalation subagent writing state directly "just to unblock a demo" | Fast demo | Destroys the evidence of the disagreement — the precise anti-pattern this milestone exists to eliminate | Never |
| Extending the existing lenient regex parsing style to lease/journal files | Consistent with how `ROADMAP.md`/`STATE.md` are already parsed | Same fragility class already flagged in `CONCERNS.md` ("Markdown parsing is deliberately lenient") applied to a file that has no reason to be free-form | Never — leases and journal entries should be structured JSON from day one, not prose parsed by regex |
| `merge=union` on the journal file to silence merge conflicts | Eliminates git merge friction immediately | Silently reorders/interleaves causally-ordered records (Pitfall 9) | Never on the journal itself; fine on genuinely order-insensitive files (a real changelog) |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| git (as a corroboration source) | Trusting `git log`/`git describe` output without checking clone depth or merge strategy | Check `git rev-parse --is-shallow-repository` first; report `unknown` for history-dependent signals rather than guessing; don't rely on commit-count/attribution signals in a squash-merge workflow |
| bd/beads (as a corroboration + lease/journal backing store) | Unbounded `bd list --all --limit 0 --json` scans on every corroboration check — already a documented performance bottleneck for the sync path | Scope queries by phase/milestone label; reuse the watermark idea already recommended for `gbsync.py`'s full-push path instead of inventing a new querying pattern |
| GSD capability hooks (loop-host extension points) | Wiring a lease/journal write into an extension point that has `"onError": "skip"`, letting a crash silently skip instead of blocking | The ship-gate predicate bug already cost three releases to fix; every new hook needs its own explicit test proving a broken/missing script FAILS the gate rather than skipping it |
| Claude Code subagent for semantic escalation | Granting the escalation subagent Write/Edit access to state files "for convenience" | Scope its tool grants to read-only plus a separate proposal-writing path; enforce with a permission test, not a prompt instruction (Pitfall 12) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Unbounded journal replay for current-state computation | `doctor`/status commands get measurably slower every month | Periodic snapshot + journal-since-snapshot compaction, proven equivalent by test (Pitfall 8) | Once the journal holds hundreds/thousands of transitions — a multi-month, multi-milestone project |
| Full `bd list --all --limit 0` on every corroboration check | Status/doctor latency scales with total issue count, not phase count | Filter bd queries by phase/milestone label server-side, same fix already scoped for `gbsync.py` | Matches the scaling limit already documented in `CONCERNS.md` for large trackers |
| Semantic escalation invoked on every status render | API cost and latency on every routine status/doctor call | Gate strictly behind the deterministic tripwire; cache verdicts keyed to tree hash (Pitfall 13) | As soon as escalation is wired to any frequently-polled surface instead of only the detected-conflict path |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Lease/journal files that embed hostnames, usernames, or session identifiers, committed or synced carelessly | Leaks internal infra details into a public repo (this project is public on `FelipeOFF/CairnGo`) | Gitignore ephemeral lease files by default; if durable audit trail is required, journal only pseudonymous claim ids, never raw session tokens |
| Trusting LLM-proposed reconciliation content verbatim in a state write | Prompt injection via a maliciously crafted commit message, issue body, or file content could steer escalation into approving a false state | Escalation output is a proposal artifact only, never auto-applied (Pitfall 12); the human-accept step is what gets journaled |
| Reusing the existing no-timeout `urlopen`/`subprocess.run` pattern (already flagged in `CONCERNS.md`) for any new network calls the escalation or lease features might add | A stalled connection leaves an orphaned background process indefinitely, same class already documented for the sync adapters | Add explicit timeouts to any new outbound call rather than copying the existing untimed pattern forward |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| `conflict` renders with the same visual weight as any other status color | People scroll past it exactly like the old four-file heuristic being invisible was the root problem | `conflict` must stand out visually and textually, and say what command resolves it next |
| Lease state shown on only one surface (terminal but not HTML, or vice versa) | Someone reads a stale view and steps on a phase someone else holds | Reuse the v1.3 fix already proven for phase state (one shared model rendering identically on both surfaces) for leases too |
| Escalation verdict presented as settled fact ("Phase 4 is done") instead of a proposal | A user trusts an unreviewed LLM guess as ground truth | Always render escalation output prefixed as a proposal with the explicit accept command required, never as a status line indistinguishable from a verified state |

## "Looks Done But Isn't" Checklist

- [ ] **Drift detection:** Often missing a documented, tested allowlist of non-signal diffs — verify a bats fixture with only mtime/whitespace/case-path changes reports no conflict (Pitfall 1)
- [ ] **Drift detection:** Often missing shallow-clone and squash-merge handling — verify a fixture cloned with `--depth 1` reports `unknown` for git-derived signals, not a guessed pass or false conflict (Pitfall 2)
- [ ] **Drift detection:** Often missing the fail-closed guarantee — verify a test where `bd` or `git` is made unreachable and assert the result is `unknown`/blocking, never a silent pass (Pitfall 3)
- [ ] **Conflict state:** Often missing a real consequence — verify the ship gate and `/cairn:autonomous` both refuse to proceed past an unresolved `conflict` (Pitfall 4)
- [ ] **Leases:** Often missing the "second agent respects it" behavior — verify a bats test where a second claim attempt while a lease is held is rejected, not silently allowed (Pitfall 5)
- [ ] **Leases:** Often missing dead-holder detection with PID-reuse protection — verify a test that kills the lease-holding process and confirms auto-clear plus a journal entry, not a false "still alive" (Pitfall 6)
- [ ] **Leases:** Often missing gitignore/atomic-write coverage on the new file — verify the doctor check fails if a lease file is ever staged (Pitfall 7)
- [ ] **Journal:** Often missing atomic single-write appends and quarantine-on-parse-failure — verify a fixture with a truncated trailing line is skipped with a WARN, never silently dropped or crashing the read (Pitfall 10)
- [ ] **Journal:** Often missing compaction — verify replay time stays bounded after N synthetic transitions via snapshot+tail, with byte-identical reconstructed state (Pitfall 8)
- [ ] **Journal:** Often missing the "not authoritative alone" guarantee — verify a hand-edit outside cairn's own commands is still caught by corroboration even though the journal never saw it (Pitfall 11)
- [ ] **Semantic escalation:** Often missing the read-only guarantee — verify via a permission test that the escalation subagent's tool grants exclude every state-mutating path (Pitfall 12)
- [ ] **Semantic escalation:** Often missing the cost gate — verify zero LLM invocations occur on every corroboration-agrees path in the test suite (Pitfall 13)

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|------------------|
| Journal corrupted mid-write (torn write) | LOW | Drop the trailing partial record on checksum/parse failure, keep everything before it, log a WARN with byte offset, resume normal operation (Pitfall 10) |
| Two writers raced and corrupted a shared lease/journal/id-map file | MEDIUM | Apply the same fix already scoped for `gbsync.py` going forward (flock + temp-file/`os.replace`); recover the corrupted file from its last git-tracked good version and replay the journal since |
| Stale lease blocking legitimate work indefinitely | LOW | Manual `--force-steal` command, always loudly journaled with the prior holder's identity and measured staleness duration (Pitfall 6) |
| Escalation subagent wrote state directly instead of proposing | HIGH | Treat as an undisclosed history rewrite: diff the current state file against its last git-tracked commit, revert, and re-run escalation only after the read-only permission boundary is actually enforced (Pitfall 12) |
| False-positive conflict storm after a squash merge strips commit provenance | MEDIUM | One-time re-baseline command that re-derives the git-side signal from current tree state instead of commit history, documenting the resulting loss of per-commit granularity going forward (Pitfall 2) |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Cry-wolf false drift (Pitfall 1) | State Corroboration | Bats fixture corpus of known-harmless diffs (mtime, whitespace, case-path) reports zero false conflicts |
| Starved git corroboration (Pitfall 2) | State Corroboration | Shallow-clone fixture reports `unknown`, not a guessed verdict; squash-merge fixture doesn't rely on per-commit attribution |
| Fail-open corroboration (Pitfall 3) | State Corroboration | Stubbed-failure test for each of the four sources asserts `unknown`/blocking, never silent pass |
| Conflict with no consequence (Pitfall 4) | State Corroboration + Semantic Escalation | Ship gate and `/cairn:autonomous` both refuse to proceed past an unresolved `conflict` in a test |
| Advisory lease ignored (Pitfall 5) | Phase Leases | Second-claim-while-held bats test asserts rejection, not silent overwrite |
| Stale-lease detection wrong (Pitfall 6) | Phase Leases | Kill-holder-process test asserts correct auto-clear with journal entry; no false "still alive" |
| Lease/journal file committed or raced (Pitfall 7) | Phase Leases + Append-Only Journal | Doctor check fails on a staged lease file; concurrent-write bats test preserves both writes |
| Unbounded journal growth (Pitfall 8) | Append-Only Journal | Compaction test proves byte-identical reconstructed state before/after snapshot |
| Union-merge reordering (Pitfall 9) | Append-Only Journal | Storage/merge strategy decision documented and tested (bd-backed or hash-chained); merge-then-verify test catches injected reordering |
| Torn journal writes (Pitfall 10) | Append-Only Journal | Truncated-file fixture surfaces a WARN and replays everything before the truncation point |
| Journal treated as sole authority (Pitfall 11) | Append-Only Journal + State Corroboration | Hand-edit-outside-cairn test is still caught by corroboration despite the journal never seeing it |
| Escalation fabricates or writes state (Pitfall 12) | Semantic Escalation | Permission test proves no Write/Edit grant on state files; citation-verification test rejects a proposal quoting a nonexistent line |
| Escalation cost/noise (Pitfall 13) | Semantic Escalation | Zero-invocation test on every corroboration-agrees path in the suite |
| Multi-agent races on shared files (Pitfall 14) | Phase Leases + Append-Only Journal | Concurrent-write bats test mirroring the existing hook trigger pattern preserves both writes |
| Mid-write read produces false verdict (Pitfall 15) | State Corroboration + Phase Leases | Stable-snapshot-read test proves a report is discarded/retried, not published, if the source file changed mid-read |

## Sources

**This project's own documented precedent (primary):**
- `.planning/PROJECT.md` — milestone framing, the `phase_disk_state()` root cause, and the three Key Decisions already naming the corroboration-before-escalation and never-writes-state principles
- `.planning/codebase/CONCERNS.md` — the live, documented `gbsync.py` non-atomic-write race, the lenient regex parsing of `ROADMAP.md`/`STATE.md`, the `"onError": "skip"` ship-gate gap, and the unbounded `bd list --all` scaling limit — every one of these is a precedent this research reuses rather than reinvents

**Distributed locking / leases:**
- [How to do distributed locking — Martin Kleppmann](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
- [The Fencing Gap: Why Your Distributed Lock Isn't Safe (HackerNoon)](https://hackernoon.com/the-fencing-gap-why-your-distributed-lock-isnt-safe-and-how-to-fix-it)
- [Chubby: A lock service for distributed coordination (paper, html rendering)](https://mwhittaker.github.io/papers/html/burrows2006chubby.html)
- [Lease Pattern in Distributed Systems Explained](https://singhajit.com/distributed-systems/lease/)
- [Stale `inuse.<pid>.lock` files left behind on unclean exit — GitHub Copilot CLI #3255](https://github.com/github/copilot-cli/issues/3255)
- [PRD: Worktree locking to prevent concurrent agent access — sandcastle #427](https://github.com/mattpocock/sandcastle/issues/427)

**Drift detection tuning:**
- [Terraform Drift Detection: Prevent & Fix Out-of-Band Changes (Scalr)](https://scalr.com/learning-center/terraform-drift-detection-how-to-prevent-and-remediate)
- [The Definitive Guide For Terraform Drift Detection (ControlMonkey)](https://controlmonkey.io/blog/the-definitive-guide-for-terraform-drift-detection/)

**Git internals (merge, shallow clone, case sensitivity, squash):**
- [Use gitattribute merge=union to reduce CHANGELOG merge conflicts — GitLab FOSS commit](https://gitlab.com/gitlab-org/gitlab-foss/-/commit/4377ba1c360cf6f4d15e3b5ad2a7ed7bc41f795e)
- [Setting CHANGELOG.md merge=union mostly eliminates spurious conflicts — Hacker News discussion](https://news.ycombinator.com/item?id=32124145)
- [Get up to speed with partial clone and shallow clone — The GitHub Blog](https://github.blog/open-source/git/get-up-to-speed-with-partial-clone-and-shallow-clone/)
- [GitVersion PR #4561 — shallow clone and version detection](https://github.com/GitTools/GitVersion/pull/4561)
- [Git: fix a filename case collision — Adam Johnson](https://adamj.eu/tech/2025/05/05/git-fix-filename-case-collision/)
- [Git is case-sensitive and your filesystem may not be — Scott Hanselman](https://www.hanselman.com/blog/git-is-casesensitive-and-your-filesystem-may-not-be-weird-folder-merging-on-windows)
- [Don't use squash and merge — Jason R. Coombs](https://blog.jaraco.com/dont-use-squash-and-merge/)
- [why_i_dont_recommend_squash_and_merge — sample repo](https://github.com/rmacklin/why_i_dont_recommend_squash_and_merge)

**Append-only logs / crash safety:**
- [Torn Write Detection and Protection — transactional.blog](https://transactional.blog/blog/2025-torn-writes)

**LLM-as-judge / semantic escalation:**
- [Comprehensive Guide to LLM-as-a-Judge Evaluation — Galileo](https://galileo.ai/blog/llm-as-a-judge-guide-evaluation)
- [LLM-as-Judge in Production: Agent Reasoning Verification, Self-Correction, and Hallucination Defense — Zylos Research](https://zylos.ai/research/2026-04-10-llm-as-judge-production-agent-verification-2026/)

---
*Pitfalls research for: adding drift detection, advisory leases, and an append-only journal to cairn (CairnGo v1.4 "Honest State")*
*Researched: 2026-07-29*
