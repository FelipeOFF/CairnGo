<!-- cairn capability — verify:post fragment, injected into the orchestrator.
     Deterministic cross-check of bd state vs the phase's VERIFICATION
     report, via the bundled script. -->

## Cross-check beads state against verification (cairn)

Applies only when the project root contains `.beads/`. If it is missing,
skip silently.

After the verification report is written, run the bundled cross-check for
the phase (it exits 0 and prints a report; it no-ops silently outside beads
repos):

```bash
CAP=".gsd/capabilities/cairn"; [ -d "$CAP" ] || CAP="${GSD_HOME:-$HOME}/.gsd/capabilities/cairn"
bash "$CAP/scripts/cairn-loop-gate.sh" verify-cross <N>
```

Surface the script's output to the user verbatim. If it reports MISMATCH
lines, reconcile before moving on:

- Verification passed but issues remain non-closed → close them with a
  one-line reason (`bd close <id> --reason "..."`), then refresh the map
  (`bash "$CAP/scripts/cairn-map.sh" <N>`).
- Issues closed but verification is missing or failed → reopen the affected
  ids (`bd reopen <id>`) or record the verification, whichever matches
  reality. The GSD docs win over stale issue state.
