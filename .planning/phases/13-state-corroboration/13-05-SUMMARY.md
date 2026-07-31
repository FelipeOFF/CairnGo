---
phase: 13-state-corroboration
plan: "05"
status: complete
requirements: [CORR-08]
beads: [CairnGo-x4p]
---

# Phase 13 Plan 05 — Summary

The hook records the closing PR, and when it fails, the failure survives.

## What shipped

**`post-bd-write.sh` gained a third background job.** On a `bd close` with a
resolved issue id, it asks `gh pr view` for the PR number and, if one comes back,
fires `bd update <id> --external-ref gh-<N>`. No PR yet is a silent no-op, as is
`gh` being absent — those are ordinary, not errors.

That external ref is what makes the git axis of corroboration possible at all.
This repository squash-merges, so the source branch's commits are discarded and
no commit message has ever carried a bd id: zero of 239, measured, not assumed.
The `(#N)` in the squash subject is the only durable join key, and this writes the
other half of it.

**The job's output goes to `.cairn/hook.log`** — the one deliberate exception to
this file's otherwise universal `/dev/null` redirection, called out in the code
and in the header contract.

## The thing worth knowing

This hook **always exits 0**, by design and by contract: its job is to inject
context and fire background work, never to fail the tool call that triggered it.
Which means an assertion that the hook exits 0 proves absolutely nothing. It would
have passed before this change, after this change, and after this change was
deleted.

So the load-bearing test asserts on the **content of the log**: with `bd` stubbed
to print an error and exit nonzero, the hook still exits 0 *and* the stubbed error
text appears in `.cairn/hook.log`, polled for rather than assumed.

And that test was mutation-tested before being trusted. The log redirect was
reverted to `/dev/null`, the test was re-run and **failed**, then the fix was
restored and the file compared byte-for-byte against its pre-mutation state. A
test nobody has tried to break is a test nobody knows the strength of.
