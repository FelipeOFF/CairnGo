<!-- cairn capability — execute:wave:post fragment, injected into the executor.
     Closes the completed plan's tracked work and refreshes the generated
     phase map after SUMMARY.md is written. -->

## Close this plan's beads issues on completion (cairn)

Applies only when the project root contains `.beads/`. If it is missing, or
the plan has no `beads:` frontmatter key, skip silently.

After your plan's tasks are complete, verification passed, and SUMMARY.md is
written — and only then — close every id in the plan's `beads:` frontmatter:

```bash
bd close <id> --reason "<one-line accomplishment from the plan's SUMMARY.md>"
```

- The reason is one line, taken from the SUMMARY's headline accomplishment
  (e.g. "Signup and login handlers implemented and tested").
- A plan that stopped early or deferred work does NOT close its ids — leave
  them claimed and note the state in SUMMARY.md instead.
- Then refresh the phase's generated map so `<NN>-BEADS-MAP.md` reflects the
  closes (the bundle script no-ops outside beads repos):
  ```bash
  CAP=".gsd/capabilities/cairn"; [ -d "$CAP" ] || CAP="${GSD_HOME:-$HOME}/.gsd/capabilities/cairn"
  bash "$CAP/scripts/cairn-map.sh" <N>
  ```
- If `.cairn/sync.json` has an enabled backend and config `cairn.sync_push`
  is not false, push the mirror for each closed id right after closing (see
  the cairn-sync skill).
