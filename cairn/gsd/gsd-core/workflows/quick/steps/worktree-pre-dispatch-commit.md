**Step 5.6: Pre-dispatch plan commit (worktree mode only)**

When `USE_WORKTREES !== "false"`, commit PLAN.md to the current branch **before** spawning the executor. This ensures the worktree inherits PLAN.md at its branch HEAD so the executor can read it via a worktree-rooted path — avoiding the main-repo path priming that triggers CC #36182 path-resolution drift.

Skip this step entirely if `USE_WORKTREES === "false"` (non-worktree mode: PLAN.md is committed in Step 8 as usual).

```bash
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
QUICK_PLAN_PARENT=""
QUICK_PLAN_COMMIT=""
if [ "${USE_WORKTREES}" != "false" ]; then
  QUICK_PLAN_PARENT=$(git rev-parse HEAD)
  COMMIT_DOCS=$(gsd_run query config-get commit_docs 2>/dev/null || echo "true")
  if [ "$COMMIT_DOCS" != "false" ]; then
    git add "${QUICK_DIR}/${quick_id}-PLAN.md"
    # No-op skip if nothing actually staged (idempotent re-runs).
    if git diff --cached --quiet -- "${QUICK_DIR}/${quick_id}-PLAN.md"; then
      echo "ℹ Pre-dispatch PLAN.md commit skipped (no staged changes)"
    else
      # Run hooks normally (#2924). If a project opts out via
      # workflow.worktree_skip_hooks=true, honor that opt-in only.
      SKIP_HOOKS=$(gsd_run query config-get workflow.worktree_skip_hooks 2>/dev/null || echo "false")
      if [ "$SKIP_HOOKS" = "true" ]; then
        git commit --no-verify -m "docs(${quick_id}): pre-dispatch plan for ${DESCRIPTION}" -- "${QUICK_DIR}/${quick_id}-PLAN.md" \
          || { echo "ERROR: pre-dispatch PLAN.md commit failed (--no-verify path). Aborting before executor dispatch." >&2; exit 1; }
      else
        git commit -m "docs(${quick_id}): pre-dispatch plan for ${DESCRIPTION}" -- "${QUICK_DIR}/${quick_id}-PLAN.md" \
          || { echo "ERROR: pre-dispatch PLAN.md commit failed — likely a pre-commit hook failure. Fix the hook output above (or set workflow.worktree_skip_hooks=true to bypass) and re-run." >&2; exit 1; }
      fi
      QUICK_PLAN_COMMIT=$(git rev-parse HEAD)
    fi
  fi
  if [ -z "$QUICK_PLAN_COMMIT" ]; then
    QUICK_PLAN_COMMIT=$(git rev-parse HEAD)
  fi
fi
```
