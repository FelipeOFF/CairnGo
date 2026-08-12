# Step: regression_gate_run

Run the resolved prior-phase test command one-shot, bounded by a timeout, so a
watch-mode runner (vitest defaults to watch in a TTY; jest `--watch`) cannot
hang this gate forever (#1857). Uses the shared `normalize-test-command` helper
— the same one the post-merge gate uses — so the two gate paths cannot drift.

Expects `REGRESSION_FILES` (from the prior step) in scope for the pytest branch.

```bash
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
# Resolve test command: project config > Makefile > language sniff
REG_TEST_CMD=$(gsd_run query config-get workflow.test_command --default "" --raw 2>/dev/null || true)
if [ -z "$REG_TEST_CMD" ]; then
  if [ -f "Makefile" ] && grep -q "^test:" Makefile; then
    REG_TEST_CMD="make test"
  elif [ -f "Justfile" ] || [ -f "justfile" ]; then
    REG_TEST_CMD="just test"
  elif [ -f "package.json" ]; then
    REG_TEST_CMD="npm test"
  elif [ -f "Cargo.toml" ]; then
    REG_TEST_CMD="cargo test"
  elif [ -f "go.mod" ]; then
    REG_TEST_CMD="go test ./..."
  elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    REG_TEST_CMD="python -m pytest ${REGRESSION_FILES} -q --tb=short"
  else
    REG_TEST_CMD="true"
  fi
fi
# #1857: normalize to a one-shot form (defeat vitest/jest watch mode) and bound
# with a timeout so a watch-mode runner cannot hang the gate indefinitely.
REG_TEST_CMD=$(gsd_run query normalize-test-command "$REG_TEST_CMD" --cwd . 2>/dev/null || echo "$REG_TEST_CMD")
TEST_GATE_TIMEOUT=$(gsd_run query config-get workflow.test_gate_timeout 2>/dev/null || echo "600")
gsd_run run-with-timeout "$TEST_GATE_TIMEOUT" -- bash -c "$REG_TEST_CMD" 2>&1
REG_TEST_EXIT=$?
if [ "$REG_TEST_EXIT" -eq 124 ]; then
  echo "✗ REGRESSION GATE ABORTED — test runner did not exit within ${TEST_GATE_TIMEOUT}s, likely stuck in watch/dev mode (e.g. vitest without 'run'). Run tests one-shot (e.g. 'vitest run'), set workflow.test_command, or raise workflow.test_gate_timeout."
fi
```

**On `REG_TEST_EXIT` 124 (`REGRESSION GATE ABORTED`):** HALT — do not proceed to verification. The runner did not exit within the budget (watch/dev mode is the likely cause). Surface the watch-mode cause and the recovery options; never silently continue.
