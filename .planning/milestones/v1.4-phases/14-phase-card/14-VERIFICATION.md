---
phase: 14-phase-card
verified: 2026-07-31T00:00:00Z
status: gaps_found
score: 3/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Cada card nomeia o propósito da fase (CARD-01, roadmap success criterion 1)"
    status: partial
    reason: >
      roadmap_phase_rows()'s Card/Goal state machine flushes the buffer on
      ANY line matching BOLD_LABEL (`^\*\*[^*]+\*\*:?`), not only on a real
      new label. Phase 17's real Goal text in the current ROADMAP.md wraps
      across three lines and the second line starts with the emphasis word
      `**propõe**` (bold, no colon, mid-sentence) — that line matches
      BOLD_LABEL and triggers an early flush(), truncating the collected
      Goal text before the sentence-ending period exists. The
      first-sentence-fallback regex then finds no period and returns the
      truncated fragment verbatim. Confirmed against the live tree (not a
      synthetic fixture): `phases[17].purpose` is
      `"quando as fontes discordam, uma investigação lê código, história e
      memória e"` — grammatically incomplete, ends on the Portuguese
      conjunction "e" with no period — and the same string appears verbatim
      in the terminal PURPOSE list and would appear in the HTML page. Every
      other pending phase (13-16, 18) renders a correct, complete-sentence
      purpose; this is a single markdown-shape edge case, not a total
      feature failure, but it is real, reproducible today, and no test in
      tests/cairn-phase-card.bats or tests/cairn-phase-model.bats exercises
      a Goal/Card block containing an inline bold span at the start of a
      continuation line, so the suite is green while this criterion is
      false for one real phase.
    artifacts:
      - path: "cairn/scripts/cairn-status.py"
        issue: "roadmap_phase_rows()'s Card/Goal state machine (~L741-859): BOLD_LABEL flush is over-broad — it fires on any bold span at line-start, not only on a genuine new `**Label:**` line."
    missing:
      - "Narrow the continuation-line flush condition (e.g. require BOLD_LABEL to be followed by `:` before treating it as a new label, or require the matched bold text to be one of the known roadmap label words) so an inline emphasis word inside a wrapped Goal/Card paragraph does not truncate the collection."
      - "A regression test with a Goal/Card block whose second line opens with a bold emphasis word (mirroring the real Phase 17 shape) asserting the full multi-line text is captured."
---

# Phase 14: Phase card Verification Report

**Phase Goal:** toda superfície passa a dizer o que a fase É e por onde ela passou, nas
mesmas palavras — hoje o card mostra número, título e estado, e o terminal mostra
menos que o HTML.

**Verified:** 2026-07-31
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md § Phase 14, 4 success criteria — the standard)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Cada card nomeia o propósito da fase, se houve research, planos feitos/total, issues fechadas/total e o veredito da verificação | ⚠️ PARTIAL (see gap) | `phase_purpose_text()`/`phase_research_text()`/`phase_issues_text()`/`phase_verify_text()` (`cairn-status.py:1065-1098`) render all four fields on both surfaces for every pending phase — but `phases[17].purpose` is truncated mid-sentence on the real, current `ROADMAP.md` (see gap below). 5/6 pending phases (13, 14, 15, 16, 18) render correctly; phase 17 does not. |
| 2 | Board no terminal e página HTML renderizam os mesmos campos a partir da mesma leitura — provado por um teste que renderiza os dois e compara, não por inspeção | ✓ VERIFIED | `tests/cairn-phase-card.bats::"purpose/research/issues/verify render identically across --json, the terminal panel and the HTML page"` — passing. The test recomputes every expected string **from the raw `--json` scalars by literal string formatting**, never by calling `phase_research_text()`/`phase_issues_text()`/`phase_verify_text()` (confirmed by reading the test body: the comparison script is a bare `python3 -c` heredoc that only does `json.loads` + string formatting, never `import cairn-status` or any call into the module under test). This genuinely catches a bug inside the shared helpers, not just a bug in one caller. |
| 3 | Uma fase à qual falta um artefato diz qual falta, em vez de omitir a linha e deixar a ausência parecer ausência de informação | ✓ VERIFIED (as narrowed by D-04) | `check_phase_artifacts()` in `cairn-doctor.py:1006` (check 12, id `phase-artifacts`) names a `PLAN.md lacks its SUMMARY` and an unreadable `VERIFICATION.md status:` field, gated on `disk_state == "verified"`. Board itself renders a bare `—` for "nothing yet" per D-04's explicit narrowing (see D-04 discussion below — this is deliberate scope reduction, documented, not an accidental gap). |
| 4 | O card nomeia o que a fase espera e o próximo comando, com a razão de estar naquela posição na ordem | ✓ VERIFIED | `tests/cairn-phase-model.bats::"the next command carries the reason it sits where it does"` and `::"a milestone with nothing pending is told to ship, then close out"` — both passing, both re-run in this verification (see Behavioral Spot-Checks). The `next` table column carries the command; the `PURPOSE` list carries the routing reason beside each phase's purpose (D-02). |

**Score:** 3/4 truths verified, 1 partial (gap documented, narrow scope)

### The blocker that forced a plan revision (item 1 of the verification brief)

An earlier design guarded the terminal's routing-reason section (now `PURPOSE`) on `pending` alone. Since `/cairn:ship` and `/cairn:milestone complete` are emitted by `next_commands()` with `phase: None` (global commands, not attached to any pending phase), that guard would make the terminal silently drop both commands in the all-complete case while `--json` and HTML kept them — reintroducing this phase's own stated anti-goal ("o terminal mostra menos que o HTML").

**Confirmed fixed in code:** `cairn-status.py:1821` reads `if pending or global_cmds:` — not `if pending:`. `global_cmds = [c for c in cmds if c["phase"] is None]` (L1818) is computed unconditionally before the guard, so the all-complete case (`pending == []`) still enters the block via `global_cmds`.

**Confirmed the regression test genuinely fails without the fix.** I copied `cairn/` and `tests/` to an isolated scratch directory, reverted line 1821 to `if pending:`, and re-ran `tests/cairn-phase-model.bats -f "a milestone with nothing pending is told to ship, then close out"`:

```
not ok 1 a milestone with nothing pending is told to ship, then close out
#   `assert_output_contains "/cairn:ship"' failed
# expected output to contain '/cairn:ship', got:
# ...
#   Nothing pending — the milestone is ready to ship.
```

The terminal output with the guard reverted has no `/cairn:ship` or `/cairn:milestone complete` anywhere — exactly the bug the plan-checker caught and the fix addresses. On the real (unmodified) tree, the same test passes (re-run below, 28/28 in the full `cairn-phase-model.bats` file). **Verdict: the fix is real and load-bearing, not cosmetic.**

### CARD-03 parity test methodology (item 2 of the verification brief)

Read `tests/cairn-phase-card.bats::"purpose/research/issues/verify render identically across --json, the terminal panel and the HTML page"` (L192-255) directly. The comparison script:

```python
expected = {
    "purpose": p["purpose"],
    "research": "yes" if p["research_done"] else "—",
    "issues": f"{p['issues_done']}/{p['issues_total']}",
    "verify": p["verify_status"],
}
for label, text in expected.items():
    for surface, blob in (("terminal", term), ("html", html)):
        assert text in blob, (label, surface, text)
```

This is a standalone `python3 -c` script that only calls `json.loads` and string formatting — it never imports `cairn-status.py`, so it structurally cannot call `phase_research_text()`/`phase_issues_text()`/`phase_verify_text()`, even by accident. The test's own comment states this explicitly ("this script never imports cairn-status.py... A bug inside one of those shared functions would make both surfaces agree on the same wrong value; recomputing independently is what actually catches that"). **Verdict: the test does what it claims — it does NOT call the function under test to build its own expectation.**

### The `**Card:**` fallback (item 3 of the verification brief)

Confirmed via `.planning/ROADMAP.md`: only Phase 18's detail block carries a `**Card:**` line (`grep -c '\*\*Card:\*\*' .planning/ROADMAP.md` → 1, at Phase 18). Phases 13, 14, 15, 16, 17 rely entirely on the Goal first-sentence fallback.

Three dedicated tests exist in `tests/cairn-phase-card.bats` for the three resolution shapes:
- `"a Card line wins verbatim over a distracting Goal in the same block"` — a synthetic Phase 1 with both a Card and a distracting Goal (`DISTRACTINGWORD`); asserts the Card text wins and `DISTRACTINGWORD` never appears.
- `"a Goal-only block falls back to the first sentence, dropping the second"` — a synthetic Phase 2 with a two-sentence Goal, the second sentence carrying `SECONDSENTENCEMARKER`; asserts the resolved purpose is the first sentence **and explicitly asserts `SECONDSENTENCEMARKER` is absent** — proving only the first sentence was taken, not the whole block.
- `"a phase with neither Card nor Goal reads purpose as null, not a fabricated string"` — a synthetic Phase 3 with a directory but no detail block; asserts `purpose is None`.

All three pass (re-run below). **However**, this fallback logic has a real bug not caught by any of the above fixtures — see the gap recorded in frontmatter and the "Anti-Patterns / Bugs Found" section below: a genuine field-less phase in the real roadmap (Phase 17) exposes an edge case (an inline bold span opening a continuation line) that none of the synthetic fixtures reproduce.

### The narrowed criterion, D-04 (item 4 of the verification brief)

`check_phase_artifacts()`'s docstring (`cairn-doctor.py:1006-1051`) explicitly documents the residual gap, quoted verbatim:

> "Known, accepted residual gap — written down rather than left as a silent trap: a phase stuck at disk_state "executed" (its SUMMARY-less plan sits there, nobody ever runs /cairn:verify on it, so it never reaches "verified") never fires this check either. The narrowed gate trades that false negative for the mid-flight false positive it was built to remove; check 5 (phase-complete-open) independently covers the ROADMAP-checkbox-complete flavor of the same on-disk gap."

This is exactly D-04's own motivating example ("a fase estreitamento... a ausência inesperada (uma fase `executed` sem SUMMARY, por exemplo) é o que merece marca"), and it is written into the code, not merely into the plan or SUMMARY. **Verdict: the residual gap is documented as required.**

### CARD-02's fields (item 5 of the verification brief)

`purpose`, `research_done`, `issues_done`/`issues_total`, `verify_status` are all:
- Computed once in `phase_model()` (`cairn-status.py:954-957`) and exposed on every `phases[]` entry (confirmed by `tests/cairn-phase-card.bats::"every phases[] entry carries a purpose key, even phases with no detail block and no roadmap row"`).
- Rendered in the terminal table (`phase_panel_lines()`, `rsch`/`plans`/`issues`/`verify` columns + `PURPOSE` list, L1717-1834).
- Mirrored in HTML (`html_phases()`, `.phase-purpose` paragraph + three `.phase-meta` spans, L2600-2628), via the identical `phase_*_text()` helper functions — never re-derived.
- CSS for `.phase-purpose`/`.phase-meta` present in `cairn/templates/status-board.html` (L504, L517).

**Verdict: VERIFIED**, both surfaces.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `cairn/scripts/cairn-status.py` | `phase_purpose_text`/`phase_research_text`/`phase_issues_text`/`phase_verify_text`, `phase_has_research`/`phase_issue_counts`/`verification_status`, `roadmap_phase_rows()` Card/Goal parse, `phase_panel_lines()` table+PURPOSE rewrite, `html_phases()` mirror | ✓ VERIFIED (with the gap above) | All functions present, wired, exercised by passing tests; purpose-parsing has the documented edge-case bug |
| `cairn/scripts/cairn-doctor.py` | `check_phase_artifacts()` (check 12, id `phase-artifacts`) | ✓ VERIFIED | Present, wired into `main()`'s `checks = [...]`, docstring documents D-04's residual gap, 5/5 bats tests passing |
| `cairn/templates/status-board.html` | `.phase-purpose`/`.phase-meta` CSS | ✓ VERIFIED | Present at L504/L517 |
| `cairn/docs/commands/doctor.md` | `phase-artifacts` routing entry, check count bumped, `external-ref` renumbered | ✓ VERIFIED | Confirmed present via grep |
| `tests/cairn-phase-card.bats` | 8 tests: purpose resolution ×3, key-presence, research_done, issue counts, verify_status, cross-surface parity | ✓ VERIFIED | 8/8 passing (re-run) |
| `tests/cairn-phase-model.bats` | Regression coverage for the table/PURPOSE redesign and the global-command guard | ✓ VERIFIED | 28/28 passing (re-run) |
| `tests/cairn-doctor.bats` | `phase-artifacts` check coverage (5 tests) | ✓ VERIFIED | 5/5 passing (re-run, `-f phase-artifacts` filter per test_state guidance — full file not re-run, ~10min) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `phase_model()` | `phases[].purpose/research_done/issues_done/issues_total/verify_status` | direct assignment L954-957 | ✓ WIRED | |
| `phase_panel_lines()` | `phase_purpose_text()`/`phase_research_text()`/`phase_issues_text()`/`phase_verify_text()` | direct calls | ✓ WIRED | |
| `html_phases()` | same four helpers | direct calls | ✓ WIRED | Same functions, not re-derived — this is what CARD-03's parity claim rests on |
| `check_phase_artifacts()` | `cairn-status.py --json` | subprocess + `disk_reasons` cross-reference | ✓ WIRED | |
| `roadmap_phase_rows()` Card/Goal state machine | `phases[].purpose` | `card_text`/`goal_text` dicts resolved post-loop | ⚠️ PARTIAL | Wired and mostly correct; BOLD_LABEL over-matches on inline bold spans (gap above) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Regression test genuinely fails without the `pending or global_cmds` fix | Reverted L1821 to `if pending:` in an isolated scratch copy, ran `bats tests/cairn-phase-model.bats -f "a milestone with nothing pending..."` | `not ok 1` — `/cairn:ship` absent from terminal output | ✓ PASS (confirms the fix is load-bearing) |
| `tests/cairn-phase-card.bats` full file, unmodified tree | `bats tests/cairn-phase-card.bats` | `1..8`, all `ok` | ✓ PASS |
| `tests/cairn-phase-model.bats` full file, unmodified tree | `bats tests/cairn-phase-model.bats` | `1..28`, all `ok` | ✓ PASS |
| `tests/cairn-doctor.bats -f phase-artifacts`, unmodified tree | `bats tests/cairn-doctor.bats -f phase-artifacts` | `1..5`, all `ok` | ✓ PASS |
| Real `--json` purpose values for phases 13-18 on the live `ROADMAP.md` | `python3 cairn/scripts/cairn-status.py --json --planning-dir .planning` | Phase 17's purpose is a truncated fragment (`"...história e memória e"`, no closing period); phases 13-16, 18 are complete sentences | ✗ FAIL (the gap) |
| Real terminal board render carries the same truncated phase-17 purpose | `bash cairn/scripts/cairn-status.sh --width 120` | `17  quando as fontes discordam, uma investigação lê código, história e memória e — waits on phase 16` | ✗ FAIL (confirms the bug reaches the actual terminal output, not just `--json`) |

### Anti-Patterns / Bugs Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `cairn/scripts/cairn-status.py` | ~774-796 (`roadmap_phase_rows()` Card/Goal state machine) | `BOLD_LABEL` (`^\*\*[^*]+\*\*:?`) matches any bold span at line-start, including an inline emphasis word mid-paragraph, not only a genuine `**Label:**` heading | ⚠️ Warning (narrow, reproducible, real-data) | Phase 17's purpose renders as a grammatically incomplete fragment on the live board today; no regression test covers this shape |

No `TBD`/`FIXME`/`XXX` debt markers found in the files this phase modified. No stub patterns (`return null`, empty handlers, hardcoded static returns) found — every field traced to a real read of disk/bd/roadmap.

### Requirements Coverage

| Requirement | Description | Source Plan | Status | Evidence |
|---|---|---|---|---|
| CARD-01 | Todo card de fase diz para que a fase serve, não apenas seu número e estado | 14-01, 14-02 | ⚠️ PARTIAL | `phase_purpose_text()` wired on both surfaces for all phases; real-data bug truncates phase 17's purpose (gap above) |
| CARD-02 | O card informa se houve research, planos feitos/total, issues fechadas/total e o veredito da verificação | 14-01, 14-02, 14-03 | ✓ SATISFIED | `research_done`/`issues_done`+`issues_total`/`verify_status` computed, rendered on both surfaces, doctor names missing artifacts on verified phases |
| CARD-03 | O board no terminal carrega a mesma informação da página HTML — uma leitura só | 14-02 | ✓ SATISFIED | Cross-surface parity test independently recomputes expectations from raw `--json` scalars, never via the functions under test |
| CARD-04 | O card nomeia o que a fase espera e qual o próximo comando, com a razão de estar naquela posição | 14-02 | ✓ SATISFIED | `next` column + `PURPOSE` list reason; global-command guard fix verified load-bearing |

**bd cross-check:** `bd list -l m-v1.4,phase-14 --all --json` shows all four issues (`CairnGo-r4t` CARD-01, `CairnGo-hew` CARD-02, `CairnGo-1u6` CARD-03, `CairnGo-gnk` CARD-04) as `in_progress`, claimed but not yet closed — consistent with the SUMMARY notes that closing/reconciliation is the orchestrator's job pending this verdict. Given the CARD-01 gap above, **CARD-01 should not be closed as fully satisfied without either fixing the parsing bug or an explicit override decision**; CARD-02/03/04 have clean evidence and can be closed.

**ROADMAP.md / REQUIREMENTS.md reconciliation:** `.planning/ROADMAP.md`'s Phase 14 checkbox is still `[ ]` and `.planning/REQUIREMENTS.md`'s CARD-01..04 checkboxes are still `[ ]` — expected and explicitly deferred to the orchestrator per all three SUMMARY files ("STATE.md/ROADMAP.md/REQUIREMENTS.md are intentionally NOT updated... the orchestrator reconciles those shared files at wave merge time"). Not itself a phase-14 code gap, but noted since it gates issue-closing.

### Human Verification Required

None. The purpose-truncation gap was confirmed programmatically against the real `ROADMAP.md` and the real rendered terminal/HTML output — no ambiguity requiring human judgment.

### Gaps Summary

Three of four roadmap success criteria (2, 3, 4) and three of four requirements (CARD-02, CARD-03, CARD-04) are cleanly verified: the code is real, wired on both surfaces, and backed by tests that would catch a regression (confirmed directly by reverting the load-bearing guard and watching the regression test fail).

The one gap is narrow but real: `roadmap_phase_rows()`'s Card/Goal continuation-line parser treats any bold span at the start of a line as a new label and flushes early, which truncates Phase 17's actual Goal text on the live `.planning/ROADMAP.md` into a grammatically broken fragment with no closing period. This reaches the real terminal board today (`bash cairn/scripts/cairn-status.sh`), not just a hypothetical. It does not crash anything, does not violate CARD-01's letter (a purpose string is still shown, never null/fabricated), but it does violate CARD-01's substance for one specific phase — the card does not correctly say what phase 17 is for. This is squarely a case where the green test suite (238/238, including this phase's own 8+28+5 re-run above) does not prove the criterion, because no fixture reproduces the real document's inline-bold-continuation shape.

**Recommendation:** narrow the `BOLD_LABEL` flush condition (require a trailing colon, or match only the known label set) and add a regression test mirroring Phase 17's actual shape before closing CARD-01. This is a small, well-isolated fix — not a re-architecture — and does not implicate CARD-02/03/04.

---

_Verified: 2026-07-31_
_Verifier: Claude (gsd-verifier)_
