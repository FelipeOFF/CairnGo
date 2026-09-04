#!/usr/bin/env bats
load 'helpers'

@test "hyphenated command files and Claude short aliases both exist" {
  local cmd="$CAIRN_REPO_ROOT/cairn/commands"
  local pair
  for pair in init implement status doctor sync-config sync-pull grill; do
    [ -f "$cmd/cairn-${pair}.md" ]
    [ -f "$cmd/${pair}.md" ]
    grep -q "cairn-${pair}.md" "$cmd/${pair}.md"
  done
}

@test "cairn-implement refuses a raw idea and names cairn-grill" {
  grep -q '/cairn-grill' "$CAIRN_REPO_ROOT/cairn/commands/cairn-implement.md"
  grep -qF 'does **not** interview a raw idea' "$CAIRN_REPO_ROOT/cairn/commands/cairn-implement.md"
  grep -qF 'Do **not** implement code' "$CAIRN_REPO_ROOT/cairn/commands/cairn-grill.md"
  grep -qF 'Do **not** create tickets' "$CAIRN_REPO_ROOT/cairn/commands/cairn-grill.md"
}

@test "cairn-grill asks through AskUserQuestion and ask_user_question" {
  local f="$CAIRN_REPO_ROOT/cairn/commands/cairn-grill.md"
  grep -qF 'AskUserQuestion' "$f"
  grep -qF 'ask_user_question' "$f"
  grep -qF 'not in chat prose' "$f"
}

@test "skill cairn names hyphenated, Claude short, and doubled forms" {
  local f="$CAIRN_REPO_ROOT/cairn/skills/cairn/SKILL.md"
  grep -q '/cairn-grill' "$f"
  grep -q '/cairn-implement' "$f"
  grep -q '/cairn:init' "$f"
  grep -q '/cairn:cairn-init' "$f"
}

@test "commands.md lists hyphenated and Claude short names, not the GSD zoo" {
  local f="$CAIRN_REPO_ROOT/cairn/docs/commands.md"
  grep -qF '| `/cairn-grill [ref]` |' "$f"
  grep -qF '| `/cairn-implement [ref]` |' "$f"
  grep -q '| `/cairn:grill` |' "$f"
  grep -q '| `/cairn:implement` |' "$f"
  grep -q 'grok plugin update' "$f"
  run grep -E '\| `/cairn:plan` \||\| `/cairn:migrate` \|' "$f"
  [ "$status" -ne 0 ]
}

@test "skill cairn does not teach phase-N as the loop" {
  run grep -E 'phase-<N>|phase-N|/cairn:plan' "$CAIRN_REPO_ROOT/cairn/skills/cairn/SKILL.md"
  [ "$status" -ne 0 ]
  grep -q '/cairn-implement' "$CAIRN_REPO_ROOT/cairn/skills/cairn/SKILL.md"
}

@test "matt-on-beads treats CONTEXT.md as an error" {
  grep -q 'CONTEXT.md is an error' "$CAIRN_REPO_ROOT/cairn/references/matt-on-beads.md"
}

@test "cairn-root.sh falls back to this checkout" {
  run bash "$CAIRN_REPO_ROOT/cairn/scripts/cairn-root.sh"
  [ "$status" -eq 0 ]
  [ "$output" = "$CAIRN_REPO_ROOT/cairn" ]
}

@test "cairn-root.sh prefers CAIRN_PLUGIN_ROOT" {
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/scripts"
  cp "$CAIRN_REPO_ROOT/cairn/scripts/cairn-root.sh" "$tmp/scripts/"
  CAIRN_PLUGIN_ROOT="$tmp" run bash "$CAIRN_REPO_ROOT/cairn/scripts/cairn-root.sh"
  [ "$status" -eq 0 ]
  [ "$output" = "$(cd "$tmp" && pwd)" ]
}

@test "cairn-init writes plugin-root and docs/agents" {
  make_tmp_repo
  run bash "$CAIRN_REPO_ROOT/cairn/scripts/cairn-init.sh" "$PWD"
  [ "$status" -eq 0 ]
  [ -d .beads ]
  [ -f .cairn/plugin-root ]
  [ -f docs/agents/issue-tracker.md ]
  [ -f docs/agents/triage-labels.md ]
  grep -q beads docs/agents/issue-tracker.md
}

@test "v5 doctor does not fail a spec+ticket repo for missing phase-N" {
  make_tmp_repo
  bash "$CAIRN_REPO_ROOT/cairn/scripts/cairn-init.sh" "$PWD"
  spec="$(bd create --title=spec --type=epic --silent --metadata '{"cairn":{"kind":"spec"}}')"
  bd create --title=ticket --type=task --parent="$spec" --silent --metadata '{"cairn":{"kind":"ticket"}}'
  run bash "$CAIRN_REPO_ROOT/cairn/scripts/cairn-doctor.sh" --project-dir "$PWD"
  [ "$status" -eq 0 ]
  run bash "$CAIRN_REPO_ROOT/cairn/scripts/cairn-doctor.sh" --project-dir "$PWD" --json
  python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); assert d["ok"]' <<<"$output"
}

@test "plugin.json is 5.1.0 without context-mode dependency" {
  python3 - "$CAIRN_REPO_ROOT/cairn/.claude-plugin/plugin.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
assert p["version"]=="5.1.0"
deps=p.get("dependencies") or []
assert not any((d.get("name") if isinstance(d,dict) else d)=="context-mode" for d in deps)
PY
}
