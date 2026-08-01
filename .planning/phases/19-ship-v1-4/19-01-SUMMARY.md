---
phase: 19-ship-v1-4
plan: "01"
subsystem: release
tags: [python, bats, versioning, doctor, semver]
requires:
  - cairn-doctor.py's env-seam convention (CAIRN_JOURNAL/CAIRN_GBSYNC/CAIRN_MAP/CAIRN_GATE)
provides:
  - "cairn-release.sh check — the version carriers compared by exit code, not by eye"
  - "--require-tag — the flag plan 19-04 uses to prove D-02's fourth equality"
  - "cairn-doctor check 15 (release-versions), applicable only where cairn's own manifests exist"
affects:
  - "cairn-doctor.py: 15 checks -> 16, and the docstring's own count with it"
tech-stack:
  added: []
  patterns:
    - "stdlib only, .py + thin .sh pair, EXIT_* constants, die(msg, code)"
    - "shell-out to a sibling script through a CAIRN_* env seam instead of reimplementing its reads"
key-files:
  created:
    - cairn/scripts/cairn-release.py
    - cairn/scripts/cairn-release.sh
    - tests/cairn-release.bats
  modified:
    - cairn/scripts/cairn-doctor.py
    - tests/cairn-doctor.bats
decisions:
  - "capability.json exempt from the equality set but NOT from semver validity (D-02), pinned by two tests from opposite sides"
  - "semver validity applies to EVERY carrier, lockstep members included — three manifests all reading a malformed 1.4 would otherwise compare equal and pass"
  - "the doctor check applies only where cairn/.claude-plugin/plugin.json exists; absence is ok, never fail"
  - "an absent git tag is 'pending' by default, a finding only under --require-tag"
metrics:
  duration: ~75min
  completed: 2026-08-01
  tasks: 3
  commits: 3
actuals:
  tokens: 10441
  tasks: 3
  commits: 3
status: complete
---

# Phase 19 Plan 01: The version-consistency command Summary

**`cairn-release.sh check` compares the plugin version's three carriers at their three different JSON key paths, validates the capability's own axis as semver, consults the `v<version>` git tag, and returns 0 or 6 — and `cairn-doctor` now runs it as check 15 so nobody has to remember to.**

## What was built

`cairn/scripts/cairn-release.py` + the `cairn-release.sh` pair + `tests/cairn-release.bats` (14 tests), plus `check_release_versions()` in `cairn-doctor.py` and 2 tests in `tests/cairn-doctor.bats`.

The carriers and their real key paths, all measured with `jq` against this repo before a line was written:

| carrier | path | key path | value |
|---|---|---|---|
| plugin | `cairn/.claude-plugin/plugin.json` | `.version` | 1.4.2 |
| marketplace | `.claude-plugin/marketplace.json` | `.metadata.version` (nested) | 1.4.2 |
| changelog | `CHANGELOG.md` | first `## [x.y.z]` heading | 1.4.2 |
| capability | `cairn/capability/capability.json` | `.version` | 1.0.0 |
| tag | git | `v1.4.2` | present |

Three carriers at three different key paths is half the reason the command exists. The roadmap said two files for three releases running; the marketplace one, nested one level deeper than the other two, is the one nobody found by looking.

## Verification — every break performed, watched red, restored byte-identically

Restores were `cp` from a backup taken before the first break; `cmp` against that backup afterwards confirms byte-identical, and `git checkout` was never used on a file carrying uncommitted work.

`tests/cairn-release.bats` — **14/14 green**; each named break run in isolation:

| break | test(s) | broken | restored |
|---|---|---|---|
| marketplace dropped from the compared set | mismatch test | 1/1 red | 1/1 green |
| CHANGELOG head no longer read | changelog test | 1/1 red | 1/1 green |
| capability folded into the equality set | own-axis test | 1/1 red | 1/1 green |
| semver validation removed | `invalid semver` test | 1/1 red | 1/1 green |
| absent file swallowed in a mute try/except | missing-file test | 1/1 red | 1/1 green |
| empty default on the version read | both key tests | 2/2 red | 2/2 green |
| `JSONDecodeError` left to propagate | malformed-JSON test | 1/1 red | 1/1 green |
| first `## [` taken blindly | `[Unreleased]` test | 1/1 red | 1/1 green |
| `--require-tag` ignored | require-tag test | 1/1 red | 1/1 green |
| unknown subcommand falls through to `check` | usage test | 1/1 red | 1/1 green |

`tests/cairn-doctor.bats` — **baseline 58/58 → 60/60 green**:

| break | test(s) | broken | restored |
|---|---|---|---|
| absence of the manifests made a failure | not-applicable test | 1/2 red (the diverging test correctly stayed green — it has manifests) | 2/2 green |
| divergence registered as `warn` | diverging test | 1/1 red | 1/1 green |
| check never added to the `checks` list | both + the healthy-fixture count | 3/3 red | 3/3 green |

Plan verify steps, all four measured after the change:

```
bash cairn/scripts/cairn-release.sh check --json | jq -e '.ok == true'                 -> true
bash cairn/scripts/cairn-doctor.sh --json | jq -e '.checks | length == 16'             -> true   (was 15)
bash cairn/scripts/cairn-doctor.sh --json | jq -e '[.checks[]|select(.id=="release-versions")]|length == 1' -> true
! grep -q 'fifteen' cairn/scripts/cairn-doctor.py                                      -> pass   (failed before)
```

Manual drift on the real repo (marketplace bumped to 1.4.3 by hand, then restored from a `cp` backup — `git status` clean afterwards):

```
[cairn-release] 1 finding(s):
  mismatch: cairn/.claude-plugin/plugin.json ('version') = '1.4.2' but .claude-plugin/marketplace.json ('metadata.version') = '1.4.3'
exit=6
```

and the doctor, on the same drift, reported `release-versions` as `fail` with the finding verbatim in its items.

## Deviations from Plan

### [Rule 2 — missing critical functionality] Semver validity extended to every carrier

The plan scoped semver validation to `capability.json`. Applied to every carrier instead: with validity checked only on the exempt one, three manifests all reading a malformed `1.4` would compare equal and the command would exit 0. D-02 exempts `capability.json` from EQUALITY, not from validity, so widening validity does not weaken the decision — and the `invalid semver`-not-`mismatch` test still passes, because the three lockstep carriers still agree in that fixture. Documented in the module docstring. Commit `a5a714f`.

### [Rule 1 — bug] The three-nothings test passed for the wrong reason

Case 6's second half ("every carrier missing its version key") first asserted only `.findings | length == 3`. Under the empty-default break it stayed **green**: the three empty strings were caught one step downstream as `invalid semver`, so the count still came to three. A test that survives its own break is exactly what this plan exists to prevent, in miniature. Tightened to assert all three findings carry the `missing` token plus `refute_in_output "invalid semver"`; it now goes red under the break as intended (2/2 red above). Commit `3912f85`.

### [Rule 2] A fifth finding token

The plan named four stable tokens (`mismatch`, `invalid semver`, `missing`, `pending`). Malformed JSON is none of those — a file that exists and parses to nothing is not "missing" — so `invalid json` was added and documented in the docstring's token list. Case 7's test asserts on the message and the absence of a traceback, not on the token, so nothing in the plan is contradicted.

## What the plan got wrong

**The git tag for the current version already exists.** The plan states the fourth carrier "does not exist yet when this plan runs" and prescribes `pending`. Measured: `v1.4.0`, `v1.4.1` and `v1.4.2` are all present, so today's check reports the tag as an **ok** carrier, not pending. The plan's assumption describes the state *after* 19-02 bumps to 1.5.0, when `v1.5.0` will indeed be pending. Both paths are implemented and both are tested (`pending`, `--require-tag`, and present-and-matching), so nothing had to be reworked — but the plan's premise about today is false, and `--require-tag` is therefore already satisfiable at 1.4.2 rather than only after the tag step.

**The doctor docstring's numbering was already drifting.** `check_external_ref`'s own docstring says "Check 12" and `check_lease_stale`'s says "Check 13", while the module docstring numbers them 13 and 14. Not touched — out of scope for this plan and unrelated to its changes — but the file presents itself as canonical specification, and two of its checks disagree with it about their own number. Logged below.

## Deferred / out of scope

- `cairn-doctor.py`'s internal check-number drift (`check_external_ref` says 12, module docstring says 13; `check_lease_stale` says 13, module docstring says 14). Pre-existing, unrelated to this plan's changes, not fixed here.
- The `gsd-core` pin (`ref: v1.8.0` in the marketplace) versus the capability's `engines.gsd` — explicitly out of scope per the plan's objective.

## Known Stubs

None. No placeholder values, no empty defaults, no unwired data paths — the empty-default read is precisely the failure mode two tests exist to forbid.

## Requirement status — the half that is NOT done

REL-02 has two halves. This plan delivers the first: **an executable check exists that compares the three lockstep carriers and validates the fourth by its own rule.** The second half — the version actually bumped to 1.5.0 — belongs to plan 19-02 and is **not done here**.

At the end of this plan `cairn/.claude-plugin/plugin.json` still reads **1.4.2**, and so do the marketplace and the CHANGELOG. `CairnGo-ro4` covers both halves and was deliberately left open: a tracker saying "version bumped in lockstep" while `plugin.json` reads 1.4.2 would be, in miniature, exactly the green-without-proof this milestone is named after. `.planning/STATE.md`, `ROADMAP.md` and `REQUIREMENTS.md` were left untouched at the operator's instruction — they are reconciled centrally.

## Self-Check: PASSED

- `cairn/scripts/cairn-release.py` — FOUND
- `cairn/scripts/cairn-release.sh` — FOUND
- `tests/cairn-release.bats` — FOUND
- commit `a5a714f` — FOUND
- commit `3912f85` — FOUND
- commit `82f8f11` — FOUND
