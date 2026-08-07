# /cairn:land

> Did this work reach the control branch — per phase, offline, and which pull
> request took it

## Usage

```text
/cairn:land                       # the report
/cairn:land detect                # which branch would count, and why
/cairn:land apply --branches a,b  # record that decision
/cairn:land --json                # machine-readable
```

Wraps [`cairn-land.py`](../../scripts/cairn-land.py). Every path is offline:
the script opens no socket and invokes no network tool.

## Two questions, two confidences

| Question | Source | Confidence |
|---|---|---|
| did the work enter the control branch? | git ancestry, local | **exact** |
| which pull request took it there? | the local history | **partial** |
| what state is that pull request in? | `gh` / `glab` | **not here** — [`/cairn:review`](./review.md) |

The third one needs the network and lives behind a switch in a different file,
so that the boundary is structure rather than a promise:

```text
cairn-status.py  ->  cairn-land.py  ->  git, and a local cache FILE
cairn-review.py  ->  gh / glab                       (never the reverse)
```

## What it does

1. **Attributes commits to phases from two sources, both named.** `path` — the
   commit touched `<planning>/phases/<NN>-*/`. `scope` — the conventional-commit
   scope names the phase (`feat(29-05)`, `chore(29)`). Both, because measured
   2026-08-06 each alone loses real commits: the commit that CLOSES a phase
   touches ROADMAP/STATE/REQUIREMENTS and not the phase directory, so path
   alone never sees it; and scope is a convention this project happens to
   follow, so scope alone is not portable. An archived phase is still found by
   scope.
2. **Asks git once per control branch**, not once per commit:
   `git rev-list HEAD --not <branch>` is exactly the set of commits that did
   NOT enter the branch, so a commit is landed if and only if it is absent
   from that set.
3. **Reports a verdict per phase**, per control branch.

## The verdict vocabulary — exact values, never a negation

| Verdict | Meaning |
|---|---|
| `landed` | every attributed commit is reachable from the control branch |
| `partial` | some are, some are not |
| `unlanded` | none is |
| `unknown` | the question could not be answered; `reason` says which silence it is — `no-commits`, `no-branch`, `no-git` |

`unknown` is never collapsed into `unlanded`. "I looked and it is not there"
and "I could not look" are different sentences, and only the first one licenses
anybody to act.

## The pull request: `found` or `unknown`, and never "none"

| Word | Meaning |
|---|---|
| `found` | a commit attributed to the phase names a pull request — GitHub's own merge subject (`Merge pull request #6 from …`) or the squash suffix (`… (#18)`) |
| `unknown` | it does not, with a reason: `no-commits` (nothing attributed at all) or `no-reference` (commits attributed, none names a number) |

There is deliberately **no third verdict**. "There is no pull request" is a
claim about the forge, and nothing offline can make it. Measured 2026-08-06
over this repository: 14 commits carry `(#N)` in the subject, 6 merge commits
name `pull request #N`, and pull request #21 — which merged an entire
milestone — became a merge commit whose subject and body name no number at
all. The most important merge in the project is invisible offline. A surface
that reported "no PR" for it would be lying while passing a green suite.

## Which branch is the control branch

`git.control_branches` in `.cairn/config.json`, a comma-separated list —
gitflow really does have two at once, and "entrou na develop, ainda não na
main" is information rather than ambiguity. Read here, never written: the file
belongs to [`/cairn:config`](./config.md).

With the key unset, detection answers instead, and `control.source` says which
of the two produced the answer. Detection precedence:

1. `refs/remotes/origin/HEAD` — measured: `git symbolic-ref` exits 128 in this
   repository, so the most obvious source does not exist here. It degrades
   instead of dying.
2. conventional names present as refs: `develop`, `dev`, `main`, `master`,
   `trunk` — remote-tracking preferred, and **both** `develop` and `main` are
   returned when both exist (the gitflow case, not a tie to break).
3. the branch the current HEAD most descends from.

`apply` is what turns a detection into a decision.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | ok — **including** a report that answers `unknown` everywhere, which is an answer and not a failure |
| `2` | usage error, or `apply` with a branch name no ref resolves |
| `3` | nothing to do: `apply` with exactly the branches already on record |
| `5` | a script this one depends on is unavailable or unreadable (`cairn-config.py`, the config's owner) |

## Files it touches

- `.cairn/config.json` — `git.control_branches`, read always, written only by
  `apply` and only through `cairn-config.py`.

## See also

- [`/cairn:review`](./review.md) — the pull request's *state*, behind a switch
- [`/cairn:status`](./status.md) — the board renders this answer per phase
- [`/cairn:doctor`](./doctor.md) — the `phase-landed` check asks the same
  question on every health run
- [`/cairn:ship`](./ship.md) — what makes unlanded work land
