# Phase 11 — Verification

**Verified:** 2026-07-28
**Requirements:** PANEL-02, PANEL-03
**Verdict:** both met. 1 known coarseness carried to phase 12 (not a gap).

## PANEL-02 — pending work is a described list

> **Done when** an operator can pick the next phase without opening ROADMAP.md.

| Claim | Evidence |
|---|---|
| Pending phases are described, not listed as ids | Test "pending phases are described": the rendered board carries the titles and the states, not just numbers |
| Each entry states where the phase stands | `not planned` / `planned` / `executed` / `verified`, plus plan progress when the counts are known |
| …and what it is about | Title and requirement ids per entry |
| A blocked phase says what it waits on | Test "a pending phase says what it waits on" asserts `waits on 3` |
| Completed phases drop out | Test slices the rendered PENDING block and asserts the two complete fixture phases are absent |
| The operator does not need ROADMAP.md | Everything the roadmap line carries — title, requirements, progress, completion — is on the board |

## PANEL-03 — next commands, with the reason for their order

> **Done when** the suggestion is computed from state rather than authored, and
> the reason for the order is stated rather than implied.

| Claim | Evidence |
|---|---|
| Commands are computed from state on disk | Test walks the ladder on one phase: no artifacts → `/cairn:plan 3`, PLAN → `/cairn:work 3`, SUMMARY → `/cairn:verify 3` |
| They are `/cairn:*`, the operator's own namespace | Every emitted command is a cairn verb |
| Order comes from the graph, not the number | Test builds a fixture where phase 3 is blocked by an open phase-4 issue and asserts the *later* phase sorts first and unblocked |
| The reason is stated | Test asserts both `phase 4 waits on it` and `waits on phase 3` appear |
| A finished milestone gets the closing pair | Test ticks every phase and asserts exactly `["/cairn:ship", "/cairn:milestone complete"]`, with the milestone named in the second reason |
| The terminal and the HTML cannot drift | Test reads the computed commands from `--json`, then asserts every command **and every reason** appears in both the rendered terminal panel and the written HTML file |
| It is scriptable | `--json` carries `next_commands` with a fixed key set, asserted by test |

## Defect found and fixed during this phase

`blocked_by` was computed from the roadmap checkbox, so a phase **verified on
disk** but not yet ticked kept every phase behind it reading "waits on 10". A
dependency is satisfied by the work being done, not by the bookkeeping catching
up. Found by reading the real board mid-phase rather than by a test; the model
now treats `complete or disk_state == "verified"` as satisfied.

## Rendered and measured

Measured in a real browser rather than eyeballed:

- No horizontal scroll at 1512px or 680px; the panel stacks below 760px.
- Column heads share a baseline (546px); phase numbers all at 258px, titles all
  at 295px.
- No child overflows its card, so the chamfered corner shaves no glyph.
- Contrast sampled from the rendered pixel: painted background `rgb(29,27,21)`,
  giving 4.75–4.80:1 for secondary text — clear AA. The token-based estimate
  (5.03) was optimistic, which is why the pixel was sampled.

## Carried to phase 12 (known, not a gap)

Phase-level `blocked_by` aggregates every issue edge in the phase, so a phase
holding one free issue and one blocked issue reads as blocked. That is true of
the phase as a whole and coarser than the lanes above it; PANEL-04's parallelism
work is where the distinction belongs.
