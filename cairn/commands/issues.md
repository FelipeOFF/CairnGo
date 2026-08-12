---
description: List beads issues, optionally scoped to a phase
argument-hint: "[phase-number]"
group: view
---

List tracked work from beads.

- If a phase number was given (`$ARGUMENTS` is non-empty):
  `bd list -l m-<milestone>,phase-$ARGUMENTS`, with the milestone from
  ROADMAP.md's current milestone header.
  Legacy repos whose issues carry no `m-*` labels: fall back to plain
  `bd list -l phase-$ARGUMENTS`.
- Otherwise: `bd list` for the whole project.

Group the output by status (open / in_progress / closed) and note any
dependency-blocked issues.
