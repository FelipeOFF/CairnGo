# Status: from a row of numbers to a panel you can act on

Requirements captured from the operator, for a later milestone. Written down
because they came from a live walkthrough of a working panel and would
otherwise live only in a chat log.

## The problem with the status surface today

The roadmap parser reads **phase numbers and completion, nothing else**. Title,
goal, dependencies and plan progress are all discarded (`roadmap_phases()` in
`cairn/scripts/cairn-status.py` returns two lists of ints).

That is why the board renders a phase as `04` and why its empty space cannot
be filled by a visual redesign alone: the data to fill it is never read. Any
layout work that does not fix this ends up prettier and equally uninformative.

The roadmap already carries what is missing, in a form that needs no heroic
parsing:

    - [x] Phase 3: Repetition, Aggregation & Cost Decomposition (2/2 plans) — completed 2026-07-26

Title, plan progress and completion date are all on the line.

## What to build

### 1. Pending work as a described list, not a row

Pending phases are currently a compact row of ids. They become a list, one
entry per phase, each carrying **what the phase is about** — enough that
choosing what to run next is an informed decision rather than a guess at a
number. Per entry: phase number, title, plan progress (`2/3 plans`), and its
state on disk (planned / executed / verified).

The operator's words for why: what is missing is knowing what each pending
phase *is*, so the choice of what to execute can be assertive.

### 2. Next commands, in cairn's own namespace, with the reason for the order

A section listing **which `/cairn:*` commands to run next and why in that
order**. Explicitly not a list of GSD commands: the surface should speak the
vocabulary the operator drives.

The next legal command per phase is derivable from state on disk, so this is
computed, not authored:

| state on disk | next command |
|---|---|
| no PLAN.md | `/cairn:plan <N>` |
| PLAN.md, no SUMMARY.md | `/cairn:work <N>` |
| SUMMARY.md, no VERIFICATION.md | `/cairn:verify <N>` |
| every phase complete | `/cairn:ship`, then `/cairn:milestone complete` |

Ordering comes from the roadmap's declared dependencies, not from phase number.

### 3. Parallelism and autonomy

With dependencies mapped, phases that depend on nothing still open are
independent and can proceed at the same time. The panel should say so
concretely: which phases can run in parallel right now, and what the split
looks like — for instance planning one phase while another executes.

This is the input for a multi-agent workflow suggestion and for
`/cairn:autonomous`, which today decides its own order without surfacing it.

## Notes on scope

- The same three blocks are what fill the HTML board's empty space. The
  operator's complaint about the board ("use the whole screen, it is opened on
  a desktop") and this request are one piece of work, not two.
- The terminal board, `--json` and the HTML board should all read from one
  model, so the three surfaces cannot drift.
- Layers A1 (pull requests and review state) and A2 (external tracker status
  reconciliation) exist in the reference panel the operator demonstrated.
  They are out of scope for this milestone and are noted only so the phase
  panel is designed without blocking them later.
