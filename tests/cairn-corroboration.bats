#!/usr/bin/env bats
# cairn-corroboration.bats — the corroboration engine phase_model() feeds
# from four independent reads (disk, bd, the ROADMAP checkbox, STATE.md's
# active_phase): bd_state(), corroborate(), the additive evidence/
# corroboration/conflicts/needs_doctor keys, phase_next_command()'s and
# next_commands()'s shared needs_doctor guard, and main()'s bd-unreachable
# fail-open degrade (CORR-01..CORR-04).
#
# Two test styles are mixed deliberately:
#   - CLI-level tests (`run bash "$STATUS_SH" ...`) exercise the real
#     end-to-end path through main(), exactly like cairn-status.bats and
#     cairn-phase-model.bats.
#   - Direct-call tests exec cairn-status.py as a python module (see
#     PY_LOAD below) to reach states the CLI cannot produce yet: bd_ok is a
#     single flag for one whole phase_model() call (a real bd outage is
#     global, not per-phase, by design — D-07), so a fixture with ONE phase
#     "ok" and another "unknown" cannot exist through main() alone. Those
#     tests call corroborate()/bd_state()/next_commands() directly instead,
#     isolating "does the consumer read needs_doctor correctly" from "does
#     a live bd outage compute unknown correctly" (the latter is proven
#     end-to-end by the forced-bd-failure CLI tests near the bottom).
#
# Assertion style note (same as cairn-status.bats and cairn-phase-model.bats):
# a failing `[[ ]]` mid-test does NOT fail a bats test on this bash, so
# substring checks use grep -qF. Structural JSON/model assertions run as
# BARE `python3 -c` pipelines (no `run` wrapper): a raised AssertionError
# exits nonzero, which fails the bats test the same way `set -e` would —
# `run` is used only where a specific exit code ($status) itself is the
# thing under test.

load 'helpers'

STATUS_SH="$CAIRN_REPO_ROOT/cairn/scripts/cairn-status.sh"
CAIRN_STATUS_PY="$CAIRN_SCRIPTS_DIR/cairn-status.py"

# Every direct-call python3 snippet execs this first: loads cairn-status.py
# as a module named cairn_status (not "__main__", so its own
# `if __name__ == "__main__": main()` guard never fires) without needing a
# normal `import` on a hyphenated filename.
PY_LOAD="
import importlib.util
spec = importlib.util.spec_from_file_location('cairn_status', '$CAIRN_STATUS_PY')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)
"

# Read one field of one phase out of --json (copied from
# tests/cairn-phase-model.bats — same helper, same contract). Booleans and
# other non-list/dict scalars print via Python's own str(), so a bool comes
# back "True"/"False" — prefer a python3 pipeline over this helper for
# boolean fields like needs_doctor.
phase_field() {
  python3 -c '
import json, sys
doc = json.load(sys.stdin)
n, key = int(sys.argv[1]), sys.argv[2]
for p in doc["phases"]:
    if p["number"] == n:
        v = p[key]
        print(json.dumps(v) if isinstance(v, (list, dict)) else ("" if v is None else v))
        sys.exit(0)
sys.exit("phase %d not in model" % n)
' "$1" "$2"
}

# A minimal 2-phase roadmap for corroboration fixtures: both phases
# unchecked, neither has a phase directory yet. Individual tests tick a
# checkbox and/or create a phase directory to build the exact disk/roadmap
# combination under test.
write_corr_roadmap() {
  mkdir -p .planning
  cat > .planning/ROADMAP.md <<'EOF'
# Roadmap: Corroboration Fixture

## Phases

- [ ] Phase 1: First phase
- [ ] Phase 2: Second phase
EOF
}

# A `bd` stub that IS present on PATH but fails every invocation with a
# nonzero exit — a REAL subprocess failure (present, then broken), distinct
# from tests/cairn-status.bats's "bd missing from PATH" test (bd absent
# entirely — a different failure shape this engine must not confuse with a
# broken query). Prints the stub's directory; callers prepend it to PATH.
make_failing_bd_stub() {
  local stub="$BATS_TEST_TMPDIR/failing-bd-bin"
  mkdir -p "$stub"
  cat > "$stub/bd" <<'EOF'
#!/usr/bin/env bash
echo "bd: simulated database failure" >&2
exit 9
EOF
  chmod +x "$stub/bd"
  printf '%s' "$stub"
}

# ─── R1: disk vs bd (severity blocks) ────────────────────────────────────────

@test "disk-vs-bd disagreement is a blocks conflict naming both sides" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  # Phase 2 already has a SUMMARY (disk says "executed"); bd still shows its
  # own issue open — the two direct, artifact-backed reads disagree.
  touch .planning/phases/02-api/02-01-SUMMARY.md
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1
  bd create "phase 2 still open" -t task -l phase-2 --silent >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 2 corroboration)" = "conflict" ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
p = [x for x in d["phases"] if x["number"] == 2][0]
items = [c for c in p["conflicts"]
         if c["severity"] == "blocks" and c["sources"] == ["disk", "bd"]]
assert len(items) == 1, p["conflicts"]
detail = items[0]["detail"]
# Never one side chosen silently: both the disk claim and the bd claim
# must be nameable in the same string.
assert "executed" in detail or "verified" in detail, detail
assert "open" in detail, detail
assert p["needs_doctor"] is True, p
'
}

# ─── R2: roadmap vs disk (severity blocks) ───────────────────────────────────

@test "roadmap-vs-disk disagreement is a blocks conflict even with zero bd issues" {
  require_bd
  make_tmp_repo
  write_corr_roadmap
  sed -i.bak 's/^- \[ \] Phase 1/- [x] Phase 1/' .planning/ROADMAP.md
  rm -f .planning/ROADMAP.md.bak
  # No phase directory at all for phase 1: the checkbox claims done, disk
  # has nothing built.
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 1 corroboration)" = "conflict" ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
p = [x for x in d["phases"] if x["number"] == 1][0]
assert p["evidence"]["bd"] == "none", p["evidence"]
items = [c for c in p["conflicts"]
         if c["severity"] == "blocks" and c["sources"] == ["roadmap", "disk"]]
assert len(items) == 1, p["conflicts"]
'
}

# ─── R3: STATE.md vs disk (severity informs, never re-routes) ───────────────

@test "a stale STATE.md pointer over an already-verified phase informs without touching next_command" {
  require_bd
  make_tmp_repo
  write_corr_roadmap
  mkdir -p .planning/phases/02-second
  touch .planning/phases/02-second/02-01-PLAN.md
  touch .planning/phases/02-second/02-01-SUMMARY.md
  touch .planning/phases/02-second/02-VERIFICATION.md
  cat > .planning/STATE.md <<'EOF'
---
active_phase: "2"
---
EOF
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1
  # No bd issues for phase 2 at all — bd agrees by having no opinion.

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | phase_field 2 corroboration)" = "conflict" ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
p = [x for x in d["phases"] if x["number"] == 2][0]
assert len(p["conflicts"]) == 1, p["conflicts"]
assert p["conflicts"][0]["severity"] == "informs", p["conflicts"]
assert p["conflicts"][0]["sources"] == ["state_md", "disk"], p["conflicts"]
assert not any(c["severity"] == "blocks" for c in p["conflicts"]), p["conflicts"]
assert p["needs_doctor"] is False, p
# The informs-only conflict never re-routes next_command: it stays exactly
# the disk-driven value for "verified" (None), never "/cairn:doctor".
assert p["next_command"] is None, p["next_command"]
'
}

# ─── disk_state regression (bullet 4: cairn-phase-model.bats is unmodified) ──
# Proven by running that file's own suite unmodified — see this plan's
# <verify> block (`bats tests/cairn-corroboration.bats
# tests/cairn-phase-model.bats tests/cairn-status.bats`), not duplicated
# here.

# ─── bd_state(): the ALL-not-ANY discipline (bullet 5) ──────────────────────

@test "bd_state excludes an issue whose other phase label is not roadmap-complete" {
  python3 -c "$PY_LOAD"'
issues = [{"labels": ["phase-3", "phase-4"], "status": "open"}]
# Phase 3 is roadmap-complete, phase 4 is not: the issue is genuine live
# work for phase 4, so it must never count against phase 3.
result_3 = cs.bd_state(issues, 3, {3})
assert result_3 == "none", result_3
# ...and it DOES count for phase 4 — proving the exclusion is selective,
# not a blanket "cross-phase issues never count anywhere".
result_4 = cs.bd_state(issues, 4, {3})
assert result_4 == "open", result_4
'
}

# ─── ROADMAP SC4, the /cairn:autonomous half (bullets 6-8) ──────────────────
# R2 always implies complete=true (roadmap_complete is literally
# row["complete"]), so a phase carrying an R2 "blocks" conflict is always
# filtered out of pending_phases()/next_commands() by construction — it can
# never be the "blocks-conflict pending phase" these three tests need. Only
# R1 (disk-vs-bd) can produce a "blocks" conflict on a phase that stays
# pending, so all three below build it that way.

@test "a blocks conflict on a pending phase routes it to doctor and sorts it behind a runnable one" {
  require_bd
  make_tmp_repo
  write_corr_roadmap
  mkdir -p .planning/phases/02-second
  touch .planning/phases/02-second/02-01-PLAN.md
  touch .planning/phases/02-second/02-01-SUMMARY.md
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1
  bd create "phase 2 still open" -t task -l phase-2 --silent >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
byn = {p["number"]: p for p in d["phases"]}
# Phase 1: untouched, no conflict — genuinely runnable.
assert byn[1]["corroboration"] == "ok", byn[1]
assert byn[1]["needs_doctor"] is False, byn[1]
assert byn[1]["next_command"] == "/cairn:plan 1", byn[1]
# Phase 2: the disk-vs-bd blocks conflict.
assert byn[2]["corroboration"] == "conflict", byn[2]
assert byn[2]["needs_doctor"] is True, byn[2]
cmds = {c["phase"]: c for c in d["next_commands"]}
assert cmds[2]["command"] == "/cairn:doctor", cmds[2]
assert cmds[2]["blocked"] is True, cmds[2]
assert cmds[1]["blocked"] is False, cmds[1]
# The runnable phase sorts ahead of the conflicting one — the literal proof
# that /cairn:autonomous (which reads next_commands[0]) picks phase 1.
assert d["next_commands"][0]["phase"] == 1, d["next_commands"]
'
}

@test "an unknown verdict is deprioritized exactly like a blocks conflict, through the same needs_doctor field" {
  # bd_ok is one flag for a whole phase_model() call (a real outage is
  # global, per D-07), so a live fixture cannot hold one "ok" phase and one
  # "unknown" phase at once. This proves the two halves of the chain
  # directly instead: corroborate() really does produce "unknown" with an
  # EMPTY conflicts list on a clean bd-unreadable read (no fabricated
  # evidence for the miss), and next_commands() reads that exact
  # needs_doctor value — never recomputing it — to deprioritize the phase
  # exactly like a "blocks" conflict would. The end-to-end "a real bd
  # outage makes every phase unknown" claim is proven separately below by
  # the forced-bd-failure CLI tests (Task 2).
  python3 -c "$PY_LOAD"'
verdict, evidence, conflicts = cs.corroborate(2, "planned", False, "none", False, None)
assert verdict == "unknown", verdict
assert conflicts == [], conflicts
assert evidence["bd"] == "unknown", evidence
needs_doctor = (verdict == "unknown"
                or (verdict == "conflict"
                    and any(c["severity"] == "blocks" for c in conflicts)))
assert needs_doctor is True, needs_doctor

model = [
    {"number": 1, "complete": False, "title": "Runnable phase",
     "depends_on": [], "blocked_by": [], "disk_state": "none",
     "corroboration": "ok", "conflicts": [], "needs_doctor": False,
     "next_command": "/cairn:plan 1"},
    {"number": 2, "complete": False, "title": "Unknown-bd phase",
     "depends_on": [], "blocked_by": [], "disk_state": "planned",
     "corroboration": verdict, "conflicts": conflicts,
     "needs_doctor": needs_doctor, "next_command": "/cairn:doctor"},
]
cmds = cs.next_commands(model)
byphase = {c["phase"]: c for c in cmds}
assert byphase[2]["command"] == "/cairn:doctor", byphase[2]
assert byphase[2]["blocked"] is True, byphase[2]
assert byphase[1]["blocked"] is False, byphase[1]
assert cmds[0]["phase"] == 1, cmds
assert cmds[1]["phase"] == 2, cmds
'
}

@test "a needs_doctor phase as the only pending phase routes to doctor, not the ship auto-suggestion" {
  require_bd
  make_tmp_repo
  mkdir -p .planning
  cat > .planning/ROADMAP.md <<'EOF'
# Roadmap: Corroboration Fixture

## Phases

- [ ] Phase 1: Only phase
EOF
  # disk_state pinned to "verified" — the specific value at which, absent
  # the needs_doctor guard, the untouched base dict returns None and
  # next_commands() would build an empty list, triggering the
  # milestone-complete /cairn:ship auto-suggestion instead.
  mkdir -p .planning/phases/01-only
  touch .planning/phases/01-only/01-01-PLAN.md
  touch .planning/phases/01-only/01-01-SUMMARY.md
  touch .planning/phases/01-only/01-VERIFICATION.md
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1
  bd create "phase 1 still open" -t task -l phase-1 --silent >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
p = d["phases"][0]
assert p["number"] == 1
assert p["disk_state"] == "verified", p["disk_state"]
assert p["corroboration"] == "conflict", p["corroboration"]
assert p["needs_doctor"] is True, p
cmds = d["next_commands"]
assert cmds, "next_commands is empty — the guard did not fire"
assert cmds[0]["command"] == "/cairn:doctor", cmds
assert cmds[0]["blocked"] is True, cmds
assert cmds[0]["command"] != "/cairn:ship", cmds
'
}

# ─── Complete-phase interaction (bullet 9) ───────────────────────────────────

@test "a complete phase keeps next_command None despite a blocks conflict, and drops out of next_commands" {
  require_bd
  make_tmp_repo
  mkdir -p .planning
  cat > .planning/ROADMAP.md <<'EOF'
# Roadmap: Corroboration Fixture

## Phases

- [x] Phase 1: Marked complete
EOF
  # Same disk-vs-bd shape as the first R1 test above, but the checkbox is
  # also ticked this time.
  mkdir -p .planning/phases/01-marked
  touch .planning/phases/01-marked/01-01-PLAN.md
  touch .planning/phases/01-marked/01-01-SUMMARY.md
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1
  bd create "phase 1 still open" -t task -l phase-1 --silent >/dev/null

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
p = d["phases"][0]
assert p["number"] == 1
assert p["complete"] is True, p
assert p["corroboration"] == "conflict", p["corroboration"]
# The field reflects corroboration honestly even though the phase is
# complete — only phase_next_command()s short-circuit hides it from the
# suggested command.
assert p["needs_doctor"] is True, p
assert p["next_command"] is None, p["next_command"]
assert all(c["phase"] != 1 for c in d["next_commands"]), d["next_commands"]
'
}

# ─── Task 2: bd-unreachable fail-open (CORR-03, the highest-priority test) ──
# Every test below stubs a `bd` that IS present on PATH and fails every
# invocation with a nonzero exit — a real subprocess failure, not an
# absent binary (see tests/cairn-status.bats:385-397 for that other case).

@test "a real bd query failure degrades every phase to unknown evidence, never ok, through --json" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1
  local stub
  stub="$(make_failing_bd_stub)"

  run env PATH="$stub:$PATH" bash "$STATUS_SH" --json
  [ "$status" -eq 5 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["phases"], "no phases in the model"
for p in d["phases"]:
    assert p["evidence"]["bd"] == "unknown", p
    assert p["corroboration"] in ("conflict", "unknown"), p
    assert p["corroboration"] != "ok", p
'
}

@test "the same forced bd failure exits 5 through the plain terminal board render too" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1
  local stub
  stub="$(make_failing_bd_stub)"

  # The render path a human actually looks at, not only the machine one.
  run env PATH="$stub:$PATH" bash "$STATUS_SH" --width 100
  [ "$status" -eq 5 ]
  [ -n "$output" ]
  grep -qF 'PENDING PHASES' <<<"$output"
}

@test "the same forced bd failure exits 5 through the --html render path too" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  bd init -q --prefix cf --non-interactive >/dev/null 2>&1
  local stub
  stub="$(make_failing_bd_stub)"

  run env PATH="$stub:$PATH" bash "$STATUS_SH" --html board.html
  [ "$status" -eq 5 ]
  [ -f board.html ]
  grep -qF 'wrote' <<<"$output"
}

@test "a repo with no .beads at all still resolves bd's axis to none, not unknown" {
  require_bd
  make_tmp_repo
  make_gsd_fixture "$PWD"
  # No bd init at all: this is "no bd usage here", not "bd failed" — the
  # distinction a future edit must not collapse into one value.

  run bash "$STATUS_SH" --json
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["note"] is not None and "no .beads/" in d["note"], d["note"]
for p in d["phases"]:
    assert p["evidence"]["bd"] == "none", p
    assert p["evidence"]["bd"] != "unknown", p
'
}

@test "the module docstring documents the new corroboration keys and bd_ok" {
  run bash -c "sed -n '1,/^import /p' '$CAIRN_STATUS_PY'"
  [ "$status" -eq 0 ]
  grep -qF 'evidence' <<<"$output"
  grep -qF 'corroboration' <<<"$output"
  grep -qF 'bd_ok' <<<"$output"
}
