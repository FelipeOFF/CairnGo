#!/usr/bin/env bats
# cairn-reconcile-agent.bats — structural/static proof for Plan 17-02's
# tool-restricted investigator subagent (cairn/agents/reconcile-investigator.md)
# and the /cairn:reconcile command (cairn/commands/reconcile.md) that
# orchestrates it. Bats never invokes a real LLM subagent (no such precedent
# exists anywhere in this test suite), so every check here is a STATIC
# assertion against the two committed artifacts' text — meaningful, not
# vacuous, because it asserts the actual declared capability boundary (which
# tools the harness will grant) and the actual committed step order, not
# merely "the file exists".
#
# The write-capable-tools check is the one this plan's own plan-check
# blocker landed on directly: a first draft that only grepped for the
# absence of Bash/Edit would have missed an unscoped Write grant entirely.
# The fix here asserts the FULL write-capable set (Write, Edit, Bash,
# NotebookEdit) is absent from the tools: line specifically — never the
# whole file, since the file's own prose talks ABOUT Write at length to
# explain why it's excluded, and grepping the whole file for "Write" would
# always find it there and falsely fail.
#
# The step-ordering check is a PROXY, not a full proof: bats cannot spawn
# the Task tool, so it cannot prove a live run of /cairn:reconcile actually
# respects this order at runtime — only that the command's own committed
# prose mentions each anchor in the right sequence. The load-bearing,
# mechanically-proven half of ESC-04's gate is Plan 17-01's own `collect`
# refusal (tests/cairn-reconcile.bats), not this file. Do not read a green
# run here as equivalent proof to that one.
#
# Assertion style note (inherited from tests/cairn-reconcile.bats): a
# failing `[[ ]]` or `! cmd` mid-test does NOT reliably fail a bats test on
# this bash, so every check below uses plain `[ ]` against a `run`-captured
# `$status`/`$output`, never a bare negated command.

load 'helpers'

AGENT_FILE="$CAIRN_REPO_ROOT/cairn/agents/reconcile-investigator.md"
COMMAND_FILE="$CAIRN_REPO_ROOT/cairn/commands/reconcile.md"

# The full write-capable tool set — not just the two (Bash, Edit) the
# plan-check's original target named. Any one of these present in the
# tools: line is a failure.
# ctx_purge destroys the context-mode knowledge base, so it belongs in this
# set even though it is an MCP tool rather than a core one. The naive way to
# grant memory access here would have been the glob other agents use
# (mcp__<server>__*), which would have handed this agent ctx_purge along with
# ctx_search — a destructive write inside the one agent whose whole point is
# having no write at all. The grant names ctx_search and nothing else.
WRITE_CAPABLE="Write Edit Bash NotebookEdit ctx_purge"

# The exact grant Task 1 declared: Read/Grep/Glob always, ctx_search only
# if a future revision confirms its real MCP tool name — never a name
# guessed today.
ALLOWED_TOOLS="Read Grep Glob mcp__plugin_context-mode_context-mode__ctx_search"

tools_line() {
  grep "^tools:" "$AGENT_FILE" | sed 's/^tools:[[:space:]]*//'
}

anchor_line() {
  grep -n -- "$1" "$COMMAND_FILE" | head -1 | cut -d: -f1
}

#-----------------------------------------------------------------------------
# Task 1 — the tool grant itself: zero write-capable tools, and nothing
# beyond the declared allowed set.
#-----------------------------------------------------------------------------

@test "agent: reconcile-investigator.md exists and declares exactly one tools: frontmatter line" {
  [ -f "$AGENT_FILE" ]
  run bash -c "grep -c '^tools:' '$AGENT_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]
}

@test "agent: tools: grant contains NONE of the full write-capable set (Write, Edit, Bash, NotebookEdit) -- not merely the two the plan-check named" {
  local line tool
  line="$(tools_line)"
  [ -n "$line" ]

  for tool in $WRITE_CAPABLE; do
    run bash -c "grep -cw -- '$tool' <<< '$line'"
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
    [ "$output" -eq 0 ]
  done
}

@test "agent: tools: grant is a non-empty subset of {Read, Grep, Glob, ctx_search} -- proves the grant is exactly what Task 1 declared, not merely 'missing the bad ones'" {
  local line
  line="$(tools_line)"
  [ -n "$line" ]

  local -a granted
  IFS=',' read -ra granted <<< "$line"
  [ "${#granted[@]}" -gt 0 ]

  local raw trimmed allowed found
  for raw in "${granted[@]}"; do
    trimmed="$(echo "$raw" | tr -d '[:space:]')"
    [ -n "$trimmed" ]
    found=0
    for allowed in $ALLOWED_TOOLS; do
      if [ "$trimmed" = "$allowed" ]; then
        found=1
      fi
    done
    [ "$found" -eq 1 ]
  done
}

#-----------------------------------------------------------------------------
# Task 1 — the body documents the write-incapacity in prose too, not just
# in the frontmatter (a leftover-prose bug the frontmatter check alone
# would miss: a corrected tools: line with a body that still instructs
# writing a file).
#-----------------------------------------------------------------------------

@test "agent: body states it never writes any file, naming /cairn:reconcile as the sole writer of conflicts.json" {
  run bash -c "grep -cF -- 'You never write \`.cairn/conflicts.json\` or any other file.' '$AGENT_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]

  run bash -c "grep -cF -- 'is the sole writer of that file' '$AGENT_FILE'"
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]
}

#-----------------------------------------------------------------------------
# Task 2 — command step order: gate -> cache -> collect -> spawn -> write
# -> verify -> present, proxy-tested via each anchor's first line number
# (see header comment: this is a proxy, not a runtime proof).
#-----------------------------------------------------------------------------

@test "command: reconcile.md exists" {
  [ -f "$COMMAND_FILE" ]
}

@test "command: corroboration gate precedes collect, precedes the subagent spawn, precedes the command's own conflicts.json write, precedes verify, precedes apply-reconciliation" {
  local l_corrob l_collect l_spawn l_write l_verify l_apply
  l_corrob="$(anchor_line 'corroboration')"
  l_collect="$(anchor_line 'collect')"
  l_spawn="$(anchor_line 'reconcile-investigator')"
  l_write="$(anchor_line 'conflicts.json')"
  l_verify="$(anchor_line 'verify')"
  l_apply="$(anchor_line 'apply-reconciliation')"

  [ -n "$l_corrob" ]
  [ -n "$l_collect" ]
  [ -n "$l_spawn" ]
  [ -n "$l_write" ]
  [ -n "$l_verify" ]
  [ -n "$l_apply" ]

  [ "$l_corrob" -lt "$l_collect" ]
  [ "$l_collect" -lt "$l_spawn" ]
  [ "$l_spawn" -lt "$l_write" ]
  [ "$l_write" -lt "$l_verify" ]
  [ "$l_verify" -lt "$l_apply" ]
}

#-----------------------------------------------------------------------------
# Both files — the prose layer's own version of the collector's ESC-02
# guarantee: no direct bd write invocation anywhere in this command's or
# this agent's own committed text (mirrors Plan 17-01's script-level
# static check, one layer up).
#-----------------------------------------------------------------------------

@test "static: neither reconcile.md nor reconcile-investigator.md instructs a direct bd write (bd create/update/close/reopen)" {
  local verb
  for verb in "bd create" "bd update" "bd close" "bd reopen"; do
    run bash -c "grep -v '^#' '$COMMAND_FILE' | grep -cF -- '$verb'"
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
    [ "$output" -eq 0 ]

    run bash -c "grep -v '^#' '$AGENT_FILE' | grep -cF -- '$verb'"
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
    [ "$output" -eq 0 ]
  done
}
