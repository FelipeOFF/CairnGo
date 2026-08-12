<!-- cairn capability — plan:post fragment, injected into the planner.
     Links every generated PLAN.md to the bd issues it advances, then
     regenerates the phase's NN-BEADS-MAP.md view. Skill-level source of
     truth for the conventions: the cairn plugin skill "cairn". -->

## Link plans to beads issues (cairn)

Applies only when the project root contains BOTH `.planning/` and `.beads/`.
If either is missing, skip this section entirely and say nothing.

After the phase's PLAN.md files are written:

1. **Resolve requirements against the tracker.** List the phase's issues:
   `bd list -l m-<milestone>,phase-<N> --all --limit 0 --json` (unpadded `N`,
   e.g. `phase-3`). Each cairn-managed issue carries
   `metadata.gsd.req` — match those ids against each PLAN.md's
   `requirements:` frontmatter list.
2. **Create issues for unmapped requirements** (dedup key
   `(gsd.req, gsd.milestone)` — never create a second issue for a
   requirement that already has one in this milestone):
   ```bash
   bd create "CAT-NN: <requirement title>" \
     -l m-<milestone>,phase-<N> \
     --metadata '{"gsd": {"req": "CAT-NN", "phase": N, "milestone": "vX.Y", "plan": "NN-PP"}}'
   ```
3. **Write `beads:` frontmatter** on every generated PLAN.md — the bd ids
   that plan advances, with a short trailing comment mapping ids to
   requirements:
   ```yaml
   beads: [proj-7hp, proj-4qv]   # REQ-01/02 — provisioner; REQ-04 — registry
   ```
   A plan whose requirements have no issues (nothing tracker-worthy) may
   omit the key — do not invent issues for it.
4. **Regenerate the phase map** so `<NN>-BEADS-MAP.md` reflects the new
   links (the bundle script no-ops outside beads repos):
   ```bash
   CAP=".gsd/capabilities/cairn"; [ -d "$CAP" ] || CAP="${GSD_HOME:-$HOME}/.gsd/capabilities/cairn"
   bash "$CAP/scripts/cairn-map.sh" <N>
   ```

Precedence: where a bd issue conflicts with the phase's CONTEXT.md or
PLAN.md, the GSD doc wins — update the issue (dated reconciliation note
outside the map's generated markers), never follow the stale issue. If
`.cairn/sync.json` has an enabled backend, push the mirror for each issue
you created or updated (see the cairn-sync skill).
