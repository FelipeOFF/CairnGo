# Codebase Concerns

**Analysis Date:** 2026-07-25

## Tech Debt

**Non-atomic, unlocked `.cairn/` state file writes (`cairn/scripts/gbsync.py`):**
- Issue: `write_json()` (`cairn/scripts/gbsync.py:83-85`) does a plain read-modify-write of `id-map.json`, `state.json`, and `conflicts.json` with no file locking and no atomic replace (no write-to-temp-then-rename). `do_push()` (`cairn/scripts/gbsync.py:157-200`) reads the full `id-map.json`, mutates one entry, and writes the whole file back.
- Files: `cairn/scripts/gbsync.py`, triggered from `cairn/hooks/post-bd-write.sh:99-112` (mirror push) and the `--bg-full-push` re-invocation path (`cairn/hooks/post-bd-write.sh:29-46`).
- Impact: `post-bd-write.sh` is a PostToolUse hook that fires a `nohup bash gbsync.sh <verb> <id> &` background process on **every** `bd create/update/close/reopen` call. If the agent (or a script) issues several `bd` writes in quick succession, multiple independent `gbsync.py` processes race to read-modify-write the same `id-map.json` — a classic lost-update race that can silently drop an external-id mapping, causing a later push to create a duplicate mirror issue instead of updating the existing one.
- Fix approach: acquire an `flock`-based lock (or a lockfile with retry/backoff) around the read-modify-write in `write_json`/`do_push`/`do_pull`, and write via temp-file + `os.replace` for crash-safety.

**Markdown parsing is deliberately "lenient" regex/heuristic parsing of GSD's free-form docs:**
- Issue: `cairn-gate.py`, `cairn-doctor.py`, and `cairn-migrate.py` all infer phase completion and the active milestone by regex-matching `ROADMAP.md` checkbox lines / progress-table rows and `STATE.md` frontmatter, including a literal `🚧` emoji or `(in progress)` string match to find the active milestone (`cairn/scripts/cairn-migrate.py:329-337`, mirrored in `cairn/scripts/cairn-gate.py:14-20` and `cairn/scripts/cairn-doctor.py:51`).
- Files: `cairn/scripts/cairn-gate.py`, `cairn/scripts/cairn-doctor.py`, `cairn/scripts/cairn-migrate.py` (`parse_roadmap`, `state_active_phase`, `state_milestone`, `roadmap_milestone`).
- Impact: This is an explicit, documented design tradeoff (cairn intentionally doesn't bind to GSD internals — `cairn/docs/architecture.md:202`), but it means any drift in how the separately-versioned GSD plugin renders `ROADMAP.md`/`STATE.md` (e.g. a different progress emoji, a reworded "(in progress)" marker, a changed checkbox format) can silently misresolve the active milestone or completed-phase set — the ship gate, doctor, and migrate detector would then act on the wrong data with no hard error.
- Fix approach: add a doctor check that cross-validates the lenient parse against a stricter expectation (e.g. warn if zero phases parse when `ROADMAP.md` is non-empty) so drift surfaces as a WARN instead of silent misbehavior.

**`cairn-migrate.py` is a 1754-line monolith:**
- Issue: single file implements three migration modes (A/B/C), plan generation, a topological sort over epic/issue dependencies, an idempotent `Applier` with journaled resume, and hand-rolled YAML-frontmatter surgery (`merge_beads_frontmatter`, `cairn/scripts/cairn-migrate.py:1553-1602`) via line-based regex rather than a YAML library.
- Files: `cairn/scripts/cairn-migrate.py` (largest file in the repo by a wide margin — `cairn-doctor.py` is 630 lines, the next largest).
- Impact: high review/maintenance cost for the single highest-risk script (it mutates both `.beads/` and `.planning/*.md` in a project being migrated). A change in one migration mode's plan-building logic (`build_plan_a`/`build_plan_b`/`build_plan_c`) is easy to accidentally couple with another mode's code path since they share large stretches of state (`IssueIndex`, `StepList`).
- Fix approach: no immediate bug, but a future refactor should split plan-building (A/B/C) from the `Applier`/journal engine into separate modules to reduce blast radius per change.

**Thin `.sh` wrappers assume `python3` is present with no explicit check:**
- Issue: `cairn-gate.sh`, `cairn-doctor.sh`, `cairn-migrate.sh`, `cairn-relabel.sh`, `gbsync.sh`, `cairn-map.sh`, `cairn/capability/scripts/cairn-loop-gate.sh` all do `exec python3 "$HERE/<script>.py" "$@"` with `set -euo pipefail` but no `command -v python3` guard.
- Files: `cairn/scripts/*.sh`, `cairn/capability/scripts/cairn-loop-gate.sh`.
- Impact: on a machine without `python3` on PATH, every one of these wrappers fails with a bare "python3: command not found" and exit code 127 — not one of the documented exit codes (0/2/5/6/7) that callers branch on. `cairn-init.sh`'s pre-push shim is documented to block **only** on exit 6 and warn-not-block on exit 5 (`cairn/scripts/cairn-init.sh:105-107`); an exit-127 failure falls through that contract undocumented. The GSD capability gate (`cairn/capability/capability.json:108-121`) also has `"onError": "skip"` for the blocking `ship:pre` gate, so a `python3`-missing crash there may silently skip the blocking check rather than failing loudly.
- Fix approach: add a `command -v python3 >/dev/null || { echo ... ; exit 5; }` guard to each wrapper so a missing interpreter maps to the same "tooling unavailable, never block" exit code as a missing `bd`.

## Known Bugs

No currently open bugs are tracked in this repo's own `.beads` database (`bd list --all --json` returns zero issues as of this analysis) and this is the fresh 1.0.0 fork release, so there is no accumulated open-bug backlog. Worth noting from `CHANGELOG.md` as evidence of the fragility class above: two of the four items in the 1.0.0 "Fixed" section were CLI/parsing bugs (a zero-padded phase-directory glob resolving the wrong phase directory; `gbsync --dry-run` being silently ignored instead of implemented) — the same class of bug the lenient-parsing and thin-wrapper concerns above are prone to reintroducing.

## Security Considerations

**No timeout on outbound HTTP calls made from background (fire-and-forget) hook processes:**
- Risk: `urllib.request.urlopen(req)` is called with no `timeout=` argument in every network-calling adapter.
- Files: `cairn/adapters/jira.py:49`, `cairn/adapters/gitlab.py:46`, `cairn/adapters/azure-boards.py:49`, `cairn/adapters/asana.py:39`.
- Current mitigation: none. `github.py` shells out to the `gh` CLI instead of raw HTTP, which has its own retry/timeout behavior, but `subprocess.run(["gh", *args], ...)` in `cairn/adapters/github.py:23` also has no `timeout=`.
- Recommendations: these adapters are invoked from `nohup`'d background processes fired by the `PostToolUse` hook (`cairn/hooks/post-bd-write.sh:99-107`) after every `bd` lifecycle write — a stalled TCP connection or slow external API leaves an orphaned background process indefinitely (no supervision, no kill switch). Add an explicit timeout (e.g. 15-30s) to every `urlopen`/`subprocess.run` call in the adapters and dispatcher.

**Unpinned `curl | bash` install path for the `bd` binary:**
- Risk: both the interactive fallback instructions and CI itself install `beads` via `curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash` with no version pin or checksum verification.
- Files: `cairn/scripts/cairn-init.sh:34`, `cairn/hooks/session-start.sh:30`, `cairn/commands/init.md:74`, `.github/workflows/ci.yml:12`.
- Current mitigation: none — this is standard practice for the ecosystem and is documented as a user-facing choice (alongside `brew install` / `npm install -g`), not an automatic unattended execution against arbitrary user data.
- Recommendations: low priority, but CI in particular could pin a release tag/commit SHA of the installer rather than trusting `main` at build time, since a compromised upstream script would run unattended on every CI run.

**External tool content is trusted verbatim on pull-reconciliation:**
- Risk: `gbsync.py`'s `do_pull`/`bd_apply` (`cairn/scripts/gbsync.py:115-125`) writes an external tracker's title/body straight into `bd update --title ... --body-file -` with last-writer-wins semantics; there is no sanitization of titles/bodies pulled from Jira/GitHub/GitLab/Asana/Azure Boards.
- Files: `cairn/scripts/gbsync.py`.
- Current mitigation: `subprocess.run(cmd, input=body, ...)` uses an argv list (not `shell=True`), so shell/command injection is not possible — this is a content-integrity concern, not an injection vulnerability.
- Recommendations: none needed beyond noting the trust boundary; anyone with write access to a linked external tracker can overwrite local `bd` issue titles/bodies.

## Performance Bottlenecks

**Unbounded `bd list --all --limit 0 --json` scans on every hook-triggered full push:**
- Problem: when a `bd create` fires with no `.cairn/id-map.json` entry (the common case for a brand-new issue) and a sync backend is enabled, `post-bd-write.sh`'s `--bg-full-push` path (`cairn/hooks/post-bd-write.sh:29-46`) lists **every** bd issue in the project (`bd list --all --limit 0 --json`) and diffs it against the id-map to find every unmapped issue, then pushes each one individually via a separate `gbsync.sh create` subprocess.
- Files: `cairn/hooks/post-bd-write.sh`.
- Cause: no incremental/delta tracking of "issues created since the id-map was last built" — every unmapped-issue discovery re-scans the whole tracker.
- Improvement path: this runs backgrounded (`nohup ... &`) so it does not block the hook's 10s budget (`cairn/hooks/hooks.json`), but on a tracker with thousands of issues it could still take meaningfully long and spawn many sequential `gbsync.sh create` subprocesses (each with its own non-atomic `id-map.json` write — compounding the race condition noted above). Track a watermark of the last-scanned issue count/timestamp to avoid a full scan on every full-push trigger.

## Fragile Areas

**`post-bd-write.sh`'s positional bd-id extraction heuristic:**
- Files: `cairn/hooks/post-bd-write.sh:64-107` (the `PARSED=` python3 heredoc).
- Why fragile: to mirror the correct issue after a `bd update`/`bd close`/`bd reopen`, the hook must guess which whitespace-delimited token in an arbitrary shell command string is the issue id, by walking flags and skipping a hardcoded `VALUE_FLAGS` set (`--parent`, `--epic`, `--reason`, `-l`, `--assignee`, etc.) that must be kept in sync with `bd`'s actual CLI surface. Any future `bd` flag that takes a value and isn't added to `VALUE_FLAGS` will be misparsed as the positional id, silently mirroring the wrong issue (or none).
- Safe modification: whenever `bd`'s CLI gains a new value-taking flag, `VALUE_FLAGS` in this script must be updated in lockstep; this is an implicit contract with an external binary, not enforced by any test that fails when `bd`'s flags change.
- Test coverage: `tests/hooks.bats` exercises the parser against a fixed set of known command shapes, but does not test against `bd`'s live `--help` output, so a bd upgrade adding a new flag would not be caught automatically.

**Hand-rolled YAML frontmatter surgery instead of a YAML parser:**
- Files: `cairn/scripts/cairn-migrate.py:1553-1602` (`merge_beads_frontmatter`), `cairn/scripts/cairn-migrate.py:1493-1517` (`do_write_file`).
- Why fragile: `merge_beads_frontmatter` line-scans a `PLAN.md`'s frontmatter block looking for a `beads:` key in either inline-flow (`beads: [a, b]`) or block-list (`beads:\n  - a\n  - b`) form using targeted regexes, then rewrites just that key's lines in place. An unusual-but-valid YAML shape (multi-line flow list, an inline comment placed unusually, mixed quoting) risks either failing to detect the key (silently appending a duplicate) or corrupting the rest of the frontmatter.
- Safe modification: any change to how `beads:` frontmatter is authored elsewhere (by GSD's own plan-writing prose, or by a human hand-edit) needs to stay within the two shapes this regex understands.
- Test coverage: `tests/cairn-migrate.bats` covers the two documented shapes; there is no fuzz/property test for malformed or unusual frontmatter.

**Informal, cross-plugin capability contract with GSD:**
- Files: `cairn/capability/capability.json`, `cairn/capability/fragments/*.md`, `.claude-plugin/plugin.json` (`"engines": {"gsd": ">=1.8.0"}`).
- Why fragile: cairn's capability hooks into GSD's loop at named extension points (`plan:post`, `execute:wave:pre`, `execute:wave:post`, `verify:post`, `ship:pre`) that are owned and versioned by the separate `gsd` plugin. The `engines.gsd` constraint is an open-ended lower bound (`>=1.8.0`) with no upper bound, so a future breaking change in GSD's loop-host contract (e.g. renaming `execute:wave:pre`, changing the fragment injection format) would not be blocked by version pinning and could silently stop cairn's hooks from firing. The capability manifest itself documents one such existing gap (`execute:pre` is declared in the loop host contract but never actually dispatched, so the claim hook had to register at the narrower `execute:wave:pre` instead — `cairn/capability/capability.json:6`).
- Safe modification: any change to `cairn/capability/capability.json` extension-point names must be cross-checked against the currently-installed GSD plugin's loop-host contract, not just against cairn's own tests.
- Test coverage: `tests/capability.bats` tests the capability's own scripts/fragments in isolation; it does not (and structurally cannot, from this repo) test against GSD's actual loop dispatcher.

## Scaling Limits

**Full-table `bd list --all --limit 0` scans across the codebase:**
- Current capacity: fine for the small/solo-developer issue counts this tool targets.
- Limit: `cairn-gate.py`, `cairn-doctor.py`, `cairn-migrate.py`'s `list_issues`, and `post-bd-write.sh`'s full-push path all invoke `bd list --all --limit 0 --json` (unbounded result set) and then filter/aggregate client-side in Python. On a tracker with many thousands of issues, every ship-gate check, doctor run, and unmapped-issue full-push would need to marshal and parse the entire issue set as JSON on every invocation.
- Scaling path: none implemented; would need `bd`-side filtering (e.g. by label) pushed into the query instead of client-side filtering, where `bd`'s CLI supports it.

## Dependencies at Risk

**`bd` (beads) binary, minimum version 1.1.0, is a hard runtime dependency not manageable as a plugin:**
- Risk: cairn cannot declare `bd` as a plugin dependency (it's a standalone binary, not a Claude Code plugin), so every script independently checks `command -v bd` and every doc/hook repeats manual install instructions (`brew install beads` / `npm install -g @beads/bd` / the curl installer) in three separate places (`cairn/scripts/cairn-init.sh`, `cairn/hooks/session-start.sh`, `cairn/commands/init.md`).
- Impact: the three install-instruction copies can drift out of sync with each other or with the actual current beads release process.
- Migration plan: none needed today; worth consolidating into one canonical snippet if beads' install story changes.

**GSD plugin version drift (see "Fragile Areas" above):**
- Risk: `engines.gsd: ">=1.8.0"` has no upper bound, so a major GSD release could break cairn's capability contribution points without any version-pin failure to surface it.
- Impact: cairn's `plan:post`/`execute:wave:*`/`verify:post`/`ship:pre` hooks could silently stop firing, degrading cairn back to `.cairn.enabled`-off behavior (GSD "untouched", per the capability's own design note) without any error — a soft failure that is easy to miss.
- Migration plan: consider adding an upper bound once GSD's own breaking-change cadence is better established, or a runtime capability-version check in `cairn-doctor.py`.

## Missing Critical Features

**No locking or mock/fixture layer for the sync-adapter test surface (see Test Coverage Gaps below).**

## Test Coverage Gaps

**Zero test coverage for all five sync adapters:**
- What's not tested: `cairn/adapters/jira.py`, `cairn/adapters/github.py`, `cairn/adapters/gitlab.py`, `cairn/adapters/azure-boards.py`, `cairn/adapters/asana.py` — push/pull request construction, auth-header building, status normalization (e.g. Jira's `statusCategory` mapping, Asana's `completed` boolean, ADF↔text conversion in `jira.py`'s `adf`/`adf_to_text`), and error handling are exercised only by `python3 -m py_compile` (a syntax check) in CI (`.github/workflows/ci.yml:23`).
- Files: `cairn/adapters/*.py`; the only sync-related bats suite, `tests/gbsync.bats`, deliberately tests only the `--dry-run` path, which by design "never calls an adapter or writes id-map.json" (`tests/gbsync.bats:2-6`).
- Risk: any adapter regression (a malformed request body, a wrong status-mapping table entry, a broken transition lookup in `jira.py`'s `transition()`) would only be discovered by a real user's real external-tracker sync failing in production, since CI has no credentials for any of the five backends and cannot exercise live push/pull.
- Priority: High — this is the largest untested surface area handling real external I/O and data reconciliation (last-writer-wins conflict resolution) in the codebase.

**No concurrency/race test for `.cairn/id-map.json` writes:**
- What's not tested: the lost-update race described under Tech Debt (concurrent `gbsync.py` background invocations racing on the same state file).
- Files: `cairn/scripts/gbsync.py`.
- Risk: silent id-map corruption under realistic usage (several `bd` writes in one agent turn) would not be caught by any existing test.
- Priority: Medium.

**No timeout/network-failure simulation for adapters:**
- What's not tested: adapter behavior when `urlopen`/`gh` hangs or the network is unreachable (relevant given the no-timeout concern above).
- Files: `cairn/adapters/*.py`.
- Priority: Medium.

---

*Concerns audit: 2026-07-25*
