# Field report — migrate leaves roadmap-complete phases open

Source: an adopting repository with ~40 GSD phases already delivered, migrated with cairn **1.2.0** / bd **1.1.2**, `migrate --mode A`. Issue ids below are anonymised (`acme-*`).

## Confirmed facts

- Plan: 298 steps (59 create_epic, 78 create_issue, 57 frontmatter_beads, 52 dep_add, **29 close_issue**, 22 gen_map, 1 bd_init). Apply: 293 executed, **5 failed**; re-run: 79 executed, 214 already done, same 5 failures.
- Phases 1-25: **no directory** under `.planning/phases/` → no SUMMARY/VERIFICATION → migrate emitted no close steps for them (root cause #1).
- No `migrate-journal.json`; state lives in `.cairn/migrate-state.json` (25 KB, JSONL of completed steps).

## Findings not covered by the local diagnosis

1. **Exit 0 on the first run despite 5 failures** — apply reported success while failures had occurred (expected: EXIT_PARTIAL 8). Exit-code propagation was broken on that path.
2. **The 5 close_issue failures are bd refusing to close a parent with open children**: every one reads `bd close acme-X: cannot close: blocked by open issues [acme-Y] (use --force to override)`.
   Cascade: complete phases with no directory stayed open → their epics blocked epics of *later* phases that DID have artifacts → even those closes failed. Fix: close in topological order (blockers first), and/or `--force` on migration closes.
3. **Completeness is also expressed as a milestone range**: besides `- [x] Phase N:` (no bold — real lines look like `- [x] Phase 23: Backend production ready — PR #453 merged`), the roadmap marks phases complete through collapsed blocks: `<summary>✅ v1.0 MVP (Phases 1-5.1) — SHIPPED 2026-04-09</summary>`. The completeness parser has to expand `(Phases X-Y)` ranges carrying COMPLETE/SHIPPED, decimals included. In-flight phases appear as a bare `### Phase 48:` heading with no checkbox.
4. **Zero-pad mismatch**: label `phase-1` (unpadded, correct) against a title reading "Phase 01" — matching must tolerate it.

## Example: a complete phase left open

`acme-0oe` [EPIC] Phase 25, labels `m-v1.5, phase-25`, metadata `gsd {milestone v1.5, phase 25}`, **BLOCKS `acme-62l`** (epic for Phase 26), status OPEN. Migrate emitted `create_epic` and a `close_issue` for phase 26 (which had a directory), but that close failed on blocker `acme-0oe` — phase 25, no directory, never got a close step of its own.

## Remediation needed for already-migrated repos

The code fix prevents new migrations from producing this state. It does not repair repositories already migrated with 1.2.0 or earlier: their bd databases still hold open issues for delivered phases, plus the dependency chains those open issues block. Those repos need an explicit, ordered bulk-close path.
