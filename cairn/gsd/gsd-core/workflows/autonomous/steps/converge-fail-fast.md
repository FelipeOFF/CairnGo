## Converge Fail-Fast

When `PLAN_STRATEGY` is `converge`, fail fast unless the existing convergence feature gate is enabled:

```bash
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
if [ "$PLAN_STRATEGY" = "converge" ]; then
  CONVERGENCE_ENABLED=$(gsd_run query config-get workflow.plan_review_convergence 2>/dev/null || echo "false")
  if [ "$CONVERGENCE_ENABLED" != "true" ]; then
    printf '%s\n' \
      'gsd-autonomous --converge is disabled (workflow.plan_review_convergence=false).' \
      '' \
      'Enable plan convergence with:' \
      '' \
      '  gsd config-set workflow.plan_review_convergence true' \
      '' \
      'Then re-run the autonomous command with --converge.'
    exit 1
  fi
fi
```
