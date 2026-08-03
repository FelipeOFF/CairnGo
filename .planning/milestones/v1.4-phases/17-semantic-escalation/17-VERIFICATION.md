---
phase: 17-semantic-escalation
verified: 2026-07-31T23:16:29Z
status: human_needed
score: 3/4 roadmap success criteria fully behaviorally verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "SC2 / ESC-04: 'a investigação roda apenas sobre conflito detectado — um teste afirma zero invocações numa passada em repositório onde tudo concorda.' The mechanical half (cairn-reconcile.py collect refuses on a non-conflict verdict, writes nothing) IS bats-proven against a real fixture — independently re-run and confirmed in this verification. What is NOT proven by any test: that the reconcile-investigator subagent (the Task-tool spawn inside /cairn:reconcile) is never invoked on a non-conflict phase, or that /cairn:reconcile's D-04 cache check actually skips re-spawning on a hash match at runtime."
    test: "Run /cairn:reconcile N once against a genuinely all-agree phase (corroboration == 'ok') in a live session and confirm no Task-tool subagent spawn occurs. Separately, run /cairn:reconcile N twice in a row against an unchanged conflicted phase and confirm the second run presents the cached proposal without a second Task-tool spawn."
    expected: "Zero Task-tool invocations on the all-agree run; zero NEW Task-tool invocations on the second, hash-matching run against the conflicted phase."
    why_human: "bats cannot spawn the Task tool — there is no precedent anywhere in this test suite for a bats test invoking a real LLM subagent, so this specific runtime invariant can only be proxy-tested by static ordering of the command's own committed prose (tests/cairn-reconcile-agent.bats), never exercised live."
human_verification:
  - test: "Run /cairn:reconcile N once against a genuinely all-agree phase and confirm no Task-tool subagent spawn occurs; run it twice against an unchanged conflicted phase and confirm the second run reuses the cached proposal without re-spawning."
    expected: "Zero subagent invocations on the all-agree run; zero new subagent invocation on the cache-hit run."
    why_human: "bats cannot invoke the Task tool — only the command's own prose ordering is statically checked (tests/cairn-reconcile-agent.bats), never a live run."
  - test: "Decide whether ESC-01's literal third evidence source ('memória') needs to be wired into cairn/agents/reconcile-investigator.md's tools: frontmatter, or whether the código+história-only scope shipped in this phase is accepted as-is."
    expected: "Either an explicit acceptance of the current scope, or a follow-up plan granting the investigator a context-mode MCP tool (e.g. mcp__plugin_context-mode_context-mode__ctx_search, or ctx_search once a canonical name is confirmed for this harness)."
    why_human: "This is a product/scope decision, not a mechanical defect — see the ESC-01 finding below."
---

# Phase 17: Semantic escalation Verification Report

**Phase Goal:** Quando as fontes discordam, uma investigação lê código, história e
memória e **propõe** uma reconciliação; aplicar é ato humano, e a investigação é
incapaz de gravar estado por construção, não por instrução.

**Verified:** 2026-07-31T23:16:29Z
**Status:** human_needed (2 items below — neither is a broken mechanism; both are
disclosed scope/proxy limitations that deserve a human decision, not a code fix)
**Re-verification:** No — initial verification

## Independently re-run test evidence

I did not take SUMMARY.md's pass counts on faith. I re-ran the phase's own test
suites myself, in this session, against the working tree as committed:

| Suite | Command | Result |
| ----- | ------- | ------ |
| `tests/cairn-reconcile-agent.bats` | `bats tests/cairn-reconcile-agent.bats` | **7/7 pass** |
| `tests/cairn-reconcile.bats` | `bats tests/cairn-reconcile.bats` | **12/12 pass** (67.96s, real bd fixtures) |
| `tests/cairn-doctor.bats` (targeted) | `bats tests/cairn-doctor.bats -f "apply-reconciliation"` | **7/7 pass** (96.48s, real bd fixtures) |

The full, untargeted `tests/cairn-doctor.bats` (58 scenarios, 51 pre-existing + 7
new) was **not** re-run in full by me — the file's own header and this phase's
execution notes both document it taking well over 10 minutes; the orchestrator's
own full run (58/58) plus my own targeted re-run of the 7 new
`apply-reconciliation` scenarios (all passing, independently) is the evidence
base for that suite.

I also independently confirmed, outside any test file: `grep -v '^#'
cairn/scripts/cairn-reconcile.py | grep -Ec '"(create|update|close|reopen)"'`
returns `0`; `python3 -c "import py_compile; ..."` compiles both
`cairn-reconcile.py` and `cairn-doctor.py` cleanly; and a synthetic `Write(.cairn
/conflicts.json)`-scoped tools line still trips `grep -cw -- "Write"` (returns
`1`), proving the agent-frontmatter bats check is not fooled by a
scoped-looking write grant.

## Goal Achievement

### Observable Truths (ROADMAP.md's 4 numbered success criteria — the contract)

| # | Truth (ROADMAP.md, verbatim intent) | Status | Evidence |
| - | ------------------------------------ | ------ | -------- |
| 1 | Um `grep` sobre o caminho de análise não encontra nenhum verbo de escrita do bd, e um teste roda esse caminho contra um fixture e afirma que nada mutou | ✓ VERIFIED | `grep -v '^#' cairn/scripts/cairn-reconcile.py \| grep -Ec '"(create\|update\|close\|reopen)"'` → 0 (re-run, confirmed). `tests/cairn-reconcile.bats#collect: THE LOAD-BEARING TEST` snapshots `bd list --all --json` AND a `sha256sum` manifest of the tracked tree (excluding `.git/`/`.cairn/`) before/after a real `collect` run against a genuinely conflicted fixture — byte-identical both ways. Independently re-run: pass. |
| 2 | A investigação roda apenas sobre conflito detectado — um teste afirma zero invocações numa passada em repositório onde tudo concorda | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | The mechanical, load-bearing half — `cairn-reconcile.py collect` refusing (exit 3, zero bundle written) against a real all-agree fixture — IS bats-proven and independently re-confirmed. What is NOT proven by any runnable test: that `/cairn:reconcile`'s own Task-tool subagent spawn is ever actually skipped at runtime. `tests/cairn-reconcile-agent.bats` only proves the *command's own prose* mentions `corroboration` before the subagent-spawn anchor (static line-ordering) — a proxy, explicitly named as such in both 17-02-PLAN.md's `<objective>` and 17-02-SUMMARY.md's coverage notes, never claimed as equivalent proof. See `behavior_unverified_items` above. |
| 3 | A proposta nomeia, para cada alegação, o arquivo e a linha em que ela se apoia, e uma checagem confirma que o texto citado está mesmo lá | ✓ VERIFIED | `cairn-reconcile.py verify` re-opens `citation["file"]` at `citation["line"]` and compares the literal text exactly (`_check_one_citation`, lines 567-595). `tests/cairn-reconcile.bats#verify: THE CITATION TRAP` builds a proposal with one correct citation and one citing a real file/line whose actual text differs — asserts the WHOLE proposal is rejected (`valid: false`, exit 4, exactly 1 failure reported, `refute_in_output "1 of 2"`), not partial credit. Independently re-run: pass. The "vacuous acceptance" hole (a proposal with zero claims/citations computing zero failures and reporting valid) is closed in code (`cmd_verify`, lines 627-637) and covered by its own test (`verify: a proposal with no claims (or zero citations) is rejected, never vacuously valid`). |
| 4 | Aplicar é comando separado, invocado por humano, que enumera cada mudança antes de fazer qualquer uma | ✓ VERIFIED | `cairn-doctor.py --apply-reconciliation N` is a distinct flag (`run_apply_reconciliation`), never auto-triggered. `tests/cairn-doctor.bats#apply-reconciliation: every claim is enumerated in output BEFORE the first bd write happens` asserts, via `grep -n` line numbers on REAL command output against a REAL bd fixture, that both enumerated claim lines precede the first `bd close` confirmation line. Independently re-run: pass, alongside the positive-apply, stale-hash, bad-citation, issue-provenance, and unrecognized-vocabulary refusal tests (6 more scenarios, all independently re-run and passing). |

**Score:** 3/4 truths fully behaviorally verified, 1 present-but-behavior-unverified (not failed — see above).

### The four fail-closed paths in `--apply-reconciliation` (explicit attack point)

| Path | Refuses on | Code | Test (independently re-run) |
| ---- | ---------- | ---- | ---------------------------- |
| Staleness | `evidence_hash` no longer matches a REAL re-`collect` at apply-time | `cairn-doctor.py:1589-1591` | `apply-reconciliation: a stale evidence_hash is refused, bd state unchanged` — pass |
| Citation | Any citation fails a REAL `cairn-reconcile.py verify N` at apply-time | `cairn-doctor.py:1595-1602` | `apply-reconciliation: a proposal with one wrong citation is refused wholesale, bd state unchanged` — pass |
| Closed action vocabulary | `recommended_action.type` outside `{bd_close, bd_reopen, manual_review}` | `cairn-doctor.py:1611-1618` (checked in the SAME pre-flight pass, before any enumeration prints) | `apply-reconciliation: an unrecognized recommended_action.type refuses the WHOLE apply, bd state unchanged` — pass |
| Issue provenance | `recommended_action.issue` carries no `phase-N` label (reuses `phase_nums()`) | `cairn-doctor.py:1619-1626` | `apply-reconciliation: correct citations do not excuse a claim naming an id outside phase N, bd state unchanged` — pass |

All four are checked in code, fail-closed (refuse the WHOLE apply, never a
per-claim partial), and each is independently confirmed by a real bats
scenario against a real `bd` fixture — not merely asserted in prose. Note on
scope: the issue-provenance check verifies the target id carries *any*
`phase-N` label (reusing `check_phase_complete_open`'s own filter), not
narrowly "did this id appear in this specific conflict's own corroboration
evidence" — a slightly broader but still fail-closed and effective check,
matching what 17-03-PLAN.md's own Step 4 specifies verbatim.

### ESC-02: incapable by construction, not by instruction

`cairn/agents/reconcile-investigator.md`'s frontmatter:
```
tools: Read, Grep, Glob
```
Confirmed: this line contains **none** of `Write`, `Edit`, `Bash`,
`NotebookEdit` — the full write-capable set, not just the two
(`Bash`/`Edit`) the plan-check's original blocker named. `tests/cairn-reconcile-agent.bats`
greps the extracted `tools:` line specifically (never the whole file, since
the body discusses "Write" at length to explain its own absence) for the
full `WRITE_CAPABLE` set with `grep -cw`, a word-boundary match — I
independently confirmed this closes the exact loophole the brief named: a
synthetic `tools: Read, Grep, Glob, Write(.cairn/conflicts.json)` line still
trips `grep -cw -- "Write"` (returns `1`, i.e. found), because `(` is a word
boundary. The check would fail the build against a scoped-looking `Write(...)`
variant, not just a bare `Write`.

`cairn-reconcile.py` (the collector) carries zero `bd` subprocess calls of
any kind — confirmed by `grep -n '\bbd\b'` returning only comments/docstring
prose and a JSON schema field name, never a live invocation — and zero
`create`/`update`/`close`/`reopen` string literals outside comments.

### D-03 citation verification: one bad citation invalidates the whole proposal

Confirmed at three layers, all independently re-run:
1. `cairn-reconcile.py verify` (17-01) — the citation-trap test, described above.
2. `cairn-doctor.py --apply-reconciliation` (17-03) re-runs `verify` for real
   at apply-time (never trusting the proposal's own generation-time check) —
   `apply-reconciliation: a proposal with one wrong citation is refused
   wholesale, bd state unchanged`.
3. The empty/vacuous-proposal hole is closed: a proposal with no claims, an
   empty `claims` list, or claims carrying zero citations is `valid: false`
   (exit 4), never vacuously accepted — this is explicitly the fix the
   executor found necessary against the plan's own Task 2 smoke test
   (17-01-SUMMARY.md's "Auto-fixed Issues #2").

### ESC-03 gating and enumerate-before-mutate

`--apply-reconciliation` always exits on its own (never falls through to the
ordinary 15-check report) with a distinct exit-code contract (2 usage / 0
not-conflicted-moot / 7 failed). The enumeration-precedes-mutation test
proves ordering with real `grep -n` line numbers against actual command
output from a real run — not presence alone. Independently re-run: pass,
alongside the positive-apply test that confirms the `bd_close` claim's issue
is genuinely closed afterward and the `manual_review` claim's target is
untouched.

### ESC-04 gating and the honesty of its claim

`collect` refusing on an all-agree repo is genuinely bats-proven with a real
fixture (independently re-run, pass). "Zero invocations of the subagent" is,
as the brief anticipated, only proxy-tested by prose line-ordering, because
bats cannot invoke the Task tool. Both 17-02-PLAN.md's `<objective>` and
17-02-SUMMARY.md's coverage notes say this plainly and repeatedly — e.g.
17-02-PLAN.md: *"Do not read Task 3's ordering test as equivalent proof to
Plan 17-01's mutation/gating tests; it is a weaker, necessary-but-not-
sufficient check on the command's own wiring."* This verification agrees
with that self-assessment and, per the honest-verifier discipline, routes it
to human_verification (⚠️ PRESENT_BEHAVIOR_UNVERIFIED, not VERIFIED, not
FAILED) rather than letting a green proxy read as the literal criterion.

I also independently confirmed the other half of ESC-04's claim — "nunca
numa passada rotineira de status ou doctor" — is genuinely true in code: `grep
-n "cairn-reconcile" cairn/scripts/cairn-doctor.py cairn/scripts/cairn-status.py`
shows `cairn-reconcile.py` is invoked from exactly one place,
`run_apply_reconciliation()`, itself gated behind the explicit
`--apply-reconciliation N` flag — never from the ordinary 15-check pass, and
never from `cairn-status.py` at all.

### House style

`.py`/`.sh` pair (`cairn-reconcile.py` + `.sh`, thin `exec python3 ... "$@"`
wrapper, header restates the exit-code contract) — present. `EXIT_*`
constants defined and documented in both the module docstring and inline —
present (`EXIT_OK=0`, `EXIT_USAGE=2`, `EXIT_NOT_CONFLICTED=3`,
`EXIT_INVALID_PROPOSAL=4`). Stdlib only (`argparse`, `hashlib`, `json`, `os`,
`re`, `subprocess`, `sys`, `tempfile`, `datetime`, `pathlib`) — confirmed, no
third-party imports. No type hints, no dataclasses — confirmed via grep for
`->`/`: <type>` annotations and `class`/`dataclass` keywords (none found
outside a docstring arrow used as prose, not an annotation).
`tests/cairn-reconcile.bats` and `tests/cairn-reconcile-agent.bats` exist and
follow the house header-comment convention. `cairn/commands/doctor.md` and
`cairn/docs/commands/doctor.md` (the second, more thorough reference doc)
were both updated — confirmed present, per CONVENTIONS.md's
Documentation-as-Contract rule.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `cairn/scripts/cairn-reconcile.py` | `collect`/`verify` subcommands, write-free | ✓ VERIFIED | 710 lines, compiles clean, zero bd write verbs |
| `cairn/scripts/cairn-reconcile.sh` | thin wrapper | ✓ VERIFIED | 11 lines, `exec python3 ... "$@"` |
| `cairn/agents/reconcile-investigator.md` | `tools: Read, Grep, Glob` only | ✓ VERIFIED | zero write-capable tools, confirmed by grep and by bats |
| `cairn/commands/reconcile.md` | gate → cache → collect → spawn → write → verify → present | ✓ VERIFIED | step order confirmed by grep -n line-number check (both manual and bats) |
| `cairn/scripts/cairn-doctor.py` (`--apply-reconciliation`) | 6 fail-closed paths, enumerate-before-apply | ✓ VERIFIED | wired in `main()` before the checks list, always exits on its own |
| `tests/cairn-reconcile.bats` | 12 scenarios | ✓ VERIFIED | 12/12, independently re-run |
| `tests/cairn-reconcile-agent.bats` | 7 scenarios | ✓ VERIFIED | 7/7, independently re-run |
| `tests/cairn-doctor.bats` (new scenarios) | 7 scenarios | ✓ VERIFIED | 7/7, independently re-run (targeted filter) |
| `.gitignore` | `.cairn/reconcile-evidence.json` added alongside existing `.cairn/conflicts.json` | ✓ VERIFIED | both entries present |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `collect` | `cairn-status.py --json` | subprocess, `phases[]` row for N | ✓ WIRED | `cmd_collect`, lines 465-493 |
| `collect` | `cairn-journal.py last-moved`/`history` | subprocess-and-degrade | ✓ WIRED | `journal_last_moved`/`journal_history`, lines 332-365 |
| `collect` | `git log`/`git rev-parse` | subprocess, capped at 50, pathspec-narrowed | ✓ WIRED | `git_log_evidence`/`git_is_shallow`, lines 293-323 |
| `verify` | citation's own file+line | direct file read, exact compare | ✓ WIRED | `_check_one_citation`, lines 567-595 |
| `/cairn:reconcile` | `cairn-reconcile.sh collect`/`verify` | shell commands in numbered steps | ✓ WIRED | `reconcile.md` steps 2, 3, 5 |
| `/cairn:reconcile` | `reconcile-investigator` subagent | Task tool spawn (prose) | ⚠️ UNVERIFIABLE AT RUNTIME BY THIS SUITE | step 3, correctly ordered in prose; never exercised by a test (see behavior_unverified_items) |
| `/cairn:reconcile` | `.cairn/conflicts.json` | deterministic write of the command's own step 4 | ✓ WIRED (design) | not independently exercised live, but the write shape is fixed and consumed correctly by `verify`/`--apply-reconciliation`, both of which ARE exercised live against hand-written proposal fixtures matching this exact schema |
| `--apply-reconciliation` | `.cairn/conflicts.json` | read | ✓ WIRED | `run_apply_reconciliation`, lines 1552-1561 |
| `--apply-reconciliation` | `cairn-reconcile.py collect`/`verify` | subprocess, freshness + citation re-check | ✓ WIRED | lines 1567-1602 |
| `--apply-reconciliation` | `bd close`/`bd update` | subprocess, closed vocabulary only | ✓ WIRED | lines 1660-1682 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ------------ | ------ | -------- |
| ESC-01 | 17-01, 17-02 | Investigation reads código, história e memória, proposes a reconciliation | ◐ PARTIAL | Código (repo files via Read/Grep/Glob + capped `git_log`) and história (`cairn-journal.py` last-moved/history) are both wired into the evidence bundle and the subagent's further investigation. **Memória is not wired**: the subagent's `tools:` grant is `Read, Grep, Glob` only, deliberately omitting a context-mode/`ctx_search` tool. 17-02's own decision log justifies this as "no established convention exists anywhere in this codebase for naming an MCP tool inside an agent's tools: frontmatter" — **this verification found that claim does not fully hold**: this same environment's globally-installed vendored GSD agents (`~/.claude/agents/gsd-project-researcher.md` and others) declare `tools: ..., mcp__context7__*`, a real, working precedent for naming an MCP tool (via server-wildcard) inside an agent's `tools:` line, and this project's own `cairn/commands/recall.md`/`remember.md` already establish context-mode's `ctx_*` tools as "present by default" for this project. Not a broken mechanism — a scope decision that should be made explicitly, not left standing on a claim that doesn't hold up. See human_verification. |
| ESC-02 | 17-01, 17-02 | Structurally incapable of writing state — capability absence, not instruction | ✓ SATISFIED | `cairn-reconcile.py` carries zero bd write verbs (grep-confirmed, twice) and a real run mutates neither bd state nor the working tree (bats-confirmed, independently re-run). `reconcile-investigator.md`'s `tools:` grant contains zero write-capable tools (bats-confirmed against the full set, independently re-run, and confirmed non-vacuous against a synthetic scoped-Write variant). |
| ESC-03 | 17-03 | Apply is a separate, human-invoked command that enumerates before mutating | ✓ SATISFIED | `--apply-reconciliation N` is distinct from `/cairn:reconcile`, always exits on its own, enumerates every claim (grep -n-proven to precede the first bd write) before applying anything, executes only `bd_close`/`bd_reopen`. All independently re-run and passing. |
| ESC-04 | 17-01, 17-02 | Runs only on detected conflict, never in a routine status/doctor pass, cached by evidence hash | ✓ SATISFIED (mechanical gate + cache-hash stability) / ⚠️ the runtime "zero subagent invocations" claim is proxy-only | `collect`'s gate (exit 3, nothing written on non-conflict) is bats-proven with a real fixture. `evidence_hash` stability across two consecutive unchanged runs is bats-proven. `cairn-reconcile.py` is invoked from exactly one place in `cairn-doctor.py` (`--apply-reconciliation`'s own handler, itself human-invoked) and never from the routine 15-check pass or from `cairn-status.py` — confirmed by direct grep. The live "the subagent itself is never spawned on non-conflict, and a cache hit skips re-spawning" claim is not exercised by any test (bats cannot invoke the Task tool) — see behavior_unverified_items. |

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers, no
"not yet implemented" language, no empty-return stubs, no hardcoded-empty
data flowing to output, in any of the phase's new/modified files.

### Behavioral Spot-Checks / Probe Execution

Not applicable in the probe-script sense (no `scripts/*/tests/probe-*.sh`
convention exists in this codebase). This phase's "spot-checks" ARE its bats
suites, all independently re-run above.

## Human Verification Required

### 1. Live smoke test: subagent invocation count on a non-conflict and on a cache hit

**Test:** Run `/cairn:reconcile N` once against a phase whose corroboration
reads `ok`, and once twice-in-a-row against an unchanged conflicted phase.
**Expected:** Zero Task-tool spawns on the first run; zero *new* spawn on
the second run of the second pair (the cached proposal is presented
instead).
**Why human:** bats cannot invoke the Task tool. The mechanical, load-bearing
half of this guarantee (`collect` refusing to gather/write anything on a
non-conflict verdict) IS proven with a real fixture; only the subagent-spawn
count itself is unproven by any runnable test. This is an architectural
ceiling of this test suite, not an implementation defect, and both the plan
and summary say so plainly.

### 2. Scope decision: ESC-01's "memória" source

**Test:** Decide whether `cairn/agents/reconcile-investigator.md` should be
granted a context-mode tool (e.g. `mcp__plugin_context-mode_context-mode__ctx_search`)
so the investigator can read prior session memory, or whether the current
código+história-only scope is accepted as this phase's final shape.
**Expected:** An explicit decision — either accept as-is (and correct
17-02's decision log, which currently claims no naming precedent exists,
when one does), or file a follow-up plan.
**Why human:** Product/scope call, not a mechanical defect — every other
guarantee in this phase (ESC-02, ESC-03, ESC-04's mechanical half) is fully
implemented and independently verified regardless of this decision.

## Gaps Summary

No blocking gaps. Every one of the phase's own `must_haves` (all three
plans' `truths`/`artifacts`/`key_links`) and all four of ROADMAP.md's
numbered success criteria have real, independently-re-run test evidence
behind them — nothing here rests on SUMMARY.md's word alone. The two items
above are WARNINGs, not BLOCKERs: neither points at a broken or missing
mechanism. One (subagent invocation count) is an inherent ceiling of this
test suite's tooling, honestly disclosed in the plan and summary text
itself, exactly as this verification's brief anticipated it would be. The
other (ESC-01's "memória" source) is a real, narrow scope gap against the
requirement's literal text, whose stated justification does not fully hold
under scrutiny — worth a deliberate human decision before treating ESC-01 as
fully closed, but not a defect in what was actually built and tested for
ESC-02/ESC-03/ESC-04.

---

*Verified: 2026-07-31T23:16:29Z*
*Verifier: Claude (gsd-verifier)*

---

## Resolução dos itens de decisão humana (2026-07-31)

**1. A memória do ESC-01 — RESOLVIDO.** O verificador estava certo e a premissa do
executor era falsa: oito agentes GSD instalados globalmente declaram ferramentas
MCP em `tools:`, e o `cairn/commands/recall.md` deste repo trata os `ctx_*` como
dependência de primeira classe. A convenção existe.

Decidido pelo Felipe: conceder **apenas** `ctx_search`, escrito por extenso —
`tools: Read, Grep, Glob, mcp__plugin_context-mode_context-mode__ctx_search`.

O conserto óbvio teria sido copiar o padrão glob que os outros agentes usam
(`mcp__<server>__*`). Isso entregaria o servidor inteiro do context-mode a este
agente, **incluindo `ctx_purge`**, que destrói a base de conhecimento — uma escrita
destrutiva dentro do único agente cujo propósito inteiro é não ter escrita nenhuma.
O `cairn-context` do próprio repo já proíbe essa chamada nesta camada.

`ctx_purge` foi acrescentado ao conjunto write-capable do teste, e o teste de
allowlist (`ALLOWED_TOOLS`) foi provado rejeitando o glob: instalado
`mcp__plugin_context-mode_context-mode__*`, o teste 3 falhou; restaurado, 7/7, com
o arquivo byte-idêntico.

**2. "Zero invocações" do subagente — permanece proxy, por limite real.** O gate
determinístico do `collect` (recusa com exit 3, nada escrito) é provado por bats
contra fixture real. Se o spawn da Task tool é de fato pulado em runtime não é
demonstrável por esta suíte, porque bats não invoca a Task tool. Plano, summary e
este laudo dizem isso explicitamente — o proxy não é apresentado como o critério.

Com o item 1 resolvido, os 4 critérios de sucesso e ESC-01..04 têm código e teste
por trás. O item 2 fica registrado como limite conhecido, não como lacuna aberta.
