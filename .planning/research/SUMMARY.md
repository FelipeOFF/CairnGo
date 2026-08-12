# Project Research Summary

**Project:** cairn v1.4 "Honest State"
**Domain:** Multi-source state corroboration, cooperative phase leases, and an append-only journal for a GSD↔beads CLI plugin
**Researched:** 2026-07-29
**Confidence:** HIGH

## Executive Summary

cairn's status board decides a phase's state by checking whether four filenames exist on disk — never opening them, never asking `bd`, never asking `git`. Three consecutive 1.4.x releases shipped because a signal reported success without proving it (a `gsd_run` shim missing from PATH, a capability gate that no-ops when its script is missing, a `|| echo "skipped"` that turned failure into success). This milestone exists to replace that single fragile read with a corroborated one, add a cooperative lease so two agents in the same phase is a visible fact rather than a silent race, and add an append-only journal so the history of what actually happened survives a crash or a disagreement. All four researchers converged on the same diagnosis and, largely, the same cure: never collapse independent signals into one enum, never silently treat "I couldn't check" as "it's fine," and never let anything but a human-gated command write a correction once sources disagree.

The recommended approach requires no new dependency — every primitive is `subprocess`, `os`, `json`, the `git` CLI, and the `bd` CLI, already present in this codebase (STACK). The corroboration model should be additive, Kubernetes-conditions-style (a parallel `evidence`/`corroboration`/`conflicts` structure sitting beside the untouched, four-value `disk_state` field), a conclusion `ARCHITECTURE` reached by reading this repo's own code and `FEATURES` reached independently by surveying Terraform, Kubernetes, jj, and `kubectl describe` — two unrelated methods landing on one design is the strongest single signal in this research set. Phase leases should ride `bd`'s own claim primitive rather than a new lockfile, because `bd` already syncs cross-machine and already carries actor/timestamp/staleness semantics this milestone would otherwise have to reinvent. The journal should stay local, gitignored, append-only JSONL, and — critically — must never be read as the authoritative "current state" on its own; it is one more input to the same corroboration model that already covers disk/bd/roadmap, never a shortcut around it.

The one finding that changes scope, not just implementation: **the fourth corroboration source named in the milestone's own language — "git commits that reference bd ids" — is empty.** A live `git log --all` grep across this repository's entire 239-commit history finds zero matches, because the repo squash-merges every PR and nothing has ever been wired to stamp a bd id into a commit message or trailer (STACK). This is not a corner case to special-case later; it is the current, 100%-of-history state, and the requirement must be rewritten before roadmap-building proceeds, not discovered mid-implementation. Beyond that, the research surfaced one genuine, unresolved design fork — file-based leases (STACK) versus a bd lease-issue (ARCHITECTURE) — which this summary resolves in favor of the bd lease-issue, with one open verification item flagged for the requirements step.

## Key Findings

### Recommended Stack

No new package. The entire feature is buildable from Python's standard library (`subprocess`, `os` for atomic file primitives, `json`, `hashlib`/`uuid`, `socket`, `time`) plus the `git` and `bd` CLIs cairn already shells out to. The research question was never "what library" but "which stdlib primitive is actually correct" — several intuitive answers (`os.rename` for lock acquisition, `PIPE_BUF` for append atomicity, `open(path, "a")` for atomic writes) are verified wrong in this exact environment and documented with the correct replacement (STACK).

**Core technologies:**
- `os.open(O_CREAT|O_EXCL|O_WRONLY)` or `os.mkdir` — atomic "create-or-fail" lease acquisition (only relevant if a local-file lease component ever exists; see Lease Placement below) — verified `os.rename` silently overwrites and cannot detect contention (STACK)
- `os.open(O_APPEND)` + single `os.write()` per line — the only recipe that actually gets POSIX's atomic-append guarantee for journal writes; a buffered `io.TextIOWrapper` (`open(path, "a")`) does not reliably map to one syscall (STACK)
- `git log --grep` / `-S` / `-G`, tiered by cost, narrowed by pathspec and `--since` — the corroboration query pattern, with a hard requirement to check `git rev-parse --is-shallow-repository` first and degrade to `unknown` rather than trust a possibly-corrupted shallow-clone result (STACK)
- `bd update --external-ref` — an existing, currently-unused `bd` flag that becomes the practical replacement for commit-message bd-id linkage (see Collision 1 below)
- `.gitattributes` `*.jsonl merge=union` — a real, zero-config git capability, verified to work, but verified to reorder and silently deduplicate byte-identical lines; PITFALLS independently argues this specific driver is the wrong tool for an order-sensitive log (see Collision 4)

### Expected Features

cairn's problem — a declared state silently diverging from reality — is structurally the same problem Terraform, Kubernetes, dbt, Ansible, and Pulumi already solved, in different shapes (FEATURES). The competitive bar is set by those tools, not by other GSD-family projects, none of which corroborate state against anything external at all.

**Must have (table stakes):**
- A read-only corroboration pass that never writes, mirroring `terraform plan -refresh-only` / `ansible --check` / `pulumi refresh --preview-only` — every mature tool researched gates writes behind a second, explicit command
- Independent per-signal conditions, not one collapsed enum — Kubernetes Conditions and git's staged/unstaged/untracked triad both refuse to compress multiple facts into one word; this is the direct fix for `phase_disk_state()`'s root-cause bug
- An explicit "cannot determine" / `conflict` value that never silently defaults to a guess — Kubernetes' literal `True`/`False`/`Unknown` convention, where an absent condition reads as `Unknown`, not `False`
- A human-readable diff naming which sources disagree and what each claims — Terraform's "Objects have changed outside of Terraform" note is the template: name the mismatch, not just "state mismatch"
- Machine-readable `--json` mirroring the human view, additive to the existing schema — matches `gh pr checks --json`'s bucket field and cairn's own existing `/cairn:status --json` precedent

**Should have (differentiators):**
- A named `conflict` phase-state, itemized by source, with each side's claim shown — no competitor in cairn's space corroborates state against bd/git at all, so this is a genuine advantage over the rest of the GSD family even though it's table stakes against Terraform/K8s
- A rich phase status card (identity block → conditions table → events tail → next command), modeled on `kubectl describe pod`'s three-zone layout and `systemctl status`'s "one glyph, then progressive detail" hierarchy
- Phase-level lease visibility extending the already-shipped `◆ assignee` DOING-lane marker up to phase granularity

**Defer (v2+):**
- Severity-classified conflicts (a cairn-native `.tfdriftignore` equivalent) — defer until there's a real corpus of conflict types; premature tiers on zero data is the same guessing the alert-fatigue research warns against
- Cross-repo or cross-milestone conflict trend views — no evidence any researched tool needs this at cairn's scale

### Architecture Approach

Every claim in ARCHITECTURE is grounded in code read directly from this repo, not inferred: `phase_model()` (`cairn-status.py:581-623`) is the single function all three render surfaces (terminal, `--json`, HTML) already read from, which means one additive change to its output shape reaches every surface simultaneously with no new call site. `phase_next_command()`'s bare dict-literal subscript on `disk_state` (`cairn-status.py:641-646`) is the one function that would crash with `KeyError` if the state enum were widened in place — this is the concrete reason the corroboration data must be a parallel structure, not a fifth string value.

**Major components:**
1. **Corroboration** (`phase_model()` additive keys: `evidence`, `corroboration`, `conflicts`) — compares disk/bd/roadmap/STATE.md, degrades to `unknown` on missing data, never fabricates a conflict from an absent source
2. **Phase lease** (`cairn-lease.py`/`.sh`, wired into `work.md`/`execute-wave-pre.md` for acquire and `verify.md`/`verify-post.md` for release) — a dedicated bd issue per phase, claimed/released through bd's existing primitive
3. **Journal** (`cairn-journal.py`/`.sh`, JSONL at `.cairn/journal.jsonl`) — cairn's own observed-transitions log, local and gitignored, never a replacement for corroboration
4. **Escalation** (`cairn/commands/reconcile.md` + `cairn-doctor.py --apply-reconciliation <N>`) — a capability split into a provably write-free analysis path and a separate, human-gated apply path, not a prompt instruction trusted to hold

### Critical Pitfalls

Every pitfall in the research is graded against one question: does this feature introduce a new way to report success without proving it — the exact bug shape that cost three prior releases (PITFALLS). Full list of fifteen pitfalls is in `PITFALLS.md`; the five that most directly threaten this milestone's own premise:

1. **Fail-open corroboration** (Pitfall 3) — an unreachable `bd` or failed `git` call must produce `unknown`, never a silent "no conflict found." This is graded the single highest-priority test to write, ahead of any feature code.
2. **The cry-wolf detector** (Pitfall 1) — mtime-only diffs, regenerated-JSON key reordering, and case-path mismatches must be allowlisted with a justification *before* shipping, or `conflict` trains people to ignore it, exactly the alert-fatigue failure Terraform teams already hit.
3. **The conflict nobody clears** (Pitfall 4) — a `conflict` with no consequence (nothing blocks, nothing ages) is functionally identical to no detection, except it now erodes trust in every other signal on the board.
4. **Journal-as-ground-truth** (Pitfall 11) — reproducing `phase_disk_state()`'s exact bug shape with a new artifact, by letting any "current state" helper replay the journal alone instead of cross-checking live sources. A hand-edit outside cairn's own commands must still be caught, even though the journal never saw it.
5. **Escalation that writes what it was told only to propose** (Pitfall 12) — an agent with Write access and a "resolve this" framing will often take the shortest path to a green state; the fix has to be a permission boundary the agent structurally lacks, not an instruction it is trusted to obey.

## Where the Research Agreed, and Where It Collided

### 1. The git corroboration signal is empty — this changes the requirement, not just the implementation

STACK ran a live `git log --all --format='%H%n%B' | grep -oE 'CairnGo-[a-z0-9]+'` against this repository's full 239-commit history: **zero matches, anywhere** — not in a subject, body, or trailer. This repo squash-merges every recent PR (verified via single-parent chains despite `(#N)` in subjects), which destroys every intermediate commit message from the source branch; the squash body itself has never carried a bd id. PITFALLS independently names the same mechanism from the outside (Pitfall 2: "starved corroboration") citing squash-merge's well-documented attribution loss and shallow clones (`actions/checkout@v4` defaults to `fetch-depth: 1`) as a second, compounding way this source goes silent in CI.

**Resolution:** treat git-sourced, bd-id-in-commit corroboration as *optional, corroborating-only evidence*, never a required or contradicting signal — its absence today is "no data," not "no work," and a design that scores it as a peer vote would mark the project's entire shipped history `conflict` on day one. Two concretely buildable replacements exist and are not mutually exclusive:
- **`bd update <id> --external-ref gh-<PR#>`** — an existing, currently-unused `bd` flag (verified present in the installed 1.1.0 binary). PR numbers are reliably present in every recent squash-commit subject (`(#18)`, `(#19)`, `(#20)` — 100% of the last 10 checked), so populating this at close time (a natural extension of the existing `post-bd-write.sh` hook) recovers a working `bd-issue → git commit` join key on *existing* history, via `git log --grep='(#18)'`, with no history rewrite.
- **A new `Bd-Issue:` trailer**, stamped automatically going forward — verified extractable via `git log --format='%(trailers:key=Bd-Issue,valueonly)'`, proven against the `Co-authored-by:` trailer already present on every commit. This prevents the gap from recurring but does nothing for history that already happened.

**Recommendation for the requirements step:** adopt both. `--external-ref` at `bd close` time closes the gap retroactively and immediately; the trailer prevents recurrence. Rewrite PROJECT.md's "four corroboration sources" language to state explicitly that signal (c) — git — is best-effort and its absence must never downgrade an otherwise-agreeing verdict from the other sources into `conflict`.

### 2. Where corroboration lives — independent convergence, not a coincidence

ARCHITECTURE reasoned from this repo's own code: widening `phase_disk_state()`'s return value in place is a category error (the function's contract is explicitly "disk facts only," and a `conflict` value folded in would make the field lie about its own definition) and a concrete crash (`phase_next_command()`'s dict subscript raises `KeyError` on any fifth value). Replacing `disk_state` with a computed object instead is worse — it silently breaks every existing `phase["disk_state"] == "verified"` consumer (dict never `==` string) and fights the codebase's own "one spelling, shared by every surface" convention.

FEATURES reached the identical shape independently, by external survey: Kubernetes Conditions (`True`/`False`/`Unknown`, each condition independent, absence reads as `Unknown`) and `kubectl describe pod`'s three-zone layout (identity block, conditions table, events log, never merged into one) are exactly this pattern; `docker compose ps` collapsing process-uptime and health-check into one `STATUS` string is the researched anti-pattern this design avoids.

**Resulting `--json` contract:** `disk_state` is untouched — same four values, same meaning, same type, for every existing consumer. Each phase row gains additive keys: `evidence` (raw per-source values: disk, bd, roadmap, state_md), `corroboration` (`"ok"` | `"conflict"` | `"unknown"`, per Collision 3's fail-open requirement), and `conflicts` (a list of itemized, human-readable mismatch strings, empty when `corroboration` is `"ok"`). `phase_next_command()` gets one new guard clause *before* its existing dict lookup, which can never `KeyError` because the enum it indexes on never grows.

### 3. Lease placement — two real designs, not a false disagreement, resolved in favor of bd

**STACK's design:** a lease file rooted at `git rev-parse --path-format=absolute --git-common-dir` (not `.planning/` or `.cairn/`, both of which are physically different files per `git worktree` — verified by creating a real worktree and diffing the resolved paths). This is load-bearing specifically because this user's stated workflow is one worktree per concurrent agent; a lease inside `.planning/`/`.cairn/` would be invisible to a second agent working the same phase from a different worktree and would fail at exactly the scenario it exists to catch.

**ARCHITECTURE's design:** no new file at all — a dedicated bd issue per phase (`phase-<N> lease`), acquired via `bd update <lease-id> --claim` and released via `bd update <lease-id> --assignee "" --status open`, the exact primitive cairn already uses for per-plan issue claims today.

**Comparison:**
- *Worktree problem:* STACK's git-common-dir path solves visibility across worktrees of *one* repository. The bd lease-issue solves a strictly larger problem — bd's Dolt store already syncs across machines and clones via `refs/dolt/data` on the git remote, not just worktrees of one local checkout, so it covers the worktree case as a subset of a broader guarantee, with zero new sync mechanism to build.
- *Crash recovery:* STACK's file design requires new, hand-rolled staleness machinery (heartbeat TTL written into the lease file, `os.kill(pid, 0)` as a same-host fast path, session-hook-driven renewal) — all verified correct, but all net-new code and new atomicity primitives to test. The bd lease-issue reuses bd's own actor/timestamp/assignee semantics and `cairn-doctor.py`'s already-shipped `claims-stale` check (check 8) almost verbatim — the same staleness pattern already built and tested for per-issue claims, extended one level up.
- *What doctor can check:* a file-based lease needs a brand-new doctor check that resolves a novel filesystem path outside `.planning`. A bd-issue lease needs a doctor check that is a near-copy of code that already exists.

**Recommendation:** the bd lease-issue (ARCHITECTURE) is the better primary design — broader coverage, less net-new surface area, and it reuses a staleness/actor pattern this codebase has already shipped and validated once. STACK's file-placement research is not wasted: its finding that `.planning/`/`.cairn/` are per-worktree and therefore wrong for *any* shared state is a general principle that should govern any local-only file this milestone does introduce (the journal, notably — see Collision 4), and the atomic-file-primitive recipes remain the correct fallback if `bd` is ever unreachable.

**Open verification item for requirements:** neither researcher confirmed where `bd`'s local Dolt database physically lives relative to a `git worktree` — if it is per-worktree rather than shared (like `.git` itself), a claim made from worktree A might not be visible from worktree B without an explicit `bd sync`, reproducing the exact worktree-invisibility problem STACK found for files. This must be confirmed before the lease design is finalized (see Gaps to Address).

### 4. The journal's authority — reconciled, and the apparent tension dissolves given ARCHITECTURE's storage choice

ARCHITECTURE states that `STATE.md` and the journal "persist independently and are cross-checked" rather than one deriving from the other — they answer different questions (`STATE.md` is GSD's hand-authored declaration of current intent; the journal is cairn's append-only observed history) with different owners. Read alone, "two files that can disagree" sounds like exactly the bug this milestone exists to kill. PITFALLS sharpens the concern precisely (Pitfall 11): any "current state" helper that replays the journal alone, without cross-checking bd/git/tree, reproduces `phase_disk_state()`'s bug shape with a new artifact — a hand-edit outside cairn's own commands would be invisible to the journal and produce a confidently wrong "everything matches."

**These are not actually in tension once Collision 2's mechanism is applied.** ARCHITECTURE's own resolution is to feed `STATE.md`'s `active_phase` in as *one more evidence source* inside the same `corroborate()` function that already reconciles disk/bd/roadmap — exactly the Kubernetes-conditions model, not a special two-file merge. If `STATE.md` claims `active_phase: 5` while lease/bd/disk evidence shows phase 5 already `verified` and all live claims sit under phase 7, that mismatch becomes a visible `corroboration: "conflict"` the same way any other mismatch does. The journal supplies *history* to explain a conflict ("disk moved to verified at 14:03, `STATE.md`'s pointer never moved after that") but is never consulted as ground truth on its own. The reconciled position: journal and `STATE.md` are two of potentially five inputs to one corroboration mechanism, never a two-way merge that must independently agree.

**The merge=union tension resolves the same way, structurally.** STACK's `.gitattributes merge=union` research (verified: real, zero-config, but verified to reorder disjoint appends non-chronologically and silently deduplicate byte-identical lines) assumes the journal is a git-tracked file merged across branches. PITFALLS independently argues (Pitfall 9) that `merge=union` is the wrong tool for an order-sensitive log, contrasting it with GitLab's legitimate use of the same driver for an order-insensitive `CHANGELOG.md`. **ARCHITECTURE's actual design sidesteps the question**: it places the journal at `.cairn/journal.jsonl`, gitignored alongside `state.json`/`conflicts.json`/`id-map.json` — a local, per-machine forensics trail, never git-tracked, never the cross-agent visibility mechanism (that job belongs to bd, per Collision 3). No git merge ever touches this file under that design, so STACK's `merge=union` caveats and PITFALLS' Pitfall 9 warning both become moot for the primary design, while remaining exactly correct as a documented reason *not* to git-track the journal later without first adopting the hash-chain alternative PITFALLS names (Pitfall 9, option b).

**Resulting position:** journal is local, gitignored, append-only, and structurally incapable of being sole authority for anything cross-machine — which is the strongest possible enforcement of Pitfall 11's "input, never authority" rule, because it cannot even see what happened on another machine. `STATE.md` remains GSD's untouched declaration. Both feed `corroborate()`; neither is asked to agree with the other directly.

### 5. Guards against reproducing the milestone's own root bug

Every researcher touched this from a different angle; consolidated into concrete, buildable guards:

- **Three-state outputs, never two.** Every corroboration source reports `agree` / `disagree` (→ `conflict`) / `unknown`; `unknown` must never silently collapse into `agree` — this is Pitfall 3's single highest-priority test, and it is the same convention FEATURES found load-bearing in Kubernetes' own API.
- **Additive-only schema changes.** `disk_state` is never widened or retyped; new evidence lives in parallel keys (Collision 2). This is what keeps `phase_next_command()`'s existing dict lookup permanently `KeyError`-proof rather than merely "probably fine."
- **A fixture corpus of known-harmless diffs, written before the detector ships.** mtime-only changes, regenerated-JSON key reordering, case-path variants must be allowlisted with a one-line justification each and proven to produce zero false conflicts (Pitfall 1) — the same discipline `bench-corpus.bats` already applies to this repo's cost claims.
- **Escalation is a capability split, not a rule.** The analysis half's source code contains zero `bd` write verbs anywhere — a fact provable by grep and testable by a bats assertion that runs it against a fixture and asserts no mutation. The apply half is a separate, explicitly human-invoked flag on the existing `cairn-doctor.py` fixer-flag pattern. An agent "wanting" to shortcut past the proposal has no tool call available that would satisfy its own task definition (ARCHITECTURE §5, PITFALLS Pitfall 12).
- **Deterministic corroboration strictly gates semantic escalation.** The LLM investigation runs only on a detected `conflict`, never on a routine status/doctor pass, and its verdict is cached by tree/commit hash so re-running against unchanged state doesn't re-spend or produce a second, different answer (Pitfall 13, matching PROJECT.md's own already-logged decision).
- **`conflict` must have a real consequence.** The ship gate refuses to advance a `conflict`-state phase; `/cairn:autonomous` excludes it from next-phase selection. A conflict with no consequence is, empirically, identical to no detection at all within weeks (Pitfall 4).
- **Every write is a script, never a prose instruction.** Journal append, lease acquire/release, and reconciliation-apply are all pushed into scripts whose source is provably free of the writes they must not make; capability fragments and command prose only ever call those scripts, never perform the write themselves (ARCHITECTURE §3, and the codebase's own already-stated "if a `SKILL.md` sentence can be a script check, make it one" rule).
- **Torn writes are quarantined, never silently dropped.** A truncated trailing journal line on read produces a WARN with its byte offset and the reader still replays everything before it — a crash must never look identical to "nothing happened" (Pitfall 10).

## Implications for Roadmap

Build order follows one dependency chain confirmed by all three non-STACK researchers: **corroboration → lease (+ journal primitive) → journal fully wired → escalation** (ARCHITECTURE §4, cross-checked against PITFALLS' pitfall-to-phase mapping and FEATURES' MVP/dependency graph, which both independently name "the per-signal conditions model" as the thing everything else requires first).

### Phase 1: State Corroboration (Conditions Model)

**Rationale:** the direct fix for `phase_disk_state()`'s diagnosed root cause; needs zero new I/O (the `bd` issues list is already fetched before `phase_model()` runs, roadmap/`complete` is already parsed) and no dependency on lease or journal. Everything downstream is unbuildable without it (FEATURES' dependency graph; ARCHITECTURE §4's smallest-slice argument).
**Delivers:** `phase_model()` gains `evidence`/`corroboration`/`conflicts` per phase row; `phase_next_command()`'s additive guard clause; a conflict marker rendered identically on the terminal board, `--json`, and HTML (all three already read from the one shared model, so this ships to all three surfaces simultaneously with no new call site); a new `cairn-doctor.py` corroboration check; resolution of Collision 1 (git signal treated as optional, `--external-ref` populated at close time).
**Addresses:** FEATURES table stakes — per-signal conditions, explicit conflict/unknown, read-only pass, itemized human-readable diff, additive `--json`.
**Avoids:** Pitfall 1 (cry-wolf — ship the harmless-diff fixture corpus first), Pitfall 3 (fail-open — three-state outputs, stubbed-failure tests for each source), Pitfall 2 (shallow-clone/squash-merge git handling — degrade to `unknown`, never guess), Pitfall 15 (mid-write read stability — read from a stable snapshot where correctness gates an action).

### Phase 2: Phase Leases

**Rationale:** buildable independently, but its user-visible payoff ("another agent in this phase is a fact, not a surprise") depends on corroboration's render plumbing already existing — a lease with no board-visible signal fails the requirement's own wording. Reuses bd's already-shipped claim/staleness/actor primitive rather than inventing a new one (Collision 3).
**Delivers:** `cairn-lease.py`/`.sh` (acquire/release/status via a dedicated bd lease-issue per phase); insertion at `work.md`/`execute-wave-pre.md` (acquire, before the per-id claim loop) and `verify.md`/`verify-post.md` (release, unconditional — pass or fail, once per phase regardless of wave count); a doctor staleness check mirroring the existing `claims-stale` check; `session-stop.sh` extended to warn on a leftover lease the same way it already warns on leftover issue claims.
**Uses:** `bd update --claim` / `bd update --assignee "" --status open` (STACK, ARCHITECTURE); STACK's git-common-dir finding retained as the general principle for any local-only file this phase might still introduce, not as the lease's primary mechanism.
**Avoids:** Pitfall 5 (advisory lease ignored — wire the check into every mutating entry point as the first action, hard-tested), Pitfall 6 (PID reuse / cross-host TTL / clock skew — heartbeat-vs-fixed-deadline, PID liveness only as a same-host fast path), Pitfall 14 (races on shared files — reuse the fix already scoped for `gbsync.py`'s lost-update bug if any local file component remains).

### Phase 3: Append-Only Journal

**Rationale:** cheap and standalone-testable, but has nothing meaningful to record until leases exist (the first genuine acquire/release *events*) — build the journal primitive alongside lease, then retrofit corroboration-transition logging into `cairn-status.py` once both exist (ARCHITECTURE §4).
**Delivers:** `cairn-journal.py`/`.sh` (`append`/`read`), local gitignored JSONL at `.cairn/journal.jsonl`, atomic single-`os.write()`-per-line appends, read-time validation that quarantines malformed trailing lines with a WARN, a compaction/snapshot design proven byte-identical to full replay.
**Uses:** the `os.open(O_APPEND)` atomicity recipe (STACK); the JSONL idiom already precedented by `cairn-migrate.py`'s resumable journal (ARCHITECTURE).
**Implements:** the Collision 4 resolution — journal and `STATE.md` both feed `corroborate()` as evidence, neither is authoritative alone, and the journal is never git-merged.
**Avoids:** Pitfall 8 (unbounded growth — compaction designed in from the start, not a later hardening pass), Pitfall 9 (union-merge reordering — moot, since the journal is never git-tracked under this design), Pitfall 10 (torn writes), Pitfall 11 (journal-as-ground-truth — a hand-edit outside cairn's own commands must still be caught by corroboration even though the journal never saw it).

### Phase 4: Semantic Escalation

**Rationale:** last by construction — needs a real `conflict` verdict to trigger on (Phase 1) and ideally journal history to read before proposing a resolution (Phase 3). Building it earlier means designing its evidence-gathering step against a corroboration shape that doesn't exist yet.
**Delivers:** `cairn/commands/reconcile.md` (new prose command, read-only tool usage — reads `bd show`, `git log`/`blame`, `.planning/*.md`); a proposal artifact reusing the already-gitignored, currently-unused `.cairn/conflicts.json`; `cairn-doctor.py --apply-reconciliation <N>` (new flag on the existing fixer-flag pattern, human-invoked, itemized report, never silent).
**Uses:** the capability-split enforcement model (ARCHITECTURE §5) — analysis and apply are separate programs with disjoint capabilities, the same separation `cairn-doctor.py` already proves works between its read-only checks and `--close-completed`.
**Avoids:** Pitfall 12 (fabricated verdicts / writes-state — permission boundary, not a prompt instruction; citation-verification against quoted file contents), Pitfall 13 (cost/noise — gated strictly behind a detected conflict, cached by tree hash, zero-invocation tested on every agreeing path).

### Phase Ordering Rationale

- Corroboration first because it requires zero new I/O and is the sole prerequisite every other component's payoff depends on (both ARCHITECTURE's code-level dependency analysis and FEATURES' external-survey dependency graph agree independently).
- Lease before journal-is-fully-wired because lease is the first component with genuine before/after state-change events; a journal with nothing real to record yet "invites false confidence that history is being kept" (Pitfall 8's framing, applied to sequencing).
- Escalation last because a read-only analysis path needs a corroboration shape to read and — ideally — journal history to cite; building it against a moving target wastes the capability-split design work.
- This order also directly matches PROJECT.md's own already-logged Key Decision — "Corroboração determinística antes de escalada semântica" — so the roadmap is not inventing a new sequencing principle, only making the milestone's own stated one concrete.

### Smallest first slice a user would notice

Extend `phase_model()`'s per-phase row with three additions that require **no new script, no new file, no new bd write, no capability/hook change**: a pure `bd_state(issues, n)` function deriving state from the already-in-hand `issues` list, a pure `corroborate(disk_state, complete, bd_state)` comparing three already-computed values, and the `phase_next_command()` guard clause plus one line each in `phase_state_text()`/`phase_panel_lines()`/`html_phases()` to render the marker. This is visible on the very next `/cairn:status` run across all three existing surfaces simultaneously (terminal, `--json`, HTML) — the literal delivery of PROJECT.md's Active Requirement #1 ("discordância vira `conflict`, nunca escolha silenciosa"), standalone, before any lease or journal code exists (ARCHITECTURE §4).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Phase Leases):** confirm where `bd`'s local Dolt database physically lives relative to a `git worktree` before finalizing the bd-lease-issue design — if it is per-worktree rather than shared, the lease inherits the same worktree-invisibility problem STACK found for files, and the requirements step needs to decide whether an explicit `bd sync` trigger at session boundaries closes that gap.
- **Phase 4 (Semantic Escalation):** the citation-verification schema (mechanically confirming a proposal's quoted evidence actually appears in the file it cites) is a real design surface with no existing precedent in this codebase — worth a short research-phase pass on structured-output verification patterns before planning the prose command.

Phases with standard patterns (skip research-phase):
- **Phase 1 (State Corroboration):** extends an existing, well-understood function (`phase_model()`) with a pattern (Kubernetes conditions) independently validated by two research methods; no external unknowns.
- **Phase 3 (Append-Only Journal):** the JSONL/atomic-append pattern is already precedented in this codebase by `cairn-migrate.py`; the storage-and-authority questions are resolved by this summary (Collision 4).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Nearly every claim reproduced live in this repo/sandbox (real `git worktree`, real shallow clone, real `flock`/`O_EXCL`/`os.rename` tests, real `.gitattributes merge=union` scratch repos). Two claims (NFS `flock` reliability, `actions/checkout` default depth) are MEDIUM — web-sourced but cross-checked against authoritative primary docs, not independently reproduced here. |
| Features | MEDIUM-HIGH | Cross-checked against official docs for every tool cited (HashiCorp, Kubernetes, dbt, Ansible, Pulumi, git-scm, Docker, GitHub CLI) plus independent practitioner sources for the alert-fatigue and CLI-density claims specifically. No live reproduction, appropriately, since this is external-ecosystem survey rather than an internal-repo question. |
| Architecture | HIGH | Every claim grounded in code read directly from this repository (`cairn-status.py`, `cairn-doctor.py`, `cairn-gate.py`, capability fragments, hooks, skill docs) — nothing inferred or guessed, no external ecosystem unknowns in play. |
| Pitfalls | HIGH | General failure patterns cross-checked against multiple independent sources (distributed-locking literature, VCS internals, database WAL design, LLM-as-judge production writeups); project-specific translation grounded directly in this repo's own `CONCERNS.md`/`PROJECT.md`, which already document a live instance of nearly every failure class named. |

**Overall confidence:** HIGH — two independent research methods (code-reading and external-ecosystem survey) converged on the same corroboration design without coordinating, which is a stronger signal than either alone; the one real design fork (lease placement) is resolved with a clear recommendation and one explicit open verification item, rather than smoothed over.

### Gaps to Address

- **bd's Dolt DB storage path relative to `git worktree`:** unconfirmed by either researcher. Must be verified during Phase 2 planning before the bd-lease-issue design is finalized as sole mechanism — if per-worktree, an explicit sync trigger (session-start/session-stop hook, or a `bd sync` call inside `cairn-lease.sh`) needs to be designed in, not discovered after the fact.
- **Exact TTL/heartbeat threshold values:** STACK and PITFALLS agree the number should be "generous, hours not minutes," but neither commits to a specific value. Pick a concrete default during Phase 2 planning, not left as an implementer's judgment call.
- **Whether `conflict` blocks `ship:pre`:** ARCHITECTURE explicitly flags this as "a milestone decision, not an implementation detail." PITFALLS is unambiguous that a `conflict` with no consequence degrades to noise within weeks (Pitfall 4). Recommend locking this to "yes, blocks" at the requirements step rather than leaving it open through planning — the twin `cairn-gate.py`/`cairn-loop-gate.py` scripts both need the identical additive check if adopted, so ambiguity here has a two-file blast radius.
- **Whether the journal should ever become git-tracked/durable across machines:** currently scoped local-only/gitignored by ARCHITECTURE's design, which is also what dissolves the `merge=union` tension (Collision 4). If a genuine cross-machine durable-audit-trail requirement emerges later, revisit with PITFALLS' hash-chain alternative (Pitfall 9, option b), never with a bare `merge=union` retrofit.
- **`--external-ref` vs. `Bd-Issue:` trailer adoption:** this summary recommends both (Collision 1), but the requirements step should confirm the `post-bd-write.sh` hook is the intended place to auto-populate `--external-ref` at close time, since that hook's contract ("fire-and-forget, never fail the caller") needs an explicit statement that this new responsibility doesn't change it.

## Sources

### Primary (HIGH confidence)
- This repository's own code, read directly: `cairn/scripts/cairn-status.py`, `cairn-doctor.py`, `cairn-gate.py`, `cairn/capability/*`, `cairn/commands/*`, `cairn/hooks/*`, `cairn/skills/cairn/SKILL.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/CONCERNS.md`, `.planning/PROJECT.md`, `.gitignore`
- Live commands reproduced against this repository (239 commits, `git 2.42.1`): `git log --grep`/`-S`/`-G`, `git rev-parse --git-common-dir`, `git worktree add`, `git clone --depth`, `bd --help`, `bd show --json`
- Scratch repos built and merged in-session to verify `merge=union`, shallow-clone, `flock`, `O_EXCL`/`os.rename`, and worktree path-resolution behavior
- `man gitattributes` (local, git 2.42.1) — primary/official source for the `union` driver's documented reordering behavior

### Secondary (MEDIUM-HIGH confidence)
- HashiCorp (Terraform drift/refresh tutorials, blog, support articles), Kubernetes (`kubernetes.io` Pod Conditions docs, `maelvls.dev`), dbt Labs Developer Hub, Ansible community docs (check/diff mode), Pulumi docs and blog (refresh/drift), git-scm.com, GitHub CLI manual, Docker docs
- jj-vcs conflicts documentation and independent commentary (Chris Krycho) on first-class stored conflicts
- Alert-fatigue and drift-severity practitioner sources (Scalr, ControlMonkey, Dev|Journal, Drift Alert Burnout)
- `open(2)`/`flock(2)` Linux manual pages (man7.org) and Lennart Poettering's file-locking analysis, for NFS/`O_APPEND` caveats
- `actions/checkout` GitHub Marketplace documentation, for CI default shallow-clone depth

### Tertiary (LOW confidence — none used)
- No tertiary-confidence claims were load-bearing in this research set; every claim in STACK and ARCHITECTURE was either reproduced live or read directly from source code, and every claim in FEATURES and PITFALLS was cross-checked against at least one official or authoritative primary source.

---
*Research completed: 2026-07-29*
*Ready for roadmap: yes*
