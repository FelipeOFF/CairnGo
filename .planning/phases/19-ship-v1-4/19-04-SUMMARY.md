---
phase: 19-ship-v1-4
plan: "04"
subsystem: release
tags: [release, changelog, git-tag, python, bats]
requires:
  - "19-01: cairn-release.py check, its EXIT_* block and its docstring style"
  - "19-02: the `## [1.5.0]` CHANGELOG section, including its `### Upgrading` subsection"
  - "19-03: the .cairn ignore fix that makes the migration answer true"
provides:
  - "cairn-release.py notes VERSION — release notes derived from one CHANGELOG section"
  - ".planning/phases/19-ship-v1-4/19-RELEASE-NOTES-1.5.0.md — the derived body, for --notes-file"
  - "annotated git tag v1.5.0, LOCAL ONLY, carrying the same derived body"
affects:
  - "the text published to users; nothing else at runtime"
tech-stack:
  added: []
  patterns:
    - "subcommand on the existing .py, wrapper header in lockstep"
    - "golden byte-for-byte test as the proof that a derivation does not rewrite"
key-files:
  created:
    - .planning/phases/19-ship-v1-4/19-RELEASE-NOTES-1.5.0.md
  modified:
    - cairn/scripts/cairn-release.py
    - cairn/scripts/cairn-release.sh
    - tests/cairn-release.bats
    - CHANGELOG.md
decisions:
  - "The section preamble leads `## What changed`. The plan's rule named only the subsections; the [1.5.0] section opens with the one-sentence summary of the whole release, and dropping it would have thrown away the best line in the notes."
  - "One spelling of the migration subsection, `### Upgrading`, with no alias list. An alias nobody tested is a second way to be wrong."
  - "An EMPTY migration subsection is the same finding as an absent one. Without it, a bare `### Upgrading` heading defeats the whole gate."
  - "Heading scans honour fenced code blocks, so a CHANGELOG entry that quotes a markdown heading inside ``` cannot cut a section in half."
  - "The annotated tag carries the derived body verbatim instead of the hand-written condensation the three 1.4.x tags carry — that condensation was a third text to keep in agreement."
metrics:
  duration: ~55min
  completed: 2026-08-01
  tasks: 2 of 3 (task 3 is the blocking human checkpoint)
  commits: 4
actuals:
  tokens: 17961       # chars/4 over the five files changed (71846 chars)
  tokens_diff_only: 6110   # chars/4 over the added lines alone (24440 chars)
  tasks: 2
  commits: 4
status: complete
---

# Phase 19 Plan 04: Release notes derived, tag created locally, publication left to the human

**`cairn-release notes 1.5.0` cuts the CHANGELOG's `## [1.5.0]` section and relabels it into the published order; the annotated `v1.5.0` tag carries that same body byte for byte; nothing was pushed or published.**

## What was built

### `notes VERSION` (cairn-release.py, cairn-release.sh)

One derivation, three consumers. The rule is fixed and deliberately dumb — the
command writes no prose, it cuts and labels:

1. find `## [<version>] - <date>`, cut to the next version heading, exclusive;
2. print `## Am I affected?` then the `### Upgrading` body, literal;
3. print `## What changed` then the section preamble and every other
   subsection, literal, in order, with their own `###` headings preserved.

Steps 2 and 3 are in the published order the three 1.4.x releases established —
the user's question first, the change list last — which is the opposite of Keep
a Changelog's order. Reordering and labelling is deterministic; rewriting would
not be.

Exit codes stay `0` / `2` / `6`. A section with no (or an empty) migration
subsection exits 6; a version absent from the CHANGELOG exits 6 naming the
version, never empty output with exit 0. The `.sh` usage and exit-code header
moved in lockstep, and the docstring records what was MEASURED (which
subsections each real section carries) versus what is ASSUMED (one spelling of
the migration heading).

### The notes file and the tag

`.planning/phases/19-ship-v1-4/19-RELEASE-NOTES-1.5.0.md` is the redirected
output of the derivation and is byte-identical to it. The annotated tag
`v1.5.0` was created **locally** at `d09b7f4` with `--cleanup=verbatim`
(default `strip` would have eaten every `##` heading as a comment) and its
object body is byte-identical to `title + derived body + "Full notes:
CHANGELOG.md"`.

Title line, the only sentence of this release written by hand, and the one that
serves both the tag subject and the release title:

    cairn 1.5.0 — phase state stops being a guess, and independent phases run at the same time

`check --require-tag` now exits 0 with all four carriers, so D-02's fourth
equality is proved for the first time in the cycle.

## Verification

`bats tests/cairn-release.bats` — 14/14 before, **21/21 after**.
`bats tests/cairn-doctor.bats` — 60/60 before and after.

Seven new tests, each with its named break performed, watched red, then
restored byte-identically from a `cp` backup (never `git checkout`, the tree
held uncommitted work):

| Break | Red |
|---|---|
| reflow every block (collapse interior whitespace) | 15 |
| cut to EOF instead of the next version heading | 15, 16 |
| swap the question and changes labels | 15, 17 |
| derive without a migration answer | 18 |
| accept a bare migration heading | 19 |
| swallow the absent-version finding, exit 0 | 20 |
| default the version argument | 21 |

Restored: 21/21 green, source sha256 identical to the pre-break copy.

Task 2's `<verify>` ran all eight steps green, including the remote read that
does NOT silence error: `git ls-remote --tags origin refs/tags/v1.5.0` answered
with **status 0 and empty output**. "I did not push" and "I could not ask" got
different verdicts, which is the same demand this phase makes of phase state.

## Deviations from Plan

### [Rule 1 - Bug] A cross-reference the derivation inverts

**Found during:** Task 2, reading the derived output.
**Issue:** the `### Upgrading` body said the generated files were "described
just above" — true in CHANGELOG.md, where the `### Fixed` entry precedes it,
and FALSE in the release notes, where the derivation puts the migration answer
first and the change list after. The published text would have pointed the
reader up at nothing.
**Fix:** name the files instead of their position, so the sentence is true on
both surfaces. Fixed in the CHANGELOG and the notes regenerated, per the plan's
own rule that the notes file is never edited by hand.
**Files modified:** CHANGELOG.md
**Commit:** a7973e2

### Two tests that were strengthened after their break stayed GREEN

Not a plan defect — an execution one, caught by actually running the breaks
instead of asserting they would work:

- The golden fixture was one flat line per entry. Under the reflow break,
  collapsing whitespace on lines that have none changed no bytes, so the
  golden — the one test whose entire job is to catch a rewrite — stayed green.
  The fixture entries now wrap onto indented continuation lines, the way the
  real CHANGELOG's do. The fixture comment records why.
- The absent-version test only grepped the version string, which the
  no-migration message also carries, so two different failures reported
  identically. It now greps the distinct `## [9.9.9]` phrasing and refutes
  `Upgrading`.

### Plan defects found

1. **The derivation rule does not say what happens to the section preamble.**
   Step 3 says "the other subsections"; the preamble is not a subsection. Taken
   literally, the derived notes would silently drop `cairn stops inferring that
   a phase is done…`, which is the single best summary of the release. Decided:
   the preamble leads `## What changed`, before the first `###`. Recorded here
   because a future reader will otherwise read the docstring against the plan
   and find them disagreeing.

2. **An empty `### Upgrading` heading would have passed the gate.** The plan
   only requires the ABSENCE of the subsection to exit 6. A heading with
   nothing under it satisfies "has a migration subsection" while answering
   nothing — the exact failure the gate exists to prevent, with the paperwork
   in order. Both are now the same finding, with test 19 pinning it.

3. **`git tag -F` defaults to `--cleanup=strip`, which deletes every line
   starting with `#`.** The plan says to build the tag message from the derived
   body without mentioning this; done naively, the tag would have silently lost
   `## Am I affected?`, `## What changed`, `### Added` and `### Fixed` — and the
   plan's own `comm` check would have caught it, which is to its credit.
   `--cleanup=verbatim` is required and is now recorded.

## Known Stubs

None.

## What was NOT done, on purpose (D-04)

No `git push` of any commit or tag. No `gh release create`. No call that writes
to the remote. The four commits and the tag are local. The two commands that
publish are handed to the human at the checkpoint.

## Self-Check: PASSED

- `.planning/phases/19-ship-v1-4/19-RELEASE-NOTES-1.5.0.md` — FOUND
- commits 727f013, a7973e2, d09b7f4 — FOUND in `git log`
- `refs/tags/v1.5.0` — FOUND, object type `tag`
- `git ls-remote --tags origin refs/tags/v1.5.0` — answered, empty
