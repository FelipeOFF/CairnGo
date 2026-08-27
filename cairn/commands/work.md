---
description: Execute a phase — claim each plan record's beads, do the work, close the record with its summary and the beads with their reason
argument-hint: <phase-number> [--wave N] [--tdd]
group: loop
---

Execute phase **$ARGUMENTS** under the `cairn` conventions.

**The record is the bead.** Nothing this command produces is a file: every
piece of prose goes through one boundary,
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" <kind> --phase <N>`,
body on stdin, and lands on the phase carrier (`design` for the design
kinds, one `## KIND` section each; `acceptance_criteria` for a verification;
`notes` for a review) or on a plan record (`plan-NN`, a child of the carrier).
Read it back with `bd show <carrier> --json | jq -r .design`, and the phase's
table with `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" <N>`. A
`.planning/` directory, when present, is a GSD project waiting to be
imported — never a place this command writes.

1. **Acquire this phase's coordination lease before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-lease.sh" acquire "$N"
   ```
   Exit `3` means another live worktree currently holds the lease — purely
   informational, never a reason to block: surface the script's printed report
   verbatim (who holds it, and since when), then continue. Exit `5` (bd
   unavailable) degrades the same non-blocking way. `--wave N` runs only that
   plan record; `--tdd` writes the failing test before each change.

2. **Read the plan off the beads.** The phase's plan records are the
   carrier's children carrying `plan-NN`:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"
   bd list --parent <carrier> --json      # the plan records, plan-01, plan-02, …
   bd show <plan-record> --json | jq -r '.title, .description'
   ```
   Each record names the requirement ids it advances (`LINK-02`,
   `CARRY-01`…); the map turns those names into bead ids. A record naming no
   requirement is a plan nothing can claim — say so and go back to
   `/cairn:plan <N>` rather than executing untracked. Skip records already
   `closed` (their summary is on them).

3. **For each open plan record, in order — before starting it:** for every
   bead the record names, `bd update <id> --claim` (atomic: assigns and sets
   `in_progress`; idempotent when already yours).

4. **Do the wave.** Measure before changing (the real command output, the real
   file), write the test that would fail without the change, change, run the
   relevant suite — `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-test.sh"
   --jobs 8 tests/<file>.bats`, never `bats` raw — and commit the wave on the
   branch it was handed. Notes worth keeping mid-wave go on the carrier:
   `cairn-record.sh log --phase "$N"` (appended, never overwritten).

5. **On a wave's successful completion and verification, close its record
   and its beads:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-record.sh" summary --phase "$N" --plan PP <<'BODY'
   ENTREGUE. <tests green, by file and count>. <what changed and why, the
   traps found, what was deliberately left out>
   BODY
   bd close <id> --reason="<1–2 sentence summary>"      # each bead the wave delivered
   ```
   The summary **closes** the record the plan opened — the bead count does
   not rise. A wave that fails and cannot be recovered stops here: say which
   record, which step, which output; release what you claimed
   (`bd update <id> --assignee "" --status open`) and leave the record open.

6. **Done check:** `bd list -l m-<milestone>,phase-<N> --all` (the milestone
   from `cairn-status.sh --json`; unpadded number) should show nothing but
   the carrier open when the phase is complete — report anything else still
   open. A closed carrier mirrors to its card when `.cairn/sync.json` has a
   backend; with no token in the shell the write waits on the bead — run
   `/cairn:jira flush` to send it.

7. **Refresh the phase's map** so it reflects the closes:
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-map.sh" "$N"`.

Next: `/cairn:verify <N>` or `/cairn:ship`.
