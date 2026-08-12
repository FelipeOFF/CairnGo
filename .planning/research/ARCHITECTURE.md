# Architecture Research

**Domain:** GSD↔beads integration (cairn plugin) — corroborated phase state, phase leases, append-only journal
**Researched:** 2026-07-29
**Confidence:** HIGH — every claim below is grounded in code read directly from this repo (`cairn/scripts/cairn-status.py`, `cairn-doctor.py`, `cairn-gate.py`, `cairn/capability/*`, `cairn/commands/*`, `cairn/hooks/*`, `cairn/skills/cairn/SKILL.md`), not inferred or guessed. No external ecosystem unknowns are in play — this is an internal integration-design question.

This supersedes the previous `ARCHITECTURE.md` in this directory, which was v1.1 benchmark-harness research (dated 2026-07-25, unrelated to this milestone). This is not an ecosystem survey. It answers five specific architecture-integration questions for the v1.4 "Honest State" milestone (corroborated phase state, phase leases, append-only journal) against cairn's existing, shipped design. Only this file is produced (per the task's explicit output instruction) — no STACK/FEATURES/PITFALLS files, since there is no new external technology to select.

---

## 0. What exists today (baseline, so the deltas below are legible)

**The single read.** `phase_model(planning_dir, issues=None)` (`cairn/scripts/cairn-status.py:581-623`) is the one function all three rendering surfaces — the terminal board, `--json`, and `--html` — read from. It builds a list of per-phase dicts by merging `roadmap_phase_rows()` (ROADMAP.md, parsed leniently) with `phase_dirs()` (what phase directories exist on disk), then calls `phase_disk_state(pdir)` per phase and attaches `depends_on`/`blocked_by`/`next_command`. It is called from exactly two places: `main()` (`cairn-status.py:2202`, with `issues` populated from all four bd lanes) and `roadmap_phases()` (`cairn-status.py:652`, with `issues=None` — a lighter internal call used only to get `(all, done)` phase-number lists).

**`phase_disk_state(pdir)`** (`cairn-status.py:349-367`) is pure file-existence sniffing — `has("-VERIFICATION.md")` → `"verified"`, `has("-SUMMARY.md")` → `"executed"`, `has("-PLAN.md")` → `"planned"`, else `"none"`. It never opens a file, never calls `bd`, never calls `git`. This is the function PROJECT.md names as the milestone's root cause.

**`phase_next_command(p)`** (`cairn-status.py:626-646`) is a **bare dict-literal subscript** on `p["disk_state"]`:
```python
return {
    "none": f"/cairn:plan {p['number']}",
    "planned": f"/cairn:work {p['number']}",
    "executed": f"/cairn:verify {p['number']}",
    "verified": None,
}[p["disk_state"]]
```
Any value of `disk_state` outside these four exact strings raises `KeyError`. This is the one function that genuinely breaks if the enum is widened in place.

**Everything else that reads `disk_state` is already defensive.** `DISK_STATE_LABEL` (`cairn-status.py:686-691`, used by `phase_state_text()`) is a `.get(..., "unknown")` lookup — it degrades gracefully on an unrecognized value. `phase_model()`'s own use (`row["disk_state"] = phase_disk_state(pdir)` and the `done_set` comprehension `p["disk_state"] == "verified"`) is a plain equality check, not a subscript — safe under a wider value space.

**`--json` publishes the full model.** `main()` builds `data["phases"] = phases` (the raw `phase_model()` output) and, under `--json`, prints every non-underscore key verbatim (`cairn-status.py:2262-2267`). So `phases[i].disk_state` is already a public, machine-readable contract today.

**Claim, not lease, is the only concurrency primitive that exists.** Three entry paths converge on the exact same `bd update <id> --claim` / `bd close <id> --reason ...` sequence, at the *plan* (not phase) granularity:
- `/cairn:work N` (`cairn/commands/work.md:13-20`) — prose, claims every id in a plan's `beads:` frontmatter before executing it, closes on completion.
- Plain `/gsd:execute-phase N` via the GSD capability — `execute:wave:pre` (`cairn/capability/fragments/execute-wave-pre.md`) claims before wave dispatch; `execute:wave:post` (`execute-wave-post.md`) closes after SUMMARY.md is written. Registered in `cairn/capability/capability.json` at `contributions[1]` and `[2]`.
- `/cairn:autonomous` (`cairn/commands/autonomous.md`) — delegates to `/cairn:plan N` → `/cairn:work N` → `/cairn:verify N` per phase; it does not have its own claim mechanism, it inherits `/cairn:work`'s.

`execute-wave-pre.md:21-24` already documents the failure mode leases are meant to fix: *"If an id is claimed by someone else, do not steal it: surface the conflict in your output and continue with the plan (the orchestrator resolves ownership)."* — conflict discovery today is **per-id, reactive, and mid-execution**, not phase-level and up-front.

**`cairn-doctor.py` already has the two closest analogues to what this milestone needs.** Check 8, `claims-stale` (`cairn-doctor.py:645-666`), flags an `in_progress` issue whose assignee's phase-label disagrees with `STATE.md`'s `active_phase` — the existing "possible stale claim" pattern a lease-staleness check should mirror exactly. Check 5, `phase-complete-open` (`cairn-doctor.py:534-591`), is the existing model for a **read-then-optionally-fix** flow: checks run read-only by default, and `--close-completed` is a separate, explicitly-named flag that performs writes, reported post-fix, never silently. This is the exact shape the escalation-write-separation in §5 reuses.

**Two sources of local per-machine state already exist and are gitignored** (`.gitignore:3-9`): `.cairn/id-map.json`, `.cairn/state.json`, `.cairn/conflicts.json`, `.cairn/state/`. `state.json` is already read by `sync_status()` (`cairn-status.py:863-897`) for sync-pull watermarks. `conflicts.json` is declared in `.gitignore` but **not read or written by any script today** — it is reserved, unused local state, which is directly relevant to §5.

**A JSONL append-only journal pattern already exists in this codebase**, for a different feature: `cairn-migrate.py` drives `detect → plan → confirm → apply` through "a JSONL journal in `.cairn/migrate-state.json` [that] makes the whole run resumable without duplicating writes" (per `.planning/codebase/ARCHITECTURE.md`). This is the direct precedent §3 reuses rather than inventing a new persistence idiom.

**No script reads `git` state today**, except `cairn-migrate.py:479` (`git -C <dir> ...` for its own migration bookkeeping). `cairn-status.py`, `cairn-doctor.py`, and `cairn-gate.py` never call `git`. Any git-sourced corroboration claim is new I/O, not a refactor of existing code.

---

## 1. Where corroboration belongs

**Recommendation: (b) — keep `disk_state` exactly as it is, add a parallel evidence/verdict structure next to it, Kubernetes-conditions style.** Reject (a) and (c).

### Why (a) — widen the enum — is wrong, not just risky

It is not simply "the dict lookup needs a fifth key." It is a category error: `phase_disk_state()`'s docstring contract is explicitly **"how far a phase has actually got ON DISK"** — a pure filesystem fact. `conflict` is not a disk fact; it is a fact about *disagreement between sources*, one of which is disk. Folding it into `disk_state` makes the field lie about its own definition the moment two non-disk sources (bd, git) disagree while disk itself is perfectly legible (e.g., `-SUMMARY.md` exists, so disk says `"executed"`, but bd shows the phase's issues still `in_progress` — disk read succeeded; the *conflict* is elsewhere). It also throws away the one thing a `conflict` state must carry to be useful: *which* sources disagree and *why* — a bare string can't hold that, and every consumer would need a second lookup to explain the value anyway, defeating the point of widening the same field.

It is also the concrete break the question asks about: `phase_next_command(p)`'s dict subscript (`cairn-status.py:641-646`) raises `KeyError` on any value outside its four keys. That is not a hypothetical risk, it is a straight-line crash in production the moment `phase_disk_state()` (or whatever function callers read for "state") is allowed to return a fifth string.

### Why (c) — replace with a computed record — breaks the stated backward-compat requirement

Turning `disk_state` into an object (`{"verdict": ..., "claims": {...}}`) changes the JSON **type** of an already-public field. Every existing `--json` consumer doing `phase["disk_state"] == "verified"` goes from a working comparison to `False` forever (dict never `==` a string) — a silent, not loud, break. `phase_next_command`'s dict subscript on an unhashable dict raises `TypeError`, not `KeyError` — a different crash than (a), same severity. It also fights the codebase's own house style: every rendering-facing value in this file is deliberately kept as a flat string computed once and shared (`phase_progress_text()`, `phase_state_text()` — see their docstrings: *"one spelling, shared by every surface, so ... cannot read differently in two places"*). Handing three different renderers (terminal, `--json`, HTML) a nested object to unwrap independently reintroduces exactly the divergence risk `phase_model()` was built to kill.

### Why (b) is the concrete, safe answer

Add new keys to each phase row **without touching `disk_state`**:

```python
p["evidence"] = {"disk": "executed", "bd": "in_progress", "roadmap": "incomplete", "state_md": None}
p["corroboration"] = "ok"       # or "conflict"
p["conflicts"] = []             # human-readable mismatch strings when corroboration == "conflict"
```

- `disk_state`'s type, value space (4 strings), and meaning are **completely unchanged** — every existing consumer, in this repo or outside it, keeps working exactly as today. This is the literal backward-compatibility answer: the old field is a frozen subset of the new payload, nothing is removed or retyped, only added.
- `phase_next_command(p)` gets one new guard clause **before** its existing dict lookup, not a rewrite of it:
  ```python
  def phase_next_command(p):
      if p["complete"]:
          return None
      if p.get("corroboration") == "conflict":
          return "/cairn:doctor"          # or a dedicated /cairn:reconcile <N>, see §5
      return {
          "none": f"/cairn:plan {p['number']}", ...
      }[p["disk_state"]]
  ```
  The dict literal is untouched — it can never `KeyError` under this design because `disk_state`'s value space never grows. The new branch is additive.
- Every render surface that already iterates `phase_model()`'s rows picks up the new fields for free, because they all read from the one shared list — no new query, no new call site, satisfying the exact invariant `phase_model()`'s own docstring states: *"The board, `--json` and the HTML page previously each re-derived what they needed... This is the single read."* Corroboration is one more thing added to that single read, not a second read.
- It mirrors `cairn-doctor.py`'s own established vocabulary (`{status: ok|warn|fail, detail, items}` per check) — `corroboration`/`conflicts` is the same shape at phase-row granularity instead of check granularity. This is idiomatic reuse, not a new pattern for the codebase to learn.

### Exact functions/files that must change

**`cairn/scripts/cairn-status.py`:**
- **UNCHANGED:** `phase_disk_state(pdir)` — do not touch it; it stays "disk facts only."
- **NEW:** a corroboration function, e.g. `def bd_phase_state(issues, n) -> str` (derive "closed" / "in_progress" / "open" / "none" from the phase's `phase-N`-labeled issues — `issues` is already passed into `phase_model()`, zero new I/O) and `def corroborate(disk_state, complete, bd_state, state_md_active) -> (verdict, evidence, conflicts)`.
- **MODIFIED (additive):** `phase_model(planning_dir, issues=None, root=None)` — signature gains an optional `root` (needed for §1's future git-sourced evidence; not required for the MVP slice in §4, which needs only `disk_state` + `bd_state` + `complete`, all already in scope). Attach `evidence`/`corroboration`/`conflicts` to each row.
- **MODIFIED (additive guard):** `phase_next_command(p)` — new early-return branch before the existing dict lookup (shown above).
- **MODIFIED (extend, no signature change):** `phase_state_text(p)`, `phase_panel_lines()` (terminal PENDING PHASES panel), `html_phases()` (HTML pending-phase list) — read `p["conflicts"]`/`p["corroboration"]` to render an inline conflict marker; all three already take the phase dict as input, so this is a body-only change.
- **MODIFIED (call site):** `main()` (`cairn-status.py:2202`) — pass `root` into `phase_model()` once corroboration needs it beyond the MVP slice.
- **Note the second call site:** `roadmap_phases()` (`cairn-status.py:652`) calls `phase_model(planning_dir)` with `issues=None`. Corroboration must degrade gracefully here exactly the way `issue_phase_deps(issues or [])` already does (empty list in, empty edges out) — `bd_state` becomes `"unknown"` and `corroboration` stays `"ok"` (never fabricate a conflict from absent data) when no issues are supplied.

**`cairn/scripts/cairn-doctor.py`:**
- **NEW check** (e.g. check 11, `phase-corroboration`) that calls the same `corroborate()` helper (shared, not duplicated — either both scripts import a common function or, in keeping with the codebase's "no shared runtime utility module" rule (`.planning/codebase/STRUCTURE.md` — "Where to Add New Code"), `cairn-doctor.py` shells out to `cairn-status.py --json` and reads `phases[].corroboration` off it, the same way `check_maps_fresh` already shells out to `cairn-map.py --check`). Surfaces conflicts as WARN/FAIL using the existing `{id, status, detail, items}` shape.

**`cairn/scripts/cairn-gate.py` and `cairn/capability/scripts/cairn-loop-gate.py`** (documented "standalone twin" of each other — a change to one's gating logic must be mirrored in the other, per `.planning/codebase/ARCHITECTURE.md`'s "Dual command surface, single mechanism" constraint): whether a `conflict`-verdict phase should also block `ship:pre` alongside today's "non-closed issue in a completed phase" check is a milestone decision, not an implementation detail — flag it for the roadmap, but if adopted, both files need the identical additive check.

---

## 2. Lease lifecycle

**There is no phase-level lease today — only per-issue `bd --claim`.** Two agents can each claim different, unclaimed ids under the *same* phase-N label pair right now, and nothing surfaces that as a fact until `execute-wave-pre.md`'s reactive per-id conflict check fires mid-execution on whichever id collides first.

### Where to acquire/release, and why

**Mechanism: reuse bd's own claim primitive, not a new file.** The architecture already states, as a hard rule, *"Nothing is a source of truth except the external tool that owns it"* and *".beads/ internals are never a read/write surface... every access goes through `bd ... --json`"* (`.planning/codebase/ARCHITECTURE.md`). A file-based `.cairn/leases.json` would be per-machine, gitignored, local-only state (like `state.json`/`conflicts.json` already are) — invisible to a second agent on a different machine or worktree, which directly defeats the milestone's own requirement wording: *"outro agente dentro da mesma fase é fato visível, não surpresa"* (Active requirement #2, PROJECT.md). bd is the one store that already syncs cross-machine (via `refs/dolt/data` on the git remote, per CLAUDE.md's one-line architecture summary) and already carries actor + timestamp on every write — exactly the structural advantage PROJECT.md calls out (*"bd é um banco com timestamp, autor e motivo de fechamento"*).

Concretely: introduce one dedicated, idempotently-created **lease issue per phase** — `bd create "phase-<N> lease" -l m-<milestone>,phase-<N>,cairn-lease --metadata '{"gsd":{"phase":N,"milestone":"vX.Y"}}'` the first time the phase is worked, reused thereafter (same dedup discipline the skill already documents for requirement issues). Acquire = `bd update <lease-id> --claim` (atomic assignee+in_progress, exactly today's per-id claim primitive). Release = `bd update <lease-id> --assignee "" --status open` (the exact release command `cairn/skills/cairn/SKILL.md`'s "Pause / resume" section already documents for individual issue claims). Zero new storage, zero new sync mechanism — the lease rides bd's existing multi-writer database and its existing conflict semantics (bd itself refuses a second claim on an already-claimed issue).

**New script, not new prose:** `cairn-lease.py`/`cairn-lease.sh` (`acquire N | release N | status N`), following the established script/wrapper pair pattern (`cairn-gate.py`/`.sh`, `cairn-map.py`/`.sh`) and shipping with its own `tests/cairn-lease.bats`, per `CONTRIBUTING.md`'s "every new script ships with a `.bats` file" and "scripts over prose" rules. A lease acquire/release is exactly the kind of deterministic, testable behavior the anti-pattern section of `.planning/codebase/ARCHITECTURE.md` says must not land as prose-only.

**Acquire site — the one convergence point both live paths already share:** both `/cairn:work N` (`work.md` step 1) and the `execute:wave:pre` fragment (`execute-wave-pre.md`) claim ids at the *same logical moment* — "before starting a plan." Insert `bash cairn-lease.sh acquire <N>` immediately before that per-id claim loop in **both** places:
- `cairn/commands/work.md` — new step 0/1, before the existing "for every id ... `bd update <id> --claim`" step.
- `cairn/capability/fragments/execute-wave-pre.md` — same insertion point, so plain `/gsd:execute-phase N` gets identical coverage for free (this is the codebase's own "Dual command surface, single mechanism" rule already in force for claim/close — extend it, don't invent a third path).
- `/cairn:autonomous` needs **no separate integration point** — `autonomous.md`'s "Work" step already delegates to `/cairn:work N`, so lease acquire is inherited automatically.

On "leased by someone else": surface it in output and stop before claiming any ids (a cheaper, up-front version of the existing reactive per-id conflict message in `execute-wave-pre.md:21-24`) rather than burning partial claims first.

**Release site: `verify:post` / `/cairn:verify N`, not `execute:wave:post`.** A phase can have multiple plans/waves; releasing at every wave's `execute:wave:post` would drop the lease while a later wave of the same phase still needs it. `verify:post` (`cairn/capability/fragments/verify-post.md`) and `/cairn:verify N` are the one point both paths reach exactly once, after all of a phase's execution is attempted, regardless of wave count — release there **unconditionally** (pass or fail), because tying release to "success only" leaves a lease stuck exactly when a human most needs the phase unblocked (a failed run).

### Crash, stop rule, Ctrl-C

A lease that never gets released because the process died is worse than no lease — a permanent lock. The lease must never be a hard mutex; it must be a **fact with a timestamp that can go stale**, exactly like the claim primitive it's built on (bd already has this exact property today, which is *why* `claims-stale` — check 8 — exists at all).

- **Doctor is the detector, never the auto-releaser.** New check (paired with, or extending, check 8's `claims-stale` logic in `cairn-doctor.py`): flag a phase lease whose `updated_at` predates a staleness threshold as a WARN, with the exact `bd update <lease-id> --assignee "" --status open` remedy printed — read-only detection, matching `cairn-doctor.py`'s own documented contract ("Read-only except for `--fix-labels`... and `--close-completed`"). A human or a later agent decides to break a stale lease; doctor never does it silently.
- **Crash (killed process, no hook fires):** nothing releases automatically — by design, this is not a regression from today's per-issue claim behavior, it's the same property. Doctor's staleness check is the only recovery path, deliberately, so the milestone doesn't invent a stronger guarantee than the primitive (`bd --claim`) it's built on.
- **Stop rules (`autonomous.md`'s documented "Stop rules" section):** already contains the exact sentence to extend — *"leave the repo consistent — release claims that no longer reflect active work (`bd update <id> --assignee "" --status open`)... when [a stop rule fires]."* Add phase-lease release alongside issue-claim release in that same sentence — a prose edit to an existing, already-correct pattern, not a new mechanism.
- **Ctrl-C inside a Claude Code session:** the `Stop` hook (`cairn/hooks/session-stop.sh`) already fires on every kind of session end and already resolves the current actor (`$BEADS_ACTOR` → `git config user.name` → `$USER`) to warn about leftover `in_progress` issues assigned to them. Extend it (additive — it already has a "never block, always exit 0, at most one warning line" contract) to also check for an open lease held by that same actor and warn about it in the identical style.

### What the doctor needs to check

A **new check** (numbered after the corroboration check from §1), reusing `claims-stale`'s pattern:
1. For every phase with an open (`in_progress`) lease issue: report `{holder, phase, age since last update}`. WARN when age exceeds a staleness threshold.
2. Separately (informational at minimum, likely feeding straight into §1's `corroboration: conflict`): a phase with **no lease** but `in_progress` issues under `phase-N` claimed by more than one distinct assignee — the "two agents in the same phase, nobody leased it" gap. This is where §1 and §2 meet: a lease held by actor A while bd shows `phase-N` issues claimed by actor B is exactly a `corroboration: "conflict"` in `phase_model()`, not merely a doctor-only warning — doctor is the periodic explicit health check; corroboration is the always-on signal every render surface (board/`--json`/HTML) already shows on every run.

---

## 3. Journal

### What counts as an event

The journal records **cairn's own observed transitions and actions**, not a mirror of everything bd already timestamps. bd's own DB already gives every issue an actor + timestamp on every write — duplicating that into a second log would be a second, competing source of truth for the same fact, which is the exact bug this milestone exists to kill. The journal exists for what *no* existing store captures: when did *cairn* observe a cross-source disagreement, when did a phase lease change hands, when did an automated fixer (doctor `--close-completed`) act. This scope is explicit in PROJECT.md's own Key Decisions: *"O journal só vê o que o cairn faz; humano ou outra ferramenta editando código continua invisível"* — the journal is deliberately narrower than corroboration, not a replacement for it.

### Minimum record schema

One JSON object per line (JSONL — the exact idiom `cairn-migrate.py` already uses for its own resumable journal at `.cairn/migrate-state.json`, reused here rather than inventing a new persistence shape):

```json
{"ts": "2026-07-29T14:03:11Z", "actor": "felipe", "phase": 7, "milestone": "v1.4",
 "event": "lease_acquired", "source": "cairn-lease",
 "detail": {"lease_id": "cairn-a1b2"}}
```

Event vocabulary (minimum set): `lease_acquired`, `lease_released`, `lease_stale_detected`, `corroboration_conflict_detected`, `corroboration_resolved`, `doctor_apply_reconciliation` (see §5), `doctor_close_completed` (already-existing behavior in `check_phase_complete_open`'s `--close-completed` path, currently unlogged anywhere but `bd`'s own history — this is the first genuinely new value the journal adds for an *existing* feature).

Storage: `.cairn/journal.jsonl`, gitignored alongside `state.json`/`conflicts.json`/`id-map.json` — **per-machine, local, append-only**. This is a deliberate choice, not an oversight: the journal is *not* the cross-agent visibility mechanism (bd already is one, per §2); it is a local audit trail for forensics and for corroboration to diff against its own prior verdict ("why does the board say verified when I thought it was executed? — check when disk_state actually flipped").

### Who writes

**Scripts write; prose/fragments only trigger scripts that write — never write directly.** This is the enforcement, not a convention: an LLM hand-appending JSONL from a fragment's instructions is exactly the "prose-only deterministic behavior" anti-pattern `.planning/codebase/ARCHITECTURE.md` already names and forbids (*"If a SKILL.md sentence can be a script check, make it one"*), and an append-only guarantee cannot survive LLM-authored writes (malformed lines, skipped events, inconsistent shape).

Given this codebase's own explicit rule — *"There is no shared runtime utility module (no `lib/` or `common.py`)... duplication of small helpers is the accepted tradeoff for dependency-free, independently-testable CLIs"* (`.planning/codebase/STRUCTURE.md`) — the correct primitive is a **new small script**, `cairn-journal.py`/`.sh` (`append --event ... --phase ... --detail '<json>'`, `read --phase N`), shelled out to by every writer exactly the way scripts already shell out to `cairn-map.sh`/`gbsync.sh`:
- `cairn-lease.py` shells out to `cairn-journal.sh append` on every acquire/release/staleness-detection.
- `cairn-status.py`'s corroboration step shells out on every verdict *transition* (compare against the last known verdict for that phase — read-then-append, not append-every-render — to avoid flooding the journal on every `/cairn:status` invocation).
- `cairn-doctor.py` shells out when `--close-completed` actually closes something (it already has `closed_n` and per-issue reasons in hand — this is a body-only addition to existing code) and when the new reconciliation-apply flag from §5 fires.
- **Capability fragments and command prose never call `cairn-journal.sh` directly** — they only call the scripts above (`cairn-lease.sh`, etc.), which journal internally as a side effect of a deterministic operation. This is what keeps the journal deterministic and testable by bats, matching the "scripts over prose" rule exactly.

### Relation to STATE.md

**STATE.md is not derived from the journal, and the journal does not derive from STATE.md — they persist independently and are cross-checked, exactly the way disk/bd/roadmap are cross-checked in §1.** They answer different questions and have different owners: `STATE.md`'s `active_phase`/`next_action` (read by `state_frontmatter()`, `cairn-status.py:813-829`) is GSD's own hand-authored **declaration of current intent** — per `.planning/codebase/ARCHITECTURE.md`, `.planning/*.md` is *"read leniently, never hand-written by cairn except generated map blocks"* and the skill's own Precedence section says the GSD doc always wins on conflict. The journal is cairn's append-only **observed history**. Making one derive from the other would violate that ownership boundary in one direction or the other.

The correct integration is additive, not architectural surgery: treat `STATE.md`'s `active_phase` as **one more evidence source** in §1's `corroborate()` function (`evidence.state_md_active_phase`), exactly the way `synthesize_next()` already treats it as one input among several rather than as ground truth (*"bd wins for work items, STATE.md wins for workflow steps"* — `cairn-status.py:912-923` docstring). If `STATE.md` claims `active_phase: 5` while the lease/bd/disk evidence all show phase 5 already `verified` and all live claims sit under phase 7, that mismatch becomes a visible `corroboration: "conflict"` (a "STATE.md looks stale" conflict) the same way a disk/bd mismatch does — and the journal supplies the *history* to explain it ("disk state moved to verified at 14:03, STATE.md's active_phase pointer never moved after that"). This is the literal meaning of PROJECT.md's *"estado lido, não reconstruído"*: corroboration reads the journal's last-known verdict rather than recomputing full history on every render, while `STATE.md` remains exactly what it always was, owned by GSD, never touched by cairn's own writes.

---

## 4. Build order

**Dependency chain: corroboration → lease (+ journal primitive) → journal fully wired → escalation.**

1. **Corroboration (§1) has no dependency on lease or journal.** It only needs `disk_state` (exists), a `bd_state` derivation from the `issues` list already passed into `phase_model()` (zero new I/O — the four bd lanes are already fetched in `main()` before `phase_model()` is called), and the roadmap's `complete` flag (already parsed). Git-sourced evidence is a nice-to-have, not a requirement for a first, real `conflict` verdict. This can ship standalone.

2. **Lease (§2) is buildable independently**, but its *user-visible payoff* — "another agent in this phase is a visible fact, not a surprise" — depends on corroboration's render plumbing already existing, otherwise a lease is acquired/released with no board-visible signal at all, which fails the requirement's own wording ("fato visível"). Build lease second so its conflicts (lease-holder vs. bd-claimant mismatch) have somewhere to surface.

3. **The journal's shared primitive (`cairn-journal.py`) is cheap and standalone-testable, but has nothing meaningful to record until §1 and §2 exist** — before that, the only events available are things bd's own DB timestamps already capture equally well, and an empty-in-practice log is worse than no log (it invites false confidence that history is being kept). Build the journal script/schema *alongside* lease (§2) — lease is the first component with genuine acquire/release *events* (a clear before/after state change) that benefit immediately from an append log for crash forensics — then retrofit the corroboration-transition calls into `cairn-status.py` once both exist. The retrofit cost is small: a handful of `cairn-journal.sh append` call sites inside already-built scripts, not new architecture.

4. **Escalation (§5) is last by construction** — it needs a real `conflict` verdict to trigger on (§1) and ideally journal history to read before proposing a resolution (§3). Building it earlier would mean designing its read-only evidence-gathering step against a corroboration shape that doesn't exist yet.

### Smallest first slice with a user-visible improvement

Extend `phase_model()`'s per-phase row with three in-memory-only additions — no new script, no new file, no new bd write, no capability/hook change:

- `bd_state(issues, n)` — a small pure function deriving "closed" / "in_progress" / "open" / "none" from the already-in-hand `issues` list.
- `corroborate(disk_state, complete, bd_state)` — compares three values already computed in the same function, returns `(verdict, conflicts)`.
- The `phase_next_command(p)` guard clause (§1) and one line each in `phase_state_text()` / `phase_panel_lines()` / `html_phases()` to surface the marker.

This ships in one phase, needs zero new bats-tested scripts, and is visible on the very next `/cairn:status` run across all three existing surfaces simultaneously (terminal board, `--json`, HTML) — literally *"discordância vira conflict, nunca escolha silenciosa"* (Active requirement #1) delivered standalone. It also directly matches the milestone's own stated sequencing decision in PROJECT.md's Key Decisions table: *"Corroboração determinística antes de escalada semântica."*

---

## 5. Where escalation sits, and how "never writes state" is enforced architecturally

The milestone's own Key Decision states the requirement but not the mechanism: *"A escalada nunca grava estado — só propõe. Um agente que corrige o próprio registro de estado destrói a evidência do erro."* A sentence in a fragment or a `SKILL.md` is **not** an enforcement mechanism in this codebase's own terms — `.planning/codebase/ARCHITECTURE.md` explicitly ranks *"Enforcement is layered by strength: GSD capability code > Claude Code hooks > git pre-push shim > prose convention"*, and prose is the layer this repo's own `CONTRIBUTING.md` says must justify *not* being a script ("If a SKILL.md sentence can be a script check, make it one"). An LLM investigation genuinely needs judgment (reading git history, code, memory to figure out *why* two sources disagree) and so cannot itself be a deterministic script — but that does not mean its "don't write" constraint has to live only in its instructions.

### The real mechanism: a capability split, not a rule

Structure escalation as **two separate programs with disjoint capabilities**, the same separation `cairn-doctor.py` already uses successfully between its read-only checks and its explicitly-flagged `--close-completed`/`--fix-labels` fixers:

1. **A read-only, provably-write-free analysis path.** A new command `cairn/commands/reconcile.md` (prose, genuinely open-ended LLM investigation — reads `bd show`, `git log`/`git blame`/`git show`, `.planning/*.md`, `ctx_search` context-mode memory) is fed by a new deterministic data-gathering step — either a new `cairn-evidence.py` or (preferably, to avoid duplicating logic) `cairn-status.py --json`'s existing `phases[].evidence`/`conflicts` output from §1, reused rather than re-derived. Whichever script gathers evidence contains **zero calls to any `bd` write verb** (`create`/`update`/`close`/`reopen`) anywhere in its source — a fact provable by grep, and testable by a bats assertion that runs the script against a fixture and asserts no mutation occurred. This is the same class of guarantee `check_bd_version()` / `check_req_issue()` / every read-only check function in `cairn-doctor.py` already has today: they are read-only *because their source has no write calls in it*, not because a docstring asks nicely.
2. **The LLM half's success criterion is "a proposal artifact exists," never "state is resolved."** The escalation's output is written with the ordinary Write tool to a data file, not to a tracker: reuse the already-gitignored, already-declared-but-currently-unused `.cairn/conflicts.json` (`.gitignore:5`), or append outside the generated-marker block of `NN-BEADS-MAP.md` — the codebase's own established idiom for "a manual note that survives regeneration and flags a divergence without acting on it" (`plan-post.md`'s Precedence line: *"divergent issues are flagged ⚠ and updated, not followed"*; `verify-post.md`'s reconciliation guidance is the same shape). Because the task's own definition of "done" is *producing this file*, there is no reason — not even an incentive from task-completion pressure — for the LLM to reach for `bd update`/`bd close` at all; doing so would not satisfy what it was asked to do.
3. **Applying a proposal is a separate, explicitly-invoked, human-gated write path**, following `check_phase_complete_open`'s already-proven pattern exactly: add a new flag to the *existing* `cairn-doctor.py`, e.g. `--apply-reconciliation <N>`, which reads `.cairn/conflicts.json`/the proposal and performs **only** the specific, itemized writes the proposal enumerated (same "read-modify-write" metadata discipline the skill already documents), reported post-fix the same way `--close-completed`'s report is (`closed_n`, per-issue outcome, never silent). This is a human decision surfaced through the fixer-flag convention this repo already trusts, not a new trust boundary.

### Where it sits, concretely

- **Trigger:** `cairn-doctor.py`'s new corroboration check (§1's WARN/FAIL for `conflict`-state phases) *suggests* `/cairn:reconcile <N>` in its `detail`/`items` output — doctor itself never invokes the LLM investigation; it stays exactly as read-only as it is today. The status board's footer `note` (already used identically for `stale_complete` → *"run /cairn:doctor --close-completed"*, `cairn-status.py:2216-2217`) gets the same treatment, pointing at `/cairn:reconcile` for genuine conflicts.
- **Analysis:** `cairn/commands/reconcile.md` (new prose command) + reuse of `cairn-status.py --json`'s evidence output (no new script needed for evidence-gathering if §1 is built first — this is another reason §4's ordering matters).
- **Proposal artifact:** `.cairn/conflicts.json` (reusing declared-but-dormant local state) or a note outside `NN-BEADS-MAP.md`'s generated markers.
- **Apply path:** `cairn-doctor.py --apply-reconciliation <N>` (new flag on the existing script, same file, same fixer-flag convention as `--close-completed`/`--fix-labels`, its own guarded code block — testable in isolation the same way `check_phase_complete_open`'s fixpoint bulk-close is already tested).

The guarantee is architectural, not behavioral: the analysis half's *source code* has no write calls (grep-provable, bats-testable), and the apply half is a *different command a human must separately invoke*, consuming the analysis's output as inert data rather than the analysis directly causing a mutation. An LLM "wanting" to skip the proposal and just fix it directly has no natural tool call available in its own task definition that would do so — the task is defined as "write this file," not "make bd/ROADMAP/STATE agree."

---

## Integration Points

| Surface | File | Change | New / Modified |
|---|---|---|---|
| Phase model | `cairn/scripts/cairn-status.py` | `phase_model()` gains `evidence`/`corroboration`/`conflicts` per row | Modified (additive) |
| Next-command routing | `cairn/scripts/cairn-status.py` | `phase_next_command()` gains a conflict guard before its existing dict lookup | Modified (additive) |
| Terminal/HTML rendering | `cairn/scripts/cairn-status.py` | `phase_state_text()`, `phase_panel_lines()`, `html_phases()` render the conflict marker | Modified (body only) |
| `--json` contract | `cairn/scripts/cairn-status.py` | New keys on `phases[]`; `disk_state` untouched | Additive, non-breaking |
| Doctor conflict check | `cairn/scripts/cairn-doctor.py` | New check (corroboration WARN/FAIL) | New check function |
| Doctor lease-staleness check | `cairn/scripts/cairn-doctor.py` | New check, mirrors check 8 `claims-stale` | New check function |
| Doctor apply-reconciliation | `cairn/scripts/cairn-doctor.py` | New `--apply-reconciliation <N>` flag, guarded write block | New flag/block |
| Ship gate | `cairn/scripts/cairn-gate.py` + `cairn/capability/scripts/cairn-loop-gate.py` | Possible additive check for conflict-state completed phases (roadmap decision) | Modified, twin scripts must stay in sync |
| Lease acquire | `cairn/commands/work.md`, `cairn/capability/fragments/execute-wave-pre.md` | Insert `cairn-lease.sh acquire <N>` before the per-id claim loop | New script call, both entry points |
| Lease release | `cairn/commands/verify.md` (or wherever `/cairn:verify` is documented), `cairn/capability/fragments/verify-post.md` | Insert `cairn-lease.sh release <N>` unconditionally | New script call, both entry points |
| Lease script | `cairn/scripts/cairn-lease.py` + `.sh` | Acquire/release/status via bd lease-issue claim | New script + wrapper + bats |
| Stale-lease warning | `cairn/hooks/session-stop.sh` | Extend existing actor-resolution + warning logic | Modified (additive) |
| Stop-rule release | `cairn/commands/autonomous.md` | Extend existing "release claims" sentence to include lease release | Prose edit |
| Journal primitive | `cairn/scripts/cairn-journal.py` + `.sh` | `append`/`read` subcommands, JSONL at `.cairn/journal.jsonl` | New script + wrapper + bats |
| Journal writers | `cairn-lease.py`, `cairn-status.py`, `cairn-doctor.py` | Shell out to `cairn-journal.sh append` on state-changing events | Modified (side-effect calls) |
| Escalation trigger | `cairn/scripts/cairn-doctor.py`, `cairn/scripts/cairn-status.py` | Suggest `/cairn:reconcile <N>` in doctor items / status note | Modified (message only) |
| Escalation command | `cairn/commands/reconcile.md` | New prose command, read-only tool usage, writes only the proposal file | New command |
| Proposal storage | `.cairn/conflicts.json` (already gitignored, currently unused) or `NN-BEADS-MAP.md`'s outside-marker notes | Reuse existing local-state slot / existing "manual note survives regen" idiom | Reused, not new |

## Anti-Patterns specific to this milestone

### Widening `phase_disk_state()`'s return value in place

**What happens:** Someone adds `"conflict"` as a fifth return value of `phase_disk_state()` to make the "minimal diff."
**Why it's wrong:** Breaks the function's own documented contract (disk-only facts), crashes `phase_next_command()`'s dict subscript with `KeyError`, and changes a field every existing `--json` consumer already depends on having exactly 4 values.
**Do this instead:** Add a parallel `corroboration`/`evidence` structure (§1); leave `disk_state` alone.

### Letting a fragment or `SKILL.md` sentence append to the journal or perform the lease/escalation write

**What happens:** A capability fragment or command prose is told "append an event when you do X" or "the escalation should never call `bd update`," trusting the LLM to comply.
**Why it's wrong:** This repo's own anti-pattern section calls this out directly for deterministic behavior in general; for the escalation specifically, an instruction is not an enforcement mechanism, and a wrongly-behaving agent destroys the very evidence the corroboration system exists to preserve.
**Do this instead:** Push every write (journal append, lease acquire/release, reconciliation apply) into a script whose source is provably free of the writes it must not make (§5), and give prose only the ability to call scripts, never to perform the write itself.

### Tying phase-lease release to `execute:wave:post`

**What happens:** Lease is released as soon as one plan/wave of a multi-wave phase closes its ids.
**Why it's wrong:** A phase with more than one wave still in flight loses its lease mid-phase, reopening exactly the concurrent-work-invisible gap this milestone exists to close.
**Do this instead:** Release once, at `verify:post`/`/cairn:verify N` — the one point both entry paths reach exactly once per phase, regardless of wave count, on both pass and fail.

## Sources

All findings are drawn directly from this repository's own code and docs, read on 2026-07-29:
- `cairn/scripts/cairn-status.py` (phase model, disk-state, next-command, rendering)
- `cairn/scripts/cairn-doctor.py` (check pattern, fixer-flag pattern, claims-stale)
- `cairn/scripts/cairn-gate.py` and `cairn/capability/capability.json` (ship gate, twin-script constraint)
- `cairn/capability/fragments/{plan-post,execute-wave-pre,execute-wave-post,verify-post}.md`
- `cairn/commands/{work,autonomous}.md`
- `cairn/hooks/{hooks.json,post-bd-write.sh,session-stop.sh,session-start.sh}`
- `cairn/skills/cairn/SKILL.md` (claim/release primitives, precedence rules, dedup key)
- `.planning/codebase/ARCHITECTURE.md` and `.planning/codebase/STRUCTURE.md` (layered enforcement, no-shared-lib rule, generated-view pattern)
- `.planning/PROJECT.md` (milestone requirements and the three journal/corroboration/escalation Key Decisions)
- `.gitignore` (existing `.cairn/` local-state files, including the currently-unused `conflicts.json`)

---
*Architecture research for: cairn v1.4 "Honest State" milestone*
*Researched: 2026-07-29*
