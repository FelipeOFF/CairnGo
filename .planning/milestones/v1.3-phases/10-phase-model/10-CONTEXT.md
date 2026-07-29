# Phase 10: Phase model — read what a phase actually is - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning
**Source:** Interactive autonomous run, continuing straight from v1.2.

<domain>
## Phase Boundary

The status surface can only render a phase as a number, because a number is all
it reads. Requirement: PANEL-01. bd issue: CairnGo-b33 — see `10-BEADS-MAP.md`.

Research backing: `.planning/research/status-phase-panel.md`.

This phase builds the model and proves the three surfaces render from it. The
described pending list (PANEL-02), the next-command section (PANEL-03), the
parallelism note (PANEL-04) and the desktop layout (PANEL-05) consume it in
phases 11 and 12.

</domain>

<decisions>
## Implementation decisions (locked)

- **One read, three surfaces.** `phase_model()` is built once in `main()` and
  handed to the terminal board, `--json` and the HTML page. `roadmap_phases()`
  survives only as a derivation of it, so the counts and the described list
  cannot disagree.
- **Dependencies come from bd first, PLAN.md second.** bd already holds the
  graph — the milestone registers the edges when it creates the issues — so it
  is available *before* a phase is planned. `PLAN.md`'s `depends_on:`
  frontmatter only exists after planning, and relying on it alone would report
  every unplanned phase as independent, which is the one claim the parallelism
  work must not get wrong. The two sources are unioned.
- **`next_command` is computed from disk, never authored**, so it cannot rot
  when someone runs a command out of band. A phase the roadmap calls complete
  gets no command at all, whatever the disk says: finished milestones have
  their phase dirs archived out of `.planning/phases/`, so reading disk state
  alone would tell the operator to go and plan phase 1 again.
- **Roadmap lines are parsed by shape, never by splitting on the dash.** The
  completion suffix (`— completed 2026-07-26`) carries its own em dash and
  titles carry theirs ("Phase model — read what a phase actually is"). The
  suffix is stripped by pattern; the trailing parenthetical is then classified
  as plan progress or requirement ids; what remains is the title.
- **Both roadmap dialects are supported.** `- [x] Phase 1: Title (2/2 plans) —
  completed <date>` and `- [x] **Phase 1: Title** - description` both appear in
  real repos; the bold span delimits the title and what follows it is a
  description, not part of the name.

</decisions>

<risks>
- The model reads two roadmap sources (checkbox lines and the progress table)
  and merges them. A roadmap that carries only one still works, with the fields
  the other would have supplied left null rather than invented.
- Dependency coverage is only as good as what is written down. A phase with no
  bd edges and no planned `depends_on:` genuinely has no recorded dependency;
  phase 12's parallelism section must say that rather than imply independence
  was verified.
</risks>
