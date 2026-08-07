---
description: Audit a milestone against its original intent before archiving — GSD audit-milestone, reported against the same gate /cairn:milestone complete enforces
argument-hint: "[version]"
wraps: audit-milestone
wrap-family: milestone
---

Audit milestone **$ARGUMENTS** against its original intent, under the `cairn`
conventions.

What this adds over `/gsd:audit-milestone`: the audit's verdict has to be read
next to what bd says, because `/cairn:milestone complete` **already refuses to
archive over a non-closed issue**. This wrapper points at that gate rather than
re-implementing it — two gates for one thing is the disease this project
treats, and a second one would drift from the first.

1. **Preflight, before anything else:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-wrap.sh" preflight audit-milestone
   ```
   Exit `6` or `5` **stops here** — print the script's message verbatim.

2. **Resolve the milestone.** `$ARGUMENTS` may name a version; otherwise take
   it from ROADMAP.md's current milestone header, or STATE.md. Everything below
   is scoped by `m-<milestone>`.

3. **Read the tracker's own view first**, so the audit is compared against it
   rather than believed on its own:
   ```bash
   bd list -l m-<milestone> --all --limit 0 --json
   ```
   Note what is still open, and under which `phase-<N>` label. The label pair
   is `m-<milestone>` + `phase-<N>`, with the **unpadded** number — `phase-3`,
   never `phase-03`.

4. **Claim the audit's own issue**, when one exists: `bd update <id> --claim`
   (atomic: assigns and sets `in_progress`).

5. **Run `/gsd:audit-milestone $ARGUMENTS`.**

6. **Reconcile the two verdicts, and name every disagreement:**
   - the audit says a phase is incomplete while its issues are all closed;
   - the audit says the milestone is done while bd still has open issues under
     it.

   Neither is resolved by picking a side here. Report both, with ids and phase
   numbers, and route: the gate is `/cairn:milestone complete`, and the drift
   between the planning files themselves is `/cairn:doctor`.

7. **A gap the audit found becomes an issue**, with the label pair and the
   stamp — never a paragraph in a report that nobody assigns:
   ```bash
   bd create "<gap>" -t task -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"milestone": "<vX.Y>", "phase": <N>, "req": "<REQ-ID>"}}'
   ```

8. **Close the audit's own issue** with the verdict:
   `bd close <id> --reason="<verdict, and what it turned up>"`. The gaps it
   found stay **open** — they are the work, not the audit of it. Nothing about
   this command closes a phase's issues; that is the gate's job.

Next: `/cairn:milestone complete`.
