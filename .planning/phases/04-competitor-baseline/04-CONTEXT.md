# Phase 4: Competitor Baseline - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning
**Source:** Autonomous run. The competitor CHOICE is deliberately delegated to this phase's research (flagged since the roadmap); everything else below is locked.

<domain>
## Phase Boundary

A competing workflow plugin is benchmarked fairly, on its own documented defaults, through the same isolated pipeline. Requirement: COMP-01. bd issue: CairnGo-3jj — see `04-BEADS-MAP.md`. Highest reputational risk of the milestone: a misconfigured competitor arm published publicly is the single worst outcome available.

</domain>

<decisions>
## Implementation Decisions (locked)

### Competitor selection (research decides WHICH, these are the criteria)
- **Must NOT be GSD-family**: `buildomator/buildomator` IS upstream GSD (renamed; verified live in Phase 2) — the `gsd-only` arm already covers it. Candidates: GitHub spec-kit, BMAD-method, ralph-specum, or another non-GSD Claude Code workflow plugin with real adoption.
- **Decisive criterion: headless viability** — the plugin must work under `claude -p` + `--plugin-dir` provisioning in an isolated HOME with API-key auth (the pipeline shipped in Phase 2). A competitor that can't run headless can't be benchmarked fairly; research must VERIFY this per candidate (not assume), and pick the strongest candidate that passes.
- **Pin exactly** like the others: repo + tag/commit, recorded in the manifest with a dated comment.

### Fairness discipline (non-negotiable — Pitfall 5)
- The competitor runs on **its own documented defaults** — its README/quickstart is the configuration authority, mirrored into the manifest. No tuning it down, no tuning cairn up.
- Same task prompt, same fixture, same pinned model, same `claude_flags` as every other arm; only provisioning differs.
- The manifest carries a `defaults_source` field: URL/path of the competitor doc the configuration was taken from, so any reader can audit the arm's setup against the vendor's own instructions.
- Re-verification checkpoint is part of the phase (the roadmap demands it): after staging, an explicit check that the competitor plugin actually LOADS and its commands are visible to claude in the isolated env — a silently-broken arm measuring "vanilla with dead weight" is the misconfiguration disaster this phase exists to prevent.

### Mechanics (reuse, don't invent)
- `stage-plugins.py` gets the competitor entry (git+tag provisioning, same shape as GSD's).
- New `benchmarks/baselines/competitor-<name>.json` manifest (name carries the plugin, e.g. `competitor-spec-kit`).
- Stub-first tests as always; CI $0. Live validation conditional on ANTHROPIC_API_KEY exactly like Phase 2's pending check.

### Claude's Discretion
- Which candidate wins (per criteria above), manifest naming details, how the load-check is implemented (e.g. `claude -p "/help" --plugin-dir ...` expecting the plugin's commands listed — via stub in CI, documented live procedure).

</decisions>

<canonical_refs>
## Canonical References

- `.planning/research/PITFALLS.md` — Pitfall 5 (misconfigured competitor arm) is THIS phase's reason to exist
- `.planning/research/FEATURES.md` — competitor landscape notes (buildomator claim, spec-kit/BMAD mentions)
- `benchmarks/scripts/stage-plugins.py` + `benchmarks/baselines/*.json` — the mechanics to extend
- `.planning/phases/02-baseline-isolation-multi-baseline-harness/02-0{2,3}-SUMMARY.md` — staging + conditional-live patterns

</canonical_refs>

<specifics>
## Specific Ideas

- The load-check ("plugin visible in isolated env") doubles as a keepable artifact: its output belongs in the SUMMARY as the audit trail that the arm was alive.

</specifics>

<deferred>
## Deferred Ideas

- Corpus growth — Phase 5. Charts/publication — Phase 6. Running the full N=5 live matrix — data collection happens when the corpus exists (Phase 5/6 boundary).

</deferred>

---
*Phase: 04-competitor-baseline*
*Context gathered: 2026-07-26 via autonomous run*
