#!/usr/bin/env bats
load 'helpers'

@test "only hyphen cairn-* command files exist" {
  local n
  n="$(find "$CAIRN_REPO_ROOT/cairn/commands" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
  [ "$n" = "6" ]
  for f in cairn-init cairn-implement cairn-status cairn-doctor cairn-sync-config cairn-sync-pull; do
    [ -f "$CAIRN_REPO_ROOT/cairn/commands/${f}.md" ]
  done
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

@test "plugin.json is 5.0.0 without context-mode dependency" {
  python3 - "$CAIRN_REPO_ROOT/cairn/.claude-plugin/plugin.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
assert p["version"]=="5.0.0"
deps=p.get("dependencies") or []
assert not any((d.get("name") if isinstance(d,dict) else d)=="context-mode" for d in deps)
PY
}
