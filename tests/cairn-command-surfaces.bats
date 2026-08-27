#!/usr/bin/env bats
# cairn-command-surfaces.bats — the /cairn:* PROMPTS as a contract.
#
# Every other suite here tests a script. These surfaces have no script: they
# are the files an agent reads before it speaks to the operator, and they age
# in a way nothing catches — a script can be right while the page that
# explains it is a year behind. Measured precedents in this repository, all of
# them the same shape:
#
#   1. docs/commands/doctor.md said "fifteen checks" with sixteen registered
#   2. cairn-doctor.py's docstring said "eighteen checks in total" with
#      nineteen, then "not one of the 17 checks" with nineteen
#   3. docs/commands/doctor.md:449 said "not one of the 18 checks" while line
#      371 of the SAME file said "nineteen" — two hand numbers disagreeing
#      inside one file
#   4. commands/help.md's map listed cairn's own commands by hand and had
#      already dropped /cairn:reconcile (CairnGo-q9l)
#   5. commands/doctor.md taught three status symbols after the script grew a
#      fourth (CairnGo-026)
#
# So the rule these tests enforce is not "the number is right", it is "no
# number is written by hand at all, and every list is derived or addressed".
#
# Assertion style: exact values, never a negation of a value; and a negative
# is `refute_*`, never `! grep` (bash's `!` suppresses errexit, so a failing
# `! grep` would not fail the test).

load 'helpers'

DOCTOR_PY="$CAIRN_SCRIPTS_DIR/cairn-doctor.py"
WRAP="$CAIRN_SCRIPTS_DIR/cairn-wrap.sh"
DOCTOR_PROMPT="$CAIRN_REPO_ROOT/cairn/commands/doctor.md"
# The single routing table the prompt addresses instead of copying.
# Overridable so the coverage assertion can be proved against a deliberately
# broken COPY of the table — the table itself belongs to another workstream in
# this phase and is never edited to run a test.
DOCTOR_ROUTING="${CAIRN_DOCTOR_ROUTING:-$CAIRN_REPO_ROOT/cairn/docs/commands/doctor.md}"

refute_in_file() {
  if grep -qF -- "$1" "$2"; then
    echo "unexpectedly found '$1' in $2" >&2
    return 1
  fi
}

# Every check id the doctor's --json actually reports, one per line.
#
# Derived from a RUN, never from a list written here: a list in the test is
# the same defect the tests below exist to catch, moved one file over. The
# fixture is minimal on purpose — a check with no input still reports itself
# (that is what the fourth status is for), so the id set is complete without
# a populated repo.
doctor_check_ids() {
  local dir="$1"
  python3 "$DOCTOR_PY" --project-dir "$dir" --json \
    | python3 -c 'import json,sys; print("\n".join(c["id"] for c in json.load(sys.stdin)["checks"]))'
}

make_doctor_id_fixture() {
  local dir="$BATS_TEST_TMPDIR/idfix"
  mkdir -p "$dir"
  git init -q "$dir"
  git -C "$dir" config user.email "cairn-tests@example.com"
  git -C "$dir" config user.name "Cairn Tests"
  make_gsd_fixture "$dir"
  ( cd "$dir" && bd init -q --prefix surf --non-interactive >/dev/null 2>&1 )
  printf '%s\n' "$dir"
}

# ---------------------------------------------------------------------------
# CairnGo-026 — the /cairn:doctor PROMPT and the fourth status
# ---------------------------------------------------------------------------

@test "the doctor prompt teaches all four statuses, not three" {
  # MEASURED 2026-08-07 against b9fdfb3: the prompt said
  # `one ✓/⚠/✗ line per check` — three symbols — while cairn-doctor.py:614
  # has carried four since phase 23:
  #   SYMBOL = {"ok": "✓", "not-applicable": "⊘", "warn": "⚠", "fail": "✗"}
  # The operator hears the verdict through this page, so a three-state
  # vocabulary puts the false green back into the conversation after the code
  # stopped printing it.
  local sym
  for sym in "✓" "⊘" "⚠" "✗"; do
    grep -qF -- "$sym" "$DOCTOR_PROMPT"
  done
  local word
  for word in "not-applicable" "no-input" "out-of-scope"; do
    grep -qF -- "$word" "$DOCTOR_PROMPT"
  done
}

@test "the doctor prompt knows the INCOMPLETE verdict and that it exits 0" {
  # cairn-doctor.py:3502-3508 ranks the verdict FAIL > INCOMPLETE > ok, and
  # :3512 exits 0 for INCOMPLETE on purpose: an absent input is friction, not
  # a state inconsistency. A page that only maps exit codes to verdicts would
  # report an incomplete run as clean.
  grep -qF "INCOMPLETE" "$DOCTOR_PROMPT"

  # And it must say how the verdict is DERIVED from --json, because the
  # payload carries no `verdict` key — measured: the top-level keys are
  # ok, failed, applicable, counts, note, active_phase, milestone.
  grep -qF '`failed`' "$DOCTOR_PROMPT"
  grep -qF '`ok`' "$DOCTOR_PROMPT"
}

@test "every check id the doctor reports has an entry in the routing table" {
  require_bd
  local dir; dir="$(make_doctor_id_fixture)"

  local ids; ids="$(doctor_check_ids "$dir")"
  [ -n "$ids" ]

  # The prompt names ONE routing table and every id must have an entry in it.
  # This is the assertion that makes addressing safe: a check added without
  # its remediation turns red here, at the file whose owner added the check.
  local id missing=""
  while IFS= read -r id; do
    [ -n "$id" ] || continue
    grep -qF -- "$id" "$DOCTOR_ROUTING" || missing="$missing $id"
  done <<<"$ids"

  if [ -n "$missing" ]; then
    echo "check id(s) with no entry in $DOCTOR_ROUTING:$missing" >&2
    return 1
  fi
}

@test "the doctor prompt addresses the routing table instead of copying it" {
  # MEASURED 2026-08-07: the prompt routed 9 of the 21 ids the --json
  # reports. Twelve had no treatment at all: bd-version, gsd-capability,
  # phase-corroboration, phase-artifacts, external-ref, lease-stale,
  # release-versions, test-parallel, req-ledger, response-language,
  # phase-landed, plan-counters.
  #
  # The fix is an address, not a second copy: docs/commands/doctor.md already
  # carries one entry per id and ships inside the plugin (verified at
  # ~/.claude/plugins/cache/cairngo/cairn/1.5.0/docs/commands/doctor.md).
  # Copying it here would create the two-hand-lists shape of precedents 1-4.
  grep -qF "docs/commands/doctor.md" "$DOCTOR_PROMPT"
}

# ---------------------------------------------------------------------------
# CairnGo-q9l — the /cairn:help map derives BOTH halves
# ---------------------------------------------------------------------------

# Every installed command name, one per line — wrappers and cairn's own.
all_command_names() {
  bash "$WRAP" list --commands-dir "$1" --json \
    | jq -r '.commands[]'
}

@test "the help map names no command by hand, beyond the six prose names" {
  # MEASURED 2026-08-06 (CairnGo-q9l): commit aa48bb3 made the WRAPPER half of
  # the map derived and left cairn's own half typed — and that half had
  # already dropped a command:
  #     grep -c 'cairn:reconcile' cairn/commands/help.md  ->  0
  # while /cairn:reconcile existed, had a page, and had a row in the
  # reference. Nothing caught it: `docs --check` only looks at cairn/docs/,
  # and the suite only knew how to reject the opposite direction (a name in
  # the help that is not on disk).
  #
  # The allowlist below is the whole hand-written surface that survives, and
  # each name is there for a reason that is not "a listing":
  #   config, sync-config, context-config — the three-config-files section,
  #     required by name in tests/cairn-config.bats ("the three config
  #     commands are told apart in one place")
  #   new, migrate, status — the next-step routing rule in the opening
  #     paragraph, which is behaviour, not a map
  # Anything else means somebody typed the map back in.
  local help="$CAIRN_REPO_ROOT/cairn/commands/help.md"
  local allowed=" config sync-config context-config new migrate status "

  local name typed=""
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    case "$allowed" in *" $name "*) continue ;; esac
    if grep -qF -- "/cairn:$name" "$help"; then
      typed="$typed $name"
    fi
  done < <(all_command_names "$CAIRN_REPO_ROOT/cairn/commands")

  if [ -n "$typed" ]; then
    echo "the help map transcribes command name(s):$typed" >&2
    return 1
  fi
}

@test "the help map says where BOTH halves come from" {
  local help="$CAIRN_REPO_ROOT/cairn/commands/help.md"

  # The wrapper half (phase 26, aa48bb3) — kept.
  grep -qF 'cairn-wrap.sh" list' "$help"

  # The own half: the set difference, and the per-command fields that make a
  # rendered line possible without a list on this page.
  grep -qF '.wrappers[].command' "$help"
  grep -qF 'group:' "$help"
  grep -qF 'description:' "$help"

  # And the rule that keeps a new command visible even when its author
  # forgets the group key: wrong heading is allowed, missing is not.
  grep -qF 'OTHER' "$help"
}

@test "a command added to the disk appears in the map with no prose edited" {
  # The same proof by ADDITION that phase 26's verification ran for the
  # wrappers, now for cairn's own half: drop a file in, and the derivation
  # the help page reads reports it — with nobody editing help.md.
  local dir="$BATS_TEST_TMPDIR/probe-commands"
  mkdir -p "$dir"
  cp "$CAIRN_REPO_ROOT/cairn/commands/status.md" "$dir/status.md"
  cp "$CAIRN_REPO_ROOT/cairn/commands/phase.md" "$dir/phase.md"   # a wrapper
  cat > "$dir/zzz-probe.md" <<'EOF'
---
description: A probe command that exists only inside this test
group: view
---
body
EOF

  run bash "$WRAP" list --commands-dir "$dir" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.commands[] | select(. == "zzz-probe")] | length' '1'
  assert_json_eq "$output" '[.wrappers[] | select(.command == "zzz-probe")] | length' '0'

  # The two fields the page tells the agent to read are on the file itself.
  assert_frontmatter_key "$dir/zzz-probe.md" "group"
  assert_frontmatter_key "$dir/zzz-probe.md" "description"

  # And a file with NO group is still listed — it renders under OTHER, never
  # nowhere. This is the half that makes "invisible" impossible.
  cat > "$dir/zzz-groupless.md" <<'EOF'
---
description: A probe command whose author forgot the group key
---
body
EOF
  run bash "$WRAP" list --commands-dir "$dir" --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '[.commands[] | select(. == "zzz-groupless")] | length' '1'
}

@test "every command cairn owns declares the group it prints under" {
  # Not required for visibility — a groupless command still renders, under
  # OTHER. Required so that the shipped map reads as designed rather than
  # accumulating an OTHER pile nobody notices.
  local dir="$CAIRN_REPO_ROOT/cairn/commands"
  local listing; listing="$(bash "$WRAP" list --commands-dir "$dir" --json)"

  local name ungrouped=""
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    # Wrappers group by wrap-family, which cairn-wrap.py already enforces.
    if [ "$(jq -r --arg n "$name" \
        '[.wrappers[] | select(.command == $n)] | length' <<<"$listing")" != "0" ]; then
      continue
    fi
    grep -qE '^group: [a-z-]+$' "$dir/$name.md" || ungrouped="$ungrouped $name"
  done < <(jq -r '.commands[]' <<<"$listing")

  if [ -n "$ungrouped" ]; then
    echo "cairn command(s) with no group: key:$ungrouped" >&2
    return 1
  fi
}

# ---------------------------------------------------------------------------
# CairnGo-3w9 — a script with no door is invisible to the derived page
# ---------------------------------------------------------------------------

@test "the two phase-30 scripts have both doors" {
  # MEASURED 2026-08-07: phase 30 shipped cairn-land.py and cairn-review.py
  # with a .sh pair and a bats suite each, and neither had a /cairn:* command
  # or a page. Found while writing a routing string for /cairn:land — which
  # did not exist, so the string had to name the script instead.
  local name
  for name in land review; do
    [ -f "$CAIRN_REPO_ROOT/cairn/scripts/cairn-$name.py" ]
    [ -f "$CAIRN_REPO_ROOT/cairn/commands/$name.md" ]
    [ -f "$CAIRN_REPO_ROOT/cairn/docs/commands/$name.md" ]
    # And the command reaches the script it is a door onto.
    grep -qF "scripts/cairn-$name.sh" "$CAIRN_REPO_ROOT/cairn/commands/$name.md"
  done

  # Both are now in the derived listing, which is the half of WRAP-03 that
  # could not fire before: a script with no command is not listed BY
  # DEFINITION, so the derived page had no way to notice the absence.
  local listing
  listing="$(bash "$WRAP" list --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" --json)"
  assert_json_eq "$listing" '[.commands[] | select(. == "land")] | length' '1'
  assert_json_eq "$listing" '[.commands[] | select(. == "review")] | length' '1'
}

@test "every cairn script is reachable by command, or its absence is written down" {
  # The guard that makes the NEXT phase-30 loud. A script with no /cairn:*
  # command is not a defect by itself — most of these are invoked BY the
  # commands — but an unexamined one is exactly how land and review shipped
  # with no door. So every script is either a command or carries a reason
  # here, and a new script forces that decision instead of inheriting silence.
  #
  # MEASURED 2026-08-15 (GUARD-02): the sweep below globbed `cairn-*.py` and
  # six files walked past it — five carrying an underscore
  # (cairn_gsd_fact, cairn_gsd_parse, cairn_gsd_render, cairn_identity,
  # cairn_source) and one not starting with `cairn-` at all (gbsync). A
  # guard whose glob is narrower than the directory it guards is a guard
  # that a filename decides. So the glob is `*.py`: every python file under
  # cairn/scripts/ answers, and the naming style stops being an exemption.
  #
  # bash 3.2 (the macOS default) has no associative arrays — a case, then.
  # The reason is the payload: an entry with no sentence is not an entry.
  script_has_written_reason() {
    case "$1" in
      bookkeep) echo "the end-of-phase bookkeeping the loop commands invoke; contract at docs/commands/bookkeep.md, and named in the help page" ;;
      capability) echo "install-time plumbing for the GSD capability; invoked by /cairn:init and /cairn:migrate" ;;
      gate) echo "the deterministic milestone gate; invoked by /cairn:ship and /cairn:milestone complete" ;;
      gsd) echo "the python dispatcher answering the gsd-tools trivial-family verbs (phase 33); the workflows' gsd_run preamble points at it from phase 36 on — a runtime shim, not a project verb" ;;
      gsd-state) echo "the state sibling of the gsd dispatcher (phase 34, D-01): estado + roadmap-phase + planning-docs misc over bd; only ever exec'd BY cairn-gsd.py with the canonical verb — an implementation detail of the dispatcher, never a command" ;;
      gsd-init) echo "the init sibling of the gsd dispatcher (phase 34, D-01): worktree + init bundles + generic misc; only ever exec'd BY cairn-gsd.py — an implementation detail of the dispatcher, never a command" ;;
      gsd-check) echo "the checking sibling of the gsd dispatcher (phase 35, D-01): the checagem family + the CHECK-03 ex-orphans; only ever exec'd BY cairn-gsd.py with the canonical verb — an implementation detail of the dispatcher, never a command" ;;
      gsd-record) echo "the golden recorder for the gsd differential harness (phase 33); re-records tests/fixtures/gsd-goldens/ from the real pinned-tag binary — a maintainer measurement, not a project verb" ;;
      inventory) echo "the pinned-tag GSD corpus inventory the v1.6 remeasure feeds contracts from; a maintainer measurement, not a project verb" ;;
      jira) echo "Jira detection; invoked by /cairn:sync-config" ;;
      journal) echo "the append-only resume journal; invoked by /cairn:migrate and the parallel runner" ;;
      lease) echo "the phase lease; invoked by the loop commands and released by bookkeep" ;;
      map) echo "the generated phase-beads map; invoked by /cairn:plan, /cairn:work and bookkeep" ;;
      parallel) echo "the parallel phase runner; invoked by /cairn:autonomous" ;;
      preamble) echo "the vendored-preamble rewriter (phase 36, D-01): the one script that WRITES under cairn/gsd/, and only on the runtime-resolution line of paths registered in cairn/gsd-adaptations.json — transplant maintenance, not a project verb" ;;
      record) echo "the single write boundary of planning record (phase 38, v1.7): the prompt layer calls it instead of writing a planning document, and it writes the FACT to bd — a boundary the model crosses, never a verb a person runs" ;;
      relabel) echo "label maintenance; invoked by /cairn:phase and by the doctor's --fix-labels" ;;
      release) echo "release engineering for cairn's OWN repo; routed by the doctor's release-versions check" ;;
      test) echo "the bats suite runner for cairn's OWN repo; routed by the doctor's test-parallel check" ;;
      trend) echo "first-pass verdict history across cycles; a maintainer report, not a project verb" ;;
      stop) echo "the stop flag a running loop honours at its next boundary (phase 50): written by the board's stop action (or cairn-stop.sh request from a terminal) and read by /cairn:autonomous and /cairn:implement through cairn-stop.sh check, and by cairn-lease status and cairn-parallel batch as stop_requested — a signal file with one reader, never a session verb" ;;
      wrap) echo "the derivation tool itself; invoked by /cairn:help and by the docs regeneration" ;;

      # The six the `cairn-*.py` glob used to miss (GUARD-02). Five are
      # library modules — imported, never exec'd, no .sh wrapper by a
      # decision each one records in its own docstring — and the sixth has
      # a door under another name. The key keeps the filename's own shape:
      # `${name#cairn-}` does not strip an underscore, and it should not.
      cairn_gsd_render) echo "the MEASURED output envelope of the gsd binary, in ONE source (phase 34, D-01); imported by the three siblings cairn-gsd-state.py, cairn-gsd-init.py and cairn-gsd-check.py so they do not carry copies that can drift — a module, never a CLI, and its docstring says so" ;;
      cairn_gsd_parse) echo "the DOCUMENT substrate of the gsd binary (phase 38, CairnGo-2fyg): frontmatter, must_haves, PLAN tasks, CONTEXT decisions, the SUMMARY coverage block; imported by cairn-gsd-check.py and by cairn_gsd_fact.py, and it reaches no verdict — a module, no .sh" ;;
      cairn_gsd_fact) echo "the FACT substrate of the gsd binary (phase 38, CairnGo-2fyg): read-only git, bounded subprocess, drift classification, artifact audit; imported by cairn-gsd-check.py alone, split out because parse READS a document and this INTERROGATES the repo — a module, no .sh" ;;
      cairn_identity) echo "the two narrow identity conversions (collapse_home, machine_id) that cairn-journal.py and cairn-lease.py apply BEFORE writing a git-tracked file (CairnGo-xclf): the journal needs to tell two machines apart and never to name one; a library with no verb of its own, exercised through its two callers in tests/cairn-journal.bats and routed to by the doctor's identity finding" ;;
      cairn_source) echo "the project roadmap derived from bd (v1.7), replacing the ~25 markdown parsers that read ROADMAP.md; imported by cairn-map.py, cairn-gate.py, cairn-trend.py, cairn-doctor.py and cairn-status.py, and asserted directly by tests/cairn-roadmap-source.bats — the question about a phase arrives through those doors, never through a verb of its own" ;;
      gbsync) echo "the hub-and-spoke sync dispatcher (bd is the hub; push on bd lifecycle events, pull on demand, import for pre-existing external items); it HAS a door, under another name — /cairn:sync-pull runs gbsync.sh pull and /cairn:sync-config runs gbsync.sh import/update — plus the gbsync.sh wrapper, tests/gbsync.bats and cairn/docs/sync.md" ;;

      *) return 1 ;;
    esac
  }

  local path name undoored=""
  for path in "$CAIRN_REPO_ROOT"/cairn/scripts/*.py; do
    name="$(basename "$path" .py)"
    name="${name#cairn-}"
    [ -f "$CAIRN_REPO_ROOT/cairn/commands/$name.md" ] && continue
    script_has_written_reason "$name" >/dev/null && continue
    undoored="$undoored $name"
  done

  if [ -n "$undoored" ]; then
    echo "cairn script(s) with no /cairn: command and no written reason:$undoored" >&2
    echo "give it a command + a page, or add it to the table in this test with why" >&2
    return 1
  fi
}

@test "the command reference lists every command, and its block is current" {
  # The two new commands must have reached BOTH derived surfaces, not just the
  # help: a row in the reference and a page behind the link. This is the same
  # pair tests/cairn-wrap.bats guards for the whole page — asserted here too
  # because it is the acceptance of this issue, not a side effect.
  run bash "$WRAP" docs --check --json \
    --commands-dir "$CAIRN_REPO_ROOT/cairn/commands" \
    --doc "$CAIRN_REPO_ROOT/cairn/docs/commands.md" \
    --doc-pages-dir "$CAIRN_REPO_ROOT/cairn/docs/commands"
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.undocumented | length' '0'
  assert_json_eq "$output" '.missing_pages | length' '0'
}

# ---------------------------------------------------------------------------
# CairnGo-z320 (GUARD-03) — a cobertura estrutural E' o contrato pretendido
# ---------------------------------------------------------------------------
#
# POR QUE TREZE COMANDOS NAO TEM TESTE DE COMPORTAMENTO PROPRIO, e por que
# isso e' decisao e nao esquecimento.
#
# MEDIDO 2026-08-15: dos 40 comandos, 20 nao tem oraculo comportamental, e
# treze deles sao INDISTINGUIVEIS do ponto de vista de script — o unico
# executavel que o prompt manda rodar e' cairn-map.sh, o mesmo nos treze. O
# que separa /cairn:spec-phase de /cairn:ui-phase nao e' codigo: e' o texto
# que o modelo le. E prosa nao tem oraculo. Um teste que afirmasse o texto
# viraria assercao sobre redacao — quebra quando alguem melhora uma frase,
# e continua verde quando o comando para de fazer o que promete. Isso nao
# mede comportamento; mede que ninguem editou o arquivo.
#
# O QUE GARANTE NO LUGAR. Tres testes enumeram cairn/commands/*.md inteiro e
# portanto valem para os 40, estes treze inclusive:
#
#   - todo comando declara o `group` sob o qual imprime          (acima)
#   - o help e a referencia listam todo comando, com pagina atras do link
#     (acima; e o par completo em tests/cairn-wrap.bats)
#   - nenhum comando `inline` delega para fora, e todo `implementation:
#     vendored` aponta um arquivo que existe (tests/cairn-standalone.bats)
#
# Um comando destes nao pode, entao: sumir da superficie derivada, cair no
# monte OTHER, apontar para um arquivo que nao existe, nem delegar para um
# /gsd: que o standalone proibiu. Essa e' a cobertura, e ela e' o contrato
# PRETENDIDO — nao um degrau a caminho de um teste por comando.
#
# O QUE TERIA DE MUDAR para um deles merecer oraculo proprio: deixar de ser
# indistinguivel. No instante em que um destes prompts passa a mandar rodar
# qualquer coisa alem de cairn-map.sh, ele adquiriu comportamento observavel
# — exit code, saida, efeito — e passa a caber teste. O teste abaixo e'
# exatamente essa vigia: ele nao mede prosa, mede a indistincao, e reprova
# quando ela acaba.

@test "os comandos que so invocam cairn-map.sh sao exatamente os treze declarados" {
  # Nao e' uma lista de comandos "sem teste" — e' a lista dos que nao tem o
  # que testar. Sair dela e' o sinal, nos dois sentidos: quem entra herda a
  # decisao acima e precisa ser escrito aqui; quem sai ganhou um executavel
  # proprio e a pergunta "isto ja merece oraculo?" volta a valer.
  # Phase 46 esvaziou a lista de dez de uma vez: a familia phase (e plan,
  # verify) passou a gravar pelo cairn-record.sh, ganhou comportamento
  # observavel e um oraculo proprio — tests/cairn-record-commands.bats, que
  # mede em cada md o kind gravado e a ausencia de escrita em .planning/.
  local expected="cleanup new review-backlog"

  local file refs actual=""
  for file in "$CAIRN_REPO_ROOT"/cairn/commands/*.md; do
    refs="$(grep -oE '(cairn[-_][a-z_-]+|gbsync)\.(sh|py)' "$file" \
            | sort -u | tr '\n' ' ')"
    [ "$refs" = "cairn-map.sh " ] || continue
    actual="$actual $(basename "$file" .md)"
  done
  actual="$(printf '%s\n' $actual | LC_ALL=C sort | tr '\n' ' ')"
  actual="${actual# }"; actual="${actual% }"

  if [ "$actual" != "$expected" ]; then
    echo "the roster of map-only commands moved." >&2
    echo "  declared: $expected" >&2
    echo "  measured: $actual" >&2
    echo "a command that LEFT now runs something besides cairn-map.sh: it has observable behaviour, so ask whether it earns its own oracle, then update this list." >&2
    echo "a command that JOINED is newly indistinguishable: add it here, and read the block above for why it gets no test of its own." >&2
    return 1
  fi
}

# ---------------------------------------------------------------------------
# CairnGo-13t (FIX-01) — a step ordered at a moment it cannot run
# ---------------------------------------------------------------------------

@test "o mapa nao depende de diretorio de fase, e nenhuma superficie manda GERAR arquivo" {
  # ATE A v1.6 este par de casos media outra coisa: `cairn-map.sh <N>` saia 4
  # ("no phase directory matching phase N") quando a pasta da fase ainda nao
  # existia, e o defeito era a PROSA que ordenava a geracao no momento em que
  # nenhuma pasta existe — as pastas nasciam no plan-phase.
  #
  # A v1.7 dissolveu o defeito em vez de corrigi-lo de novo: o mapa deixou de
  # ser arquivo escrito numa pasta e virou vista impressa do bd. Uma fase e'
  # um label; nao precisa de pasta, e por isso nao ha momento errado para
  # perguntar. O que sobra para vigiar e' o verbo: nenhuma superficie pode
  # voltar a mandar ESCREVER o mapa.
  require_bd
  make_tmp_repo
  bd init -q --prefix fix01 --non-interactive >/dev/null 2>&1

  # sem .planning/, sem pasta de fase: a vista sai, exit 0
  run bash "$CAIRN_SCRIPTS_DIR/cairn-map.sh" 20
  [ "$status" -eq 0 ]
  grep -qF "Phase 20" <<<"$output"

  # e nenhuma superficie ordena escrever/gerar/regenerar um arquivo de mapa
  local hits
  hits="$(grep -rniE '(write|generate|regenerate|refresh)[^.]{0,40}(BEADS-MAP|phase map)' \
            "$CAIRN_REPO_ROOT/cairn/commands" "$CAIRN_REPO_ROOT/cairn/skills" \
            2>/dev/null || true)"
  if [ -n "$hits" ]; then
    echo "a surface still orders the map to be written:" >&2
    echo "$hits" >&2
    return 1
  fi
}

@test "controle negativo: uma superficie forjada que manda gerar o mapa E mordida" {
  local forged="$BATS_TEST_TMPDIR/forged-surface"
  mkdir -p "$forged"
  printf 'Then regenerate the phase map with cairn-map.sh <N>.\n' \
    > "$forged/x.md"
  run grep -rniE '(write|generate|regenerate|refresh)[^.]{0,40}(BEADS-MAP|phase map)' "$forged"
  [ "$status" -eq 0 ]
  grep -qF "regenerate the phase map" <<<"$output"
}
@test "no cairn command prompt writes a check count by hand" {
  # The guard against the five measured precedents. The doctor grows checks
  # every other phase — it goes from 21 to 22 in this very phase — so any
  # count written into a prompt is a lie with a delay on it.
  local file hits
  for file in "$CAIRN_REPO_ROOT"/cairn/commands/*.md; do
    # PLURAL only, on purpose: "at least one check failed" is a sentence
    # about a run, not a count of the set. "nineteen checks", "the 21
    # checks", "18 checks in total" are the defect.
    hits="$(grep -niE '\<(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|twenty-one|twenty-two|[0-9]+)[ -]+(doctor )?checks\>' "$file" || true)"
    if [ -n "$hits" ]; then
      echo "a hand-written check count in $file:" >&2
      echo "$hits" >&2
      return 1
    fi
  done
}
