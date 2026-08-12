**MVP-mode UAT framing.** When `MVP_MODE=true`, follow the rules in `@~/.claude/gsd-core/references/verify-mvp-mode.md`. Briefly:

1. Generate the UAT script in three ordered sections: (a) user-flow walk-through derived from the phase's user-story goal, (b) technical checks (deferred — only run after user flow passes), (c) coverage check (goal-backward, narrowed to the user story's outcome clause).
2. **User-flow steps run first.** Each step is one user action: open, fill, click, type, observe. No HTTP verbs, no JSON shapes, no error codes in user-flow steps.
3. **Technical checks are deferred.** They run AFTER the user flow passes — same checks as non-MVP mode (endpoint schemas, error states, edge cases), just reordered.
4. **If user-flow step N fails, do not advance.** The verdict is FAIL; technical checks do not run. The user can re-run after fixing the underlying flow.

**User-story format guard.** When `MVP_MODE=true`, also verify the phase's goal is in User Story format via the centralized validator:

```bash
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
PHASE_GOAL=$(gsd_run query roadmap.get-phase "${phase_number}" ${GSD_WS} --pick goal)
USER_STORY_VALID=$(gsd_run query user-story.validate --story "$PHASE_GOAL" --pick valid)
if [ "$USER_STORY_VALID" != "true" ]; then
  echo "Phase ${phase_number} has '**Mode:** mvp' in ROADMAP.md but the **Goal:** is not in user-story format."
  echo "Run /gsd mvp-phase ${phase_number} to set a user-story goal before verifying."
  exit 1
fi
```

The verb owns the canonical regex `/^As a .+, I want to .+, so that .+\.$/` and returns slot extractions plus per-error guidance when invalid. Halt UAT generation on failure — never attempt to derive user-flow steps from a non-User-Story goal (low-quality UAT).
