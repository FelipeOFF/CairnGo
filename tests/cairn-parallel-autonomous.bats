#!/usr/bin/env bats
# cairn-parallel-autonomous.bats — static proof over the committed PROSE of
# /cairn:autonomous (cairn/commands/autonomous.md) and its documentation page
# (cairn/docs/commands/autonomous.md), which in this repo is contract rather
# than description.
#
# WHAT THIS FILE CANNOT PROVE, said first because it is the point.
# No bats run can show that two LLM subagents executed at the same time: what
# spawns an agent here is prose read by a model, and there is no seam in this
# suite that fakes one (the same limit tests/cairn-reconcile-agent.bats records
# for its own subagent). So the concurrency half of PAR-01 is NOT under test
# here and a green run must never be read as evidence of it. The mechanically
# proven half lives in tests/cairn-parallel.bats (31 tests): that `batch`
# consumes cairn-status.py's parallelism() instead of recomputing independence
# — proven by a CAIRN_STATUS stub whose `runnable` deliberately contradicts the
# fixture's ROADMAP — and that what `batch` announces as branch/worktree is
# byte-for-byte what `prepare` creates, proven by running both verbs over two
# phases and comparing by realpath. Plans 18-01 through 18-03 carry the rest:
# worktree isolation, lease refusal, convergent-edit detection, orphan cleanup.
#
# WHAT IS MEANINGFUL HERE, and it is not "the file exists".
# The prose is the only thing standing between a parallel agent and the three
# shared planning files, and the only thing that puts the reconciliation report
# in front of a human before a merge. Text is the actual mechanism for those,
# so asserting the text is asserting the mechanism:
#   - the parallel default is declared and `--sequential` is the named way out
#     (D-04: parallel by default, announced before starting);
#   - the four verbs appear in execution order, and planning-in-the-main-
#     checkout precedes `prepare` (a phase planned inside its worktree would
#     have GSD write ROADMAP.md there, breaking D-03 on its first step);
#   - the three forbidden paths appear LITERALLY inside the delimited subagent
#     prompt block — not merely somewhere in the file, where a paragraph
#     discussing them would satisfy a naive grep;
#   - `planning_writes` is shown to the operator even at exit 0, anchored on
#     that sentence rather than on the verb `reconcile`, because reconcile is
#     named several times and only this sentence carries the rule;
#   - the announcement names the `--max` ceiling in force, anchored INSIDE the
#     announcement step by line number;
#   - none of the four merge-strategy invocations that pick a winner in silence
#     appears in either file — eight separate checks, one chain per file, so a
#     failure says which chain in which file.
# The step-ordering and prompt-content checks are PROXIES for runtime
# behaviour, in the same sense as tests/cairn-reconcile-agent.bats: they prove
# what the committed artifact says, never what a live run does.
#
# The negative grep is self-invalidating if the prose spells the forbidden
# flags out — even to forbid them. That is why both files state the
# prohibition in words and name at most the bare values. The lesson is
# inherited from cairn-parallel.py's own read-only-region check, which filters
# comment lines first for exactly this reason.
#
# Assertion style note (inherited from the rest of this suite): a failing
# `[[ ]]` or `! cmd` mid-test does NOT reliably fail a bats test on this bash,
# so every check below is a plain `[ ]` against a `run`-captured
# `$status`/`$output`, or an integer comparison of line numbers captured by a
# helper.

load 'helpers'

COMMAND_FILE="$CAIRN_REPO_ROOT/cairn/commands/autonomous.md"
DOC_FILE="$CAIRN_REPO_ROOT/cairn/docs/commands/autonomous.md"

# The four invocations that resolve a conflict by preferring one side without
# telling anyone. Checked against BOTH files: the doc page is contract here,
# and an "illustrative" example carrying one of these is exactly where somebody
# would copy it from.
FORBIDDEN_MERGE_FLAGS=("-X ours" "-X theirs" "--strategy=ours" "-s ours")

# First line number of a fixed string in a file, empty when absent.
anchor_line() {
  grep -nF -- "$2" "$1" | head -1 | cut -d: -f1
}

# The delimited subagent prompt block, so "the prompt says X" is a claim about
# the prompt and not about the whole document.
prompt_block() {
  sed -n '/SUBAGENT-PROMPT-BEGIN/,/SUBAGENT-PROMPT-END/p' "$COMMAND_FILE"
}

#-----------------------------------------------------------------------------
# The two artifacts.
#-----------------------------------------------------------------------------

@test "autonomous: both the command and its documentation page exist" {
  [ -f "$COMMAND_FILE" ]
  [ -f "$DOC_FILE" ]
}

#-----------------------------------------------------------------------------
# D-04 — parallel by default, with a named way out. A default that has to be
# opted into is the opposite decision.
#-----------------------------------------------------------------------------

@test "command: declares parallel execution as the default and names --sequential as the way out" {
  run bash -c "grep -cF -- 'Parallel execution is the default' '$COMMAND_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  run bash -c "grep -cF -- '\`--sequential\` is the named way out' '$COMMAND_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

#-----------------------------------------------------------------------------
# The loop's shape: batch -> plan centrally -> prepare -> reconcile -> cleanup.
# Planning before prepare is the load-bearing one: /gsd:plan-phase writes
# ROADMAP.md, so a phase planned inside its own worktree breaks D-03 before it
# executes a single task.
#-----------------------------------------------------------------------------

@test "command: the four cairn-parallel verbs appear in execution order, with planning in the main checkout before prepare" {
  local l_batch l_plan l_prepare l_reconcile l_cleanup
  l_batch="$(anchor_line "$COMMAND_FILE" 'parallel.sh" batch --json')"
  l_plan="$(anchor_line "$COMMAND_FILE" 'in the main checkout, one phase at a time')"
  l_prepare="$(anchor_line "$COMMAND_FILE" 'parallel.sh" prepare "$N"')"
  l_reconcile="$(anchor_line "$COMMAND_FILE" 'parallel.sh" reconcile --json')"
  l_cleanup="$(anchor_line "$COMMAND_FILE" 'parallel.sh" cleanup --apply')"

  [ -n "$l_batch" ]
  [ -n "$l_plan" ]
  [ -n "$l_prepare" ]
  [ -n "$l_reconcile" ]
  [ -n "$l_cleanup" ]

  [ "$l_batch" -lt "$l_plan" ]
  [ "$l_plan" -lt "$l_prepare" ]
  [ "$l_prepare" -lt "$l_reconcile" ]
  [ "$l_reconcile" -lt "$l_cleanup" ]
}

#-----------------------------------------------------------------------------
# D-03 — the prohibition has to be IN the subagent's prompt, because the prompt
# is the whole mechanism. A sentence about it elsewhere in the file protects
# nothing.
#-----------------------------------------------------------------------------

@test "command: the subagent prompt block names all three forbidden planning files literally" {
  local l_begin l_end
  l_begin="$(anchor_line "$COMMAND_FILE" 'SUBAGENT-PROMPT-BEGIN')"
  l_end="$(anchor_line "$COMMAND_FILE" 'SUBAGENT-PROMPT-END')"
  [ -n "$l_begin" ]
  [ -n "$l_end" ]
  [ "$l_begin" -lt "$l_end" ]

  local path
  for path in ".planning/STATE.md" ".planning/ROADMAP.md" ".planning/REQUIREMENTS.md"; do
    run bash -c "sed -n '/SUBAGENT-PROMPT-BEGIN/,/SUBAGENT-PROMPT-END/p' '$COMMAND_FILE' | grep -cF -- '$path'"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
  done
}

#-----------------------------------------------------------------------------
# LANG-02 (plan 24-01) — the response language has to be IN the prompt, for
# the same reason the three forbidden files do: the prompt is the mechanism.
#
# The measured defect: in the v1.4 cycle every subagent this step spawned
# answered in English against an all-Portuguese plan, WITH
# `.planning/config.json:response_language` already set to `pt-BR`. The value
# existed; the hand-over did not. GSD's own standard directive says it out
# loud in ~30 workflows — "subagent prompts stay in English" — and exactly one
# file (references/execute-phase-response-language.md) says the opposite. So
# the hand-over is not something to assume; it is something to write here and
# assert on.
#
# The machine half of this proof — the value coming out of `prepare --json` —
# lives in tests/cairn-parallel.bats. Neither half claims the model actually
# pasted it: bats cannot spawn the Task tool (the same boundary
# cairn/commands/reconcile.md:29-31 records for its own gate).
#-----------------------------------------------------------------------------

@test "command: the subagent prompt block names the response language and where the value comes from" {
  # Breaks if the item drifts out of the delimited block into loose prose
  # elsewhere in the file — which phase 18-04 established as not being proof.
  run bash -c "sed -n '/SUBAGENT-PROMPT-BEGIN/,/SUBAGENT-PROMPT-END/p' '$COMMAND_FILE' | grep -cF -- 'response_language'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  # Breaks if somebody replaces it with "answer in the project's language",
  # which is the remembered instruction that already failed once.
  run bash -c "sed -n '/SUBAGENT-PROMPT-BEGIN/,/SUBAGENT-PROMPT-END/p' '$COMMAND_FILE' | grep -cF -- 'copied literally'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  # And the boundary: translating a path or an id would break the very
  # reconciliation the report feeds.
  run bash -c "sed -n '/SUBAGENT-PROMPT-BEGIN/,/SUBAGENT-PROMPT-END/p' '$COMMAND_FILE' | grep -cF -- 'file paths, commands and bd ids stay'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

@test "command: the count the prompt block declares matches the number of items it actually carries" {
  local declared items
  # "carries all six of these" — the word, not a digit, which is how the file
  # writes it.
  run bash -c "sed -n '/SUBAGENT-PROMPT-BEGIN/,/SUBAGENT-PROMPT-END/p' '$COMMAND_FILE' | grep -cF -- 'carries all six of these'"
  [ "$status" -eq 0 ]
  declared="$output"
  [ "$declared" -eq 1 ]

  # Every item is a top-level bullet opening with a bold label.
  run bash -c "sed -n '/SUBAGENT-PROMPT-BEGIN/,/SUBAGENT-PROMPT-END/p' '$COMMAND_FILE' | grep -c '^- \*\*'"
  [ "$status" -eq 0 ]
  items="$output"
  # Breaks when a seventh item lands and the sentence still says six — the
  # kind of quiet disagreement between a count and its list that this project
  # treats as a defect rather than a typo.
  [ "$items" -eq 6 ]
}

@test "command: step 2 names response_language among the fields prepare prints" {
  # The assembler can only copy a field it has been told exists.
  run bash -c "grep -cF -- '\`planning_files_forbidden\` and' '$COMMAND_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  local l_prepare l_lang
  l_prepare="$(anchor_line "$COMMAND_FILE" 'parallel.sh" prepare "$N"')"
  l_lang="$(anchor_line "$COMMAND_FILE" '`response_language`.')"
  [ -n "$l_prepare" ]
  [ -n "$l_lang" ]
  [ "$l_prepare" -lt "$l_lang" ]
}

@test "doc: the documentation page also says the subagent is handed its response language" {
  run bash -c "grep -cF -- 'response_language' '$DOC_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

#-----------------------------------------------------------------------------
# T-18-16 — no merge strategy that picks a winner in silence, in EITHER file.
# Eight checks rather than two loops over a joined blob, so the failure names
# the chain and the file.
#-----------------------------------------------------------------------------

@test "static: neither the command nor its doc page contains a merge-strategy flag that resolves a conflict automatically" {
  local file flag
  for file in "$COMMAND_FILE" "$DOC_FILE"; do
    for flag in "${FORBIDDEN_MERGE_FLAGS[@]}"; do
      run bash -c "grep -cF -- '$flag' '$file'"
      [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
      if [ "$output" -ne 0 ]; then
        echo "forbidden merge-strategy chain '$flag' appears $output time(s) in $file"
        return 1
      fi
    done
  done
}

#-----------------------------------------------------------------------------
# Stop rules: reconcile exit 6 halts the run; one parallel phase failing does
# not. Both directions matter — the first keeps an unreviewed merge from
# happening, the second keeps three good phases from being thrown away because
# a fourth broke (PAR-05).
#-----------------------------------------------------------------------------

@test "command: reconcile exit 6 is a stop rule, and one parallel phase failing is explicitly not one" {
  run bash -c "grep -cF -- 'Exit 6 is a stop rule' '$COMMAND_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  run bash -c "grep -cF -- 'The failure of one parallel phase does not stop the others' '$COMMAND_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

#-----------------------------------------------------------------------------
# The one check that keeps D-03's detection from being detection nobody reads.
# `reconcile` reports a planning-file write WITHOUT moving the exit code (the
# failing variant is deferred), so prose that reacts only to exit 6 lets a
# violation through on any run that is otherwise clean. Anchored on the
# sentence, never on the verb: `reconcile` appears many times and only this
# sentence carries the rule.
#-----------------------------------------------------------------------------

@test "command: planning_writes is presented to the operator even when reconcile exits 0" {
  run bash -c "grep -cF -- '\`planning_writes\` is presented to the operator even when the exit is 0' '$COMMAND_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

#-----------------------------------------------------------------------------
# The ceiling, inside the announcement step. Under D-04 the announcement is the
# moment the operator interrupts, and a discretionary ceiling they cannot see
# makes "two phases run" indistinguishable from "five were free and three were
# cut". Bounded by line number so the anchor cannot drift into some other
# section and still pass.
#-----------------------------------------------------------------------------

@test "command: the announcement step names the --max ceiling in force and how to change it" {
  local l_announce l_loop l_ceiling l_howto
  l_announce="$(anchor_line "$COMMAND_FILE" '**Announce the run before anything is created.**')"
  l_loop="$(anchor_line "$COMMAND_FILE" '## The loop')"
  l_ceiling="$(anchor_line "$COMMAND_FILE" 'Name the ceiling in force')"
  l_howto="$(anchor_line "$COMMAND_FILE" '`--max N` raises or lowers it')"

  [ -n "$l_announce" ]
  [ -n "$l_loop" ]
  [ -n "$l_ceiling" ]
  [ -n "$l_howto" ]

  [ "$l_announce" -lt "$l_ceiling" ]
  [ "$l_ceiling" -lt "$l_loop" ]
  [ "$l_howto" -lt "$l_loop" ]
}

#-----------------------------------------------------------------------------
# Documentation-as-Contract: the page is loaded as contract in this repo, so a
# doc that still describes a sequential-only command is a false contract, not a
# stale sentence.
#-----------------------------------------------------------------------------

@test "doc: the documentation page carries the parallel default and lists --sequential in its flags table" {
  run bash -c "grep -cF -- 'Parallel execution is the default' '$DOC_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]

  run bash -c "grep -c '^| \`--sequential\` |' '$DOC_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]

  run bash -c "grep -c '^| \`--max N\` |' '$DOC_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]
}
