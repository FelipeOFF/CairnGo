#!/usr/bin/env bats
# cairn-doctor.bats — exercises the consistency doctor's CLI contract
# (cairn-doctor.py / the cairn-doctor.sh wrapper):
#   0 all ok or warnings only (warnings never change the exit code) or not
#   applicable, 2 usage / refused --fix-labels, 5 bd unavailable, 7 any
#   check failed.
#
# Each test starts from the HEALTHY wired fixture (all seventeen checks ✓)
# and breaks exactly one check, asserting on that check's reported status.
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail
# a bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# Insert `beads: [IDS]` into a PLAN.md's frontmatter (right after the
# opening ---).
add_plan_beads() {
  python3 - "$1" "$2" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
lines = p.read_text().splitlines(keepends=True)
lines.insert(1, f"beads: [{sys.argv[2]}]\n")
p.write_text("".join(lines))
PY
}

# Insert `milestone: v1.0` into the fixture STATE.md frontmatter.
stamp_state_milestone() {
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/STATE.md")
lines = p.read_text().splitlines(keepends=True)
lines.insert(1, "milestone: 'v1.0'\n")   # right after the opening ---
p.write_text("".join(lines))
PY
}

# Healthy wired fixture on top of make_gsd_fixture (phase 1 complete,
# phase 2 active): one issue per ROADMAP requirement with the pair labels
# and gsd metadata stamp, plan frontmatter pointing at them, maps fresh.
make_doctor_fixture() {
  bd init -q --prefix doc --non-interactive >/dev/null 2>&1
  DOC_A1="$(bd create "AUTH-01: Signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  DOC_A2="$(bd create "AUTH-02: Login flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v1.0"}}' --silent)"
  DOC_P2="$(bd create "API-01: Rate limiting" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-01","phase":2,"milestone":"v1.0"}}' --silent)"
  bd close "$DOC_A1" >/dev/null
  bd close "$DOC_A2" >/dev/null
  add_plan_beads .planning/phases/01-auth/01-01-PLAN.md "$DOC_A1, $DOC_A2"
  add_plan_beads .planning/phases/02-api/02-01-PLAN.md "$DOC_P2"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  # A HEALTHY repo has a way back, so the healthy fixture has one. Added with
  # check 22 (issues-recoverable, 2026-08-07): without this the reference
  # fixture would carry a permanent warning, and the file's own baseline
  # assertion — "nothing warns" — would have had to be weakened to accept the
  # very defect the check was written to surface.
  bd export --all -o .beads/issues.jsonl >/dev/null 2>&1
  git add -f .beads/issues.jsonl >/dev/null 2>&1
  git -c user.email=t@t -c user.name=t commit -q -m "beads: export" \
    -- .beads/issues.jsonl >/dev/null 2>&1 || true
  wire_capability_ok
}

# Check 10 reads GLOBAL state — which GSD plugins are installed on the machine
# — so without a seam every doctor test would inherit the developer's plugin
# list and pass or fail by accident. Measured 2026-08-12: this development
# machine has `gsd-core@cairngo` installed, which after the phase-37 inversion
# turns check 10 into a FAIL in every fixture. CAIRN_INSTALLED_PLUGINS pins it.
#
# The phase-37 inversion also emptied this helper's other half. It used to
# stage .gsd/capabilities/cairn so the check would find the capability
# REGISTERED; that same directory is now leftover state the check WARNS about,
# so staging it would make the healthy fixture carry a permanent warning. The
# capability was archived — there is no host for it — and the healthy fixture
# is a machine that never had one.
#
# $1 is kept for call-site compatibility and is ignored: "legacy" used to mean
# "a GSD 4.x binary answers here", and no lineage of external GSD is a healthy
# state any more. Tests that need an installed lineage assert it in
# tests/cairn-doctor-lineage.bats, which owns check 10 outright.
wire_capability_ok() {
  local plugins="$PWD/.installed-plugins.json"
  printf '{"plugins":{}}\n' > "$plugins"
  export CAIRN_INSTALLED_PLUGINS="$plugins"
}

@test "healthy wired fixture: exit 0, nothing warns or fails, and it still reads ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  # `ok`, not INCOMPLETE. This fixture IS a user's repo — it carries none of
  # cairn's own manifests — so 23-02 gave it ⊘ checks. Every one of them is
  # out-of-scope, and the footer must still read ok: this assertion is the
  # mechanical proof that the phase did not trade a permanent false green for
  # a permanent false red in every repo that uses cairn.
  grep -qF "[cairn-doctor] ok" <<<"$output"
  refute_in_output "⚠"
  refute_in_output "✗"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.applicable' 'true'
  assert_json_eq "$output" '.ok' 'true'
  # The count is hardcoded ON PURPOSE: it is the canary for a check that was
  # written and never registered in main()'s `checks` list. 16 -> 17 here
  # came with check 16, test-parallel (29-06); 17 -> 18 with check 17,
  # req-ledger (29-07); 18 -> 19 with check 18, response-language (phase 24).
  #
  # That last bump is the one this assertion was really built for, and it
  # took the shape nothing else here can catch. Phases 23 and 24 ran in
  # parallel worktrees and each added a check WITHOUT knowing about the
  # other's. Neither branch's test was wrong on its own branch: 23 asserted
  # 18 and passed, 24 asserted 19 and passed. git merged both files with NO
  # conflict — the silent auto-merge that damaged phases 14/15 of this
  # project — and the merged tree registered 19 checks while this literal
  # still read 18. Two red tests, one defect, and the ONLY thing that named
  # it was this canary.
  #
  # It is also the assertion that caught the reporting failure it was built
  # for. It stayed red through a `bats tests/cairn-doctor.bats` whose log was
  # read through `tail -15`, so the failure line scrolled out and the run was
  # called green. The full-suite run through cairn-test.sh is what surfaced
  # it. A number read off the end of a truncated log is not a measurement.
  #
  # 19 -> 20 with check 19, phase-landed (phase 30, PR-04). Edited HERE and at
  # the second site further down in this same file, in one change, having read
  # this note first — which is the whole point of the note. Phase 30 also found
  # cairn-doctor.py's own docstring still saying "eighteen checks in total"
  # while nineteen were registered: prose kept by hand goes stale, this literal
  # does not, and that asymmetry is why the literal is the contract.
  #
  # 20 -> 21 with check 20, plan-counters (phase 25, criterion 6). Both sites
  # here, the numbered list in cairn-doctor.py's docstring and the table in
  # cairn/docs/commands/doctor.md were edited in the same change.
  #
  # 21 -> 22 with check 21, state-dialect (phase 25, criterion 5) — and this
  # bump is the one the note was written for, all over again: phase 25 ran in
  # TWO parallel worktrees, exactly the shape that made this literal wrong
  # once. The four sites were edited in one change, from the branch that owns
  # cairn-doctor.py; the other branch never touches it, so there is one
  # writer and no merge to be silent about.
  assert_json_eq "$output" '.checks | length' '24'
  # The exact ordered set, not "unique == ok": after 23-02 this fixture has
  # two ⊘ checks (cairn's own manifests are absent by construction), and an
  # assertion that merely tolerated extra values would stop proving anything.
  assert_json_eq "$output" \
    '[.checks[].status] | unique | sort | join(",")' 'not-applicable,ok'
  # `.failed` is the exact mirror of the exit code, and it is NOT `.ok`'s
  # complement: `.ok` also answers "did every check in scope actually run".
  assert_json_eq "$output" '.failed' 'false'
  # And the load-bearing half: not one of those ⊘ is a gap.
  assert_json_eq "$output" \
    '[.checks[] | select(.status=="not-applicable" and .scope=="no-input")] | length' \
    '0'
}

# Break: derive any counter as `len(checks) - the others`, the shape
# cairn-doctor.py carried before this phase. A fifth status would then land
# in the success bucket in silence — a brand-new false green inside the
# phase that exists to remove them.
@test "report footer: four counters, summing to the check count, none by subtraction" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # One bucket per word of the vocabulary: a status with no symbol has
  # nowhere to be counted, which is the whole point of deriving the buckets
  # from SYMBOL's own keys.
  assert_json_eq "$output" '.counts | length' '4'
  assert_json_eq "$output" \
    '[.counts | to_entries[] | .value] | add' \
    "$(jq -r '.checks | length' <<<"$output")"
  # Recomputed from the check list itself, so the footer's arithmetic is not
  # taken on trust — it has to agree with a number we derived separately.
  assert_json_eq "$output" '.counts.ok' \
    "$(jq -r '[.checks[] | select(.status == "ok")] | length' <<<"$output")"
  assert_json_eq "$output" '.counts["not-applicable"]' \
    "$(jq -r '[.checks[] | select(.status == "not-applicable")] | length' \
        <<<"$output")"
  assert_json_eq "$output" '.counts.warn' \
    "$(jq -r '[.checks[] | select(.status == "warn")] | length' <<<"$output")"
  assert_json_eq "$output" '.counts.fail' \
    "$(jq -r '[.checks[] | select(.status == "fail")] | length' <<<"$output")"
  # Closed vocabulary: subtracting the four leaves nothing behind.
  assert_json_eq "$output" \
    '[.checks[].status] - ["ok","not-applicable","warn","fail"] | length' '0'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qE '^\[cairn-doctor\] ok — [0-9]+ ok, [0-9]+ not-applicable, [0-9]+ warning\(s\), [0-9]+ failure\(s\)$' \
    <<<"$output"
}

# Break: reuse ✓ for the new state, or pick a character that renders two
# columns wide under a CJK locale. The proof is unicodedata, never how the
# glyph looks in this terminal — the same rule phase 21 measured for the
# board's step symbols.
@test "status vocabulary: four symbols, the new one distinct and single-width" {
  make_tmp_repo
  cat > symbol_check.py <<'PY'
import ast
import re
import sys
import unicodedata

src = open(sys.argv[1]).read()
sym = ast.literal_eval(re.search(r"SYMBOL = (\{.*?\})", src, re.S).group(1))
assert set(sym) == {"ok", "not-applicable", "warn", "fail"}, sorted(sym)
na = sym["not-applicable"]
assert na != sym["ok"], f"the new state must not wear the success marker: {na}"
for name, ch in sorted(sym.items()):
    width = unicodedata.east_asian_width(ch)
    assert width == "N", (name, ch, width)
print(f"{na} U+{ord(na):04X} {unicodedata.name(na)}")
PY
  run python3 symbol_check.py "$CAIRN_SCRIPTS_DIR/cairn-doctor.py"
  [ "$status" -eq 0 ]
  grep -qF "U+2298" <<<"$output"
}

# ---------------------------------------------------------------------------
# Os quatro testes de gsd-capability que viviam aqui foram REMOVIDOS pela fase
# 37, e o que eles asseriam foi para tests/cairn-doctor-lineage.bats.
#
# Eles não regrediram: eles descreviam a pergunta antiga, e ela deixou de
# existir. Um por um, e por que cada um não tem tradução:
#
#   "the 4.x lineage fails the doctor, exit 7" — ainda falha, mas exigia
#     literalmente `claude plugin install gsd-core@cairngo` na saída. Essa
#     prescrição inverteu para `uninstall`; o teste B1 do arquivo novo é o
#     controle que prova que a frase antiga não sai mais.
#   "gsd-core without a registered capability fails" — registro de capability
#     deixou de ser o que o check mede. A capability foi arquivada (D-04): não
#     há host externo para as contributions.
#   "a staged bundle missing its gate script fails" — mesma razão; o bundle
#     staged em .gsd/ hoje é resíduo, e resíduo é WARN com fix de limpeza (A4).
#   "no GSD binary at all warns" — a ausência de binário GSD passou de sinal
#     ambíguo a ESTADO ESPERADO, e o A1 do arquivo novo asserta exatamente
#     isso, agora como `ok`.
#
# Removê-los em silêncio seria apagar a memória da inversão; por isso a nota.
# ---------------------------------------------------------------------------

@test "req-issue: requirement without a gsd.req issue fails, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Wipe gsd.req off AUTH-01's issue (--metadata replaces the gsd key
  # wholesale) and regenerate the map so ONLY check 1 breaks.
  bd update "$DOC_A1" --metadata '{"gsd":{"phase":1,"milestone":"v1.0"}}' >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.checks[] | select(.id=="req-issue") | .status' 'fail'
  assert_json_eq "$output" '.checks[] | select(.id=="req-issue") | .items | length' '1'
  grep -qF "AUTH-01" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ req-issue" <<<"$output"
  grep -qF "[cairn-doctor] FAIL" <<<"$output"
}

@test "frontmatter-ids: dangling id in PLAN beads fails, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/phases/02-api/02-01-PLAN.md")
p.write_text(p.read_text().replace("beads: [", "beads: [doc-zzz, ", 1))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="frontmatter-ids") | .status' 'fail'
  assert_json_eq "$output" '.checks[] | select(.id=="frontmatter-ids") | .items | length' '1'
  grep -qF "doc-zzz not found in bd" <<<"$output"
}

@test "frontmatter-ids: bead without the plan's phase label fails" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # DOC_P2 is referenced by the phase-2 plan — moving its label to phase-1
  # makes the frontmatter reference wrong (regen maps to keep check 3 ok).
  bd label remove "$DOC_P2" phase-2 >/dev/null
  bd label add "$DOC_P2" phase-1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="frontmatter-ids") | .status' 'fail'
  grep -qF "lacks label phase-2" <<<"$output"
}

@test "maps-fresh: close without regenerating the map warns, exit 0" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # A new open issue (not a close) keeps disk/bd corroboration agreeing —
  # phase 2 stays "not done" on both sides — while still making the map
  # stale, which is all this test needs.
  bd create "API-02: Second endpoint" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-02","phase":2,"milestone":"v1.0"}}' \
    --silent >/dev/null   # map 2 NOT regenerated

  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # warnings alone never change the exit code
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.checks[] | select(.id=="maps-fresh") | .status' 'warn'
  grep -qF "stale map 02-BEADS-MAP.md" <<<"$output"

  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⚠ maps-fresh" <<<"$output"

  # Regenerate -> clean again.
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  refute_in_output "⚠"
}

@test "superseded-released: superseded plan holding a live bead warns" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # A superseded plan still pointing at the OPEN phase-2 issue.
  cat > .planning/phases/02-api/02-02-PLAN.md <<EOF
---
phase: 02-api
plan: "02"
status: superseded
beads: [$DOC_P2]
---

Superseded draft plan.
EOF

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="superseded-released") | .status' 'warn'
  # Superseded plans are excluded from check 2 — its ids are not "dangling".
  assert_json_eq "$output" '.checks[] | select(.id=="frontmatter-ids") | .status' 'ok'
  grep -qF "still open" <<<"$output"
}

@test "phase-complete-open: open issue in a completed phase warns; --close-completed closes; re-run clean" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 checked off in ROADMAP.md
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null   # keep check 3 ok

  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # phase-complete-open itself only WARNs here, but phase-corroboration
  # (check 11) independently reads the same fact — phase 1 verified on
  # disk, one of its issues still open — as its R1 "blocks" rule (disk vs
  # bd), so the OVERALL run fails until the straggler is closed.
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '1'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
  grep -qF "$straggler" <<<"$output"
  # Phase 1's disk artifacts agree (PLAN has its SUMMARY) — no divergence note.
  refute_in_output "artifacts disagree"

  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  grep -qF "closed $straggler" <<<"$output"
  refute_in_output "⚠ phase-complete-open"

  # Actually closed in bd.
  run bd show "$straggler" --json
  assert_json_eq "$output" '.[0].status' 'closed'

  # Idempotent: a second run has nothing left to close.
  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  refute_in_output "closed $straggler"

  # Refresh the phase-1 map (the close changed a row) -> fully clean re-run.
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  refute_in_output "⚠"
  refute_in_output "✗"
}

@test "phase-complete-open: absent when completed phases hold nothing open" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture   # phase-1 issues closed, open issue only in phase 2

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '0'
}

@test "phase-complete-open: a cross-phase issue with one live phase is never flagged or closed" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 complete, phase 2 active
  make_doctor_fixture
  # phase-1 (complete) AND phase-2 (live): ALL, not any. cairn-status keeps
  # this issue out of stale_complete and offers it as the next action, and
  # its footer sends the user to --close-completed — which must not then
  # kill the very issue the board just recommended.
  local cross
  cross="$(bd create "API-02: Spans two phases" -t task -l phase-1,phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-02","phase":2,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '0'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  refute_in_output "closed $cross"
  run bd show "$cross" --json
  assert_json_eq "$output" '.[0].status' 'open'

  # cairn-status agrees: not stale, and still the pick.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-status.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.stale_complete | length' '0'

  # A single-label phase-1 straggler in the same board IS still swept, so
  # the ALL predicate narrows the target set without disabling the flag.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  grep -qF "closed $straggler" <<<"$output"
  refute_in_output "closed $cross"
  run bd show "$cross" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "phase-complete-open: --close-completed prints the divergence note BEFORE closing" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  rm .planning/phases/01-auth/01-01-SUMMARY.md   # disk now disagrees

  # The warning must reach the operator in the SAME run that closes: after
  # the close the issues leave check 5's scope and the note is unreachable.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  grep -qF "artifacts disagree" <<<"$output"
  grep -qF "confirm the phase is really done before closing" <<<"$output"
  grep -qF "closed $straggler" <<<"$output"
  # ...and it is ordered before the close line, not after it.
  local warn_line close_line
  warn_line="$(grep -nF "artifacts disagree" <<<"$output" | head -1 | cut -d: -f1)"
  close_line="$(grep -nF "closed $straggler" <<<"$output" | head -1 | cut -d: -f1)"
  [ "$warn_line" -lt "$close_line" ]

  # --json stays ONE machine line (the note never leaks onto stdout/stderr)
  # and still carries the divergence note inside the report.
  local straggler2
  straggler2="$(bd create "AUTH-05: Another follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-05","phase":1,"milestone":"v1.0"}}' --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json --close-completed
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.applicable' 'true'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-complete-open") | .items[] | select(test("artifacts disagree"))] | length' '1'
}

@test "phase-complete-open: notes when ROADMAP checkbox and disk artifacts diverge" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  rm .planning/phases/01-auth/01-01-SUMMARY.md   # disk now disagrees

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # VERIFICATION.md still exists, so disk still reads "verified" — an open
  # issue in a verified phase is also phase-corroboration's R1 "blocks"
  # conflict (check 11), which is why the run fails overall even though
  # phase-complete-open itself only warns.
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .items | length' '2'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
  grep -qF "$straggler" <<<"$output"
  grep -qF "artifacts disagree" <<<"$output"
}

@test "phase-complete-open: the divergence note names the real on-disk gap" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' \
    --silent >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  # Gap 1: the PLAN is there, its SUMMARY is not. VERIFICATION.md still
  # exists, so disk still reads "verified" to phase-corroboration — an
  # open issue (AUTH-04) in a verified phase is its R1 "blocks" conflict
  # (check 11), so the run fails overall even though phase-complete-open
  # itself only warns.
  rm .planning/phases/01-auth/01-01-SUMMARY.md
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  grep -qF "01-01-PLAN.md lacks its SUMMARY" <<<"$output"
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'

  # Gap 2: no phase directory at all — the note used to blame a missing
  # SUMMARY for a phase that has no PLAN to lack one. disk now reads
  # "none"; roadmap still marks phase 1 complete, which is R2's "blocks"
  # conflict (roadmap vs disk) — still failing, for a different reason.
  rm -rf .planning/phases/01-auth
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  grep -qF "no phase directory on disk" <<<"$output"
  refute_in_output "lacks its SUMMARY"
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
}

@test "phase-complete-open: --close-completed drains an epic<-epic<-epic chain in ONE run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Both phases complete, on the ROADMAP checkbox AND on disk, so the whole
  # chain below is in scope and no divergence note fires.
  # Marking phase 2 complete moves the derived views with it: API-01's own
  # checkbox and every STATE plan/phase counter. Left stale they are a REAL
  # ledger disagreement that check 17 names and fails on, which would take
  # this test to exit 7 for a reason that has nothing to do with the bulk
  # close it exercises.
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/ROADMAP.md")
p.write_text(p.read_text().replace("- [ ] **Phase 2: API**",
                                   "- [x] **Phase 2: API**"))
r = Path(".planning/REQUIREMENTS.md")
r.write_text(r.read_text().replace("- [ ] **API-01**", "- [x] **API-01**"))
s = Path(".planning/STATE.md")
s.write_text(s.read_text()
             .replace("  completed_phases: 1", "  completed_phases: 2")
             .replace("  completed_plans: 1", "  completed_plans: 2")
             .replace("  percent: 50", "  percent: 100"))
PY
  cp .planning/phases/01-auth/01-01-SUMMARY.md \
     .planning/phases/02-api/02-01-SUMMARY.md
  bd close "$DOC_P2" >/dev/null   # keep the sweep's scope to the chain

  # The shape that broke the bulk close in the field: epics chained by
  # blocks edges, each holding an open task child. bd refuses to close an
  # epic with an open child AND an issue with an open blocker, so NO single
  # ordered pass closes all six — only a fixpoint drains it.
  local e1 t1 e2 t2 e3 t3
  e1="$(bd create "Phase 1 epic" -t epic -l phase-1,m-v1.0 --silent)"
  t1="$(bd create "REQ-A: child of the phase 1 epic" -t task \
    -l phase-1,m-v1.0 --parent "$e1" --silent)"
  e2="$(bd create "Phase 2 epic" -t epic -l phase-2,m-v1.0 --silent)"
  t2="$(bd create "REQ-B: child of the phase 2 epic" -t task \
    -l phase-2,m-v1.0 --parent "$e2" --silent)"
  e3="$(bd create "Phase 2 follow-up epic" -t epic -l phase-2,m-v1.0 --silent)"
  t3="$(bd create "REQ-C: child of the follow-up epic" -t task \
    -l phase-2,m-v1.0 --parent "$e3" --silent)"
  bd dep add "$e2" "$e1" >/dev/null   # e2 blocked by e1
  bd dep add "$e3" "$e2" >/dev/null   # e3 blocked by e2
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  local id
  for id in "$e1" "$t1" "$e2" "$t2" "$e3" "$t3"; do
    if ! grep -qF "closed $id —" <<<"$output"; then
      echo "id $id was never closed. output:" >&2
      echo "$output" >&2
      return 1
    fi
  done
  grep -qF "closed 6 via --close-completed" <<<"$output"

  # bd agrees: one invocation left nothing open anywhere.
  run bd list --all --json
  assert_json_eq "$output" '[.[] | select(.status != "closed")] | length' '0'

  # Re-run is clean and idempotent.
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 0 ]
  refute_in_output "[cairn-doctor] closed"
  refute_in_output "✗"
  # phase-corroboration (check 11) still reports one "informs" item — this
  # fixture marks phase 2 complete on disk without also moving STATE.md's
  # active_phase off 2, a real (non-blocking) staleness the check exists to
  # surface — so a blanket refute of "⚠" would now fail for a legitimate
  # reason. Assert the specific check is clean AND pin the warning that is
  # expected, so an unexpected SECOND warning from any other check still
  # breaks this test — which is the property the blanket refute was
  # carrying, and the reason not to simply drop it.
  grep -qF "✓ phase-complete-open" <<<"$output"
  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" '[.checks[] | select(.status=="warn")] | length' '1'
  assert_json_eq "$output" '.checks[] | select(.status=="warn") | .id' 'phase-corroboration'
}

@test "phase-complete-open: a close bd refuses fails the check, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 complete, phase 2 still open
  make_doctor_fixture
  # An epic in the COMPLETE phase 1 whose only child lives in the still-open
  # phase 2. The child is not a target (its phase is live) and --force is
  # not on the table, so bd refuses the epic on every pass: the fixpoint
  # cannot drain it and the run must say so instead of exiting 0.
  local epic child
  epic="$(bd create "AUTH-06: Phase 1 epic" -t epic -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-06","phase":1,"milestone":"v1.0"}}' --silent)"
  child="$(bd create "API-02: live child in phase 2" -t task \
    -l phase-2,m-v1.0 --parent "$epic" \
    --metadata '{"gsd":{"req":"API-02","phase":2,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json --close-completed
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-complete-open") | .status' 'fail'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-complete-open") | .items[] | select(test("could not close"))] | length' '1'
  grep -qF "$epic" <<<"$output"
  grep -qF "open child" <<<"$output"   # bd's own refusal reason is relayed

  # Nothing was forced: the epic and its live child are both still open.
  run bd show "$epic" --json
  assert_json_eq "$output" '.[0].status' 'open'
  run bd show "$child" --json
  assert_json_eq "$output" '.[0].status' 'open'

  # Same verdict in the human report.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --close-completed
  [ "$status" -eq 7 ]
  grep -qF "✗ phase-complete-open" <<<"$output"
  grep -qF "[cairn-doctor] FAIL" <<<"$output"
}

@test "orphans: unknown phase label and phase-less issue warn; migrated-todo exempt" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local ghost loose todo
  ghost="$(bd create "Ghost of a phase" -t task -l phase-9,m-v1.0 --silent)"
  loose="$(bd create "Loose end" -t task --silent)"
  todo="$(bd create "Parked todo" -t task -l migrated-todo --silent)"

  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .items | length' '2'
  grep -qF "$ghost" <<<"$output"
  grep -qF "$loose" <<<"$output"
  refute_in_output "$todo"
}

# VOID-03's second half, and the proof is DIFFERENTIAL, not a bare "the count
# reached zero" — that would also pass if someone switched the whole axis off
# by accident. The SAME repo with the SAME issues is run twice and exactly one
# thing changes between the runs: whether the milestone's archived ROADMAP is
# on disk.
#
# Break: exempt without looking at .planning/milestones/ at all — above all
# the most tempting shortcut, "every closed issue is exempt", which passes the
# second run and fails the first.
@test "orphans: a closed issue is exempt only because its milestone is archived (differential)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local old
  old="$(bd create "Delivered last cycle" -t task -l phase-9,m-v0.9 --silent)"
  bd close "$old" >/dev/null

  # Run 1: no archive on disk. The issue is an orphan, exactly as before.
  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'warn'
  grep -qF "$old" <<<"$output"

  # The single variable: /gsd:complete-milestone's own archive artifact.
  mkdir -p .planning/milestones
  echo "# Roadmap: v0.9 (archived)" > .planning/milestones/v0.9-ROADMAP.md

  # Run 2: same repo, same issues, same labels.
  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .items | length' '0'
  refute_in_output "$old"
  # Break: exempt in SILENCE. A repo with sixty-one historical issues would
  # then be indistinguishable from a repo with none, and the phase would have
  # traded a permanent noise for a permanent silence.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .detail | test("1 .*archiv")' 'true'
}

# Break: write the predicate with "any archived milestone label" instead of
# "ALL of them". This is the contour that the naive version passes every other
# test on and fails only here — and it is the one milestone.md documents as
# EXPECTED behaviour: a carried-over issue shows as a transient orphan until
# the new roadmap places it, and that warning must survive.
@test "orphans: an issue carried into the active milestone is NOT exempt" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  mkdir -p .planning/milestones
  echo "# Roadmap: v0.9 (archived)" > .planning/milestones/v0.9-ROADMAP.md
  local carried
  carried="$(bd create "Carried over, not yet placed" -t task \
    -l phase-9,m-v0.9,m-v1.0 --silent)"
  bd close "$carried" >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'warn'
  grep -qF "$carried" <<<"$output"
}

# Break: exempt on the archive alone, forgetting the issue is still live.
# Work left hanging off a cycle that already closed is precisely a finding
# worth reporting, not historical noise.
@test "orphans: an OPEN issue of an archived milestone is NOT exempt" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  mkdir -p .planning/milestones
  echo "# Roadmap: v0.9 (archived)" > .planning/milestones/v0.9-ROADMAP.md
  local live
  live="$(bd create "Never finished last cycle" -t task -l phase-9,m-v0.9 \
    --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'warn'
  grep -qF "$live" <<<"$output"
}

# Break: exempt by absence of evidence. With no m-* label there is no proof of
# archiving at all, and exempting anyway is the same reasoning as approving
# because nothing was compared — the defect this whole phase removes.
@test "orphans: a closed issue with no milestone label is NOT exempt" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  mkdir -p .planning/milestones
  echo "# Roadmap: v0.9 (archived)" > .planning/milestones/v0.9-ROADMAP.md
  local unstamped
  unstamped="$(bd create "Closed, never stamped" -t task -l phase-9 --silent)"
  bd close "$unstamped" >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'warn'
  grep -qF "$unstamped" <<<"$output"
}

# THE INVARIANT OF THE WHOLE PHASE, and the one test that would go red if a
# fifth state were ever added without coming through here. It asserts nothing
# about any single check on purpose.
@test "status vocabulary invariant: four states, every ⊘ scoped, counters summing to the check count" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # 1. Closed vocabulary: subtracting the four leaves nothing.
  assert_json_eq "$output" \
    '[.checks[].status] - ["ok","not-applicable","warn","fail"] | length' '0'
  # 2. Every not-applicable carries one of the two families, and nothing else
  #    carries a scope at all.
  assert_json_eq "$output" \
    '[.checks[] | select(.status=="not-applicable") | select((.scope=="out-of-scope" or .scope=="no-input") | not)] | length' \
    '0'
  assert_json_eq "$output" \
    '[.checks[] | select(.status!="not-applicable") | select(has("scope"))] | length' \
    '0'
  # 3. The four counters sum to the number of registered checks.
  assert_json_eq "$output" \
    '[.counts | to_entries[] | .value] | add' \
    "$(jq -r '.checks | length' <<<"$output")"
  assert_json_eq "$output" '.counts | length' '4'
}

# VOID-02 / criterion 2 of the phase's ROADMAP entry, end to end. This is THE
# proof of the phase: a repo whose roadmap lists nothing must not hand back a
# perfectly green board.
#
# Break: any one of the named checks going back to approving the void. Each is
# asserted by id, on the exact value — `!= "ok"` would be satisfied by `warn`,
# and that is how a false green nearly walked past a test written against
# false greens in phase 29.
@test "empty roadmap: the checks that compared nothing say so, and the footer says the report is incomplete" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  make_roadmap_without_phases

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # The verdict moved where it is READ, not where it decides to block.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.failed' 'false'
  assert_json_eq "$output" '.ok' 'false'

  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-issue") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-issue") | .scope' 'no-input'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .scope' 'no-input'

  # MEASURED CORRECTION to the plan: maps-fresh walks the phase DIRECTORIES on
  # disk and never reads ROADMAP.md, so an empty roadmap leaves it with its
  # input intact — it runs for real and reports what it FOUND (the two
  # generated maps went stale the moment the roadmap changed under them).
  # Asserting the exact `warn` is what proves the correction: a check that
  # still has something to compare must keep comparing, not get swept into
  # the promotion because a neighbouring check lost its input.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="maps-fresh") | .status' 'warn'

  # Each one says WHAT was missing, not just that it gave up.
  grep -qF "ROADMAP.md lists no phase" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "[cairn-doctor] INCOMPLETE" <<<"$output"
  refute_in_output "✓ req-issue"
  refute_in_output "✓ orphans"
}

# Break, and it is the expensive one: refusing check_orphans AS A WHOLE when
# the roadmap is empty. That is the tempting, naive version of the promotion,
# and it would hide every finding of the second axis — a phase that exists to
# remove false green would have created new silence instead.
@test "orphans with an empty roadmap: the axis that still works keeps reporting" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  make_roadmap_without_phases
  local loose
  loose="$(bd create "Loose end nobody placed" -t task --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # The exact value: warn, because there IS a finding — not not-applicable.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .status' 'warn'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="orphans") | .items | length' '1'
  grep -qF "$loose" <<<"$output"
  # And the information that the other axis never ran is NOT lost just
  # because there was something to warn about.
  grep -qF "ROADMAP.md lists no phase" <<<"$output"
}

# Break: promote the plan-inventory checks off the wrong axis. Before 23-03
# both of these read `ok` over an empty inventory — "0 plan bead id(s)
# verified" and "0 superseded plan(s), no live beads" are counts of nothing
# announced as a clean bill of health.
@test "plan-inventory checks: no PLAN.md at all is not-applicable/no-input on both axes" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  rm -f .planning/phases/*/*-PLAN.md

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="frontmatter-ids") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="frontmatter-ids") | .scope' 'no-input'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="superseded-released") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="superseded-released") | .scope' 'no-input'
}

# Break: read the `beads:` gap as vacuous truth. A plan with no stamp is
# EXACTLY the gap cairn exists to prevent, so "0 ids verified" over plans that
# are right there is the loudest possible no-input, not a pass.
@test "frontmatter-ids: plans present but none stamped is not-applicable/no-input" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  python3 - <<'PY'
import re
from pathlib import Path
for p in Path(".planning/phases").glob("*/*-PLAN.md"):
    p.write_text(re.sub(r"^beads: .*\n", "", p.read_text(), flags=re.MULTILINE))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="frontmatter-ids") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="frontmatter-ids") | .scope' 'no-input'
  grep -qF "carries a 'beads:'" <<<"$output"
  # Its sibling on the same axis DID sweep every plan and found no superseded
  # one — that is a real answer, and it must stay `ok`.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="superseded-released") | .status' 'ok'
}

# THE PERMANENCE TEST, and it is not decoration: it is what stops a future
# pass from promoting, by reflex, a check that phase 23 deliberately decided
# to leave alone. Each of these four counts zero in the healthy fixture and
# each of those zeroes is a real answer — the check swept its universe and
# found nothing wrong in it.
#
# Break: promote any of them. `lease-stale` with no lease registered has not
# "failed to check"; it looked for a stuck lease, there is none, and there is
# nothing the operator would want to do about that.
@test "phase 23 decided NOT to promote these four: they stay exactly ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-complete-open") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="label-pairs") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="external-ref") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="lease-stale") | .status' 'ok'
}

# Break: wire this promotion to the roadmap. maps-fresh walks
# `.planning/phases/` on disk and never reads ROADMAP.md, so emptying the
# phases tree is the only lever that silences it — a promotion hung off the
# roadmap would never fire here, and would fire in the test above where the
# check still has work to do.
#
# This is also the shape of a project on day one: a roadmap not yet written
# and no phase directories. It must not read as a clean bill of health.
@test "maps-fresh: no phase directory at all is not-applicable/no-input, not '0 maps current'" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  make_roadmap_without_phases
  rm -rf .planning/phases/*

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="maps-fresh") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="maps-fresh") | .scope' 'no-input'
  grep -qF "no phase directory" <<<"$output"
  # The report as a whole says it is incomplete, and still does not block.
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.failed' 'false'
}

@test "label-pairs: phase-only label warns, --fix-labels repairs, re-run clean" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  stamp_state_milestone
  local stray
  stray="$(bd create "Stray unpaired task" -t task -l phase-2 --silent)"

  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.milestone' 'v1.0'
  assert_json_eq "$output" '.checks[] | select(.id=="label-pairs") | .status' 'warn'
  grep -qF "$stray" <<<"$output"

  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --fix-labels
  [ "$status" -eq 0 ]
  grep -qF "fixed 1 via cairn-relabel pair" <<<"$output"
  refute_in_output "⚠ label-pairs"

  # The pair label and gsd.milestone actually landed in bd.
  run bd show "$stray" --json
  assert_json_eq "$output" '.[0].labels | sort | join(",")' 'm-v1.0,phase-2'
  assert_json_eq "$output" '.[0].metadata.gsd.milestone' 'v1.0'

  # Refresh the phase-2 map (the stray is a new row) -> fully clean re-run.
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  beads_export_refresh
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  refute_in_output "⚠"
  refute_in_output "✗"
}

@test "--fix-labels refuses when the milestone is unresolvable, exit 2" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # no milestone in STATE.md or ROADMAP.md
  make_doctor_fixture
  bd create "Stray unpaired task" -t task -l phase-2 --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --fix-labels
  [ "$status" -eq 2 ]
  grep -qF "milestone unresolvable" <<<"$output"
}

@test "claims-stale: assigned in_progress issue outside the active phase warns" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # STATE.md active_phase: 2
  make_doctor_fixture
  local claimed
  claimed="$(bd create "AUTH-03: Password reset" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-03","phase":1,"milestone":"v1.0"}}' --silent)"
  bd update "$claimed" --claim >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null   # keep check 3 ok

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # claims-stale itself only WARNs, but phase-corroboration (check 11)
  # independently reads the same fact — phase 1 verified on disk, one of
  # its issues in_progress — as its R1 "blocks" conflict (disk vs bd), so
  # the OVERALL run fails until the claim is resolved.
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.active_phase' '2'
  assert_json_eq "$output" '.checks[] | select(.id=="claims-stale") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="claims-stale") | .items | length' '1'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
  grep -qF "$claimed" <<<"$output"
  grep -qF "stale claim" <<<"$output"
}

@test "bd-doctor: summary line captured in the report" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="bd-doctor") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="bd-doctor") | .detail | startswith("exit 0:")' 'true'
}

@test "no .planning/ — not applicable, exit 0, suggests /cairn:migrate" {
  require_bd
  make_tmp_repo
  bd init -q --prefix doc --non-interactive >/dev/null 2>&1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
  grep -qF "/cairn:migrate" <<<"$output"

  # MEASURED 2026-08-07 while adding check 20: this path registers ZERO
  # checks — the doctor short-circuits before the check list is built, so
  # `.checks` is empty and `.ok` is true by construction. Any assertion here
  # about a particular check's status or scope would pass against every
  # implementation, which is not a proof of anything. Said out loud because
  # the vacuous version of it was written first.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks | length' '0'
  assert_json_eq "$output" '.ok' 'true'
}

@test "no .beads/ — not applicable, exit 0, suggests /cairn:migrate" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
  grep -qF "/cairn:migrate" <<<"$output"
}

@test "neither .planning/ nor .beads/ — not applicable, no migrate hint" {
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
  refute_in_output "/cairn:migrate"
}

@test "bd missing from PATH exits 5 with a warning" {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  mkdir .beads   # applicable, but bd is unreachable
  local stub="$BATS_TEST_TMPDIR/nobd-bin"
  mkdir -p "$stub"
  # Link the real interpreter (not a version-manager shim needing PATH).
  ln -s "$(python3 -c 'import sys; print(sys.executable)')" "$stub/python3"
  ln -s "$(command -v bash)" "$stub/bash"
  ln -s "$(command -v dirname)" "$stub/dirname"

  run env PATH="$stub" "$stub/bash" "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 5 ]
  grep -qF "warning" <<<"$output"
}

@test "unknown flag is a usage error, exit 2" {
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --frobnicate
  [ "$status" -eq 2 ]
}

# Mais dois testes de gsd-capability removidos pela fase 37, pela mesma razão
# dos quatro acima — e estes dois em particular mediam coisas que a inversão
# tornou irrelevantes por completo:
#
#   "an unloadable gsd-core manifest fails and outranks registration" — o
#     defeito de manifesto é do plugin gsd-core UPSTREAM (open-gsd/gsd-core
#     #2077). cairn não instala mais esse plugin, então não há manifesto alheio
#     para reparar; e se um gsd-core estiver instalado, o check já falha antes,
#     pedindo uninstall. `repair-manifest` continua existindo em
#     cairn-capability.py para quem o tenha por conta própria.
#   "two GSD lineages installed at once fails the doctor" — a única mudança é
#     que agora UMA linhagem já basta para falhar. O caso das duas juntas
#     virou A2c em tests/cairn-doctor-lineage.bats, e a asserção de que as
#     duas são NOMEADAS sobreviveu inteira.
#
# --------------------------------------------------------------------------- #
# phase-corroboration (check 11, CORR-06) — 13-03
# --------------------------------------------------------------------------- #

# Point STATE.md's active_phase at N (fixture always ships '"2"').
set_state_active_phase() {
  python3 - "$1" <<'PY'
import re
import sys
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(re.sub(r'active_phase: ".*?"', f'active_phase: "{sys.argv[1]}"',
                     p.read_text()))
PY
}

@test "phase-corroboration: clean fixture reports ok with no items" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .items | length' '0'
}

@test "phase-corroboration: disk-vs-bd blocks conflict fails the check and the run, exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 verified on disk and roadmap-complete
  make_doctor_fixture
  # Plan 13-01's canonical "blocks" scenario: disk says phase 1 is done
  # (SUMMARY + VERIFICATION exist), bd still has an open issue for it.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(startswith("1:"))] | length' '1'
  grep -qF "disk reports phase 1 verified" <<<"$output"
  grep -qF "close the open bd issue(s) if the work is done" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ phase-corroboration" <<<"$output"
  grep -qF "[cairn-doctor] FAIL" <<<"$output"
}

@test "phase-corroboration: state_md-vs-disk informs conflict warns, never fails the run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 verified, phase 2 active
  make_doctor_fixture
  # Point the workflow pointer at the phase that already shipped — a stale
  # pointer (R3, informs) with nothing else disagreeing.
  set_state_active_phase 1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # informs never fails the run (D-10)
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .items | length' '1'
  grep -qF "STATE.md still points at phase 1, disk already reports verified" <<<"$output"
  grep -qF "STATE.md's active_phase looks stale" <<<"$output"
}

@test "phase-corroboration: recommendation text is routed per conflict source pair" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Both a "blocks" (disk vs bd) AND an "informs" (state_md vs disk)
  # conflict on the SAME phase in the SAME run — the routed recommendation
  # must differ per item, not bleed from one item's text into the other's.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  set_state_active_phase 1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(test("disk reports")) | select(test("close the open bd issue"))] | length' '1'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(test("STATE.md still points")) | select(test("close the open bd issue"))] | length' '0'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(test("STATE.md still points")) | select(test("looks stale"))] | length' '1'
}

# --------------------------------------------------------------------------- #
# phase-corroboration's last-moved enrichment (JOUR-02) — 16-05
# --------------------------------------------------------------------------- #

@test "last-moved: a real conflict item names each cited source's last-moved timestamp, or 'never observed'" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Plan 13-01's canonical "blocks" scenario: disk says phase 1 is done,
  # bd still has an open issue for it.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  # Seed phase 1's disk axis directly (cairn-journal.py observe, NOT
  # through any /cairn:status render), so its last-moved timestamp is a
  # KNOWN value captured straight from the seed call — never guessed.
  local seed_output seeded_ts
  seed_output="$(printf '[{"phase":1,"evidence":{"disk":"verified"}}]' \
    | python3 "$CAIRN_SCRIPTS_DIR/cairn-journal.py" observe --project-dir "$PWD" --json)"
  seeded_ts="$(jq -r '.written[0].ts' <<<"$seed_output")"
  [ -n "$seeded_ts" ]
  [ "$seeded_ts" != "null" ]

  # A CAIRN_JOURNAL stub that blocks ONLY the `observe` subcommand (the
  # exact call cairn-status.py's own internal journal wiring, Plan 16-04,
  # makes as part of computing this very conflict) but execs into the
  # REAL cairn-journal.py for every other subcommand. Without this, bd's
  # first-ever real value would be observed and journaled moments before
  # doctor's own last-moved read — this stub is what keeps bd genuinely
  # "never observed" while disk's earlier seed stays exactly as written.
  local stub="$BATS_TEST_TMPDIR/observe-blocking-journal.py"
  cat > "$stub" <<'PYEOF'
#!/usr/bin/env python3
import os, sys
if sys.argv[1] == "observe":
    sys.exit(1)
os.execv(sys.executable,
         [sys.executable, os.environ["CAIRN_JOURNAL_REAL"]] + sys.argv[1:])
PYEOF
  chmod +x "$stub"

  run env CAIRN_JOURNAL="$stub" \
      CAIRN_JOURNAL_REAL="$CAIRN_SCRIPTS_DIR/cairn-journal.py" \
      bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'

  local item
  item="$(jq -r '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(startswith("1:"))][0]' <<<"$output")"
  [ "$item" != "null" ]
  grep -qF "disk last moved $seeded_ts" <<<"$item"
  grep -qF "bd last moved never observed" <<<"$item"
}

@test "last-moved: an axis observed by two checkouts names each machine and claims no order between them" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  # Phase 28: the journal is partitioned one file per checkout, so an axis
  # CAN have been observed by more than one. Seeded as two simulated
  # machines against one directory, which is exactly the four-worktree
  # situation this repository was measured in.
  local ts_a ts_b
  ts_a="$(printf '[{"phase":1,"evidence":{"disk":"verified"}}]' \
    | CAIRN_JOURNAL_MACHINE=hostA python3 "$CAIRN_SCRIPTS_DIR/cairn-journal.py" \
        observe --project-dir "$PWD" --json | jq -r '.written[0].ts')"
  ts_b="$(printf '[{"phase":1,"evidence":{"disk":"planned"}}]' \
    | CAIRN_JOURNAL_MACHINE=hostB python3 "$CAIRN_SCRIPTS_DIR/cairn-journal.py" \
        observe --project-dir "$PWD" --json | jq -r '.written[0].ts')"
  [ -n "$ts_a" ]
  [ -n "$ts_b" ]
  [ "$ts_a" != "$ts_b" ]

  local stub="$BATS_TEST_TMPDIR/observe-blocking-journal.py"
  cat > "$stub" <<'PYEOF'
#!/usr/bin/env python3
import os, sys
if sys.argv[1] == "observe":
    sys.exit(1)
os.execv(sys.executable,
         [sys.executable, os.environ["CAIRN_JOURNAL_REAL"]] + sys.argv[1:])
PYEOF
  chmod +x "$stub"

  run env CAIRN_JOURNAL="$stub" \
      CAIRN_JOURNAL_REAL="$CAIRN_SCRIPTS_DIR/cairn-journal.py" \
      bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # The severity is decided before the clause is ever built, and stays put.
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-corroboration") | .status' 'fail'

  local item
  item="$(jq -r '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(startswith("1:"))][0]' <<<"$output")"
  [ "$item" != "null" ]
  # Both machines named, both timestamps shown, and the sentence that says
  # outright that no order is claimed between them (E14: a -16.7 ms clock
  # offset against a 10.8 ms minimum record gap).
  grep -qF "on hostA" <<<"$item"
  grep -qF "on hostB" <<<"$item"
  grep -qF "$ts_a" <<<"$item"
  grep -qF "$ts_b" <<<"$item"
  grep -qF "order between machines not claimed" <<<"$item"
}

@test "DJOUR-03: deleting the whole journal surface moves no status, no severity, no exit code" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  # A first run, which journals as a side effect and so leaves real history
  # behind for the delete to have something to destroy.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  local before_status="$status"
  local before="$output"
  [ "$before_status" -eq 7 ]
  # Confirm the journal genuinely has content -- otherwise the delete below
  # proves nothing.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-journal.sh" history --json --project-dir "$PWD"
  [ "$(jq '.records | length' <<<"$output")" -gt 0 ]
  grep -qF "last moved" <<<"$before"

  # Phase 28 made the surface bigger than one path: the partition directory
  # AND the inherited single file.
  rm -rf .cairn/journal
  rm -f .cairn/journal.jsonl*
  run bash "$CAIRN_SCRIPTS_DIR/cairn-journal.sh" history --json --project-dir "$PWD"
  assert_json_eq "$output" '.records | length' '0'
  assert_json_eq "$output" '.partitions | length' '0'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  local after_status="$status"
  local after="$output"

  # Exact values, on both sides. Never "still fails" -- a check that went
  # from fail to fail for a different reason would satisfy that.
  [ "$after_status" -eq "$before_status" ]
  assert_json_eq "$after" '.checks[] | select(.id=="phase-corroboration") | .status' \
    "$(jq -r '.checks[] | select(.id=="phase-corroboration") | .status' <<<"$before")"
  # Every check's status, not just the one this clause hangs off.
  [ "$(jq -Sc '[.checks[] | {id, status}]' <<<"$before")" \
    = "$(jq -Sc '[.checks[] | {id, status}]' <<<"$after")" ]
  # Same number of items, in the same order, for the corroboration check.
  [ "$(jq '[.checks[] | select(.id=="phase-corroboration") | .items[]] | length' <<<"$before")" \
    = "$(jq '[.checks[] | select(.id=="phase-corroboration") | .items[]] | length' <<<"$after")" ]

  # THE SHARP ONE. The doctor run itself journals as a side effect (its own
  # cairn-status.py --json call observes), so the deleted journal is
  # repopulated by the very run being measured and the `last moved` clause
  # comes BACK -- with fresh timestamps. That is the journal rebuilding
  # itself, not the verdict moving. So the assertion is byte equality of
  # every corroboration item with the timestamps normalised away: if
  # anything but a timestamp changed, this fails.
  local norm_before norm_after
  norm_before="$(jq -r '[.checks[] | select(.id=="phase-corroboration") | .items[]] | .[]' <<<"$before" \
    | sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.+-]+/<TS>/g')"
  norm_after="$(jq -r '[.checks[] | select(.id=="phase-corroboration") | .items[]] | .[]' <<<"$after" \
    | sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.+-]+/<TS>/g')"
  [ "$norm_before" = "$norm_after" ]

  # And the case where the journal cannot come back at all: with the
  # journal script itself unreachable, the clause is simply gone and the
  # verdict is still the same one.
  run env CAIRN_JOURNAL=/nonexistent/path bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq "$before_status" ]
  refute_in_output "last moved"
  [ "$(jq -Sc '[.checks[] | {id, status}]' <<<"$before")" \
    = "$(jq -Sc '[.checks[] | {id, status}]' <<<"$output")" ]
}

@test "last-moved: a broken CAIRN_JOURNAL leaves status/detail identical to a working journal, only the clause is missing" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  local working_status working_count
  working_status="$(jq -r '.checks[] | select(.id=="phase-corroboration") | .status' <<<"$output")"
  working_count="$(jq -r '.checks[] | select(.id=="phase-corroboration") | .items | length' <<<"$output")"
  grep -qF "last moved" <<<"$output"

  run env CAIRN_JOURNAL=/nonexistent/path bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  local broken_status broken_count
  broken_status="$(jq -r '.checks[] | select(.id=="phase-corroboration") | .status' <<<"$output")"
  broken_count="$(jq -r '.checks[] | select(.id=="phase-corroboration") | .items | length' <<<"$output")"
  [ "$broken_status" = "$working_status" ]
  [ "$broken_count" = "$working_count" ]
  refute_in_output "last moved"
}

@test "last-moved: journal_last_moved() is called at most once per phase, not once per conflict item" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Phase 2 with BOTH a disk-vs-bd AND a roadmap-vs-disk conflict at once
  # (the plan's own example): roadmap ticked, disk still "planned" (a
  # PLAN.md, no SUMMARY yet), bd's only phase-2 issue closed.
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/ROADMAP.md")
p.write_text(p.read_text().replace("- [ ] **Phase 2: API**",
                                   "- [x] **Phase 2: API**"))
PY
  bd close "$DOC_P2" >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null

  local stub="$BATS_TEST_TMPDIR/counting-journal.py"
  local count_file="$BATS_TEST_TMPDIR/last-moved-call-count"
  cat > "$stub" <<'PYEOF'
#!/usr/bin/env python3
import os, sys
with open(os.environ["CAIRN_JOURNAL_CALL_COUNT_FILE"], "a") as f:
    f.write(sys.argv[1] + "\n")
os.execv(sys.executable,
         [sys.executable, os.environ["CAIRN_JOURNAL_REAL"]] + sys.argv[1:])
PYEOF
  chmod +x "$stub"

  run env CAIRN_JOURNAL="$stub" \
      CAIRN_JOURNAL_CALL_COUNT_FILE="$count_file" \
      CAIRN_JOURNAL_REAL="$CAIRN_SCRIPTS_DIR/cairn-journal.py" \
      bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-corroboration") | .items[] | select(startswith("2:"))] | length' '2'

  [ -f "$count_file" ]
  local n_last_moved
  n_last_moved="$(grep -c '^last-moved$' "$count_file" || true)"
  [ "$n_last_moved" -eq 1 ]
}

# --------------------------------------------------------------------------- #
# .gitignore — the journal entry and its compaction siblings (Plan 16-05)
# --------------------------------------------------------------------------- #

@test "gitignore: the journal's per-machine scratch is never staged by git add -A, but its partition segment is" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The .gitignore under test is the REPO'S OWN — copied into the fixture
  # so this proves the actual entry takes effect, not a fixture stand-in.
  cp "$CAIRN_REPO_ROOT/.gitignore" .gitignore

  # Seed a real conflict (same fixture shape as the last-moved tests
  # above) so the journal carries genuine content, not an empty stub.
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  # Phase 28: the write lands in this checkout's own PARTITION, and that
  # segment is the one thing under .cairn/ that IS meant to be versioned.
  local segment
  segment="$(python3 "$CAIRN_SCRIPTS_DIR/cairn-journal.py" provenance \
    --project-dir "$PWD" --json | jq -r '.segment')"
  [ -f "$segment" ]
  [ ! -f .cairn/journal.jsonl ]

  # The per-machine scratch that lives next to the segments: the partition's
  # own compaction lock, and the shape a pre-phase-28 crash could leave in
  # .cairn/ itself.
  : > "$(dirname "$segment")/leftover.compact.lock"
  : > .cairn/journal.jsonl.tmp-abc123
  : > .cairn/journal.jsonl.compact.lock

  git add -A

  # Nothing per-machine is staged...
  run git diff --cached --name-only
  refute_in_output "journal.jsonl"
  refute_in_output ".compact.lock"

  # ...and the partition segment IS, because a journal that never crosses
  # machines was the design phase 28 replaced.
  run git diff --cached --name-only
  grep -qF "$(basename "$segment")" <<<"$output"
}

# --------------------------------------------------------------------------- #
# phase-artifacts (check 12, CARD-02/D-04) — 14-03
# --------------------------------------------------------------------------- #

# Give phase 2's existing 02-01-PLAN.md a SUMMARY.md (so it stops being the
# ordinary mid-flight gap the healthy fixture ships with) and add a second
# plan, 02-02-PLAN.md, deliberately left without one — the "two plans, only
# one summarized" shape check_phase_artifacts' missing-SUMMARY half looks
# for. ROADMAP.md's phase-2 checkbox is left unticked throughout (the
# fixture never ticks it), so any item here is coming from disk_state, not
# from check 5's ROADMAP-complete gate.
make_phase2_two_plans_one_summary() {
  cat > .planning/phases/02-api/02-01-SUMMARY.md <<'EOF'
---
phase: 02-api
plan: "01"
subsystem: api
tags: [python, api]
provides:
  - rate limiting middleware in src/api.py
key-files:
  created: [src/api.py]
  modified: []
key-decisions: []
duration: 8min
completed: 2026-07-21
status: complete
---

# Phase 2: API Summary (Minimal)

**Rate limiting middleware implemented and tested.**
EOF
  cat > .planning/phases/02-api/02-02-PLAN.md <<'EOF'
---
phase: 02-api
plan: "02"
type: execute
wave: 1
depends_on: []
files_modified: [src/api_extra.py]
autonomous: true
requirements: []
must_haves:
  truths: []
  artifacts: []
  key_links: []
---

<objective>
Second plan in phase 2, deliberately left without a SUMMARY.md — the
missing-SUMMARY fixture for phase-artifacts.

Purpose: exercise check_phase_artifacts' missing-SUMMARY half.
Output: src/api_extra.py
</objective>

<tasks>

<task type="auto">
  <name>Task 1: placeholder</name>
  <files>src/api_extra.py</files>
  <action>placeholder</action>
  <verify>true</verify>
  <done>placeholder</done>
</task>

</tasks>
EOF
  # The fixture adds a plan and a summary to phase 2, so STATE.md's plan
  # counters move with it. Left behind they are a REAL ledger disagreement
  # (check 17 names them), and this fixture is about phase-artifacts — a
  # second finding riding along would make the "exactly one warning" assertion
  # below fail for a reason that has nothing to do with what it tests.
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(p.read_text()
             .replace("  total_plans: 2", "  total_plans: 3")
             .replace("  completed_plans: 1", "  completed_plans: 2"))
PY
}

# NN-VERIFICATION.md with a readable status: field — pushes phase 2's
# disk_state to "verified" without itself triggering the unreadable-status
# half.
add_phase2_verification_passed() {
  cat > .planning/phases/02-api/02-VERIFICATION.md <<'EOF'
---
phase: 02-api
verified: 2026-07-25T10:00:00Z
status: passed
score: 1/1 must-haves verified
behavior_unverified: 0
---

# Phase 2: API Verification Report

**Status:** passed
EOF
}

# NN-VERIFICATION.md with a readable frontmatter block but NO status:
# field — the unreadable-verdict fixture.
add_phase2_verification_no_status() {
  cat > .planning/phases/02-api/02-VERIFICATION.md <<'EOF'
---
phase: 02-api
verified: 2026-07-25T10:00:00Z
---

# Phase 2: API Verification Report (status field omitted)
EOF
}

# Pushing phase 2 to disk_state "verified" without this would ALSO trip
# phase-corroboration's own R1/R3 axes (DOC_P2, phase 2's bd issue, is
# still open; STATE.md's active_phase fixture default is "2"), confounding
# the assertions below with a second, unrelated check's findings. Closes
# the issue, regenerates its map (closing changes the map's status column,
# see maps-fresh), and points active_phase somewhere that collides with no
# real phase — isolating these tests to phase-artifacts' own behavior, the
# same way the phase-corroboration tests above build single-conflict
# fixtures on purpose.
# Take phase 2's corroboration out of the picture so a phase-artifacts test
# measures phase-artifacts and nothing else. The bd side must be made to AGREE
# with what the disk actually says, and $1 names which side the disk is on:
#
#   done      the phase reached executed/verified -> close the bd issue
#   underway  the phase has plans still unsummarized -> leave it open
#
# It used to close the issue unconditionally, and that was correct only while
# a single -SUMMARY.md was enough to call a whole phase `executed` (FIX-05,
# CairnGo-0po). With `executed` now meaning EVERY plan has its summary, a
# two-plan/one-summary phase reads `planned`, and closing its issue creates a
# real disk-vs-bd conflict instead of removing one. Which is the point of the
# fix: the model stopped agreeing with a claim the disk does not support.
neutralize_phase2_corroboration() {
  case "${1:-done}" in
    done) bd close "$DOC_P2" >/dev/null ;;
    underway) : ;;
    *) echo "neutralize_phase2_corroboration: unknown disk side '$1'" >&2
       return 1 ;;
  esac
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 2 >/dev/null
  set_state_active_phase 99
}

@test "phase-artifacts: clean fixture reports ok with no items" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .items | length' '0'
}

@test "phase-artifacts: verified phase with an unsummarized plan warns, names the file, never fails the run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 2's checkbox stays unticked throughout
  make_doctor_fixture
  make_phase2_two_plans_one_summary
  add_phase2_verification_passed
  neutralize_phase2_corroboration

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # a phase-artifacts warn never turns the run exit 7
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .status' 'warn'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-artifacts") | .items[] | select(. == "phase 2: 02-02-PLAN.md lacks its SUMMARY")] | length' '1'
}

@test "phase-artifacts: same two-plan/one-summary phase with NO VERIFICATION.md produces zero items (mid-flight regression)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Identical to the warn case above MINUS add_phase2_verification_passed —
  # this is the exact false positive an earlier, ungated draft produced and
  # a plan-checker caught: a phase between waves, with some plans still
  # unsummarized, disk_state never having reached "verified". It must stay
  # green forever, not just today.
  make_phase2_two_plans_one_summary
  # Adding 02-01-SUMMARY.md alone used to move phase 2's disk_state from
  # "planned" to "executed", which tripped phase-corroboration's disk-vs-bd
  # axis against the still-open DOC_P2 — an unrelated confound this test is
  # not about, and the reason the neutralizer closed that issue.
  #
  # Since FIX-05 (CairnGo-0po) `executed` means EVERY plan has its summary, so
  # this phase reads "planned" and the confound is gone at the source: an open
  # issue is what a phase with unsummarized plans is supposed to have. Closing
  # it now would MANUFACTURE the conflict the neutralizer exists to remove.
  neutralize_phase2_corroboration underway

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .status' 'ok'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-artifacts") | .items[] | select(startswith("phase 2:"))] | length' '0'
}

@test "phase-artifacts: verified phase with an unreadable VERIFICATION status warns, never fails the run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Give 02-01 its summary so this scenario isolates the unreadable-status
  # half — no missing-SUMMARY noise mixed into the same item set.
  cat > .planning/phases/02-api/02-01-SUMMARY.md <<'EOF'
---
phase: 02-api
plan: "01"
subsystem: api
tags: [python, api]
provides:
  - rate limiting middleware in src/api.py
key-files:
  created: [src/api.py]
  modified: []
key-decisions: []
duration: 8min
completed: 2026-07-21
status: complete
---

# Phase 2: API Summary (Minimal)

**Rate limiting middleware implemented and tested.**
EOF
  add_phase2_verification_no_status
  neutralize_phase2_corroboration

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-artifacts") | .status' 'warn'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="phase-artifacts") | .items[] | select(. == "phase 2: has a VERIFICATION.md but no readable '"'"'status:'"'"' field in its frontmatter")] | length' '1'
}

@test "phase-artifacts: a lone phase-artifacts warn never turns an otherwise-clean run into a failure" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  make_phase2_two_plans_one_summary
  add_phase2_verification_passed
  neutralize_phase2_corroboration

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '[.checks[] | select(.status=="fail")] | length' '0'
  assert_json_eq "$output" '[.checks[] | select(.status=="warn")] | .[0].id' 'phase-artifacts'
  assert_json_eq "$output" '[.checks[] | select(.status=="warn")] | length' '1'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⚠ phase-artifacts" <<<"$output"
  refute_in_output "✗"
  grep -qF "[cairn-doctor] ok" <<<"$output"
}

# --------------------------------------------------------------------------- #
# external-ref (check 13, CORR-08/D-11) — 13-03
# --------------------------------------------------------------------------- #

@test "external-ref: unambiguous git match reported by default, --link-refs backfills, idempotent" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # Isolate the scenario to DOC_A1: DOC_A2 already carries an external_ref,
  # so it drops out of `lacking` and stays out of what is asserted here.
  bd update "$DOC_A2" --external-ref gh-1 >/dev/null
  mkdir -p src
  echo "def signup(): pass" >> src/auth.py
  git add src/auth.py
  git commit -qm "feat(auth): add signup handler (#42)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'warn'
  assert_json_eq "$output" \
    "[.checks[] | select(.id==\"external-ref\") | .items[] | select(. == \"$DOC_A1 -> gh-42\")] | length" '1'

  # Nothing written yet — the default run is read-only.
  run bd show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref // "none"' 'none'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --link-refs
  [ "$status" -eq 0 ]
  grep -qF "linked $DOC_A1 -> gh-42" <<<"$output"

  run bd show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref' 'gh-42'

  # Idempotent: a second run (a fresh process reading fresh bd state) has
  # nothing left to link.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json --link-refs
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'ok'
  refute_in_output "linked"
}

@test "external-ref: two different PR numbers in the window is ambiguous, never a candidate" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  bd update "$DOC_A2" --external-ref gh-1 >/dev/null
  mkdir -p src
  echo "one" >> src/auth.py
  git add src/auth.py
  git commit -qm "wip: signup tweak (#10)"
  echo "two" >> src/auth.py
  git add src/auth.py
  git commit -qm "wip: another tweak (#11)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .items | length' '0'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --link-refs
  [ "$status" -eq 0 ]
  run bd show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref // "none"' 'none'
}

@test "external-ref: a real shallow clone skips --link-refs entirely, writes nothing (D-08)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  mkdir -p src
  echo "def signup(): pass" >> src/auth.py
  git add src/auth.py
  git commit -qm "feat(auth): add signup handler (#42)"

  # A REAL shallow clone (git clone --depth 1), per STACK.md's verified
  # recipe — not a simulated flag. bd's actual data lives under a
  # gitignored embeddeddolt/ dir that a plain clone never carries, and
  # .planning/ here was never committed either, so both are copied across
  # the same way an operator would after cloning.
  local src_repo="$PWD"
  local clone_dir="$BATS_TEST_TMPDIR/ext-ref-shallow-clone"
  git clone --depth 1 -q "file://$src_repo" "$clone_dir"
  rm -rf "$clone_dir/.beads"
  cp -r "$src_repo/.beads" "$clone_dir/.beads"
  chmod 700 "$clone_dir/.beads"
  cp -r "$src_repo/.planning" "$clone_dir/.planning"

  run git -C "$clone_dir" rev-parse --is-shallow-repository
  [ "$output" = "true" ]

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --project-dir "$clone_dir" \
    --json --link-refs
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'warn'
  grep -qF "shallow clone" <<<"$output"

  run bd -C "$clone_dir" show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref // "none"' 'none'
}

@test "external-ref: composes with --close-completed in one invocation" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 checked off in ROADMAP.md
  make_doctor_fixture
  bd update "$DOC_A2" --external-ref gh-1 >/dev/null
  mkdir -p src
  echo "def signup(): pass" >> src/auth.py
  git add src/auth.py
  git commit -qm "feat(auth): add signup handler (#42)"
  local straggler
  straggler="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json --link-refs --close-completed
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="phase-complete-open") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="external-ref") | .status' 'ok'

  run bd show "$DOC_A1" --json
  assert_json_eq "$output" '.[0].external_ref' 'gh-42'
  run bd show "$straggler" --json
  assert_json_eq "$output" '.[0].status' 'closed'
}

# --------------------------------------------------------------------------- #
# lease-stale (check 13, LEASE-05) — 15-03
# --------------------------------------------------------------------------- #

LEASE="$CAIRN_SCRIPTS_DIR/cairn-lease.sh"

# Hand-set a lease issue's heartbeat_at to hours-in-the-past via bd update
# directly (same technique as tests/cairn-lease.bats' own staleness
# fixture) — never a real 4-hour sleep.
stale_lease_heartbeat() {
  local lease_id="$1" phase="$2" holder="$3" acquired_at="$4" hours_ago="$5"
  local stale_ts
  stale_ts="$(python3 -c "
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) - timedelta(hours=$hours_ago)).isoformat())
")"
  bd update "$lease_id" --metadata \
    "{\"cairn\":{\"lease\":{\"phase\":$phase,\"holder\":\"$holder\",\"actor\":\"a\",\"host\":\"h\",\"acquired_at\":\"$acquired_at\",\"heartbeat_at\":\"$stale_ts\"}}}" \
    >/dev/null
}

@test "lease-stale: a lease with a heartbeat older than 4h warns, itemized by phase and holder, exit 0" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$LEASE" acquire 2 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local lease_id acquired_at holder
  lease_id="$(jq -r '.id' <<<"$output")"
  acquired_at="$(jq -r '.acquired_at' <<<"$output")"
  holder="$(jq -r '.holder' <<<"$output")"

  stale_lease_heartbeat "$lease_id" 2 "$holder" "$acquired_at" 5

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]   # WARN never fails the doctor run (D-04/LEASE-05)
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .status' 'warn'
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .items | length' '1'
  grep -qF "phase 2" <<<"$output"
  grep -qF "$holder" <<<"$output"
  grep -qF "reclaimable" <<<"$output"
  grep -qF "cairn-lease.sh release 2" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⚠ lease-stale" <<<"$output"
}

@test "lease-stale: a freshly-acquired lease (no stale heartbeat) reads ok, empty items" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$LEASE" acquire 2 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .items | length' '0'
}

@test "lease-stale: the lease bookkeeping issue is exempt from check 6 (orphans) even vacant" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$LEASE" acquire 2 --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$LEASE" release 2 --project-dir "$PWD"
  [ "$status" -eq 0 ]

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .status' 'ok'
  assert_json_eq "$output" '.checks[] | select(.id=="orphans") | .items | length' '0'
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .status' 'ok'
}

@test "lease-stale: cairn-lease.py itself failing degrades to warn, never crashes the doctor run" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  # A bd wrapper that fails ONLY the lease-label lookup cairn-lease.py's
  # status --all makes ('bd ... -l lease ...'), passing every other
  # invocation straight through to the real bd. Same PATH-stub seam as the
  # "bd missing from PATH" test above, narrowed to a single sibling
  # script's own bd call instead of bd being entirely absent — the only
  # way to observe lease-stale actually degrade while the REST of the
  # doctor run completes normally.
  local real_bd
  real_bd="$(command -v bd)"
  local stub="$BATS_TEST_TMPDIR/bd-lease-fail-bin"
  mkdir -p "$stub"
  cat > "$stub/bd" <<EOF
#!/usr/bin/env bash
for a in "\$@"; do
  if [ "\$a" = "lease" ]; then
    echo "bd: simulated lease lookup failure" >&2
    exit 1
  fi
done
exec "$real_bd" "\$@"
EOF
  chmod +x "$stub/bd"

  run env PATH="$stub:$PATH" bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"
  assert_json_eq "$output" '.checks[] | select(.id=="lease-stale") | .status' 'warn'
  grep -qF "lease staleness could not be computed" <<<"$output"
  # The failure stayed scoped to lease-stale — nothing else regressed. The
  # assertion used to read `.status != "ok"`, which phase 23 broke two plans
  # before this one: 23-02 gave this fixture — a USER's repo, carrying none of
  # cairn's manifests — a legitimate ⊘ on release-versions and test-parallel,
  # and `!= "ok"` counts a ⊘ as a regression. Measured at that commit: this
  # test returned 2 where it expected 0.
  #
  # So it now asks the question it always meant: did any OTHER check turn warn
  # or fail. Named exactly, never by negating "ok" — a negation of ok is
  # satisfied by warn, which is precisely the confusion this phase exists to
  # remove. The two ⊘ are then pinned by id AND by family, so a THIRD one
  # appearing (a real regression into the fourth state) still fails here.
  assert_json_eq "$output" \
    '[.checks[] | select(.id != "lease-stale")
                | select(.status == "warn" or .status == "fail")] | length' '0'
  #
  # THREE since phase 30: `phase-landed` joins them, and it is the same class
  # of legitimate ⊘ the note above describes. This fixture is a git repo with
  # no remote and no commit (make_tmp_repo), so no control branch exists to
  # compare against — permanently, for a repo shaped like this — which is
  # `out-of-scope` and not `no-input`. Charging it as a gap would hand every
  # single-branch user repo a permanent INCOMPLETE footer, the exact false-red
  # phase 23 refused. The literal is EDITED, never loosened to a subset: a
  # subset assertion is the one that stops catching a real regression into the
  # fourth state, and catching that is why this line exists.
  #
  # FOUR since phase 25: `state-dialect` joins them, same class again. This
  # fixture's STATE.md carries active_phase and no current_phase, so there is
  # no second dialect for it to disagree with — out-of-scope, and never
  # no-input, which would charge every GSD repo that has not run
  # cairn-bookkeep with a permanent gap the doctor already reports once, on
  # claims-stale.
  assert_json_eq "$output" \
    '[.checks[] | select(.status == "not-applicable") | .id] | sort | join(",")' \
    'phase-landed,release-versions,state-dialect,test-parallel'
  assert_json_eq "$output" \
    '[.checks[] | select(.status == "not-applicable") | .scope] | sort | join(",")' \
    'out-of-scope,out-of-scope,out-of-scope,out-of-scope'
}

# --------------------------------------------------------------------------- #
# --apply-reconciliation (ESC-03, Phase 17 Plan 3) — the human-invoked,
# separate command that applies a verified semantic-escalation reconciliation
# proposal. Not a check: a fixer, tested the same way --close-completed and
# --fix-labels are, against a real conflicted fixture and a real bd.
# --------------------------------------------------------------------------- #

RECONCILE="$CAIRN_SCRIPTS_DIR/cairn-reconcile.sh"

# The same disk-vs-bd "blocks" corroboration conflict the phase-corroboration
# tests above build (line ~833): phase 1 verified on disk and roadmap-
# complete, one straggler bd issue for phase 1 still open — the recipe that
# makes `cairn-reconcile.py collect 1` succeed with a "conflict" verdict
# instead of refusing. Exports RECON_STRAGGLER (the open issue's id).
make_conflicted_fixture() {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  RECON_STRAGGLER="$(bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent)"
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
}

# A fresh, evidence-hash-current reconciliation proposal for PHASE: a
# bd_close claim naming TARGET (any bd id — callers pick one in or out of
# PHASE's own labels) plus a manual_review claim, both citing REAL lines
# from ROADMAP.md so citation verification passes. Calls a real `collect`
# to capture the CURRENT evidence_hash — the same hash
# --apply-reconciliation's own freshness re-check will re-derive and
# compare against, so a proposal built by this helper and applied
# immediately always starts out valid on both axes.
write_valid_proposal() {
  local phase="$1" target="$2"
  local ehash
  ehash="$(bash "$RECONCILE" collect "$phase" --project-dir "$PWD" --json | jq -r '.evidence_hash')"
  local line1
  line1="$(sed -n '1p' .planning/ROADMAP.md)"
  mkdir -p .cairn
  python3 - "$phase" "$ehash" "$target" "$line1" <<'PY'
import json
import sys

phase, ehash, target, line1 = sys.argv[1:5]
proposal = {
    "phase": int(phase),
    "generated_at": "2026-07-31T00:00:00Z",
    "evidence_hash": ehash,
    "claims": [
        {
            "statement": f"{target} is an open straggler in a phase disk "
                         "already reports verified.",
            "citations": [
                {"file": ".planning/ROADMAP.md", "line": 1, "text": line1}
            ],
            "recommended_action": {"type": "bd_close", "issue": target,
                                    "reason": "phase complete, straggler stale"}
        },
        {
            "statement": "A separate, ambiguous finding needs a human look.",
            "citations": [
                {"file": ".planning/ROADMAP.md", "line": 1, "text": line1}
            ],
            "recommended_action": {"type": "manual_review", "issue": None,
                                    "note": "ambiguous, needs a human"}
        }
    ]
}
with open(".cairn/conflicts.json", "w") as f:
    json.dump(proposal, f)
PY
}

@test "apply-reconciliation: no .cairn/conflicts.json -> clean refusal, no crash" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"
  grep -qiF "no proposal" <<<"$output"
}

@test "apply-reconciliation: a stale evidence_hash is refused, bd state unchanged" {
  require_bd
  make_conflicted_fixture
  local bd_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"

  write_valid_proposal 1 "$RECON_STRAGGLER"
  # Corrupt the stored hash to a plausible-looking but wrong one — the
  # tree did not actually move, but the proposal's own claim about its
  # evidence no longer matches what a fresh collect produces.
  python3 - <<'PY'
import json
from pathlib import Path
p = Path(".cairn/conflicts.json")
data = json.loads(p.read_text())
data["evidence_hash"] = "sha256:" + "0" * 64
p.write_text(json.dumps(data))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 7 ]
  grep -qF "proposal is stale" <<<"$output"

  local bd_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  [ "$bd_before" = "$bd_after" ]
  run bd show "$RECON_STRAGGLER" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "apply-reconciliation: a proposal with one wrong citation is refused wholesale, bd state unchanged" {
  require_bd
  make_conflicted_fixture
  local bd_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"

  write_valid_proposal 1 "$RECON_STRAGGLER"
  # Poison ONE citation's text so it no longer matches what is really on
  # line 1 — the other claim's citation is left correct (D-03's trap: one
  # bad citation must still reject the WHOLE proposal).
  python3 - <<'PY'
import json
from pathlib import Path
p = Path(".cairn/conflicts.json")
data = json.loads(p.read_text())
data["claims"][0]["citations"][0]["text"] = \
    "this is definitely not what line 1 of ROADMAP.md says"
p.write_text(json.dumps(data))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 7 ]
  grep -qF "citation verification" <<<"$output"

  local bd_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  [ "$bd_before" = "$bd_after" ]
  run bd show "$RECON_STRAGGLER" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "apply-reconciliation: correct citations do not excuse a claim naming an id outside phase N, bd state unchanged" {
  require_bd
  make_conflicted_fixture
  local bd_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"

  # $DOC_P2 (make_doctor_fixture's phase-2 issue) carries no phase-1 label.
  # Every citation in this proposal is genuinely correct — the ONLY defect
  # is that the bd_close claim targets an issue outside the phase being
  # reconciled.
  write_valid_proposal 1 "$DOC_P2"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 7 ]
  grep -qF "issue-provenance" <<<"$output"
  grep -qF "carries no phase-1 label" <<<"$output"

  local bd_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  [ "$bd_before" = "$bd_after" ]
  run bd show "$DOC_P2" --json
  assert_json_eq "$output" '.[0].status' 'open'
}

@test "apply-reconciliation: every claim is enumerated in output BEFORE the first bd write happens" {
  require_bd
  make_conflicted_fixture
  write_valid_proposal 1 "$RECON_STRAGGLER"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 0 ]
  # Both claims — the bd_close AND the manual_review — appear in the
  # enumeration.
  grep -qF "will close $RECON_STRAGGLER" <<<"$output"
  grep -qF "skipped (manual review" <<<"$output"

  # ...and BOTH enumerated lines precede the first bd 'closed' confirmation
  # line: the FULL plan prints before the first write, never interleaved
  # enumerate-then-apply-then-enumerate-next.
  local enum_line1 enum_line2 close_line
  enum_line1="$(grep -nF "will close $RECON_STRAGGLER" <<<"$output" | head -1 | cut -d: -f1)"
  enum_line2="$(grep -nF "skipped (manual review" <<<"$output" | head -1 | cut -d: -f1)"
  close_line="$(grep -nF "closed $RECON_STRAGGLER —" <<<"$output" | head -1 | cut -d: -f1)"
  [ -n "$close_line" ]
  [ "$enum_line1" -lt "$close_line" ]
  [ "$enum_line2" -lt "$close_line" ]
}

@test "apply-reconciliation: a valid fresh proposal actually closes the bd_close issue; manual_review never touches bd" {
  require_bd
  make_conflicted_fixture
  write_valid_proposal 1 "$RECON_STRAGGLER"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 0 ]
  grep -qF "1 applied, 1 skipped (manual review), 0 refused by bd" <<<"$output"

  run bd show "$RECON_STRAGGLER" --json
  assert_json_eq "$output" '.[0].status' 'closed'
}

@test "apply-reconciliation: an unrecognized recommended_action.type refuses the WHOLE apply, bd state unchanged" {
  require_bd
  make_conflicted_fixture
  local bd_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"

  write_valid_proposal 1 "$RECON_STRAGGLER"
  # Corrupt the SECOND claim's type to something outside the closed
  # vocabulary — the FIRST claim is a perfectly valid bd_close, proving one
  # bad claim refuses the whole proposal, never just its own.
  python3 - <<'PY'
import json
from pathlib import Path
p = Path(".cairn/conflicts.json")
data = json.loads(p.read_text())
data["claims"][1]["recommended_action"]["type"] = "bd_delete"
p.write_text(json.dumps(data))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --apply-reconciliation 1
  [ "$status" -eq 7 ]
  grep -qF "unrecognized recommended_action.type" <<<"$output"

  local bd_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  [ "$bd_before" = "$bd_after" ]
  run bd show "$RECON_STRAGGLER" --json
  assert_json_eq "$output" '.[0].status' 'open'
}


#-----------------------------------------------------------------------------
# release-versions (check 15, REL-02) — 19-01
#-----------------------------------------------------------------------------

# Write cairn's own version carriers into the fixture at their REAL paths and
# REAL key paths — plugin.json's top-level `version`, marketplace.json's
# NESTED `metadata.version`, the CHANGELOG's first released heading,
# capability.json's own axis. $1 = lockstep version, $2 = the marketplace
# version (default: the same, i.e. agreement).
write_release_carriers() {
  local version="$1" market="${2:-$1}"
  mkdir -p cairn/.claude-plugin .claude-plugin cairn/capability
  printf '{"name": "cairn", "version": "%s"}\n' "$version" \
    > cairn/.claude-plugin/plugin.json
  printf '{"name": "cairngo", "metadata": {"version": "%s"}, "plugins": []}\n' \
    "$market" > .claude-plugin/marketplace.json
  printf '{"id": "cairn", "version": "1.0.0"}\n' \
    > cairn/capability/capability.json
  cat > CHANGELOG.md <<EOF
# Changelog

## [$version] - 2026-08-01

### Added

- fixture entry
EOF
}

# Break: make the absence of the plugin manifests a failure. Red here — and it
# would have turned every user's doctor red too, since no wired repo carries
# cairn's own manifests.
@test "release-versions: a repo without cairn's plugin manifests is out-of-scope, never a failure and never incomplete" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # Was `ok` with the words "not applicable" buried in the prose; 23-02 moved
  # them into the field. The exact value, never a negation.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .status' 'not-applicable'
  # Break, and it is the one that would hurt every user of cairn: marking this
  # `no-input`. The manifests will NEVER exist in a wired repo, so calling it
  # a gap would leave every user repo permanently INCOMPLETE — a false red
  # traded for a false green, which is the same defect mirrored.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .scope' 'out-of-scope'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .items | length' '0'
  assert_json_eq "$output" '.ok' 'true'
}

# Break: register the check as `warn`, or forget to add it to the `checks`
# list at all — red in both cases (warn never reaches exit 7; an absent check
# never appears in the report).
@test "release-versions: a diverging carrier fails the check and takes the doctor to exit 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  # First: the carriers agree, so the check is ok and the doctor still exits 0.
  write_release_carriers 1.5.0
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .detail' \
    'every version carrier agrees on 1.5.0, git tag v1.5.0 pending'

  # Then the third carrier drifts — the exact drift that shipped three times.
  write_release_carriers 1.5.0 1.4.2
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="release-versions") | .status' 'fail'
  assert_json_eq "$output" '.ok' 'false'
  grep -qF "metadata.version" <<<"$output"
  grep -qF "1.4.2" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ release-versions" <<<"$output"
}

#-----------------------------------------------------------------------------
# test-parallel (check 16, AUTO-04) — 29-06
#
# The environment dimension is controlled through BATS' OWN seam,
# BATS_PARALLEL_BINARY_NAME (bats-exec-suite:8), rather than by rebuilding
# PATH: it is the same variable bats itself reads to decide which binary to
# fan out through, so pointing it at something that exists (or does not) asks
# the check exactly the question bats would ask. Rebuilding PATH would also
# have to keep bd, git and python3 reachable, which is a lot of machinery for
# a question with a one-variable answer.
#
# The two branches that do NOT depend on this machine (no bats at all; the
# report itself unavailable) go through the CAIRN_TEST seam with a stub
# reporter, the same way the release check is driven through CAIRN_RELEASE.
#-----------------------------------------------------------------------------

# Break: drop the applicability guard. Red here — and it would put a warning
# about GNU parallel in front of every user of a wired repo, about a bats
# suite they do not have.
@test "test-parallel: a repo without cairn's plugin manifest is out-of-scope, and the report stays complete" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'not-applicable'
  # Same break as check 15's guard: `no-input` here would make every wired
  # repo read INCOMPLETE forever over a bats suite it does not have.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .scope' 'out-of-scope'
  assert_json_eq "$output" '.ok' 'true'
}

@test "test-parallel: with the prerequisites present the check is ok and names the job count" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The FULL set of carriers, not just plugin.json: that file is also check
  # 15's applicability marker, so writing it alone turns release-versions on
  # with nothing to agree with and takes the doctor to exit 7 for an
  # unrelated reason.
  write_release_carriers 1.5.0

  # `bash` stands in for the parallel binary: it exists on every machine this
  # suite runs on, so the ok branch is asserted deterministically instead of
  # depending on whether the developer happens to have GNU parallel.
  run env BATS_PARALLEL_BINARY_NAME=bash \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .detail | contains("bats -j")' 'true'
}

@test "test-parallel: a missing parallel binary warns with the fix and the measured cost, and the doctor still exits 0" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The FULL set of carriers, not just plugin.json: that file is also check
  # 15's applicability marker, so writing it alone turns release-versions on
  # with nothing to agree with and takes the doctor to exit 7 for an
  # unrelated reason.
  write_release_carriers 1.5.0

  run env BATS_PARALLEL_BINARY_NAME=this-binary-does-not-exist \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # Break, and it is the expensive one: turning friction into a blockage.
  # A slow suite is not a state inconsistency, and spending exit 7 on it
  # teaches everyone to ignore exit 7.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'warn'
  assert_json_eq "$output" '.ok' 'true'
  # Break: a warning that names neither the cost nor the cure.
  grep -qF "install parallel" <<<"$output"
  grep -qF "64s serial" <<<"$output"

  run env BATS_PARALLEL_BINARY_NAME=this-binary-does-not-exist \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⚠ test-parallel" <<<"$output"
}

@test "test-parallel: no bats at all is not-applicable/no-input, a different sentence than 'it will be slow'" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The FULL set of carriers, not just plugin.json: that file is also check
  # 15's applicability marker, so writing it alone turns release-versions on
  # with nothing to agree with and takes the doctor to exit 7 for an
  # unrelated reason.
  write_release_carriers 1.5.0

  local stub="$BATS_TEST_TMPDIR/no-bats-report.py"
  cat > "$stub" <<'PY'
import json
print(json.dumps({"bats": None, "jobs": 8, "jobs_source": "cpu count",
                  "parallel_binary": "parallel", "can_parallelize": True,
                  "blockers": [], "measured_cost": "n/a"}))
PY

  run env CAIRN_TEST="$stub" bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # Break: keep the `warn` 29-06 left here with a comment saying this branch
  # belongs to phase 23. Nothing about parallelism was concluded, so `warn`
  # ("it will be slow") states a fact the check never established.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'not-applicable'
  # `no-input`, NOT `out-of-scope`: the manifest guard above already proved we
  # are inside cairn's own tree, where the suite exists and should be runnable.
  # A missing tool is a gap someone can close, so it DOES make the report
  # incomplete — while still never touching the exit code.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .scope' 'no-input'
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.failed' 'false'
  # Break: routing "no bats" into the slow-suite branch. can_parallelize is
  # true in this report, so a check that looked at that field first would
  # report ok on a machine that cannot run the suite at all.
  grep -qF "cannot run here at all" <<<"$output"
}

@test "test-parallel: an unusable environment report degrades to warn, never a crash and never a failure" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # The FULL set of carriers, not just plugin.json: that file is also check
  # 15's applicability marker, so writing it alone turns release-versions on
  # with nothing to agree with and takes the doctor to exit 7 for an
  # unrelated reason.
  write_release_carriers 1.5.0

  local stub="$BATS_TEST_TMPDIR/broken-report.py"
  printf 'import sys\nsys.stderr.write("boom\\n")\nsys.exit(1)\n' > "$stub"

  run env CAIRN_TEST="$stub" bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # Break: letting one check's subprocess failure take the whole doctor down,
  # or promoting it to fail. The other fifteen checks still have answers.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="test-parallel") | .status' 'warn'
  grep -qF "exited 1" <<<"$output"
}

#-----------------------------------------------------------------------------
# req-ledger (check 17, AUTO-07) — 29-07
#
# The chain nobody was validating: an active requirement has a coverage row,
# the row count is the number the footer claims, each phase's
# `**Requirements**:` line actually yields its ids, and a plan whose SUMMARY
# is on disk has its checkbox ticked.
#
# EVERY status assertion below is on the EXACT value (`fail`, `ok`, `warn`),
# never on "is not ok". The negation is satisfied by `warn`, and `warn` is
# precisely the wrong state this check can fall into by accident: the
# neighbouring defensive shell-out allowlists returncodes (0, 5), and
# cairn-bookkeep.py reconcile spends 3 on the very disagreement this check
# exists to report. Copied unchanged, the central case would land in the
# "tool unavailable" branch, return `warn`, and leave the doctor exiting 0 —
# a check against false green producing false green, passed by a test that
# could not tell.
#
# The ledger itself is never re-parsed here or in the doctor: cairn-bookkeep.py
# owns that reading, and these tests drive it through the CAIRN_BOOKKEEP seam
# the same way the release check is driven through CAIRN_RELEASE.
#-----------------------------------------------------------------------------

# Insert LINE immediately before the first line starting with MARKER.
# Appending to REQUIREMENTS.md instead lands the item under `## Traceability`,
# where it is not an active requirement at all and the fixture proves nothing.
req_insert_before() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
lines = p.read_text().splitlines()
i = next(j for j, l in enumerate(lines) if l.startswith(sys.argv[2]))
lines.insert(i, sys.argv[3])
p.write_text("\n".join(lines) + "\n")
PY
}

# Write `N requirements, M mapped.` as the coverage footer: a WHOLE line
# directly after the last table row. cairn-bookkeep.py locates the footer by
# POSITION, never by searching the file for its text.
add_coverage_footer() {
  python3 - "$1" "$2" <<'PY'
import re
import sys
from pathlib import Path
p = Path(".planning/REQUIREMENTS.md")
lines = p.read_text().splitlines()
last = max(i for i, l in enumerate(lines) if re.match(r"^\|\s*[A-Za-z]", l))
lines.insert(last + 1, f"{sys.argv[1]} requirements, {sys.argv[2]} mapped.")
p.write_text("\n".join(lines) + "\n")
PY
}

# Turn phase 1's readable `**Requirements**: [AUTH-01, AUTH-02]` into the
# ellipsis this repo's ROADMAP.md:400 actually carries.
elide_requirements_line() {
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/ROADMAP.md")
p.write_text(p.read_text().replace(
    "**Requirements**: [AUTH-01, AUTH-02]",
    "**Requirements**: AUTH-01 … AUTH-02"))
PY
}

# Give phase 2 a SUMMARY on disk while its plan checkbox still reads `- [ ]`.
# The GSD fixture writes plan items in the prose dialect (`- [ ] 02-01:
# title`); the derived-5 link reads the filename dialect this repo's own
# ROADMAP uses, the only one that names a file to look for on disk. The
# STATE counter is bumped along with it so the ONE finding under test is the
# checkbox, not a progress number riding on the same edit.
stale_plan_checkbox() {
  python3 - <<'PY'
from pathlib import Path
road = Path(".planning/ROADMAP.md")
road.write_text(road.read_text().replace(
    "- [ ] 02-01: Add rate limiting middleware",
    "- [ ] 02-01-PLAN.md — Add rate limiting middleware"))
state = Path(".planning/STATE.md")
state.write_text(state.read_text().replace(
    "  completed_plans: 1", "  completed_plans: 2"))
Path(".planning/phases/02-api/02-01-SUMMARY.md").write_text(
    "---\nphase: 02-api\nplan: '01'\nstatus: complete\n---\n\nDone.\n")
PY
}

# A stand-in for cairn-bookkeep.py that prints PAYLOAD and exits CODE — the
# only way to ask this check what it does with an exit code the real script
# does not produce today.
#
# The payload rides in a sibling file rather than being quoted into the stub's
# source: embedding JSON in Python in bash needs three levels of escaping to
# agree, and the first version of this helper got it wrong silently.
write_bookkeep_stub() {
  local path="$1" code="$2" payload="$3"
  printf '%s' "$payload" > "$path.payload"
  {
    printf 'import sys\n'
    printf 'sys.stdout.write(open("%s.payload").read())\n' "$path"
    printf 'sys.exit(%s)\n' "$code"
  } > "$path"
}

# Break: skip the first link. Red — AUTO-07's whole point is that an active
# requirement with no row went unnoticed for days.
@test "req-ledger: an active requirement with no coverage row fails and names the id" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  req_insert_before .planning/REQUIREMENTS.md "## Traceability" \
    "- [ ] **API-02**: Public API exposes a health endpoint"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  assert_json_eq "$output" '.ok' 'false'
  grep -qF "API-02" <<<"$output"
  grep -qF "no row in the coverage table" <<<"$output"
  # The finding routes to the command that resolves it.
  grep -qF "cairn-bookkeep.sh reconcile --apply" <<<"$output"
}

# Break: skip the second link — the one nobody thinks to write, because the
# footer "is only prose". It is the line that read 29 while the table held 33.
@test "req-ledger: a footer claiming another number fails and names both numbers" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  add_coverage_footer 9 9

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "9 requirements, 9 mapped." <<<"$output"
  grep -qF "it claims 9 active requirement(s) / 9 coverage row(s)" <<<"$output"
  grep -qF "the ledger holds 3 active requirement(s) / 3 coverage row(s)" \
    <<<"$output"
}

# Break: inherit the blind spot that has check 1 report `ok :: 29
# requirement(s) mapped` against 35 active requirements.
@test "req-ledger: an elided **Requirements**: line fails, naming the phase and the ids parsed" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  elide_requirements_line

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "Phase 1:" <<<"$output"
  grep -qF "ellipsis-between-ids" <<<"$output"
  grep -qF "does not yield the ids the ledger assigns it" <<<"$output"

  # The raw line and the ids the parser actually got, asserted on the HUMAN
  # report: json.dumps escapes the ellipsis to …, so a grep for it
  # against --json passes or fails for a reason that has nothing to do with
  # this check.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ req-ledger" <<<"$output"
  grep -qF "**Requirements**: AUTH-01 … AUTH-02" <<<"$output"
  grep -qF "parsed ['AUTH-01', 'AUTH-02']" <<<"$output"
}

# Break: leave the view 29-02 taught the bookkeeper to WRITE without a reader.
@test "req-ledger: a plan with its SUMMARY on disk and an unticked checkbox fails, naming the plan" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  stale_plan_checkbox

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "02-01-PLAN.md" <<<"$output"
  grep -qF "02-01-SUMMARY.md is on disk" <<<"$output"
}

# Break: a check that fails on everything would "catch" every test above and
# be worth nothing. This is the one that proves it can say yes.
@test "req-ledger: a coherent ledger reads ok and counts what it checked" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .items | length' '0'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .detail' \
    'every requirement-ledger link agrees — 3 active requirement(s) against 3 coverage row(s), 0 excluded by rule (deferred / out of scope)'
}

# Break: count a deferred requirement as a gap. The doctor fills with noise
# about requirements deliberately outside the table, and gets ignored.
@test "req-ledger: a deferred requirement outside the table is ok, and the count is explained" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  printf '\n## Deferred (v2)\n\n- **API-09**: Webhook fanout\n' \
    >> .planning/REQUIREMENTS.md

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'ok'
  grep -qF "1 excluded by rule (deferred / out of scope)" <<<"$output"
}

# Break: the wide `except` that returns ok, AND the `warn` verdict that
# satisfies "is not ok" while leaving the doctor at exit 0. Both are red here.
@test "req-ledger: cairn-bookkeep.py out of place is exactly fail, and the doctor exits 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run env CAIRN_BOOKKEEP="$BATS_TEST_TMPDIR/no-such-bookkeep.py" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "the requirement ledger could not be read" <<<"$output"
}

# Break: copy check 11's allowlist `(0, 5)` unchanged. Exit 3 — the ONLY
# verdict this check exists to report — would land in the unavailable branch
# and the doctor would exit 0 over a ledger it was just told disagrees.
@test "req-ledger: exit 3 with a valid report is a reading, not an unavailability (the (0, 3) allowlist)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-disagrees.py"
  write_bookkeep_stub "$stub" 3 '{"coverage": {"rows": 3}, "requirements": {"active": ["A-01", "A-02", "A-03"], "deferred": [], "out_of_scope": []}, "disagreements": [{"kind": "coverage-row-missing", "subject": "A-03", "found": null, "expected": "a coverage table row", "source": "REQUIREMENTS.md:9"}]}'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "A-03" <<<"$output"
  # The reading happened: the census is a parsed report, not an error string.
  grep -qF "3 active requirement(s) against 3 coverage row(s)" <<<"$output"
  refute_in_output "could not be read"
}

# Break: any defensive branch that returns `warn`. cairn-doctor.py's own
# exit-code table records that a warning never changes the exit code, so a
# warn here is a doctor approving a ledger nobody managed to read.
@test "req-ledger: an exit outside the allowlist is fail, never warn" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-boom.py"
  write_bookkeep_stub "$stub" 4 'boom'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "exited 4" <<<"$output"
}

# Break: return `fail` on unparsable output only when it is empty, or degrade
# to warn the way the checks around it legitimately do.
@test "req-ledger: an unparsable report is fail, and the doctor exits 7" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-garbage.py"
  write_bookkeep_stub "$stub" 0 'not json at all'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'fail'
  grep -qF "invalid JSON" <<<"$output"
}

# Break: fail a repo that keeps no coverage view. Every user's roadmap without
# a coverage table would go to exit 7 over a table that has no business being
# there — the trap check 15 documents, one check over.
@test "req-ledger: a roadmap with no coverage view is out-of-scope, never a failure and never incomplete" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-no-view.py"
  write_bookkeep_stub "$stub" 3 '{"coverage": {"rows": 0}, "requirements": {"active": [], "deferred": [], "out_of_scope": []}, "disagreements": [{"kind": "coverage-view-missing", "subject": "coverage table", "found": null, "expected": "a coverage table", "source": "ROADMAP.md"}]}'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'not-applicable'
  # Break: calling this a gap. Keeping no coverage view is a METHOD choice a
  # project is entitled to make — the comment on REQ_LEDGER_VOID_KIND says so
  # — and marking it `no-input` would make every such repo read INCOMPLETE
  # forever over a table it deliberately does not keep.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .scope' 'out-of-scope'
  assert_json_eq "$output" '.ok' 'true'
  grep -qF "no coverage view" <<<"$output"
}

# Break: convert this guard and leave it unproved. It is the branch a repo
# that keeps no REQUIREMENTS.md at all lands on, and before 23-02 no test
# touched it — a promotion nobody proves is a promotion nobody notices
# regressing.
@test "req-ledger: a .planning/ with no REQUIREMENTS.md is out-of-scope, never a failure" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  rm .planning/REQUIREMENTS.md

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .scope' 'out-of-scope'
  # It still names WHAT is missing — the routing survives the promotion.
  grep -qF "REQUIREMENTS.md" <<<"$output"
}

# Break: silently drop a disagreement this check does not claim. An
# unexplained absence is the defect the phase removes; so is spending exit 7
# on `state-narrative-stale`, free text reconcile itself declines to rewrite.
@test "req-ledger: a disagreement outside its links is surfaced as warn, never exit 7 and never dropped" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  local stub="$BATS_TEST_TMPDIR/bookkeep-aside.py"
  write_bookkeep_stub "$stub" 3 '{"coverage": {"rows": 3}, "requirements": {"active": ["A-01", "A-02", "A-03"], "deferred": [], "out_of_scope": []}, "disagreements": [{"kind": "state-narrative-stale", "subject": "last_activity_desc", "found": "old prose", "expected": {"fase": 2}, "source": "STATE.md"}]}'

  run env CAIRN_BOOKKEEP="$stub" \
    bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="req-ledger") | .status' 'warn'
  grep -qF "last_activity_desc" <<<"$output"
  grep -qF "outside req-ledger's own links" <<<"$output"
}

# Break: write the function and forget to add it to main()'s `checks` list —
# the quietest way for a new check not to exist, and the one no test that
# calls the function directly would ever catch.
@test "req-ledger: the check is registered and reported in --json" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.checks[].id] | index("req-ledger") != null' \
    'true'
}

#-----------------------------------------------------------------------------
# claims-stale with no input (check 8, AUTO-08's mechanical half) — 29-07
#
# The purest specimen of the defect this phase removes, measured 2026-08-04
# in cairn's own repo: `✓ claims-stale  skipped — no active_phase in
# STATE.md` — a check that had never run once in the project's life, wearing
# the success marker. The verdict changes; the DIALECT does not. Which key
# STATE.md should carry (`current_phase`, what GSD writes, or `active_phase`,
# what cairn reads) is a business rule open in CairnGo-rq0, and no test here
# takes a side.
#-----------------------------------------------------------------------------

# Remove the frontmatter key entirely — the state of every repo whose
# STATE.md was written by GSD.
drop_state_active_phase() {
  python3 - <<'PY'
import re
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(re.sub(r'^active_phase: ".*?"\n', "", p.read_text(),
                    flags=re.MULTILINE))
PY
}

# Break (three times over): keep the `ok` — the state of this check before
# 29-07 — or keep the `warn` 29-07 left as a placeholder for this phase, or
# promote a missing input to a blocking failure. This branch is the tracer
# slice: STATE.md IS here, so the key it lacks is a GAP, not a repo the check
# has no business running in — hence no-input, and hence `.ok` false.
@test "claims-stale: no active_phase is not-applicable/no-input, routes, and never blocks" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  drop_state_active_phase

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # A check with no input is friction, not a state inconsistency: exit 7
  # spent on friction stops meaning anything. The verdict moved where it is
  # READ, not where it decides to block.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.failed' 'false'
  # The health key can no longer be true while a check inside the doctor's
  # remit never received its input.
  assert_json_eq "$output" '.ok' 'false'
  # The exact value, never "is not ok": the old verdict WAS ok, then warn,
  # and a negation would also accept a fail that has no business being one.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .scope' 'no-input'
  grep -qF "cannot check" <<<"$output"
  grep -qF "active_phase" <<<"$output"
  grep -qF "CairnGo-rq0" <<<"$output"
  # The finding routes: it names the surfaces that read the key.
  grep -qF "cairn-lease.py" <<<"$output"
  grep -qF "hooks/session-start.sh" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "⊘ claims-stale" <<<"$output"
  refute_in_output "✓ claims-stale"
  refute_in_output "⚠ claims-stale"
  # The footer says the report is incomplete without saying anything failed.
  grep -qF "[cairn-doctor] INCOMPLETE" <<<"$output"
  refute_in_output "[cairn-doctor] FAIL"
}

# Break: a branch that never returns ok makes the check lie in the other
# direction. This is the first proof in this project that it approves when it
# actually has something to compare.
@test "claims-stale: with active_phase present the check really runs and returns ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  # The fixture ships active_phase: "2"; DOC_P2 is the phase-2 issue, so an
  # in_progress claim on it is INSIDE the active phase and must not flag.
  bd update "$DOC_P2" --status in_progress --assignee tester >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .detail' \
    'no assigned in_progress issues outside phase 2'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .items | length' '0'
}

# Break: delete the check instead of fixing its verdict — the lazy way out,
# and the one the id list catches.
@test "claims-stale: no verdict change removes a check from the report" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  drop_state_active_phase

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # 23 since check 22, issues-recoverable (2026-08-07) — see the long note on
  # the same
  # assertion near the top of this file for why the merge, and not either
  # branch, is what made this literal wrong once, and why BOTH sites are
  # edited in one change.
  assert_json_eq "$output" '.checks | length' '24'
  assert_json_eq "$output" '[.checks[].id] | index("claims-stale") != null' \
    'true'
}

# ─── check 20, plan-counters (CairnGo-6bx, phase 25 criterion 6) ─────────────
#
# MEASURED 2026-08-06, right after the close of phase 22:
#
#   .planning/STATE.md          on disk
#   total_plans:     39         NN-MM-PLAN.md ...... 39
#   completed_plans: 47   <---  NN-MM-SUMMARY.md ... 39
#   percent:         91         NN-SUMMARY.md ....... 8     47 = 39 + 8
#
# `cairn-bookkeep reconcile` returned `disagreements: []` over that file while
# printing both contradictory numbers inside the SAME JSON object: writer and
# verifier derive completed_plans with one rule, so they agree. This check
# exists because it does NOT recompute — `completed > total` is impossible by
# arithmetic and needs nothing from either glob.

# Set STATE.md's two plan counters to COMPLETED ($1) of TOTAL ($2).
set_state_plan_counters() {
  COMPLETED="$1" TOTAL="$2" python3 - <<'PY'
import os
import re
from pathlib import Path
p = Path(".planning/STATE.md")
t = p.read_text()
t = re.sub(r"^(\s*)total_plans:.*$",
           lambda m: f"{m.group(1)}total_plans: {os.environ['TOTAL']}",
           t, count=1, flags=re.MULTILINE)
t = re.sub(r"^(\s*)completed_plans:.*$",
           lambda m: f"{m.group(1)}completed_plans: {os.environ['COMPLETED']}",
           t, count=1, flags=re.MULTILINE)
p.write_text(t)
PY
}

@test "plan-counters fails a STATE.md claiming more plans done than exist" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  set_state_plan_counters 47 39

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="plan-counters") | .status][0]' 'fail'
  # Both numbers reach the operator: a finding that says "the counters
  # disagree" without saying which two numbers is not actionable.
  printf '%s' "$output" | jq -r \
    '[.checks[] | select(.id=="plan-counters") | .items[]][0]' \
    | grep -qF '47'
  printf '%s' "$output" | jq -r \
    '[.checks[] | select(.id=="plan-counters") | .items[]][0]' \
    | grep -qF '39'
}

@test "plan-counters passes a STATE.md whose two numbers are possible" {
  # The negative half. Without it, "always fail" would pass the test above,
  # and this check runs on every doctor invocation in every repository.
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  set_state_plan_counters 39 39

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="plan-counters") | .status][0]' 'ok'
}

@test "plan-counters reports no input, never ok, when STATE.md has no counters" {
  # A missing `progress:` block is GSD's absence, not an inconsistency — and
  # saying `ok` over an input that never arrived is the shape phase 23 removed
  # from this file. The value asserted is the exact one, never the negation.
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  python3 - <<'PY'
import re
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(re.sub(r"^\s*(total_plans|completed_plans):.*\n", "",
                    p.read_text(), flags=re.MULTILINE))
PY

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="plan-counters") | .status][0]' 'not-applicable'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="plan-counters") | .scope][0]' 'no-input'
}

# Break: take a side on the dialect. Writing `active_phase` into STATE.md (or
# teaching any cairn surface to read `current_phase`) resolves the symptom by
# deciding a business rule that belongs to grooming, and it silently changes
# what every repo with a STATE.md already on disk means.
# The title was "…and never reads current_phase" until phase 25: check 21,
# state-dialect, now READS current_phase — to compare it, never to stand in
# for it. The abstention this test protects is claims-stale's, and it is
# unchanged: no synonym, no fallback, no second reader of one fact.
@test "claims-stale: the doctor never writes active_phase, and never takes current_phase as its synonym" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  drop_state_active_phase
  python3 - <<'PY'
from pathlib import Path
p = Path(".planning/STATE.md")
lines = p.read_text().splitlines(keepends=True)
lines.insert(1, 'current_phase: "2"\n')   # the dialect GSD actually writes
p.write_text("".join(lines))
PY
  cp .planning/STATE.md "$BATS_TEST_TMPDIR/state-before.md"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # current_phase is NOT adopted as a synonym: the check still has no input.
  # The value moved with 23-01 (warn -> not-applicable); the abstention this
  # test protects did not, and the assertion is still on the exact value.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .scope' 'no-input'
  # And STATE.md is byte-identical — the doctor is read-only about this.
  run diff "$BATS_TEST_TMPDIR/state-before.md" .planning/STATE.md
  [ "$status" -eq 0 ]
}

#-----------------------------------------------------------------------------
# LANG-02 (plan 24-03) — check 18, response-language: the net under the one
# step of the install flow that is prose.
#
# /cairn:init records the answer in .cairn/config.json (it must: when it asks,
# .planning/ does not exist and cairn is forbidden from creating it), and the
# propagation into .planning/config.json:response_language — the key GSD's own
# workflows read — fires when cairn-config.py `set` runs again after the
# /gsd:new-project hand-off. A step in prose is the thing that gets skipped,
# and that skip is invisible: nothing breaks, half the subagents just answer
# in the wrong language. That is what this check makes visible.
#
# Every assertion below is on the EXACT status value, never on a negation.
#-----------------------------------------------------------------------------

# Write .cairn/config.json's language ($1) and/or .planning/config.json's ($2).
# An empty argument means "leave that file without the key".
write_language_pair() {
  mkdir -p .cairn .planning
  if [ -n "$1" ]; then
    printf '{\n  "agents": {\n    "response_language": "%s"\n  }\n}\n' "$1" \
      > .cairn/config.json
  else
    printf '{}\n' > .cairn/config.json
  fi
  if [ -n "$2" ]; then
    printf '{\n  "response_language": "%s"\n}\n' "$2" > .planning/config.json
  else
    printf '{\n  "commit_docs": true\n}\n' > .planning/config.json
  fi
}

@test "response-language: the two files agreeing is ok, and says the language out loud" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  write_language_pair "Portuguese" "Portuguese"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="response-language") | .status' 'ok'
  # Breaks on a check that warns when everything is right — noise trains
  # people to stop reading the report.
  grep -qF "Portuguese" <<<"$output"
}

@test "response-language: an install answer that never reached GSD's config warns and names the exact command" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  write_language_pair "Portuguese" ""

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # THE case this check exists for: step 6 of /cairn:init skipped. Breaks if
  # the skip passes in silence, which is the whole defect.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="response-language") | .status' 'warn'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="response-language") | .items | length' '1'
  grep -qF "set agents.response_language 'Portuguese'" <<<"$output"

  # warn, not fail: a divergence breaks nothing mechanically, and spending
  # exit 7 on it would train everyone to ignore exit 7.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 0 ]
  grep -qF "response-language" <<<"$output"
}

@test "response-language: two different values warn, showing both and naming which one governs" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  write_language_pair "Portuguese" "Japanese"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="response-language") | .status' 'warn'
  # Both values shown, and the winner named: GSD's key governs, so leaving the
  # reader to guess would reproduce the confusion the check reports.
  grep -qF "'Japanese'" <<<"$output"
  grep -qF "'Portuguese'" <<<"$output"
  grep -qF "/gsd:config" <<<"$output"
}

@test "response-language: no recorded answer at all is ok, not a warning" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  write_language_pair "" ""

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # Breaks on a check that nags every repo that never ran /cairn:init's
  # language step — there is nothing to keep in agreement.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="response-language") | .status' 'ok'
}

@test "response-language: the doctor writes neither file, in any of the states" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  write_language_pair "Portuguese" "Japanese"
  cp .cairn/config.json "$BATS_TEST_TMPDIR/cairn-before.json"
  cp .planning/config.json "$BATS_TEST_TMPDIR/planning-before.json"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="response-language") | .status' 'warn'

  # The doctor reports; cairn-config.py set is what writes. Breaks on a check
  # that "helpfully" fixes the divergence it found.
  run diff "$BATS_TEST_TMPDIR/cairn-before.json" .cairn/config.json
  [ "$status" -eq 0 ]
  run diff "$BATS_TEST_TMPDIR/planning-before.json" .planning/config.json
  [ "$status" -eq 0 ]
}

# --------------------------------------------------------------------------- #
# Check 19, phase-landed (PR-04, phase 30) — a phase the roadmap calls complete
# whose work never entered the control branch.
#
# The doctor reads NO git for this. cairn-land.py owns every git read behind
# the question and the doctor invokes it through the CAIRN_LAND seam, the same
# shape checks 3 and 17 use for cairn-map.py and cairn-bookkeep.py. The last
# test in this block pins that: a stubbed CAIRN_LAND changes the verdict, which
# it could not do if the answer were re-derived here.
#
# Every assertion is on the exact status value. `!= "ok"` is satisfied by
# `warn`, by `fail` AND by `not-applicable`, which are four different
# instructions to whoever reads the report.
# --------------------------------------------------------------------------- #

# Commit the fixture and point a remote-tracking ref at it. `update-ref` writes
# exactly the ref a fetch would, so no remote and no network are involved.
land_commit_and_publish() {
  git add -A >/dev/null 2>&1 || true
  git commit -qm "feat(01-01): the auth phase" >/dev/null 2>&1
  git update-ref refs/remotes/origin/main "$(git rev-parse HEAD)"
}

@test "phase-landed: a complete phase on the control branch reads ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  land_commit_and_publish

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .items | length' '0'
}

@test "phase-landed: a complete phase ahead of the control branch warns" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  land_commit_and_publish
  # Phase 1's closing commit lands AFTER the control branch was published —
  # the shape of this whole repository today, and of anybody mid-cycle.
  git commit -q --allow-empty -m "chore(01): close phase 1" >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # WARN and not FAIL, and the exit code proves the distinction: unpushed work
  # is friction, and exit 7 spent on friction stops meaning anything.
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .status' 'warn'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .detail | test("/cairn:ship")' \
    'true'
  # The finding NAMES the phase and the branch — a warning that says only
  # "something did not land" is the silence this check exists to remove.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .items[0]
     | test("phase 1") and test("origin/main")' 'true'
}

@test "phase-landed: an ARCHIVED milestone's phase that never landed fails" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  land_commit_and_publish
  # A closed cycle, on disk, exactly the way /gsd:complete-milestone leaves it.
  mkdir -p .planning/milestones/v0.9-phases/03-legacy
  echo "# archived" > .planning/milestones/v0.9-ROADMAP.md
  git add -A >/dev/null
  git commit -qm "chore: archive v0.9" >/dev/null
  # ...and work attributed to phase 3 that the control branch does not have.
  # Attributed by SCOPE, because the archive moved the directory out of
  # .planning/phases/ — which is precisely the case the second attribution
  # source exists for.
  git commit -q --allow-empty -m "feat(03-01): the legacy phase" >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  # FAIL, and exit 7: this is not "I have not pushed yet", it is a cycle
  # CLOSED over work the control branch does not have.
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .status' 'fail'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .items[0] | test("ARCHIVED")' \
    'true'
  assert_json_eq "$output" '.failed' 'true'
}

@test "phase-landed: a complete phase the history cannot place raises nothing" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  # A history that names no phase in a scope AND never touched the phase
  # directory — so neither attribution source can place phase 1. This is the
  # shape of phases 7-12 of this repository, MEASURED 2026-08-06: archived from
  # cycles that predate the conventional-commit scope convention.
  echo readme > README.md
  git add README.md >/dev/null
  git commit -qm "initial import" >/dev/null
  git update-ref refs/remotes/origin/main "$(git rev-parse HEAD)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  # `ok`, on the exact value: an unplaceable phase is NAMED and not charged.
  # Charging it would hand every long-lived repo a permanent finding about
  # history nobody is going to rewrite — the false-red phase 23 refused.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .status' 'ok'
  # Named, though. Silence about it would be the opposite defect.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .items[0] | test("unknown ::")' \
    'true'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .items[0] | test("no-commits")' \
    'true'
}

@test "phase-landed: no control branch is out-of-scope, never a gap" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  git add -A >/dev/null 2>&1 || true
  git commit -qm "feat(01-01): the auth phase" >/dev/null 2>&1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .status' 'not-applicable'
  # out-of-scope, NOT no-input: a single-branch repo has nothing to compare
  # against permanently, and `no-input` would clear `.ok` and hand every one
  # of them an INCOMPLETE footer forever.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .scope' 'out-of-scope'
  assert_json_eq "$output" '.ok' 'true'
}

@test "phase-landed: a broken CAIRN_LAND degrades to warn, never to fail" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  land_commit_and_publish

  local stub="$BATS_TEST_TMPDIR/broken-land.py"
  printf '%s\n' 'import sys' 'sys.exit(9)' > "$stub"
  run env CAIRN_LAND="$stub" bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  refute_in_output "Traceback"
  # WARN and not FAIL: the doctor could not ask the question, which is not the
  # same as the answer being bad. Same degrade shape as check 11.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .status' 'warn'
  assert_json_eq "$output" '.failed' 'false'
}

@test "phase-landed: the verdict comes from cairn-land.py, not from git here" {
  # THE SEAM, pinned. A stub that answers a DIFFERENT verdict than the real
  # repository would changes the report — which it could not do if this check
  # re-read git itself. Breaks by: writing a `git merge-base` into
  # cairn-doctor.py, which is how one fact acquires a second answer.
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture
  land_commit_and_publish

  local stub="$BATS_TEST_TMPDIR/stub-land.py"
  cat > "$stub" <<'PY'
import json
print(json.dumps({
    "control": {"branches": ["origin/invented"], "source": "config",
                "detail": "stubbed"},
    "phases": {"1": {"status": "unlanded", "commits": 4, "sources": ["scope"],
                     "branches": {"origin/invented": "unlanded"},
                     "reason": None, "pr": {"status": "unknown"}}},
    "answered": True, "reason": None, "detail": "stubbed"}))
PY
  run env CAIRN_LAND="$stub" bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .status' 'warn'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .items[0]
     | test("origin/invented")' 'true'
  # And the real run of the same fixture reads `ok` — without this line the
  # assertion above would pass against a check that always warns.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="phase-landed") | .status' 'ok'
}

# ─── check 21, state-dialect (CairnGo-ctr, AUTO-10, phase 25 criterion 5) ────
#
# MEASURED 2026-08-05, reconfirmed 2026-08-07 in this checkout:
#
#   $ grep -rn current_phase cairn/     -> ZERO readers
#   $ grep -rln active_phase cairn/     -> cairn-status.py, cairn-doctor.py,
#                                          cairn-lease.py, cairn-migrate.py,
#                                          hooks/session-start.sh
#   $ sed -n 5p .planning/STATE.md      -> current_phase: 30   (no active_phase)
#
# cairn wrote the key nothing here reads. The owner decided (2026-08-06) to
# write BOTH, and made the comparison part of the decision: two keys that must
# agree and that nobody compares is this cycle's defect, measured four times.

# Replace the fixture's `active_phase: "N"` with `current_phase: N` — the
# frontmatter of every STATE.md GSD has ever written, and the state this repo
# was measured in on 2026-08-05.
speak_gsd_dialect_only() {
  python3 - <<'PY'
import re
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(re.sub(r'^active_phase: "(.*?)"$', r"current_phase: \1",
                    p.read_text(), flags=re.MULTILINE))
PY
}

# Add `current_phase: N` beside the fixture's own active_phase.
add_current_phase() {
  N="$1" python3 - <<'PY'
import os
import re
from pathlib import Path
p = Path(".planning/STATE.md")
p.write_text(re.sub(r'^(active_phase: ".*?")$',
                    lambda m: m.group(1) + "\ncurrent_phase: "
                    + os.environ["N"],
                    p.read_text(), count=1, flags=re.MULTILINE))
PY
}

# Break three ways: drop the check from the registry; compare the keys with a
# phase recomputed from the roadmap (which would agree with whichever key the
# same rule wrote, and never fail); or downgrade the disagreement to a warn,
# which is the false green this whole cycle removes.
@test "state-dialect: two keys naming two different phases is a FAIL that routes" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  add_current_phase 1     # the fixture's active_phase is "2"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" '.failed' 'true'
  # The exact value, never "is not ok": `warn` and `not-applicable` both
  # satisfy a negation, and both would be wrong here.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .status' 'fail'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .items[0]' \
    'current_phase 1 != active_phase 2'
  # It routes to the one command that owns both keys.
  grep -qF "cairn-bookkeep.sh close" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh"
  [ "$status" -eq 7 ]
  grep -qF "✗ state-dialect" <<<"$output"
}

# The negative half: without it, "always fails" would pass a check that runs
# on every doctor invocation in every repository.
@test "state-dialect: two keys naming the same phase is ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  add_current_phase 2     # agrees with the fixture's active_phase "2"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .detail' \
    "STATE.md's two phase keys agree on phase 2"
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | has("scope")' 'false'
}

# The assignment that had to be argued instead of measured, and the one a
# careless version gets wrong: ONE key is out-of-scope, never no-input.
#
# Break: return no-input here. Every GSD repository that has never run
# cairn-bookkeep — which is all of them, including this fixture — would get
# `.ok: false` forever, a permanent false red, and check 8 already reports the
# very same missing key as its own no-input. One gap, counted once.
@test "state-dialect: one key only is out-of-scope, and never a gap" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  # The fixture as it ships: active_phase and no current_phase.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .scope' 'out-of-scope'
  assert_json_eq "$output" '.ok' 'true'

  # And the mirror image — the dialect every GSD STATE.md speaks.
  speak_gsd_dialect_only
  ! grep -qF "active_phase" "$PWD/.planning/STATE.md"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .scope' 'out-of-scope'
  # `.ok` is false here — but because of check 8's no-input on the missing
  # active_phase, not because of this one. Asserted at the check, so the two
  # verdicts cannot be confused for each other.
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .scope' 'no-input'
}

# THE CRITERION, END TO END, and the only test here that drives both halves of
# AUTO-10 in one run: a STATE.md in the GSD dialect, the check that has never
# once run in this project's life reporting no input over it, cairn-bookkeep
# writing the key cairn reads, and the same check running afterwards.
#
# Break: revert STATE_KEYS_WRITTEN or the anchor condition in build_plan and
# the second half of this test goes back to no-input — which is exactly the
# measurement of 2026-08-05.
@test "AUTO-10: close --apply lands active_phase, and claims-stale stops reporting no input" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_doctor_fixture

  speak_gsd_dialect_only
  grep -qF "current_phase: 2" "$PWD/.planning/STATE.md"
  ! grep -qF "active_phase" "$PWD/.planning/STATE.md"

  # Before: the measured false green's successor — a check with no input.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .status' 'not-applicable'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .scope' 'no-input'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-bookkeep.sh" close 2 --apply \
    --no-tracker --planning-dir "$PWD/.planning"
  [ "$status" -eq 0 ]

  # The key cairn reads is in the file, beside the key GSD writes, naming the
  # same phase — so check 21 has something to compare and agrees.
  grep -qF "current_phase: 2" "$PWD/.planning/STATE.md"
  grep -qF "active_phase: 2" "$PWD/.planning/STATE.md"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | .status' 'ok'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="claims-stale") | has("scope")' 'false'
  assert_json_eq "$output" \
    '.checks[] | select(.id=="state-dialect") | .status' 'ok'
}

# ─── check 22, issues-recoverable (2026-08-07) ──────────────────────────────
#
# The check was born from a measurement on this repository, not from a
# hypothetical: `.beads/embeddeddolt` was 27 MB inside .gitignore,
# `.beads/issues.jsonl` did not exist, `.beads/backup/` was 13 MB and also
# ignored, and the remote carried 0 refs/dolt out of 42 refs. A clean clone
# recovered NONE of the 176 issues — while CLAUDE.md:25 had been stating in
# writing, for weeks, that the sync used refs/dolt/data and that the JSONL was
# a passive export.
#
# The rung that matters is FAIL, and these tests build the exact shape that
# produced it rather than a simplified stand-in.

@test "issues-recoverable: no export and no promise is friction, never a failure" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  # make_bd_fixture now models a wired repo and commits an export, so a test
  # about the ABSENCE of one has to undo that in the open. Explicit beats a
  # fixture that quietly stopped producing the shape under test.
  git rm -q --cached .beads/issues.jsonl >/dev/null 2>&1
  git -c user.email=t@t -c user.name=t commit -q -m "untrack export" >/dev/null 2>&1
  # A repository that just ran `bd init` has issues and no export, and that is
  # NOT broken — it is young. The first version of this check called it `fail`
  # and turned 62 of this file's 123 tests red in one commit, because every
  # fixture is exactly this shape. Phase 23 wrote the rule it broke (D-07): no
  # fix may change the verdict of a path that is legitimately green today.
  run git ls-files -- .beads
  ! grep -qF "issues.jsonl" <<<"$output"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="issues-recoverable")] | .[0].status' 'warn'
  # The detail must say the consequence, not the symptom.
  run bash -c "bash '$CAIRN_SCRIPTS_DIR/cairn-doctor.sh' --json | jq -r '[.checks[] | select(.id==\"issues-recoverable\")] | .[0].detail'"
  grep -qF "recovers NONE" <<<"$output"
}

@test "issues-recoverable: a promise the artifact does not keep is a failure" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  # make_bd_fixture now models a wired repo and commits an export, so a test
  # about the ABSENCE of one has to undo that in the open. Explicit beats a
  # fixture that quietly stopped producing the shape under test.
  git rm -q --cached .beads/issues.jsonl >/dev/null 2>&1
  git -c user.email=t@t -c user.name=t commit -q -m "untrack export" >/dev/null 2>&1
  # THE SHAPE MEASURED ON 2026-08-07, and the only one that earns exit 7: the
  # configuration states an export is produced and git carries none. That is
  # not a young repository, it is two sources disagreeing about whether the
  # issues can be recovered — which is the thing this whole tool exists to
  # name. On the real repository the promise lived in CLAUDE.md instead of the
  # config; a check cannot read prose, so it reads the claim bd itself makes.
  bd config set export.auto true >/dev/null 2>&1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="issues-recoverable")] | .[0].status' 'fail'
  run bash -c "bash '$CAIRN_SCRIPTS_DIR/cairn-doctor.sh' --json | jq -r '[.checks[] | select(.id==\"issues-recoverable\")] | .[0].detail'"
  grep -qF "CONFIG SAYS OTHERWISE" <<<"$output"
}

@test "issues-recoverable: a tracked export covering the store is ok" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"

  # The export comes from make_bd_fixture, which models a wired repo. Doing it
  # again here would fail on "nothing to commit" — the fixture already did it.

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="issues-recoverable")] | .[0].status' 'ok'
}

@test "issues-recoverable: an export behind the store warns, and never fails" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"

  # The export comes from make_bd_fixture, which models a wired repo. Doing it
  # again here would fail on "nothing to commit" — the fixture already did it.
  # An issue created after the export is exactly the ordinary staleness this
  # rung exists for. It is WARN and not FAIL because a stale export still
  # recovers most of the history, and spending exit 7 on lag is how exit 7
  # stops meaning anything.
  bd create "born after the export" -t task -p 4 --silent >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="issues-recoverable")] | .[0].status' 'warn'
  # A warning never counts as a failure — the vocabulary rule phase 23 settled.
  # Asserted on the BUCKET and not on the process exit, because other checks in
  # this fixture fail on their own and would make the exit code say nothing
  # about this one.
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="issues-recoverable" and .status=="fail")] | length' '0'
}

@test "issues-recoverable: it reads what git TRACKS, never what is on disk" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  # make_bd_fixture now models a wired repo and commits an export, so a test
  # about the ABSENCE of one has to undo that in the open. Explicit beats a
  # fixture that quietly stopped producing the shape under test.
  git rm -q --cached .beads/issues.jsonl >/dev/null 2>&1
  git -c user.email=t@t -c user.name=t commit -q -m "untrack export" >/dev/null 2>&1

  # The whole defect in one assertion: the file is present, complete, and
  # correct on disk, and git does not carry it. Reading the directory would
  # call this recoverable; reading git does not.
  bd export --all -o .beads/issues.jsonl >/dev/null 2>&1
  [ -s .beads/issues.jsonl ]

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="issues-recoverable")] | .[0].status' 'warn'
}

@test "issues-recoverable: the audit trail is not mistaken for an export" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  # make_bd_fixture now models a wired repo and commits an export, so a test
  # about the ABSENCE of one has to undo that in the open. Explicit beats a
  # fixture that quietly stopped producing the shape under test.
  git rm -q --cached .beads/issues.jsonl >/dev/null 2>&1
  git -c user.email=t@t -c user.name=t commit -q -m "untrack export" >/dev/null 2>&1

  # .beads/interactions.jsonl IS tracked in a real beads repo and is JSONL,
  # and it reconstructs no issue. Counting it would turn the failing repo of
  # 2026-08-07 read as covered while nothing was recoverable.
  printf '{"kind":"x","issue_id":"nope"}\n' > .beads/interactions.jsonl
  git add -f .beads/interactions.jsonl
  git commit -q -m "audit trail"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="issues-recoverable")] | .[0].status' 'warn'
}

@test "issues-recoverable: with no .beads the doctor never reaches this check" {
  make_tmp_repo
  make_gsd_fixture "$PWD"
  rm -rf .beads

  # MEASURED 2026-08-07, and it is why this file carries no test asserting the
  # check's own `out-of-scope` rung: with .beads/ absent the doctor
  # short-circuits before running ANY check — `applicable:false`, `checks:[]`,
  # exit 0 — so that rung is unreachable through the CLI. It stays in the
  # source as a defensive branch for a direct call, and it is documented as
  # unreachable rather than guarded by an assertion that would pass over an
  # empty list and prove nothing. Phase 25 shipped exactly that empty
  # assertion once (G14) and had to delete it.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.applicable' 'false'
  assert_json_eq "$output" '.checks | length' '0'
}

# ─── check 23, export-identity (2026-08-11) ─────────────────────────────────
#
# A consequence of check 22, not an independent idea. Before the export was
# enabled the bd store never left the laptop, so a hostname or an absolute path
# inside an issue was inert. Making the issues RECOVERABLE also made every
# issue field a published file, and the first record through the new door
# carried a session id — caught by hand, before the push. A door opened
# deliberately needs its guard built in the same move.

@test "export-identity: a clean export names no machine and no session" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity")] | .[0].status' 'ok'
}

@test "export-identity: a session id in prose fails, and names the issue" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  # The exact shape that came through the new door on 2026-08-07.
  local id
  id="$(bd create "leaky" -t task -p 4 \
    --description "Medicao da sessao cb465565 contra o runtime" --silent)"
  beads_export_refresh

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  [ "$status" -eq 7 ]
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity")] | .[0].status' 'fail'
  run bash -c "bash '$CAIRN_SCRIPTS_DIR/cairn-doctor.sh' --json | jq -r '[.checks[] | select(.id==\"export-identity\")] | .[0].items | join(\" \")'"
  grep -qF "session id" <<<"$output"
}

@test "export-identity: an absolute home path in prose fails" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  bd create "pathy" -t task -p 4 \
    --description "medido em /Users/alguem/Projects/CairnGo" --silent >/dev/null
  beads_export_refresh

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity")] | .[0].status' 'fail'
}

@test "export-identity: the placeholder paths this project argues with are not findings" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  # /Users/x is deliberate: the journal's partition key argues that the SAME
  # path string on two machines collides, and that argument needs an absolute
  # path to make. Rewriting it as ~ destroys the point, so the guard must not
  # demand it. Phase 28 already keeps three of these on purpose.
  bd create "the collision argument" -t task -p 4 \
    --description "/Users/x/Projects/CairnGo is the same string on both" \
    --silent >/dev/null
  beads_export_refresh

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity")] | .[0].status' 'ok'
}

@test "export-identity: a value a TOOL wrote warns, because scrubbing it is undone" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  # cairn-lease.py records the holder's absolute path and gethostname() in bd
  # metadata by design, so the next `lease acquire` rewrites whatever you
  # scrub. That earns a named warning and a tracked fix (CairnGo-xclf), not a
  # failure the operator cannot clear.
  local id
  id="$(bd create "phase-99 lease" -t chore -p 4 --silent)"
  bd update "$id" --metadata \
    '{"cairn":{"lease":{"host":"some-box.local","holder":"/Users/someone/p","phase":99}}}' \
    >/dev/null 2>&1
  beads_export_refresh

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity")] | .[0].status' 'warn'
  # A warning never moves the exit code.
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity" and .status=="fail")] | length' '0'
}

@test "export-identity: a session id a tool wrote still fails, wherever it sits" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  # The hostname rule bends for authorship; the session rule does not. No tool
  # has a reason to write one, and the rule it breaks is absolute.
  local id
  id="$(bd create "toolish" -t chore -p 4 --silent)"
  bd update "$id" --metadata \
    '{"cairn":{"note":"see https://claude.ai/code/session_abc12345"}}' \
    >/dev/null 2>&1
  beads_export_refresh

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity")] | .[0].status' 'fail'
}

@test "export-identity: with no tracked export it is no-input, and check 22 owns the gap" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_bd_fixture "$PWD"
  git rm -q --cached .beads/issues.jsonl >/dev/null 2>&1
  git -c user.email=t@t -c user.name=t commit -q -m "untrack" >/dev/null 2>&1

  run bash "$CAIRN_SCRIPTS_DIR/cairn-doctor.sh" --json
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity")] | .[0].status' 'not-applicable'
  assert_json_eq "$output" \
    '[.checks[] | select(.id=="export-identity")] | .[0].scope' 'no-input'
}
