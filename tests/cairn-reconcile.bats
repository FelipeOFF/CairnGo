#!/usr/bin/env bats
# cairn-reconcile.bats — exercises the semantic escalation collector/
# citation-checker CLI contract (cairn-reconcile.py / the cairn-reconcile.sh
# wrapper): collect (gated on a "conflict" corroboration verdict, ESC-04,
# D-01), verify (D-03's file+line+literal-text citation re-check, whole-
# proposal invalidation on any single bad citation).
#
# Two tests here are load-bearing beyond the usual pass/fail:
#   - the mutation-proof test snapshots BOTH bd state and the tracked
#     working tree before/after a real `collect` run against a genuinely
#     conflicted fixture, and asserts byte-identical — a grep over the
#     source only proves the TEXT has no write verb today; this proves
#     RUNNING it has no side effect (ESC-02).
#   - the citation-trap test constructs a proposal with one CORRECT
#     citation and one that names a real file/line but the WRONG text, and
#     asserts the whole proposal is rejected — not "N of M claims
#     verified" (D-03).
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail
# a bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'

RECONCILE="$CAIRN_SCRIPTS_DIR/cairn-reconcile.sh"

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# Bd fixture mirroring tests/cairn-doctor.bats's own phase-corroboration
# recipe (reimplemented here, not sourced — .bats files cannot load each
# other's local helpers): phase 1's issues closed (agrees with
# make_gsd_fixture's phase 1, which is verified + roadmap-complete on
# disk), phase 2's issue open (mid-flight, matching make_gsd_fixture's
# phase 2). On its own this is the "everything agrees" fixture; a caller
# adds a straggler + cairn-map.sh re-run on top to produce a real
# disk-vs-bd "blocks" conflict for phase 1 (tests/cairn-doctor.bats:833).
make_corroboration_fixture() {
  bd init -q --prefix rec --non-interactive >/dev/null 2>&1
  REC_A1="$(bd create "AUTH-01: Signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  REC_A2="$(bd create "AUTH-02: Login flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v1.0"}}' --silent)"
  REC_P2="$(bd create "API-01: Rate limiting" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-01","phase":2,"milestone":"v1.0"}}' --silent)"
  bd close "$REC_A1" >/dev/null
  bd close "$REC_A2" >/dev/null
}

# Adds a straggler bd issue still open for phase 1 (already verified on
# disk and roadmap-complete) and regenerates its beads map — the exact
# disk-vs-bd "blocks" recipe tests/cairn-doctor.bats:833-858 uses.
make_phase1_conflict() {
  bd create "AUTH-04: Forgotten follow-up" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-04","phase":1,"milestone":"v1.0"}}' --silent >/dev/null
  bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 1 >/dev/null
}

# O PORTADOR da fase 1: o bead que carrega `phase-1` e NAO e' requisito (sem
# `gsd.req`), nem plano, nem filho. E' ele que herdou o papel da secao
# `### Phase 1` do roteiro — o titulo e' o nome da fase, a description e' o
# que ela promete.
make_phase1_carrier() {
  REC_C1="$(bd create "Auth foundation" -t task -l phase-1,m-v1.0 \
    -d "Signup, login e a sessao que os dois compartilham." --silent)"
}

#-----------------------------------------------------------------------------
# Task 1 — static: zero bd write verbs, zero journal-append calls (ESC-02)
#-----------------------------------------------------------------------------

@test "static: cairn-reconcile.py's source carries zero bd write verbs and zero journal-append calls" {
  local src="$CAIRN_SCRIPTS_DIR/cairn-reconcile.py"
  [ -f "$src" ]

  run bash -c "grep -v '^#' '$src' | grep -Ec '\"(create|update|close|reopen)\"'"
  [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
  [ "$output" -eq 0 ]

  run bash -c "grep -v '^#' '$src' | grep -Ec '\"(observe|lease|append)\"'"
  [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
  [ "$output" -eq 0 ]
}

#-----------------------------------------------------------------------------
# Task 1 — gating (ESC-04): collect refuses on anything but a "conflict"
# verdict, and never writes when it refuses.
#-----------------------------------------------------------------------------

@test "collect: an all-agree fixture reports 'ok' and collect refuses — exit 3, nothing written" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 3 ]
  assert_json_eq "$output" '.collected' 'false'
  assert_json_eq "$output" '.corroboration' 'ok'
  [ ! -f .cairn/reconcile-evidence.json ]

  # Same refusal, human mode — the message names the phase and verdict.
  run bash "$RECONCILE" collect 1 --project-dir "$PWD"
  [ "$status" -eq 3 ]
  grep -qF "phase 1 corroboration is 'ok'" <<<"$output"
  [ ! -f .cairn/reconcile-evidence.json ]
}

@test "collect: refusing on a non-conflicted phase deletes a stale bundle left over for a DIFFERENT phase" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_conflict

  # A real bundle for phase 1 exists on disk.
  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  [ -f .cairn/reconcile-evidence.json ]
  assert_json_eq "$output" '.phase' '1'

  # Checking phase 2 (which agrees, "ok") refuses AND cleans up the now-
  # mismatched phase-1 bundle — a bundle that no longer matches what was
  # just checked must never be left behind.
  run bash "$RECONCILE" collect 2 --project-dir "$PWD" --json
  [ "$status" -eq 3 ]
  [ ! -f .cairn/reconcile-evidence.json ]
}

@test "collect: a phase number absent from the model exits usage (2), never crashes" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture

  run bash "$RECONCILE" collect 999 --project-dir "$PWD" --json
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"
  grep -qF "does not exist in the model" <<<"$output"
}

#-----------------------------------------------------------------------------
# Task 1 — THE LOAD-BEARING TEST (ESC-02): running collect against a real
# conflicted fixture mutates neither bd state nor the tracked working tree.
# .cairn/ is excluded from the tree manifest because collect's OWN
# evidence-bundle write (and cairn-status.py's own journal side effect) is
# expected there — that is not what this test is proving.
#-----------------------------------------------------------------------------

@test "collect: THE LOAD-BEARING TEST -- a real collect run against a conflicted fixture mutates neither bd state nor the working tree" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_conflict

  # Confirm the fixture really IS conflicted before proving collect leaves
  # it untouched — the gating tests above cover the refusal path; this
  # test needs the ACCEPT path to actually run.
  run bash -c "python3 '$CAIRN_SCRIPTS_DIR/cairn-status.py' --json --planning-dir '$PWD/.planning' | jq -r '.phases[] | select(.number==1) | .corroboration'"
  [ "$status" -eq 0 ]
  [ "$output" = "conflict" ]

  local bd_before tree_before
  bd_before="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  tree_before="$(find . -type f ! -path './.git/*' ! -path './.cairn/*' -exec sha256sum {} + | sort)"

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  [ -f .cairn/reconcile-evidence.json ]
  assert_json_eq "$output" '.phase' '1'
  assert_json_eq "$output" '.corroboration.verdict' 'conflict'

  local bd_after tree_after
  bd_after="$(bd list --all --limit 0 --json | jq -S 'sort_by(.id)')"
  tree_after="$(find . -type f ! -path './.git/*' ! -path './.cairn/*' -exec sha256sum {} + | sort)"

  [ "$bd_before" = "$bd_after" ]
  [ "$tree_before" = "$tree_after" ]
}

#-----------------------------------------------------------------------------
# Task 1 — D-04: two consecutive collects against the same unchanged
# conflicted fixture produce the identical evidence_hash.
#-----------------------------------------------------------------------------

@test "collect: two consecutive runs against an unchanged conflicted fixture produce the identical evidence_hash (D-04)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_conflict

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local hash1
  hash1="$(jq -r '.evidence_hash' <<<"$output")"
  [ -n "$hash1" ]
  [[ "$hash1" == sha256:* ]]

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local hash2
  hash2="$(jq -r '.evidence_hash' <<<"$output")"

  [ "$hash1" = "$hash2" ]

  # The bundle written to disk carries the same hash too, not just stdout.
  run bash -c "jq -r '.evidence_hash' .cairn/reconcile-evidence.json"
  [ "$status" -eq 0 ]
  [ "$output" = "$hash1" ]
}

@test "collect: gathers roadmap excerpt, journal history, and corroboration evidence verbatim" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_conflict

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]

  assert_json_eq "$output" '.phase' '1'
  assert_json_eq "$output" '.corroboration.evidence.disk' 'verified'
  assert_json_eq "$output" '.corroboration.evidence.bd' 'open'
  assert_json_eq "$output" '.corroboration.conflicts | length > 0' 'true'
  assert_json_eq "$output" '.roadmap_excerpt | startswith("### Phase 1: Auth")' 'true'
  assert_json_eq "$output" '.journal.history | length > 0' 'true'
  assert_json_eq "$output" '.git_shallow' 'false'
  assert_json_eq "$output" '.git_log | type' 'array'
}

# A REGRA DAS DUAS FONTES, aplicada a' evidencia de TEXTO. O `### Phase N` era
# o que a fase dizia de si mesma; num repo ja migrado esse texto mora na issue
# PORTADORA, e a alternativa — devolver null — mandaria o investigador
# raciocinar sobre um conflito sem nunca ler o que a fase prometeu.
@test "collect: sem ROADMAP.md em disco a evidencia de texto vem do portador da fase" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_carrier
  make_phase1_conflict
  rm .planning/ROADMAP.md

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.roadmap_excerpt | startswith("Phase 1: Auth foundation")' 'true'
  # A promessa da fase chega inteira, nao so' o nome dela.
  assert_json_eq "$output" '.roadmap_excerpt | contains("Signup, login")' 'true'
  # E o texto NAO se disfarca de secao de markdown: quem le este pacote
  # responde citando arquivo e linha, e um `###` aqui convidaria a citar um
  # arquivo que nao existe neste repositorio.
  assert_json_eq "$output" '.roadmap_excerpt | startswith("###")' 'false'
  assert_json_eq "$output" ".roadmap_excerpt | contains(\"[bd $REC_C1]\")" 'true'
}

# A ausencia e' dita, nunca preenchida: sem portador nao ha nome de fase, e o
# titulo de um REQUISITO ("AUTH-01: Signup flow") emprestado no lugar seria uma
# promessa que ninguem fez.
@test "collect: sem ROADMAP.md e sem portador a evidencia de texto e' null" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_conflict
  rm .planning/ROADMAP.md

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.roadmap_excerpt' 'null'
}

# Enquanto o roteiro existe em disco ele e' a ENTRADA e o portador nao o
# contradiz — um GSD por importar e' tudo o que `.planning/` existe para ser.
@test "collect: com ROADMAP.md em disco o roteiro vence o portador" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_carrier
  make_phase1_conflict

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" \
    '.roadmap_excerpt | startswith("### Phase 1: Auth")' 'true'
  assert_json_eq "$output" '.roadmap_excerpt | contains("[bd ")' 'false'
}

@test "DJOUR-03: with the whole journal surface deleted the bundle still collects, history empty" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_conflict

  # A first collect, so the journal genuinely has history to destroy (the
  # collect's own cairn-status.py call journals as a side effect).
  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  local before="$output"
  assert_json_eq "$before" '.journal.history | length > 0' 'true'

  # Phase 28 made the surface bigger than one path: the partition directory
  # AND the inherited single file. The journal script is neutralised too --
  # otherwise the collect's own observe would repopulate what was deleted
  # before journal_history() ever reads it, and this would prove nothing.
  rm -rf .cairn/journal
  rm -f .cairn/journal.jsonl*

  run env CAIRN_JOURNAL=/nonexistent/path bash "$RECONCILE" collect 1 \
    --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.journal.history' '[]'
  assert_json_eq "$output" '.journal.last_moved' 'null'
  # Every other section of the bundle is intact and says the same thing --
  # the journal is evidence, never authority.
  assert_json_eq "$output" '.phase' '1'
  assert_json_eq "$output" '.corroboration.evidence.disk' \
    "$(jq -r '.corroboration.evidence.disk' <<<"$before")"
  assert_json_eq "$output" '.corroboration.evidence.bd' \
    "$(jq -r '.corroboration.evidence.bd' <<<"$before")"
  assert_json_eq "$output" '.corroboration.conflicts | length > 0' 'true'
  assert_json_eq "$output" '.roadmap_excerpt | startswith("### Phase 1: Auth")' 'true'
}

@test "collect: the bundle carries EXACTLY these keys — nothing that is not evidence gets into the hash" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_corroboration_fixture
  make_phase1_conflict

  run bash "$RECONCILE" collect 1 --project-dir "$PWD" --json
  [ "$status" -eq 0 ]

  # An assertion on the SET, added by plan 24-03 for a specific reason. The
  # response language the reconcile-investigator answers in is passed to it by
  # /cairn:reconcile step 3, read from cairn-config — deliberately NOT from
  # here. `evidence_hash` is computed over this dict (cairn-reconcile.py:
  # 525-531) and step 2 compares it to decide whether a prior proposal can be
  # reused; a language field in the bundle would invalidate every cached
  # proposal on every change of language, spending a subagent over something
  # that changed no evidence at all.
  #
  # So this goes red both ways, which is the point: a new field added to the
  # bundle turns it red, and so does a field silently removed from it.
  assert_json_eq "$output" '[keys[]] | sort | join(",")' \
    'context_excerpt,corroboration,evidence_hash,generated_at,git_log,git_shallow,journal,phase,roadmap_excerpt'

  # The two that are added AFTER the hash is taken, named so the boundary of
  # what the hash covers stays visible in a test rather than only in a comment.
  assert_json_eq "$output" '.evidence_hash | startswith("sha256:")' 'true'
  assert_json_eq "$output" '.generated_at | type' 'string'
}

#-----------------------------------------------------------------------------
# Task 2 — verify: a fully-correct proposal is valid; a proposal with one
# bad citation is rejected wholesale (D-03).
#-----------------------------------------------------------------------------

@test "verify: a proposal with every citation correct verifies as valid, exit 0" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  local line1
  line1="$(sed -n '1p' .planning/ROADMAP.md)"

  python3 - "$line1" > proposal.json <<'PY'
import json
import sys

line1 = sys.argv[1]
proposal = {
    "phase": 1,
    "generated_at": "2026-07-31T00:00:00Z",
    "evidence_hash": "sha256:deadbeef",
    "claims": [
        {
            "statement": "ROADMAP.md's first line is the project title.",
            "citations": [
                {"file": ".planning/ROADMAP.md", "line": 1, "text": line1}
            ],
            "recommended_action": {"type": "manual_review", "issue": None,
                                    "note": "n/a"}
        }
    ]
}
print(json.dumps(proposal))
PY

  run bash "$RECONCILE" verify 1 --file "$PWD/proposal.json" --project-dir "$PWD" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.valid' 'true'
  assert_json_eq "$output" '.failed_citations | length' '0'
}

@test "verify: THE CITATION TRAP -- one bad citation invalidates the WHOLE proposal, even with a correct citation present" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  # A real line from a real file already in the fixture (the CORRECT
  # citation), plus a DIFFERENT real line/file cited with fabricated text
  # that is NOT what is actually there (the trap).
  local line1
  line1="$(sed -n '1p' .planning/ROADMAP.md)"
  local real_line3
  real_line3="$(sed -n '3p' .planning/ROADMAP.md)"
  # Self-verify the fixture: the wrong text below must NOT equal what is
  # really on line 3, or this test would prove nothing.
  [ "$real_line3" != "this text is definitely not on line 3 of ROADMAP.md" ]

  python3 - "$line1" > proposal.json <<'PY'
import json
import sys

line1 = sys.argv[1]
proposal = {
    "phase": 1,
    "generated_at": "2026-07-31T00:00:00Z",
    "evidence_hash": "sha256:deadbeef",
    "claims": [
        {
            "statement": "Correct claim: ROADMAP.md's first line is the project title.",
            "citations": [
                {"file": ".planning/ROADMAP.md", "line": 1, "text": line1}
            ],
            "recommended_action": {"type": "manual_review", "issue": None,
                                    "note": "n/a"}
        },
        {
            "statement": "Bad claim: line 3 says something it does not say.",
            "citations": [
                {"file": ".planning/ROADMAP.md", "line": 3,
                 "text": "this text is definitely not on line 3 of ROADMAP.md"}
            ],
            "recommended_action": {"type": "manual_review", "issue": None,
                                    "note": "n/a"}
        }
    ]
}
print(json.dumps(proposal))
PY

  run bash "$RECONCILE" verify 1 --file "$PWD/proposal.json" --project-dir "$PWD" --json
  [ "$status" -eq 4 ]
  assert_json_eq "$output" '.valid' 'false'
  # Exactly one failure — the bad citation on line 3 — and the WHOLE
  # proposal is still rejected, not "1 of 2 claims verified": there is no
  # code path here that reports a partial accept.
  assert_json_eq "$output" '.failed_citations | length' '1'
  assert_json_eq "$output" '.failed_citations[0].line' '3'
  assert_json_eq "$output" '.failed_citations[0].error' 'text mismatch'

  # Human mode: rejects wholesale too, names the failure, never claims
  # partial success.
  run bash "$RECONCILE" verify 1 --file "$PWD/proposal.json" --project-dir "$PWD"
  [ "$status" -eq 4 ]
  grep -qF "proposal rejected" <<<"$output"
  refute_in_output "1 of 2"
}

@test "verify: a missing citation file and an out-of-range line both fail their citation, never crash" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  cat > proposal.json <<'EOF'
{
  "phase": 1,
  "generated_at": "2026-07-31T00:00:00Z",
  "evidence_hash": "sha256:deadbeef",
  "claims": [
    {
      "statement": "Cites a file that does not exist.",
      "citations": [
        {"file": ".planning/DOES-NOT-EXIST.md", "line": 1, "text": "anything"}
      ],
      "recommended_action": {"type": "manual_review", "issue": null, "note": "n/a"}
    },
    {
      "statement": "Cites a line far beyond the file's own length.",
      "citations": [
        {"file": ".planning/ROADMAP.md", "line": 99999, "text": "anything"}
      ],
      "recommended_action": {"type": "manual_review", "issue": null, "note": "n/a"}
    }
  ]
}
EOF

  run bash "$RECONCILE" verify 1 --file "$PWD/proposal.json" --project-dir "$PWD" --json
  [ "$status" -eq 4 ]
  refute_in_output "Traceback"
  assert_json_eq "$output" '.valid' 'false'
  assert_json_eq "$output" '.failed_citations | length' '2'
}

@test "verify: a proposal with no claims (or zero citations) is rejected, never vacuously valid" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  echo '{"phase": 1, "citations_test": true}' > proposal.json
  run bash "$RECONCILE" verify 1 --file "$PWD/proposal.json" --project-dir "$PWD" --json
  [ "$status" -eq 4 ]
  assert_json_eq "$output" '.valid' 'false'

  echo '{"phase": 1, "claims": []}' > proposal2.json
  run bash "$RECONCILE" verify 1 --file "$PWD/proposal2.json" --project-dir "$PWD" --json
  [ "$status" -eq 4 ]
  assert_json_eq "$output" '.valid' 'false'

  echo '{"phase": 1, "claims": [{"statement": "no citations at all", "citations": []}]}' > proposal3.json
  run bash "$RECONCILE" verify 1 --file "$PWD/proposal3.json" --project-dir "$PWD" --json
  [ "$status" -eq 4 ]
  assert_json_eq "$output" '.valid' 'false'
}

@test "verify: a proposal whose own phase field does not match the requested phase exits usage (2)" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  echo '{"phase": 2, "claims": []}' > proposal.json
  run bash "$RECONCILE" verify 1 --file "$PWD/proposal.json" --project-dir "$PWD" --json
  [ "$status" -eq 2 ]
  refute_in_output "Traceback"
}
