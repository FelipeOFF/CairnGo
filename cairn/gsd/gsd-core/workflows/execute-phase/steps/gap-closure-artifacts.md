<step name="close_parent_artifacts">
**For decimal/polish phases only (X.Y pattern):** Close the feedback loop by resolving parent UAT and debug artifacts.

**Skip if** phase number has no decimal (e.g., `3`, `04`) — only applies to gap-closure phases like `4.1`, `03.1`.

**1. Detect decimal phase and derive parent:**
```bash
# Check if phase_number contains a decimal
if [[ "$PHASE_NUMBER" == *.* ]]; then
  PARENT_PHASE="${PHASE_NUMBER%%.*}"
fi
```

**2. Find parent UAT file:**
```bash
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
PARENT_INFO=$(gsd_run query find-phase "${PARENT_PHASE}" --raw)
# Extract directory from PARENT_INFO JSON, then find UAT file in that directory
```

**If no parent UAT found:** Skip this step (gap-closure may have been triggered by VERIFICATION.md instead).

**3. Update UAT gap statuses:**

Read the parent UAT file's `## Gaps` section. For each gap entry with `status: failed`:
- Update to `status: resolved`

**4. Update UAT frontmatter:**

If all gaps now have `status: resolved`:
- Update frontmatter `status: diagnosed` → `status: resolved`
- Update frontmatter `updated:` timestamp

**5. Resolve referenced debug sessions:**

For each gap that has a `debug_session:` field:
- Read the debug session file
- Update frontmatter `status:` → `resolved`
- Update frontmatter `updated:` timestamp
- Move to resolved directory:
```bash
mkdir -p .planning/debug/resolved
mv .planning/debug/{slug}.md .planning/debug/resolved/
```

**6. Commit updated artifacts:**
```bash
gsd_run query commit "docs(phase-${PARENT_PHASE}): resolve UAT gaps and debug sessions after ${PHASE_NUMBER} gap closure" --files .planning/phases/*${PARENT_PHASE}*/*-UAT.md .planning/debug/resolved/*.md
```
</step>
