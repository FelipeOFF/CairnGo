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

## Release this phase's lease (cairn)

Applies only when the project root contains `.beads/`. If it is missing,
skip silently.

Regardless of whether verification passed or failed above, and regardless
of what the cross-check reported, release the phase's lease exactly once:

```bash
CAP=".gsd/capabilities/cairn"; [ -d "$CAP" ] || CAP="${GSD_HOME:-$HOME}/.gsd/capabilities/cairn"
bash "$CAP/scripts/cairn-lease.sh" release <N>
```

This block recomputes `CAP` on its own, self-contained at this insertion
point, rather than reusing the variable already set earlier in this file for
the cross-check call above — even though it resolves to the same value
today. `execute-wave-pre.md`'s own acquire paragraph does the same for the
identical reason: neither fragment's correctness should depend on where it
sits relative to anything else in the file, so a later edit that reorders
these paragraphs can never silently break the resolution.

This is the phase's single, deterministic release point (LEASE-04: once per
phase, pass or fail) — it does NOT check who currently holds the lease
first. It clears whoever holds it, on purpose, because verification
reaching this point at all means the phase's work cycle is over, regardless
of which worktree ran it. This is intentionally the ONLY place this
mechanism releases the lease — verify.md's own step 1 already triggers this
fragment by calling `/gsd:verify-work`, so do not add a second explicit
release call in verify.md's prose; that would only risk a redundant
(harmless but pointless) double release.
