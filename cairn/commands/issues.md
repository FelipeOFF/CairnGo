---
description: List beads issues, optionally scoped to a phase
argument-hint: "[phase-number]"
---

List tracked work from beads.

- If a phase number was given (`$ARGUMENTS` is non-empty): `bd list -l phase-$ARGUMENTS`.
- Otherwise: `bd list` for the whole project.

Group the output by status (open / in_progress / closed) and note any
dependency-blocked issues.
