---
description: Did this work reach the control branch — per phase, offline, and which pull request took it
argument-hint: "[detect] [apply --branches a,b] [--json]"
group: view
---

Answer "is this actually merged?" per phase, from the repository already on
disk. No argument, or `report`, runs the report; `detect` and `apply` are about
which branch counts as the control branch.

## 1. Report

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-land.sh" report $ARGUMENTS
```

One line per phase: how many commits are attributed to it, its verdict on each
control branch, and which pull request the local history names.

**Two questions, two confidences, and never mix them.** Whether the work
entered the control branch is answered by git ancestry and is exact. Which pull
request took it there is answered only as far as the local history carries it.

Phase verdicts: `landed` (every attributed commit is reachable from the control
branch), `partial` (some are), `unlanded` (none is), `unknown` (the question
could not be answered, and `reason` says why — `no-commits`, `no-branch`,
`no-git`). `unknown` is never collapsed into `unlanded`: "I looked and it is
not there" and "I could not look" are different sentences, and only the first
licenses anyone to act.

Pull-request words: `found` or `unknown`, with a reason (`no-commits`,
`no-reference`). **There is deliberately no "none".** That would be a claim
about the forge, and nothing offline can make it — measured in this repository,
the merge that took a whole milestone in carries no number anywhere in its
subject or body. Say `unknown` and say why; never report "no PR".

## 2. Which branch counts

The control branch comes from `git.control_branches` in `.cairn/config.json` —
a comma-separated list, because gitflow really does have two at once. With the
key unset the report **detects** one and says so in `control.source`, so the
answer is useful before anyone decides.

Show what detection found, and what confirming it would look like:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-land.sh" detect
bash "${CLAUDE_PLUGIN_ROOT}/scripts/cairn-land.sh" apply --branches origin/main
```

`apply` turns a detection into a decision — offer it when the user agrees with
what `detect` found, never run it unasked. Exit `3` means the branches on
record already are exactly those: nothing to do, not a failure.

## 3. What this command never does

It opens no socket and invokes no network tool — that is structural, not a
promise: the pull-request *state* lives behind `/cairn:review`, in a separate
file the status board never invokes. So an `unknown` here is not something to
resolve by asking GitHub from this command.

Exit codes: `0` ok — including a report that answers `unknown` everywhere,
which is an answer; `2` usage, or `apply` with a branch no ref resolves; `3`
nothing to do; `5` a script it depends on is unavailable.

Related: `/cairn:ship` is what makes unlanded work land; the doctor's
`phase-landed` check is this same question, asked on every health run.
