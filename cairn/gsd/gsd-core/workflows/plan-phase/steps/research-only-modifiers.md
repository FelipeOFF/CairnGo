### 5.0. Research-Only Modifiers (`--view`, `--research`)

**Skip if:** `RESEARCH_ONLY` is `false`.

Three branches in research-only mode (`--research-phase <N>`):

1. **`--view`**: print the phase's research RECORD to stdout, no spawn, exit. If there is no research record, error with: `--view requires existing research on the phase; drop --view to spawn the researcher.`
2. **`--research`** (force-refresh): re-spawn researcher unconditionally — fall through to "Spawn gsd-phase-researcher" below.
3. **Neither flag AND `has_research=true`:** auto-use the existing research and exit cleanly — do not prompt, do not re-spawn. Emit `Phase ${PHASE} already has a research record, using it. To force-refresh, re-invoke with --research; to print, re-invoke with --view. Record: ${PHASE_BEAD}` then exit. The explicit-flag escape hatches cover any deviation; this matches §5.1's promptless auto-use of existing research, removing the §5.0/§5.1 inconsistency (#159).

```bash
if [[ "$VIEW_ONLY" == "true" ]]; then
  RESEARCH_BODY=$(bd show "$PHASE_BEAD" --json 2>/dev/null | jq -r '.design // ""')
  [ -n "$RESEARCH_BODY" ] || { echo "Error: --view requires existing research on Phase ${PHASE}. Drop --view to spawn the researcher."; exit 1; }
  printf '%s\n' "$RESEARCH_BODY"; exit 0
fi
```

`$PHASE_BEAD` is the phase carrier — the `phase-${PHASE}` bead with no parent
(`cairn-record.sh` resolves the same way).
