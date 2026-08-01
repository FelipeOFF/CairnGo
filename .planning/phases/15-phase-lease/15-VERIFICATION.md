---
phase: 15-phase-lease
verified: 2026-07-31T06:56:33Z
status: passed
score: 4/4 success criteria verified (5/5 requirements satisfied)
behavior_unverified: 0
overrides_applied: 0
---

# Phase 15: Phase lease Verification Report

**Phase Goal:** dois agentes na mesma fase vira fato visível antes do trabalho
começar, em vez de descoberta reativa no meio da execução, id por id.

**Verified:** 2026-07-31T06:56:33Z
**Status:** passed
**Re-verification:** No — initial verification (merged tree at `672e754`,
containing both Phase 14 and Phase 15's changes)

## Goal Achievement

### Observable Truths (ROADMAP.md success criteria)

| # | Truth (ROADMAP.md success criterion) | Status | Evidence |
|---|---|---|---|
| 1 | `/cairn:work N` numa fase segurada por outro actor vivo reporta quem segura e desde quando, em vez de seguir em silêncio | ✓ VERIFIED | `work.md` step 1 calls `cairn-lease.sh acquire "$N"` via `${CLAUDE_PLUGIN_ROOT}` and surfaces exit-3's verbatim report, then continues into the claim loop regardless (`cairn/commands/work.md:13-30`). The underlying exit-3/report behavior is exercised by `tests/cairn-lease.bats#acquire on a live-held phase writes nothing, exits 3, names the holder and since-when` — PASS. |
| 2 | Um lease tomado numa worktree é visível a partir de uma segunda worktree do mesmo repositório | ✓ VERIFIED | `tests/cairn-lease.bats#the tracer: lease acquired in worktree A is visible from a real second worktree B` uses a real `git worktree add` (not simulated) and asserts `held=true`/`holder=<worktree A path>` from a second, independently-invoked process pointed at worktree B — PASS. |
| 3 | Um lease cuja sessão morreu é reportado como obsoleto pelo doctor e pode ser liberado; nunca vira bloqueio permanente | ✓ VERIFIED | `cairn-doctor.py` check 13 (`check_lease_stale`, `cairn/scripts/cairn-doctor.py:1291-1358`) shells to `cairn-lease.py status --all --json` and itemizes any held+stale lease as WARN, never FAIL. `is_stale()` in `cairn-lease.py` degrades a missing/corrupt heartbeat to stale (reclaimable), never to "perpetually live" (D-04/T-15-02). A stale lease is reclaimed automatically by the next `acquire` (`tests/cairn-lease.bats#a stale lease (heartbeat older than 4h) is reclaimed by the next acquire, with a fresh acquired_at` — PASS) and reported by the doctor (`tests/cairn-doctor.bats -f lease` — 4/4 PASS, including the fresh-vs-stale and bd-failure-degrades cases). |
| 4 | A liberação acontece uma vez por fase, pass or fail; uma sessão morta à força não deixa lease que ninguém consiga limpar | ✓ VERIFIED | `verify-post.md` calls the unconditional `cairn-lease.sh release <N>` exactly once, regardless of verification outcome (`cairn/capability/fragments/verify-post.md:29-58`), using its own self-contained `CAP=` resolver block (not reused from the earlier cairn-loop-gate.sh call). `session-stop.sh` additionally releases every lease the worktree holds via `release --mine` on a clean stop. For a session that never stops cleanly (force-killed), the doctor's stale-lease WARN + automatic reclaim-on-next-acquire (criterion 3's mechanism) is the backstop that guarantees no permanent lock — proven end-to-end without either hook running by `tests/hooks.bats#the hook-never-ran risk: a lease whose heartbeat was never renewed is independently reported stale by both cairn-lease status and cairn-doctor, without either hook ever running` — PASS. |

**Score:** 4/4 success criteria verified, 0 present-but-behavior-unverified.

### Requirements Coverage

| Requirement | Description | Source Plan(s) | Status | Evidence |
|---|---|---|---|---|
| LEASE-01 | É possível ver que outro agente está trabalhando dentro de uma fase antes de entrar nela | 15-02 (work.md acquire), 15-05 (status footer) | ✓ SATISFIED | `work.md`'s acquire-before-claim-loop step (15-02) + `cairn-status.py`'s footer line, rendered only when held and fresh, identical across terminal/`--plain`/HTML (`tests/cairn-status.bats -f lease` — 8/8 PASS). |
| LEASE-02 | Entrar numa fase que outro actor vivo segura avisa quem segura e desde quando, em vez de sobrepor em silêncio | 15-01 (exit 3 contract), 15-02 (wiring) | ✓ SATISFIED | `cairn-lease.py cmd_acquire` writes nothing and reports holder/actor/acquired_at/heartbeat_at on a live conflict (exit `EXIT_HELD=3`); `work.md`/`execute-wave-pre.md` surface this verbatim and continue (D-04, never silent overwrite, never a hard stop — confirmed by grep for "stop"/"abort" returning nothing near the acquire/release steps). |
| LEASE-03 | O lease atravessa worktrees | 15-01 | ✓ SATISFIED | Real `git worktree add` tracer test, see truth #2 above. |
| LEASE-04 | Um lease deixado por sessão morta é detectável e liberável, nunca um bloqueio permanente | 15-01, 15-03, 15-04 | ✓ SATISFIED | Staleness/reclaim in `cairn-lease.py`, doctor WARN in `cairn-doctor.py` check 13, hook-never-ran risk closed by `tests/hooks.bats` (see truths #3/#4). |
| LEASE-05 | `/cairn:doctor` reporta lease obsoleto com a mesma disciplina com que já reporta claim obsoleto | 15-03 | ✓ SATISFIED | `check_lease_stale()` mirrors `check_claims_stale()`'s WARN-only, itemized, never-FAIL discipline; healthy fixture's `.checks | length` bumped 13→14 and passes (`tests/cairn-doctor.bats -f "healthy wired fixture"` — PASS). |

### Named Attack Points (from the verification brief)

1. **The `${CLAUDE_PLUGIN_ROOT}` blocker, fixed correctly.** Confirmed by direct read and grep:
   - `verify-post.md` and `execute-wave-pre.md` both use the `.gsd/capabilities/cairn` CAP-locator (`grep -n "CLAUDE_PLUGIN_ROOT" cairn/capability/fragments/{execute-wave-pre,verify-post}.md` → **zero matches**).
   - `verify-post.md` carries **two** independent occurrences of the exact resolver line (`grep -cF '...CAP=...' verify-post.md` → **2**), one for the pre-existing `cairn-loop-gate.sh` call and one newly added, self-contained, for the lease release — not a reuse.
   - `work.md` correctly keeps `${CLAUDE_PLUGIN_ROOT}` (confirmed at `cairn/commands/work.md:15`), since it is a genuine cairn command, not a fragment injected into another plugin's context. The prose explicitly documents why not to "fix" this to match the fragments.

2. **The vendored shim is a pure delegator.** `cairn/capability/scripts/cairn-lease.sh` is structurally identical to `cairn-map.sh` (same four-tier resolution, same `.beads/`/`cairn.enabled` guards, same `exec python3 ...` delegation, same "warn + exit 0" fallback). `grep -n "heartbeat\|LEASE_TTL" cairn/capability/scripts/cairn-lease.sh` → **zero matches**. All TTL/metadata logic lives exclusively in `cairn/scripts/cairn-lease.py`.

3. **The shim's exit-0 degrade is distinguished from a real write by content, not exit code.** `tests/capability.bats#bundle lease shim honors the .cairn/plugin-root pointer...` neutralizes both `CAIRN_PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT`, calls `acquire` through the copied shim, then makes a **follow-up `status` call through the same shim** and asserts `held: true` — proving the underlying `bd` write actually landed, not merely that the process exited 0. PASS.

4. **D-03's named risk — hook-never-ran staleness must be observable.** `tests/hooks.bats#the hook-never-ran risk: ...` never invokes `session-start.sh` or `session-stop.sh` at all; it hand-advances a real lease's `heartbeat_at` past the 4h TTL via `bd update --metadata` and asserts `stale: true` from an independent `cairn-lease.sh status` call **and** that `cairn-doctor.sh --json`'s `lease-stale` check independently reports the same phase as WARN — two independent surfaces, content-based assertions, no exit-code-only check. PASS.

5. **The lease must not appear as work.** Confirmed on all three fronts:
   - Lanes: `is_lease_issue()` in `cairn-status.py` filters `ready`/`doing`/`blocked`/`closed` before `phase_model()` ever sees them (`tests/cairn-status.bats#the lease-labeled bookkeeping issue never appears in any lane...` — PASS).
   - Doctor orphans: `NO_PHASE_EXEMPT = {"migrated-todo", "backlog", "quick", "lease"}` (`cairn/scripts/cairn-doctor.py:247`), used at the orphans check's label-intersection test (`cairn/scripts/cairn-doctor.py:711`); `tests/cairn-doctor.bats#lease-stale: the lease bookkeeping issue is exempt from check 6 (orphans) even vacant` — PASS.
   - `session-stop.sh`: the deferred-items.md finding from Plan 15-04 was fixed in Plan 15-05 — line 42 of `cairn/hooks/session-stop.sh` filters `"lease" not in (i.get("labels") or [])` inside the in_progress-issue report's Python block. The precision test `tests/hooks.bats#session-stop: the in_progress-issue report excludes the lease bookkeeping issue but still reports a genuine in_progress issue in the same run` proves the exemption is scoped correctly (lease excluded, a real in_progress issue for the same actor still reported in the same run) — PASS.

6. **LEASE-03 cross-worktree uses a real worktree.** `grep -n "git worktree add" tests/cairn-lease.bats` finds 6 call sites across the file's tracer/staleness/renew/status-all/release-mine tests — every one of them a real `git worktree add -q "$wt_b" -b wt-b-branch`, never a simulated/faked second identity.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `cairn/scripts/cairn-lease.py` | acquire/release/renew/status subcommands, TTL/staleness authority | ✓ VERIFIED | 599 lines, full contract implemented, exit codes 0/2/3/5 as documented. |
| `cairn/scripts/cairn-lease.sh` | thin exec wrapper | ✓ VERIFIED (present, not separately re-read — used transitively by every `cairn-lease.bats` test via `$LEASE`). |
| `cairn/capability/scripts/cairn-lease.sh` | locator/delegator shim, zero lease logic | ✓ VERIFIED | Mirrors `cairn-map.sh` exactly; zero heartbeat/TTL logic (grep confirmed). |
| `cairn/scripts/cairn-doctor.py` | check 13 `lease-stale`, `NO_PHASE_EXEMPT` extended | ✓ VERIFIED | Wired into `main()`'s checks list; docstring updated to "fourteen checks". |
| `cairn/scripts/cairn-status.py` | lane exclusion, `data["lease"]`, footer line on 3 surfaces | ✓ VERIFIED | `is_lease_issue()`, `fetch_lease_status()`, `active_lease()`/`lease_line_text()` shared by `footer_lines()`/`render_plain()`/`html_foot()`. |
| `cairn/hooks/session-start.sh` | backgrounded best-effort renew | ✓ VERIFIED | Job 4, inside the `.planning/`+`.beads/` guard, `nohup ... &`. |
| `cairn/hooks/session-stop.sh` | synchronous `release --mine` + confirmation line + lease exemption | ✓ VERIFIED | Both the release call and the in_progress-report exemption present. |
| `cairn/commands/work.md` | acquire as step 1, `${CLAUDE_PLUGIN_ROOT}` | ✓ VERIFIED | |
| `cairn/capability/fragments/execute-wave-pre.md` | per-wave re-acquire, CAP-locator | ✓ VERIFIED | Heartbeat rationale stated verbatim as reasoning. |
| `cairn/capability/fragments/verify-post.md` | unconditional release, CAP-locator (x2) | ✓ VERIFIED | |
| `tests/cairn-lease.bats` | 16 cases incl. real cross-worktree tracer | ✓ VERIFIED | 16/16 PASS (full run). |
| `tests/capability.bats` | 20 cases incl. 3 lease-shim tests | ✓ VERIFIED | 20/20 PASS (full run). |
| `tests/hooks.bats` | 33 cases incl. hook-never-ran risk test | ✓ VERIFIED | 33/33 PASS (full run). |
| `tests/cairn-doctor.bats` | 47 cases incl. lease-stale | ✓ VERIFIED | 5/5 PASS on `-f lease` filter (targeted, per time budget); healthy-fixture count-14 case independently confirmed PASS. Test-state claim of 47/47 full run accepted per task's documented test_state and file's declared `@test` count (47) matching. |
| `tests/cairn-status.bats` | 51 cases incl. lease footer/lane/json | ✓ VERIFIED | 8/8 PASS on `-f lease` filter (targeted, per time budget). File's declared `@test` count (51) matches claimed full-run total. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `cairn-lease.py status --all --json` | `cairn-doctor.py` check 13 / `cairn-status.py` footer | subprocess shell-out, no re-derived TTL math | ✓ WIRED | Both call sites confirmed by grep + code read; both degrade to WARN/`None` on failure, never crash. |
| lease issue's `lease` label (never `phase-<N>`) | `NO_PHASE_EXEMPT` / `is_lease_issue()` / session-stop.sh filter | label-set membership check | ✓ WIRED | Same label convention honored in all three consumers. |
| `execute-wave-pre.md`/`verify-post.md`'s `CAP=` resolver | `cairn/capability/scripts/cairn-lease.sh` | two-line CAP-locator, matching every other fragment | ✓ WIRED | Confirmed identical to the pre-existing `cairn-loop-gate.sh` pattern. |
| `work.md`'s acquire step | `cairn-lease.py` exit code 3 | "report, don't stop" prose | ✓ WIRED | Confirmed no "stop"/"abort" language near the step. |

### Behavioral Spot-Checks / Test Execution

| Test file | Method | Result |
|---|---|---|
| `tests/cairn-lease.bats` | Full run (`bats tests/cairn-lease.bats`) | 16/16 PASS |
| `tests/capability.bats` | Full run | 20/20 PASS |
| `tests/hooks.bats` | Full run | 33/33 PASS |
| `tests/cairn-doctor.bats -f "lease"` | Targeted (full run skipped — 8-10min budget per task instructions) | 5/5 PASS (4 lease-stale cases + 1 incidental "superseded-released" substring match) |
| `tests/cairn-doctor.bats -f "healthy wired fixture"` | Targeted | 1/1 PASS (`.checks | length` == 14) |
| `tests/cairn-status.bats -f "lease"` | Targeted (full run skipped — same reason) | 8/8 PASS |

No failures encountered in any run. `@test` counts declared in each file (16, 20, 33, 47, 51 = 167 in the five phase-15-touched files; 238 claimed across "all touched files" in the task brief, which includes files outside this read set) match the counts asserted by the task's documented test_state.

### Anti-Patterns Found

None. `grep -n -E "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` across all ten phase-15-touched source/hook/prose files returned one match, in `session-start.sh`'s pre-existing (unrelated, Phase-13-era) prose about `TodoWrite` — not a debt marker.

### Human Verification Required

None. All four ROADMAP success criteria and all five LEASE-01..05 requirements have either a direct passing automated test or a grep-confirmed static wiring check; no behavior-dependent truth was left unexercised.

### Gaps Summary

No gaps found. All four ROADMAP.md success criteria are met, all five LEASE requirements are satisfied, the D-03 heartbeat risk has a real closing test, the `${CLAUDE_PLUGIN_ROOT}`-vs-CAP-locator blocker from the first plan draft is correctly fixed and verified in the shipped fragments, the vendored shim is a pure delegator with no duplicated TTL logic, and the lease bookkeeping issue is invisible to every "is this real work" surface (lanes, doctor orphans, session-stop's in_progress report) with a precision test proving the exemption doesn't over-filter.

One process note, not a code gap: `.planning/REQUIREMENTS.md`'s LEASE-01..05 checkboxes are still unchecked and its status table still reads "Pending" — this is expected, since closing bd issues and updating REQUIREMENTS.md is documented as the orchestrator's job following this verification, and the 5 corresponding bd issues (`CairnGo-ec2`, `CairnGo-3s6`, `CairnGo-7gq`, `CairnGo-13q`, `CairnGo-dwl`) are confirmed `in_progress` (claimed, not yet closed) via `bd list -l m-v1.4,phase-15 --all --json`.

---

*Verified: 2026-07-31T06:56:33Z*
*Verifier: Claude (gsd-verifier)*
