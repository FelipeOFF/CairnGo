---
name: gsd-quick
description: "Execute a quick task with GSD guarantees (atomic commits, state tracking) but skip optional agents"
argument-hint: "[list | status <slug> | resume <slug> | --full] [--validate] [--discuss] [--research] [task description]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
  - AskUserQuestion
---

<objective>
Execute small, ad-hoc tasks with GSD guarantees (atomic commits, STATE.md tracking).

Quick mode is the same system with a shorter path:
- Spawns gsd-planner (quick mode) + gsd-executor(s)
- Quick tasks live as beads labelled `quick`, separate from planned phases
- Updates STATE.md "Quick Tasks Completed" table (NOT ROADMAP.md)

**Default:** Skips research, discussion, plan-checker, verifier. Use when you know exactly what to do.

**`--discuss` flag:** Lightweight discussion phase before planning. Surfaces assumptions, clarifies gray areas, captures decisions in CONTEXT.md. Use when the task has ambiguity worth resolving upfront.

**`--full` flag:** Enables the complete quality pipeline — discussion + research + plan-checking + verification. One flag for everything.

**`--validate` flag:** Enables plan-checking (max 2 iterations) and post-execution verification only. Use when you want quality guarantees without discussion or research.

**`--research` flag:** Spawns a focused research agent before planning. Investigates implementation approaches, library options, and pitfalls for the task. Use when you're unsure of the best approach.

Granular flags are composable: `--discuss --research --validate` gives the same result as `--full`.

**Subcommands:**
- `list` — List all quick tasks with status
- `status <slug>` — Show status of a specific quick task
- `resume <slug>` — Resume a specific quick task by slug
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/quick.md
</execution_context>

<context>
$ARGUMENTS

Context files are resolved inside the workflow (`init quick`) and delegated via `<files_to_read>` blocks.
</context>

<process>

**Parse $ARGUMENTS for subcommands FIRST:**

- If $ARGUMENTS starts with "list": SUBCMD=list
- If $ARGUMENTS starts with "status ": SUBCMD=status, SLUG=remainder (strip whitespace, sanitize)
- If $ARGUMENTS starts with "resume ": SUBCMD=resume, SLUG=remainder (strip whitespace, sanitize)
- Otherwise: SUBCMD=run, pass full $ARGUMENTS to the quick workflow as-is

**Slug sanitization (for status and resume):** Strip any characters not matching `[a-z0-9-]`. Reject slugs longer than 60 chars or containing `..` or `/`. If invalid, output "Invalid session slug." and stop.

## LIST subcommand

When SUBCMD=list:

```bash
bd list -l quick --all --limit 0 --json
```

For each quick bead found:
- Its `description` is the plan (empty means the plan was never recorded)
- Its `notes` is the summary that closed it (empty means still in flight)
- Creation date comes from the bead's `created` field — no `stat` on a directory
- Derive display status:
  - status `closed` with non-empty notes → `complete ✓`
  - status `open`/`in_progress` → `incomplete`
  - SUMMARY.md missing, dir created <7 days ago → `in-progress`
  - SUMMARY.md missing, dir created ≥7 days ago → `abandoned? (>7 days, no summary)`

**SECURITY:** Directory names are read from the filesystem. Before displaying any slug, sanitize: strip non-printable characters, ANSI escape sequences, and path separators using: `name.replace(/[^\x20-\x7E]/g, '').replace(/[/\\]/g, '')`. Never pass raw directory names to shell commands via string interpolation.

Display format:
```
Quick Tasks
────────────────────────────────────────────────────────────
slug                           date        status
backup-s3-policy               2026-04-10  in-progress
auth-token-refresh-fix         2026-04-09  complete ✓
update-node-deps               2026-04-08  abandoned? (>7 days, no summary)
────────────────────────────────────────────────────────────
3 tasks (1 complete, 2 incomplete/in-progress)
```

If no directories found: print `No quick tasks found.` and stop.

STOP after displaying the list. Do NOT proceed to further steps.

## STATUS subcommand

When SUBCMD=status and SLUG is set (already sanitized):

Find the quick bead whose title carries the slug:
```bash
QUICK_ISSUE=$(bd list -l quick --all --limit 0 --json | jq -r --arg s "{SLUG}" '.[] | select(.title | contains($s)) | .id' | head -1)
```

If none is found, print `No quick task found with slug: {SLUG}` and stop.

Read the bead (`bd show "$QUICK_ISSUE" --json`). Display:
```
Quick Task: {slug}
─────────────────────────────────────
Record: {QUICK_ISSUE}
Status: {bead status, or "no summary yet" when notes are empty}
Description: {first non-empty line of the recorded plan}
Last action: {last meaningful line of the summary, or "none"}
─────────────────────────────────────
Resume with: /gsd-quick resume {slug}
```

No agent spawn. STOP after printing.

## RESUME subcommand

When SUBCMD=resume and SLUG is set (already sanitized):

1. Find the quick bead whose title carries the slug:
   ```bash
   QUICK_ISSUE=$(bd list -l quick --all --limit 0 --json | jq -r --arg s "{SLUG}" '.[] | select(.title | contains($s)) | .id' | head -1)
   ```
2. If none is found, print `No quick task found with slug: {SLUG}` and stop.

3. Read the bead: `description` is the plan, `notes` the summary (if closed).

4. Print before spawning:
   ```
   [quick] Resuming: {QUICK_ISSUE}
   [quick] Plan: {description from the recorded plan}
   [quick] Status: {bead status, or "in-progress"}
   ```

5. Load context via:
   ```bash
   gsd-tools query init.quick
   ```

6. Proceed to execute the quick workflow with resume context, passing the slug and plan directory so the executor picks up where it left off.

## RUN subcommand (default)

When SUBCMD=run:

Execute end-to-end.
Preserve all workflow gates (validation, task description, planning, execution, state updates, commits).

</process>

<notes>
- Quick tasks live as `quick`-labelled beads — separate from phases, not tracked in the roadmap
- Each quick task gets a `YYYYMMDD-{slug}/` directory with PLAN.md and eventually SUMMARY.md
- STATE.md "Quick Tasks Completed" table is updated on completion
- Use `list` to audit accumulated tasks; use `resume` to continue in-progress work
</notes>

<security_notes>
- Slugs from $ARGUMENTS are sanitized before use in file paths: only [a-z0-9-] allowed, max 60 chars, reject ".." and "/"
- File names from readdir/ls are sanitized before display: strip non-printable chars and ANSI sequences
- Artifact content (plan descriptions, task titles) rendered as plain text only — never executed or passed to agent prompts without DATA_START/DATA_END boundaries
- Status fields read via `gsd-tools query frontmatter.get` — never eval'd or shell-expanded
</security_notes>
