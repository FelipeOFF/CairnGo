#!/usr/bin/env bats
# cairn-gate.bats — exercises the ship gate's CLI contract (cairn-gate.py /
# the cairn-gate.sh wrapper) and the git pre-push shim cairn-init.sh installs:
#   0 all clear / not applicable, 5 bd unavailable (never blocks a push),
#   6 gate failed (offending issue ids listed, the only code that blocks).
#
# Assertion style note: a failing `[[ ]]` or `! cmd` mid-test does NOT fail a
# bats test on this bash, so substring checks use grep -qF and negative
# checks use refute_in_output.

load 'helpers'

refute_in_output() {
  if grep -qF -- "$1" <<<"$output"; then
    echo "unexpectedly found '$1' in output" >&2
    return 1
  fi
}

# Gate fixture on top of make_gsd_fixture (phase 1 complete, phase 2 open):
# two phase-1 issues (closed — phase 1 is DONE) and one open phase-2 issue,
# all carrying the m-v1.0 + phase-N pair labels and the gsd metadata stamp.
make_gate_fixture() {
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  GATE_A1="$(bd create "Signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  GATE_A2="$(bd create "Login flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-02","phase":1,"milestone":"v1.0"}}' --silent)"
  GATE_P2="$(bd create "Rate limiting" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-01","phase":2,"milestone":"v1.0"}}' --silent)"
  bd close "$GATE_A1" >/dev/null
  bd close "$GATE_A2" >/dev/null
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

@test "gate passes when every completed-phase issue is closed (open phase-2 ignored)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "ok — no open issues" <<<"$output"
  refute_in_output "$GATE_P2"
}

@test "reopened completed-phase issue fails the gate: exit 6, id listed" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  bd update "$GATE_A1" -s open >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 6 ]
  grep -qF "GATE FAILED" <<<"$output"
  # The offending id is the first token of its own line.
  grep -qE "^${GATE_A1}[[:space:]]" <<<"$output"
  # The open phase-2 issue is NOT offending — phase 2 isn't complete.
  refute_in_output "$GATE_P2"
}

@test "milestone scoping: other-milestone issues pass, unlabeled legacy strays fail" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  stamp_state_milestone

  # An open phase-1 issue from ANOTHER milestone must not trip the v1.0 gate.
  local other stray
  other="$(bd create "Future rework" -t task -l phase-1,m-v2.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v2.0"}}' --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  refute_in_output "$other"

  # An open phase-1 issue with NO m-* label is a legacy stray — it counts.
  stray="$(bd create "Legacy leftover" -t task -l phase-1 --silent)"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 6 ]
  grep -qE "^${stray}[[:space:]]" <<<"$output"
  refute_in_output "$other"
}

@test "--json prints a machine summary on pass and fail" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  stamp_state_milestone

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.applicable' 'true'
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.milestone' 'v1.0'
  assert_json_eq "$output" '.completed_phases[0]' '1'
  assert_json_eq "$output" '.offending | length' '0'

  bd update "$GATE_A2" -s open >/dev/null
  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" '.ok' 'false'
  assert_json_eq "$output" '.offending | length' '1'
  assert_json_eq "$output" '.offending[0].id' "$GATE_A2"
  assert_json_eq "$output" '.offending[0].phase' '1'
}

#-----------------------------------------------------------------------------
# roadmap-complete-but-nothing-built (CORR-05 / D-10) — additive, independent
# of what bd says. See cairn-loop-gate.bats-equivalent test in capability.bats
# for the twin's coverage, and the cross-script test there for lockstep proof.
#-----------------------------------------------------------------------------

@test "gate blocks a completed phase with no directory on disk at all, even with zero bd issues" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # ROADMAP: phase 1 is [x]
  bd init -q --prefix noart --non-interactive >/dev/null 2>&1   # zero issues
  rm -rf .planning/phases/01-auth

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" \
    '[.offending[] | select(.status == "no-artifacts")] | length' '1'
  assert_json_eq "$output" \
    '.offending[] | select(.status == "no-artifacts") | .phase' '1'
  assert_json_eq "$output" \
    '.offending[] | select(.status == "no-artifacts") | .id' 'null'

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 6 ]
  grep -qF "GATE FAILED" <<<"$output"
  grep -qF "phase-1" <<<"$output"
}

@test "gate blocks a completed phase whose disk holds only a bare PLAN.md (planned, never executed)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # ROADMAP: phase 1 is [x], with SUMMARY + VERIFICATION
  bd init -q --prefix noart --non-interactive >/dev/null 2>&1   # zero issues
  rm -f .planning/phases/01-auth/01-01-SUMMARY.md \
        .planning/phases/01-auth/01-VERIFICATION.md

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 6 ]
  assert_json_eq "$output" \
    '[.offending[] | select(.status == "no-artifacts")] | length' '1'
}

@test "gate passes a completed phase with VERIFICATION.md on disk and zero bd issues (unchanged by this check)" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"   # phase 1 already ships a VERIFICATION.md
  bd init -q --prefix noart --non-interactive >/dev/null 2>&1   # zero issues

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ok' 'true'
  assert_json_eq "$output" '.offending | length' '0'
}

@test "no .beads/ — gate not applicable, exit 0 with a note" {
  make_tmp_repo
  make_gsd_fixture "$PWD"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
}

# O portador da fase: a issue com o par de labels e SEM gsd.req, sem plan-NN
# e sem sufixo de filho. E' ele que herdou o papel do checkbox do roteiro.
make_bd_only_fixture() {
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  BD_CARRIER1="$(bd create "Fase 1: autenticacao" -t task -l phase-1,m-v1.0 --silent)"
  BD_A1="$(bd create "Signup flow" -t task -l phase-1,m-v1.0 \
    --metadata '{"gsd":{"req":"AUTH-01","phase":1,"milestone":"v1.0"}}' --silent)"
  BD_CARRIER2="$(bd create "Fase 2: API" -t task -l phase-2,m-v1.0 --silent)"
  BD_P2="$(bd create "Rate limiting" -t task -l phase-2,m-v1.0 \
    --metadata '{"gsd":{"req":"API-01","phase":2,"milestone":"v1.0"}}' --silent)"
}

@test "sem .planning/ e sem .beads/ o gate nao se aplica: exit 0 com nota" {
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "not applicable" <<<"$output"
  grep -qF ".beads" <<<"$output"
}

# O CASO QUE A v1.7 TROUXE, e que o teste anterior nunca exercitou: um repo
# JA MIGRADO — .beads/ presente, .planning/ nenhum. Ate aqui o gate saia 0
# dizendo "not applicable" e o pre-push passava qualquer coisa; o ship gate
# estava morto exatamente no repo que o cairn existe para servir.
@test "repo migrado: fase cujo portador fechou com trabalho aberto reprova, exit 6" {
  require_bd
  make_tmp_repo
  make_bd_only_fixture
  [ ! -d .planning ]
  bd close "$BD_CARRIER1" >/dev/null
  bd close "$BD_A1" >/dev/null
  bd close "$BD_CARRIER2" >/dev/null   # fase 2 declarada pronta...

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 6 ]
  grep -qF "$BD_P2" <<<"$output"       # ...mas o trabalho dela segue aberto
  refute_in_output "$BD_A1"
}

@test "repo migrado: portador fechado com todo o trabalho fechado passa" {
  require_bd
  make_tmp_repo
  make_bd_only_fixture
  bd close "$BD_CARRIER1" >/dev/null
  bd close "$BD_A1" >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "ok — no open issues" <<<"$output"
}

# A razao de bloqueio por ARTEFATO EM DISCO mede se o disco sustenta o que o
# DOCUMENTO afirma. Sem documento nao ha afirmacao a conferir, e roda-la
# assim reprovaria toda fase de todo repo migrado pela ausencia de arquivos
# que o cairn nao escreve mais.
@test "repo migrado: a razao de artefato-em-disco nao se aplica" {
  require_bd
  make_tmp_repo
  make_bd_only_fixture
  bd close "$BD_CARRIER1" >/dev/null
  bd close "$BD_A1" >/dev/null

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.source' 'bd'
  assert_json_eq "$output" '.offending | length' '0'
}

@test "repo migrado sem portador fechado: nada a barrar, exit 0" {
  require_bd
  make_tmp_repo
  make_bd_only_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "no phase carrier is closed" <<<"$output"
}

# O roteiro em disco AINDA vence enquanto existe: um GSD por importar e' a
# ENTRADA, e o portador nao pode contradizer o checkbox nesse estado.
@test "com ROADMAP.md em disco a fonte segue sendo o roteiro, nao o portador" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.source' 'roadmap'
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

  run env PATH="$stub" "$stub/bash" "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 5 ]
  grep -qF "warning" <<<"$output"
}

#-----------------------------------------------------------------------------
# pre-push shim (installed by cairn-init.sh)
#-----------------------------------------------------------------------------

# Write an executable stub gate that exits CODE, path in $GATE_STUB.
make_gate_stub() {
  GATE_STUB="$BATS_TEST_TMPDIR/gate-stub-$1.sh"
  printf '#!/usr/bin/env bash\necho "stub gate exit %s"\nexit %s\n' "$1" "$1" \
    > "$GATE_STUB"
  chmod +x "$GATE_STUB"
}

@test "cairn-init installs the pre-push shim idempotently" {
  require_bd
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  # A full `bd init` may set core.hooksPath (e.g. .beads/hooks) — the shim
  # follows the ACTIVE hooks dir, so resolve it the same way.
  local hooks_dir
  hooks_dir="$(git rev-parse --git-path hooks)"
  [ -x "$hooks_dir/pre-push" ]
  grep -qF "cairn pre-push gate" "$hooks_dir/pre-push"

  # Re-run: refreshed in place — our own shim is never chained aside to .old.
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  [ -x "$hooks_dir/pre-push" ]
  grep -qF "cairn pre-push gate" "$hooks_dir/pre-push"
  if [ -f "$hooks_dir/pre-push.old" ]; then
    if grep -qF "cairn pre-push gate" "$hooks_dir/pre-push.old"; then
      echo "our own shim was wrongly chained aside to pre-push.old" >&2
      return 1
    fi
  fi
}

@test "the generated shim bakes no absolute path — the gate resolves at push time" {
  require_bd
  make_tmp_repo

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  local hooks_dir shim
  hooks_dir="$(git rev-parse --git-path hooks)"
  shim="$hooks_dir/pre-push"

  # CairnGo-pg9. The generator interpolated its own $SCRIPTS_DIR into the
  # heredoc, so the installed hook carried the absolute path of whichever
  # machine — and whichever plugin VERSION — happened to run the init. It
  # never failed loudly, because a plugin cache directory does not disappear;
  # it just ran a gate five releases old on every push, in silence.
  ! grep -qF "$CAIRN_SCRIPTS_DIR" "$shim"
  ! grep -qE '^GATE=.*:-/' "$shim"

  # What replaces it: resolution at PUSH time, over tiers that are all either
  # relative to the repo being pushed or read from the environment.
  grep -qF 'GATE="${CAIRN_GATE:-}"' "$shim"
  grep -qF '"$REPO_ROOT/cairn/scripts/cairn-gate.sh"' "$shim"
  grep -qF '.cairn/plugin-root' "$shim"

  # And the gate still resolves in a repo that is NOT a cairn checkout: tier 3
  # is the pointer this same init writes, gitignored, never committed.
  [ "$(head -1 .cairn/plugin-root)" = "$(cd "$CAIRN_SCRIPTS_DIR/.." && pwd)" ]
  grep -qxF '.cairn/plugin-root' .gitignore
}

@test "shim chains a pre-existing foreign pre-push hook (runs it first)" {
  require_bd
  make_tmp_repo
  # bd init sets core.hooksPath (.beads/hooks) and installs bd's own hooks —
  # always resolve the ACTIVE hooks dir instead of assuming .git/hooks.
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  local hooks_dir
  hooks_dir="$(git rev-parse --git-path hooks)"
  mkdir -p "$hooks_dir"
  printf '#!/usr/bin/env bash\ntouch "%s/old-hook-ran"\nexit 0\n' "$PWD" \
    > "$hooks_dir/pre-push"
  chmod +x "$hooks_dir/pre-push"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  [ -x "$hooks_dir/pre-push.old" ]
  grep -qF "cairn pre-push gate" "$hooks_dir/pre-push"

  make_gate_stub 0
  run env CAIRN_GATE="$GATE_STUB" "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 0 ]
  [ -f old-hook-ran ]
}

@test "shim blocks only on gate exit 6; 5 and 0 let the push through" {
  require_bd
  make_tmp_repo
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  local hooks_dir
  hooks_dir="$(git rev-parse --git-path hooks)"
  # Isolate the shim's exit-code contract from whatever hook got chained
  # aside (test 'shim chains...' covers the chain path).
  rm -f "$hooks_dir/pre-push.old"

  make_gate_stub 6
  run env CAIRN_GATE="$GATE_STUB" "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 6 ]
  grep -qF "PUSH BLOCKED" <<<"$output"

  make_gate_stub 5
  run env CAIRN_GATE="$GATE_STUB" "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 0 ]
  grep -qF "bd unavailable" <<<"$output"

  make_gate_stub 0
  run env CAIRN_GATE="$GATE_STUB" "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 0 ]
}

@test "end to end: git push blocked while a completed-phase issue is open, allowed after close" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]

  local remote="$BATS_TEST_TMPDIR/remote.git"
  git init -q --bare "$remote"
  git remote add origin "$remote"
  git add -A >/dev/null
  git commit -qm "fixture"

  bd update "$GATE_A1" -s open >/dev/null
  run git push origin HEAD
  [ "$status" -ne 0 ]
  grep -qF "PUSH BLOCKED" <<<"$output"

  bd close "$GATE_A1" >/dev/null
  run git push origin HEAD
  [ "$status" -eq 0 ]
}

@test "cairn-init refuses to clobber a foreign pre-push.old (earlier chained hook kept)" {
  require_bd
  make_tmp_repo
  bd init -q --prefix gate --non-interactive >/dev/null 2>&1
  local hooks_dir
  hooks_dir="$(git rev-parse --git-path hooks)"
  mkdir -p "$hooks_dir"
  printf '#!/usr/bin/env bash\n# foreign hook X\nexit 0\n' > "$hooks_dir/pre-push"
  chmod +x "$hooks_dir/pre-push"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  grep -qF "foreign hook X" "$hooks_dir/pre-push.old"

  # Another tool later replaces the shim with a fresh foreign hook. A re-run
  # must refuse instead of overwriting pre-push.old (silently deleting X).
  printf '#!/usr/bin/env bash\n# foreign hook Y\nexit 0\n' > "$hooks_dir/pre-push"
  chmod +x "$hooks_dir/pre-push"
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -ne 0 ]
  grep -qF "refusing to overwrite" <<<"$output"
  grep -qF "foreign hook X" "$hooks_dir/pre-push.old"
  grep -qF "foreign hook Y" "$hooks_dir/pre-push"
}

@test "shim gates the pushed repo even when CLAUDE_PROJECT_DIR points elsewhere" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  bd update "$GATE_A1" -s open >/dev/null   # completed phase 1 has open work
  run bash "$CAIRN_SCRIPTS_DIR/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  local hooks_dir repo_with_issue
  hooks_dir="$(git rev-parse --git-path hooks)"
  repo_with_issue="$CAIRN_TMP_REPO"
  rm -f "$hooks_dir/pre-push.old"   # isolate from bd's own chained hooks

  # A clean second repo plays the Claude session's project. cairn-gate
  # prefers $CLAUDE_PROJECT_DIR over cwd, so without the shim pinning
  # --planning-dir the push would be gated against the WRONG repo (exit 0).
  make_tmp_repo
  local other_project="$CAIRN_TMP_REPO"
  cd "$repo_with_issue"

  run env CLAUDE_PROJECT_DIR="$other_project" \
    "$hooks_dir/pre-push" origin ssh://x < /dev/null
  [ "$status" -eq 6 ]
  grep -qF "PUSH BLOCKED" <<<"$output"
}

@test "the milestone carrier is not phase work: open, it never blocks the gate" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  make_gate_fixture
  local carrier
  carrier="$(bd create "v1.0 — the fixture cycle" -t task -l m-v1.0,milestone --silent)"

  run bash "$CAIRN_SCRIPTS_DIR/cairn-gate.sh"
  [ "$status" -eq 0 ]
  grep -qF "ok — no open issues" <<<"$output"
  refute_in_output "$carrier"
}
