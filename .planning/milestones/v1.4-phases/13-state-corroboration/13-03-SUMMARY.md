---
phase: 13-state-corroboration
plan: "03"
status: complete
requirements: [CORR-06, CORR-08]
beads: [CairnGo-bnr, CairnGo-x4p]
---

# Phase 13 Plan 03 — Summary

The doctor learned to read the corroboration, and to repair the git link that
squash-merging destroyed.

## What shipped

**`phase-corroboration`** — fails on a `blocks`-severity conflict, warns on
`informs` or `unknown`, and routes each finding to a recommendation keyed by which
pair of sources disagreed. Two severities only, per the phase's decisions: the
research is explicit that severity tiers invented on zero real data are how alert
fatigue starts.

**`external-ref`** — the `--link-refs` backfill, following `--close-completed`
exactly: read-only by default, writes only behind the named flag, prints every id
it touches, idempotent. It matches a closed issue to its PR through the `(#N)` in
the squash-commit subject, scoped by the files the phase's plans declared and a
±2-day window, and it refuses an ambiguous match rather than guessing.

**A shallow clone stops it cold.** `git rev-parse --is-shallow-repository` is
checked before any git query. A shallow clone does not merely lack history — it
produces a *false positive* at the boundary commit, where a diff is computed
against an empty tree. That was reproduced live during research, not theorised.

## The thing worth knowing

**Six pre-existing tests changed from exit 0 to exit 7, and none was weakened.**
Each gained an assertion naming the check that now fails. Their fixtures always
contained a genuine divergence — an open issue in a phase the disk calls verified
— and until this commit nothing in the doctor looked at it. The tests were not
wrong before; they were complete descriptions of a system that could not see.

One went the other way on purpose: the `maps-fresh` fixture was corrected rather
than its assertion relaxed, swapping a `bd close` for a new open issue so disk and
bd keep agreeing and the test goes back to testing map staleness alone.

The `--close-completed` test lost its blanket `refute "⚠"`, because the fixture
now carries one legitimate `informs` divergence. Rather than accept the narrower
check, the assertion was replaced with a precise one — exactly one warning across
all checks, and it is this one — so an unexpected second warning from any other
check still breaks the test. That was the property the blanket refute was
carrying, and dropping it would have quietly reduced what this test can catch.
