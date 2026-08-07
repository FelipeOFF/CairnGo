---
description: Investigate a detected phase conflict and propose a cited reconciliation — proposes only, never applies
argument-hint: "<phase-number>"
group: health
---

Investigate phase **$ARGUMENTS**'s conflict and produce a citation-checked
proposal for a human to review. This command never touches bd state on its
own — it only ever writes one file, a proposal, for a separate,
human-invoked step to act on.

## 1. Gate: only a real conflict is worth investigating

`$ARGUMENTS` is the phase number (`N`, below). Run:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-status.sh" --json --planning-dir .planning
```

and read that phase's `corroboration` key:

```bash
jq -r --arg n "$N" '.phases[] | select((.number|tostring)==$n) | .corroboration'
```

If it does not read exactly `"conflict"`, tell the user there is nothing to
investigate and **stop here** — do nothing further. This is ESC-04's gate,
enforced a second time at this layer on top of Plan 17-01's own mechanical
refusal inside the evidence gatherer itself (the load-bearing, bats-proven
half of this guarantee — this command's own step order below is only a
proxy check, since bats cannot spawn the Task tool to prove a live run
actually respects it).

## 2. Cache check: reuse a still-valid proposal

Before spending anything on a fresh investigation, run the cheap,
deterministic collector to see whether the evidence underneath a prior
proposal has actually changed:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-reconcile.sh" collect "$N" --json
```

If a proposal from a previous run already exists for this phase, compare
this run's `evidence_hash` to the one stamped in that prior proposal. A
match means nothing this conflict cites has changed since it was written
(D-04) — present that prior proposal as-is, skip straight to step 6, and
stop; zero new subagent spend. A mismatch, or no prior proposal at all,
continues to step 3.

## 3. Investigate: spawn the restricted subagent

Capture this run's `evidence_hash` from step 2's output now — it is the
ONE hash value this flow will ever stamp into the proposal, never a value
read back from the subagent.

Read the response language, from the script rather than from memory:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-config.sh" get agents.response_language
```

The `claims` this subagent returns are cited prose that a person reads, so
they are written in that language. **Paths, bd ids, hashes, branch names and
any line quoted from the repository stay exactly as they are** — a quotation
that was translated is not a quotation, and the whole value of a cited
proposal is that the citation can be checked.

The language deliberately does NOT travel inside the evidence bundle. Its
`evidence_hash` is computed over the bundle (`cairn-reconcile.py:525-531`) and
step 2 compares that hash to decide whether a previous proposal can be reused;
a language field inside it would invalidate every cached proposal on every
change of language, spending a subagent over something that changed no
evidence at all.

Spawn the `reconcile-investigator` subagent (Task tool), passing it the
evidence bundle's path (`.cairn/reconcile-evidence.json`, where step 2's
run wrote it), the phase number and that response language, and instruct it to
return **only** a JSON object of the shape `{"claims": [...]}` as its final
message. It
holds no `Write`, `Edit`, `Bash`, or `NotebookEdit` tool — it cannot write
`.cairn/conflicts.json`, or anything else, itself; see
`cairn/agents/reconcile-investigator.md` for the full tool grant and the
reasoning behind it.

## 4. Write the proposal — the one file write this command performs

Parse the subagent's final message as JSON. A parse failure, or a missing
or malformed `claims` key, is a failed investigation: report the raw text
to the user and stop — write nothing.

On success, construct the full envelope from values this command already
knows on its own — never from anything the subagent said about them:

```json
{
  "phase": <N>,
  "generated_at": "<now, ISO 8601>",
  "evidence_hash": "<captured in step 3, from step 2's collect run>",
  "claims": [<parsed straight from the subagent's returned text>]
}
```

Write it to `.cairn/conflicts.json`. This parse-and-write step is this
command's own deterministic action — the subagent that produced the
`claims` array never held a tool capable of performing it.

## 5. Verify before anyone sees it

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-reconcile.sh" verify "$N"
```

Exit `4` means at least one citation failed re-checking against the file it
claims to quote — name which citation(s) failed and **stop**; never
present an unverified proposal as trustworthy. Exit `0` continues to
step 6.

## 6. Present

Show each claim, its citation(s), and its recommended action, in plain
language — never raw JSON. Name `/cairn:doctor --apply-reconciliation $N`
as the next command: this command's own flow only ever writes the
proposal file (step 4); applying anything is a separate, human-invoked
step.
